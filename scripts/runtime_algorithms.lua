-- Deterministic, gameplay-independent Lua 5.3 algorithms.
local M={}
function M.rng(seed)
 assert(math.type(seed)=='integer'and seed>0 and seed<2147483647,'invalid RNG state')
 local r={state=seed}
 function r:next()self.state=self.state*48271%2147483647 return self.state end
 function r:integer(lo,hi)assert(lo<=hi)return lo+self:next()%(hi-lo+1)end
 function r:restore(v)assert(math.type(v)=='integer'and v>0 and v<2147483647)self.state=v end
 return r
end
function M.heap()
 local h={data={},serial=0}
 local function less(a,b)return a.priority<b.priority or a.priority==b.priority and a.order<b.order end
 function h:push(value,priority)
  assert(type(priority)=='number'and priority==priority and math.abs(priority)<math.huge)
  self.serial=self.serial+1 local e={value=value,priority=priority,order=self.serial}local i=#self.data+1
  while i>1 do local p=i//2 if not less(e,self.data[p])then break end self.data[i]=self.data[p]i=p end self.data[i]=e
 end
 function h:pop()
  local first=self.data[1]if not first then return end local tail=table.remove(self.data)
  if #self.data>0 then local i=1 while i*2<=#self.data do local c=i*2 if c<#self.data and less(self.data[c+1],self.data[c])then c=c+1 end if not less(self.data[c],tail)then break end self.data[i]=self.data[c]i=c end self.data[i]=tail end
  return first.value,first.priority
 end
 return h
end
function M.shortest(start,goal,neighbors)
 local q=M.heap()local distances={[start]=0}local previous={}local work=0 q:push(start,0)
 while #q.data>0 do local u,cost=q:pop()
  if cost==distances[u]then
   work=work+1 if u==goal then local route={u}while previous[u]do u=previous[u]table.insert(route,1,u)end return route,cost,work end
   for _,edge in ipairs(neighbors(u))do assert(edge.cost>=0 and edge.cost<math.huge,'invalid edge cost')local nextCost=cost+edge.cost
    if not distances[edge.to]or nextCost<distances[edge.to]then distances[edge.to]=nextCost previous[edge.to]=u q:push(edge.to,nextCost)end
   end
  end
 end return nil,nil,work
end
function M.grid(width,height,blocked)
 assert(math.type(width)=='integer'and math.type(height)=='integer'and width>0 and height>0)
 return function(index)
  local x=(index-1)%width+1 local y=(index-1)//width+1 local out={}
  for _,d in ipairs({{0,-1},{-1,0},{1,0},{0,1}})do local a,b=x+d[1],y+d[2]if a>=1 and a<=width and b>=1 and b<=height then local i=(b-1)*width+a if not blocked(i)then out[#out+1]={to=i,cost=1}end end end return out
 end
end
function M.segment_distance(px,py,ax,ay,bx,by)
 local dx,dy=bx-ax,by-ay local d=dx*dx+dy*dy local t=d==0 and 0 or math.max(0,math.min(1,((px-ax)*dx+(py-ay)*dy)/d))
 return math.sqrt((px-ax-t*dx)^2+(py-ay-t*dy)^2)
end
function M.in_circle(x,y,cx,cy,r)return(x-cx)^2+(y-cy)^2<=r*r end
function M.in_rect(x,y,cx,cy,hw,hh)return math.abs(x-cx)<=hw and math.abs(y-cy)<=hh end
function M.reservations()
 local r={entries={}}
 function r:claim(key,owner,expires,now)self:expire(now) local e=self.entries[key]if e and e.owner~=owner then return false end self.entries[key]={owner=owner,expires=expires}return true end
 function r:release(owner)for key,e in pairs(self.entries)do if e.owner==owner then self.entries[key]=nil end end end
 function r:expire(now,alive)for key,e in pairs(self.entries)do if e.expires<=now or alive and not alive(e.owner)then self.entries[key]=nil end end end
 return r
end
function M.machine(initial,transitions)
 local m={state=initial}
 function m:send(event,context)local t=transitions[self.state]and transitions[self.state][event]if not t or t.guard and not t.guard(context)then return false end if t.action then t.action(context)end self.state=t.to return true end
 return m
end
function M.clock()
 local c={time=0,paused=false}
 function c:tick(dt)assert(dt>=0 and dt<math.huge)if not self.paused then self.time=self.time+dt end return self.time end return c
end
function M.cache(capacity,load,release)
 assert(math.type(capacity)=='integer'and capacity>0)local c={values={},order={}}
 function c:get(key)
  local value=self.values[key]if value==nil then value=load(key)assert(value~=nil,'missing resource')self.values[key]=value end
  for i=#self.order,1,-1 do if self.order[i]==key then table.remove(self.order,i)end end self.order[#self.order+1]=key
  while #self.order>capacity do local old=table.remove(self.order,1)release(old,self.values[old])self.values[old]=nil end return value
 end
 function c:close()for _,key in ipairs(self.order)do release(key,self.values[key])end self.values={}self.order={}end return c
end
function M.replay(events,dispatch)
 local previous=-math.huge for i,e in ipairs(events)do assert(e.time>=previous,'unsorted replay')previous=e.time dispatch(e,i)end
end
return M
