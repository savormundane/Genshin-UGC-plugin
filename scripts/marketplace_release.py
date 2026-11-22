"""Generate the marketplace entries for the public plugin root."""

import argparse
import json
import re
import subprocess

from check_repository import REPO, ROOT, SEMVER

INDEX = 'marketplace/dsh-index.json'
DSH_ENGINE = '0.2.2-rc.5'
GITHUB = f'https://github.com/{REPO}'
CLAUDE = '.claude-plugin/marketplace.json'
AGENT = '.github/plugin/marketplace.json'
CODEX = '.agents/plugins/marketplace.json'


def read_json(root, relative):
    return json.loads((root / relative).read_text(encoding='utf-8-sig'))


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def marketplace_files(root):
    core = read_json(root, 'plugin.json')
    version, identity = core['version'], core['name']
    if not re.fullmatch(SEMVER, version):
        raise ValueError('Invalid public plugin version')
    description = read_json(root, '.claude-plugin/plugin.json')['description']
    entry = {'name': identity, 'source': './', 'description': description}
    catalog = {'name': 'genshin-ugc', 'owner': core['author'], 'plugins': [entry]}
    codex = {
        'name': catalog['name'],
        'interface': {'displayName': 'Genshin-UGC'},
        'plugins': [{
            'name': identity,
            'source': {'source': 'local', 'path': './'},
            'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
            'category': 'Productivity',
        }],
    }
    bundle = {
        'name': 'genshin-ugc-dsh',
        'version': version,
        'description': description,
        'license': core['license'],
        'repository': {'type': 'git', 'url': f'git+{GITHUB}.git'},
        'engines': {'dsh': DSH_ENGINE},
        'files': [
            'cordis.patch.yml', 'plugin.json', 'assets/', 'docs/', 'references/',
            'skills/', 'scripts/', 'runtime/', 'samples/', 'vendor/', 'pyproject.toml', 'uv.lock',
            'LICENSE', 'THIRD_PARTY_NOTICES.md', 'PUBLIC_SOURCES.json',
        ],
        'dsh': {'bundle': {'patch': './cordis.patch.yml'}},
    }
    return {CLAUDE: json_text(catalog), AGENT: json_text(catalog),
            CODEX: json_text(codex), 'package.json': json_text(bundle)}


def dsh_index(bundle, commit, timestamp):
    return {
        'format': 1,
        'title': 'Genshin-UGC',
        'plugins': [{
            'name': bundle['name'],
            'title': 'Genshin-UGC',
            'description': bundle['description'],
            'repository': {'url': GITHUB},
            'versions': [{
                'version': bundle['version'],
                'publishTimestamp': timestamp,
                'source': {'type': 'git', 'url': GITHUB, 'commit': commit},
                'engines': bundle['engines'],
            }],
        }],
    }


def check_marketplace(root):
    errors = []
    for relative, expected in marketplace_files(root).items():
        path = root / relative
        if not path.is_file() or path.read_text(encoding='utf-8-sig') != expected:
            errors.append(f'{relative}: regenerate with scripts/marketplace_release.py')
    for relative in ('cordis.patch.yml', 'scripts/dsh-paths.mjs', 'scripts/mcp_launcher.cjs'):
        if not (root / relative).is_file():
            errors.append(f'{relative}: missing plugin entry')
    if (root / 'marketplace/genshin-ugc').exists():
        errors.append('Marketplaces must share the root plugin')
    index = read_json(root, INDEX)
    pinned, = index['plugins'][0]['versions']
    bundle = read_json(root, 'package.json')
    version, current = pinned['version'], bundle['version']
    commit, timestamp = pinned['source']['commit'], pinned['publishTimestamp']
    if (not re.fullmatch(r'[0-9a-f]{40}', commit) or type(timestamp) is not int or timestamp <= 0
            or not re.fullmatch(SEMVER, version)
            or tuple(map(int, version.split('.'))) > tuple(map(int, current.split('.')))
            or index != dsh_index({**bundle, 'version': version}, commit, timestamp)):
        errors.append(f'{INDEX}: invalid DSH index or mismatched bundle identity')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dsh-source', metavar='COMMIT', help='Refresh only the DSH index from a committed bundle')
    args = parser.parse_args()
    try:
        if args.dsh_source:
            def git(*arguments):
                return subprocess.check_output(['git', *arguments], cwd=ROOT, encoding='utf-8').strip()

            commit = git('rev-parse', '--verify', '--end-of-options', args.dsh_source + '^{commit}')
            bundle = json.loads(git('show', f'{commit}:package.json'))
            if bundle != read_json(ROOT, 'package.json'):
                raise ValueError('The selected commit must contain the current DSH bundle manifest')
            for filename in bundle['files']:
                git('cat-file', '-e', f'{commit}:{filename.rstrip("/")}')
            timestamp = int(git('show', '-s', '--format=%ct', commit))
            (ROOT / INDEX).write_text(json_text(dsh_index(bundle, commit, timestamp)), encoding='utf-8')
        else:
            for relative, contents in marketplace_files(ROOT).items():
                target = ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents, encoding='utf-8')
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Marketplace preparation failed: {error}\n')


if __name__ == '__main__':
    main()
