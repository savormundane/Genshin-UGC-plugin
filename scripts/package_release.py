"""Package one explicitly selected plugin or single Skill directory."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import zipfile


def build_release(source, output, layout='auto', archive_root=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_dir():
        raise ValueError('Source must be a directory')
    if output.is_relative_to(source):
        raise ValueError('Output must be outside the source directory')
    policy_path = source / 'distribution.json'
    policy = json.loads(policy_path.read_text(encoding='utf-8')) if policy_path.exists() else {'schema': 1, 'exclude_prefixes': []}
    if not isinstance(policy, dict) or set(policy) != {'schema', 'exclude_prefixes'} or policy['schema'] != 1 or not isinstance(policy['exclude_prefixes'], list):
        raise ValueError('Invalid distribution policy')
    excluded = policy['exclude_prefixes']
    if any(not isinstance(p, str) or not p.endswith('/') or p.startswith('/') or ':' in p or '\\' in p or '..' in p.split('/') for p in excluded):
        raise ValueError('Unsafe distribution exclusion')
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
        if f.is_file() and f.name not in ('AGENTS.md', '.env', '.env.local') and f.suffix not in ('.pyc','.pyo') and not any(f.relative_to(source).as_posix().startswith(p) for p in excluded):
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
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for f in files:
            member = archive_root + '/' + f.relative_to(source).as_posix()
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, f.read_bytes())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        for f in files:
            member = archive_root + '/' + f.relative_to(source).as_posix()
            if archive.read(member) != f.read_bytes():
                raise ValueError('Archive differs from source: ' + member)
    return {'layout': layout, 'excluded_prefixes': excluded, 'files': len(files), 'skills': len(entries),
            'zip_bytes': output.stat().st_size,
            'largest_file_bytes': max(f.stat().st_size for f in files),
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'archive_content_verified': True, 'agent_installation_tested': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--layout', choices=['auto', 'skill', 'plugin'], default='auto')
    parser.add_argument('--archive-root')
    args = parser.parse_args()
    print(json.dumps(build_release(args.source, args.out, args.layout, args.archive_root)))
