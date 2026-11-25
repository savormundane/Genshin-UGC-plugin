"""Native port existence, independent of whether an instance happens to store a pin."""
from functools import lru_cache
from miliastra.native.core import get,slot,ref,definition_id,node_catalog,node_records,put
from level_inventory import fields,vals
from authoring_io import PLUGIN,read_json


SERVER_BUILTIN = (10001, 20000, 22000, 0)
EDITOR_LIST_CAPACITY = 100
# Slots present in the server editor contracts and omitted from the bundled
# native catalogue. Keys are (builtin, pin direction, index).
SERVER_EXTRA_PORTS = {
    (224, 3, 1):14, (245, 3, 5):14, (245, 3, 6):14, (260, 4, 0):14,
    (319, 3, 0):14, (384, 3, 2):14, (395, 3, 2):14, (398, 3, 1):14, (399, 3, 1):14,
    (652, 3, 1):14, (653, 4, 0):14, (656, 3, 1):14, (657, 4, 0):14,
    (668, 3, 5):14, (668, 3, 6):14, (683, 4, 5):14, (697, 3, 5):14,
    (725, 3, 1):27, (768, 4, 0):14, (1938, 3, 1):14, (3360, 3, 0):28, (3360, 3, 1):6,
}
# Editor literals omitted by older public signatures. Their enum values are
# cross-checked against NodeEditorPack's enum_id.ts. They cannot accept edges.
SERVER_STORED_ENUMS = {
    (209, 210, 2): (305,),
    (389, 389, 2): (2820,2821),
    (395, 395, 3): (2810,2811,2812),
}
# The hidden nameplate editor action has a standard execution entrance.
SERVER_EXTRA_FLOWS = {615:{1:1,2:1}}
CLIENT_CATEGORIES = (20001,20002,20007)
# Wire pin types from the two VarType enums. A client vector (11), for
# example, must not be read as a server string-list (11).
CLIENT_TYPES = {'Ety':1,'L<Ety>':2,'Int':3,'L<Int>':4,'Bol':5,'L<Bol>':6,
                'Flt':7,'L<Flt>':8,'Str':9,'L<Str>':10,'Vec':11,'L<Vec>':12,
                'Gid':14,'L<Gid>':15,'Fct':16,'Cfg':18,'Pfb':19,'L<Cfg>':20,
                'L<Pfb>':21,'Struct':22,'L<Struct>':23,'L<Fct>':25}
# Local-variable kernels share a concrete ID across value types. Their
# ConcreteBase index and the inner ClientType descriptor identify the type.
CLIENT_LOCAL_TYPES = (3,9,1,14,7,11,5,4,10,2,15,8,12,6,18,19,20,21,16,25,24)
CLIENT_LOCAL_PORTS = {(200081,2000):(3,1),(200082,1036):(4,0)}
# Creation Status Get_Custom_Variable specializations verified in the two
# official Creation templates and the client_variable_specialization seed.
CLIENT_STATUS_OUTPUTS = {4200:5,4201:3,4202:7,4206:11}
CLIENT_CONVERSIONS = {
    801:(3,7),802:(3,9),803:(1,9),804:(14,9),805:(5,3),
    806:(5,9),807:(7,3),808:(7,9),809:(11,9),810:(16,9),
}


@lru_cache(maxsize=1)
def client_contracts():
    source=read_json(PLUGIN/'scripts/native-client-ports.json')
    return {tuple(map(int,key.split('/'))):{(kind,index):typ for kind,index,typ in pins}
            for key,pins in source['nodes'].items()}


@lru_cache(maxsize=2048)
def client_node(n):
    locator,_,_=node_records(n)
    return get(locator,1,0)==10001 and get(locator,2,0) in CLIENT_CATEGORIES


@lru_cache(maxsize=2048)
def client_contract(n):
    generic,concrete,_=node_records(n)
    category,ident,cid=get(generic,2,0),ref(generic),get(concrete,5,0,0)
    # Older fixed point projectile launches use a server-category locator for
    # the same fixed kernel. The shell and port contract remain Skill.
    kernel_category=20000 if (category,ident,cid)==(20002,200052,2000) and get(concrete,2,0)==20000 else category
    if (category not in CLIENT_CATEGORIES or not concrete or any(
            (get(loc,1,0),get(loc,2,0),get(loc,3,0),get(loc,4,0,0))!=(10001,scope,22000,0)
            for loc,scope in ((generic,category),(concrete,kernel_category)))):
        return None
    if (category,ident)==(20007,200173) and cid in CLIENT_STATUS_OUTPUTS:
        return {(3,0):13,(3,1):9,(4,0):CLIENT_STATUS_OUTPUTS[cid]}
    # Filter Get Custom Variable has an additional concrete form for a list
    # of structures. The reference audit checks its actual structure ID.
    if (category,ident,cid)==(20001,200016,1064):
        return {(3,0):1,(3,1):9,(4,0):23}
    return client_contracts().get((category,ident,cid))


def client_value_type(value):
    descriptor=get(value,4,default=b'')
    return get(get(descriptor,101,default=b''),2,0) if get(descriptor,1,0)==2 else None


def client_local_type(pin):
    value=get(pin,3,default=b'')
    wrapper=get(value,110,default=b'')
    index=get(wrapper,1,0,0)
    native_type=client_value_type(get(wrapper,2,default=b''))
    if (get(value,1,0)==10000 and wrapper
            and 0<=index<len(CLIENT_LOCAL_TYPES) and native_type==CLIENT_LOCAL_TYPES[index]):
        return native_type
    return None


def client_conversion(n,kind,index):
    if (kind,index) not in ((3,1),(4,0)):return None
    _,_,pins=node_records(n)
    selector=pins.get((3,0),b'')
    if vals(fields(selector),5):return None
    value=get(get(get(selector,3,default=b''),110,default=b''),2,default=b'')
    if get(value,1,0)!=6 or client_value_type(value)!=13:return None
    types=CLIENT_CONVERSIONS.get(get(get(value,106,default=b''),1,0))
    return types[kind==4] if types is not None else None


def catalogue_type(token,types,client):
    if client:
        if token.startswith('L<E<'):return 17
        if token.startswith('E<'):return 13
        if token.startswith('D<') and 'R<' not in token:return 24
        return CLIENT_TYPES.get(token)
    known=types.get(token)
    if known is not None:return known
    if token.startswith('E<'):return 14
    if token.startswith('D<') and 'R<' not in token:return 27
    return None


def declared_kernel_matches(n,definition):
    signature=get(definition,4,default=b'')
    generic,concrete,_=node_records(n)
    shell,kernel=get(signature,1),get(signature,2)
    if not shell or not kernel:return False
    # A distinct kernel must match both locators from the same declaration.
    # The declaration's own role, class and peer contract are audited separately.
    identity=lambda locator:tuple(get(locator,i,0,0) for i in (1,2,3,4,5))
    return identity(generic)==identity(shell) and identity(concrete)==identity(kernel)


def server_builtin(n, ident):
    locator, _, _ = node_records(n)
    return (ref(locator) == ident and tuple(get(locator, field, 0, 0) for field in (1, 2, 3, 4)) == SERVER_BUILTIN)


def server_enum_literal(n,ident,kind,index):
    _,concrete,pins=node_records(n)
    enums=SERVER_STORED_ENUMS.get((ident,ref(concrete),index))
    if kind!=3 or enums is None or not server_builtin(n,ident):return False
    if tuple(get(concrete,i,0,0) for i in (1,2,3,4))!=SERVER_BUILTIN:return False
    pin=pins.get((kind,index),b'')
    value=get(pin,3,default=b'')
    if ident==209:value=get(get(value,110,default=b''),2,default=b'')
    descriptor=get(value,4,default=b'')
    return (not vals(fields(pin),5) and get(value,1,0)==6 and get(descriptor,1,0)==1
            and get(get(descriptor,100,default=b''),1,0)==14
            and get(get(value,106,default=b''),1,0) in enums)


@lru_cache(maxsize=256)
def editor_list_storage(n):
    """Calibrated editor list specialization, including in-file structure types."""
    if not server_builtin(n, 169):
        return False
    _, locator, _ = node_records(n)
    return (any(row['ConcreteId']==ref(locator) for row in node_catalog()[0][169]['TypeMappings'])
            and tuple(get(locator,i,0,0) for i in (1,2,3,4))==SERVER_BUILTIN) or struct_list_assembly(n)


@lru_cache(maxsize=128)
def struct_list_assembly(n):
    """The structure specialization has no concrete locator and uses a registered item type."""
    if not server_builtin(n,169):return False
    _,concrete,pins=node_records(n)
    if concrete:return False
    from miliastra.native.core import structure_ids
    output=get(pins.get((4,0),b''),3,default=b'')
    variant=get(output,110,default=b'')
    descriptor=get(get(variant,2,default=b''),4,default=b'')
    registered={get(get(r,100,default=b''),1,0) for r in vals(fields(n),10)}-{None}
    return (get(output,1,0)==10000 and get(variant,1,0)==10 and
            get(descriptor,1,0)==1 and get(get(descriptor,100,default=b''),1,0)==26 and
            len(registered)==1 and structure_ids(n,4,0,{})==registered)


@lru_cache(maxsize=1)
def flow_catalog():
    # Read declarations as data through the existing AST catalogue; never execute
    # third-party node implementations. The bundled writer uses these ordinals
    # when no NodeEditorPack index override is present.
    from node_build import node_definitions
    declarations={}
    for entry in node_definitions():
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


@lru_cache(maxsize=256)
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


def declaration_type(port):
    descriptor=get(port,4,default=b'')
    typ=get(descriptor,3,0)
    enum=get(get(descriptor,101,default=b''),1,0)
    if get(descriptor,1,0)==6 and get(descriptor,4,0)==14 and enum and typ==10000+enum:
        return 14
    if typ is None and (get(descriptor,1,0),get(descriptor,4,0),enum)==(6,4,1):
        return 4  # Modify Structure's per-field write switch.
    return typ


def structure_update(definition):
    return get(get(definition,107,default=b''),1,0)==1005


def instance_declared_port(n,definition,kind,index):
    ports=declared_ports(definition)
    if structure_update(definition) and kind==3:
        _,_,pins=node_records(n)
        uid=get(pins.get((kind,index),b''),7,0)
        if uid is not None:
            # The stored slot can predate new members inserted into the
            # structure. Composite pin UIDs survive that ordinal change.
            return next((p for (k,_),p in ports.items()if k==kind and get(p,8,0)==uid),None)
        if (kind,index) not in pins:
            current={get(p,8,0):i for (k,i),p in ports.items()if k==kind}
            if any(k==kind and get(p,7,0) in current and current[get(p,7,0)]!=i
                   for (k,i),p in pins.items()):
                return None  # No stored identity for an implicit moved slot.
    return ports.get((kind,index))


def reference_error(n,definitions):
    generic=ref(get(n,2,default=b''));concrete=ref(get(n,3,default=b''))
    if generic in definitions:
        if concrete is not None and concrete!=generic and not declared_kernel_matches(n,definitions[generic]):
            return 'declaration references disagree'
        return None
    if client_contract(n) is not None:return None
    entry=node_catalog()[0].get(generic)
    if entry is None:return 'generic node definition absent'
    if generic in(300000,300001,300002,300003,300004):return None
    # A concrete ID is scoped to this generic family, not merely to any known
    # node or user definition in the file. Omission retains the generic form.
    allowed={generic}|{m['ConcreteId']for m in entry.get('TypeMappings',[])}
    # Fixed client kernels are declared directly in the bundled catalogue.
    # A shared numeric kernel ID is only valid with the matching client locator.
    if entry.get('Range')=='Client' and entry.get('ConcreteID')==concrete:
        descriptors=[get(n,field,default=b'') for field in (2,3)]
        if all(tuple(get(d,i,0,0) for i in (1,2,3,4))==(10001,20002,22000,0) for d in descriptors):
            return None
    if concrete is not None and concrete not in allowed:return 'concrete type outside generic family'
    return None


def resolve_dynamic(n,definitions,signals,roles):
    """Resolve generic signal selectors against this file's actual declarations."""
    generic=ref(get(n,2,default=b''));concrete=ref(get(n,3,default=b''))
    ident=definition_id(n,definitions)
    if generic not in(300000,300001,300002,300003,300004)and ident not in roles:return n,None
    if (concrete is not None and concrete not in definitions and concrete!=generic and
            not (generic in definitions and declared_kernel_matches(n,definitions[generic]))):
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
        from miliastra.native.model import constant
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


def exists(n,kind,index,definitions,*,stored=False):
    """True/False from a known contract; None means the contract is unresolved."""
    if kind not in(1,2,3,4,5,6)or index<0:return False
    definition=definitions.get(definition_id(n,definitions))
    if definition is not None:
        if instance_declared_port(n,definition,kind,index) is not None:return True
        return None if structure_update(definition) and kind==3 else False
    contract=client_contract(n)
    if contract is not None and (kind,index) in contract:
        generic,concrete,pins=node_records(n)
        if (kind,index)==CLIENT_LOCAL_PORTS.get((ref(generic),ref(concrete))):
            return True if client_local_type(pins.get((kind,index),b'')) is not None else None
        if (ref(generic),ref(concrete))==(200022,130) and (kind,index) in ((3,1),(4,0)):
            return True if client_conversion(n,kind,index) is not None else None
        return True
    ident=ref(get(n,2,default=b''));entry=node_catalog()[0].get(ident)
    if entry is None:return None
    if kind in(1,2):
        counts=flow_catalog().get(ident)
        if counts is None and server_builtin(n,ident):counts=SERVER_EXTRA_FLOWS.get(ident)
        if counts is None:
            return False if entry['Class']in('Query','Arithmetic')else None
        if ident==3 and kind==2:
            # Multiple_Branches stores its ordered case labels at InParam 1.
            p=next((p for p in vals(fields(n),4)if slot(p)==(3,1)),None)
            if p is None:return index==0
            if vals(fields(p),5)or get(p,3)is None:return None
            from miliastra.native.model import constant
            cases=constant(get(p,3))
            if not isinstance(cases,list):return False
            return index<=len(cases)
        return index<counts[kind]
    if kind in(5,6):
        # Metadata layout differs by builtin family. Do not infer its schema
        # from the data port list; dynamic declarations are checked above.
        return None
    if ident in(300000,300001,300002,300003,300004):
        # The builtin catalogue describes only the unbound skeleton.
        return None
    if ident==169 and kind==3:
        # Assembly_List's first native input is the count, followed by items.
        _,_,pins=node_records(n)
        p=pins.get((3,0))
        expanded=editor_list_storage(n)
        if p is None:return 1<=index<=EDITOR_LIST_CAPACITY if expanded else None
        if vals(fields(p),5)or get(p,3)is None:return None
        from miliastra.native.model import constant
        count=constant(get(p,3))
        if type(count)!=int or not 0<=count<=EDITOR_LIST_CAPACITY:return False
        item=pins.get((kind,index),b'')
        return index<=(EDITOR_LIST_CAPACITY if stored and expanded and not vals(fields(item),5) else count)
    if (ident,kind,index) in SERVER_EXTRA_PORTS and server_builtin(n,ident):return True
    if stored and server_enum_literal(n,ident,kind,index):return True
    # The bundled catalogue omits the list-index argument. The official node
    # signature and the writer's emitted InParam 1 both define an integer.
    if ident==128 and kind==3 and index==1:return True
    # Official server signature and original GIL both store the variable name
    # at InParam 0. It is missing from the bundled getter catalogue.
    if ident==337 and kind==3 and index==0:return True
    ports=entry['Inputs'if kind==3 else'Outputs']
    if contract is not None and kind==3:return None
    return index<len(ports)
