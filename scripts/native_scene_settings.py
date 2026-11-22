"""Read and edit scoped native camera, preset point, terrain and environment records."""
import struct

from authoring_io import schema
from level_authoring import flt, integer, msg, set_section, text
from level_inventory import container, fields, unique, vals
from native_core import get, replace_message
from native_scene import encode_vector, read_vector, typed_record, vector
from native_scene_edits import patch_fields, patch_vectors, select_record

TERRAIN_MATERIALS = {'grass': 0, 'tile': 1, 'sand': 2, 'stone_wall': 4, 'snow': 5}
STRAIGHT_SLOPES = {'flat': 0, '+z': 16, '+x': 17, '-z': 18, '-x': 19}
CELL_METRES = 5
LAYER_METRES = 2.5


def single_float(data, number):
    raw = get(data, number, 5)
    return None if raw is None else struct.unpack('<f', raw)[0]


def camera_settings(record):
    body = get(record, 2, default=b'')
    return {
        'camera_id': get(record, 1, 0),
        'name': get(body, 1, default=b'').decode('utf-8'),
        'mode': get(body, 12, 0, 0),
        'distance_m': single_float(body, 2),
        'fov_deg': single_float(body, 3),
        'min_distance_m': single_float(body, 5),
        'max_distance_m': single_float(body, 6),
    }


def set_scene_camera(data, op):
    schema(op, ('op', 'camera_id', 'distance_m', 'fov_deg'), ('op', 'camera_id'))
    if not any(name in op for name in ('distance_m', 'fov_deg')):
        raise ValueError('Provide distance_m or fov_deg')
    _, root = container(data)
    section = unique(root, 18, default=b'')
    record = select_record(section, 1, op['camera_id'], 'Camera template')
    before = camera_settings(record)
    if not before['name'] or before['mode'] not in (0, 2) or before['distance_m'] is None or before['fov_deg'] is None:
        raise ValueError('Unsupported existing camera template')
    updates = {}
    if 'distance_m' in op:
        distance = vector([op['distance_m'], 1, 1], 'Camera distance', positive=True)[0]
        old, near, far = (before[k] for k in ('distance_m', 'min_distance_m', 'max_distance_m'))
        if far != old or near is None or old <= 0 or not 0 < near <= far:
            raise ValueError('Uncalibrated camera distance and zoom range')
        if near == far:
            updates[5] = (5, distance)
        elif distance < near:
            raise ValueError('Camera distance cannot be less than its existing zoom minimum')
        updates.update({2: (5, distance), 6: (5, distance)})
    if 'fov_deg' in op:
        fov = vector([op['fov_deg'], 1, 1], 'Camera FOV', positive=True)[0]
        if not 0 < fov < 180:
            raise ValueError('Camera FOV must be between 0 and 180 degrees')
        updates[3] = (5, fov)
    body = patch_fields(get(record, 2), updates)
    changed = patch_fields(record, {2: (2, body)})
    return set_section(data, 18, replace_message(section, 1, record, changed)), {
        'before': before, 'after': camera_settings(changed),
    }


def point_settings(record, spawns):
    ident = get(record, 1, 0)
    return {
        'point_id': ident, 'name': get(record, 501, default=b'').decode('utf-8'),
        'position_m': read_vector(get(record, 2, default=b'')),
        'rotation_deg': read_vector(get(record, 3, default=b'')),
        'spawn': ident in spawns,
    }


def spawn_references(section):
    return {get(entry, 2, 0) for entry in vals(fields(get(section, 3, default=b'')), 2)}


def add_scene_points(data, op):
    schema(op, ('op', 'points'), ('op', 'points'))
    if not isinstance(op['points'], list) or not op['points']:
        raise ValueError('Provide at least one preset point')
    _, root = container(data)
    section = unique(root, 11)
    if section is None:
        raise ValueError('Calibrated level settings section required')
    points = get(section, 5, default=b'')
    spawns = spawn_references(section)
    existing = [point_settings(p, spawns) for p in vals(fields(points), 1)]
    ids = {p['point_id'] for p in existing}
    if len(ids) != len(existing) or None in ids or not spawns.issubset(ids):
        raise ValueError('Preset point identities or spawn references are inconsistent')
    names = {p['name'] for p in existing}
    records = []
    created = []
    next_id = max({0x40000000, *ids}) + 1
    for point in op['points']:
        schema(point, ('point_id', 'name', 'position_m', 'rotation_deg'), ('name', 'position_m'))
        name = point['name']
        if not isinstance(name, str) or not name.strip() or '\0' in name or name in names:
            raise ValueError('Preset point name must be unique and nonempty')
        while next_id in ids:
            next_id += 1
        ident = point.get('point_id', next_id)
        if type(ident) is not int or not 0x40000001 <= ident < 0x40400000 or ident in ids:
            raise ValueError('Preset point ID is already used or outside the calibrated range')
        ids.add(ident)
        names.add(name)
        position = vector(point['position_m'], 'Preset point position')
        rotation = vector(point.get('rotation_deg', [0, 0, 0]), 'Preset point rotation')
        record = (integer(1, ident) + msg(2, encode_vector(position)) + msg(3, encode_vector(rotation))
                  + text(501, name) + integer(502, 1))
        records.append(msg(1, record))
        created.append(point_settings(record, spawns))
    result = patch_fields(section, {5: (2, points + b''.join(records))})
    return set_section(data, 11, result), {'points': created}


def set_scene_point(data, op):
    schema(op, ('op', 'point_id', 'position_m', 'rotation_deg'), ('op', 'point_id'))
    changes = {number: vector(op[key], key) for key, number in (('position_m', 2), ('rotation_deg', 3)) if key in op}
    if not changes:
        raise ValueError('Provide position_m or rotation_deg for the preset point')
    _, root = container(data)
    section = unique(root, 11, default=b'')
    points = get(section, 5, default=b'')
    target = select_record(points, 1, op['point_id'], 'Preset point')
    spawns = spawn_references(section)
    before = point_settings(target, spawns)
    if not before['name'] or get(target, 502, 0) != 1:
        raise ValueError('Uncalibrated preset point record')
    updated = patch_vectors(target, changes)
    result = patch_fields(section, {5: (2, replace_message(points, 1, target, updated))})
    return set_section(data, 11, result), {'before': before, 'after': point_settings(updated, spawns)}


def terrain_header(record):
    origin = get(get(record, 3, default=b''), 1)
    if origin is None:
        raise ValueError('Terrain origin absent')
    return {
        'terrain_id': get(record, 1, 0),
        'name': get(get(record, 2, default=b''), 1, default=b'').decode('utf-8'),
        'origin_m': read_vector(origin), 'cell_m': CELL_METRES, 'layer_m': LAYER_METRES,
    }


def terrain_cell(raw, origin):
    cell = fields(raw)
    ident = unique(cell, 1, 0)
    if ident is None or not 0 <= ident <= 0xffffffff:
        raise ValueError('Invalid terrain cell index')
    x, z = ident & 0xffff, ident >> 16
    layers, material, water, path, slope = (unique(cell, number, 0, 0) for number in range(2, 7))
    return {
        'index': [x, z], 'center_xz_m': [origin[0] + CELL_METRES*x, origin[2] + CELL_METRES*z],
        'top_m': origin[1] + LAYER_METRES*layers, 'layers': layers, 'material': material,
        'water_layers': water, 'water_top_m': origin[1] + LAYER_METRES*(layers+water) if water else None,
        'path': path == 1, 'slope': slope,
    }


def terrain_settings(record):
    info = terrain_header(record)
    cells = [terrain_cell(raw, info['origin_m']) for raw in vals(fields(record), 4)]
    if len({tuple(cell['index']) for cell in cells}) != len(cells):
        raise ValueError('Ambiguous terrain cell indices')
    return {**info, 'cells': cells}


def set_terrain_cells(data, op):
    schema(op, ('op', 'terrain_id', 'version', 'mode', 'cells'), ('op', 'terrain_id', 'version', 'mode', 'cells'))
    if (op['version'], op['mode']) != ('7.2', 'beyond'):
        raise ValueError('Terrain writes support platform 7.2 in beyond mode')
    if not isinstance(op['cells'], list) or not op['cells']:
        raise ValueError('Provide a nonempty terrain change list')
    _, root = container(data)
    section = unique(root, 7, default=b'')
    record = select_record(section, 1, op['terrain_id'], 'Terrain')
    terrain = terrain_settings(record)
    current = {tuple(cell['index']): cell for cell in terrain['cells']}
    edits = {}
    for box in op['cells']:
        schema(box, ('index', 'to', 'layers', 'material', 'water_layers', 'path', 'slope'), ('index',))
        start, end = box['index'], box.get('to', box['index'])
        if any(not isinstance(pair, list) or len(pair) != 2 or
               any(type(i) is not int or not 0 <= i <= 0xffff for i in pair) for pair in (start, end)):
            raise ValueError('Cell index must be [X, Z] integers')
        (x0, x1), (z0, z1) = (sorted(axis) for axis in zip(start, end))
        if (x1-x0+1) * (z1-z0+1) > len(current):
            raise ValueError('Terrain edit extends past existing cells')
        changes = {}
        for key, number in (('layers', 2), ('water_layers', 4)):
            if key in box:
                if type(box[key]) is not int or not 0 <= box[key] <= 20:
                    raise ValueError('Terrain layer counts must be integers between 0 and 20')
                changes[number] = (0, box[key] or None)
        if 'material' in box:
            material = box['material']
            if not isinstance(material, str) or material not in TERRAIN_MATERIALS:
                raise ValueError('Uncalibrated terrain material')
            changes[3] = (0, TERRAIN_MATERIALS[material] or None)
        if 'path' in box:
            if type(box['path']) is not bool:
                raise ValueError('Terrain path must be boolean')
            changes[5] = (0, 1 if box['path'] else None)
        if 'slope' in box:
            slope = box['slope']
            if not isinstance(slope, str) or slope not in STRAIGHT_SLOPES:
                raise ValueError('Choose flat or a calibrated straight slope axis')
            changes[6] = (0, STRAIGHT_SLOPES[slope] or None)
        if not changes:
            raise ValueError('Specify a terrain cell change')
        for x in range(x0, x1+1):
            for z in range(z0, z1+1):
                key = (x, z)
                cell = current.get(key)
                if cell is None or key in edits:
                    raise ValueError('Terrain cells must exist and be selected once: ' + str(key))
                layer_count = box.get('layers', cell['layers'])
                water = box.get('water_layers', cell['water_layers'])
                slope = changes.get(6, (0, cell['slope']))[1] or 0
                road = box.get('path', cell['path'])
                if (not 1 <= layer_count+water <= 20 or cell['slope'] not in STRAIGHT_SLOPES.values()
                        or water and (road or slope) or slope and (road or layer_count < 2)):
                    raise ValueError('Unsupported combination of terrain layers, water, road and slope')
                edits[key] = changes
    output = []
    changes = []
    for number, wire, raw, encoded in fields(record):
        if number == 4 and wire == 2:
            before = terrain_cell(raw, terrain['origin_m'])
            patch = edits.get(tuple(before['index']))
            if patch is not None:
                changed = patch_fields(raw, patch)
                changes.append({'before': before, 'after': terrain_cell(changed, terrain['origin_m'])})
                encoded = msg(4, changed) if changed != raw else encoded
        output.append(encoded)
    newer = b''.join(output)
    return set_section(data, 7, replace_message(section, 1, record, newer)), {
        'terrain_id': op['terrain_id'], 'cells': changes, 'navigation': 'not_checked',
    }


def environment_settings(record):
    block = typed_record(record, 4, 70)
    body = get(get(block or b'', 75, default=b''), 1, default=b'')
    sky = get(body, 1, default=b'')
    name = get(get(typed_record(record, 4, 1) or b'', 11, default=b''), 1, default=b'')
    curved = any(24 <= n <= 57 and w == 2 for n, w, _, _ in fields(sky))
    lights = [get(raw, 2, 0) for raw in vals(fields(get(body, 2, default=b'')), 1)]
    return {
        'environment_id': get(record, 1, 0), 'name': name.decode('utf-8'),
        'hour': get(sky, 58 if curved else 6, 0, 0),
        'curves': curved, 'light_ids': lights,
    }


def set_fixed_environment_hour(data, op):
    schema(op, ('op', 'environment_id', 'hour'), ('op', 'environment_id', 'hour'))
    if type(op['hour']) is not int or not 0 <= op['hour'] <= 23:
        raise ValueError('Environment hour must be an integer from 0 to 23')
    _, root = container(data)
    section = unique(root, 15, default=b'')
    record = select_record(section, 1, op['environment_id'], 'Environment')
    if get(record, 2, 0) != 26:
        raise ValueError('Expected an environment configuration')
    before = environment_settings(record)
    block = typed_record(record, 4, 70)
    wrapper = get(block or b'', 75, default=b'')
    body = get(wrapper, 1, default=b'')
    sky = get(body, 1, default=b'')
    if before['curves'] or get(sky, 8) != b'' or get(sky, 3, 0, 0) != 0 or single_float(sky, 9) is None:
        raise ValueError('Only the calibrated fixed, curve-free sky can change its hour')
    sky = patch_fields(sky, {6: (0, op['hour'] or None)})
    body = patch_fields(body, {1: (2, sky)})
    wrapper = patch_fields(wrapper, {1: (2, body)})
    newer = replace_message(record, 4, block, patch_fields(block, {75: (2, wrapper)}))
    return set_section(data, 15, replace_message(section, 1, record, newer)), {
        'before': before, 'after': environment_settings(newer),
    }


def light_payload(record):
    block = typed_record(record, 4, 69)
    wrapper = get(block or b'', 74, default=b'')
    bundle = get(wrapper, 1, default=b'')
    point = get(bundle, 1, default=b'')
    settings = get(point, 51, default=b'')
    if get(record, 2, 0) != 27 or get(settings, 1, 0) != 3 or get(point, 52) is not None:
        return None
    return block, wrapper, bundle, point, settings


def light_settings(record):
    payload = light_payload(record)
    if payload is None:
        return None
    _, _, _, point, settings = payload
    name = get(get(typed_record(record, 4, 1) or b'', 11, default=b''), 1, default=b'')
    return {
        'light_id': get(record, 1, 0), 'name': name.decode('utf-8'),
        'position_m': read_vector(get(point, 3, default=b'')), 'range_m': single_float(point, 2),
        'radius_m': single_float(settings, 2), 'intensity': single_float(settings, 3),
    }


def set_point_light(data, op):
    values = {'range_m': 2, 'radius_m': 2, 'intensity': 3}
    schema(op, ('op', 'light_id', 'position_m', *values), ('op', 'light_id'))
    if not any(key in op for key in ('position_m', *values)):
        raise ValueError('Provide a point light change')
    _, root = container(data)
    section = unique(root, 15, default=b'')
    record = select_record(section, 1, op['light_id'], 'Point light')
    payload = light_payload(record)
    if payload is None:
        raise ValueError('Uncalibrated point light')
    before = light_settings(record)
    block, wrapper, bundle, point, settings = payload
    numbers = {}
    for key in values:
        if key in op:
            number = vector([op[key], 0, 0], key)[0]
            if number < 0 or (key != 'intensity' and number == 0):
                raise ValueError('Point light requires nonnegative intensity and positive distances')
            numbers[key] = number
    settings = patch_fields(settings, {values[key]: (5, number) for key, number in numbers.items() if key != 'range_m'})
    updates = {51: (2, settings)}
    if 'range_m' in numbers:
        updates[2] = (5, numbers['range_m'])
    point = patch_fields(point, updates)
    if 'position_m' in op:
        point = patch_vectors(point, {3: vector(op['position_m'], 'Point light position')})
    bundle = patch_fields(bundle, {1: (2, point)})
    wrapper = patch_fields(wrapper, {1: (2, bundle)})
    newer = replace_message(record, 4, block, patch_fields(block, {74: (2, wrapper)}))
    return set_section(data, 15, replace_message(section, 1, record, newer)), {
        'before': before, 'after': light_settings(newer),
    }


def add_point_light(data, op):
    from native_gameplay import config_name,config_payload,config_record,config_records,name_value,next_config_id,number,replace_payload
    from native_scene_edits import append_library_entries
    schema(op, ('op','environment_id','name','position_m','radius_m','range_m','intensity'),
           ('op','environment_id','name','position_m'))
    _, root = container(data)
    section,library = unique(root,15,default=b''),unique(root,6)
    if library is None:raise ValueError('Light creation requires a native resource library')
    sky = config_record(section,op['environment_id'],26)
    _,_,body = config_payload(sky,70,75)
    listing = get(body,2,default=b'')
    names = {config_name(r) for r in config_records(section) if get(r,2,0)==27}
    name = name_value(op['name'])
    if name in names:raise ValueError('Point light name must be unique')
    position = vector(op['position_m'],'Point light position')
    radius = number(op.get('radius_m',10),'Light radius')
    visibility = number(op.get('range_m',100),'Light range')
    intensity = number(op.get('intensity',3),'Light intensity')
    if radius<=0 or visibility<=0:raise ValueError('Point light range and radius must be positive')
    ident = next_config_id(section,1182793728)
    new_light = integer(1,ident)+integer(2,27)+msg(4,integer(1,1)+msg(11,text(1,name)))
    effect = integer(1,3)+flt(2,radius)+flt(3,intensity)
    point = flt(2,visibility)+msg(3,encode_vector(position))+msg(4)+msg(51,effect)
    new_light += msg(4,integer(1,69)+msg(74,msg(1,msg(1,point)+integer(2,1))))
    slot = max((get(r,1,0,0) for r in vals(fields(listing),1)),default=0)+1
    linked = listing+msg(1,integer(1,slot)+integer(2,ident))
    updated = replace_payload(sky,70,75,patch_fields(body,{2:(2,linked)}))
    section = replace_message(section,1,sky,updated)+msg(1,new_light)
    data = set_section(data,15,section)
    return set_section(data,6,append_library_entries(library,55,5300,[ident],create=True)), {
        'environment_id':op['environment_id'],'light':light_settings(new_light)}


def inspect_settings(root):
    level = unique(root, 11, default=b'')
    spawns = spawn_references(level)
    shared = vals(fields(unique(root, 15, default=b'')), 1)
    return {
        'cameras': [camera_settings(r) for r in vals(fields(unique(root, 18, default=b'')), 1)],
        'points': [point_settings(r, spawns) for r in vals(fields(get(level, 5, default=b'')), 1)],
        'terrains': [terrain_settings(r) for r in vals(fields(unique(root, 7, default=b'')), 1)],
        'environments': [environment_settings(r) for r in shared if get(r, 2, 0) == 26],
        'point_lights': [report for r in shared if get(r, 2, 0) == 27 and (report := light_settings(r))],
    }


SETTINGS_EDITS = {fn.__name__: fn for fn in (
    set_scene_camera, set_scene_point, add_scene_points, set_terrain_cells, set_fixed_environment_hour, set_point_light,
    add_point_light,
)}
