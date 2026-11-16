"""Focused release tests using small temporary Git repositories."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from check_repository import check, MANIFESTS, REQUIRED_FILES
from prepare_release import prepare


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
        for name in MANIFESTS:
            self.write(name, json.dumps({"name": "fixture", "version": version, "skills": "./skills/"}))
        self.write("install.ps1", f"param([string]$Version = '{version}')\n")
        self.write("skills/fixture/SKILL.md", "---\nname: fixture\ndescription: Neutral fixture\n---\n")
        self.write("vendor/beyond/node_modules/fixture/index.js", "export const value = 1;\n")
        self.write("runtime/fixture.bin", "neutral binary input\n")
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
                with zipfile.ZipFile(first / f"Genshin-UGC-{version}-windows-x64.zip") as archive:
                    names = archive.namelist()
                    self.assertIn("Genshin-UGC/vendor/beyond/node_modules/fixture/index.js", names)
                    self.assertIn("Genshin-UGC/runtime/fixture.bin", names)
                    self.assertFalse(any("/.git/" in n or "/.venv/" in n for n in names))
                    self.assertEqual(archive.read("Genshin-UGC/install.ps1"), (first / "install.ps1").read_bytes())
                with self.assertRaisesRegex(ValueError, "new directory"):
                    prepare(self.root, first, self.notes)

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
