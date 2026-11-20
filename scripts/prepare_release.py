"""Prepare local release assets from a clean Git commit. Never push or publish."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from check_repository import check
from package_release import build_release, validate_windows_names

ROOT = Path(__file__).resolve().parents[1]


def prepare(source: Path, output: Path, notes: Path) -> dict:
    source, output, notes = source.resolve(), output.resolve(), notes.resolve()
    if output.exists() or output.is_relative_to(source):
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
    with tempfile.TemporaryDirectory(prefix="ugc-release-", dir=output.parent) as temporary:
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
        filename = f"Genshin-UGC-{version}-windows-x64.zip"
        package = build_release(tree, staged / filename, "plugin", "Genshin-UGC")
        shutil.copyfile(tree / "install.ps1", staged / "install.ps1")
        assets = {name: hashlib.sha256((staged / name).read_bytes()).hexdigest()
                  for name in (filename, "install.ps1")}
        (staged / "SHA256SUMS.txt").write_text("".join(f"{sha}  {name}\n" for name, sha in assets.items()), encoding="utf-8")
        (staged / "release-notes.md").write_text(release_notes, encoding="utf-8")
        report = {"schema": 1, "version": version, "tag": "v" + version,
                  "source_commit": commit, "package": package, "assets": assets,
                  "notes_sha256": hashlib.sha256((staged / "release-notes.md").read_bytes()).hexdigest(),
                  "published": False, "client_loading": "not_checked", "game_host": "not_checked"}
        (staged / "release-review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if git("rev-parse", "HEAD") != commit or git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("Repository changed while preparing assets")
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
