"""Prepare local release assets from a clean Git commit. Never push or publish."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

from check_repository import (
    CHANGELOG_VERSION, DOC_VERSIONS, INSTALLER_VERSION, MANIFESTS, SEMVER, SOURCE_DOC_VERSIONS, check,
)
from package_release import (
    agent_plugins_zip_name, build_release, distribution_exclusions, sha256_file,
    validate_windows_names,
)

ROOT = Path(__file__).resolve().parents[1]
DSH_PACKAGE = "dsh-miliastra-wonderland"


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


def set_release_version(root: Path, version: str) -> None:
    """Synchronize a candidate version without creating a Git tag or release."""
    from marketplace_release import marketplace_files

    if not re.fullmatch(SEMVER, version, re.ASCII):
        raise ValueError("Expected x.y.z release version")
    values = tuple(map(int, version.split(".")))
    if ".".join(map(str, values)) != version:
        raise ValueError("Release version components must not have leading zeros")
    current = json.loads((root / "plugin.json").read_text(encoding="utf-8-sig"))["version"]
    if values < tuple(map(int, current.split("."))):
        raise ValueError(f"Release version cannot move backwards from {current}")

    def write_json_text(path, content):
        previous = path.read_bytes() if path.is_file() else b""
        newline = "\r\n" if b"\r\n" in previous else "\n"
        path.write_text(content, encoding="utf-8", newline=newline)

    for relative in MANIFESTS:
        path = root / relative
        contents = json.loads(path.read_text(encoding="utf-8-sig"))
        if contents["version"] != version:
            contents["version"] = version
            write_json_text(path, json.dumps(contents, ensure_ascii=False, indent=2) + "\n")
    for relative, content in marketplace_files(root).items():
        target = root / relative
        if not target.is_file() or target.read_text(encoding="utf-8-sig") != content:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_json_text(target, content)
    sync_release_text(root)
    errors = check(root)
    if errors:
        raise ValueError("\n".join(errors))


def package_npm(tree: Path, output: Path, version: str) -> dict:
    """Build and check the Cordis archive against the committed source snapshot."""
    package = json.loads((tree / "package.json").read_text(encoding="utf-8-sig"))
    if package.get("name") != DSH_PACKAGE or package.get("version") != version:
        raise ValueError(f"Expected npm manifest {DSH_PACKAGE}@{version}")
    filename = f"{DSH_PACKAGE}-{version}.tgz"
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if npm is None:
        raise ValueError("npm is required to prepare the Cordis archive")
    subprocess.run(
        [npm, "pack", "--offline", "--ignore-scripts", "--loglevel=error",
         "--pack-destination", str(output)],
        cwd=tree, check=True, stdout=subprocess.DEVNULL,
    )
    tgz = output / filename
    prefixes, excluded = distribution_exclusions(tree, required=True)
    native_lock = json.loads((tree / "vendor/beyond/native-canvas.json").read_text(encoding="utf-8"))
    excluded.extend(f"vendor/beyond/{path}" for path in native_lock["files"])
    from check_public_scope import POLICY, check_entries, read_policy
    policy = tree / POLICY
    approved = read_policy(policy.read_bytes()) if policy.is_file() else None
    required = {
        "package.json", "cordis.patch.yml", "plugin.json", "README.md", "LICENSE",
        "THIRD_PARTY_NOTICES.md", "PUBLIC_SOURCES.json", "pyproject.toml", "uv.lock",
        "scripts/mcp_launcher.cjs", "scripts/dsh-paths.mjs", "scripts/dsh-runtime-check.mjs",
        "assets/icon.png", "locale/en.json", "locale/zh.json", "docs/dsh/overview.en.md",
        "docs/dsh/overview.zh.md", "vendor/beyond/native-canvas.json",
        *(skill.relative_to(tree).as_posix() for skill in tree.glob("skills/*/SKILL.md")),
    }
    with tarfile.open(tgz, "r:gz") as archive:
        entries = archive.getmembers()
        names = [entry.name.removeprefix("package/") for entry in entries]
        validate_windows_names(names)
        if approved is not None:
            problems = check_entries(names, approved)
            if problems:
                raise ValueError("\n".join(problems))
        for entry, relative in zip(entries, names, strict=True):
            if (not entry.isfile() or relative == entry.name
                    or any(part in ("", ".", "..") for part in relative.split("/"))
                    or relative in excluded or relative.startswith(tuple(prefixes))):
                raise ValueError(f"Unexpected npm archive member: {entry.name}")
            source = tree / relative
            archived = archive.extractfile(entry)
            if archived is None or not source.is_file() or archived.read() != source.read_bytes():
                raise ValueError(f"npm member differs from source snapshot: {relative}")
        missing = required.difference(names)
        if missing:
            raise ValueError(f"Missing npm archive members: {', '.join(sorted(missing))}")
    return {"filename": filename, "files": len(names), "sha256": sha256_file(tgz)}


def prepare(
    source: Path, output: Path, notes: Path | None = None, *,
    expected_version: str | None = None, with_npm: bool = False,
    beyond_native_archive: Path | None = None,
) -> dict:
    source, output = source.resolve(), output.absolute()
    if os.path.lexists(output) or output.resolve().is_relative_to(source):
        raise ValueError("Output must be a new directory outside the repository")
    output = output.parent.resolve() / output.name

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
        from check_public_scope import POLICY, check_tree
        if (source / POLICY).is_file():
            problems = check_tree(tree)
            if problems:
                raise ValueError("\n".join(problems))
        errors = check(tree)
        if errors:
            raise ValueError("\n".join(errors))
        version = json.loads((tree / "plugin.json").read_text(encoding="utf-8-sig"))["version"]
        if expected_version is not None and version != expected_version:
            raise ValueError(f"Expected release {expected_version}; plugin.json declares {version}")
        if notes is None:
            changelog = (tree / "CHANGELOG.md").read_text(encoding="utf-8-sig")
            heading = re.search(rf"^##[ \t]+v?{re.escape(version)}[ \t]*$", changelog, re.M)
            if not heading:
                raise ValueError(f"CHANGELOG.md has no release notes for {version}")
            tail = changelog[heading.end():]
            release_notes = re.split(r"^##[ \t]+", tail, maxsplit=1, flags=re.M)[0].strip()
        else:
            release_notes = notes.read_text(encoding="utf-8-sig")
        if not release_notes.strip():
            raise ValueError("Release notes must not be empty")
        staged = temporary / "assets"
        staged.mkdir()
        filename = agent_plugins_zip_name(version)
        package = build_release(
            tree, staged / filename, "agent-plugins", beyond_native_archive=beyond_native_archive,
        )
        assets = {filename: package["sha256"]}
        (staged / "release-notes.md").write_text(release_notes, encoding="utf-8")
        report = {"schema": 1, "version": version, "tag": "v" + version,
                  "source_commit": commit, "package": package, "assets": assets,
                  "notes_sha256": sha256_file(staged / "release-notes.md"),
                  "published": False, "client_loading": "not_checked", "game_host": "not_checked"}
        if with_npm:
            npm = package_npm(tree, staged, version)
            report["npm"] = npm
            assets[npm["filename"]] = npm["sha256"]
            for name, digest in assets.items():
                (staged / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="ascii", newline="\n")
        (staged / "release-review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if git("rev-parse", "HEAD") != commit or git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("Repository changed while preparing assets")
        if os.path.lexists(output):
            raise FileExistsError(f"Output already exists: {output}")
        staged.rename(output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--set-version", help="Synchronize versioned files for a release PR")
    parser.add_argument("--notes", type=Path, help="Use a separate notes file instead of CHANGELOG.md")
    parser.add_argument("--expected-version")
    parser.add_argument("--with-npm", action="store_true")
    parser.add_argument("--beyond-native-archive", type=Path)
    args = parser.parse_args()
    try:
        if args.set_version is not None:
            if args.notes or args.expected_version or args.with_npm or args.beyond_native_archive:
                parser.error("Package flags require --output")
            set_release_version(ROOT, args.set_version)
            print(f"Synchronized release files to {args.set_version}")
        else:
            print(json.dumps(prepare(
                ROOT, args.output, args.notes, expected_version=args.expected_version, with_npm=args.with_npm,
                beyond_native_archive=args.beyond_native_archive,
            ), ensure_ascii=False, indent=2))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Release preparation failed: {exc}\n")
