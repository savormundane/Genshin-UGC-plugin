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

MANUAL_AGENTS = ('agent-plugins', 'deepseek-harness')
AGENTS = ('codex', 'claude-code', *MANUAL_AGENTS)
MCP_SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json'
MCP_NAME = 'genshin-ugc-public-local'


def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def save(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    pending = p.with_suffix('.pending')
    pending.write_text(json_text(data), encoding='utf-8')
    os.replace(pending, p)


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def preflight(agent, project=None, outputs=None):
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('Complete bundle requires Windows x64')
    if not (3, 11) <= sys.version_info[:2] <= (3, 12):
        raise ValueError('Locked dependencies require Python 3.11-3.12')
    client = None if agent in MANUAL_AGENTS else shutil.which('codex' if agent == 'codex' else 'claude')
    node = shutil.which('node')
    if not node or (agent not in MANUAL_AGENTS and not client):
        raise ValueError('Install Node.js and the selected client first. No global installer is run.')
    version = subprocess.check_output([node, '--version'], text=True).strip()
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', version)
    minimum = (24, 9, 0) if agent == 'deepseek-harness' else (22, 0, 0)
    if not match or tuple(map(int, match.groups())) < minimum:
        raise ValueError('Node.js ' + '.'.join(map(str, minimum)) + '+ required')
    if client:
        run([client, 'plugin', '--help'], capture_output=True)
    if project is not None:
        if not project.is_dir() or project == Path(project.anchor):
            raise ValueError('Select an existing project, not an entire drive')
        if project.is_relative_to(outputs) or outputs.is_relative_to(project):
            raise ValueError('Project and output directories must be disjoint')
    return client, node


def archive_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(archive, expected, destination, version):
    if archive_sha256(archive) != expected.lower():
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


def marketplace_files(agent, version, node, config):
    market = 'genshin-ugc-download-' + agent + '-' + version.replace('.', '-')
    server = {'type': 'stdio', 'command': 'node',
              'args': ['${PLUGIN_ROOT}/scripts/mcp_launcher.cjs'],
              'env': {'UGC_RUNTIME_CONFIG': str(config)}}
    if agent == 'deepseek-harness':
        bundle = config.parent / 'Genshin-UGC'
        # The Cordis YAML loader accepts JSON. Using the existing serializer keeps Windows paths
        # and Unicode lossless without evaluating expressions or interpolating YAML strings.
        patch = [{'insert': [
            {'id': 'genshin-ugc-skills', 'name': '@deepseek-ai/dsh-skill-filesystem',
             'config': {'providerName': 'genshin-ugc-public', 'includeDefaultRoots': False,
                        'customSkillDirs': [str(bundle / 'skills')]}},
            {'id': 'genshin-ugc-mcp', 'name': '@deepseek-ai/dsh-mcp-client',
             'config': {'serverName': 'genshin_ugc', 'transport': 'stdio', 'command': node,
                        'args': [str(bundle / 'scripts/mcp_launcher.cjs')], 'env': server['env'],
                        'cwd': str(bundle), 'toolCallTimeoutMs': 930000, 'failOnStartupError': True}},
        ]}]
        return None, {
            Path('cordis-bundle/package.json'): {
                'name': '@local/genshin-ugc-public', 'version': version, 'private': True,
                'description': 'Genshin-UGC Skills and local MCP for DeepSeek Harness',
                'engines': {'dsh': '0.2.2-rc.5'}, 'files': ['cordis.patch.yml'],
                'dsh': {'bundle': {'patch': './cordis.patch.yml'}}},
            Path('cordis-bundle/cordis.patch.yml'): patch,
        }
    if agent == 'claude-code':
        server.update(command=node, args=['${CLAUDE_PLUGIN_ROOT}/scripts/mcp_launcher.cjs'])
        return market, {
            Path('Genshin-UGC/.mcp.json'): {'mcpServers': {MCP_NAME: server}},
            Path('.claude-plugin/marketplace.json'): {
                'name': market, 'owner': {'name': 'Genshin-UGC contributors'},
                'plugins': [{'name': 'genshin-ugc-public', 'source': './Genshin-UGC'}]},
        }
    files = {Path('Genshin-UGC/mcp.json'): {'$schema': MCP_SCHEMA, 'mcpServers': {MCP_NAME: server}}}
    if agent == 'agent-plugins':
        return None, files
    files[Path('.agents/plugins/marketplace.json')] = {
        'name': market, 'interface': {'displayName': 'Genshin-UGC'},
        'plugins': [{'name': 'genshin-ugc-public', 'source': {'source': 'local', 'path': './Genshin-UGC'},
                     'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'}, 'category': 'Productivity'}],
    }
    return market, files


def linked(path):
    return path.is_symlink() or (path.exists() and bool(getattr(path.lstat(), 'st_file_attributes', 0) & 1024))


def configure_marketplace(home, agent, version, node, config):
    """All client-specific configuration lives in this owned version directory."""
    market, files = marketplace_files(agent, version, node, config)
    for relative, data in files.items():
        target = home / relative
        if any(linked(home / part) for part in (relative, *relative.parents)) or linked(target.with_suffix('.pending')):
            raise ValueError(f'Linked marketplace configuration refused: {relative}')
        save(target, data)
    return market


def verify_unfinished_bundle(home, archive, binding, generated):
    """Compare all retained files with the archive or exact installer-generated configuration."""
    with tempfile.TemporaryDirectory(prefix='resume-check-', dir=home.parent) as temporary:
        extracted = extract(archive, binding['archive_sha256'], Path(temporary), binding['version'])
        bundle = home / 'Genshin-UGC'
        if linked(bundle) or not bundle.is_dir():
            raise ValueError('Linked or missing unfinished bundle')
        expected = {path.relative_to(extracted.parent): path for path in extracted.rglob('*') if path.is_file()}
        actual = {}
        for path in bundle.rglob('*'):
            if linked(path):
                raise ValueError(f'Linked unfinished bundle entry refused: {path.relative_to(home)}')
            if path.is_file():
                actual[path.relative_to(home)] = path
        if expected.keys() - actual.keys() or actual.keys() - expected.keys() - generated.keys():
            raise ValueError('Missing or unregistered file in unfinished bundle')
        for relative, data in generated.items():
            if any(linked(home / part) for part in (relative, *relative.parents)):
                raise ValueError(f'Linked marketplace configuration refused: {relative}')
            candidate = home / relative
            if candidate.exists():
                actual[relative] = candidate
        for relative, path in actual.items():
            data = path.read_bytes()
            if relative in expected and data == expected[relative].read_bytes():
                continue
            if relative in generated and data == json_text(generated[relative]).replace('\n', os.linesep).encode('utf-8'):
                continue
            raise ValueError(f'Unfinished bundle differs from archive or installer configuration: {relative}')


def run_codex_plugin(client, *arguments):
    try:
        return run([client, 'plugin', *arguments], capture_output=True, encoding='utf-8', timeout=90).stdout
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or '').strip()
        raise RuntimeError(f"Codex plugin {' '.join(str(value) for value in arguments)} failed ({error.returncode}): {detail}") from error


def codex_registration(client, record):
    """Use the scoped CLI query so unrelated marketplaces do not affect recovery."""
    marketplace = record['marketplace']
    result = json.loads(run_codex_plugin(client, 'list', '--marketplace', marketplace, '--available', '--json'))
    rows = result['installed'] + result['available']
    if not rows:
        return None
    selector = 'genshin-ugc-public@' + marketplace
    if len(rows) != 1 or rows[0].get('pluginId') != selector:
        raise ValueError(f'Unexpected Codex registration for {marketplace}')
    row = rows[0]
    source = row.get('source', {})
    market_source = row.get('marketplaceSource', {})
    source_path = Path(source.get('path', ''))
    market_path = Path(market_source.get('source', ''))
    root = Path(record['home']).resolve()
    if (row.get('version') != record['version'] or source.get('source') != 'local'
            or market_source.get('sourceType') != 'local'
            or not source_path.is_absolute() or not source_path.samefile(root / 'Genshin-UGC')
            or not market_path.is_absolute() or not market_path.samefile(root)):
        raise ValueError(f'Codex registration source or version differs for {selector}')
    if row.get('installed') is not bool(result['installed']) or type(row.get('enabled')) is not bool:
        raise ValueError(f'Codex returned an unknown installation state for {selector}')
    return row


def ensure_codex_active(client, record):
    selector = 'genshin-ugc-public@' + record['marketplace']
    registration = codex_registration(client, record)
    if registration is None:
        # Codex refuses an existing name attached to another source.
        run_codex_plugin(client, 'marketplace', 'add', record['home'])
        registration = codex_registration(client, record)
        if registration is None:
            raise ValueError(f'Codex did not expose the added marketplace for {selector}')
    if not registration.get('installed'):
        run_codex_plugin(client, 'add', selector, '--json')
        registration = codex_registration(client, record)
    if not registration or not registration.get('installed') or not registration.get('enabled'):
        raise ValueError(f'Codex has not installed and enabled {selector}')
def retire_codex_registration(client, record):
    owned = codex_registration(client, record)
    if owned and owned['installed']:
        run_codex_plugin(client, 'remove', owned['pluginId'])
        owned = codex_registration(client, record)
        if owned and owned['installed']:
            raise ValueError(f"Codex still reports the plugin as installed: {owned['pluginId']}")
    if owned:
        run_codex_plugin(client, 'marketplace', 'remove', record['marketplace'])
        if codex_registration(client, record) is not None:
            raise ValueError(f"Codex still reports the marketplace: {record['marketplace']}")


def activate_codex_install(client, record, previous, state, state_path):
    ensure_codex_active(client, record)
    if state['current'] != record:
        state['current'] = record
        if previous:
            state['history'].append(previous)
        save(state_path, state)
    if previous:
        retire_codex_registration(client, previous)


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
    manual = args.agent in MANUAL_AGENTS
    if manual and args.action != 'install':
        raise ValueError('Manage registration and rollback in the host. The prepared files are retained.')
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
    codex = args.agent == 'codex'
    pending_retirement = state.get('pending_rollback_retirement') if codex else None
    if pending_retirement and (args.action != 'rollback' or not previous or args.version != previous['version']):
        raise ValueError('Complete the pending Codex rollback with the current version before another operation')
    if args.action == 'uninstall':
        result = {'registration_removed': True, 'retained_for_rollback': str(root)}
        if not previous:
            if codex and state['history']:
                return result
            raise ValueError('No installation owned by this installer')
        if codex:
            retire_codex_registration(client, previous)
        else:
            run([client, 'plugin', 'uninstall', 'genshin-ugc-public@' + previous['marketplace']])
            run([client, 'plugin', 'marketplace', 'remove', previous['marketplace']])
        state['history'].append(previous)
        state['current'] = None
        save(state_path, state)
        return result
    if args.action == 'rollback':
        selected = [r for r in state['history'] if r['version'] == args.version]
        if codex and previous and previous['version'] == args.version:
            selected.append(previous)
        if not selected:
            raise ValueError('No retained installation for this version')
        record = selected[-1]
        if not Path(record['home']).is_relative_to(root) or not Path(record['config']).is_file():
            raise ValueError('Retained installation is unavailable')
        run([record['python'], '-X', 'utf8', '-B', Path(record['home']) / 'Genshin-UGC/scripts/install_smoke.py',
             '--config', record['config'], '--node', node])
        if codex:
            ensure_codex_active(client, record)
        else:
            activate(client, args.agent, record, previous)
        if previous != record:
            state['current'] = record
            state['history'] = [r for r in state['history'] if r != record] + ([previous] if previous else [])
            if codex and previous:
                state['pending_rollback_retirement'] = previous
            save(state_path, state)
        if codex and state.get('pending_rollback_retirement'):
            retire_codex_registration(client, state['pending_rollback_retirement'])
            state.pop('pending_rollback_retirement')
            save(state_path, state)
        return {'rolled_back': args.version, 'agent_host_load': 'not_checked'}
    if not args.archive or not args.sha256:
        raise ValueError('Archive and expected SHA-256 required')
    home = root / 'versions' / args.agent / args.version
    for part in (home,*home.parents):
        if part==root.parent:break
        if linked(part):
            raise ValueError('Linked installation directory refused')
    journal = home / 'installation-pending.json'
    config = home / 'runtime.json'
    runtime = home / 'runtime'
    bundle = home / 'Genshin-UGC'
    python = runtime / 'Scripts/python.exe'
    market, generated = marketplace_files(args.agent, args.version, node, config)
    binding = {'schema': 1, 'version': args.version, 'archive_sha256': args.sha256.lower(),
               'agent': args.agent, 'home': str(home), 'project': str(project), 'outputs': str(outputs)}
    record = {'version': args.version, 'home': str(home), 'config': str(config),
              'python': str(python), 'marketplace': market, 'archive_sha256': binding['archive_sha256']}
    if archive_sha256(args.archive) != binding['archive_sha256']:
        raise ValueError('Archive SHA-256 mismatch')
    recovering_activation = False
    if home.exists():
        if manual and os.path.lexists(home / 'preparation.json'):
            raise ValueError('This version is already prepared. Use its existing directory in the host.')
        if linked(journal):
            raise ValueError('Linked installation journal refused')
        pending = read_json(journal) if getattr(args, 'resume', False) and journal.is_file() else None
        recovering_activation = args.agent == 'codex' and pending is not None and pending.get('phase') == 'activation'
        if any(r and r['home'] == str(home) for r in [previous, *state['history']]) and not (
                recovering_activation and previous == record):
            raise ValueError('Activated versions cannot be resumed or overwritten')
        if pending is None:
            raise ValueError('Version directory exists; --resume requires a registered unfinished installation')
        if pending.get('binding') != binding:
            raise ValueError('Resume parameters differ from the unfinished installation')
        if recovering_activation:
            if pending.get('record') != record or pending.get('node') != node or 'previous' not in pending:
                raise ValueError('Codex activation record is incomplete or its parameters have changed')
            original = pending['previous']
            if previous == record:
                if original is not None and original not in state['history']:
                    raise ValueError('Previous Codex installation is missing from history')
            elif previous != original:
                raise ValueError('Current Codex installation changed since activation began')
            previous = original
        elif pending.get('phase') not in ('dependencies', 'checks', *(['preparation'] if manual else [])):
            raise ValueError('Activation has already been attempted and cannot be resumed for this Agent')
        verify_unfinished_bundle(home, args.archive, binding,
                                 generated if recovering_activation or (manual and pending.get('phase') == 'preparation') else {})
    else:
        if getattr(args,'resume',False):raise ValueError('No registered unfinished version to resume')
        home.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='extract-', dir=home.parent) as td:
            stage = Path(td)
            extract(args.archive, args.sha256, stage, args.version)
            save(stage/'installation-pending.json',{'binding':binding,'phase':'dependencies'})
            os.replace(stage, home)
    # Not activated yet. Failed dependencies leave a diagnostic copy, never an active half-install.
    if not config.exists():
        if recovering_activation:
            raise ValueError('Runtime configuration is missing from the interrupted Codex activation')
        command=[sys.executable, '-X', 'utf8', '-B', bundle / 'scripts/configure_runtime.py',
                 '--python', sys.executable, '--runtime', runtime, '--project', project,
                 '--outputs', outputs, '--config', config]
        if runtime.exists():command.append('--resume')
        run(command)
    else:
        restored=read_json(config)
        if restored.get('project_root')!=str(project) or restored.get('output_root')!=str(outputs) or restored.get('python')!=str(runtime/'Scripts/python.exe'):
            raise ValueError('Unfinished runtime configuration differs from registered parameters')
    smoke = [python, '-X', 'utf8', '-B', bundle / 'scripts/install_smoke.py', '--config', config, '--node', node]
    if manual:
        save(journal, {'binding': binding, 'phase': 'preparation'})
        configure_marketplace(home, args.agent, args.version, node, config)
        run([*smoke, '--adapter', args.agent])
        result = {'prepared': args.version, 'agent': args.agent, 'runtime_smoke': 'passed',
                  'registration': 'pending_host_registration', 'agent_host_load': 'not_checked',
                  'plugin_directory': str(bundle), 'config': str(config)}
        if args.agent == 'deepseek-harness':
            result.update(bundle_directory=str(home / 'cordis-bundle'),
                          next='Add the bundle directory in DeepSeek Harness Plugins for the selected profile.')
        else:
            result['next'] = 'Use your host\'s local Agent Plugin import with plugin_directory.'
        save(home / 'preparation.json', result)
        journal.unlink()
        return result
    if not recovering_activation:
        save(journal, {'binding': binding, 'phase': 'checks'})
    run(smoke)
    activation = {'binding': binding, 'phase': 'activation'}
    if args.agent == 'codex':
        activation.update(record=record, previous=previous, node=node)
        save(journal, activation)
        try:
            configure_marketplace(home, args.agent, args.version, node, config)
            activate_codex_install(client, record, previous, state, state_path)
        except (ValueError, RuntimeError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
            save(journal, {**activation, 'last_error': str(error)})
            raise ValueError(f'Codex activation remains pending: {error}. Diagnose this state and use --resume with the same inputs.') from error
    else:
        save(journal, activation)
        configure_marketplace(home, args.agent, args.version, node, config)
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
    p.add_argument('--agent', choices=AGENTS, required=True)
    p.add_argument('--resume',action='store_true')
    for key in ('root', 'version'):
        p.add_argument('--' + key, required=True)
    for key in ('archive', 'sha256', 'project', 'outputs'):
        p.add_argument('--' + key)
    print(json.dumps(operate(p.parse_args()), ensure_ascii=False))
