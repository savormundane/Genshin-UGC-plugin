"""Deterministic, artifact-bound allocation of explicitly scoped native IDs."""
from pathlib import Path
import argparse,json
from authoring_io import schema,sha,canonical,read_json,output_directory,finish,write_json
from project_index import build


def plan(data,spec):
    schema(spec,('schema','base_sha256','namespaces','reservations','requests','remap'),('base_sha256','namespaces','requests'))
    if sha(data)!=spec['base_sha256']:raise ValueError('Base hash mismatch')
    for field in ('namespaces','requests','reservations','remap'):
        if not isinstance(spec.get(field,[]),list):raise ValueError('Expected list: '+field)
    index=build(data)
    if index['issues']:raise ValueError('Cannot allocate IDs in an invalid object index')
    spaces={};occupied={};owners=set();reservations=[]
    # Namespace names describe ownership. They do not split native identity domains.
    for item in index['objects']:
        if type(item['id'])is int:
            occupied.setdefault((item['kind'],tuple(item['scope'])),set()).add(item['id'])
    for space in spec['namespaces']:
        schema(space,('name','kind','scope','minimum','maximum'),('name','kind','scope','minimum','maximum'))
        if not isinstance(space['name'],str)or not space['name']or space['name']in spaces:raise ValueError('Unique namespace name required')
        if space['kind']not in ('node','graph','definition','structure','template','entity','control','script','storage_template','storage_slot'):raise ValueError('Unsupported native identity kind')
        scope=space['scope']
        if not isinstance(scope,list)or any(type(v)not in(str,int)for v in scope):raise ValueError('Invalid identity scope')
        if space['kind']=='node':
            if len(scope)!=2 or scope[0]not in('ordinary','composite')or type(scope[1])is not int:raise ValueError('Node scope requires graph kind and ID')
        elif space['kind']=='graph':
            if len(scope)!=1 or scope[0]not in('ordinary','composite'):raise ValueError('Graph scope requires graph kind')
        elif space['kind']=='storage_slot':
            if len(scope)!=1 or type(scope[0])is not int:raise ValueError('Storage slot scope requires template ID')
        elif scope:raise ValueError('Identity kind is not scoped')
        if any(type(space[k])is not int for k in('minimum','maximum'))or not 0<=space['minimum']<=space['maximum']<=4294967295:raise ValueError('Invalid uint32 allocation range')
        spaces[space['name']]=space
    for item in spec.get('reservations',[]):
        schema(item,('namespace','name','id'),('namespace','name','id'))
        space=spaces.get(item['namespace'])
        if space is None:raise ValueError('Unknown reservation namespace')
        ident=item['id'];owner=(item['namespace'],item['name'])
        if not isinstance(item['name'],str)or not item['name']or owner in owners:raise ValueError('Duplicate/invalid reservation name')
        if type(ident)is not int or not space['minimum']<=ident<=space['maximum']:raise ValueError('Reservation outside range')
        domain=(space['kind'],tuple(space['scope']));used=occupied.setdefault(domain,set())
        if ident in used:raise ValueError('Reservation collides with native object or reservation')
        used.add(ident);owners.add(owner);reservations.append(dict(item))
    allocated=[]
    for item in spec['requests']:
        schema(item,('namespace','name','id'),('namespace','name'))
        space=spaces.get(item['namespace']);owner=(item['namespace'],item['name'])
        if space is None:raise ValueError('Unknown allocation namespace')
        if not isinstance(item['name'],str)or not item['name']or owner in owners:raise ValueError('Duplicate/invalid allocation name')
        domain=(space['kind'],tuple(space['scope']));used=occupied.setdefault(domain,set())
        ident=item.get('id',space['minimum'])
        if type(ident)is not int or not space['minimum']<=ident<=space['maximum']:raise ValueError('Requested ID outside range')
        if 'id'in item:
            if ident in used:raise ValueError('Requested ID already occupied')
        else:
            while ident in used and ident<=space['maximum']:ident+=1
            if ident>space['maximum']:raise ValueError('ID namespace capacity exhausted')
        used.add(ident);owners.add(owner)
        allocated.append({'namespace':item['namespace'],'name':item['name'],'id':ident,'kind':space['kind'],'scope':space['scope']})
    if not allocated:raise ValueError('At least one ID request required')
    result={'schema':2,'kind':'native-id-allocation','base_sha256':sha(data),'spec':spec,'allocations':allocated,
            'reservations':reservations,'complete_reference_index':False,'unresolved':index['unresolved'],
            'scope':'allocate_against_indexed_native_identities','native_modified':False}
    if spec.get('remap'):
        from native_changes import plan as native_plan
        operations=[];selected=set();used_allocations=set()
        for item in spec['remap']:
            schema(item,('graph_kind','graph_id','nodes'),('graph_kind','graph_id','nodes'))
            identity=(item['graph_kind'],item['graph_id'])
            if identity in selected:raise ValueError('Duplicate remap graph')
            selected.add(identity);mapping=[]
            if not isinstance(item['nodes'],list)or not item['nodes']:raise ValueError('Remap nodes required')
            for entry in item['nodes']:
                schema(entry,('from','namespace','name'),('from','namespace','name'))
                candidates=[a for a in allocated if a['namespace']==entry['namespace']and a['name']==entry['name']]
                if len(candidates)!=1:raise ValueError('Unique allocated remap target required')
                target=candidates[0];owner=(target['namespace'],target['name'])
                if target['kind']!='node'or target['scope']!=list(identity):raise ValueError('Remap target namespace scope mismatch')
                if owner in used_allocations:raise ValueError('Allocated target reused')
                used_allocations.add(owner);mapping.append({'from':entry['from'],'to':target['id']})
            operations.append({'op':'remap_nodes','graph_kind':item['graph_kind'],'graph_id':item['graph_id'],'mapping':mapping})
        patch={'schema':2,'base_sha256':sha(data),'allowed_top_level_fields':[10],'operations':operations}
        result['native_plan']=native_plan(data,patch,Path.cwd(),Path.cwd())
        result['native_modified']=True
    result['plan_sha256']=sha(canonical(result).encode())
    return result


def apply(data,record):
    schema(record,('schema','kind','base_sha256','spec','allocations','reservations','complete_reference_index','unresolved','scope','native_modified','plan_sha256','native_plan'),
           ('kind','base_sha256','spec','allocations','reservations','complete_reference_index','unresolved','scope','native_modified','plan_sha256'))
    unsigned={k:v for k,v in record.items()if k!='plan_sha256'}
    if sha(canonical(unsigned).encode())!=record['plan_sha256']:raise ValueError('ID plan digest mismatch')
    expected=plan(data,record['spec'])
    if canonical(expected)!=canonical(record):raise ValueError('ID plan differs from current allocation')
    return {'schema':2,'kind':'native-id-registry','base_sha256':sha(data),'plan_sha256':record['plan_sha256'],
            'allocations':record['allocations'],'reservations':record['reservations'],'native_modified':record['native_modified'],
            'editor':'not_checked','host':'not_checked'}


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    for name in('plan','apply'):
        command=sub.add_parser(name);command.add_argument('input');command.add_argument('spec');command.add_argument('--out',required=True)
    args=parser.parse_args(argv);source=Path(args.input).resolve();config=Path(args.spec).resolve()
    raw=source.read_bytes();document=read_json(config);inputs={str(source):sha(raw),str(config):sha(config.read_bytes())}
    result=plan(raw,document)if args.operation=='plan'else apply(raw,document)
    with output_directory(args.out)as stage:
        write_json(stage/('plan.json'if args.operation=='plan'else'registry.json'),result)
        record=result if args.operation=='plan'else document
        if 'native_plan'in record:
            write_json(stage/'native-plan.json',record['native_plan'])
            if args.operation=='apply':
                from native_changes import apply_plan
                changed,applied=apply_plan(raw,record['native_plan'],config.parent)
                (stage/'level.gil').write_bytes(changed);write_json(stage/'native-report.json',applied)
        report=finish(stage,inputs,kind='native-ids-'+args.operation,native_modified=args.operation=='apply'and record['native_modified'])
    print(json.dumps(report,ensure_ascii=False));return 0
