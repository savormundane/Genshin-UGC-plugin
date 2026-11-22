"""Resolve named native identities without losing their resource type."""
import ast
import json
import re
from pathlib import Path

from authoring_io import DiagnosticError, schema, sha


KINDS = {'entity', 'template', 'currency', 'item', 'shop', 'backpack', 'control', 'control_group',
         'pickup_template', 'skill', 'creature_skill'}


class Bindings:
    def __init__(self, entries=()):
        self.ids = {}
        self.merge(dict(entries))

    def merge(self, entries):
        for name, ident in entries.items():
            kind, _, suffix = name.partition(':')
            if kind not in KINDS or not suffix.strip() or type(ident) is not int or not 0 < ident <= 0x7fffffff:
                raise ValueError(f'Invalid native binding: {name!r}')
            if self.ids.setdefault(name, ident) != ident:
                raise DiagnosticError('native.binding_ambiguous', f'Native binding has conflicting identities: {name}',
                                      object=name, expected=self.ids[name], actual=ident)

    def add(self, kind, name, ident):
        self.merge({f'{kind}:{name}': ident})

    def reference(self, value, kinds, **location):
        if not isinstance(value, dict):
            return value
        schema(value, ('ref',), ('ref',))
        name = value['ref']
        if not isinstance(name, str) or name.partition(':')[0] not in kinds:
            raise DiagnosticError('native.binding_wrong_type', f'Expected a {" or ".join(kinds)} binding, got {name!r}',
                                  object=name, expected=list(kinds), actual=name, **location)
        if name not in self.ids:
            raise DiagnosticError('native.binding_missing',
                                  f'Native binding {name!r} is missing. Declare the key before use or supply its bindings.json.',
                                  object=name, expected=name, actual=None, **location)
        return self.ids[name]

    def payload(self):
        return {'schema': 1, 'bindings': dict(self.ids)}


def _identities(data):
    from native_gameplay_index import build_gameplay

    for row in build_gameplay(data)['objects']:
        kind = 'control_group' if row.get('group') else row['kind']
        if kind in KINDS:
            yield row['key'], kind, row['id']


def bind_selectors(data, selectors):
    """Capture explicit, unique project objects in a portable binding table."""
    if not isinstance(selectors, dict) or not selectors:
        raise ValueError('Provide a nonempty map from typed names to exact project object keys')
    candidates = {}
    for key, kind, ident in _identities(data):
        candidates.setdefault(key, []).append((kind, ident))
    entries = {}
    for name, key in selectors.items():
        if not isinstance(key, str):
            raise ValueError(f'Binding {name!r} requires a project object key')
        matches = candidates.get(key, [])
        if len(matches) != 1 or matches[0][0] != name.partition(':')[0]:
            raise DiagnosticError('native.binding_object_mismatch', f'Binding {name!r} needs one matching project object',
                                  object=name, expected=key, actual=[kind for kind, _ in matches])
        entries[name] = {'object_key': key, 'id': matches[0][1]}
    Bindings({name: entry['id'] for name, entry in entries.items()})
    return {'schema': 2, 'gil_sha256': sha(data), 'bindings': entries}


def bindings_for_gil(data, bindings):
    """Seal the identities emitted by a successful edit or graph build."""
    objects = {}
    for key, kind, ident in _identities(data):
        objects.setdefault((kind, ident), []).append(key)
    entries = {}
    for name, ident in bindings.ids.items():
        keys = objects.get((name.partition(':')[0], ident), [])
        if len(keys) != 1:
            raise DiagnosticError('native.binding_object_mismatch', f'Cannot seal binding {name!r} in the resulting GIL',
                                  object=name, expected=ident, actual=keys)
        entries[name] = {'object_key': keys[0], 'id': ident}
    return {'schema': 2, 'gil_sha256': sha(data), 'bindings': entries}


def read_bindings(path, baseline=None):
    path = Path(path).resolve()
    data = path.read_bytes()
    value = json.loads(data.decode('utf-8-sig'))
    version = value.get('schema') if isinstance(value, dict) else None
    fields = ('schema', 'bindings', 'gil_sha256') if version == 2 else ('schema', 'bindings')
    schema(value, fields, fields, version=2 if version == 2 else 1)
    entries = value['bindings']
    if not isinstance(entries, dict):
        raise ValueError('Native bindings must be a map from typed names to objects')
    if version == 2:
        if not isinstance(value['gil_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', value['gil_sha256']):
            raise ValueError('A native binding table requires a GIL SHA-256')
        for entry in entries.values():
            schema(entry, ('object_key', 'id'), ('object_key', 'id'))
            if not isinstance(entry['object_key'], str) or not entry['object_key']:
                raise ValueError('A native binding requires an exact project object key')
        bindings = Bindings({name: entry['id'] for name, entry in entries.items()})
    else:
        bindings = Bindings(entries)
    if baseline is None:
        return bindings, sha(data)
    if version != 2:
        raise DiagnosticError('native.unbound_binding_table', 'Run graph bind for this GIL before building with external bindings',
                              phase='graph_bindings', source=str(path), expected=2, actual=version)
    observed = sha(baseline)
    if value['gil_sha256'] != observed:
        raise DiagnosticError('native.binding_baseline_mismatch', 'External bindings belong to a different GIL. Run graph bind for the current baseline.',
                              phase='graph_bindings', source=str(path), expected=value['gil_sha256'], actual=observed)
    sealed = bindings_for_gil(baseline, bindings)['bindings']
    for name, entry in entries.items():
        if entry != sealed[name]:
            raise DiagnosticError('native.binding_object_mismatch', f'Binding {name!r} does not identify the recorded object',
                                  phase='graph_bindings', source=str(path), object=name, expected=entry, actual=sealed[name])
    return bindings, sha(data)


def bind_operation(op, bindings):
    kind = op['op']

    def resolve(value, field, *kinds):
        return bindings.reference(value, kinds, phase=kind, field=field)

    flat = {
        'add_box_trigger': {'entity_id': ('entity',)},
        'add_native_movers': {'entity_id': ('entity',)},
        'set_linear_motion': {'entity_id': ('entity',)},
        'set_entity_transform': {'entity_id': ('entity',)},
        'set_native_preset_state': {'entity_id': ('entity',)},
        'create_native_drop': {'source_template_id': ('template',), 'item_id': ('item',)},
    }.get(kind, {})
    if kind in ('mount','native_combat','add_native_global_timer'):
        flat = {'entity_id': ('template',) if op.get('section') == 4 else ('entity',)}
    if kind == 'native_economy_binding':
        family = op.get('kind')
        flat = {'entity_id': ('template',) if op.get('section') == 4 else ('entity',)}
        if family in ('backpack', 'shop'):
            flat['resource_id'] = (family,)
        if family == 'loot':
            flat['drop_template_id'] = ('pickup_template',)
        if isinstance(op.get('holdings'), list):
            holdings = ('item',) if family == 'loot' else ('currency', 'item')
            op = {**op, 'holdings': [{**row, 'resource_id': resolve(row['resource_id'], 'holdings.resource_id', *holdings)}
                                     for row in op['holdings']]}
    if kind == 'place_static_scene' and isinstance(op.get('prototypes'), dict):
        return {**op, 'prototypes': {model: resolve(value, f'prototypes.{model}', 'entity')
                                     for model, value in op['prototypes'].items()}}
    if kind == 'duplicate_entities' and isinstance(op.get('copies'), list):
        return {**op, 'copies': [{**row, 'source_entity_id': resolve(row['source_entity_id'], 'copies.source_entity_id', 'entity')}
                                  for row in op['copies']]}
    if kind == 'instantiate_object_templates' and isinstance(op.get('instances'), list):
        return {**op, 'instances': [{**row, 'template_id': resolve(row['template_id'], 'instances.template_id', 'template')}
                                    if 'template_id' in row else row for row in op['instances']]}
    if flat:
        return {**op, **{field: resolve(op[field], field, *kinds) for field, kinds in flat.items() if field in op}}
    return op


# Known Graph Code ID ports and event fields with calibrated native identities.
GRAPH_PORT_KINDS = {
    '货币配置ID': ('currency',), '道具配置ID': ('item',), '物品配置ID': ('item',), '技能配置ID': ('skill',),
    '造物技能配置ID': ('creature_skill',), 'GUID': ('entity',), '界面控件组索引': ('control', 'control_group'),
}


def expand_graph(code, source, bindings):
    """Expand literal native_id calls on a compiler copy, keeping source line numbers."""
    if 'native_id' not in code:
        return code
    try:
        tree = ast.parse(code, filename=str(source))
    except SyntaxError:
        return code  # The ordinary Graph Code validator owns syntax errors.
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    edits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != 'native_id':
            continue
        location = {'phase': 'graph_bindings', 'source': str(source), 'line': node.lineno, 'severity': 'error'}
        if (node.end_lineno != node.lineno or node.keywords or len(node.args) != 1
                or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str)):
            raise DiagnosticError('native.binding_literal', 'native_id requires one literal typed key on one line', **location)
        parent = parents[node]
        port = parent.arg if isinstance(parent, ast.keyword) else None
        if isinstance(parent, ast.Compare):
            port = next((value.id for value in (parent.left, *parent.comparators)
                         if isinstance(value, ast.Name) and value.id in GRAPH_PORT_KINDS), None)
        expected = GRAPH_PORT_KINDS.get(port, tuple(sorted(KINDS)))
        if port:
            location['port'] = port
        ident = bindings.reference({'ref': node.args[0].value}, expected, **location)
        edits.append((node.lineno - 1, node.col_offset, node.end_col_offset, str(ident).encode('ascii')))
    lines = code.encode('utf-8').split(b'\n')
    for line, start, end, replacement in sorted(edits, reverse=True):
        lines[line] = lines[line][:start] + replacement + lines[line][end:]
    return b'\n'.join(lines).decode('utf-8')
