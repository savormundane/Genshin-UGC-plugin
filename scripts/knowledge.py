"""Source-bound knowledge queries. Documentation authority is not host evidence."""
from difflib import SequenceMatcher
from pathlib import Path
from unicodedata import normalize
import argparse,json,re
from authoring_io import PLUGIN,read_json,sha

REGISTRY=PLUGIN/'scripts/knowledge-sources.json'
HAN = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]+')
FORMAL_NAME = re.compile(r'[a-z_][a-z_0-9]*(?:\.[a-z_][a-z_0-9]*)*')
BUTTON_CLICK = ('按钮点击', '点击按钮', '按钮被点击', '点按钮', '监听按钮', '绑定点击', '点击事件')
AREA_CLICK = ('点击区域', '区域点击')
API_ALIASES = {
    'ClientUIPresetButtonControl.AddCursorEventListener': BUTTON_CLICK,
    'ClientUICursorEventAreaControl.AddCursorEventListener': AREA_CLICK,
    'Enum.CursorEventType.CursorClick': BUTTON_CLICK + AREA_CLICK,
    'ClientUIBaseControl.SetVisible': ('隐藏控件', '隐藏界面', '显示控件', '显示界面', '控件显隐', '显示隐藏'),
    'ClientUIBaseControl.SetActive': ('停用控件', '禁用控件', '激活控件'),
    'ClientUIBaseControl.SetAnchoredPosition': ('设置位置', '设置控件位置', '移动控件', '改控件位置'),
    'ClientUIBaseControl.AddKeyEventListener': ('监听按键', '按键事件', '注册按键'),
    'Script.RegisterServerSignalHandler': ('监听服务器信号', '接收服务器信号', '监听服务端信号', '接收服务端信号'),
}
MATCH_BASES = ('symbol_exact', 'symbol_mention', 'alias', 'description', 'symbol_fragment')

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

def client_catalogue(source=None, *, include_search_details=False):
    from miliastra.client.api_catalogue import catalogue
    if source is None:source=sources()['client_api']
    if source['integrity']!='passed':raise ValueError('Client API source changed; review source registry before use')
    parsed=catalogue(PLUGIN/source['path'], include_search_details=include_search_details)
    if parsed['sha256']!=source['sha256']:raise ValueError('Client API source changed during parsing')
    return parsed,source


def api(symbol):
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError('Nonempty API query required')
    cat, source = client_catalogue(include_search_details=True)
    query = normalize('NFKC', symbol).strip().casefold().replace(':', '.')
    han = HAN.findall(query)
    names = set(FORMAL_NAME.findall(query)) if han else set()
    member_names = names | {query}
    phrases = {phrase for phrase in han if len(phrase) >= 4}
    short = han[0] if len(han) == 1 and not names and 2 <= len(han[0]) <= 3 else ''

    def score(name, description, member=None):
        key = name.casefold()
        if key == query:
            return 0, 0
        if key in names or (member and member.casefold() in member_names):
            return 1, 0
        if not han:
            return (4, 0) if member is None and query in key else None
        alias_length = max((len(phrase) for phrase in API_ALIASES.get(name, ()) if phrase in query), default=0)
        if alias_length:
            return 2, -alias_length
        if not description:
            return None
        if short and short in description:
            return 3, -len(short)
        span = max((SequenceMatcher(None, phrase, description, autojunk=False).find_longest_match().size
                    for phrase in phrases), default=0)
        return (3, -span) if span >= 4 else None

    entries = {}
    for name, row in cat['methods'].items():
        basis = row['parameter_basis'] + [row['return_basis']]
        status = 'unknown' if 'unknown' in basis else 'derived' if 'derived' in basis else 'documented'
        entries[name] = {**row, 'knowledge_status': status}
    entries.update((f'{owner}.{name}', {**row, 'knowledge_status': 'documented'})
                   for owner, fields in cat['fields'].items() for name, row in fields.items())
    entries.update((name, {'values': values, 'knowledge_status': 'documented'}) for name, values in cat['enums'].items())
    entries.update((name, {**row, 'knowledge_status': 'documented', 'kind': 'lifecycle_callback'})
                   for name, row in cat['callbacks'].items())

    ranked = []
    for name, row in entries.items():
        rank = score(name, row.get('description'))
        if name in cat['enum_members']:
            members = cat['enum_members'][name]
            hits = []
            for member in members:
                value = member['value']
                member_rank = score(f'{name}.{value}', member['description'], value)
                if member_rank is not None:
                    hits.append((member_rank, member))
            hits.sort(key=lambda item: (item[0], item[1]['line']))
            row['line'] = members[0]['line']
            if hits:
                member_rank, best = hits[0]
                rank = member_rank if rank is None else min(rank, member_rank)
                row.update(line=best['line'], description=best['description'],
                           matched_values=[member for _, member in hits[:3]])
        if rank is not None:
            description = row.get('description')
            ranked.append((rank, {**row, 'symbol': name, 'source': source,
                                  'description': None if description in ('', '-', '—') else description,
                                  'match_basis': MATCH_BASES[rank[0]]}))

    ranked.sort(key=lambda item: (item[0], item[1]['symbol'] if han else ''))
    exact = [row for rank, row in ranked if rank[0] == 0]
    matches = exact or [row for _, row in ranked[:20]]
    matched_names = {part for row in matches for part in (row['symbol'].casefold(), row['symbol'].rsplit('.', 1)[-1].casefold())}
    conflicts = [entry for entry in read_json(REGISTRY)['conflicts']
                 if any(query in name.casefold() or name.casefold() in query or name.casefold() in matched_names
                        for name in entry['symbols'])]
    result = {'schema':1, 'status':'passed' if matches else 'not_checked', 'query':symbol, 'matches':matches,
              'conflicts':conflicts, 'scope':'bundled API contract; documented is not editor or host verified',
              'editor':'not_checked', 'host':'not_checked'}
    if not matches:
        result['retry_hint'] = '随包客户端 Lua API 资料中未找到匹配。请用更短的术语、已知别名或正式符号重查。'
    return result

def snapshot():
    records=sources()
    if any(r['integrity']!='passed' for r in records.values()):raise ValueError('Knowledge source changed; review registry before snapshot')
    return {'schema':1,'kind':'knowledge_snapshot','sources':records,
            'client_api':client_catalogue(records['client_api'])[0],
            'scope':'bundled source snapshot; no new official, editor or host verification'}

def difference(before,after):
    from authoring_io import schema
    from capability_index import OWNERS
    from validation_evidence import contract
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
    checks=contract()['public_checks']
    affected=sorted(affected)
    cases=sorted({case for name in affected for case in checks.get(name, {}).get('cases', [])})
    coverage_gaps={name:checks.get(name, {}).get('gap', '请按实际改动补做此能力的定向回归。')
                   for name in affected}
    return {'schema':1,'changed_sources':changed_sources,'api':{'added':added,'removed':removed,'changed':changed},
            'affected_capabilities':affected,'suggested_suites':sorted({case.split('::')[0] for case in cases}),
            'suggested_cases':cases,'coverage_gaps':coverage_gaps,
            'compatibility':'review_required' if removed or changed or changed_sources or added else 'unchanged',
            'before_sha256':sha(Path(before).read_bytes()),'after_sha256':sha(Path(after).read_bytes()),
            'checks_executed':False,'editor':'not_checked','host':'not_checked',
            'scope':'review aid; semantic changes require source review; use docs diff for platform bodies'}

def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='operation',required=True)
    q=sub.add_parser('api');q.add_argument('symbol', metavar='QUERY', help='Formal symbol, English fragment, or Chinese purpose');sub.add_parser('sources');sub.add_parser('snapshot')
    diff=sub.add_parser('diff');diff.add_argument('before');diff.add_argument('after')
    a=p.parse_args(argv)
    result=api(a.symbol) if a.operation=='api' else snapshot() if a.operation=='snapshot' else difference(a.before,a.after) if a.operation=='diff' else {'schema':1,'sources':sources()}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
