"""Client global-variable references against explicitly bound native owners."""
from authoring_io import schema,sha
from native_core import model,get
from native_variables import audit,summary
from level_inventory import container,fields,vals


def validate_targets(targets):
    if not isinstance(targets,dict):raise ValueError('variable_targets must be an object')
    for scope,target in targets.items():
        if scope not in ('Level','PlayerSelf','AvatarSelf'):raise ValueError('Unknown client variable scope')
        schema(target,('kind','id'),('kind','id'))
        if target['kind']not in ('entity','template')or type(target['id'])is not int or target['id']<0:
            raise ValueError('Invalid client variable target')


def check(raw,scripts,targets):
    validate_targets(targets)
    native=model(raw)if raw is not None else None
    issues,unknown=audit(native)if native else([],[])
    bodies={}
    if raw is not None:
        _,root=container(raw)
        for section in (4,5):
            for group in vals(root,section):
                for body in vals(fields(group),1):bodies.setdefault((section,get(body,1,0)),[]).append(body)
    refs=[];errors=[];unresolved=[]
    operations={('game','GetGlobalCustomVariableValue'):'read',
                ('Script','RegisterCustomVariableChangedHandler'):'listen',
                ('Script','UnregisterCustomVariableChangedHandler'):'unlisten'}
    for script in scripts:
        for call in script.get('api',{}).get('calls',[]):
            operation=operations.get((call['owner'],call['name']))
            if operation is None:continue
            args=call['arguments'];scope_arg=args[0]if args else None;name_arg=args[1]if len(args)>1 else None
            scope=scope_arg.get('value')if scope_arg and scope_arg.get('enum')=='Enum.CustomVariableEntityType'else None
            name=name_arg.get('value')if name_arg and name_arg.get('type')=='string'else None
            ref={'mapping':script['mapping'],'line':call['line'],'range':call['range'],'operation':operation,'scope':scope,'name':name}
            target=targets.get(scope)
            if scope is None or name is None:ref['resolution']='dynamic';unresolved.append(ref)
            elif target is None:ref['resolution']='target_not_bound';unresolved.append(ref)
            elif native is None:ref['resolution']='native_not_supplied';unresolved.append(ref)
            else:
                owner=(4 if target['kind']=='template'else 5,target['id']);owners=[owner]
                ref['target']=target
                selected=bodies.get(owner,[])
                if len(selected)!=1:ref['resolution']='target_missing_or_ambiguous';errors.append(ref)
                else:
                    candidates=[r for r in native['custom_variables']['records']if(r['section'],r['entity_id'])==owner and r['name']==name]
                    inherited_unknown=False
                    if not candidates and owner[0]==5:
                        locators=vals(fields(selected[0]),2)
                        if len(locators)==1 and get(locators[0],2,0,0)==0:
                            inherited=(4,get(locators[0],1,0));owners.append(inherited)
                            if len(bodies.get(inherited,[]))!=1:inherited_unknown=True
                            else:candidates=[r for r in native['custom_variables']['records']if(r['section'],r['entity_id'])==inherited and r['name']==name]
                        else:inherited_unknown=True
                    relevant=lambda item:(item.get('section'),item.get('entity_id'))in owners and item.get('custom_variable',name)==name
                    if any(relevant(item)for item in issues)or len(candidates)>1:
                        ref['resolution']='invalid_or_ambiguous_declaration';errors.append(ref)
                    elif inherited_unknown or any(relevant(item)for item in unknown):
                        ref['resolution']='declaration_unresolved';unresolved.append(ref)
                    elif not candidates:ref['resolution']='missing';errors.append(ref)
                    else:ref.update(resolution='resolved',declaration=summary(candidates[0]))
            refs.append(ref)
    return {'status':'failed'if errors else'not_checked'if unresolved else'passed'if refs else'not_applicable',
            'scope':'explicitly_bound_custom_variable_owners','references':refs,'errors':errors,'unresolved':unresolved,
            'artifact_sha256':sha(raw)if raw is not None else None,'target_binding_source':'project_contract',
            'runtime_owner_identity':'not_checked','runtime_value_and_callback':'not_checked'}
