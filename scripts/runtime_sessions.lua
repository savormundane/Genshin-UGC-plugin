-- Session-scoped ordered commands and validated snapshots. Caller owns authority.
local M={}
local MAX=2147483647
local function integer(v)return math.type(v)=='integer'and v>=0 and v<=MAX end
local function identifier(v)return type(v)=='string'and #v>0 or math.type(v)=='integer'and v>=0 end
local function shape(v,allowed)
 if type(v)~='table'or getmetatable(v)~=nil then return false end
 for k in pairs(v)do if not allowed[k]then return false end end return true
end
local function clone(value,seen,depth)
 local t=type(value)
 assert(t=='nil'or t=='boolean'or t=='string'or t=='number'or t=='table','unsupported checkpoint value')
 if t=='number'then assert(value==value and math.abs(value)<math.huge,'nonfinite checkpoint number')end
 if t~='table'then return value end
 seen=seen or{};depth=depth or 0
 assert(depth<32 and not seen[value]and getmetatable(value)==nil,'invalid checkpoint table')
 seen[value]=true local result={}
 for k,v in pairs(value)do assert(type(k)=='string'or math.type(k)=='integer','invalid checkpoint key');result[k]=clone(v,seen,depth+1)end
 seen[value]=nil return result
end
local function members(ids)
 assert(type(ids)=='table'and getmetatable(ids)==nil,'member array required')
 local set={}local count=0
 for k,v in pairs(ids)do assert(math.type(k)=='integer'and k>=1 and k<=#ids,'dense member array required');count=count+1 end
 assert(count==#ids,'member array contains holes')
 for _,id in ipairs(ids)do assert(identifier(id)and not set[id],'invalid/duplicate member');set[id]=true end
 return clone(ids),set
end
local function ready(s)
 if #s.members==0 then return false end
 for _,id in ipairs(s.members)do if not s.confirmed[id]then return false end end return true
end
local function nextvalue(v)assert(v<MAX,'session counter exhausted');return v+1 end
local actions={confirm=true,withdraw=true,complete=true}
local function valid_command(p)
 return shape(p,{session=true,revision=true,sequence=true,action=true,value=true})and type(p.session)=='string'and
  integer(p.revision)and p.revision>0 and integer(p.sequence)and p.sequence>0 and actions[p.action]and
  ((p.action=='confirm'and type(p.value)=='boolean')or(p.action~='confirm'and p.value==nil))
end
function M.create(options)
 assert(shape(options,{session=true,members=true,phase=true,revision=true}),'invalid session options')
 assert(type(options.session)=='string'and #options.session>0 and type(options.phase)=='string'and #options.phase>0,'session/phase required')
 local ids,set=members(options.members);local revision=options.revision or 1
 assert(integer(revision)and revision>0,'invalid revision')
 local s={schema=2,session=options.session,revision=revision,serial=0,phase=options.phase,members=ids,confirmed={},finished={},received={}}
 local object={}
 function object:view()return clone(s)end
 function object:ready()return ready(s)end
 function object:done()
  if not ready(s)then return false end
  for _,id in ipairs(s.members)do if not s.finished[id]then return false end end return true
 end
 local function revise(phase,newids,newset)
  local rev,serial=nextvalue(s.revision),nextvalue(s.serial)
  s.revision=rev;s.serial=serial;s.phase=phase;s.members=newids;set=newset;s.confirmed={};s.finished={};s.received={};s.state=nil
  return rev
 end
 function object:advance(phase)
  assert(type(phase)=='string'and #phase>0,'phase required')
  return revise(phase,s.members,set)
 end
 function object:roster(newids)
  local list,newset=members(newids)
  return revise(s.phase,list,newset)
 end
 function object:command(sender,p)
  if not valid_command(p)then return false,'invalid_command'end
  if p.session~=s.session then return false,'wrong_session'end
  if p.revision~=s.revision then return false,'stale_revision'end
  if not set[sender]then return false,'not_member'end
  local last=s.received[sender]
  if last and p.sequence==last.sequence then
   if p.action==last.action and p.value==last.value then return true,'duplicate'end
   return false,'conflicting_duplicate'
  end
  if p.sequence~=(last and last.sequence or 0)+1 then return false,'sequence_gap_or_stale'end
  if p.action=='complete'and not ready(s)then return false,'barrier_not_ready'end
  if p.action=='withdraw'or(p.action=='confirm'and p.value==false)then
   revise(s.phase,s.members,set);return true,'revision_changed'
  end
  local serial=nextvalue(s.serial)
  if p.action=='confirm'then s.confirmed[sender]=true else s.finished[sender]=true end
  s.received[sender]={sequence=p.sequence,action=p.action,value=p.value};s.serial=serial
  return true,'accepted'
 end
 function object:checkpoint(state)
  local copied=clone(state);local serial=nextvalue(s.serial)
  s.state=copied;s.serial=serial;return clone(s)
 end
 function object:restore(snapshot)
  assert(shape(snapshot,{schema=true,session=true,revision=true,serial=true,phase=true,members=true,confirmed=true,finished=true,received=true,state=true}),'invalid snapshot fields')
  assert(snapshot.schema==2 and type(snapshot.session)=='string'and type(snapshot.phase)=='string'and #snapshot.phase>0,'unknown snapshot contract')
  assert(integer(snapshot.revision)and snapshot.revision>0 and integer(snapshot.serial),'invalid snapshot counters')
  local list,newset=members(snapshot.members)
  for _,field in ipairs({'confirmed','finished'})do
   local values=snapshot[field];assert(type(values)=='table'and getmetatable(values)==nil,'snapshot set required')
   for id,value in pairs(values)do assert(newset[id]and value==true,'invalid snapshot member set')end
  end
  if next(snapshot.finished)~=nil then assert(ready(snapshot),'finished snapshot has incomplete confirmations')end
  assert(type(snapshot.received)=='table'and getmetatable(snapshot.received)==nil,'snapshot sequence map required')
  for id,r in pairs(snapshot.received)do
   assert(newset[id]and shape(r,{sequence=true,action=true,value=true})and integer(r.sequence)and r.sequence>0,'invalid snapshot sequence')
   assert(r.action=='complete'and r.value==nil and snapshot.finished[id]or r.action=='confirm'and r.value==true and snapshot.confirmed[id],'invalid snapshot command record')
  end
  for _,id in ipairs(list)do
   if snapshot.confirmed[id]then assert(snapshot.received[id],'confirmation lacks command record')end
   if snapshot.finished[id]then assert(snapshot.received[id]and snapshot.received[id].action=='complete','completion lacks command record')end
  end
  local candidate=clone(snapshot)
  if candidate.session~=s.session then return false,'wrong_session'end
  if candidate.revision<s.revision or candidate.serial<=s.serial then return false,'stale_snapshot'end
  if candidate.revision==s.revision then
   if candidate.phase~=s.phase or #list~=#s.members then return false,'revision_identity_conflict'end
   for i,id in ipairs(list)do if id~=s.members[i]then return false,'revision_identity_conflict'end end
  end
  s=candidate;set=newset;return true,clone(candidate.state)
 end
 return object
end
return M
