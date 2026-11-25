"""Test the published descriptors and installer-owned preparation contract."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import install_plugin as installer


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'


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
            self.assertIn('spawnSync python.exe ENOENT', check.stderr)
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
        ):
            with self.subTest(config=relative):
                descriptor = installer.read_json(ROOT / relative)
                if relative == 'mcp.json':
                    self.assertEqual(set(descriptor), {'$schema', 'mcpServers'})
                    self.assertEqual(descriptor['$schema'], installer.MCP_SCHEMA)
                self.assertEqual(descriptor['mcpServers'], {installer.MCP_NAME: {
                    'type': 'stdio', 'command': 'node',
                    'args': [anchor + '/scripts/mcp_launcher.cjs'],
                    'env': {'MILIASTRA_WONDERLAND_PLUGIN_DATA': data},
                }})
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
                if agent == 'deepseek-harness':
                    self.assertIsNone(market)
                    manifest = files[Path('cordis-bundle/package.json')]
                    patch_file = manifest['dsh']['bundle']['patch']
                    self.assertEqual(manifest['version'], '3.8.0')
                    self.assertEqual(manifest['engines']['dsh'], '0.2.2-rc.5')
                    skills, mcp = files[Path('cordis-bundle') / patch_file][0]['insert']
                    self.assertEqual(skills['name'], '@deepseek-ai/dsh-skill-filesystem')
                    self.assertFalse(skills['config']['includeDefaultRoots'])
                    self.assertEqual(skills['config']['customSkillDirs'], [str(home / 'miliastra-wonderland/skills')])
                    self.assertEqual(mcp['name'], '@deepseek-ai/dsh-mcp-client')
                    self.assertEqual(mcp['config']['args'], [str(home / 'miliastra-wonderland/scripts/mcp_launcher.cjs')])
                    self.assertEqual(mcp['config']['env']['MILIASTRA_WONDERLAND_RUNTIME_CONFIG'], str(config))
                elif agent == 'claude-code':
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

    def test_manual_modes_do_not_register_or_overwrite(self):
        for agent in installer.MANUAL_AGENTS:
            with self.subTest(agent=agent), tempfile.TemporaryDirectory(prefix='ugc 准备 ') as temp:
                root = Path(temp)
                archive = root / 'bundle.zip'
                requirements = ['plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json',
                                'mcp.json', '.mcp.json', 'LICENSE', 'scripts/runtime-requirements.lock',
                                'scripts/mcp_launcher.cjs', 'vendor/beyond/bundle.json']
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
                    self.assertIn('--adapter', run.call_args.args[0])
                    self.assertFalse((home / 'installation-pending.json').exists())
                    with self.assertRaisesRegex(ValueError, '文件已准备好'):
                        installer.operate(args)
                    activate.assert_not_called()
                    codex_activate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
