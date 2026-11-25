"""Author editor-native HUD layouts and controls driven by nodes and level data."""
import math

from authoring_io import schema
from level_authoring import (component, flt, integer, kind_meta, msg, reverse_meta, self_meta, set_section,
                             stream, template_meta, text, vi)
from level_inventory import container, fields, unique, vals
from miliastra.native.core import get, replace_message
from miliastra.native.gameplay import int_range, name_value, number
from miliastra.native.scene import typed_record
from miliastra.native.scene_edits import one, patch_fields, select_record
from miliastra.native.variables import read as read_variables

CONTROLS = {
    # native content type, base/override slots, base/override tags, rectangle kind
    'text': (25, 9, 10, 19, 19, 3),
    'button': (22, 7, 7, 17, 16, 1),
    'progress': (26, 10, 11, 20, 20, 4),
    'timer': (27, 11, 12, 21, 21, 5),
    'scoreboard': (28, 12, 13, 22, 22, 6),
}


def roots(section, kind):
    return [r for r in vals(fields(section), 502) if any(get(b,502,0)==kind for b in vals(fields(r),502))]


def control_name(row):
    block = next((b for b in vals(fields(row),505) if (get(b,501,0),get(b,502,0))==(2,15)), b'')
    return get(get(block,12,default=b''),501,default=b'').decode('utf-8')


def control_content(name):
    return msg(505, msg(12,text(501,name))+integer(501,2)+integer(502,15))


def native_root(ident, kind, name):
    if kind == 7:
        layout = component(ident,5,7,15,b'',8,17,b'')
    else:
        layout = msg(17)+integer(501,7)+integer(502,14)
    return (integer(501,ident)+msg(502,layout)+msg(502,self_meta(ident))+control_content(name)
            +msg(505,component(ident,1,11,11,msg(11)+integer(501,1),4,13,msg(11)+integer(501,1))))


def rect_pair(values, label, limits, *, size=False):
    if not isinstance(values,list) or len(values)!=2 or any(type(v) not in (int,float) or abs(v)>limit or
          not math.isfinite(v) or (size and v<=0) for v,limit in zip(values,limits)):
        raise ValueError('Invalid ' + label)
    return b''.join(flt(axis,value) for axis,value in enumerate(values,501) if value)


def native_hud(data, op):
    schema(op, ('op','layout_id','player_template_id','group_name','group_key','controls'), ('controls',))
    _, root = container(data)
    section = unique(root,9,default=b'')
    records = vals(fields(section),502)
    registered = get(section,501,default=b'')
    if not records:
        if registered or section:
            raise ValueError('Existing HUD section has unsupported layout records')
        layout_id = 1073741825
        library_id = 1073741826
        if op.get('layout_id',layout_id)!=layout_id:
            raise ValueError('New native layouts use the default layout ID 1073741825')
        layout, library = native_root(layout_id,7,'默认布局'),native_root(library_id,14,'')
        registered = vi(layout_id)+vi(library_id)
        section = msg(501,registered)+msg(502,layout)+msg(502,library)
        records = [layout,library]
    else:
        layouts = roots(section,7)
        layout = one((l for l in layouts if 'layout_id' not in op or get(l,501,0)==op['layout_id']), 'Native HUD layout')
        library = one(roots(section,14), 'Native HUD control library')
        layout_id,library_id = get(layout,501,0),get(library,501,0)
        if not {layout_id,library_id}.issubset(stream(registered)):
            raise ValueError('HUD layout and library must be registered')
    names = {control_name(row) for row in records}
    next_id = max(1073741826, *(get(r,501,0) for r in records))+1
    all_slots = [get(get(b,12,default=b''),501,0,0) for r in records for b in vals(fields(r),502)
                 if get(b,502,0)==6]
    slot = max(all_slots,default=0)
    generated, library_additions, layout_additions, created = [], [], [], []
    group_name = op.get('group_name')
    if 'group_key' in op and group_name is None:raise ValueError('HUD group_key requires group_name')
    group_ids = None
    group_children = {}
    if 'group_name'in op:
        group_name = name_value(group_name)
        if group_name in names:raise ValueError('HUD group name is already in use')
        names.add(group_name)
        group_ids = [int_range(next_id+i,'HUD group ID',1073741825) for i in range(3)]
        next_id += len(group_ids)
        slot += 1
        group_slot = slot
        group_children = {i:[] for i in group_ids}
    items = op['controls']
    if not isinstance(items,list) or not items:
        raise ValueError('Provide at least one native HUD control')
    player_ids = [get(t,1,0) for t in vals(fields(unique(root,4,default=b'')),1) if get(t,2,0)==1000000]
    player = op.get('player_template_id', player_ids[0] if len(player_ids)==1 else None)
    variables = {r['name'] for r in read_variables(root)['records']
                 if (r['section'],r['entity_id'],r['type_id'])==(4,player,3) and player in player_ids}
    timers = {get(r,1,default=b'').decode('utf-8') for r in vals(fields(unique(root,12,default=b'')),1)}
    for item in items:
        family = item.get('kind')
        options = {'text': ('text','font_size'), 'button': ('key_index',), 'progress': ('current','minimum','maximum'),
                   'timer': ('timer',), 'scoreboard': ('variable','player_count')}
        if family not in options:
            raise ValueError('Native control kind must be text, button, progress, timer or scoreboard')
        required = {'text': ('text',), 'button': (), 'progress': ('current','minimum','maximum'),
                    'timer': ('timer',), 'scoreboard': ('variable','player_count')}[family]
        schema(item, ('kind','key','name','position_px','size_px','hidden',*options[family]),
               ('kind','name','position_px','size_px',*required))
        name = name_value(item['name'])
        if name in names:
            raise ValueError('HUD control name is already in use')
        names.add(name)
        if type(item.get('hidden',False)) is not bool:
            raise ValueError('HUD hidden must be boolean')
        position = rect_pair(item['position_px'],'HUD position',[800,450])
        size = rect_pair(item['size_px'],'HUD size',[1600,900],size=True)
        if family == 'text':
            if not isinstance(item['text'],str):
                raise ValueError('HUD content must be text')
            font = int_range(item.get('font_size',24),'HUD font size',1,200)
            payload = integer(502,font)+integer(504,1)+msg(505,text(501,item['text']))
        elif family == 'button':
            index = int_range(item.get('key_index',1),'Interaction key',1,8)
            payload = integer(501,index)+integer(502,1)+integer(503,2)+msg(509,integer(501,0xffffffffffffffff))
        elif family == 'progress':
            bound = [name_value(item[k]) for k in ('current','minimum','maximum')]
            if not set(bound).issubset(variables):
                raise ValueError('Progress requires declared integer variables on the selected player template')
            payload = b''.join(msg(n,integer(501,100)+text(502,var)) for n,var in enumerate(bound,504))
        elif family == 'timer':
            timer = name_value(item['timer'])
            if timer not in timers:
                raise ValueError('HUD timer requires a declared global timer')
            payload = text(503,timer)
        else:
            var = name_value(item['variable'])
            if var not in variables:
                raise ValueError('Scoreboard requires an integer variable on the selected player template')
            count = int_range(item['player_count'],'Scoreboard player count',1,8)
            payload = integer(501,1)+integer(502,1)+b''.join(integer(n,1) for n in (506,507,508,509))
            # Player entries are zero-based. The secondary column is left unbound.
            for i in range(count):
                row = integer(501,i) if i else b''
                payload += msg(510,row+msg(502,row+text(502,var)))
            payload += b''.join(msg(511,integer(501,i)+msg(502,integer(501,0xffffffffffffffff)))
                                for i in range(1,9) if i>=count)
        kind, base_slot, override_slot, base_tag, override_tag, rect_kind = CONTROLS[family]
        ids = [int_range(next_id+i,'HUD ID',1073741825) for i in range(3)]
        next_id += len(ids)
        template, library_copy, layout_copy = ids
        slot += 1
        half = flt(501,.5)+flt(502,.5)
        frame = (msg(501,flt(1,1)+flt(2,1)+flt(3,1))+msg(502,half)+msg(503,half)
                 +msg(504,position)+msg(505,size)+msg(506,half))
        rect = b''.join(msg(501,(integer(501,i) if i else b'')+msg(502,frame)) for i in range(4))
        rect += integer(502,rect_kind)
        visible = msg(15)+integer(501,5)
        override_visible = visible + (integer(502,1) if item.get('hidden') else b'')
        parents = group_ids or (None,library_id,layout_id)
        for ident,parent in zip(ids,parents):
            record = integer(501,ident)+msg(502,self_meta(ident))+msg(502,kind_meta(slot))
            if group_ids:
                group_children[parent].append(ident)
            else:
                identity = reverse_meta(ids[1:]) if parent is None else template_meta(template)
                record += msg(502,identity)
            if parent is not None:
                record += integer(504,parent)
            record += control_content(name)
            record += msg(505,component(ident,4,23,14,visible,5,14,override_visible))
            record += msg(505,component(ident,1,12,11,msg(12)+integer(501,2),4,13,msg(12,rect)+integer(501,2)))
            record += msg(505,component(ident,base_slot,kind,base_tag,b'',override_slot,override_tag,payload))
            generated.append(msg(502,record))
        if not group_ids:
            layout_additions.append(vi(layout_copy))
            library_additions.append(vi(library_copy))
            registered += vi(template)
        entry={'name':name,'kind':family,'template_id':template,'control_id':layout_copy,'library_id':library_copy}
        if 'key' in item:entry['key']=name_value(item['key'])
        created.append(entry)
    if group_ids:
        group_template,group_library,group_layout = group_ids
        for ident,parent in zip(group_ids,(None,library_id,layout_id)):
            metadata = component(ident,6,13,16,b'',6,15,b'')
            identity = reverse_meta(group_ids[1:]) if parent is None else template_meta(group_template)
            record = (integer(501,ident)+msg(502,self_meta(ident))+msg(502,kind_meta(group_slot))
                      +msg(502,identity)+msg(502,metadata)+msg(503,b''.join(vi(i) for i in group_children[ident])))
            if parent is not None:record += integer(504,parent)
            flag = msg(15)+integer(501,5)
            record += control_content(group_name)+msg(505,component(ident,4,23,14,flag,5,14,flag))
            generated.append(msg(502,record))
        layout_additions.append(vi(group_layout))
        library_additions.append(vi(group_library))
        registered += vi(group_template)
    for root_record, additions in ((layout,layout_additions),(library,library_additions)):
        children = get(root_record,503,default=b'')+b''.join(additions)
        section = replace_message(section,502,root_record,patch_fields(root_record,{503:(2,children)}))
    section = patch_fields(section,{501:(2,registered)}) + b''.join(generated)
    report={'layout_id':layout_id,'library_id':library_id,'controls':created}
    if group_ids:
        report['group']={'template_id':group_template,'group_id':group_layout,'library_id':group_library}
        if 'group_key' in op:report['group']['key']=name_value(op['group_key'])
    return set_section(data,9,section), report


def set_native_hud_control(data, op):
    changes = ('name','text','position_px','size_px','hidden')
    schema(op, ('op','template_id',*changes), ('template_id',))
    if not any(k in op for k in changes):raise ValueError('Provide a native HUD control change')
    _,root = container(data)
    section = unique(root,9,default=b'')
    records = vals(fields(section),502)
    def record(ident):
        return one((r for r in records if get(r,501,0)==ident),'HUD control identity')
    template = record(int_range(op['template_id'],'HUD control template ID'))
    def meta(r,kind):
        return one((b for b in vals(fields(r),502) if get(b,502,0)==kind), 'HUD metadata ' + str(kind))
    def copies(r):
        ids = stream(get(get(meta(r,4),14),501,default=b''))
        if len(ids)!=2 or len(set(ids))!=2:raise ValueError('Two native HUD copies required')
        return [record(i) for i in ids]
    def slot_of(r):
        return get(get(meta(r,6),12,default=b''),501,0)
    parent = get(template,504,0)
    if parent is None:
        members=[template,*copies(template)]
    else:
        group = record(parent)
        meta(group,13)
        children = [stream(get(g,503,default=b'')) for g in copies(group)]
        members=[template,*[one((record(i) for i in ids if slot_of(record(i))==slot_of(template)),'Grouped control counterpart')
                            for ids in children]]
    if 'name'in op:
        name=name_value(op['name'])
        if any(control_name(r)==name for r in records if r not in members):
            raise ValueError('HUD control name is already in use')
    if 'text'in op and not isinstance(op['text'],str):raise ValueError('HUD content must be text')
    if 'hidden'in op and type(op['hidden']) is not bool:raise ValueError('HUD hidden must be boolean')
    coordinates={}
    for key,axis,limits,is_size in (('position_px',504,[800,450],False),('size_px',505,[1600,900],True)):
        if key in op:
            rect_pair(op[key],key,limits,size=is_size)
            coordinates[axis]={i:(5,v or None) for i,v in enumerate(op[key],501)}
    for control in members:
        native={get(b,502,0) for b in vals(fields(control),505)}
        if len(native & {v[0] for v in CONTROLS.values()})!=1:
            raise ValueError('Select a calibrated native text, button, progress, timer or scoreboard control')
        revised=control
        def payload_edit(kind,tag,mutator):
            block=one((b for b in vals(fields(revised),505) if get(b,502,0)==kind),'HUD property '+str(kind))
            override=get(block,503)
            value=get(override or b'',tag)
            if value is None or get(override,502,0)!=kind:
                raise ValueError('Uncalibrated native HUD property '+str(kind))
            new_override=replace_message(override,tag,value,mutator(value))
            return replace_message(revised,505,block,replace_message(block,503,override,new_override))
        if coordinates:
            def place(wrapper):
                frames=get(wrapper,12)
                if frames is None:raise ValueError('Native HUD frame data is missing')
                states=vals(fields(frames),501)
                if len(states)!=4 or {get(r,501,0,0) for r in states}!={0,1,2,3}:
                    raise ValueError('Native HUD requires four known device frames')
                for state in states:
                    box=get(state,502)
                    for axis,values in coordinates.items():
                        previous=get(box,axis,default=b'')
                        box=patch_fields(box,{axis:(2,patch_fields(previous,values))})
                    frames=replace_message(frames,501,state,replace_message(state,502,get(state,502),box))
                return replace_message(wrapper,12,get(wrapper,12),frames)
            revised=payload_edit(12,13,place)
        if 'text'in op:
            revised=payload_edit(25,19,lambda v:patch_fields(v,{505:(2,patch_fields(get(v,505,default=b''),
                                                                     {501:(2,op['text'].encode('utf-8'))}))}))
        if 'hidden'in op:
            revised=payload_edit(23,14,lambda v:patch_fields(v,{502:(0,1 if op['hidden'] else None)}))
        if 'name'in op:
            name_block=one((b for b in vals(fields(revised),505) if (get(b,501,0),get(b,502,0))==(2,15)),'HUD name')
            value=get(name_block,12)
            named=patch_fields(value,{501:(2,name.encode('utf-8'))})
            revised=replace_message(revised,505,name_block,replace_message(name_block,12,value,named))
        section=replace_message(section,502,control,revised)
    return set_section(data,9,section), {'template_id':op['template_id'],'control_ids':[get(r,501,0)for r in members],
                                        'changes':{k:op[k]for k in changes if k in op}}


def add_native_global_timer(data, op):
    schema(op, ('op','name','seconds','countdown','section','entity_id'), ('name','seconds','section','entity_id'))
    _, root = container(data)
    timers = unique(root,12,default=b'')
    label = name_value(op['name'])
    if any(get(r,1,default=b'').decode('utf-8')==label for r in vals(fields(timers),1)):
        raise ValueError('Global timer name is already in use')
    sec = number(op['seconds'],'Timer seconds')
    countdown = op.get('countdown',True)
    if not 0<sec<=86400 or type(countdown) is not bool:
        raise ValueError('Global timers require 0 < seconds <= 86400 and a boolean countdown')
    section_id = op['section']
    if type(section_id) is not int or section_id not in (4,5):
        raise ValueError('Timer holder requires section 4 or 5')
    section = unique(root,section_id,default=b'')
    holder = select_record(section,1,op['entity_id'],'Timer holder')
    is_player = section_id==4 and get(holder,2,0)==1000000
    is_level = section_id==5 and get(get(holder,2,default=b''),1,0)==10003004
    if not (is_player or is_level):
        raise ValueError('Global timer holder must be a player template or the level entity')
    ordinal = max(len(vals(fields(timers),1)),*(get(r,501,0,0) for r in vals(fields(timers),1)),0)+1
    row = text(1,label)+flt(2,sec)+(integer(3,1) if countdown else b'')+integer(501,ordinal)
    field = 8 if is_player else 7
    typed = typed_record(holder,field,16,strict=True)
    if typed is None:
        revised = holder+msg(field,integer(1,16)+integer(2,1)+msg(26,text(1,label)))
    else:
        body = get(typed,26)
        if body is None or get(typed,2,0)!=1 or label.encode('utf-8') in vals(fields(body),1):
            raise ValueError('Uncalibrated or duplicated global timer binding')
        revised = replace_message(holder,field,typed,replace_message(typed,26,body,body+text(1,label)))
    data = set_section(data,section_id,replace_message(section,1,holder,revised))
    return set_section(data,12,timers+msg(1,row)), {'name':label,'seconds':sec,'countdown':countdown,'entity_id':op['entity_id']}


HUD_EDITS = {f.__name__: f for f in (native_hud,set_native_hud_control,add_native_global_timer)}
