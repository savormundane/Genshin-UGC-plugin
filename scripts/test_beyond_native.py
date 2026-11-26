import asyncio
from base64 import b64decode
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from authoring_io import PLUGIN, read_json, sha, sha_file, write_json
from beyond_native import (
    LOCK_NAME, NATIVE_BINARY, NATIVE_FILES, extract_native_archive,
    native_library_path, read_native_lock,
)


class BeyondNativeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='mw-canvas-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.backend = self.root / 'plugin' / 'vendor' / 'beyond'
        self.backend.mkdir(parents=True)
        self.data = self.root / 'data'
        self.payload = {name: name.encode() for name in NATIVE_FILES}
        self.archive = self.root / 'asset.zip'
        self.write_archive(self.payload)
        self.lock = {
            'schema': 1,
            'url': 'https://github.com/savormundane/miliastra-wonderland-plugin/releases/download/'
                   'beyond-canvas-v0.1.100/miliastra-beyond-canvas-0.1.100-windows-x64.zip',
            'sha256': sha_file(self.archive),
            'files': {name: sha(contents) for name, contents in self.payload.items()},
        }
        (self.backend / LOCK_NAME).write_text(json.dumps(self.lock), encoding='utf-8')
        (self.backend / 'bundle.json').write_text(json.dumps({'files': self.lock['files']}), encoding='utf-8')

    def write_archive(self, payload):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, contents in payload.items():
                archive.writestr(name, contents)

    def test_first_use_caches_verified_files_then_refuses_tampered_cache(self):
        with patch('os.environ', {'MILIASTRA_WONDERLAND_PLUGIN_DATA': str(self.data)}):
            with patch('beyond_native.download_native_archive',
                       side_effect=lambda _lock, path: shutil.copyfile(self.archive, path)) as download:
                binding = native_library_path(self.backend)
                self.assertEqual(binding.read_bytes(), self.payload[NATIVE_BINARY])
                self.assertTrue(binding.is_relative_to(self.data))
                self.assertEqual(native_library_path(self.backend), binding)
                download.assert_called_once()
                self.assertFalse((self.backend / NATIVE_BINARY).exists())
                binding.write_bytes(b'corrupt')
                with self.assertRaisesRegex(ValueError, 'file SHA-256 mismatch'):
                    native_library_path(self.backend)
                download.assert_called_once()

    def test_bundled_pair_needs_no_network(self):
        extract_native_archive(self.lock, self.archive, self.root / 'offline')
        with patch('beyond_native.download_native_archive') as download:
            binding = native_library_path(self.root / 'offline', lock=self.lock)
            self.assertEqual(binding, self.root / 'offline' / NATIVE_BINARY)
            binding.unlink()
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                native_library_path(self.root / 'offline', lock=self.lock)
            download.assert_not_called()

    def test_archive_and_file_digests_and_entry_names_are_checked(self):
        destination = self.root / 'extracted'
        for payload, lock_archive, error in (
            ({**self.payload, NATIVE_BINARY: b'corrupt'}, False, 'archive SHA-256 mismatch'),
            ({**self.payload, '../extra': b'extra'}, True, 'Unexpected.*archive entries'),
            ({**self.payload, NATIVE_BINARY: b'corrupt'}, True, 'file SHA-256 mismatch'),
        ):
            with self.subTest(error=error):
                self.write_archive(payload)
                lock = {**self.lock, 'sha256': sha_file(self.archive)} if lock_archive else self.lock
                with self.assertRaisesRegex(ValueError, error):
                    extract_native_archive(lock, self.archive, destination)
                self.assertFalse(destination.exists())

    def test_lock_must_match_manifest(self):
        (self.backend / 'bundle.json').write_text('{"files":{}}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differs from the bundled file manifest'):
            read_native_lock(self.backend)

    def test_mcp_forwards_proxy_settings_only_when_beyond_can_run(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        from miliastra.mcp.bridge import Bridge

        project = self.root / 'project'
        outputs = self.root / 'outputs'
        project.mkdir()
        outputs.mkdir()
        spec = project / 'spec.json'
        write_json(spec, {})
        bridge = Bridge(project, outputs)
        settings = {
            'HTTP_PROXY': 'http://127.0.0.1:8080',
            'https_proxy': 'http://127.0.0.1:8443',
            'NO_PROXY': 'localhost',
            'MILIASTRA_WONDERLAND_BEYOND_NATIVE_ROOT': str(self.root / 'provided-canvas'),
        }

        async def worker(*args, **kwargs):
            write_json(Path(args[-1]), {'status': 'failed'})
            return SimpleNamespace(wait=AsyncMock(return_value=0))

        async def run():
            args = {'spec': spec.name, 'sha256': sha_file(spec), 'output': 'probe'}
            with patch('os.environ', {**settings, 'OTHER_SECRET': 'test-value'}), \
                 patch('asyncio.create_subprocess_exec', side_effect=worker) as spawn:
                for operation, options, expected in (
                    ('simulate', {'preview': True}, settings),
                    ('produce', {}, settings),
                    ('simulate', {}, {}),
                ):
                    await bridge.call(operation, {**args, **options})
                    env = spawn.await_args.kwargs['env']
                    self.assertEqual({name: env[name] for name in settings if name in env}, expected)
                    self.assertNotIn('OTHER_SECRET', env)

        asyncio.run(run())

    def test_offline_revision_prepares_only_the_declared_source_changes(self):
        from beyond_backend import PIN, read_bundle_revision, verify_bundle_files
        from prepare_beyond_revision import prepare

        source = self.backend.parents[1]
        old = self.backend / 'studio/index.js'
        old.parent.mkdir()
        old.write_bytes(b'export const value = 1;\n')
        license_path = self.backend / 'LICENSE'
        license_path.write_bytes(b'License text fixture\n')
        manifest = self.backend / 'bundle.json'
        write_json(manifest, {
            'commit': PIN,
            'files': {**self.lock['files'], 'studio/index.js': sha_file(old), 'LICENSE': sha_file(license_path)},
        })
        scripts = source / 'scripts'
        scripts.mkdir()
        pin = scripts / 'beyond-revision.json'
        original_digest = sha_file(manifest)
        write_json(pin, {'schema': 1, 'upstream_commit': PIN, 'bundle_sha256': original_digest})
        write_json(source / 'PUBLIC_SOURCES.json', {'distribution_changes': []})
        old.write_bytes(b'export const value = 2;\n')
        destination = self.root / 'review'
        license_path.write_bytes(b'Unreviewed license change\n')
        with self.assertRaisesRegex(ValueError, 'integrity failure: LICENSE'):
            prepare(source, destination, ['studio/index.js'], 'Maintained behavior fixture')
        self.assertFalse(destination.exists())
        license_path.write_bytes(b'License text fixture\n')

        result = prepare(source, destination, ['studio/index.js'], 'Maintained behavior fixture')
        self.assertEqual(result['sources'], ['studio/index.js'])
        self.assertNotEqual(result['bundle_sha256'], original_digest)
        self.assertEqual(sha_file(manifest), original_digest)
        shutil.copyfile(destination / 'vendor/beyond/bundle.json', manifest)
        with self.assertRaisesRegex(ValueError, 'revision pin'):
            read_bundle_revision(self.backend, pin)
        new_pin, new_manifest = read_bundle_revision(self.backend, destination / 'scripts/beyond-revision.json')
        self.assertEqual(new_pin['bundle_sha256'], result['bundle_sha256'])
        self.assertEqual(verify_bundle_files(self.backend, new_manifest, read_native_lock(self.backend)), {})
        changes = read_json(destination / 'PUBLIC_SOURCES.json')['distribution_changes']
        self.assertEqual({row['path'] for row in changes}, {
            'vendor/beyond/studio/index.js', 'vendor/beyond/bundle.json',
        })

    def test_beyond_mcp_preview_reports_assertion_and_lua_failures(self):
        from mcp import Client, StdioServerParameters, types

        archive = os.environ.get('MILIASTRA_TEST_BEYOND_ARCHIVE')
        backend = PLUGIN / 'vendor/beyond'
        lock = read_native_lock(backend)
        if archive:
            native_root = self.root / 'provided-canvas'
            extract_native_archive(lock, Path(archive), native_root)
        elif not (backend / NATIVE_BINARY).is_file():
            self.skipTest('Provide MILIASTRA_TEST_BEYOND_ARCHIVE or a bundled Windows Canvas payload')

        project = self.root / 'preview project'
        shutil.copytree(PLUGIN / 'samples/beyond-button', project)
        spec = project / 'preview.json'
        changed = read_json(spec)
        button = project / 'button.lua'
        button_script = button.read_text(encoding='utf-8')
        changed['case']['asserts'][0]['contains'] = 'Missing assertion marker'
        write_json(spec, changed)
        outputs = self.root / 'outputs'
        outputs.mkdir()
        env = {key: value for key, value in os.environ.items() if not key.startswith('MILIASTRA_WONDERLAND_')}
        env['MILIASTRA_WONDERLAND_PLUGIN_DATA'] = str(self.data)
        if archive:
            env['MILIASTRA_WONDERLAND_BEYOND_NATIVE_ROOT'] = str(native_root)
        server = StdioServerParameters(
            command=sys.executable,
            args=['-X', 'utf8', '-B', str(PLUGIN / 'scripts/qianxing.py'), 'mcp', 'serve',
                  '--project', str(project), '--output-root', str(outputs)],
            env=env,
        )

        def assert_diagnostic_image(outcome, digest):
            self.assertEqual([item.type for item in outcome.content], ['text', 'image', 'text', 'text'])
            self.assertIn('预览失败', outcome.content[2].text)
            image, = [item for item in outcome.content if isinstance(item, types.ImageContent)]
            self.assertEqual(image.mime_type, 'image/png')
            self.assertEqual(sha(b64decode(image.data, validate=True)), digest)
            self.assertFalse(image.data in json.dumps(outcome.structured_content))

        async def run():
            async with Client(server) as client:
                args = {'spec': spec.name, 'sha256': sha_file(spec), 'output': 'preview', 'preview': True}
                outcome = await client.call_tool('simulate', args)
                self.assertFalse(outcome.is_error, outcome)
                response = outcome.structured_content
                self.assertEqual(response['status'], 'failed')
                self.assertIsNone(response['output'])
                self.assertFalse((outputs / 'preview').exists())
                self.assertEqual(response['diagnostics'][0]['code'], 'beyond_assertion_failed')
                output = Path(response['diagnostics_output'])
                self.assertEqual(output, outputs / 'preview.diagnostics')
                for name in ('preview.png', 'external-simulation.json', 'manifest.json'):
                    self.assertEqual(response['diagnostics_sha256'][name], sha_file(output / name))
                preview_digest = response['diagnostics_sha256']['preview.png']
                assert_diagnostic_image(outcome, preview_digest)
                report = read_json(output / 'external-simulation.json')
                self.assertEqual(report['status'], 'failed')
                self.assertEqual(report['checks']['lua']['status'], 'passed')
                self.assertIn('Button clicked', json.dumps(report['logs']))
                self.assertNotIn('qianxing-mcp-', json.dumps(response))
                old_preview = b'previous diagnostics image'
                (output / 'preview.png').write_bytes(old_preview)
                retry_outcome = await client.call_tool('simulate', args)
                self.assertFalse(retry_outcome.is_error, retry_outcome)
                retry = retry_outcome.structured_content
                self.assertIsNone(retry['output'])
                self.assertIsNone(retry.get('diagnostics_output'))
                self.assertEqual(retry['diagnostics'][-1]['code'], 'diagnostics_output_unavailable')
                self.assertEqual(response['diagnostics_sha256']['manifest.json'], sha_file(output / 'manifest.json'))
                self.assertEqual((output / 'preview.png').read_bytes(), old_preview)
                assert_diagnostic_image(retry_outcome, preview_digest)

                startup = 'function OnStart()\n    error("startup failed")\nend\n'
                click = changed['case']['events']
                static_assertion = [{'kind': 'control', 'name': 'Action', 'field': 'name', 'equals': 'Action'}]
                signal = (
                    'function OnStart()\n'
                    '    script:RegisterServerSignalHandler("Probe", function()\n'
                    '        error("signal failed")\n'
                    '    end)\n'
                    'end\n'
                )
                signal_events = [
                    {'t': 0, 'kind': 'view', 'playerIndex': 2},
                    {'t': 0, 'kind': 'serverSend', 'name': 'Probe', 'target': 'PlayerSelf'},
                    {'t': 0, 'kind': 'view', 'playerIndex': 1},
                ]
                ordinary_logs = button_script.replace(
                    'print("Button clicked")', 'print("lua-error info text")\n        printerr("lua-error error text")',
                )
                for name, source, players, events, asserts, message in (
                    ('startup', startup, 1, [], [], 'startup failed'),
                    ('startup-static', startup, 1, [], static_assertion, 'startup failed'),
                    ('signal-other-player', signal, 2, signal_events, static_assertion, 'signal failed'),
                    ('ordinary-logs', ordinary_logs, 1, click, static_assertion, None),
                ):
                    with self.subTest(name=name):
                        button.write_text(source, encoding='utf-8', newline='\n')
                        changed['scripts'][0]['sha256'] = sha_file(button)
                        write_json(spec, {**changed, 'case': {
                            **changed['case'], 'playerCount': players, 'events': events, 'asserts': asserts,
                        }})
                        outcome = await client.call_tool('simulate', {
                            **args, 'sha256': sha_file(spec), 'output': name,
                        })
                        self.assertFalse(outcome.is_error, outcome)
                        response = outcome.structured_content
                        expected = 'failed' if message else 'passed'
                        self.assertEqual(response['status'], expected, response)
                        destination = outputs / name
                        diagnostics = destination.with_name(name + '.diagnostics')
                        output = diagnostics if message else destination
                        self.assertEqual(destination.exists(), message is None)
                        self.assertEqual(diagnostics.exists(), message is not None)
                        report = read_json(output / 'external-simulation.json')
                        self.assertEqual(report['status'], expected)
                        self.assertEqual(report['checks']['assertions']['status'], 'passed' if asserts else 'not_checked',
                                         report['diagnostics'])
                        lua = report['checks']['lua']
                        self.assertEqual(lua['status'], expected)
                        if message:
                            self.assertIsNone(response['output'])
                            self.assertEqual(Path(response['diagnostics_output']), diagnostics)
                            self.assertEqual([item['code'] for item in response['diagnostics']], ['beyond_lua_error'])
                            error, = lua['errors']
                            self.assertIn(message, error['message'])
                            self.assertEqual(error['player_index'], 2 if players == 2 else 1)
                            if name.startswith('startup'):
                                self.assertIn(message, lua['mount_error'])
                                self.assertTrue(any(row['level'] == 'lua-error' and message in row['text']
                                                    for row in report['logs']))
                            else:
                                self.assertIsNone(lua['mount_error'])
                                self.assertFalse(any(message in row['text'] for row in report['logs']))
                            for artifact in ('preview.png', 'render.json', 'external-simulation.json', 'manifest.json'):
                                self.assertEqual(response['diagnostics_sha256'][artifact], sha_file(output / artifact))
                            assert_diagnostic_image(outcome, response['diagnostics_sha256']['preview.png'])
                            self.assertIn(message, outcome.content[2].text)
                            self.assertTrue(read_json(output / 'render.json')['tree'])
                        else:
                            self.assertEqual(Path(response['output']), destination)
                            self.assertEqual(lua['errors'], [])
                            self.assertEqual(report['diagnostics'], [])
                            logs = [(row['level'], row['text']) for row in report['logs']]
                            self.assertIn(('info', 'lua-error info text'), logs)
                            self.assertIn(('error', 'lua-error error text'), logs)

        asyncio.run(run())
        self.assertFalse((self.data / 'beyond-native').exists())

    def test_worker_hydrates_only_in_its_native_cache(self):
        project = self.backend.parents[1]
        archive = self.archive.rename(project / self.archive.name)
        scratch = self.root / 'scratch'
        scratch.mkdir()
        request = scratch / 'request.json'
        request.write_text(json.dumps({
            'operation': 'produce', 'scratch': str(scratch), 'project': str(project),
            'output_root': str(scratch), 'arguments': {'spec': str(self.backend), 'output': str(archive)},
            'inputs': {},
        }), encoding='utf-8')
        probe = """
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import shutil, sys

sys.path.insert(0, sys.argv.pop(1))
from beyond_native import native_library_path
import mcp_worker

def produce(backend, archive):
    with patch('beyond_native.download_native_archive',
               side_effect=lambda _lock, path: shutil.copyfile(archive, path)):
        binding = native_library_path(Path(backend))
    try:
        Path(archive).with_suffix('.forbidden').write_text('refuse')
    except ValueError as error:
        assert 'MCP write outside request output' in str(error)
    else:
        raise AssertionError('Project write was accepted')
    return {'binding': str(binding)}

sys.modules['production_core'] = SimpleNamespace(produce=produce, produce_summary=None, ProductionError=RuntimeError)
mcp_worker.main()
"""
        result = scratch / 'result.json'
        child = subprocess.run([sys.executable, '-B', '-c', probe, str(Path(__file__).resolve().parent),
                                str(request), str(result)], capture_output=True, text=True,
                               env={**os.environ, 'MILIASTRA_WONDERLAND_PLUGIN_DATA': str(self.data), 'MILIASTRA_WONDERLAND_BEYOND_NATIVE_ROOT': ''})
        self.assertEqual(child.returncode, 0, child.stderr)
        binding = Path(json.loads(result.read_text(encoding='utf-8'))['binding'])
        self.assertEqual(binding, self.data / 'beyond-native' / self.lock['sha256'] / NATIVE_BINARY)
        self.assertEqual(sha_file(binding), self.lock['files'][NATIVE_BINARY])
        self.assertFalse(archive.with_suffix('.forbidden').exists())


if __name__ == '__main__':
    unittest.main()
