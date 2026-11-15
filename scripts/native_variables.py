"""Calibrated template/instance custom-variable declarations and type references.

Entity overrides live in section5/entry7; template defaults in section4/entry8.
Template entry7 is component data, not the same variable-group representation.
"""
from collections import Counter
from authoring_io import sha
from level_inventory import fields,vals
from native_core import get

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
    from native_structures import audit_value,record_reference
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
