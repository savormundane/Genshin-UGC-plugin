from pathlib import Path
import tempfile
import unittest
import zipfile

from check_public_scope import check_entries, check_tree, require_distributable
from package_release import build_release


class PublicScopeTests(unittest.TestCase):
    def test_unlisted_file_and_private_path_are_rejected(self):
        allowed = {"docs/public.md", "public-files.txt", "notes/AGENTS.md"}
        findings = check_entries({"docs/public.md", "docs/draft.md", "notes/AGENTS.md"}, allowed)
        self.assertEqual(len(findings), 2)
        self.assertTrue(any("Private path" in finding for finding in findings))
        self.assertTrue(any("outside public allowlist" in finding for finding in findings))

    def test_content_is_checked_even_in_reviewed_paths_without_printing_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "public-files.txt").write_text("guide.md\npublic-files.txt\n", encoding="utf-8")
            guide = root / "guide.md"
            guide.write_text("A public example.\n", encoding="utf-8")
            self.assertEqual(check_tree(root), [])
            marker = "ghp_" + "A" * 36
            guide.write_text(marker + "\nC:/Users/" + "test-account/Documents/work\n", encoding="utf-8")
            findings = check_tree(root)
            self.assertEqual(set(findings), {"GitHub token: 'guide.md'", "personal absolute path: 'guide.md'"})
            self.assertNotIn(marker, "\n".join(findings))

    def test_pending_rights_only_block_publication(self):
        with self.assertRaisesRegex(ValueError, "1 unresolved redistribution"):
            require_distributable({"permission_unverified_files": [{"path": "fixture.md"}]})
        require_distributable({"permission_unverified_files": []})

    def test_zip_uses_the_allowlist_at_the_file_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "skill"
            source.mkdir()
            (source / "public-files.txt").write_text("SKILL.md\npublic-files.txt\n", encoding="utf-8")
            (source / "SKILL.md").write_text("---\nname: fixture\ndescription: Fixture\n---\n",
                                             encoding="utf-8")
            (source / "draft.md").write_text("Internal fixture", encoding="utf-8")
            output = Path(temp) / "fixture.zip"
            build_release(source, output, "skill")
            with zipfile.ZipFile(output) as archive:
                self.assertIn("skill/SKILL.md", archive.namelist())
                self.assertNotIn("skill/draft.md", archive.namelist())


if __name__ == "__main__":
    unittest.main()
