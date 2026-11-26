"""Versioned document selection and explicit platform configuration checks."""
from pathlib import Path
from unicodedata import normalize
import argparse,difflib,json,math,re
from authoring_io import DiagnosticError,PLUGIN,read_json,sha,schema,canonical

CATALOGUE=PLUGIN/'scripts/platform-sources.json'
MOVERS=('linear','rotation','target_rotation','path','point','level_path')
DOCUMENTS={'creature':'mh74ae9fsg8i','movers':'mhnmcmipncrg','timer':'mhufb90zbnts',
           'photo_button':'mhtpwgitsigc','combat_text_filter':'mh3lmk9tmrky','prefab_group':'mhzhzb9rw0uy'}

HAN = r'[\u3400-\u4dbf\u4e00-\u9fff]'
CHINESE = re.compile(HAN + '+')
QUERY_TERM = re.compile(HAN + r'+|[a-z0-9_]+(?:[.:-][a-z0-9_]+)*')
QUESTION_PREFIX = re.compile(
    r'^(?:(?:请问|我?想问(?:一下|问)?|我?想(?:了解|知道)|在千星奇域(?:里|中)|'
    r'请?帮我(?:查|看)(?:一下)?)[\s,，、:：]*)+'
)
QUESTION_WORDS = re.compile(
    r'请问|想了解|(?:怎么|如何|怎样)(?:使用|用|调用|工作)?|'
    r'(?:有哪些|有什么)(?:用法|使用方法)?|有没有|是什么|'
    r'在哪(?:里|份文档里)?|哪里|能不能|可不可以|是否|能否'
)
LINK_URL = re.compile(r'https?://[^\s<>)）]+')
MARKDOWN_HEADING = re.compile(r'^\s*#{1,6}\s+\**\s*(?:\d+[.、]\s*)?')


def selection(version):
    raw=CATALOGUE.read_bytes()
    index=json.loads(raw.decode('utf-8-sig'))
    if index['schema']!=1:raise ValueError('Unknown platform source catalogue schema')
    profiles=index['profiles']
    if not isinstance(version,str) or version not in profiles:
        raise DiagnosticError('platform.version_unknown',
                              f'无法识别千星奇域版本 {version!r}。请核对游戏内版本后重试。'
                              f'当前已收录 {"、".join(profiles)}。目标版本尚未收录时，可附上版本号和资料来源反馈。',
                              supported_versions=list(profiles), detail='Unknown platform version: '+str(version))
    lineage=[];current=version
    while current is not None:
        if not isinstance(current,str)or current not in profiles:
            raise ValueError(f'Missing or invalid platform parent: {current!r} in {version}')
        if current in lineage:raise ValueError('Platform inheritance cycle: '+' -> '.join([*lineage,current]))
        lineage.append(current)
        if 'base' not in profiles[current]:raise ValueError('Platform profile has no parent declaration: '+current)
        current=profiles[current]['base']
    result={}
    for ident,row in index['documents'].items():
        selected=next((v for v in lineage if v in row['versions']),None)
        if selected is None:continue
        source=row['versions'][selected]
        result[ident]={**{k:row[k]for k in('id','title','official_url')},**source,
                       'requested_version':version,'source_version':selected,
                       'knowledge_status':'documented','editor':'not_checked','host':'not_checked',
                       'applicability':'inherited_source_not_revalidated' if selected!=version else 'selected_document_profile',
                       'inherited':selected!=version,'update_entry':ident in index['update_documents']}
    return index,lineage,result,sha(raw)


def documents(version):
    return selection(version)[2]


def _content(record):
    path=(PLUGIN/record['path']).resolve()
    if not path.is_relative_to(PLUGIN.resolve())or path.is_symlink():raise ValueError('Invalid platform document path')
    if not path.is_file():raise ValueError('Selected platform document file missing: '+record['id'])
    raw=path.read_bytes()
    if sha(raw)!=record['sha256']:raise ValueError('Platform source digest changed: '+record['id'])
    return {**record,'content':raw.decode('utf-8-sig')}


def show(version,ident):
    records=documents(version)
    if ident not in records:raise ValueError('Document absent in selected profile: '+str(ident))
    return _content(records[ident])


def _chinese_matches(records, query, version):
    if not CHINESE.search(query):
        return []
    literal = QUESTION_PREFIX.sub('', normalize('NFKC', query).casefold().strip())
    terms = {}
    for word in QUERY_TERM.findall(QUESTION_WORDS.sub(' ', literal)):
        chinese = CHINESE.fullmatch(word)
        term = word.strip('的呢吗') if chinese else word
        if term == version or (chinese and len(term) < 2):
            continue
        # Keep short terms and formal identifiers literal. Longer Chinese clauses
        # can share adjacent pairs with a passage that uses a different word order.
        pairs = set()
        if chinese and len(term) >= 4:
            pairs = {term[start:start + 2] for start in range(len(term) - 1)}
        terms[term] = pairs
    if not terms:
        return []

    ranked = []
    for record, text, lines in records:
        title = record['title'].casefold()
        exact = {term for term in terms if term in text}
        approximate = terms.keys() - exact
        coverage = {
            term: sum(pair in text for pair in terms[term]) for term in approximate
        }
        if any(count < max(2, math.ceil(len(terms[term]) * 2 / 3))
               for term, count in coverage.items()):
            continue

        evidence = []
        heading_match = 0
        for line, folded in lines:
            heading = MARKDOWN_HEADING.match(folded)
            if heading:
                heading_text = folded[heading.end():].strip('* ')
                if heading_text in exact:
                    heading_match = max(heading_match, len(heading_text))
            exact_hits = sum(len(term) for term in exact if term in folded)
            pair_hits = sum(pair in folded for term in approximate for pair in terms[term])
            if exact_hits or pair_hits >= 2:
                evidence.append((exact_hits, pair_hits, line))
        evidence.sort(key=lambda row: (-row[0], -row[1]))
        excerpts = [line[:500] for _, _, line in evidence[:3]]
        if excerpts:
            score = (
                -sum(len(term) for term in exact if term in title),
                -(len(title) if title in literal else 0),
                -heading_match,
                -len(exact), -sum(coverage.values()), record['title'], record['id'],
            )
            ranked.append((score, {**record, 'excerpts': excerpts}))
    ranked.sort(key=lambda entry: entry[0])
    return [record for _, record in ranked]


def search(version, query, limit=20):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Document limit must be 1..100')
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Document query required')
    folded = query.casefold()
    terms = folded.split()
    records, matches = [], []
    for source in documents(version).values():
        record = _content(source)
        body = record.pop('content')
        # Match visible text and keep the corresponding original lines for excerpts.
        lines = [(line, LINK_URL.sub('', line.casefold())) for line in body.splitlines()]
        text = record['title'].casefold() + ' ' + '\n'.join(line for _, line in lines)
        records.append((record, text, lines))
        if all(term in text for term in terms):
            excerpts = [original[:500] for original, line in lines
                        if any(term in line for term in terms)]
            matches.append({**record, 'excerpts': excerpts[:3]})
    matches.sort(key=lambda record: (folded not in record['title'].casefold(),
                                     record['title'], record['id']))
    if not matches:
        matches = _chinese_matches(records, query, version)
    result = {'schema': 2, 'version': version, 'query': query, 'matches': len(matches),
              'documents': matches[:limit]}
    if not matches:
        result['retry_hint'] = '当前版本的随包资料未找到匹配项。请拆成短关键词，或改用平台术语和正式名称重查。'
    return result


def difference(before,after,ident=None):
    left=documents(before);right=documents(after)
    if ident is not None and ident not in left and ident not in right:raise ValueError('Unknown document ID')
    rows=[]
    for key in([ident]if ident else sorted(left.keys()|right.keys())):
        a=_content(left[key])if key in left else None;b=_content(right[key])if key in right else None
        status='added'if a is None else'removed'if b is None else'unchanged'if a['sha256']==b['sha256']else'changed'
        row={'id':key,'title':(b or a)['title'],'status':status,'before':None if a is None else{k:v for k,v in a.items()if k!='content'},
             'after':None if b is None else{k:v for k,v in b.items()if k!='content'}}
        if ident:
            row['text_diff']='\n'.join(difflib.unified_diff((a or{}).get('content','').splitlines(),(b or{}).get('content','').splitlines(),fromfile=before,tofile=after,lineterm=''))
        rows.append(row)
    return {'schema':2,'from':before,'to':after,'comparison':'source text; changes include formatting, not inferred API changes',
            'counts':{s:sum(r['status']==s for r in rows)for s in('added','removed','changed','unchanged')},'documents':rows}


def _profile(version,mode):
    if mode not in('classic','beyond'):raise ValueError('Unknown platform mode: '+str(mode))
    from platform_rules72 import SOURCES
    index,lineage,docs,digest=selection(version)
    dependencies={k:(v,) for k,v in DOCUMENTS.items()}|SOURCES
    for kind in ('timer','combat_text_filter'):
        dependencies[kind]=(*dependencies[kind],DOCUMENTS['creature'])
    limits={};mode_limits={};rules={};mover_conflicts={}
    for revision in reversed(lineage):
        settings=index['profiles'][revision]
        limits.update(settings.get('limits',{}))
        mode_limits.update(settings.get('mode_limits',{}).get(mode,{}))
        mover_conflicts.update(settings.get('conflicts',{}).get('mover_pairs',{}))
        decisions=settings.get('rules',{})
        for kind,ids in dependencies.items():
            if kind in decisions:
                decision=decisions[kind]
                if type(decision)is not bool:raise ValueError('Platform rule decision must be boolean: '+kind)
                rules[kind]='enabled' if decision else 'disabled'
            elif rules.get(kind)=='enabled' and any(revision in index['documents'][i]['versions'] for i in ids if i in index['documents']):
                rules[kind]='review_required'
    context={'schema':2,'version':version,'mode':mode,'source_catalogue_sha256':digest,
            'limits':limits|mode_limits,
            'document_inheritance':'unmodified entries retain their recorded source version',
            'native_format_version':'not_calibrated_by_this_profile','editor':'not_checked','host':'not_checked'}
    return context,rules,mover_conflicts,dependencies,docs


def profile(version,mode):
    return _profile(version,mode)[0]


def check(spec):
    schema(spec,('schema','version','mode','objects','native_bindings'),('schema','version','mode','objects'))
    context,rules,mover_conflicts,dependencies,docs=_profile(spec['version'],spec['mode']);limits=context['limits']
    objects=spec['objects']
    if not isinstance(objects,list):raise ValueError('Platform objects must be a list')
    fields={'creature':('skill_count',),'movers':('active',),'timer':('entity','sequence'),
            'photo_button':('trigger','cooldown_origin'),'combat_text_filter':('entity_kind','filters_per_template'),
            'prefab_group':('members',)}
    from platform_rules72 import FIELDS,check as check72
    fields.update(FIELDS)
    checks=[];seen=set();sources={};timers={};photos=[]
    def result(obj,rule,passed,detail):
        checks.append({'object':obj['id'],'rule':rule,'status':'passed'if passed else'failed','detail':detail})
    for obj in objects:
        if not isinstance(obj,dict)or obj.get('kind')not in fields:raise ValueError('Unsupported platform object kind')
        kind=obj['kind'];schema(obj,('id','kind',*fields[kind]),('id','kind',*fields[kind]))
        if not isinstance(obj['id'],str)or not obj['id'].strip()or obj['id']in seen:raise ValueError('Unique nonempty platform object IDs required')
        seen.add(obj['id'])
        if rules.get(kind)!='enabled':
            detail='Rule requires review for the selected source version' if rules.get(kind)=='review_required' else 'Rule unavailable in selected profile'
            checks.append({'object':obj['id'],'rule':kind,'status':'not_checked','detail':detail})
            continue
        for ident in dependencies[kind]:
            if ident not in docs:raise ValueError('Platform rule source absent: '+ident)
            if ident not in sources:
                _content(docs[ident]);sources[ident]=docs[ident]
        if kind in FIELDS:
            checks.extend(check72(obj,context['mode']))
            continue
        if kind=='creature':
            count=obj['skill_count']
            if type(count)!=int or count<0:raise ValueError('skill_count must be a nonnegative integer')
            result(obj,'creature.skill_limit',count<=limits['creature_skills'],{'actual':count,'maximum':limits['creature_skills']})
        elif kind=='movers':
            active=obj['active']
            if not isinstance(active,list)or any(v not in MOVERS for v in active):raise ValueError('Unknown mover type')
            # The 7.1 prose and matrix disagree for point/rotation pairs.
            # Keep that conflict visible instead of choosing the permissive row.
            for i,a in enumerate(active):
                for b in active[i+1:]:
                    reason=mover_conflicts.get('/'.join(sorted((a,b))))
                    if reason:
                        checks.append({'object':obj['id'],'rule':'movers.compatibility','status':'not_checked','detail':{'types':[a,b],'reason':reason}});continue
                    compatible='linear'in(a,b)or set((a,b))=={'path','point'}
                    result(obj,'movers.compatibility',compatible,{'types':[a,b]})
            if len(active)<2:result(obj,'movers.compatibility',True,{'types':active})
        elif kind=='timer':
            entity=obj['entity'];sequence=obj['sequence']
            if not isinstance(entity,str)or not entity:raise ValueError('Timer entity identity required')
            if not isinstance(sequence,list)or not sequence or any(type(v)not in(int,float)or not math.isfinite(v)or v<0 for v in sequence):
                raise ValueError('Timer sequence needs finite nonnegative numbers')
            timers.setdefault(entity,[]).append(obj)
            result(obj,'timer.sequence_limit',len(sequence)<=limits['timer_sequence'],{'actual':len(sequence),'maximum':limits['timer_sequence']})
            minimum=limits['timer_interval_seconds']
            result(obj,'timer.interval',all(b>a and b-a>=minimum-1e-12 for a,b in zip(sequence,sequence[1:])),{'minimum_seconds':minimum})
        elif kind=='photo_button':
            photos.append(obj)
            result(obj,'photo_button.trigger',obj['trigger']=='photo_close',{'required':'photo_close'})
            result(obj,'photo_button.cooldown_origin',obj['cooldown_origin']=='photo_close',{'required':'photo_close'})
        elif kind=='combat_text_filter':
            counts=obj['filters_per_template']
            if not isinstance(counts,list)or any(type(v)!=int or v<0 for v in counts):raise ValueError('Filter counts must be nonnegative integers')
            result(obj,'combat_filter.player_only',obj['entity_kind']=='player',{'required':'player'})
            limit=limits['combat_filter_templates']
            result(obj,'combat_filter.template_limit',len(counts)<=limit,{'actual':len(counts),'maximum':limit})
            limit=limits['combat_filters_per_template']
            result(obj,'combat_filter.item_limit',all(v<=limit for v in counts),{'actual':counts,'maximum':limit})
        elif kind=='prefab_group':
            members=obj['members']
            if not isinstance(members,list)or not members:raise ValueError('Prefab group members required')
            names=set()
            for member in members:
                schema(member,('id','dynamic'),('id','dynamic'))
                if not isinstance(member['id'],str)or not member['id']or member['id']in names or type(member['dynamic'])!=bool:raise ValueError('Unique member IDs and boolean dynamic flag required')
                names.add(member['id'])
            result(obj,'prefab_group.dynamic_only',all(m['dynamic']for m in members),{'members':[m['id']for m in members]})
    limit=limits['timers_per_entity']
    for entity,items in timers.items():result(items[0],'timer.entity_limit',len(items)<=limit,{'entity':entity,'actual':len(items),'maximum':limit})
    limit=limits['classic_photo_buttons']
    if photos and limit is not None:result(photos[0],'photo_button.classic_limit',len(photos)<=limit,{'actual':len(photos),'maximum':limit})
    if 'native_bindings'in spec:
        bindings=spec['native_bindings']
        if not isinstance(bindings,dict)or not bindings:raise ValueError('Nonempty native_bindings object required')
        objects_by_id={obj['id']:obj for obj in objects};selectors=set();entities={}
        for ident,binding in bindings.items():
            if ident not in objects_by_id or objects_by_id[ident]['kind']!='timer':raise ValueError('Native binding currently requires a declared timer')
            schema(binding,('graph','node','entity','name'),('graph','node','entity','name'))
            if any(type(binding[k])is not int or binding[k]<0 for k in('graph','node','entity'))or not isinstance(binding['name'],str)or not binding['name']:
                raise ValueError('Invalid native timer selector')
            selector=(binding['graph'],binding['node'])
            if selector in selectors:raise ValueError('Duplicate native timer selector')
            selectors.add(selector);logical=objects_by_id[ident]['entity']
            if logical in entities and entities[logical]!=binding['entity']:raise ValueError('Logical timer entity has conflicting native bindings')
            entities[logical]=binding['entity']
    status='failed'if any(r['status']=='failed'for r in checks)else'not_checked'if not checks or any(r['status']=='not_checked'for r in checks)else'passed'
    return {'schema':2,'status':status,'scope':'declared_configuration','artifact_verified':False,'profile':context,
            'configuration_sha256':sha(canonical(spec).encode()),'checks':checks,'sources':sources,
            'unchecked_features':['component_binary_generation','resource_ID_support','runtime_lifecycle','detailed_node_signatures'],
            'editor':'not_checked','host':'not_checked'}


def main(argv=None):
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='operation',required=True)
    s=sub.add_parser('search');s.add_argument('query');s.add_argument('--version',required=True);s.add_argument('--limit',type=int,default=20)
    s=sub.add_parser('show');s.add_argument('id');s.add_argument('--version',required=True)
    s=sub.add_parser('diff');s.add_argument('--from',dest='before',required=True);s.add_argument('--to',dest='after',required=True);s.add_argument('--id')
    s=sub.add_parser('profile');s.add_argument('--version',required=True);s.add_argument('--mode',choices=['classic','beyond'],required=True)
    s=sub.add_parser('check');s.add_argument('spec');s.add_argument('--gil')
    a=p.parse_args(argv)
    if a.operation=='search':value=search(a.version,a.query,a.limit)
    elif a.operation=='show':value=show(a.version,a.id)
    elif a.operation=='diff':value=difference(a.before,a.after,a.id)
    elif a.operation=='profile':value=profile(a.version,a.mode)
    else:
        spec=read_json(a.spec);value=check(spec)
        if a.gil:
            from platform_native import check as check_native
            value['native']=check_native(Path(a.gil).read_bytes(),spec)
            if value['native']['status']!='passed'and value['status']!='failed':value['status']=value['native']['status']
    print(json.dumps(value,ensure_ascii=False,indent=2))
    return 2 if value.get('status')in('failed','not_checked')else 0


if __name__=='__main__':raise SystemExit(main())
