"""Minimal read-only checks for the public repository; no external dependencies."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    "plugin.json",
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
)
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "docs/installation.md",
    "references/README.md",
)
SEMVER = r"\d+\.\d+\.\d+"
REPO = "savormundane/miliastra-wonderland-plugin"
SOURCE_ARCHIVE = f"https://github.com/{REPO}/archive/refs/heads/main.zip"
INSTALL_TAG = rf"https://raw\.githubusercontent\.com/{REPO}/v({SEMVER})/install\.ps1\b"
ZIP_VERSION = rf"\bMiliastra-Wonderland-({SEMVER})-windows-x64\.zip\b"
DOC_VERSIONS = {
    "README.md": {
        "current version": rf"\*\*当前版本 `({SEMVER})`\*\*",
        "download tag": rf"https://github\.com/{REPO}/releases/download/v({SEMVER})/",
        "ZIP filename": ZIP_VERSION,
    },
    "docs/installation.md": {
        "release tag": rf"https://github\.com/{REPO}/releases/tag/v({SEMVER})\b",
        "install command tag": INSTALL_TAG,
        "ZIP filename": ZIP_VERSION,
    },
}
RELEASE_TAG = rf"https://github\.com/{REPO}/releases/tag/v({SEMVER})\b"
SOURCE_DOC_VERSIONS = {
    "README.md": {"current version": DOC_VERSIONS["README.md"]["current version"], "release tag": RELEASE_TAG},
    "docs/installation.md": {"release tag": RELEASE_TAG,
                             "local ZIP filename": rf"\bMiliastra-Wonderland-({SEMVER})-windows-x64\.zip\b"},
}
DESTINATION = r'(<[^\n<>]+>|(?:[^()\s]|\([^()\n]*\))+)'
LINK_RE = re.compile(r'(?<!\\)\]\(\s*' + DESTINATION + r'''(?:\s+(?:"[^"]*"|'[^']*'|\([^)]*\)))?\s*\)''')
REFERENCE_RE = re.compile(r'^ {0,3}\[[^]\n]+\]:\s*' + DESTINATION, re.M)
FENCE_RE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
CODE_RE = re.compile(r'(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)')


def markdown_destinations(text):
    body = []
    fence = None
    for line in re.sub(r'<!--[\s\S]*?(?:-->|$)', '', text).splitlines():
        delimiter = FENCE_RE.match(line)
        if fence is not None:
            if delimiter and delimiter[1][0] == fence[0] and len(delimiter[1]) >= len(fence) and not delimiter[2].strip():
                fence = None
            continue
        if delimiter:
            fence = delimiter[1]
            continue
        if line.startswith(('    ', '\t')):
            continue
        body.append(CODE_RE.sub('', line))
    text = '\n'.join(body)
    for pattern in (LINK_RE, REFERENCE_RE):
        for match in pattern.finditer(text):
            yield match[1]



def check(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    manifests: dict[str, dict] = {}
    for relative in MANIFESTS:
        path = root / relative
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("manifest must be an object")
            manifests[relative] = data
        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: cannot parse manifest: {exc}")

    versions = {path: data.get("version") for path, data in manifests.items()}
    if any(not isinstance(value, str) or not re.fullmatch(SEMVER, value) for value in versions.values()):
        errors.append(f"Invalid plugin versions: {versions}")
    elif len(set(versions.values())) != 1:
        errors.append(f"Plugin manifest versions differ: {versions}")
    version = versions.get("plugin.json")
    identities = {path: data.get("name") for path, data in manifests.items()}
    if any(not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
           for name in identities.values()) or len(set(identities.values())) > 1:
        errors.append(f"Invalid Miliastra Wonderland plugin identity: {identities}")

    if isinstance(version, str) and re.fullmatch(SEMVER, version):
        readme = root / "README.md"
        source_release = readme.is_file() and not re.search(
            DOC_VERSIONS["README.md"]["download tag"], readme.read_text(encoding="utf-8-sig"))
        for relative, patterns in (SOURCE_DOC_VERSIONS if source_release else DOC_VERSIONS).items():
            path = root / relative
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8-sig")
            if source_release and (re.search(DOC_VERSIONS["README.md"]["download tag"], text) or re.search(INSTALL_TAG, text)):
                errors.append(f"{relative}: source release must use local ZIP packaging")
            for label, pattern in patterns.items():
                found = set(re.findall(pattern, text))
                if source_release and label == "release tag" and not found and SOURCE_ARCHIVE in text:
                    continue
                if found != {version}:
                    details = ", ".join(sorted(found)) if found else "missing"
                    errors.append(f"{relative}: {label} must match plugin.json ({version}); found {details}")

    installer = root / "install.ps1"
    defaults = re.findall(r"\[string\]\$Version\s*=\s*'([^']+)'", installer.read_text(encoding="utf-8-sig")) if installer.is_file() else []
    if defaults != [version]:
        errors.append("install.ps1 default version must match plugin.json")

    changelog = root / "CHANGELOG.md"
    if changelog.is_file():
        released = re.search(r"^##[ \t]+v?(\d+\.\d+\.\d+)(?=\s|$)", changelog.read_text(encoding="utf-8-sig"), re.M)
        if released is None or released[1] != version:
            errors.append("CHANGELOG.md first released version must match plugin.json")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    if (root / ".agents/plugins/marketplace.json").exists() or (root / "package.json").exists():
        from marketplace_release import check_marketplace

        try:
            errors.extend(check_marketplace(root))
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            errors.append(f"Marketplace configuration: {exc}")

    backend = root / "vendor/beyond"
    if (backend / "native-canvas.json").exists():
        from beyond_native import read_native_lock, verify_native_files

        try:
            verify_native_files(backend, read_native_lock(backend))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"Beyond native Canvas distribution: {exc}")

    docs = list(root.glob("*.md"))
    for directory in ("docs", "skills", "references", "scripts", ".github"):
        docs.extend((root / directory).rglob("*.md"))
    provenance = root / "PUBLIC_SOURCES.json"
    raw_paths = set()
    if provenance.is_file():
        try:
            registry = json.loads(provenance.read_text(encoding="utf-8-sig"))
            rows = registry["permission_unverified_files"]
            groups = registry["groups"]
            if not isinstance(rows, list) or not isinstance(groups, dict):
                raise ValueError("invalid source groups or permission records")
            for row in rows:
                relative = row["path"]
                if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative
                        or relative.startswith("/") or ".." in PurePosixPath(relative).parts
                        or PurePosixPath(relative).as_posix() != relative or relative in raw_paths):
                    raise ValueError(f"invalid or duplicate recorded path {relative!r}")
                raw_paths.add(relative)
                digest = row["sha256"]
                if (row.get("status") != "redistribution_permission_unverified" or row.get("group") not in groups
                        or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                    errors.append(f"{relative}: incomplete source or permission record")
                    continue
                target = root / relative
                if (not target.resolve().is_relative_to(root) or not target.is_file()
                        or hashlib.sha256(target.read_bytes()).hexdigest() != digest):
                    errors.append(f"{relative}: file missing or differs from recorded source digest")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors.append(f"PUBLIC_SOURCES.json: {exc}")
    for path in sorted(set(docs)):
        relative = path.relative_to(root).as_posix()
        if (relative in raw_paths or relative.startswith(("references/official/", "references/platform/"))
                or "vendor" in path.relative_to(root).parts or not path.is_file()):
            continue
        for raw in markdown_destinations(path.read_text(encoding="utf-8-sig")):
            target = unquote(raw.strip().strip("<>").split("#", 1)[0].split("?", 1)[0])
            if re.match(r"^(?:file:|[a-z]:[\\/])", target, re.I):
                errors.append(f"{path.relative_to(root)}: machine-local link {raw}")
                continue
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root) or not resolved.exists():
                errors.append(f"{path.relative_to(root)}: invalid link {raw}")

    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        sys.exit(1)
    print("PASS: manifests, installer, changelog, documentation versions and local links")
