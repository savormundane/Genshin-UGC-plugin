"""Independent Lua clients coupled to final native graphs through a deterministic queue."""
from copy import deepcopy
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
        doc=(PLUGIN/'references/platform/community/client-controls-api.md').read_text(encoding='utf-8')
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
def differing_path(actual, expected, path=()):
    """Return the first mismatch, keeping boolean and numeric values distinct."""
    if type(actual) is dict and type(expected) is dict:
        for key in expected:
            if key not in actual:
                return (*path,key)
            mismatch=differing_path(actual[key],expected[key],(*path,key))
            if mismatch is not None:
                return mismatch
        return next(((*path,key) for key in actual if key not in expected),None)
    if type(actual) is list and type(expected) is list:
        for index,(left,right) in enumerate(zip(actual,expected)):
            mismatch=differing_path(left,right,(*path,index))
            if mismatch is not None:
                return mismatch
        return None if len(actual)==len(expected) else (*path,min(len(actual),len(expected)))
    return path if isinstance(actual,bool)!=isinstance(expected,bool) or actual!=expected else None


def scene_sources(spec, base):
    items = spec['clients'] + ([spec['server']] if 'server' in spec else [])
    if any(not isinstance(item, dict) or not isinstance(item.get('source'), str) or not item['source'] for item in items):
        raise ValueError('Each simulation client and server needs a source path')
    return {str(resolve(base, item['source'])) for item in items}


def load_scenario(path, *, replay=False):
    path = Path(path).resolve()
    value = read_json(path)
    record = value.get('replay', value) if isinstance(value, dict) else value
    is_replay = isinstance(record, dict) and record.get('kind') == 'joint-simulation-replay'
    if not is_replay and not replay:
        return value, path.parent, None
    required = ('schema', 'kind', 'scenario', 'scenario_sha256', 'base', 'inputs')
    schema(record, required, required, version=1)
    if not is_replay or sha(canonical(record['scenario']).encode('utf-8')) != record['scenario_sha256']:
        raise ValueError('Replay scene digest mismatch')
    base = Path(record['base'])
    if not base.is_absolute():
        raise ValueError('Replay requires the original absolute scenario directory')
    spec = record['scenario']
    inputs = record['inputs']
    if not isinstance(inputs, dict) or set(inputs) != scene_sources(spec, base):
        raise ValueError('Replay inputs must cover every declared scene source')
    if any(not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) for digest in inputs.values()):
        raise ValueError('Invalid replay input digest')
    return spec, base, inputs


def execute(spec,base,trace=None,*,expected_inputs=None):
    schema(spec,('schema','clients','server','steps','faults','assertions','observations','clock','expected_pending_packets'),('clients','steps'))
    expected_pending=spec.get('expected_pending_packets',0)
    if type(expected_pending) is not int or expected_pending<0:
        raise ValueError('expected_pending_packets must be a nonnegative integer')
    clients={};variable_bindings={};variable_syncs=[];inputs={};serial=0;queue=[];clock=0;occurrences={};journal=[]
    def check_digest(path, digest):
        if expected_inputs is not None and expected_inputs.get(str(path)) != digest:
            raise DiagnosticError('simulation.replay_input_changed', 'Replay input digest differs', phase='input',
                                  source=str(path), expected=expected_inputs.get(str(path)), actual=digest)

    def read_source(path):
        raw = path.read_bytes()
        digest = sha(raw)
        check_digest(path, digest)
        inputs[str(path)] = digest
        return raw

    if expected_inputs is not None:
        for source in expected_inputs:
            path = Path(source)
            check_digest(path, sha_file(path) if path.is_file() else None)
    if not isinstance(spec['clients'],list) or (not spec['clients'] and 'server' not in spec):
        raise ValueError('Provide independent clients or a native server')
    native_only = not spec['clients']
    layer = 'native_graph_model' if native_only else 'lua_model'
    faults=spec.get('faults',[])
    fault_counts=[{'hits':0,'scheduled':0,'delivered':0,'dropped':0} for _ in faults]
    for fault in faults:
        schema(fault,('name','source','target','occurrence','action','delay','required'),('name','action'))
        if type(fault.get('required',True))is not bool:raise ValueError('fault.required must be boolean')
        if fault['action']not in('drop','duplicate','delay','reorder'):raise ValueError('Unknown transport fault')
        if 'occurrence'in fault and(type(fault['occurrence'])!=int or fault['occurrence']<1):raise ValueError('Positive fault occurrence required')
        if fault['action']in('delay','reorder')and(type(fault.get('delay'))not in(int,float)or not 0<=fault['delay']<=3600):raise ValueError('Nonnegative finite transport delay required')
    if trace is not None:
        trace.update(journal=journal,inputs=inputs,phase='startup',layer=layer,declared_sources=scene_sources(spec,base))
    if 'clock'in spec:
        schema(spec['clock'],('start',),('start',));clock=spec['clock']['start']
        if type(clock)not in(int,float)or not 0<=clock<1e12:raise ValueError('Finite nonnegative model clock required')
    server=None
    if 'server'in spec:
        from native_model import NativeModel
        s=spec['server'];schema(s,('source','initial','graph_ids','instances','entity_guids','required_timers','level_entity','timer_index_base'),('source',))
        graph_ids=s.get('graph_ids')
        if native_only and (not isinstance(graph_ids,list) or not graph_ids or
                            any(type(ident) is not int for ident in graph_ids) or len(set(graph_ids))!=len(graph_ids)):
            raise ValueError('Native-only simulation requires explicit, unique server.graph_ids')
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
        raw=read_source(path)
        server=NativeModel(raw,s.get('initial'),graph_ids,s.get('instances'),s.get('entity_guids'),s.get('level_entity'),
                           mounted_only=native_only,timer_index_base=s.get('timer_index_base',1))
        server.timers.time=clock
    for item in spec['clients']:
        if trace is not None:trace.update(client=item.get('id'),source=item.get('source'),mapping=item.get('mapping'))
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
            if server is None:raise ValueError('Selected variables require a native server')
            initial_variables[key]=server.variable(selection['entity'],selection['name'])
        variable_bindings[item['id']]=selections
        path=resolve(base,item['source']);mapping=item.get('mapping','main.lua')
        if trace is not None:trace.update(source=str(path),client=item['id'],mapping=mapping)
        raw=read_source(path)
        source,bindings=script_from_gil(raw,mapping)if path.suffix.lower()=='.gil'else(raw.decode('utf-8-sig'),None)
        clients[item['id']]=Client(source,bindings,mapping,item.get('canvas',(1600,900)),item.get('params'),initial_variables)
    def enqueue(source,target,name,params):
        nonlocal serial
        key=(source,str(target),name);occurrences[key]=occurrences.get(key,0)+1;delay=0;copies=1
        timing_rule=copy_rule=None
        for index,f in enumerate(faults):
            if f['name']==name and f.get('source',source)==source and f.get('target',target)==target and f.get('occurrence',occurrences[key])==occurrences[key]:
                fault_counts[index]['hits']+=1
                if f['action']=='drop':
                    fault_counts[index]['dropped']+=1
                    return
                if f['action']=='duplicate':
                    copies=2;copy_rule=index
                else:
                    delay=f['delay'];timing_rule=index
        applied=tuple(index for index in (copy_rule,timing_rule) if index is not None)
        for index in applied:fault_counts[index]['scheduled']+=copies
        for _ in range(copies):
            serial+=1
            heapq.heappush(queue,(clock+delay,serial,source,target,name,params,applied))
    def collect():
        for ident,c in clients.items():
            for p in c.packets():enqueue(ident,'server',p['name'],p['params']if isinstance(p['params'],list)else [])
    def drain():
        work=0
        while queue and queue[0][0]<=clock:
            work+=1
            if work>10000:raise ValueError('Transport budget exceeded')
            time,order,source,target,name,params,applied=heapq.heappop(queue);journal.append({'time':time,'source':source,'target':target,'name':name,'params':params})
            if target=='server':
                if server is None:raise ValueError('No native server configured')
                for p in server.request(name,params,source):enqueue('server',p['target'],p['name'],p['params'])
            else:
                if target not in clients:raise ValueError('Unknown signal target')
                c=clients[target];c.call(c.h.receive,name,c.to_lua(params))
            for index in applied:fault_counts[index]['delivered']+=1
            collect()
    def observe(item,expected=False):
        if 'entity' in item:
            result_key='equals' if expected else 'name'
            schema(item,('entity','path','variable',result_key),('entity','path',result_key))
            ident=item['entity']
            if server is None or type(ident) is not int or ident not in server.entities:
                raise ValueError('Native observation requires a placed entity')
            if item['path']=='variable':
                name=item.get('variable')
                if not isinstance(name,str) or not name:raise ValueError('Native variable observation requires a variable name')
                return deepcopy(server.variable(ident,name))
            if 'variable' in item:raise ValueError('variable is only used with the native variable path')
            if item['path']=='model_visible':return server.model_visibility.get(ident)
            if item['path']=='position_m':return server.position_m(ident)
            raise ValueError('Unknown native observation path')
        client=clients[item['client']]
        return client.plain(client.h.value(item['path']))
    values={};observation_steps=[];route_events=[]
    if trace is not None:
        trace.update(observations=values, observation_steps=observation_steps)
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
        elif op=='observe':
            schema(step,('op','entity','path','variable','name'),('op','entity','path','name'))
            name=step['name']
            if not isinstance(name,str) or not name or name in values:
                raise ValueError('Observation step requires a unique nonempty name')
            values[name]=observe({k:v for k,v in step.items() if k!='op'})
            observation_steps.append({'name':name,'entity':step['entity'],'path':step['path'],'time':clock,'value':values[name],
                                      **({'variable':step['variable']} if 'variable' in step else {})})
        elif op=='sync_variables':
            schema(step,('op','client','notify'),('op','client','notify'))
            if server is None or step['client']not in clients or type(step['notify'])is not bool:raise ValueError('Invalid variable synchronization target/policy')
            selections=variable_bindings[step['client']]
            if not selections:raise ValueError('Variable synchronization requires selected variables')
            rows=[]
            for selection in selections:
                if selection['entity']in server.removed_entities:raise ValueError('Variable synchronization entity removed')
                rows.append({**selection,'value':server.variable(selection['entity'],selection['name'])})
            c=clients[step['client']];c.call(c.h.syncVariables,c.to_lua(rows),step['notify'])
            variable_syncs.append({'client':step['client'],'time':clock,'notify':step['notify'],'variables':selections})
        elif op in('entity_created','entity_removed'):
            schema(step,('op','entity'),('op','entity'))
            if server is None:raise ValueError('Native server required')
            for p in getattr(server,op)(step['entity']):enqueue('server',p['target'],p['name'],p['params'])
        elif op == 'route':
            route_fields = ('entity', 'trigger_entity', 'trigger_id', 'points_m')
            schema(step, ('op', *route_fields), route_fields)
            if server is None:
                raise ValueError('Route requires a native server')
            route = {key: step[key] for key in route_fields if key != 'points_m'}
            route.update(step_index=step_index, time=clock, geometry={'status': 'not_checked'},
                         node_execution={'status': 'not_checked'}, host='not_checked')
            route_events.append(route)
            if trace is not None:
                trace['route_events'] = route_events
            for packet in server.walk_route(step['entity'], step['trigger_entity'], step['trigger_id'],
                                            step['points_m'], route):
                enqueue('server', packet['target'], packet['name'], packet['params'])
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
    assertions=spec.get('assertions',[])
    for assertion_index,a in enumerate(assertions,1):
        if trace is not None:trace.update(phase='assertion',assertion_index=assertion_index,clock=clock)
        actual=observe(a,expected=True)
        mismatch=differing_path(actual,a['equals'])
        if mismatch is not None:
            message='Joint assertion failed '+a['path']
            if trace is not None:
                try:canonical(actual)
                except (TypeError,ValueError):actual=repr(actual)
                trace['diagnostic']={'code':'joint_assertion_failed','message':message,'phase':'assertion',
                                     'assertion_index':assertion_index,'field':a['path'],
                                     **{key:a[key] for key in ('client','entity','variable') if key in a},
                                     'expected':a['equals'],'actual':actual,'value_path':list(mismatch),'time':clock}
            raise ValueError(message)
    for a in spec.get('observations',[]):
        if trace is not None:trace.update(phase='observation',clock=clock,observation=a['name'])
        if any(row['name']==a['name'] for row in observation_steps):
            raise ValueError('Final observation name collides with an observation step')
        values[a['name']]=observe(a)
    gaps=[]
    if not spec.get('assertions'):gaps.append('no assertions executed')
    native_gaps=[]
    if server:
        if not server.work:native_gaps.append('native server not executed')
        required=set(spec['server'].get('graph_ids',[]))
        if required-server.executed_graphs:native_gaps.append('required graphs not executed: '+str(sorted(required-server.executed_graphs)))
        for requirement in spec['server'].get('required_timers',[]):
            count=sum(event.get('timer')==requirement['name']and event.get('entity')==requirement['entity']for event in server.event_log)
            if count<requirement['minimum_events']:native_gaps.append('required timer events not reached: '+canonical({**requirement,'actual':count}))
    gaps.extend(native_gaps)
    fault_report=[]
    for index,(rule,counts) in enumerate(zip(faults,fault_counts)):
        observed=counts['dropped'] or (counts['scheduled']>0 and counts['scheduled']==counts['delivered'])
        fault_report.append({'rule':rule,**counts,'status':'passed' if observed else 'not_checked'})
        if rule.get('required',True) and not observed:
            reason='required fault deliveries incomplete' if counts['scheduled'] else 'required fault not exercised'
            gaps.append(f'{reason}: {index}')
    pending_matches=len(queue)==expected_pending
    if not pending_matches:gaps.append(f'pending packets: expected {expected_pending}, actual {len(queue)}')
    acceptance={'status':'not_checked' if gaps else 'passed','gaps':gaps}
    native_assertions=sum('entity' in assertion for assertion in assertions)
    lua_assertions=len(assertions)-native_assertions
    checks={'assertions':{'status':'passed' if assertions else 'not_checked','executed':len(assertions),
                          'native':native_assertions,'lua':lua_assertions},
            'transport':{'status':'passed' if pending_matches and all(not f['rule'].get('required',True) or f['status']=='passed' for f in fault_report) else 'not_checked',
                         'pending':len(queue),'expected_pending':expected_pending},
            'coverage':acceptance}
    return {'schema':2,'layer':layer,'execution_status':'passed','status':acceptance['status'],
            'acceptance':acceptance,'checks':checks,
            'diagnostics':[{'code':'joint_coverage_missing','message':gap}for gap in gaps],
            'evidence':{'lua_model':'not_applicable' if native_only else 'passed' if lua_assertions else 'not_checked',
                        'native_graph_model':('passed' if native_assertions and not native_gaps else 'not_checked') if server else 'not_applicable',
                        'editor':'not_checked','host':'not_checked','real_storage_reentry':'not_checked'},
            'inputs':inputs,'journal':journal,'pending_packets':len(queue),'faults':fault_report,'observations':values,'assertions':len(assertions),'executed_graphs':sorted(server.executed_graphs)if server else [],'server_work':server.work if server else 0,'variable_syncs':variable_syncs,'server_variables':server.db if server else {},'lifecycle_events':[event for event in server.event_log if 'lifecycle'in event]if server else [],'timer_events':[event for event in server.event_log if 'timer'in event]if server else [],
            'mounts':server.mount_origins if server else [],
            'executed_instances':[{'graph_id':graph,'owner_entity':owner} for graph,owner in
                                  sorted(server.executed_instances,key=lambda pair:(pair[0], -1 if pair[1] is None else pair[1]))] if server else [],
            'model_visibility':{str(ident):visible for ident,visible in server.model_visibility.items()} if server else {},
            'model_visibility_events':[event for event in server.event_log if 'model_visible' in event] if server else [],
            'motion_events':[event for event in server.event_log if 'motion' in event] if server else [],
            **({'route_events': route_events} if route_events else {}),
            'observation_steps':observation_steps,
            'host_tested':False,'editor_tested':False}


def evaluate(spec,base,*,expected_inputs=None):
    """Collect the same failure and coverage report in the CLI and MCP workers."""
    trace={}
    try:
        return execute(spec,base,trace,expected_inputs=expected_inputs)
    except Exception as exc:
        import traceback
        from native_model import UncalibratedRoute, UncalibratedVariable
        diagnostic=trace.pop('diagnostic',None)
        replay = {}
        declared = trace.pop('declared_sources', None)
        if declared and declared == set(trace['inputs']):
            replay['replay'] = {'schema': 1, 'kind': 'joint-simulation-replay', 'base': str(Path(base).resolve()),
                                'scenario': spec, 'scenario_sha256': sha(canonical(spec).encode('utf-8')),
                                'inputs': trace['inputs']}
        if isinstance(exc, (UncalibratedVariable, UncalibratedRoute)):
            gap=str(exc)
            coverage={'status':'not_checked','gaps':[gap]}
            details = ({'code': 'native_variable_default_unchecked', 'entity': exc.entity, 'variable': exc.variable}
                       if isinstance(exc, UncalibratedVariable) else
                       {'code': 'native_route_unchecked', 'step_index': trace['step_index']})
            return {'schema':2,'layer':trace.get('layer','lua_model'),'status':'not_checked',
                    'execution_status':'not_checked','acceptance':coverage,
                    'checks':{'coverage':coverage},
                    'diagnostics':[{**details, 'message': gap, 'phase': trace.get('phase','input')}],
                    **({'route_events': trace['route_events']} if 'route_events' in trace else {}),
                    'inputs':trace.get('inputs',{}),'trace':trace,'editor_tested':False,'host_tested':False,**replay}
        if isinstance(exc, DiagnosticError):
            diagnostic=exc.diagnostics[0]
        if diagnostic is None:
            diagnostic={'code':'joint_model_failed','message':str(exc),'phase':trace.get('phase','input')}
            if diagnostic['phase']=='step':
                diagnostic.update(step_index=trace['step_index'],actual=trace['step'],time=trace['clock'])
            elif diagnostic['phase']=='startup':
                diagnostic.update({key:trace[key] for key in ('client','source','mapping') if key in trace})
            elif diagnostic['phase']=='assertion':
                diagnostic.update(assertion_index=trace['assertion_index'],time=trace['clock'])
        assertion_failed=diagnostic['code']=='joint_assertion_failed'
        return {'schema':2,'layer':trace.get('layer','lua_model'),'status':'failed',
                'execution_status':'passed' if assertion_failed else 'failed',
                'acceptance':{'status':'failed','gaps':[]},
                'checks':{'assertions':{'status':'failed' if assertion_failed else 'not_checked',
                                        'executed':diagnostic.get('assertion_index',0)}},
                'diagnostics':[diagnostic],'inputs':trace.get('inputs',{}),
                **({'route_events': trace['route_events']} if 'route_events' in trace else {}),
                'error':str(exc),'trace':trace,'stack':traceback.format_exc(),
                'editor_tested':False,'host_tested':False,**replay}


class SimulationFailure(ValueError):
    def __init__(self,detail):self.detail=detail;super().__init__('Joint model failed: '+canonical(detail))
def run(spec,base,timeout=30,*,expected_inputs=None):
    env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(sys.path);env['PYTHONDONTWRITEBYTECODE']='1'
    request=canonical({'spec':spec,'base':str(base),'expected_inputs':expected_inputs})
    try:r=subprocess.run([sys.executable,'-X','utf8','-B',__file__,'--worker'],input=request,encoding='utf-8',capture_output=True,timeout=timeout,env=env)
    except subprocess.TimeoutExpired as e:raise ValueError('Joint model timeout')from e
    if r.returncode:
        if r.stdout:raise SimulationFailure(json.loads(r.stdout))
        raise ValueError('Joint model failed: '+r.stderr[-3000:])
    return json.loads(r.stdout)
if __name__=='__main__':
    v=json.loads(sys.stdin.read())
    result=evaluate(v['spec'],v['base'],expected_inputs=v.get('expected_inputs'))
    print(canonical(result))
    if result['status']=='failed':raise SystemExit(2)
