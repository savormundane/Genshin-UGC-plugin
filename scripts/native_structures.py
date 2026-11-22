"""Check calibrated structure references even when no graph edge consumes them."""
from native_core import get,slot,definition_id,audited_port_type,structure_ids,descriptor_structure_ids
from native_ports import client_node,declared_ports
from level_inventory import fields,vals


def record_reference(references,context,target,relation):
    if references is not None and target is not None:
        references.append({'context':context,'struct_id':target,'relation':relation})


def audit_dictionary(value,context,known,issues,unknown,declared=None,references=None):
    """Dictionary subtype 504 is a structure ID; payload 37/504 is a type."""
    descriptors=[d for d in(declared,get(value,2))if d is not None]
    contracts=[]
    for descriptor in descriptors:
        subtype=get(descriptor,2,default=b'')
        key_type=get(subtype,502,0);value_type=get(subtype,503,0)
        target=get(subtype,504,0)
        contracts.append((key_type,value_type,target or None))
        if get(descriptor,1,0)!=27:issues.append({**context,'error':'dictionary descriptor type mismatch'})
        if key_type is None or value_type is None:
            unknown.append({**context,'error':'dictionary key/value types unresolved'})
        if value_type in(25,26):
            record_reference(references,context,target,'dictionary_value_type')
            if not target:unknown.append({**context,'error':'dictionary structure identity unresolved'})
            elif target not in known:issues.append({**context,'error':'dictionary structure declaration absent','target':target})
    if len(set(contracts))>1:issues.append({**context,'error':'dictionary declaration/default mismatch'})
    if not contracts:
        unknown.append({**context,'error':'dictionary descriptor absent'})
        return
    key_type,value_type,target=contracts[0]
    payload=get(value,37,default=b'')
    if not payload:return  # The bundled writer encodes empty defaults as bytes.
    payload_types=(get(payload,503,0),get(payload,504,0))
    if payload_types!=(key_type,value_type):
        issues.append({**context,'error':'dictionary payload type mismatch','actual':list(payload_types)})
    rows=fields(payload);keys=vals(rows,501);values=vals(rows,502);pairs=vals(rows,1)
    if len(keys)!=len(values):issues.append({**context,'error':'dictionary key/value count mismatch'})
    if pairs and (keys or values) and len(pairs)!=len(keys):
        issues.append({**context,'error':'dictionary pair count mismatch'})
    entries=[(k,v,['entry',i])for i,(k,v)in enumerate(zip(keys,values))]
    # Validate unpaired values too, so truncating the key list cannot hide a ref.
    entries.extend((b'',v,['value',i])for i,v in enumerate(values[len(keys):],len(keys)))
    entries.extend((k,b'',['key',i])for i,k in enumerate(keys[len(values):],len(values)))
    for i,pair in enumerate(pairs):
        where={**context,'value_path':[*context.get('value_path',[]),'pair',i]}
        body=get(pair,35,default=b'');subtype=get(get(pair,2,default=b''),2,default=b'')
        # Pair structures are local dictionary carriers (64 in the original
        # string/bool sample), not declarations in the global structure table.
        pair_id=get(subtype,2,0);body_id=get(body,501,0)
        if get(pair,1,0)!=25 or get(get(pair,2,default=b''),1,0)!=25:
            issues.append({**where,'error':'dictionary pair type mismatch'})
        if pair_id is None or body_id is None:
            unknown.append({**where,'error':'dictionary pair identity unresolved'})
        elif pair_id!=body_id:issues.append({**where,'error':'dictionary pair identity mismatch'})
        for descriptor in descriptors:
            carrier=get(get(descriptor,2,default=b''),2,0)
            if carrier and pair_id!=carrier:
                issues.append({**where,'error':'dictionary pair/descriptor identity mismatch'})
        if (get(subtype,502,0),get(subtype,503,0))!=(key_type,value_type):
            issues.append({**where,'error':'dictionary pair subtype mismatch'})
        pair_target=get(subtype,504,0)
        if value_type in(25,26) and pair_target!=target:
            issues.append({**where,'error':'dictionary pair structure mismatch','target':pair_target})
        children=vals(fields(body),1)
        if len(children)!=2:issues.append({**where,'error':'dictionary pair arity mismatch'})
        for position,child in enumerate(children):
            expected_type=key_type if position==0 else value_type
            child_context={**where,'value_path':[*where['value_path'],position]}
            if get(child,1,0)!=expected_type:
                issues.append({**child_context,'error':'dictionary item type mismatch','expected':expected_type})
            audit_value(child,child_context,known,issues,unknown,target if position else None,references=references)
    for key,item,path in entries:
        for position,child in enumerate((key,item)):
            if not child:continue
            where={**context,'value_path':[*context.get('value_path',[]),*path,position]}
            expected_type=key_type if position==0 else value_type
            if get(child,1,0)!=expected_type:
                issues.append({**where,'error':'dictionary item type mismatch','expected':expected_type})
            audit_value(child,where,known,issues,unknown,target if position else None,references=references)


def audit_value(value,context,known,issues,unknown,expected=None,declared=None,references=None):
    """Calibrated typed defaults; field 502/4 is a value ID, not a type ID."""
    typ=get(value,1,0)
    if typ==27 or (declared is not None and get(declared,1,0)==27):
        audit_dictionary(value,context,known,issues,unknown,declared,references)
        return
    if typ not in(25,26):return
    container=get(value,10+typ,default=b'')
    descriptor=get(get(value,2,default=b''),2,default=b'')
    ids={get(descriptor,2,0),get(container,501,0),expected}-{None}
    for sid in sorted(ids):record_reference(references,context,sid,'default_structure')
    if not ids:unknown.append({**context,'error':'default structure identity unresolved'})
    if len(ids)>1:issues.append({**context,'error':'conflicting default structure identities','structures':sorted(ids)})
    for sid in sorted(ids-known):issues.append({**context,'error':'default structure declaration absent','struct_id':sid})
    target=next(iter(ids))if len(ids)==1 else None
    for index,child in enumerate(vals(fields(container),1)):
        if not child:continue
        where={**context,'value_path':[*context.get('value_path',[]),index]}
        if typ==26 and get(child,1,0)!=25:
            issues.append({**where,'error':'structure list default item type mismatch'})
        audit_value(child,where,known,issues,unknown,target if typ==26 else None,references=references)


def audit_references(model,references=None,*,type_at=audited_port_type):
    known={get(get(s,1,default=b''),1,0)for s in model['structs']}
    issues=[];unknown=[]
    if None in known:issues.append({'error':'structure ID absent'})
    for structure in model['structs']:
        sid=get(get(structure,1,default=b''),1,0)
        for body_key in(1,2):
            body=get(structure,body_key)
            if body is None:continue
            context={'struct_id':sid,'body':body_key}
            if get(body,1,0)!=sid:issues.append({**context,'error':'structure body identity mismatch','actual':get(body,1,0)})
            seen=set()
            for member in vals(fields(body),3):
                index=get(member,503,0);where={**context,'member':index}
                if index is None or index in seen:issues.append({**where,'error':'missing or duplicate structure member index'})
                seen.add(index)
                descriptor=get(member,1,default=b'');value=get(member,3,default=b'')
                types={get(member,502,0),get(descriptor,1,0),get(value,1,0)}-{None}
                if len(types)>1:issues.append({**where,'error':'structure member type mismatch','types':sorted(types)})
                target=get(get(descriptor,2,default=b''),2,0)if types&{25,26}else None
                record_reference(references,where,target,'member_type')
                if target is not None and target not in known:issues.append({**where,'error':'member structure declaration absent','target':target})
                audit_value(value,where,known,issues,unknown,target,descriptor,references)
    templates=set()
    for template in model['storage_templates']:
        ident=get(template,1,0);context={'storage_template':ident}
        if ident is None or ident in templates:issues.append({**context,'error':'missing or duplicate storage template ID'})
        templates.add(ident);slots=set()
        for slot_data in vals(fields(get(template,2,default=b'')),2):
            index=get(slot_data,1,0);where={**context,'storage_slot':index}
            if index is None or index in slots:issues.append({**where,'error':'missing or duplicate storage slot ID'})
            slots.add(index);descriptor=get(slot_data,2,default=b'')
            if get(descriptor,1,0)==1:record_reference(references,where,get(descriptor,2,0),'storage_slot_type')
            if get(descriptor,1,0)!=1:unknown.append({**where,'error':'storage slot type unresolved'})
            elif get(descriptor,2,0)not in known:issues.append({**where,'error':'storage structure declaration absent','struct_id':get(descriptor,2,0)})
    # Declarations are live resources independently of instantiated consumers.
    for ident,d in model['definitions'].items():
        ports=declared_ports(d)
        for key,p in ports.items():
            descriptor=get(p,4,default=b'');ids=descriptor_structure_ids(descriptor)
            context={'definition':ident,'port':list(key)}
            for sid in sorted(ids):record_reference(references,context,sid,'declaration_port_type')
            for sid in ids-known:issues.append({**context,'error':'declaration structure absent','struct_id':sid})
            if len(ids)>1:issues.append({**context,'error':'conflicting declaration structure identities','structures':sorted(ids)})
            if get(descriptor,3,0)in(25,26)and not ids:unknown.append({**context,'error':'declaration structure identity unresolved'})
            if get(descriptor,3,0)==26:
                child=get(get(descriptor,102,default=b''),1)
                if child is not None and get(child,3,0)!=25:
                    issues.append({**context,'error':'structure list declaration element type mismatch'})
        behavior=get(d,107,default=b'');kind=get(behavior,1,0)
        if kind in(1003,1004,1005):
            sid=get(get(behavior,{1003:104,1004:105,1005:106}[kind],default=b''),1,0)
            record_reference(references,{'definition':ident},sid,'structure_helper')
            if sid not in known:issues.append({'definition':ident,'error':'structure helper target absent','struct_id':sid})
            primary=ports.get((4,0)if kind==1003 else(3,0),b'')
            primary_id=get(get(get(primary,4,default=b''),104,default=b''),2,0)
            if primary_id!=sid:issues.append({'definition':ident,'error':'structure helper identity mismatch','structures':[sid,primary_id]})
    for g in model['graphs']+model['composite_graphs']:
        for ident,n in g['nodes'].items():
            context={'graph':g['id'],'graph_kind':g['kind'],'node':ident}
            for registration in vals(fields(n),10):
                descriptor=get(registration,100)
                if descriptor is not None:
                    sid=get(descriptor,1,0)
                    record_reference(references,context,sid,'node_registration')
                    if sid not in known:issues.append({**context,'error':'registered structure absent','struct_id':sid})
            keys={slot(p)for p in vals(fields(n),4)}
            definition=model['definitions'].get(definition_id(n,model['definitions']))
            if definition is not None:keys.update(declared_ports(definition))
            for kind,index in sorted(keys):
                if kind not in(3,4):continue
                if type_at(g,n,kind,index,model['definitions'])not in((22,23) if client_node(n) else (25,26)):continue
                ids=structure_ids(n,kind,index,model['definitions']);where={**context,'port':[kind,index]}
                for sid in sorted(ids):record_reference(references,where,sid,'node_port_type')
                if not ids:unknown.append({**where,'error':'struct identity unresolved'})
                if len(ids)>1:issues.append({**where,'error':'conflicting port structure identities','structures':sorted(ids)})
                for sid in sorted(ids-known):issues.append({**where,'error':'referenced structure declaration absent','struct_id':sid})
    return issues,unknown
