"""Parameterised single-record storage slots and achievement resources; no game assets."""
from pathlib import Path
import argparse,json,re
from authoring_io import *
from protocol_types import TYPES,valid
from native_core import get,model,inspect as native_inspect,register_definitions
from level_authoring import msg,integer,text,vi,pack,set_section
from level_inventory import fields,vals

def validate(spec):
    version=spec.get('schema')if isinstance(spec,dict)else None
    if version not in(2,3):raise ValueError('Storage schema must be 2 or 3')
    schema(spec,('schema','name','struct_id','template_id','graph_id','host_entity_id','fields','slots','dictionary','previous_dictionary','capacity_bytes','record_version','compatible_record_version','achievements'),('name','struct_id','template_id','graph_id','fields','slots','capacity_bytes'),version=version)
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,31}',spec['name']):raise ValueError('Invalid storage name')
    if type(spec['slots'])!=int or not 1<=spec['slots']<=32:raise ValueError('slots must be 1..32')
    if len(spec['name']+'_slot_'+str(spec['slots']))>20:raise ValueError('Generated storage variable name exceeds native 20-character limit')
    if type(spec['capacity_bytes'])!=int or spec['capacity_bytes']<1:raise ValueError('Positive capacity required')
    if type(spec.get('record_version',1))!=int or not 1<=spec.get('record_version',1)<=65535:raise ValueError('record_version must be 1..65535')
    if 'compatible_record_version'in spec:
        old=spec['compatible_record_version']
        if version!=3 or type(old)is not int or not 1<=old<spec.get('record_version',1):
            raise ValueError('compatible_record_version requires a lower schema 3 record version with the same field layout')
        if spec.get('previous_dictionary') is not None and spec.get('previous_dictionary')!=spec.get('dictionary'):
            raise ValueError('Record version upgrade requires an unchanged integer-list dictionary')
    for key in ('struct_id','template_id','graph_id'):
        if type(spec[key])!=int or not 2**30<=spec[key]<2**31:raise ValueError('Explicit application ID required')
    seen=set()
    if not spec['fields']:raise ValueError('Storage fields required')
    for f in spec['fields']:
        schema(f,('name','type','default','confirm','max_items'),('name','type','default','confirm'))
        reserved=('self','request','records','record','updated','count','compatible','complete')+ (('session','revision','ok')if version==3 else())
        pattern=r'[A-Za-z_][A-Za-z0-9_]*'if version==3 else r'[A-Za-z_]\w*'
        if not re.fullmatch(pattern,f['name']) or f['name'] in seen or f['name'].startswith('qx_')or f['name']in reserved:raise ValueError('Unique non-reserved identifier field names required')
        seen.add(f['name'])
        if f['type'] not in ('integer','boolean','integer_list') or not valid(f['type'],f['default']):raise ValueError('Calibrated storage fields: integer, boolean, integer_list')
        if f['confirm'] not in ('equal','min','max','contains_bits') or f['type']!='integer'and f['confirm']!='equal':raise ValueError('Invalid confirmation policy')
        if 'max_items'in f and(f['type']!='integer_list'or type(f['max_items'])!=int or f['max_items']<0):raise ValueError('max_items requires an integer list and a nonnegative limit')
        if f['type']=='integer_list'and len(f['default'])>f.get('max_items',spec['capacity_bytes']//8):raise ValueError('Default list exceeds declared capacity')
    logical=(40 if version==3 else 8)+sum(8 if f['type']=='integer'else 1 if f['type']=='boolean'else 8*len(f['default'])for f in spec['fields'])
    if logical>spec['capacity_bytes']:raise ValueError('Default logical payload exceeds capacity_bytes')
    d=spec.get('dictionary',[]);old=spec.get('previous_dictionary',[])
    if any(not isinstance(s,str)for s in d)or len(set(d))!=len(d)or d[:len(old)]!=old:raise ValueError('Dictionary must be append-only')
    ids=set()
    for a in spec.get('achievements',[]):
        schema(a,('id','name','goal'),('id','name','goal'))
        if type(a['id'])!=int or a['id']<1 or a['id']in ids or type(a['goal'])!=int or a['goal']<1:raise ValueError('Invalid achievement ID/goal')
        ids.add(a['id'])
    return spec
def wire_fields(spec):
    meta=[{'name':'qx_record_version','type':'integer','default':spec.get('record_version',1),'confirm':'equal'}]
    if spec['schema']==3:meta += [{'name':name,'type':'integer','default':value,'confirm':'equal'}for name,value in [('qx_protocol',3),('qx_session',0),('qx_revision',0),('qx_request',0)]]
    return [*meta,*spec['fields']]
def native_sections(spec):
    """Calibrated field rules: no opaque full-level template is embedded."""
    s=validate(spec);members=[]
    for index,f in enumerate(wire_fields(s),1):
        t=TYPES[f['type']][1];descriptor=integer(1,t)+msg(2)
        if t==8:default=msg(18,msg(1,b''.join(vi(x%2**64)for x in f['default'])))
        else:default=msg(10+t,integer(1,int(f['default'])%2**64) if f['default'] else b'')
        value=integer(1,t)+msg(2,descriptor)+default
        member=msg(1,descriptor)+msg(3,value)+text(5,f['name'])+text(501,f['name'])+integer(502,t)+integer(503,index)
        members.append(msg(3,member))
    body=integer(1,s['struct_id'])+integer(2,2)+b''.join(members)+text(501,s['name'])+integer(502,1)+integer(503,3)
    wrapper=msg(1,body)+msg(2,body)+integer(3,3)+integer(4,len(members))+integer(5,1)
    records=b''.join(msg(2,integer(1,i)+msg(2,integer(1,1)+integer(2,s['struct_id']))+integer(3,1)+text(4,s['name']+'_slot_'+str(i)))for i in range(1,s['slots']+1))
    save=msg(1,integer(1,s['template_id'])+msg(2,integer(1,1)+records+text(501,s['name'])))
    achievements=integer(2,1)+integer(5,1)+b''.join(msg(4,integer(1,a['id'])+text(2,a['name'])+integer(6,a['goal']))for a in s.get('achievements',[]))
    return wrapper,save,achievements
def attach(data,spec):
    wrapper,save,achievements=native_sections(spec);m=model(data)
    if any(get(get(d,1,default=b''),1,0)==spec['struct_id']for d in m['structs']):raise ValueError('Structure ID collision')
    current=get(data[20:-4],31,default=b'')
    if any(get(t,1,0)==spec['template_id']for t in vals(fields(current),1)):raise ValueError('Save template ID collision')
    section=get(data[20:-4],10,default=b'')+msg(6,wrapper)
    if not vals(fields(section),2):
        # The upstream struct importer requires assembly/split/update definition
        # prototypes. Retain only its calibrated declarations, never seed graphs.
        calibration=PLUGIN/'vendor/ayaya/private_extensions/ugc_file_tools/builtin_resources/seeds/ingame_save_structs_bootstrap.gil'
        calibrated=model(calibration.read_bytes());definitions=calibrated['definitions']
        # These retained helper declarations reference their calibration types
        # even when no graph instantiates them. Keep that dependency closure;
        # never import the seed's graphs, entities or storage layouts.
        existing_structs={get(get(d,1,default=b''),1,0):d for d in model(set_section(data,10,section))['structs']}
        for structure in calibrated['structs']:
            sid=get(get(structure,1,default=b''),1,0)
            if sid in existing_structs:
                if existing_structs[sid]!=structure:raise ValueError('Calibration structure identity collision '+str(sid))
            else:section+=msg(6,structure)
        section+=b''.join(msg(2,msg(1,d))for d in definitions.values())
    # Build exact field ports, not an all-fields prototype bound to another ID.
    existing=model(set_section(data,10,section))['definitions'];next_id=max([1610612739,*existing])+1
    uid=max([0,*[get(p,8,0,0)for d in existing.values()for key in(100,101,102,103,106)for p in vals(fields(d),key)]])+1
    struct_desc=integer(1,10001)+integer(3,25)+integer(4,25)+msg(104,integer(2,spec['struct_id']))
    def descriptor(kind):
        if kind=='integer':return integer(1,2)+integer(3,3)+integer(4,3)
        if kind=='boolean':return integer(1,6)+integer(3,4)+integer(4,4)+msg(101,integer(1,1))
        return integer(1,10002)+integer(3,8)+integer(4,8)+msg(102,msg(1,descriptor('integer')))
    def port(name,kind,index,desc,struct=False):
        nonlocal uid
        raw=text(1,name)+integer(2,1)+msg(3,integer(1,kind)+(integer(2,index)if index else b''))+msg(4,desc)+(msg(5,integer(1,13))if struct else b'')+integer(8,uid);uid+=1;return raw
    for offset,title in enumerate(('拼装结构体','拆分结构体')):
        r=integer(1,10001)+integer(2,20000)+integer(3,22001)+integer(5,next_id+offset)
        d=msg(4,msg(1,r)+msg(2,r)+msg(4))
        if offset==0:
            d+=b''.join(msg(102,port(f['name'],3,i,descriptor(f['type'])))for i,f in enumerate(wire_fields(spec)))+msg(103,port('结构体',4,0,struct_desc,True))
        else:
            d+=msg(102,port('结构体',3,0,struct_desc,True))+b''.join(msg(103,port(f['name'],4,i,descriptor(f['type'])))for i,f in enumerate(wire_fields(spec)))
        d+=msg(107,integer(1,1003+offset)+msg(104+offset,integer(1,spec['struct_id'])))+text(200,title)+integer(203,5)+integer(204,4)
        section+=msg(2,msg(1,d))
    data=set_section(set_section(data,10,section),31,current+save)
    if spec.get('achievements'):
        settings=get(data[20:-4],25,default=b'');old=get(settings,3,default=b'');ids={get(a,1,0)for a in vals(fields(old),4)}
        if any(a['id']in ids for a in spec['achievements']):raise ValueError('Achievement ID collision')
        from native_core import put
        merged=old+b''.join(msg(4,a)for a in vals(fields(achievements),4));merged=put(put(merged,2,1,0),5,1,0)
        data=set_section(data,25,put(settings,3,merged))
    return register_definitions(data)
def generate(spec,stage,*,server_only=False):
    s=validate(spec);name=s['name'];fs=s['fields'];signals=[];methods=[]
    annotations={'integer':'整数','boolean':'布尔值','integer_list':'整数列表'}
    wire=wire_fields(s);version=s.get('record_version',1)
    struct={'type':'Struct','struct_name':name,'struct_ype':'basic','fields':[{'field_name':f['name'],'param_type':annotations[f['type']],'default_value':{'value':f['default']}}for f in wire]}
    folder=stage/'resources/管理配置/结构体定义/局内存档结构体';folder.mkdir(parents=True)
    # Graph Code's semantic binder accepts basic field shapes; the ingame-save
    # resource directory controls native persistence (native struct kind=2).
    (folder/(name+'.py')).write_text('STRUCT_ID = '+repr(str(s['struct_id']))+'\nSTRUCT_TYPE = "basic"\nSTRUCT_PAYLOAD = '+repr(struct)+'\n',encoding='utf-8')
    basic=stage/'resources/管理配置/结构体定义/基础结构体';basic.mkdir(parents=True)
    (basic/(name+'.py')).write_bytes((folder/(name+'.py')).read_bytes())
    if s['schema']==3:
        from storage_v3 import graph_methods
        signals,methods=graph_methods(s,wire)
    for slot in (range(1,s['slots']+1)if s['schema']==2 else []):
        variable=name+'_slot_'+str(slot)
        for action in ('read','write'):
            signal=name+'_'+action+'_'+str(slot);reply=signal+'_reply'
            params=[{'name':'request','parameter_type':'整数'}]+([{'name':f['name'],'parameter_type':annotations[f['type']]}for f in fs]if action=='write'else [])
            signals.append((signal,params));signals.append((reply,[{'name':'request','parameter_type':'整数'},{'name':'ok','parameter_type':'布尔值'}]+[{'name':f['name'],'parameter_type':annotations[f['type']]}for f in fs]))
            signature=', '.join(['事件源实体: "实体"','事件源GUID: "GUID"','信号来源实体: "实体"','request: "整数"']+([f['name']+': '+repr(annotations[f['type']])for f in fs]if action=='write'else []))
            defaults=', '.join(f['name']+'='+('qx_empty_'+f['name']if f['type']=='integer_list'and not f['default']else repr(f['default']))for f in fs)
            wire_defaults=', '.join(f['name']+'='+('[0,0]'if f['type']=='integer_list'else repr(f['default']))for f in wire)
            def aliases(tag):return {f['name']:f['name']+'字段_'+tag for f in wire}
            def split_lines(indent,source,tag):
                names=aliases(tag)
                return [indent+names[f['name']]+': '+repr(annotations[f['type']])+' = '+repr(f['default'])for f in wire if f['type']!='integer_list']+[indent+', '.join(names[f['name']]for f in wire)+' = 拆分结构体(self.game, 结构体='+source+', 结构体名='+repr(name)+', '+wire_defaults+')']
            def reply_fields(tag):return ', '.join(f['name']+'='+aliases(tag)[f['name']]for f in fs)
            def write_lines(indent):
                rows=[indent+'qx_updated_record: "结构体" = 拼装结构体(self.game, 结构体名='+repr(name)+', qx_record_version='+str(version)+', '+', '.join(f['name']+'='+f['name']for f in fs)+')',indent+'updated: "结构体列表" = 拼装列表(self.game, qx_updated_record)',indent+'设置自定义变量(self.game, 目标实体=信号来源实体, 变量名='+repr(variable)+', 变量值=updated, 是否触发事件=False)',indent+'qx_readback_records: "结构体列表" = 获取自定义变量(self.game, 目标实体=信号来源实体, 变量名='+repr(variable)+')',indent+'qx_readback_count: "整数" = 获取列表长度(self.game, 列表=qx_readback_records)',indent+'if qx_readback_count == 1:',indent+'    qx_readback_record: "结构体" = 获取列表对应值(self.game, 列表=qx_readback_records, 序号=0)']
                rows+=split_lines(indent+'    ','qx_readback_record','saved')
                rows+=[indent+'    发送信号(self.game, 信号名='+repr(reply)+', request=request, ok='+aliases('saved')['qx_record_version']+' == '+str(version)+', '+reply_fields('saved')+')',indent+'else:',indent+'    发送信号(self.game, 信号名='+repr(reply)+', request=request, ok=False, '+defaults+')']
                return rows
            lines=['    def on_'+signal+'(self, '+signature+'):','        records: "结构体列表" = 获取自定义变量(self.game, 目标实体=信号来源实体, 变量名='+repr(variable)+')','        count: "整数" = 获取列表长度(self.game, 列表=records)','        if count == 1:','            record: "结构体" = 获取列表对应值(self.game, 列表=records, 序号=0)']
            lines+=split_lines('            ','record','current')
            lines+=['            if '+aliases('current')['qx_record_version']+' == '+str(version)+':']
            lines+=write_lines('                ')if action=='write'else['                发送信号(self.game, 信号名='+repr(reply)+', request=request, ok=True, '+reply_fields('current')+')']
            lines+=['            else:','                发送信号(self.game, 信号名='+repr(reply)+', request=request, ok=False, '+defaults+')','        elif count == 0:']
            lines+=write_lines('            ')if action=='write'else['            发送信号(self.game, 信号名='+repr(reply)+', request=request, ok=True, '+defaults+')']
            lines+=['        else:','            发送信号(self.game, 信号名='+repr(reply)+', request=request, ok=False, '+defaults+')']
            if action=='write':
                fixed=8+sum(8 if f['type']=='integer'else 1 if f['type']=='boolean'else 0 for f in fs)
                lists=[f for f in fs if f['type']=='integer_list']
                size=str(fixed)+''.join(' + 获取列表长度(self.game, 列表='+f['name']+') * 8'for f in lists)
                checks=['('+size+') <= '+str(s['capacity_bytes'])]+['获取列表长度(self.game, 列表='+f['name']+') <= '+str(f.get('max_items',s['capacity_bytes']//8))for f in lists]
                lines=[lines[0],'        if '+' and '.join(checks)+':',*['    '+line for line in lines[1:]],'        else:','            发送信号(self.game, 信号名='+repr(reply)+', request=request, ok=False, '+defaults+')']
            empty=[]
            for f in fs:
                if f['type']=='integer_list'and not f['default']:empty+=['        qx_seed_'+f['name']+': "整数列表" = 拼装列表(self.game, 0)','        qx_empty_ref_'+f['name']+', qx_empty_'+f['name']+' = 获取局部变量(self.game, 初始值=qx_seed_'+f['name']+')','        清除列表(self.game, 列表=qx_empty_'+f['name']+')']
            lines=[lines[0],*empty,*lines[1:]]
            methods.append('\n'.join(lines))
    for a in s.get('achievements',[]):
        signal=name+'_achievement_'+str(a['id']);signals.append((signal,[{'name':'request','parameter_type':'整数'}]))
        signals.append((signal+'_reply',[{'name':'request','parameter_type':'整数'},{'name':'ok','parameter_type':'布尔值'}]))
        methods.append('    def on_'+signal+'(self, 事件源实体: "实体", 事件源GUID: "GUID", 信号来源实体: "实体", request: "整数"):\n        设置成就进度计数(self.game, 设置实体=信号来源实体, 成就序号='+str(a['id'])+', 进度计数='+str(a['goal'])+')\n        complete: "布尔值" = 查询成就是否完成(self.game, 目标实体=信号来源实体, 成就序号='+str(a['id'])+')\n        发送信号(self.game, 信号名='+repr(signal+'_reply')+', request=request, ok=complete)')
    folder=stage/'resources/管理配置/信号';folder.mkdir(parents=True)
    for signal,params in signals:
        (folder/(signal+'.py')).write_text('SIGNAL_ID = '+repr(signal)+'\nSIGNAL_PAYLOAD = '+repr({'signal_name':signal,'parameters':params})+'\n',encoding='utf-8')
    if server_only:
        guarded=[]
        for method in methods:
            signature,*body=method.splitlines()
            guard=['        qx_owner: "实体" = 获取自身实体(self.game)',
                   '        if 信号来源实体 == qx_owner:']
            guarded.append('\n'.join([signature,*guard,*['    '+line for line in body]]))
        methods=guarded
    code='"""\ngraph_id: '+str(s['graph_id'])+'\ngraph_name: '+name+'\ngraph_type: server\n"""\nfrom app.runtime.engine.graph_prelude_server import *\nclass '+name+':\n    def __init__(self, game, owner_entity):\n        self.game = game\n        self.owner_entity = owner_entity\n    def register_handlers(self):\n        return\n'+'\n\n'.join(methods)+'\n'
    (stage/'storage.py').write_text(code,encoding='utf-8')
    write_json(stage/'storage.json',s)
    report={'signals':len(signals),'slots':s['slots'],'fields':len(fs),'record_version':version,
            'capacity_bytes':s['capacity_bytes'],'default_logical_bytes':(40 if s['schema']==3 else 8)+sum(
                8 if f['type']=='integer'else 1 if f['type']=='boolean'else 8*len(f['default'])for f in fs),
            'capacity_kind':'application logical payload and codec budget; host quota unverified',
            'native_config_created':True,'compiled':False}
    if server_only:
        write_json(stage/'server-signals.json',{'request_source':'player entity','definitions':dict(signals)})
        return {**report,'transport':'server'}
    from asset_pipeline import lua
    (stage/'contract.lua').write_text('return '+lua(s)+'\n',encoding='utf-8')
    (stage/'runtime.lua').write_bytes((PLUGIN/'scripts/runtime_storage.lua').read_bytes())
    adapter='''return function(game,script,slot,timeout,retries)
 local Runtime=(function()
RUNTIME
 end)()
 local contract=CONTRACT
 local methods=METHODS
 assert(math.type(slot)=='integer'and slot>=1 and slot<=contract.slots)
 local tx=Runtime.transaction(contract.fields,function(kind,request,values)
  local s=game.ServerSignal(contract.name..'_'..kind..'_'..slot);s:AddInt(request)
  if kind=='write'then for i,f in ipairs(contract.fields)do s[methods[f.type]](s,values[i])end end s:SendSignal()
 end,timeout,retries)
 local codec=Runtime.codec(contract.dictionary or{},contract.capacity_bytes,contract.record_version or 1)
 local write=tx.write
 function tx:write(values,exitIntent)
  assert(type(values)=='table'and #values==#contract.fields,'record field count')local bytes=8
  for i,f in ipairs(contract.fields)do local value=values[i]
   if f.type=='integer'then assert(math.type(value)=='integer')bytes=bytes+8
   elseif f.type=='boolean'then assert(type(value)=='boolean')bytes=bytes+1
   else assert(type(value)=='table'and #value<=(f.max_items or contract.capacity_bytes//8))
    for k,v in pairs(value)do assert(math.type(k)=='integer'and k>=1 and k<=#value and math.type(v)=='integer')end bytes=bytes+8*#value
   end
  end assert(bytes<=contract.capacity_bytes,'logical record capacity exceeded')return write(self,values,exitIntent)
 end
 function tx:encode(value,words)local body=codec:encode(value)return codec:words(body,words),{encoded_bytes=#body,capacity_bytes=contract.capacity_bytes,native_words=words}end
 function tx:decode(words)return codec:decode(codec:from_words(words))end
 function tx:write_encoded(value,index,words,exitIntent)
  assert(self.cache and contract.fields[index].type=='integer_list','encoded storage field required')
  if #self.cache[index]>0 then self:decode(self.cache[index])end
  local values={}for i,v in ipairs(self.cache)do values[i]=v end values[index]=self:encode(value,words)return self:write(values,exitIntent)
 end
 for _,kind in ipairs({'read','write'})do
  local signal=contract.name..'_'..kind..'_'..slot..'_reply'
  script:RegisterServerSignalHandler(signal,function(_,p)local values={}for i=1,#contract.fields do values[i]=p[i+2]end tx:receive(p[1],kind,values,p[2])end)
 end
 local known={}for _,a in ipairs(contract.achievements or{})do known[a.id]=true end
 local achievement=Runtime.achievements(function(id,request)assert(known[id],'unconfigured achievement');local signal=game.ServerSignal(contract.name..'_achievement_'..id);signal:AddInt(request);signal:SendSignal()end)
 tx.achievement=achievement
 for _,a in ipairs(contract.achievements or{})do
  script:RegisterServerSignalHandler(contract.name..'_achievement_'..a.id..'_reply',function(_,p)achievement:ack(p[1],a.id,p[2])end)
 end
 function tx:close()
  for _,kind in ipairs({'read','write'})do script:UnregisterServerSignalHandler(contract.name..'_'..kind..'_'..slot..'_reply')end
  for _,a in ipairs(contract.achievements or{})do script:UnregisterServerSignalHandler(contract.name..'_achievement_'..a.id..'_reply')end
 end
 return tx
end
'''.replace('RUNTIME',(PLUGIN/'scripts/runtime_storage.lua').read_text(encoding='utf-8')).replace('CONTRACT',lua(s)).replace('METHODS',lua({k:v[2]for k,v in TYPES.items()}))
    (stage/'client_adapter.lua').write_text(adapter,encoding='utf-8')
    if s['schema']==3:
        from storage_v3 import client_adapter
        (stage/'client_adapter.lua').write_text(client_adapter(s,adapter),encoding='utf-8')
    return report
def build(path,out,*,server_only=False):
    p=Path(path).resolve();s=validate(read_json(p))
    with output_directory(out)as stage:
        info=generate(s,stage,server_only=server_only);return finish(stage,{str(p):sha(p.read_bytes())},kind='storage',**info)
def diagnose(events):
    groups={}
    for e in events:
        schema(e,('player','request','phase','fields','artifact_sha256','slot','session','expected_revision','revision'),('player','request','phase','artifact_sha256'))
        if any(key in e for key in('slot','session','expected_revision','revision')):
            if type(e.get('slot'))!=int or not 1<=e['slot']<=32 or type(e.get('session'))!=int or e['session']<0:raise ValueError('Versioned logs require slot and session')
            if any(type(e[key])!=int or e[key]<0 for key in('expected_revision','revision')if key in e):raise ValueError('Invalid log revision')
        groups.setdefault((str(e['player']),e['request'],e['artifact_sha256'],e.get('slot'),e.get('session')),[]).append(e)
    order=['read','progress','write','readback','settlement','reentry'];out=[]
    for key,es in groups.items():
        phases={e['phase']for e in es};stages=order if key[3]is None else ['read','open',*order[1:]]
        out.append({'player':key[0],'request':key[1],'artifact_sha256':key[2],**({'slot':key[3],'session':key[4]}if key[3]is not None else{}),'observed':[x for x in stages if x in phases],'missing':[x for x in stages if x not in phases],'events':es})
    return {'schema':2,'groups':out,'host_verified':False}
def inspect_storage(data):
    native=native_inspect(data);m=model(data);structures=[];templates=[];types={v[1]:k for k,v in TYPES.items()}
    for s in m['structs']:
        body=get(s,1,default=b'');members=[]
        for member in vals(fields(body),3):
            typ=get(member,502,0,get(get(member,1,default=b''),1,0))
            members.append({'name':get(member,501,default=get(member,5,default=b'')).decode('utf-8'),'type_id':typ,'type':types.get(typ),'index':get(member,503,0)})
        structures.append({'id':get(body,1,0),'kind':get(body,2,0),'name':get(body,501,default=b'').decode('utf-8'),'fields':members})
    for t in vals(fields(get(data[20:-4],31,default=b'')),1):
        body=get(t,2,default=b'');slots=[]
        for s in vals(fields(body),2):slots.append({'id':get(s,1,0),'variable':get(s,4,default=b'').decode('utf-8'),'struct_id':get(get(s,2,default=b''),2,0),'max_records':get(s,3,0)})
        templates.append({'id':get(t,1,0),'name':get(body,501,default=b'').decode('utf-8'),'slots':slots})
    settings=get(get(data[20:-4],25,default=b''),3,default=b'')
    achievements=[{'id':get(a,1,0),'name':get(a,2,default=b'').decode('utf-8'),'goal':get(a,6,0)}for a in vals(fields(settings),4)]
    missing=[s['struct_id']for t in templates for s in t['slots']if s['struct_id']not in{v['id']for v in structures}]
    return {**native,'structures':structures,'storage_templates':templates,'achievements':achievements,'missing_storage_structures':missing,'status':'failed'if missing else'passed'if templates else'not_applicable','real_storage_reentry':'not_checked'}
def main(argv=None):
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='op',required=True)
    a=s.add_parser('build');a.add_argument('spec');a.add_argument('--out',required=True)
    a=s.add_parser('inspect');a.add_argument('input');a=s.add_parser('diagnose');a.add_argument('input');a=p.parse_args(argv)
    result=build(a.spec,a.out)if a.op=='build'else inspect_storage(Path(a.input).read_bytes())if a.op=='inspect'else diagnose(read_json(a.input))
    print(json.dumps(result,ensure_ascii=False));return 2 if result.get('status')=='failed'else 0
