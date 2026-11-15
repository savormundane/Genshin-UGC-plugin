-- Installed inside a schema-3 adapter. Tickets belong to this adapter/slot only.
return function(tx,codec,contract,slot)
 local tickets={}local closed=false
 function tx:prepare_migration(migration,index,words)
  assert(not closed and self.ready and not self.pending and not self.error,'storage not ready')
  local field=contract.fields[index]
  assert(field and field.type=='integer_list'and field.confirm=='equal','migration requires exact list confirmation')
  assert(math.type(words)=='integer'and words>0,'native word count')
  local original=codec:from_words(self.cache[index])
  local prepared=migration:prepare(original)
  assert(prepared.target_version==(contract.record_version or 1),'target codec differs')
  codec:decode(prepared.candidate)
  local encoded=codec:words(prepared.candidate,words)
  assert(#encoded<=(field.max_items or contract.capacity_bytes//8),'native field capacity')
  local size=40
  for i,f in ipairs(contract.fields)do
   size=size+(f.type=='integer'and 8 or f.type=='boolean'and 1 or 8*#(i==index and encoded or self.cache[i]))
  end
  assert(size<=contract.capacity_bytes,'logical record capacity exceeded')
  local ticket={}
  tickets[ticket]={original=original,candidate=encoded,index=index,session=self.session,revision=self.revision,serial=self.serial,changed=prepared.changed}
  return ticket,{original=original,slot=slot,session=self.session,revision=self.revision,changed=prepared.changed}
 end
 function tx:commit_migration(ticket,exitIntent)
  local item=assert(tickets[ticket],'unknown migration ticket')
  assert(not closed and self.ready and not self.pending and not self.error,'storage not ready')
  assert(item.session==self.session and item.revision==self.revision and item.serial==self.serial,'stale migration ticket')
  assert(codec:from_words(self.cache[item.index])==item.original,'source record changed')
  assert(item.changed,'record already current')
  local values={}for i,v in ipairs(self.cache)do values[i]=v end
  values[item.index]=item.candidate
  local request=self:write(values,exitIntent)
  tickets[ticket]=nil
  return request
 end
 local close=tx.close
 function tx:close()closed=true;tickets={};return close(self)end
end
