"""Native ordinary object records and independent static GIA packages."""
from collections import Counter
import struct

from level_inventory import GIL_HEADER, STATIC_GIA_HEADER, container, fields, unique, vals
from level_authoring import flt, integer, msg, pack, text

OBJECT_ID_START = 0x40400001
OBJECT_ID_END = 0x404FFFFF
FLOAT32_MAX = 3.4028234663852886e38
TRS = ('position_m', 'rotation_deg', 'scale')


def vector(value, label, *, positive=False):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(label + ' requires three numbers (X, Y, Z)')
    if any(type(v) not in (int, float) or not -FLOAT32_MAX <= v <= FLOAT32_MAX for v in value):
        raise ValueError(label + ' requires finite float32 values')
    result = list(struct.unpack('<3f', struct.pack('<3f', *value)))
    if positive and min(result) <= 0:
        raise ValueError(label + ' requires positive values')
    return result


def encode_vector(values):
    return b''.join(flt(i, value) for i, value in enumerate(values, 1) if value)


def route_box_entry(points, center, size):
    """Find the first crossing into the open interior of an axis-aligned box."""
    lower = [c - width / 2 for c, width in zip(center, size)]
    upper = [c + width / 2 for c, width in zip(center, size)]
    if any(a >= b for a, b in zip(lower, upper)):
        raise ValueError('Trigger bounds cannot be represented at this position')
    for segment, (start, end) in enumerate(zip(points, points[1:]), 1):
        if all(lo < coord < hi for lo, coord, hi in zip(lower, start, upper)):
            continue
        near, far = 0.0, 1.0
        delta = [b - a for a, b in zip(start, end)]
        for lo, hi, origin, step in zip(lower, upper, start, delta):
            if step == 0:
                if not lo < origin < hi:
                    break
                continue
            enter, leave = sorted(((lo - origin) / step, (hi - origin) / step))
            near, far = max(near, enter), min(far, leave)
            if near >= far:
                break
        else:
            return {'segment': segment, 'fraction': near,
                    'position_m': [origin + near * step for origin, step in zip(start, delta)]}
    return None


def singular(rows, number, wire=2, default=None):
    matches = [(w, value) for field, w, value, _ in rows if field == number]
    if not matches:
        return default
    if len(matches) != 1 or matches[0][0] != wire:
        raise ValueError(f'Ambiguous or incompatible native field {number}')
    return matches[0][1]


def read_vector(value, *, require_axes=False):
    rows = fields(value)
    axes = [singular(rows, i, 5, None if require_axes else bytes(4)) for i in (1, 2, 3)]
    if None in axes:
        raise ValueError('Missing explicit native scale axis')
    return vector([struct.unpack('<f', raw)[0] for raw in axes], 'Native vector')


def typed_record(core, field, kind, *, strict=False):
    read = singular if strict else unique
    matching = [raw for raw in vals(fields(core), field) if read(fields(raw), 1, 0) == kind]
    if len(matching) > 1:
        raise ValueError('Ambiguous native record of kind ' + str(kind))
    return matching[0] if matching else None


def read_transform(body, *, explicit=False):
    rows = fields(body)
    if explicit:
        result = {}
        for number, name in enumerate(TRS, 1):
            raw = singular(rows, number)
            if raw is None:
                raise ValueError(f'Missing calibrated {name} vector')
            result[name] = read_vector(raw, require_axes=name == 'scale')
        return result
    return {
        name: read_vector(unique(rows, field, default=default))
        for name, field, default in (
            ('position_m', 1, b''), ('rotation_deg', 2, b''),
            ('scale', 3, encode_vector([1, 1, 1])),
        )
    }


def is_object_id(ident):
    return type(ident) is int and OBJECT_ID_START <= ident <= OBJECT_ID_END


def model_reference(ident, source):
    return {'type': 'template', 'id': ident, 'source': source, 'resource_verified': False}


def object_body(raw, property_field, component_field, space):
    label = typed_record(raw, property_field, 1, strict=True)
    component = typed_record(raw, component_field, 1, strict=True)
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
    types = sorted({kind for part in vals(fields(raw), component_field)
                    if (kind := singular(fields(part), 1, 0)) is not None})
    transform = {'space': space, 'axes': 'native_xyz_y_up', **read_transform(body, explicit=True)}
    return {'name': name, 'transform': transform, 'component_types': types}, marker == 1


def placed_details(raw, templates, space='world'):
    rows = fields(raw)
    locator = fields(singular(rows, 2, default=b''))
    ident = singular(locator, 1, 0)
    category = singular(locator, 2, 0, 0)
    companion = singular(rows, 8, 0)
    if not ident:
        raise ValueError('Placed template locator absent')
    if category == 1 and companion == ident:
        template = {'scope': 'platform', 'id': ident}
        model = model_reference(ident, 'instance_locator')
    elif category == 0 and ident in templates:
        model_id = templates[ident]['model']['id']
        if companion not in (None, model_id):
            raise ValueError('Instance and project template model locators disagree')
        template = {'scope': 'project', 'id': ident}
        model = model_reference(model_id, 'project_template')
    else:
        raise ValueError('Missing or unsupported placed template locator')
    info, static = object_body(raw, 5, 6, space)
    return {**info, 'template': template, 'model': model, 'static': static,
            'transform_editable': space == 'world' and min(info['transform']['scale']) > 0}


def identified_records(records):
    """Return each decodable record with its identity or a concrete identity error."""
    for raw in records:
        try:
            ident = singular(fields(raw), 1, 0)
        except ValueError as exc:
            yield None, raw, str(exc)
            continue
        yield ident, raw, None if ident else 'Native record identity absent'


def read_templates(root, unresolved=None):
    records = [row for group in vals(root, 4) for row in vals(fields(group), 1)]
    records = list(identified_records(records))
    counts = Counter(ident for ident, _, _ in records)
    templates = {}
    for ident, raw, error in records:
        try:
            if error or counts[ident] != 1 or not is_object_id(ident):
                raise ValueError(error or 'Ambiguous or unsupported project template identity')
            model_id = singular(fields(raw), 2, 0)
            if not model_id:
                raise ValueError('Project template has no calibrated model locator')
            info, _ = object_body(raw, 6, 7, 'template_default')
            templates[ident] = {**info, 'model': model_reference(model_id, 'template_record'),
                                'transform_editable': False}
        except ValueError as exc:
            if unresolved is not None:
                unresolved.append({'section': 4, 'id': ident, 'error': str(exc)})
    return templates


def spatial_objects(header, root, unresolved=None):
    """Read calibrated placed/template transforms and owner-local decorations."""
    if header[1:4] == STATIC_GIA_HEADER:
        try:
            records = read_gia_records(root)
        except ValueError as exc:
            if unresolved is not None:
                unresolved.append({'section': 1, 'error': str(exc)})
            return {}
        return {('gia_resource', obj['record_id']): {
            'name': obj['name'], 'static': obj['static'], 'transform_editable': False,
            'template': {'scope': 'platform', 'id': obj['template_id']},
            'model': model_reference(obj['template_id'], 'instance_locator'),
            'transform': {'space': 'asset_world', 'axes': 'native_xyz_y_up', **{key: obj[key] for key in TRS}},
        } for obj in records}
    if header[1:4] != GIL_HEADER:
        return {}
    from native_scene_edits import decoration_links

    templates = read_templates(root, unresolved)
    objects = {('template', ident): detail for ident, detail in templates.items()}
    decoration_rows = []
    for group in vals(root, 27):
        try:
            decoration_rows.extend(fields(group))
        except ValueError as exc:
            if unresolved is not None:
                unresolved.append({'section': 27, 'error': str(exc)})
    for section, kind in ((4, 'template'), (5, 'entity')):
        groups = vals(root, section)
        records = list(identified_records(raw for group in groups for raw in vals(fields(group), 1)))
        counts = Counter(ident for ident, _, _ in records)
        parts = list(identified_records(vals(decoration_rows, 1 if section == 4 else 2)))
        part_counts = Counter(ident for ident, _, _ in parts)
        decorations = {ident: raw for ident, raw, error in parts if not error and part_counts[ident] == 1}
        for ident, raw, error in records:
            try:
                if error or counts[ident] != 1:
                    raise ValueError(error or 'Ambiguous scene object identity')
                if kind == 'entity':
                    if not is_object_id(ident):
                        raise ValueError('Uncalibrated placed-object identity range')
                    detail = placed_details(raw, templates)
                    if len(groups) != 1:
                        detail['transform_editable'] = False
                    objects[kind, ident] = detail
                _, part_ids = decoration_links(raw, section)
            except ValueError as exc:
                if unresolved is not None and (kind == 'entity' or ident in templates):
                    unresolved.append({'section': section, 'id': ident, 'error': str(exc)})
                continue
            read_parts = []
            for part_id in part_ids:
                try:
                    part = decorations.get(part_id)
                    if part is None:
                        raise ValueError('Decoration target absent or ambiguous')
                    rows = fields(part)
                    marker = singular(rows, 3, 0)
                    owner = typed_record(part, 4, 40, strict=True)
                    parent = singular(fields(singular(fields(owner or b''), 50, default=b'')), 502, 0)
                    if marker != (1 if section == 4 else None) or parent != ident:
                        raise ValueError('Decoration owner link disagrees with its native record')
                    model_id = singular(rows, 2, 0)
                    if not model_id:
                        raise ValueError('Decoration has no calibrated model locator')
                    info, _ = object_body(part, 4, 5, 'owner_local')
                    read_parts.append({'id': part_id, **info, 'model': model_reference(model_id, 'decoration_record')})
                except ValueError as exc:
                    if unresolved is not None:
                        unresolved.append({'section': 27, 'id': part_id, 'owner_section': section,
                                           'owner_id': ident, 'error': str(exc)})
            if read_parts and (kind, ident) in objects:
                objects[kind, ident]['decorations'] = read_parts
    return objects


def ordinary_object(core):
    """Recognize placed ordinary platform objects, including the static marker."""
    record = fields(core)
    ident = unique(record, 1, 0)
    if not is_object_id(ident):
        return None
    locator = fields(unique(record, 2, default=b''))
    template = unique(locator, 1, 0)
    if (
        not template or template != unique(record, 8, 0)
        or unique(locator, 2, 0) != 1
    ):
        return None
    label = typed_record(core, 5, 1)
    component = typed_record(core, 6, 1)
    if label is None or component is None:
        return None
    name_fields = fields(unique(fields(label), 11, default=b''))
    name = unique(name_fields, 1)
    transform = unique(fields(component), 11)
    if not name or transform is None:
        return None
    return {
        'record_id': ident, 'template_id': template, 'name': name.decode('utf-8'),
        'static': unique(name_fields, 2, 0, 0) == 1, **read_transform(transform),
    }


def read_gia(data, *, static_only=False):
    header, root = container(data)
    if header[1:4] != STATIC_GIA_HEADER:
        raise ValueError('Expected a supported GIA container')
    return read_gia_records(root, static_only=static_only)


def read_gia_records(root, *, static_only=False):
    if static_only and any(n not in (1, 3) or w != 2 for n, w, _, _ in root):
        raise ValueError('Static scene contains unexpected resource records')
    objects = []
    for item in vals(root, 1):
        asset = fields(item)
        wrapper = unique(asset, 12)
        if wrapper is None or unique(asset, 5, 0) != 3:
            if static_only:
                raise ValueError('Expected a standalone ordinary object')
            continue
        entry = fields(wrapper)
        record = ordinary_object(unique(entry, 1, default=b''))
        loc = fields(unique(asset, 1, default=b''))
        if (
            record is None or unique(loc, 2, 0) != 1 or unique(loc, 3, 0) != 2
            or unique(loc, 4, 0) != record['record_id']
            or unique(entry, 4, 0) != record['template_id']
            or unique(asset, 3) != record['name'].encode('utf-8')
        ):
            if static_only:
                raise ValueError('GIA object identity or template locator mismatch')
            continue
        if static_only and (not record['static'] or vals(asset, 2)):
            raise ValueError('Static object has an unsupported dependency or dynamic marker')
        objects.append(record)
    if len({obj['record_id'] for obj in objects}) != len(objects):
        raise ValueError('Duplicate GIA object identity')
    return objects


def static_objects(data):
    header, root = container(data)
    if header[1:4] == STATIC_GIA_HEADER:
        records = read_gia(data)
    elif header[1:4] == (1, 806, 2):
        placed = unique(root, 5, default=b'')
        records = [part for raw in vals(fields(placed), 1) if (part := ordinary_object(raw))]
    else:
        raise ValueError('Expected calibrated GIL or GIA framing')
    return [obj for obj in records if obj['static']]


def static_gia(objects):
    # Ordinary object import reads the metadata, prototype locator, static
    # name property and transform. Other components take the native defaults.
    assets = []
    for item in objects:
        ident = item['record_id']
        template = item['template_id']
        name = item['name']
        locator = integer(2, 1) + integer(3, 2) + integer(4, ident)
        template_ref = integer(1, template) + integer(2, 1)
        label = integer(1, 1) + msg(11, text(1, name) + integer(2, 1))
        transform = b''.join(
            msg(field, encode_vector(item[key]))
            for field, key in ((1, 'position_m'), (2, 'rotation_deg'), (3, 'scale'))
        ) + integer(501, 0xffffffff)
        core = (
            integer(1, ident) + msg(2, template_ref) + msg(5, label)
            + msg(6, integer(1, 1) + msg(11, transform)) + integer(8, template)
        )
        assets.append(msg(1, msg(1, locator) + text(3, name) + integer(5, 3)
                          + msg(12, msg(1, core) + integer(4, template))))
    return pack(b''.join(assets) + text(3, 'generated\\scene.gia'), STATIC_GIA_HEADER)
