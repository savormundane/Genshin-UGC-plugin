"""Draw calibrated world placements and compare two GIL layouts at one scale."""

import math
from pathlib import Path

from authoring_io import finish, output_directory, write_json
from miliastra.native.scene_edits import WHITEBOX
from project_index import build_scene


def scene_rows(path):
    report = build_scene(path.read_bytes())
    if report['artifacts']['level']['format'] != 'gil':
        raise ValueError('Scene layout preview requires a GIL')
    rows = {}
    for obj in report['objects']:
        if obj['kind'] != 'entity':
            continue
        key = obj['key']
        if key in rows:
            raise ValueError('Ambiguous scene entity: ' + key)
        row = rows[key] = {name: obj[name] for name in ('id', 'key', 'name')}
        spatial = obj.get('spatial')
        if not spatial or spatial['transform']['space'] != 'world':
            row['transform'] = None
            continue
        transform = row['transform'] = spatial['transform']
        row['model'] = spatial['model']
        row['template'] = spatial['template']
        rx, ry, rz = transform['rotation_deg']
        if spatial['model']['id'] in WHITEBOX and min(transform['scale']) > 0 and rx % 360 == rz % 360 == 0:
            x, y, z = transform['scale']
            theta = math.radians(ry % 360)
            s, c = abs(math.sin(theta)), abs(math.cos(theta))
            row['outline_m'] = [c * x + s * z, y, s * x + c * z]
            row['outline_source'] = 'unit_whitebox_proxy'
    return rows, report


def coverage(rows, report):
    positioned = sum(bool(row['transform']) for row in rows.values())
    outlines = sum('outline_m' in row for row in rows.values())
    return {'scene_index': report['checks']['scene_index']['status'],
            'spatial_coverage': (report['checks']['spatial_coverage']['status']
                                 if positioned == len(rows) else 'not_checked'),
            'indexed_entities': len(rows), 'positioned_entities': positioned,
            'without_world_position': len(rows) - positioned,
            'whitebox_outlines': outlines, 'position_markers_only': positioned - outlines,
            'unresolved_records': len(report['unresolved']), 'issues': len(report['issues']),
            'complete_reference_index': report['complete_reference_index']}


def render(path, axes, current, previous, changes):
    from PIL import Image, ImageDraw

    points = [r for r in (*current.values(), *previous.values()) if r['transform']]
    size = (1100, 760)
    image = Image.new('RGB', size, '#151B25')
    draw = ImageDraw.Draw(image)
    margin = 76
    low = [min(r['transform']['position_m'][axis] - r.get('outline_m', (0, 0, 0))[axis] / 2
               for r in points) for axis in axes]
    high = [max(r['transform']['position_m'][axis] + r.get('outline_m', (0, 0, 0))[axis] / 2
                for r in points) for axis in axes]
    scale = min((size[i] - 2 * margin) / max(1, high[i] - low[i]) for i in (0, 1))
    middle = [(lo + hi) / 2 for lo, hi in zip(low, high)]

    def point(row):
        xyz = row['transform']['position_m']
        return (size[0] / 2 + (xyz[axes[0]] - middle[0]) * scale,
                size[1] / 2 - (xyz[axes[1]] - middle[1]) * scale)

    focused = {key: kinds for key, kinds in changes.items() if 'unresolved' not in kinds}
    for key in sorted(focused.keys() & current.keys() & previous.keys()):
        if 'moved' in focused[key]:
            draw.line((point(previous[key]), point(current[key])), fill='#D0A862', width=2)
    for old, rows in ((True, previous), (False, current)):
        for key, row in sorted(rows.items()):
            if not row['transform'] or old and key not in focused:
                continue
            x, y = point(row)
            kinds = focused.get(key, ())
            colour = ('#E58291' if 'removed' in kinds else '#728096') if old else (
                '#71DABB' if 'added' in kinds else '#FFC971' if kinds else '#93C3EF')
            if 'outline_m' in row:
                w, h = (max(2, row['outline_m'][axis] * scale / 2) for axis in axes)
                draw.rectangle((x-w, y-h, x+w, y+h), outline=colour, width=2)
            draw.ellipse((x-2, y-2, x+2, y+2), fill=colour)
            if (not old and (kinds or len(current) <= 24) or 'removed' in kinds):
                draw.text((x+5, y-5), str(row['id']), fill=colour)
    view = 'Top | X right, Z up' if axes[1] == 2 else 'Side | X right, Y up'
    draw.text((24, 20), f'{view} | {scale:.4g} px per metre', fill='white')
    draw.text((24, 42), 'Outline: scaled unit whitebox proxy   Dot: indexed native origin', fill='#B9CADF')
    if previous:
        draw.text((24, size[1]-29), 'Green: added   Amber: changed   Rose: removed   Grey: previous', fill='#B9CADF')
    image.save(path)
    return {'min_m': low, 'max_m': high, 'pixels_per_metre': scale, 'axes': ['XYZ'[i] for i in axes],
            'image_size_px': list(size)}


def preview(path, out, *, before=None):
    path = Path(path).resolve()
    current, report = scene_rows(path)
    inputs = {str(path): report['artifacts']['level']['sha256']}
    previous = {}
    old_report = None
    changes = {}
    if before is not None:
        before = Path(before).resolve()
        previous, old_report = scene_rows(before)
        inputs[str(before)] = old_report['artifacts']['level']['sha256']
        for key in sorted(current.keys() | previous.keys()):
            old, new = previous.get(key), current.get(key)
            if old is not None and not old['transform'] or new is not None and not new['transform']:
                kinds = ['unresolved']
            elif old is None:
                kinds = ['added']
            elif new is None:
                kinds = ['removed']
            else:
                kinds = [kind for field, kind in (('position_m', 'moved'), ('rotation_deg', 'rotated'),
                                                  ('scale', 'resized'))
                         if old['transform'][field] != new['transform'][field]]
                if old['model'] != new['model'] or old['template'] != new['template']:
                    kinds.append('model_changed')
                if old['name'] != new['name']:
                    kinds.append('renamed')
            if kinds:
                changes[key] = kinds
    if not any(r['transform'] for r in (*current.values(), *previous.values())):
        raise ValueError('Scene has no calibrated world placements to draw')

    scope = 'indexed_world_positions_and_whitebox_bound_proxies'
    coverage_report = {'current': coverage(current, report),
                       'before': coverage(previous, old_report) if old_report else None}
    with output_directory(out) as stage:
        views = {name: render(stage / f'{name}.png', axes, current, previous, changes)
                 for name, axes in (('top', (0, 2)), ('side', (0, 1)))}
        write_json(stage / 'layout.json', {
            'schema': 1, 'basis': 'native_entity_key', 'views': views, 'objects': list(current.values()),
            'unresolved': report['unresolved'], 'issues': report['issues'],
            'before_unresolved': old_report['unresolved'] if old_report else [],
            'before_issues': old_report['issues'] if old_report else [],
            'changes': [{'key': key, 'kinds': kinds, 'before': previous.get(key), 'after': current.get(key)}
                        for key, kinds in changes.items()],
            'scope': scope, 'coverage': coverage_report, 'editor': 'not_checked', 'host': 'not_checked',
        })
        return finish(stage, inputs, kind='scene-preview', views=views,
                      objects=coverage_report['current']['positioned_entities'],
                      changes=len(changes), scope=scope, coverage=coverage_report,
                      editor='not_checked', host='not_checked')
