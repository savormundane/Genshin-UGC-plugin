-- Control callbacks use the official API; budgets are supplied by the caller.
local M={}
function M.properties()
 local p={values=setmetatable({},{__mode='k'})}
 local function copy(v)if type(v)~='table'then return v end local c={}for k,x in pairs(v)do c[k]=copy(x)end return c end
 local function equal(a,b)
  if type(a)~=type(b)then return false end if type(a)~='table'then return a==b end
  for k,v in pairs(a)do if not equal(v,b[k])then return false end end for k in pairs(b)do if a[k]==nil then return false end end return true
 end
 function p:write(control,method,...)
  local args=table.pack(...)local previous=self.values[control]
  if previous and equal(previous[method],args)then return false end
  control[method](control,table.unpack(args,1,args.n))
  if not previous then previous={}self.values[control]=previous end previous[method]=copy(args)return true
 end
 function p:forget(control)self.values[control]=nil end
 return p
end
function M.scope()
 local s={cleanups={},closed=false}
 function s:add(cleanup)assert(not self.closed)self.cleanups[#self.cleanups+1]=cleanup end
 function s:listen(control,kind,event,callback)
  assert(not self.closed and(kind=='Cursor'or kind=='Key'))control['Add'..kind..'EventListener'](control,event,callback)
  self:add(function()control['Remove'..kind..'EventListener'](control,event,callback)end)
 end
 function s:close()if self.closed then return false end self.closed=true for i=#self.cleanups,1,-1 do self.cleanups[i]()end self.cleanups={}return true end
 return s
end
function M.pool(create,reset,destroy,capacity,properties)
 assert(math.type(capacity)=='integer'and capacity>0)local p={free={},used={},count=0,generation=0}
 function p:acquire(owner)
  assert(owner~=nil and not self.used[owner])local c=table.remove(self.free)
  if not c then if self.count>=capacity then return nil end c=create()self.count=self.count+1 end
  if properties then properties:forget(c)end self.generation=self.generation+1 local handle={control=c,owner=owner,generation=self.generation}self.used[owner]=handle return handle
 end
 function p:release(handle)if self.used[handle.owner]~=handle then return false end reset(handle.control)if properties then properties:forget(handle.control)end self.used[handle.owner]=nil self.free[#self.free+1]=handle.control return true end
 function p:valid(handle)return self.used[handle.owner]==handle end
 function p:close()for _,h in pairs(self.used)do if properties then properties:forget(h.control)end destroy(h.control)end for _,c in ipairs(self.free)do if properties then properties:forget(c)end destroy(c)end self.used={}self.free={}self.count=0 end
 return p
end
function M.queue()
 local q={tasks={},serial=0}
 function q:add(owner,priority,operations,valid)
  self:cancel(owner)self.serial=self.serial+1 local t={owner=owner,priority=priority,operations=operations,index=1,order=self.serial,valid=valid}self.tasks[#self.tasks+1]=t return t
 end
 function q:cancel(owner)for i=#self.tasks,1,-1 do if self.tasks[i].owner==owner then self.tasks[i].cancelled=true table.remove(self.tasks,i)end end end
 function q:tick(createBudget,writeBudget)
  local created,written=0,0 table.sort(self.tasks,function(a,b)return a.priority>b.priority or a.priority==b.priority and a.order<b.order end)
  -- Callbacks may cancel, replace or enqueue tasks. This tick owns a snapshot;
  -- remove by task identity and defer newly submitted work to the next tick.
  local scheduled={}for i,t in ipairs(self.tasks)do scheduled[i]=t end
  for _,t in ipairs(scheduled)do
   while not t.cancelled and t.index<=#t.operations do
    if t.valid and not t.valid()then t.cancelled=true break end
    local op=t.operations[t.index]local c,w=op.creates or 0,op.writes or 0 assert(c>=0 and w>=0)
    if created+c>createBudget or written+w>writeBudget then break end
    op.run()created=created+c written=written+w t.index=t.index+1
   end
   if t.cancelled or t.index>#t.operations then
    for i=#self.tasks,1,-1 do if self.tasks[i]==t then table.remove(self.tasks,i)break end end
   end
  end return created,written
 end return q
end
function M.position_owner()
 local p={owners={}}
 function p:claim(control,token)if self.owners[control]and self.owners[control]~=token then return false end self.owners[control]=token return true end
 function p:write(control,token,x,y)if self.owners[control]and self.owners[control]~=token then return false end control:SetAnchoredPosition(x,y)return true end
 function p:release(token)for c,t in pairs(self.owners)do if t==token then self.owners[c]=nil end end end return p
end
function M.overlay(capture,restore,pause)
 local m={context=nil}
 function m:open()if self.context then return false end self.context=capture()pause(true)return true end
 function m:close()if not self.context then return false end local c=self.context restore(c)self.context=nil pause(false)return true end return m
end
function M.list(update,hide)
 local state={}
 return function(items,key)
  for i,v in ipairs(items)do local k=key(v)if state[i]~=k then update(i,v)state[i]=k end end
  for i=#state,#items+1,-1 do hide(i)state[i]=nil end
 end
end
function M.drag(positions,control,token,onDrop)
 assert(positions:claim(control,token))local d={active=true}
 function d:move(x,y)if not self.active then return false end return positions:write(control,token,x,y)end
 function d:finish(target)if not self.active then return false end self.active=false positions:release(token)if target~=nil then onDrop(target)end return true end
 function d:cancel()return self:finish(nil)end return d
end
return M
