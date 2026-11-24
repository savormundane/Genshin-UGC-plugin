"""Read-only native differences and content-bound, portable modification plans."""
from pathlib import Path
from collections import Counter,defaultdict
from copy import deepcopy
import os
from authoring_io import sha,sha_file,canonical,schema,resolve
from level_inventory import calibrated_container,container,fields,vals
from native_core import model,get,slot,ref,apply
from project_index import build,key


def snapshot(data):
    # Keep the stored plan difference contract stable for existing scene objects.
    index=build(data,include_scene=False,include_gameplay=False);m=model(data);_,root=container(data)
    objects={o['key']:{k:v for k,v in o.items()if k!='sha256'or o['kind']!='document'}for o in index['objects']}
    raw={}
    for g in m['graphs']+m['composite_graphs']:
        scope=(g['kind'],g['id']);raw[key('level','graph',*scope)]=sha(g['raw'])
        for ident,n in g['nodes'].items():
            target=key('level','node',*scope,ident);raw[target]=sha(n)
            # Preserve unparsed carriers verbatim. Known primitive literals are
            # decoded as additional information, never as a replacement for bytes.
            ports=[]
            for p in vals(fields(n),4):
                item={'port':list(slot(p)),'type_id':get(p,4,0),'uid':get(p,7,0)}
                value=get(p,3)
                if value is not None:
                    item['value_bytes']=value.hex()
                    if get(value,1,0)in(1,2,5,6):
                        from native_model import constant
                        item['literal']=constant(value)
                ports.append(item)
            objects[target].update(ports=sorted(ports,key=lambda p:p['port']),version=get(n,9,0,0),
                                   generic_id=ref(get(n,2,default=b'')),concrete_id=ref(get(n,3,default=b'')))
    for ident,d in m['definitions'].items():raw[key('level','definition',ident)]=sha(d)
    for s in m['structs']:raw[key('level','structure',get(get(s,1,default=b''),1,0))]=sha(s)
    for t in m['storage_templates']:raw[key('level','storage_template',get(t,1,0))]=sha(t)
    for r in m['custom_variables']['records']:
        raw[key('level','custom_variable','template'if r['section']==4 else'entity',r['entity_id'],r['name'])]=sha(r['raw'])
    from native_graph_variables import read as graph_variables
    for r in graph_variables(m):raw[key('level','graph_variable',r['graph_kind'],r['graph'],r['name'])]=sha(r['raw'])
    if m['format']=='gil':
        for number,kind in((4,'template'),(5,'entity'),(9,'control'),(50,'script')):
            for section in vals(root,number):
                for item in vals(fields(section),502 if number==9 else 1):
                    raw[key('level',kind,get(item,501 if number==9 else 1,0))]=sha(item)
    else:
        for unit in vals(root,1)+vals(root,2):
            locator=get(unit,1,default=b'')
            raw[key('level','gia_resource',get(locator,2,0,0),get(locator,4,0,0))]=sha(unit)
    # Serialization side is not a different semantic connection.
    references=[]
    for edge in index['references']:
        location={k:v for k,v in edge['location'].items()if k!='serialized_at'}
        references.append({k:edge[k]for k in('source','target','relation')}|{'location':location})
    return index,objects,raw,references


def difference(before,after,allowed=None,*,include_spatial=True,include_points=True,include_gameplay=True,include_gameplay_references=True):
    if allowed is not None and (not isinstance(allowed,list)or any(type(v)!=int or not 1<=v<=536870911 for v in allowed)or len(allowed)!=len(set(allowed))):
        raise ValueError('Unique valid allowed top-level field numbers required')
    bh,bfields=container(before);ah,afields=container(after)
    left,lo,lr,le=snapshot(before);right,ro,rr,re=snapshot(after)
    if left['artifacts']['level']['format']!=right['artifacts']['level']['format']:raise ValueError('Native diff requires the same format')
    def changed(a,b):
        return [{'key':k,'change':'added'if k not in a else'removed'if k not in b else'modified',
                 'before':a.get(k),'after':b.get(k)}for k in sorted(set(a)|set(b))if a.get(k)!=b.get(k)]
    def sections(rows):
        result=defaultdict(list)
        for n,w,v,raw in rows:result[str(n)].append({'wire':w,'sha256':sha(raw),'bytes':len(raw)})
        return dict(result)
    lc=Counter(canonical(e)for e in le);rc=Counter(canonical(e)for e in re)
    import json
    added=[{'reference':json.loads(k),'count':v}for k,v in sorted((rc-lc).items())]
    removed=[{'reference':json.loads(k),'count':v}for k,v in sorted((lc-rc).items())]
    protected=None
    if allowed is not None:
        l=b''.join(raw for n,w,v,raw in bfields if n not in allowed)
        r=b''.join(raw for n,w,v,raw in afields if n not in allowed)
        protected={'allowed_top_level_fields':allowed,'before_sha256':sha(l),'after_sha256':sha(r),
                   'unchanged':l==r and bh[1:4]==ah[1:4]and before[-4:]==after[-4:]}
    result={'schema':2,'kind':'native-diff','before_sha256':sha(before),'after_sha256':sha(after),
            'bytes_equal':before==after,'status':'passed'if right['status']=='passed'and(protected is None or protected['unchanged'])else'failed',
            'validation':{'before':{'status':left['status'],'issues':left['issues'],'unresolved':left['unresolved']},
                          'after':{'status':right['status'],'issues':right['issues'],'unresolved':right['unresolved']}},
            'objects':changed(lo,ro),'references':{'added':added,'removed':removed},'serialized_objects':changed(lr,rr),
            'top_level_fields':changed(sections(bfields),sections(afields)),
            'field_order_changed':[(n,w)for n,w,v,r in bfields]!=[(n,w)for n,w,v,r in afields],
            'envelope':{'before':list(bh[1:4]),'after':list(ah[1:4]),'changed':bh[1:4]!=ah[1:4]},
            'protected':protected,'complete_semantic_diff':False,'unindexed':sorted(set(left['unindexed'])|set(right['unindexed'])),
            'editor':'not_checked','host':'not_checked'}
    if include_spatial and before!=after:
        from native_scene import spatial_objects
        scenes=[{key('level',kind,*((1,) if kind=='gia_resource' else ()),ident):detail
                 for (kind,ident),detail in spatial_objects(header,root).items()}
                for header,root in ((bh,bfields),(ah,afields))]
        changes=changed(*scenes)
        if changes:result['spatial_objects']=changes
    if include_points and bh[3]==2 and ah[3]==2 and [r for n,w,v,r in bfields if n==11]!=[r for n,w,v,r in afields if n==11]:
        from native_scene_settings import point_settings,spawn_references
        points=[]
        for rows in (bfields,afields):
            level=next(iter(vals(rows,11)),b'')
            spawns=spawn_references(level)
            points.append({str(p['point_id']):p for row in vals(fields(get(level,5,default=b'')),1)
                           if (p:=point_settings(row,spawns))['point_id'] is not None})
        changes=changed(*points)
        if changes:result['scene_points']=changes
    if include_gameplay and bh[3]==2 and ah[3]==2 and any(
            r['key'] in ('11','12','15','16') for r in result['top_level_fields']):
        from native_gameplay import config_name
        from level_inventory import unique
        gameplay=[]
        for rows in (bfields,afields):
            records={}
            for r in vals(fields(unique(rows,15,default=b'')),1):
                ident,kind=get(r,1,0),get(r,2,0)
                if ident is not None:
                    records[key('level','resource',kind,ident)]={'kind':kind,'id':ident,'name':config_name(r),'sha256':sha(r)}
            settings=unique(rows,11,default=b'')
            for label,items in (('respawn',get(settings,4,default=b'')),('player_group',get(settings,6,default=b''))):
                for r in vals(fields(items),1):
                    ident=get(r,1,0)
                    if ident is not None:
                        records[key('level',label,ident)]={'id':ident,'sha256':sha(r)}
            for r in vals(fields(unique(rows,12,default=b'')),1):
                name=get(r,1,default=b'').decode('utf-8')
                records[key('level','global_timer',name)]={'name':name,'sha256':sha(r)}
            gameplay.append(records)
        changes=changed(*gameplay)

        if changes:result['gameplay_records']=changes
    if include_gameplay_references and bh[3]==2 and ah[3]==2:
        from native_gameplay_index import build_gameplay
        reports = [build_gameplay(raw) for raw in (before, after)]
        edges = [Counter(canonical(e) for e in report['references']) for report in reports]
        if edges[0] != edges[1]:
            result['gameplay_references'] = {
                'added': [{'reference': json.loads(edge), 'count': count} for edge, count in sorted((edges[1]-edges[0]).items())],
                'removed': [{'reference': json.loads(edge), 'count': count} for edge, count in sorted((edges[0]-edges[1]).items())]}
        for side, report in zip(('before','after'), reports):
            if report['issues']:
                result['validation'][side]['issues'].extend(report['issues'])
                result['validation'][side]['status']='failed'
        if reports[1]['issues']:
            result['status']='failed'
    return result


def fingerprint(plan):
    # Locations may change when a complete input bundle is moved. The operation
    # tokens and content digests, including reviewed differences, stay bound.
    value={k:v for k,v in plan.items()if k not in('plan_sha256','inputs')}
    value['inputs']={k:{'sha256':v['sha256']}for k,v in plan['inputs'].items()}
    return sha(canonical(value).encode('utf-8'))


def operation_sources(op):
    if 'source' in op:
        yield 'source'
    if op['op']=='arrange_instances' and 'previous_bindings' in op:
        yield 'previous_bindings'
    if op['op']=='append_client_ui' and 'asset_data' in op:
        yield 'asset_data'


def arrangements(report):
    return [operation for operation in report['operations'] if operation['op']=='arrange_instances']


def plan(data,spec,base,destination):
    calibrated_container(data)
    operations=spec.get('operations') if isinstance(spec,dict) else None
    if not isinstance(operations,list) or any(not isinstance(op,dict) for op in operations):
        raise ValueError('Native patch must specify operations as a list of objects')
    spec=deepcopy(spec);inputs={};bound=deepcopy(spec)
    destination=Path(destination).resolve()
    for index,op in enumerate(spec['operations']):
        for field in operation_sources(op):
            source=resolve(base,op[field]);token=f'@input:{index}' if field=='source' else f'@input:{index}:{field}'
            location=os.path.relpath(source,destination) if source.drive==destination.drive else str(source)
            inputs[token]={'source':Path(location).as_posix(),'sha256':sha_file(source)}
            bound['operations'][index][field]=token;op[field]=str(source)
    if spec.get('strict_audit',True)is not True:raise ValueError('Modification plans require strict audit')
    output,applied=apply(data,spec,base)
    diff=difference(data,output,spec['allowed_top_level_fields'])
    if diff['status']!='passed':
        from authoring_io import DiagnosticError
        from project_index import write_audit_error

        if not diff['protected']['unchanged']:
            raise DiagnosticError('native.protected_bytes_changed', 'Modification plan protected bytes changed',
                                  phase='result', allowed_top_level_fields=spec['allowed_top_level_fields'])
        raise write_audit_error(diff['validation']['after'], 'result',
                                'Modification plan final reference/protection check failed',
                                code='native.result_reference_failed')
    for item in inputs.values():
        if sha_file(resolve(destination,item['source']))!=item['sha256']:raise ValueError('Plan input changed while reading')
    result={'schema':2,'kind':'native-change-plan','patch':bound,'inputs':inputs,
            'result_sha256':sha(output),'difference':diff}
    if changes:=arrangements(applied):result['arrangements']=changes
    result['plan_sha256']=fingerprint(result)
    return result


def plan_summary(record, destination='plan.json'):
    diff=record['difference']
    result={'schema':2,'kind':record['kind'],'status':diff['status'],'report':str(destination),
            'base_sha256':diff['before_sha256'],'result_sha256':record['result_sha256'],
            'plan_sha256':record['plan_sha256'],'inputs':record['inputs'],
            'checks':{'protected_bytes':diff['protected']['unchanged'],
                      'project_references':diff['validation']['after']['status']},
            'changed_top_level_fields':[int(change['key']) for change in diff['top_level_fields']],
            'diagnostics':diff['validation']['after']['issues']+diff['validation']['after']['unresolved']}
    if 'arrangements' in record:result['arrangements']=record['arrangements']
    return result


def apply_plan(data,record,base):
    calibrated_container(data)
    required=('schema','kind','patch','inputs','result_sha256','difference','plan_sha256')
    schema(record,(*required,'arrangements'),required)
    if record['kind']!='native-change-plan':raise ValueError('Unknown native plan kind')
    if not isinstance(record['inputs'],dict):raise ValueError('Plan inputs must be a token map')
    for token,item in record['inputs'].items():
        schema(item,('source','sha256'),('source','sha256'))
        if not isinstance(token,str)or not token.startswith('@input:')or not isinstance(item['source'],str)or not item['source']:
            raise ValueError('Invalid plan input token/path')
    if fingerprint(record)!=record['plan_sha256']:raise ValueError('Native plan digest mismatch')
    spec=deepcopy(record['patch']);used=set();inputs={}
    if spec.get('strict_audit',True)is not True:raise ValueError('Modification plans require strict audit')
    for op in spec['operations']:
        for field in operation_sources(op):
            token=op[field]
            if token not in record['inputs']:raise ValueError('Unbound native plan input')
            item=record['inputs'][token];source=resolve(base,item['source'])
            if sha_file(source)!=item['sha256']:raise ValueError('Native plan input digest changed: '+token)
            used.add(token);inputs[str(source)]=item['sha256'];op[field]=str(source)
    if used!=set(record['inputs']):raise ValueError('Unused native plan input')
    output,report=apply(data,spec,base)
    if sha(output)!=record['result_sha256']:raise ValueError('Native plan result digest mismatch')
    if arrangements(report)!=record.get('arrangements',[]):raise ValueError('Native plan arrangement preview changed')
    actual=difference(data,output,spec['allowed_top_level_fields'],
                      include_spatial='spatial_objects' in record['difference'],
                      include_points='scene_points' in record['difference'],
                      include_gameplay='gameplay_records' in record['difference'],
                      include_gameplay_references='gameplay_references' in record['difference'])
    if actual['status']!='passed'or actual!=record['difference']:raise ValueError('Native plan difference changed')
    for source,digest in inputs.items():
        if sha_file(source)!=digest:raise ValueError('Native plan input changed during apply')
    report.update(plan_sha256=record['plan_sha256'],inputs=inputs,difference=actual)
    return output,report
