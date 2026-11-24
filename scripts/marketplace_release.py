"""Generate terminal marketplace entries and the DeepSeek Harness Bundle manifest."""

import argparse
import json
import re

from check_repository import REPO, ROOT, SEMVER

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
    display_name = read_json(root, '.codex-plugin/plugin.json')['interface']['displayName']
    claude = read_json(root, '.claude-plugin/plugin.json')
    if claude['displayName'] != display_name:
        raise ValueError('Codex and Claude display names differ')
    description = claude['description']
    english_description = "Look up nodes and Lua APIs, inspect levels, and create node graphs and assets for Genshin Impact's Miliastra Wonderland."
    entry = {'name': identity, 'source': './', 'description': description}
    catalog = {'name': identity, 'owner': core['author'], 'plugins': [entry]}
    codex = {
        'name': catalog['name'],
        'interface': {'displayName': display_name},
        'plugins': [{
            'name': identity,
            'source': {'source': 'local', 'path': './'},
            'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
            'category': 'Productivity',
        }],
    }
    distribution = read_json(root, 'distribution.json')
    vendor_exclusions = ['!' + prefix + '**' for prefix in distribution['exclude_prefixes']
                         if prefix.startswith('vendor/')]
    bundle = {
        'name': identity,
        'version': version,
        'description': english_description,
        'license': core['license'],
        'repository': {'type': 'git', 'url': f'git+{GITHUB}.git'},
        'engines': {'dsh': DSH_ENGINE},
        'files': [
            'cordis.patch.yml', 'plugin.json', 'locale/', 'assets/', 'docs/', 'references/',
            'skills/', 'scripts/', 'runtime/', 'samples/', 'vendor/', 'pyproject.toml', 'uv.lock',
            'LICENSE', 'THIRD_PARTY_NOTICES.md', 'PUBLIC_SOURCES.json',
        ] + vendor_exclusions,
        'dsh': {'bundle': {'patch': './cordis.patch.yml'}},
        'exports': {'./locale/*.json': './locale/*.json', './package.json': './package.json'},
    }
    claude_catalog = {**catalog, 'plugins': [{**entry, 'displayName': display_name}]}
    return {CLAUDE: json_text(claude_catalog), AGENT: json_text(catalog),
            CODEX: json_text(codex), 'package.json': json_text(bundle),
            'locale/en.json': json_text({'meta': {'title': display_name, 'description': english_description}}),
            'locale/zh.json': json_text({'meta': {
                'title': '千星奇域开发插件',
                'description': '查询节点和 Lua API，检查关卡，编写节点图并制作图元素材。',
            }})}


def check_marketplace(root):
    errors = []
    for relative, expected in marketplace_files(root).items():
        path = root / relative
        if not path.is_file() or path.read_text(encoding='utf-8-sig') != expected:
            errors.append(f'{relative}: regenerate with scripts/marketplace_release.py')
    for relative in ('cordis.patch.yml', 'scripts/dsh-paths.mjs', 'scripts/mcp_launcher.cjs'):
        if not (root / relative).is_file():
            errors.append(f'{relative}: missing plugin entry')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        for relative, contents in marketplace_files(ROOT).items():
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding='utf-8')
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Marketplace preparation failed: {error}\n')


if __name__ == '__main__':
    main()
