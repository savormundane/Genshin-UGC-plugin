"""Scoped GIL edits for already-recognized 3D objects and their decorations."""
import re
import struct

from authoring_io import schema
from level_inventory import container, fields, unique, vals
from level_authoring import flt, integer, msg, set_section, stream, text, vi
from native_core import get, replace_message
from native_scene import (
    OBJECT_ID_END, OBJECT_ID_START, encode_vector, ordinary_object,
    read_transform, read_vector, typed_record, vector,
)

TRS = ('position_m', 'rotation_deg', 'scale')
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


def patch_vector(body, values):
    return patch_fields(body, {number: (5, value or None) for number, value in enumerate(values, 1)})


def patch_vectors(body, changes):
    updated = {}
    for number, value in changes.items():
        current = get(body, number, default=b'')
        updated[number] = (2, patch_vector(current, value))
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


def colour_value(colour):
    if not isinstance(colour, str) or not re.fullmatch('#[a-fA-F0-9]{6}', colour):
        raise ValueError('Colour must be #RRGGBB')
    return int(colour[1:], 16)


def describe_decoration(record):
    owner = typed_record(record, 4, 40)
    transform = typed_record(record, 5, 1)
    label = typed_record(record, 4, 1)
    colour = typed_record(record, 5, 22)
    if get(record, 3, 0) != 1 or owner is None or transform is None or label is None:
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


def add_box_trigger(data, op):
    schema(op, ('op', 'entity_id', 'offset_m', 'size_m'), ('op', 'entity_id', 'size_m'))
    section, target = dynamic_object(data, op)
    if typed_record(target, 7, 5) is not None:
        raise ValueError('Target already has a trigger record')
    template = get(target, 2, default=b'')
    template_id = get(template, 1, 0)
    if template_id and get(template, 2, 0, 0) == 0:
        _, root = container(data)
        owner = select_record(unique(root, 4, default=b''), 1, template_id, 'Trigger template')
        if typed_record(owner, 8, 5) is not None:
            raise ValueError('Target already inherits a trigger from its template')
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
    config = msg(7, integer(1, 5) + integer(2, 1) + msg(15, msg(1, trigger)))
    rows = fields(target)
    at = next((i for i, row in enumerate(rows) if row[0] > 7), len(rows))
    newer = b''.join(row[3] for row in rows[:at]) + config + b''.join(row[3] for row in rows[at:])
    actual = get(get(typed_record(newer, 7, 5), 15), 1)
    if actual != trigger:
        raise ValueError('Collision trigger readback failed')
    return set_section(data, 5, replace_message(section, 1, target, newer)), {
        'entity_id': op['entity_id'], 'trigger_id': 1, 'targets': ['character'],
        'offset_m': offset, 'size_m': size,
    }



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
    set_object_transform, set_decoration, append_decorations, add_box_trigger, set_linear_motion,
)}
