"""Run the explicit client API subset in Lua 5.3; no renderer/editor/host emulator."""
from pathlib import Path
import argparse,hashlib,json,math,os,re,subprocess,sys
from authoring_io import read_json
PLUGIN=Path(__file__).resolve().parents[1]


class ClientSimulationFailure(ValueError):
 def __init__(self,message,detail):
  super().__init__(message)
  self.detail=detail


def _run_in_process(source,scenario,bindings=None,mapping='main.lua'):
 try:from lupa.lua53 import LuaRuntime
 except ImportError:raise ValueError('离线模拟需要Lua5.3解释器：安装lupa==2.6到当前Python环境；不影响关卡生成和其他CLI')
 if not isinstance(scenario,dict) or set(scenario)-{'schema','canvas','steps','assertions','params'} or type(scenario.get('schema'))!=int or scenario.get('schema')!=1:raise ValueError('模拟场景需要schema=1')
 steps=scenario.get('steps',[]);assertions=scenario.get('assertions',[])
 if not isinstance(steps,list) or len(steps)>10000 or not isinstance(assertions,list):raise ValueError('场景步骤/断言无效或超过10000')
 size=scenario.get('canvas',[1600,900])
 if not isinstance(size,list) or len(size)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in size):raise ValueError('画布需要两个有限正数')
 params=scenario.get('params',{})
 if not isinstance(params,dict):raise ValueError('params须为对象')
 templates={};script_id=0x40000001
 if bindings is not None:
  if bindings.get('diagnostics'):raise ValueError('关卡关联有诊断错误，请先修复')
  for t in bindings.get('templates',[]):templates[t['template_guid']]={'name':t['name'],'kind':t.get('kind','container')}
  found=[s for s in bindings.get('scripts',[]) if s['name']==mapping]
  if len(found)!=1:raise ValueError('模拟映射须精确匹配完整.lua名称；现有='+repr([s['name'] for s in bindings.get('scripts',[])]))
  script_id=found[0]['id']
 lua=LuaRuntime(unpack_returned_tuples=True,register_eval=False,register_builtins=False,max_memory=64*1024*1024)
 def convert(v):
  if isinstance(v,dict):return lua.table_from({k:convert(x) for k,x in v.items()})
  if isinstance(v,list):return lua.table_from([convert(x) for x in v])
  return v
 enums={}
 doc=PLUGIN/'skills/qianxing-editor/references/client-controls-api.md'
 for category,name in re.findall(r'\|\s*`Enum\.(\w+)`\s*\|\s*`(\w+)`',doc.read_text(encoding='utf-8')):enums.setdefault(category,{})[name]=name
 # Symbolic enum values are model inputs, not the host's numerical ABI.
 h=lua.execute((PLUGIN/'scripts/client_simulator.lua').read_text(encoding='utf-8'))
 h.setup(convert(enums),convert({'width':size[0],'height':size[1],'mapping':mapping,'scriptId':script_id,'templates':templates,'params':params}))
 limit=lua.eval('function() debug.sethook(function() error("模拟指令预算耗尽") end,"",2000000) end')
 clear=lua.eval('function() debug.sethook() end')
 def call(fn,*args):
  limit()
  try:return fn(*args)
  finally:clear()
 activity={'phase':'load'}
 try:
  call(h.load,source)
  activity={'phase':'startup'}
  call(h.boot)
  for step_index,step in enumerate(steps,1):
   activity={'phase':'step','step_index':step_index}
   if not isinstance(step,dict) or 'op' not in step:raise ValueError('步骤需要op')
   op=step['op']
   if op=='tick':
    if set(step)!={'op','dt'} or type(step['dt']) not in (int,float) or not math.isfinite(step['dt']) or not 0<=step['dt']<=3600:raise ValueError('tick需要有限dt，范围0..3600')
    call(h.tick,step['dt'])
   elif op=='lifecycle':
    if set(step)!={'op','name'} or step['name'] not in ('OnInit','OnStart','OnEnable','OnDisable','OnDestroy'):raise ValueError('不支持的生命周期')
    call(h.requestLifecycle,step['name'])
   elif op=='invoke':
    if set(step)-{'op','name','args'} or not isinstance(step.get('name'),str) or not isinstance(step.get('args',[]),list):raise ValueError('invoke需要name和可选args')
    fn=h.env[step['name']]
    if fn is None:raise ValueError('脚本方法不存在：'+step['name'])
    call(fn,*[convert(v) for v in step.get('args',[])])
   elif op=='signal':
    if set(step)!={'op','name','params'} or not isinstance(step['name'],str) or not isinstance(step['params'],list):raise ValueError('signal需要name和有序params列表')
    call(h.receive,step['name'],convert(step['params']))
   elif op in ('cursor','key'):
    if set(step)-{'op','control','event','data'} or not all(isinstance(step.get(k),str) for k in ('control','event')):raise ValueError('输入步骤需要control、event和可选data')
    target=h.value(step['control']);family='Cursor' if op=='cursor' else 'Key'
    category='CursorEventType' if op=='cursor' else 'KeyEventType'
    if step['event'] not in enums.get(category,{}):raise ValueError('未知输入枚举：'+step['event'])
    if not isinstance(step.get('data',{}),dict):raise ValueError('输入data须为对象')
    data=step.get('data',{})
    if op=='cursor':
     if set(data)-{'ui_x','ui_y','press_x','press_y','delta_x','delta_y','dragging','touch_id'}:raise ValueError('光标data存在未支持字段')
     for key,value in data.items():
      if key=='dragging':valid=type(value)==bool
      elif key=='touch_id':valid=type(value)==int
      else:valid=type(value) in (int,float) and math.isfinite(value)
      if not valid:raise ValueError('光标data字段类型错误：'+key)
    call(h.fire,target,family,step['event'],convert(step.get('data',{})))
   else:raise ValueError('未知模拟步骤：'+str(op))
  checked=[]
  for assertion_index,item in enumerate(assertions,1):
   activity={'phase':'assertion','assertion_index':assertion_index}
   if not isinstance(item,dict) or set(item)!={'path','equals'} or not isinstance(item['path'],str) or not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',item['path']):raise ValueError('断言需要path与equals，只支持字段路径')
   actual=h.value(item['path']);expected=item['equals']
   if type(expected) not in (str,int,float,bool,type(None)):raise ValueError('断言期望仅支持标量')
   if actual!=expected or (type(actual)==bool)!=(type(expected)==bool):raise ValueError('模拟断言失败：'+item['path']+'，预期='+repr(expected)+'，实际='+repr(actual))
   checked.append(item['path'])
 except Exception as e:
  message=str(e)
  line=re.search(r'\[string "client"\]:(\d+):',message)
  diagnostic={'code':'lua_model_failed','message':message.split('\nstack traceback:',1)[0],**activity}
  if line:
   diagnostic['line']=int(line[1])
  raise ClientSimulationFailure('客户端离线模型执行失败：'+message,{
   'diagnostic':diagnostic,'logs':[h.logs[i] for i in range(1,len(h.logs)+1)],
  }) from e
 def plain(v):
  if hasattr(v,'items'):
   keys=list(v.keys())
   if all(type(k)==int for k in keys)and sorted(keys)==list(range(1,len(keys)+1)):return [plain(v[i])for i in range(1,len(keys)+1)]
   return {str(k):plain(x)for k,x in v.items()}
  return v
 return {'schema':'qianxing-client-simulation/v1','layer':'simulation','source_sha256':hashlib.sha256(source.encode('utf-8')).hexdigest(),'scenario_sha256':hashlib.sha256(json.dumps(scenario,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'source_matches_embedded_mapping': None if bindings is None else hashlib.sha256(source.encode('utf-8')).hexdigest()==found[0]['sha256'],'sent_signals':[{'name':h.sentSignals[i].name,'params':[plain(h.sentSignals[i].params[j]) for j in range(1,len(h.sentSignals[i].params)+1)],'types':[h.sentSignals[i].types[j] for j in range(1,len(h.sentSignals[i].types)+1)]} for i in range(1,len(h.sentSignals)+1)],'steps':len(steps),'assertions_passed':checked,'logs':[h.logs[i] for i in range(1,len(h.logs)+1)],'live_controls':len(list(h.controls.keys())),'unsupported_api_policy':'fail','rendering_verified':False,'editor_verified':False,'host_verified':False}

def run(source,scenario,bindings=None,mapping='main.lua',timeout=10):
 if type(timeout) not in (int,float) or not math.isfinite(timeout) or not .05<=timeout<=120:raise ValueError('模型超时须为0.05..120秒')
 if not isinstance(source,str) or not source:raise ValueError('模拟源码不能为空')
 try:request=json.dumps({'source':source,'scenario':scenario,'bindings':bindings,'mapping':mapping},ensure_ascii=False,allow_nan=False)
 except (TypeError,ValueError) as e:raise ValueError('模型输入必须是有限JSON数据：'+str(e)) from e
 env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(str(p) for p in sys.path);env['PYTHONDONTWRITEBYTECODE']='1'
 try:result=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--worker'],input=request,capture_output=True,text=True,encoding='utf-8',env=env,timeout=timeout)
 except subprocess.TimeoutExpired as e:raise ValueError('模拟执行超时，已终止本次独立模型进程；可能存在循环或回调过慢') from e
 try:response=json.loads(result.stdout)
 except ValueError as e:raise ValueError('模型进程未返回有效报告：'+result.stderr[-1200:]) from e
 if result.returncode or not response.get('ok'):
  raise ClientSimulationFailure(response.get('error','模型进程失败'),response.get('detail',{}))
 return {**response['result'],'isolated_process':True,'timeout_seconds':timeout}

def legacy_main(argv):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--scenario',required=True);p.add_argument('--level');p.add_argument('--mapping',default='main.lua');p.add_argument('--out');p.add_argument('--timeout',type=float,default=10);a=p.parse_args(argv)
 if a.out and Path(a.out).exists():raise ValueError('模拟报告已存在，请指定新文件')
 scene=json.loads(Path(a.scenario).read_text(encoding='utf-8-sig'))
 if scene.get('schema')==2:
  from joint_simulator import run as run_joint
  result=run_joint(scene,Path(a.scenario).resolve().parent,a.timeout)
  if a.out:
   with Path(a.out).open('x',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2)
  return result
 source_path=Path(a.source);raw=source_path.read_bytes();bindings=None
 if source_path.suffix.lower()=='.gil':
  if a.level:raise ValueError('源码已为GIL时不再提供--level，避免交付来源冲突')
  from level_authoring import inspect_bindings
  from level_inventory import container,fields,vals,unique
  bindings=inspect_bindings(raw);_,root=container(raw)
  matches=[unique(fields(e),5) for group in vals(root,50) for e in vals(fields(group),1) if unique(fields(e),3,default=b'').decode('utf-8')==a.mapping]
  if len(matches)!=1 or not matches[0]:raise ValueError('需要唯一完整映射名；现有='+repr([s['name'] for s in bindings['scripts']]))
  source=matches[0].decode('utf-8-sig')
 else:
  source=raw.decode('utf-8-sig')
  if a.level:
   from level_authoring import inspect_bindings
   bindings=inspect_bindings(Path(a.level).read_bytes())
 result=run(source,json.loads(Path(a.scenario).read_text(encoding='utf-8-sig')),bindings,a.mapping,a.timeout)
 result['input_file_sha256']=hashlib.sha256(raw).hexdigest()
 if a.out:
  with Path(a.out).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
 return result


def check_startup(path, mapping=None, timeout=10):
 path=Path(path).resolve()
 raw=path.read_bytes()
 report={'schema':2,'layer':'lua_model','scope':'startup','source':str(path),
         'input_sha256':hashlib.sha256(raw).hexdigest(),'mapping':mapping,'logs':[],
         'checks':{'startup':{'status':'not_checked'}},'diagnostics':[],
         'editor':'not_checked','host':'not_checked'}
 bindings=None
 if path.suffix.lower()=='.gil':
  from level_authoring import inspect_bindings
  from joint_simulator import script_from_gil
  bindings=inspect_bindings(raw)
  names=[s['name'] for s in bindings['scripts']]
  if mapping is None and len(names)==1:
   mapping=names[0]
  if names.count(mapping)!=1:
   report.update(status='failed',diagnostics=[{
    'code':'lua_mapping_required','message':'Choose one exact embedded script using --mapping.',
    'source':str(path),'expected':mapping,'available_mappings':names,
   }])
   return report
  source,_=script_from_gil(raw,mapping,bindings=bindings)
 elif path.suffix.lower()=='.lua' and mapping is None:
  source=raw.decode('utf-8-sig')
 else:
  raise ValueError('Startup check accepts .lua or .gil; --mapping requires a GIL')
 report['mapping']=mapping
 report['source_sha256']=hashlib.sha256(source.encode('utf-8')).hexdigest()
 try:
  startup=run(source,{'schema':1},bindings,mapping or 'main.lua',timeout)
 except ValueError as exc:
  detail=getattr(exc,'detail',{})
  diagnostic=detail.get('diagnostic',{'code':'lua_model_failed','message':str(exc)})
  report.update(status='failed',logs=detail.get('logs',[]),
                diagnostics=[{**diagnostic,'source':str(path),'mapping':mapping}])
 else:
  report.update(status='passed',logs=startup['logs'],live_controls=startup['live_controls'])
 report['checks']['startup']['status']=report['status']
 return report


def main(argv=None):
 args=list(sys.argv[1:] if argv is None else argv)
 commands=('check','run','replay','preview')
 # Retain the positional-source form, including a file whose name is a command.
 if args and args[0] not in ('-h','--help') and (
     args[0] not in commands or any(a=='--scenario' or a.startswith('--scenario=') for a in args[1:])):
  return legacy_main(args)
 parser=argparse.ArgumentParser(prog='qianxing.py simulate',description=__doc__,
                                epilog='Legacy: simulate SOURCE --scenario SCENE [--mapping NAME] [--out REPORT]')
 sub=parser.add_subparsers(dest='operation',required=True)
 check=sub.add_parser('check',help='Execute a single script through modeled startup')
 check.add_argument('input');check.add_argument('--mapping');check.add_argument('--timeout',type=float,default=10)
 joint=sub.add_parser('run',help='Validate a schema 2 client and native graph scenario')
 joint.add_argument('input');joint.add_argument('--out');joint.add_argument('--timeout',type=float,default=10)
 replay=sub.add_parser('replay',help='Rerun the exact scene and inputs from a failure report')
 replay.add_argument('input');replay.add_argument('--out');replay.add_argument('--timeout',type=float,default=10)
 preview=sub.add_parser('preview',help='Render a Beyond scene, optionally with assertions')
 preview.add_argument('input');preview.add_argument('--out',required=True);preview.add_argument('--backend')
 parsed=parser.parse_args(args)
 path=Path(parsed.input).resolve()
 try:
  if parsed.operation=='check':
   result=check_startup(path,parsed.mapping,parsed.timeout)
  elif parsed.operation=='preview':
   from beyond_backend import run as run_beyond
   result=run_beyond(path,parsed.backend,parsed.out,preview=True)
  else:
   from joint_simulator import run as run_joint, load_scenario, SimulationFailure
   if parsed.out and Path(parsed.out).exists():
    raise ValueError('Output exists; use a new report path')
   try:
    spec,base,inputs=load_scenario(path,replay=parsed.operation=='replay')
    result=run_joint(spec,base,parsed.timeout,expected_inputs=inputs)
   except SimulationFailure as exc:
    result=exc.detail
   if parsed.out:
    with Path(parsed.out).open('x',encoding='utf-8') as stream:
     json.dump(result,stream,ensure_ascii=False,indent=2)
 except (ValueError,OSError,TypeError,KeyError,ImportError,subprocess.SubprocessError) as exc:
  result={'status':'failed','checks':{},'diagnostics':[
   {'code':'simulation_input_or_runtime','message':str(exc),'source':str(path)}
  ]}
 print(json.dumps(result,ensure_ascii=False,indent=2))
 return 0 if result['status']=='passed' else 2


if __name__=='__main__':
 if sys.argv[1:]==['--worker']:
  try:
   request=json.loads(sys.stdin.read());value=_run_in_process(**request);print(json.dumps({'ok':True,'result':value},ensure_ascii=False,allow_nan=False))
  except Exception as error:
   print(json.dumps({'ok':False,'error':str(error),'detail':getattr(error,'detail',{})},ensure_ascii=False));raise SystemExit(2)
 else:
  try:
   result=main()
   if isinstance(result,dict):
    print(json.dumps(result,ensure_ascii=False,indent=2))
   else:
    raise SystemExit(result)
  except (ValueError,OSError,TypeError,KeyError) as error:print(str(error),file=sys.stderr);raise SystemExit(2)
