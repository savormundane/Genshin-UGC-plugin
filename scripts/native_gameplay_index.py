"""Read calibrated gameplay identities and reference carriers from a GIL."""
from collections import Counter, defaultdict

from authoring_io import DiagnosticError, sha
from level_inventory import container, fields, graph_records, unique, vals
from native_core import get, ref
from native_economy import RESOURCES
from native_gameplay import config_name, config_records
from native_hud import control_name, roots
from native_scene import typed_record


CONFIG_KINDS = {1: 'status', 4: 'class', 5: 'curve', 6: 'skill', 10: 'item', 26: 'environment', 27: 'light',
                28: 'creature_skill', **{entry[0]: name for name, entry in RESOURCES.items()}}


def build_gameplay(data, namespace='level'):
    from project_index import key

    header, root = container(data)
    if header[3] != 2:
        raise ValueError('Gameplay scope requires a GIL file')
    objects, references, issues = [], [], []
    by_kind, by_id = defaultdict(list), defaultdict(set)

    def object_row(kind, ident, name='', scope=(), **details):
        identity = key(namespace, kind, *scope, ident)
        row = {'key': identity, 'kind': kind, 'id': ident, 'name': name, 'scope': list(scope),
               'artifact': namespace, **details}
        objects.append(row)
        by_kind[kind, ident].append(row)
        by_id[ident].add(identity)
        return identity

    def link(source, kind, ident, relation, field, *, match=None):
        if ident in (None, 0, ''):
            return
        target = key(namespace, kind, *(('ordinary',) if kind == 'graph' else ()), ident)
        rows = by_kind[kind, ident]
        actual = [row.get(match[0]) for row in rows] if match and rows else sorted(by_id[ident])
        if not rows:
            resolution = 'wrong_type' if actual else 'missing'
        elif len(rows) != 1:
            resolution = 'ambiguous'
        elif match and rows[0].get(match[0]) != match[1]:
            resolution = 'wrong_type'
        else:
            resolution = 'resolved'
        references.append({'source': source, 'target': target, 'relation': relation, 'resolution': resolution,
                           'location': {'field': field}, 'domain': 'gameplay'})
        if resolution != 'resolved':
            issues.append({'code': 'native.reference_' + resolution, 'error': f'{relation} {resolution}: {target}',
                           'source': source, 'object': source, 'field': field, 'expected': match[1] if match else target,
                           'actual': actual, 'target': target, 'relation': relation, 'domain': 'gameplay'})

    def config_link(source, raw, kinds, relation, field):
        ident = get(raw, 2, 0)
        if get(raw, 1, 0) != 1 or ident is None:
            return
        matches = [kind for kind in kinds if by_kind[kind, ident]]
        if not matches:
            matches = [kind for kind in kinds if RESOURCES[kind][1] < ident < RESOURCES[kind][1] + 0x400000]
        # Some carriers refer to platform defaults. A matching local ID or
        # the calibrated config namespace identifies the typed local reference.
        if matches or ident in local_ids:
            link(source, matches[0] if matches else kinds[0], ident, relation, field)

    configs = []
    local_ids = set()
    for row in config_records(unique(root, 15, default=b'')):
        kind, ident = CONFIG_KINDS.get(get(row, 2, 0)), get(row, 1, 0)
        if ident is None:
            continue
        local_ids.add(ident)
        if kind is not None:
            source = object_row(kind, ident, config_name(row), native_kind=get(row, 2, 0))
            configs.append((source, kind, row))
    for kind, row in graph_records(data):
        if kind == 'ordinary':
            locator = get(row, 1, default=b'')
            object_row('graph', ref(locator), get(row, 2, default=b'').decode('utf-8'), (kind,),
                       category=get(locator, 2, 0))
    section = unique(root, 9, default=b'')
    layouts = {get(row, 501, 0) for row in roots(section, 7)}
    controls = []
    for row in vals(fields(section), 502):
        ident = get(row, 501, 0)
        if ident is not None:
            group = any((get(meta, 501, 0), get(meta, 502, 0)) == (6, 13) for meta in vals(fields(row), 502))
            source = object_row('control', ident, control_name(row), layout=ident in layouts, group=group)
            controls.append((source, row))
    for row in vals(fields(unique(root, 12, default=b'')), 1):
        name = get(row, 1, default=b'').decode('utf-8')
        if name:
            object_row('global_timer', name, name)
    for row in vals(fields(unique(root, 18, default=b'')), 1):
        ident = get(row, 1, 0)
        if ident:
            object_row('camera', ident)
    owners = []
    for section_id, kind in ((4, 'template'), (5, 'entity')):
        for row in vals(fields(unique(root, section_id, default=b'')), 1):
            ident = get(row, 1, 0)
            if ident is None:
                continue
            named = typed_record(row, 6 if section_id == 4 else 5, 1)
            name = get(get(named or b'', 11, default=b''), 1, default=b'').decode('utf-8')
            pickup = section_id == 4 and get(row, 9, 0) == 2 and typed_record(row, 8, 36) is not None
            source = object_row(kind, ident, name, section=section_id, pickup=pickup)
            if pickup:
                source = object_row('pickup_template', ident, name, section=section_id)
            owners.append((source, section_id, row, pickup))

    def payload(row, carrier, kind, field):
        return get(get(typed_record(row, carrier, kind) or b'', field, default=b''), 1, default=b'')

    for source, kind, row in configs:
        if kind == 'shop':
            shop = payload(row, 4, 48, 58)
            for side, item_tag, price_tag in ((5, 1, 4), (6, 2, 5)):
                for index, offer in enumerate(vals(fields(get(shop, side, default=b'')), 1)):
                    field = f'15/48/58/1/{side}/1[{index}]'
                    config_link(source, get(offer, item_tag, default=b''), ('item',), 'shop_item', f'{field}/{item_tag}')
                    price = get(offer, price_tag, default=b'')
                    config_link(source, get(price, 1, default=b''), ('currency',), 'shop_currency', f'{field}/{price_tag}/1')
        elif kind == 'class':
            movement = payload(row, 4, 8, 16)
            layout, camera = get(movement, 2, 0), get(movement, 1, 0)
            if layout in layouts or (layout and (layouts or layout != 1073741825)):
                link(source, 'control', layout, 'class_layout', '15/8/16/1/2', match=('layout', True))
            if camera and by_kind['camera', camera]:
                link(source, 'camera', camera, 'class_camera', '15/8/16/1/1')
        elif kind == 'skill':
            for index, cast in enumerate(vals(fields(payload(row, 4, 21, 30)), 5)):
                link(source, 'graph', get(cast, 1, 0), 'skill_graph', f'15/21/30/1/5[{index}]/1', match=('category', 20002))
        elif kind == 'creature_skill':
            timeline_block = typed_record(row, 4, 35) or b''
            top = get(timeline_block, 45, default=b'')
            if get(top, 2, 0) == 51:
                for tag, wire, event, _ in fields(get(top, 1, default=b'')):
                    if tag in (4, 6) and wire == 2:
                        link(source, 'graph', get(event, 1, 0), 'creature_skill_graph',
                             f'15/35/45/1/{tag}/1', match=('category', 20008))

    for source, section_id, row, pickup in owners:
        carrier = 8 if section_id == 4 else 7
        for kind, tag, family in ((33, 44, 'backpack'), (35, 46, 'shop'), (37, 48, 'loot'), (36, 47, 'pickup')):
            record = typed_record(row, carrier, kind)
            if record is None or get(record, 2, 0) != 1 or (family == 'pickup' and not pickup):
                continue
            component = get(record, tag, default=b'')
            location = f'{section_id}/{carrier}/{kind}/{tag}'
            if family == 'shop':
                for index, binding in enumerate(vals(fields(component), 1)):
                    config_link(source, get(binding, 2, default=b''), ('shop',), 'entity_shop', f'{location}/1[{index}]/2')
                continue
            if family == 'backpack':
                config_link(source, get(component, 1, default=b''), ('backpack',), 'entity_backpack', f'{location}/1')
            if family == 'loot':
                locator = get(component, 3, default=b'')
                if get(locator, 1, 0) == 1:
                    link(source, 'pickup_template', get(locator, 2, 0), 'loot_template', f'{location}/3')
            slot = {'backpack': 3, 'loot': 4, 'pickup': 7}[family]
            for index, row in enumerate(vals(fields(get(component, slot, default=b'')), 1)):
                config_link(source, get(row, 1, default=b''), ('item', 'currency') if family == 'backpack' else ('item',),
                            f'{family}_holding', f'{location}/{slot}/1[{index}]/1')
    for source, row in controls:
        for content in vals(fields(row), 505):
            if get(content, 502, 0) == 27:
                for override in vals(fields(content), 503):
                    timer = get(get(override, 21, default=b''), 503, default=b'').decode('utf-8')
                    link(source, 'global_timer', timer, 'hud_timer', '9/502/505/503/21/503')
    for identity, count in Counter(row['key'] for row in objects).items():
        if count > 1:
            issues.append({'code': 'native.reference_ambiguous', 'error': 'duplicate gameplay identity',
                           'object': identity, 'expected': 1, 'actual': count, 'domain': 'gameplay'})
    return {'schema': 2, 'scope': 'gameplay', 'status': 'failed' if issues else 'passed',
            'artifacts': {namespace: {'format': 'gil', 'sha256': sha(data)}}, 'objects': objects,
            'references': references, 'script_mappings': [], 'issues': issues, 'unresolved': [],
            'checks': {'calibrated_gameplay_references': 'failed' if issues else 'passed'},
            'complete_reference_index': False, 'unindexed': ['platform_defaults', 'uncalibrated_gameplay_variants',
                                                              'untyped_graph_constants', 'runtime_references'],
            'editor': 'not_checked', 'host': 'not_checked'}


def require_gameplay(report, phase):
    issues = [issue for issue in report['issues'] if issue.get('domain') == 'gameplay']
    if issues:
        first = issues[0]
        error = DiagnosticError(first['code'], f'{phase} gameplay references failed: {first["error"]}', phase=phase)
        error.diagnostics = [{'phase': phase, 'message': issue['error'], **issue} for issue in issues]
        raise error
