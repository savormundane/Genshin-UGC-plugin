"""Restricted interpreter of emitted native graphs. Unknown nodes fail explicitly."""
from copy import deepcopy
import struct
from native_core import model,get,slot,ref,node_catalog,definition_id,port_type
from level_inventory import fields,vals

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

class NativeModel:
    def __init__(self,data,initial=None,graph_ids=None,instances=None,entity_guids=None,level_entity=None):
        self.model=model(data);self.db=deepcopy(initial or {});self.persisted=deepcopy(self.db);self.out=[];self.logs=[];self.achievements={};self.work=0
        self.entity_guids={}
        for entity,guid in (entity_guids or {}).items():
            if not str(entity).isdigit() or type(guid)!=int or guid<0:raise ValueError('Invalid entity GUID mapping')
            self.entity_guids[str(entity)]=guid
        self.event_log=[];self.created_entities=set();self.removed_entities=set();self.level_entity=level_entity
        self.roles={};self.signal_sizes={};self.graphs=[g for g in self.model['graphs']if graph_ids is None or g['id']in graph_ids]
        graph_map={g['id']:g for g in self.graphs}
        mounts=[{'graph_id':m['graph_id'],'owner_entity':m['entity_id']}for m in self.model['mounts']if m['section']==5 and m['graph_id']in graph_map]
        if instances is not None:
            seen=set()
            for item in instances:
                if set(item)!={'graph_id','owner_entity'}or item['graph_id']not in graph_map or type(item['owner_entity'])!=int:raise ValueError('Invalid graph instance')
                key=(item['graph_id'],item['owner_entity'])
                if key in seen:raise ValueError('Duplicate graph instance')
                seen.add(key)
            mounts=instances
        self.instances=[(graph_map[m['graph_id']],m['owner_entity'])for m in mounts]
        if level_entity is not None and(type(level_entity)is not int or level_entity<0 or not any(owner==level_entity for _,owner in self.instances)):
            raise ValueError('Level entity requires a modeled graph instance')
        mounted={m['graph_id']for m in mounts}
        self.instances.extend((g,None)for g in self.graphs if g['id']not in mounted)
        self.catalog=node_catalog()[0];self.locals={};self.executed_graphs=set()
        from native_timers import TimerClock
        self.timers=TimerClock()
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
        emitted=self._dispatch(pending)
        self.event_log.append({'lifecycle':'entity_removed','entity':entity,'guid':guid,'time':self.timers.time,'handlers':len(pending)})
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
                        if variable_name in self.db.get(str(entity),{}):return self.db[str(entity)][variable_name]
                        return default_value(port_type(n,4,0,self.model['definitions']))
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
                        if inp(n,0)in self.removed_entities:raise ValueError('Timer target entity removed')
                        if title=='Start_Timer':
                            if (pin(n,3,4)is not None or (ident,4)in self.data_edges[graph['id']])and inp(n,4)!=0:raise ValueError('Timer extra GUID input is not modeled')
                            self.timers.command('start',inp(n,0),inp(n,1),inp(n,2),inp(n,3))
                        else:self.timers.command(title.split('_')[0].lower(),inp(n,0),inp(n,1))
                    elif title=='Set_Custom_Variable':
                        target,key,value=inp(n,0),inp(n,1),inp(n,2)
                        if target in self.removed_entities:raise ValueError('Variable target entity removed')
                        typ=port_type(n,3,2,self.model['definitions'])
                        if typ is None:raise ValueError('Unresolved custom variable value type')
                        before=self.db.get(str(target),{}).get(key)
                        if before is None and typ not in CONTAINER_TYPES:before=default_value(typ)
                        trigger=inp(n,3)if pin(n,3,3)is not None else True
                        if type(trigger)is not bool:raise ValueError('Variable event trigger must be boolean')
                        if pin(n,3,4)is not None and inp(n,4)!=trigger:raise ValueError('Variable event trigger mirror mismatch')
                        self.db.setdefault(str(target),{})[key]=value
                        if trigger:
                            change_value={'name':key,'type':typ,'before':deepcopy(before),'after':deepcopy(value)}
                            for listener_graph,listener_owner in self.instances:
                                if listener_owner!=target:continue
                                for listener_id,listener in listener_graph['nodes'].items():
                                    if self.title(listener)!='When_Custom_Variable_Changes':continue
                                    listener_type=port_type(listener,4,3,self.model['definitions'])
                                    if listener_type is None:raise ValueError('Unresolved variable event type')
                                    if listener_type==typ:pending.append((listener_graph,listener_owner,listener_id,None,[],change_value))
                            self.event_log.append({'entity':target,'variable':key,'type':typ})
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
                    else:raise ValueError('Unsupported native execution '+title)
                follow(n,branch)
            execute(event_id)
        self.out.extend(emitted);return emitted
    def settle(self):self.persisted=deepcopy(self.db)
    def reenter(self):self.db=deepcopy(self.persisted)
