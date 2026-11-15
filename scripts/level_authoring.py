"""Generate Qianxing structures from typed inputs; never clone a complete game."""
from pathlib import Path
import argparse,hashlib,json,math,re,struct
from level_inventory import fields,vals,unique,container
import platform_schema as platform

SCHEMA='qianxing-level-spec/v1'
KINDS={'container':4,'text':5,'image':6,'area':7}
def vi(v):
 if type(v)!=int or not 0<=v<2**64:raise ValueError('整数超出uint64范围')
 out=bytearray()
 while v>=128:out.append((v&127)|128);v>>=7
 out.append(v);return bytes(out)
def integer(n,v):return vi(n*8)+vi(v)
def msg(n,v=b''):return vi(n*8+2)+vi(len(v))+v
def text(n,v):return msg(n,v.encode('utf-8'))
def flt(n,v):return vi(n*8+5)+struct.pack('<f',v)
def encode(rows):
 return b''.join(integer(n,v) if w==0 else msg(n,encode(v) if isinstance(v,list) else v) if w==2 else vi(n*8+w)+v for n,w,v in rows)
def pack(payload,header=(1,806,2)):
 return struct.pack('>5I',len(payload)+20,*header,len(payload))+payload+b'\0\0\x06\x79'
def repack(data,root):return pack(b''.join(r[3] for r in root),container(data)[0][1:4])
def set_section(data,n,value):
 header,root=container(data);matches=[f for f in root if f[:2]==(n,2)]
 if len(matches)>1:raise ValueError('重复的顶层字段：'+str(n))
 payload=b''.join(msg(n,value) if f[:2]==(n,2) else f[3] for f in root)
 if not matches:payload+=msg(n,value)
 return pack(payload,header[1:4])
def stream(b):
 # Packed protobuf varints have no tags. A synthetic wire-0 field supplies framing.
 result=[];pos=0
 while pos<len(b):
  v=0
  for shift in range(0,70,7):
   if pos>=len(b):raise ValueError('截断的ID列表')
   c=b[pos];pos+=1
   if shift==63 and c>1:raise ValueError('ID超出uint64')
   v|=(c&127)<<shift
   if c<128:result.append(v);break
  else:raise ValueError('无效ID列表')
 return result

def locator(g):return integer(2,1)+integer(3,8)+integer(4,g)
def self_meta(g):return msg(11,integer(501,g))+integer(501,1)+integer(502,5)
def kind_meta(k):return msg(12,integer(501,k))+integer(501,2)+integer(502,6)
def template_meta(g):return msg(13,integer(501,g))+integer(501,3)+integer(502,3)
def reverse_meta(gs):return msg(14,msg(501,b''.join(vi(g) for g in gs)))+integer(501,4)+integer(502,4)
def component(g,prop,typeid,base_tag,base_value,value_prop,value_tag,value):
 return msg(base_tag,base_value)+integer(501,prop)+integer(502,typeid)+msg(503,msg(value_tag,value)+integer(501,value_prop)+integer(502,typeid)+integer(503,1)+msg(504,locator(g)))
def rect(g,width,height,stretch=False):
 def xy(x,y):return flt(501,x)+flt(502,y)
 value=msg(501,flt(1,1)+flt(2,1)+flt(3,1))+msg(502,xy(0 if stretch else .5,0 if stretch else .5))+msg(503,xy(1 if stretch else .5,1 if stretch else .5))+msg(504)+msg(505,xy(width,height))+msg(506,xy(.5,.5))+msg(508)
 states=b''.join(msg(501,(integer(501,s) if s else b'')+msg(502,value)) for s in range(4))
 data=states+integer(502,25)+integer(504,1)
 return component(g,1,12,11,msg(12)+integer(501,2),4,13,msg(12,data)+integer(501,2))
def script_component(g,ids):
 value=integer(501,1)+msg(502,b''.join(msg(1,integer(1,i)) for i in ids)) if ids else b''
 return component(g,63,83,73,b'',65,74,value)
def control(g,name,kind='container',width=100,height=100,scripts=(),stretch=False):
 if kind not in KINDS:raise ValueError('不支持的控件类型：'+str(kind))
 out=integer(501,g)+msg(502,self_meta(g))+msg(505,msg(12,text(501,name))+integer(501,2)+integer(502,15))
 out+=msg(505,component(g,4,86,14,msg(17)+integer(501,7),5,14,msg(17)+integer(501,7)))+msg(505,rect(g,width,height,stretch))+msg(505,script_component(g,scripts))
 if kind=='text':out+=msg(505,component(g,64,84,74,b'',66,75,integer(501,20)+integer(503,12)+integer(504,0xffffffff)+integer(505,0xffffff)+integer(507,858993459)+msg(510)+integer(512,20)+integer(513,20)))
 if kind=='image':
  out+=msg(505,component(g,73,96,83,b'',75,84,integer(502,0xffffffff)))
  out+=msg(505,component(g,74,97,84,b'',76,85,integer(502,1)+integer(504,1)+integer(505,1)+integer(507,2)+integer(508,100)+integer(510,1)+msg(511,flt(501,8)+flt(502,8))+flt(512,85)+flt(513,85)+integer(515,1)))
 if kind=='area':out+=msg(505,component(g,65,85,75,b'',67,76,integer(501,1)))
 if kind=='container':out+=msg(505,component(g,68,91,78,b'',70,79,(integer(503,1)+integer(504,1)) if stretch else b''))
 out+=msg(505,component(g,67,90,77,b'',69,78,b''))
 return out

def ui_records(data):
 _,root=container(data);section=unique(root,9,default=b'')
 return [fields(x) for x in vals(fields(section),502)]
def script_records(data):
 _,root=container(data);out=[]
 for sec in vals(root,50):
  for e in vals(fields(sec),1):
   ef=fields(e);name=unique(ef,3,default=b'').decode('utf-8',errors='replace')
   out.append({'id':unique(ef,1,0),'name':name,'display_name':unique(ef,2,default=b'').decode('utf-8',errors='replace'),'bytes':len(unique(ef,5,default=b'')),'sha256':hashlib.sha256(unique(ef,5,default=b'')).hexdigest()})
 return out

def inspect_bindings(data):
 records=ui_records(data);known={unique(fs,501,0):fs for fs in records};scripts=script_records(data);script_ids={s['id'] for s in scripts};templates=[];bindings=[];diagnostics=[];names={}
 if len(known)!=len(records):diagnostics.append('控件GUID重复')
 for item in scripts:
  if type(item['id'])!=int or not item['name']:diagnostics.append('脚本映射缺少GUID或名称')
 if len(script_ids)!=len(scripts):diagnostics.append('脚本GUID重复')
 if len({item['name'] for item in scripts})!=len(scripts):diagnostics.append('脚本映射名称重复')
 for gid,fs in known.items():
  names[gid]=''
  for c in vals(fs,505):
   cf=fields(c)
   if unique(cf,501,0)==2:names[gid]=unique(fields(unique(cf,12,default=b'')),501,default=b'').decode('utf-8',errors='replace')
 for gid,fs in known.items():
  for m in vals(fs,502):
   mf=fields(m)
   # Only kind-marked prototype/library entries use meta13 as a template pointer.
   if unique(mf,501,0)!=3 or unique(mf,502,0)!=3:continue
   t=unique(fields(unique(mf,13,default=b'')),501,0)
   target=known.get(t);valid=False
   if target:
    for rm in vals(target,502):
     rf=fields(rm)
     if unique(rf,501,0)==4 and unique(rf,502,0)==4:
      valid=gid in stream(unique(fields(unique(rf,14,default=b'')),501,default=b''))
   kind=None
   for marker in vals(fs,502):
    meta=fields(marker)
    if unique(meta,501,0)==2 and unique(meta,502,0)==6:kind=unique(fields(unique(meta,12,default=b'')),501,0)
   kind=next((name for name,value in KINDS.items() if value==kind),'client-root' if kind==8 else None)
   templates.append({'kind':kind,'entry_guid':gid,'name':names[gid],'template_guid':t,'instantiation_index':t,'reciprocal_reference_verified':valid})
   if not valid:diagnostics.append('模板指向不存在或反向关联不匹配：'+str(gid))
  for c in vals(fs,505):
   cf=fields(c)
   if unique(cf,501,0)!=63 or unique(cf,502,0)!=83:continue
   for override in vals(cf,503):
    sf=fields(override)
    if unique(sf,501,0)!=65:continue
    script=fields(unique(sf,74,default=b''));group=fields(unique(script,502,default=b''))
    for ref in vals(group,1):
     sid=unique(fields(ref),1,0);bindings.append({'control_guid':gid,'control_name':names[gid],'script_guid':sid,'mapping_found':sid in script_ids})
     if sid not in script_ids:diagnostics.append('控件引用不存在的脚本映射：'+str(sid))
 return {'schema':'qianxing-client-bindings/v1','scripts':scripts,'controls':[{'guid':g,'name':names[g],'parent':unique(fs,504,0)} for g,fs in known.items()],'templates':templates,'script_bindings':bindings,'diagnostics':diagnostics,'editor_import_tested':False,'host_tested':False}

def register_script(data,name,code,display_name=None,script_id=None):
 if not isinstance(name,str) or not name.endswith('.lua') or not name.strip():raise ValueError('脚本映射名须为完整文件名，例如 main.lua')
 if not isinstance(code,bytes) or not code:raise ValueError('Lua源码不能为空')
 code.decode('utf-8-sig');existing=script_records(data)
 if any(s['name']==name for s in existing):raise ValueError('脚本映射已存在，更新请用replace-lua精确匹配：'+name)
 reserved={s['id'] for s in existing};sid=script_id if script_id is not None else max({0x40000000}|{x for x in reserved if type(x)==int})+1
 if type(sid)!=int or not 0x40000001<=sid<=0x7fffffff or sid in reserved:raise ValueError('脚本GUID越界或冲突')
 _,root=container(data);old=unique(root,50,default=b'');entries=fields(old)
 entry=integer(1,sid)+text(2,display_name or name[:-4])+text(3,name)+msg(5,code)
 # field2 is the observed script-folder marker, not a sequence counter.
 if len([f for f in entries if f[:2]==(2,0)])>1:raise ValueError('脚本文件夹标记重复，拒绝重写')
 payload=b''.join(raw for n,w,v,raw in entries)+msg(1,entry)
 if not any(f[:2]==(2,0) for f in entries):payload+=integer(2,1)
 return set_section(data,50,payload),sid

def bind_script(data,control_guid,script_id):
 scripts={s['id'] for s in script_records(data)}
 if script_id not in scripts:raise ValueError('脚本GUID不存在，请先注册映射')
 _,root=container(data);section=unique(root,9,default=b'');records=fields(section);found=0;output=[]
 for n,w,v,raw in records:
  if (n,w)!=(502,2) or unique(fields(v),501,0)!=control_guid:output.append(raw);continue
  found+=1;fs=fields(v);cs=[c for c in vals(fs,505) if unique(fields(c),501,0)==63]
  if len(cs)>1:raise ValueError('脚本组件重复，拒绝改写')
  # Preserve all other components and every existing script binding.
  ids=[b['script_guid'] for b in inspect_bindings(data)['script_bindings'] if b['control_guid']==control_guid]
  if script_id not in ids:ids.append(script_id)
  def put(blob,key,value):
   parsed=fields(blob);hits=[f for f in parsed if f[:2]==(key,2)]
   if len(hits)>1:raise ValueError('脚本组件嵌套字段重复')
   result=b''.join(msg(key,value) if f[:2]==(key,2) else f[3] for f in parsed)
   return result if hits else result+msg(key,value)
  replacement=script_component(control_guid,ids)
  if cs:
   cf=fields(cs[0]);overrides=[f for f in cf if f[:2]==(503,2) and unique(fields(f[2]),501,0)==65]
   if len(overrides)!=1:raise ValueError('未识别的脚本属性布局，拒绝覆盖')
   target=overrides[0];script_value=unique(fields(target[2]),74,default=b'')
   group=unique(fields(script_value),502,default=b'')
   present=[unique(fields(v),1,0) for v in vals(fields(group),1)]
   if script_id not in present:group+=msg(1,integer(1,script_id))
   changed=put(target[2],74,put(script_value,502,group))
   replacement=b''.join(msg(503,changed) if f is target else f[3] for f in cf)
  component_bytes=msg(505,replacement)
  out=b''.join(component_bytes if a==505 and unique(fields(b),501,0)==63 else r for a,c,b,r in fs)
  if not cs:out+=component_bytes
  output.append(msg(502,out))
 if found!=1:raise ValueError('挂载控件GUID缺失或不唯一：'+str(control_guid))
 result=set_section(data,9,b''.join(output));report=inspect_bindings(result)
 if report['diagnostics']:raise ValueError('挂载回读失败：'+repr(report['diagnostics']))
 return result

def initial_level(identifier,map_size=(20,20)):
 if not isinstance(identifier,str) or not identifier.strip():raise ValueError('存档标识不能为空')
 if not isinstance(map_size,(list,tuple)) or len(map_size)!=2:raise ValueError('map_size需要宽高两个整数')
 width,height=map_size
 if any(type(v)!=int or not 1<=v<=20 for v in map_size):raise ValueError('当前已校准地图范围为1..20格')
 sections={n:encode(getattr(platform,name)) for n,name in platform.PLATFORM_SECTIONS.items()}
 map_record=integer(1,0x40000001)+msg(2,text(1,'Map'))+msg(3,msg(1,flt(1,-547.5)+flt(2,-2.5)+flt(3,-547.5))+msg(2))
 map_record+=b''.join(msg(4,integer(1,((100+x)<<16)|(100+z))+integer(2,1)) for x in range(width) for z in range(height))
 sections[7]=msg(1,map_record);sections[10]=b'';sections[9]=b''
 root=text(2,identifier)
 for n in [3,4,5,6,7,8,9,10,11,12,14,15,16,17,18,19,20,21,22,23,25,27,29,30,31,32,33,35,36,37,38,43,44,45,46,48,49,50]:root+=msg(n,sections.get(n,b''))
 return pack(root+integer(40,0)+integer(41,2))

LUA_KEYWORDS=set('and break do else elseif end false for function goto if in local nil not or repeat return then true until while'.split())
def with_template_alias(code,alias,indices):
 if not isinstance(alias,str) or not re.fullmatch(r'[A-Za-z_]\w*',alias) or alias in LUA_KEYWORDS:raise ValueError('templates_as需要有效Lua变量名，不能是关键字')
 from asset_pipeline import lua
 prefix=('-- qianxing-template-alias: '+alias+'\nlocal '+alias+' = '+lua(indices)+'\n').encode('utf-8')
 if code.startswith(prefix):return code
 if code.startswith(b'-- qianxing-template-alias:'):raise ValueError('源码含不同或过期模板前缀，请使用未生成的原始Lua输入')
 return prefix+code.decode('utf-8-sig').encode('utf-8')

def compile_spec(spec,base):
 if not isinstance(spec,dict) or set(spec)-{'schema','id','scripts','root_script','templates','map_size'} or spec.get('schema')!=SCHEMA:raise ValueError('需要qianxing-level-spec/v1，存在未知或缺失字段')
 data=initial_level(spec.get('id','qianxing_level'),spec.get('map_size',[20,20]));sources={};script_ids={};script_sources={};aliases={}
 scripts=spec.get('scripts',[])
 if not isinstance(scripts,list):raise ValueError('scripts须为列表')
 for s in scripts:
  if not isinstance(s,dict) or set(s)-{'name','source','templates_as'} or not {'name','source'}<=set(s):raise ValueError('脚本项需要name/source，可选templates_as')
  src=(Path(base)/s['source']).resolve();code=src.read_bytes();sources[str(src)]=hashlib.sha256(code).hexdigest();data,sid=register_script(data,s['name'],code);script_ids[s['name']]=sid
  script_sources[s['name']]=code
  if 'templates_as' in s:aliases[s['name']]=s['templates_as']
 name=spec.get('root_script')
 if name is not None and name not in script_ids:raise ValueError('root_script未在scripts中注册：'+str(name))
 templates=spec.get('templates',[])
 if not isinstance(templates,list) or not templates:raise ValueError('至少声明一个控件模板')
 names=set();records=[];registry=[];indices={};next_id=0x40001000
 def alloc():
  nonlocal next_id
  next_id+=1;return next_id
 def group_record(g,name,kind,width,height,metas=(),parent=None):
  out=control(g,name,kind,width,height)
  for meta in metas:out+=msg(502,meta)
  if parent is not None:out+=integer(504,parent)
  return out
 # Keep the calibrated default layout GUID; all application-owned GUIDs are allocated.
 layout=0x40000001;library=alloc();root_template=alloc();layout_group=alloc();root_actual=alloc();library_group=alloc();library_actual=alloc()
 root_control=control(root_actual,'Root','container',0,0,[script_ids[name]] if name else [],True)
 library_control=control(library_actual,'Root','container',0,0,[script_ids[name]] if name else [],True)
 def client_group(g,actual,metas=(),parent=None):
  # Client-UI group: kind 8, object type 23, component 62 refers to the actual root control.
  out=integer(501,g)+msg(502,self_meta(g))+msg(505,msg(12,text(501,'ClientUI'))+integer(501,2)+integer(502,15))
  for meta in metas:out+=msg(502,meta)
  if parent is not None:out+=integer(504,parent)
  out+=msg(505,component(g,4,23,14,msg(15)+integer(501,5),5,14,msg(15)+integer(501,5)))+msg(505,rect(g,0,0,True))+msg(505,component(g,62,82,72,b'',64,73,integer(501,actual)))
  return out
 layout_record=integer(501,layout)+msg(502,self_meta(layout))+msg(502,msg(15)+integer(501,5)+integer(502,7))+msg(503,vi(layout_group))+msg(505,msg(12,text(501,'Layout'))+integer(501,2)+integer(502,15))+msg(505,component(layout,1,11,11,msg(11)+integer(501,1),4,13,msg(11)+integer(501,1)))
 records += [layout_record,client_group(root_template,root_actual,[kind_meta(8),reverse_meta([layout_group,library_group])]),client_group(layout_group,root_actual,[kind_meta(8),template_meta(root_template)],layout),root_control,client_group(library_group,library_actual,[kind_meta(8),template_meta(root_template)],library),library_control]
 registry=[root_template,layout,library]
 for t in templates:
  if not isinstance(t,dict) or set(t)-{'name','kind','size'} or not {'name','kind'}<=set(t):raise ValueError('模板项需要name/kind，可选size')
  n=t['name'];k=t['kind'];size=t.get('size',[100,100])
  if not isinstance(n,str) or not n.strip() or n in names or k not in KINDS:raise ValueError('模板名称重复或类型不支持')
  if not isinstance(size,list) or len(size)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in size):raise ValueError('模板size需要两个正数')
  names.add(n);template=alloc();entry=alloc();registry.insert(0,template);indices[n]=template
  records.append(group_record(template,n,k,*size,[kind_meta(KINDS[k]),reverse_meta([entry])]))
  records.append(group_record(entry,n,k,*size,[kind_meta(KINDS[k]),template_meta(template)],library))
 # A prototype hierarchy root records entries; records hold actual GUID indices, never list ordinals.
 children=[unique(fields(rec),501,0) for rec in records if unique(fields(rec),504,0)==library]
 library_record=integer(501,library)+msg(502,self_meta(library))+msg(502,msg(21)+integer(501,11)+integer(502,88))+msg(503,b''.join(vi(g) for g in children))+msg(505,msg(12,text(501,'ClientUIPrototypeHierarchyRoot'))+integer(501,2)+integer(502,15))
 records.append(library_record)
 data=set_section(data,9,msg(501,b''.join(vi(i) for i in registry))+b''.join(msg(502,r) for r in records))
 for mapping,alias in aliases.items():
  from production_core import replace_lua
  data=replace_lua(data,mapping,with_template_alias(script_sources[mapping],alias,indices))
 report=inspect_bindings(data)
 if report['diagnostics']:raise ValueError('生成关联不闭合：'+repr(report['diagnostics']))
 report.update(template_indices=indices,template_aliases=aliases)
 report.update(generator='genshin-ugc-native-authoring',whole_game_template_used=False,source_sha256=sources,sha256=hashlib.sha256(data).hexdigest(),structural_generation=True,playable_level_verified=False)
 return data,report

def create(spec_path,out):
 p=Path(spec_path).resolve();data,report=compile_spec(json.loads(p.read_text(encoding='utf-8-sig')),p.parent)
 out=Path(out).resolve()
 if out.suffix.lower()!='.gil':raise ValueError('输出扩展名须为.gil')
 if out.exists():raise ValueError('输出已存在，请选择新文件：'+str(out))
 out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as f:f.write(data)
 return {**report,'output':str(out)}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='op',required=True)
 c=s.add_parser('create');c.add_argument('spec');c.add_argument('--out',required=True)
 i=s.add_parser('inspect');i.add_argument('input')
 b=s.add_parser('bind');b.add_argument('input');b.add_argument('--control',type=int,required=True);b.add_argument('--script',required=True);b.add_argument('--mapping',required=True);b.add_argument('--out',required=True)
 a=p.parse_args(argv)
 if a.op=='create':return create(a.spec,a.out)
 data=Path(a.input).read_bytes()
 if a.op=='inspect':return inspect_bindings(data)
 target=Path(a.out).resolve()
 if target.exists() or target==Path(a.input).resolve():raise ValueError('不覆盖原文件或现有输出，请选择新文件')
 data,sid=register_script(data,a.mapping,Path(a.script).read_bytes());data=bind_script(data,a.control,sid)
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(data)
 return {**inspect_bindings(data),'output':str(target),'sha256':hashlib.sha256(data).hexdigest()}
if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
