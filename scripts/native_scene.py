"""Native ordinary object records and independent static GIA packages."""
import struct

from level_inventory import container, fields, unique, vals
from level_authoring import flt, integer, msg, pack, text

OBJECT_ID_START = 0x40400001
OBJECT_ID_END = 0x404FFFFF
FLOAT32_MAX = 3.4028234663852886e38
STATIC_GIA_HEADER = (1, 806, 3)


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


def read_vector(value):
    rows = fields(value)
    if any(number in (1, 2, 3) and wire != 5 for number, wire, _, _ in rows):
        raise ValueError('Unsupported transform coordinate wire type')
    return vector([struct.unpack('<f', unique(rows, i, 5, bytes(4)))[0] for i in (1, 2, 3)], 'Native vector')


def typed_record(core, field, kind):
    matching = [raw for raw in vals(fields(core), field) if unique(fields(raw), 1, 0) == kind]
    if len(matching) > 1:
        raise ValueError('Ambiguous native record of kind ' + str(kind))
    return matching[0] if matching else None


def read_transform(body):
    rows = fields(body)
    return {
        name: read_vector(unique(rows, field, default=default))
        for name, field, default in (
            ('position_m', 1, b''), ('rotation_deg', 2, b''),
            ('scale', 3, encode_vector([1, 1, 1])),
        )
    }


def ordinary_object(core):
    """Recognize placed ordinary platform objects, including the static marker."""
    record = fields(core)
    ident = unique(record, 1, 0)
    if ident is None or not OBJECT_ID_START <= ident <= OBJECT_ID_END:
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
