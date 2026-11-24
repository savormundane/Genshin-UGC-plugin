"""Shared deterministic I/O boundaries for the schema-2 authoring tools."""
from pathlib import Path
import hashlib,json,os,stat,tempfile
from contextlib import contextmanager

PLUGIN=Path(__file__).resolve().parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()


def sha_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


class DiagnosticError(ValueError):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.diagnostics = [{'code': code, 'message': message, **details}]


def missing_input(path, detail='Input file missing'):
    return DiagnosticError('io.input_missing', f'找不到输入文件 {path}。请核对文件名、扩展名和所在目录后重试。',
                           source=str(path), detail=detail)


def require_new_output(path):
    if path.exists():
        raise DiagnosticError('io.output_exists', f'输出目录 {path} 已存在。请换用尚不存在的输出目录后重试。',
                              source=str(path), detail='Output exists; use a new path: '+str(path))


class ProductionInputs(dict):
    """Keep the digest first observed by production, including child receipts."""

    def bind(self, path, digest, phase):
        source = str(Path(path).resolve())
        expected = self.setdefault(source, digest)
        if expected != digest:
            raise DiagnosticError('production.input_changed', f'Input changed during {phase}: {source}',
                                  phase=phase, source=source, expected=expected, actual=digest)

    def track(self, path, phase):
        path = Path(path).resolve()
        self.bind(path, sha_file(path), phase)
        return path

    def merge(self, receipt, phase):
        for path, digest in receipt.items():
            self.bind(path, digest, phase)

    def verify(self):
        for source, expected in self.items():
            path = Path(source)
            actual = sha_file(path) if path.is_file() else None
            if expected != actual:
                raise DiagnosticError('production.input_changed', f'Input changed before delivery: {source}',
                                      phase='delivery', source=source, expected=expected, actual=actual)


def require_active_baseline(explicit, active, phase, source, active_source):
    if active is None:
        return
    expected, actual = sha(active), sha(explicit)
    if expected != actual:
        raise DiagnosticError('production.baseline_conflict',
                              f'{phase} baseline {source} differs from the active GIL from {active_source}',
                              phase=phase, source=str(source), active_source=str(active_source),
                              expected=expected, actual=actual)


def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def write_json(path,value):Path(path).write_text(canonical(value)+'\n',encoding='utf-8')
def schema(value,allowed,required=(),version=2):
    if not isinstance(value,dict) or set(value)-set(allowed) or set(required)-set(value):raise ValueError('Unknown/missing fields: '+str(allowed))
    if 'schema' in allowed and (type(value.get('schema'))!=int or value['schema']!=version):raise ValueError('Expected schema '+str(version))
def resolve(base,path):return (Path(base)/path).resolve()
def inventory(root, *, cache=None):
    def fail(error):
        raise error

    root=Path(root);result={}
    excluded = {'.git', '__pycache__'}
    for directory, dirs, files in os.walk(root, onerror=fail):
        dirs[:] = [name for name in dirs if name not in excluded]
        for entry in dirs + [name for name in files if name not in excluded]:
            p = Path(directory)/entry
            item = p.lstat()
            if stat.S_ISLNK(item.st_mode) or getattr(item,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('Linked inputs are unsupported: '+str(p))
            if not stat.S_ISREG(item.st_mode) or p.suffix in ('.pyc','.pyo'):
                continue
            name = p.relative_to(root).as_posix()
            if cache is None:
                result[name] = sha_file(p)
                continue
            signature = (item.st_size, item.st_mtime_ns, item.st_ctime_ns, item.st_ino)
            previous = cache.get(name)
            digest = previous[1] if previous is not None and previous[0] == signature else sha_file(p)
            cache[name] = (signature, digest)
            result[name] = digest
    return dict(sorted(result.items()))
@contextmanager
def output_directory(out):
    out=Path(out).resolve()
    require_new_output(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qianxing-stage-',dir=out.parent) as td:
        stage=Path(td)/'result';stage.mkdir()
        yield stage
        os.rename(stage,out)
def finish(stage,inputs,*,files=None,**details):
    if isinstance(inputs, ProductionInputs):
        inputs.verify()
    else:
        for p,digest in inputs.items():
            if sha_file(p)!=digest:raise ValueError('Input changed: '+p)
    report={'schema':2,'inputs':inputs,'files':inventory(stage) if files is None else files,'editor_tested':False,'host_tested':False,**details}
    write_json(stage/'manifest.json',report);return report
