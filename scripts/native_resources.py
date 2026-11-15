"""Declaration identities, graph dependencies and composite interface references."""
from collections import Counter
from native_core import get,ref,slot,port_type,structure_id,descriptor_structure_id
from native_ports import declared_ports,exists
from level_inventory import fields,vals


def locator_key(raw):
    return tuple(get(raw,k,0,0)for k in(1,2,3,4,5))


def audit_resources(model):
    issues=[];unknown=[];definitions=model['definitions']
    from native_signals import audit_gia_signals
    signal_issues,signal_unknown,signal_declarations=audit_gia_signals(model)
    issues.extend(signal_issues);unknown.extend(signal_unknown)
    composites={g['id']:g for g in model['composite_graphs']};owners={}
    client_senders={ref(get(s,7,default=b''))for s in model['signals']}
    if model['format']=='gia':client_senders.update(i for i,r in signal_declarations.items()if r['role']==7)
    for ident,d in definitions.items():
        signature=get(d,4,default=b'');shell=get(signature,1);kernel=get(signature,2)
        where={'definition':ident};behavior=get(get(d,107,default=b''),1,0)
        if ident is None or shell is None or kernel is None:
            issues.append({**where,'error':'declaration signature reference absent'})
        elif locator_key(shell)!=locator_key(kernel):
            # Original signal calibration: client send-to-server declarations
            # use their own shell ID but builtin kernel 2000, in category 20002.
            calibrated=(ident in client_senders and behavior==1001 and
                        locator_key(shell)==(10001,20002,22001,0,ident)and
                        locator_key(kernel)==(10001,20002,22000,0,2000))
            # Original structure GIA exports include client helpers backed by
            # the assemble/split kernels in the same client graph category.
            category=get(shell,2,0)
            calibrated=calibrated or (behavior in(1003,1004)and category in(20001,20002,20007)and
                        locator_key(shell)==(10001,category,22001,0,ident)and
                        locator_key(kernel)==(10001,category,22000,0,{1003:1060,1004:1061}[behavior]))
            if not calibrated:issues.append({**where,'error':'declaration signature references disagree'})
        target=get(signature,4)
        if behavior==1000 or target:
            gid=ref(target or b'');g=composites.get(gid)
            if g is None:issues.append({**where,'error':'composite graph target absent','graph':gid});continue
            if behavior!=1000:issues.append({**where,'error':'composite graph reference on non-composite declaration'})
            if locator_key(target)!=locator_key(get(g['raw'],1,default=b'')):
                issues.append({**where,'error':'composite graph locator mismatch','graph':gid})
            owners.setdefault(gid,[]).append((ident,d))
    for gid,g in composites.items():
        where={'graph':gid,'graph_kind':'composite'}
        if get(get(g['raw'],1,default=b''),3,0)!=21002:
            issues.append({**where,'error':'composite graph identity kind mismatch'})
        if gid not in owners:issues.append({**where,'error':'composite graph declaration absent'})
        for ident,d in owners.get(gid,[]):
            ports=declared_ports(d);seen=set();mapped=Counter()
            for mapping in vals(fields(g['raw']),4):
                external=slot(mapping);target=get(mapping,2,0)
                signatures=[]
                for key in(3,4):
                    raw=get(mapping,key)
                    signatures.append(None if raw is None else(get(raw,1,0,0),get(raw,2,0,0)))
                shell,kernel=signatures;context={**where,'definition':ident,'port':list(external),'target':target}
                key=(external,target,shell,kernel)
                if key in seen:issues.append({**context,'error':'duplicate composite interface mapping'})
                seen.add(key);mapped[external]+=1
                if external not in ports:issues.append({**context,'error':'composite external port absent'});continue
                n=g['nodes'].get(target)
                if n is None:issues.append({**context,'error':'composite internal node absent'});continue
                if shell is None or kernel is None or shell[0]!=external[0]or kernel[0]!=external[0]:
                    issues.append({**context,'error':'composite interface direction mismatch'});continue
                presence=exists(n,*shell,definitions)
                if presence is False:issues.append({**context,'error':'composite internal port absent'});continue
                if presence is None:unknown.append({**context,'error':'composite internal port unresolved'})
                # The bundled backend uses ordinal indices when no calibrated
                # NodeEditorPack override is available. Do not accept an arbitrary
                # kernel index just because a stored instance repeats that value.
                if kernel!=shell:unknown.append({**context,'error':'composite kernel mapping uncalibrated','shell':list(shell),'kernel':list(kernel)})
                if external[0]in(3,4):
                    descriptor=get(ports[external],4,default=b'')
                    expected=get(descriptor,3,0);actual=port_type(n,*shell,definitions)
                    if expected is None or actual is None:unknown.append({**context,'error':'composite interface type unresolved'})
                    elif expected!=actual:issues.append({**context,'error':'composite interface type mismatch','types':[expected,actual]})
                    elif expected in(25,26):
                        sid=descriptor_structure_id(descriptor)
                        inner=structure_id(n,*shell,definitions)
                        if sid is None or inner is None:unknown.append({**context,'error':'composite interface structure unresolved'})
                        elif sid!=inner:issues.append({**context,'error':'composite interface structure mismatch'})
            for key in ports:
                if key[0]==4 and mapped[key]!=1:
                    issues.append({**where,'definition':ident,'port':list(key),'error':'composite data output requires one mapping'})
    gids={g['id']for g in model['graphs']}
    for gid in model['graph_library']:
        if gid not in gids:issues.append({'graph':gid,'error':'graph library target absent'})
    resources=model['resources'];keys=Counter((r['class'],r['id'])for r in resources)
    for key,count in keys.items():
        if count>1:issues.append({'resource':list(key),'error':'duplicate GIA resource identity'})
    for r in resources:
        for target in r['references']:
            if tuple(target)not in keys:issues.append({'resource':[r['class'],r['id']],'target':target,'error':'GIA dependency absent'})
    return issues,unknown


def composite_contracts(model):
    """Compare independently allocated GIA/GIL IDs by unique declaration names.

    Port UIDs are also allocated differently by the two backends. Each file's
    own UID relationships are audited separately; compare typed interface slots,
    internal nodes, constants and mappings across representations.
    """
    from level_inventory import graph_summary
    definitions=model['definitions'];graphs={g['id']:g for g in model['composite_graphs']};result={}
    for ident,d in definitions.items():
        if get(get(d,107,default=b''),1,0)!=1000:continue
        name=get(d,200,default=b'').decode('utf-8')
        if not name or name in result:raise ValueError('Composite declaration name missing or ambiguous')
        gid=ref(get(get(d,4,default=b''),4,default=b''));g=graphs.get(gid)
        if g is None:raise ValueError('Composite graph dependency absent')
        summary=graph_summary(g['raw'])
        contract={key:summary[key]for key in('stored_nodes','connections','variables','literal_values')}
        contract['ports']=[(key,get(p,1),get(get(p,4,default=b''),3,0))for key,p in sorted(declared_ports(d).items())]
        contract['mappings']=sorted((slot(p),get(p,2,0),tuple((get(get(p,k,default=b''),1,0,0),get(get(p,k,default=b''),2,0,0))for k in(3,4)))for p in vals(fields(g['raw']),4))
        contract['nodes']=[]
        for index,n in sorted(g['nodes'].items()):
            types=[]
            for key in(2,3):
                type_id=ref(get(n,key,default=b''))
                types.append(('declaration',get(definitions[type_id],200))if type_id in definitions else('builtin',type_id))
            contract['nodes'].append((index,types))
        result[name]=contract
    return result
