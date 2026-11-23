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

import install_public as installer


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCHEMA = 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'


class ProtocolTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32' and shutil.which('node'), 'Windows Node.js required')
    def test_launcher_rejects_invalid_explicit_python(self):
        with tempfile.TemporaryDirectory(prefix='ugc launcher ') as temporary:
            env = {**os.environ, 'UGC_PUBLIC_INSTALL_ROOT': temporary, 'UGC_PYTHON': 'relative.exe'}
            env.pop('UGC_RUNTIME_CONFIG', None)
            env.pop('UGC_PLUGIN_DATA', None)
            result = subprocess.run(['node', str(ROOT / 'scripts/mcp_launcher.cjs')],
                                    env=env, capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual((result.returncode, result.stdout), (2, ''))
            self.assertIn('UGC_PYTHON must be an absolute path', result.stderr)

    def test_release_descriptors(self):
        core = installer.read_json(ROOT / 'plugin.json')
        self.assertEqual(core['$schema'], PLUGIN_SCHEMA)
        version = core['version']
        for relative in ('.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
            manifest = installer.read_json(ROOT / relative)
            self.assertEqual((manifest['name'], manifest['version']), (core['name'], version))
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
                    'env': {'UGC_PLUGIN_DATA': data},
                }})
        names = {'qianxing-editor': 'Qianxing Editor', 'qianxing-graph-code': 'Qianxing Graph Code',
                 'qianxing-gil': 'Qianxing GIL', 'qianxing-assets': 'Qianxing Assets'}
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
                    self.assertEqual(skills['config']['customSkillDirs'], [str(home / 'Genshin-UGC/skills')])
                    self.assertEqual(mcp['name'], '@deepseek-ai/dsh-mcp-client')
                    self.assertEqual(mcp['config']['args'], [str(home / 'Genshin-UGC/scripts/mcp_launcher.cjs')])
                    self.assertEqual(mcp['config']['env']['UGC_RUNTIME_CONFIG'], str(config))
                elif agent == 'claude-code':
                    self.assertIn(Path('.claude-plugin/marketplace.json'), files)
                    server, = files[Path('Genshin-UGC/.mcp.json')]['mcpServers'].values()
                    self.assertEqual(server['args'], ['${CLAUDE_PLUGIN_ROOT}/scripts/mcp_launcher.cjs'])
                    self.assertEqual(server['env']['UGC_RUNTIME_CONFIG'], str(config))
                    self.assertNotIn(Path('Genshin-UGC/mcp.json'), files)
                else:
                    data = files[Path('Genshin-UGC/mcp.json')]
                    self.assertEqual(data['$schema'], installer.MCP_SCHEMA)
                    server, = data['mcpServers'].values()
                    self.assertEqual(server['command'], 'node')
                    self.assertEqual(server['env']['UGC_RUNTIME_CONFIG'], str(config))
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
                        output.write(ROOT / relative, 'Genshin-UGC/' + relative)
                    for skill in (ROOT / 'skills').glob('*/SKILL.md'):
                        output.write(skill, 'Genshin-UGC/' + skill.relative_to(ROOT).as_posix())
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
                    with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
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
                    self.assertEqual(Path(result['plugin_directory']), home / 'Genshin-UGC')
                    self.assertIn('--adapter', run.call_args.args[0])
                    self.assertFalse((home / 'installation-pending.json').exists())
                    with self.assertRaisesRegex(ValueError, 'already prepared'):
                        installer.operate(args)
                    activate.assert_not_called()
                    codex_activate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
