"""Create and bind native currency, inventory, shop, and pickup data."""
from authoring_io import schema
from level_authoring import flt, integer, msg, set_section, text
from level_inventory import container, fields, unique, vals
from native_core import get, replace_message
from native_bindings import Bindings
from native_gameplay import (config_name, config_payload, config_record, config_records, config_ref, int_range,
                             name_value, next_config_id, replace_payload)
from native_scene import encode_vector, read_templates, typed_record, vector
from native_scene_edits import append_library_entries, next_object_ids, one, patch_fields, rename_transform_object, select_record


# kind, ID range anchor, payload type, carrier, library tab, entry tag
RESOURCES = {
    'currency': (11, 1115684864, 41, 54, 23, 3700),
    'backpack': (12, 1119879168, 42, 55, 22, 3800),
    'item': (9, 1107296256, 39, 49, 19, 3100),
    'shop': (17, 1136656384, 48, 58, 28, 4000),
}


def price_record(currency, amount):
    return msg(1, config_ref(currency)) + integer(2, amount)


def economy_config(data, op, *, bindings=None):
    if bindings is None:bindings = Bindings()
    schema(op, ('op', 'resources'), ('resources',))
    if not isinstance(op['resources'], list) or not op['resources']:
        raise ValueError('Provide at least one economy resource')
    _, root = container(data)
    section, library = unique(root, 15, default=b''), unique(root, 6)
    if library is None:
        raise ValueError('Native resource library required')
    result, aliases = [], {}
    for item in op['resources']:
        family = item.get('kind')
        if family not in RESOURCES:
            raise ValueError('Economy resource kind must be currency, backpack, item, or shop')
        kind, anchor, block, tag, tab, entry = RESOURCES[family]
        options = {'currency': ('icon_id',), 'backpack': ('capacity',),
                   'item': ('icon_id', 'max_stack', 'description'),
                   'shop': ('sell', 'buy')}[family]
        schema(item, ('kind', 'key', 'name', 'resource_id', *options), ('kind','key'))
        key = name_value(item['key'])
        if key in aliases:
            raise ValueError('Economy resource keys must be unique')
        if 'resource_id' in item:
            ident = item['resource_id']
            original = config_record(section, ident, kind)
            name = name_value(item.get('name', config_name(original)))
            if name != config_name(original):
                raise ValueError('Update resource properties using its existing name')
            _, _, payload = config_payload(original, block, tag)
        else:
            original = None
            ident = next_config_id(section, anchor)
            name = name_value(item.get('name', key))
            if any(get(r, 2, 0) == kind and config_name(r) == name for r in config_records(section)):
                raise ValueError(f'Duplicate {family} name {name}')
            drop = integer(3, 4350) + msg(4)
            if family == 'currency':
                payload = integer(1, 100001) + integer(2, 1) + msg(4, drop)
            elif family == 'backpack':
                payload = integer(1, 10) + msg(3, drop)
            elif family == 'item':
                basic = (integer(1, 999) + integer(3, 1) + integer(4, 4201) + integer(5, 4301)
                         + msg(6, integer(501, 20005)) + integer(502, 1))
                behavior = b''.join(integer(i, 1) for i in (1, 2, 3, 4)) + flt(6, 10) + flt(7, 10)
                payload = (msg(1, basic) + msg(2, msg(1, drop)) + msg(3, behavior)
                           + integer(4, 90001) + msg(11, integer(1, 1) + integer(2, 1)))
            else:
                payload = integer(1, 1) + integer(4, 1) + msg(5) + msg(6) + msg(7) + integer(10, 1) + integer(11, 1)

        def reference(value, category):
            ident = aliases.get(value) if isinstance(value, str) else bindings.reference(
                value, (category,), phase='economy_config', field=category)
            config_record(section, ident, RESOURCES[category][0])
            return ident

        updates = {}
        if 'icon_id' in item:
            updates[4 if family == 'item' else 1] = 0, int_range(item['icon_id'], 'Platform icon ID')
        if 'capacity' in item:
            updates[1] = 0, int_range(item['capacity'], 'Backpack capacity')
        if family == 'item' and ('max_stack' in item or 'description' in item):
            basic = get(payload, 1)
            changes = {}
            if 'max_stack' in item:
                changes[1] = 0, int_range(item['max_stack'], 'Maximum stack')
            if 'description' in item:
                if not isinstance(item['description'], str):
                    raise ValueError('Item description must be text')
                changes[501] = 2, item['description'].encode('utf-8') or None
            updates[1] = 2, patch_fields(basic, changes)
        for side, field, ref_tag, price_tag in (('sell', 6, 2, 5), ('buy', 5, 1, 4)):
            if side not in item:
                continue
            rows = item[side]
            if not isinstance(rows, list):
                raise ValueError('Shop offers must be a list')
            table = get(payload, field, default=b'')
            seen = set()
            for offer in rows:
                options = ('stock',) if side == 'sell' else ()
                schema(offer, ('item', 'currency', 'price', *options), ('item','currency','price'))
                target = reference(offer['item'], 'item')
                currency = reference(offer['currency'], 'currency')
                price = int_range(offer['price'], 'Offer price')
                if target in seen:
                    raise ValueError('An item may appear only once per side of a shop')
                seen.add(target)
                existing = vals(fields(table), 1)
                matches = [r for r in existing if get(get(r, ref_tag, default=b''), 2, 0) == target]
                if len(matches) > 1:
                    raise ValueError('Existing shop offer is ambiguous')
                current = matches[0] if matches else None
                if side == 'sell':
                    if current is None:
                        index = max((get(r, 1, 0, 0) for r in existing), default=0) + 1
                        current_bytes = (integer(1, index) + msg(2, config_ref(target)) + integer(3, 1)
                                         + integer(4, 1) + integer(7, 1) + integer(8, 1))
                    else:
                        current_bytes = current
                else:
                    current_bytes = current or msg(1, config_ref(target)) + integer(2, 1) + integer(3, 1)
                old_price = get(current_bytes, price_tag)
                if old_price is None:
                    new_price = price_record(currency, price)
                else:
                    old_currency = get(old_price, 1, default=b'')
                    new_price = patch_fields(old_price, {1: (2, patch_fields(old_currency, {1: (0, 1), 2: (0, currency)})),
                                                         2: (0, price)})
                changes = {price_tag: (2, new_price)}
                if 'stock' in offer:
                    changes[8] = 0, int_range(offer['stock'], 'Shop stock')
                updated = patch_fields(current_bytes, changes)
                table = table + msg(1, updated) if current is None else replace_message(table, 1, current, updated)
            updates[field] = 2, table
        updated = patch_fields(payload, updates)
        if family == 'shop' and not (get(updated, 5) or get(updated, 6)):
            raise ValueError('Shop requires a sell or buy offer')
        if original is None:
            header = integer(1, ident) + integer(2, kind)
            named = msg(4, integer(1, 1) + msg(11, text(1, name)))
            section += msg(1, header + named + msg(4, integer(1, block) + msg(tag, msg(1, updated))))
            library = append_library_entries(library, tab, entry, [ident], create=True)
        else:
            section = replace_message(section, 1, original, replace_payload(original, block, tag, updated))
        aliases[key] = ident
        bindings.add(family,key,ident)
        result.append({'key': key, 'name': name, 'kind': family, 'resource_id': ident, 'created': original is None})
    return set_section(set_section(data, 15, section), 6, library), {'resources': result}


def native_economy_binding(data, op):
    family = op.get('kind')
    options = {'backpack': ('resource_id', 'holdings'), 'shop': ('resource_id', 'name'), 'loot': ('drop_template_id','holdings')}
    if family not in options:
        raise ValueError('Choose backpack, shop, or loot')
    schema(op, ('op', 'kind', 'section', 'entity_id', *options[family]), ('kind','section','entity_id'))
    section_id = op['section']
    if type(section_id) is not int or section_id not in (4, 5):
        raise ValueError('Economy bindings require template section 4 or instance section 5')
    _, root = container(data)
    section = unique(root, section_id, default=b'')
    target = select_record(section, 1, op['entity_id'], 'Economy target')
    named = typed_record(target, 5, 1, strict=True) if section_id == 5 else None
    if section_id == 5 and get(get(named or b'', 11, default=b''), 2, 0, 0)==1:
        raise ValueError('Native economy components require a dynamic instance')
    config = unique(root, 15, default=b'')
    carrier = 8 if section_id == 4 else 7
    kinds = {'backpack': (33, 44), 'shop': (35, 46), 'loot': (37, 48)}
    kind, tag = kinds[family]
    existing = typed_record(target, carrier, kind, strict=True)
    payload = get(existing or b'', tag)
    if existing is not None and (payload is None or get(existing, 2, 0) != 1):
        raise ValueError('Uncalibrated existing economy component')
    if section_id == 5 and existing is None:
        template_id = get(get(target, 2, default=b''), 1, 0)
        if template_id in read_templates(root):
            template = select_record(unique(root, 4, default=b''), 1, template_id, 'Economy target template')
            if typed_record(template, 8, kind, strict=True) is not None:
                raise ValueError('Target inherits this component. Edit its template instead')
    details = {}
    if family in ('backpack', 'shop'):
        ident = op.get('resource_id')
        record = config_record(config, ident, RESOURCES[family][0])
        details['resource_id'] = ident
    if family == 'shop':
        if payload and len(vals(fields(payload), 1)) != 1:
            raise ValueError('Existing shop binding is ambiguous')
        label = name_value(op.get('name', config_name(record)))
        line = get(payload or b'', 1, default=b'')
        updates = {1: (0, 1), 2: (2, config_ref(ident)), 3: (2, label.encode('utf-8')), 501: (2, label.encode('utf-8'))}
        payload = patch_fields(payload or b'', {1: (2, patch_fields(line, updates))})
    else:
        slot = 3 if family == 'backpack' else 4
        holdings = get(payload or b'', slot, default=b'')
        rows = op.get('holdings', [])
        if not isinstance(rows, list) or (family == 'loot' and not rows):
            raise ValueError('Provide a holdings list with item or currency IDs and amounts')
        seen = set()
        for entry in rows:
            schema(entry, ('resource_id','amount'), ('resource_id','amount'))
            resource = select_record(config, 1, entry['resource_id'], 'Holding resource')
            row_id = get(resource, 1, 0)
            if row_id in seen or get(resource, 2, 0) not in ((9, 11) if family == 'backpack' else (9,)):
                raise ValueError('Holdings require unique resources of the expected kind')
            seen.add(row_id)
            amount = int_range(entry['amount'], 'Holding amount')
            matches = [r for r in vals(fields(holdings), 1) if get(get(r, 1, default=b''), 2, 0) == row_id]
            if matches:
                old = one(matches, 'Existing holding')
                holdings = replace_message(holdings, 1, old, patch_fields(old, {2: (0, amount)}))
            else:
                holdings += msg(1, msg(1, config_ref(row_id)) + integer(2, amount))
        if family == 'backpack':
            updates = {1: (2, config_ref(ident)), 3: (2, holdings)}
        else:
            drop_id = op.get('drop_template_id')
            drop = select_record(unique(root, 4, default=b''), 1, drop_id, 'Pickup template')
            if get(drop, 9, 0) != 2 or typed_record(drop, 8, 36, strict=True) is None:
                raise ValueError('Loot requires a native pickup template')
            updates = {1: (0, 1), 3: (2, config_ref(drop_id)), 4: (2, holdings), 5: (0, 4350)}
            details['drop_template_id'] = drop_id
        payload = patch_fields(payload or b'', updates)
        details['holdings'] = [{'resource_id': get(get(r, 1, default=b''), 2, 0), 'amount': get(r, 2, 0)}
                               for r in vals(fields(holdings), 1)]
    if existing is None:
        updated = target + msg(carrier, integer(1, kind) + integer(2, 1) + msg(tag, payload))
    else:
        updated = replace_message(target, carrier, existing, patch_fields(existing, {tag: (2, payload)}))
    result = set_section(data, section_id, replace_message(section, 1, target, updated))
    return result, {'section': section_id, 'entity_id': op['entity_id'], 'kind': family, **details}


def create_native_drop(data, op):
    schema(op, ('op','key','name','source_template_id','item_id','amount','pickup_size_m'),
           ('name','source_template_id','item_id','amount'))
    _, root = container(data)
    section, library = unique(root, 4, default=b''), unique(root, 6)
    source = select_record(section, 1, op['source_template_id'], 'Pickup model template')
    if op['source_template_id'] not in read_templates(root) or get(source, 9, 0) or library is None:
        raise ValueError('Select a plain ordinary model template in the current level')
    for field in (6, 7, 8):
        if any(get(p, 1, 0) not in {6: {1, 13, 14, 19, 20, 38, 40, 52, 61, 62},
                                    7: {1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 16, 17, 19},
                                    8: {1, 3, 6, 14, 18, 19}}[field] for p in vals(fields(source), field)):
            raise ValueError('Pickup model template has additional components')
    for field, kind, tag in ((6, 40, 50), (7, 2, 12), (7, 3, 13), (8, 1, 11)):
        if get(typed_record(source, field, kind, strict=True) or b'', tag):
            raise ValueError('Pickup model template has dependent decoration, model, graph or variable records')
    name = name_value(op['name'])
    key = name_value(op['key']) if 'key'in op else None
    item = int_range(op['item_id'], 'Material item ID')
    config_record(unique(root, 15, default=b''), item, 9)
    amount = int_range(op['amount'], 'Pickup amount')
    size = vector(op.get('pickup_size_m', [1, 1, 1]), 'Pickup box dimensions', positive=True)
    ident = next(next_object_ids(data, root), None)
    if ident is None:
        raise ValueError('Object ID range exhausted')
    result = rename_transform_object(source, name, {}, property_field=6, component_field=7)
    result = patch_fields(result, {1: (0, ident), 9: (0, 2)})
    parts = []
    for field, wire, value, raw in fields(result):
        kind = get(value, 1, 0) if wire == 2 and field in (6, 7, 8) else None
        if (field, kind) == (6, 38):
            parts.append(msg(6, patch_fields(value, {48: (2, flt(1, 1))})))
        elif (field, kind) == (7, 7):
            parts.append(msg(7, patch_fields(value, {17: (2, patch_fields(get(value, 17, default=b''),
                                                                         {1: (5, 1000), 2: (5, None), 4: (0, 1)}))})))
        elif (field, kind) != (8, 6):
            parts.append(raw)
    area = msg(11, msg(1) + msg(2, encode_vector(size)) + msg(3)) + text(502, '区域1') + integer(503, 1)
    pickup = integer(1, 1) + msg(3, integer(501, 20000)) + integer(4, 1)
    pickup += msg(7, msg(1, msg(1, config_ref(item)) + integer(2, amount))) + msg(8, area)
    result = b''.join(parts) + msg(8, integer(1, 36) + integer(2, 1) + msg(47, pickup))
    data = set_section(data, 4, section + msg(1, result))
    info={'drop_template_id':ident,'name':name,'item_id':item,'amount':amount}
    if key is not None:info['key']=key
    return set_section(data,6,append_library_entries(library,21,3300,[ident],create=True)),info


ECONOMY_EDITS = {f.__name__: f for f in (economy_config, native_economy_binding, create_native_drop)}
