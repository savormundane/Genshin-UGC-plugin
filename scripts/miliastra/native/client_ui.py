"""Append calibrated client templates to a level with an existing client UI."""
from itertools import islice
import json

from authoring_io import resolve, schema, sha
from level_authoring import (bind_script, client_control_kind, control, inspect_bindings, integer, kind_meta, msg,
                             register_script, reverse_meta, set_section, stream, template_meta, vi, with_template_alias)
from level_inventory import container, fields, unique, vals
from miliastra.native.core import get, replace_message
from miliastra.native.scene import GIL_HEADER, vector
from miliastra.native.scene_edits import one, patch_fields


def append_client_ui(data, op, base):
    required = ('op', 'source', 'mapping', 'mount_guid', 'container', 'button')
    schema(op, (*required, 'templates_as', 'asset_data'), required)
    header, root = container(data)
    if header[1:4] != GIL_HEADER:
        raise ValueError('Client UI append requires a calibrated GIL container')
    section = unique(root, 9, default=b'')
    records = vals(fields(section), 502)
    library = one((r for r in records if any((get(meta, 501, 0), get(meta, 502, 0)) == (11, 88)
                    and get(meta, 21) is not None for meta in vals(fields(r), 502))), 'Client prototype library')
    library_id = get(library, 501, 0)
    registry = unique(fields(section), 501)
    if registry is None or stream(registry).count(library_id) != 1:
        raise ValueError('Client prototype library must appear once in the packed UI registry')
    children = unique(fields(library), 503, default=b'')
    listed = stream(children)
    actual = [get(r, 501, 0) for r in records if get(r, 504, 0) == library_id]
    if len(listed) != len(set(listed)) or set(listed) != set(actual):
        raise ValueError('Client prototype library children differ from their parent references')
    mount = op['mount_guid']
    if type(mount) is not int:
        raise ValueError('An exact client container GUID is required')
    target = one((r for r in records if get(r, 501, 0) == mount), 'Client script mount')
    if client_control_kind(fields(target)) != 'container':
        raise ValueError('Client script mount must be a calibrated client container')

    before = inspect_bindings(data)
    names = {row['name'] for row in before['templates']}
    used_ids = [r['guid'] for r in before['controls']] + [s['id'] for s in before['scripts']]
    start = max(ident for ident in [0x40001000, *used_ids] if type(ident) is int) + 1
    ids = list(islice((ident for ident in range(start, 0x7fffffff + 1) if vi(ident) not in data), 5))
    if len(ids) != 5:
        raise ValueError('Client UI identity range exhausted')
    used_slots = (get(get(meta, 12, default=b''), 501, 0, 0) for r in records for meta in vals(fields(r), 502)
                  if (get(meta, 501, 0), get(meta, 502, 0)) == (2, 6))
    first_slot = max(used_slots, default=0) + 1
    if not 0 < first_slot < 0x7fffffff:
        raise ValueError('Client template index range exhausted')

    templates, added = {}, []
    for index, kind in enumerate(('container', 'button')):
        item = op[kind]
        schema(item, ('name', 'size'), ('name', 'size'))
        name, size = item['name'], item['size']
        if not isinstance(name, str) or not name.strip() or '\0' in name or name in names:
            raise ValueError(f'Provide an unused client template name for {kind}')
        if not isinstance(size, list) or len(size) != 2:
            raise ValueError(f'Provide two positive float32 dimensions for {kind}')
        width, height, _ = vector([*size, 1], f'{kind} size', positive=True)
        names.add(name)
        template, entry = ids[2*index:2*index+2]
        slot = msg(502, kind_meta(first_slot+index))
        prototype = control(template, name, kind, width, height) + slot + msg(502, reverse_meta([entry]))
        member = control(entry, name, kind, width, height) + slot + msg(502, template_meta(template)) + integer(504, library_id)
        added.extend((msg(502, prototype), msg(502, member)))
        registry += vi(template)
        children += vi(entry)
        templates[kind] = {'name': name, 'template_guid': template, 'entry_guid': entry}
    section = replace_message(section, 502, library, patch_fields(library, {503: (2, children)}))
    section = patch_fields(section, {501: (2, registry)}) + b''.join(added)

    source = resolve(base, op['source'])
    raw = source.read_bytes()
    alias = op.get('templates_as', 'qx_templates')
    code = with_template_alias(raw, alias, {kind: item['template_guid'] for kind, item in templates.items()})
    asset_info = {}
    if 'asset_data' in op:
        from miliastra.assets.pipeline import lua

        if alias == 'qx_assets':
            raise ValueError('Template alias conflicts with qx_assets')
        data_bytes = resolve(base, op['asset_data']).read_bytes()
        packed = json.loads(data_bytes.decode('utf-8-sig'))
        fields_required = ('schema', 'kind', 'assets')
        schema(packed, fields_required, fields_required, version=1)
        if packed['kind'] != 'asset-batch-data' or not isinstance(packed['assets'], dict) or not packed['assets']:
            raise ValueError('asset_data must be data.json from assets batch generate')
        code = ('local qx_assets = ' + lua(packed['assets']) + '\n').encode('utf-8') + code
        asset_info = {'asset_data_sha256': sha(data_bytes), 'asset_alias': 'qx_assets'}
    result, script_id = register_script(set_section(data, 9, section), op['mapping'], code, script_id=ids[4])
    result = bind_script(result, mount, script_id)
    inspect = inspect_bindings(result)
    observed = {(row['kind'], row['template_guid'], row['entry_guid']) for row in inspect['templates']
                if row['reciprocal_reference_verified']}
    if any((kind, item['template_guid'], item['entry_guid']) not in observed for kind, item in templates.items()):
        raise ValueError('Client template reciprocal binding readback differs')
    if not any(row['control_guid'] == mount and row['script_guid'] == script_id and row['mapping_found']
               for row in inspect['script_bindings']):
        raise ValueError('Client script mount readback differs')
    return result, {'templates': templates, 'library_guid': library_id, 'mount_guid': mount,
                    'script_guid': script_id, 'mapping': op['mapping'], 'templates_as': alias,
                    'source_sha256': sha(raw), **asset_info}
