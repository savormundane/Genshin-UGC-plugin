"""Manual release check: actual ZIP structure, extraction and content identity."""

from pathlib import Path, PureWindowsPath
import hashlib, json, shutil, subprocess, sys, tempfile, unittest, zipfile
import os
from unittest.mock import patch
from check_repository import check, MANIFESTS, REPO, REQUIRED_FILES
from marketplace_release import marketplace_files
from package_release import build_release, validate_windows_names
from install_plugin import AGENTS, extract, read_json


WINDOWS_TEST_PROFILE = PureWindowsPath('C:/Users') / ('a' * 24)


class ReleaseTests(unittest.TestCase):
    def assert_legacy_windows_paths_fit(self, root, members):
        paths = (str(root / member) for member in members)
        length, longest = max((len(path.encode('utf-16-le')) // 2, path) for path in paths)
        self.assertLess(length, 260, longest)

    def test_git_files_fit_claude_windows_paths(self):
        root = Path(__file__).resolve().parents[1]
        git = shutil.which('git')
        if not git or not (root / '.git').exists():
            self.skipTest('Git checkout required for tracked path checks')
        tracked = subprocess.check_output([git, 'ls-files', '-z'], cwd=root, timeout=60)
        members = tracked.decode('utf-8').rstrip('\0').split('\0')
        self.assertTrue(members[0])
        # Chat and Cowork account marketplaces accept at most 5,000 files per plugin.
        self.assertLessEqual(len(members), 5_000, 'Claude account marketplace file limit')
        marketplace = read_json(root / '.claude-plugin/marketplace.json')
        (plugin,) = marketplace['plugins']
        version = read_json(root / '.claude-plugin/plugin.json')['version']
        plugins = WINDOWS_TEST_PROFILE / '.claude/plugins'
        self.assert_legacy_windows_paths_fit(
            plugins / 'marketplaces' / marketplace['name'], members
        )
        repository = read_json(root / 'plugin.json')['repository'].rstrip('/')
        clone_name = '-'.join(repository.rsplit('/', 2)[-2:]) + '..clone'
        self.assert_legacy_windows_paths_fit(plugins / 'marketplaces' / clone_name, members)
        isolated_config = PureWindowsPath(
            'C:/Users/abcde/AppData/Local/Temp/mw-claude-market-12345678'
        )
        self.assert_legacy_windows_paths_fit(
            isolated_config / 'plugins/marketplaces' / clone_name, members
        )
        cache = plugins / 'cache' / marketplace['name'] / plugin['name'] / version
        self.assert_legacy_windows_paths_fit(cache, members)

    def test_windows_zip_bundles_locked_beyond_native_files(self):
        with tempfile.TemporaryDirectory(prefix='ugc native bundle ') as temporary:
            root = Path(temporary)
            source = root / 'plugin'
            backend = source / 'vendor/beyond'
            backend.mkdir(parents=True)
            skill = source / 'skills/fixture/SKILL.md'
            skill.parent.mkdir(parents=True)
            skill.write_text(
                '---\nname: fixture\ndescription: Distribution fixture\n---\n', encoding='utf-8'
            )
            (source / 'plugin.json').write_text('{"name": "fixture"}\n', encoding='utf-8')
            native_package = 'node_modules/@napi-rs/canvas-win32-x64-msvc'
            payload = {
                f'{native_package}/skia.win32-x64-msvc.node': b'fixture canvas native module',
                f'{native_package}/icudtl.dat': b'fixture ICU data',
            }
            asset = root / 'canvas.zip'
            with zipfile.ZipFile(asset, 'w') as archive:
                for name, contents in payload.items():
                    archive.writestr(name, contents)
            lock = {
                'schema': 1,
                'url': (
                    'https://github.com/savormundane/miliastra-wonderland-plugin/releases/download/'
                    'beyond-canvas-v0.1.100/miliastra-beyond-canvas-0.1.100-windows-x64.zip'
                ),
                'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
                'files': {
                    name: hashlib.sha256(contents).hexdigest() for name, contents in payload.items()
                },
            }
            (backend / 'native-canvas.json').write_text(json.dumps(lock), encoding='utf-8')
            (backend / 'bundle.json').write_text(
                json.dumps({'files': lock['files']}), encoding='utf-8'
            )
            offline = root / 'offline.zip'
            with patch(
                'beyond_native.download_native_archive',
                side_effect=AssertionError('Unexpected download'),
            ):
                result = build_release(source, offline, beyond_native_archive=asset)
                with zipfile.ZipFile(offline) as archive:
                    for name, contents in payload.items():
                        self.assertEqual(archive.read(f'plugin/vendor/beyond/{name}'), contents)
                self.assertFalse(any((backend / name).exists() for name in payload))
                self.assertEqual(result['files'], 6)
                corrupt = root / 'corrupt.zip'
                corrupt.write_bytes(asset.read_bytes() + b'tampered')
                invalid = root / 'invalid.zip'
                with self.assertRaises(ValueError):
                    build_release(source, invalid, beyond_native_archive=corrupt)
                self.assertFalse(invalid.exists())

            fetched = root / 'fetched.zip'
            with patch(
                'beyond_native.download_native_archive',
                side_effect=lambda lock, path: shutil.copyfile(asset, path),
            ) as download:
                build_release(source, fetched)
            download.assert_called_once()
            self.assertEqual(fetched.read_bytes(), offline.read_bytes())
            self.assertFalse(any((backend / name).exists() for name in payload))

            repackage = root / 'repackage.zip'
            for name, contents in payload.items():
                file = backend / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(contents)
            with patch(
                'beyond_native.download_native_archive',
                side_effect=AssertionError('Unexpected download'),
            ):
                build_release(source, repackage)
            self.assertEqual(repackage.read_bytes(), offline.read_bytes())

    def test_shared_zip_and_cordis_exclusions(self):
        npm = shutil.which('npm.cmd' if sys.platform == 'win32' else 'npm')
        if not npm:
            self.skipTest('npm required to check the Cordis pack list')
        with tempfile.TemporaryDirectory(prefix='ugc distribution ') as temporary:
            root = Path(temporary)
            source = root / 'source'
            plugin = {
                'name': 'fixture',
                'version': '1.2.3',
                'license': 'GPL-3.0-only',
                'author': {'name': 'Distribution fixture'},
            }
            policy = {
                'schema': 1,
                'exclude_prefixes': [
                    '.ruff_cache/',
                    'node_modules/',
                    'samples/seeds/',
                    'vendor/tool/demo/',
                ],
                'exclude_files': ['assets/private.txt'],
            }
            omitted = {
                '.ruff_cache/fixture',
                'node_modules/local/index.js',
                'samples/seeds/input.txt',
                'vendor/tool/demo/index.js',
                'assets/private.txt',
            }
            retained = {
                'samples/seeds-guide.txt',
                'vendor/tool/index.js',
                'assets/private-example.txt',
                'vendor/beyond/node_modules/runtime/index.js',
            }
            inputs = {
                'plugin.json': json.dumps(plugin),
                '.codex-plugin/plugin.json': json.dumps(
                    {**plugin, 'interface': {'displayName': 'Fixture'}}
                ),
                '.claude-plugin/plugin.json': json.dumps({'description': 'Test plugin'}),
                'distribution.json': json.dumps(policy),
                'skills/fixture/SKILL.md': '---\nname: fixture\ndescription: Distribution fixture\n---\n',
                **dict.fromkeys(omitted | retained, 'Test content'),
            }
            for name, content in inputs.items():
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            manifests = marketplace_files(source)
            claude = json.loads(manifests['.claude-plugin/marketplace.json'])
            self.assertEqual(claude['metadata']['description'], 'Test plugin')
            self.assertEqual(claude['plugins'][0]['source'], './')
            self.assertNotIn('displayName', claude['plugins'][0])
            (source / 'package.json').write_text(manifests['package.json'], encoding='utf-8')
            zip_path = root / 'fixture.zip'
            build_release(source, zip_path, archive_root='fixture')
            with zipfile.ZipFile(zip_path) as archive:
                zip_paths = {name.removeprefix('fixture/') for name in archive.namelist()}
            packed = subprocess.run(
                [
                    npm,
                    'pack',
                    '--dry-run',
                    '--offline',
                    '--ignore-scripts',
                    '--json',
                    '--cache',
                    str(root / 'npm-cache'),
                ],
                cwd=source,
                check=True,
                capture_output=True,
                encoding='utf-8',
                timeout=60,
            )
            cordis_paths = {entry['path'] for entry in json.loads(packed.stdout)[0]['files']}
            for paths in (zip_paths, cordis_paths):
                self.assertTrue(retained <= paths)
                self.assertFalse(omitted & paths)

            policy['exclude_files'] = ['assets/private[1].txt']
            (source / 'distribution.json').write_text(json.dumps(policy), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'literal paths'):
                marketplace_files(source)

    def test_windows_archive_names_and_roundtrip(self):
        for names in (
            ['Bundle/ /file'],
            ['Bundle/ leading/file'],
            ['Bundle/file '],
            ['Bundle/trailing./file'],
            ['Bundle/CON.txt'],
            ['Bundle/good//file'],
            ['Bundle/Foo/a', 'Bundle/foo/b'],
            ['Bundle/file', 'Bundle/FILE/child'],
        ):
            with self.subTest(names=names), self.assertRaises(ValueError):
                validate_windows_names(names)
        with tempfile.TemporaryDirectory(prefix='ugc zip names ') as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            (source / 'SKILL.md').write_text(
                '---\nname: neutral\ndescription: Neutral test\n---\n', encoding='utf-8'
            )
            (source / '中文 文件.txt').write_bytes(b'contents\r\n')
            result = build_release(source, root / 'bundle.zip', archive_root='Bundle')
            self.assertTrue(result['extracted_names_verified'])
            self.assertEqual(result['skills'], 1)
            self.assertEqual(result['utf8_entries'], 1)
            (source / ' bad.txt').touch()
            with self.assertRaisesRegex(ValueError, 'Invalid Windows archive path'):
                build_release(source, root / 'bad.zip', archive_root='Bundle')
            self.assertFalse((root / 'bad.zip').exists())

    def test_changelog_check(self):
        with tempfile.TemporaryDirectory(prefix='ugc release version ') as temporary:
            root = Path(temporary)
            for name in MANIFESTS + REQUIRED_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                manifest = {'name': 'miliastra-wonderland', 'version': '1.2.3'}
                path.write_text(
                    json.dumps(manifest) if name in MANIFESTS else '# Neutral\n', encoding='utf-8'
                )
            github = f'https://github.com/{REPO}/releases'
            install = f'https://raw.githubusercontent.com/{REPO}/v1.2.3/install.ps1'
            zip_name = 'Miliastra-Wonderland-1.2.3-windows-x64.zip'
            (root / 'README.md').write_text(
                f'**当前版本 `1.2.3`**\n{github}/download/v1.2.3/{zip_name}\n',
                encoding='utf-8',
            )
            (root / 'docs/installation.md').write_text(
                f'{github}/tag/v1.2.3\n{install}\n{zip_name}\n',
                encoding='utf-8',
            )
            (root / 'install.ps1').write_text("param([string]$Version = '1.2.3')", encoding='utf-8')
            changelog = root / 'CHANGELOG.md'
            changelog.write_text(
                '# Changes\n\n## Unreleased\n\n## 1.2.2\n\n## 1.2.3\n', encoding='utf-8'
            )
            self.assertTrue(any('CHANGELOG.md' in error for error in check(root)))
            changelog.write_text('# Changes\n\n## Unreleased\n\n## 1.2.3\n', encoding='utf-8')
            self.assertEqual(check(root), [])

    def test_complete_bundle(self):
        root = Path(__file__).resolve().parents[1]
        plugin = read_json(root / 'plugin.json')
        with tempfile.TemporaryDirectory(prefix='ugc release space ') as td:
            temp = Path(td)
            zip_path = temp / 'plugin.zip'
            result = build_release(
                root, zip_path, layout='agent-plugins',
                beyond_native_archive=os.environ.get('MILIASTRA_TEST_BEYOND_ARCHIVE'),
            )
            restored = extract(zip_path, result['sha256'], temp / 'extracted', plugin['version'])
            lock_path = root / 'vendor/beyond/native-canvas.json'
            locked = (
                {
                    Path('vendor/beyond') / name: digest
                    for name, digest in read_json(lock_path)['files'].items()
                }
                if lock_path.is_file()
                else {}
            )
            with zipfile.ZipFile(zip_path) as archive:
                members = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
                versions = WINDOWS_TEST_PROFILE / 'AppData/Local/Miliastra Wonderland/versions'
                for agent in AGENTS:
                    with self.subTest(agent=agent):
                        self.assert_legacy_windows_paths_fit(
                            versions / agent / plugin['version'] / plugin['name'], members
                        )
                for entry in archive.infolist():
                    relative = Path(entry.filename)
                    self.assertNotIn('.git', relative.parts)
                    self.assertNotIn('marketplace', relative.parts)
                    self.assertNotEqual(relative.name, 'marketplace.json')
                    self.assertFalse(entry.filename.endswith('GE_IMG_Tool.exe'))
                    self.assertFalse(entry.filename.endswith('Invoke-Geimg.ps1'))
                    self.assertFalse(entry.filename.endswith('GEIMG LOGO.png'))
                    contents = (restored / relative).read_bytes()
                    if relative in locked:
                        self.assertEqual(hashlib.sha256(contents).hexdigest(), locked[relative])
                    else:
                        self.assertEqual(contents, (root / relative).read_bytes())
            self.assertTrue(all((restored / relative).is_file() for relative in locked))
            bundle = read_json(restored / 'vendor/beyond/bundle.json')
            for path, digest in bundle['files'].items():
                self.assertEqual(
                    hashlib.sha256((restored / 'vendor/beyond' / path).read_bytes()).hexdigest(),
                    digest,
                )
            sources = read_json(restored / 'PUBLIC_SOURCES.json')
            latest = {
                change['path']: change['sha256'] for change in sources['distribution_changes']
            }
            for change in sources['distribution_changes']:
                if 'excluded_files_sha256' not in change:
                    continue
                self.assertEqual(
                    hashlib.sha256((restored / change['path']).read_bytes()).hexdigest(),
                    latest[change['path']],
                )
                for path, digest in change['excluded_files_sha256'].items():
                    self.assertFalse((restored / path).exists(), path)
                    self.assertNotIn(path.removeprefix('vendor/beyond/'), bundle['files'])
                    self.assertFalse((root / path).exists(), path)
                    self.assertRegex(digest, r'^[a-f0-9]{64}$')
            self.assertTrue(list((restored / 'vendor/beyond/node_modules').rglob('*.node')))
            self.assertFalse(list((restored / 'vendor/beyond/node_modules').rglob('*.map')))
            beyond = restored / 'vendor/beyond'
            for path in (
                'studio/index.js', 'studio/host-png.js', 'client/lua-runtime/src/index.js',
                'server/index.js', 'node_modules/@napi-rs/canvas/LICENSE',
                'node_modules/fengari/LICENSE', 'node_modules/protobufjs/LICENSE',
            ):
                self.assertTrue((beyond / path).is_file(), path)
            for path in (
                'web', 'dsh-plugin', 'mcp', 'editor-ui', 'studio/play/pixi-renderer.js',
                'node_modules/pixi.js', 'node_modules/qxqy-studio',
                'node_modules/qxqy-lua-runtime', 'node_modules/qxqy-server',
            ):
                self.assertFalse((beyond / path).exists(), path)


if __name__ == '__main__':
    unittest.main()
