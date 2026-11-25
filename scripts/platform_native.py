"""Selected timer bindings and calibrated time-sequence edits."""
import math,struct
from authoring_io import PLUGIN,sha
from level_authoring import flt,msg,set_section
from miliastra.native.core import model,get,ref,slot,replace_message
from miliastra.native.ports import reference_error
from miliastra.native.model import constant
from level_inventory import calibrated_container,fields,vals


def timer_context(native,binding,*,writing=False):
    graphs=[g for g in native['graphs'] if g['id']==binding['graph']]
    if len(graphs)!=1 or binding['node'] not in graphs[0]['nodes']:
        return 'failed','missing_or_ambiguous_node',None
    graph=graphs[0];node=graph['nodes'][binding['node']]
    if ref(get(node,2,default=b''))!=79 or 79 in native['definitions'] or reference_error(node,native['definitions']):
        return 'failed','not_calibrated_start_timer',None
    inputs={0,1,2,3} if writing else {0,1,3}
    for source,n in graph['nodes'].items():
        for pin in vals(fields(n),4):
            kind,index=slot(pin)
            for edge in vals(fields(pin),5):
                target=get(edge,2,default=b'');remote=get(edge,1,0)
                if ((source==binding['node'] and kind==3 and index in inputs)
                        or (remote==binding['node'] and kind==4 and get(target,1,0)==3 and get(target,2,0,0) in inputs)):
                    return 'not_checked','connected_timer_inputs',None
    pins={}
    for pin in vals(fields(node),4):
        key=slot(pin)
        if key in pins and key[0]==3 and key[1] in inputs:
            return 'failed','ambiguous_timer_input',None
        pins[key]=pin
    values={}
    for index,cls in ((0,1),(1,5),(3,10002)):
        value=get(pins.get((3,index),b''),3)
        if value is None or get(value,1,0)!=cls:
            return 'not_checked','unsupported_or_missing_constant',None
        if index==3 and any(get(v,1,0)!=4 for v in vals(fields(get(value,109,default=b'')),1)):
            return 'not_checked','unsupported_or_missing_constant',None
        values[index]=constant(value)
    return 'passed',None,(graph,node,pins[(3,3)],values)


def check(raw,spec):
    from platform_profiles import check as check_configuration
    declared=check_configuration(spec)
    if declared['status']!='passed':raise ValueError('Platform configuration must pass before native binding')
    native=model(raw);checks=[];objects={o['id']:o for o in spec['objects']}
    for ident,binding in spec.get('native_bindings',{}).items():
        row={'object':ident,'selector':binding,'status':'passed'};checks.append(row)
        status,reason,context=timer_context(native,binding)
        if status!='passed':row.update(status=status,reason=reason);continue
        values=context[3]
        expected=[struct.unpack('<f',struct.pack('<f',v))[0]for v in objects[ident]['sequence']]
        row['actual']={'entity':values[0],'name':values[1],'sequence':values[3]}
        if values[0]!=binding['entity']or values[1]!=binding['name']or values[3]!=expected:
            row.update(status='failed',reason='native_timer_differs_from_configuration')
    return {'schema':2,'status':'failed'if any(c['status']=='failed'for c in checks)else'not_checked'if not checks or any(c['status']=='not_checked'for c in checks)else'passed',
            'scope':'selected_native_timer_constants','artifact_sha256':sha(raw),'checks':checks,
            'unbound_objects':[o for o in objects if o not in spec.get('native_bindings',{})],
            'whole_artifact_verified':False,'runtime_concurrency':'not_checked','editor':'not_checked','host':'not_checked'}


def set_sequence(data,native,spec,timer_id):
    from platform_profiles import CATALOGUE,check as check_configuration
    calibrated_container(data)
    if not isinstance(timer_id,str) or not timer_id:
        raise ValueError('Timer editing requires a GIL and a timer_id')
    declared=check_configuration(spec)
    bindings=spec.get('native_bindings',{})
    if declared['status']!='passed' or timer_id not in bindings:
        raise ValueError('Timer editing requires a passing platform configuration and an explicit binding')
    binding=bindings[timer_id]
    status,reason,context=timer_context(native,binding,writing=True)
    if status!='passed':raise ValueError('Timer edit refused: '+reason)
    graph,node,pin,values=context
    if values[0]!=binding['entity'] or values[1]!=binding['name']:
        raise ValueError('Native timer entity or name differs from the binding')
    times=next(o['sequence'] for o in spec['objects'] if o['id']==timer_id)
    if any(v>3.4028234663852886e38 for v in times):raise ValueError('Timer time exceeds float32 range')
    expected=list(struct.unpack(f'<{len(times)}f',struct.pack(f'<{len(times)}f',*times)))
    interval=next(r['detail']['minimum_seconds'] for r in declared['checks']
                  if r['object']==timer_id and r['rule']=='timer.interval')
    if expected[-1]<=0 or any(not math.isfinite(v) for v in expected) or any(b-a<interval-1e-12 for a,b in zip(expected,expected[1:])):
        raise ValueError(f'Encoded float32 timer sequence must end above zero and increase by at least {interval}: {expected}')
    sources={CATALOGUE.relative_to(PLUGIN).as_posix():declared['profile']['source_catalogue_sha256']}
    sources.update({r['path']:r['sha256'] for r in declared['sources'].values()})
    detail={'timer_id':timer_id,'selector':binding,'before':values[3],'after':expected,'platform_sources':sources}
    if values[3]==expected:return data,detail
    array=get(pin,3);payload=get(array,109)
    if payload is None or not vals(fields(payload),1):raise ValueError('Existing timer sequence carrier required')
    rows=fields(payload);entries=vals(rows,1)
    new_entries=[]
    for index,value in enumerate(expected):
        entry=entries[index] if index<len(entries) else entries[-1]
        scalar=get(entry,104)
        if scalar is None or any(n==1 and w!=5 for n,w,_,_ in fields(scalar)):
            raise ValueError('Uncalibrated timer float carrier')
        current=get(scalar,1,5)
        if index>=len(entries) and (any((n,w) not in ((1,0),(2,0),(4,0),(104,2)) for n,w,_,_ in fields(entry))
                or any((n,w)!=(1,5) for n,w,_,_ in fields(scalar))):
            raise ValueError('Timer entry contains unknown fields and cannot be extended')
        encoded=flt(1,value) if value else b''
        if current is not None:
            changed=b''.join(encoded if n==1 else raw for n,_,_,raw in fields(scalar))
        else:
            changed=scalar+encoded
        new_entries.append(replace_message(entry,104,scalar,changed))
    for entry in entries[len(expected):]:
        if (any((n,w) not in ((1,0),(2,0),(4,0),(104,2)) for n,w,_,_ in fields(entry))
                or any((n,w)!=(1,5) for n,w,_,_ in fields(get(entry,104,default=b'')))):
            raise ValueError('Timer entry contains unknown fields and cannot be removed')
    replacements=iter(new_entries)
    chunks=[]
    for number,wire,old,raw in rows:
        if (number,wire)==(1,2):
            replacement=next(replacements,None)
            if replacement is not None:chunks.append(raw if old==replacement else msg(1,replacement))
        else:chunks.append(raw)
    chunks.extend(msg(1,entry) for entry in replacements)
    changed=replace_message(array,109,payload,b''.join(chunks))
    new_node=replace_message(node,4,pin,replace_message(pin,3,array,changed))
    new_graph=replace_message(graph['raw'],3,node,new_node)
    section=get(data[20:-4],10)
    wrappers=[w for w in vals(fields(section),1) if get(w,1)==graph['raw']]
    if len(wrappers)!=1:raise ValueError('Timer graph wrapper must match exactly once')
    wrapper=wrappers[0]
    updated=set_section(data,10,replace_message(section,1,wrapper,replace_message(wrapper,1,graph['raw'],new_graph)))
    status,reason,after=timer_context(model(updated),binding,writing=True)
    if status!='passed' or after[3][3]!=expected:raise ValueError('Native timer sequence readback differs: '+str(reason))
    return updated,detail
