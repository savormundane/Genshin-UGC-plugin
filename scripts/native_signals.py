"""Signal GIA declarations: native peer links, roles and parameter dialects.

GIA has no GIL section10/5 registry. Read its own declaration metadata instead;
never manufacture a registry or infer a role from the localized node title.
"""
from collections import Counter
from native_core import get,ref
from native_ports import declared_ports
from level_inventory import fields,vals


def bind_generated_versions(data):
    """Fill omitted signal versions in a newly exported GIA, never repair conflicts."""
    from native_core import model,definition_id,put,rewrite
    from native_ports import resolve_dynamic
    from level_inventory import container
    from level_authoring import pack
    m=model(data)
    if m['format']!='gia':raise ValueError('Signal version binding requires generated GIA')
    records=declarations(m);roles={i:(r['name'],r['role'])for i,r in records.items()};changes=[]
    def unit(raw):
        wrapper=get(raw,13)
        if wrapper is None:return raw
        inner=get(wrapper,1,default=b'');graph=get(inner,1)
        if graph is None:raise ValueError('Generated GIA graph wrapper absent')
        def node(raw):
            resolved,error=resolve_dynamic(raw,m['definitions'],[],roles)
            if error:raise ValueError('Generated GIA signal binding failed: '+error)
            ident=definition_id(resolved,m['definitions'])
            if ident not in records:return raw
            version=get(get(m['definitions'][ident],4,default=b''),5,0,0)
            current=get(raw,9,0)
            if current is not None and current!=version:
                raise ValueError('Generated GIA signal version conflict')
            if current is None and version:
                changes.append({'graph':ref(get(graph,1,default=b'')),'node':get(raw,1,0),
                                'definition':ident,'version':version})
                return put(raw,9,version,0)
            return raw
        changed=rewrite(graph,3,node)
        return raw if changed==graph else put(raw,13,put(wrapper,1,put(inner,1,changed)))
    header,rows=container(data);body=b''.join(r for _,_,_,r in rows)
    for key in(1,2):body=rewrite(body,key,unit)
    return (pack(body,header[1:4])if changes else data),changes


def declarations(model):
    result={}
    for ident,d in model['definitions'].items():
        behavior=get(d,107,default=b'');kind=get(behavior,1,0)
        if kind not in(1001,1002)and not any(get(behavior,k)for k in(101,102)):continue
        shell=get(get(d,4,default=b''),1,default=b'')
        role={(20000,1001):1,(20000,1002):2,(20002,1001):7}.get((get(shell,2,0),kind))
        info=get(behavior,102 if kind==1002 else 101,default=b'')
        result[ident]={'definition':ident,'role':role,'name':get(info,1,default=b'').decode('utf-8'),
                       'peers':{k:get(info,k,default=b'')for k in(2,3)}}
    return result


def descriptor_problem(raw,typ,client=False):
    """Validate calibrated scalar/list descriptors, not arbitrary type numbers.

    Mapping is specific to signal_writeback/gia_export.py, whose GUID encoding
    differs from helpers.py's GIL writer. Only the 18 public signal types are
    admitted; this does not certify their behavior in the host.
    """
    scalar={1:1,2:2,3:3,4:5,5:7,6:9,12:12,20:20,21:21}
    lists={7:2,8:3,9:4,10:5,11:6,13:1,15:12,22:20,23:21}
    if typ not in scalar and typ not in lists:return 'unresolved'
    mapped=scalar[typ]if typ in scalar else scalar[lists[typ]]+1
    expected=mapped if client else typ
    if get(raw,3,0)!=expected or get(raw,4,0)!=expected:return 'type mismatch'
    if typ in lists:
        if get(raw,1,0)!=10002:return 'list descriptor mismatch'
        child=get(get(raw,102,default=b''),1)
        if child is None:return 'list element absent'
        return descriptor_problem(child,lists[typ],client)
    if get(raw,102)is not None:return 'unexpected list descriptor'
    if get(raw,1,0,0)!={1:0,2:1,3:2,4:6,5:4,6:5,12:7,20:1,21:1}[typ]:return 'scalar descriptor mismatch'
    if typ==4 and get(get(raw,101,default=b''),1,0)!=(200001 if client else 1):return 'boolean descriptor mismatch'
    return None


def audit_gia_signals(model):
    from native_resources import locator_key
    issues=[];unknown=[];records=declarations(model)
    if model['format']!='gia':return issues,unknown,records
    definitions=model['definitions'];groups={}
    resources={r['id']:r for r in model['resources']if r['class']==23}
    for ident,item in records.items():
        where={'definition':ident,'signal':item['name']};role=item['role']
        if role is None:issues.append({**where,'error':'GIA signal role unrecognized'});continue
        shell=get(get(definitions[ident],4,default=b''),1,default=b'')
        if locator_key(shell)!=(10001,20002 if role==7 else 20000,22001,0,ident):
            issues.append({**where,'error':'GIA signal declaration locator mismatch'})
        if not item['name']:issues.append({**where,'error':'GIA signal name absent'})
        groups.setdefault(item['name'],{}).setdefault(role,[]).append(ident)
        expected_roles={1:(2,7),2:(1,7),7:(2,1)}[role]
        dependencies={tuple(x)for x in resources[ident]['references']}
        for field,expected in zip((2,3),expected_roles):
            locator=item['peers'][field];target=ref(locator);peer=records.get(target)
            context={**where,'field':field,'target':target}
            if peer is None:issues.append({**context,'error':'GIA signal peer absent'});continue
            if peer['role']!=expected or peer['name']!=item['name']:
                issues.append({**context,'error':'GIA signal peer role or name mismatch'})
            shell=get(get(definitions[target],4,default=b''),1,default=b'')
            if locator_key(locator)!=locator_key(shell):issues.append({**context,'error':'GIA signal peer locator mismatch'})
            if (23,target)not in dependencies:issues.append({**context,'error':'GIA signal peer dependency absent'})
    for name,group in groups.items():
        where={'signal':name}
        if set(group)!={1,2,7}or any(len(ids)!=1 for ids in group.values()):
            issues.append({**where,'error':'GIA signal requires unique send/listen/client roles'});continue
        ids={role:items[0]for role,items in group.items()}
        ports={role:declared_ports(definitions[ident])for role,ident in ids.items()}
        versions={get(get(definitions[i],4,default=b''),5,0,0)for i in ids.values()}
        if len(versions)!=1:issues.append({**where,'error':'GIA signal role version mismatch'})
        for role,ps in ports.items():
            flows={k for k in ps if k[0]in(1,2)}
            if flows!=({(2,0)}if role==2 else{(1,0),(2,0)}):
                issues.append({**where,'definition':ids[role],'error':'GIA signal flow interface mismatch'})
            if any(k[0]==(3 if role==2 else 4)for k in ps):
                issues.append({**where,'definition':ids[role],'error':'GIA signal data direction mismatch'})
            if {k for k in ps if k[0]==5}!=({(5,0),(5,1)}if role==7 else{(5,0)}):
                issues.append({**where,'definition':ids[role],'error':'GIA signal metadata interface mismatch'})
        for index,typ in enumerate((1,2,1)):
            p=ports[2].get((4,index))
            if p is None or descriptor_problem(get(p,4,default=b''),typ):
                issues.append({**where,'port':[4,index],'error':'GIA signal fixed output mismatch'})
        params={role:{index-(3 if role==2 else 0):p for(kind,index),p in ps.items()
                      if kind==(4 if role==2 else 3)and(role!=2 or index>=3)}for role,ps in ports.items()}
        expected=set(range(len(params[1])))
        if any(set(ps)!=expected for ps in params.values()):
            issues.append({**where,'error':'GIA signal parameter slots mismatch'});continue
        names=[get(p,1,default=b'')for p in params[1].values()]
        if any(not n for n in names)or any(n>1 for n in Counter(names).values()):
            issues.append({**where,'error':'GIA signal parameter names absent or duplicate'})
        for index,p in params[1].items():
            typ=get(get(p,4,default=b''),3,0);pname=get(p,1,default=b'')
            for role in(1,2,7):
                other=params[role][index];context={**where,'definition':ids[role],'parameter':index}
                if get(other,1,default=b'')!=pname:issues.append({**context,'error':'GIA signal parameter name mismatch'})
                problem=descriptor_problem(get(other,4,default=b''),typ,role==7)
                if problem=='unresolved':unknown.append({**context,'type':typ,'error':'GIA signal parameter dialect uncalibrated'})
                elif problem:issues.append({**context,'error':'GIA signal parameter '+problem})
    return issues,unknown,records
