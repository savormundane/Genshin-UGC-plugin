-- Explicit QX record migration. Produces a candidate; never writes storage.
local M={}
function M.create(config)
 assert(type(config)=='table'and math.type(config.target)=='integer','migration configuration')
 local target=config.target
 assert(target>0 and target<=65535 and type(config.versions)=='table','migration target')
 local versions={}
 for version,entry in pairs(config.versions)do
  assert(math.type(version)=='integer'and version>0 and version<=target,'migration version')
  assert(type(entry)=='table'and type(entry.codec)=='table'and type(entry.codec.decode)=='function'and type(entry.codec.encode)=='function'and type(entry.validate)=='function','migration contract')
  if version~=target then
   assert(math.type(entry.next)=='integer'and entry.next>version and entry.next<=target and type(entry.upgrade)=='function','migration edge')
  else assert(entry.next==nil and entry.upgrade==nil,'target has no migration')end
  versions[version]={codec=entry.codec,validate=entry.validate,next=entry.next,upgrade=entry.upgrade}
 end
 assert(versions[target],'missing target contract')
 for version in pairs(versions)do
  local at=version
  while at~=target do local entry=assert(versions[at],'missing migration edge');at=entry.next end
 end
 local migration={}
 function migration:prepare(body)
  assert(type(body)=='string'and #body>=4 and body:sub(1,2)=='QX','invalid record header')
  local source=string.unpack('>I2',body,3)
  local entry=assert(versions[source],'unknown record version')
  local value=entry.codec:decode(body)
  assert(entry.validate(value)==true,'invalid source record')
  local steps={}local at=source
  while at~=target do
   value=entry.upgrade(value)
   steps[#steps+1]={from=at,to=entry.next}
   at=entry.next;entry=versions[at]
   assert(entry.validate(value)==true,'invalid migrated record')
  end
  local candidate=source==target and body or entry.codec:encode(value)
  assert(type(candidate)=='string'and #candidate>=4 and candidate:sub(1,2)=='QX'and string.unpack('>I2',candidate,3)==target,'invalid target encoding')
  assert(entry.validate(entry.codec:decode(candidate))==true,'target readback invalid')
  return {source_version=source,target_version=target,original=body,candidate=candidate,changed=candidate~=body,steps=steps}
 end
 return migration
end
return M
