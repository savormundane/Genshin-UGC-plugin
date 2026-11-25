"""Native character, skill and player settings with format-specific field selection."""
import struct

from authoring_io import schema
from level_authoring import flt, integer, msg, set_section, stream, text, vi
from level_inventory import container, fields, unique, vals
from miliastra.native.core import get, model, replace_message
from miliastra.native.scene import encode_vector, typed_record, vector
from miliastra.native.scene_edits import append_library_entries, one, patch_fields, select_record


def name_value(value):
    if not isinstance(value, str) or not value.strip() or '\0' in value:
        raise ValueError('Native record name must be nonempty text')
    return value


def int_range(value, label, minimum=1, maximum=0x7fffffff):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{label} must be an integer in {minimum}..{maximum}')
    return value


def number(value, label, minimum=0):
    if type(value) not in (int, float) or not minimum <= value <= 3.4028234663852886e38:
        raise ValueError(f'{label} must be a finite float32 >= {minimum}')
    return struct.unpack('<f', struct.pack('<f', value))[0]


def config_records(section):
    return vals(fields(section), 1)


def config_record(section, ident, kind):
    row = select_record(section, 1, ident, 'Gameplay resource')
    if get(row, 2, 0) != kind:
        raise ValueError(f'Resource {ident} does not have native kind {kind}')
    return row


def config_name(row, carrier=4):
    block = typed_record(row, carrier, 1)
    return get(get(block or b'', 11, default=b''), 1, default=b'').decode('utf-8')


def next_config_id(section, anchor):
    existing = {get(row, 1, 0) for row in config_records(section)}
    return int_range(max((i for i in existing if i is not None and anchor < i < anchor + 0x400000),
                         default=anchor) + 1, 'Gameplay resource ID', anchor + 1, anchor + 0x3fffff)


def config_payload(row, block_type, payload_field, *, carrier=4):
    block = typed_record(row, carrier, block_type, strict=True)
    wrapper = get(block or b'', payload_field)
    payload = get(wrapper or b'', 1)
    if payload is None:
        raise ValueError(f'Expected gameplay block {block_type} with field {payload_field}/1')
    return block, wrapper, payload


def replace_payload(row, block_type, payload_field, updated, *, carrier=4):
    block, wrapper, payload = config_payload(row, block_type, payload_field, carrier=carrier)
    new_block = replace_message(block, payload_field, wrapper, replace_message(wrapper, 1, payload, updated))
    return replace_message(row, carrier, block, new_block)


def config_ref(ident):
    return integer(1, 1) + integer(2, ident)


def set_native_class(data, op):
    attrs = {'health': 1, 'attack': 2, 'defence': 3, 'stamina': 5}
    movement = {'jump': 3, 'sprint': 4, 'climb': 5, 'glide': 6}
    schema(op, ('op', 'class_id', 'attributes', 'movement', 'layout_id', 'camera_id'), ('class_id',))
    _, root = container(data)
    section = unique(root, 15, default=b'')
    original = config_record(section, op['class_id'], 4)
    row, changed = original, {}
    for group, mapping, block_kind, tag, wire in (('attributes', attrs, 10, 18, 5),
                                                  ('movement', movement, 8, 16, 0)):
        values = op.get(group, {})
        schema(values, mapping, ())
        if not values:
            continue
        _, _, payload = config_payload(row, block_kind, tag)
        updates = {}
        for key, value in values.items():
            if wire == 5:
                value = number(value, key)
                if key == 'health' and value <= 0:
                    raise ValueError('Character class health must be positive')
            elif type(value) is not bool:
                raise ValueError(f'{key} must be boolean')
            updates[mapping[key]] = wire, value if wire == 5 else 1 if value else None
        observed = patch_fields(payload, updates)
        row = replace_payload(row, block_kind, tag, observed)
        changed[group] = {key: (struct.unpack('<f', get(observed, mapping[key], 5))[0] if wire == 5
                                else bool(get(observed, mapping[key], 0))) for key in values}
    for key, field in (('layout_id', 2), ('camera_id', 1)):
        if key not in op:
            continue
        ident = int_range(op[key], key)
        if key == 'layout_id':
            layouts = [r for r in vals(fields(unique(root, 9, default=b'')), 502)
                       if get(r, 501, 0) == ident and any(get(b, 502, 0) == 7 for b in vals(fields(r), 502))]
            one(layouts, 'Native HUD layout')
        else:
            select_record(unique(root, 18, default=b''), 1, ident, 'Native camera')
        _, _, payload = config_payload(row, 8, 16)
        row = replace_payload(row, 8, 16, patch_fields(payload, {field: (0, ident)}))
        changed[key] = ident
    if not changed:
        raise ValueError('Provide at least one class setting')
    return set_section(data, 15, replace_message(section, 1, original, row)), {'class_id': op['class_id'], **changed}


def add_respawn_points(data, op):
    schema(op, ('op', 'player_template_id', 'points'), ('player_template_id', 'points'))
    if not isinstance(op['points'], list) or not op['points']:
        raise ValueError('Provide at least one respawn point')
    _, root = container(data)
    level = unique(root, 11)
    source = unique(root, 4)
    template = select_record(source or b'', 1, op['player_template_id'], 'Player template')
    if get(template, 2, 0) != 1000000 or get(level or b'', 4) is None:
        raise ValueError('Calibrated player template and level respawn list required')
    revive = typed_record(template, 6, 5, strict=True)
    settings = get(revive or b'', 14)
    if settings is None:
        raise ValueError('No native revive settings on this player template')
    listed = get(settings, 10, default=b'')
    respawns = get(level, 4)
    presets = get(level, 5, default=b'')
    existing = vals(fields(respawns), 1)
    used_ids = [get(r, 1, 0, 0) for r in existing]
    used_names = {get(r, 501, default=b'').decode('utf-8') for r in existing}
    used_points = {get(r, 2, 0) for r in existing}
    if len(used_ids) != len(set(used_ids)) or not set(stream(listed)).issubset(used_ids):
        raise ValueError('Existing respawn references are inconsistent')
    result = []
    for item in op['points']:
        schema(item, ('point_id', 'name', 'initially_active'), ('point_id', 'name'))
        name = name_value(item['name'])
        point = int_range(item['point_id'], 'Preset point ID')
        if name in used_names or point in used_points:
            raise ValueError('Respawn name and preset point must each be unique')
        select_record(presets, 1, point, 'Respawn preset point')
        active = item.get('initially_active', False)
        if type(active) is not bool:
            raise ValueError('initially_active must be boolean')
        ident = int_range(max(used_ids, default=0) + 1, 'Respawn ID')
        respawns += msg(1, integer(1, ident) + integer(2, point) + text(501, name))
        used_names.add(name)
        used_points.add(point)
        used_ids.append(ident)
        if active:
            listed += vi(ident)
        result.append({'respawn_id': ident, 'point_id': point, 'name': name, 'initially_active': active})
    new_revive = replace_message(revive, 14, settings, patch_fields(settings, {10: (2, listed or None)}))
    new_template = replace_message(template, 6, revive, new_revive)
    data = set_section(data, 4, replace_message(source, 1, template, new_template))
    return set_section(data, 11, patch_fields(level, {4: (2, respawns)})), {'respawn_points': result}


def set_native_player_group(data, op):
    schema(op, ('op', 'group_id', 'min_players', 'max_players'), ('group_id', 'min_players', 'max_players'))
    _, root = container(data)
    level = unique(root, 11, default=b'')
    groups = get(level, 6, default=b'')
    target = select_record(groups, 1, op['group_id'], 'Player group')
    slots = list(stream(get(target, 4, default=b'')))
    if not slots or len(set(slots)) != len(slots) or min(slots) < 1 or max(slots) > 8:
        raise ValueError('A calibrated player group with an explicit list of slots is required')
    upper = int_range(op['max_players'], 'Maximum players', 1, len(slots))
    lower = int_range(op['min_players'], 'Minimum players', 1, upper)
    group = patch_fields(target, {501: (0, lower), 502: (0, upper)})
    payload = replace_message(groups, 1, target, group)
    return set_section(data, 11, replace_message(level, 6, groups, payload)), {
        'group_id': op['group_id'], 'slots': slots, 'min_players': get(group, 501, 0), 'max_players': get(group, 502, 0)}


def set_native_revive(data,op):
    options={'fall_loss_percent':(2,5),'health_percent':(3,5),'lives':(6,0),'delay_seconds':(7,0),
             'automatic':(8,0),'show_screen':(9,0)}
    schema(op,('op','player_template_id',*options),('player_template_id',))
    _,root=container(data)
    section=unique(root,4,default=b'')
    target=select_record(section,1,op['player_template_id'],'Player template')
    record=typed_record(target,6,5,strict=True)
    existing=get(record or b'',14)
    if get(target,2,0)!=1000000 or existing is None:
        raise ValueError('Calibrated player revive settings required')
    fields_to_write,changes={},{}
    for name,(tag,wire) in options.items():
        if name not in op:continue
        value=op[name]
        if wire==5:
            value=number(value,name)
            if value>100:raise ValueError('Revive percentages must be between 0 and 100')
        elif name in ('automatic','show_screen'):
            if type(value)is not bool:raise ValueError(name+' must be boolean')
        else:
            value=int_range(value,name,0)
        fields_to_write[tag]=(wire,int(value) if type(value) is bool and value else value or None)
        changes[name]=value
    if not changes:raise ValueError('Provide at least one revive setting')
    edited=replace_message(record,14,existing,patch_fields(existing,fields_to_write))
    player=replace_message(target,6,record,edited)
    return set_section(data,4,replace_message(section,1,target,player)),{
        'player_template_id':op['player_template_id'],'changes':changes}


def select_graph(data, selection, category):
    graphs = model(data)['graphs']
    matches = [g for g in graphs if (g['name'] if isinstance(selection, str) else g['id']) == selection
               and get(get(g['raw'], 1), 2, 0) == category]
    return one(matches, 'Graph for category ' + str(category))


def native_creature_graph(data,op):
    """Author the calibrated one-entry Decision/Status pair or a notify-only creature skill graph."""
    from miliastra.native.core import put, ref
    kind=op.get('kind')
    choices={'decision':('status_graph',20007,58,6600),'status':('skill_slot',20009,60,6800),
             'skill':('source_graph',20008,59,6700)}
    if kind not in choices:raise ValueError('Choose creature graph kind decision, status, or skill')
    option,category,tab,code=choices[kind]
    schema(op,('op','kind','name','graph_id',option),('kind','name',option))
    name=name_value(op['name'])
    model_graphs=model(data)['graphs']
    used={g['id'] for g in model_graphs}
    anchor=1082130432
    auto=max((i for i in used if anchor<i<anchor+0x400000),default=anchor)+1
    ident=int_range(op.get('graph_id',auto),'Creature graph ID',anchor+1,anchor+0x3fffff)
    if ident in used or any(g['name']==name for g in model_graphs):
        raise ValueError('Creature graph name or ID is already in use')
    locator=integer(1,10000)+integer(2,category)+integer(3,21001)+integer(5,ident)
    if kind=='skill':
        source=select_graph(data,op[option],20002)
        if ({ref(get(node,2,default=b'')) for node in source['nodes'].values()}!={200042,200039}
                or any(n not in (1,2,3,100) for n,_,_,_ in fields(source['raw']))):
            raise ValueError('Creature skill conversion needs a compiled start and Notify Server graph')
        graph=put(put(source['raw'],1,locator),2,name.encode('utf-8'))
    else:
        def pin(kind,index,typ=None,value=None,connection=None):
            key=integer(1,kind)+(integer(2,index) if index else b'')
            result=msg(1,key)+msg(2,key)
            if value is not None:result+=msg(3,value)+integer(4,typ)
            if connection is not None:result+=msg(5,connection)
            return msg(4,result)
        def descriptor(typ):
            return msg(4,integer(1,2)+msg(101,integer(2,typ)))
        def node(index,generic,concrete):
            family=integer(1,10001)+integer(2,20007)+integer(3,22000)
            return integer(1,index)+msg(2,family+integer(5,generic))+msg(3,family+integer(5,concrete))
        entrance=integer(1,1)
        edge=integer(1,2)+msg(2,entrance)+msg(3,entrance)
        begins=node(1,200126,4000)+pin(2,0,connection=edge)+msg(11,integer(1,1)+msg(100,integer(1,1)))
        enabled=integer(1,6)+descriptor(5)+msg(106,integer(1,1))
        if kind=='status':
            index=int_range(op[option],'Creature skill slot')
            value=integer(1,2)+integer(2,1)+descriptor(3)+msg(102,integer(1,index))
            action=node(2,200129,4012)+pin(3,0,5,enabled)+pin(3,1,3,value)
        else:
            status=select_graph(data,op[option],20009)
            selector=integer(1,12)+msg(106,integer(1,1))
            value=integer(1,1)+integer(2,1)+msg(3,selector)+descriptor(18)+msg(100,integer(1,status['id']))
            index=integer(1,2)+integer(2,1)+descriptor(3)+msg(102,integer(1,1))
            action=node(2,200128,4011)+pin(3,0,5,enabled)+pin(3,1,18,value)+pin(3,2,3,index)
        graph=msg(1,locator)+text(2,name)+msg(3,begins)+msg(3,action)+integer(100,1)
    _,root=container(data)
    section,library=unique(root,10,default=b''),unique(root,6)
    if library is None:raise ValueError('Native graph library required')
    data=set_section(data,10,section+msg(1,msg(1,graph)))
    data=set_section(data,6,append_library_entries(library,tab,code,[ident],create=True))
    return data,{'graph_id':ident,'name':name,'kind':kind,option:op[option],'stored_nodes':len(vals(fields(graph),3))}


def native_skill(data, op):
    """Generate an instant character skill or reuse a same-level creature animation timeline."""
    schema(op, ('op','key','name','skill_id','graph','creature_skill_witness'), ('name','graph'))
    creature = 'creature_skill_witness' in op
    kind, anchor, tab, lib_tag, category = (28, 1191182336, 61, 6900, 20008) if creature else (6, 1098907648, 12, 2800, 20002)
    graph_id = select_graph(data, op['graph'], category)['id']
    name = name_value(op['name'])
    _, root = container(data)
    section = unique(root, 15, default=b'')
    mirrors = unique(root, 16, default=b'')
    library = unique(root, 6)
    if library is None:
        raise ValueError('Native skill library required')
    ident = int_range(op.get('skill_id', next_config_id(section, anchor)), 'Skill ID', anchor + 1, anchor + 0x3fffff)
    if any(get(r, 1, 0) == ident or (get(r, 2, 0) == kind and config_name(r) == name)
           for r in config_records(section)) or any(get(r, 1, 0) == ident for r in config_records(mirrors)):
        raise ValueError('Native skill name or ID already exists')
    named = integer(1, 1) + msg(11, text(1, name))
    if creature:
        witness = config_record(section, op['creature_skill_witness'], 28)
        bits = vals(fields(witness), 4)
        if sorted(get(b, 1, 0, 0) for b in bits) != [1, 35, 36, 73]:
            raise ValueError('Expected an animated creature skill as the witness')
        timeline_block = typed_record(witness, 4, 35, strict=True)
        top = get(timeline_block, 45, default=b'')
        timeline = get(top, 1, default=b'')
        if get(top, 2, 0) != 51 or not vals(fields(timeline), 3):
            raise ValueError('Uncalibrated creature skill timeline')
        events = [field for field, wire, v, _ in fields(timeline) if wire == 2 and field in (4, 6) and get(v, 1, 0)]
        if not events:
            raise ValueError('Creature skill has no graph events')
        patched = b''.join(msg(n, patch_fields(v, {1: (0, graph_id)})) if w == 2 and n in events else raw
                           for n,w,v,raw in fields(timeline))
        new_timeline = replace_message(timeline_block, 45, top, replace_message(top, 1, timeline, patched))
        structural = [new_timeline if get(b, 1, 0) == 35 else b for b in bits if get(b, 1, 0) != 1]
    else:
        cast = integer(2, 1) + integer(3, 2) + integer(5, 1) + integer(9, 2)
        cast += msg(10, flt(1, 1) + flt(2, 1) + flt(3, 1))
        cast += flt(11, 1) + flt(12, 1) + flt(13, 120) + flt(15, 1) + flt(16, 1)
        event = msg(5, integer(1, graph_id) + integer(2, 1073741825))
        basics = msg(1, integer(7, 20001)) + msg(2) + msg(3, cast) + msg(4, integer(2, 1)) + event + msg(6) + msg(7)
        defaults = b''.join(msg(i, integer(1, 1) + integer(2, 1)) for i in (9, 10))
        structural = [integer(1, 21) + msg(30, msg(1, basics)),
                      integer(1, 35) + msg(45, msg(1, defaults) + integer(2, 2) + integer(3, 250422)),
                      integer(1, 36) + msg(46)]
    live = integer(1, ident) + integer(2, kind) + msg(4, named) + b''.join(msg(4, b) for b in structural)
    copy = integer(1, ident) + integer(2, ident) + msg(3, integer(1, 1) + msg(11)) + b''.join(msg(3, b) for b in structural)
    data = set_section(data, 15, section + msg(1, live))
    data = set_section(data, 16, mirrors + msg(1, copy))
    data = set_section(data, 6, append_library_entries(library, tab, lib_tag, [ident], create=True))
    report = {'skill_id': ident, 'name': name, 'graph_id': graph_id, 'kind': 'creature' if creature else 'instant_character'}
    if 'key' in op:report['key']=name_value(op['key'])
    return data, report


def set_creature_skill_set(data, op):
    schema(op, ('op','template_id','decision_graph','skills','cooldown_seconds'), ('template_id','decision_graph','skills'))
    graph_id = select_graph(data, op['decision_graph'], 20007)['id']
    _, root = container(data)
    templates, resources = unique(root, 4, default=b''), unique(root, 15, default=b'')
    target = select_record(templates, 1, op['template_id'], 'Complex creature template')
    asset_id = get(target, 2, 0, 0)
    decision, skill_set, settings = [typed_record(target, 6, n, strict=True) for n in (80, 81, 82)]
    if not 30000000 <= asset_id < 40000000 or None in (decision, skill_set, settings):
        raise ValueError('Use a complex creature template with native decision and skill settings')
    ids = op['skills']
    if not isinstance(ids, list) or not ids:
        raise ValueError('Provide one or more creature skill IDs')
    _, _, slots = config_payload(target, 81, 80, carrier=6)
    skills = []
    for index, ident in enumerate(ids, 1):
        skill = config_record(resources, ident, 28)
        _, _, basics = config_payload(skill, 73, 78)
        if get(get(basics, 2, default=b''), 1, 0) != asset_id - 20000000:
            raise ValueError('Creature skill was configured for another model')
        if ident in ids[:index-1]:
            raise ValueError('Creature skills must be unique')
        timing = flt(4, 3) + integer(6, 1)
        skills.append(msg(1, integer(1, index) + msg(2, config_ref(ident)) + msg(3, timing) + text(12, f'技能_{index}')))
    _, _, previous_decision = config_payload(target, 80, 79, carrier=6)
    target_new = replace_payload(target, 80, 79, patch_fields(previous_decision,
                                 {1: (0, 1), 2: (0, graph_id), 501: (0, 20007)}), carrier=6)
    other = b''.join(raw for n,_,_,raw in fields(slots) if n != 1)
    if 'cooldown_seconds' in op:
        shared = get(other, 2, default=b'')
        other = patch_fields(other, {2: (2, patch_fields(shared, {1: (5, number(op['cooldown_seconds'], 'Shared cooldown'))}))})
    target_new = replace_payload(target_new, 81, 80, b''.join(skills) + other, carrier=6)
    return set_section(data, 4, replace_message(templates, 1, target, target_new)), {
        'template_id': op['template_id'], 'decision_graph_id': graph_id, 'skills': list(ids)}


def set_native_faction_relations(data, op):
    schema(op, ('op', 'faction_id', 'hostile_to'), ('faction_id', 'hostile_to'))
    _, root = container(data)
    level = unique(root, 11, default=b'')
    factions = get(level, 2, default=b'')
    records = vals(fields(factions), 1)
    target_id = int_range(op['faction_id'], 'Faction ID')
    target = one((r for r in records if get(r, 2, 0) == target_id), 'Faction')
    others = [get(r, 2, 0) for r in records if r != target]
    hostile = op['hostile_to']
    if (not isinstance(hostile, list) or len(others) != len(set(others))
            or any(type(i) is not int or i not in others for i in hostile) or len(hostile) != len(set(hostile))):
        raise ValueError('Hostile factions must be unique existing faction IDs other than the source')
    friendly = sorted(set(others) - set(hostile))
    members = {12: friendly, 13: sorted(hostile)}
    edited = patch_fields(target, {n: (2, b''.join(vi(i) for i in ids) or None) for n,ids in members.items()})
    updated = replace_message(factions, 1, target, edited)
    return set_section(data, 11, replace_message(level, 2, factions, updated)), {
        'faction_id': target_id, 'friendly_to': friendly, 'hostile_to': sorted(hostile)}


def native_unit_status(data, op):
    schema(op, ('op','name','status_id','outline','speed_percent','stack_limit'), ('name',))
    if ('outline'in op)==('speed_percent'in op):
        raise ValueError('Select one calibrated unit status effect: outline or speed_percent')
    _, root = container(data)
    section, mirrors, library = (unique(root,n,default=b'') for n in (15,16,6))
    name = name_value(op['name'])
    anchor = 1077936128
    ident = int_range(op.get('status_id',next_config_id(section,anchor)), 'Unit status ID', anchor+1, anchor+0x3fffff)
    if (any(get(r,1,0)==ident or get(r,2,0)==1 and config_name(r)==name for r in config_records(section))
            or any(get(r,1,0)==ident for r in config_records(mirrors))):
        raise ValueError('Unit status ID or name is already in use')
    max_stack = int_range(op.get('stack_limit',1),'Unit status stack limit')
    targets = (1404,1405,1402)
    if 'outline'in op:
        colors = {'green':6,'white':14}
        color = op['outline']
        if color not in colors:raise ValueError('Outline color must be green or white')
        effect_id, value = 710002, colors[color]
    else:
        effect_id, value = 20001, int_range(op['speed_percent'],'Speed percent',-100,40)
        targets = (1404,1405)
    parameter = integer(1,3)+integer(4,value%(1<<64))+msg(10)+msg(12)+msg(13)
    effect = msg(1,integer(1,effect_id)+msg(2,parameter)) + msg(2,b''.join(vi(i) for i in targets))
    lifetime = flt(1,1)+msg(2,integer(501,20003))+integer(4,1)+integer(5,max_stack)+integer(6,1)+flt(9,1)
    body = (msg(1,lifetime)+msg(2,integer(1,1)+integer(3,1)+integer(4,1))+msg(3,effect)
            +msg(4)+msg(5)+integer(6,30001))
    blocks = [integer(1,1)+msg(11,text(1,name)),integer(1,6)+msg(21,msg(1,body))]
    live = integer(1,ident)+integer(2,1)+b''.join(msg(4,b) for b in blocks)
    copy = integer(1,ident)+integer(2,ident)+b''.join(msg(3,b) for b in blocks)
    data = set_section(data,15,section+msg(1,live))
    data = set_section(data,16,mirrors+msg(1,copy))
    data = set_section(data,6,append_library_entries(library,11,1900,[ident],create=True))
    return data, {'status_id':ident,'name':name,'effect':'outline' if 'outline'in op else 'speed_percent'}


def native_combat(data,op):
    fieldspec=('op','section','entity_id','attack','hurtbox')
    schema(op,fieldspec,('section','entity_id'))
    if not any(k in op for k in ('attack','hurtbox')):
        raise ValueError('Provide a direct attack ability or a box hurtbox')
    section_id=op['section']
    if type(section_id)is not int or section_id not in (4,5):
        raise ValueError('Combat requires template section 4 or instance section 5')
    _,root=container(data)
    section=unique(root,section_id,default=b'')
    target=select_record(section,1,op['entity_id'],'Combat owner')
    property_field,component_field,general_field=((6,7,8) if section_id==4 else (5,6,7))
    label=typed_record(target,property_field,1,strict=True)
    if typed_record(target,component_field,3,strict=True) is None or get(get(label or b'',11,default=b''),2,0,0)==1:
        raise ValueError('Combat requires a dynamic entity with a graph component')
    output=target
    report={'section':section_id,'entity_id':op['entity_id']}
    if 'attack'in op:
        attack=op['attack']
        schema(attack,('name','coefficient','added_damage'),('name',))
        name=name_value(attack['name'])
        coeff=number(attack.get('coefficient',1),'Attack coefficient')
        bonus=number(attack.get('added_damage',0),'Added damage')
        existing=typed_record(target,property_field,14,strict=True)
        container_value=get(existing or b'',23,default=b'')
        listing=get(container_value,1,default=b'')
        if any(get(u,4,default=b'').decode('utf-8')==name for u in vals(fields(listing),1)):
            raise ValueError('Ability name is already in use')
        damage=flt(2,coeff)+(flt(3,bonus) if bonus else b'')+integer(4,1300)+integer(6,2201)+integer(7,2303)
        impact=integer(1,191)+integer(3,2501)+flt(5,1)+msg(6)+msg(7)+integer(10,2)
        body=(text(1,'GI_RootNode')+msg(2)+msg(3)+msg(4,damage)+msg(5,impact)
              +integer(6,3000)+msg(7,flt(1,1)+integer(3,3200)))
        listing=patch_fields(listing,{3:(2,get(listing,3,default='能力单元'.encode('utf-8')))})
        listing+=msg(1,integer(2,2)+text(4,name)+msg(12,body))
        updated=patch_fields(container_value,{1:(2,listing)})
        if existing is None:
            output+=msg(property_field,integer(1,14)+msg(23,updated))
        else:
            output=replace_message(output,property_field,existing,patch_fields(existing,{23:(2,updated)}))
        report['attack']={'name':name,'coefficient':coeff,'added_damage':bonus}
    if 'hurtbox'in op:
        hurtbox=op['hurtbox']
        schema(hurtbox,('size_m','offset_m','health'),('size_m',))
        size=vector(hurtbox['size_m'],'Hurtbox size',positive=True)
        offset=vector(hurtbox.get('offset_m',[0,0,0]),'Hurtbox offset')
        if max(size)>500:raise ValueError('Hurtbox dimensions must be at most 500 metres')
        existing=typed_record(output,general_field,19,strict=True)
        box=msg(11,msg(1,encode_vector(offset))+msg(2,encode_vector(size))+msg(3))
        area=box+text(502,'区域1')+integer(503,1)
        row=integer(1,1)+integer(2,1)+msg(3,area)+text(502,'受击盒1')
        if existing is not None:
            current=get(existing,29,default=b'')
            if vals(fields(current),1):raise ValueError('Combat owner already has a hurtbox')
            revised=patch_fields(existing,{29:(2,current+msg(1,row))})
            output=replace_message(output,general_field,existing,revised)
        else:
            output+=msg(general_field,integer(1,19)+integer(2,1)+msg(29,msg(1,row)))
        report['hurtbox']={'size_m':size,'offset_m':offset}
        if 'health'in hurtbox:
            health=number(hurtbox['health'],'Combat health')
            combat=typed_record(output,component_field,7,strict=True)
            attr=get(combat or b'',17)
            if health<=0 or attr is None:raise ValueError('Positive health and a calibrated combat attributes block required')
            output=replace_message(output,component_field,combat,
                                   replace_message(combat,17,attr,patch_fields(attr,{1:(5,health),4:(0,None)})))
            report['hurtbox']['health']=health
    return set_section(data,section_id,replace_message(section,1,target,output)),report


GAMEPLAY_EDITS = {f.__name__: f for f in (set_native_class, add_respawn_points, set_native_player_group,
                                         native_skill, set_creature_skill_set, set_native_faction_relations,
                                         native_unit_status, native_creature_graph, native_combat, set_native_revive)}
