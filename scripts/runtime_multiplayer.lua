-- Revision-bound confirmation and recovery primitives, no game state policy.
local M={}
local function copy(v)if type(v)~='table'then return v end local out={}for k,x in pairs(v)do out[k]=copy(x)end return out end
function M.barrier(members)
 local b={revision=1,members={},confirmed={},finished={},checkpoint=nil}
 for _,id in ipairs(members)do assert(not b.members[id])b.members[id]=true end
 function b:revise()self.revision=self.revision+1 self.confirmed={}self.finished={}return self.revision end
 function b:roster(ids)local m={}for _,id in ipairs(ids)do assert(not m[id])m[id]=true end self.members=m return self:revise()end
 function b:confirm(id,revision,value)if revision~=self.revision or not self.members[id]then return false end self.confirmed[id]=value~=false or nil if value==false then self.finished[id]=nil end return true end
 function b:complete(id,revision)if revision~=self.revision or not self.members[id]or not self:ready()then return false end self.finished[id]=true return true end
 function b:ready()if next(self.members)==nil then return false end for id in pairs(self.members)do if not self.confirmed[id]then return false end end return true end
 function b:done()if not self:ready()then return false end for id in pairs(self.members)do if not self.finished[id]then return false end end return true end
 function b:save(state)self.checkpoint={revision=self.revision,members=copy(self.members),confirmed=copy(self.confirmed),finished=copy(self.finished),state=copy(state)}return copy(self.checkpoint)end
 function b:restore(c)assert(c.revision>=self.revision,'stale checkpoint')self.revision=c.revision self.members=copy(c.members)self.confirmed=copy(c.confirmed)self.finished=copy(c.finished)self.checkpoint=copy(c)return copy(c.state)end
 return b
end
return M
