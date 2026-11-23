-- Deterministic client contract model. Rendering and native host scheduling are not modeled.
local H={logs={},controls={},sentSignals={},variables={},paused=false,time=0}
local function strict(label,values)
 return setmetatable({}, {__index=function(_,k) if values[k]~=nil then return values[k] end;error('模型未实现接口: '..label..'.'..tostring(k),2) end,__newindex=function(_,k) error('模型只读接口: '..label..'.'..tostring(k),2) end})
end
local function boolean(v) assert(type(v)=='boolean','参数必须是boolean');return v end
local function number(v) assert(type(v)=='number' and v==v and math.abs(v)~=math.huge,'参数必须是有限数字');return v end
local function live(c) assert(H.stateMap[c] and H.stateMap[c].alive,'控件已销毁或不是模型控件') end
local function invoke(name,...)
 local f=H.env[name]
 if f~=nil then assert(type(f)=='function','生命周期不是函数: '..name);return f(...) end
end
function H.refresh()
 if not H.booted then return end
 local s=H.scriptState
 local enabled=s.alive and s.enabled and H.root.activeInHierarchy
 if enabled~=H.effectiveEnabled then
  H.effectiveEnabled=enabled
  invoke(enabled and 'OnEnable' or 'OnDisable')
 end
end
local function detach(c)
 local parent=H.stateMap[c].parent
 if parent then local list=H.children[parent];for i=#list,1,-1 do if list[i]==c then table.remove(list,i) end end end
end
local function reparent(c,parent)
 live(c)
 if parent~=nil then
  live(parent);local ancestor=parent
  while ancestor do assert(ancestor~=c,'父级关系不能形成循环');ancestor=H.stateMap[ancestor].parent end
 end
 detach(c);H.stateMap[c].parent=parent
 if parent then table.insert(H.children[parent],c) end
 H.refresh()
end
local layoutFields={anchoredPositionX=0,anchoredPositionY=0,sizeDeltaX=100,sizeDeltaY=100,anchorMinX=.5,anchorMinY=.5,anchorMaxX=.5,anchorMaxY=.5,pivotX=.5,pivotY=.5,localScaleX=1,localScaleY=1,localScaleZ=1,localRotationX=0,localRotationY=0,localRotationZ=0}
local function control(name,prefab,parent,kind)
 local state={alive=true,id=H.nextId,name=name,prefabIndex=prefab or 0,parent=nil,active=false,visible=true,canControllerFocus=false}
 H.nextId=H.nextId+1
 for k,v in pairs(layoutFields) do state[k]=v end
 local writable={name='string',parent='parent',canControllerFocus='boolean'}
 for k in pairs(layoutFields) do writable[k]='number' end
 if kind=='text' then
  state.text='';writable.text='string';state.fontSize=20;writable.fontSize='integer'
  state.minimumFontSize=1;writable.minimumFontSize='integer'
  for _,k in ipairs({'fontColor','bgColor','outlineColor'}) do state[k]={r=255,g=255,b=255,a=255};writable[k]='color' end
  for _,k in ipairs({'enableOutline','adaptiveFontSize'}) do state[k]=false;writable[k]='boolean' end
  for _,k in ipairs({'horizontalAlignment','verticalAlignment'}) do writable[k]='string' end
 end
 if kind=='image' then
  state.imageColor={r=255,g=255,b=255,a=255};writable.imageColor='color'
  for _,k in ipairs({'enableMask','enableSoftEdge','reverseMaskArea'}) do state[k]=false;writable[k]='boolean' end
  for _,k in ipairs({'softEdgeWidthX','softEdgeWidthY','horizontalSoftRange','verticalSoftRange','fillAmount'}) do state[k]=0;writable[k]='number' end
  for _,k in ipairs({'imageType','softEdgeMode','fillType','fillHorizontalType','fillVerticalType','fillRadial90Type','fillRadialType'}) do writable[k]='string' end
 end
 local cursorControl=kind=='area' or kind=='button'
 if cursorControl then state.raycastTarget=true;writable.raycastTarget='boolean' end
 if kind=='button' then state.interactable=true;writable.interactable='boolean' end
 local children,listeners={},{};local methods={};local c
 function methods:SetActive(v)live(self);state.active=boolean(v);H.refresh() end
 function methods:SetVisible(v)live(self);state.visible=boolean(v) end
 function methods:GetChildren()live(self);return {table.unpack(children)} end
 function methods:GetChild(n)live(self);for _,child in ipairs(children) do if child.name==n then return child end end end
 function methods:FindChild(path)local target=self;for part in string.gmatch(path,'[^/]+') do target=target and target:GetChild(part) end;return target end
 function methods:GetScripts()live(self);return self==H.root and H.scriptState.alive and {H.env.script} or {} end
 function methods:GetScript(id)live(self);if self==H.root and H.scriptState.alive and H.scriptState.scriptMappingId==id then return H.env.script end end
 function methods:GetScriptByPath(path)live(self);if self==H.root and H.scriptState.alive and H.scriptState.path==path then return H.env.script end end
 function methods:GetSiblingIndex()live(self);if not state.parent then return 0 end;for i,item in ipairs(H.children[state.parent]) do if item==self then return i-1 end end end
 function methods:SetSiblingIndex(index)
  live(self);assert(math.type(index)=='integer','索引必须是integer')
  if not state.parent then return false end
  local list=H.children[state.parent];if index<0 or index>=#list then return false end
  for i,item in ipairs(list) do if item==self then table.remove(list,i);break end end
  table.insert(list,index+1,self);return true
 end
 function methods:SetAsFirstSibling()return self:SetSiblingIndex(0) end
 function methods:SetAsLastSibling()return self:SetSiblingIndex(state.parent and #H.children[state.parent]-1 or 0) end
 for _,pair in ipairs({{'AnchoredPosition','anchoredPosition'},{'SizeDelta','sizeDelta'},{'AnchorMin','anchorMin'},{'AnchorMax','anchorMax'},{'Pivot','pivot'}}) do
  local method,field=pair[1],pair[2]
  methods['Set'..method]=function(self,x,y)live(self);state[field..'X']=number(x);state[field..'Y']=number(y) end
  methods['Get'..method]=function(self)live(self);return state[field..'X'],state[field..'Y'] end
 end
 for _,pair in ipairs({{'LocalScale','localScale'},{'LocalRotation','localRotation'}}) do
  local method,field=pair[1],pair[2]
  methods['Set'..method]=function(self,x,y,z)live(self);state[field..'X']=number(x);state[field..'Y']=number(y);state[field..'Z']=number(z) end
  methods['Get'..method]=function(self)live(self);return state[field..'X'],state[field..'Y'],state[field..'Z'] end
 end
 for _,family in ipairs({'Cursor','Key','Navigation'}) do
  methods['Add'..family..'EventListener']=function(self,event,cb)
   live(self);assert(family~='Cursor' or cursorControl,'光标监听需要检测区域或预设按钮');assert(type(event)=='string' and type(cb)=='function','监听需要有效枚举及回调')
   local key=family..':'..event;listeners[key]=listeners[key] or {};table.insert(listeners[key],cb)
  end
  methods['Remove'..family..'EventListener']=function(self,event,cb)
   live(self);local list=listeners[family..':'..event] or {}
   for i=#list,1,-1 do if list[i]==cb then table.remove(list,i) end end
  end
  methods['Remove'..family..'EventListeners']=function(self,event)live(self);listeners[family..':'..event]=nil end
  methods['RemoveAll'..family..'EventListeners']=function(self)live(self);for key in pairs(listeners) do if key:sub(1,#family+1)==family..':' then listeners[key]=nil end end end
 end
 if cursorControl then
  function methods:SimulateCursorClick()for _,event in ipairs({'CursorDown','CursorUp','CursorClick'}) do if self.alive then H.fire(self,'Cursor',event,{}) end end end
 end
 if kind=='image' then
  function methods:SetImage(source,id)live(self);assert(type(source)=='string' and math.type(id)=='integer','图片需要枚举来源与整数ID');state.imageSource=source;state.imageId=id end
  function methods:SetSoftEdgeWidth(x,y)self.softEdgeWidthX=x;self.softEdgeWidthY=y end
 end
 c=setmetatable({}, {__index=function(_,k)
  if k=='alive' then return state.alive end
  live(c)
  if methods[k] then return methods[k] end
  if k=='activeInHierarchy' then return state.active and (not state.parent or state.parent.activeInHierarchy) end
  if state[k]~=nil or k=='parent' then return state[k] end
  error('模型未实现控件字段: '..tostring(k),2)
 end,__newindex=function(_,k,v)
  live(c);local expected=writable[k]
  assert(expected,'只读或未实现控件字段: '..tostring(k))
  if expected=='parent' then reparent(c,v)
  else
   if expected=='integer' then assert(math.type(v)=='integer','控件字段需要integer: '..k)
   elseif expected=='color' then
    assert(type(v)=='table','控件字段需要ColorValue: '..k)
    for _,channel in ipairs({'r','g','b','a'}) do number(v[channel]);assert(v[channel]>=0 and v[channel]<=255,'Color分量必须为0..255') end
    v={r=v.r,g=v.g,b=v.b,a=v.a}
   else assert(type(v)==expected,'控件字段类型错误: '..k) end
   if expected=='number' then number(v) end
   state[k]=v
  end
 end})
 H.stateMap[c]=state;H.controls[state.id]=c;H.children[c]=children;H.listenerMap[c]=listeners
 if parent then reparent(c,parent) end
 return c
end
local function destroy(c)
 live(c)
 -- Disabling/destroying the root runs the modeled callbacks once, while its tree is still readable.
 if c==H.root then H.requestLifecycle('OnDestroy') end
 local function clear(x)
  for _,child in ipairs({table.unpack(H.children[x])}) do if H.stateMap[child].alive then clear(child) end end
  local state=H.stateMap[x];detach(x);state.alive=false;H.controls[state.id]=nil;H.listenerMap[x]={};H.children[x]={}
 end
 clear(c)
end
function H.setup(enums,config)
 H.listenerMap={};H.stateMap={};H.children={};H.nextId=1;H.config=config;H.handlers={};H.variableHandlers={};H.variables=config.variables or {};H.booted=false;H.effectiveEnabled=false;H.updateEnabled=true
 local stringCopy,mathCopy={},{}
 for k,v in pairs(string) do if k~='dump' then stringCopy[k]=v end end
 for k,v in pairs(math) do mathCopy[k]=v end
 mathCopy.isnan=function(v)return type(v)=='number' and v~=v end
 mathCopy.isinf=function(v)return v==math.huge or v==-math.huge end
 local env={assert=assert,error=error,ipairs=ipairs,pairs=pairs,next=next,pcall=pcall,xpcall=xpcall,select=select,tonumber=tonumber,tostring=tostring,type=type,table=table,string=stringCopy,utf8=utf8,math=mathCopy,debug={traceback=debug.traceback},_VERSION=_VERSION}
 env.Enum=enums
 env.print=function(...)
  assert(#H.logs<1000,'模拟日志超过1000条')
  local a={};for i=1,select('#',...) do a[i]=tostring(select(i,...)) end;H.logs[#H.logs+1]=table.concat(a,'\t')
 end
 env.printerr=function(...)env.print('ERROR',...) end
 env.os=strict('os',{clock=function()return H.time end})
 H.env=env;H.root=control('Root',0,nil,'container');H.stateMap[H.root].active=true
 H.scriptState={alive=true,enabled=true,object=H.root,path=config.mapping,scriptMappingId=config.scriptId}
 local scriptMethods={}
 function scriptMethods:GetParam(name)return config.params[name] end
 function scriptMethods:Invoke(name,...)assert(H.scriptState.alive,'脚本已销毁');assert(type(env[name])=='function','脚本方法不存在');env[name](...) end
 function scriptMethods:EnableUpdate(v)H.updateEnabled=boolean(v) end
 function scriptMethods:RegisterServerSignalHandler(name,cb)assert(type(name)=='string' and type(cb)=='function');H.handlers[name]=cb end
 function scriptMethods:UnregisterServerSignalHandler(name)H.handlers[name]=nil end
 function scriptMethods:RegisterCustomVariableChangedHandler(kind,name,callback)
  assert((kind=='Level'or kind=='PlayerSelf'or kind=='AvatarSelf')and type(name)=='string'and type(callback)=='function','invalid variable listener')
  H.variableHandlers[kind..':'..name]=callback
 end
 function scriptMethods:UnregisterCustomVariableChangedHandler(kind,name)H.variableHandlers[kind..':'..name]=nil end
 env.script=setmetatable({}, {__index=function(_,k)
  if scriptMethods[k] then return scriptMethods[k] end
  if H.scriptState[k]~=nil then return H.scriptState[k] end
  error('模型未实现脚本字段: '..tostring(k),2)
 end,__newindex=function(_,k,v)
  assert(k=='enabled','只读或未实现脚本字段: '..tostring(k));assert(H.scriptState.alive,'脚本已销毁');H.scriptState.enabled=boolean(v);H.refresh()
 end})
 local function color(r,g,b,a)
  number(r);number(g);number(b);number(a)
  for _,v in ipairs({r,g,b,a}) do assert(v>=0 and v<=255,'Color分量必须为0..255') end
  return {r=r,g=g,b=b,a=a}
 end
 env.Color={FromRGBA=function(r,g,b,a)return color(r,g,b,a==nil and 255 or a) end,FromRGB=function(r,g,b)return color(r,g,b,255) end,ToRGBA=function(c)return c.r,c.g,c.b,c.a end}
 env.game=strict('game',{
  GetUICanvasSize=function()return config.width,config.height end,
  GetClientUIRoots=function()return H.root.alive and {H.root} or {} end,
  FindClientUIRoot=function(name)if H.root.alive and name==H.root.name then return H.root end end,
  GetClientUIControl=function(id)return H.controls[id] end,
  InstantiateClientUIControl=function(index,parent)
   local prefab=config.templates[index];assert(prefab,'模板索引不存在: '..tostring(index)..'；需要模板记录GUID，不是1/2/3序号')
   if parent then live(parent) end
   return control(prefab.name,index,parent,prefab.kind)
  end,
  DestroyClientUIControl=destroy,
  PrintClientUITree=function()
   local ids={};for id in pairs(H.controls) do ids[#ids+1]=id end;table.sort(ids)
   for _,id in ipairs(ids) do local c=H.controls[id];env.print(id,c.name,c.prefabIndex) end
  end,
  PauseLevelTime=function(v)H.paused=boolean(v) end,IsLevelTimePaused=function()return H.paused end,
  GetGlobalCustomVariableValue=function(kind,name)return H.variables[kind..':'..name] end,
  ServerSignal=function(name)
   assert(type(name)=='string');local values,types={},{};local signal={}
   local function validate(kind,v)
    if kind:sub(-4)=='List'then
     assert(type(v)=='table','信号列表需要table')local count=0
     for k,x in pairs(v)do assert(math.type(k)=='integer'and k>=1 and k<=#v);validate(kind:sub(1,-5),x)count=count+1 end assert(count==#v)return
    end
    if kind=='Int' then assert(math.type(v)=='integer','信号Int参数必须是integer')
    elseif kind=='Float' then number(v)
    elseif kind=='Bool' then boolean(v)
    elseif kind=='String' then assert(type(v)=='string','信号String参数必须是string')
    elseif kind=='Vector3'then assert(type(v)=='table');number(v.x);number(v.y);number(v.z)
    elseif kind=='Guid'or kind=='Entity'or kind=='PrefabId'or kind=='ConfigId'then assert(math.type(v)=='integer'and v>=0)
    else error('模型未实现信号类型: '..tostring(kind)) end
   end
   local function append(kind,v)
    validate(kind,v);values[#values+1]=v;types[#types+1]=kind
   end
   for _,kind in ipairs({'Int','Float','Bool','String','Vector3','Guid','Entity','PrefabId','ConfigId'}) do
    signal['Add'..kind]=function(_,v)append(kind,v) end
    signal['Add'..kind..'List']=function(_,v)append(kind..'List',v)end
   end
   function signal:AddParam(kind,value)append(kind,value) end
   function signal:SendSignal()H.sentSignals[#H.sentSignals+1]={name=name,params={table.unpack(values)},types={table.unpack(types)}} end
   return strict('ServerSignal',signal)
  end
 })
 env._G=env
end
function H.load(source)local f,e=load(source,'client','t',H.env);assert(f,e);return f() end
function H.syncVariables(rows,notify)
 assert(type(notify)=='boolean','explicit variable notification policy required')
 assert(H.scriptState.alive,'script destroyed')
 for _,row in ipairs(rows)do H.variables[row.scope..':'..row.name]=row.value end
 if notify then
  for _,row in ipairs(rows)do
   local callback=H.variableHandlers[row.scope..':'..row.name]
   if callback then callback(row.scope,row.name) end
  end
 end
end
function H.boot()
 assert(not H.booted,'模型不能重复启动');invoke('OnInit');invoke('OnStart');H.booted=true;H.refresh()
end
function H.requestLifecycle(name)
 local s=H.scriptState
 if name=='OnEnable' then assert(s.alive,'脚本已销毁');s.enabled=true;H.refresh()
 elseif name=='OnDisable' then assert(s.alive,'脚本已销毁');s.enabled=false;H.refresh()
 elseif name=='OnDestroy' then
  if s.alive then s.enabled=false;H.refresh();invoke('OnDestroy');s.alive=false;H.handlers={};H.variableHandlers={} end
 else error('OnInit/OnStart由模型启动调用；重开请invoke实际重置函数') end
end
function H.tick(dt)
 H.time=H.time+number(dt)
 if H.effectiveEnabled and H.updateEnabled then
  invoke('OnUpdate',dt)
  if H.effectiveEnabled and H.updateEnabled and not H.paused then invoke('OnLevelUpdate',dt) end
 end
end
function H.fire(target,family,event,data)
 live(target)
 if not H.effectiveEnabled then return false end
 if family=='Cursor' then
  local state=H.stateMap[target]
  if state.raycastTarget==false or state.interactable==false then return false end
 end
 local current=target
 while current do if not current.activeInHierarchy or not current.visible then return false end;current=H.stateMap[current].parent end
 local payload=data
 if family=='Cursor' then
  payload=strict('CursorEventData',{dragging=data.dragging or false,touchId=data.touch_id or 0,GetUIPos=function()return data.ui_x or 0,data.ui_y or 0 end,GetPressUIPos=function()return data.press_x or 0,data.press_y or 0 end,GetUIPosDelta=function()return data.delta_x or 0,data.delta_y or 0 end})
 end
 local list=H.listenerMap[target][family..':'..event] or {}
 for _,cb in ipairs({table.unpack(list)}) do if not target.alive then break end;if cb(payload)==true then return true end end
 return false
end
function H.receive(name,params)
 if H.effectiveEnabled and H.handlers[name] then H.handlers[name](name,params) end
end
function H.value(path)
 local value=H.env
 for part in string.gmatch(path,'[^.]+') do if value==nil then return nil end;value=value[part] end
 return value
end
return H
