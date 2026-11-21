"""Source-bound knowledge queries. Documentation authority is not host evidence."""
from pathlib import Path
import argparse,json
from authoring_io import PLUGIN,read_json,sha

REGISTRY=PLUGIN/'scripts/knowledge-sources.json'

def sources():
    registry=read_json(REGISTRY)
    if registry.get('schema')!=1:raise ValueError('Unknown knowledge registry schema')
    result={}
    for key,row in registry['sources'].items():
        path=(PLUGIN/row['path']).resolve()
        if not path.is_relative_to(PLUGIN.resolve()):raise ValueError('Knowledge source outside plugin')
        actual=sha(path.read_bytes()) if path.is_file() else None
        result[key]={**row,'integrity':'passed' if actual==row['sha256'] else 'failed',
                     'actual_sha256':actual,'editor':'not_checked','host':'not_checked'}
    return result

def client_catalogue(source=None):
    from client_api_catalogue import catalogue
    if source is None:source=sources()['client_api']
    if source['integrity']!='passed':raise ValueError('Client API source changed; review source registry before use')
    parsed=catalogue(PLUGIN/source['path'])
    if parsed['sha256']!=source['sha256']:raise ValueError('Client API source changed during parsing')
    return parsed,source


def api(symbol):
    if not isinstance(symbol,str) or not symbol.strip():raise ValueError('Nonempty API symbol required')
    cat,source=client_catalogue();matches=[]
    for name,row in cat['methods'].items():
        if name==symbol or symbol.casefold() in name.casefold():
            basis=row['parameter_basis']+[row['return_basis']]
            matches.append({'symbol':name,**row,'source':source,'knowledge_status':'unknown' if 'unknown'in basis else 'derived' if 'derived'in basis else 'documented'})
    for owner,fields in cat['fields'].items():
        for name,row in fields.items():
            qualified=owner+'.'+name
            if qualified==symbol or symbol.casefold() in qualified.casefold():matches.append({'symbol':qualified,**row,'source':source,'knowledge_status':'documented'})
    for name,values in cat['enums'].items():
        if symbol.casefold() in name.casefold():matches.append({'symbol':name,'values':values,'source':source,'knowledge_status':'documented'})
    for name,row in cat['callbacks'].items():
        if symbol.casefold() in name.casefold():matches.append({'symbol':name,**row,'source':source,'knowledge_status':'documented','kind':'lifecycle_callback'})
    exact=[r for r in matches if r['symbol']==symbol]
    return {'schema':1,'status':'passed' if matches else 'not_checked','query':symbol,'matches':exact or matches[:20],
            'conflicts':[c for c in read_json(REGISTRY)['conflicts'] if any(symbol.casefold() in x.casefold() or x.casefold() in symbol.casefold() for x in c['symbols'])],
            'scope':'bundled API contract; documented is not editor or host verified','editor':'not_checked','host':'not_checked'}

def snapshot():
    records=sources()
    if any(r['integrity']!='passed' for r in records.values()):raise ValueError('Knowledge source changed; review registry before snapshot')
    return {'schema':1,'kind':'knowledge_snapshot','sources':records,
            'client_api':client_catalogue(records['client_api'])[0],
            'scope':'bundled source snapshot; no new official, editor or host verification'}

def difference(before,after):
    from authoring_io import schema
    from capability_index import OWNERS
    old,new=read_json(before),read_json(after)
    for value in (old,new):
        schema(value,('schema','kind','sources','client_api','scope'),('kind','sources','client_api'),version=1)
        if value['kind']!='knowledge_snapshot' or not isinstance(value['sources'],dict):raise ValueError('Expected knowledge snapshot')
        if not isinstance(value['client_api'],dict) or any(not isinstance(value['client_api'].get(k),dict)for k in ('methods','fields','enums','callbacks')):raise ValueError('Invalid API snapshot catalogue')
    changed_sources=sorted(k for k in old['sources'].keys()|new['sources'].keys() if old['sources'].get(k)!=new['sources'].get(k))
    # Location/wording changes are source changes, not automatic signature breaks.
    metadata={'line','type_source_lines','description'}
    def contracts(value):
        result={}
        for group in ('methods','enums','callbacks'):
            for name,row in value[group].items():result[group+':'+name]={k:v for k,v in row.items()if k not in metadata} if isinstance(row,dict)else row
        for owner,fields in value['fields'].items():
            for name,row in fields.items():result['fields:'+owner+'.'+name]={k:v for k,v in row.items()if k not in metadata}
        return result
    left,right=contracts(old['client_api']),contracts(new['client_api'])
    added=sorted(right.keys()-left.keys());removed=sorted(left.keys()-right.keys())
    changed=sorted(k for k in left.keys()&right.keys()if left[k]!=right[k])
    affected=set()
    if added or removed or changed or 'client_api'in changed_sources:affected.update(('knowledge','ui','assembly','simulation','protocol','storage'))
    if 'platform_catalogue'in changed_sources:affected.update(('platform','project','native'))
    if 'pixels'in changed_sources:affected.update(('asset_inspection','native_assets'))
    if set(changed_sources)-{'client_api','platform_catalogue','pixels'}:affected.update(OWNERS)
    suites={'test_knowledge_diagnosis.py','test_v36_architecture.py'} if affected else set()
    if affected&{'ui','assembly','protocol','storage'}:suites.update(('test_client_api.py','test_client_check.py','test_client_protocol.py','test_storage_v3.py'))
    if 'platform'in affected:suites.update(('test_platform_profiles.py','test_platform_native.py'))
    if 'native_assets'in affected:suites.update(('test_asset_pipeline.py','test_native_asset_layers.py'))
    return {'schema':1,'changed_sources':changed_sources,'api':{'added':added,'removed':removed,'changed':changed},
            'affected_capabilities':sorted(affected),'suggested_suites':sorted(suites),
            'compatibility':'review_required' if removed or changed or changed_sources or added else 'unchanged',
            'before_sha256':sha(Path(before).read_bytes()),'after_sha256':sha(Path(after).read_bytes()),
            'checks_executed':False,'editor':'not_checked','host':'not_checked',
            'scope':'review aid; semantic changes require source review; use docs diff for platform bodies'}

def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='operation',required=True)
    q=sub.add_parser('api');q.add_argument('symbol');sub.add_parser('sources');sub.add_parser('snapshot')
    diff=sub.add_parser('diff');diff.add_argument('before');diff.add_argument('after')
    a=p.parse_args(argv)
    result=api(a.symbol) if a.operation=='api' else snapshot() if a.operation=='snapshot' else difference(a.before,a.after) if a.operation=='diff' else {'schema':1,'sources':sources()}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
