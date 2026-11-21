"""Focused release tests using small temporary Git repositories."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from check_repository import check, MANIFESTS, REQUIRED_FILES, REPO
from prepare_release import prepare
from package_release import build_release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ugc release test ")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "repository with spaces"
        self.root.mkdir()
        self.notes = self.base / "notes.md"
        self.notes.write_text("Synthetic release. Host not checked.\n", encoding="utf-8")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.STDOUT)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def fixture(self, version="1.2.3"):
        self.git("init", "--quiet")
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "release@example.invalid")
        for name in REQUIRED_FILES:
            self.write(name, "Fixture\n")
        asset = f"Genshin-UGC-{version}-windows-x64.zip"
        install = f"https://raw.githubusercontent.com/{REPO}/v{version}/install.ps1"
        releases = f"https://github.com/{REPO}/releases"
        self.write("README.md", f"**当前版本 `{version}`**\n[ZIP]({releases}/download/v{version}/{asset})\n"
                               f"```powershell\nInstall from {install}\n```\n")
        self.write("docs/installation.md", f"[Release]({releases}/tag/v{version})\n"
                                           f"```powershell\nInstall from {install}\n"
                                           f"Install from {asset}\nRollback -Version 0.1.0\n```\n")
        self.write("CHANGELOG.md", f"# Fixture\n\n## {version}\n")
        for name in MANIFESTS:
            self.write(name, json.dumps({"name": "fixture", "version": version, "skills": "./skills/"}))
        self.write("install.ps1", f"param([string]$Version = '{version}')\n")
        self.write("skills/fixture/SKILL.md", "---\nname: fixture\ndescription: Neutral fixture\n---\n")
        self.write("vendor/beyond/node_modules/fixture/index.js", "export const value = 1;\n")
        self.write("runtime/fixture.bin", "neutral binary input\n")
        self.write("references/中文 文件.txt", "Unicode fixture\n")
        self.write(".gitignore", ".venv/\n")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "fixture")
        self.write(".venv/private.txt", "must never be packaged")

    def test_complete_deterministic_assets(self):
        for version in ("1.2.3", "4.5.6"):
            with self.subTest(version=version):
                self.fixture(version)
                first = self.base / (version + " first")
                second = self.base / (version + " second")
                report = prepare(self.root, first, self.notes)
                again = prepare(self.root, second, self.notes)
                self.assertEqual(report, again)
                self.assertFalse(report["published"])
                self.assertEqual(report["source_commit"], self.git("rev-parse", "HEAD").decode().strip())
                for name, sha in report["assets"].items():
                    self.assertEqual(hashlib.sha256((first / name).read_bytes()).hexdigest(), sha)
                    self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
                filename = f"Genshin-UGC-{version}-windows-x64.zip"
                self.assertEqual(set(report["assets"]), {filename})
                self.assertEqual({p.name for p in first.iterdir()}, {filename, "release-notes.md", "release-review.json"})
                with zipfile.ZipFile(first / f"Genshin-UGC-{version}-windows-x64.zip") as archive:
                    names = archive.namelist()
                    self.assertIn("Genshin-UGC/vendor/beyond/node_modules/fixture/index.js", names)
                    self.assertIn("Genshin-UGC/runtime/fixture.bin", names)
                    self.assertIn("Genshin-UGC/references/中文 文件.txt", names)
                    self.assertFalse(any("/.git/" in n or "/.venv/" in n for n in names))
                    self.assertEqual(archive.read("Genshin-UGC/install.ps1"), (self.root / "install.ps1").read_bytes())
                with self.assertRaisesRegex(ValueError, "new directory"):
                    prepare(self.root, first, self.notes)


    def test_zip_verification_failure_keeps_target_absent(self):
        self.fixture()
        output = self.base / 'failed.zip'
        with patch.object(zipfile.ZipFile, 'testzip', return_value='bad entry'):
            with self.assertRaisesRegex(ValueError, 'CRC'):
                build_release(self.root, output, archive_root='Fixture')
        self.assertFalse(output.exists())
        self.assertEqual(list(self.base.glob('.ugc-package-*')), [])
        output.write_bytes(b'original')
        with self.assertRaises(FileExistsError):
            build_release(self.root, output, archive_root='Fixture')
        self.assertEqual(output.read_bytes(), b'original')

    def test_link_checks_cover_first_party_and_skip_code_and_snapshots(self):
        self.fixture()
        self.write('references/中文 文件(例).md', '# Fixture')
        self.write('skills/fixture/reference.md',
                   '[valid](<../../references/中文 文件(例).md> "title")\n'
                   '~~~md\n[example](absent.md)\n~~~\n'
                   '```md\n[example](absent.md)\n```\n'
                   '    [indented example](absent.md)\n'
                   '[bad]: missing.md\n')
        self.write('references/official/raw.md', '[raw](absent.md)')
        self.write('references/registered.md', '[raw](absent.md)')
        self.write('PUBLIC_SOURCES.json', json.dumps({'permission_unverified_files': [{'path': 'references/registered.md'}]}))
        errors = check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('missing.md', errors[0])

    def test_active_install_documentation_versions(self):
        self.fixture()
        self.assertEqual(check(self.root), [])
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        install = (self.root / "docs/installation.md").read_text(encoding="utf-8")
        for file, text, old, new, label in (
            ("README.md", readme, "当前版本 `1.2.3`", "当前版本 `1.2.2`", "current version"),
            ("README.md", readme, "download/v1.2.3", "download/v1.2.2", "download tag"),
            ("docs/installation.md", install, "/tag/v1.2.3", "/tag/v1.2.2", "release tag"),
            ("docs/installation.md", install, "/v1.2.3/install.ps1", "/v1.2.2/install.ps1", "install command tag"),
            ("docs/installation.md", install, "Genshin-UGC-1.2.3-", "Genshin-UGC-1.2.2-", "ZIP filename"),
        ):
            with self.subTest(file=file, label=label):
                self.write(file, text.replace(old, new))
                self.assertTrue(any(label in error for error in check(self.root)))
                self.write(file, text)
        self.write("docs/contributing/guide.md", "[bad](missing.md)")
        self.assertTrue(any("missing.md" in error for error in check(self.root)))

    def test_dirty_input_rejected_without_output(self):
        self.fixture()
        self.write("pending.txt", "uncommitted")
        output = self.base / "output"
        with self.assertRaisesRegex(ValueError, "pending changes"):
            prepare(self.root, output, self.notes)
        self.assertFalse(output.exists())

    def test_installer_version_and_manifest_errors(self):
        self.fixture()
        self.write("install.ps1", "param([string]$Version = '9.0.0')")
        self.assertTrue(any("default version" in e for e in check(self.root)))
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "mismatch")
        with self.assertRaisesRegex(ValueError, "default version"):
            prepare(self.root, self.base / "output", self.notes)
        self.assertFalse((self.base / "output").exists())
        for invalid in ([], {"version": []}, {"version": "broken"}):
            self.write("plugin.json", json.dumps(invalid))
            self.assertTrue(check(self.root))

    def test_packaging_failure_is_not_committed(self):
        self.fixture()
        output = self.base / "failed"
        with patch("prepare_release.build_release", side_effect=ValueError("test failure")):
            with self.assertRaisesRegex(ValueError, "test failure"):
                prepare(self.root, output, self.notes)
        self.assertFalse(output.exists())
        with self.assertRaisesRegex(ValueError, "outside"):
            prepare(self.root, self.root / "release", self.notes)


if __name__ == "__main__":
    unittest.main()
