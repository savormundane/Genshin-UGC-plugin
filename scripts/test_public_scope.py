import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import zipfile

from check_public_scope import check_entries, check_git, check_npm_metadata, check_tree, require_distributable
from package_release import build_release


class PublicScopeTests(unittest.TestCase):
    def test_git_archive_drains_padding_before_waiting_for_exit(self):
        policy = b"public-files.txt\n"
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            member = tarfile.TarInfo("public-files.txt")
            member.size = len(policy)
            archive.addfile(member, io.BytesIO(policy))
        stream.write(b"\0" * 64 * 1024)
        expected_end = stream.tell()
        stream.seek(0)
        process = MagicMock()
        process.__enter__.return_value = process
        process.stdout = stream

        def wait():
            self.assertEqual(stream.tell(), expected_end)
            return 0

        process.wait.side_effect = wait
        git_results = (b"fixture-tree\n", policy, b"100644 blob fixture\tpublic-files.txt\0")
        with patch("check_public_scope.subprocess.check_output", side_effect=git_results), \
             patch("check_public_scope.subprocess.Popen", return_value=process):
            self.assertEqual(check_git("HEAD"), [])
        process.wait.assert_called_once()

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

    def test_excluded_originals_stay_out_even_if_renamed_in_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = b"an original kept outside this distribution"
            (root / "public-files.txt").write_text(
                "PUBLIC_SOURCES.json\nSKILL.md\ncopy.md\noriginal.md\npublic-files.txt\n", encoding="utf-8"
            )
            (root / "PUBLIC_SOURCES.json").write_text(json.dumps({
                "permission_unverified_files": [],
                "excluded_unverified_files": [
                    {"path": "original.md", "sha256": hashlib.sha256(original).hexdigest()}
                ],
            }), encoding="utf-8")
            (root / "SKILL.md").write_text("---\nname: fixture\ndescription: Fixture\n---\n", encoding="utf-8")
            (root / "original.md").write_text("Path is still excluded.", encoding="utf-8")
            (root / "copy.md").write_bytes(original)
            failures = check_tree(root)
            self.assertIn("Excluded redistribution path: 'original.md'", failures)
            self.assertIn("Excluded redistribution bytes: 'copy.md'", failures)
            with self.assertRaisesRegex(ValueError, "Restricted package content"):
                build_release(root, root.parent / (root.name + ".zip"))

    def test_npm_version_allows_inherited_contacts_and_rejects_new_ones(self):
        archive = Path("fixture-1.0.1.tgz")
        prior = {"name": "maintainer", "email": "historical@example.test"}
        metadata = {
            "name": "fixture", "version": "1.0.1", "maintainers": [prior],
            "_npmUser": {"trustedPublisher": {"id": "github"}, "email": "npm-oidc-no-reply@github.com"},
            "dist": {"attestations": {"provenance": {"predicateType": "fixture"}}},
        }
        history = {"name": "fixture", "versions": {"1.0.0": {"maintainers": [prior]}}}
        approved = "approved@example.test"
        check_npm_metadata(metadata, approved, archive, history=history)
        metadata["maintainers"] = [prior, {"name": "new", "email": approved.upper()}]
        check_npm_metadata(metadata, approved, archive, history=history)
        for record in ({"name": "new", "email": prior["email"]},
                       {"name": prior["name"], "email": "unapproved@example.test"}):
            with self.subTest(record=record):
                metadata["maintainers"] = [record]
                history["versions"]["1.0.1"] = metadata
                with self.assertRaisesRegex(ValueError, "outside the approved public contact"):
                    check_npm_metadata(metadata, approved, archive, history=history)

    def test_npm_version_checks_publisher_and_registry_source(self):
        archive = Path("fixture-1.0.0.tgz")
        metadata = {
            "name": "fixture",
            "_npmUser": {"trustedPublisher": {"id": "github"}, "email": "npm-oidc-no-reply@github.com"},
            "dist": {"attestations": {"provenance": {"predicateType": "fixture"}}},
            "_from": f"file:./{archive.name}",
            "_resolved": str(archive.resolve().as_posix()),
        }
        check_npm_metadata(metadata, "", archive)
        metadata["_resolved"] = "file:" + "C:/Users/" + "test-account/Documents/fixture.tgz"
        with self.assertRaisesRegex(ValueError, "unexpected package source path"):
            check_npm_metadata(metadata, "", archive)
        metadata.pop("_resolved")
        metadata["_npmUser"]["email"] = "private@example.test"
        with self.assertRaisesRegex(ValueError, "lacks direct GitHub trusted publishing provenance"):
            check_npm_metadata(metadata, "", archive)

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

    def test_zip_requires_approved_inputs_after_distribution_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "skill"
            source.mkdir()
            (source / "SKILL.md").write_text(
                "---\nname: fixture\ndescription: Fixture\n---\n", encoding="utf-8"
            )
            (source / "public-files.txt").write_text(
                "SKILL.md\ndistribution.json\nignored/demo.md\npublic-files.txt\nruntime.json\ntool.py\n",
                encoding="utf-8",
            )
            (source / "distribution.json").write_text(
                json.dumps({
                    "schema": 1,
                    "exclude_prefixes": ["ignored/"],
                    "exclude_files": ["public-files.txt", "runtime.json"],
                }),
                encoding="utf-8",
            )
            output = Path(temp) / "fixture.zip"
            tool = source / "tool.py"
            for wrong_input in ("absent", "directory"):
                with self.subTest(wrong_input=wrong_input):
                    if wrong_input == "directory":
                        tool.mkdir()
                    with self.assertRaisesRegex(ValueError, "Approved package input.*tool[.]py"):
                        build_release(source, output, "skill")
                    self.assertFalse(output.exists())
            tool.rmdir()
            tool.write_text("value = 1\n", encoding="utf-8")
            build_release(source, output, "skill")
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"skill/SKILL.md", "skill/distribution.json", "skill/tool.py"},
                )


if __name__ == "__main__":
    unittest.main()
