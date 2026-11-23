"""Scoped GIL edits for 3D objects and their decorations."""
from collections import Counter, defaultdict
import re
import struct

from authoring_io import read_json, resolve, schema
from level_inventory import container, entity_graph_ids, fields, unique, vals
from level_authoring import flt, integer, msg, set_section, stream, text, vi
from native_core import get, replace_message
from native_scene import (
    GIL_HEADER, OBJECT_ID_END, OBJECT_ID_START, TRS, encode_vector, is_object_id, ordinary_object,
    placed_details, read_gia, read_templates, read_transform, read_vector, singular, typed_record, vector,
)

WHITEBOX = {10009001: '长方体', 10009002: '球体', 10009008: '圆柱', 10009009: '圆锥'}
DECORATION_START = 0x40000001
DECORATION_END = 0x400FFFFF


def one(matches, label):
    values = list(matches)
    if len(values) != 1:
        raise ValueError(label + ' must match exactly once')
    return values[0]


def patch_fields(data, updates):
    """Replace specified scalars/messages in place, preserving other wire records."""
    encode = {0: integer, 2: msg, 5: flt}
    pending = dict(updates)
    result = []
    for number, wire, old, raw in fields(data):
        if number not in updates:
            result.append(raw)
            continue
        if number not in pending or updates[number][0] != wire:
            raise ValueError('Ambiguous or incompatible native field ' + str(number))
        _, value = pending.pop(number)
        if value is not None:
            old = struct.unpack('<f', old)[0] if wire == 5 else old
            result.append(raw if old == value else encode[wire](number, value))
    for number, (wire, value) in pending.items():
        if value is not None:
            result.append(encode[wire](number, value))
    return b''.join(result)


def patch_vector(body, values, *, preserve_zero=False):
    stored = {field: raw for field, wire, raw, _ in fields(body) if wire == 5} if preserve_zero else {}
    updates = {axis: (5, value if value or (axis in stored and struct.unpack('<f', stored[axis])[0] == 0) else None)
               for axis, value in enumerate(values, 1)}
    return patch_fields(body, updates)


def patch_vectors(body, changes, *, preserve_zero=False):
    updated = {}
    for number, value in changes.items():
        current = get(body, number, default=b'')
        updated[number] = (2, patch_vector(current, value, preserve_zero=preserve_zero))
    return patch_fields(body, updated)


def transform_edits(body, op):
    changes = {
        number: vector(op[key], key, positive=key == 'scale')
        for number, key in enumerate(TRS, 1) if key in op
    }
    return patch_vectors(body, changes)


def select_record(section, field, ident, label):
    if type(ident) is not int or ident <= 0:
        raise ValueError('Invalid ' + label + ' ID')
    return one((raw for raw in vals(fields(section), field) if get(raw, 1, 0) == ident), label)


def next_object_ids(data, root):
    occupied = (get(raw, 1, 0) for n in (4, 5) for raw in vals(fields(unique(root, n, default=b'')), 1))
    start = max((i for i in occupied if is_object_id(i)), default=OBJECT_ID_START - 1) + 1
    for ident in range(start, OBJECT_ID_END + 1):
        if vi(ident) not in data:
            yield ident


def append_library_entries(library, kind, code, identities, *, create=False):
    entries = b''.join(msg(5, integer(1, code) + integer(2, ident)) for ident in identities)
    tabs = [tab for tab in vals(fields(library), 1) if get(tab, 1, 0) == kind]
    if not tabs and create:
        return library + msg(1, integer(1, kind) + msg(2, text(1, 'root') + integer(3, 1))
                             + msg(3, text(1, '未分类页签') + integer(3, 2) + entries))
    tab = one(tabs, 'Native library tab '+str(kind))
    listing = get(tab, 3)
    if listing is None:
        raise ValueError('Native library tab has no uncategorized listing')
    updated = replace_message(tab, 3, listing, listing + entries)
    return replace_message(library, 1, tab, updated)


def rename_transform_object(raw, name, changes, property_field=5, component_field=6):
    if not isinstance(name, str) or not name.strip() or '\0' in name:
        raise ValueError('Placed object name must be nonempty')
    label = typed_record(raw, property_field, 1, strict=True)
    body = patch_fields(get(label, 11), {1: (2, name.encode('utf-8'))})
    raw = replace_message(raw, property_field, label, patch_fields(label, {11: (2, body)}))
    if any(key in changes for key in TRS):
        transform = typed_record(raw, component_field, 1, strict=True)
        body = transform_edits(get(transform, 11), changes)
        raw = replace_message(raw, component_field, transform, patch_fields(transform, {11: (2, body)}))
    return raw


def duplicate_entities(data, op):
    schema(op, ('op', 'copies'), ('op', 'copies'))
    copies = op['copies']
    if not isinstance(copies, list) or not copies:
        raise ValueError('Provide a nonempty list of placed entity copies')
    _, root = container(data)
    section = singular(root, 5)
    library = singular(root, 6)
    if section is None or library is None:
        raise ValueError('Calibrated placed-object section and library required')
    tab = select_record(library, 1, 3, 'Placed-object library tab')
    listing = singular(fields(tab), 3)
    if listing is None:
        raise ValueError('Placed-object library listing absent')
    members = Counter(get(entry, 2, 0) for entry in vals(fields(listing), 5) if get(entry, 1, 0) == 200)
    records = {get(raw, 1, 0): raw for raw in vals(fields(section), 1)}
    templates = read_templates(root)
    available = next_object_ids(data, root)
    additions = []
    result = []
    keys = set()
    for copy in copies:
        schema(copy, ('key', 'source_entity_id', 'name', *TRS), ('key', 'source_entity_id', 'name'))
        key, source, name = copy['key'], copy['source_entity_id'], copy['name']
        if not isinstance(key, str) or not key.strip() or key in keys:
            raise ValueError('Copy keys must be unique nonempty strings')
        keys.add(key)
        if not is_object_id(source) or source not in records or members[source] != 1:
            raise ValueError('Source must be an ordinary placed object listed exactly once: ' + str(source))
        original = records[source]
        detail = placed_details(original, templates)
        if not detail['transform_editable']:
            raise ValueError('Source is outside the calibrated copy format: ' + str(source))
        if any((n, w) not in ((1,0),(2,2),(5,2),(6,2),(7,2),(8,0)) for n,w,_,_ in fields(original)):
            raise ValueError('Uncalibrated fields on placed object: ' + str(source))
        _, decoration_ids = decoration_links(original, 5)
        if decoration_ids:
            raise ValueError('Placed object has instance-owned decorations: ' + str(source))
        # Other components are copied verbatim. An embedded self ID would
        # require a calibrated remapping contract before it can be duplicated.
        if any(w == 2 and vi(source) in value for _,w,value,_ in fields(original)):
            raise ValueError('Placed object contains an embedded reference to its own ID: ' + str(source))
        assigned = next(available, None)
        if assigned is None:
            raise ValueError('Ordinary object ID range exhausted')
        clone = rename_transform_object(original, name, copy)
        clone = patch_fields(clone, {1: (0, assigned)})
        additions.append(msg(1, clone))
        result.append({'key': key, 'source_entity_id': source, 'entity_id': assigned,
                       'graph_ids': list(entity_graph_ids(clone)),
                       **placed_details(clone, templates)})
    updated_library = append_library_entries(library, 3, 200, [item['entity_id'] for item in result])
    output = set_section(set_section(data, 5, section + b''.join(additions)), 6, updated_library)
    return output, {'copies': result}


def place_static_scene(data, op, base):
    schema(op, ('op', 'source', 'version', 'mode', 'prototypes', 'offset_m'),
           ('op', 'source', 'version', 'mode', 'prototypes'))
    from scene_authoring import MODE, VERSION
    if (op['version'], op['mode']) != (VERSION, MODE):
        raise ValueError('Static GIA placement supports platform 7.2 in beyond mode')
    assets = read_gia(resolve(base, op['source']).read_bytes(), static_only=True)
    if not assets:
        raise ValueError('Static scene GIA has no objects')
    mapping = op['prototypes']
    required = {str(obj['template_id']) for obj in assets}
    if not isinstance(mapping, dict) or mapping.keys() != required or not all(is_object_id(i) for i in mapping.values()):
        raise ValueError('Provide a placed prototype ID for each platform template in the GIA')
    _, root = container(data)
    placed = {get(raw, 1, 0): raw for raw in vals(fields(singular(root, 5, default=b'')), 1)}
    for template, ident in mapping.items():
        reference = ordinary_object(placed.get(ident, b''))
        if not reference or str(reference['template_id']) != template or not reference['static']:
            raise ValueError(f'Prototype {ident} must be a static placed instance of platform template {template}')
    offset = vector(op.get('offset_m', [0, 0, 0]), 'Scene offset')
    copies = [
        {'key': str(item['record_id']), 'source_entity_id': mapping[str(item['template_id'])],
         'name': item['name'], 'position_m': [v + delta for v, delta in zip(item['position_m'], offset)],
         'rotation_deg': item['rotation_deg'], 'scale': item['scale']}
        for item in assets
    ]
    return duplicate_entities(data, {'op': 'duplicate_entities', 'copies': copies})


def arrangement_objects(spec):
    from scene_authoring import MODE, VERSION

    schema(spec, ('schema', 'version', 'mode', 'offset_m', 'objects', 'arrays'), ('version', 'mode'), version=1)
    if (spec['version'], spec['mode']) != (VERSION, MODE):
        raise ValueError('Instance arrangements support platform 7.2 in beyond mode')
    objects, arrays = spec.get('objects', []), spec.get('arrays', [])
    if not isinstance(objects, list) or not isinstance(arrays, list):
        raise ValueError('Arrangement objects and arrays must be lists')
    limit = OBJECT_ID_END - OBJECT_ID_START + 1
    if len(objects) > limit:
        raise ValueError('Arrangement exceeds the ordinary object ID range')
    offset = vector(spec.get('offset_m', [0, 0, 0]), 'Arrangement offset')
    rows = list(objects)
    for array in arrays:
        required = ('key_prefix', 'source_entity_id', 'start_m', 'step_m', 'count')
        schema(array, (*required, 'rotation_deg', 'scale'), required)
        prefix, count = array['key_prefix'], array['count']
        if not isinstance(prefix, str) or not prefix.strip() or '\0' in prefix:
            raise ValueError('Array key_prefix must be a nonempty string')
        if type(count) is not int or not 0 <= count <= limit - len(rows):
            raise ValueError('Array count must be nonnegative and fit the ordinary object ID range')
        start = vector(array['start_m'], f'Array {prefix} start')
        step = vector(array['step_m'], f'Array {prefix} step')
        common = {name: array[name] for name in ('source_entity_id', 'rotation_deg', 'scale') if name in array}
        for i in range(count):
            rows.append({**common, 'key': f'{prefix}/{i + 1:04d}',
                         'position_m': [origin + i * delta for origin, delta in zip(start, step)]})

    layout = {}
    for row in rows:
        schema(row, ('key', 'source_entity_id', 'name', *TRS), ('key', 'source_entity_id'))
        key, source = row['key'], row['source_entity_id']
        if not isinstance(key, str) or not key.strip() or '\0' in key or key in layout:
            raise ValueError('Arrangement keys must be unique nonempty strings: ' + repr(key))
        if not is_object_id(source):
            raise ValueError(f'Arrangement prototype for {key} must be an ordinary placed entity ID')
        name = row.get('name', key)
        if not isinstance(name, str) or not name.strip() or '\0' in name:
            raise ValueError(f'Arrangement name for {key} must be nonempty')
        desired = {field: vector(row[field], f'{field} for {key}', positive=field == 'scale')
                   for field in TRS if field in row}
        if 'position_m' in desired:
            desired['position_m'] = vector([v + delta for v, delta in zip(desired['position_m'], offset)],
                                           f'World position for {key}')
        layout[key] = {'key': key, 'source_entity_id': source, 'name': name, **desired}
    return layout


def arrange_instances(data, op, base, *, baseline):
    from native_bindings import read_bindings

    schema(op, ('op', 'source', 'previous_bindings'), ('op', 'source'))
    layout = arrangement_objects(read_json(resolve(base, op['source'])))
    previous = {}
    if 'previous_bindings' in op:
        bindings, _ = read_bindings(resolve(base, op['previous_bindings']), baseline)
        if (any(not name.startswith('entity:') for name in bindings.ids)
                or len(set(bindings.ids.values())) != len(bindings.ids)):
            raise ValueError('Previous arrangement bindings must map distinct entity keys to distinct placed instances')
        previous = {name.removeprefix('entity:'): ident for name, ident in bindings.ids.items()}
    if not layout and not previous:
        raise ValueError('Provide an arrangement with objects, arrays, or previous bindings')

    _, root = container(data)
    section = singular(root, 5, default=b'')
    templates = read_templates(root)
    records = defaultdict(list)
    for record in vals(fields(section), 1):
        records[get(record, 1, 0)].append(record)
    instances, updates = {}, {}
    for key, ident in previous.items():
        if not is_object_id(ident):
            raise ValueError(f'Arrangement key {key} requires an ordinary placed entity ID')
        target = one(records[ident], f'Placed entity for {key}')
        before = placed_details(target, templates)
        if not before['transform_editable']:
            raise ValueError(f'Placed entity for {key} is outside the calibrated transform scope')
        item = layout.get(key)
        after = before['transform']
        change = 'retained'
        if item is not None:
            prototype = placed_details(one(records[item['source_entity_id']], f'Arrangement prototype for {key}'), templates)
            if any(before[field] != prototype[field] for field in ('template', 'model', 'static')):
                raise ValueError(f'Arrangement prototype for {key} differs from the existing instance identity')
            after = before['transform'] | {name: item[name] for name in TRS if name in item}
            change = 'unchanged'
            if after != before['transform']:
                changes = {n: after[name] for n, name in enumerate(TRS, 1) if after[name] != before['transform'][name]}
                newer = patch_entity_transform(target, changes)
                if placed_details(newer, templates) != {**before, 'transform': after}:
                    raise ValueError(f'Arrangement transform readback differs for {key}')
                updates[target] = newer
                change = 'moved'
        instances[key] = {'key': key, 'entity_id': ident, 'change': change,
                          'before': before['transform'], 'after': after}

    new_keys = sorted(layout.keys() - previous.keys())
    if new_keys:
        data, copied = duplicate_entities(data, {'op': 'duplicate_entities', 'copies': [layout[key] for key in new_keys]})
        for row in copied['copies']:
            key = row['key']
            instances[key] = {'key': key, 'entity_id': row['entity_id'], 'change': 'created',
                              'before': None, 'after': row['transform']}
    if updates:
        section = singular(container(data)[1], 5)
        placed = b''.join(msg(1, updates[value]) if (number, wire) == (1, 2) and value in updates else raw
                          for number, wire, value, raw in fields(section))
        data = set_section(data, 5, placed)
    counts = Counter(row['change'] for row in instances.values())
    return data, {'counts': {name: counts[name] for name in ('created', 'moved', 'unchanged', 'retained')},
                  'instances': [instances[key] for key in sorted(instances)]}


def set_object_transform(data, op):
    schema(op, ('op', 'section', 'entity_id', *TRS), ('op', 'section', 'entity_id'))
    if op['section'] != 5 or not any(key in op for key in TRS):
        raise ValueError('Select a placed static object in section 5 and give a transform change')
    _, root = container(data)
    section = unique(root, 5, default=b'')
    target = select_record(section, 1, op['entity_id'], 'Placed object')
    before = ordinary_object(target)
    if before is None or not before['static']:
        raise ValueError('Target is outside the calibrated ordinary static object format')
    block = typed_record(target, 6, 1)
    body = get(block, 11)
    changed = patch_fields(block, {11: (2, transform_edits(body, op))})
    newer = replace_message(target, 6, block, changed)
    after = ordinary_object(newer)
    if {k: v for k, v in before.items() if k not in TRS} != {k: v for k, v in after.items() if k not in TRS}:
        raise ValueError('Static object identity changed')
    return set_section(data, 5, replace_message(section, 1, target, newer)), {'before': before, 'after': after}


def patch_entity_transform(target, changes):
    component = typed_record(target, 6, 1, strict=True)
    body = singular(fields(component), 11)
    changed = patch_vectors(body, changes, preserve_zero=True)
    return replace_message(target, 6, component, replace_message(component, 11, body, changed))


def set_entity_transform(data, op):
    schema(op, ('op', 'section', 'entity_id', *TRS), ('op', 'section', 'entity_id'))
    if type(op['section']) is not int or op['section'] != 5 or not is_object_id(op['entity_id']):
        raise ValueError('Select a calibrated placed entity in section 5')
    changes = {n: vector(op[name], name, positive=name == 'scale')
               for n, name in enumerate(TRS, 1) if name in op}
    if not changes:
        raise ValueError('Specify at least one position_m, rotation_deg, or scale')
    header, root = container(data)
    if header[1:4] != GIL_HEADER:
        raise ValueError('Entity transform edits require a calibrated GIL container')
    ident = op['entity_id']
    section = singular(root, 5, default=b'')
    target = select_record(section, 1, ident, 'Placed entity')
    singular(fields(target), 1, 0)
    templates = read_templates(root)
    before = placed_details(target, templates)
    if not before['transform_editable']:
        raise ValueError('Entity transform layout or scale is outside the calibrated write scope')
    newer = patch_entity_transform(target, changes)
    result = data if target == newer else set_section(data, 5, replace_message(section, 1, target, newer))
    _, observed_root = container(result)
    observed = select_record(singular(observed_root, 5), 1, ident, 'Written entity')
    after = placed_details(observed, templates)
    expected = before['transform'] | {TRS[n - 1]: value for n, value in changes.items()}
    if after != {**before, 'transform': expected}:
        raise ValueError('Placed entity transform readback differs')
    return result, {'section': 5, 'entity_id': ident, 'before': before, 'after': after}


def colour_value(colour):
    if not isinstance(colour, str) or not re.fullmatch('#[a-fA-F0-9]{6}', colour):
        raise ValueError('Colour must be #RRGGBB')
    return int(colour[1:], 16)


def describe_decoration(record):
    owner = typed_record(record, 4, 40)
    transform = typed_record(record, 5, 1)
    label = typed_record(record, 4, 1)
    colour = typed_record(record, 5, 22)
    template_part = get(get(record, 12, default=b''), 1, 0)
    marker = get(record, 3, 0)
    if (owner is None or transform is None or label is None
            or (marker != 1 and not (marker is None and template_part is not None))):
        raise ValueError('Unsupported decoration record')
    parent = get(get(owner, 50, default=b''), 502, 0)
    tr = get(transform, 11)
    if parent is None or tr is None:
        raise ValueError('Decoration parent or transform absent')
    colour_data = get(colour, 32, default=b'') if colour is not None else b''
    rgb = f"#{get(colour_data, 5, 0, 0):06X}" if get(colour_data, 1, 0) == 1 else None
    return {'decoration_id': get(record, 1, 0), 'owner_id': parent,
            'model_id': get(record, 2, 0), 'name': get(get(label, 11, default=b''), 1, default=b'').decode('utf-8'),
            'color_rgb': rgb, **read_transform(tr)}


def decoration_links(owner, section):
    prop = typed_record(owner, 6 if section == 4 else 5, 40)
    if prop is None:
        return None, []
    raw = get(prop, 50, default=b'')
    ids = stream(get(raw, 501, default=b''))
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate decoration links')
    return prop, ids


def set_decoration(data, op):
    schema(op, ('op', 'section', 'entity_id', 'decoration_id', *TRS, 'color_rgb'),
           ('op', 'section', 'entity_id', 'decoration_id'))
    sec = op['section']
    if sec not in (4, 5) or not any(key in op for key in (*TRS, 'color_rgb')):
        raise ValueError('Select a template or placed object and provide a part change')
    _, root = container(data)
    owner = select_record(unique(root, sec, default=b''), 1, op['entity_id'], 'Decoration owner')
    decoration_type = 1 if sec == 4 else 2
    rows = unique(root, 27, default=b'')
    original = select_record(rows, decoration_type, op['decoration_id'], 'Decoration')
    before = describe_decoration(original)
    if (sec == 4) != (get(original,3,0)==1):
        raise ValueError('Decoration and owner scope differ')
    _, ids = decoration_links(owner, sec)
    if before['owner_id'] != op['entity_id'] or before['decoration_id'] not in ids:
        raise ValueError('Decoration links do not identify the same owner')
    updated = original
    if any(key in op for key in TRS):
        transform = typed_record(original, 5, 1)
        changed = patch_fields(transform, {11: (2, transform_edits(get(transform, 11), op))})
        updated = replace_message(updated, 5, transform, changed)
    if 'color_rgb' in op:
        colour = typed_record(original, 5, 22)
        if colour is None:
            raise ValueError('Existing colour component required')
        values = get(colour, 32, default=b'')
        blend = get(values, 6, 0)
        if blend not in (6700, 6701) or get(values, 3, 0) is None:
            raise ValueError('Unsupported native colour component')
        rgb = colour_value(op['color_rgb'])
        argb = (get(values, 3, 0) & 0xff000000) | rgb
        changed = patch_fields(values, {1: (0, 1), 3: (0, argb), 5: (0, rgb or None)})
        updated = replace_message(updated, 5, colour, patch_fields(colour, {32: (2, changed)}))
    after = describe_decoration(updated)
    return set_section(data, 27, replace_message(rows, decoration_type, original, updated)), {'before': before, 'after': after}


def append_decorations(data, op):
    schema(op, ('op', 'section', 'entity_id', 'parts'), ('op', 'section', 'entity_id', 'parts'))
    if op['section'] != 4:
        raise ValueError('New whitebox decorations belong to an existing template in section 4')
    _, root = container(data)
    templates = unique(root, 4, default=b'')
    owner = select_record(templates, 1, op['entity_id'], 'Decoration template')
    if get(owner, 2, 0) not in (*WHITEBOX, 10005018) or typed_record(owner, 7, 3) is None:
        raise ValueError('An existing dynamic whitebox or empty-model template is required')
    rows = unique(root, 27)
    prop, ids = decoration_links(owner, 4)
    if rows is None or prop is None:
        raise ValueError('The template must already have a calibrated decoration list and section')
    records = vals(fields(rows), 1)
    by_id = {get(record, 1, 0): record for record in records}
    if len(by_id) != len(records) or None in by_id:
        raise ValueError('Ambiguous template decoration records')
    for ident in ids:
        if ident not in by_id or describe_decoration(by_id[ident])['owner_id'] != op['entity_id']:
            raise ValueError('Template decoration links are incomplete')
    occupied = {get(record, 1, 0) for field in (1, 2) for record in vals(fields(rows), field)}
    occupied.update(get(record, 1, 0) for section in (4, 5)
                    for record in vals(fields(unique(root, section, default=b'')), 1))
    next_id = max((DECORATION_START - 1, *(i for i in occupied if i is not None and DECORATION_START <= i <= DECORATION_END))) + 1
    parts = op['parts']
    if not isinstance(parts, list) or not parts or next_id + len(parts) - 1 > DECORATION_END:
        raise ValueError('Provide a nonempty list within the decoration ID range')
    new_records = []
    for ident, part in enumerate(parts, next_id):
        schema(part, ('shape_id', 'name', *TRS, 'color_rgb', 'solid'), ('shape_id', 'name', 'position_m'))
        shape, name = part['shape_id'], part['name']
        if type(shape) is not int or shape not in WHITEBOX or not isinstance(name, str) or not name.strip() or '\0' in name:
            raise ValueError('Use a calibrated whitebox shape ID and a nonempty part name')
        solid = part.get('solid', True)
        if type(solid) is not bool:
            raise ValueError('Decoration solid must be boolean')
        vectors = [vector(part.get(key, default), key, positive=key == 'scale')
                   for key, default in zip(TRS, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))]
        tr = b''.join(msg(number, encode_vector(value)) for number, value in enumerate(vectors, 1))
        rgb = colour_value(part['color_rgb']) if 'color_rgb' in part else 0xffffff
        rgb_fields = (integer(1, 1) if 'color_rgb' in part else b'') + integer(3, 0xff000000 | rgb)
        rgb_fields += flt(4, 100) + (integer(5, rgb) if rgb else b'') + integer(6, 6700)
        collision = integer(1, 1) + integer(2, 1) if solid else b''
        record = (
            integer(1, ident) + integer(2, shape) + integer(3, 1)
            + msg(4, integer(1, 1) + msg(11, text(1, name)))
            + msg(4, integer(1, 40) + msg(50, integer(502, op['entity_id'])))
            + msg(4, integer(1, 111) + msg(93))
            + msg(5, integer(1, 1) + msg(11, tr))
            + msg(5, integer(1, 5) + msg(15, collision))
            + msg(5, integer(1, 2) + msg(12))
            + msg(5, integer(1, 22) + msg(32, rgb_fields))
            + msg(11)
        )
        new_records.append(record)
    added_ids = [get(record, 1, 0) for record in new_records]
    linked = patch_fields(get(prop, 50, default=b''), {501: (2, b''.join(vi(i) for i in ids + added_ids))})
    newer = replace_message(owner, 6, prop, patch_fields(prop, {50: (2, linked)}))
    decoration_rows = fields(rows)
    at = next((i for i, row in enumerate(decoration_rows) if row[:2] == (2, 2)), len(decoration_rows))
    decorated = (b''.join(row[3] for row in decoration_rows[:at])
                 + b''.join(msg(1, record) for record in new_records)
                 + b''.join(row[3] for row in decoration_rows[at:]))
    result = set_section(data, 4, replace_message(templates, 1, owner, newer))
    result = set_section(result, 27, decorated)
    if decoration_links(newer, 4)[1] != ids + added_ids:
        raise ValueError('New template decoration links did not read back')
    return result, {'entity_id': op['entity_id'], 'parts': [describe_decoration(record) for record in new_records]}


def dynamic_object(data, op):
    _, root = container(data)
    section = unique(root, 5, default=b'')
    target = select_record(section, 1, op['entity_id'], 'Dynamic placed object')
    label = typed_record(target, 5, 1)
    ident = get(target, 1, 0)
    if (not OBJECT_ID_START <= ident <= OBJECT_ID_END or label is None
            or get(get(label, 11, default=b''), 2, 0, 0) != 0
            or typed_record(target, 6, 3) is None):
        raise ValueError('Existing dynamic ordinary object with a graph component required')
    return section, target


def dynamic_target(data, op):
    number = op.get('section', 5)
    if type(number) is not int or number not in (4,5):
        raise ValueError('Dynamic object section must be 4 (template) or 5 (instance)')
    _, root = container(data)
    if number == 4:
        section = unique(root,4,default=b'')
        target = select_record(section,1,op['entity_id'],'Ordinary object template')
        if op['entity_id'] not in read_templates(root) or get(target,9,0,0) or typed_record(target,7,3) is None:
            raise ValueError('Select an ordinary dynamic object template with a graph component')
        inherited = b''
    else:
        section,target = dynamic_object(data,op)
        locator = get(target,2,default=b'')
        template = get(locator,1,0)
        inherited = (select_record(unique(root,4,default=b''),1,template,'Native object template')
                     if template and get(locator,2,0,0)==0 else b'')
    return number,section,target,inherited


def add_box_trigger(data, op):
    schema(op, ('op', 'section','entity_id', 'offset_m', 'size_m'), ('op', 'entity_id', 'size_m'))
    number,section,target,inherited = dynamic_target(data,op)
    carrier = 8 if number==4 else 7
    if typed_record(target,carrier,5) is not None or typed_record(inherited,8,5) is not None:
        raise ValueError('Target already has a local or inherited trigger')
    size = vector(op['size_m'], 'Trigger size', positive=True)
    offset = vector(op.get('offset_m', [0, 0, 0]), 'Trigger offset')
    if max(size) > 500:
        raise ValueError('Calibrated trigger box dimensions must be at most 500 metres')
    area = msg(11, msg(1, encode_vector(offset)) + msg(2, encode_vector(size)) + msg(3))
    area += text(502, '区域1') + integer(503, 1)
    trigger = (
        integer(1, 1) + integer(2, 1) + msg(3, b'\x01\x02') + msg(4, area)
        + text(502, '触发器 序号:1') + msg(503, b'\x00')
    )
    config = msg(carrier, integer(1, 5) + integer(2, 1) + msg(15, msg(1, trigger)))
    rows = fields(target)
    at = next((i for i, row in enumerate(rows) if row[0] > carrier), len(rows))
    newer = b''.join(row[3] for row in rows[:at]) + config + b''.join(row[3] for row in rows[at:])
    actual = get(get(typed_record(newer, carrier, 5), 15), 1)
    if actual != trigger:
        raise ValueError('Collision trigger readback failed')
    return set_section(data, number, replace_message(section, 1, target, newer)), {
        'entity_id': op['entity_id'], 'trigger_id': 1, 'targets': ['character'],
        'offset_m': offset, 'size_m': size,
    }


def add_native_movers(data, op):
    from authoring_io import PLUGIN, sha_file
    from native_gameplay import name_value, number
    from platform_profiles import CATALOGUE, check
    from scene_authoring import MODE, VERSION
    schema(op, ('op','section','entity_id','version','mode','motions','follow'), ('entity_id','version','mode'))
    if (op['version'],op['mode'])!=(VERSION,MODE):
        raise ValueError('Mover creation requires 7.2 beyond')
    section_id,section,target,inherited = dynamic_target(data,op)
    field = 8 if section_id==4 else 7
    motions = op.get('motions',[])
    follow = op.get('follow',False)
    if not isinstance(motions,list) or type(follow) is not bool or not (motions or follow):
        raise ValueError('Declare motions or attach a follow component')
    if follow and motions:
        raise ValueError('Author a follow component or a basic mover list on this target')
    if any(typed_record(target,field,k) is not None or typed_record(inherited,8,k) is not None for k in (4,9)):
        raise ValueError('Target already has a local or inherited mover component')
    loops = {'once':1000,'bounce':1001,'restart':1002}
    baseline = msg(502,integer(2,1000)+msg(502))
    rotation_body = (msg(1,encode_vector([1,0,1]))+msg(2)+integer(3,5501)+flt(4,1)
                     +integer(6,5600)+flt(7,1))
    untouched = (msg(512,integer(1,4)+msg(15,rotation_body)+baseline)
                 +msg(513,integer(1,2)+msg(13)+msg(502,integer(2,1000)+msg(502)+integer(503,1))))
    names,kinds,records,details = set(),[],[],[]
    for i,item in enumerate(motions,1):
        schema(item, ('name','active','seconds','displacement_m','waypoints','loop'), ('name',))
        label = name_value(item['name'])
        active = item.get('active',False)
        if type(active) is not bool or label in names:
            raise ValueError('Mover names must be unique and active must be boolean')
        names.add(label)
        if 'waypoints'in item:
            steps,loop = item['waypoints'],item.get('loop','once')
            if not isinstance(steps,list) or not 1<=len(steps)<=20 or loop not in loops or 'displacement_m'in item or 'seconds'in item:
                raise ValueError('Path mover requires 1–20 waypoints and loop once, bounce or restart')
            path = integer(2,loops[loop])
            for step in steps:
                schema(step, ('position_m','rotation_deg','seconds'), ('seconds',))
                position = vector(step.get('position_m',[0,0,0]),'Path waypoint offset')
                rotation = vector(step.get('rotation_deg',[0,0,0]),'Path waypoint rotation')
                seconds = number(step['seconds'],'Path travel time')
                if not 0<seconds<=600:raise ValueError('Path travel time must be in (0, 600]')
                path += msg(501,msg(2,encode_vector(position))+msg(3,encode_vector(rotation))+flt(4,seconds)
                            +integer(5,900)+msg(7)+msg(8))
            body = integer(1,2)+msg(13)+msg(502,path+msg(502))
            kind = 'path'
        else:
            if not {'seconds','displacement_m'}.issubset(item) or 'loop'in item:
                raise ValueError('Linear motion requires seconds and displacement_m')
            seconds = number(item['seconds'],'Linear motion seconds')
            offset = vector(item['displacement_m'],'Linear motion displacement')
            if not 0<seconds<=600 or not any(offset):
                raise ValueError('Linear motion requires nonzero displacement and 0 < seconds <= 600')
            velocity = vector([v/seconds for v in offset],'Linear motion velocity')
            body = msg(11,flt(1,seconds)+msg(2,encode_vector(velocity))+msg(501,encode_vector(offset)))+baseline
            kind = 'linear'
        kinds.append(kind)
        record = text(1,label)+(integer(2,1) if active else b'')+integer(501,i)+msg(511,body)+untouched
        records.append(msg(3,record))
        details.append({'motion_id':i,'name':label,'kind':kind,'active':active})
    checked = check({'schema':2,'version':op['version'],'mode':op['mode'],
                     'objects':[{'id':str(op['entity_id']),'kind':'movers','active':kinds}]})
    if checked['status']!='passed':raise ValueError('Platform mover compatibility did not pass')
    if motions:
        target_new = target+msg(field,integer(1,4)+integer(2,1)+msg(14,b''.join(records)+integer(505,1)))
    else:
        target_new = target
    if follow:
        # A graph assigns the runtime target and enables this attachment.
        body = (text(2,'default')+msg(3,flt(1,1)+flt(3,1))+msg(4)+integer(5,1200)
                +integer(6,1100)+msg(7,msg(11))+text(502,'完全跟随'))
        target_new += msg(field,integer(1,9)+integer(2,1)+msg(19,body))
    sources = {CATALOGUE.relative_to(PLUGIN).as_posix(): sha_file(CATALOGUE)}
    sources.update({info['path']:info['sha256'] for info in checked['sources'].values()})
    changed = set_section(data,section_id,replace_message(section,1,target,target_new))
    return changed, {'section':section_id,'entity_id':op['entity_id'],'motions':details,'follow':follow,'platform_sources':sources}


def set_native_preset_state(data,op):
    from native_gameplay import int_range
    schema(op,('op','section','entity_id','state_id','value'),('section','entity_id','state_id','value'))
    number,section,target,_=dynamic_target(data,op)
    field=7 if number==4 else 6
    block=typed_record(target,field,2,strict=True)
    payload=get(block or b'',12)
    if payload is None:
        raise ValueError('Target has no calibrated model preset states')
    ident=int_range(op['state_id'],'Model preset state ID')
    value=int_range(op['value'],'Model preset state value',0,0xffffffff)
    state=select_record(payload,2,ident,'Model preset state')
    new_state=patch_fields(state,{2:(0,value or None)})
    updated=replace_message(block,12,payload,replace_message(payload,2,state,new_state))
    edited=replace_message(target,field,block,updated)
    return set_section(data,number,replace_message(section,1,target,edited)),{
        'section':number,'entity_id':op['entity_id'],'state_id':ident,'before':get(state,2,0,0),'after':get(new_state,2,0,0)}



def set_linear_motion(data, op):
    schema(op, ('op', 'entity_id', 'motion_id', 'version', 'mode', 'seconds', 'displacement_m'),
           ('op', 'entity_id', 'motion_id', 'version', 'mode', 'seconds', 'displacement_m'))
    from platform_profiles import CATALOGUE, check
    from authoring_io import PLUGIN, sha_file

    section, target = dynamic_object(data, op)
    component = typed_record(target, 7, 4)
    if component is None:
        raise ValueError('An existing basic motion component is required')
    configs = get(component, 14, default=b'')
    motions = [(field, raw) for field, wire, raw, _ in fields(configs) if field in (1, 3) and wire == 2]
    if type(op['motion_id']) is not int or op['motion_id'] < 1:
        raise ValueError('Invalid motion ID')
    layout_field, motion = one(
        ((field, raw) for field, raw in motions if get(raw, 503 if field == 1 else 501, 0) == op['motion_id']),
        'Motion',
    )
    slots = [get(raw, 511, default=b'') if field == 3 else raw for field, raw in motions]
    if any(get(slot, 11) is None for slot in slots):
        raise ValueError('Existing basic motion component must contain only calibrated linear entries')
    declared = check({'schema': 2, 'version': op['version'], 'mode': op['mode'],
                      'objects': [{'id': str(op['entity_id']), 'kind': 'movers', 'active': ['linear'] * len(slots)}]})
    if declared['status'] != 'passed':
        raise ValueError('Platform motion rules did not pass')
    slot = get(motion, 511) if layout_field == 3 else motion
    body = get(slot, 11)
    if get(body, 1, 5) is None or get(body, 2) is None or get(body, 501) is None:
        raise ValueError('Uncalibrated straight motion parameters')
    seconds = vector([op['seconds'], 0, 0], 'Motion seconds')[0]
    displacement = vector(op['displacement_m'], 'Motion displacement')
    if not 0 < seconds <= 600 or not any(displacement):
        raise ValueError('Linear motion requires nonzero displacement and 0 < seconds <= 600')
    velocity = vector([value / seconds for value in displacement], 'Motion velocity')
    updated = patch_vectors(body, {2: velocity, 501: displacement})
    updated = patch_fields(updated, {1: (5, seconds)})
    slot = patch_fields(slot, {11: (2, updated)})
    motion_updated = patch_fields(motion, {511: (2, slot)}) if layout_field == 3 else slot
    configs = replace_message(configs, layout_field, motion, motion_updated)
    newer = replace_message(target, 7, component, patch_fields(component, {14: (2, configs)}))
    sources = {CATALOGUE.relative_to(PLUGIN).as_posix(): sha_file(CATALOGUE)}
    sources.update({info['path']: info['sha256'] for info in declared['sources'].values()})
    return set_section(data, 5, replace_message(section, 1, target, newer)), {
        'entity_id': op['entity_id'], 'motion_id': op['motion_id'], 'seconds': seconds,
        'displacement_m': read_vector(get(updated, 501)), 'velocity_m_s': read_vector(get(updated, 2)),
        'platform_sources': sources,
    }


SCENE_EDITS = {fn.__name__: fn for fn in (
    duplicate_entities, set_object_transform, set_entity_transform, set_decoration, append_decorations,
    add_box_trigger, add_native_movers, set_linear_motion, set_native_preset_state,
)}
