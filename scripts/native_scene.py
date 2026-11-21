"""Calibrated scene-object identities and transforms for native GIL/GIA."""

from collections import Counter
import math
import struct

from authoring_io import schema
from level_authoring import flt, set_section, stream
from level_inventory import container, fields, unique, vals
from native_core import replace_message

GIL_HEADER = (1, 806, 2)
GIA_HEADER = (1, 806, 3)
OBJECT_ID_START = 0x40400001
OBJECT_ID_END = 0x404FFFFF
TRS = ('position_m', 'rotation_deg', 'scale')
FLOAT32_MAX = 3.4028234663852886e38


def singular(rows, number, wire=2, default=None):
    """A calibrated field has exactly one wire type and no duplicate records."""
    matches = [(kind, value) for field, kind, value, _ in rows if field == number]
    if not matches:
        return default
    if len(matches) != 1 or matches[0][0] != wire:
        raise ValueError(f'Ambiguous or incompatible native field {number}')
    return matches[0][1]


def typed_record(rows, field, kind):
    matches = [record for record in vals(rows, field) if singular(fields(record), 1, 0) == kind]
    if len(matches) > 1:
        raise ValueError(f'Ambiguous native component {kind}')
    return matches[0] if matches else None


def read_transform(body, space):
    result = {'space': space, 'axes': 'native_xyz_y_up'}
    rows = fields(body)
    for number, name in enumerate(TRS, 1):
        raw = singular(rows, number)
        if raw is None:
            raise ValueError(f'Missing calibrated {name} vector')
        vector = fields(raw)
        defaults = None if name == 'scale' else bytes(4)
        values = [singular(vector, axis, 5, defaults) for axis in (1, 2, 3)]
        if any(value is None for value in values):
            raise ValueError('Missing explicit native scale axis')
        result[name] = [struct.unpack('<f', value)[0] for value in values]
        if not all(math.isfinite(value) for value in result[name]):
            raise ValueError(f'Non-finite native {name}')
    return result


def model_reference(model_id, source):
    # The GIL stores a native template/asset locator. It does not establish
    # catalogue availability, mesh IDs, dimensions, or the model's geometry.
    return {'type': 'template', 'id': model_id, 'source': source, 'resource_verified': False}


def object_body(rows, property_field, component_field, space):
    label = typed_record(rows, property_field, 1)
    component = typed_record(rows, component_field, 1)
    if label is None or component is None:
        raise ValueError('Calibrated name and transform components required')
    name_fields = fields(singular(fields(label), 11, default=b''))
    name = singular(name_fields, 1, default=b'').decode('utf-8')
    body = singular(fields(component), 11)
    if not name or body is None:
        raise ValueError('Calibrated name and transform bodies required')
    marker = singular(name_fields, 2, 0, 0)
    if marker not in (0, 1):
        raise ValueError('Uncalibrated static-unit marker')
    types = sorted({kind for raw in vals(rows, component_field)
                    if (kind := singular(fields(raw), 1, 0)) is not None})
    return {'name': name, 'transform': read_transform(body, space), 'component_types': types}, marker


def is_object_id(ident):
    return ident is not None and OBJECT_ID_START <= ident <= OBJECT_ID_END


def template_details(rows):
    model_id = singular(rows, 2, 0)
    if not model_id:
        return None
    info, _ = object_body(rows, 6, 7, 'template_default')
    return {**info, 'model': model_reference(model_id, 'template_record'), 'transform_editable': False}


def placed_details(rows, templates, space='world'):
    locator = fields(singular(rows, 2, default=b''))
    template_id = singular(locator, 1, 0)
    category = singular(locator, 2, 0, 0)
    companion = singular(rows, 8, 0)
    if not template_id:
        return None
    if category == 1 and companion == template_id:
        template = {'scope': 'platform', 'id': template_id}
        model = model_reference(template_id, 'instance_locator')
    elif category == 0 and template_id in templates:
        model_id = templates[template_id]['model']['id']
        if companion not in (None, model_id):
            return None
        template = {'scope': 'project', 'id': template_id}
        model = model_reference(model_id, 'project_template')
    else:
        return None
    info, marker = object_body(rows, 5, 6, space)
    return {**info, 'template': template, 'model': model, 'static': marker == 1,
            'transform_editable': space == 'world' and min(info['transform']['scale']) > 0}


def unique_objects(records, regular_ids=True):
    identified = []
    for raw in records:
        try:
            rows = fields(raw)
            ident = singular(rows, 1, 0)
        except ValueError:
            continue
        identified.append((ident, rows))
    counts = Counter(ident for ident, _ in identified)
    return {ident: rows for ident, rows in identified
            if counts[ident] == 1 and (is_object_id(ident) if regular_ids else ident)}


def read_templates(root):
    records = [record for section in vals(root, 4) for record in vals(fields(section), 1)]
    templates = {}
    for ident, rows in unique_objects(records).items():
        try:
            detail = template_details(rows)
            if detail is not None:
                templates[ident] = detail
        except ValueError:
            # Spatial data is optional on otherwise indexable native records.
            continue
    return templates


def decoration_details(owner, owners_section, ident, decorations):
    links = typed_record(owner, 6 if owners_section == 4 else 5, 40)
    if links is None:
        return []
    ids = stream(singular(fields(singular(fields(links), 50, default=b'')), 501, default=b''))
    if len(ids) != len(set(ids)):
        raise ValueError('Ambiguous owner decoration list')
    parts = []
    for part_id in ids:
        rows = decorations.get(part_id)
        if rows is None:
            continue
        marker = singular(rows, 3, 0)
        if marker != (1 if owners_section == 4 else None):
            continue
        parent = typed_record(rows, 4, 40)
        if parent is None or singular(fields(singular(fields(parent), 50, default=b'')), 502, 0) != ident:
            continue
        model_id = singular(rows, 2, 0)
        if model_id:
            info, _ = object_body(rows, 4, 5, 'owner_local')
            parts.append({'id': part_id, **info, 'model': model_reference(model_id, 'decoration_record')})
    return parts


def spatial_objects(header, root):
    """Map only recognized records to the existing project-index identities."""
    objects = {}
    if header[1:4] == GIL_HEADER:
        templates = read_templates(root)
        objects.update({('template', ident): info for ident, info in templates.items()})
        decoration_sections = []
        for group in vals(root, 27):
            try:
                decoration_sections.extend(fields(group))
            except ValueError:
                # Section 27 is optional to the general object index.
                continue
        for section, kind in ((4, 'template'), (5, 'entity')):
            owner_sections = vals(root, section)
            records = [raw for group in owner_sections for raw in vals(fields(group), 1)]
            decoration_field = 1 if section == 4 else 2
            decorations = unique_objects(vals(decoration_sections, decoration_field), regular_ids=False)
            for ident, rows in unique_objects(records).items():
                try:
                    info = templates.get(ident) if section == 4 else placed_details(rows, templates)
                except ValueError:
                    continue
                if info is None:
                    continue
                if len(owner_sections) != 1:
                    info['transform_editable'] = False
                objects[kind, ident] = info
                try:
                    parts = decoration_details(rows, section, ident, decorations)
                except ValueError:
                    # An uncalibrated decoration does not change the owner's coordinates.
                    continue
                if parts:
                    info['decorations'] = parts
    elif header[1:4] == GIA_HEADER:
        for raw in vals(root, 1):
            try:
                resource = fields(raw)
                if singular(resource, 5, 0) != 3 or vals(resource, 2):
                    continue
                locator = fields(singular(resource, 1, default=b''))
                if (singular(locator, 2, 0), singular(locator, 3, 0)) != (1, 2):
                    continue
                ident = singular(locator, 4, 0)
                body = fields(singular(resource, 12, default=b''))
                record = fields(singular(body, 1, default=b''))
                if not is_object_id(ident) or singular(record, 1, 0) != ident:
                    continue
                value = placed_details(record, {}, 'asset_world')
                if (value is not None and value['model']['id'] == singular(body, 4, 0)
                        and value['name'].encode('utf-8') == singular(resource, 3)):
                    objects['gia_resource', ident] = value
            except ValueError:
                continue
    return objects


def patch_vector(raw, values):
    pending = dict(enumerate(values, 1))
    parts = []
    for number, _, old, encoded in fields(raw):
        if number in pending:
            replacement = pending.pop(number)
            if struct.unpack('<f', old)[0] == replacement:
                parts.append(encoded)
            elif replacement != 0.0:
                parts.append(flt(number, replacement))
        else:
            parts.append(encoded)
    parts.extend(flt(number, value) for number, value in pending.items() if value != 0.0)
    return b''.join(parts)


def set_entity_transform(data, op):
    schema(op, ('op', 'section', 'entity_id', *TRS), ('op', 'section', 'entity_id'))
    ident = op['entity_id']
    requested = {key: op[key] for key in TRS if key in op}
    if type(op['section']) is not int or op['section'] != 5 or type(ident) is not int or not is_object_id(ident):
        raise ValueError('Select an ordinary placed object by entity_id in section 5')
    if not requested:
        raise ValueError('Specify at least one of position_m, rotation_deg, or scale')
    for key, value in requested.items():
        if (not isinstance(value, list) or len(value) != 3
                or any(type(axis) not in (int, float) or not -FLOAT32_MAX <= axis <= FLOAT32_MAX for axis in value)):
            raise ValueError(f'{key} requires three finite float32 coordinates')
        requested[key] = list(struct.unpack('<3f', struct.pack('<3f', *value)))
    if 'scale' in requested and min(requested['scale']) <= 0:
        raise ValueError('Scale must remain positive after float32 conversion')
    header, root = container(data)
    if header[1:4] != GIL_HEADER:
        raise ValueError('Entity transform edits require a calibrated GIL container')
    section = singular(root, 5, default=b'')
    matches = [raw for raw in vals(fields(section), 1) if unique(fields(raw), 1, 0) == ident]
    if len(matches) != 1:
        raise ValueError('Placed entity must match exactly once')
    target, = matches
    rows = fields(target)
    # Reject mixed-wire identity fields on the selected object.
    singular(rows, 1, 0)
    templates = read_templates(root)
    before = placed_details(rows, templates)
    if before is None or not before['transform_editable']:
        raise ValueError('Unsupported placed-object model locator or transform')
    component = typed_record(rows, 6, 1)
    transform = singular(fields(component), 11)
    updated = transform
    for number, key in enumerate(TRS, 1):
        if key in requested:
            raw = singular(fields(transform), number)
            updated = replace_message(updated, number, raw, patch_vector(raw, requested[key]))
    record = replace_message(target, 6, component, replace_message(component, 11, transform, updated))
    result = data if record == target else set_section(data, 5, replace_message(section, 1, target, record))
    _, observed_root = container(result)
    observed = next(raw for raw in vals(fields(singular(observed_root, 5)), 1) if unique(fields(raw), 1, 0) == ident)
    after = placed_details(fields(observed), templates)
    if after != {**before, 'transform': {**before['transform'], **requested}}:
        raise ValueError('Placed object transform readback differs')
    return result, {'section': 5, 'entity_id': ident, 'before': before, 'after': after}
