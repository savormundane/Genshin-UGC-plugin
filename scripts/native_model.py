"""Restricted interpreter of emitted native graphs. Unknown nodes fail explicitly."""
from collections import Counter, defaultdict
from copy import deepcopy
import math
import struct
from native_core import model,get,slot,ref,node_catalog,definition_id,port_type
from level_inventory import container,fields,vals

CONTAINER_TYPES=(7,8,9,10,11,13,15,22,23,24,25,26,27)

def default_value(typ):
    if typ in(7,8,9,10,11,13,15,22,23,24,26):return []
    if typ in(1,2,3,17,20,21):return 0
    if typ==4:return False
    if typ==5:return 0.0
    if typ==6:return ''
    if typ==12:return {'x':0.0,'y':0.0,'z':0.0}
    if typ==27:return {}
    raise ValueError('Unknown native variable default type '+str(typ))

def constant(value):
    cls=get(value,1,0)
    if cls==10000:return constant(get(get(value,110,default=b''),2,default=b''))
    if cls in (1,2,6):
        n=get(get(value,{1:101,2:102,6:106}[cls],default=b''),1,0,0)
        return n-2**64 if cls==2 and n>=2**63 else n
    if cls==4:
        raw=get(get(value,104,default=b''),1,5)
        return struct.unpack('<f',raw)[0]if raw else 0.0
    if cls==5:return get(get(value,105,default=b''),1,default=b'').decode('utf-8')
    if cls==7:
        vector=get(get(value,107,default=b''),1,default=b'')
        return {name:struct.unpack('<f',get(vector,i,5))[0]if get(vector,i,5)is not None else 0.0 for i,name in enumerate(('x','y','z'),1)}
    if cls in (10001,10002):return [constant(v)for v in vals(fields(get(value,108 if cls==10001 else 109,default=b'')),1)]
    if cls is None:return 0
    raise ValueError('Unsupported native constant class '+str(cls))

class UncalibratedVariable(ValueError):
    def __init__(self, entity, variable, reason):
        self.entity=entity
        self.variable=variable
        super().__init__(f'Native variable {variable!r} on entity {entity} has no calibrated initial value: {reason}')


class UncalibratedRoute(ValueError):
    """The native record or graph is outside the route model's calibrated scope."""


class NativeModel:
    def __init__(self,data,initial=None,graph_ids=None,instances=None,entity_guids=None,level_entity=None,*,
                 mounted_only=False,timer_index_base=1):
        self.model=model(data);self.out=[];self.logs=[];self.achievements={};self.work=0
        self.entity_guids={}
        for entity,guid in (entity_guids or {}).items():
            if not str(entity).isdigit() or type(guid)!=int or guid<0:raise ValueError('Invalid entity GUID mapping')
            self.entity_guids[str(entity)]=guid
        self.event_log=[];self.created_entities=set();self.removed_entities=set();self.level_entity=level_entity
        self.model_visibility={}
        self.scene_data=data;self.scene_objects=None;self.linear_motions={}
        entity_counts=Counter(e['entity_id'] for e in self.model['entities'] if e['section']==5)
        self.entities={ident for ident,count in entity_counts.items() if ident is not None and count==1}
        self.roles={};self.signal_sizes={};self.graphs=[g for g in self.model['graphs']if graph_ids is None or g['id']in graph_ids]
        graph_map={g['id']:g for g in self.graphs}
        origins = defaultdict(list)
        template_counts = Counter(e['entity_id'] for e in self.model['entities'] if e['section'] == 4)
        template_mounts = defaultdict(list)
        for mount in self.model['mounts']:
            graph, owner = mount['graph_id'], mount['entity_id']
            if graph not in graph_map:
                continue
            if mount['section'] == 5:
                origins[graph,owner].append({'section':5,'entity_id':owner})
            elif template_counts[owner] == 1:
                template_mounts[owner].append(graph)
        parent_templates = {}
        _, root = container(data)
        for section in vals(root,5):
            for row in vals(fields(section),1):
                owner = get(row,1,0)
                locators = vals(fields(row),2)
                if owner not in self.entities or len(locators) != 1 or get(locators[0],2,0,0) != 0:
                    continue
                template = get(locators[0],1,0)
                if template_counts[template] == 1:
                    parent_templates[owner] = template
        if instances is None or mounted_only:
            for owner,template in parent_templates.items():
                for graph in template_mounts.get(template,()):
                    origins[graph,owner].append({'section':4,'entity_id':template})
        self.initialize_variables(initial, parent_templates, {k for k,v in template_counts.items() if k is not None and v==1})
        mounts = [{'graph_id':graph,'owner_entity':owner} for graph,owner in origins]
        if mounted_only:
            if self.model['format']!='gil' or not graph_ids or set(graph_ids)!=set(graph_map):
                raise ValueError('Native-only simulation requires exact graph IDs from a GIL')
            if any(get(get(g['raw'],1,default=b''),2,0)!=20000 for g in self.graphs):
                raise ValueError('Native-only simulation requires ordinary server graphs')
            if (any(owner not in self.entities or len(sources)!=len({source['section'] for source in sources})
                    for (_,owner),sources in origins.items()) or {graph for graph,_ in origins}!=set(graph_map)):
                raise ValueError('Selected server graph must have unique native placed-entity mounts')
        if instances is not None:
            seen=set()
            for item in instances:
                if set(item)!={'graph_id','owner_entity'}or item['graph_id']not in graph_map or type(item['owner_entity'])!=int:raise ValueError('Invalid graph instance')
                key=(item['graph_id'],item['owner_entity'])
                if key in seen:raise ValueError('Duplicate graph instance')
                if mounted_only and key not in origins:
                    raise ValueError('Selected graph instance is not mounted to that entity in the GIL')
                seen.add(key)
            mounts=instances
        if mounted_only and {m['graph_id'] for m in mounts}!=set(graph_map):
            raise ValueError('Select a mounted instance for every requested graph')
        self.mount_origins=[{**m,'origins':origins.get((m['graph_id'],m['owner_entity']),[])} for m in mounts]
        self.instances=[(graph_map[m['graph_id']],m['owner_entity'])for m in mounts]
        if level_entity is not None and(type(level_entity)is not int or level_entity<0 or not any(owner==level_entity for _,owner in self.instances)):
            raise ValueError('Level entity requires a modeled graph instance')
        mounted={m['graph_id']for m in mounts}
        self.instances.extend((g,None)for g in self.graphs if g['id']not in mounted)
        self.catalog=node_catalog()[0];self.locals={};self.executed_graphs=set();self.executed_instances=set()
        from native_timers import TimerClock
        self.timers=TimerClock(timer_index_base)
        self.data_edges={}
        for graph in self.graphs:
            incoming={}
            for ident,n in graph['nodes'].items():
                for p in vals(fields(n),4):
                    kind,index=slot(p)
                    if kind not in(3,4):continue
                    for edge in vals(fields(p),5):
                        remote=get(edge,2,default=b'');other=get(edge,1,0)
                        rk,ri=get(remote,1,0,0),get(remote,2,0,0)
                        if (kind,rk)not in((3,4),(4,3))or other not in graph['nodes']:raise ValueError('Invalid native data edge')
                        consumer,provider=((ident,index),(other,ri))if kind==3 else((other,ri),(ident,index))
                        incoming.setdefault(consumer,set()).add(provider)
            if any(len(providers)!=1 for providers in incoming.values()):raise ValueError('Ambiguous native data input')
            self.data_edges[graph['id']]={key:next(iter(value))for key,value in incoming.items()}
        settings=get(data[20:-4],25,default=b'');achievement_settings=get(settings,3,default=b'')
        self.goals={get(a,1,0):get(a,6,0,1)for a in vals(fields(achievement_settings),4)}
        for signal in self.model['signals']:
            name=get(signal,3,default=b'').decode('utf-8');params=[get(p,1,default=b'').decode('utf-8')for p in vals(fields(signal),4)]
            if name in self.signal_sizes:raise ValueError('Duplicate native signal name '+name)
            self.signal_sizes[name]=len(params)
            for role,key in enumerate((1,2,7,9)):
                r=get(signal,key)
                if r:
                    if ref(r)in self.roles:raise ValueError('Duplicate native signal role ID')
                    self.roles[ref(r)]=(name,role,params)
        self.listeners={}
        for graph,owner in self.instances:
            for event_id,event in graph['nodes'].items():
                ident=definition_id(event,self.model['definitions']);role=self.roles.get(ident)
                actual=role[0]if role and role[1]==1 else None
                if ident==300001:
                    signal_pin=next((p for p in vals(fields(event),4)if slot(p)==(5,0)),None)
                    actual=constant(get(signal_pin,3,default=b''))if signal_pin else None
                    if actual not in self.signal_sizes:raise ValueError('Unknown native listener signal '+str(actual))
                if actual is not None:self.listeners.setdefault(actual,[]).append((graph,owner,event_id))
    def initialize_variables(self, initial, parent_templates, template_ids):
        from native_variables import scalar_default, scalar_payload
        declarations=defaultdict(dict)
        for record in self.model['custom_variables']['records']:
            values=declarations[record['section'],record['entity_id']]
            name=record['name']
            if name in values:
                values[name]=(False, 'ambiguous declarations')
                continue
            try:
                values[name]=(True,scalar_default(scalar_payload(record),record['type_id']))
            except (ValueError,struct.error) as exc:
                values[name]=(False,str(exc))
        self.db={}
        self.uncalibrated_variables={}
        owners=self.entities | template_ids
        for owner in sorted(owners):
            defaults=declarations.get((4,parent_templates.get(owner,owner if owner not in self.entities else None)),{})
            overrides=declarations.get((5,owner),{}) if owner in self.entities else {}
            for name,(known,value) in (defaults | overrides).items():
                if known:
                    self.db.setdefault(str(owner),{})[name]=value
                else:
                    self.uncalibrated_variables[str(owner),name]=value
        if initial is not None:
            if not isinstance(initial,dict) or any(not isinstance(v,dict) for v in initial.values()):
                raise ValueError('Native initial variables require an object of entity variable maps')
            for owner,values in initial.items():
                self.db.setdefault(str(owner),{}).update(deepcopy(values))
        self.persisted=deepcopy(self.db)

    def variable(self, entity, name, *, fallback_type=None):
        values=self.db.get(str(entity),{})
        if name in values:
            return values[name]
        reason=self.uncalibrated_variables.get((str(entity),name))
        if reason is not None:
            raise UncalibratedVariable(entity,name,reason)
        if fallback_type is not None:
            return default_value(fallback_type)
        raise ValueError(f'Native variable {name!r} is absent on entity {entity}')

    def title(self,n):
        ident=definition_id(n,self.model['definitions']);d=self.model['definitions'].get(ident)
        return get(d,200,default=b'').decode('utf-8')if d else self.catalog.get(ident,{}).get('Name','Unknown_'+str(ident))
    def builtin_event(self,n,expected):
        generic=ref(get(n,2,default=b''))
        if generic!=expected or generic in self.model['definitions']:return False
        from native_ports import reference_error
        error=reference_error(n,self.model['definitions'])
        if error:raise ValueError('Invalid native event reference: '+error)
        return True
    def request(self,name,params,source):
        # A transport delivery owns its payload; graph-local container edges keep references.
        pending=[]
        if name not in self.signal_sizes:raise ValueError('Unknown native signal '+name)
        if len(params)!=self.signal_sizes[name]:raise ValueError('Native signal parameter count mismatch '+name)
        for graph,owner,event_id in self.listeners.get(name,[]):
            pending.append((graph,owner,event_id,source,deepcopy(params),None))
        if not pending:raise ValueError('Native signal handler missing '+name)
        return self._dispatch(pending)

    def entity_created(self,entity):
        if type(entity)is not int or entity<0:raise ValueError('Invalid created entity')
        if entity in self.removed_entities:raise ValueError('Removed entity identity cannot be reused')
        if entity in self.created_entities:raise ValueError('Entity creation already dispatched')
        instances=[(graph,owner)for graph,owner in self.instances if owner==entity]
        if not instances:raise ValueError('Created entity has no modeled graph instance')
        pending=[]
        for graph,owner in instances:
            for ident,n in graph['nodes'].items():
                if self.builtin_event(n,71):
                    pending.append((graph,owner,ident,None,[],{'lifecycle':'entity_created'}))
        if not pending:raise ValueError('Entity creation handler missing')
        self.created_entities.add(entity)
        emitted=self._dispatch(pending)
        self.event_log.append({'lifecycle':'entity_created','entity':entity,'time':self.timers.time,
                               'handlers':len(pending)})
        return emitted

    def entity_removed(self,entity):
        if type(entity)is not int or entity<0:raise ValueError('Invalid removed entity')
        if self.level_entity is None:raise ValueError('Entity removal requires explicit level_entity')
        if entity==self.level_entity:raise ValueError('Level entity removal is not modeled')
        if entity in self.removed_entities:raise ValueError('Entity already removed')
        if not any(owner==entity for _,owner in self.instances):raise ValueError('Removed entity has no modeled graph instance')
        if str(entity)not in self.entity_guids:raise ValueError('Removed entity GUID mapping required')
        guid=self.entity_guids[str(entity)];pending=[]
        for graph,owner in self.instances:
            if owner!=self.level_entity:continue
            for ident,n in graph['nodes'].items():
                if self.builtin_event(n,72):
                    pending.append((graph,owner,ident,None,[],{'lifecycle':'entity_removed','guid':guid}))
        self.removed_entities.add(entity)
        self.instances=[(graph,owner)for graph,owner in self.instances if owner!=entity]
        for name,listeners in self.listeners.items():self.listeners[name]=[item for item in listeners if item[1]!=entity]
        for key in list(self.timers.entries):
            if key[0]==entity:del self.timers.entries[key]
        self.linear_motions.pop(entity,None)
        emitted=self._dispatch(pending)
        self.event_log.append({'lifecycle':'entity_removed','entity':entity,'guid':guid,'time':self.timers.time,'handlers':len(pending)})
        return emitted

    def position_m(self,entity):
        if entity not in self.entities or entity in self.removed_entities:
            raise ValueError('Position requires a live placed entity')
        if self.scene_objects is None:
            from level_inventory import container
            from native_scene import spatial_objects
            self.scene_objects=spatial_objects(*container(self.scene_data))
        detail=self.scene_objects.get(('entity',entity))
        if detail is None:
            raise ValueError('Entity position is outside the calibrated scene layout')
        motion=self.linear_motions.get(entity)
        if motion is None:
            return detail['transform']['position_m'].copy()
        elapsed=min(self.timers.time-motion['time'],motion['seconds'])
        return [origin+speed*elapsed for origin,speed in zip(motion['position_m'],motion['velocity_m_s'])]

    def walk_route(self, entity, owner, trigger_id, points, report):
        from native_scene import route_box_entry, vector
        from native_scene_edits import read_box_trigger

        if (any(type(ident) is not int or ident not in self.entities or ident in self.removed_entities
                for ident in (entity, owner)) or entity == owner):
            raise ValueError('Route requires distinct live entrant and trigger-owner entities')
        if type(trigger_id) is not int or trigger_id < 1:
            raise ValueError('Route trigger ID must be a positive integer')
        if not isinstance(points, list) or not 2 <= len(points) <= 4096:
            raise ValueError('Route requires 2 to 4096 world-space points')
        points = [vector(point, 'Route point') for point in points]
        try:
            position = self.position_m(owner)
            pose = self.scene_objects['entity', owner]['transform']
            if owner in self.linear_motions or pose['scale'] != [1, 1, 1] or any(
                    angle % 360 for angle in pose['rotation_deg']):
                raise ValueError('Route coverage requires a stationary unrotated trigger owner at unit scale')
            offset, size = read_box_trigger(self.scene_data, owner, trigger_id)
            center = [coordinate + delta for coordinate, delta in zip(position, offset)]
            crossing = route_box_entry(points, center, size)
        except ValueError as exc:
            report['geometry']['reason'] = str(exc)
            raise UncalibratedRoute(str(exc)) from exc
        report['geometry'] = {'status': 'hit' if crossing else 'missed', 'center_m': center, 'size_m': size}
        if not crossing:
            report['node_execution']['reason'] = 'The route did not enter the box'
            return []
        report['geometry']['entry'] = crossing
        mounted = {row['graph_id'] for row in self.mount_origins
                   if row['owner_entity'] == owner and row['origins']}
        pending = []
        handlers = []
        for graph, instance in self.instances:
            if instance != owner or graph['id'] not in mounted or get(get(graph['raw'], 1, default=b''), 2, 0) != 20000:
                continue
            for ident, node in graph['nodes'].items():
                if self.builtin_event(node, 92):
                    handlers.append({'graph_id': graph['id'], 'node_id': ident})
                    pending.append((graph, owner, ident, None, [], {'collision_enter': (entity, trigger_id)}))
        report['node_execution']['handlers'] = handlers
        if not pending:
            reason = 'No selected, natively mounted server graph has a calibrated collision-entry node on this trigger owner'
            report['node_execution']['reason'] = reason
            raise UncalibratedRoute(reason)
        try:
            emitted = self._dispatch(pending)
        except ValueError as exc:
            report['node_execution']['reason'] = str(exc)
            if str(exc).startswith(('Unsupported native execution', 'Unsupported native output')):
                raise UncalibratedRoute(str(exc)) from exc
            report['node_execution']['status'] = 'failed'
            raise
        report['node_execution']['status'] = 'passed'
        return emitted

    def tick(self,dt):
        emitted=[]
        def fire(entity,name,index,cycle):
            pending=[]
            for graph,owner in self.instances:
                if owner!=entity:continue
                for ident,n in graph['nodes'].items():
                    if self.builtin_event(n,83):pending.append((graph,owner,ident,None,[],{'timer':True,'name':name,'index':index,'cycle':cycle}))
            self.event_log.append({'timer':name,'entity':entity,'index':index,'cycle':cycle,'time':self.timers.time})
            emitted.extend(self._dispatch(pending))
        self.timers.tick(dt,fire)
        return emitted

    def _dispatch(self,pending):
        emitted=[];steps=0
        # FIFO model scheduling: generated variable events run after the active event flow.
        for graph,owner,event_id,source,params,change in pending:
            self.executed_graphs.add(graph['id'])
            self.executed_instances.add((graph['id'],owner))
            nodes=graph['nodes'];self.locals={};constructed={};active=set();loops={}
            def pin(n,k,i):return next((p for p in vals(fields(n),4)if slot(p)==(k,i)),None)
            def inp(n,i):
                edge=self.data_edges[graph['id']].get((get(n,1,0),i))
                if edge is not None:return output(*edge)
                p=pin(n,3,i)
                if p is None:raise ValueError('Native input absent '+str((get(n,1,0),i)))
                v=constant(get(p,3,default=b''));return bool(v)if get(p,4,0)==4 else v
            def output(ident,index=0):
                if ident==event_id:
                    if change is not None and 'collision_enter' in change:
                        entrant, trigger_id = change['collision_enter']
                        if index in (0, 2):
                            return entrant if index == 0 else owner
                        if index in (1, 3):
                            key = str(entrant if index == 1 else owner)
                            if key not in self.entity_guids:
                                raise ValueError('Collision-entry GUID output requires entity_guids mapping')
                            return self.entity_guids[key]
                        if index == 4:
                            return trigger_id
                        raise ValueError('Unknown collision-entry event output')
                    if change is not None and change.get('lifecycle')=='entity_removed':
                        if index!=0:raise ValueError('Unknown entity removal output')
                        return change['guid']
                    if index in(0,1):
                        if owner is None:raise ValueError('Native event identity requires a mounted graph instance')
                        if index==0:return owner
                        if str(owner)not in self.entity_guids:raise ValueError('Native event GUID requires entity_guids mapping')
                        return self.entity_guids[str(owner)]
                    if change is not None:
                        if change.get('lifecycle'):raise ValueError('Unknown entity creation output')
                        if change.get('timer'):
                            if index not in(2,3,4):raise ValueError('Unknown timer event output')
                            return change[{2:'name',3:'index',4:'cycle'}[index]]
                        if index==2:return change['name']
                        if index not in(3,4):raise ValueError('Unknown variable event output')
                        if change['type']in CONTAINER_TYPES:raise ValueError('Container variable events have no before/after values')
                        return change['before'if index==3 else'after']
                    if index==2:return source
                    if index<3 or index-3>=len(params):raise ValueError('Unknown signal event output')
                    return params[index-3]
                key=(ident,index)
                if key in active:raise ValueError('Native data cycle')
                active.add(key)
                try:
                    n=nodes[ident];title=self.title(n)
                    args=lambda:[inp(n,i)for i in sorted({slot(p)[1]for p in vals(fields(n),4)if slot(p)[0]==3}|{i for node_id,i in self.data_edges[graph['id']]if node_id==ident})]
                    if title=='Finite_Loop':
                        if index!=0 or ident not in loops:raise ValueError('Finite loop output requires an active iteration')
                        return loops[ident]['value']
                    if title=='Get_Custom_Variable':
                        entity,variable_name=inp(n,0),inp(n,1)
                        if entity in self.removed_entities:raise ValueError('Variable target entity removed')
                        return self.variable(entity,variable_name,fallback_type=port_type(n,4,0,self.model['definitions']))
                    if title=='Get_Corresponding_Value_From_List':
                        value,index=inp(n,0),inp(n,1)
                        if type(index)!=int or not 0<=index<len(value):raise ValueError('Native list index out of range')
                        return value[index]
                    if title=='Get_List_Length':return len(inp(n,0))
                    if title=='Assembly_List':
                        if ident not in constructed:constructed[ident]=[inp(n,i+1)for i in range(inp(n,0))]
                        return constructed[ident]
                    if title=='Get_Self_Entity':
                        if owner is None:raise ValueError('Get_Self_Entity requires a mounted graph instance or explicit owner')
                        return owner
                    if 'Achievement'in title and ('Completed'in title or 'Complete'in title):return self.achievements.get((inp(n,0),inp(n,1)),0)>=self.goals.get(inp(n,1),1)
                    if title=='Get_Local_Variable':
                        if index==0:return ('local',ident)
                        if ident not in self.locals:self.locals[ident]=inp(n,0)
                        return self.locals[ident]
                    if title in ('拼装结构体','Assembly_Structure'):
                        d=self.model['definitions'][definition_id(n,self.model['definitions'])];ports=vals(fields(d),102)
                        return {get(p,1,default=b'').decode('utf-8'):inp(n,get(get(p,3,default=b''),2,0,0))for p in ports}
                    if title in ('拆分结构体','Split_Structure'):
                        d=self.model['definitions'][definition_id(n,self.model['definitions'])];p=next(p for p in vals(fields(d),103)if get(get(p,3,default=b''),2,0,0)==index)
                        return inp(n,0)[get(p,1,default=b'').decode('utf-8')]
                    a=args()
                    if title=='Equal':return a[0]==a[1]
                    if title in ('Less_Than','Less'):return a[0]<a[1]
                    if title in ('Less_Than_Or_Equal','Less_Than_Or_Equal_To','Less_Than_or_Equal_To'):return a[0]<=a[1]
                    if title in ('Greater_Than','Greater'):return a[0]>a[1]
                    if title in ('Greater_Than_Or_Equal','Greater_Than_Or_Equal_To','Greater_Than_or_Equal_To'):return a[0]>=a[1]
                    if title in ('Addition','Add'):return a[0]+a[1]
                    if title in ('Subtraction','Subtract'):return a[0]-a[1]
                    if title in ('Multiplication','Multiply'):return a[0]*a[1]
                    if title in ('Logical_Not','Logical_NOT_Operation','Not'):return not a[0]
                    if title in ('Logical_And','Logical_AND_Operation','And'):return a[0]and a[1]
                    if title in ('Logical_Or','Logical_OR_Operation','Or'):return a[0]or a[1]
                    raise ValueError('Unsupported native output '+title)
                finally:active.remove(key)
            def follow(n,branch):
                p=pin(n,2,branch)
                if p:
                    for edge in vals(fields(p),5):
                        execute(get(edge,1,0),get(get(edge,2,default=b''),2,0,0))
                        if any(loop['broken']for loop in loops.values()):return
            def execute(ident,entry=0):
                nonlocal steps
                steps+=1;self.work+=1
                if steps>10000:raise ValueError('Native execution budget exceeded')
                n=nodes[ident];title=self.title(n);role=self.roles.get(definition_id(n,self.model['definitions']));branch=0
                if ident!=event_id:
                    if title=='Finite_Loop':
                        if entry==1:
                            if ident not in loops:raise ValueError('Cannot break an inactive finite loop')
                            loops[ident]['broken']=True;return
                        if entry!=0 or ident in loops:raise ValueError('Invalid finite loop entry')
                        first,last=inp(n,0),inp(n,1)
                        if type(first)!=int or type(last)!=int:raise ValueError('Finite loop bounds must be integers')
                        loops[ident]={'value':first,'broken':False}
                        for value in range(first,last+1):
                            steps+=1;self.work+=1
                            if steps>10000:raise ValueError('Native execution budget exceeded')
                            loops[ident]['value']=value;follow(n,0)
                            if any(loop['broken']for loop in loops.values()):break
                        del loops[ident]
                        follow(n,1);return
                    elif title=='Break_Loop':pass
                    elif title in('Start_Timer','Pause_Timer','Resume_Timer','Stop_Timer'):
                        target=inp(n,0)
                        if target in self.removed_entities:raise ValueError('Timer target entity removed')
                        if title=='Start_Timer':
                            source_guid=self.data_edges[graph['id']].get((ident,4))
                            if pin(n,3,4) is not None or source_guid is not None:
                                guid=inp(n,4)
                                if guid!=0:
                                    from native_ports import server_builtin
                                    if (not server_builtin(n,79) or source_guid!=(event_id,1) or target!=owner
                                            or guid!=self.entity_guids.get(str(owner))):
                                        raise ValueError('Timer extra GUID must match the target event owner')
                            self.timers.command('start',target,inp(n,1),inp(n,2),inp(n,3))
                        else:self.timers.command(title.split('_')[0].lower(),target,inp(n,1))
                    elif title=='Multiple_Branches' and self.builtin_event(n,3):
                        selected,labels=inp(n,0),inp(n,1)
                        if (type(selected) not in (int,str) or not isinstance(labels,list)
                                or any(type(label) is not type(selected) for label in labels)
                                or len(set(labels))!=len(labels)):
                            raise ValueError('Multiple branches require distinct typed case labels')
                        branch=labels.index(selected)+1 if selected in labels else 0
                    elif title=='Add_Uniform_Basic_Linear_Motion_Device' and self.builtin_event(n,84):
                        from native_ports import server_builtin
                        if not server_builtin(n,84):
                            raise ValueError('Uncalibrated linear motion node locator')
                        target,name,seconds,speed=(inp(n,i) for i in range(4))
                        if (type(target) is not int or not isinstance(name,str) or not name
                                or type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<=0
                                or not isinstance(speed,dict) or set(speed)!=set('xyz')
                                or any(type(v) not in (int,float) or not math.isfinite(v) for v in speed.values())):
                            raise ValueError('Linear motion requires an entity, name, positive duration and finite velocity')
                        now=self.timers.time
                        prior=self.linear_motions.get(target)
                        if prior and now<prior['time']+prior['seconds']:
                            raise ValueError('Overlapping linear motions are outside the modeled scope')
                        position=self.position_m(target)
                        if self.scene_objects['entity',target]['static']:
                            raise ValueError('Linear motion requires a dynamic placed entity')
                        motion={'motion':name,'entity':target,'time':now,'seconds':seconds,
                                'graph':graph['id'],'node':ident,'position_m':position,
                                'velocity_m_s':[speed[axis] for axis in 'xyz']}
                        self.linear_motions[target]=motion
                        self.event_log.append(motion)
                    elif title=='Activate_Disable_Model_Display' and self.builtin_event(n,308):
                        from native_ports import server_builtin
                        if not server_builtin(n,308):
                            raise ValueError('Uncalibrated model visibility node locator')
                        target,visible=inp(n,0),inp(n,1)
                        if type(target) is not int or target not in self.entities or target in self.removed_entities or type(visible) is not bool:
                            raise ValueError('Model visibility requires a placed entity and a Boolean value')
                        if (port_type(n,3,0,self.model['definitions']),port_type(n,3,1,self.model['definitions']))!=(1,4):
                            raise ValueError('Model visibility node input contract differs')
                        self.model_visibility[target]=visible
                        self.event_log.append({'entity':target,'model_visible':visible,'graph':graph['id'],
                                               'node':ident,'time':self.timers.time})
                    elif title=='Set_Custom_Variable':
                        target,key,value=inp(n,0),inp(n,1),inp(n,2)
                        if target in self.removed_entities:raise ValueError('Variable target entity removed')
                        typ=port_type(n,3,2,self.model['definitions'])
                        if typ is None:raise ValueError('Unresolved custom variable value type')
                        trigger=inp(n,3)if pin(n,3,3)is not None else True
                        if type(trigger)is not bool:raise ValueError('Variable event trigger must be boolean')
                        if pin(n,3,4)is not None and inp(n,4)!=trigger:raise ValueError('Variable event trigger mirror mismatch')
                        if trigger:
                            change_value=None
                            for listener_graph,listener_owner in self.instances:
                                if listener_owner!=target:continue
                                for listener_id,listener in listener_graph['nodes'].items():
                                    if self.title(listener)!='When_Custom_Variable_Changes':continue
                                    listener_type=port_type(listener,4,3,self.model['definitions'])
                                    if listener_type is None:raise ValueError('Unresolved variable event type')
                                    if listener_type!=typ:continue
                                    if change_value is None:
                                        before=None if typ in CONTAINER_TYPES else self.variable(target,key,fallback_type=typ)
                                        change_value={'name':key,'type':typ,'before':deepcopy(before),'after':deepcopy(value)}
                                    pending.append((listener_graph,listener_owner,listener_id,None,[],change_value))
                            self.event_log.append({'entity':target,'variable':key,'type':typ})
                        self.db.setdefault(str(target),{})[key]=value
                    elif title in('Clear_List','Insert_Value_Into_List','Remove_Value_From_List','Modify_Value_in_List','Concatenate_List'):
                        value=inp(n,0)
                        if not isinstance(value,list):raise ValueError('Native list operation requires a list')
                        if title=='Clear_List':value.clear()
                        elif title=='Concatenate_List':value.extend(list(inp(n,1)))
                        else:
                            index=inp(n,1);limit=len(value)+(1 if title=='Insert_Value_Into_List'else 0)
                            if type(index)!=int or not 0<=index<limit:raise ValueError('Native list index out of range')
                            if title=='Insert_Value_Into_List':value.insert(index,inp(n,2))
                            elif title=='Remove_Value_From_List':value.pop(index)
                            else:value[index]=inp(n,2)
                    elif title=='Set_Local_Variable':self.locals[inp(n,0)[1]]=inp(n,1)
                    elif title=='Double_Branch':branch=0 if inp(n,0)else 1
                    elif title=='Print_String':self.logs.append(str(inp(n,0)))
                    elif title in ('Set_Achievement_Progress_Tally','Change_Achievement_Progress_Tally'):
                        key=(inp(n,0),inp(n,1));self.achievements[key]=inp(n,2)+(self.achievements.get(key,0)if title.startswith('Change_')else 0)
                    elif role and role[1]==0:
                        if owner is None:raise ValueError('Server signal send requires a mounted graph instance')
                        payload=[inp(n,i)for i in range(len(role[2]))]
                        # Server-local delivery preserves container references. FIFO ordering
                        # is a model contract; it is not a claim about host scheduling.
                        for target_graph,target_owner,target_event in self.listeners.get(role[0],[]):
                            pending.append((target_graph,target_owner,target_event,owner,list(payload),None))
                    elif role and role[1]==2:
                        raise ValueError('Client graph send-to-server node cannot execute in the server model')
                    elif role and role[1]==3:
                        payload=deepcopy([inp(n,1+i)for i in range(len(role[2]))])
                        emitted.append({'name':role[0],'params':payload,'target':inp(n,0)})
                    else:raise ValueError(f"Unsupported native execution {title} in graph {graph['id']}, node {ident}")
                follow(n,branch)
            execute(event_id)
        self.out.extend(emitted);return emitted
    def settle(self):self.persisted=deepcopy(self.db)
    def reenter(self):self.db=deepcopy(self.persisted)
