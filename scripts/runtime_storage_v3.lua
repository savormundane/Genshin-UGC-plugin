-- Optimistic session/revision handshake over the native schema-3 graph.
return function(Runtime,fields,send,timeout,retries)
 local tx
 tx=Runtime.transaction(fields,function(kind,request,values)
  send(kind,request,values,tx.session,tx.revision)
 end,timeout,retries)
 local read,write,receive=tx.read,tx.write,tx.receive
 tx.ready=false
 function tx:read()self.ready=false return read(self)end
 function tx:write(values,exitIntent)
  assert(self.ready and not self.error,'open storage successfully before writing')
  return write(self,values,exitIntent)
 end
 function tx:receive_v3(id,kind,values,ok,session,revision)
  local p=self.pending
  if not p or p.id~=id or p.kind~=kind then return false,'unrelated'end
  if not ok then self.ready=false return receive(self,id,kind,values,false)end
  if math.type(session)~='integer'or math.type(revision)~='integer'or session<0 or revision<0 then return false,'invalid metadata'end
  if kind~='read'and(session~=self.session or revision~=self.revision+1)then return false,'revision differs'end
  local accepted,exitIntent=receive(self,id,kind,values,true)
  if not accepted then return false,exitIntent end
  self.revision=revision
  if kind=='read'then
   assert(session<9223372036854775807,'session exhausted')
   self.session=session+1
   self:begin('open')
   return false,'opening'
  end
  self.ready=true
  return true,exitIntent
 end
 return tx
end
