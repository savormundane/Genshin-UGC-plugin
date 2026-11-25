"""Read-only, artifact-bound JSONL diagnostics; log text is never executable."""
from pathlib import Path
import argparse,json,re
from authoring_io import schema,read_json,resolve,sha
from miliastra.client.check import inspect
from miliastra.client.assembly import locate


def diagnose(path):
    path=Path(path).resolve();spec=read_json(path)
    schema(spec,('schema','logs','bindings'),('logs','bindings'))
    if not isinstance(spec['logs'],list)or not spec['logs']:raise ValueError('Log files required')
    if not isinstance(spec['bindings'],list):raise ValueError('Log bindings must be a list')
    inputs={str(path):sha(path.read_bytes())};bindings={}
    for binding in spec['bindings']:
        schema(binding,('build_id','artifact','mapping','source_map'),('build_id','artifact','mapping'))
        if not isinstance(binding['build_id'],str)or not binding['build_id']:raise ValueError('Build identity required')
        if binding['mapping']is not None and not isinstance(binding['mapping'],str):raise ValueError('Invalid binding mapping')
        source=resolve(path.parent,binding['artifact']);raw=source.read_bytes();digest=sha(raw);inputs[str(source)]=digest
        mapping=None
        if 'source_map'in binding:
            source_map=resolve(path.parent,binding['source_map']);mapping=read_json(source_map);inputs[str(source_map)]=sha(source_map.read_bytes())
        # Reuse the exact final-body and source-map boundary. No Lua is executed.
        checked=inspect(source,mapping=binding['mapping'],source_map=mapping)
        key=(binding['build_id'],digest,binding['mapping'])
        if key in bindings:raise ValueError('Duplicate log artifact binding')
        bindings[key]={'source_map':mapping,'syntax':checked['checks']['syntax'],'artifact':str(source)}
    events=[];unparsed=[];groups={}
    for name in spec['logs']:
        source=resolve(path.parent,name);raw=source.read_bytes();inputs[str(source)]=sha(raw)
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
        if sha(Path(name).read_bytes())!=digest:raise ValueError('Diagnostic input changed')
    return {'schema':2,'status':'not_checked'if unparsed or any(e['binding']=='unmatched'for e in events)or not events else'passed',
            'scope':'log_parsing_and_artifact_correlation','inputs':inputs,'events':events,'unparsed':unparsed,
            'bindings':[{'build_id':k[0],'artifact_sha256':k[1],'mapping':k[2],'artifact':v['artifact'],'syntax':v['syntax']}for k,v in bindings.items()],
            'groups':[{'build_id':k[0],'artifact_sha256':k[1],'mapping':k[2],'player':k[3],'session':k[4],'slot':k[5],'request':k[6],'graph_instance':k[7],'revision':k[8],'event_indices':v}for k,v in groups.items()],
            'observed_error_count':sum(e.get('level')=='error'for e in events),'editor':'not_checked','host':'not_checked',
            'note':'Matched logs establish attribution only, not runtime acceptance or persistence confirmation.'}


def main(argv=None):
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True)
    command=sub.add_parser('diagnose');command.add_argument('spec');command.add_argument('--out');args=parser.parse_args(argv)
    report=diagnose(args.spec)
    if args.out:
        with Path(args.out).open('x',encoding='utf-8')as output:json.dump(report,output,ensure_ascii=False,indent=2)
    print(json.dumps(report,ensure_ascii=False));return 0 if report['status']=='passed'else 1
