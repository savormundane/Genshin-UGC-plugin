"""Schema-2 executable production with final auditing and source-bound evidence."""

from pathlib import Path
import json
import re
import shutil
from typing import Any
from authoring_io import (
    PLUGIN,
    DiagnosticError,
    ProductionInputs,
    canonical,
    finish,
    inventory,
    output_directory,
    read_json,
    require_active_baseline,
    resolve,
    schema,
    sha,
    sha_file,
    write_json,
)


def produce(
    path: str | Path,
    out: str | Path,
    evidence: dict[str, Any] | None = None,
    *,
    job: dict[str, Any] | None = None,
    job_digest: str | None = None,
) -> dict[str, Any]:
    from production_core import _produce as build_shared_stages
    from miliastra.native.bindings import Bindings, bindings_for_gil, read_bindings

    path = Path(path).resolve()
    base = path.parent
    if job is None:
        job_bytes = path.read_bytes()
        job = json.loads(job_bytes.decode('utf-8-sig'))
        job_digest = sha(job_bytes)
    if 'portable' in job:
        from portable_delivery import produce as produce_portable

        return produce_portable(
            path, out, {} if evidence is None else evidence, job=job, job_digest=job_digest
        )
    schema(
        job,
        (
            'schema',
            'client',
            'client_check',
            'level',
            'storage',
            'native',
            'assets',
            'protocol',
            'protocol_native',
            'animation',
            'graphs',
            'gil',
            'simulation',
            'experiment',
            'platform',
            'project',
            'ui',
            'resources',
            'beyond',
            'scene',
        ),
        ('schema',),
    )
    if len(job) == 1:
        raise ValueError('No production stages')
    evidence = {} if evidence is None else evidence
    inputs = ProductionInputs({str(path): job_digest})
    stages = []
    executions = []
    previous_outputs = {}
    previous_inputs = set()
    inventory_cache = {}

    def track(p):
        return inputs.track(p, 'production')

    def read_input(p, phase):
        data = p.read_bytes()
        inputs.bind(p, sha(data), phase)
        return data

    def state(name):
        nonlocal previous_outputs
        ident = str(len(stages)) + ':' + name
        current = inventory(stage, cache=inventory_cache)
        outputs = {
            file: digest for file, digest in current.items() if previous_outputs.get(file) != digest
        }
        executions.append(
            {
                'id': ident,
                'name': name,
                'depends_on': [executions[-1]['id']] if executions else [],
                'inputs_added': sorted(inputs.keys() - previous_inputs),
                'outputs': outputs,
                'outputs_scope': 'changed',
                'removed_outputs': sorted(previous_outputs.keys() - current.keys()),
                'status': 'passed',
            }
        )
        previous_inputs.update(inputs)
        previous_outputs = current
        stages.append(name)
        evidence[name] = {'status': 'passed', 'layer': 'static'}

    # Resolve external inputs and required executors before generating anything.
    from capabilities import doctor

    environment = doctor()
    if (
        any(k in job for k in ('level', 'native', 'graphs', 'gil', 'storage'))
        and not environment['node']
    ):
        raise ValueError('Node is required for native production')
    if 'graphs' in job or 'storage' in job:
        if not environment['python_supported'] or not environment['ayaya']:
            raise ValueError('Bundled backend requires supported Python and Ayaya sources')
    if 'experiment' in job and not environment['lua53']:
        raise ValueError('lupa.lua53 is required for the declared experiment')
    if job.get('assets') and not environment['pillow']:
        raise ValueError('Pillow is required for asset generation')
    platform_report = None
    platform_configuration = None
    client_contract = None
    ui_spec = None
    scene_path = None
    whitebox = None
    final_patch = None
    storage_server = False
    if 'scene' in job:
        scene_job = job['scene']
        schema(scene_job, ('spec', 'whitebox'))
        if not scene_job:
            raise ValueError('Scene stage requires a layout or whitebox export')
        if 'spec' in scene_job:
            scene_path = track(resolve(base, scene_job['spec']))
        if 'whitebox' in scene_job:
            whitebox = scene_job['whitebox']
            schema(whitebox, ('source', 'template_id'), ('source', 'template_id'))
            if whitebox['source'] != '@level':
                track(resolve(base, whitebox['source']))
    resource_check = None
    if 'resources' in job:
        from resource_catalogue import check as check_resources
        from platform_profiles import CATALOGUE

        schema(job['resources'], ('spec',), ('spec',))
        resource_check = check_resources(track(resolve(base, job['resources']['spec'])))
        track(CATALOGUE)
        inputs.merge(resource_check['inputs'], 'resources')
        if resource_check['status'] != 'passed':
            raise ValueError(
                'Resource contract incomplete: '
                + canonical(resource_check['errors'] + resource_check['unresolved'])
            )
    if 'ui' in job:
        schema(job['ui'], ('spec',), ('spec',))
        ui_spec = read_json(track(resolve(base, job['ui']['spec'])))
    if 'client_check' in job:
        from miliastra.client.api import PARSER, PARSER_FILES
        from knowledge import REGISTRY, sources

        schema(job['client_check'], ('spec',), ('spec',))
        client_contract = read_json(track(resolve(base, job['client_check']['spec'])))
        track(REGISTRY)
        track(PLUGIN / sources()['client_api']['path'])
        track(PARSER / 'SOURCE.json')
        track(PLUGIN / 'scripts/client_ast.cjs')
        for name in PARSER_FILES:
            track(PARSER / name)
        if not environment['node']:
            raise ValueError('Node is required for client API checks')
    if resource_check is not None and resource_check['check_client'] and client_contract is None:
        raise ValueError('Resource client cross-check requires client_check contract')
    if 'project' in job:
        schema(job['project'], ('spec',), ('spec',))
        track(resolve(base, job['project']['spec']))
    if 'platform' in job:
        from platform_profiles import check, CATALOGUE

        schema(job['platform'], ('spec',), ('spec',))
        config = track(resolve(base, job['platform']['spec']))
        platform_configuration = read_json(config)
        platform_report = check(platform_configuration)
        track(CATALOGUE)
        for source in platform_report['sources'].values():
            track(PLUGIN / source['path'])
        if platform_report['status'] != 'passed':
            evidence['platform_configuration'] = {
                'status': platform_report['status'],
                'layer': 'static',
                'scope': 'declared_configuration',
                'report': platform_report,
            }
            raise ValueError(
                'Platform configuration acceptance incomplete: '
                + canonical(platform_report['checks'])
            )
    if 'client' in job:
        c = job['client']
        if 'assembly' in c:
            from miliastra.client.assembly import assemble

            cp = track(resolve(base, c['assembly']))
            _, mapping = assemble(read_json(cp), cp.parent)
            inputs.merge(mapping['inputs'], 'client_assembly')
        elif 'source' in c:
            track(resolve(base, c['source']))
    if 'level' in job:
        lp = track(resolve(base, job['level']['spec']))
        level = read_json(lp)
        for item in level['scripts']:
            if 'source' in item:
                track(resolve(lp.parent, item['source']))
    if 'native' in job:
        from miliastra.native.changes import operation_sources

        native = job['native']
        schema(native, ('base', 'spec', 'plan', 'after_graphs'), ('base',))
        if ('spec' in native) == ('plan' in native):
            raise ValueError('Choose native spec or plan')
        track(resolve(base, native['base']))
        np = track(resolve(base, native.get('spec', native.get('plan'))))
        patch = read_json(np)
        if patch.get('schema') != 2:
            raise ValueError('Native patch/plan requires schema 2')
        if 'plan' in native:
            for item in patch['inputs'].values():
                track(resolve(np.parent, item['source']))
        else:
            for op in patch['operations']:
                for field in operation_sources(op):
                    if field == 'source' and op[field] == '@scene':
                        if scene_path is None or op['op'] != 'place_static_scene':
                            raise ValueError('@scene requires a scene stage and place_static_scene')
                    else:
                        track(resolve(np.parent, op[field]))
        if 'after_graphs' in native:
            if 'graphs' not in job and 'storage' not in job:
                raise ValueError('native.after_graphs requires compiled graphs')
            fp = track(resolve(base, native['after_graphs']))
            final_patch = (fp, read_json(fp))
            if final_patch[1].get('base_sha256') != '@level':
                raise ValueError('native.after_graphs must bind its baseline to @level')
            for op in final_patch[1]['operations']:
                for field in operation_sources(op):
                    track(resolve(fp.parent, op[field]))
    if 'storage' in job:
        from miliastra.storage import validate

        storage = job['storage']
        schema(storage, ('spec', 'base', 'transport', 'host_section'), ('spec',))
        mode = storage.get('transport', 'client')
        if mode not in ('client', 'server'):
            raise ValueError('Storage transport must be client or server')
        storage_server = mode == 'server'
        if type(storage.get('host_section', 5)) is not int or storage.get(
            'host_section', 5
        ) not in (4, 5):
            raise ValueError('Storage host section must be template 4 or instance 5')
        if storage_server and storage.get('host_section') != 4:
            raise ValueError(
                'Server storage mounts one copy per player. Use host_section: 4 and a player template ID'
            )
        sp = track(resolve(base, storage['spec']))
        validate(read_json(sp))
        if storage.get('base'):
            track(resolve(base, storage['base']))
    for item in job.get('assets', []):
        track(resolve(base, item['source']))
        if 'spec' in item:
            track(resolve(base, item['spec']))
    if 'protocol' in job:
        from production_core import protocol

        protocol(job['protocol'])
        if client_contract is not None:
            if 'protocol' in client_contract and client_contract['protocol'] != job['protocol']:
                raise ValueError('Client protocol contract differs from production protocol')
            client_contract = {**client_contract, 'protocol': job['protocol']}
    if 'graphs' in job:
        schema(job['graphs'], ('spec', 'include_sources'), ('spec',))
        if type(job['graphs'].get('include_sources', False)) is not bool:
            raise ValueError('include_sources must be boolean')
        gp = track(resolve(base, job['graphs']['spec']))
        graph = read_json(gp)
        if graph.get('schema') not in (1, 2):
            raise ValueError('Unknown graph schema')
        for item in graph['graphs']:
            track(resolve(gp.parent, item['source']))
        if graph.get('base_gil'):
            track(resolve(gp.parent, graph['base_gil']))
        if graph.get('bindings'):
            track(resolve(gp.parent, graph['bindings']))
        if graph.get('project_resources'):
            for p in resolve(gp.parent, graph['project_resources']).rglob('*'):
                if p.is_file():
                    track(p)
    for frame in job.get('animation', {}).get('frames', []):
        if not frame['asset'].startswith('@asset:'):
            track(resolve(base, frame['asset']))
    for name in ('base', 'source'):
        if name in job.get('gil', {}):
            track(resolve(base, job['gil'][name]))
    if 'simulation' in job:
        sp = track(resolve(base, job['simulation']['spec']))
        scene = read_json(sp)
        if scene.get('schema') != 2:
            raise ValueError('Joint production simulation requires schema 2')
        if scene['clients'] and not environment['lua53']:
            raise ValueError('lupa.lua53 is required for declared Lua simulations')
        for item in scene['clients'] + ([scene['server']] if scene.get('server') else []):
            if item['source'] != '@level':
                track(resolve(sp.parent, item['source']))
    if 'experiment' in job:
        ep = track(resolve(base, job['experiment']['spec']))
        experiment = read_json(ep)
        if experiment.get('schema') != 2:
            raise ValueError('Unknown experiment schema')
        track(resolve(ep.parent, experiment['source']))
    if not environment['lua53']:
        from level_authoring import script_records

        lua_inputs = any(
            Path(p).suffix.lower() == '.lua'
            or Path(p).suffix.lower() == '.gil'
            and script_records(Path(p).read_bytes())
            for p in inputs
        )
        if (
            lua_inputs
            or ('storage' in job and not storage_server)
            or any(k in job for k in ('client', 'assets', 'animation', 'protocol'))
        ):
            raise ValueError('lupa.lua53 is required for final Lua compilation')
    for p in (PLUGIN / 'scripts').glob('*'):
        if p.is_file():
            track(p)
    if 'graphs' in job or 'storage' in job:
        for p in (PLUGIN / 'vendor/ayaya').rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'):
                track(p)
    with output_directory(out) as stage:
        if resource_check is not None:
            write_json(stage / 'resource-report.json', resource_check)
            resource_rows = [
                {**row, 'source': {k: v for k, v in row['source'].items() if k != 'path'}}
                for row in resource_check['resources']
            ]
            write_json(
                stage / 'resource-catalogue.json',
                {
                    'schema': 2,
                    'version': resource_check['version'],
                    'resources': resource_rows,
                    'complete_platform_catalogue': False,
                },
            )
            state('resource_contract')
            evidence['resource_contract'].update(
                scope='declared_resource_uses',
                artifact_references_verified=False,
                report='resource-report.json',
            )
        write_json(stage / 'environment.json', environment)
        if scene_path is not None:
            from scene_authoring import build as build_scene

            result = build_scene(scene_path, stage / 'scene')
            inputs.merge(result['inputs'], 'scene')
            state('native_static_scene')
            evidence['native_static_scene'].update(
                report='scene/manifest.json', objects=result['object_count']
            )
        if platform_report is not None:
            write_json(stage / 'platform-configuration.json', platform_configuration)
            write_json(stage / 'platform-report.json', platform_report)
            state('platform_configuration')
            evidence['platform_configuration'].update(
                scope='declared_configuration',
                artifact_verified=False,
                report='platform-report.json',
            )
        legacy = {k: v for k, v in job.items() if k in ('protocol', 'protocol_native', 'animation')}
        legacy['schema'] = 1
        raw = None
        active_stage = None
        storage_spec = None
        binding = None
        storage_host = None
        bindings = Bindings()
        layout_keys = set()
        if 'client' in job:
            c = job['client']
            if set(c) == {'assembly'}:
                from miliastra.client.assembly import assemble

                ap = track(resolve(base, c['assembly']))
                code, mapping = assemble(read_json(ap), ap.parent)
                inputs.merge(mapping['inputs'], 'client_assembly')
                (stage / 'assembled.lua').write_text(code, encoding='utf-8', newline='\n')
                write_json(stage / 'source-map.json', mapping)
                legacy['client'] = {'source': str(stage / 'assembled.lua')}
                state('client_assembly')
            elif set(c) == {'source'}:
                legacy['client'] = {'source': str(track(resolve(base, c['source'])))}
            else:
                raise ValueError('client selects source or assembly')
        if 'storage' in job:
            from miliastra.storage import build, attach

            sp = track(resolve(base, job['storage']['spec']))
            storage_spec = read_json(sp)
            storage_report = build(sp, stage / 'storage', server_only=storage_server)
            inputs.merge(storage_report['inputs'], 'storage')
            state('storage_generation')
        fitted_assets = {}
        if 'assets' in job:
            legacy['assets'] = []
            asset_names = set()
            for item in job['assets']:
                if (
                    not isinstance(item.get('name'), str)
                    or not re.fullmatch(r'[A-Za-z0-9_-]+', item['name'])
                    or item['name'] in asset_names
                ):
                    raise ValueError('Unique safe asset names required')
                asset_names.add(item['name'])
                if item.get('kind') == 'fit':
                    schema(
                        item,
                        ('name', 'kind', 'source', 'spec', 'require_target'),
                        ('name', 'kind', 'source', 'spec'),
                    )
                    require_target = item.get('require_target', False)
                    if type(require_target) is not bool:
                        raise ValueError('require_target must be boolean')
                    from miliastra.assets.fit import build

                    result = build(
                        track(resolve(base, item['source'])),
                        track(resolve(base, item['spec'])),
                        stage / 'fitted-assets' / item['name'],
                    )
                    inputs.merge(result['inputs'], 'asset_fit')
                    quality = result['quality']
                    fitted_assets[item['name']] = {
                        'report': f"fitted-assets/{item['name']}/catalog.json",
                        **quality,
                    }
                    if require_target and not quality['target_reached']:
                        layers = [
                            {key: row[key] for key in ('name', 'error', 'stop_reason')}
                            for row in result['layers']
                            if not row['target_reached']
                        ]
                        evidence['asset_fit_quality'] = {
                            'status': 'failed',
                            'layer': 'software_preview',
                            'assets': fitted_assets,
                        }
                        raise DiagnosticError(
                            'asset.fit_target_unmet',
                            f"Fitted asset {item['name']} exceeds the declared error target",
                            phase='asset_fit',
                            object=item['name'],
                            expected=quality['target_error'],
                            actual=layers,
                        )
                    state('asset_fit')
                elif item.get('kind') == 'gia':
                    from miliastra.native.assets import build

                    source = track(resolve(base, item['source']))
                    sp = track(resolve(base, item['spec']))
                    result = build(source, sp, stage / 'native-assets' / item['name'])
                    inputs.merge(result['inputs'], 'native_assets')
                    state('native_assets')
                elif item.get('kind') == 'batch':
                    from miliastra.assets.batch import generate

                    schema(item, ('name', 'kind', 'source'), ('name', 'kind', 'source'))
                    relative = f"asset-batches/{item['name']}"
                    result = generate(track(resolve(base, item['source'])), stage / relative)
                    inputs.merge(result['inputs'], 'asset_batch')
                    state('asset_batch')
                    evidence.setdefault(
                        'asset_batch_budget',
                        {'status': 'passed', 'layer': 'software_preview', 'batches': {}},
                    )['batches'][item['name']] = {
                        'catalog': relative + '/' + result['catalog'],
                        'controls': result['controls'],
                        'max_controls': result['max_controls'],
                    }
                else:
                    legacy['assets'].append(
                        {**item, 'source': str(track(resolve(base, item['source'])))}
                    )
            if not legacy['assets']:
                legacy.pop('assets')
        if 'animation' in legacy:
            for frame in legacy['animation']['frames']:
                if not frame['asset'].startswith('@asset:'):
                    frame['asset'] = str(track(resolve(base, frame['asset'])))
        resource_job = {
            k: legacy.pop(k)
            for k in ('assets', 'protocol', 'protocol_native', 'animation')
            if k in legacy
        }
        if resource_job:
            resource_job['schema'] = 1
            write_json(stage / 'resource-job.json', resource_job)
            resource_report = build_shared_stages(
                stage / 'resource-job.json', stage / 'resources', {}
            )
            inputs.merge(
                {
                    p: h
                    for p, h in resource_report['source_sha256'].items()
                    if not Path(p).is_relative_to(stage)
                },
                'resources',
            )
            evidence.update(resource_report['evidence'])
            state('resource_generation')
        if 'level' in job:
            from level_authoring import compile_spec

            lp = track(resolve(base, job['level']['spec']))
            raw, binding = compile_spec(read_json(lp), lp.parent)
            inputs.merge(binding['source_sha256'], 'level')
            write_json(stage / 'client-bindings.json', binding)
            state('level_generation')
            active_stage = 'level_generation'
        if 'native' in job:
            if raw is not None:
                raise ValueError('Choose level generation or explicit native baseline')
            from miliastra.native.core import apply

            p = track(resolve(base, job['native']['base']))
            if 'plan' in job['native']:
                from miliastra.native.changes import apply_plan

                sp = track(resolve(base, job['native']['plan']))
                record = read_json(sp)
                raw, r = apply_plan(read_input(p, 'native'), record, sp.parent)
                inputs.merge(r['inputs'], 'native')
                write_json(stage / 'native-diff.json', r['difference'])
                write_json(stage / 'native-plan.json', record)
            else:
                sp = track(resolve(base, job['native']['spec']))
                spec = read_json(sp)
                for op in spec['operations']:
                    for field in operation_sources(op):
                        if field == 'source' and op[field] == '@scene':
                            if scene_path is None or op['op'] != 'place_static_scene':
                                raise ValueError(
                                    '@scene requires a scene stage and place_static_scene'
                                )
                            op[field] = str((stage / 'scene/scene.gia').resolve())
                        else:
                            track(resolve(sp.parent, op[field]))
                raw, r = apply(read_input(p, 'native'), spec, sp.parent)
            bindings.merge(r.get('bindings', {}).get('bindings', {}))
            layout_keys.update(r.get('layout_bindings', {}).get('bindings', {}))
            for operation in r['operations']:
                for relative, digest in operation.get('platform_sources', {}).items():
                    inputs.bind(PLUGIN / relative, digest, 'native')
            write_json(stage / 'native-report.json', r)
            state('native_apply')
            active_stage = 'native_apply'
        if ui_spec is not None:
            from miliastra.native.ui import layout

            if raw is None:
                raise ValueError('UI stage requires generated level or native baseline')
            bound = (
                {**ui_spec, 'base_sha256': sha(raw)}
                if ui_spec.get('base_sha256') == '@level'
                else ui_spec
            )
            raw, ui_report = layout(raw, bound)
            write_json(stage / 'ui-report.json', ui_report)
            state('native_ui')
            active_stage = 'native_ui'
        if storage_spec is not None:
            if job['storage'].get('base'):
                p = resolve(base, job['storage']['base'])
                requested = read_input(p, 'storage')
                require_active_baseline(requested, raw, 'storage.base', p, active_stage)
                if raw is None:
                    raw = requested
            if raw is None and storage_server:
                raise ValueError('Server storage requires a native baseline')
            storage_host = storage_spec.get('host_entity_id')
            if storage_server:
                from miliastra.native.core import get
                from miliastra.native.scene_edits import select_record

                player = select_record(
                    get(raw[20:-4], 4, default=b''),
                    1,
                    storage_host,
                    'Server storage player template',
                )
                if get(player, 2, 0) != 1000000:
                    raise ValueError('Server storage host must be a player template')
            if raw is not None:
                raw = attach(raw, storage_spec)
                active_stage = 'storage'
            if storage_host is None and 'level' in job:
                from miliastra.native.core import get
                from level_inventory import fields, vals

                candidates = []
                for e in vals(fields(get(raw[20:-4], 5, default=b'')), 1):
                    kinds = {get(c, 1, 0) for c in vals(fields(e), 6)}
                    if kinds == {1, 3, 4, 7}:
                        candidates.append(get(e, 1, 0))
                if len(candidates) != 1:
                    raise ValueError('Generated controller calibration is ambiguous')
                storage_host = candidates[0]
            if raw is not None and storage_host is None:
                raise ValueError('Existing storage baseline requires host_entity_id')
        if raw is not None:
            (stage / 'base.gil').write_bytes(raw)
        graph_spec = None
        graph_baseline = raw
        if 'graphs' in job:
            gp = track(resolve(base, job['graphs']['spec']))
            graph_spec = read_json(gp)
            for i, item in enumerate(graph_spec['graphs'], 1):
                source = track(resolve(gp.parent, item['source']))
                item['source'] = str(source)
                if job['graphs'].get('include_sources'):
                    target = stage / 'graph-source' / str(i) / source.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            if graph_spec.get('base_gil'):
                p = resolve(gp.parent, graph_spec['base_gil'])
                graph_baseline = read_input(p, 'graphs')
                require_active_baseline(graph_baseline, raw, 'graphs.base_gil', p, active_stage)
                graph_spec['base_gil'] = str(p)
            elif raw is not None:
                graph_spec['base_gil'] = str(stage / 'base.gil')
            if graph_spec.get('bindings'):
                source = resolve(gp.parent, graph_spec['bindings'])
                external, digest = read_bindings(source, graph_baseline)
                inputs.bind(source, digest, 'graph_bindings')
                bindings.merge(external.ids)
                evidence['graph_binding_identity'] = {
                    'status': 'passed' if graph_baseline is not None else 'not_checked',
                    'layer': 'static',
                    'scope': 'external_gil_binding',
                }
            for mount in graph_spec.get('mounts', []):
                if 'entity_key' in mount:
                    if 'entity_id' in mount or mount.get('section') != 5 or raw is None:
                        raise ValueError(
                            'Graph mount entity_key requires the generated placed-object baseline'
                        )
                    mount['entity_id'] = {'ref': 'entity:' + mount.pop('entity_key')}
                expected = ('template',) if mount.get('section') == 4 else ('entity',)
                if 'entity_id' in mount:
                    mount['entity_id'] = bindings.reference(
                        mount['entity_id'], expected, phase='graph_mount', field='entity_id'
                    )
            if graph_spec.get('project_resources'):
                graph_spec['project_resources'] = str(
                    resolve(gp.parent, graph_spec['project_resources'])
                )
        generated_roots = []
        if storage_spec is not None and raw is not None:
            if graph_spec is None:
                graph_spec = {
                    'schema': 2,
                    'graphs': [],
                    'base_gil': str(stage / 'base.gil'),
                    'formats': ['gia', 'gil'],
                    'allowed_top_level_fields': [10, 6, 11, 35],
                }
            generated_roots.append(stage / 'storage/resources')
            graph_spec['graphs'].append(
                {'source': str(stage / 'storage/storage.py'), 'scope': 'server'}
            )
            # Native structures/helper declarations were already authored into
            # this baseline. Resources supply Graph Code type information;
            # avoid a second importer rewriting those authoritative declarations.
            graph_spec['include_sections'] = list(
                dict.fromkeys(graph_spec.get('include_sections', ['graphs']) + ['signals'])
            )
            graph_spec.setdefault('struct_bindings', []).append(
                {'graph_name': storage_spec['name'], 'struct_id': storage_spec['struct_id']}
            )
            graph_spec.setdefault('graph_ids', {})[storage_spec['name']] = storage_spec['graph_id']
        if graph_spec and job.get('protocol_native'):
            generated_roots.append(stage / 'resources/protocol-native/resources')
            graph_spec['include_sections'] = list(
                dict.fromkeys(graph_spec.get('include_sections', ['graphs']) + ['signals'])
            )
        if graph_spec and generated_roots:
            from graph_resources import merge_resources

            resources = stage / (
                'protocol-graph-resources' if job.get('protocol_native') else 'merged-resources'
            )
            roots = [graph_spec['project_resources']] if graph_spec.get('project_resources') else []
            receipt = merge_resources([*roots, *generated_roots], resources)
            inputs.merge(
                {
                    path: digest
                    for path, digest in receipt.items()
                    if not Path(path).is_relative_to(stage)
                },
                'graph_resources',
            )
            graph_spec['project_resources'] = str(resources)
        if graph_spec:
            if bindings.ids:
                graph_bindings = stage / 'graph-bindings.json'
                write_json(
                    graph_bindings,
                    bindings_for_gil(graph_baseline, bindings)
                    if graph_baseline is not None
                    else bindings.payload(),
                )
                graph_spec['bindings'] = str(graph_bindings)
            else:
                graph_spec.pop('bindings', None)
            write_json(stage / 'graph-job.json', graph_spec)
            legacy['graphs'] = {'spec': str(stage / 'graph-job.json')}
        if 'gil' in job:
            g = {**job['gil']}
            if 'base' in g:
                g['base'] = str(track(resolve(base, g['base'])))

            if 'source' in g:
                g['source'] = str(track(resolve(base, g['source'])))
            if binding and g['mapping'] in binding.get('template_aliases', {}):
                from level_authoring import with_template_alias

                source = Path(g['source'] if 'source' in g else legacy['client']['source'])
                original = source.read_bytes()
                patched = with_template_alias(
                    original, binding['template_aliases'][g['mapping']], binding['template_indices']
                )
                (stage / 'bound-client.lua').write_bytes(patched)
                g['source'] = str(stage / 'bound-client.lua')
                if (stage / 'source-map.json').exists():
                    mapping = read_json(stage / 'source-map.json')
                    offset = patched[: len(patched) - len(original)].count(b'\n')
                    for segment in mapping['segments']:
                        segment['start'] += offset
                        segment['end'] += offset
                    mapping['generated_prefix_lines'] = offset
                    write_json(stage / 'source-map.json', mapping)
            legacy['gil'] = g
        if raw is not None and 'gil' not in legacy:
            (stage / 'level.gil').write_bytes(raw)
        if len(legacy) > 1:
            write_json(stage / 'legacy-job.json', legacy)
            r = build_shared_stages(
                stage / 'legacy-job.json',
                stage / 'build',
                {},
                include_runtime=set(legacy) != {'schema', 'graphs'},
                fallback_gil=stage / 'base.gil' if raw is not None else None,
            )
            inputs.merge(
                {p: h for p, h in r['source_sha256'].items() if not Path(p).is_relative_to(stage)},
                'production',
            )
            for k, v in r['evidence'].items():
                evidence[k] = v
            final = stage / 'build/level.gil'
            if not final.exists():
                final = stage / 'build/graphs/level.gil'
            if final.exists():
                shutil.copyfile(final, stage / 'level.gil')
            state('production')
        if (stage / 'level.gil').exists():
            if 'client' in job and 'gil' not in job:
                raise ValueError('Embedding a client stage requires an explicit gil.mapping')
            if job.get('protocol_native') and job.get('protocol', {}).get('schema') == 2:
                from miliastra.client.signal_binding import bind_replies

                outgoing = [
                    s for s in job['protocol']['signals'] if s['direction'] == 'server_to_client'
                ]
                if outgoing:
                    raw, bound = bind_replies(
                        (stage / 'level.gil').read_bytes(),
                        [s['name'] for s in outgoing],
                        {s['name']: s.get('target', 'signal_source') for s in outgoing},
                    )
                    (stage / 'level.gil').write_bytes(raw)
                    write_json(stage / 'protocol-client-targets.json', bound)
            if job.get('protocol_native'):
                from protocol_codegen import check_gil

                evidence['protocol_native'] = check_gil(
                    stage / 'level.gil', read_json(stage / 'resources/protocol-native/wire.json')
                )
            if storage_spec is not None:
                s = storage_spec
                raw = (stage / 'level.gil').read_bytes()
                if not storage_server:
                    from miliastra.client.signal_binding import bind_replies

                    prefix = s['name'] + ('_v3_' if s['schema'] == 3 else '_')
                    replies = [
                        prefix + kind + '_' + str(i) + '_reply'
                        for i in range(1, s['slots'] + 1)
                        for kind in (
                            ('read', 'open', 'write') if s['schema'] == 3 else ('read', 'write')
                        )
                    ]
                    replies += [
                        s['name'] + '_achievement_' + str(a['id']) + '_reply'
                        for a in s.get('achievements', [])
                    ]
                    raw, bound = bind_replies(raw, replies)
                    write_json(stage / 'client-replies.json', bound)
                from miliastra.native.core import apply, model

                graphs = [g for g in model(raw)['graphs'] if g['name'] == s['name']]
                if len(graphs) != 1:
                    raise ValueError('Generated storage graph missing')
                section = job['storage'].get('host_section', 5)
                patch = {
                    'schema': 2,
                    'base_sha256': sha(raw),
                    'allowed_top_level_fields': [section, 6],
                    'operations': [
                        {
                            'op': 'mount',
                            'section': section,
                            'entity_id': storage_host,
                            'graph_id': graphs[0]['id'],
                        }
                    ],
                }
                raw, mounted = apply(raw, patch, stage)
                (stage / 'level.gil').write_bytes(raw)
                write_json(stage / 'storage-mount.json', mounted)
                evidence['mounts'] = {
                    'status': 'passed',
                    'report': 'storage-mount.json',
                    'verified_generated_graphs': 1,
                    'transport': 'server' if storage_server else 'client',
                }
            if final_patch is not None:
                from miliastra.native.changes import difference
                from miliastra.native.core import apply

                fp, patch = final_patch
                baseline = (stage / 'level.gil').read_bytes()
                bound = {**patch, 'base_sha256': sha(baseline)}
                raw, report = apply(baseline, bound, fp.parent, bindings=bindings)
                bindings.merge(report.get('bindings', {}).get('bindings', {}))
                layout_keys.update(report.get('layout_bindings', {}).get('bindings', {}))
                for operation in report['operations']:
                    for relative, digest in operation.get('platform_sources', {}).items():
                        inputs.bind(PLUGIN / relative, digest, 'native_after_graphs')
                (stage / 'level.gil').write_bytes(raw)
                write_json(stage / 'native-final-report.json', report)
                write_json(
                    stage / 'native-final-diff.json',
                    difference(baseline, raw, bound['allowed_top_level_fields']),
                )
                state('native_after_graphs')
            from miliastra.native.core import audit

            result = audit((stage / 'level.gil').read_bytes())
            write_json(stage / 'native-audit.json', result)
            if result['status'] != 'passed':
                from project_index import write_audit_error

                raise write_audit_error(
                    result, 'result', 'Final native audit failed', code='native.result_audit_failed'
                )
            state('native_audit')
            if ui_spec is not None:
                from miliastra.native.ui import layout

                final_ui = (stage / 'level.gil').read_bytes()
                compared, ui_report = layout(final_ui, {**ui_spec, 'base_sha256': sha(final_ui)})
                if compared != final_ui:
                    raise ValueError('Final native UI differs from declared layout')
                write_json(stage / 'ui-report.json', ui_report)
                evidence['native_ui'].update(
                    report='ui-report.json',
                    scope=ui_report['scope'],
                    parent_geometry_verified=False,
                )
            from level_authoring import inspect_bindings

            write_json(
                stage / 'client-bindings.json', inspect_bindings((stage / 'level.gil').read_bytes())
            )
            if 'gil' in legacy:
                from joint_simulator import script_from_gil

                g = legacy['gil']
                code, _ = script_from_gil((stage / 'level.gil').read_bytes(), g['mapping'])
                expected = (
                    Path(g.get('source', legacy.get('client', {}).get('source', '')))
                    .read_bytes()
                    .decode('utf-8-sig')
                )
                if code != expected:
                    raise ValueError('Final embedded Lua differs from selected client source')
                (stage / 'client.lua').write_text(code, encoding='utf-8', newline='\n')
                if (stage / 'source-map.json').exists():
                    source_map = read_json(stage / 'source-map.json')
                    source_map.update(
                        embedded_source_sha256=sha(code.encode('utf-8')),
                        embedded_mapping=g['mapping'],
                    )
                    write_json(stage / 'source-map.json', source_map)
        if platform_configuration is not None and 'native_bindings' in platform_configuration:
            from platform_native import check as check_platform_native

            if not (stage / 'level.gil').exists():
                raise ValueError('Platform native bindings require final GIL')
            native_platform = check_platform_native(
                (stage / 'level.gil').read_bytes(), platform_configuration
            )
            write_json(stage / 'platform-native-report.json', native_platform)
            if native_platform['status'] != 'passed':
                raise ValueError(
                    'Final platform native binding incomplete: '
                    + canonical(native_platform['checks'])
                )
            state('platform_native')
            evidence['platform_native'].update(
                layer='readback',
                scope=native_platform['scope'],
                report='platform-native-report.json',
                whole_artifact_verified=False,
            )
        if 'project' in job or (stage / 'level.gil').exists():
            from project_index import (
                build as index_native,
                inspect as inspect_project,
                write_audit_error,
            )

            final = (stage / 'level.gil').read_bytes() if (stage / 'level.gil').exists() else None
            if 'project' in job and final is not None:
                project_spec = read_json(resolve(base, job['project']['spec']))
                if sum(a.get('source') == '@level' for a in project_spec.get('artifacts', [])) != 1:
                    raise ValueError('Project checks require exactly one @level final artifact')
            project_report = (
                inspect_project(resolve(base, job['project']['spec']), final)
                if 'project' in job
                else index_native(final)
            )
            inputs.merge(project_report.get('inputs', {}), 'project_references')
            write_json(stage / 'project-report.json', project_report)
            if project_report['status'] != 'passed':
                from miliastra.native.gameplay_index import require_gameplay

                require_gameplay(project_report, 'project_references')
                raise write_audit_error(
                    project_report,
                    'project_references',
                    'Final project reference check failed',
                    code='native.result_reference_failed',
                )
            state('project_references')
            evidence['project_references'].update(
                scope=project_report['scope'],
                complete_reference_index=False,
                report='project-report.json',
            )
        if whitebox is not None:
            from scene_authoring import export_whitebox

            whitebox_source = (
                stage / 'level.gil'
                if whitebox['source'] == '@level'
                else track(resolve(base, whitebox['source']))
            )
            if not whitebox_source.is_file():
                raise ValueError('Whitebox export requires a final GIL at @level or a source file')
            if isinstance(whitebox['template_id'], dict) and whitebox['source'] != '@level':
                raise ValueError('A whitebox template binding requires source @level')
            template_id = bindings.reference(
                whitebox['template_id'], ('template',), phase='whitebox', field='template_id'
            )
            result = export_whitebox(whitebox_source, template_id, stage / 'whitebox')
            if whitebox['source'] != '@level':
                inputs.merge(result['inputs'], 'whitebox')
            state('whitebox_geometry')
            evidence['whitebox_geometry'].update(
                report='whitebox/manifest.json', parts=result['part_count']
            )
        # Inspect the final container after every native mutation and Lua writeback,
        # including mappings that were never materialized as loose .lua files.
        from miliastra.client.check import inspect as inspect_client

        client_reports = []
        api_target = (
            stage / 'level.gil' if (stage / 'level.gil').exists() else stage / 'build/client.lua'
        )
        if client_contract is not None:
            if not api_target.exists():
                raise ValueError('API contract requires final GIL or client Lua')
            write_json(stage / 'client-api-contract.json', client_contract)
        if (stage / 'level.gil').exists():
            source_map = (
                read_json(stage / 'source-map.json')
                if (stage / 'source-map.json').exists()
                else None
            )
            client_reports.append(
                {
                    'artifact': 'level.gil',
                    **inspect_client(
                        stage / 'level.gil', source_map=source_map, contract=client_contract
                    ),
                }
            )
        for source in sorted(stage.rglob('*.lua')):
            if 'graphs' in source.relative_to(stage).parts:
                continue
            client_reports.append(
                {
                    'artifact': source.relative_to(stage).as_posix(),
                    **inspect_client(
                        source, contract=client_contract if source == api_target else None
                    ),
                }
            )
        client_status = (
            'failed'
            if any(r['status'] == 'failed' for r in client_reports)
            else 'not_checked'
            if any(r['status'] == 'not_checked' for r in client_reports)
            else 'passed'
            if any(r['scripts'] for r in client_reports)
            else 'not_applicable'
        )
        api_status = next(
            (r['checks']['api'] for r in client_reports if 'contract_sha256' in r), 'not_checked'
        )
        client_report = {
            'schema': 2,
            'status': client_status,
            'layer': 'static',
            'artifacts': client_reports,
            'api': api_status,
            'references': 'not_checked',
            'editor': 'not_checked',
            'host': 'not_checked',
        }
        write_json(stage / 'client-check.json', client_report)
        state('client_check')
        evidence['client_check'].update(
            status=client_status, report='client-check.json', scope='final_embedded_and_loose_Lua'
        )
        executions[-1]['status'] = client_status
        syntax_status = (
            'failed'
            if any(r['checks']['syntax'] == 'failed' for r in client_reports)
            else 'passed'
            if any(r['scripts'] for r in client_reports)
            else 'not_applicable'
        )
        evidence['client_syntax'] = {
            'status': syntax_status,
            'layer': 'static',
            'report': 'client-check.json',
            'scope': 'final_embedded_and_loose_Lua',
        }
        evidence['client_api'] = {
            'status': api_status,
            'layer': 'static',
            'report': 'client-check.json',
            'scope': 'contract_bound_final_client',
        }
        if client_status in ('failed', 'not_checked'):
            raise ValueError('Final Lua check failed: ' + canonical(client_report))
        if resource_check is not None and resource_check['check_client']:
            from resource_catalogue import check_client as check_client_resources

            target_name = api_target.relative_to(stage).as_posix()
            target_report = next(r for r in client_reports if r['artifact'] == target_name)
            references = check_client_resources(target_report, resource_check)
            write_json(stage / 'client-resource-report.json', references)
            if references['status'] != 'passed':
                raise ValueError('Final client resource check incomplete: ' + canonical(references))
            state('client_resource_references')
            evidence['client_resource_references'].update(
                scope=references['scope'],
                report='client-resource-report.json',
                complete_reference_index=False,
            )
        final_gil_path = stage / 'level.gil'
        final_gil_sha256 = (
            sha_file(final_gil_path)
            if ('simulation' in job or 'beyond' in job) and final_gil_path.is_file()
            else None
        )
        if 'simulation' in job:
            from joint_simulator import run

            sp = track(resolve(base, job['simulation']['spec']))
            scene = read_json(sp)
            server = scene.get('server')
            staged_level = str(final_gil_path)
            for item in scene['clients'] + ([server] if server else []):
                item['source'] = (
                    staged_level
                    if item['source'] == '@level'
                    else str(track(resolve(sp.parent, item['source'])))
                )
            result = run(scene, sp.parent, job['simulation'].get('timeout', 30))
            inputs.merge(
                {p: h for p, h in result['inputs'].items() if not Path(p).is_relative_to(stage)},
                'simulation',
            )
            if result['acceptance']['status'] != 'passed':
                evidence['simulation'] = {'status': 'failed', 'coverage': result['acceptance']}
                raise ValueError(
                    'Required simulation acceptance incomplete: '
                    + str(result['acceptance']['gaps'])
                )
            # The simulator reads the staged file; published references resolve from the delivery.
            artifact_names = {staged_level: final_gil_path.name}
            report_inputs = {
                artifact_names.get(source, source): digest
                for source, digest in result['inputs'].items()
            }
            write_json(stage / 'simulation.json', {**result, 'inputs': report_inputs})
            state('simulation')
            evidence['simulation']['layer'] = (
                'lua_model' if scene['clients'] else 'native_graph_model'
            )
            clients = [
                {
                    'client': item['id'],
                    'source': artifact_names.get(item['source'], item['source']),
                    'sha256': result['inputs'][item['source']],
                    'mapping': item.get('mapping', 'main.lua')
                    if Path(item['source']).suffix.lower() == '.gil'
                    else None,
                }
                for item in scene['clients']
            ]
            servers = (
                [{
                    'source': artifact_names.get(server['source'], server['source']),
                    'sha256': result['inputs'][server['source']],
                }]
                if server
                else []
            )
            for layer, sources in (('lua_model', clients), ('native_graph_model', servers)):
                model_status = result['evidence'][layer]
                bound = bool(
                    final_gil_sha256
                    and sources
                    and all(
                        item['sha256'] == final_gil_sha256
                        and (layer != 'lua_model' or item['mapping'])
                        for item in sources
                    )
                )
                evidence[layer] = {
                    'status': model_status if bound or not sources else 'not_checked',
                    'model_status': model_status,
                    'report': 'simulation.json' if sources else None,
                    'artifact_scope': 'final_gil'
                    if bound
                    else 'external_or_mixed'
                    if sources
                    else 'not_applicable',
                    'artifact_sha256': final_gil_sha256 if bound else None,
                    'bindings': sources,
                }
            final_scene = all(
                evidence[layer]['artifact_scope'] != 'external_or_mixed'
                for layer in ('lua_model', 'native_graph_model')
            )
            evidence['simulation'].update(
                artifact_scope='final_gil' if final_scene else 'external_or_mixed',
                artifact_sha256=final_gil_sha256 if final_scene else None,
                report='simulation.json',
            )
        if 'experiment' in job:
            from experiments import execute

            ep = track(resolve(base, job['experiment']['spec']))
            r = execute(read_json(ep), ep.parent)
            inputs.merge(r['inputs'], 'experiment')
            write_json(stage / 'experiment.json', r)
            if not r['passed']:
                evidence['experiment'] = {'status': 'failed', 'observations': r}
                raise ValueError('Experiment contains failures; see production evidence')
            state('experiment')
            evidence['experiment']['layer'] = 'simulation'
        if 'beyond' in job:
            from beyond_backend import run as run_beyond

            schema(job['beyond'], ('spec', 'backend'), ('spec',))
            external = track(resolve(base, job['beyond']['spec']))
            outcome = run_beyond(
                external,
                resolve(base, job['beyond']['backend']) if 'backend' in job['beyond'] else None,
                stage / 'beyond',
                final_gil=final_gil_path,
            )
            inputs.merge(
                {p: h for p, h in outcome['inputs'].items() if not Path(p).is_relative_to(stage)},
                'beyond',
            )
            preview = read_json(stage / 'beyond/external-simulation.json')
            binding = preview['gil_binding']
            bound = bool(final_gil_sha256 and binding and binding['sha256'] == final_gil_sha256)
            attribution = {
                'artifact_scope': 'final_gil' if bound else 'external_or_mixed',
                'artifact_sha256': final_gil_sha256 if bound else None,
            }
            state('external_simulation')
            evidence['external_simulation'].update(
                layer='external_lua_model',
                report='beyond/external-simulation.json',
                final_gil_status=preview['status'] if bound else 'not_checked',
                **attribution,
            )
            evidence['external_software_preview'] = {
                'status': preview['rendering'],
                'layer': 'software_preview',
                'report': 'beyond/render.json' if preview['preview_generated'] else None,
                'final_gil_status': preview['rendering'] if bound else 'not_checked',
                **attribution,
            }
        for name in ('lua_model', 'native_graph_model', 'compilation_readback', 'software_preview'):
            evidence.setdefault(name, {'status': 'not_applicable'})
        if graph_spec:
            evidence['compilation_readback'] = {
                'status': 'passed',
                'report': 'build/graphs/replacement-report.json'
                if graph_spec.get('schema') == 2
                else 'build/graphs/build-report.json',
            }
        if any(item.get('kind') == 'gia' for item in job.get('assets', [])):
            evidence['software_preview'] = {'status': 'passed', 'path': 'native-assets'}
        if fitted_assets:
            evidence['fitted_software_preview'] = {
                'status': 'passed',
                'layer': 'software_preview',
                'path': 'fitted-assets',
            }
            quality_status = (
                'passed' if all(a['target_reached'] for a in fitted_assets.values()) else 'failed'
            )
            evidence['asset_fit_quality'] = {
                'status': quality_status,
                'layer': 'software_preview',
                'assets': fitted_assets,
            }
        evidence['editor'] = {'status': 'not_checked'}
        evidence['host'] = {'status': 'not_checked'}
        evidence['real_storage_reentry'] = {'status': 'not_checked'}
        evidence['v3_pipeline'] = {'status': 'passed'}
        # Copy only stable reviewable artifacts; internal jobs contain temporary paths.
        if graph_baseline is not None and bindings.ids and (stage / 'level.gil').is_file():
            sealed = bindings_for_gil((stage / 'level.gil').read_bytes(), bindings)
            write_json(stage / 'bindings.json', sealed)
            if layout_keys:
                write_json(
                    stage / 'layout-bindings.json',
                    {
                        **sealed,
                        'bindings': {
                            name: sealed['bindings'][name] for name in sorted(layout_keys)
                        },
                    },
                )
        for file in (
            'legacy-job.json',
            'graph-job.json',
            'graph-bindings.json',
            'resource-job.json',
        ):
            if (stage / file).exists():
                (stage / file).unlink()
        state('source_integrity')
        final_files = inventory(stage)
        graph_file = stage / 'dependency-graph.json'
        write_json(
            graph_file,
            {
                'schema': 3,
                'executions': executions,
                'external_and_tool_inputs': inputs,
                'final_artifacts': final_files.copy(),
            },
        )
        final_files[graph_file.name] = sha_file(graph_file)
        report = finish(
            stage,
            inputs,
            files=final_files,
            kind='production',
            specification=str(path),
            stages=stages,
            evidence=evidence,
        )
        write_json(stage / 'production-report.json', report)
        from delivery_artifacts import roles

        report['files'] = {
            **final_files,
            'production-report.json': sha_file(stage / 'production-report.json'),
        }
        report['artifacts'] = roles(report['files'])
        write_json(stage / 'manifest.json', report)
    return report
