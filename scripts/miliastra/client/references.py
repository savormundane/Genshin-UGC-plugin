"""Resolve source-located Lua signal names against the final native container."""
from collections import Counter
from miliastra.native.core import model,get
from authoring_io import sha
from level_inventory import fields,vals
from protocol_types import TYPES


def check_protocol(raw,scripts,contract):
    from production_core import protocol
    from protocol_codegen import wire
    declarations={s['name']:s for s in protocol(contract)['signals']}
    references=[];errors=[];unresolved=[];layouts=[]
    operations={('game','ServerSignal'):('send','client_to_server'),
                ('Script','RegisterServerSignalHandler'):('listen','server_to_client'),
                ('Script','UnregisterServerSignalHandler'):('unlisten','server_to_client')}
    for script in scripts:
        for call in script.get('api',{}).get('calls',[]):
            operation=operations.get((call['owner'],call['name']))
            if operation is None:continue
            argument=call['arguments'][0]if call['arguments']else None
            name=argument.get('value')if argument and argument['type']=='string'else None
            ref={'mapping':script['mapping'],'line':call['line'],'range':call['range'],
                 'name':name,'operation':operation[0],'required_direction':operation[1]}
            declaration=declarations.get(name)
            if name is None:ref['resolution']='dynamic';unresolved.append(ref)
            elif declaration is None:ref['resolution']='undeclared';errors.append(ref)
            elif declaration['direction']!=operation[1]:
                ref.update(resolution='direction_mismatch',declared_direction=declaration['direction']);errors.append(ref)
            else:ref['resolution']='resolved'
            references.append(ref)
    if raw is not None:
        native=model(raw)['signals']
        for name,declaration in declarations.items():
            expected=[{'name':f['name'],'type':TYPES[f['type']][1]}for f in wire(declaration)]
            matches=[s for s in native if get(s,3,default=b'').decode('utf-8')==name]
            actual=None if len(matches)!=1 else [{'name':get(p,1,default=b'').decode('utf-8'),'type':get(p,2,0)}for p in vals(fields(matches[0]),4)]
            record={'name':name,'expected':expected,'actual':actual,'status':'passed'if actual==expected else'failed'}
            layouts.append(record)
            if record['status']=='failed':errors.append({'error':'protocol_native_layout_mismatch',**record})
    return {'status':'failed'if errors else'not_checked'if unresolved else'passed',
            'scope':'declared_protocol_direction_and_native_wire_layout','references':references,'layouts':layouts,
            'errors':errors,'unresolved':unresolved,'direction_source':'explicit_project_contract',
            'native_layout':'not_checked'if raw is None else'failed'if any(x['status']=='failed'for x in layouts)else'passed',
            'delivery':'not_checked','runtime_phase_and_target':'not_checked'}


def check_templates(raw,scripts):
    from level_authoring import inspect_bindings
    bindings=inspect_bindings(raw);templates={}
    for template in bindings['templates']:
        templates.setdefault(template['instantiation_index'],[]).append(template)
    references=[];errors=[];unresolved=[]
    for script in scripts:
        for call in script.get('api',{}).get('calls',[]):
            if (call['owner'],call['name'])!=('game','InstantiateClientUIControl'):continue
            argument=call['arguments'][0]if call['arguments']else{}
            ident=argument.get('value')
            reference={'mapping':script['mapping'],'line':call['line'],'range':call['range'],'kind':'control_template','index':ident}
            if type(ident)is not int:
                reference['resolution']='dynamic';unresolved.append(reference)
            else:
                matches=templates.get(ident,[])
                if len(matches)!=1:
                    reference['resolution']='missing'if not matches else'ambiguous';errors.append(reference)
                elif not matches[0]['reciprocal_reference_verified']:
                    reference['resolution']='invalid_template_binding';errors.append(reference)
                else:
                    reference.update(resolution='resolved',template_name=matches[0]['name'],template_guid=matches[0]['template_guid'])
            references.append(reference)
    return {'status':'failed'if errors else'not_checked'if unresolved else'passed'if references else'not_applicable',
            'scope':'instantiated_control_template_indices','artifact_sha256':sha(raw),'references':references,
            'errors':errors,'unresolved':unresolved,'runtime_control_ids':'not_checked','parent_lifetime':'not_checked','complete_reference_index':False}


def check_signals(raw,scripts):
    native=model(raw)
    names=Counter(get(s,3,default=b'').decode('utf-8')for s in native['signals'])
    references=[];errors=[];unresolved=[];packets=[]
    method_types={v[2]:v[1]for v in TYPES.values()}
    operations={('game','ServerSignal'):'send',('Script','RegisterServerSignalHandler'):'listen',
                ('Script','UnregisterServerSignalHandler'):'unlisten'}
    for script in scripts:
        for call in script.get('api',{}).get('calls',[]):
            operation=operations.get((call['owner'],call['name']))
            if operation is None:continue
            arg=call['arguments'][0]if call['arguments']else None
            name=arg.get('value')if arg and arg['type']=='string'else None
            reference={'mapping':script['mapping'],'line':call['line'],'range':call['range'],
                       'kind':'signal','operation':operation,'name':name}
            if name is None:
                reference['resolution']='dynamic';unresolved.append(reference)
            elif names[name]!=1:
                reference['resolution']='missing'if names[name]==0 else'ambiguous';errors.append(reference)
            else:reference['resolution']='resolved'
            references.append(reference)
        calls=script.get('api',{}).get('calls',[])
        for creation in calls:
            if (creation['owner'],creation['name'])!=('game','ServerSignal'):continue
            arg=creation['arguments'][0]if creation['arguments']else None
            name=arg.get('value')if arg else None
            if name is None or names[name]!=1:continue
            declaration=next(s for s in native['signals']if get(s,3,default=b'').decode('utf-8')==name)
            expected=[get(p,2,0)for p in vals(fields(declaration),4)]
            uses=sorted([c for c in calls if c.get('signal_origin')==creation['range']],key=lambda c:c['range'][0])
            actual=[];sent=False
            uncertain=creation.get('conditional',True)or any(c.get('conditional',True)or c.get('scope')!=creation.get('scope')for c in uses)
            uncertain=uncertain or any(d['reason']=='signal_escapes_known_calls'for d in script.get('api',{}).get('unresolved',[]))
            for call in uses:
                if call['name']in method_types:actual.append(method_types[call['name']])
                elif call['name']=='AddParam':uncertain=True
                elif call['name']=='SendSignal':
                    packet={'mapping':script['mapping'],'line':call['line'],'name':name,'expected':expected,'actual':list(actual),
                            'status':'not_checked'if uncertain or sent else'passed'if actual==expected else'failed'}
                    packets.append(packet);sent=True
                    if packet['status']=='failed':errors.append({'error':'signal_parameter_order_or_type',**packet})
                    elif packet['status']=='not_checked':unresolved.append({'error':'signal_parameter_flow_unresolved',**packet})
    return {'status':'failed'if errors else'not_checked'if unresolved else'passed'if references else'not_applicable',
            'scope':'signal_names_and_straight_line_send_parameters','artifact_sha256':sha(raw),'references':references,
            'errors':errors,'unresolved':unresolved,'packets':packets,
            'signal_parameters':'failed'if any(p['status']=='failed'for p in packets)else'not_checked'if not packets or any(p['status']=='not_checked'for p in packets)else'passed',
            'direction_and_delivery':'not_checked','complete_reference_index':False}
