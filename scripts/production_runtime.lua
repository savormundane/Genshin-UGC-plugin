-- Plugin-owned Lua 5.3 support; transport/control callbacks are supplied by the caller.
local M={}
function M.scope()
 local self={cleanups={},closed=false}
 function self:add(fn) assert(type(fn)=="function"); assert(not self.closed); self.cleanups[#self.cleanups+1]=fn; return fn end
 function self:close()
  if self.closed then return {} end
  self.closed=true;local errors={}
  for i=#self.cleanups,1,-1 do local ok,e=pcall(self.cleanups[i]);if not ok then errors[#errors+1]=tostring(e) end end
  self.cleanups={};return errors
 end
 return self
end
function M.dirty()
 local values,seen={},{}
 return function(key,value,write)
  if seen[key] and values[key]==value then return false end
  write(value);values[key]=value;seen[key]=true;return true
 end
end
local function valid(t,v)
 if t:sub(-5)=="_list" then
  if type(v)~="table"then return false end local n=0
  for k,x in pairs(v)do if type(k)~="number"or k%1~=0 or k<1 or k>#v or not valid(t:sub(1,-6),x)then return false end n=n+1 end
  return n==#v
 end
 if t=="vector3"then
  if type(v)~="table"then return false end local n=0 for k,x in pairs(v)do if k~="x"and k~="y"and k~="z"or not valid("number",x)then return false end n=n+1 end return n==3
 end
 if t=="guid"or t=="entity"or t=="prefab_id"or t=="config_id"then return math.type(v)=="integer"and v>=0 end
 if t=="string" then return type(v)=="string" end
 if t=="boolean" then return type(v)=="boolean" end
 if type(v)~="number" or v~=v or v==math.huge or v==-math.huge then return false end
 if t=="integer" then return v%1==0 and v>=-2147483648 and v<=2147483647 end
 return t=="number"
end
function M.protocol(contract,session,round)
 local signals={};for _,s in ipairs(contract.signals) do signals[s.name]=s end
 local last={}
 local self={}
 function self:accept(source,direction,phase,packet)
  local s=type(packet)=="table" and signals[packet.name]
  if source==nil or not s or direction~=s.direction then return false,"signal/source" end
  if packet.session~=session or packet.round~=round then return false,"session/round" end
  local phaseOK=false;for _,p in ipairs(s.phases) do if p==phase then phaseOK=true end end
  if not phaseOK then return false,"phase" end
  if not valid("integer",packet.sequence) or packet.sequence<1 then return false,"sequence" end
  if type(packet.payload)~="table" or #packet.payload~=#s.fields then return false,"arity" end
  local count=0;for k in pairs(packet.payload) do if type(k)~="number" or k%1~=0 or k<1 or k>#s.fields then return false,"payload key" end;count=count+1 end
  if count~=#s.fields then return false,"arity" end
  for i,f in ipairs(s.fields) do local v=packet.payload[i];if not valid(f.type,v) or (f.max_length and #v>f.max_length) then return false,"type/length" end end
  local bySource=last[source] or {};local previous=bySource[packet.name]
  if packet.sequence<=(previous or 0) then return false,"duplicate/old" end
  if s.policy=="ordered"and packet.sequence~=(previous or 0)+1 then return false,"gap"end
  bySource[packet.name]=packet.sequence;last[source]=bySource;return true,packet.payload
 end
 function self:forget(source) last[source]=nil end
 return self
end
function M.player(animation,draw,loop)
 local self={time=0,index=nil};local duration=0
 for _,f in ipairs(animation.frames) do duration=duration+f.duration end
 assert(duration>0 and type(draw)=="function")
 function self:update(dt)
  assert(type(dt)=="number" and dt>=0 and dt<math.huge)
  self.time=loop and (self.time+dt%duration)%duration or math.min(self.time+dt,duration)
  local t=loop and self.time%duration or math.min(self.time,duration)
  local i=1;while i<#animation.frames and t>=animation.frames[i].duration do t=t-animation.frames[i].duration;i=i+1 end
  if i~=self.index then draw(animation.frames[i],animation.pool_size,i);self.index=i end
  return i
 end
 function self:reset() self.time=0;self.index=nil end
 return self
end
function M.rectangles(frame,scale,mirror,emit,hide,pool)
 assert(type(scale)=="number" and scale>0 and scale<math.huge)
 local rects=frame.data.rects;assert(pool>=#rects)
 for i,r in ipairs(rects) do
  local x=r[1]+r[3]/2-frame.anchor[1]
  emit(i,(mirror and -x or x)*scale,(frame.anchor[2]-r[2]-r[4]/2)*scale,r[3]*scale,r[4]*scale,frame.data.palette[r[5]])
 end
 for i=#rects+1,pool do hide(i) end
end
return M
