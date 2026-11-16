"""Minimal read-only checks for the public repository; no external dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
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
    "references/README.md",
)
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


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
    if any(not isinstance(value, str) or not re.fullmatch(r"\d+\.\d+\.\d+", value) for value in versions.values()):
        errors.append(f"Invalid plugin versions: {versions}")
    elif len(set(versions.values())) != 1:
        errors.append(f"Plugin manifest versions differ: {versions}")

    installer = root / "install.ps1"
    defaults = re.findall(r"\[string\]\$Version\s*=\s*'([^']+)'", installer.read_text(encoding="utf-8-sig")) if installer.is_file() else []
    if defaults != [versions.get("plugin.json")]:
        errors.append("install.ps1 default version must match plugin.json")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    docs = [root / name for name in REQUIRED_FILES if name.endswith(".md")]
    docs.extend((root / "docs").glob("*.md"))
    for path in docs:
        if not path.is_file():
            continue
        for raw in LINK_RE.findall(path.read_text(encoding="utf-8-sig")):
            target = raw.strip().split(" ", 1)[0].strip("<>").split("#", 1)[0].split("?", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if not resolved.is_relative_to(root) or not resolved.exists():
                errors.append(f"{path.relative_to(root)}: invalid link {raw}")

    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        sys.exit(1)
    print("PASS: manifests, required documents and local links")
