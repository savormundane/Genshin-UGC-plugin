"""Regenerate the public marketplace entries from the release manifests and Skills."""

import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from check_repository import LINK_RE, REFERENCE_RE, REPO, ROOT, SEMVER, markdown_destinations

PACKAGE = 'marketplace/genshin-ugc'
INDEX = 'marketplace/dsh-index.json'
DSH_ENGINE = '0.2.2-rc.5'
GITHUB = f'https://github.com/{REPO}'
CATALOGS = ('.claude-plugin/marketplace.json', '.github/plugin/marketplace.json',
            '.agents/plugins/marketplace.json')


def read_json(root, relative):
    return json.loads((root / relative).read_text(encoding='utf-8-sig'))


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def marketplace_files(root):
    core = read_json(root, 'plugin.json')
    claude = read_json(root, '.claude-plugin/plugin.json')
    codex = read_json(root, '.codex-plugin/plugin.json')
    version, identity = core['version'], core['name']
    if not re.fullmatch(SEMVER, version):
        raise ValueError('Invalid public plugin version')
    for field in ('composerIcon', 'logo'):
        codex['interface'].pop(field, None)
    codex['mcpServers'] = './mcp.json'
    source = './' + PACKAGE
    entry = {'name': identity, 'source': source, 'description': claude['description']}
    catalog = {'name': 'genshin-ugc', 'owner': core['author'], 'plugins': [entry]}
    codex_catalog = {
        'name': catalog['name'],
        'interface': {'displayName': 'Genshin-UGC'},
        'plugins': [{
            'name': identity,
            'source': {'source': 'local', 'path': source},
            'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
            'category': 'Productivity',
        }],
    }
    files = {CATALOGS[0]: json_text(catalog), CATALOGS[1]: json_text(catalog),
             CATALOGS[2]: json_text(codex_catalog)}
    for relative, manifest in (('plugin.json', core), ('.claude-plugin/plugin.json', claude),
                               ('.codex-plugin/plugin.json', codex)):
        files[f'{PACKAGE}/{relative}'] = json_text(manifest)
    for filename, token in (('mcp.json', 'PLUGIN_ROOT'), ('.mcp.json', 'CLAUDE_PLUGIN_ROOT')):
        descriptor = read_json(root, filename)
        server, = descriptor['mcpServers'].values()
        server['args'] = ['${' + token + '}/launch.cjs']
        server.pop('env', None)
        files[f'{PACKAGE}/{filename}'] = json_text(descriptor)

    files[f'{PACKAGE}/package.json'] = json_text({
        'name': 'genshin-ugc-dsh',
        'version': version,
        'description': claude['description'],
        'license': core['license'],
        'repository': {'type': 'git', 'url': f'git+{GITHUB}.git', 'directory': PACKAGE},
        'engines': {'dsh': DSH_ENGINE},
        'files': ['cordis.patch.yml', 'dsh-paths.mjs', 'launch.cjs', 'plugin.json', 'skills/', 'LICENSE'],
        'dsh': {'bundle': {'patch': './cordis.patch.yml'}},
    })
    files[f'{PACKAGE}/LICENSE'] = (root / 'LICENSE').read_text(encoding='utf-8-sig')
    skills = set((root / 'skills').glob('*/SKILL.md'))
    if len(skills) != 5:
        raise ValueError('Expected five public Skills')
    for skill in sorted(skills):
        body = skill.read_text(encoding='utf-8-sig')
        destinations = set(markdown_destinations(body))

        def retarget(match):
            raw = match[1]
            dest = urlsplit(raw.strip('<>'))
            if raw not in destinations or not dest.path or dest.scheme or dest.netloc:
                return match[0]
            target = (skill.parent / unquote(dest.path)).resolve()
            if target in skills:
                return match[0]
            if not target.is_relative_to(root) or not target.is_file():
                raise ValueError(f'{skill.relative_to(root)}: invalid marketplace reference {raw}')
            path = f'/{REPO}/blob/v{version}/' + quote(target.relative_to(root).as_posix())
            url = urlunsplit(('https', 'github.com', path, dest.query, dest.fragment))
            offset = match.start(1) - match.start()
            return match[0][:offset] + url + match[0][offset + len(raw):]

        body = REFERENCE_RE.sub(retarget, LINK_RE.sub(retarget, body))
        files[f'{PACKAGE}/{skill.relative_to(root).as_posix()}'] = body
    return files


def dsh_index(bundle, commit, timestamp):
    return {
        'format': 1,
        'title': 'Genshin-UGC',
        'plugins': [{
            'name': bundle['name'],
            'title': 'Genshin-UGC',
            'description': bundle['description'],
            'repository': {'url': GITHUB, 'directory': PACKAGE},
            'versions': [{
                'version': bundle['version'],
                'publishTimestamp': timestamp,
                'source': {'type': 'git', 'url': GITHUB, 'commit': commit, 'path': PACKAGE},
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
    for relative in ('launch.cjs', 'dsh-paths.mjs', 'cordis.patch.yml'):
        if not (root / PACKAGE / relative).is_file():
            errors.append(f'{PACKAGE}/{relative}: missing marketplace entry')
    if (root / INDEX).is_file():
        index = read_json(root, INDEX)
        pinned, = index['plugins'][0]['versions']
        bundle = read_json(root, f'{PACKAGE}/package.json')
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
            relative = f'{PACKAGE}/package.json'
            bundle = json.loads(git('show', f'{commit}:{relative}'))
            if bundle != read_json(ROOT, relative):
                raise ValueError('The selected commit must contain the current DSH bundle manifest')
            for filename in bundle['files']:
                git('cat-file', '-e', f'{commit}:{PACKAGE}/{filename.rstrip("/")}')
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
