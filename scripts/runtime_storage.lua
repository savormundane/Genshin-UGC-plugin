-- Bounded deterministic codec and correlated storage transactions. No host API invented.
local M={}
local function clone(v)if type(v)~='table'then return v end local t={}for k,x in pairs(v)do t[k]=clone(x)end return t end
function M.codec(dictionary,limit,version)
 local index={}for i,s in ipairs(dictionary)do assert(type(s)=='string'and not index[s]);index[s]=i end
 local function u(n)local s={}repeat local b=n%128 n=n//128 s[#s+1]=string.char(b+(n>0 and 128 or 0))until n==0 return table.concat(s)end
 local c={}
 function c:encode(value)
  local seen={}local function emit(v,depth)
   assert(depth<32,'codec depth')local t=type(v)
   if t=='nil'then return string.char(0)elseif t=='boolean'then return string.char(v and 2 or 1)
   elseif t=='number'then assert(v==v and math.abs(v)<math.huge);return math.type(v)=='integer'and string.char(7)..string.pack('>i8',v)or string.char(3)..string.pack('>d',v)
   elseif t=='string'then if index[v]then return string.char(4)..u(index[v])end return string.char(5)..u(#v)..v
   elseif t=='table'then
    assert(not seen[v],'codec cycle')seen[v]=true local keys={}for k in pairs(v)do assert(type(k)=='string'or type(k)=='number');keys[#keys+1]=k end
    table.sort(keys,function(a,b)if type(a)~=type(b)then return type(a)<type(b)end return a<b end)
    local out={string.char(6),u(#keys)}for _,k in ipairs(keys)do out[#out+1]=emit(k,depth+1)out[#out+1]=emit(v[k],depth+1)end seen[v]=nil return table.concat(out)
   end error('unsupported codec type')
  end
  local raw=emit(value,0)local compressed={}local at=1
  -- Zero/high repetition compression with an explicit escape byte. Dictionary
  -- references remain append-only; no platform-specific slot size is assumed.
  while at<=#raw do local b=raw:byte(at)local n=1 while n<255 and raw:byte(at+n)==b do n=n+1 end
   if n>=4 or b==255 then compressed[#compressed+1]=string.char(255,n,b)else compressed[#compressed+1]=raw:sub(at,at+n-1)end at=at+n
  end
  local body='QX'..string.pack('>I2',version)..table.concat(compressed)assert(#body<=limit,'storage capacity exceeded')return body
 end
 function c:decode(body)
  assert(type(body)=='string'and #body<=limit and body:sub(1,2)=='QX'and string.unpack('>I2',body,3)==version,'incompatible storage')
  local raw={}local at=5 local total=0
  while at<=#body do local b=body:byte(at)at=at+1 local text
   if b==255 then local n,x=body:byte(at,at+1)assert(n and x and n>0,'truncated run')at=at+2 text=string.rep(string.char(x),n)else text=string.char(b)end
   total=total+#text assert(total<=limit*256,'decompression capacity')raw[#raw+1]=text
  end
  raw=table.concat(raw)at=1 local nodes=0
  local function integer()local n,p=0,1 for i=1,8 do local b=assert(raw:byte(at),'truncated integer')at=at+1 n=n+(b%128)*p if b<128 then return n end p=p*128 end error('integer overflow')end
  local function parse(depth)
   nodes=nodes+1 assert(nodes<=30000 and depth<32,'codec structure')local tag=raw:byte(at)at=at+1
   if tag==0 then return nil elseif tag==1 then return false elseif tag==2 then return true elseif tag==3 then local v;v,at=string.unpack('>d',raw,at)assert(v==v and math.abs(v)<math.huge)return v
   elseif tag==7 then local v;v,at=string.unpack('>i8',raw,at)return v
   elseif tag==4 then return assert(dictionary[integer()],'unknown dictionary index')
   elseif tag==5 then local n=integer()assert(at+n-1<=#raw,'truncated string')local v=raw:sub(at,at+n-1)at=at+n return v
   elseif tag==6 then local n=integer()assert(n<=10000)local out={}for i=1,n do local k=parse(depth+1)assert(type(k)=='string'or type(k)=='number')assert(out[k]==nil,'duplicate key')out[k]=parse(depth+1)end return out end error('unknown codec tag')
  end local value=parse(0)assert(at==#raw+1,'trailing data')return value
 end
 function c:words(body,count)
  assert(#body+4<=count*3,'native capacity exceeded')local raw=string.pack('>I4',#body)..body local words={}
  for i=1,count do local a,b,d=raw:byte((i-1)*3+1,(i-1)*3+3)words[i]=(a or 0)*65536+(b or 0)*256+(d or 0)end return words
 end
 function c:from_words(words)
  local out={}for _,v in ipairs(words)do assert(math.type(v)=='integer'and v>=0 and v<16777216)out[#out+1]=string.char(v//65536,v//256%256,v%256)end
  local raw=table.concat(out)local n=string.unpack('>I4',raw)assert(n<=limit and n+4<=#raw,'invalid native length')return raw:sub(5,n+4)
 end
 return c
end
function M.transaction(fields,send,timeout,retries)
 local t={serial=0,pending=nil,cache=nil,exit=false,clock=0}
 local function confirmed(actual,expected)
  for i,f in ipairs(fields)do local a,b=actual[i],expected[i]
   if f.confirm=='equal'then
    local function equal(x,y)if type(x)~=type(y)then return false end if type(x)~='table'then return x==y end for k,v in pairs(x)do if not equal(v,y[k])then return false end end for k in pairs(y)do if x[k]==nil then return false end end return true end
    if not equal(a,b)then return false end
   elseif f.confirm=='max'then if type(a)~='number'or a<b then return false end
   elseif f.confirm=='min'then if type(a)~='number'or a>b then return false end
   elseif f.confirm=='contains_bits'then if math.type(a)~='integer'or a&b~=b then return false end
   else error('unknown confirmation policy')end
  end return true
 end
 function t:begin(kind,values,exitIntent)
  assert(not self.pending,'transaction busy')self.serial=self.serial+1 self.exit=exitIntent==true
  self.pending={id=self.serial,kind=kind,values=clone(values),attempt=0,sent=self.clock}send(kind,self.serial,clone(values))return self.serial
 end
 function t:read()return self:begin('read')end
 function t:write(values,exitIntent)assert(self.cache~=nil,'read storage successfully before writing')return self:begin('write',values,exitIntent)end
 function t:receive(id,kind,values,ok)
  local p=self.pending if not p or p.id~=id or kind~=p.kind then return false,'unrelated'end
  if not ok then self.pending=nil self.exit=false self.error='native failure'return false,self.error end
  if p.kind=='write'and not confirmed(values,p.values)then return false,'readback differs'end
  self.cache=clone(values)self.pending=nil self.error=nil return true,self.exit
 end
 function t:tick(dt)
  assert(dt>=0 and dt<math.huge)self.clock=self.clock+dt local p=self.pending
  if p and self.clock-p.sent>=timeout then
   if p.attempt>=retries then self.error='timeout'self.pending=nil self.exit=false return false end
   p.attempt=p.attempt+1 p.sent=self.clock send(p.kind,p.id,clone(p.values))
  end return true
 end
 function t:cancel_exit()self.exit=false end
 return t
end
function M.achievements(send)
 local a={pending={},confirmed={},serial=0}
 function a:request(id)self.serial=self.serial+1 self.pending[self.serial]=id send(id,self.serial)return self.serial end
 function a:ack(request,id,ok)if self.pending[request]~=id then return false end self.pending[request]=nil if ok then self.confirmed[id]=true end return ok end return a
end
return M
