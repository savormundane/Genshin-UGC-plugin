"""Calibrated template/instance custom-variable declarations and type references.

Entity overrides live in section5/entry7; template defaults in section4/entry8.
Template entry7 is component data, not the same variable-group representation.
"""
from collections import Counter
import math,struct
from authoring_io import sha,schema
from level_authoring import flt,integer,msg,set_section,text
from level_inventory import calibrated_container,container,fields,unique,vals
from miliastra.native.core import get,replace_message

TYPES={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,17,20,21,22,23,24,25,26,27}


def read(root):
    records=[];issues=[];unknown=[]
    for section,group_field in((4,8),(5,7)):
        for body in vals(root,section):
            for entity in vals(fields(body),1):
                owner={'section':section,'entity_id':get(entity,1,0)};groups=0
                for group_index,group in enumerate(vals(fields(entity),group_field)):
                    if get(group,1,0)!=1:continue
                    if get(group,2,0)!=1:
                        unknown.append({**owner,'error':'custom variable group category unresolved','group_field':group_field,'group_index':group_index})
                        continue
                    groups+=1
                    payload=get(group,11)
                    if payload is None:
                        issues.append({**owner,'error':'custom variable group payload absent'})
                        continue
                    for index,item in enumerate(vals(fields(payload),1)):
                        name=get(item,2,default=b'').decode('utf-8')
                        records.append({**owner,'name':name,'type_id':get(item,3,0),'group_field':group_field,
                                        'group_index':group_index,'index':index,'raw':item,
                                        'descriptor':get(item,6),'value':get(item,4)})
                if groups>1:issues.append({**owner,'error':'duplicate custom variable group'})
    return {'records':records,'issues':issues,'unresolved':unknown}


def summary(record):
    return {k:v for k,v in record.items()if k not in('raw','descriptor','value')}|{
        'descriptor_sha256':sha(record['descriptor'])if record['descriptor']is not None else None,
        'value_sha256':sha(record['value'])if record['value']is not None else None}


def scalar_default(payload,typ):
    wire={3:0,4:0,5:5,6:2}[typ]
    if any(n==1 and w!=wire for n,w,_,_ in fields(payload)):
        raise ValueError('Uncalibrated scalar default encoding')
    value=get(payload,1,wire)
    if typ==3:
        value=value or 0
        return value-(1<<64) if value>=1<<63 else value
    if typ==4:
        if value not in (None,0,1):raise ValueError('Uncalibrated boolean default')
        return value==1
    if typ==5:
        value=struct.unpack('<f',value)[0] if value is not None else 0.0
        if not math.isfinite(value):raise ValueError('Nonfinite existing float default')
        return value
    return (value or b'').decode('utf-8')


def scalar_field(value, typ):
    if typ==3 and type(value)is int and -(1<<63)<=value<(1<<63):
        return integer(1,value%(1<<64)) if value else b''
    if typ==4 and type(value)is bool:
        return integer(1,1) if value else b''
    if typ==5 and type(value) in (float,int) and abs(value)<=3.4028234663852886e38:
        return flt(1,value) if value else b''
    if typ==6 and isinstance(value,str):
        return text(1,value)
    raise ValueError('Invalid value for existing scalar type '+str(typ))


def add_native_variables(data, op):
    from miliastra.native.scene import typed_record
    from miliastra.native.scene_edits import select_record
    schema(op, ('op','template_id','variables'), ('template_id','variables'))
    items = op['variables']
    if not isinstance(items,list) or not items:
        raise ValueError('Provide one or more native scalar defaults')
    _, root = container(data)
    section = unique(root,4,default=b'')
    target = select_record(section,1,op['template_id'],'Variable template')
    carrier = typed_record(target,8,1,strict=True)
    if carrier is not None and (get(carrier,2,0)!=1 or get(carrier,11) is None):
        raise ValueError('Existing variable group is outside the calibrated format')
    previous = get(carrier or b'',11,default=b'')
    names = {get(r,2,default=b'').decode('utf-8') for r in vals(fields(previous),1)}
    additions = []
    written = []
    types = {'integer':3,'boolean':4,'float':5,'string':6}
    for item in items:
        schema(item, ('name','type','default'), ('name','type','default'))
        name, kind = item['name'], item['type']
        if not isinstance(name,str) or not 1<=len(name)<=20 or not name.strip() or '\0' in name or name in names:
            raise ValueError('Native variable names must be unique and have 1–20 characters')
        if kind not in types:
            raise ValueError('Choose integer, boolean, float, or string')
        typ = types[kind]
        descriptor = integer(1,typ)+msg(2)
        payload = scalar_field(item['default'],typ)
        value = integer(1,typ)+msg(2,descriptor)+msg(10+typ,payload)
        additions.append(msg(1,text(2,name)+integer(3,typ)+msg(4,value)+integer(5,1)+msg(6,descriptor)))
        names.add(name)
        written.append({'name':name,'type':kind,'default':scalar_default(payload,typ)})
    updated = previous+b''.join(additions)
    if carrier is None:
        new_target = target+msg(8,integer(1,1)+integer(2,1)+msg(11,updated))
    else:
        new_target = replace_message(target,8,carrier,replace_message(carrier,11,previous,updated))
    return set_section(data,4,replace_message(section,1,target,new_target)), {'template_id':op['template_id'],'variables':written}


def scalar_payload(record):
    """Locate a typed default only when its native descriptors agree."""
    typ=record['type_id'];default=record['value']
    if typ not in (3,4,5,6) or default is None or record['descriptor'] is None:
        raise ValueError('Only existing calibrated scalar defaults are writable')
    payload=get(default,typ+10)
    if (payload is None or get(default,1,0)!=typ or get(get(default,2,default=b''),1,0)!=typ
            or get(record['descriptor'],1,0)!=typ):
        raise ValueError('Custom variable default type mismatch')
    return payload


def set_default(data,model,op):
    keys=('op','section','entity_id','name','value')
    schema(op,keys,keys)
    section,ident,name,value=(op[k] for k in keys[1:])
    calibrated_container(data)
    if (type(section)is not int or section not in (4,5)
            or type(ident)is not int or ident<0 or not isinstance(name,str) or not name):
        raise ValueError('Custom variable target requires GIL, section 4 or 5, entity_id and name')
    records=[r for r in model['custom_variables']['records']
             if (r['section'],r['entity_id'],r['name'])==(section,ident,name)]
    if len(records)!=1:raise ValueError('Expected one existing custom variable in the selected scope')
    record=records[0];typ=record['type_id'];default=record['value']
    carrier=typ+10;payload=scalar_payload(record)
    before=scalar_default(payload,typ)
    field=scalar_field(value,typ)
    new_payload=b''.join(field if n==1 else raw for n,_,_,raw in fields(payload))
    if all(n!=1 for n,_,_,_ in fields(payload)):new_payload+=field
    after=scalar_default(new_payload,typ)
    detail={'section':section,'entity_id':ident,'name':name,'type_id':typ,'before':before,'after':after}
    if before==after:return data,detail
    body=get(data[20:-4],section)
    owners=[e for e in vals(fields(body),1) if get(e,1,0)==ident]
    if len(owners)!=1:raise ValueError('Custom variable owner must match exactly once')
    owner=owners[0];group_field=record['group_field']
    groups=[g for g in vals(fields(owner),group_field) if (get(g,1,0),get(g,2,0))==(1,1)]
    if len(groups)!=1:raise ValueError('Custom variable group must match exactly once')
    group=groups[0];items=get(group,11)
    old_item=record['raw']
    new_item=replace_message(old_item,4,default,replace_message(default,carrier,payload,new_payload))
    new_group=replace_message(group,11,items,replace_message(items,1,old_item,new_item))
    updated=set_section(data,section,replace_message(body,1,owner,replace_message(owner,group_field,group,new_group)))
    observed=[r for r in read(container(updated)[1])['records']
              if (r['section'],r['entity_id'],r['name'])==(section,ident,name)]
    if len(observed)!=1 or scalar_default(get(observed[0]['value'],carrier),typ)!=after:
        raise ValueError('Custom variable default readback differs')
    return updated,detail


def audit_default_types(value,context,issues,unknown,expected=None):
    typ=get(value,1,0);descriptor=get(value,2,default=b'')
    if typ not in TYPES:unknown.append({**context,'error':'custom variable default type unresolved','type_id':typ})
    if typ is None or get(descriptor,1,0)!=typ or(expected is not None and typ!=expected):
        issues.append({**context,'error':'custom variable default type mismatch'})
    payload=get(value,10+typ)if typ in TYPES else None
    if typ in TYPES and payload is None:issues.append({**context,'error':'custom variable value carrier absent','type_id':typ})
    children=[]
    if typ in(25,26):children=[(child,[10+typ,1,i])for i,child in enumerate(vals(fields(payload or b''),1))]
    elif typ==27:
        subtype=get(descriptor,2,default=b'')
        for field in(502,503):
            if get(subtype,field,0)not in TYPES:unknown.append({**context,'error':'custom variable dictionary type unresolved','field':field})
        for field in(501,502):children.extend((child,[37,field,i])for i,child in enumerate(vals(fields(payload or b''),field)))
        # Pair carrier identities are checked by native_structures, not mistaken
        # for global structure declarations here.
        for i,pair in enumerate(vals(fields(payload or b''),1)):
            children.extend((child,[37,1,i,35,1,j])for j,child in enumerate(vals(fields(get(pair,35,default=b'')),1)))
    for child,path in children:
        audit_default_types(child,{**context,'value_path':[*context.get('value_path',[]),*path]},issues,unknown)


def audit(model,references=None):
    from miliastra.native.structures import audit_value,record_reference
    data=model['custom_variables'];issues=list(data['issues']);unknown=list(data['unresolved'])
    known={get(get(s,1,default=b''),1,0)for s in model['structs']}
    counts=Counter((r['section'],r['entity_id'],r['name'])for r in data['records'])
    for (section,entity,name),count in counts.items():
        if count>1:issues.append({'section':section,'entity_id':entity,'custom_variable':name,'error':'duplicate custom variable name'})
    for r in data['records']:
        context={k:r[k]for k in('section','entity_id','group_field','group_index','index')}|{'custom_variable':r['name']}
        if not r['name']:issues.append({**context,'error':'custom variable name absent'})
        typ=r['type_id'];descriptor=r['descriptor'];value=r['value']
        if typ not in TYPES:unknown.append({**context,'error':'custom variable type unresolved','type_id':typ})
        if descriptor is None or value is None:
            issues.append({**context,'error':'custom variable descriptor/default absent'})
            continue
        embedded=get(value,2)
        types=[typ,get(descriptor,1,0)]
        if None in types or len(set(types))!=1:
            issues.append({**context,'error':'custom variable type mismatch','types':types})
        audit_default_types(value,context,issues,unknown,typ)
        declared_subtype=get(descriptor,2,default=b'');value_subtype=get(embedded or b'',2,default=b'')
        target=None
        if typ in(25,26):
            target=get(declared_subtype,2,0)
            record_reference(references,context,target,'custom_variable_type')
            if target is None:unknown.append({**context,'error':'custom variable structure identity unresolved'})
            elif target not in known:issues.append({**context,'error':'custom variable structure declaration absent','target':target})
        elif typ==27:
            # Original instance/template declarations can omit dictionary subtypes
            # that are present in the default's full descriptor. Compare every
            # explicit field, then validate the complete default contract below.
            for field in(2,502,503,504):
                declared=get(declared_subtype,field,0)
                if declared is not None and declared!=get(value_subtype,field,0):
                    issues.append({**context,'error':'custom variable dictionary subtype mismatch','field':field})
        audit_value(value,context,known,issues,unknown,target,references=references)
    return issues,unknown
