"""One contract -> native signal resources, client bridge and independently checked wire layout."""
from pathlib import Path
import json,hashlib,shutil
from level_inventory import fields,vals,unique,container
from protocol_types import TYPES
ENVELOPE=[{'name':'session_key','type':'string'},{'name':'round_id','type':'integer'},{'name':'sequence_id','type':'integer'}]
def wire(signal):
    if any(f['name'] in {x['name'] for x in ENVELOPE} for f in signal['fields']):raise ValueError('Parameter conflicts with transport envelope')
    return ENVELOPE+signal['fields']
def generate(contract,dest):
    from miliastra.assets.pipeline import lua
    dest=Path(dest);resources=dest/'resources/管理配置/信号';resources.mkdir(parents=True)
    layout=[]
    for s in contract['signals']:
        ordered=wire(s);sid='ugc_'+hashlib.sha256(s['name'].encode()).hexdigest()[:24]
        payload={'signal_name':s['name'],'parameters':[{'name':f['name'],'parameter_type':TYPES[f['type']][0]} for f in ordered]}
        (resources/(sid+'.py')).write_text('SIGNAL_ID = '+repr(sid)+'\nSIGNAL_PAYLOAD = '+repr(payload)+'\n',encoding='utf-8')
        layout.append({'name':s['name'],'direction':s['direction'],'fields':ordered,'signal_id':sid})
    (dest/'wire.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding='utf-8')
    types={k:v[2] for k,v in TYPES.items()}
    bridge="""-- Generated from the same native wire contract. Host APIs from bundled official reference.
return function(runtime,game,script,contract,session,round)
 local incoming=runtime.protocol(contract,session,round)
 local outgoing=runtime.protocol(contract,session,round)
 local definitions={};for _,s in ipairs(contract.signals) do definitions[s.name]=s end
 local methods=METHODS
 local seq={};local scope=runtime.scope();local self={}
 function self:send(name,phase,payload)
  local s=assert(definitions[name],"Unknown signal");assert(s.direction=="client_to_server")
  local packet={name=name,session=session,round=round,sequence=(seq[name] or 0)+1,payload=payload}
  local ok,e=outgoing:accept("local","client_to_server",phase,packet);assert(ok,e)
  local signal=game.ServerSignal(name);signal:AddString(session);signal:AddInt(round);signal:AddInt(packet.sequence)
  for i,f in ipairs(s.fields) do signal[methods[f.type]](signal,payload[i]) end
  signal:SendSignal();seq[name]=packet.sequence;return packet.sequence
 end
 function self:listen(name,source,phase,handler)
  local s=assert(definitions[name]);assert(s.direction=="server_to_client")
  script:RegisterServerSignalHandler(name,function(signalName,p)
   if type(p)~="table" or #p~=#s.fields+3 then return end
   local payload={};for i=1,#s.fields do payload[i]=p[i+3] end
   local packet={name=signalName,session=p[1],round=p[2],sequence=p[3],payload=payload}
   local ok,data=incoming:accept(source(),"server_to_client",phase(),packet);if ok then handler(data) end
  end)
  scope:add(function() script:UnregisterServerSignalHandler(name) end)
 end
 function self:close() return scope:close() end
 return self
end
""".replace('METHODS',lua(types))
    (dest/'client_bridge.lua').write_text(bridge,encoding='utf-8');return layout

def check_gil(path,layout):
    _,root=container(Path(path).read_bytes());registries=[];definitions={}
    for section in vals(root,10):
        for entry in vals(fields(section),2):
            d=unique(fields(entry),1)
            if d is None:continue
            df=fields(d);meta=fields(unique(df,4,default=b''));locator=fields(unique(meta,1,default=b''));ident=unique(locator,5,0)
            if ident is not None:
                if ident in definitions:raise ValueError('Duplicate custom definition ID')
                definitions[ident]=df
    for section in vals(root,10):
        for registry in vals(fields(section),5):registries+=vals(fields(registry),3)
    result=[]
    for s in layout:
        hits=[fields(x) for x in registries if unique(fields(x),3)==s['name'].encode()]
        if len(hits)!=1:raise ValueError('Signal registry missing or ambiguous: '+s['name'])
        params=[fields(x) for x in vals(hits[0],4)]
        if len(params)!=len(s['fields']):raise ValueError('Signal arity differs: '+s['name'])
        for p,f in zip(params,s['fields']):
            if unique(p,1)!=f['name'].encode() or unique(p,2,0)!=TYPES[f['type']][1]:raise ValueError('Signal wire order/type differs: '+s['name'])
        roles=[]
        for role,key in enumerate((1,2,7,9)):
            reference=unique(hits[0],key)
            if reference is None and key==9:
                roles.append({'role':role,'status':'not_applicable','reason':'Verified backend uses three native roles'});continue
            if reference is None:raise ValueError('Missing signal role '+str(role))
            ident=unique(fields(reference),5,0)
            if ident not in definitions:raise ValueError('Signal role definition missing')
            definition=definitions[ident];ports=[fields(x) for x in vals(definition,103 if role==1 else 102)]
            indices=[]
            for f in s['fields']:
                matching=[p for p in ports if unique(p,1)==f['name'].encode()]
                if len(matching)!=1:raise ValueError('Signal role parameter missing/ambiguous: '+f['name'])
                locator=unique(matching[0],3)
                if locator is None:raise ValueError('Signal role port locator missing')
                indices.append(unique(fields(locator),2,0,0))
            if indices!=list(range((3 if role==1 else 1 if role==3 else 0),(3 if role==1 else 1 if role==3 else 0)+len(s['fields']))):raise ValueError('Signal role parameter order/index mismatch')
            roles.append({'role':role,'definition':ident,'port_indices':indices})
        result.append({'name':s['name'],'parameters':len(params),'roles':roles})
    return {'status':'passed','signals':result}
