"""Resolve existing UI bindings and attach reviewed Lua to a calibrated GIL."""

from authoring_io import read_json, resolve, schema, sha
from level_authoring import (
    bind_script,
    client_control_kind,
    inspect_bindings,
    register_script,
    ui_records,
)
from level_inventory import calibrated_container, unique


def _select(rows, selector, identity, label):
    if type(selector) is int:
        matches = [row for row in rows if row[identity] == selector]
    elif isinstance(selector, str) and selector.strip():
        matches = [row for row in rows if row['name'] == selector]
    else:
        raise ValueError(f'{label}须用准确名称或整数标识')
    if len(matches) != 1:
        raise ValueError(f'{label}须唯一匹配，实际找到 {len(matches)} 个。请在工程索引中核对标识。')
    return matches[0]


def resolve_mount(data, control, template=None):
    """Resolve identity and kind from GIL bytes without interpreting bitmap content."""
    calibrated_container(data)
    bindings = inspect_bindings(data)
    if bindings['diagnostics']:
        raise ValueError('关卡界面绑定回读失败：' + repr(bindings['diagnostics']))
    records = {unique(record, 501, 0): record for record in ui_records(data)}
    target = _select(bindings['controls'], control, 'guid', '挂载控件')
    target_id = target['guid']
    if (
        client_control_kind(records[target_id]) != 'container'
        or any(target_id in (row['entry_guid'], row['template_guid']) for row in bindings['templates'])
    ):
        raise ValueError('挂载目标须为已识别的客户端容器控件')
    result = {'gil_sha256': sha(data), 'control_guid': target_id, 'control_name': target['name']}
    if template is not None:
        image = _select(bindings['templates'], template, 'template_guid', '图片模板')
        index = image['instantiation_index']
        if (
            image['kind'] != 'image' or not image['reciprocal_reference_verified']
            or type(index) is not int or not 0 < index <= 0x7fffffff
            or client_control_kind(records[index]) != 'image'
        ):
            raise ValueError('图片模板须有唯一且可回读的图片根控件与模板关联')
        result.update(
            template_index=index, template_entry_guid=image['entry_guid'],
            template_name=image['name'], template_sha256=sha(b''.join(row[3] for row in records[index])),
        )
    return result


def attach(data, op, base, *, base_sha256):
    required = ('op', 'control_guid', 'source', 'mapping')
    schema(op, (*required, 'fit_catalog'), required)
    mapping = op['mapping']
    if (
        not isinstance(mapping, str) or not mapping.endswith('.lua') or len(mapping) <= 4
        or mapping.strip() != mapping or any(ch in mapping for ch in '/\\:') or not mapping.isprintable()
    ):
        raise ValueError('请指定完整的 Lua 映射文件名，例如 marker.lua')
    if type(op['control_guid']) is not int or op['control_guid'] <= 0:
        raise ValueError('请指定经审阅的整数控件标识')
    source = resolve(base, op['source'])
    code = source.read_bytes()
    source_sha256 = sha(code)
    if 'fit_catalog' in op:
        catalog = read_json(resolve(base, op['fit_catalog']))
        mount = catalog.get('mount') if isinstance(catalog, dict) and catalog.get('schema') == 2 else None
        proof = mount.get('gil_binding') if isinstance(mount, dict) else None
        if (
            not isinstance(proof, dict) or proof.get('gil_sha256') != base_sha256
            or mount.get('sha256') != source_sha256 or type(proof.get('template_index')) is not int
        ):
            raise ValueError('拟合报告须绑定同一关卡和 Lua 摘要')
        target = resolve_mount(data, op['control_guid'], proof['template_index'])
        if {**target, 'gil_sha256': base_sha256} != proof:
            raise ValueError('拟合报告里的挂载控件或图片模板已变化')
    else:
        target = resolve_mount(data, op['control_guid'])

    from miliastra.client.check import check

    checked = check(code, 'lua')
    if checked['checks']['syntax'] != 'passed':
        raise ValueError('Lua 语法检查失败：' + repr(checked['diagnostics']))
    result, script_guid = register_script(data, mapping, code)
    result = bind_script(result, target['control_guid'], script_guid)
    after = inspect_bindings(result)
    if (
        not any(row['guid'] == target['control_guid'] for row in after['controls'])
        or not any(row['id'] == script_guid and row['name'] == mapping and row['sha256'] == source_sha256
                   for row in after['scripts'])
        or not any(row['control_guid'] == target['control_guid'] and row['script_guid'] == script_guid
                   and row['mapping_found'] for row in after['script_bindings'])
    ):
        raise ValueError('Lua 映射和控件挂载回读失败')
    return result, {**target, 'mapping': mapping, 'script_guid': script_guid, 'lua_sha256': source_sha256}
