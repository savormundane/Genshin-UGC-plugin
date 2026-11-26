"""Compile final Lua bodies without executing them; bind diagnostics to source maps."""

from pathlib import Path
import re
from typing import Any
from authoring_io import sha, schema, canonical


def check(raw: bytes, kind: str, *, mapping=None, source_map=None, contract=None) -> dict[str, Any]:
    if kind not in ('lua', 'gil'):
        raise ValueError('Client check accepts lua or gil')
    if kind == 'lua':
        if mapping is not None:
            raise ValueError('A script mapping requires GIL input')
        bodies = [{'mapping': None, 'raw': raw}]
    else:
        from level_authoring import inspect_bindings, unique
        from level_inventory import container, fields, vals

        bindings = inspect_bindings(raw)
        if bindings['diagnostics']:
            raise ValueError('Invalid client bindings: ' + str(bindings['diagnostics']))
        _, root = container(raw)
        bodies = []
        for section in vals(root, 50):
            for entry in vals(fields(section), 1):
                fs = fields(entry)
                if any(n == 5 and w != 2 for n, w, v, chunk in fs):
                    raise ValueError('Unsupported Lua body encoding')
                bodies.append(
                    {
                        'mapping': unique(fs, 3).decode('utf-8'),
                        'script_id': unique(fs, 1, 0),
                        'raw': unique(fs, 5, default=b''),
                    }
                )
        if mapping is not None:
            bodies = [b for b in bodies if b['mapping'] == mapping]
            if len(bodies) != 1:
                raise ValueError('Exact unique embedded Lua mapping required')
    for body in bodies:
        body['code'] = body['raw'].decode('utf-8-sig')
    contracts = {}
    if contract is not None:
        schema(contract, ('schema', 'scripts', 'protocol', 'variable_targets'), ('scripts',))
        from miliastra.client.variables import validate_targets

        validate_targets(contract.get('variable_targets', {}))
        if 'protocol' in contract:
            from protocol_types import validate_protocol

            validate_protocol(contract['protocol'])
        if not isinstance(contract['scripts'], list) or not contract['scripts']:
            raise ValueError('API contract requires scripts')
        for item in contract['scripts']:
            schema(item, ('mapping', 'source_sha256', 'bindings'), ('mapping', 'source_sha256'))
            name = item['mapping']
            if name is not None and (not isinstance(name, str) or not name):
                raise ValueError('Invalid API contract mapping')
            if name in contracts:
                raise ValueError('Duplicate API contract mapping')
            if not isinstance(item['source_sha256'], str) or not re.fullmatch(
                '[0-9a-f]{64}', item['source_sha256']
            ):
                raise ValueError('Invalid API source digest')
            contracts[name] = item
        if set(contracts) != {b['mapping'] for b in bodies}:
            raise ValueError('API contract must cover exactly the checked mappings')
        for body in bodies:
            if contracts[body['mapping']]['source_sha256'] != sha(body['code'].encode('utf-8')):
                raise ValueError('API contract differs from checked Lua')
    mapped = None
    if source_map is not None:
        schema(
            source_map,
            (
                'schema',
                'segments',
                'inputs',
                'assembled_source_sha256',
                'generated_prefix_lines',
                'embedded_source_sha256',
                'embedded_mapping',
            ),
            ('segments', 'assembled_source_sha256'),
        )
        if not isinstance(source_map['segments'], list):
            raise ValueError('Source map segments must be a list')
        target = source_map.get('embedded_mapping', mapping)
        if mapping is not None and target != mapping:
            raise ValueError('Source map mapping differs from selected script')
        matches = (
            [b for b in bodies if b['mapping'] == target]
            if kind == 'gil' and target is not None
            else bodies
        )
        if len(matches) != 1:
            raise ValueError('Source map requires one unambiguous script mapping')
        mapped = matches[0]
        expected = (
            source_map.get('embedded_source_sha256', source_map['assembled_source_sha256'])
            if kind == 'gil'
            else source_map['assembled_source_sha256']
        )
        if sha(mapped['code'].encode('utf-8')) != expected:
            raise ValueError('Source map differs from checked Lua')
        lines = len(re.split(r'\r\n|\n\r|\r|\n', mapped['code']))
        previous = 0
        for segment in source_map['segments']:
            schema(segment, ('file', 'start', 'end', 'sha256'), ('file', 'start', 'end', 'sha256'))
            if (
                not isinstance(segment['file'], str)
                or not segment['file']
                or type(segment['start']) is not int
                or type(segment['end']) is not int
            ):
                raise ValueError('Invalid source map segment')
            if (
                segment['start'] <= previous
                or segment['end'] < segment['start'] - 1
                or segment['end'] > lines
            ):
                raise ValueError('Source map segments overlap or exceed checked Lua')
            if not isinstance(segment['sha256'], str) or not re.fullmatch(
                '[0-9a-f]{64}', segment['sha256']
            ):
                raise ValueError('Invalid source segment digest')
            previous = max(segment['start'] - 1, segment['end'])
    report = {
        'schema': 2,
        'status': 'not_applicable' if not bodies else 'passed',
        'layer': 'static',
        'scope': 'all_embedded_mappings'
        if kind == 'gil' and mapping is None
        else 'selected_mapping'
        if kind == 'gil'
        else 'lua_source',
        'input_sha256': sha(raw),
        'scripts': [],
        'checks': {
            'syntax': 'not_applicable' if not bodies else 'passed',
            'source_map': 'passed' if source_map is not None else 'not_applicable',
            'api': 'not_checked',
            'references': 'not_checked',
        },
        'lua_model': 'not_checked',
        'editor': 'not_checked',
        'host': 'not_checked',
    }
    if source_map is not None:
        report['source_map_sha256'] = sha(canonical(source_map).encode('utf-8'))
    if contract is not None:
        report['contract_sha256'] = sha(canonical(contract).encode('utf-8'))
    if bodies:
        from lupa.lua53 import LuaRuntime, LuaSyntaxError

        runtime = LuaRuntime(register_eval=False, register_builtins=False)
        report['compiler'] = {
            'implementation': 'lupa.lua53',
            'lua_version': list(runtime.lua_version),
            'mode': 'text_compile_only',
        }
        for body in bodies:
            item = {k: v for k, v in body.items() if k not in ('raw', 'code')}
            item.update(
                status='passed',
                body_sha256=sha(body['raw']),
                text_sha256=sha(body['code'].encode('utf-8')),
                diagnostics=[],
            )
            try:
                runtime.compile(body['code'], name='@qianxing-client', mode='t')
            except LuaSyntaxError as error:
                message = str(error)
                match = re.search(r'qianxing-client:(\d+):', message)
                line = int(match[1]) if match else None
                origin = None
                if body is mapped and line is not None:
                    from miliastra.client.assembly import locate

                    origin = locate(source_map, line)
                item['status'] = 'failed'
                item['diagnostics'].append(
                    {'error': 'lua_syntax', 'message': message, 'line': line, 'origin': origin}
                )
                report['status'] = 'failed'
                report['checks']['syntax'] = 'failed'
            if contract is not None and item['status'] == 'passed':
                from miliastra.client.api import analyze

                item['api'] = analyze(body['code'], contracts[body['mapping']].get('bindings', []))
                for diagnostic in item['api']['errors'] + item['api']['unresolved']:
                    from miliastra.client.assembly import locate

                    diagnostic['origin'] = (
                        locate(source_map, diagnostic['line']) if body is mapped else None
                    )
                item['status'] = item['api']['status']
            report['scripts'].append(item)
    if contract is not None:
        statuses = [s.get('api', {}).get('status', 'not_checked') for s in report['scripts']]
        report['checks']['api'] = (
            'failed'
            if 'failed' in statuses
            else 'not_checked'
            if 'not_checked' in statuses
            else 'passed'
        )
        if any(s['status'] == 'failed' for s in report['scripts']):
            report['status'] = 'failed'
        elif 'not_checked' in statuses:
            report['status'] = 'not_checked'
        from miliastra.client.variables import check as check_variables

        variables = check_variables(
            raw if kind == 'gil' else None, report['scripts'], contract.get('variable_targets', {})
        )
        report['variable_references'] = variables
        report['checks']['variables'] = variables['status']
        if variables['status'] == 'failed':
            report['status'] = 'failed'
        elif variables['status'] == 'not_checked' and report['status'] != 'failed':
            report['status'] = 'not_checked'
        if 'protocol' in contract:
            from miliastra.client.references import check_protocol

            protocol_report = check_protocol(
                raw if kind == 'gil' else None, report['scripts'], contract['protocol']
            )
            report['protocol_references'] = protocol_report
            report['checks']['protocol'] = protocol_report['status']
            if protocol_report['status'] == 'failed':
                report['status'] = 'failed'
            elif protocol_report['status'] == 'not_checked' and report['status'] != 'failed':
                report['status'] = 'not_checked'
        if kind == 'gil':
            from miliastra.client.references import check_signals

            references = check_signals(raw, report['scripts'])
            report['signal_references'] = references
            report['checks']['signal_names'] = references['status']
            if references['status'] == 'failed':
                report['status'] = 'failed'
            elif references['status'] == 'not_checked' and report['status'] != 'failed':
                report['status'] = 'not_checked'
            from miliastra.client.references import check_templates

            templates = check_templates(raw, report['scripts'])
            report['template_references'] = templates
            report['checks']['control_templates'] = templates['status']
            if templates['status'] == 'failed':
                report['status'] = 'failed'
            elif templates['status'] == 'not_checked' and report['status'] != 'failed':
                report['status'] = 'not_checked'
    if bodies:
        next_steps = []
        if kind == 'gil' and mapping is None and len(bodies) > 1:
            next_steps.append(
                {
                    'code': 'select_lua_mapping',
                    'message': 'Use client check INPUT --mapping NAME to check one of the listed script mappings.',
                }
            )
        if contract is None:
            next_steps.append(
                {
                    'code': 'api_contract_missing',
                    'message': 'The default check compiles Lua syntax. Supply --contract (MCP: contract) to check API calls and declared references.',
                }
            )
        if report['checks']['syntax'] == 'passed':
            next_steps.append(
                {
                    'code': 'check_startup',
                    'message': 'Run simulate check INPUT with the same mapping to execute modeled startup callbacks.',
                }
            )
        report['next_steps'] = next_steps
    return report


def inspect(path, *, mapping=None, source_map=None, contract=None):
    path = Path(path)
    return check(
        path.read_bytes(),
        path.suffix.lower().lstrip('.'),
        mapping=mapping,
        source_map=source_map,
        contract=contract,
    )
