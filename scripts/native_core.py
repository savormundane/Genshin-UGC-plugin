"""Raw-preserving native graph model, final-edge audit and explicit schema-2 patches."""
from pathlib import Path
from collections import Counter
import argparse,json
from functools import lru_cache
from level_inventory import fields,vals,unique,container,graph_summary,graph_records
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
    ids=set()
    d=definitions.get(definition_id(n,definitions))
    if d:
        ports=[p for p in vals(fields(d),102 if kind==3 else 103)if get(p,3)is not None and get(get(p,3),2,0,0)==index]
        if len(ports)==1:
            ids.update(descriptor_structure_ids(get(ports[0],4,default=b'')))
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
def graph_blobs(data):
    return [raw for kind,raw in graph_records(data)if kind=='ordinary']
def model(data):
    header,root=container(data);definitions={};graphs=[];composites=[];mounts=[];structs=[];signals=[];libraries=[];entities=[];resources=[]
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
                entities.append({'section':section_id,'entity_id':get(entity,1,0)})
                for c in vals(fields(entity),6):
                    if get(c,1,0)!=3:continue
                    for group in vals(fields(c),13):
                        for entry in vals(fields(group),1):
                            r=get(entry,1,default=b'');mounts.append({'section':section_id,'entity_id':get(entity,1,0),'graph_id':get(r,2,0)})
    ids=[g['id'] for g in graphs]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate graph ID')
    ids=[g['id']for g in composites]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate composite graph ID')
    for section in vals(root,6):
        for entry in vals(fields(section),1):
            if get(entry,1,0)==4:
                for group in vals(fields(entry),3):libraries.extend(get(r,2,0)for r in vals(fields(group),5))
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
def port_type(n,kind,index,definitions):
    pins=[p for p in vals(fields(n),4) if slot(p)==(kind,index)]
    explicit=get(pins[0],4,0) if pins else None
    d=definitions.get(definition_id(n,definitions))
    if d:
        dp=[p for p in vals(fields(d),102 if kind==3 else 103) if get(p,3)is not None and get(get(p,3),2,0,0)==index]
        declared=get(get(dp[0],4,default=b''),3,0) if len(dp)==1 else None
        if declared is not None and explicit is not None and explicit!=declared:raise ValueError('Instance/declaration type mismatch: '+str({'node':get(n,1,0),'kind':kind,'port':index,'definition':definition_id(n,definitions),'actual':explicit,'declared':declared}))
        return declared if declared is not None else explicit
    nodes,types=node_catalog();entry=nodes.get(ref(get(n,2,default=b'')))
    if entry:
        if entry['ID']==337 and kind==3 and index==0:
            if explicit is not None and explicit!=6:raise ValueError('Graph variable name input must be string')
            return 6
        if entry['ID']==128 and kind==3 and index==1:
            if explicit is not None and explicit!=3:raise ValueError('List index input must be integer')
            return 3
        ports=entry['Inputs' if kind==3 else 'Outputs']
        if index<len(ports):
            token=ports[index]
            if token in types:
                if explicit is not None and explicit!=types[token]:raise ValueError('Instance/catalogue type mismatch: '+str({'node':get(n,1,0),'generic':ref(get(n,2,default=b'')),'concrete':ref(get(n,3,default=b'')),'kind':kind,'port':index,'actual':explicit,'expected':types[token]}))
                return types[token]
            # Struct specialisations use usingStruct/value identity descriptors,
            # while the generic locator may retain the catalogue's default ID.
            if explicit in(25,26)and structure_id(n,kind,index,definitions)is not None:return explicit
            concrete=ref(get(n,3,default=b''))
            mapping=next((x for x in entry.get('TypeMappings',[]) if x['ConcreteId']==concrete),None)
            if mapping:
                rule=mapping['Type']
                if rule.startswith('S<T:')and rule.endswith('>'):rule=rule[4:-1]
                resolved=types.get(token.replace('R<T>',rule))
                if resolved is not None:
                    if explicit is not None and explicit!=resolved:raise ValueError('Instance/concrete type mismatch: '+str((get(n,1,0),kind,index,explicit,resolved)))
                    return resolved
    return explicit
def audit(data,strict=True):
    from native_ports import exists,declared_ports,resolve_dynamic,reference_error
    m=model(data);issues=[];unknown=[];edges=0;catalog=node_catalog()[0]
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
                if reference_problem:issues.append({'graph':g['id'],'node':ident,'error':reference_problem})
                resolved[ident],error=resolve_dynamic(n,m['definitions'],m['signals'],roles)
                if error:issues.append({'graph':g['id'],'node':ident,'error':error})
            resolved_graphs.append({**g,'nodes':resolved})
        m[group]=resolved_graphs
    from native_structures import audit_references
    structure_issues,structure_unknown=audit_references(m)
    issues.extend(structure_issues);unknown.extend(structure_unknown)
    from native_variables import audit as audit_variables
    variable_issues,variable_unknown=audit_variables(m)
    issues.extend(variable_issues);unknown.extend(variable_unknown)
    from native_graph_variables import audit as audit_graph_variables
    graph_variable_issues,graph_variable_unknown=audit_graph_variables(m)
    issues.extend(graph_variable_issues);unknown.extend(graph_variable_unknown)
    from native_resources import audit_resources
    resource_issues,resource_unknown=audit_resources(m)
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
            if definition is None and ref(get(n,2,default=b''))not in catalog:
                unknown.append({'graph':g['id'],'node':ident,'error':'unknown node definition','definition':definition_id(n,m['definitions'])})
            if definition:
                expected=get(get(definition,4,default=b''),5,0,0)
                actual=get(n,9,0,0)
                if expected!=actual:issues.append({'graph':g['id'],'node':ident,'error':'definition version mismatch','expected':expected,'actual':actual})
                for p in pins:
                    kind,index=slot(p)
                    declared=declared_ports(definition).get((kind,index))
                    if declared is None:issues.append({'graph':g['id'],'node':ident,'port':[kind,index],'error':'dynamic port absent or ambiguous'})
                    elif get(p,7,0)is not None and get(declared,8,0)is not None and get(p,7,0)!=get(declared,8,0):issues.append({'graph':g['id'],'node':ident,'port':[kind,index],'error':'dynamic port identity mismatch'})
            for p in pins:
                kind,index=slot(p)
                if definition is None:
                    presence=exists(n,kind,index,m['definitions'])
                    if presence is False:issues.append({'graph':g['id'],'node':ident,'port':[kind,index],'error':'instance port absent from contract'})
                    elif presence is None:unknown.append({'graph':g['id'],'node':ident,'port':[kind,index],'error':'port contract unresolved'})
                if kind in(3,4):port_type(n,kind,index,m['definitions'])
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
                    a=port_type(g['nodes'][source],rk,ri,m['definitions']);b=port_type(n,kind,index,m['definitions'])
                    if a is None or b is None:unknown.append({'graph':g['id'],'node':ident,'input':index,'source':source,'output':ri,'source_node_type':ref(get(g['nodes'][source],2,default=b'')),'target_node_type':ref(get(n,2,default=b'')),'types':[a,b],'source_descriptor':g['nodes'][source].hex()[:1000]})
                    elif a!=b:issues.append({'graph':g['id'],'node':ident,'input':index,'source':source,'error':'connected type mismatch','types':[a,b]})
                    # Struct-bearing values must carry the same calibrated type identity.
                    if a in (25,26) and b==a:
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
    pure_names={'Get_Custom_Variable','Get_List_Length','Get_Corresponding_Value_From_List'}
    permitted={i for i,e in catalog.items() if e['Name'] in pure_names}
    if set(pure_ids)-permitted:raise ValueError('Unproven pure node types')
    nodes=vals(fields(graph),3);aliases={};fan=Counter(get(c,1,0) for n in nodes for p in vals(fields(n),4) for c in vals(fields(p),5));seen={}
    if any(fan[get(n,1,0)]>fanout_cap for n in nodes if ref(get(n,2,default=b''))in pure_ids):raise ValueError('Existing read-expression fanout exceeds budget')
    for n in nodes:
        nid=get(n,1,0);typ=ref(get(n,2,default=b''));pins=vals(fields(n),4)
        if typ not in pure_ids or any(slot(p)[0] not in (3,4) for p in pins):continue
        shape=b''.join(raw for a,w,v,raw in fields(n) if a not in (1,5,6))
        keep=next((x for x in seen.get(shape,[]) if fan[x]+fan[nid]<=fanout_cap),None)
        if keep is None:seen.setdefault(shape,[]).append(nid)
        else:aliases[nid]=keep;fan[keep]+=fan[nid]
    def redirect(n):return rewrite(n,4,lambda p:rewrite(p,5,lambda c:put(c,1,aliases.get(get(c,1,0),get(c,1,0)),0)))
    graph=b''.join(msg(a,redirect(v)) if a==3 and w==2 else raw for a,w,v,raw in fields(graph) if not(a==3 and w==2 and get(v,1,0) in aliases))
    return graph,aliases
def apply(data,spec,base):
    schema(spec,('schema','base_sha256','allowed_top_level_fields','operations','strict_audit'),('base_sha256','allowed_top_level_fields','operations'))
    if sha(data)!=spec['base_sha256']:raise ValueError('Base hash mismatch')
    allowed=spec['allowed_top_level_fields'];before=container(data)[1];logs=[]
    for op in spec['operations']:
        m=model(data);kind=op['op']
        if kind=='set_entity_transform':
            from native_scene import set_entity_transform
            if 5 not in allowed:raise ValueError('Entity transform edits require allowed top-level field 5')
            data,detail=set_entity_transform(data,op)
            logs.append({'op':kind,**detail})
            continue
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
                source=resolve(base,op['source']);raw=source.read_bytes();blobs=[b for k,b in graph_records(raw)if k==graph_kind]
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
                    graph,aliases=optimize(graph,set(op['pure_node_types']),op['fanout_cap']);logs.append({'aliases':aliases})
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
                found.append(1);components=vals(fields(e),6);slots=[c for c in components if get(c,1,0)==3]
                if len(slots)!=1:raise ValueError('Calibrated graph component required')
                c=slots[0];group=get(c,13,default=b'');entry=msg(1,integer(1,1)+integer(2,op['graph_id'])+integer(3,op.get('category',20000)))
                refs=[get(get(r,1,default=b''),2,0) for r in vals(fields(group),1)]
                if op['graph_id'] not in refs:c=put(c,13,group+msg(1,entry))
                return b''.join(msg(6,c) if a==6 and v==slots[0] else raw for a,w,v,raw in fields(e))
            section=rewrite(section,1,entity_patch)
            if len(found)!=1:raise ValueError('Entity selector must match exactly once')
            data=set_section(data,section_id,section)
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
            raw=resolve(base,op['source']).read_bytes();value=get(raw[20:-4],op['field'])
            if value is None:raise ValueError('Source section absent')
            data=set_section(data,op['field'],value)
        else:raise ValueError('Unsupported native operation '+str(kind))
        logs.append({'op':kind})
    after=container(data)[1]
    if [r for n,w,v,r in before if n not in allowed]!=[r for n,w,v,r in after if n not in allowed]:raise ValueError('Protected bytes changed')
    report=audit(data,spec.get('strict_audit',True))
    if report['status']!='passed':raise ValueError('Final audit failed: '+json.dumps(report,ensure_ascii=False))
    return data,{'schema':2,'operations':logs,'audit':report,'protected_fields_unchanged':True,'sha256':sha(data)}
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='op',required=True)
    for name in ('inspect','audit'):
        a=s.add_parser(name);a.add_argument('input');a.add_argument('--out')
    a=s.add_parser('diff');a.add_argument('input');a.add_argument('other');a.add_argument('--allow-fields',nargs='*',type=int);a.add_argument('--out')
    a=s.add_parser('plan');a.add_argument('input');a.add_argument('--spec',required=True);a.add_argument('--out',required=True)
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
    print(json.dumps(report,ensure_ascii=False));return 0 if report.get('status')!='failed' else 2
