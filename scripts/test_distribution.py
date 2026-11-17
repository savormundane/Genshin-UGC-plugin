"""Manual release check: actual ZIP structure, extraction and content identity."""
from pathlib import Path
import hashlib,tempfile,unittest,zipfile
from package_release import build_release
from install_public import extract,read_json


class ReleaseTests(unittest.TestCase):
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
                    self.assertFalse(entry.filename.endswith('GE_IMG_Tool.exe'))
                    self.assertFalse(entry.filename.endswith('Invoke-Geimg.ps1'))
                    self.assertEqual((restored/relative).read_bytes(),(root/relative).read_bytes())
            bundle=read_json(restored/'vendor/beyond/bundle.json')
            for path,digest in bundle['files'].items():
                self.assertEqual(hashlib.sha256((restored/'vendor/beyond'/path).read_bytes()).hexdigest(),digest)
            self.assertTrue(list((restored/'vendor/beyond/node_modules').rglob('*.node')))
            self.assertFalse(list((restored/'vendor/beyond/node_modules').rglob('*.map')))


if __name__=='__main__':unittest.main()
