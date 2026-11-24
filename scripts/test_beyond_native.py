import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from authoring_io import sha, sha_file
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
        with patch.dict('os.environ', {'UGC_PLUGIN_DATA': str(self.data), 'UGC_BEYOND_NATIVE_ROOT': ''}):
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


if __name__ == '__main__':
    unittest.main()
