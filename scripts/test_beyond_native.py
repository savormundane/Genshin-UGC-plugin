import asyncio
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

    def test_failed_beyond_mcp_preview_retains_diagnostics(self):
        from mcp import Client, StdioServerParameters

        archive = os.environ.get('MILIASTRA_TEST_BEYOND_ARCHIVE')
        backend = PLUGIN / 'vendor/beyond'
        lock = read_native_lock(backend)
        if archive:
            cache = self.data / 'beyond-native'
            cache.mkdir(parents=True)
            extract_native_archive(lock, Path(archive), cache / lock['sha256'])
        elif not (backend / NATIVE_BINARY).is_file():
            self.skipTest('Provide MILIASTRA_TEST_BEYOND_ARCHIVE or a bundled Windows Canvas payload')

        project = self.root / 'preview project'
        shutil.copytree(PLUGIN / 'samples/beyond-button', project)
        spec = project / 'preview.json'
        changed = read_json(spec)
        changed['case']['asserts'][0]['contains'] = 'Missing assertion marker'
        write_json(spec, changed)
        outputs = self.root / 'outputs'
        outputs.mkdir()
        env = {key: value for key, value in os.environ.items() if not key.startswith('MILIASTRA_WONDERLAND_')}
        env['MILIASTRA_WONDERLAND_PLUGIN_DATA'] = str(self.data)
        server = StdioServerParameters(
            command=sys.executable,
            args=['-X', 'utf8', '-B', str(PLUGIN / 'scripts/qianxing.py'), 'mcp', 'serve',
                  '--project', str(project), '--output-root', str(outputs)],
            env=env,
        )

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
                report = read_json(output / 'external-simulation.json')
                self.assertEqual(report['status'], 'failed')
                self.assertIn('Button clicked', json.dumps(report['logs']))
                self.assertNotIn('qianxing-mcp-', json.dumps(response))
                retry = (await client.call_tool('simulate', args)).structured_content
                self.assertIsNone(retry['output'])
                self.assertEqual(retry['diagnostics'][-1]['code'], 'diagnostics_output_unavailable')
                self.assertEqual(response['diagnostics_sha256']['manifest.json'], sha_file(output / 'manifest.json'))

        asyncio.run(run())

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
