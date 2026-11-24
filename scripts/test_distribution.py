"""Manual release check: actual ZIP structure, extraction and content identity."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile,unittest,zipfile
from check_repository import check, MANIFESTS, REPO, REQUIRED_FILES
from marketplace_release import marketplace_files
from package_release import build_release, validate_windows_names
from install_plugin import extract,read_json


class ReleaseTests(unittest.TestCase):
    def test_shared_zip_and_cordis_exclusions(self):
        npm = shutil.which('npm.cmd' if sys.platform == 'win32' else 'npm')
        if not npm:
            self.skipTest('npm required to check the Cordis pack list')
        with tempfile.TemporaryDirectory(prefix='ugc distribution ') as temporary:
            root = Path(temporary)
            source = root / 'source'
            plugin = {'name': 'fixture', 'version': '1.2.3', 'license': 'GPL-3.0-only',
                      'author': {'name': 'Distribution fixture'}}
            policy = {'schema': 1, 'exclude_prefixes': ['samples/seeds/', 'vendor/tool/demo/'],
                      'exclude_files': ['assets/private.txt']}
            omitted = {'samples/seeds/input.txt', 'vendor/tool/demo/index.js', 'assets/private.txt'}
            retained = {'samples/seeds-guide.txt', 'vendor/tool/index.js', 'assets/private-example.txt'}
            inputs = {
                'plugin.json': json.dumps(plugin),
                '.codex-plugin/plugin.json': json.dumps({**plugin, 'interface': {'displayName': 'Fixture'}}),
                '.claude-plugin/plugin.json': json.dumps({'displayName': 'Fixture', 'description': 'Test plugin'}),
                'distribution.json': json.dumps(policy),
                'skills/fixture/SKILL.md': '---\nname: fixture\ndescription: Distribution fixture\n---\n',
                **dict.fromkeys(omitted | retained, 'Test content'),
            }
            for name, content in inputs.items():
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            (source / 'package.json').write_text(marketplace_files(source)['package.json'], encoding='utf-8')
            zip_path = root / 'fixture.zip'
            build_release(source, zip_path, archive_root='fixture')
            with zipfile.ZipFile(zip_path) as archive:
                zip_paths = {name.removeprefix('fixture/') for name in archive.namelist()}
            packed = subprocess.run([npm, 'pack', '--dry-run', '--offline', '--ignore-scripts', '--json',
                                     '--cache', str(root / 'npm-cache')],
                                    cwd=source, check=True, capture_output=True, encoding='utf-8', timeout=60)
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
                ['Bundle/ /file'], ['Bundle/ leading/file'], ['Bundle/file '],
                ['Bundle/trailing./file'], ['Bundle/CON.txt'], ['Bundle/good//file'],
                ['Bundle/Foo/a', 'Bundle/foo/b'], ['Bundle/file', 'Bundle/FILE/child']):
            with self.subTest(names=names), self.assertRaises(ValueError):
                validate_windows_names(names)
        with tempfile.TemporaryDirectory(prefix='ugc zip names ') as temporary:
            root = Path(temporary)
            source = root/'source'
            source.mkdir()
            (source/'SKILL.md').write_text('---\nname: neutral\ndescription: Neutral test\n---\n', encoding='utf-8')
            (source/'中文 文件.txt').write_bytes(b'contents\r\n')
            result = build_release(source, root/'bundle.zip', archive_root='Bundle')
            self.assertTrue(result['extracted_names_verified'])
            self.assertEqual(result['skills'], 1)
            self.assertEqual(result['utf8_entries'], 1)
            (source/' bad.txt').touch()
            with self.assertRaisesRegex(ValueError, 'Invalid Windows archive path'):
                build_release(source, root/'bad.zip', archive_root='Bundle')
            self.assertFalse((root/'bad.zip').exists())

    def test_changelog_check(self):
        with tempfile.TemporaryDirectory(prefix='ugc release version ') as temporary:
            root = Path(temporary)
            for name in MANIFESTS + REQUIRED_FILES:
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                manifest = {'name': 'miliastra-wonderland', 'version': '1.2.3'}
                path.write_text(json.dumps(manifest) if name in MANIFESTS else '# Neutral\n', encoding='utf-8')
            github = f'https://github.com/{REPO}/releases'
            install = f'https://raw.githubusercontent.com/{REPO}/v1.2.3/install.ps1'
            zip_name = 'Miliastra-Wonderland-1.2.3-windows-x64.zip'
            (root/'README.md').write_text(
                f'**当前版本 `1.2.3`**\n{github}/download/v1.2.3/{zip_name}\n',
                encoding='utf-8',
            )
            (root/'docs/installation.md').write_text(
                f'{github}/tag/v1.2.3\n{install}\n{zip_name}\n', encoding='utf-8',
            )
            (root/'install.ps1').write_text("param([string]$Version = '1.2.3')", encoding='utf-8')
            changelog = root/'CHANGELOG.md'
            changelog.write_text('# Changes\n\n## Unreleased\n\n## 1.2.2\n\n## 1.2.3\n', encoding='utf-8')
            self.assertTrue(any('CHANGELOG.md' in error for error in check(root)))
            changelog.write_text('# Changes\n\n## Unreleased\n\n## 1.2.3\n', encoding='utf-8')
            self.assertEqual(check(root), [])

    def test_complete_bundle(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='ugc release space ') as td:
            temp=Path(td);zip_path=temp/'plugin.zip'
            result=build_release(root,zip_path,archive_root='miliastra-wonderland')
            restored=extract(zip_path,result['sha256'],temp/'extracted',read_json(root/'plugin.json')['version'])
            with zipfile.ZipFile(zip_path) as archive:
                for entry in archive.infolist():
                    path=Path(entry.filename);relative=Path(*path.parts[1:])
                    self.assertNotIn('.git',path.parts)
                    self.assertNotIn('marketplace', relative.parts)
                    self.assertNotEqual(relative.name, 'marketplace.json')
                    self.assertFalse(entry.filename.endswith('GE_IMG_Tool.exe'))
                    self.assertFalse(entry.filename.endswith('Invoke-Geimg.ps1'))
                    self.assertFalse(entry.filename.endswith('GEIMG LOGO.png'))
                    self.assertEqual((restored/relative).read_bytes(),(root/relative).read_bytes())
            bundle=read_json(restored/'vendor/beyond/bundle.json')
            for path,digest in bundle['files'].items():
                self.assertEqual(hashlib.sha256((restored/'vendor/beyond'/path).read_bytes()).hexdigest(),digest)
            sources = read_json(restored/'PUBLIC_SOURCES.json')
            for change in sources['distribution_changes']:
                if 'excluded_files_sha256' not in change:
                    continue
                self.assertEqual(hashlib.sha256((restored/change['path']).read_bytes()).hexdigest(), change['sha256'])
                for path, digest in change['excluded_files_sha256'].items():
                    self.assertFalse((restored/path).exists(), path)
                    self.assertNotIn(path.removeprefix('vendor/beyond/'), bundle['files'])
                    self.assertEqual(hashlib.sha256((root/path).read_bytes()).hexdigest(), digest)
            self.assertTrue(list((restored/'vendor/beyond/node_modules').rglob('*.node')))
            self.assertFalse(list((restored/'vendor/beyond/node_modules').rglob('*.map')))


if __name__=='__main__':unittest.main()
