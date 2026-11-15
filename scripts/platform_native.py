"""Read-only selected timer bindings against final native artifacts."""
import struct
from authoring_io import sha
from native_core import model,get,ref,slot
from native_ports import reference_error
from native_model import constant
from level_inventory import fields,vals


def check(raw,spec):
    from platform_profiles import check as check_configuration
    declared=check_configuration(spec)
    if declared['status']!='passed':raise ValueError('Platform configuration must pass before native binding')
    native=model(raw);checks=[];objects={o['id']:o for o in spec['objects']}
    for ident,binding in spec.get('native_bindings',{}).items():
        row={'object':ident,'selector':binding,'status':'passed'};checks.append(row)
        graphs=[g for g in native['graphs']if g['id']==binding['graph']]
        if len(graphs)!=1 or binding['node']not in graphs[0]['nodes']:
            row.update(status='failed',reason='missing_or_ambiguous_node');continue
        nodes=graphs[0]['nodes'];node=nodes[binding['node']]
        if ref(get(node,2,default=b''))!=79 or 79 in native['definitions']or reference_error(node,native['definitions']):
            row.update(status='failed',reason='not_calibrated_start_timer');continue
        incoming=set()
        for source,n in nodes.items():
            for p in vals(fields(n),4):
                kind,index=slot(p)
                for edge in vals(fields(p),5):
                    target=get(edge,2,default=b'');remote=get(edge,1,0)
                    if source==binding['node']and kind==3:incoming.add(index)
                    elif remote==binding['node']and kind==4 and get(target,1,0)==3:incoming.add(get(target,2,0,0))
        if incoming.intersection((0,1,3)):
            row.update(status='not_checked',reason='connected_timer_inputs');continue
        pins={slot(p):p for p in vals(fields(node),4)};values={}
        for index,cls in ((0,1),(1,5),(3,10002)):
            value=get(pins.get((3,index),b''),3)
            if value is None or get(value,1,0)!=cls:break
            if index==3 and any(get(v,1,0)!=4 for v in vals(fields(get(value,109,default=b'')),1)):break
            values[index]=constant(value)
        if len(values)!=3:row.update(status='not_checked',reason='unsupported_or_missing_constant');continue
        expected=[struct.unpack('<f',struct.pack('<f',v))[0]for v in objects[ident]['sequence']]
        row['actual']={'entity':values[0],'name':values[1],'sequence':values[3]}
        if values[0]!=binding['entity']or values[1]!=binding['name']or values[3]!=expected:
            row.update(status='failed',reason='native_timer_differs_from_configuration')
    return {'schema':2,'status':'failed'if any(c['status']=='failed'for c in checks)else'not_checked'if not checks or any(c['status']=='not_checked'for c in checks)else'passed',
            'scope':'selected_native_timer_constants','artifact_sha256':sha(raw),'checks':checks,
            'unbound_objects':[o for o in objects if o not in spec.get('native_bindings',{})],
            'whole_artifact_verified':False,'runtime_concurrency':'not_checked','editor':'not_checked','host':'not_checked'}
