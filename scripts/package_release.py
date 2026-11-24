"""Package one explicitly selected plugin or single Skill directory."""
from pathlib import Path, PureWindowsPath
import argparse
import hashlib
import json
import os
import re
import tempfile
import zipfile


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_windows_names(names):
    """Reject names Windows would change or map to the same path."""
    entries = set()
    prefixes = {}
    for name in names:
        if name in entries:
            raise ValueError(f'Duplicate archive path: {name!r}')
        entries.add(name)
        name.encode('utf-8')
        parts = name.removesuffix('/').split('/')
        prefix = []
        for index, part in enumerate(parts):
            if (not part or part != part.strip() or part.endswith('.')
                    or re.search(r'[<>:"\\|?*\x00-\x1f]', part)
                    or PureWindowsPath(part).is_reserved()):
                raise ValueError(f'Invalid Windows archive path: {name!r}')
            prefix.append(part)
            current = ('/'.join(prefix), index < len(parts) - 1 or name.endswith('/'))
            prior = prefixes.setdefault(current[0].casefold(), current)
            if prior != current:
                raise ValueError(f'Windows archive path collision: {prior[0]!r} and {name!r}')


def distribution_exclusions(source, *, required=False):
    policy_path = source / 'distribution.json'
    if not required and not policy_path.exists():
        return [], []
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    if (not isinstance(policy, dict) or policy.get('schema') != 1
            or policy.keys() - {'schema', 'exclude_prefixes', 'exclude_files'}
            or not isinstance(policy.get('exclude_prefixes'), list)
            or not isinstance(policy.get('exclude_files', []), list)):
        raise ValueError('Invalid distribution policy')
    prefixes = policy['exclude_prefixes']
    files = policy.get('exclude_files', [])
    if any(not isinstance(p, str) or not p.endswith('/') or p.startswith('/') or ':' in p or '\\' in p or '..' in p.split('/') for p in prefixes):
        raise ValueError('Unsafe distribution exclusion')
    if any(not isinstance(p, str) or ':' in p or '\\' in p
           or any(part in ('', '.', '..') for part in p.split('/')) for p in files):
        raise ValueError('Unsafe distribution file exclusion')
    return prefixes, files


def build_release(source, output, layout='auto', archive_root=None, *, beyond_native_archive=None):
    source, output = Path(source).resolve(), Path(output).absolute()
    if os.path.lexists(output):
        raise FileExistsError(f'Output already exists: {output}')
    output = output.parent.resolve() / output.name
    if not source.is_dir():
        raise ValueError('Source must be a directory')
    if output.is_relative_to(source):
        raise ValueError('Output must be outside the source directory')
    excluded, excluded_files = distribution_exclusions(source)
    archive_root = archive_root or source.name
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', archive_root) or archive_root in ('.', '..'):
        raise ValueError('Invalid archive root')
    files = []
    for f in sorted(source.rglob('*')):
        if f.is_symlink():
            raise ValueError('Symlinks are not packaged: ' + str(f))
        parts = f.relative_to(source).parts
        if any(p in ('.git', '.venv', '__pycache__', '.pytest_cache') for p in parts):
            continue
        relative = '/'.join(parts)
        if (relative in excluded_files or any(relative.startswith(p) for p in excluded)
                or relative in ('.codex/config.toml', '.claude/settings.local.json')):
            continue
        if (f.name in ('AGENTS.md', 'AGENTS.override.md', 'CLAUDE.local.md', '.git-credentials', '.env')
                or f.name.startswith('.env.') and f.name not in ('.env.example', '.env.sample', '.env.template')):
            continue
        if f.is_file() and f.suffix not in ('.pyc', '.pyo'):
            files.append(f)
    if not files:
        raise ValueError('No package files')
    entries = [f for f in files if f.name.lower() == 'skill.md']
    root_skill = source / 'SKILL.md'
    if layout == 'auto':
        layout = 'skill' if root_skill.is_file() else 'plugin'
    if layout == 'plugin':
        manifest = source / '.codex-plugin/plugin.json'
        if not manifest.exists():manifest = source / 'plugin.json'
        m = json.loads(manifest.read_text(encoding='utf-8-sig'))
        declared = m.get('skills', './skills/')
        if not isinstance(declared,str) or not declared.startswith('./') or '..' in Path(declared).parts:
            raise ValueError('Invalid declared skill directory')
        skill_root=(source/declared).resolve()
        if not skill_root.is_relative_to(source) or not skill_root.is_dir():raise ValueError('Declared skill directory missing or outside package')
        entries = [f for f in entries if f.is_relative_to(skill_root)]
    for f in entries:
        text = f.read_text(encoding='utf-8-sig')
        front = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
        if not front:
            raise ValueError('Missing skill frontmatter: ' + str(f))
        for key in ('name', 'description'):
            values = re.findall(r'^' + key + r':\s*([^\r\n]+)$', front[1], re.M)
            if len(values) != 1 or not values[0].strip():
                raise ValueError('Invalid skill ' + key + ': ' + str(f))
    if layout == 'skill':
        if entries != [root_skill]:
            raise ValueError('Single Skill layout requires exactly one root SKILL.md')
    elif layout == 'plugin':
        manifest = source / '.codex-plugin/plugin.json'
        if not manifest.exists():
            manifest = source / 'plugin.json'
        m = json.loads(manifest.read_text(encoding='utf-8-sig'))
        if not m.get('name') or not entries:
            raise ValueError('Plugin identity and skills required')
    else:
        raise ValueError('Unknown layout')
    members = {f.relative_to(source): f for f in files}
    beyond = Path('vendor/beyond')
    native_lock = beyond / 'native-canvas.json'
    locked_members = {}
    if beyond_native_archive is not None and not (source / native_lock).is_file():
        raise ValueError('A Beyond native archive requires vendor/beyond/native-canvas.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ugc-package-', dir=output.parent) as staging:
        staging = Path(staging)
        if (source / native_lock).is_file():
            from beyond_native import (download_native_archive, extract_native_archive,
                                       read_native_lock, verify_native_files)
            if native_lock not in members or beyond / 'bundle.json' not in members:
                raise ValueError('The full Windows ZIP must include the Beyond lock and manifest')
            lock = read_native_lock(source / beyond)
            native_files = {beyond / relative: relative for relative in lock['files']}
            if any(path.as_posix() in excluded_files or path.as_posix().startswith(tuple(excluded))
                   for path in native_files):
                raise ValueError('The full Windows ZIP must include the locked Beyond native files')
            locked_members = {f'{archive_root}/{path.as_posix()}': lock['files'][relative]
                              for path, relative in native_files.items()}
            bundled = verify_native_files(source / beyond, lock)
            if beyond_native_archive is not None or not bundled:
                archive = Path(beyond_native_archive) if beyond_native_archive is not None else staging / 'native-canvas.zip'
                if beyond_native_archive is None:
                    download_native_archive(lock, archive)
                hydrated = staging / 'native-canvas'
                extract_native_archive(lock, archive, hydrated)
                members.update({path: hydrated / relative for path, relative in native_files.items()})
        members = {archive_root + '/' + path.as_posix(): members[path] for path in sorted(members)}
        validate_windows_names(members)
        staged = staging / 'package.zip'
        with zipfile.ZipFile(staged, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member, f in members.items():
                info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                contents = f.read_bytes()
                if member in locked_members and hashlib.sha256(contents).hexdigest() != locked_members[member]:
                    raise ValueError(f'ZIP native Canvas member SHA-256 mismatch: {member}')
                archive.writestr(info, contents)
        with tempfile.TemporaryDirectory(prefix='ugc-zip-check-') as temporary, zipfile.ZipFile(staged) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC failed')
            zip_entries = archive.infolist()
            if [entry.filename for entry in zip_entries] != list(members):
                raise ValueError('ZIP entry names differ from source')
            unicode_names = [entry for entry in zip_entries if not entry.filename.isascii()]
            if any(not entry.flag_bits & 0x800 for entry in unicode_names):
                raise ValueError('Non-ASCII ZIP names must carry the UTF-8 flag')
            archive.extractall(temporary)
            unpacked = Path(temporary)
            restored = {f.relative_to(unpacked).as_posix() for f in unpacked.rglob('*') if f.is_file()}
            if restored != set(members):
                raise ValueError('Extracted file names differ from ZIP entries')
            for member, original in members.items():
                if (unpacked / member).read_bytes() != original.read_bytes():
                    raise ValueError('Extracted bytes differ from source: ' + member)
        file_size = staged.stat().st_size
        digest = sha256_file(staged)
        largest_file_bytes = max(path.stat().st_size for path in members.values())
        if os.name == 'nt':
            staged.rename(output)
        else:
            # POSIX rename overwrites a file created during the build.
            os.link(staged, output)
    return {'layout': layout, 'excluded_prefixes': excluded, 'excluded_files': excluded_files,
            'files': len(members), 'skills': len(entries),
            'zip_bytes': file_size,
            'largest_file_bytes': largest_file_bytes,
            'sha256': digest,
            'archive_content_verified': True, 'extracted_names_verified': True,
            'utf8_entries': len(unicode_names), 'agent_installation_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--layout', choices=['auto', 'skill', 'plugin'], default='auto')
    parser.add_argument('--archive-root')
    parser.add_argument('--beyond-native-archive', type=Path,
                        help='Use a local Beyond Windows x64 release asset verified against the source lock')
    args = parser.parse_args()
    print(json.dumps(build_release(args.source, args.out, args.layout, args.archive_root,
                                   beyond_native_archive=args.beyond_native_archive)))
