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


def check() -> list[str]:
    errors: list[str] = []
    manifests: dict[str, dict] = {}
    for relative in MANIFESTS:
        path = ROOT / relative
        try:
            manifests[relative] = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            errors.append(f"{relative}: cannot parse manifest: {exc}")

    versions = {path: data.get("version") for path, data in manifests.items()}
    if len(set(versions.values())) != 1 or any(not value for value in versions.values()):
        errors.append(f"Plugin manifest versions differ: {versions}")

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    docs = [ROOT / name for name in REQUIRED_FILES if name.endswith(".md")]
    docs.extend((ROOT / "docs").glob("*.md"))
    for path in docs:
        if not path.is_file():
            continue
        for raw in LINK_RE.findall(path.read_text(encoding="utf-8-sig")):
            target = raw.strip().split(" ", 1)[0].strip("<>").split("#", 1)[0].split("?", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                errors.append(f"{path.relative_to(ROOT)}: invalid link {raw}")

    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        sys.exit(1)
    print("PASS: manifests, required documents and local links")
