"""Calibrated fourth native signal role and trusted event-source reply targeting."""
from native_core import *
from level_authoring import text

def bind_replies(data,names,targets=None):
    targets=targets or{}
    m=model(data);section=get(data[20:-4],10,default=b'');defs=m['definitions'];next_id=max([1610612739,*defs])+1
    uids=[get(p,8,0,0)for d in defs.values()for k in(100,101,102,103,106)for p in vals(fields(d),k)];uid=max([0,*uids])+1
    additions=[];replacements={};registries={};rewrites={};reports=[]
    for s in m['signals']:
        name=get(s,3,default=b'').decode('utf-8')
        if name not in names:continue
        if get(s,9):raise ValueError('Reply already has a client role')
        old_id=ref(get(s,1));old=defs[old_id];new_id=next_id;next_id+=1;new_ref=put(get(s,1),5,new_id,0)
        metadata=msg(1,new_ref)+msg(2,new_ref)+msg(4)+integer(5,get(s,6,0,2));d=msg(4,metadata)
        pin_map={}
        for kind,key in((1,100),(2,101),(5,106)):
            ps=vals(fields(old),key)
            if len(ps)!=1:raise ValueError('Signal execution/name calibration missing')
            p=put(ps[0],8,uid,0);uid+=1;pin_map[(kind,0)]=get(p,8,0);d+=msg(key,p)
        target_uid=uid;uid+=1
        d+=msg(102,text(1,'目标玩家')+integer(2,1)+msg(3,integer(1,3))+msg(4,integer(3,1)+integer(4,1))+integer(8,target_uid))
        params=vals(fields(s),4);new_params=[]
        for i,param in enumerate(params):
            pname=get(param,1);ports=[p for p in vals(fields(old),102)if get(p,1)==pname]
            if len(ports)!=1:raise ValueError('Signal parameter declaration missing')
            p=put(put(ports[0],3,integer(1,3)+integer(2,i+1)),8,uid,0);new_params.append(put(param,7,uid,0));pin_map[(3,i)]=uid;uid+=1;d+=msg(102,p)
        info=text(1,name)+msg(2,get(s,1))+msg(3,get(s,7))+msg(4,get(s,2))
        d+=msg(107,integer(1,1006)+msg(108,info))+text(200,'发送客户端脚本信号')+integer(203,1)+integer(204,8)
        additions.append(msg(2,msg(1,d)))
        updated=b''.join(r for n,w,v,r in fields(s)if n!=4)+b''.join(msg(4,p)for p in new_params)+msg(9,new_ref);registries[s]=updated
        for g in m['graphs']:
            events=[i for i,n in g['nodes'].items()if any(ref(get(signal,2,default=b''))==definition_id(n,defs)for signal in m['signals'])]
            reachable={}
            for event in events:
                pending=[event];seen=set()
                while pending:
                    i=pending.pop()
                    if i in seen:continue
                    seen.add(i);reachable.setdefault(i,set()).add(event)
                    for p in vals(fields(g['nodes'][i]),4):
                        if slot(p)[0]==2:pending.extend(get(c,1,0)for c in vals(fields(p),5))
            for ident,n in g['nodes'].items():
                if definition_id(n,defs)!=old_id:continue
                target_policy=targets.get(name,'signal_source');target_source=None
                if target_policy.startswith('field:'):
                    field=target_policy[6:];position=next(i for i,p in enumerate(params)if get(p,1).decode('utf-8')==field)
                    target_source=next(p for p in vals(fields(n),4)if slot(p)==(3,position))
                else:
                    owners=reachable.get(ident,set())
                    if len(owners)!=1:raise ValueError('Client reply needs one reachable trusted signal source')
                    event=next(iter(owners))
                new=put(put(n,2,new_ref),3,new_ref)
                def pin_patch(p):
                    kind,index=slot(p)
                    if(kind,index)not in pin_map:return p
                    p=put(p,7,pin_map[(kind,index)],0)
                    if kind==3:
                        for k in(1,2):p=put(p,k,integer(1,3)+integer(2,index+1))
                    return p
                new=rewrite(new,4,pin_patch)
                target=msg(1,integer(1,3))+msg(2,integer(1,3))+integer(4,1)+integer(7,target_uid)
                if target_source is not None:target+=b''.join(raw for k,w,v,raw in fields(target_source)if k in(3,5))
                else:target+=msg(5,integer(1,event)+msg(2,integer(1,4)+integer(2,2))+msg(3,integer(1,4)+integer(2,2)))
                new+=msg(4,target);rewrites[(g['id'],ident)]=new
        reports.append({'name':name,'definition_id':new_id,'target':'trusted signal source','parameter_count':len(params)})
    if set(names)!={r['name']for r in reports}:raise ValueError('Requested reply signal absent')
    def graph_patch(w):
        raw=get(w,1)
        if not raw:return w
        gid=ref(get(raw,1));return put(w,1,rewrite(raw,3,lambda n:rewrites.get((gid,get(n,1,0)),n)))
    section=rewrite(section,1,graph_patch)
    section=rewrite(section,5,lambda r:rewrite(r,3,lambda s:registries.get(s,s)))+b''.join(additions)
    from native_core import register_definitions
    return register_definitions(set_section(data,10,section)),reports
