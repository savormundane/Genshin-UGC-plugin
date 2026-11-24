"""Raw-preserving native graph model, final-edge audit and explicit schema-2 patches."""
from pathlib import Path
from collections import Counter
import argparse,json
from functools import lru_cache
from level_inventory import calibrated_container,fields,vals,unique,container,graph_summary,graph_records,entity_graph_ids,graph_component_field,graph_library_ids
from level_authoring import msg,integer,pack,set_section
from authoring_io import PLUGIN,sha,read_json,schema,resolve,write_json

@lru_cache(maxsize=1)
def node_catalog():
    v=read_json(PLUGIN/'vendor/ayaya/private_extensions/ugc_file_tools/node_data/index.json')
    return {x['ID']:x for x in v['NodesList']}, {x['Expression']:x['ID'] for x in v['TypesList']}

def get(b,n,w=2,default=None):return unique(fields(b),n,w,default)
def put(b,n,v,w=2):
    fs=fields(b);hits=[x for x in fs if x[:2]==(n,w)]
    if len(hits)>1:raise ValueError('Ambiguous field '+str(n))
    raw=integer(n,v) if w==0 else msg(n,v)
    return b''.join(raw if x[:2]==(n,w) else x[3] for x in fs)+(raw if not hits else b'')
def rewrite(b,n,fn):return b''.join(msg(n,fn(v)) if a==n and w==2 else raw for a,w,v,raw in fields(b))
def replace_message(parent,field,old,new):
    rows=fields(parent)
    if sum((n,w,v)==(field,2,old) for n,w,v,_ in rows)!=1:
        raise ValueError('Native message selector must match exactly once: '+str(field))
    if old==new:return parent
    return b''.join(msg(n,new) if (n,w,v)==(field,2,old) else raw for n,w,v,raw in rows)
def ref(b):return get(b,5,0)
def definition_id(n,definitions):
    concrete=ref(get(n,3,default=b''));generic=ref(get(n,2,default=b''))
    return concrete if concrete in definitions else generic
def descriptor_structure_ids(descriptor):
    """TypedValue may carry a struct identity directly or inside list type info."""
    ids={get(get(descriptor,104,default=b''),2,0)}-{None}
    if get(descriptor,3,0)==26:
        child=get(get(descriptor,102,default=b''),1)
        if child is not None:ids.update(descriptor_structure_ids(child))
    return ids
def descriptor_structure_id(descriptor):
    ids=descriptor_structure_ids(descriptor)
    return next(iter(ids))if len(ids)==1 else None
def structure_ids(n,kind,index,definitions):
    from native_ports import client_node
    ids=set()
    d=definitions.get(definition_id(n,definitions))
    if d:
        from native_ports import instance_declared_port
        port=instance_declared_port(n,d,kind,index)
        if port is not None:ids.update(descriptor_structure_ids(get(port,4,default=b'')))
    for p in vals(fields(n),4):
        if slot(p)!=(kind,index):continue
        value=get(p,3,default=b'')
        if get(value,1,0)==10000:
            concrete=get(value,110,default=b'')
            wrapper=get(get(get(concrete,5,default=b''),100,default=b''),1,default=b'')
            ids.add(get(get(wrapper,100,default=b''),1,0))
            value=get(concrete,2,default=b'')
        sid=get(get(get(get(value,4,default=b''),100,default=b''),100,default=b''),1,0)
        if sid is not None:ids.add(sid)
        if client_node(n):
            descriptor=get(value,4,default=b'')
            info=get(descriptor,101,default=b'')
            if get(descriptor,1,0)==2 and get(info,2,0) in (22,23):
                ids.add(get(get(info,100,default=b''),1,0))
    registrations=vals(fields(n),10)
    if d is None:ids.update(get(get(r,100,default=b''),1,0)for r in registrations)
    if ref(get(n,2,default=b''))==18 and kind==4 and index==1:
        for p in vals(fields(n),4):
            if slot(p)!=(3,0):continue
            value=get(p,3,default=b'')
            if get(value,1,0)==10000:value=get(get(value,110,default=b''),2,default=b'')
            ids.add(get(get(get(get(value,4,default=b''),100,default=b''),100,default=b''),1,0))
    ids.discard(None)
    return ids

def structure_id(n,kind,index,definitions):
    ids=structure_ids(n,kind,index,definitions)
    return next(iter(ids))if len(ids)==1 else None
def slot(b):
    k=get(b,1,default=b'');return get(k,1,0,0),get(k,2,0,0)


@lru_cache(maxsize=1024)
def node_records(n):
    rows=fields(n)
    pins={}
    for pin in vals(rows,4):
        pins.setdefault(slot(pin),pin)
    return unique(rows,2,default=b''),unique(rows,3,default=b''),pins


def graph_blobs(data):
    return [raw for kind,raw in graph_records(data)if kind=='ordinary']
def model(data):
    header,root=container(data);definitions={};graphs=[];composites=[];mounts=[];structs=[];signals=[];entities=[];resources=[]
    if header[3]==3:
        for unit in vals(root,1)+vals(root,2):
            locator=get(unit,1,default=b'')
            resources.append({'class':get(locator,2,0,0),'id':get(locator,4,0,0),'references':[[get(r,2,0,0),get(r,4,0,0)]for r in vals(fields(unit),2)]})
            structure_wrapper=get(unit,22)
            if structure_wrapper is not None or get(unit,5,0)==29:
                structure=get(structure_wrapper or b'',1)
                if structure is None:raise ValueError('Unsupported GIA structure wrapper')
                sid=get(get(structure,1,default=b''),1,0)
                if (get(locator,2,0),get(locator,3,0),get(locator,4,0),get(unit,5,0))!=(1,15,sid,29) or sid is None:
                    raise ValueError('GIA structure resource identity mismatch')
                structs.append(structure)
            wrapper=get(unit,14)
            if wrapper is not None:
                d=get(get(wrapper,1,default=b''),1)
                if d is None:raise ValueError('Unsupported GIA declaration wrapper')
                ident=ref(get(get(d,4,default=b''),1,default=b''))
                if get(locator,2,0)!=23 or get(locator,4,0)!=ident:raise ValueError('GIA declaration resource identity mismatch')
                if ident in definitions:raise ValueError('Duplicate definition ID '+str(ident))
                definitions[ident]=d
    for section in vals(root,10):
        for raw in vals(fields(section),2):
            d=get(raw,1,default=b'');locator=get(get(d,4,default=b''),1,default=b'');ident=ref(locator)
            if ident in definitions:raise ValueError('Duplicate definition ID '+str(ident))
            definitions[ident]=d
        structs+=vals(fields(section),6)
        for registry in vals(fields(section),5):signals+=vals(fields(registry),3)
    for kind,raw in graph_records(data):
        nodes={}
        for n in vals(fields(raw),3):
            ident=get(n,1,0)
            if ident in nodes:raise ValueError('Duplicate node index '+str(ident))
            nodes[ident]=n
        (graphs if kind=='ordinary'else composites).append({'raw':raw,'kind':kind,'id':ref(get(raw,1,default=b'')),'name':get(raw,2,default=b'').decode('utf-8'),'nodes':nodes})
    for section_id in ((4,5)if header[3]!=3 else()):
        for section in vals(root,section_id):
            for entity in vals(fields(section),1):
                identity={'section':section_id,'entity_id':get(entity,1,0)}
                entities.append(identity)
                mounts.extend({**identity,'graph_id':gid} for gid in entity_graph_ids(entity,section_id))
    ids=[g['id'] for g in graphs]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate graph ID')
    ids=[g['id']for g in composites]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate composite graph ID')
    libraries=list(graph_library_ids(root)) if header[3]!=3 else []
    storage=[t for section in vals(root,31)for t in vals(fields(section),1)]
    from native_variables import read
    variables=read(root)if header[3]!=3 else{'records':[],'issues':[],'unresolved':[]}
    return {'format':'gia'if header[3]==3 else'gil','graphs':graphs,'composite_graphs':composites,'definitions':definitions,'structs':structs,'signals':signals,'mounts':mounts,'entities':entities,'graph_library':libraries,'storage_templates':storage,'resources':resources,'custom_variables':variables}
def inspect(data):
    m=model(data)
    from native_variables import summary
    from native_graph_variables import read as graph_variables,summary as graph_variable_summary,accesses as graph_variable_accesses
    from native_signals import declarations
    signal_declarations=[{**r,'peers':{k:ref(v)for k,v in r['peers'].items()}}for r in declarations(m).values()]if m['format']=='gia'else[]
    instances=[]
    for g in m['graphs']+m['composite_graphs']:
        for ident,n in g['nodes'].items():
            instances.append({'graph_id':g['id'],'graph_kind':g['kind'],'node':ident,'generic_type':ref(get(n,2,default=b'')),'concrete_type':ref(get(n,3,default=b'')),'definition_id':definition_id(n,m['definitions']),'definition_version':get(n,9,0),'ports':[{'slot':list(slot(p)),'type_id':get(p,4,0),'structure_id':structure_id(n,*slot(p),m['definitions'])if slot(p)[0]in(3,4)else None,'uid':get(p,7,0),'connections':[{'node':get(c,1,0),'slot':[get(get(c,2,default=b''),1,0,0),get(get(c,2,default=b''),2,0,0)]}for c in vals(fields(p),5)]}for p in vals(fields(n),4)]})
    return {'schema':2,'sha256':sha(data),'graphs':[graph_summary(g['raw']) for g in m['graphs']],'composite_graphs':[graph_summary(g['raw'])for g in m['composite_graphs']],
            'instances':instances,'definitions':[{'id':i,'name':get(d,200,default=b'').decode('utf-8'),'version':get(get(d,4,default=b''),5,0),'inputs':len(vals(fields(d),102)),'outputs':len(vals(fields(d),103)),'ports':[{'group':key,'name':get(p,1,default=b'').decode('utf-8'),'slot':[get(get(p,3,default=b''),1,0,0),get(get(p,3,default=b''),2,0,0)],'uid':get(p,8,0),'type_id':get(get(p,4,default=b''),3,0),'structure_id':descriptor_structure_id(get(p,4,default=b''))}for key in(100,101,102,103,106)for p in vals(fields(d),key)]} for i,d in m['definitions'].items()],
            'structure_count':len(m['structs']),'signal_count':len(m['signals']),'signal_declarations':signal_declarations,'entities':m['entities'],'custom_variables':[summary(r)for r in m['custom_variables']['records']],'graph_variables':[graph_variable_summary(r)for r in graph_variables(m)],'graph_variable_accesses':graph_variable_accesses(m),'mounts':m['mounts'],'graph_library':m['graph_library'],'editor_tested':False,'host_tested':False}
def register_definitions(data):
    """Keep the native declaration index complete before backend ID allocation.

    The backend prioritises section10/5/2 over declaration bodies when that
    index exists. Missing helper entries otherwise let new signal IDs overwrite
    live struct definitions. Copy locators from actual declarations only.
    """
    m=model(data);section=get(data[20:-4],10,default=b'');registry=get(section,5,default=b'')
    known={ref(r)for r in vals(fields(registry),2)}
    for ident,d in m['definitions'].items():
        if ident not in known:registry+=msg(2,get(get(d,4,default=b''),1));known.add(ident)
    return set_section(data,10,put(section,5,registry))
def bind_structures(data,bindings):
    m=model(data);section=get(data[20:-4],10,default=b'')
    for binding in bindings:
        sid=binding['struct_id'];name=binding['graph_name'];selected=[g for g in m['graphs']if g['name']==name]
        if len(selected)!=1:raise ValueError('Structure binding requires one graph')
        definitions={}
        for ident,d in m['definitions'].items():
            title=get(d,200,default=b'').decode('utf-8')
            if title not in('拼装结构体','拆分结构体','修改结构体'):continue
            ports=vals(fields(d),102)+vals(fields(d),103)
            ids={get(get(get(p,4,default=b''),104,default=b''),2,0)for p in ports}
            if sid in ids:
                if title in definitions:raise ValueError('Ambiguous structure helper declaration')
                definitions[title]=(ident,d)
        def patch_node(n):
            builtin=ref(get(n,2,default=b''))
            if builtin in node_catalog()[0] and any(get(p,4,0)in(25,26)for p in vals(fields(n),4)):
                def bind_value(p):
                    typ=get(p,4,0)
                    if typ not in(25,26):return p
                    old=structure_id(n,*slot(p),m['definitions'])
                    if old is not None and old!=sid:raise ValueError('Existing structure identity conflicts')
                    cls=10001 if typ==25 else 10002
                    item=integer(1,1)+msg(100,integer(1,typ)+integer(2,1)+msg(100,integer(1,sid)))
                    base=integer(1,cls)+msg(4,item)+msg(108 if typ==25 else 109)
                    wrapper=integer(1,cls)+(msg(100,integer(1,sid))if typ==25 else b'')
                    concrete=integer(1,22 if builtin in(22,50)else 10)+msg(2,base)+msg(5,integer(4,1)+msg(100,msg(1,wrapper)))
                    return put(p,3,integer(1,10000)+integer(2,1)+msg(110,concrete))
                n=rewrite(n,4,bind_value)
                if builtin in(22,50,128,142,169):
                    registration=msg(1,get(n,2))+integer(2,175 if builtin in(22,50)else 10)+integer(3,1)+msg(100,integer(1,sid))
                    n=put(n,10,registration)
            title={300002:'拼装结构体',300003:'拆分结构体',300004:'修改结构体'}.get(ref(get(n,2,default=b'')))
            if title is None:
                d=m['definitions'].get(definition_id(n,m['definitions']))
                if d and get(get(d,107,default=b''),1,0)in(1003,1004,1005):
                    def declared_pin(p):
                        kind,index=slot(p)
                        if kind not in(3,4):return p
                        ports=[dp for dp in vals(fields(d),102 if kind==3 else 103)if get(dp,3)is not None and get(get(dp,3),2,0,0)==index]
                        if len(ports)!=1:raise ValueError('Generated declaration port missing')
                        typ=get(get(ports[0],4,default=b''),3,0)
                        return put(p,4,typ,0)if typ is not None else p
                    return rewrite(n,4,declared_pin)
                return n
            if title not in definitions:raise ValueError('Missing native helper '+title+' for structure '+str(sid))
            ident,d=definitions[title];r=get(get(d,4,default=b''),1,default=b'');new=put(put(n,2,r),3,r)
            if title=='拆分结构体':
                # Keyword placeholders establish output types in Graph Code;
                # they are not native input ports on a split declaration.
                new=b''.join(raw for key,w,v,raw in fields(new)if not(key==4 and w==2 and slot(v)[0]==3 and slot(v)[1]>0))
            def bind_pin(p):
                kind,index=slot(p);key={1:100,2:101,3:102,4:103}.get(kind)
                if key is None:return p
                matches=[dp for dp in vals(fields(d),key)if get(dp,3)is not None and get(get(dp,3),2,0,0)==index]
                if len(matches)!=1:raise ValueError('Unbound dynamic structure port '+str((title,kind,index))+': expected '+str([(get(p,1),get(get(p,3,default=b''),2,0,0))for p in vals(fields(d),key)]))
                p=put(p,7,get(matches[0],8,0),0);typ=get(get(matches[0],4,default=b''),3,0)
                return put(p,4,typ,0)if typ is not None else p
            return rewrite(new,4,bind_pin)
        old=selected[0]['raw'];new=rewrite(old,3,patch_node)
        if m['format']=='gia':
            def unit(u):
                wrapper=get(u,13)
                if wrapper is None:return u
                inner=get(wrapper,1,default=b'')
                return put(u,13,put(wrapper,1,put(inner,1,new)))if get(inner,1)==old else u
            header,rows=container(data);body=b''.join(r for _,_,_,r in rows)
            for key in(1,2):body=rewrite(body,key,unit)
            data=pack(body,header[1:4])
        else:section=rewrite(section,1,lambda w:put(w,1,new)if get(w,1)==old else w)
    return data if m['format']=='gia'else set_section(data,10,section)
class PortTypeMismatch(ValueError):
    def __init__(self, source, actual, expected, message=None):
        self.source = source
        self.actual = actual
        self.expected = expected
        super().__init__(message or f'Instance/{source} type mismatch: actual {actual}, expected {expected}')


def port_type(n,kind,index,definitions):
    from native_ports import (CLIENT_LOCAL_PORTS, EDITOR_LIST_CAPACITY, SERVER_EXTRA_PORTS,
                              catalogue_type, client_contract, client_conversion, client_local_type, client_node,
                              client_value_type, declaration_type, editor_list_storage, instance_declared_port,
                              server_builtin, server_enum_literal, struct_list_assembly)

    generic,concrete,pins=node_records(n)
    ident,concrete_id=ref(generic),ref(concrete)
    explicit=get(pins.get((kind,index),b''),4,0)
    def checked(expected,source,message=None):
        if explicit is not None and explicit!=expected:
            raise PortTypeMismatch(source,explicit,expected,message)
        return expected
    d=definitions.get(concrete_id,definitions.get(ident))
    if d:
        port=instance_declared_port(n,d,kind,index)
        declared=declaration_type(port) if port is not None else None
        return checked(declared,'declaration') if declared is not None else explicit
    client=client_node(n)
    contract=client_contract(n)
    expected=contract.get((kind,index)) if contract is not None else None
    if contract is not None and (kind,index)==CLIENT_LOCAL_PORTS.get((ident,concrete_id)):
        expected=client_local_type(pins.get((kind,index),b''))
        return checked(expected,'client local variable descriptor') if expected is not None else None
    if contract is not None and (ident,concrete_id)==(200022,130) and (kind,index) in ((3,1),(4,0)):
        expected=client_conversion(n,kind,index)
        if expected is not None:return checked(expected,'client conversion selector')
        # The legacy catalogue has several conversion variants with the same
        # concrete ID. An unrecognized selector cannot use the first variant.
        return None
    if expected is not None:
        # Specific-location hitboxes also exist with the older list-shaped box
        # size and boolean radius toggle. Require the contextual typed value.
        legacy={(3,9):12,(3,10):5}.get((kind,index))
        if (ident,concrete_id)==(200051,2000) and legacy is not None:
            value=get(pins.get((kind,index),b''),3,default=b'')
            if client_value_type(value)==legacy:expected=legacy
        return checked(expected,'client native port contract')
    nodes,types=node_catalog();entry=nodes.get(ident)
    if entry:
        supplemental=SERVER_EXTRA_PORTS.get((ident,kind,index))
        if supplemental is not None and server_builtin(n,ident):
            return checked(supplemental,'calibrated server port')
        if server_enum_literal(n,ident,kind,index):
            return checked(14,'calibrated server enum literal')
        if entry['ID']==337 and kind==3 and index==0:
            return checked(6,'calibrated graph variable port','Graph variable name input must be string')
        if entry['ID']==128 and kind==3 and index==1:
            return checked(3,'calibrated list index port','List index input must be integer')
        if ident==169 and struct_list_assembly(n):
            if kind==3 and 1<=index<=EDITOR_LIST_CAPACITY:return checked(25,'registered structure list item')
            if kind==4 and index==0:return checked(26,'registered structure list output')
        ports=entry['Inputs' if kind==3 else 'Outputs']
        editor_slot=ident==169 and kind==3 and len(ports)<=index<=EDITOR_LIST_CAPACITY and editor_list_storage(n)
        if index<len(ports) or editor_slot:
            token='R<T>' if editor_slot else ports[index]
            known=catalogue_type(token,types,client)
            if known is not None:
                return checked(known,'catalogue')
            # Struct specialisations use usingStruct/value identity descriptors,
            # while the generic locator may retain the catalogue's default ID.
            if explicit in((22,23) if client else (25,26)) and structure_id(n,kind,index,definitions)is not None:return explicit
            mapping=next((x for x in entry.get('TypeMappings',[]) if x['ConcreteId']==concrete_id),None)
            if mapping:
                rule=mapping['Type']
                if rule.startswith('S<T:')and rule.endswith('>'):rule=rule[4:-1]
                substitute=token.replace('R<T>',rule)
                if rule.startswith('D<') and rule.endswith('>') and ',' in rule:
                    key_type,value_type=rule[2:-1].split(',',1)
                    substitute=substitute.replace('R<K>',key_type).replace('R<V>',value_type)
                if rule.startswith('S<K:') and ',V:' in rule and rule.endswith('>'):
                    key_type,value_type=rule[4:-1].split(',V:',1)
                    substitute=substitute.replace('R<K>',key_type).replace('R<V>',value_type)
                resolved=catalogue_type(substitute,types,client)
                if resolved is not None:
                    return checked(resolved,'concrete')
    return explicit


def node_location(graph,n):
    source=get(n,2,default=b'');concrete=get(n,3,default=b'')
    return {'graph':graph['id'],'graph_kind':graph['kind'],
            'graph_category':get(get(graph['raw'],1,default=b''),2,0),
            'node':get(n,1,0),
            'native_locator':[get(source,i,0,0) for i in (1,2,3,4,5)],
            'concrete_locator':[get(concrete,i,0,0) for i in (1,2,3,4,5)] if concrete else None}


def port_location(graph,n,kind,index):
    return {**node_location(graph,n),'port':[kind,index]}


def audited_port_type(graph,n,kind,index,definitions,*,conflicts=None):
    try:
        return port_type(n,kind,index,definitions)
    except PortTypeMismatch as exc:
        if conflicts is not None:
            key=(graph['kind'],graph['id'],get(n,1,0),kind,index)
            conflicts[key]={**port_location(graph,n,kind,index),'error':str(exc),
                            'code':'native_port_type_mismatch','actual':exc.actual,'expected':exc.expected,
                            'contract_source':exc.source}
        return None


def audit(data,strict=True):
    from native_ports import (client_contract,client_node,exists,declared_ports,instance_declared_port,
                              resolve_dynamic,reference_error,structure_update)
    m=model(data);issues=[];unknown=[];edges=0;catalog=node_catalog()[0]
    conflicts={}
    def type_at(graph,n,kind,index,definitions):
        return audited_port_type(graph,n,kind,index,definitions,conflicts=conflicts)
    entity_keys=Counter((e['section'],e['entity_id'])for e in m['entities'])
    for (section,ident),count in entity_keys.items():
        if ident is None:issues.append({'section':section,'error':'entity ID absent'})
        elif count>1:issues.append({'section':section,'entity_id':ident,'error':'duplicate entity ID'})
    mount_keys=Counter((e['section'],e['entity_id'],e['graph_id'])for e in m['mounts'])
    for (section,entity,gid),count in mount_keys.items():
        if count>1:issues.append({'section':section,'entity_id':entity,'graph_id':gid,'error':'duplicate graph mount'})
    for definition in m['definitions'].values():declared_ports(definition)
    sids=[get(get(s,1,default=b''),1,0)for s in m['structs']]
    if len(sids)!=len(set(sids)):issues.append({'error':'duplicate structure ID'})
    names=[get(s,3,default=b'')for s in m['signals']]
    if len(names)!=len(set(names)):issues.append({'error':'duplicate signal name'})
    roles={}
    if m['format']=='gia':
        from native_signals import declarations
        roles={i:(r['name'],r['role'])for i,r in declarations(m).items()if r['role']is not None}
    for signal in m['signals']:
        for key in(1,2,7,9):
            locator=get(signal,key)
            if locator and ref(locator)not in m['definitions']:issues.append({'error':'signal declaration missing','signal':get(signal,3,default=b'').decode('utf-8'),'definition':ref(locator)})
            if locator:
                ident=ref(locator)
                if ident in roles:issues.append({'error':'duplicate signal role ID','definition':ident})
                roles[ident]=(get(signal,3,default=b'').decode('utf-8'),key)
    # Every audit consumer needs the same resolved, read-only node view,
    # including structure checks that run before connection validation.
    for group in('graphs','composite_graphs'):
        resolved_graphs=[]
        for g in m[group]:
            resolved={}
            for ident,n in g['nodes'].items():
                reference_problem=reference_error(n,m['definitions'])
                if reference_problem:issues.append({**node_location(g,n),'error':reference_problem})
                resolved[ident],error=resolve_dynamic(n,m['definitions'],m['signals'],roles)
                if error:issues.append({**node_location(g,n),'error':error})
            resolved_graphs.append({**g,'nodes':resolved})
        m[group]=resolved_graphs
    from native_structures import audit_references
    structure_issues,structure_unknown=audit_references(m,type_at=type_at)
    issues.extend(structure_issues);unknown.extend(structure_unknown)
    from native_variables import audit as audit_variables
    variable_issues,variable_unknown=audit_variables(m)
    issues.extend(variable_issues);unknown.extend(variable_unknown)
    from native_graph_variables import audit as audit_graph_variables
    graph_variable_issues,graph_variable_unknown=audit_graph_variables(m,type_at=type_at)
    issues.extend(graph_variable_issues);unknown.extend(graph_variable_unknown)
    from native_resources import audit_resources
    resource_issues,resource_unknown=audit_resources(m,type_at=type_at)
    issues.extend(resource_issues);unknown.extend(resource_unknown)
    for g in m['graphs']+m['composite_graphs']:
        data_sources={}
        for ident,n in g['nodes'].items():
            pins=vals(fields(n),4);keys=[slot(p) for p in pins]
            if len(keys)!=len(set(keys)):issues.append({'graph':g['id'],'node':ident,'error':'duplicate pin'})
            if ref(get(n,2,default=b''))==22:
                # The bundled writer mirrors constant trigger input 3 at hidden input 4.
                triggers=[next((p for p in pins if slot(p)==(3,i)),None)for i in(3,4)]
                if all(p is not None and get(p,3)is not None and not vals(fields(p),5)for p in triggers):
                    from native_model import constant
                    if constant(get(triggers[0],3))!=constant(get(triggers[1],3)):
                        issues.append({'graph':g['id'],'node':ident,'error':'variable event trigger mirror mismatch'})
            definition=m['definitions'].get(definition_id(n,m['definitions']))
            if definition is None and ref(get(n,2,default=b''))not in catalog and client_contract(n) is None:
                unknown.append({**node_location(g,n),'error':'unknown node definition',
                                'definition':definition_id(n,m['definitions'])})
            if definition:
                expected=get(get(definition,4,default=b''),5,0,0)
                actual=get(n,9,0,0)
                if expected!=actual:issues.append({'graph':g['id'],'node':ident,'error':'definition version mismatch','expected':expected,'actual':actual})
                used_uids=set()
                for p in pins:
                    kind,index=slot(p)
                    declared=instance_declared_port(n,definition,kind,index)
                    uid=get(p,7,0)
                    if uid is not None and structure_update(definition):
                        if uid in used_uids:issues.append({**port_location(g,n,kind,index),'error':'duplicate instance port UID','uid':uid})
                        used_uids.add(uid)
                    if declared is None:issues.append({'graph':g['id'],'node':ident,'port':[kind,index],'error':'dynamic port absent or ambiguous'})
                    elif uid is not None and get(declared,8,0)is not None and uid!=get(declared,8,0):issues.append({'graph':g['id'],'node':ident,'port':[kind,index],'error':'dynamic port identity mismatch'})
            for p in pins:
                kind,index=slot(p)
                if definition is None:
                    presence=exists(n,kind,index,m['definitions'],stored=True)
                    if presence is not True:
                        where=port_location(g,n,kind,index)
                        (issues if presence is False else unknown).append({**where,
                            'contract_source':'catalogue and calibrated native ports',
                            'error':'instance port absent from contract' if presence is False else 'port contract unresolved'})
                if kind in(3,4):type_at(g,n,kind,index,m['definitions'])
            for p in pins:
                kind,index=slot(p)
                for c in vals(fields(p),5):
                    edges+=1;source=get(c,1,0);remote=get(c,2,default=b'');rk,ri=get(remote,1,0,0),get(remote,2,0,0)
                    if source not in g['nodes']:issues.append({'graph':g['id'],'node':ident,'error':'dangling edge','source':source});continue
                    if (kind,rk)not in((2,1),(1,2),(3,4),(4,3)):
                        issues.append({'graph':g['id'],'node':ident,'error':'invalid edge direction','ports':[[kind,index],[rk,ri]]});continue
                    if kind in(1,2):
                        target=g['nodes'][source]
                        presence=exists(target,rk,ri,m['definitions'])
                        if presence is False:issues.append({'graph':g['id'],'node':ident,'error':'execution edge port absent','target':source,'port':[rk,ri]})
                        elif presence is None:unknown.append({'graph':g['id'],'node':ident,'error':'execution edge contract unresolved','target':source,'port':[rk,ri]})
                        continue
                    # Normalize both serialized directions. Mirrored endpoint
                    # records describe one edge, not two independent providers.
                    consumer,provider=((ident,index),(source,ri))if kind==3 else((source,ri),(ident,index))
                    data_sources.setdefault(consumer,set()).add(provider)
                    presence=exists(g['nodes'][source],rk,ri,m['definitions'])
                    if presence is False:issues.append({'graph':g['id'],'node':ident,'error':'data edge port absent','target':source,'port':[rk,ri]})
                    elif presence is None:unknown.append({'graph':g['id'],'node':ident,'error':'data edge contract unresolved','target':source,'port':[rk,ri]})
                    a=type_at(g,g['nodes'][source],rk,ri,m['definitions']);b=type_at(g,n,kind,index,m['definitions'])
                    if a is None or b is None:unknown.append({'graph':g['id'],'node':ident,'input':index,'source':source,'output':ri,'source_node_type':ref(get(g['nodes'][source],2,default=b'')),'target_node_type':ref(get(n,2,default=b'')),'types':[a,b],'source_descriptor':g['nodes'][source].hex()[:1000]})
                    elif a!=b:issues.append({'graph':g['id'],'node':ident,'input':index,'source':source,'error':'connected type mismatch','types':[a,b]})
                    # Struct-bearing values must carry the same calibrated type identity.
                    if a in ((22,23) if client_node(n) else (25,26)) and b==a:
                        sa=structure_id(g['nodes'][source],rk,ri,m['definitions']);sb=structure_id(n,kind,index,m['definitions'])
                        if sa is None or sb is None:unknown.append({'graph':g['id'],'node':ident,'error':'struct identity unresolved'})
                        elif sa!=sb:issues.append({'graph':g['id'],'node':ident,'error':'struct identity mismatch','structures':[sa,sb]})
                        elif sa not in sids:issues.append({'graph':g['id'],'node':ident,'error':'referenced structure declaration absent','struct_id':sa})
        for (consumer,index),providers in data_sources.items():
            if len(providers)>1:
                issues.append({'graph':g['id'],'node':consumer,'port':[3,index],
                               'error':'multiple data input providers','providers':[list(p)for p in sorted(providers)]})
    gids={g['id'] for g in m['graphs']}
    for mount in m['mounts']:
        if mount['graph_id'] not in gids:issues.append({**mount,'error':'mounted graph absent'})
        elif mount['graph_id']not in m['graph_library']:issues.append({**mount,'error':'mounted graph not registered in graph library'})
    issues.extend(conflicts.values())
    result={'schema':2,'sha256':sha(data),'status':'failed' if issues or strict and unknown else 'passed','edges':edges,'issues':issues,'unresolved':unknown,'layer':'static','host_tested':False}
    return result
def require_mounts(m,contracts):
    """Check a unique graph and entity selector, including its native section."""
    for contract in contracts:
        if set(contract)-{'graph_name','entity_id','section'}or not {'graph_name','entity_id'}<=set(contract):
            raise ValueError('Invalid required mount contract')
        section=contract.get('section')
        if section is not None and (type(section)!=int or section not in(4,5)):
            raise ValueError('Required mount section must be template=4 or instance=5')
        graphs=[g for g in m['graphs']if g['name']==contract['graph_name']]
        entities=[e for e in m['entities']if e['entity_id']==contract['entity_id']and(section is None or e['section']==section)]
        if len(graphs)!=1 or len(entities)!=1:raise ValueError('Required mount selector missing or ambiguous')
        target=entities[0]
        mounts=[p for p in m['mounts']if p['graph_id']==graphs[0]['id']and p['entity_id']==target['entity_id']and p['section']==target['section']]
        if len(mounts)!=1:raise ValueError('Required mount missing or duplicated')
    return len(contracts)


def optimize(graph,pure_ids,fanout_cap):
    if type(fanout_cap)!=int or fanout_cap<1:raise ValueError('Positive fanout cap required')
    catalog,_=node_catalog()
    permitted_names={'Get_Custom_Variable','Get_List_Length','Get_Corresponding_Value_From_List'}
    permitted={i for i,e in catalog.items() if e['Name'] in permitted_names}
    read_types=set(pure_ids)
    if read_types-permitted:raise ValueError('Read node type outside serialized rewrite experiment')
    nodes=vals(fields(graph),3);aliases={};fan=Counter(get(c,1,0) for n in nodes for p in vals(fields(n),4) for c in vals(fields(p),5));seen={}
    if any(fan[get(n,1,0)]>fanout_cap for n in nodes if ref(get(n,2,default=b''))in read_types):raise ValueError('Existing read-expression fanout exceeds budget')
    for n in nodes:
        nid=get(n,1,0);typ=ref(get(n,2,default=b''));pins=vals(fields(n),4)
        if typ not in read_types or any(slot(p)[0] not in (3,4) for p in pins):continue
        shape=b''.join(raw for a,w,v,raw in fields(n) if a not in (1,5,6))
        keep=next((x for x in seen.get(shape,[]) if fan[x]+fan[nid]<=fanout_cap),None)
        if keep is None:seen.setdefault(shape,[]).append(nid)
        else:aliases[nid]=keep;fan[keep]+=fan[nid]
    def redirect(n):return rewrite(n,4,lambda p:rewrite(p,5,lambda c:put(c,1,aliases.get(get(c,1,0),get(c,1,0)),0)))
    graph=b''.join(msg(a,redirect(v)) if a==3 and w==2 else raw for a,w,v,raw in fields(graph) if not(a==3 and w==2 and get(v,1,0) in aliases))
    return graph,aliases
def apply(data,spec,base,*,bindings=None):
    from authoring_io import DiagnosticError
    from project_index import build as project_index, write_audit_error
    from native_gameplay_index import build_gameplay, require_gameplay
    from native_bindings import Bindings, bind_operation, bindings_for_gil
    bindings = Bindings(bindings.ids if bindings is not None else {})
    schema(spec,('schema','base_sha256','allowed_top_level_fields','operations','strict_audit'),('base_sha256','allowed_top_level_fields','operations'))
    digest=sha(data)
    if digest!=spec['base_sha256']:
        raise DiagnosticError('native.base_sha256_mismatch','Base hash mismatch',phase='native_apply',
                              field='base_sha256',expected=spec['base_sha256'],actual=digest)
    from native_scene_edits import SCENE_EDITS, arrange_instances, place_static_scene
    from native_scene_settings import SETTINGS_EDITS
    from native_prefabs import OBJECT_CREATION,author_objects
    from native_gameplay import GAMEPLAY_EDITS
    from native_economy import ECONOMY_EDITS
    from native_hud import HUD_EDITS
    from native_variables import add_native_variables

    allowed=spec['allowed_top_level_fields'];_,before=calibrated_container(data);logs=[]
    input_data=data
    scene_ops={op['op'] for op in spec['operations']}
    gameplay_edits=GAMEPLAY_EDITS | ECONOMY_EDITS | HUD_EDITS | {'add_native_variables':add_native_variables}
    placement=bool(scene_ops & ({'arrange_instances','duplicate_entities','place_static_scene'}|OBJECT_CREATION))
    scoped_authoring={'set_entity_transform','add_scene_points','add_point_light','add_native_movers','set_native_preset_state','append_client_ui'}
    guarded=placement or bool(scene_ops & (scoped_authoring|gameplay_edits.keys()))
    if guarded:
        label=('Entity placement' if placement else 'Entity transform' if 'set_entity_transform' in scene_ops
               else 'Native gameplay' if scene_ops & gameplay_edits.keys() else 'Native scene')
        if spec.get('strict_audit',True) is not True:
            raise ValueError(label+' edits require strict audit')
        baseline=project_index(data,include_scene=False)
        require_gameplay(baseline,'baseline')
        if baseline['status']!='passed':
            raise write_audit_error(baseline, 'baseline', label+' baseline audit failed',
                                    code='native.baseline_audit_failed')
    elif spec.get('strict_audit',True):
        require_gameplay(build_gameplay(data),'baseline')
    authored_templates={}
    authored_entities={}
    layout_bindings=Bindings()
    for op in spec['operations']:
        kind=op['op'];op=bind_operation(op,bindings)
        scene_edit=SCENE_EDITS.get(kind) or SETTINGS_EDITS.get(kind)
        gameplay_edit=gameplay_edits.get(kind)
        if 'entity_key' in op and kind in ('add_box_trigger','add_native_movers','set_linear_motion','set_entity_transform','mount','native_economy_binding','native_combat'):
            op=dict(op);key=op.pop('entity_key')
            ids=authored_entities.get(key,[]) if isinstance(key,str) else []
            if len(ids)!=1 or 'entity_id' in op or op.get('section',5)!=5:
                raise ValueError('Placed object key is missing or ambiguous: '+repr(key))
            op['entity_id']=ids[0]
            if kind in ('native_economy_binding','native_combat'):op['section']=5
        if gameplay_edit is not None:
            if kind=='native_economy_binding' and 'drop_template_key'in op:
                op=dict(op);key=op.pop('drop_template_key')
                ids=authored_templates.get(key,[]) if isinstance(key,str) else []
                if len(ids)!=1 or 'drop_template_id'in op:
                    raise ValueError('Pickup template key is missing or ambiguous: '+repr(key))
                op['drop_template_id']=ids[0]
            data,detail=(gameplay_edit(data,op,bindings=bindings) if kind=='economy_config' else gameplay_edit(data,op))
            if kind=='create_native_drop' and 'key'in detail:
                authored_templates.setdefault(detail['key'],[]).append(detail['drop_template_id'])
                bindings.add('pickup_template',detail['key'],detail['drop_template_id'])
            if kind=='native_hud':
                for row in detail['controls']:
                    if 'key' in row:bindings.add('control',row['key'],row['control_id'])
                group=detail.get('group',{})
                if 'key' in group:bindings.add('control_group',group['key'],group['group_id'])
            if kind=='native_skill' and 'key' in detail:
                bindings.add('creature_skill' if 'creature_skill_witness' in op else 'skill',detail['key'],detail['skill_id'])
            logs.append({'op':kind,**detail})
            continue
        if kind in OBJECT_CREATION:
            if kind=='instantiate_object_templates':
                instances=[]
                for row in op.get('instances',[]):
                    if 'template_key' not in row:
                        instances.append(row);continue
                    item=dict(row);key=item.pop('template_key');ids=authored_templates.get(key,[]) if isinstance(key,str) else []
                    if len(ids)!=1 or 'template_id' in item:
                        raise ValueError('Object template key is missing or ambiguous: '+repr(key))
                    instances.append({**item,'template_id':ids[0]})
                op={**op,'instances':instances}
            data,detail=author_objects(data,op,base)
            for row in detail.get('templates',[]):
                authored_templates.setdefault(row['key'],[]).append(row['template_id'])
                bindings.add('template',row['key'],row['template_id'])
            for row in detail.get('instances',[]):
                authored_entities.setdefault(row['key'],[]).append(row['entity_id'])
                bindings.add('entity',row['key'],row['entity_id'])
            logs.append({'op':kind,**detail})
            continue
        if scene_edit is not None or kind in ('place_static_scene','arrange_instances'):
            if kind=='arrange_instances':
                data,detail=arrange_instances(data,op,base,baseline=input_data)
            elif kind=='place_static_scene':
                data,detail=place_static_scene(data,op,base)
            else:
                data,detail=scene_edit(data,op)
            if kind in ('duplicate_entities','arrange_instances'):
                for row in detail['copies' if kind=='duplicate_entities' else 'instances']:
                    authored_entities.setdefault(row['key'],[]).append(row['entity_id'])
                    bindings.add('entity',row['key'],row['entity_id'])
                    if kind=='arrange_instances':layout_bindings.add('entity',row['key'],row['entity_id'])
            logs.append({'op':kind,**detail})
            continue
        if kind=='append_client_ui':
            from native_client_ui import append_client_ui
            data,detail=append_client_ui(data,op,base)
            logs.append({'op':kind,**detail})
            continue
        m=model(data)
        if kind=='set_custom_variable_default':
            from native_variables import set_default
            data,detail=set_default(data,m,op)
            logs.append({'op':kind,**detail})
            continue
        if kind=='set_timer_sequence':
            from platform_native import set_sequence
            schema(op,('op','source','timer_id'),('op','source','timer_id'))
            data,detail=set_sequence(data,m,read_json(resolve(base,op['source'])),op['timer_id'])
            logs.append({'op':kind,**detail})
            continue
        if kind in ('replace_graph','append_graph','rewire','optimize','remap_nodes'):
            graph_kind=op.get('graph_kind','ordinary')
            if graph_kind not in('ordinary','composite'):raise ValueError('Unknown graph kind')
            pool=m['graphs']if graph_kind=='ordinary'else m['composite_graphs']
            section_key=1 if graph_kind=='ordinary'else 4
            matches=[g for g in pool if g['id']==op.get('graph_id')]
            if kind!='append_graph' and len(matches)!=1:raise ValueError('Graph selector must match exactly once')
            if kind in ('replace_graph','append_graph'):
                source=resolve(base,op['source']);raw=source.read_bytes()
                calibrated_container(raw,allow_gia=True)
                blobs=[b for k,b in graph_records(raw)if k==graph_kind]
                candidates=[b for b in blobs if op.get('source_graph_id') is None or ref(get(b,1,default=b''))==op['source_graph_id']]
                if len(candidates)!=1:raise ValueError('Source graph selector must match exactly once')
                graph=candidates[0]
                if kind=='replace_graph':
                    graph=put(graph,1,get(matches[0]['raw'],1));name=get(matches[0]['raw'],2)
                    graph=put(graph,2,name)if name is not None else b''.join(r for n,w,v,r in fields(graph)if n!=2)
                elif any(g['id']==ref(get(graph,1)) for g in pool):raise ValueError('Graph ID collision')
            else:
                graph=matches[0]['raw']
                if kind=='remap_nodes':
                    schema(op,('op','graph_kind','graph_id','mapping'),('op','graph_id','mapping'))
                    from native_ids import remap_nodes
                    graph=remap_nodes(graph,op['mapping'])
                elif kind=='rewire':
                    target=op['node'];pins=op['input'];found=[]
                    def node_patch(n):
                        if get(n,1,0)!=target:return n
                        def pin_patch(p):
                            if list(slot(p))!=pins:return p
                            found.append(1)
                            current=vals(fields(p),5)
                            if len(current)==1 and get(current[0],1,0)==op['source_node']and get(get(current[0],2,default=b''),2,0,0)==op.get('source_port',0):return p
                            return b''.join(r for a,w,v,r in fields(p) if a!=5)+msg(5,integer(1,op['source_node'])+msg(2,integer(1,4)+integer(2,op.get('source_port',0)))+msg(3,integer(1,4)+integer(2,op.get('source_port',0))))
                        return rewrite(n,4,pin_patch)
                    graph=rewrite(graph,3,node_patch)
                    if len(found)!=1:raise ValueError('Pin selector must match exactly once')
                else:
                    # Pure declarations are caller supplied and hash-bound to this exact base.
                    graph,aliases=optimize(graph,set(op['pure_node_types']),op['fanout_cap'])
                    logs.append({'aliases':aliases,'scope':'serialized_graph_rewrite','editor':'not_checked','host':'not_checked'})
                    if graph_kind=='composite':graph=rewrite(graph,4,lambda p:put(p,2,aliases.get(get(p,2,0),get(p,2,0)),0))
            section=get(data[20:-4],10,default=b'')
            if kind=='append_graph':section+=msg(section_key,msg(1,graph))
            elif kind=='remap_nodes':
                section=b''.join(msg(a,put(v,1,graph))if a==section_key and w==2 and get(v,1)==matches[0]['raw']and graph!=matches[0]['raw']else raw for a,w,v,raw in fields(section))
            else:section=rewrite(section,section_key,lambda w:put(w,1,graph) if get(w,1)==matches[0]['raw'] else w)
            data=set_section(data,10,section)
        elif kind=='mount':
            section_id=op.get('section',5)
            if section_id not in (4,5):raise ValueError('Mount section must be template=4 or instance=5')
            if op['graph_id'] not in {g['id'] for g in m['graphs']}:raise ValueError('Graph to mount absent')
            section=get(data[20:-4],section_id,default=b'');found=[]
            def entity_patch(e):
                if get(e,1,0)!=op['entity_id']:return e
                found.append(1);component_field=graph_component_field(e,section_id)
                components=vals(fields(e),component_field);slots=[c for c in components if get(c,1,0)==3]
                if len(slots)!=1:raise ValueError('Calibrated graph component required')
                c=slots[0];group=get(c,13,default=b'');entry=msg(1,integer(1,1)+integer(2,op['graph_id'])+integer(3,op.get('category',20000)))
                refs=[get(get(r,1,default=b''),2,0) for r in vals(fields(group),1)]
                if op['graph_id'] not in refs:c=put(c,13,group+msg(1,entry))
                return b''.join(msg(component_field,c) if a==component_field and v==slots[0] else raw for a,w,v,raw in fields(e))
            section=rewrite(section,1,entity_patch)
            if len(found)!=1:raise ValueError('Entity selector must match exactly once')
            data=set_section(data,section_id,section)
            if op['graph_id'] in m['graph_library']:
                logs.append({'op':kind})
                continue
            library=get(data[20:-4],6,default=b'');registered=[]
            def library_patch(e):
                if get(e,1,0)!=4:return e
                groups=vals(fields(e),3)
                if len(groups)!=1:raise ValueError('Explicit calibrated graph library group required')
                registered.append(1);group=groups[0]
                if op['graph_id']not in[get(r,2,0)for r in vals(fields(group),5)]:group+=msg(5,integer(1,800)+integer(2,op['graph_id']))
                return put(e,3,group)
            library=rewrite(library,1,library_patch)
            if len(registered)!=1:raise ValueError('Graph library entry missing')
            data=set_section(data,6,library)
        elif kind=='section_from':
            _,source_root=calibrated_container(resolve(base,op['source']).read_bytes())
            value=unique(source_root,op['field'])
            if value is None:raise ValueError('Source section absent')
            data=set_section(data,op['field'],value)
        else:raise ValueError('Unsupported native operation '+str(kind))
        logs.append({'op':kind})
    after=container(data)[1]
    if [r for n,w,v,r in before if n not in allowed]!=[r for n,w,v,r in after if n not in allowed]:
        raise DiagnosticError('native.protected_bytes_changed', 'Protected bytes changed', phase='result',
                              allowed_top_level_fields=allowed)
    report=audit(data,spec.get('strict_audit',True))
    if report['status']!='passed':
        failures=report['issues']+report['unresolved']
        raise write_audit_error(report, 'result', f'Final audit failed ({len(failures)} findings)',
                                code='native.result_audit_failed')
    if guarded:
        final=project_index(data,include_scene=False,validation=report)
        require_gameplay(final,'result')
        if final['status']!='passed':
            raise write_audit_error(final, 'result', 'Final project references failed',
                                    code='native.result_reference_failed')
    elif allowed and set(allowed) & {4,5,9,10,12,15} and spec.get('strict_audit',True):
        require_gameplay(build_gameplay(data),'result')
    result={'schema':2,'operations':logs,'audit':report,'protected_fields_unchanged':True,'sha256':sha(data)}
    if bindings.ids:result['bindings']=bindings.payload()
    if layout_bindings.ids:
        if len(set(layout_bindings.ids.values()))!=len(layout_bindings.ids):
            raise ValueError('Arrangement keys must identify distinct placed instances')
        result['layout_bindings']=bindings_for_gil(data,layout_bindings)
    return data,result
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='op',required=True)
    for name in ('inspect','audit'):
        a=s.add_parser(name);a.add_argument('input');a.add_argument('--out')
    a=s.add_parser('diff');a.add_argument('input');a.add_argument('other');a.add_argument('--allow-fields',nargs='*',type=int);a.add_argument('--out')
    a=s.add_parser('plan');a.add_argument('input');a.add_argument('--spec',required=True);a.add_argument('--out',required=True);a.add_argument('--summary',action='store_true')
    a=s.add_parser('apply');a.add_argument('input');choice=a.add_mutually_exclusive_group(required=True);choice.add_argument('--spec');choice.add_argument('--plan');a.add_argument('--out',required=True)
    a=p.parse_args(argv);data=Path(a.input).read_bytes()
    if a.op=='apply':
        if Path(a.out).exists():raise ValueError('Output exists')
        if a.plan:
            from native_changes import apply_plan
            output,report=apply_plan(data,read_json(a.plan),Path(a.plan).resolve().parent)
        else:output,report=apply(data,read_json(a.spec),Path(a.spec).resolve().parent)
        with Path(a.out).open('xb') as f:f.write(output)
    elif a.op in('diff','plan'):
        from native_changes import difference,plan
        if a.out and Path(a.out).exists():raise ValueError('Output exists')
        report=difference(data,Path(a.other).read_bytes(),a.allow_fields)if a.op=='diff'else plan(data,read_json(a.spec),Path(a.spec).resolve().parent,Path(a.out).resolve().parent)
        if a.out:
            with Path(a.out).open('x',encoding='utf-8')as f:json.dump(report,f,ensure_ascii=False,indent=2)
    else:
        report=inspect(data) if a.op=='inspect' else audit(data)
        if a.out:
            with Path(a.out).open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    if a.op=='plan' and a.summary:
        from native_changes import plan_summary
        report=plan_summary(report,Path(a.out).resolve())
    print(json.dumps(report,ensure_ascii=False));return 0 if report.get('status')!='failed' else 2
