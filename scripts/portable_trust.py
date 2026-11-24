"""Data-only portable closure checks; an integrity hash is not permission to execute."""
import os
import re
from pathlib import Path, PurePosixPath
from authoring_io import DiagnosticError, PLUGIN, read_json, sha, canonical, inventory


def listed_path(root, name, checked=None):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Invalid manifest path')
    parts = PurePosixPath(name).parts
    if name.startswith('/') or '..' in parts or PurePosixPath(name).as_posix() != name:
        raise ValueError('Noncanonical manifest path')
    target = root.joinpath(*parts)
    if any(part.endswith((' ','.')) for part in parts):raise ValueError('Ambiguous Windows manifest path')
    for part in (target, *target.parents):
        if part == root.parent:
            break
        if checked is not None and part in checked:continue
        if part.is_symlink() or (part.exists() and getattr(part.lstat(),'st_file_attributes',0)&1024):
            raise ValueError('Linked input refused')
        if checked is not None:checked.add(part)
    # Canonical relative components + no linked ancestor already establish containment.
    return target


def closure(bundle):
    bundle = Path(bundle).absolute()
    checked=set()
    record = read_json(listed_path(bundle, 'portable.json',checked))
    if record.get('schema') != 1 or not isinstance(record.get('files'), dict):
        raise ValueError('Unknown portable input schema')
    for name, digest in record['files'].items():
        path = listed_path(bundle, name,checked)
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or not path.is_file() or sha(path.read_bytes()) != digest:
            raise ValueError('Portable input missing or changed: '+name)
    actual_dirs=set()
    for directory, dirs, files in os.walk(bundle, followlinks=False):
        for name in dirs+files:
            path = Path(directory)/name
            relative = path.relative_to(bundle).as_posix()
            listed_path(bundle, relative,checked)
            if path.is_dir():actual_dirs.add(relative)
            if path.is_file() and relative != 'portable.json' and relative not in record['files']:
                raise ValueError('Unregistered portable input: '+relative)
    job = listed_path(bundle, 'workspace/'+record['job'],checked)
    if job.relative_to(bundle).as_posix() not in record['files']:
        raise ValueError('Portable job is not registered')
    inferred={parent.as_posix() for name in record['files'] for parent in PurePosixPath(name).parents if parent.as_posix()!='.'}
    directories=record.get('directories',sorted(inferred))
    if not isinstance(directories,list) or any(not isinstance(d,str) for d in directories) or len(set(directories))!=len(directories):
        raise ValueError('Invalid portable directory manifest')
    for name in directories:listed_path(bundle,name,checked)
    if set(directories)!=actual_dirs:raise ValueError('Missing or unregistered portable directory')
    # Follow only known declarative references; collect parses data, never imports project code.
    from portable_delivery import collect
    _,_,required,_,_,_=collect(job,{},snapshot_root=bundle/'workspace')
    if any(path.relative_to(bundle).as_posix() not in record['files'] for path in required):
        raise ValueError('Unregistered configuration dependency')
    token = sha(canonical({'record': record, 'manifest_sha256': sha((bundle/'portable.json').read_bytes())}).encode())
    return record, token


def trusted_execution(bundle, approval):
    record, token = closure(bundle)
    if approval != token:
        raise ValueError('Project execution requires explicit trusted_inputs_sha256 from the static report')
    packaged = {name[len('workspace/toolchain/'):]: digest for name, digest in record['files'].items() if name.startswith('workspace/toolchain/')}
    current = inventory(PLUGIN)
    if packaged != current:
        raise DiagnosticError(
            'portable.toolchain_mismatch',
            'Portable toolchain differs from the current trusted plugin. '
            '请使用与原交付完全一致的版本和安装包重建，或先执行静态核对。',
            expected=sha(canonical(packaged).encode('utf-8')),
            actual=sha(canonical(current).encode('utf-8')),
            missing_files=len(packaged.keys() - current.keys()),
            extra_files=len(current.keys() - packaged.keys()),
            changed_files=sum(packaged[name] != current[name] for name in packaged.keys() & current.keys()),
        )
    return record


def child_environment():
    names = ('SYSTEMROOT','WINDIR','PATH','PATHEXT','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','HOME','LANG','LC_ALL')
    return {name: os.environ[name] for name in names if name in os.environ}
