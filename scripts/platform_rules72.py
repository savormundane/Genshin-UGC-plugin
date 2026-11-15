"""Source-backed declared semantics, never native binary field calibration."""
import math
from authoring_io import schema

FIELDS={
 'disturbance':('entity_kind','devices','selected_index','expected_active_index'),
 'push_collision':('entity_kind','supported','hook','shape','center','scale','rotation','index','custom_native_enabled','controls_native'),
 'filter_semantics':('active_templates','include','exclude','tags','expected_match','owner_resolution','friendly_includes_self'),
 'camera_takeover':('entity_kind','skill_camera','expected_during','expected_after'),
 'clear_velocity':('enabled','expected_clears_force'),
 'translations':('languages','entries'),
 'arrival':('radius','accept_precise_sliding')}
SOURCES={'disturbance':['mhr24urr9kjq'],'push_collision':['mh223e9ljnpu','mhb8nl0w8cao'],
 'filter_semantics':['mh3lmk9tmrky'],'camera_takeover':['mhfua005zpeg'],
 'clear_velocity':['mho81frl33im'],'translations':['mhk59aiqtwyk'],'arrival':['mh3rgo0c16c8']}

def check(obj,mode):
    kind=obj['kind'];rows=[]
    def emit(rule,passed,detail):
        rows.append({'object':obj['id'],'rule':kind+'.'+rule,'status':'not_checked'if passed is None else'passed'if passed else'failed','detail':detail})
    def number(v):return type(v)in(int,float)and math.isfinite(v)
    def strings(v):return isinstance(v,list)and all(isinstance(x,str)and x for x in v)and len(set(v))==len(v)
    def flag(v):
        if type(v)is not bool:raise ValueError('Boolean semantic expectation required')
    if kind=='disturbance':
        emit('dynamic_object',obj['entity_kind']=='dynamic_object','Only dynamic objects support this component')
        devices=obj['devices']
        if not isinstance(devices,list):raise ValueError('Devices must be a list')
        indices=[];active=0
        for d in devices:
            schema(d,('index','type','initial_active','expected_duration'),('index','type','initial_active'))
            if type(d['index'])is not int or d['index']<0 or d['index']in indices:raise ValueError('Unique nonnegative device index required')
            if d['type']not in ('launcher','tractor','force_field'):raise ValueError('Unknown disturbance type')
            flag(d['initial_active']);indices.append(d['index']);active+=d['initial_active']
            if 'expected_duration'in d:
                if not number(d['expected_duration'])or d['expected_duration']<0:raise ValueError('Finite nonnegative duration required')
                if d['type']=='tractor':emit('tractor_duration',d['expected_duration']<=30,{'index':d['index'],'runtime_max_seconds':30,'scope':'expected runtime duration, not editor field maximum'})
        emit('single_initial',active<=1,{'active':active})
        for key in ('selected_index','expected_active_index'):
            if obj[key]is not None and (type(obj[key])is not int or obj[key]<0):raise ValueError('Index must be null or nonnegative integer')
        expected=obj['selected_index']if obj['selected_index']in indices else None
        emit('selection',obj['expected_active_index']==expected,{'effective_index':expected,'missing_or_null_disables_all':True})
    elif kind=='push_collision':
        emit('complex_creature',obj['entity_kind']=='complex_creature','Only some complex creatures support this component')
        if obj['supported']is not None:flag(obj['supported'])
        emit('availability',obj['supported'],{'basis':'explicit caller declaration; verify supported creature in editor'})
        emit('hook',isinstance(obj['hook'],str)and bool(obj['hook'].strip()),'Attachment hook required')
        emit('shape',obj['shape']in ('box','sphere','capsule'),'box/sphere/capsule')
        for key in ('center','scale','rotation'):
            v=obj[key]
            if not isinstance(v,list)or len(v)!=3 or not all(number(x)for x in v):raise ValueError('Finite XYZ vector required: '+key)
        if type(obj['index'])is not int or obj['index']<0:raise ValueError('Nonnegative collision index required')
        flag(obj['controls_native']);flag(obj['custom_native_enabled'])
        emit('native_switch_prerequisite',not obj['controls_native']or obj['custom_native_enabled'],'Native collision toggle requires custom native collision enabled; not a prerequisite for extra collision')
        emit('declared_transform',True,{'center':obj['center'],'scale':obj['scale'],'rotation':obj['rotation'],'native_written':False})
    elif kind=='filter_semantics':
        if type(obj['active_templates'])is not int or obj['active_templates']<0:raise ValueError('Nonnegative template count required')
        emit('single_template',obj['active_templates']<=1,'At most one effective template')
        if not all(strings(obj[k])for k in ('include','exclude','tags')):raise ValueError('Unique nonempty tag strings required')
        flag(obj['expected_match']);flag(obj['friendly_includes_self'])
        matched=set(obj['include'])<=set(obj['tags'])and not set(obj['exclude'])&set(obj['tags'])
        emit('tags',obj['expected_match']==matched,{'match':bool(matched),'include':'all','exclude':'any'})
        emit('owner',obj['owner_resolution']=='topmost_or_self','Use topmost owner, or the entity itself if none')
        emit('friendly',not obj['friendly_includes_self'],'Friendly camps exclude own camp')
    elif kind=='camera_takeover':
        flag(obj['skill_camera'])
        if mode!='classic'or obj['entity_kind']!='object':emit('context',None,'Documented rule applies to classic object camera only')
        elif obj['skill_camera']:
            emit('during',obj['expected_during']=='skill','Qualifying skill camera takes over')
            emit('after',obj['expected_after']=='configured_object','Return to configured object camera after skill')
        else:emit('context',None,'No qualifying skill camera declared')
    elif kind=='clear_velocity':
        flag(obj['enabled']);flag(obj['expected_clears_force'])
        emit('force_preserved',not obj['expected_clears_force'],'Clearing velocity does not remove sustained forces')
    elif kind=='translations':
        if not strings(obj['languages'])or not obj['languages']:raise ValueError('Required language list must be nonempty')
        if not isinstance(obj['entries'],list)or not obj['entries']:raise ValueError('Translation entries required')
        seen=set()
        for entry in obj['entries']:
            schema(entry,('id','origin','translations'),('id','origin','translations'))
            if not isinstance(entry['id'],str)or not entry['id']or entry['id']in seen:raise ValueError('Unique translation entry ID required')
            seen.add(entry['id'])
            if entry['origin']not in ('text','graph_variable','instance_override'):raise ValueError('Unknown translation origin')
            values=entry['translations']
            if not isinstance(values,dict)or any(not isinstance(k,str)or not isinstance(v,str)for k,v in values.items()):raise ValueError('Translation map must contain strings')
            missing=[lang for lang in obj['languages']if not values.get(lang,'').strip()]
            emit('coverage',not missing,{'entry':entry['id'],'origin':entry['origin'],'missing':missing,'scope':'declared texts only; no automatic native extraction'})
    elif kind=='arrival':
        if not number(obj['radius'])or obj['radius']<0:raise ValueError('Finite nonnegative arrival radius required')
        flag(obj['accept_precise_sliding'])
        emit('zero_radius',True if obj['radius']>0 or obj['accept_precise_sliding']else None,'Zero radius triggers precise movement and sliding; explicit acknowledgement required')
    return rows
