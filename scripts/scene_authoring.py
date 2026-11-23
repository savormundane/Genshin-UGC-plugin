"""Select native models and build a standalone static Qianxing scene."""
import argparse
import json
import os
from pathlib import Path

from authoring_io import finish, output_directory, resolve, schema, sha, write_json
from native_scene import OBJECT_ID_END, OBJECT_ID_START, read_gia, static_gia, static_objects, vector

VERSION = '7.2'
MODE = 'beyond'


def scene_spec(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    spec = json.loads(raw.decode('utf-8-sig'))
    schema(spec, ('schema', 'version', 'mode', 'catalogues', 'offset_m', 'objects'),
           ('version', 'mode', 'objects'), version=1)
    catalogues = spec.get('catalogues', [])
    if not isinstance(catalogues, list) or any(not isinstance(p, str) or not p for p in catalogues):
        raise ValueError('Scene catalogues must be paths relative to the scene specification')
    if (spec['version'], spec['mode']) != (VERSION, MODE):
        raise ValueError('Static scene build supports platform 7.2 in beyond mode')
    return spec, {str(path): sha(raw)}


def build(path, out):
    from resource_catalogue import catalogue

    path = Path(path).resolve()
    spec, inputs = scene_spec(path)
    discovered = catalogue(spec['version'], [resolve(path.parent, p) for p in spec.get('catalogues', [])],
                           include_model_candidates=True)
    inputs.update(discovered['inputs'])
    models = {row['id']: row for row in discovered['resources'] if row['type'] == 'model'}
    offset = vector(spec.get('offset_m', [0, 0, 0]), 'Scene offset')
    objects = spec['objects']
    if not isinstance(objects, list) or not 1 <= len(objects) <= OBJECT_ID_END - OBJECT_ID_START + 1:
        raise ValueError('Provide a nonempty scene that fits the ordinary object ID range')

    layout = {}
    for obj in objects:
        schema(obj, ('key', 'name', 'template_id', 'position_m', 'rotation_deg', 'scale', 'size_m'),
               ('key', 'name', 'template_id', 'position_m'))
        key, name, template = obj['key'], obj['name'], obj['template_id']
        if not isinstance(key, str) or not key.strip() or key in layout:
            raise ValueError('Scene layout keys must be unique nonempty strings')
        if not isinstance(name, str) or not name.strip() or '\0' in name:
            raise ValueError('Scene object name must be nonempty')
        model = models.get(template) if type(template) is int else None
        if model is None:
            raise ValueError('Unknown native model template: ' + repr(template))
        if model.get('selection') != 'native_verified':
            raise ValueError('Native static record evidence required for model ' + str(template))
        if model['mode'] not in (MODE, 'both'):
            raise ValueError('Model mode does not match the scene target: ' + str(template))
        position = vector(obj['position_m'], 'Position for ' + key)
        position = vector([p + d for p, d in zip(position, offset)], 'World position for ' + key)
        rotation = vector(obj.get('rotation_deg', [0, 0, 0]), 'Rotation for ' + key)
        if 'size_m' in obj:
            dims = model['dimensions']
            if 'scale' in obj or dims is None or not model.get('dimensions_verified') or min(dims) <= 0:
                raise ValueError('Measured positive model dimensions and no scale are required for size_m: ' + key)
            size = vector(obj['size_m'], 'Size for ' + key, positive=True)
            scale = vector([value / basis for value, basis in zip(size, dims)], 'Scale for ' + key, positive=True)
        else:
            scale = vector(obj.get('scale', [1, 1, 1]), 'Scale for ' + key, positive=True)
        layout[key] = {
            'name': name, 'template_id': template, 'static': True,
            'position_m': position, 'rotation_deg': rotation, 'scale': scale,
        }
    ordered = [
        (key, dict(layout[key], record_id=OBJECT_ID_START + index))
        for index, key in enumerate(sorted(layout))
    ]
    selected = {obj['template_id'] for obj in layout.values()}
    with output_directory(out) as stage:
        gia = stage / 'scene.gia'
        expected = [record for _, record in ordered]
        gia.write_bytes(static_gia(expected))
        actual = read_gia(gia.read_bytes(), static_only=True)
        if actual != expected:
            raise ValueError('Static GIA readback differs from the scene layout')
        write_json(stage / 'scene.json', spec)
        write_json(stage / 'scene-resources.json', {
            'schema': 1, 'version': spec['version'], 'mode': spec['mode'],
            'identity_scope': 'output_gia',
            'objects': [dict(record, key=key) for (key, _), record in zip(ordered, actual)],
            'models': [
                {**{k: v for k, v in models[ident].items() if k not in ('source', 'dimensions_source')},
                 'source_sha256': models[ident]['source']['sha256']}
                for ident in sorted(selected)
            ],
        })
        (stage / 'IMPORT.md').write_text(
            '# 导入 3D 静态场景\n\n'
            '在 7.2 超限模式的千星奇域编辑器中，通过「资产导入导出管理」加载 scene.gia，'
            '转存所选资产。检查模型、摆放、旋转和尺寸，按需要保存。'
            '导入后以实际存档中的对象身份为准。\n\n'
            '可编辑的布局见 scene.json。将它放回原场景配置所在目录，'
            '或按新的目录调整 catalogues 相对路径，再生成到新目录。'
            'scene-resources.json 中的记录编号只用于本 GIA。原生导入与游戏表现待核对。\n',
            encoding='utf-8', newline='\n',
        )
        return finish(
            stage, inputs, kind='native-static-scene', specification=str(path),
            version=spec['version'], mode=spec['mode'], object_count=len(actual),
            native_templates=sorted(selected), coordinates='native_world_xyz_y_up',
            checks={'readback': 'passed', 'editor': 'not_checked', 'host': 'not_checked'},
        )


def capture_catalogue(source, out, version, mode):
    """Register witnessed platform template IDs from ordinary static objects."""
    from platform_profiles import profile

    profile(version, mode)
    source = Path(source).resolve()
    out = Path(out).resolve()
    blob = source.read_bytes()
    records = {}
    for obj in static_objects(blob):
        records.setdefault(obj['template_id'], obj)
    if not records:
        raise ValueError('The export contains no ordinary static object with a platform template ID')
    path = (Path(os.path.relpath(source, out.parent)).as_posix()
            if source.drive == out.drive else source.as_posix())
    provenance = {'path': path, 'sha256': sha(blob)}
    result = {
        'schema': 2, 'version': version, 'resources': [
            {'type': 'model', 'id': ident, 'name': obj['name'], 'mode': mode,
             'category': '静态物件', 'dimensions': None, 'dependencies': None,
             'source': provenance, 'selection': 'native_verified'}
            for ident, obj in sorted(records.items())
        ],
    }
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return {'status': 'passed', 'templates': sorted(records), 'count': len(records), 'output': str(out),
            'input_sha256': provenance['sha256'], 'target_metadata': 'caller_declared'}



def inspect(path, terrain_id=None):
    from level_inventory import container, fields, unique, vals
    from native_core import get
    from native_scene import ordinary_object, typed_record
    from native_scene_edits import describe_decoration
    from native_scene_settings import inspect_settings
    from project_index import build_scene

    data = Path(path).read_bytes()
    header, root = container(data)
    result = {'schema': 1, 'input_sha256': sha(data), 'editor': 'not_checked', 'host': 'not_checked'}
    if header[3] == 3:
        if terrain_id is not None:
            raise ValueError('Terrain inspection requires a GIL')
        scene = build_scene(data)
        return {**result, 'format': 'gia', 'objects': read_gia(data),
                'spatial_objects': [row for row in scene['objects'] if row['kind'] == 'gia_resource'],
                'spatial_unresolved': scene['unresolved']}
    if header[1:4] != (1, 806, 2):
        raise ValueError('Scene inspection requires a calibrated GIL or GIA')
    records = vals(fields(unique(root, 5, default=b'')), 1)
    objects = [obj for raw in records if (obj := ordinary_object(raw))]
    interactive = []
    for record in records:
        trigger = typed_record(record, 7, 5)
        if trigger is None:
            continue
        trigger_ids = [get(raw, 1, 0) for raw in vals(fields(get(trigger, 15, default=b'')), 1)]
        if trigger_ids:
            name = typed_record(record, 5, 1)
            title = get(get(name or b'', 11, default=b''), 1, default=b'').decode('utf-8')
            interactive.append({'entity_id': get(record, 1, 0), 'name': title, 'trigger_ids': trigger_ids,
                                'has_graph_component': typed_record(record, 6, 3) is not None})
    decorations = []
    for number, wire, raw, _ in fields(unique(root, 27, default=b'')):
        if number not in (1, 2) or wire != 2 or get(raw, 3, 0) != 1:
            continue
        owner = typed_record(raw, 4, 40)
        if owner is not None and get(get(owner, 50, default=b''), 502, 0) is not None:
            decorations.append(dict(describe_decoration(raw), section=4 if number == 1 else 5))
    settings = inspect_settings(root)
    if terrain_id is not None:
        settings['terrains'] = [item for item in settings['terrains'] if item['terrain_id'] == terrain_id]
        if len(settings['terrains']) != 1:
            raise ValueError('Terrain selector must match exactly once')
    else:
        for item in settings['terrains']:
            item['cell_count'] = len(item.pop('cells'))
    scene = build_scene(data)
    return {**result, 'format': 'gil', 'objects': objects, 'collision_triggers': interactive,
            'decorations': decorations, 'spatial_objects': [row for row in scene['objects']
            if row['kind'] in ('entity', 'template', 'decoration')], 'spatial_unresolved': scene['unresolved'], **settings}


def preview(path, template_id, out):
    """Draw scale and local position as orthographic whitebox proxies."""
    from PIL import Image, ImageDraw
    from native_scene_edits import WHITEBOX

    report = inspect(path)
    if report['format'] != 'gil':
        raise ValueError('Whitebox preview requires a GIL template')
    parts = [part for part in report['decorations']
             if part['section'] == 4 and part['owner_id'] == template_id
             and part['model_id'] in WHITEBOX and min(part['scale']) > 0]
    if not parts:
        raise ValueError('Template has no supported whitebox decorations')
    with output_directory(out) as stage:
        for name, axes in (('top', (0, 2)), ('side', (0, 1))):
            image = Image.new('RGB', (640, 480), '#20252E')
            draw = ImageDraw.Draw(image)
            low = [min(p['position_m'][axis]-p['scale'][axis]/2 for p in parts) for axis in axes]
            high = [max(p['position_m'][axis]+p['scale'][axis]/2 for p in parts) for axis in axes]
            # Separate positions from widths in pixel space so small but valid
            # proxies do not collapse to zero extent near a large coordinate.
            zoom = min(580 / max(high[0]-low[0], max(p['scale'][axes[0]] for p in parts)),
                       400 / max(high[1]-low[1], max(p['scale'][axes[1]] for p in parts)))
            for part in parts:
                x, y = (part['position_m'][axis] for axis in axes)
                w, h = (part['scale'][axis] * zoom for axis in axes)
                cx, cy = 30 + (x-low[0])*zoom, 440 - (y-low[1])*zoom
                box = (cx-w/2, cy-h/2, cx+w/2, cy+h/2)
                shape = draw.ellipse if part['model_id'] == 10009002 else draw.rectangle
                shape(box, fill=part['color_rgb'] or '#9AABC3', outline='white')
                draw.text((cx+2, cy+2), str(part['decoration_id']), fill='white', stroke_width=1, stroke_fill='black')
            draw.text((18, 16), f'{name} projection | native metres | local positions and scales', fill='white')
            image.save(stage / (name + '.png'))
        return finish(stage, {str(Path(path).resolve()): report['input_sha256']}, kind='whitebox-preview',
                      template_id=template_id, parts=len(parts), scope='axis_aligned_part_proxies',
                      editor='not_checked', host='not_checked')


def export_whitebox(path, template_id, out):
    """Export the shape dependencies of an empty-model GIL template."""
    from level_inventory import container, fields, unique, vals
    from native_assets import primitive_group_gia
    from native_core import get
    from native_scene import GIL_HEADER, read_templates, typed_record
    from native_scene_edits import WHITEBOX, decoration_links, describe_decoration, select_record

    source=Path(path).resolve()
    raw=source.read_bytes()
    header,root=container(raw)
    if header[1:4]!=GIL_HEADER:raise ValueError('Whitebox export requires a calibrated GIL')
    template=select_record(unique(root,4,default=b''),1,template_id,'Whitebox template')
    template_info=read_templates(root).get(template_id)
    if template_info is None or get(template,2,0)!=10005018:
        raise ValueError('Select a whitebox composition with the empty-model base')
    transform=template_info['transform']
    if transform['scale']!=[1,1,1] or any(transform['position_m']+transform['rotation_deg']):
        raise ValueError('Whitebox export requires an identity transform on the empty-model base')
    _,ids=decoration_links(template,4)
    section=unique(root,27,default=b'')
    parts,dependencies=[],[]
    for ident in ids:
        part=select_record(section,1,ident,'Whitebox decoration')
        detail=describe_decoration(part)
        if detail['model_id'] not in WHITEBOX or detail['owner_id']!=template_id:
            raise ValueError('Whitebox export requires all parts to be calibrated native shapes attached to this template')
        geometry=get(typed_record(part,5,1),11)
        colour=get(typed_record(part,5,22) or b'',32)
        if colour is None or get(colour,3,0) is None or min(detail['scale'])<=0:
            raise ValueError('Whitebox part requires a native ARGB colour and positive scale')
        parts.append((detail['model_id'],geometry,colour))
        dependencies.append({'resource_id':9+len(parts),**detail})
    if not parts:raise ValueError('Select a template with at least one whitebox part')
    name=template_info['name']
    artifact=primitive_group_gia(name,parts)
    _,units=container(artifact)
    group=unique(units,1);related=vals(units,2)
    loc=lambda record:get(record,4,0)
    links=[loc(link) for link in vals(fields(group),2)]
    actual={loc(get(unit,1)):get(get(unit,21),1) for unit in related}
    if links!=list(actual) or len(links)!=len(parts) or get(group,3)!=name.encode('utf-8'):
        raise ValueError('Generated whitebox GIA dependency closure differs')
    for link,(model,pose,colour) in zip(links,parts):
        body=actual[link]
        if (get(body,2,0),get(typed_record(body,5,1),11),get(typed_record(body,5,22),32))!=(model,pose,colour):
            raise ValueError('Generated whitebox part readback differs')
    with output_directory(out) as stage:
        (stage/'whitebox.gia').write_bytes(artifact)
        write_json(stage/'whitebox-resources.json',{'template_id':template_id,'parts':dependencies})
        return finish(stage,{str(source):sha(raw)},kind='whitebox-geometry-gia',template_id=template_id,
                      part_count=len(parts),editor='not_checked',host='not_checked')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    build_command = commands.add_parser('build')
    build_command.add_argument('spec')
    build_command.add_argument('--out', required=True)
    catalogue_command = commands.add_parser('catalogue')
    catalogue_command.add_argument('sample')
    catalogue_command.add_argument('--version', required=True)
    catalogue_command.add_argument('--mode', choices=['classic', 'beyond'], required=True)
    catalogue_command.add_argument('--out', required=True)
    inspect_command = commands.add_parser('inspect')
    inspect_command.add_argument('input')
    inspect_command.add_argument('--terrain-id', type=int)
    preview_command = commands.add_parser('preview')
    preview_command.add_argument('input')
    preview_selection = preview_command.add_mutually_exclusive_group()
    preview_selection.add_argument('--template-id', type=int)
    preview_selection.add_argument('--before')
    preview_command.add_argument('--out', required=True)
    prefab_command = commands.add_parser('export-whitebox')
    prefab_command.add_argument('input')
    prefab_command.add_argument('--template-id', required=True,type=int)
    prefab_command.add_argument('--out',required=True)
    args = parser.parse_args(argv)
    if args.operation == 'build':
        result = build(args.spec, args.out)
    elif args.operation == 'catalogue':
        result = capture_catalogue(args.sample, args.out, args.version, args.mode)
    elif args.operation == 'inspect':
        result = inspect(args.input, args.terrain_id)
    elif args.operation == 'preview' and args.template_id is not None:
        result = preview(args.input, args.template_id, args.out)
    elif args.operation == 'preview':
        from scene_preview import preview as preview_scene
        result = preview_scene(args.input, args.out, before=args.before)
    else:
        result = export_whitebox(args.input,args.template_id,args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
