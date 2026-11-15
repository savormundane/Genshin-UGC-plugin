-- Explicit asset catalogue, weighted cache and identity-bearing leases.
local M = {}
function M.create(config)
  assert(type(config.capacity)=='number' and config.capacity%1==0 and config.capacity>0, 'invalid capacity')
  assert(type(config.load)=='function' and type(config.catalogue)=='table', 'catalogue and loader required')
  local catalogue, entries, leases = {}, {}, {}
  local used, clock = 0, 0
  for name,item in pairs(config.catalogue) do
    assert(type(name)=='string' and name~='' and type(item)=='table', 'invalid catalogue entry')
    assert(type(item.rect_count)=='number' and item.rect_count%1==0 and item.rect_count>0, 'invalid rectangle count')
    catalogue[name]={source=item.source, rect_count=item.rect_count}
  end
  local capacity, loader = config.capacity, config.load
  local api = {}
  function api:acquire(name)
    local item=catalogue[name]
    if not item then return nil,'unknown asset' end
    local entry=entries[name]
    if not entry then
      if item.rect_count>capacity then return nil,'asset exceeds capacity' end
      local candidates,available={},capacity-used
      for key,value in pairs(entries) do
        if value.refs==0 then
          candidates[#candidates+1]={name=key,entry=value}
          available=available+value.weight
        end
      end
      if available<item.rect_count then return nil,'capacity pinned' end
      table.sort(candidates,function(a,b)return a.entry.last<b.entry.last end)
      -- Loader returns data only. Validate before evicting existing cached data.
      local data=loader(item.source,name)
      assert(type(data)=='table' and type(data.rects)=='table', 'invalid asset data')
      local count=0
      for key in pairs(data.rects) do
        assert(type(key)=='number' and key%1==0 and key>=1 and key<=item.rect_count,'invalid rectangle sequence')
        count=count+1
      end
      assert(count==item.rect_count,'catalogue rectangle count mismatch')
      for _,candidate in ipairs(candidates) do
        if used+item.rect_count<=capacity then break end
        entries[candidate.name]=nil;used=used-candidate.entry.weight
      end
      entry={data=data,weight=item.rect_count,refs=0,last=0}
      entries[name]=entry;used=used+entry.weight
    end
    clock=clock+1;entry.last=clock;entry.refs=entry.refs+1
    local lease={};leases[lease]=entry
    return lease
  end
  function api:data(lease)
    local entry=leases[lease]
    assert(entry,'invalid or released lease')
    return entry.data
  end
  function api:release(lease)
    local entry=leases[lease]
    if not entry then return false end
    leases[lease]=nil;entry.refs=entry.refs-1
    clock=clock+1;entry.last=clock
    return true
  end
  function api:trim()
    for name,entry in pairs(entries) do
      if entry.refs==0 then entries[name]=nil;used=used-entry.weight end
    end
    return used
  end
  function api:stats()
    local count,pinned=0,0
    for _,entry in pairs(entries) do count=count+1;if entry.refs>0 then pinned=pinned+entry.weight end end
    return {rectangles=used,capacity=capacity,entries=count,pinned=pinned}
  end
  return api
end
return M
