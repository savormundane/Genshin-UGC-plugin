"""Versioned resource metadata with explicit provenance and dependency closure."""
from pathlib import Path
import argparse,json,re
from authoring_io import schema,sha,read_json,resolve
from platform_profiles import selection,CATALOGUE


MODEL_SELECTIONS = ('native_verified', 'preview_only', 'whitebox_recipe')
MODEL_CANDIDATES = Path(__file__).with_name('scene-model-candidates.json')
MEDIA_OBSERVATIONS = Path(__file__).with_name('media-resource-observations.json')
MEDIA_OBSERVATIONS_SHA256 = '430d3f111eaaee0fa7be9a3f9c5fb6862053308a468f983a1dc83bda8a327467'


def media_observations(version, resource_type, inputs):
    """List attributed observations for discovery only."""
    raw = MEDIA_OBSERVATIONS.read_bytes()
    digest = sha(raw)
    if digest != MEDIA_OBSERVATIONS_SHA256:
        raise ValueError('Bundled media resource catalogue source changed')
    data = json.loads(raw)
    _, lineage, _, _ = selection(version)
    inputs[str(MEDIA_OBSERVATIONS)] = digest
    rows = []
    for batch in data['batches']:
        if batch['type'] != resource_type or batch['source']['source_version'] not in lineage:
            continue
        source = {**data['upstream'], **batch['source'], 'sha256': digest,
                  'path': 'scripts/media-resource-observations.json'}
        source_version = source['source_version']
        for ident, name, category, *observed in batch['rows']:
            row = {
                'type': resource_type, 'id': ident, 'name': name, 'category': category,
                'version': source_version, 'requested_version': version,
                'applicability': ('historical_observation' if source_version != version else
                                  'observation_for_requested_version'),
                'mode': None, 'dimensions': None, 'dependencies': None,
                'evidence': 'third_party_editor_observation',
                'native_write_evidence': 'none', 'host': 'not_checked', 'source': source,
            }
            if observed:
                row['reported_duration_s'] = observed[0]
            if len(observed) == 3:
                row['name_truncated'] = observed[1]
                row['source'] = {**source, 'frame_sha256': observed[2]}
            rows.append(row)
    return rows


def model_row(row, directory, version, inputs, samples):
    schema(row, ('type', 'id', 'name', 'category', 'mode', 'dimensions', 'dependencies',
                 'source', 'selection', 'dimensions_source', 'model_id', 'origin', 'preview_url'),
           ('name', 'category', 'mode', 'source', 'selection'))
    selection = row['selection']
    ident = row.get('id')
    if selection not in MODEL_SELECTIONS or row['mode'] not in ('classic', 'beyond', 'both'):
        raise ValueError('Invalid model selection or mode')
    if any(not isinstance(row[key], str) or not row[key].strip() for key in ('name', 'category')):
        raise ValueError('Model name and category must be nonempty')
    if ident is not None and (type(ident) is not int or not 0 < ident <= 0xffffffff):
        raise ValueError('Invalid model template ID')
    if selection == 'native_verified' and (ident is None or row['mode'] == 'both'):
        raise ValueError('A native model sample is bound to one template ID and one observed mode')
    if 'model_id' in row and (type(row['model_id']) is not int or row['model_id'] <= 0):
        raise ValueError('Invalid model ID')
    source = row['source']
    schema(source, ('path', 'sha256', 'line', 'url'), ('path', 'sha256'))
    path = resolve(directory, source['path'])
    if path not in samples:
        raw = path.read_bytes()
        samples[path] = (sha(raw), raw)
    digest, raw = samples[path]
    if digest != source['sha256']:
        raise ValueError('Model source digest mismatch')
    inputs[str(path)] = digest
    if selection == 'native_verified':
        from miliastra.native.scene import static_objects

        key = (path, digest)
        if key not in samples:
            samples[key] = {record['template_id'] for record in static_objects(raw)}
        if ident not in samples[key]:
            raise ValueError('Model template is absent from native static sample: ' + str(ident))
    elif 'line' in source and (type(source['line']) is not int
                              or not 1 <= source['line'] <= len(raw.decode('utf-8-sig').splitlines())):
        raise ValueError('Model source line absent')
    dims = row.get('dimensions')
    if dims is not None:
        from miliastra.native.scene import vector

        dims = vector(dims, 'Model dimensions')
        if min(dims) < 0:
            raise ValueError('Model dimensions must be nonnegative')
    dimensions_evidence = 'not_checked'
    if 'dimensions_source' in row:
        from miliastra.native.scene import vector

        evidence = row['dimensions_source']
        schema(evidence, ('path', 'sha256'), ('path', 'sha256'))
        measurement_path = resolve(directory, evidence['path'])
        measurement_raw = measurement_path.read_bytes()
        measurement_hash = sha(measurement_raw)
        if measurement_hash != evidence['sha256']:
            raise ValueError('Model dimension source digest mismatch')
        measurement = json.loads(measurement_raw.decode('utf-8-sig'))
        if (not isinstance(measurement, dict) or type(measurement.get('template_id')) is not int
                or measurement['template_id'] != ident
                or vector(measurement.get('dimensions_m'), 'Measured model dimensions') != dims):
            raise ValueError('Model dimensions differ from their measurement record')
        inputs[str(measurement_path)] = measurement_hash
        dimensions_evidence = 'matching_measurement_record_only'
        method = measurement.get('method')
        if (selection == 'native_verified' and measurement.get('sample_sha256') == digest
                and measurement.get('version') == version and measurement.get('mode') == row['mode']
                and isinstance(method, str) and method.strip()):
            dimensions_evidence = 'sample_bound_measurement_record'
    deps = row.get('dependencies')
    if deps is not None and (not isinstance(deps, list) or any(
        not isinstance(d, dict) or set(d) != {'type', 'id'}
        or not isinstance(d['type'], str) or type(d['id']) is not int for d in deps
    )):
        raise ValueError('Invalid model dependencies')
    return {
        **row, 'id': ident, 'dimensions': dims, 'dependencies': deps, 'version': version,
        'source': {**source, 'path': str(path)}, 'dimensions_evidence': dimensions_evidence,
        'dimensions_verified': dimensions_evidence == 'sample_bound_measurement_record',
        'evidence': 'native_static_record' if selection == 'native_verified' else 'declared',
        'target_metadata': 'caller_declared' if selection == 'native_verified' else 'candidate',
    }


def catalogue(version, extensions=(), *, include_model_candidates=False):
    samples = {}
    index, _, documents, digest = selection(version)
    document = documents['mh4imrrhzdzi']
    characters = index['character_ids'][document['source_version']]
    if characters['source_sha256'] != document['source_sha256'] or not characters['rows']:
        raise ValueError('Character IDs differ from the recorded document source')
    inputs = {str(CATALOGUE.resolve()): digest}
    provenance = {k: document[k] for k in ('path', 'sha256', 'source_kind', 'source_version',
                   'source_sha256', 'inherited', 'applicability', 'mirror_url', 'commit') if k in document}
    rows = [
        {'type':'character','id':ident,'name':name,'version':version,'mode':'classic',
         'dimensions':None,'dependencies':None,'evidence':'documented',
         'source':{**provenance, 'source_line':line, 'url':document['official_url']}}
        for ident, name, line in characters['rows']
    ]
    for filename in extensions:
        path=Path(filename).resolve();raw=path.read_bytes();spec=json.loads(raw.decode('utf-8-sig'));inputs[str(path)]=sha(raw)
        schema(spec,('schema','version','resources'),('version','resources'))
        if spec['version']!=version:raise ValueError('Resource catalogue version mismatch')
        if not isinstance(spec['resources'],list):raise ValueError('Resource rows required')
        for row in spec['resources']:
            if isinstance(row, dict) and row.get('type') == 'model':
                rows.append(model_row(row, path.parent, version, inputs, samples))
                continue
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
    if include_model_candidates:
        raw = MODEL_CANDIDATES.read_bytes()
        inputs[str(MODEL_CANDIDATES)] = sha(raw)
        existing = {row['id'] for row in rows if row['type'] == 'model' and row['id'] is not None}
        for model in json.loads(raw):
            if model.get('id') not in existing:
                rows.append({
                    **model, 'type': 'model', 'id': model.get('id'), 'mode': None,
                    'dimensions': None, 'dependencies': None, 'candidate_for_version': version,
                    'evidence': 'declared', 'dimensions_evidence': 'not_checked', 'dimensions_verified': False,
                })
    seen=set()
    for row in rows:
        identity=(row['type'],row['id'] if row['id'] is not None else row['name'])
        if identity in seen:raise ValueError('Duplicate resource identity: '+str(identity))
        seen.add(identity)
    for row in rows:
        if row['dependencies']is not None:
            deps=[(d['type'],d['id'])for d in row['dependencies']]
            if len(deps)!=len(set(deps)):raise ValueError('Duplicate resource dependency')
            if set(deps)-seen:raise ValueError('Missing resource dependency')
    return {'schema':2,'version':version,'resources':sorted(rows,key=lambda r:(r['type'],r['id'] is None,r['id'] or 0,r['name'])),'inputs':inputs,
            'scope':('versioned_resource_metadata_and_model_candidates' if include_model_candidates else
                     'documented_characters_and_explicit_resource_metadata'),'complete_platform_catalogue':False,'host':'not_checked'}


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
            if row['evidence']=='declared'and (row['type']=='model' or not use.get('accept_declared',False)):unknown.append({**record,'error':'resource metadata only declared'})
            if identity==(use['type'],use['id'])and 'dimensions'in use:
                if row['dimensions']is None:unknown.append({**record,'error':'resource dimensions unknown'})
                elif row['type']=='model' and not row['dimensions_verified']:
                    unknown.append({**record,'error':'model dimensions lack a sample-bound measurement record'})
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


def search(version, query='', resource_type=None, mode=None, catalogues=(), limit=None):
    if mode not in (None, 'classic', 'beyond'):
        raise ValueError('Resource search mode must be classic or beyond')
    if not isinstance(query, str) or type(limit) not in (int, type(None)) or limit is not None and limit < 1:
        raise ValueError('Resource search requires a string and a positive limit')
    result = catalogue(version, catalogues, include_model_candidates=resource_type == 'model')
    media = resource_type in ('sound', 'effect')
    if media:
        existing = {(row['type'], row['id']) for row in result['resources']}
        observations = media_observations(version, resource_type, result['inputs'])
        result['resources'].extend(row for row in observations if (row['type'], row['id']) not in existing)
        result['scope'] = 'resource_metadata_and_editor_observations'
    terms = query.casefold().split() if media else [query.casefold()]
    exact_id = media and len(terms) == 1 and re.fullmatch(r'[0-9]+', terms[0]) is not None
    matches = [
        row for row in result['resources']
        if (resource_type is None or row['type'] == resource_type)
        and (mode is None or row['mode'] in (None, mode, 'both'))
        and (str(row['id']) == terms[0] if exact_id else all(
            term in ' '.join(str(row.get(key) or '') for key in ('name', 'id', 'type', 'category')).casefold()
            for term in terms
        ))
    ]
    if media:
        matches.sort(key=lambda row: (row['version'] != version, row['id']))
    result['resources'] = matches[:limit]
    result['matches'] = len(matches)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    query=sub.add_parser('search');query.add_argument('query',nargs='?',default='');query.add_argument('--version',required=True);query.add_argument('--catalogue',action='append',default=[])
    query.add_argument('--type',dest='resource_type');query.add_argument('--mode',choices=['classic','beyond']);query.add_argument('--limit',type=int)
    verify=sub.add_parser('check');verify.add_argument('spec');verify.add_argument('--out')
    args=parser.parse_args(argv)
    if args.operation=='search':
        result=search(args.version,args.query,args.resource_type,args.mode,args.catalogue,args.limit)
    else:
        result=check(args.spec)
        if args.out:
            with Path(args.out).open('x',encoding='utf-8')as output:json.dump(result,output,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False));return 0 if result.get('status','passed')=='passed'else 1
