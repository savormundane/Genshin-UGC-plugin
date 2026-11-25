"""Prepare local release assets from a clean Git commit. Never push or publish."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from check_repository import (
    CHANGELOG_VERSION, DOC_VERSIONS, INSTALLER_VERSION, SEMVER, SOURCE_DOC_VERSIONS, check,
)
from package_release import agent_plugins_zip_name, build_release, sha256_file, validate_windows_names

ROOT = Path(__file__).resolve().parents[1]


def sync_release_text(root: Path) -> None:
    """Update release-facing text in the staged source tree from its manifest."""
    version = json.loads((root / "plugin.json").read_text(encoding="utf-8-sig"))["version"]
    if not isinstance(version, str) or not re.fullmatch(SEMVER, version):
        raise ValueError("Expected x.y.z release version")

    def replace_version(match: re.Match[str]) -> str:
        start, end = match.span(1)
        offset = match.start()
        return match[0][:start - offset] + version + match[0][end - offset:]

    for relative, patterns in DOC_VERSIONS.items():
        path = root / relative
        content = path.read_bytes().decode("utf-8")
        for pattern in dict.fromkeys((*patterns.values(), *SOURCE_DOC_VERSIONS[relative].values())):
            content = re.sub(pattern, replace_version, content)
        path.write_bytes(content.encode("utf-8"))

    installer = root / "install.ps1"
    updated, count = re.subn(INSTALLER_VERSION, replace_version, installer.read_bytes().decode("utf-8"))
    if count != 1:
        raise ValueError("Expected one default version in install.ps1")
    installer.write_bytes(updated.encode("utf-8"))

    changelog = root / "CHANGELOG.md"
    content = changelog.read_bytes().decode("utf-8")
    released = re.search(CHANGELOG_VERSION, content, re.M)
    if released and released[1] == version:
        return
    line_end = "\r\n" if "\r\n" in content else "\n"
    heading = f"## {version}{line_end}"
    unreleased = re.search(r"^##[ \t]+Unreleased[ \t]*(?:\r?\n|$)", content, re.M)
    if unreleased:
        position = unreleased.end()
        content = content[:position].rstrip("\r\n") + line_end * 2 + heading + content[position:]
    elif released:
        position = released.start()
        content = content[:position] + heading + line_end + content[position:]
    else:
        content = content.rstrip("\r\n") + line_end * 2 + heading
    changelog.write_bytes(content.encode("utf-8"))


def prepare(source: Path, output: Path, notes: Path) -> dict:
    source, output, notes = source.resolve(), output.absolute(), notes.resolve()
    if os.path.lexists(output) or output.resolve().is_relative_to(source):
        raise ValueError("Output must be a new directory outside the repository")
    release_notes = notes.read_text(encoding="utf-8-sig")
    if not release_notes.strip():
        raise ValueError("Release notes must not be empty")

    def git(*args: str) -> str:
        return subprocess.check_output(["git", "-C", str(source), *args], encoding="utf-8").strip()

    if Path(git("rev-parse", "--show-toplevel")).resolve() != source:
        raise ValueError("Source must be the Git repository root")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("Commit or remove pending changes before preparing release assets")
    commit = git("rev-parse", "HEAD")
    # Only committed inputs are exported. Ignored environments and local files
    # cannot accidentally enter the distribution through a filesystem scan.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="miliastra-release-", dir=output.parent) as temporary:
        temporary = Path(temporary)
        snapshot = temporary / "source.zip"
        subprocess.run(["git", "-C", str(source), "archive", "--format=zip",
                        "--output=" + str(snapshot), commit], check=True)
        tree = temporary / "source"
        tree.mkdir()
        with zipfile.ZipFile(snapshot) as archive:
            validate_windows_names(archive.namelist())
            for member in archive.infolist():
                if not (tree / member.filename).resolve().is_relative_to(tree) or (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Unsafe or linked source entry: " + member.filename)
            archive.extractall(tree)
        errors = check(tree)
        if errors:
            raise ValueError("\n".join(errors))
        version = json.loads((tree / "plugin.json").read_text(encoding="utf-8-sig"))["version"]
        staged = temporary / "assets"
        staged.mkdir()
        filename = agent_plugins_zip_name(version)
        package = build_release(tree, staged / filename, "agent-plugins")
        assets = {filename: package["sha256"]}
        (staged / "release-notes.md").write_text(release_notes, encoding="utf-8")
        report = {"schema": 1, "version": version, "tag": "v" + version,
                  "source_commit": commit, "package": package, "assets": assets,
                  "notes_sha256": sha256_file(staged / "release-notes.md"),
                  "published": False, "client_loading": "not_checked", "game_host": "not_checked"}
        (staged / "release-review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if git("rev-parse", "HEAD") != commit or git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("Repository changed while preparing assets")
        if os.path.lexists(output):
            raise FileExistsError(f"Output already exists: {output}")
        staged.rename(output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--notes", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(ROOT, args.output, args.notes), ensure_ascii=False, indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Release preparation failed: {exc}\n")
