"""Prepare an offline Beyond source revision for review in the plugin repository."""

import argparse
import json
from pathlib import Path, PurePosixPath

from authoring_io import PLUGIN, output_directory, read_json, sha
from beyond_backend import read_bundle_revision, verify_bundle_files
from beyond_native import read_native_lock, verify_native_files


def prepare(source: Path, output: Path, paths: list[str], reason: str) -> dict:
    source = source.resolve()
    output = output.resolve()
    if output.is_relative_to(source):
        raise ValueError('Revision output must be outside the plugin source')
    if not reason.strip() or not paths or len(set(paths)) != len(paths):
        raise ValueError('A reason and unique Beyond source paths are required')
    backend = source / 'vendor/beyond'
    pin_path = Path('scripts/beyond-revision.json')
    pin, manifest = read_bundle_revision(backend, source / pin_path)
    for name in paths:
        relative = PurePosixPath(name)
        if (name not in manifest['files'] or relative.parts[0] == 'node_modules'
                or relative.suffix not in ('.js', '.mjs', '.cjs')):
            raise ValueError('Select an existing Beyond JavaScript source: ' + name)
    native_lock = read_native_lock(backend)
    if native_lock:
        verify_native_files(backend, native_lock)
    changes = verify_bundle_files(backend, manifest, native_lock, allowed_changes=set(paths))
    if set(changes) != set(paths):
        raise ValueError('Every selected Beyond source path must have a byte change')

    ledger = read_json(source / 'PUBLIC_SOURCES.json')
    entries = ledger['distribution_changes']
    files = manifest['files']
    for name, digest in sorted(changes.items()):
        entries.append({'path': 'vendor/beyond/' + name, 'source_sha256': files[name],
                        'sha256': digest, 'reason': reason})
    files.update(changes)
    body = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    current_digest = sha(body)
    entries.append({'path': 'vendor/beyond/bundle.json', 'source_sha256': pin['bundle_sha256'],
                    'sha256': current_digest, 'reason': reason})
    updated = {**pin, 'bundle_sha256': current_digest}
    with output_directory(output) as stage:
        prepared = stage / 'vendor/beyond/bundle.json'
        prepared.parent.mkdir(parents=True)
        prepared.write_bytes(body)
        (stage / pin_path.parent).mkdir()
        (stage / pin_path).write_text(
            json.dumps(updated, indent=2) + '\n', encoding='utf-8', newline='\n')
        (stage / 'PUBLIC_SOURCES.json').write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return {'bundle_sha256': current_digest, 'sources': sorted(changes)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', help='Modified JavaScript paths relative to vendor/beyond')
    parser.add_argument('--source', type=Path, default=PLUGIN)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.out, args.paths, args.reason)))
