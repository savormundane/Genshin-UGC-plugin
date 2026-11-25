"""Merge the code resources used by graph validation and compilation."""
from pathlib import Path
import json
import os

from authoring_io import DiagnosticError, ProductionInputs, resolve, sha
from ayaya_bridge import NODE_IMPLEMENTATIONS, RUNTIME, SHARED_RESOURCES, resource_definition


def merge_resources(roots, destination):
    """Build one project resource directory and return the inputs actually read."""
    inputs = ProductionInputs()
    paths, definitions, output = {}, {}, []
    resource_types = {'信号': ('SIGNAL', 'signal_name'), '结构体定义': ('STRUCT', 'struct_name')}
    for root in map(Path, roots):
        if not root.is_dir():
            raise ValueError(f'project_resources must be a directory: {root}')
        if root.is_symlink() or getattr(root, 'is_junction', lambda: False)():
            raise ValueError(f'Linked graph resources are unsupported: {root}')
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(root)
            if set(relative.parts) & {'__pycache__','.git','out','__workbench_out__'} or path.suffix in ('.pyc','.pyo'):
                continue
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                raise ValueError(f'Linked graph resources are unsupported: {path}')
            if not path.is_file():
                continue
            if relative.parts[0] == '节点图' and path.suffix.lower() == '.py':
                raise ValueError('Declare all graph sources in graphs; project_resources contains supporting resources')
            raw = path.read_bytes()
            digest = sha(raw)
            inputs.bind(path, digest, 'graph_resources')
            key = relative.as_posix()
            if os.name == 'nt':key = key.casefold()
            if key in paths:
                source, expected = paths[key]
                if expected != digest:
                    raise DiagnosticError('graph.resource_path_conflict', f'Graph resource differs at {relative.as_posix()}',
                                          phase='graph_resources', source=str(path), other_source=str(source),
                                          field=relative.as_posix(), expected=expected, actual=digest)
                continue
            paths[key] = path, digest
            kind = resource_types.get(relative.parts[1]) if len(relative.parts) >= 3 and relative.parts[0] == '管理配置' else None
            if kind is not None and path.suffix.lower() == '.py' and '校验' not in path.stem:
                resource_type, name_field = kind
                ident, payload = resource_definition(path, id_name=resource_type+'_ID',
                                                     payload_name=resource_type+'_PAYLOAD')
                if ident is not None:
                    name = payload.get(name_field)
                    if isinstance(name,str):
                        name = name.strip()
                    # Storage keeps a copy of its struct in each of these
                    # directories for the graph and persistence importers.
                    roles = {'基础结构体','局内存档结构体'}
                    role = relative.parts[2] if resource_type=='STRUCT' and len(relative.parts)>=4 and relative.parts[2] in roles else None
                    struct_type = None
                    if resource_type == 'STRUCT':
                        struct_type, _ = resource_definition(path, id_name='STRUCT_TYPE',
                                                            payload_name='STRUCT_PAYLOAD')
                    definition = (ident, payload, struct_type)
                    keys = [(resource_type,'id',ident)]
                    if isinstance(name, str) and name:
                        keys.append((resource_type,'name',name))
                    already_emitted = False
                    for identity in keys:
                        if identity in definitions:
                            previous, source, emitted_roles = definitions[identity]
                            if definition != previous:
                                raise DiagnosticError('graph.resource_definition_conflict',
                                                      f'Conflicting {resource_type.lower()} {identity[1]} {identity[2]!r}',
                                                      phase='graph_resources', source=str(path), other_source=str(source),
                                                      field=identity[1], expected=previous, actual=definition)
                            already_emitted = already_emitted or role in emitted_roles
                    if already_emitted:
                        continue
                    for identity in keys:
                        definitions.setdefault(identity, (definition,path,set()))[2].add(role)
            output.append((relative, path))
    for relative, path in output:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = path.read_bytes()
        inputs.bind(path, sha(raw), 'graph_resources')
        target.write_bytes(raw)
    return inputs


def prepare_check_context(job_path, workspace, inputs):
    """Materialize declared project context without compiling any graphs."""
    from node_build import copy_tree

    def configuration(path):
        raw = path.read_bytes()
        inputs.bind(path, sha(raw), 'graph_context')
        return json.loads(raw.decode('utf-8-sig'))

    job = configuration(job_path)
    if not isinstance(job, dict) or type(job.get('schema')) is not int or job['schema'] not in (1, 2):
        raise ValueError('Graph check --job requires a production job with schema 1 or 2')
    graph = None
    graphs = {}
    roots = []
    generated = workspace / 'generated'
    if 'graphs' in job:
        graph_path = resolve(job_path.parent, job['graphs']['spec'])
        graph = configuration(graph_path)
        if graph.get('schema') not in (1,2):
            raise ValueError('Unknown graph build schema')
        for row in graph['graphs']:
            source = resolve(graph_path.parent,row['source'])
            if source in graphs:
                raise ValueError('Graph source must be unique in the build specification')
            graphs[source] = row
        if graph.get('project_resources'):
            roots.append(resolve(graph_path.parent, graph['project_resources']))
    if 'storage' in job:
        from miliastra.storage import generate

        storage = job['storage']
        spec = configuration(resolve(job_path.parent, storage['spec']))
        mode = storage.get('transport','client')
        if mode not in ('client','server'):
            raise ValueError('Storage transport must be client or server')
        (generated/'storage').mkdir(parents=True)
        generate(spec, generated/'storage',server_only=mode=='server')
        roots.append(generated/'storage/resources')
    if job.get('protocol_native'):
        from production_core import protocol
        from protocol_codegen import generate

        generate(protocol(job['protocol']), generated/'protocol')
        roots.append(generated/'protocol/resources')
    layout = workspace / 'assets/资源库'
    project = layout / '项目存档/BuildProject'
    project.mkdir(parents=True)
    receipt = merge_resources(roots,project)
    inputs.merge({path:digest for path,digest in receipt.items() if not Path(path).is_relative_to(generated)},'graph_context')
    copy_tree(RUNTIME / NODE_IMPLEMENTATIONS, workspace / NODE_IMPLEMENTATIONS)
    if (RUNTIME / SHARED_RESOURCES).exists():
        copy_tree(RUNTIME / SHARED_RESOURCES, workspace / SHARED_RESOURCES)
    binding = resolve(graph_path.parent, graph['bindings']) if graph and graph.get('bindings') else None
    baseline = resolve(graph_path.parent, graph['base_gil']) if graph and graph.get('base_gil') else None
    return project, graphs, binding, baseline, bool(job.get('native') or job.get('level') or 'storage' in job)
