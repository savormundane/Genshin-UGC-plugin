"""Compose shared production stages and dispatch saved jobs by schema."""

from pathlib import Path
import json
import math
import os
import re
import shutil
import tempfile
from typing import Any
from authoring_io import PLUGIN, read_json as load, require_fields as keys, sha
from knowledge import search_api_text as api  # compatibility import
from level_authoring import replace_lua
from miliastra.assets.core import ASSET_GENERATORS
from protocol_types import validate_protocol as protocol

def positive(v):
    if type(v) not in (int, float) or not math.isfinite(v) or v <= 0:
        raise ValueError('Expected finite positive value')


def input_path(value, base):
    if not isinstance(value, str) or not value:
        raise ValueError('Expected input path')
    p = (base / value).resolve()
    return p


def animation(spec, base):
    keys(spec, ('frames', 'max_controls'), ('frames',))
    if not isinstance(spec['frames'], list) or not spec['frames']:
        raise ValueError('Animation requires frames')
    frames = []
    target = None
    maximum = 0
    sources = {}
    for frame in spec['frames']:
        keys(frame, ('asset', 'duration', 'anchor'), ('asset', 'duration', 'anchor'))
        positive(frame['duration'])
        anchor = frame['anchor']
        if (
            not isinstance(anchor, list)
            or len(anchor) != 2
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in anchor)
        ):
            raise ValueError('Invalid anchor')
        path = input_path(frame['asset'], base)
        asset = load(path)
        if asset.get('schema') != 1 or asset.get('generator') not in ASSET_GENERATORS:
            raise ValueError('Expected native asset.json')
        size = asset.get('grid_size')
        if (
            not isinstance(size, list)
            or len(size) != 2
            or any(type(v) != int or v < 1 for v in size)
        ):
            raise ValueError('Invalid frame grid')
        current = asset.get('target')
        if current not in ('rectangles', 'text') or target not in (None, current):
            raise ValueError('Mixed animation formats')
        target = current
        data = asset['data']
        if target == 'rectangles':
            keys(data, ('palette', 'rects'), ('palette', 'rects'))
            palette = data['palette']
            if not isinstance(palette, list) or any(
                not isinstance(c, list)
                or len(c) != 4
                or any(type(v) != int or not 0 <= v <= 255 for v in c)
                for c in palette
            ):
                raise ValueError('Invalid frame palette')
            items = data['rects']
            if not isinstance(items, list):
                raise ValueError('rects must be a list')
            for item in items:
                if (
                    not isinstance(item, list)
                    or len(item) != 5
                    or any(type(v) != int for v in item)
                ):
                    raise ValueError('Invalid rectangle')
                x, y, w, h, c = item
                if (
                    min(x, y) < 0
                    or min(w, h) < 1
                    or x + w > size[0]
                    or y + h > size[1]
                    or not 1 <= c <= len(palette)
                ):
                    raise ValueError('Rectangle outside frame or palette')
        else:
            keys(data, ('tiles',), ('tiles',))
            items = data['tiles']
            if not isinstance(items, list):
                raise ValueError('tiles must be a list')
            for item in items:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get('text'), str)
                    or any(
                        type(item.get(k)) not in (int, float) or not math.isfinite(item[k])
                        for k in ('x', 'y', 'width', 'height', 'font_size')
                    )
                    or min(item['width'], item['height'], item['font_size']) <= 0
                ):
                    raise ValueError('Invalid text tile')
        if not isinstance(items, list) or (
            type(asset.get('controls')) != int or asset.get('controls') != len(items)
        ):
            raise ValueError('Invalid frame control count')
        maximum = max(maximum, len(items))
        sources[str(path)] = sha(path.read_bytes())
        frames.append(
            {'duration': frame['duration'], 'anchor': anchor, 'grid_size': size, 'data': data}
        )
    positive(sum(f['duration'] for f in frames))
    if 'max_controls' in spec:
        if (
            type(spec['max_controls']) != int
            or spec['max_controls'] < 1
            or maximum > spec['max_controls']
        ):
            raise ValueError('Animation pool exceeds budget')
    return {
        'schema': 1,
        'target': target,
        'pool_size': maximum,
        'frames': frames,
        'source_sha256': sources,
    }


def _produce(spec_path, out, evidence, *, include_runtime=True, fallback_gil=None):
    """Dispatch the saved public job by version."""
    path = Path(spec_path).resolve()
    job_bytes = path.read_bytes()
    job = json.loads(job_bytes.decode('utf-8-sig'))
    job_digest = sha(job_bytes)
    if job.get('schema') == 2:
        from miliastra.production import produce as produce_v2

        evidence['v3_pipeline'] = {'status': 'not_checked', 'reason': 'in_progress'}
        return produce_v2(path, out, evidence, job=job, job_digest=job_digest)
    return build_stages(path, job, job_digest, out, evidence, include_runtime=include_runtime,
                        fallback_gil=fallback_gil)


def build_stages(path, job, job_digest, out, evidence, *, include_runtime=True, fallback_gil=None):
    """Run the shared asset, graph and Lua phases of an already loaded job."""
    from miliastra.assets.pipeline import lua
    from authoring_io import ProductionInputs, require_active_baseline

    base = path.parent
    keys(
        job,
        (
            'schema',
            'client',
            'protocol',
            'protocol_native',
            'assets',
            'animation',
            'graphs',
            'gil',
            'level',
        ),
        ('schema',),
    )
    if type(job['schema']) != int or job['schema'] != 1 or len(job) == 1:
        raise ValueError('No production stages')
    if 'protocol_native' in job and (type(job['protocol_native']) != bool or 'protocol' not in job):
        raise ValueError('protocol_native requires boolean and protocol')
    out = Path(out).resolve()
    if out.exists():
        raise ValueError(
            '输出目录已存在：'
            + str(out)
            + '；可用 produce --next 创建新编号目录，或指定新的 --out；原目录不会被覆盖'
        )
    evidence['specification'] = {'status': 'passed', 'reason': ''}
    inputs = ProductionInputs({str(path): job_digest})
    stages = []

    def read(value):
        p = input_path(str(value) if isinstance(value, Path) else value, base)
        raw = p.read_bytes()
        inputs.bind(p, sha(raw), 'production')
        return raw

    def emit(dest, v):
        dest.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ugc-production-', dir=out.parent) as td:
        stage = Path(td) / 'result'
        stage.mkdir()
        client = None
        layout = None
        graph_report = None
        generated_assets = {}

        def state(name, status, reason='', **details):
            evidence[name] = {'status': status, 'reason': reason, **details}

        if 'client' in job:
            state('client_source', 'not_checked', 'in_progress')
            keys(job['client'], ('source',), ('source',))
            client = read(job['client']['source'])
            if not client:
                raise ValueError('Empty client source')
            client.decode('utf-8-sig')
            (stage / 'client.lua').write_bytes(client)
            stages.append('client_source')
            state('client_source', 'passed')
        if 'level' in job:
            from level_authoring import compile_spec

            state('level_generation', 'not_checked', 'in_progress')
            keys(job['level'], ('spec',), ('spec',))
            level_path = input_path(job['level']['spec'], base)
            data, binding = compile_spec(
                json.loads(read(level_path).decode('utf-8-sig')), level_path.parent
            )
            inputs.merge(binding['source_sha256'], 'level')
            (stage / 'level.gil').write_bytes(data)
            emit(stage / 'client-bindings.json', binding)
            (stage / 'template_indices.lua').write_text(
                'return ' + lua(binding['template_indices']) + '\n', encoding='utf-8'
            )
            stages.append('native_level_generation')
            state('level_generation', 'passed')
            state('client_bindings', 'passed')
        if 'assets' in job:
            state('assets', 'not_checked', 'in_progress')
            from miliastra.assets.pipeline import generate

            if not isinstance(job['assets'], list):
                raise ValueError('assets must be a list')
            for item in job['assets']:
                keys(item, ('name', 'source', 'options'), ('name', 'source'))
                name = item['name']
                if (
                    not isinstance(name, str)
                    or not re.fullmatch(r'[A-Za-z0-9_-]+', name)
                    or name in generated_assets
                ):
                    raise ValueError('Invalid/duplicate asset name')
                src = inputs.track(input_path(item['source'], base), 'assets')
                destination = stage / 'assets' / name
                asset = generate(src, destination, **item.get('options', {}))
                inputs.bind(src, asset['source_sha256'], 'assets')
                generated_assets[name] = destination / 'asset.json'
            stages.append('asset_generation')
            state('assets', 'passed', count=len(generated_assets))
        else:
            state('assets', 'not_applicable')
        if include_runtime:
            runtime = PLUGIN / 'scripts/production_runtime.lua'
            (stage / 'runtime.lua').write_bytes(runtime.read_bytes())
        if 'protocol' in job:
            state('protocol_contract', 'not_checked', 'in_progress')
            v = protocol(job['protocol'])
            emit(stage / 'protocol.json', v)
            (stage / 'protocol.lua').write_text('return ' + lua(v) + '\n', encoding='utf-8')
            stages.append('protocol_validation_and_export')
            from protocol_codegen import generate

            state('protocol_contract', 'passed')
            if job.get('protocol_native'):
                layout = generate(v, stage / 'protocol-native')
                state('protocol_native', 'not_checked', 'No built GIL to inspect yet')
        if 'animation' in job:
            state('animation', 'not_checked', 'in_progress')
            animation_spec = json.loads(json.dumps(job['animation']))
            for frame in animation_spec.get('frames', []):
                name = frame.get('asset', '')
                if isinstance(name, str) and name.startswith('@asset:'):
                    key = name[7:]
                    if key not in generated_assets:
                        raise ValueError('Unknown generated asset: ' + key)
                    frame['asset'] = str(generated_assets[key])
            v = animation(animation_spec, base)
            inputs.merge(
                {
                    k: h
                    for k, h in v.pop('source_sha256').items()
                    if not Path(k).is_relative_to(stage)
                },
                'animation',
            )
            emit(stage / 'animation.json', v)
            (stage / 'animation.lua').write_text('return ' + lua(v) + '\n', encoding='utf-8')
            stages.append('animation_validation_and_export')
            state('animation', 'passed')
        active_gil = stage / 'level.gil' if 'level' in job else fallback_gil
        if 'graphs' in job:
            state('graphs', 'not_checked', 'in_progress')
            from node_build import build

            keys(job['graphs'], ('spec',), ('spec',))
            p = input_path(job['graphs']['spec'], base)
            graph_spec = json.loads(read(p).decode('utf-8-sig'))
            if layout is not None:
                resources = stage / 'protocol-resources'
                from graph_resources import merge_resources

                roots = (
                    [input_path(graph_spec['project_resources'], p.parent)]
                    if graph_spec.get('project_resources')
                    else []
                )
                receipt = merge_resources([*roots, stage / 'protocol-native/resources'], resources)
                inputs.merge(
                    {
                        key: value
                        for key, value in receipt.items()
                        if not Path(key).is_relative_to(stage)
                    },
                    'graph_resources',
                )
                graph_spec['project_resources'] = str(resources)
                graph_spec['include_sections'] = list(
                    dict.fromkeys(graph_spec.get('include_sections', ['graphs']) + ['signals'])
                )
            for item in graph_spec['graphs']:
                item['source'] = str(input_path(item['source'], p.parent))
            if graph_spec.get('base_gil'):
                requested = input_path(graph_spec['base_gil'], p.parent)
                require_active_baseline(
                    read(requested),
                    active_gil.read_bytes() if active_gil else None,
                    'graphs.base_gil',
                    requested,
                    active_gil,
                )
                graph_spec['base_gil'] = str(requested)
            elif active_gil:
                graph_spec['base_gil'] = str(active_gil)
            if graph_spec.get('project_resources'):
                graph_spec['project_resources'] = str(
                    input_path(graph_spec['project_resources'], p.parent)
                )
            if graph_spec.get('bindings'):
                graph_spec['bindings'] = str(input_path(graph_spec['bindings'], p.parent))
            generated = stage / 'graph-job.json'
            emit(generated, graph_spec)
            build(generated, stage / 'graphs')
            stages.append('strict_graph_build')
            graph_report = load(stage / 'graphs/build-report.json')
            state('graphs', 'passed', report='graphs/build-report.json')
            inputs.merge(
                {
                    p: h
                    for p, h in graph_report.get('inputs_sha256', {}).items()
                    if not Path(p).is_relative_to(stage)
                },
                'graphs',
            )
            if (stage / 'graphs/level.gil').exists():
                active_gil = stage / 'graphs/level.gil'
                if 'level' in job:
                    shutil.copyfile(active_gil, stage / 'level.gil')
            if layout is not None and (stage / 'graphs/level.gil').exists():
                from protocol_codegen import check_gil

                state('protocol_native', 'not_checked', 'in_progress')
                evidence['protocol_native'] = check_gil(stage / 'graphs/level.gil', layout)
            state(
                'mounts',
                'passed' if graph_report.get('mount_contract_checked') else 'not_checked',
                '' if graph_report.get('mount_contract_checked') else 'No required_mounts contract',
                count=(graph_report.get('gil') or {}).get('required_mounts_verified', 0),
            )
        if 'gil' in job:
            state('lua_writeback', 'not_checked', 'in_progress')
            g = job['gil']
            keys(g, ('base', 'use_graph_output', 'mapping', 'source'), ('mapping',))
            if not isinstance(g['mapping'], str) or not g['mapping']:
                raise ValueError('Missing Lua mapping')
            if 'use_graph_output' in g and type(g['use_graph_output']) != bool:
                raise ValueError('Invalid graph output selection')
            if g.get('use_graph_output'):
                if 'base' in g or 'graphs' not in job:
                    raise ValueError('Ambiguous or missing graph GIL input')
                raw = (stage / 'graphs/level.gil').read_bytes()
            else:
                if 'base' in g:
                    raw = read(g['base'])
                    require_active_baseline(
                        raw,
                        active_gil.read_bytes() if active_gil else None,
                        'gil.base',
                        input_path(g['base'], base),
                        'graphs/level.gil'
                        if active_gil == stage / 'graphs/level.gil'
                        else active_gil,
                    )
                elif active_gil:
                    raw = active_gil.read_bytes()
                else:
                    raise ValueError('需要gil.base或level生成配置')
            code = read(g['source']) if 'source' in g else client
            if 'level' in job and g['mapping'] in binding.get('template_aliases', {}):
                from level_authoring import with_template_alias

                code = with_template_alias(
                    code, binding['template_aliases'][g['mapping']], binding['template_indices']
                )
            output = replace_lua(raw, g['mapping'], code)
            (stage / 'level.gil').write_bytes(output)
            stages.append('protected_lua_writeback')
            state('lua_writeback', 'passed')
        try:
            from lupa.lua53 import LuaRuntime
        except ImportError:
            state('client_syntax', 'not_checked', 'Lua 5.3 interpreter unavailable')
        else:
            runtime = LuaRuntime(register_eval=False, register_builtins=False)
            check = runtime.eval('function(s) local f,e=load(s);return f~=nil,e end')
            state('client_syntax', 'not_checked', 'in_progress')
            checked = []
            for f in stage.rglob('*.lua'):
                if 'graphs' in f.relative_to(stage).parts:
                    continue
                ok, error = check(f.read_text(encoding='utf-8-sig'))
                if not ok:
                    raise ValueError('Lua syntax: ' + str(f.relative_to(stage)) + ': ' + str(error))
                checked.append(f.relative_to(stage).as_posix())
            state('client_syntax', 'passed', files=checked)
        inputs.verify()
        for name in (
            'client_syntax',
            'protocol_contract',
            'protocol_native',
            'graphs',
            'mounts',
            'editor',
            'host',
        ):
            if name not in evidence:
                state(
                    name,
                    'not_checked'
                    if name in ('client_syntax', 'editor', 'host')
                    else 'not_applicable',
                )
        state('lua_writeback', 'passed' if 'gil' in job else 'not_applicable')
        report = {
            'schema': 2,
            'output_directory': str(out),
            'specification': str(path),
            'stages': stages,
            'source_sha256': inputs,
            'files_sha256': {
                p.relative_to(stage).as_posix(): sha(p.read_bytes())
                for p in stage.rglob('*')
                if p.is_file()
            },
            'evidence': evidence,
            'client_lua_syntax_checked': evidence['client_syntax']['status'] == 'passed',
            'protocol_native_nodes_generated': evidence['protocol_native']['status'] == 'passed',
            'mount_verified': evidence['mounts']['status'] == 'passed',
            'editor_imported': False,
            'host_tested': False,
        }
        emit(stage / 'production-report.json', report)
        os.rename(stage, out)
    return report


def produce_summary(report):
    files = report.get('files', report.get('files_sha256', {}))
    selected = ['level.gil', 'bindings.json', 'scene/scene.gia', 'whitebox/whitebox.gia', 'beyond/preview.png']
    selected.extend(name for name in files if name.startswith('fitted-assets/')
                    and name.endswith(('/mounted.lua', '/catalog.json')))
    inputs = report.get('inputs', report.get('source_sha256', {}))
    spec = report.get('specification')
    return {
        'schema': report['schema'],
        'status': 'passed',
        'output_directory': report['output_directory'],
        'report': 'production-report.json',
        'stages': report['stages'],
        'spec_sha256': inputs.get(spec),
        'input_count': len(inputs),
        'outputs_sha256': {name: files[name] for name in selected if name in files},
        'file_count': len(files),
        'checks': {
            name: {k: row[k] for k in ('status', 'layer', 'report', 'scope') if k in row}
            for name, row in report['evidence'].items()
        },
        'diagnostics': [],
    }


class ProductionError(ValueError):
    def __init__(self, message, evidence, diagnostics=None):
        super().__init__(message)
        self.production_evidence = evidence
        if diagnostics is not None:
            self.diagnostics = diagnostics


def produce(spec_path: str | Path, out: str | Path, next_output: bool = False) -> dict[str, Any]:
    """Produce a job. Public schema 1 jobs are deprecated, with removal planned for V2.0.0."""
    out = Path(out).resolve()
    if next_output:
        requested = out
        index = 2
        while out.exists():
            out = requested.with_name(requested.name + '-' + str(index))
            index += 1
    evidence = {'specification': {'status': 'not_checked', 'reason': 'in_progress'}}
    try:
        return {**_produce(spec_path, out, evidence), 'output_directory': str(out)}
    except (ValueError, OSError, TypeError, KeyError) as exc:
        diagnostics = getattr(exc, 'diagnostics', None)
        if diagnostics and any(
            item.get('code') == 'production.input_changed' for item in diagnostics
        ):
            evidence['source_integrity'] = {
                'status': 'failed',
                'layer': 'static',
                'reason': str(exc),
            }
        for value in evidence.values():
            if value.get('reason') == 'in_progress':
                value.update(status='failed', reason=str(exc))
        raise ProductionError(str(exc), evidence, diagnostics) from exc
