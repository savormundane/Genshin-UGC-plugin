"""Independent Lua clients coupled to final native graphs through a deterministic queue."""
from pathlib import Path
import hashlib,json,re,heapq,subprocess,sys,os
from authoring_io import *
from native_core import get
from level_inventory import container,fields,vals

class Client:
    def __init__(self,source,bindings=None,mapping='main.lua',canvas=(1600,900),params=None,variables=None):
        from lupa.lua53 import LuaRuntime
        self.lua=LuaRuntime(unpack_returned_tuples=True,register_eval=False,register_builtins=False,max_memory=64*1024*1024)
        self.h=self.lua.execute((PLUGIN/'scripts/client_simulator.lua').read_text(encoding='utf-8'));self.limit=self.lua.eval('function()debug.sethook(function()error("instruction budget")end,"",2000000)end')
        enums={}
        doc=(PLUGIN/'skills/client-controls-lua/references/client-controls-api.md').read_text(encoding='utf-8')
        for category,name in re.findall(r'\|\s*`Enum\.(\w+)`\s*\|\s*`(\w+)`',doc):enums.setdefault(category,{})[name]=name
        templates={t['template_guid']:{'name':t['name'],'kind':t.get('kind','container')}for t in(bindings or{}).get('templates',[])}
        self.h.setup(self.to_lua(enums),self.to_lua({'width':canvas[0],'height':canvas[1],'mapping':mapping,'scriptId':0x40000001,'templates':templates,'params':params or{},'variables':variables or{}}))
        self.call(self.h.load,source);self.call(self.h.boot)
    def to_lua(self,v):
        if isinstance(v,dict):return self.lua.table_from({k:self.to_lua(x)for k,x in v.items()})
        if isinstance(v,list):return self.lua.table_from([self.to_lua(x)for x in v])
        return v
    def plain(self,v):
        if hasattr(v,'items'):
            keys=list(v.keys())
            if keys and all(type(k)==int for k in keys)and sorted(keys)==list(range(1,len(keys)+1)):return[self.plain(v[i])for i in range(1,len(keys)+1)]
            return{str(k):self.plain(x)for k,x in v.items()}
        return v
    def call(self,f,*args):self.limit();return f(*args)
    def packets(self):
        out=[self.plain(self.h.sentSignals[i])for i in range(1,len(self.h.sentSignals)+1)];self.h.sentSignals=self.lua.table()
        for packet in out:
            if isinstance(packet['params'],list):
                for i,kind in enumerate(packet['types']):
                    if kind.endswith('List')and packet['params'][i]=={}:packet['params'][i]=[]
        return out

def script_from_gil(raw,mapping,*,bindings=None):
    from level_authoring import inspect_bindings
    if bindings is None:bindings=inspect_bindings(raw)
    _,root=container(raw);matches=[get(e,5)for s in vals(root,50)for e in vals(fields(s),1)if get(e,3)==mapping.encode()]
    if len(matches)!=1 or matches[0] is None:raise ValueError('Exact unique embedded Lua mapping required')
    return matches[0].decode('utf-8-sig'),bindings
def execute(spec,base,trace=None):
    schema(spec,('schema','clients','server','steps','faults','assertions','observations','clock'),('clients','steps'))
    clients={};variable_bindings={};variable_syncs=[];inputs={};serial=0;queue=[];clock=0;occurrences={};journal=[]
    if not isinstance(spec['clients'],list)or not spec['clients']:raise ValueError('At least one independent client is required')
    fault_hits=[0 for _ in spec.get('faults',[])]
    for fault in spec.get('faults',[]):
        schema(fault,('name','source','target','occurrence','action','delay','required'),('name','action'))
        if type(fault.get('required',True))is not bool:raise ValueError('fault.required must be boolean')
        if fault['action']not in('drop','duplicate','delay','reorder'):raise ValueError('Unknown transport fault')
        if 'occurrence'in fault and(type(fault['occurrence'])!=int or fault['occurrence']<1):raise ValueError('Positive fault occurrence required')
        if fault['action']in('delay','reorder')and(type(fault.get('delay'))not in(int,float)or not 0<=fault['delay']<=3600):raise ValueError('Nonnegative finite transport delay required')
    if trace is not None:trace.update(journal=journal,inputs=inputs,phase='startup')
    if 'clock'in spec:
        schema(spec['clock'],('start',),('start',));clock=spec['clock']['start']
        if type(clock)not in(int,float)or not 0<=clock<1e12:raise ValueError('Finite nonnegative model clock required')
    for item in spec['clients']:
        schema(item,('id','source','mapping','canvas','params','variables'),('id','source'))
        if item['id']in clients:raise ValueError('Duplicate client ID')
        selections=item.get('variables',[]);keys=set();initial_variables={};scope_entities={}
        if not isinstance(selections,list):raise ValueError('Client variables require a list')
        for selection in selections:
            schema(selection,('scope','entity','name'),('scope','entity','name'))
            if selection['scope']not in('Level','PlayerSelf','AvatarSelf')or type(selection['entity'])is not int or selection['entity']<0 or not isinstance(selection['name'],str)or not selection['name']:
                raise ValueError('Invalid client variable selection')
            key=selection['scope']+':'+selection['name']
            if key in keys:raise ValueError('Duplicate client variable selection')
            if selection['scope']in scope_entities and scope_entities[selection['scope']]!=selection['entity']:raise ValueError('Client variable scope has conflicting entities')
            scope_entities[selection['scope']]=selection['entity']
            keys.add(key)
            state=spec.get('server',{}).get('initial',{}).get(str(selection['entity']),{})
            if selection['name']not in state:raise ValueError('Selected initial native variable missing')
            initial_variables[key]=state[selection['name']]
        variable_bindings[item['id']]=selections
        path=resolve(base,item['source']);mapping=item.get('mapping','main.lua')
        if trace is not None:trace.update(source=str(path),client=item['id'],mapping=mapping)
        raw=path.read_bytes();inputs[str(path)]=sha(raw)
        source,bindings=script_from_gil(raw,mapping)if path.suffix.lower()=='.gil'else(raw.decode('utf-8-sig'),None)
        clients[item['id']]=Client(source,bindings,mapping,item.get('canvas',(1600,900)),item.get('params'),initial_variables)
    server=None
    if 'server'in spec:
        from native_model import NativeModel
        s=spec['server'];schema(s,('source','initial','graph_ids','instances','entity_guids','required_timers','level_entity'),('source',))
        required_timers=s.get('required_timers',[])
        if not isinstance(required_timers,list):raise ValueError('required_timers must be a list')
        timer_keys=set()
        for requirement in required_timers:
            schema(requirement,('entity','name','minimum_events'),('entity','name','minimum_events'))
            entity,name,count=requirement['entity'],requirement['name'],requirement['minimum_events']
            if type(entity)!=int or entity<0 or not isinstance(name,str)or not name or type(count)!=int or count<1:raise ValueError('Invalid required timer event contract')
            if (entity,name)in timer_keys:raise ValueError('Duplicate required timer identity')
            timer_keys.add((entity,name))
        path=resolve(base,s['source'])
        if trace is not None:trace.update(source=str(path),client='server',mapping=None)
        raw=path.read_bytes();inputs[str(path)]=sha(raw);server=NativeModel(raw,s.get('initial'),s.get('graph_ids'),s.get('instances'),s.get('entity_guids'),s.get('level_entity'))
        server.timers.time=clock
    def enqueue(source,target,name,params):
        nonlocal serial
        key=(source,str(target),name);occurrences[key]=occurrences.get(key,0)+1;delay=0;copies=1
        for index,f in enumerate(spec.get('faults',[])):
            if f['name']==name and f.get('source',source)==source and f.get('target',target)==target and f.get('occurrence',occurrences[key])==occurrences[key]:
                fault_hits[index]+=1
                if f['action']=='drop':return
                if f['action']=='duplicate':copies=2
                elif f['action']in('delay','reorder'):delay=f['delay']
                else:raise ValueError('Unknown transport fault')
        for _ in range(copies):serial+=1;heapq.heappush(queue,(clock+delay,serial,source,target,name,params))
    def collect():
        for ident,c in clients.items():
            for p in c.packets():enqueue(ident,'server',p['name'],p['params']if isinstance(p['params'],list)else [])
    def drain():
        work=0
        while queue and queue[0][0]<=clock:
            work+=1
            if work>10000:raise ValueError('Transport budget exceeded')
            time,order,source,target,name,params=heapq.heappop(queue);journal.append({'time':time,'source':source,'target':target,'name':name,'params':params})
            if target=='server':
                if server is None:raise ValueError('No native server configured')
                for p in server.request(name,params,source):enqueue('server',p['target'],p['name'],p['params'])
            else:
                if target not in clients:raise ValueError('Unknown signal target')
                c=clients[target];c.call(c.h.receive,name,c.to_lua(params))
            collect()
    collect();drain()
    for step_index,step in enumerate(spec['steps'],1):
        if trace is not None:trace.update(phase='step',step_index=step_index,step=step,clock=clock)
        op=step['op']
        if op=='tick':
            dt=step['dt']
            if type(dt)not in(int,float)or not 0<=dt<=3600:raise ValueError('Invalid joint tick')
            end=clock+dt;boundaries=0
            while True:
                boundaries+=1
                if boundaries>10000:raise ValueError('Joint clock event budget exceeded')
                deadlines=[end]
                if queue:deadlines.append(queue[0][0])
                due=server.timers.deadline()if server else None
                if due is not None:deadlines.append(due)
                next_time=max(clock,min(deadlines));elapsed=next_time-clock;clock=next_time
                # At a shared boundary: client tick, native timers, then FIFO
                # transport. This is a declared deterministic model convention.
                for c in clients.values():c.call(c.h.tick,elapsed)
                if server is not None:
                    for p in server.tick(elapsed):enqueue('server',p['target'],p['name'],p['params'])
                collect();drain()
                due=server.timers.deadline()if server else None
                if clock>=end and (due is None or due>clock):break
        elif op=='sync_variables':
            schema(step,('op','client','notify'),('op','client','notify'))
            if server is None or step['client']not in clients or type(step['notify'])is not bool:raise ValueError('Invalid variable synchronization target/policy')
            selections=variable_bindings[step['client']]
            if not selections:raise ValueError('Variable synchronization requires selected variables')
            rows=[]
            for selection in selections:
                if selection['entity']in server.removed_entities:raise ValueError('Variable synchronization entity removed')
                state=server.db.get(str(selection['entity']),{})
                if selection['name']not in state:raise ValueError('Selected native variable missing')
                rows.append({**selection,'value':state[selection['name']]})
            c=clients[step['client']];c.call(c.h.syncVariables,c.to_lua(rows),step['notify'])
            variable_syncs.append({'client':step['client'],'time':clock,'notify':step['notify'],'variables':selections})
        elif op in('entity_created','entity_removed'):
            schema(step,('op','entity'),('op','entity'))
            if server is None:raise ValueError('Native server required')
            for p in getattr(server,op)(step['entity']):enqueue('server',p['target'],p['name'],p['params'])
        elif op=='signal':enqueue(step['source'],step['target'],step['name'],step['params'])
        elif op in('settle','reenter'):
            if server is None:raise ValueError('Native server required')
            getattr(server,op)()
        else:
            c=clients[step['client']]
            if op=='invoke':
                fn=c.h.value(step['name'])
                if fn is None:raise ValueError('Missing callable')
                c.call(fn,*[c.to_lua(x)for x in step.get('args',[])])
            elif op in('cursor','key'):c.call(c.h.fire,c.h.value(step['control']),'Cursor'if op=='cursor'else'Key',step['event'],c.to_lua(step.get('data',{})))
            elif op=='lifecycle':c.call(c.h.requestLifecycle,step['name'])
            else:raise ValueError('Unknown joint operation')
        collect();drain()
    values={}
    assertions=spec.get('assertions',[])
    for assertion_index,a in enumerate(assertions,1):
        if trace is not None:trace.update(phase='assertion',assertion_index=assertion_index,clock=clock)
        actual=clients[a['client']].plain(clients[a['client']].h.value(a['path']))
        if actual!=a['equals']or isinstance(actual,bool)!=isinstance(a['equals'],bool):
            message='Joint assertion failed '+a['path']
            if trace is not None:
                try:canonical(actual)
                except (TypeError,ValueError):actual=repr(actual)
                trace['diagnostic']={'code':'joint_assertion_failed','message':message,'phase':'assertion',
                                     'assertion_index':assertion_index,'client':a['client'],'field':a['path'],
                                     'expected':a['equals'],'actual':actual,'time':clock}
            raise ValueError(message)
    for a in spec.get('observations',[]):values[a['name']]=clients[a['client']].plain(clients[a['client']].h.value(a['path']))
    gaps=[]
    if not spec.get('assertions'):gaps.append('no assertions executed')
    if server:
        if not server.work:gaps.append('native server not executed')
        required=set(spec['server'].get('graph_ids',[]))
        if required-server.executed_graphs:gaps.append('required graphs not executed: '+str(sorted(required-server.executed_graphs)))
        for requirement in spec['server'].get('required_timers',[]):
            count=sum(event.get('timer')==requirement['name']and event.get('entity')==requirement['entity']for event in server.event_log)
            if count<requirement['minimum_events']:gaps.append('required timer events not reached: '+canonical({**requirement,'actual':count}))
    for i,(rule,hits)in enumerate(zip(spec.get('faults',[]),fault_hits)):
        if rule.get('required',True)and not hits:gaps.append('required fault not exercised: '+str(i))
    acceptance={'status':'not_checked' if gaps else 'passed','gaps':gaps}
    checks={'assertions':{'status':'passed' if assertions else 'not_checked','executed':len(assertions)},
            'coverage':acceptance}
    return {'schema':2,'layer':'lua_model','execution_status':'passed','status':acceptance['status'],
            'acceptance':acceptance,'checks':checks,
            'diagnostics':[{'code':'joint_coverage_missing','message':gap}for gap in gaps],
            'evidence':{'lua_model':'passed'if assertions else'not_checked','native_graph_model':('passed'if server.work else'not_checked')if server else'not_applicable','editor':'not_checked','host':'not_checked','real_storage_reentry':'not_checked'},'inputs':inputs,'journal':journal,'pending_packets':len(queue),'faults':[{'rule':rule,'hits':hits,'status':'passed'if hits else'not_checked'}for rule,hits in zip(spec.get('faults',[]),fault_hits)],'observations':values,'assertions':len(assertions),'executed_graphs':sorted(server.executed_graphs)if server else [],'server_work':server.work if server else 0,'variable_syncs':variable_syncs,'server_variables':server.db if server else {},'lifecycle_events':[event for event in server.event_log if 'lifecycle'in event]if server else [],'timer_events':[event for event in server.event_log if 'timer'in event]if server else [],'host_tested':False,'editor_tested':False}


def evaluate(spec,base):
    """Collect the same failure and coverage report in the CLI and MCP workers."""
    trace={}
    try:
        return execute(spec,base,trace)
    except Exception as exc:
        import traceback
        diagnostic=trace.pop('diagnostic',None)
        if diagnostic is None:
            diagnostic={'code':'joint_model_failed','message':str(exc),'phase':trace.get('phase','input')}
            if diagnostic['phase']=='step':
                diagnostic.update(step_index=trace['step_index'],actual=trace['step'],time=trace['clock'])
            elif diagnostic['phase']=='startup':
                diagnostic.update({key:trace[key] for key in ('client','source','mapping') if key in trace})
            elif diagnostic['phase']=='assertion':
                diagnostic.update(assertion_index=trace['assertion_index'],time=trace['clock'])
        assertion_failed=diagnostic['code']=='joint_assertion_failed'
        return {'schema':2,'layer':'lua_model','status':'failed',
                'execution_status':'passed' if assertion_failed else 'failed',
                'acceptance':{'status':'failed','gaps':[]},
                'checks':{'assertions':{'status':'failed' if assertion_failed else 'not_checked',
                                        'executed':diagnostic.get('assertion_index',0)}},
                'diagnostics':[diagnostic],'inputs':trace.get('inputs',{}),
                'error':str(exc),'trace':trace,'stack':traceback.format_exc(),
                'editor_tested':False,'host_tested':False}


class SimulationFailure(ValueError):
    def __init__(self,detail):self.detail=detail;super().__init__('Joint model failed: '+canonical(detail))
def run(spec,base,timeout=30):
    env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(sys.path);env['PYTHONDONTWRITEBYTECODE']='1'
    request=canonical({'spec':spec,'base':str(base)})
    try:r=subprocess.run([sys.executable,'-X','utf8','-B',__file__,'--worker'],input=request,encoding='utf-8',capture_output=True,timeout=timeout,env=env)
    except subprocess.TimeoutExpired as e:raise ValueError('Joint model timeout')from e
    if r.returncode:
        if r.stdout:raise SimulationFailure(json.loads(r.stdout))
        raise ValueError('Joint model failed: '+r.stderr[-3000:])
    return json.loads(r.stdout)
if __name__=='__main__':
    v=json.loads(sys.stdin.read())
    result=evaluate(v['spec'],v['base'])
    print(canonical(result))
    if result['status']=='failed':raise SystemExit(2)
