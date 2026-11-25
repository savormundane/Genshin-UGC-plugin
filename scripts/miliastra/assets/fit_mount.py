"""Assemble fitted rectangle data and an identically bound software preview."""

from authoring_io import PLUGIN, sha_file, write_json
from miliastra.assets.pipeline import lua

RENDERER = PLUGIN / 'scripts/runtime_rectangle_mount.lua'
PLATFORMS = ('KEYBOARD', 'TOUCHSCREEN', 'CONTROLLER_CONSOLE', 'CONTROLLER_MOBILE')


def deliver(stage, layers, mount, inputs):
    data = [
        (stage / row['name'] / 'data.lua').read_text(encoding='utf-8').strip()
        for row in layers
    ]
    inputs[str(RENDERER)] = sha_file(RENDERER)
    source = stage / 'mounted.lua'
    source.write_text(
        '-- Set template_index to the rectangular image template in the target level.\n'
        + 'local MOUNT = ' + lua(mount) + '\n'
        + 'local LAYERS = {\n'
        + ''.join('(function()\n' + code + '\nend)(),\n' for code in data)
        + '}\n'
        + RENDERER.read_text(encoding='utf-8'),
        encoding='utf-8',
        newline='\n',
    )
    report = {'script': source.name, 'sha256': sha_file(source), **mount,
              'mount_point': 'client container', 'template_kind': 'rectangular image'}
    # The project declares one local software rectangle. Its bitmap identity
    # is defined by the pinned renderer and is not a template ID claim.
    canvas = 'pc-16-9'
    box = {'scale': {'x': 1, 'y': 1, 'z': 1}, 'rotation': {'x': 0, 'y': 0, 'z': 0},
           'anchorMin': {'x': 0.5, 'y': 0.5}, 'anchorMax': {'x': 0.5, 'y': 0.5},
           'offset': {'x': 0, 'y': 0}, 'pivot': {'x': 0.5, 'y': 0.5},
           'size': {'x': mount['width'], 'y': mount['height']}}
    fullscreen = {**box, 'anchorMin': {'x': 0, 'y': 0}, 'anchorMax': {'x': 1, 'y': 1},
                  'size': {'x': 0, 'y': 0}}
    root = {'id': 'canvas', 'kind': 'server-container', 'name': 'Canvas',
            'transformByPlatform': dict.fromkeys(PLATFORMS, fullscreen)}
    container = {'id': 'fit-root', 'kind': 'container', 'name': 'Fitted image',
                 'transformByPlatform': dict.fromkeys(PLATFORMS, box), 'children': []}
    tile = {'id': 'fit-tile', 'kind': 'image', 'name': 'Fitted rectangle',
            'guid': mount['template_index'], 'imageSource': 'StaticReference',
            'imageId': 100001, 'imageType': 'Stretch',
            'transformByPlatform': dict.fromkeys(PLATFORMS, box), 'children': []}
    server = 'server-control-template'
    client = 'client-control-template'
    write_json(stage / 'beyond-project.json', {
        'format': 'qxqy-simulator-save', 'version': 4,
        'activeAssetType': server,
        'assets': {
            'server': {'layoutSchemaVersion': 2, 'canvasId': canvas, 'meta': {'assetType': server},
                       'root': {**root, 'children': [container]}, 'selectedId': container['id']},
            'client': {'layoutSchemaVersion': 2, 'canvasId': canvas, 'meta': {'assetType': client},
                       'root': {**root, 'children': [tile]}, 'selectedId': tile['id']},
        },
    })
    count = sum(row['controls'] for row in layers)
    write_json(stage / 'beyond.json', {
        'schema': 2, 'project': 'beyond-project.json',
        'scripts': [{'source': source.name, 'sha256': report['sha256'],
                     'controlId': container['id'], 'controlAsset': server, 'path': 'mounted'}],
        'case': {'format': 'qxqy-autotest', 'version': 1, 'name': 'Fitted rectangles',
                 'events': [], 'asserts': [{'kind': 'log', 'contains': f'已创建 {count} 个拟合矩形。'}]},
    })
    return {**report, 'preview_spec': 'beyond.json', 'preview_binding': 'explicit_software_template'}
