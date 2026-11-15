"""Native port existence, independent of whether an instance happens to store a pin."""
from functools import lru_cache
from native_core import get,slot,ref,definition_id,node_catalog,put
from level_inventory import fields,vals
from authoring_io import PLUGIN,read_json


@lru_cache(maxsize=1)
def flow_catalog():
    # Read declarations as data through the existing AST catalogue; never execute
    # third-party node implementations. The bundled writer uses these ordinals
    # when no NodeEditorPack index override is present.
    from node_build import catalog
    declarations={}
    for entry in catalog(limit=10000)['nodes']:
        key=(entry['scope'],entry['name'])
        shape={kind:sum(p[1]=='流程'for p in entry.get(side,[]))
               for kind,side in((1,'inputs'),(2,'outputs'))}
        if key in declarations and declarations[key]!=shape:
            raise ValueError('Ambiguous node flow declaration '+str(key))
        declarations[key]=shape
    mapping=read_json(PLUGIN/'vendor/ayaya/private_extensions/ugc_file_tools/graph_ir/node_type_semantic_map.json')
    return {int(ident):declarations[(item.get('scope'),item.get('graph_generater_node_name'))]
            for ident,item in mapping.items()
            if (item.get('scope'),item.get('graph_generater_node_name'))in declarations}


def declared_ports(definition):
    ports={};uids=set()
    for kind,group in((1,100),(2,101),(3,102),(4,103),(5,106)):
        for ordinal,p in enumerate(vals(fields(definition),group)):
            uid=get(p,8,0)
            if uid is not None:
                if uid in uids:raise ValueError('Duplicate declaration port UID '+str(uid))
                uids.add(uid)
            descriptor=get(p,3)
            # Calibration includes editor selectors (e.g. struct update target)
            # without a port descriptor. They must not alias data input zero.
            if descriptor is None and kind!=5:continue
            # Meta entries use their group ordinal when they have no shell
            # descriptor (calibrated signal-name selectors).
            index=get(descriptor,2,0,0)if descriptor is not None else ordinal
            key=(kind,index)
            if key in ports:raise ValueError('Duplicate declaration port '+str(key))
            declared_kind=get(descriptor,1,0,kind)if descriptor is not None else kind
            if declared_kind!=kind:raise ValueError('Declaration port kind disagrees with group')
            ports[key]=p
    return ports


def reference_error(n,definitions):
    generic=ref(get(n,2,default=b''));concrete=ref(get(n,3,default=b''))
    if generic in definitions:
        if concrete is not None and concrete!=generic:return 'declaration references disagree'
        return None
    entry=node_catalog()[0].get(generic)
    if entry is None:return 'generic node definition absent'
    if generic in(300000,300001,300002,300003,300004):return None
    # A concrete ID is scoped to this generic family, not merely to any known
    # node or user definition in the file. Omission retains the generic form.
    allowed={generic}|{m['ConcreteId']for m in entry.get('TypeMappings',[])}
    if concrete is not None and concrete not in allowed:return 'concrete type outside generic family'
    return None


def resolve_dynamic(n,definitions,signals,roles):
    """Resolve generic signal selectors against this file's actual declarations."""
    generic=ref(get(n,2,default=b''));concrete=ref(get(n,3,default=b''))
    ident=definition_id(n,definitions)
    if generic not in(300000,300001,300002,300003,300004)and ident not in roles:return n,None
    if concrete is not None and concrete not in definitions and concrete!=generic:
        return n,'dynamic concrete declaration absent'
    if generic in roles and concrete in roles and generic!=concrete:
        return n,'signal declaration references disagree'
    if generic in(300002,300003,300004):
        return (n,None)if ident in definitions else(n,'dynamic structure declaration absent')
    meta_index=1 if roles.get(ident,(None,None))[1]==7 else 0
    meta=next((p for p in vals(fields(n),4)if slot(p)==(5,meta_index)),None)
    name=None
    if meta is not None:
        value=get(meta,3)
        if value is None or vals(fields(meta),5):return n,'dynamic selector must be a constant'
        from native_model import constant
        name=constant(value)
        if not isinstance(name,str):return n,'dynamic selector must be a string'
    if ident in definitions:
        if generic in(300000,300001)and ident not in roles:return n,'signal role not registered'
        if ident in roles:
            expected,role=roles[ident]
            if generic in(300000,300001)and role!={300000:1,300001:2}[generic]:return n,'signal role disagrees with generic node'
            if name is not None and name!=expected:return n,'signal selector disagrees with declaration'
        return n,None
    if generic not in(300000,300001):return n,'dynamic structure declaration absent'
    if name is None:return n,'signal selector absent'
    matches=[i for i,r in roles.items()if r==(name,{300000:1,300001:2}[generic])]
    if len(matches)!=1:return n,'signal selector absent or ambiguous in registry'
    declaration=definitions.get(matches[0])
    locator=get(get(declaration,4,default=b''),1)if declaration is not None else None
    if locator is None or ref(locator)not in definitions:return n,'signal role declaration absent'
    return put(n,3,locator),None


def exists(n,kind,index,definitions):
    """True/False from a known contract; None means the contract is unresolved."""
    if kind not in(1,2,3,4,5)or index<0:return False
    definition=definitions.get(definition_id(n,definitions))
    if definition is not None:return (kind,index)in declared_ports(definition)
    ident=ref(get(n,2,default=b''));entry=node_catalog()[0].get(ident)
    if entry is None:return None
    if kind in(1,2):
        counts=flow_catalog().get(ident)
        if counts is None:
            return False if entry['Class']in('Query','Arithmetic')else None
        if ident==3 and kind==2:
            # Multiple_Branches stores its ordered case labels at InParam 1.
            p=next((p for p in vals(fields(n),4)if slot(p)==(3,1)),None)
            if p is None:return index==0
            if vals(fields(p),5)or get(p,3)is None:return None
            from native_model import constant
            cases=constant(get(p,3))
            if not isinstance(cases,list):return False
            return index<=len(cases)
        return index<counts[kind]
    if kind==5:
        # Metadata layout differs by builtin family. Do not infer its schema
        # from the data port list; dynamic declarations are checked above.
        return None
    if ident in(300000,300001,300002,300003,300004):
        # The builtin catalogue describes only the unbound skeleton.
        return None
    if ident==169 and kind==3:
        # Assembly_List's first native input is the count, followed by items.
        p=next((p for p in vals(fields(n),4)if slot(p)==(3,0)),None)
        if p is None or vals(fields(p),5)or get(p,3)is None:return None
        from native_model import constant
        count=constant(get(p,3))
        if type(count)!=int or not 0<=count<=100:return False
        return index<=count
    # The bundled catalogue omits the list-index argument. The official node
    # signature and the writer's emitted InParam 1 both define an integer.
    if ident==128 and kind==3 and index==1:return True
    # Official server signature and original GIL both store the variable name
    # at InParam 0. It is missing from the bundled getter catalogue.
    if ident==337 and kind==3 and index==0:return True
    return index<len(entry['Inputs'if kind==3 else'Outputs'])
