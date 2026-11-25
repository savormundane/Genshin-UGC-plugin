"""Graph-scoped declarations and server VarBase defaults; not entity defaults."""
from collections import Counter
from authoring_io import sha
from miliastra.native.core import get,ref,slot,audited_port_type,structure_id,node_catalog
from level_inventory import fields,vals


ELEMENTS={7:2,8:3,9:4,10:5,11:6,13:1,15:12,22:20,23:21,24:17,26:25}
CLASSES={1:1,2:1,3:2,4:6,5:4,6:5,12:7,14:6,17:1,20:1,21:1,25:10001,27:10003,
         **{t:10002 for t in ELEMENTS}}


def read(model):
    records=[]
    for graph in model['graphs']+model['composite_graphs']:
        for index,raw in enumerate(vals(fields(graph['raw']),6)):
            if not raw:continue  # Calibrated empty table marker, not a declaration.
            records.append({'graph':graph['id'],'graph_kind':graph['kind'],'index':index,
                            'name':get(raw,2,default=b'').decode('utf-8'),'type_id':get(raw,3,0),
                            'key_type':get(raw,7,0),'value_type':get(raw,8,0),
                            'raw':raw,'default':get(raw,4)})
    return records


def summary(record):
    return {k:v for k,v in record.items()if k not in('raw','default')}|{
        'default_sha256':sha(record['default'])if record['default']is not None else None}


def accesses(model,*,type_at=audited_port_type):
    """Read builtin graph-variable accesses without evaluating dynamic names."""
    declarations={}
    for record in read(model):
        declarations.setdefault((record['graph_kind'],record['graph'],record['name']),[]).append(record)
    result=[];catalog,types=node_catalog()
    for graph in model['graphs']+model['composite_graphs']:
        connected=set()
        for ident,n in graph['nodes'].items():
            for p in vals(fields(n),4):
                for c in vals(fields(p),5):
                    remote=get(c,2,default=b'')
                    if slot(p)[0]==3:connected.add((ident,slot(p)[1]))
                    elif slot(p)[0]==4 and get(remote,1,0)==3:
                        connected.add((get(c,1,0),get(remote,2,0,0)))
        for ident,n in graph['nodes'].items():
            generic=ref(get(n,2,default=b''))
            if generic not in(323,337):continue
            value_port=(3,1)if generic==323 else(4,0)
            item={'graph_kind':graph['kind'],'graph':graph['id'],'node':ident,
                  'operation':'write'if generic==323 else'read','name':None,
                  'name_kind':'missing','resolution':'unresolved','value_port':list(value_port),
                  'type_id':type_at(graph,n,*value_port,model['definitions'])}
            p=next((p for p in vals(fields(n),4)if slot(p)==(3,0)),None)
            # A retained literal on a connected input is a fallback, not its
            # runtime name. Edges can be serialized only at the remote output.
            if (ident,0)in connected:item['name_kind']='dynamic'
            elif p is not None and get(p,3)is not None:
                value=get(p,3)
                if get(value,1,0)==10000:value=get(get(value,110,default=b''),2,default=b'')
                if get(value,1,0)==5:
                    item['name_kind']='literal';item['name']=get(get(value,105,default=b''),1,default=b'').decode('utf-8')
                else:item['name_kind']='invalid_literal'
            matches=declarations.get((graph['kind'],graph['id'],item['name']),[])if item['name_kind']=='literal'else[]
            if len(matches)==1:
                declaration=matches[0];item.update(resolution='declared',declared_type=declaration['type_id'])
                if item['type_id']in(25,26):
                    descriptor=get(get(declaration['default'] or b'',4,default=b''),100,default=b'')
                    item.update(structure_id=structure_id(n,*value_port,model['definitions']),
                                declared_structure_id=get(get(descriptor,100,default=b''),1,0))
                elif item['type_id']==27:
                    item['declared_dictionary_types']=[declaration['key_type'],declaration['value_type']]
                    concrete=ref(get(n,3,default=b''))
                    mapping=next((v for v in catalog[generic]['TypeMappings']if v['ConcreteId']==concrete),None)
                    rule=mapping['Type']if mapping else''
                    # Calibrated builtins encode dictionary types in the
                    # concrete variant; list tokens remain intact when split.
                    pair=rule[6:-2].split(',',1)if rule.startswith('S<T:D<')and rule.endswith('>>')else[]
                    item['dictionary_types']=[types.get(t)for t in pair]if len(pair)==2 else None
            elif len(matches)>1:item['resolution']='ambiguous'
            elif item['name_kind']=='literal':item['resolution']='default_if_absent'if generic==337 else'undeclared_write'
            result.append(item)
    return result


def audit_value(value,expected,context,known,issues,unknown,references=None,expected_sid=None):
    from miliastra.native.structures import record_reference
    item=get(value,4,default=b'');descriptor=get(item,100,default=b'')
    typ=get(descriptor,1,0);cls=get(value,1,0)
    if get(item,1,0)!=1:
        unknown.append({**context,'error':'graph variable default dialect unresolved'})
    if typ not in CLASSES:
        unknown.append({**context,'error':'graph variable default type unresolved','type_id':typ})
    if expected is not None and typ!=expected:
        issues.append({**context,'error':'graph variable default type mismatch','expected':expected,'actual':typ})
    if typ in CLASSES and cls!=CLASSES[typ]:
        issues.append({**context,'error':'graph variable default carrier mismatch','type_id':typ,'class':cls})
        return
    if typ not in CLASSES:return
    sid=get(get(descriptor,100,default=b''),1,0)
    if typ in(25,26):
        record_reference(references,context,sid,'graph_variable_default_structure')
        if sid is not None and sid not in known:
            issues.append({**context,'error':'graph variable default structure absent','struct_id':sid})
        if expected_sid is not None and sid is not None and sid!=expected_sid:
            issues.append({**context,'error':'graph variable list structure mismatch','expected':expected_sid,'actual':sid})
    if typ in ELEMENTS or typ==25:
        payload=get(value,109 if typ in ELEMENTS else 108,default=b'')
        for index,child in enumerate(vals(fields(payload),1)):
            where={**context,'value_path':[*context.get('value_path',[]),index]}
            audit_value(child,ELEMENTS.get(typ),where,known,issues,unknown,references,sid if typ==26 else None)
    elif typ==27:
        subtype=get(descriptor,101,default=b'');types=(get(subtype,1,0),get(subtype,2,0))
        if any(t not in CLASSES for t in types):
            unknown.append({**context,'error':'graph variable dictionary subtype unresolved','types':list(types)})
        for index,pair in enumerate(vals(fields(get(value,112,default=b'')),1)):
            where={**context,'value_path':[*context.get('value_path',[]),index]}
            pair_item=get(pair,4,default=b'');pair_type=get(pair_item,100,default=b'');pair_subtype=get(pair_type,101,default=b'')
            if get(pair,1,0)!=10007 or get(pair_item,1,0)!=1 or get(pair_type,1,0)!=25:
                issues.append({**where,'error':'graph variable dictionary pair carrier mismatch'})
            if (get(pair_subtype,1,0),get(pair_subtype,2,0))!=types:
                issues.append({**where,'error':'graph variable dictionary pair subtype mismatch'})
            body=get(pair,111,default=b'')
            for position,typ in enumerate(types,1):
                child=get(body,position)
                if child is None:issues.append({**where,'error':'graph variable dictionary item absent','position':position})
                else:audit_value(child,typ,{**where,'value_path':[*where['value_path'],position]},known,issues,unknown,references)


def audit(model,references=None,*,type_at=audited_port_type):
    records=read(model);issues=[];unknown=[]
    known={get(get(s,1,default=b''),1,0)for s in model['structs']}
    counts=Counter((r['graph_kind'],r['graph'],r['name'])for r in records)
    for (kind,graph,name),count in counts.items():
        if count>1:issues.append({'graph':graph,'graph_kind':kind,'graph_variable':name,'error':'duplicate graph variable name'})
    for record in records:
        context={k:record[k]for k in('graph','graph_kind','index')}|{'graph_variable':record['name']}
        if not record['name']:issues.append({**context,'error':'graph variable name absent'})
        typ=record['type_id'];value=record['default']
        if typ not in CLASSES:unknown.append({**context,'error':'graph variable declaration type unresolved','type_id':typ})
        if value is None:
            unknown.append({**context,'error':'graph variable default absent'})
            continue
        audit_value(value,typ,context,known,issues,unknown,references)
        if typ==27:
            subtype=get(get(get(value,4,default=b''),100,default=b''),101,default=b'')
            declared=(record['key_type'],record['value_type'])
            if declared!=(get(subtype,1,0),get(subtype,2,0)):
                issues.append({**context,'error':'graph variable dictionary declaration mismatch','declared':list(declared)})
    for access in accesses(model,type_at=type_at):
        context={k:access[k]for k in('graph_kind','graph','node','operation','name')}
        if access['name_kind']=='invalid_literal':
            issues.append({**context,'error':'graph variable name literal must be string'})
        if access['resolution']!='declared':continue
        actual=access['type_id'];expected=access['declared_type']
        if actual is None:unknown.append({**context,'error':'graph variable access type unresolved'})
        elif actual!=expected:
            issues.append({**context,'error':'graph variable access type mismatch','expected':expected,'actual':actual})
        elif actual in(25,26):
            sid=access['structure_id'];declared=access['declared_structure_id']
            if sid is not None and declared is not None and sid!=declared:
                issues.append({**context,'error':'graph variable access structure mismatch','expected':declared,'actual':sid})
        elif actual==27:
            pair=access['dictionary_types']
            if pair is None or None in pair:
                unknown.append({**context,'error':'graph variable access dictionary types unresolved'})
            elif pair!=access['declared_dictionary_types']:
                issues.append({**context,'error':'graph variable access dictionary types mismatch','expected':access['declared_dictionary_types'],'actual':pair})
    return issues,unknown
