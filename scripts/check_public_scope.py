"""Check public Git inputs and package members without logging matched content."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
POLICY = "public-files.txt"
PRIVATE_NAMES = {"agents.md", "agents.override.md", "claude.md", "claude.local.md",
                 "runtime.json", ".git-credentials", ".netrc", ".npmrc",
                 "credentials.json", "settings.local.json"}
PRIVATE_DIRS = {".codex", ".claude", ".cursor", ".private", ".venv", ".ssh", ".aws",
                "__pycache__", ".pytest_cache", ".ruff_cache"}
SECRETS = {
    "private key": re.compile(rb"(?m)^-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----\r?$"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[a-zA-Z0-9]{36,}|github_pat_[a-zA-Z0-9_]{70,})\b"),
    "npm token": re.compile(rb"\bnpm_[a-zA-Z0-9]{36,}\b"),
    "PyPI token": re.compile(rb"\bpypi-AgEIcHlwaS5vcmc[a-zA-Z0-9_-]{24,}"),
    "service key": re.compile(rb"\bsk-(?:proj-|ant-api[0-9]+-)[a-zA-Z0-9_-]{28,}"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)(?![A-Z0-9]*EXAMPLE)[A-Z0-9]{16}\b"),
}
HOME_PATH = re.compile(
    rb"(?i)(?:\b[a-z]:/+users|(?<![A-Z0-9_])/(?:home|Users))/+"
    rb"([\w.\-\x80-\xff]+)/(?:appdata|documents|desktop|downloads|\.config|\.codex|\.claude)\b"
)
PATH_EXAMPLES = {b"abcde", b"example", b"username", b"user", b"runneradmin", b"runner~1"}


def content_kinds(data: bytes) -> list[str]:
    findings = [kind for kind, pattern in SECRETS.items() if pattern.search(data)]
    normal = data.replace(b"\x00", b"").replace(b"\\", b"/")
    if any(match[1].lower() not in PATH_EXAMPLES for match in HOME_PATH.finditer(normal)):
        findings.append("personal absolute path")
    return findings


def shown_name(name: str) -> str:
    return "<restricted name>" if content_kinds(name.encode("utf-8")) else ascii(name)


def private_name(name: str) -> bool:
    parts = name.casefold().split("/")
    leaf = parts[-1]
    return (leaf in PRIVATE_NAMES or bool(PRIVATE_DIRS.intersection(parts))
            or leaf == ".env" or leaf.startswith(".env.")
            and leaf not in {".env.example", ".env.sample", ".env.template"}
            or leaf in {"id_rsa", "id_ed25519", "id_ecdsa"}
            or leaf.endswith((".pfx", ".p12", ".key")))


def read_policy(body: bytes) -> set[str]:
    names = body.decode("utf-8-sig").splitlines()
    if (names != sorted(set(names)) or POLICY not in names
            or any(str(PurePosixPath(name)) != name or name.startswith("/") or "\\" in name
                   or ":" in name or ".." in name.split("/") or not name
                   or any(ord(ch) < 32 for ch in name) for name in names)):
        raise ValueError("Public allowlist must contain unique sorted relative paths and list itself")
    return set(names)


def check_entries(names, allowed, *, exact=False):
    names = set(names)
    errors = [f"Private path: {shown_name(name)}" for name in sorted(names) if private_name(name)]
    errors.extend(f"Path outside public allowlist: {shown_name(name)}"
                  for name in sorted(names - allowed))
    if exact:
        errors.extend(f"Missing approved path: {shown_name(name)}"
                      for name in sorted(allowed - names))
    return errors


def require_distributable(source: dict) -> None:
    pending = source.get("permission_unverified_files")
    if not isinstance(pending, list):
        raise ValueError("Missing redistribution review in PUBLIC_SOURCES.json")
    if pending:
        raise ValueError(f"Public artifact publication is on hold for {len(pending)} unresolved redistribution entries")


def check_npm_metadata(metadata: dict, approved_contact: str, archive: Path | None) -> None:
    if any(owner.get("email") and owner["email"].casefold() != approved_contact.casefold()
           for owner in metadata.get("maintainers", [])):
        raise ValueError("npm registry lists a maintainer email outside the approved public contact")
    if archive is None:
        return

    publisher = metadata.get("_npmUser", {})
    if (publisher.get("trustedPublisher", {}).get("id") != "github"
            or publisher.get("email") != "npm-oidc-no-reply@github.com"
            or publisher.get("approver") or not metadata.get("dist", {}).get("attestations", {}).get("provenance")):
        raise ValueError("npm version lacks direct GitHub trusted publishing provenance")

    source = archive.resolve().as_posix()
    registry = f"https://registry.npmjs.org/{metadata['name']}/-/{archive.name}"
    sources = {archive.name, f"./{archive.name}", source, f"file:./{archive.name}",
               f"file:{archive.name}", f"file:{source}", archive.resolve().as_uri(), registry}
    if any(metadata.get(field) is not None and metadata[field] not in sources for field in ("_from", "_resolved")):
        raise ValueError("npm registry reports an unexpected package source path")


def check_tree(root: Path) -> list[str]:
    allowed = read_policy((root / POLICY).read_bytes())
    files = {item.relative_to(root).as_posix(): item for item in root.rglob("*")
             if item.is_file() or item.is_symlink()}
    failures = check_entries(files, allowed, exact=True)
    for name in sorted(files.keys() & allowed):
        path = files[name]
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            failures.append(f"Linked public file: {shown_name(name)}")
            continue
        failures.extend(f"{kind}: {shown_name(name)}" for kind in content_kinds(path.read_bytes()))
    return failures


def check_git(revision: str):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args])

    object_id = git("rev-parse", "--verify", revision + "^{tree}").decode().strip()
    allowed = read_policy(git("show", f"{object_id}:{POLICY}"))
    failures, names = [], set()
    for row in git("ls-tree", "-r", "-z", object_id).split(b"\x00"):
        if not row:
            continue
        metadata, raw_path = row.split(b"\t", 1)
        name = raw_path.decode("utf-8")
        names.add(name)
        if not metadata.startswith((b"100644 blob ", b"100755 blob ")):
            failures.append(f"Non-regular public file: {shown_name(name)}")
    failures.extend(check_entries(names, allowed, exact=True))
    if failures:
        return failures

    with subprocess.Popen(["git", "-C", str(ROOT), "archive", "--format=tar", object_id],
                          stdout=subprocess.PIPE) as process:
        with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
            seen = set()
            for entry in archive:
                if not entry.isfile():
                    continue
                seen.add(entry.name)
                failures.extend(f"{kind}: {shown_name(entry.name)}"
                                for kind in content_kinds(archive.extractfile(entry).read()))
        if process.wait() or seen != names:
            failures.append("Git archive does not match the approved public tree")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--redact-paths", action="store_true",
                        help="Report only totals in shared logs")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--tree", type=Path)
    modes.add_argument("--commit")
    modes.add_argument("--index", action="store_true")
    modes.add_argument("--outgoing", nargs=2, metavar=("BASE", "HEAD"))
    modes.add_argument("--require-distribution", action="store_true")
    modes.add_argument("--npm-metadata", type=Path, help="Verify Registry maintainer metadata without displaying it")
    parser.add_argument("--npm-archive", type=Path, help="Also verify version publication with the supplied archive path")
    args = parser.parse_args()
    try:
        if args.require_distribution:
            require_distributable(json.loads((ROOT / "PUBLIC_SOURCES.json").read_bytes()))
            failures = []
        elif args.npm_metadata:
            check_npm_metadata(json.loads(args.npm_metadata.read_bytes()),
                               os.environ.get("NPM_PUBLIC_CONTACT_EMAIL", ""), args.npm_archive)
            failures = []
        elif args.tree is not None:
            failures = check_tree(args.tree.resolve())
        elif args.outgoing:
            base, head = args.outgoing
            hashes = subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-list", f"{base}..{head}"], text=True
            ).splitlines()
            failures = [f"{sha[:12]}: {failure}" for sha in hashes for failure in check_git(sha)]
        else:
            revision = args.commit or subprocess.check_output(
                ["git", "-C", str(ROOT), "write-tree"], text=True
            ).strip()
            failures = check_git(revision)
    except (OSError, ValueError, AttributeError, KeyError, TypeError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        print(type(exc).__name__ if args.redact_paths else exc, file=sys.stderr)
        return 1
    if failures:
        if args.redact_paths:
            print(f"Public scope check blocked {len(failures)} findings. Run the check locally for paths.",
                  file=sys.stderr)
        else:
            print("\n".join(failures), file=sys.stderr)
        return 1
    print("Public scope check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
