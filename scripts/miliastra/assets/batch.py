"""Allocate and apply a shared control budget using measured asset previews."""
import argparse
import json
from pathlib import Path
import re
import sys

from miliastra.assets.pipeline import generate as generate_asset, lua_payload, positive, preview as preview_asset
from authoring_io import DiagnosticError, ProductionInputs, finish, output_directory, read_json, resolve, schema, sha, sha_file, write_json


def asset_key(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', key):
        raise ValueError('Asset keys must be safe directory names using letters, digits, _ or -')
    return key.casefold()


def preview(path, output):
    path = Path(path).resolve()
    raw = path.read_bytes()
    spec = json.loads(raw.decode('utf-8-sig'))
    required = ('schema', 'max_controls', 'assets')
    schema(spec, required, required, version=1)
    budget = spec['max_controls']
    positive(budget, 'total control budget')
    if not isinstance(spec['assets'], list) or not spec['assets']:
        raise ValueError('Provide a nonempty list of batch assets')

    keys = set()
    for item in spec['assets']:
        schema(item, ('key', 'source', 'weight', 'display', 'min_grid', 'max_error', 'options'), ('key', 'source'))
        key = asset_key(item['key'])
        if key in keys:
            raise ValueError('Duplicate batch asset key: ' + item['key'])
        keys.add(key)
        weight = item.get('weight', 1)
        if type(weight) not in (int, float) or not 0 < weight <= sys.float_info.max:
            raise ValueError('Asset weight must be positive and finite: ' + item['key'])
        schema(item.get('options', {}), ('target', 'width', 'height', 'step', 'colors', 'alpha_min',
                                         'max_controls', 'columns', 'max_bytes', 'cell', 'fit'))

    inputs = ProductionInputs({str(path): sha(raw)})
    with output_directory(output) as stage:
        assets, choices = [], {}
        for item in sorted(spec['assets'], key=lambda row: row['key']):
            key = item['key']
            source = resolve(path.parent, item['source'])
            measured = preview_asset(source, stage / key, explore=True,
                                     **{field: item[field] for field in ('display', 'min_grid', 'max_error') if field in item},
                                     **item.get('options', {}))
            inputs.bind(source, measured['source_sha256'], 'asset_batch_preview')
            assets.append({'key': key, 'source': str(source), 'source_sha256': measured['source_sha256'],
                           'weight': item.get('weight', 1), 'preview_report': f'{key}/report.json',
                           'max_error': item.get('max_error'), 'tested': len(measured['candidates']),
                           'diagnostics': measured['diagnostics']})
            viable = [row for row in measured['candidates']
                      if row['within_budget'] is not False and row['within_quality'] is not False
                      and (row['controls'] or not measured['has_foreground'])]
            frontier = []
            for row in sorted(viable, key=lambda row: (row['controls'], row['error'], row['name'])):
                if not frontier or row['error'] < frontier[-1]['error']:
                    frontier.append(row)
            choices[key] = frontier

        missing = [key for key, rows in choices.items() if not rows]
        minimum = None if missing else sum(rows[0]['controls'] for rows in choices.values())
        status = 'passed' if minimum is not None and minimum <= budget else 'failed'
        diagnostics = []
        used = None
        if missing:
            diagnostics.append({'code': 'asset_batch_no_candidate', 'message': 'No usable candidate for some assets',
                                'assets': missing})
        elif status == 'failed':
            diagnostics.append({'code': 'asset_batch_budget_unmet', 'message': 'The lowest-cost tested candidates exceed the total budget',
                                'expected': budget, 'actual': minimum})
        else:
            selected = {key: rows[0] for key, rows in choices.items()}
            used = minimum
            while used < budget:
                upgrades = []
                for asset in assets:
                    key = asset['key']
                    current = selected[key]
                    for candidate in choices[key]:
                        cost = candidate['controls'] - current['controls']
                        if 0 < cost <= budget - used:
                            benefit = asset['weight'] * (current['error'] - candidate['error']) / cost
                            upgrades.append((-benefit, key, cost, candidate['name'], candidate))
                if not upgrades:
                    break
                _, key, cost, _, candidate = min(upgrades, key=lambda row: row[:4])
                selected[key] = candidate
                used += cost
            for asset in assets:
                key = asset['key']
                row = selected[key]
                asset['selected'] = {field: row[field] for field in ('name', 'parameters', 'controls', 'error', 'alpha')}
                asset['selected'].update({field: f"{key}/{row[field]}" for field in ('preview', 'display_preview', 'difference')})
                asset['selected']['preview_sha256'] = sha_file(stage / key / row['preview'])
        report = {'schema': 1, 'kind': 'asset-batch-preview', 'status': status, 'max_controls': budget,
                  'minimum_controls': minimum, 'controls': used, 'assets': assets, 'diagnostics': diagnostics,
                  'error_metric': 'normalized premultiplied RGBA MSE on the display grid', 'host': 'not_checked'}
        write_json(stage / 'report.json', report)
        finish(stage, inputs, kind='asset-batch-preview', status=status)
    return report


def generate(path, output):
    path = Path(path).resolve()
    raw = path.read_bytes()
    report = json.loads(raw.decode('utf-8-sig'))
    if report.get('schema') != 1 or report.get('kind') != 'asset-batch-preview' or report.get('status') != 'passed':
        raise ValueError('A feasible assets batch preview report is required')
    budget = report['max_controls']
    positive(budget, 'total control budget')
    if not isinstance(report['assets'], list) or not report['assets']:
        raise ValueError('Batch preview must include at least one asset')
    inputs = ProductionInputs({str(path): sha(raw)})
    seen = set()
    for asset in report['assets']:
        key = asset_key(asset['key'])
        if key in seen:
            raise ValueError('Duplicate batch asset key: ' + asset['key'])
        seen.add(key)
        inputs.bind(resolve(path.parent, asset['source']), asset['source_sha256'], 'asset_batch_generate')
    inputs.verify()
    controls, output_assets, data = 0, {}, {}
    with output_directory(output) as stage:
        for asset in report['assets']:
            key, row = asset['key'], asset['selected']
            if asset['max_error'] is not None and not 0 <= row['error'] <= asset['max_error']:
                raise ValueError('Selected asset exceeds its error limit: ' + key)
            source = resolve(path.parent, asset['source'])
            actual = generate_asset(source, stage / key, **row['parameters'])
            inputs.bind(source, actual['source_sha256'], 'asset_batch_generate')
            if actual['controls'] != row['controls']:
                raise DiagnosticError('asset_batch_candidate_changed', 'Control count differs from batch preview',
                                      object=key, expected=row['controls'], actual=actual['controls'])
            if sha_file(stage / key / 'preview.png') != row['preview_sha256']:
                raise ValueError('Generated reference image differs from batch preview: ' + key)
            controls += actual['controls']
            if controls > budget:
                raise DiagnosticError('asset_batch_budget_exceeded', 'Generated assets exceed the total control budget',
                                      object=key, expected=budget, actual=controls)
            output_assets[key] = {'asset': f'{key}/asset.json', 'lua': f'{key}/data.lua',
                                  'preview': f'{key}/preview.png', 'controls': actual['controls'],
                                  'error': row['error'], 'source_sha256': actual['source_sha256']}
            data[key] = lua_payload(read_json(stage / key / 'asset.json'))
        catalog = {'schema': 1, 'kind': 'asset-batch', 'status': 'passed', 'max_controls': budget,
                   'controls': controls, 'assets': output_assets, 'data': 'data.json', 'host': 'not_checked'}
        write_json(stage / 'data.json', {'schema': 1, 'kind': 'asset-batch-data', 'assets': data})
        write_json(stage / 'catalog.json', catalog)
        return finish(stage, inputs, kind='asset-batch', status='passed', controls=controls, max_controls=budget,
                      catalog='catalog.json')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='qianxing.py assets batch', description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    for name, command in (('preview', preview), ('generate', generate)):
        entry = commands.add_parser(name)
        entry.set_defaults(command=command)
        entry.add_argument('input')
        entry.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    result = args.command(args.input, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'passed' else 2
