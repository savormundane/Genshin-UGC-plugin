"""Versioned resource metadata with explicit provenance and dependency closure."""
from pathlib import Path
import argparse,json,re
from authoring_io import schema,sha,read_json,resolve
from platform_profiles import show,CATALOGUE


def catalogue(version,extensions=()):
    document=show(version,'mh4imrrhzdzi');rows=[];inputs={str((Path(__file__).resolve().parents[1]/document['path']).resolve()):document['sha256'],str(CATALOGUE.resolve()):sha(CATALOGUE.read_bytes())}
    for number,line in enumerate(document['content'].splitlines(),1):
        match=re.fullmatch(r'\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|',line)
        if match:
            rows.append({'type':'character','id':int(match[1]),'name':match[2],'version':version,'mode':'classic',
                         'dimensions':None,'dependencies':None,'evidence':'documented',
                         'source':{'path':document['path'],'sha256':document['sha256'],'line':number,'url':document['official_url'],
                                   'source_version':document['source_version'],'inherited':document['inherited']}})
    if not rows:raise ValueError('Character catalogue source table absent')
    for filename in extensions:
        path=Path(filename).resolve();raw=path.read_bytes();spec=read_json(path);inputs[str(path)]=sha(raw)
        schema(spec,('schema','version','resources'),('version','resources'))
        if spec['version']!=version:raise ValueError('Resource catalogue version mismatch')
        if not isinstance(spec['resources'],list):raise ValueError('Resource rows required')
        for row in spec['resources']:
            schema(row,('type','id','name','mode','dimensions','dependencies','source'),('type','id','name','mode','dimensions','dependencies','source'))
            if row['type']not in('character','image','template','sound','effect','item','equipment','skill','unit_status','faction','currency'):raise ValueError('Unsupported resource type')
            if type(row['id'])is not int or row['id']<0 or not isinstance(row['name'],str)or not row['name']:raise ValueError('Invalid resource identity')
            if row['mode']not in('classic','beyond','both'):raise ValueError('Invalid resource mode')
            dims=row['dimensions']
            if dims is not None and (not isinstance(dims,list)or len(dims)not in(2,3)or any(type(v)is not int or v<=0 for v in dims)):raise ValueError('Invalid resource dimensions')
            deps=row['dependencies']
            if deps is not None and (not isinstance(deps,list)or any(not isinstance(d,dict)or set(d)!={'type','id'}or not isinstance(d['type'],str)or type(d['id'])is not int for d in deps)):raise ValueError('Invalid resource dependencies')
            source=row['source'];schema(source,('path','sha256','line'),('path','sha256','line'))
            source_path=resolve(path.parent,source['path']);source_raw=source_path.read_bytes()
            if sha(source_raw)!=source['sha256']:raise ValueError('Resource provenance digest mismatch')
            if type(source['line'])is not int or not 1<=source['line']<=len(source_raw.decode('utf-8-sig').splitlines()):raise ValueError('Resource provenance line absent')
            inputs[str(source_path)]=sha(source_raw)
            rows.append({**row,'version':version,'evidence':'declared','source':{**source,'path':str(source_path)}})
    seen=set()
    for row in rows:
        identity=(row['type'],row['id'])
        if identity in seen:raise ValueError('Duplicate resource identity: '+str(identity))
        seen.add(identity)
    for row in rows:
        if row['dependencies']is not None:
            deps=[(d['type'],d['id'])for d in row['dependencies']]
            if len(deps)!=len(set(deps)):raise ValueError('Duplicate resource dependency')
            if set(deps)-seen:raise ValueError('Missing resource dependency')
    return {'schema':2,'version':version,'resources':sorted(rows,key=lambda r:(r['type'],r['id'])),'inputs':inputs,
            'scope':'documented_characters_and_explicit_resource_metadata','complete_platform_catalogue':False,'host':'not_checked'}


def check(path):
    path=Path(path).resolve();spec=read_json(path)
    schema(spec,('schema','version','mode','catalogues','uses','check_client'),('version','mode','uses'))
    if 'check_client'in spec and type(spec['check_client'])is not bool:raise ValueError('check_client must be boolean')
    if spec['mode']not in('classic','beyond'):raise ValueError('Resource usage mode required')
    if not isinstance(spec.get('catalogues',[]),list)or not isinstance(spec['uses'],list)or not spec['uses']:raise ValueError('Resource usage list required')
    result=catalogue(spec['version'],[resolve(path.parent,p)for p in spec.get('catalogues',[])])
    rows={(r['type'],r['id']):r for r in result['resources']};checks=[];errors=[];unknown=[]
    for use in spec['uses']:
        schema(use,('type','id','dimensions','require_dependencies','accept_declared'),('type','id'))
        if not isinstance(use['type'],str)or type(use['id'])is not int:raise ValueError('Invalid resource usage identity')
        for option in('require_dependencies','accept_declared'):
            if option in use and type(use[option])is not bool:raise ValueError('Resource usage option must be boolean')
        queue=[(use['type'],use['id'])];visited=set();closure=[]
        while queue:
            identity=queue.pop(0)
            if identity in visited:continue
            visited.add(identity);row=rows.get(identity);record={'type':identity[0],'id':identity[1]}
            if row is None:errors.append({**record,'error':'resource absent'});continue
            closure.append(record)
            if row['mode']not in(spec['mode'],'both'):errors.append({**record,'error':'mode mismatch'})
            if row['evidence']=='declared'and not use.get('accept_declared',False):unknown.append({**record,'error':'resource metadata only declared'})
            if identity==(use['type'],use['id'])and 'dimensions'in use:
                if row['dimensions']is None:unknown.append({**record,'error':'resource dimensions unknown'})
                elif row['dimensions']!=use['dimensions']:errors.append({**record,'error':'resource dimensions mismatch'})
            if use.get('require_dependencies',False)and row['dependencies']is None:unknown.append({**record,'error':'dependency completeness unknown'})
            queue.extend((d['type'],d['id'])for d in row['dependencies']or[])
        checks.append({'request':use,'closure':closure})
    result.update(status='failed'if errors else'not_checked'if unknown else'passed',checks=checks,errors=errors,unresolved=unknown,
                  artifact_references_verified=False,check_client=spec.get('check_client',False))
    result['inputs'][str(path)]=sha(path.read_bytes())
    for filename,digest in result['inputs'].items():
        if sha(Path(filename).read_bytes())!=digest:raise ValueError('Resource input changed')
    return result


def check_client(report,resources):
    """Use already source-bound API facts; never scan strings or execute Lua."""
    sources={'StaticReference':'image','Item':'item','Equipment':'equipment','Skill':'skill',
             'UnitStatus':'unit_status','Faction':'faction','Currency':'currency','Prefab':'template'}
    allowed={(c['request']['type'],c['request']['id'])for c in resources['checks']}
    errors=[];unknown=[];references=[]
    for script in report['scripts']:
        api=script.get('api')
        if api is None:
            unknown.append({'mapping':script['mapping'],'error':'source-bound API analysis absent'});continue
        if api['status']!='passed':
            unknown.append({'mapping':script['mapping'],'error':'API analysis incomplete'})
        for call in api['calls']:
            if (call['owner'],call['name'])!=('ClientUIImageControl','SetImage'):continue
            location={'mapping':script['mapping'],'body_sha256':script['body_sha256'],'line':call['line'],'range':call['range'],'operation':'SetImage'}
            args=call['arguments'];source=args[0]if args else None;ident=args[1]if len(args)>1 else None
            kind=sources.get(source.get('value'))if source and source.get('enum')=='Enum.ImageSource'else None
            value=ident.get('value')if ident else None
            if kind is None or type(value)is not int:
                item={**location,'resolution':'dynamic','error':'image source or resource ID unresolved'};unknown.append(item)
            elif (kind,value)not in allowed:
                item={**location,'type':kind,'id':value,'resolution':'undeclared','error':'resource missing from explicit uses'};errors.append(item)
            else:item={**location,'type':kind,'id':value,'resolution':'declared_and_checked'}
            references.append(item)
    if resources['status']!='passed':errors.append({'error':'resource contract has not passed'})
    return {'schema':2,'status':'failed'if errors else'not_checked'if unknown else'passed',
            'scope':'resolved_client_SetImage_calls','input_sha256':report['input_sha256'],
            'references':references,'errors':errors,'unresolved':unknown,'complete_reference_index':False,
            'native_resource_references':'not_checked','editor':'not_checked','host':'not_checked'}


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    query=sub.add_parser('search');query.add_argument('query',nargs='?',default='');query.add_argument('--version',required=True);query.add_argument('--catalogue',action='append',default=[])
    verify=sub.add_parser('check');verify.add_argument('spec');verify.add_argument('--out')
    args=parser.parse_args(argv)
    if args.operation=='search':
        result=catalogue(args.version,args.catalogue);result['resources']=[r for r in result['resources']if args.query.casefold()in(r['name']+' '+str(r['id'])+' '+r['type']).casefold()]
    else:
        result=check(args.spec)
        if args.out:
            with Path(args.out).open('x',encoding='utf-8')as output:json.dump(result,output,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False));return 0 if result.get('status','passed')=='passed'else 1
