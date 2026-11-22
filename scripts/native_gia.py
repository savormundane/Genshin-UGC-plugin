"""Explicit server structure dependencies for newly compiled GIA graphs."""
from native_core import get,put,ref,model,bind_structures,descriptor_structure_ids,rewrite,slot,node_catalog
from level_inventory import fields,vals,container
from level_authoring import msg,integer,pack


def bind_skill_notifications(data, graph_names):
    """Lower the legacy compiler's Notify Server node to the editor Skill kernel."""
    header,rows=container(data)
    changes=[]
    def descriptor(typ):
        return msg(4,integer(1,2)+msg(101,integer(2,typ)))
    def graph(raw):
        name=get(raw,2,default=b'').decode('utf-8')
        if name not in graph_names or get(get(raw,1,default=b''),2,0)!=20002:
            return raw
        def node(n):
            generic=get(n,2,default=b'')
            if tuple(get(generic,i,0,0) for i in (1,2,3,4,5))!=(10001,20002,22000,0,200039):
                return n
            kernel=get(n,3,default=b'')
            if (get(kernel,1,0),get(kernel,2,0),get(kernel,3,0),get(kernel,4,0,0),ref(kernel))==(10001,20002,22000,0,2000):
                return n
            if (get(kernel,1,0),get(kernel,3,0),get(kernel,4,0,0),ref(kernel))!=(10001,22000,0,200039) or get(kernel,2,0) not in (20000,20002):
                raise ValueError('Generated Notify Server node has an unsupported locator')
            found=set()
            def pin(p):
                kind,index=slot(p)
                if kind!=3 or index not in (0,1,2):
                    return p
                if index in found or get(p,4,0)!=6:
                    raise ValueError('Generated Notify Server input has an unsupported type')
                found.add(index)
                value=get(p,3)
                if value is not None:
                    legacy=get(value,4,default=b'')
                    content=get(value,105,default=b'')
                    literal=get(content,1,default=b'')
                    if get(value,1,0)!=5 or get(legacy,1,0)!=1 or get(get(legacy,100,default=b''),1,0)!=6:
                        raise ValueError('Generated Notify Server input is outside the string literal contract')
                    # Client literals use ClientType.String=9. Preserve the
                    # UTF-8 bytes and encode the empty-string default natively.
                    value=integer(1,5)+(integer(2,1) if literal else b'')+descriptor(9)
                    value+=msg(105,msg(1,literal) if literal else b'')
                    p=put(p,3,value)
                return put(p,4,9,0)
            updated=rewrite(n,4,pin)
            if found!={0,1,2}:raise ValueError('Generated Notify Server node is missing string inputs')
            if not any(slot(p)==(5,0) for p in vals(fields(updated),4)):
                virtual=msg(1,integer(1,5))+msg(2,integer(1,5))
                virtual+=msg(3,integer(1,2)+descriptor(3)+msg(102))+integer(4,3)
                virtual+=msg(6,integer(1,5)+integer(2,1)+msg(100,integer(1,200039)))
                updated+=msg(4,virtual)
            changes.append({'graph':name,'node':get(n,1,0),'concrete':2000})
            return put(updated,3,put(put(kernel,2,20002,0),5,2000,0))
        return rewrite(raw,3,node)
    def unit(raw):
        return rewrite(raw,13,lambda wrapper:rewrite(wrapper,1,lambda inner:rewrite(inner,1,graph)))
    body=b''.join(r for _,_,_,r in rows)
    if header[3]==3:
        for key in (1,2):body=rewrite(body,key,unit)
    else:
        body=rewrite(body,10,lambda section:rewrite(section,1,lambda row:rewrite(row,1,graph)))
    return (pack(body,header[1:4]) if changes else data),changes


def bind_generated_variable_types(data):
    """Bind omitted Get_Custom_Variable specialisations in new compiler output."""
    if model(data)['format']!='gia':raise ValueError('Variable type binding requires generated GIA')
    catalogue,types=node_catalog();entry=catalogue[50];changes=[]
    def unit(raw):
        wrapper=get(raw,13)
        if wrapper is None:return raw
        inner=get(wrapper,1);graph=get(inner,1)
        def node(n):
            locator=get(n,2,default=b'')
            if ref(locator)!=50 or get(locator,2,0)!=20000:return n
            outputs=[p for p in vals(fields(n),4)if slot(p)==(4,0)]
            if len(outputs)!=1:raise ValueError('Generated variable getter needs one typed output')
            typ=get(outputs[0],4,0)
            # Structures and dictionaries need their identity/KV contracts;
            # this adapter only binds the catalogue's scalar/list variants.
            if typ in(25,26,27):return n
            candidates=[v['ConcreteId']for v in entry['TypeMappings']if types.get(v['Type'][4:-1])==typ]
            if len(candidates)!=1:raise ValueError('Variable getter output has no unique concrete type')
            concrete=ref(get(n,3,default=b''));target=candidates[0]
            if concrete==target:return n
            if concrete not in(None,50):raise ValueError('Generated variable getter concrete type conflicts with output')
            changes.append({'graph':get(graph,2,default=b'').decode('utf-8'),'node':get(n,1,0),'type':typ,'concrete':target})
            return put(n,3,put(get(n,3,default=get(n,2)),5,target,0))
        changed=rewrite(graph,3,node)
        return raw if changed==graph else put(raw,13,put(wrapper,1,put(inner,1,changed)))
    header,rows=container(data);body=b''.join(r for _,_,_,r in rows)
    for key in(1,2):body=rewrite(body,key,unit)
    return (pack(body,header[1:4])if changes else data),changes


def bind_generated_structures(data,baseline,bindings):
    current=model(data);source=model(baseline)
    selected=[b for b in bindings if any(g['name']==b['graph_name']for g in current['graphs'])]
    if not selected:return data,[]
    if current['format']!='gia' or source['format']!='gil':raise ValueError('Structure binding requires GIA and GIL baseline')
    if any(get(get(g['raw'],1,default=b''),2,0)!=20000 for g in current['graphs']if any(b['graph_name']==g['name']for b in selected)):
        raise ValueError('Generated GIA structure binding supports calibrated server graphs only')
    structures={get(get(s,1,default=b''),1,0):s for s in source['structs']}
    pending=[b['struct_id']for b in selected];needed=set();helpers={}
    while pending:
        sid=pending.pop(0)
        if sid in needed:continue
        if sid not in structures:raise ValueError('GIA structure dependency absent: '+str(sid))
        needed.add(sid)
        for key in(1,2):
            for member in vals(fields(get(structures[sid],key,default=b'')),3):
                desc=get(member,1,default=b'');kind=get(desc,1,0);sub=get(desc,2,default=b'')
                target=get(sub,2,0)if kind in(25,26)else(get(sub,504,0)if kind==27 and get(sub,503,0)in(25,26)else None)
                if target is not None:pending.append(target)
        for ident,d in source['definitions'].items():
            behavior=get(d,107,default=b'');kind=get(behavior,1,0)
            if kind not in(1003,1004,1005):continue
            if get(get(get(d,4,default=b''),1,default=b''),2,0)!=20000:continue
            if get(get(behavior,kind-899,default=b''),1,0)!=sid:continue
            helpers[ident]=d
            for key in(102,103):
                for p in vals(fields(d),key):pending.extend(descriptor_structure_ids(get(p,4,default=b'')))
    existing_structs={get(get(s,1,default=b''),1,0):s for s in current['structs']}
    if any(sid in existing_structs and existing_structs[sid]!=structures[sid]for sid in needed):
        raise ValueError('GIA structure dependency conflicts with baseline')
    used=set(current['definitions']);next_id=max([2**30,*used,*helpers])+1;added=[];mapping={}
    for ident,d in sorted(helpers.items()):
        if ident in used:
            mapped=next_id;next_id+=1
        else:mapped=ident
        if not 2**30<=mapped<2**31:raise ValueError('GIA structure declaration ID capacity exceeded')
        used.add(mapped);mapping[ident]=mapped
        signature=get(d,4)
        for key in(1,2):signature=put(signature,key,put(get(signature,key),5,mapped,0))
        d=put(d,4,signature)
        dependencies=set()
        for key in(102,103):
            for p in vals(fields(d),key):dependencies.update(descriptor_structure_ids(get(p,4,default=b'')))
        unit=msg(1,integer(2,23)+integer(4,mapped))
        unit+=b''.join(msg(2,integer(2,1)+integer(3,15)+integer(4,sid))for sid in sorted(dependencies))
        unit+=msg(3,get(d,200,default=b''))+integer(5,12)+msg(14,msg(1,msg(1,d)))
        added.append(unit)
    for sid in sorted(needed-existing_structs.keys()):
        unit=msg(1,integer(2,1)+integer(3,15)+integer(4,sid))+integer(5,29)+msg(22,msg(1,structures[sid]))
        added.append(unit)
    header,rows=container(data);body=b''.join(r for _,_,_,r in rows)
    related=[get(u,1)for u in added]
    def graph_unit(u):
        wrapper=get(u,13)
        if wrapper is None:return u
        graph=get(get(wrapper,1,default=b''),1,default=b'')
        if get(graph,2,default=b'').decode('utf-8')not in{b['graph_name']for b in selected}:return u
        return u+b''.join(msg(2,r)for r in related)
    for key in(1,2):body=rewrite(body,key,graph_unit)
    body+=b''.join(msg(2,u)for u in added)
    bound=bind_structures(pack(body,header[1:4]),selected)
    return bound,[{'graphs':[b['graph_name']for b in selected],'structures':sorted(needed),'definitions':mapping}]
