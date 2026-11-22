"""Manual release check: actual ZIP structure, extraction and content identity."""
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
from check_repository import check, MANIFESTS, REPO, REQUIRED_FILES
from package_release import build_release, validate_windows_names
from install_public import extract,read_json


class ReleaseTests(unittest.TestCase):
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
                path.write_text(json.dumps({'version': '1.2.3'}) if name in MANIFESTS else '# Neutral\n', encoding='utf-8')
            github = f'https://github.com/{REPO}/releases'
            install = f'https://raw.githubusercontent.com/{REPO}/v1.2.3/install.ps1'
            zip_name = 'Genshin-UGC-1.2.3-windows-x64.zip'
            (root/'README.md').write_text(
                f'**当前版本 `1.2.3`**\n{github}/download/v1.2.3/{zip_name}\n{install}\n',
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
            result=build_release(root,zip_path,archive_root='Genshin-UGC')
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
            self.assertTrue(list((restored/'vendor/beyond/node_modules').rglob('*.node')))
            self.assertFalse(list((restored/'vendor/beyond/node_modules').rglob('*.map')))


if __name__=='__main__':unittest.main()
