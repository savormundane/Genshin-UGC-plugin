"""Read-only JSONL attribution and editor debug-print decoding."""
from pathlib import Path
import argparse,json,os,re,struct
from authoring_io import schema,resolve,sha,sha_file
from level_inventory import iter_fields
from miliastra.client.check import inspect
from miliastra.client.assembly import locate


EDITOR_LOG_FORMAT = 'editor-debug-log'
MAX_EDITOR_LOG_BYTES = 64 * 1024 * 1024
MAX_EDITOR_LOG_PAGE = 1000


def _log_input(base, name, read_roots):
    if not isinstance(name, str) or not name:
        raise ValueError('Nonempty log input path required')
    if read_roots is None:
        return resolve(base, name)

    from miliastra.mcp.workspace import linked

    path = Path(os.path.abspath(base / name))
    owner = next((root for root in read_roots if path != root and path.is_relative_to(root)), None)
    if owner is None:
        raise ValueError('Log input outside allowed project/output roots')
    for part in (path, *path.parents):
        if linked(part):
            raise ValueError('Linked log input refused')
        if part == owner:
            break
    if not path.resolve().is_relative_to(owner) or not path.is_file():
        raise ValueError('Log input must be a file under the authorized project/output roots')
    return path


def _known_fields(raw, wires):
    values = {}
    for number, wire, value, _ in iter_fields(raw):
        if number in wires:
            if number in values or wire != wires[number]:
                raise ValueError(f'Ambiguous editor debug-log field {number}')
            values[number] = value
    return values


def _editor_debug_log(raw, file, offset, limit):
    # Field layout observed by 8itlab at 70470757d6fcb319c5afec13b178c87f2d8d54b3.
    # The two lengths identify framing. They do not establish a game version or build.
    size = len(raw)
    if not 8 <= size <= MAX_EDITOR_LOG_BYTES or struct.unpack_from('>II', raw) != (size - 4, size - 8):
        raise ValueError('Unsupported editor debug-log envelope')

    records = prints = 0
    events = []
    for index, (number, wire, record, _) in enumerate(iter_fields(memoryview(raw)[8:])):
        records += 1
        if (number, wire) != (1, 2):
            continue
        print_fields = _known_fields(record, {22: 2, 23: 2})
        if not print_fields:
            continue
        if len(print_fields) != 1:
            raise ValueError('Ambiguous editor debug-log print kind')
        (kind, print_record), = print_fields.items()
        text = _known_fields(print_record, {2: 2}).get(2)
        if text is None:
            raise ValueError('Missing editor debug-log print text')
        message = bytes(text).decode('utf-8')
        known = _known_fields(record, {3: 0, 4: 2, 7: 2, 9: 0})
        stamp = bytes(known[4]).decode('utf-8') if 4 in known else None
        graph = _known_fields(known[7], {2: 0}).get(2) if kind == 22 and 7 in known else None
        if kind == 22 and 7 in known and graph is None:
            raise ValueError('Missing editor debug-log graph ID')
        if offset <= prints < offset + limit:
            events.append({
                'log_file': str(file), 'log_record_index': index, 'message': message,
                'source_kind': 'client_lua_print' if kind == 23 else 'node_graph_print',
                'elapsed_seconds': str(known[3]) if 3 in known else None,
                'session_label': stamp,
                'graph_id': str(graph) if graph is not None else None,
                'entity_id': str(known[9]) if 9 in known else None,
                'build_id': None, 'artifact_sha256': None, 'mapping': None,
                'binding': 'unmatched', 'origin': None, 'artifact_syntax': 'not_checked',
                'correlation_missing': ['graph_instance', 'revision'],
                'instance_revision_correlation': 'not_checked',
            })
        prints += 1
    return events, {
        'file': str(file), 'format': EDITOR_LOG_FORMAT, 'records': records, 'print_count': prints,
        'ignored_record_count': records - prints, 'offset': offset, 'severity': 'not_checked',
        'next_offset': offset + limit if offset + limit < prints else None,
    }


def diagnose(path, *, read_roots=None):
    path = Path(path).resolve()
    spec_raw = path.read_bytes()
    spec = json.loads(spec_raw.decode('utf-8-sig'))
    schema(spec,('schema','logs','bindings'),('logs','bindings'))
    if not isinstance(spec['logs'],list)or not spec['logs']:raise ValueError('Log files required')
    if not isinstance(spec['bindings'],list):raise ValueError('Log bindings must be a list')
    inputs={str(path):sha(spec_raw)};bindings={}
    for binding in spec['bindings']:
        schema(binding,('build_id','artifact','mapping','source_map'),('build_id','artifact','mapping'))
        if not isinstance(binding['build_id'],str)or not binding['build_id']:raise ValueError('Build identity required')
        if binding['mapping']is not None and not isinstance(binding['mapping'],str):raise ValueError('Invalid binding mapping')
        source=_log_input(path.parent,binding['artifact'],read_roots);digest=sha_file(source);inputs[str(source)]=digest
        mapping=None
        if 'source_map'in binding:
            source_map=_log_input(path.parent,binding['source_map'],read_roots)
            raw = source_map.read_bytes()
            mapping = json.loads(raw.decode('utf-8-sig'))
            inputs[str(source_map)] = sha(raw)
        # Reuse the exact final-body and source-map boundary. No Lua is executed.
        checked=inspect(source,mapping=binding['mapping'],source_map=mapping)
        key=(binding['build_id'],digest,binding['mapping'])
        if key in bindings:raise ValueError('Duplicate log artifact binding')
        bindings[key]={'source_map':mapping,'syntax':checked['checks']['syntax'],'artifact':str(source)}
    events=[];unparsed=[];groups={};editor_logs=[]
    for name in spec['logs']:
        if isinstance(name, dict):
            schema(name, ('path', 'format', 'offset', 'limit'), ('path', 'format'))
            if name['format'] != EDITOR_LOG_FORMAT:
                raise ValueError(f'Unknown log format; expected {EDITOR_LOG_FORMAT}')
            offset, limit = name.get('offset', 0), name.get('limit', 100)
            if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= MAX_EDITOR_LOG_PAGE:
                raise ValueError(f'Editor log offset must be nonnegative and limit must be 1..{MAX_EDITOR_LOG_PAGE}')
            source = _log_input(path.parent, name['path'], read_roots)
            with source.open('rb') as log:
                raw = log.read(MAX_EDITOR_LOG_BYTES + 1)
            page, decoded = _editor_debug_log(raw, source, offset, limit)
            inputs[str(source)] = sha(raw)
            events.extend(page)
            editor_logs.append(decoded)
            continue
        source=_log_input(path.parent,name,read_roots);raw=source.read_bytes();inputs[str(source)]=sha(raw)
        for number,text in enumerate(raw.decode('utf-8-sig').splitlines(),1):
            if not text.strip():continue
            try:event=json.loads(text)
            except json.JSONDecodeError:
                unparsed.append({'file':str(source),'line':number,'text':text});continue
            schema(event,('build_id','artifact_sha256','mapping','line','message','level','player','session','slot','request','phase','fields','graph_instance','revision'),
                   ('build_id','artifact_sha256','mapping','message'))
            if not isinstance(event['build_id'],str)or not isinstance(event['message'],str):raise ValueError('Invalid log identity/message')
            if not isinstance(event['artifact_sha256'],str)or not re.fullmatch('[0-9a-f]{64}',event['artifact_sha256']):raise ValueError('Invalid log artifact digest')
            if event['mapping']is not None and not isinstance(event['mapping'],str):raise ValueError('Invalid log mapping')
            if 'line'in event and (type(event['line'])is not int or event['line']<1):raise ValueError('Log source line must be positive')
            if 'level'in event and event['level']not in ('debug','info','warning','error'):raise ValueError('Invalid log level')
            if 'fields'in event and not isinstance(event['fields'],dict):raise ValueError('Log fields must be an object')
            for field in ('player','session','slot','request','phase'):
                if field in event and type(event[field])not in (str,int):raise ValueError('Invalid correlation field '+field)
            if 'graph_instance'in event and (not isinstance(event['graph_instance'],str)or not event['graph_instance'].strip()):raise ValueError('Nonempty graph instance required')
            if 'revision'in event and (type(event['revision'])is not int or event['revision']<0):raise ValueError('Nonnegative integer revision required')
            key=(event['build_id'],event['artifact_sha256'],event['mapping']);bound=bindings.get(key)
            record={**event,'log_file':str(source),'log_line':number,'binding':'matched'if bound else'unmatched','origin':None}
            record['artifact_syntax']=bound['syntax']if bound else'not_checked'
            if bound and bound['source_map']is not None and 'line'in event:record['origin']=locate(bound['source_map'],event['line'])
            record['correlation_missing']=[k for k in ('graph_instance','revision')if k not in event]
            record['instance_revision_correlation']='not_checked'if record['correlation_missing']else'passed'
            events.append(record)
            identity=key+tuple(event.get(k)for k in ('player','session','slot','request','graph_instance','revision'))
            groups.setdefault(identity,[]).append(len(events)-1)
    for name,digest in inputs.items():
        if sha_file(name)!=digest:raise ValueError('Diagnostic input changed')
    return {'schema':2,'status':'not_checked'if editor_logs or unparsed or any(e['binding']=='unmatched'for e in events)or not events else'passed',
            'scope':'log_parsing_and_artifact_correlation','inputs':inputs,'events':events,'unparsed':unparsed,
            **({'editor_logs': editor_logs} if editor_logs else {}),
            'bindings':[{'build_id':k[0],'artifact_sha256':k[1],'mapping':k[2],'artifact':v['artifact'],'syntax':v['syntax']}for k,v in bindings.items()],
            'groups':[{'build_id':k[0],'artifact_sha256':k[1],'mapping':k[2],'player':k[3],'session':k[4],'slot':k[5],'request':k[6],'graph_instance':k[7],'revision':k[8],'event_indices':v}for k,v in groups.items()],
            'observed_error_count':sum(e.get('level')=='error'for e in events),'editor':'not_checked','host':'not_checked',
            'note': ('Editor debug logs expose print records. Build association and runtime acceptance require independent evidence.'
                     if editor_logs else 'Matched logs establish attribution only, not runtime acceptance or persistence confirmation.')}


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    command=sub.add_parser('diagnose');command.add_argument('spec');command.add_argument('--out');args=parser.parse_args(argv)
    report=diagnose(args.spec)
    if args.out:
        with Path(args.out).open('x',encoding='utf-8')as output:json.dump(report,output,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False));return 0 if report['status']=='passed'else 1
