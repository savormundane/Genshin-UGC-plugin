"""Shared deterministic I/O boundaries for the schema-2 authoring tools."""
from pathlib import Path
import hashlib,json,os,tempfile
from contextlib import contextmanager

PLUGIN=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()


def sha_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def write_json(path,value):Path(path).write_text(canonical(value)+'\n',encoding='utf-8')
def schema(value,allowed,required=(),version=2):
    if not isinstance(value,dict) or set(value)-set(allowed) or set(required)-set(value):raise ValueError('Unknown/missing fields: '+str(allowed))
    if 'schema' in allowed and (type(value.get('schema'))!=int or value['schema']!=version):raise ValueError('Expected schema '+str(version))
def resolve(base,path):return (Path(base)/path).resolve()
def inventory(root):
    root=Path(root);result={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('Linked inputs are unsupported: '+str(p))
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'):result[p.relative_to(root).as_posix()]=sha(p.read_bytes())
    return result
@contextmanager
def output_directory(out):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Output exists; use a new path: '+str(out))
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qianxing-stage-',dir=out.parent) as td:
        stage=Path(td)/'result';stage.mkdir()
        yield stage
        os.rename(stage,out)
def finish(stage,inputs,**details):
    for p,digest in inputs.items():
        if sha_file(p)!=digest:raise ValueError('Input changed: '+p)
    report={'schema':2,'inputs':inputs,'files':inventory(stage),'editor_tested':False,'host_tested':False,**details}
    write_json(stage/'manifest.json',report);return report
