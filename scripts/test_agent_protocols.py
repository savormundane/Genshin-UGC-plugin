"""Test the published descriptors and installer-owned preparation contract."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import venv
import zipfile

import install_plugin as installer
from runtime_policy import PYTHON_MAX


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
WINDOWS_TOOLS = (sys.platform == 'win32' and shutil.which('node') and shutil.which('powershell.exe'))


def isolated_windows_path(path, root):
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(('MILIASTRA_WONDERLAND_', 'UGC_', 'PYLAUNCHER_'))
           and key.upper() not in ('PATH', 'VIRTUAL_ENV', 'PYTHONHOME', 'PYTHONPATH')}
    return {**env, 'PATH': str(path), 'MILIASTRA_WONDERLAND_INSTALL_ROOT': str(root)}


def powershell_install(env, **arguments):
    env = {**env, 'MILIASTRA_TEST_INSTALLER': str(ROOT / 'install.ps1'),
           'MILIASTRA_TEST_INSTALL_ARGS': json.dumps(arguments)}
    return subprocess.run([
        shutil.which('powershell.exe'), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-Command',
        '[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)\n'
        'Import-Module (Join-Path $PSHOME "Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1")\n'
        '$installArgs = @{}\n'
        'foreach ($property in (ConvertFrom-Json $env:MILIASTRA_TEST_INSTALL_ARGS).PSObject.Properties) '
        '{ $installArgs[$property.Name] = $property.Value }\n'
        '& $env:MILIASTRA_TEST_INSTALLER @installArgs\n'
        'exit $LASTEXITCODE',
    ], env=env, capture_output=True, encoding='utf-8', errors='replace', timeout=120)


@unittest.skipUnless(WINDOWS_TOOLS, 'Windows Node.js and PowerShell required')
class WindowsRuntimeTests(unittest.TestCase):
    def test_py_discovery_in_installer_self_check_and_stdio(self):
        import mcp
        from mcp import Client, StdioServerParameters

        with tempfile.TemporaryDirectory(prefix='miliastra Python 查找 ') as temporary:
            root = Path(temporary)
            binaries = root / 'bin'
            binaries.mkdir()
            launcher = binaries / 'py.exe'
            source = root / 'probe.cs'
            source.write_text("""
using System;
using System.Diagnostics;
using System.IO;
class Probe {
    static int Main(string[] args) {
        if (Path.GetFileNameWithoutExtension(Environment.GetCommandLineArgs()[0]) == "uv") {
            if (args.Length == 1 && args[0] == "--version") {
                Console.WriteLine("uv fixture");
                return 0;
            }
            if (args.Length != 11 || args[0] != "run" || args[1] != "--project" || args[3] != "--locked" ||
                args[4] != "--no-build" || args[5] != "python" || args[6] != "-I" || args[7] != "-X" ||
                args[8] != "utf8" || args[9] != "-B" || !args[10].EndsWith("runtime_policy.py")) return 2;
            string environment = Environment.GetEnvironmentVariable("UV_PROJECT_ENVIRONMENT");
            File.AppendAllText(Environment.GetEnvironmentVariable("MILIASTRA_TEST_UV_LOG"), environment + "\\n");
            string python = Path.Combine(environment, "Scripts", "python.exe");
            if (!File.Exists(python)) return 5;
            using (var child = Process.Start(new ProcessStartInfo(python, "-I -X utf8 -B " + (char)34 + args[10] + (char)34) {
                UseShellExecute = false, CreateNoWindow = true
            })) {
                child.WaitForExit();
                return child.ExitCode;
            }
        }
        if (Environment.GetEnvironmentVariable("PYLAUNCHER_ALLOW_INSTALL") != null ||
            Environment.GetEnvironmentVariable("PYLAUNCHER_ALWAYS_INSTALL") != null ||
            Environment.GetEnvironmentVariable("PYTHON_MANAGER_AUTOMATIC_INSTALL") != "false") return 3;
        File.AppendAllText(Environment.GetEnvironmentVariable("MILIASTRA_TEST_PY_LOG"), args[0] + "\\n");
        string candidate = Environment.GetEnvironmentVariable("MILIASTRA_TEST_PY_" + args[0].Substring(3));
        if (candidate == null) return 4;
        Console.WriteLine(candidate);
        return 0;
    }
}
""", encoding='utf-8')
            compile_env = {**os.environ, 'MILIASTRA_TEST_CSHARP_SOURCE': str(source),
                           'MILIASTRA_TEST_CSHARP_EXE': str(launcher)}
            subprocess.run([
                shutil.which('powershell.exe'), '-NoProfile', '-NonInteractive', '-Command',
                '$ErrorActionPreference = "Stop"; Add-Type -Path $env:MILIASTRA_TEST_CSHARP_SOURCE '
                '-OutputAssembly $env:MILIASTRA_TEST_CSHARP_EXE -OutputType ConsoleApplication',
            ], env=compile_env, check=True, capture_output=True, timeout=45)
            log = root / 'py-probes.txt'
            highest = PYTHON_MAX[1] - 1
            highest_key = f'MILIASTRA_TEST_PY_{highest}'
            ready_key = f'MILIASTRA_TEST_PY_{highest - 1}'
            env = {**isolated_windows_path(binaries, root / 'installed'),
                   'MILIASTRA_TEST_PY_LOG': str(log), highest_key: 'invalid probe response',
                   ready_key: json.dumps(sys.executable),
                   'PYLAUNCHER_ALLOW_INSTALL': '1', 'PYLAUNCHER_ALWAYS_INSTALL': '1',
                   'PYTHON_MANAGER_AUTOMATIC_INSTALL': 'true'}

            selectors = [f'-3.{highest}', f'-3.{highest - 1}']
            for prefix in ('miliastra-wonderland/', ''):
                with self.subTest(wrapped=bool(prefix)):
                    archive = root / 'bootstrap.zip'
                    log.write_text('', encoding='utf-8')
                    with zipfile.ZipFile(archive, 'w') as zip_file:
                        zip_file.writestr(prefix + 'scripts/install_plugin.py',
                                          'import json, sys\nprint(json.dumps(sys.executable))\n')
                        for name in ('plugin.json', 'pyproject.toml', 'scripts/runtime_policy.py'):
                            zip_file.write(ROOT / name, prefix + name)
                    setup = powershell_install(
                        env, Archive=str(archive), Sha256=installer.archive_sha256(archive),
                        Project=str(root), Outputs=str(root / 'outputs'), Root=str(root / 'installed'),
                    )
                    self.assertEqual(setup.returncode, 0, setup.stderr)
                    self.assertEqual(setup.stderr, '')
                    self.assertEqual(Path(json.loads(setup.stdout)), Path(sys.executable))
                    self.assertEqual(log.read_text(encoding='utf-8').splitlines(), selectors)

            # Give the first selector a real CPython environment without the locked dependencies.
            incomplete = root / 'incomplete'
            venv.EnvBuilder(with_pip=False).create(incomplete)
            env[highest_key] = json.dumps(str(incomplete / 'Scripts/python.exe'))
            command = [shutil.which('node'), str(ROOT / 'scripts/mcp_launcher.cjs')]
            log.write_text('', encoding='utf-8')
            check = subprocess.run([*command, '--check'], env=env, capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn(sys.executable, check.stdout)
            self.assertEqual(log.read_text(encoding='utf-8').splitlines(), selectors)

            async def lookup():
                async with Client(StdioServerParameters(command=command[0], args=command[1:], env=env)) as client:
                    outcome = await client.call_tool('nodes_lookup', {'query': '创建实体', 'scope': 'server'})
                    self.assertFalse(outcome.is_error, outcome)
                    self.assertTrue(outcome.structured_content['result']['nodes'])

            asyncio.run(lookup())
            self.assertEqual(log.read_text(encoding='utf-8').splitlines(), selectors * 2)

            shutil.copyfile(launcher, binaries / 'uv.exe')
            rejected = subprocess.run([*command, '--check'], capture_output=True, encoding='utf-8', timeout=30,
                                      env={**env, 'MILIASTRA_WONDERLAND_PYTHON': str(root / 'missing.exe')})
            self.assertEqual(rejected.returncode, 2)
            self.assertIn('[runtime.python]', rejected.stderr)
            self.assertEqual(log.read_text(encoding='utf-8').splitlines(), selectors * 2)
            del env[ready_key]
            uv = subprocess.run([*command, '--check'], env=env, capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(uv.returncode, 0, uv.stderr)
            self.assertIn('下次启动会由 uv', uv.stdout)
            self.assertIn('Python 依赖版本需匹配锁定版本', uv.stdout)
            self.assertFalse((root / 'installed').exists())

            env['MILIASTRA_TEST_UV_LOG'] = str(root / 'uv-setup.txt')
            lock = (ROOT / 'uv.lock').read_text(encoding='utf-8')
            digest = hashlib.sha256(lock.encode('utf-8')).hexdigest()[:16]
            managed = root / 'installed/env' / digest
            ready = managed / '.miliastra-ready'
            setup = subprocess.run([*command, '--setup'], env=env, capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(setup.returncode, 5, setup.stderr)
            self.assertIn('[runtime.uv]', setup.stderr)
            self.assertFalse(ready.exists())

            venv.EnvBuilder(with_pip=False).create(managed)
            site_packages = Path(mcp.__file__).resolve().parents[1]
            (managed / 'Lib/site-packages/fixture.pth').write_text(
                f'import site; site.addsitedir({ascii(str(site_packages))})\n', encoding='utf-8',
            )
            setup = subprocess.run([*command, '--setup'], env=env, capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(setup.returncode, 0, setup.stderr)
            self.assertIn(str(managed / 'Scripts/python.exe'), setup.stdout)
            self.assertEqual(Path(env['MILIASTRA_TEST_UV_LOG']).read_text(encoding='utf-8').splitlines(),
                             [str(managed), str(managed)])
            self.assertTrue(ready.is_file())

            # The prepared environment serves MCP directly even when the original uv is unavailable.
            (binaries / 'uv.exe').unlink()
            log.write_text('', encoding='utf-8')
            asyncio.run(lookup())
            self.assertEqual(log.read_text(encoding='utf-8'), '')

    def test_powershell_recovery_reuses_valid_python_and_checks_target_before_registration(self):
        import mcp

        with tempfile.TemporaryDirectory(prefix='miliastra 保留版本 ') as temporary:
            root = Path(temporary)
            project, outputs = root / '工程', root / '产物'
            project.mkdir()
            outputs.mkdir()
            node = shutil.which('node')
            env = {**isolated_windows_path(Path(node).parent, root), 'MILIASTRA_TEST_NODE': node}
            old, current = '1.0.0', '1.1.0'
            records = {}
            for version in (old, current):
                retained = root / 'versions/codex' / version
                scripts = retained / 'miliastra-wonderland/scripts'
                scripts.mkdir(parents=True)
                shutil.copyfile(ROOT / 'pyproject.toml', scripts.parent / 'pyproject.toml')
                runtime = retained / 'runtime'
                python = runtime / 'Scripts/python.exe'
                config = retained / 'runtime.json'
                records[version] = {'version': version, 'home': str(retained), 'config': str(config),
                                    'python': str(python), 'marketplace': version}
                installer.save(config, {'schema': 1, 'python': str(python),
                                        'project_root': str(project), 'output_root': str(outputs)})
                # Run the actual state transitions against a test registry, with the real target smoke.
                (scripts / 'install_plugin.py').write_text(f"""
import argparse, json, os, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, {str(ROOT / 'scripts')!r})
import install_plugin as installer

args = argparse.Namespace(action=sys.argv[1], project=None, outputs=None, **{{
    key[2:]: value for key, value in zip(sys.argv[2::2], sys.argv[3::2])
}})
registry = Path(args.root) / 'test-registration.json'

def mark(action, record):
    state = installer.read_json(registry)
    getattr(state, action)(record['version'])
    installer.save(registry, state)

with patch.object(installer, 'preflight', return_value=('test-client', os.environ['MILIASTRA_TEST_NODE'])), \\
     patch.object(installer, 'ensure_codex_active', side_effect=lambda _, row: mark('append', row)), \\
     patch.object(installer, 'retire_codex_registration', side_effect=lambda _, row: mark('remove', row)):
    result = installer.operate(args)
print(json.dumps({{'bootstrap': sys.executable, **result}}))
""", encoding='utf-8')
                if version == old:
                    venv.EnvBuilder(with_pip=False).create(runtime)
                    site_packages = Path(mcp.__file__).resolve().parents[1]
                    (runtime / 'Lib/site-packages/test-dependencies.pth').write_text(
                        f'import site; site.addsitedir({ascii(str(site_packages))})\n', encoding='utf-8',
                    )
                    marker = scripts / 'fail-smoke'
                    marker.touch()
                    (scripts / 'install_smoke.py').write_text(f"""
import json, runpy, sys
from pathlib import Path
if Path(__file__).with_name('fail-smoke').exists():
    sys.exit('injected target smoke failure')
config = Path(sys.argv[sys.argv.index('--config') + 1])
assert Path(sys.executable) == Path(json.loads(config.read_text(encoding='utf-8'))['python'])
sys.path.insert(0, {str(ROOT / 'scripts')!r})
runpy.run_path({str(ROOT / 'scripts/install_smoke.py')!r}, run_name='__main__')
""", encoding='utf-8')
                else:
                    self.assertFalse(python.exists())

            state = root / 'codex.json'
            registry = root / 'test-registration.json'
            installer.save(state, {'schema': 1, 'current': records[current], 'history': [records[old]]})
            installer.save(registry, [current])
            original = state.read_bytes()
            rollback = {'Agent': 'codex', 'Root': str(root), 'Action': 'rollback', 'Version': old}
            smoke_failed = powershell_install(env, **rollback)
            self.assertNotEqual(smoke_failed.returncode, 0)
            self.assertIn('injected target smoke failure', smoke_failed.stderr)
            self.assertEqual(state.read_bytes(), original)
            self.assertEqual(installer.read_json(registry), [current])

            marker.unlink()
            explicit_failed = powershell_install(env, **rollback, Python=str(root / 'missing.exe'))
            self.assertNotEqual(explicit_failed.returncode, 0)
            self.assertIn('[runtime.python]', explicit_failed.stderr)
            self.assertIn(f"-Version '{old}'", explicit_failed.stderr)
            self.assertEqual(state.read_bytes(), original)

            broken = Path(records[current]['python'])
            broken.parent.mkdir(parents=True)
            broken.write_bytes(b'invalid executable for the recovery test')
            recovered = powershell_install(env, **rollback)
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            receipts = [json.loads(line) for line in recovered.stdout.splitlines() if line.startswith('{')]
            self.assertEqual(receipts[-2]['stdio'], 'passed', recovered.stdout)
            self.assertEqual(Path(receipts[-1]['bootstrap']), Path(records[old]['python']))
            self.assertEqual(receipts[-1]['rolled_back'], old)
            self.assertEqual(installer.read_json(state)['current'], records[old])
            self.assertEqual(installer.read_json(registry), [old])

            target_python = Path(records[old]['python'])
            target_python.rename(target_python.with_suffix('.disabled'))
            system_env = {**env, 'PATH': os.pathsep.join([env['PATH'], str(Path(sys.executable).parent)])}
            uninstall = {'Agent': 'codex', 'Root': str(root), 'Action': 'uninstall'}
            for next_env, options in ((system_env, {}), (env, {'Python': sys.executable})):
                removed = powershell_install(next_env, **uninstall, **options)
                self.assertEqual(removed.returncode, 0, removed.stderr)
                result = json.loads(removed.stdout.splitlines()[-1])
                self.assertTrue(result['registration_removed'])
                self.assertEqual(Path(result['bootstrap']), Path(sys.executable))
                self.assertIsNone(installer.read_json(state)['current'])
                self.assertEqual(installer.read_json(registry), [])


class ProtocolTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('node'), 'Windows Node.js required')
    def test_launcher_rejects_invalid_explicit_python(self):
        with tempfile.TemporaryDirectory(prefix='ugc launcher ') as temporary:
            env = {**os.environ, 'MILIASTRA_WONDERLAND_INSTALL_ROOT': temporary, 'MILIASTRA_WONDERLAND_PYTHON': 'relative.exe'}
            env.pop('MILIASTRA_WONDERLAND_RUNTIME_CONFIG', None)
            env.pop('MILIASTRA_WONDERLAND_PLUGIN_DATA', None)
            result = subprocess.run(['node', str(ROOT / 'scripts/mcp_launcher.cjs')],
                                    env=env, capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual((result.returncode, result.stdout), (2, ''))
            self.assertIn('指定的 Python 路径无效', result.stderr)
            self.assertIn('MILIASTRA_WONDERLAND_PYTHON 需使用绝对路径', result.stderr)

    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('node'), 'Windows Node.js required')
    def test_standalone_check_reuses_runtime_failure(self):
        with tempfile.TemporaryDirectory(prefix='ugc 自检 ') as temporary:
            env = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith(('MILIASTRA_WONDERLAND_', 'UGC_'))
                   and key.upper() not in ('PATH', 'VIRTUAL_ENV')}
            env.update(PATH=temporary, MILIASTRA_WONDERLAND_INSTALL_ROOT=str(Path(temporary) / 'install'))
            command = [shutil.which('node'), str(ROOT / 'scripts/mcp_launcher.cjs')]
            serve = subprocess.run(command, env=env, capture_output=True, encoding='utf-8', timeout=15)
            check = subprocess.run([*command, '--check'], env=env, capture_output=True, encoding='utf-8', timeout=15)
            self.assertEqual((serve.returncode, check.returncode, serve.stdout), (2, 2, ''))
            self.assertEqual(serve.stderr, check.stderr)
            self.assertIn('插件启动文件齐全', check.stdout)
            self.assertIn('未找到可用的 uv', check.stdout)
            self.assertIn('[runtime.python] 未找到可用的 Python 运行环境', check.stderr)
            self.assertIn('uv --version', check.stderr)
            self.assertIn('PATH 上未找到可探测的 python.exe', check.stderr)
            self.assertIn('PATH 上未找到 py.exe', check.stderr)
            self.assertFalse((Path(temporary) / 'install').exists())

    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('node'), 'Windows Node.js required')
    def test_launcher_warns_without_reading_retired_environment(self):
        renames = installer.read_json(ROOT / 'scripts/runtime-env-renames.json')
        old = {key: 'retired-relative-path' for key in renames}
        with tempfile.TemporaryDirectory(prefix='miliastra-env-') as temporary:
            env = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith(('MILIASTRA_WONDERLAND_', 'UGC_'))}
            env.update(old, MILIASTRA_WONDERLAND_INSTALL_ROOT=temporary, MILIASTRA_WONDERLAND_PYTHON='new-relative-path')
            result = subprocess.run(['node', str(ROOT / 'scripts/mcp_launcher.cjs')],
                                    env=env, capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual((result.returncode, result.stdout), (2, ''))
            self.assertEqual(result.stderr.count('[runtime.env.deprecated]'), len(old))
            for name, replacement in renames.items():
                self.assertIn(f'{name} 已停用，请使用 {replacement}', result.stderr)
            self.assertIn('MILIASTRA_WONDERLAND_PYTHON 需使用绝对路径', result.stderr)
            self.assertNotIn('retired-relative-path', result.stderr)

    def test_direct_cli_does_not_bind_project_from_retired_environment(self):
        renames = installer.read_json(ROOT / 'scripts/runtime-env-renames.json')
        variable, = [old for old, new in renames.items() if new == 'MILIASTRA_WONDERLAND_PROJECT_ROOT']
        with tempfile.TemporaryDirectory(prefix='miliastra-cli-env-') as temporary:
            env = {key: value for key, value in os.environ.items()
                   if not key.upper().startswith(('MILIASTRA_WONDERLAND_', 'UGC_'))}
            env.update({variable: temporary, 'MILIASTRA_WONDERLAND_INSTALL_ROOT': temporary})
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/qianxing.py'), 'doctor'],
                                    env=env, capture_output=True, encoding='utf-8', timeout=15)
            self.assertIn(f'{variable} 已停用，请使用 MILIASTRA_WONDERLAND_PROJECT_ROOT', result.stderr)
            self.assertIsNone(json.loads(result.stdout)['project_context']['project_root'])

    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('node'), 'Windows Node.js required')
    def test_standalone_check_reports_incomplete_plugin(self):
        with tempfile.TemporaryDirectory(prefix='ugc 不完整插件 ') as temporary:
            scripts = Path(temporary) / 'scripts'
            scripts.mkdir()
            launcher = scripts / 'mcp_launcher.cjs'
            shutil.copyfile(ROOT / 'scripts' / launcher.name, launcher)
            result = subprocess.run(['node', str(launcher), '--check'], capture_output=True,
                                    encoding='utf-8', timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn('不完整插件', result.stdout)
            self.assertIn('[install.files] 插件缺少启动所需文件', result.stderr)
            self.assertIn('pyproject.toml', result.stderr)

    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('powershell.exe'), 'Windows PowerShell required')
    def test_standalone_check_without_node(self):
        with tempfile.TemporaryDirectory(prefix='ugc 无 Node ') as temporary:
            env = {key: value for key, value in os.environ.items() if key.upper() != 'PATH'}
            env['PATH'] = temporary
            script = str(ROOT / 'scripts/check-install.ps1').replace("'", "''")
            check = ("[Console]::OutputEncoding = [Text.Encoding]::GetEncoding(437)\n"
                     f"& '{script}'\nexit $LASTEXITCODE")
            command = [shutil.which('powershell.exe'), '-NoProfile', '-ExecutionPolicy', 'Bypass',
                       '-Command', check]
            result = subprocess.run(command, env=env, capture_output=True, encoding='utf-8',
                                    creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn('[runtime.node] 当前 PowerShell 的 PATH 找不到 Node.js', result.stdout)
            self.assertIn('node --version', result.stdout)

    def test_release_descriptors(self):
        core = installer.read_json(ROOT / 'plugin.json')
        self.assertEqual(core['$schema'], PLUGIN_SCHEMA)
        self.assertEqual(core['name'], 'miliastra-wonderland')
        version = core['version']
        for relative in ('.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
            manifest = installer.read_json(ROOT / relative)
            self.assertEqual((manifest['name'], manifest['version']), (core['name'], version))
        bundle = installer.read_json(ROOT / 'package.json')
        self.assertEqual((bundle['name'], bundle['version']), (core['name'], version))
        self.assertEqual(bundle['exports']['./locale/*.json'], './locale/*.json')
        english = installer.read_json(ROOT / 'locale/en.json')['meta']
        chinese = installer.read_json(ROOT / 'locale/zh.json')['meta']
        self.assertEqual(set(english), set(chinese))
        self.assertEqual(english['title'], 'Miliastra Wonderland')
        self.assertEqual(chinese['title'], '千星奇域开发插件')
        self.assertEqual(english['description'], bundle['description'])
        self.assertNotRegex(english['description'], r'[\u3400-\u9fff]')
        self.assertRegex(chinese['description'], r'[\u3400-\u9fff]')
        for relative, anchor, data in (
            ('mcp.json', '${PLUGIN_ROOT}', '${PLUGIN_DATA}'),
            ('.mcp.json', '${CLAUDE_PLUGIN_ROOT}', '${CLAUDE_PLUGIN_DATA}'),
            ('.codex-plugin/mcp.json', '${PLUGIN_ROOT}', '${PLUGIN_DATA}'),
        ):
            with self.subTest(config=relative):
                descriptor = installer.read_json(ROOT / relative)
                if relative == 'mcp.json':
                    self.assertEqual(set(descriptor), {'$schema', 'mcpServers'})
                    self.assertEqual(descriptor['$schema'], installer.MCP_SCHEMA)
                expected = {
                    'type': 'stdio', 'command': 'node',
                    'args': [anchor + '/scripts/mcp_launcher.cjs'],
                    'env': {'MILIASTRA_WONDERLAND_PLUGIN_DATA': data},
                }
                if relative == '.codex-plugin/mcp.json':
                    self.assertEqual(installer.read_json(ROOT / '.codex-plugin/plugin.json')['mcpServers'],
                                     './' + relative)
                    expected['env_vars'] = installer.CODEX_MCP_ENV_VARS
                self.assertEqual(descriptor['mcpServers'], {installer.MCP_NAME: expected})
        names = {'miliastra-editor': 'Miliastra Editor', 'miliastra-graph-code': 'Miliastra Graph Code',
                 'miliastra-gil': 'Miliastra GIL', 'miliastra-assets': 'Miliastra Assets'}
        self.assertEqual({path.parent.name for path in (ROOT / 'skills').glob('*/SKILL.md')}, names.keys())
        for identity, title in names.items():
            skill = ROOT / 'skills' / identity
            self.assertIn(f'name: {identity}\n', (skill / 'SKILL.md').read_text(encoding='utf-8'))
            self.assertIn(f'display_name: "{title}"', (skill / 'agents/openai.yaml').read_text(encoding='utf-8'))
        self.assertTrue((ROOT / 'scripts/mcp_launcher.cjs').is_file())
        self.assertTrue((ROOT / 'references/README.md').is_file())

    def test_generated_configs_preserve_native_contracts(self):
        home = Path.cwd() / 'prepared with spaces 托管'
        config = home / 'runtime.json'
        node = str(home / 'bin/node.exe')
        for agent in installer.AGENTS:
            with self.subTest(agent=agent):
                market, files = installer.marketplace_files(agent, '3.8.0', node, config)
                if agent == 'claude-code':
                    self.assertIn(Path('.claude-plugin/marketplace.json'), files)
                    server, = files[Path('miliastra-wonderland/.mcp.json')]['mcpServers'].values()
                    self.assertEqual(server['args'], ['${CLAUDE_PLUGIN_ROOT}/scripts/mcp_launcher.cjs'])
                    self.assertEqual(server['env']['MILIASTRA_WONDERLAND_RUNTIME_CONFIG'], str(config))
                    self.assertNotIn(Path('miliastra-wonderland/mcp.json'), files)
                else:
                    data = files[Path('miliastra-wonderland/mcp.json')]
                    self.assertEqual(data['$schema'], installer.MCP_SCHEMA)
                    server, = data['mcpServers'].values()
                    self.assertEqual(server['command'], 'node')
                    self.assertEqual(server['env']['MILIASTRA_WONDERLAND_RUNTIME_CONFIG'], str(config))
                    if agent == 'agent-plugins':
                        self.assertIsNone(market)
                        self.assertEqual(len(files), 1)
                    else:
                        overlay = files[Path('miliastra-wonderland/.codex-plugin/mcp.json')]
                        self.assertEqual(overlay['mcpServers'], {
                            installer.MCP_NAME: {**server, 'env_vars': installer.CODEX_MCP_ENV_VARS},
                        })

    def test_same_version_install_distinguishes_active_and_retained(self):
        version = installer.read_json(ROOT / 'plugin.json')['version']
        for agent in ('codex', 'claude-code'):
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary).resolve()
                root = directory / "安装 '工作区' ’"
                relative_script = Path('versions') / agent / version / 'miliastra-wonderland/install.ps1'
                script = root / relative_script
                script.parent.mkdir(parents=True)
                shutil.copyfile(ROOT / 'install.ps1', script)
                archive = directory / 'bundle.zip'
                with zipfile.ZipFile(archive, 'w') as output:
                    output.write(script, 'install.ps1')
                config = script.parent.parent / 'runtime.json'
                original_config = {'project_root': str(directory / 'project'), 'output_root': str(directory / 'outputs')}
                installer.save(config, original_config)
                args = argparse.Namespace(
                    action='install', agent=agent, root=root, version=version, resume=False,
                    archive=archive, sha256=installer.archive_sha256(archive),
                    project=original_config['project_root'], outputs=original_config['output_root'],
                )
                record = {'version': version, 'home': str(config.parent), 'config': str(config),
                          'marketplace': 'miliastra-wonderland-download-' + agent, 'archive_sha256': args.sha256}
                state_path = root / (agent + '.json')
                active = {'schema': 1, 'current': record, 'history': []}
                installer.save(state_path, active)

                with (
                    patch.object(installer, 'preflight', return_value=('client', 'node')),
                    patch.object(installer, 'run') as run,
                    patch.object(installer, 'retire_codex_registration'),
                ):
                    with self.assertRaises(ValueError) as enabled:
                        installer.operate(args)
                    self.assertIn(f'版本 {version} 已启用', str(enabled.exception))
                    self.assertNotIn('-Action rollback', str(enabled.exception))
                    self.assertEqual(installer.read_json(state_path), active)
                    run.assert_not_called()

                    args.action = 'uninstall'
                    self.assertTrue(installer.operate(args)['registration_removed'])
                    retained = {'schema': 1, 'current': None, 'history': [record]}
                    self.assertEqual(installer.read_json(state_path), retained)
                    run.reset_mock()

                    args.action = 'install'
                    with self.assertRaises(ValueError) as stopped:
                        installer.operate(args)
                    message = str(stopped.exception)
                    self.assertIn(f'版本 {version} 已停用，安装文件仍保留', message)
                    quoted_root = str(root).replace("'", "''").replace('’', '’’')
                    quoted_script = Path(quoted_root) / relative_script
                    self.assertEqual(
                        message.splitlines()[-1],
                        f"& '{quoted_script}' -Agent {agent} -Action rollback -Version {version} -Root '{quoted_root}'",
                    )
                    self.assertEqual(installer.read_json(state_path), retained)
                    self.assertEqual(installer.read_json(config), original_config)
                    self.assertEqual(script.read_bytes(), (ROOT / 'install.ps1').read_bytes())
                    run.assert_not_called()

    def test_manual_modes_do_not_register_or_overwrite(self):
        for agent in installer.MANUAL_AGENTS:
            with self.subTest(agent=agent), tempfile.TemporaryDirectory(prefix='ugc 准备 ') as temp:
                root = Path(temp)
                archive = root / 'bundle.zip'
                writeback_template = Path(
                    'vendor/ayaya/private_extensions/ugc_file_tools/builtin_resources/templates/server/'
                    'autowire_templates_test2_server_direct_export_v2.gil'
                )
                requirements = ['plugin.json', '.codex-plugin/plugin.json', '.codex-plugin/mcp.json', '.claude-plugin/plugin.json',
                                'mcp.json', '.mcp.json', 'LICENSE', 'scripts/runtime-requirements.lock',
                                'scripts/mcp_launcher.cjs', 'vendor/beyond/bundle.json', writeback_template.as_posix()]
                with zipfile.ZipFile(archive, 'w') as output:
                    for relative in requirements:
                        output.write(ROOT / relative, 'miliastra-wonderland/' + relative)
                    for skill in (ROOT / 'skills').glob('*/SKILL.md'):
                        output.write(skill, 'miliastra-wonderland/' + skill.relative_to(ROOT).as_posix())
                project = root / 'test project'
                project.mkdir()
                args = argparse.Namespace(action='install', agent=agent, root=root / 'installed',
                                          version=installer.read_json(ROOT / 'plugin.json')['version'],
                                          project=project, outputs=root / 'outputs', archive=archive,
                                          sha256='0' * 64, resume=False)
                with patch.object(installer, 'preflight', return_value=(None, 'node')), \
                        patch.object(installer, 'activate') as activate, \
                        patch.object(installer, 'activate_codex_install') as codex_activate, \
                        patch.object(installer, 'extract', wraps=installer.extract) as extract, \
                        patch.object(installer, 'run') as run:
                    with self.assertRaisesRegex(ValueError, 'SHA-256 校验失败'):
                        installer.operate(args)
                    self.assertFalse(args.root.exists())
                    args.sha256 = installer.archive_sha256(archive)
                    run.side_effect = [None, RuntimeError('smoke failed')]
                    with self.assertRaisesRegex(RuntimeError, 'smoke failed'):
                        installer.operate(args)
                    home = args.root / 'versions' / agent / args.version
                    self.assertFalse((home / 'preparation.json').exists())
                    self.assertFalse((args.root / (agent + '.json')).exists())
                    args.resume = True
                    run.side_effect = None
                    result = installer.operate(args)
                    self.assertEqual(result['registration'], 'pending_host_registration')
                    self.assertEqual(result['agent_host_load'], 'not_checked')
                    self.assertEqual(Path(result['plugin_directory']), home / 'miliastra-wonderland')
                    self.assertEqual((home / 'miliastra-wonderland' / writeback_template).read_bytes(),
                                     (ROOT / writeback_template).read_bytes())
                    self.assertEqual(extract.call_count, 2)
                    windows_root = PureWindowsPath(r'C:\Users\abcdefgh\AppData\Local\Miliastra Wonderland')
                    for call in extract.call_args_list:
                        staging = call.args[2]
                        self.assertFalse(staging.exists())
                        projected = windows_root / staging.relative_to(args.root.resolve()).as_posix()
                        sample = projected / 'miliastra-wonderland' / writeback_template.as_posix()
                        self.assertLess(len(str(sample).encode('utf-16-le')) // 2, 260, str(sample))
                    self.assertIn('--adapter', run.call_args.args[0])
                    self.assertFalse((home / 'installation-pending.json').exists())
                    with self.assertRaisesRegex(ValueError, '文件已准备好'):
                        installer.operate(args)
                    activate.assert_not_called()
                    codex_activate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
