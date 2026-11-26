"""Windows full-bundle installer. Only explicit invocation changes client registration."""
from pathlib import Path, PurePosixPath
import argparse
from contextlib import contextmanager
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
from runtime_policy import PYTHON_RANGE, supported_python

MANUAL_AGENTS = ('agent-plugins',)
AGENTS = ('codex', 'claude-code', *MANUAL_AGENTS)
MCP_SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json'
MCP_NAME = 'miliastra-wonderland'


def read_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def generated_bytes(data):
    return data if isinstance(data, bytes) else json_text(data).replace('\n', os.linesep).encode('utf-8')


def save(p, data):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    pending = p.with_suffix('.pending')
    pending.write_bytes(generated_bytes(data))
    os.replace(pending, p)


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def preflight(agent, project=None, outputs=None):
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('完整安装包需要 Windows x64。')
    if not supported_python(sys.version_info):
        raise ValueError(f'锁定的依赖需要 CPython {PYTHON_RANGE}。')
    client = None if agent in MANUAL_AGENTS else shutil.which('codex' if agent == 'codex' else 'claude')
    node = shutil.which('node')
    if not node or (agent not in MANUAL_AGENTS and not client):
        raise ValueError('请先安装 Node.js 和所选客户端，并确认终端能找到对应命令。')
    version = subprocess.check_output([node, '--version'], text=True).strip()
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (22, 0, 0):
        raise ValueError('请安装 Node.js 22.0.0 或更高版本。')
    if client:
        run([client, 'plugin', '--help'], capture_output=True)
    if project is not None:
        if not project.is_dir() or project == Path(project.anchor):
            raise ValueError('请选择已有工程目录，避免选择整个盘符。')
        if project.is_relative_to(outputs) or outputs.is_relative_to(project):
            raise ValueError('工程目录和输出目录不能互相包含。')
    return client, node


def archive_sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def extract(archive, expected, destination, version):
    if archive_sha256(archive) != expected.lower():
        raise ValueError('ZIP 的 SHA-256 校验失败。请核对安装包和打包输出的摘要。')
    bundle = destination / 'miliastra-wonderland'
    with zipfile.ZipFile(archive) as z:
        wrapped = 'plugin.json' not in z.namelist()
        seen = set()
        for item in z.infolist():
            path = PurePosixPath(item.filename)
            if (not path.parts or (wrapped and path.parts[0] != 'miliastra-wonderland') or '..' in path.parts
                    or '\\' in item.filename or ':' in item.filename or path.is_absolute()
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('ZIP 包含不安全的路径 ' + item.filename)
            key = item.filename.rstrip('/').casefold()
            if key in seen or any(p in ('.git', '.venv', '__pycache__') for p in path.parts):
                raise ValueError('ZIP 包含重复或不应随包分发的文件 ' + item.filename)
            seen.add(key)
        z.extractall(destination if wrapped else bundle)
    for name in ('plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
        meta = read_json(bundle / name)
        if meta['name'] != 'miliastra-wonderland' or meta['version'] != version:
            raise ValueError('ZIP 中的插件标识或版本与安装参数不符。')
    required_skills = {'miliastra-editor', 'miliastra-graph-code', 'miliastra-gil', 'miliastra-assets'}
    skills = {path.parent.name for path in (bundle / 'skills').glob('*/SKILL.md')}
    if skills != required_skills:
        raise ValueError('ZIP 中的 Skill 不符合完整安装包清单。')
    for p in ('LICENSE', 'scripts/runtime-requirements.lock', 'scripts/mcp_launcher.cjs', 'vendor/beyond/bundle.json'):
        if not (bundle / p).is_file():
            raise ValueError('安装包缺少文件 ' + p)
    return bundle


@contextmanager
def staged_bundle(root, archive, expected, version):
    # Keep extraction shallow and on the same volume as the version directory.
    with tempfile.TemporaryDirectory(prefix='mw-', dir=root) as temporary:
        yield extract(archive, expected, Path(temporary), version)


def marketplace_files(agent, version, node, config):
    market = 'miliastra-wonderland-download-' + agent + '-' + version.replace('.', '-')
    server = {'type': 'stdio', 'command': 'node',
              'args': ['${PLUGIN_ROOT}/scripts/mcp_launcher.cjs'],
              'env': {'MILIASTRA_WONDERLAND_RUNTIME_CONFIG': str(config)}}
    if agent == 'claude-code':
        server.update(command=node, args=['${CLAUDE_PLUGIN_ROOT}/scripts/mcp_launcher.cjs'])
        return market, {
            Path('miliastra-wonderland/.mcp.json'): {'mcpServers': {MCP_NAME: server}},
            Path('.claude-plugin/marketplace.json'): {
                'name': market, 'owner': {'name': 'Miliastra Wonderland contributors'},
                'plugins': [{'name': 'miliastra-wonderland', 'source': './miliastra-wonderland'}]},
        }
    files = {Path('miliastra-wonderland/mcp.json'): {'$schema': MCP_SCHEMA, 'mcpServers': {MCP_NAME: server}}}
    if agent == 'agent-plugins':
        return None, files
    files[Path('.agents/plugins/marketplace.json')] = {
        'name': market, 'interface': {'displayName': 'Miliastra Wonderland'},
        'plugins': [{'name': 'miliastra-wonderland', 'source': {'source': 'local', 'path': './miliastra-wonderland'},
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
            raise ValueError(f'市场配置路径是链接，无法写入 {relative}')
        save(target, data)
    return market


def verify_unfinished_bundle(root, home, archive, binding, generated):
    """Compare all retained files with the archive or exact installer-generated configuration."""
    with staged_bundle(root, archive, binding['archive_sha256'], binding['version']) as extracted:
        bundle = home / 'miliastra-wonderland'
        if linked(bundle) or not bundle.is_dir():
            raise ValueError('未完成安装的目录缺失或指向链接。')
        expected = {path.relative_to(extracted.parent): path for path in extracted.rglob('*') if path.is_file()}
        actual = {}
        for path in bundle.rglob('*'):
            if linked(path):
                raise ValueError(f'未完成安装中的文件路径指向链接 {path.relative_to(home)}')
            if path.is_file():
                actual[path.relative_to(home)] = path
        if expected.keys() - actual.keys() or actual.keys() - expected.keys() - generated.keys():
            raise ValueError('未完成安装中有缺失或未登记的文件。')
        for relative, data in generated.items():
            if any(linked(home / part) for part in (relative, *relative.parents)):
                raise ValueError(f'市场配置路径是链接，无法写入 {relative}')
            candidate = home / relative
            if candidate.exists():
                actual[relative] = candidate
        for relative, path in actual.items():
            data = path.read_bytes()
            if relative in expected and data == expected[relative].read_bytes():
                continue
            if relative in generated and data == generated_bytes(generated[relative]):
                continue
            raise ValueError(f'未完成的安装与 ZIP 或安装器配置不一致。文件 {relative}')


def run_codex_plugin(client, *arguments):
    try:
        return run([client, 'plugin', *arguments], capture_output=True, encoding='utf-8', timeout=90).stdout
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or '').strip()
        raise RuntimeError(f"Codex 命令 plugin {' '.join(str(value) for value in arguments)} 执行失败，退出码 {error.returncode}。\n详细原因 {detail}") from error


def codex_registration(client, record):
    """Use the scoped CLI query so unrelated marketplaces do not affect recovery."""
    marketplace = record['marketplace']
    result = json.loads(run_codex_plugin(client, 'list', '--marketplace', marketplace, '--available', '--json'))
    rows = result['installed'] + result['available']
    if not rows:
        return None
    selector = 'miliastra-wonderland@' + marketplace
    if len(rows) != 1 or rows[0].get('pluginId') != selector:
        raise ValueError(f'Codex 返回的市场登记与预期不符。市场 {marketplace}')
    row = rows[0]
    source = row.get('source', {})
    market_source = row.get('marketplaceSource', {})
    source_path = Path(source.get('path', ''))
    market_path = Path(market_source.get('source', ''))
    root = Path(record['home']).resolve()
    if (row.get('version') != record['version'] or source.get('source') != 'local'
            or market_source.get('sourceType') != 'local'
            or not source_path.is_absolute() or not source_path.samefile(root / 'miliastra-wonderland')
            or not market_path.is_absolute() or not market_path.samefile(root)):
        raise ValueError(f'Codex 登记的来源或版本不一致。插件 {selector}')
    if row.get('installed') is not bool(result['installed']) or type(row.get('enabled')) is not bool:
        raise ValueError(f'Codex 返回了无法识别的安装状态。插件 {selector}')
    return row


def ensure_codex_active(client, record):
    selector = 'miliastra-wonderland@' + record['marketplace']
    registration = codex_registration(client, record)
    if registration is None:
        # Codex refuses an existing name attached to another source.
        run_codex_plugin(client, 'marketplace', 'add', record['home'])
        registration = codex_registration(client, record)
        if registration is None:
            raise ValueError(f'Codex 中找不到新登记的插件市场。插件 {selector}')
    if not registration.get('installed'):
        run_codex_plugin(client, 'add', selector, '--json')
        registration = codex_registration(client, record)
    if not registration or not registration.get('installed') or not registration.get('enabled'):
        raise ValueError(f'请确认 Codex 已安装并启用 {selector}。')
def retire_codex_registration(client, record):
    owned = codex_registration(client, record)
    if owned and owned['installed']:
        run_codex_plugin(client, 'remove', owned['pluginId'])
        owned = codex_registration(client, record)
        if owned and owned['installed']:
            raise ValueError(f"Codex 仍显示插件已安装 {owned['pluginId']}")
    if owned:
        run_codex_plugin(client, 'marketplace', 'remove', record['marketplace'])
        if codex_registration(client, record) is not None:
            raise ValueError(f"Codex 仍显示市场已登记 {record['marketplace']}")


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
    selector = 'miliastra-wonderland@' + record['marketplace']
    run([client, 'plugin', 'marketplace', 'add', record['home']])
    try:
        run([client, 'plugin', install, selector])
        if previous:
            run([client, 'plugin', remove, 'miliastra-wonderland@' + previous['marketplace']])
    except BaseException:
        # Best-effort removal of this attempted registration only. The old bundle remains available.
        subprocess.run([client, 'plugin', remove, selector], check=False)
        subprocess.run([client, 'plugin', 'marketplace', 'remove', record['marketplace']], check=False)
        raise
    if previous:
        subprocess.run([client, 'plugin', 'marketplace', 'remove', previous['marketplace']], check=False)


def operate(args):
    if args.agent not in AGENTS:
        raise ValueError('此客户端不支持通过本地安装器安装。请查看安装指南。')
    manual = args.agent in MANUAL_AGENTS
    if manual and args.action != 'install':
        raise ValueError('请在对应客户端中管理插件登记、回退或卸载。已准备的文件保存在本地。')
    if getattr(args,'resume',False) and args.action!='install':
        raise ValueError('--resume 仅用于继续未完成的安装。')
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.version):
        raise ValueError('版本需使用 x.y.z 格式。')
    root = Path(args.root).resolve()
    state_path = root / (args.agent + '.json')
    state = read_json(state_path) if state_path.exists() else {'schema': 1, 'current': None, 'history': []}
    if state.get('schema') != 1:
        raise ValueError('无法识别安装记录的版本。')
    project = Path(args.project).resolve() if args.project else None
    outputs = Path(args.outputs).resolve() if args.outputs else None
    if args.action == 'install' and (project is None or outputs is None):
        raise ValueError('请指定工程目录和独立输出目录。')
    client, node = preflight(args.agent, project, outputs)
    previous = state['current']
    codex = args.agent == 'codex'
    pending_retirement = state.get('pending_rollback_retirement') if codex else None
    if pending_retirement and (args.action != 'rollback' or not previous or args.version != previous['version']):
        raise ValueError('请先用当前版本完成尚未结束的 Codex 回退。')
    if args.action == 'uninstall':
        result = {'registration_removed': True, 'retained_for_rollback': str(root)}
        if not previous:
            if codex and state['history']:
                return result
            raise ValueError('当前目录没有此安装器登记的安装记录。')
        if codex:
            retire_codex_registration(client, previous)
        else:
            run([client, 'plugin', 'uninstall', 'miliastra-wonderland@' + previous['marketplace']])
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
            raise ValueError('找不到这个版本的保留安装。')
        record = selected[-1]
        if not Path(record['home']).is_relative_to(root) or not Path(record['config']).is_file():
            raise ValueError('无法访问保留的安装目录。')
        run([record['python'], '-X', 'utf8', '-B', Path(record['home']) / 'miliastra-wonderland/scripts/install_smoke.py',
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
        raise ValueError('请提供本地安装 ZIP 及其 SHA-256。')
    home = root / 'versions' / args.agent / args.version
    for part in (home,*home.parents):
        if part==root.parent:break
        if linked(part):
            raise ValueError('安装目录指向链接。请选择实际目录。')
    journal = home / 'installation-pending.json'
    config = home / 'runtime.json'
    runtime = home / 'runtime'
    bundle = home / 'miliastra-wonderland'
    python = runtime / 'Scripts/python.exe'
    market, generated = marketplace_files(args.agent, args.version, node, config)
    binding = {'schema': 1, 'version': args.version, 'archive_sha256': args.sha256.lower(),
               'agent': args.agent, 'home': str(home), 'project': str(project), 'outputs': str(outputs)}
    record = {'version': args.version, 'home': str(home), 'config': str(config),
              'python': str(python), 'marketplace': market, 'archive_sha256': binding['archive_sha256']}
    if archive_sha256(args.archive) != binding['archive_sha256']:
        raise ValueError('ZIP 的 SHA-256 校验失败。请核对安装包和打包输出的摘要。')
    recovering_activation = False
    if home.exists():
        if manual and os.path.lexists(home / 'preparation.json'):
            raise ValueError('此版本的文件已准备好。请在客户端中使用已有的安装目录。')
        if linked(journal):
            raise ValueError('安装进度记录的路径指向链接。')
        pending = read_json(journal) if getattr(args, 'resume', False) and journal.is_file() else None
        recovering_activation = args.agent == 'codex' and pending is not None and pending.get('phase') == 'activation'
        if any(r and r['home'] == str(home) for r in [previous, *state['history']]) and not (
                recovering_activation and previous == record):
            raise ValueError('该版本已启用。请在客户端管理它，或选择其他版本安装。')
        if pending is None:
            raise ValueError('版本目录已存在。只有已登记的未完成安装可以使用 --resume。')
        if pending.get('binding') != binding:
            raise ValueError('继续安装的参数与原安装记录不一致。请使用原参数。')
        if recovering_activation:
            if pending.get('record') != record or pending.get('node') != node or 'previous' not in pending:
                raise ValueError('Codex 启用记录不完整，或安装参数已变化。')
            original = pending['previous']
            if previous == record:
                if original is not None and original not in state['history']:
                    raise ValueError('在安装历史中找不到此前的 Codex 安装记录。')
            elif previous != original:
                raise ValueError('Codex 当前安装在启用过程中发生了变化。')
            previous = original
        elif pending.get('phase') not in ('dependencies', 'checks', *(['preparation'] if manual else [])):
            raise ValueError('此客户端已尝试启用插件。请在客户端中查看当前状态。')
        verify_unfinished_bundle(root, home, args.archive, binding,
                                 generated if recovering_activation or (manual and pending.get('phase') == 'preparation') else {})
    else:
        if getattr(args,'resume',False):raise ValueError('没有已登记的未完成版本可继续安装。')
        home.parent.mkdir(parents=True, exist_ok=True)
        with staged_bundle(root, args.archive, args.sha256, args.version) as extracted:
            stage = extracted.parent
            save(stage/'installation-pending.json',{'binding':binding,'phase':'dependencies'})
            os.replace(stage, home)
    # Not activated yet. Failed dependencies leave a diagnostic copy, never an active half-install.
    if not config.exists():
        if recovering_activation:
            raise ValueError('中断的 Codex 安装缺少运行配置。')
        command=[sys.executable, '-X', 'utf8', '-B', bundle / 'scripts/configure_runtime.py',
                 '--python', sys.executable, '--runtime', runtime, '--project', project,
                 '--outputs', outputs, '--config', config]
        if runtime.exists():command.append('--resume')
        run(command)
    else:
        restored=read_json(config)
        if restored.get('project_root')!=str(project) or restored.get('output_root')!=str(outputs) or restored.get('python')!=str(runtime/'Scripts/python.exe'):
            raise ValueError('未完成安装的运行配置与已登记的参数不一致。')
    smoke = [python, '-X', 'utf8', '-B', bundle / 'scripts/install_smoke.py', '--config', config, '--node', node]
    if manual:
        save(journal, {'binding': binding, 'phase': 'preparation'})
        configure_marketplace(home, args.agent, args.version, node, config)
        run([*smoke, '--adapter', args.agent])
        result = {'prepared': args.version, 'agent': args.agent, 'runtime_smoke': 'passed',
                  'registration': 'pending_host_registration', 'agent_host_load': 'not_checked',
                  'plugin_directory': str(bundle), 'config': str(config),
                  'next': '在客户端中使用 plugin_directory 导入本地插件。'}
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
            raise ValueError(f'Codex 启用尚未完成。请查看详细原因，再用原参数加 --resume 继续安装。\n详细原因 {error}') from error
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
            'agent_host_load': 'not_checked', 'next': '重新打开客户端，确认 Skills 和 MCP 工具可用。'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='准备、回退或卸载 Miliastra Wonderland 的本地安装。')
    p.add_argument('action', choices=('install', 'rollback', 'uninstall'))
    p.add_argument('--agent', choices=AGENTS, required=True)
    p.add_argument('--resume',action='store_true')
    for key in ('root', 'version'):
        p.add_argument('--' + key, required=True)
    for key in ('archive', 'sha256', 'project', 'outputs'):
        p.add_argument('--' + key)
    args = p.parse_args()
    try:
        print(json.dumps(operate(args), ensure_ascii=False))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        p.exit(1, f'[install.operation] 安装器执行失败。\n详细原因 {error}\n')
