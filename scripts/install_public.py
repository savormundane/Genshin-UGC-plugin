"""Windows full-bundle installer. Only explicit invocation changes client registration."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile


def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def save(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    pending = p.with_suffix('.pending')
    pending.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(pending, p)


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def preflight(agent, project=None, outputs=None):
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('Complete bundle requires Windows x64')
    if not (3, 11) <= sys.version_info[:2] <= (3, 12):
        raise ValueError('Locked dependencies require Python 3.11-3.12')
    client = shutil.which('codex' if agent == 'codex' else 'claude')
    node = shutil.which('node')
    if not client or not node:
        raise ValueError('Install the selected Agent and Node.js 22+ first; no global installer is run')
    version = subprocess.check_output([node, '--version'], text=True).strip()
    if int(version.lstrip('v').split('.')[0]) < 22:
        raise ValueError('Node.js 22+ required')
    run([client, 'plugin', '--help'], capture_output=True)
    if project is not None:
        if not project.is_dir() or project == Path(project.anchor):
            raise ValueError('Select an existing project, not an entire drive')
        if project.is_relative_to(outputs) or outputs.is_relative_to(project):
            raise ValueError('Project and output directories must be disjoint')
    return client, node


def extract(archive, expected, destination, version):
    if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != expected.lower():
        raise ValueError('Archive SHA-256 mismatch')
    with zipfile.ZipFile(archive) as z:
        seen = set()
        for item in z.infolist():
            path = PurePosixPath(item.filename)
            if (not path.parts or path.parts[0] != 'Genshin-UGC' or '..' in path.parts
                    or '\\' in item.filename or ':' in item.filename or path.is_absolute()
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('Unsafe archive entry: ' + item.filename)
            key = item.filename.rstrip('/').casefold()
            if key in seen or any(p in ('.git', '.venv', '__pycache__') for p in path.parts):
                raise ValueError('Duplicate or private archive entry: ' + item.filename)
            seen.add(key)
        z.extractall(destination)
    bundle = destination / 'Genshin-UGC'
    for name in ('plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
        meta = read_json(bundle / name)
        if meta['name'] != 'genshin-ugc-public' or meta['version'] != version:
            raise ValueError('Wrong plugin identity or version')
    if len(list((bundle / 'skills').glob('*/SKILL.md'))) != 5:
        raise ValueError('Expected five full-bundle Skills')
    for p in ('LICENSE', 'scripts/runtime-requirements.lock', 'scripts/mcp_launcher.cjs', 'vendor/beyond/bundle.json'):
        if not (bundle / p).is_file():
            raise ValueError('Incomplete bundle: ' + p)
    return bundle


def configure_marketplace(home, agent, version, node, config):
    """All client-specific configuration lives in this owned version directory."""
    bundle = home / 'Genshin-UGC'
    market = 'genshin-ugc-download-' + agent + '-' + version.replace('.', '-')
    server = {'type': 'stdio', 'command': node,
              'args': ['${PLUGIN_ROOT}/scripts/mcp_launcher.cjs'],
              'env': {'UGC_RUNTIME_CONFIG': str(config)}}
    save(bundle / 'mcp.json', {'mcpServers': {'genshin-ugc-public-local': server}})
    claude_server = dict(server, args=['${CLAUDE_PLUGIN_ROOT}/scripts/mcp_launcher.cjs'])
    save(bundle / '.mcp.json', {'mcpServers': {'genshin-ugc-public-local': claude_server}})
    save(home / '.agents/plugins/marketplace.json', {
        'name': market, 'interface': {'displayName': 'Genshin-UGC'},
        'plugins': [{'name': 'genshin-ugc-public', 'source': {'source': 'local', 'path': './Genshin-UGC'},
                     'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Productivity'}]})
    save(home / '.claude-plugin/marketplace.json', {
        'name': market, 'owner': {'name': 'Genshin-UGC contributors'},
        'plugins': [{'name': 'genshin-ugc-public', 'source': './Genshin-UGC'}]})
    return market


def activate(client, agent, record, previous):
    install = 'add' if agent == 'codex' else 'install'
    remove = 'remove' if agent == 'codex' else 'uninstall'
    selector = 'genshin-ugc-public@' + record['marketplace']
    run([client, 'plugin', 'marketplace', 'add', record['home']])
    try:
        run([client, 'plugin', install, selector])
        if previous:
            run([client, 'plugin', remove, 'genshin-ugc-public@' + previous['marketplace']])
    except BaseException:
        # Best-effort removal of this attempted registration only. The old bundle remains available.
        subprocess.run([client, 'plugin', remove, selector], check=False)
        subprocess.run([client, 'plugin', 'marketplace', 'remove', record['marketplace']], check=False)
        raise
    if previous:
        subprocess.run([client, 'plugin', 'marketplace', 'remove', previous['marketplace']], check=False)


def operate(args):
    if getattr(args,'resume',False) and args.action!='install':
        raise ValueError('--resume only applies to an unfinished install')
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
        raise ValueError('Version must be x.y.z')
    root = Path(args.root).resolve()
    state_path = root / (args.agent + '.json')
    state = read_json(state_path) if state_path.exists() else {'schema': 1, 'current': None, 'history': []}
    if state.get('schema') != 1:
        raise ValueError('Unknown installation state version')
    project = Path(args.project).resolve() if args.project else None
    outputs = Path(args.outputs).resolve() if args.outputs else None
    if args.action == 'install' and (project is None or outputs is None):
        raise ValueError('Project and outputs are required')
    client, node = preflight(args.agent, project, outputs)
    previous = state['current']
    if args.action == 'uninstall':
        if not previous:
            raise ValueError('No installation owned by this installer')
        remove = 'remove' if args.agent == 'codex' else 'uninstall'
        run([client, 'plugin', remove, 'genshin-ugc-public@' + previous['marketplace']])
        run([client, 'plugin', 'marketplace', 'remove', previous['marketplace']])
        state['history'].append(previous)
        state['current'] = None
        save(state_path, state)
        return {'registration_removed': True, 'retained_for_rollback': str(root)}
    if args.action == 'rollback':
        selected = [r for r in state['history'] if r['version'] == args.version]
        if not selected:
            raise ValueError('No retained installation for this version')
        record = selected[-1]
        if not Path(record['home']).is_relative_to(root) or not Path(record['config']).is_file():
            raise ValueError('Retained installation is unavailable')
        run([record['python'], '-X', 'utf8', '-B', Path(record['home']) / 'Genshin-UGC/scripts/install_smoke.py',
             '--config', record['config'], '--node', node])
        activate(client, args.agent, record, previous)
        state['current'] = record
        state['history'] = [r for r in state['history'] if r != record] + ([previous] if previous else [])
        save(state_path, state)
        return {'rolled_back': args.version, 'agent_host_load': 'not_checked'}
    if not args.archive or not args.sha256:
        raise ValueError('Archive and expected SHA-256 required')
    home = root / 'versions' / args.agent / args.version
    for part in (home,*home.parents):
        if part==root.parent:break
        if part.is_symlink() or (part.exists() and getattr(part.lstat(),'st_file_attributes',0)&1024):
            raise ValueError('Linked installation directory refused')
    journal = home / 'installation-pending.json'
    binding = {'schema': 1, 'version': args.version, 'archive_sha256': args.sha256.lower(),
               'agent': args.agent, 'home': str(home), 'project': str(project), 'outputs': str(outputs)}
    if hashlib.sha256(Path(args.archive).read_bytes()).hexdigest() != binding['archive_sha256']:
        raise ValueError('Archive SHA-256 mismatch')
    if home.exists():
        if any(r and r['home']==str(home) for r in [previous,*state['history']]):
            raise ValueError('Activated versions cannot be resumed or overwritten')
        if not getattr(args,'resume',False) or not journal.is_file():
            raise ValueError('Version directory exists; --resume requires a registered unfinished installation')
        pending=read_json(journal)
        if pending.get('binding')!=binding or pending.get('phase') not in ('dependencies','checks'):
            raise ValueError('Resume parameters differ or activation has already been attempted')
        # Revalidate against the same archive, without executing retained package code first.
        with tempfile.TemporaryDirectory(prefix='resume-check-',dir=home.parent) as td:
            expected=extract(args.archive,args.sha256,Path(td),args.version)
            actual=home/'Genshin-UGC'
            for item in actual.rglob('*'):
                if item.is_symlink() or getattr(item.lstat(),'st_file_attributes',0)&1024:
                    raise ValueError('Linked unfinished bundle refused')
            for item in expected.rglob('*'):
                if item.is_file():
                    target=actual/item.relative_to(expected)
                    if target.is_symlink() or not target.is_file() or target.read_bytes()!=item.read_bytes():
                        raise ValueError('Unfinished bundle differs from the verified archive')
            if {p.relative_to(actual) for p in actual.rglob('*') if p.is_file()}!={p.relative_to(expected) for p in expected.rglob('*') if p.is_file()}:
                raise ValueError('Unregistered file in unfinished bundle')
    else:
        if getattr(args,'resume',False):raise ValueError('No registered unfinished version to resume')
        home.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='extract-', dir=home.parent) as td:
            stage = Path(td)
            extract(args.archive, args.sha256, stage, args.version)
            save(stage/'installation-pending.json',{'binding':binding,'phase':'dependencies'})
            os.replace(stage, home)
    # Not activated yet. Failed dependencies leave a diagnostic copy, never an active half-install.
    config = home / 'runtime.json'
    runtime = home / 'runtime'
    bundle = home / 'Genshin-UGC'
    if not config.exists():
        command=[sys.executable, '-X', 'utf8', '-B', bundle / 'scripts/configure_runtime.py',
                 '--python', sys.executable, '--runtime', runtime, '--project', project,
                 '--outputs', outputs, '--config', config]
        if runtime.exists():command.append('--resume')
        run(command)
    else:
        restored=read_json(config)
        if restored.get('project_root')!=str(project) or restored.get('output_root')!=str(outputs) or restored.get('python')!=str(runtime/'Scripts/python.exe'):
            raise ValueError('Unfinished runtime configuration differs from registered parameters')
    save(journal,{'binding':binding,'phase':'checks'})
    python = runtime / 'Scripts/python.exe'
    run([python, '-X', 'utf8', '-B', bundle / 'scripts/install_smoke.py', '--config', config, '--node', node])
    # Stop permitting automatic resume before mutating registration; interruption here needs rollback review.
    save(journal,{'binding':binding,'phase':'activation'})
    market = configure_marketplace(home, args.agent, args.version, node, config)
    record = {'version': args.version, 'home': str(home), 'config': str(config),
              'python': str(python), 'marketplace': market, 'archive_sha256': args.sha256.lower()}
    activate(client, args.agent, record, previous)
    state['current'] = record
    if previous:
        state['history'].append(previous)
    save(state_path, state)
    journal.unlink()
    return {'installed': args.version, 'agent': args.agent, 'runtime_smoke': 'passed',
            'agent_host_load': 'not_checked', 'next': 'Restart the Agent and verify five Skills and MCP tools'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('install', 'rollback', 'uninstall'))
    p.add_argument('--agent', choices=('codex', 'claude-code'), required=True)
    p.add_argument('--resume',action='store_true')
    for key in ('root', 'version'):
        p.add_argument('--' + key, required=True)
    for key in ('archive', 'sha256', 'project', 'outputs'):
        p.add_argument('--' + key)
    print(json.dumps(operate(p.parse_args()), ensure_ascii=False))
