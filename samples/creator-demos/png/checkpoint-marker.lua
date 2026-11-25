-- BEGIN @ui
local UI = (function()
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
end)()
-- BEGIN marker-data.lua
-- BEGIN MARKER DATA
local MARKER = (function()
return {["w"]=6,["h"]=6,["maxRects"]=11,["palette"]={{48,106,118,255},{42,93,109,255},{34,96,115,255},{173,196,159,255},{30,88,109,255},{78,143,145,255},{80,148,148,255}},["rects"]={{2,1,1,1,1},{3,1,1,1,2},{1,2,1,1,3},{2,2,2,1,4},{4,2,1,1,5},{1,3,1,1,5},{2,3,1,1,6},{3,3,1,1,7},{4,3,1,1,3},{2,4,1,1,5},{3,4,1,1,3}}}
end)()
-- END MARKER DATA
-- BEGIN checkpoint-marker-render.lua
-- 通过 client assemble 装配 ui 模块和 MARKER 数据，再在编辑器中关联成品。
local RECT_TEMPLATE_INDEX = 0 -- 填写当前关卡中 MarkerRect 的控件模板索引
local DISPLAY_WIDTH, DISPLAY_HEIGHT = 144, 144
local OFFSET_X, OFFSET_Y = 0, 0
local RECT_BUDGET = 20

local tiles = {}
local pool
local started = false

local function setVisible(visible)
    for _, tile in ipairs(tiles) do
        if tile.alive then
            tile:SetVisible(visible)
        end
    end
end

local function clearMarker()
    setVisible(false)
    if pool then
        pool:close()
        pool = nil
    end
    tiles = {}
end

local function finite(value)
    return type(value) == "number" and math.abs(value) < math.huge
end

local function drawMarker()
    assert(type(MARKER) == "table" and math.type(MARKER.w) == "integer" and MARKER.w > 0
        and math.type(MARKER.h) == "integer" and MARKER.h > 0
        and type(MARKER.rects) == "table" and type(MARKER.palette) == "table",
        "请将 assets generate 输出的矩形 data.lua 完整复制到数据区。")
    local count = #MARKER.rects
    assert(MARKER.maxRects == count, "矩形数量与数据中的 maxRects 不符。请重新复制 data.lua。")
    assert(count <= RECT_BUDGET, count .. " 个矩形超过示例预算 " .. RECT_BUDGET .. "。请重新试算并选择预算内方案。")
    if count == 0 then
        print("检查点数据中没有可显示的矩形。")
        return
    end
    assert(math.type(RECT_TEMPLATE_INDEX) == "integer" and RECT_TEMPLATE_INDEX > 0,
        "请把当前关卡的 MarkerRect 控件模板索引填入 RECT_TEMPLATE_INDEX。")
    assert(finite(DISPLAY_WIDTH) and DISPLAY_WIDTH > 0 and finite(DISPLAY_HEIGHT) and DISPLAY_HEIGHT > 0
        and finite(OFFSET_X) and finite(OFFSET_Y), "请填写正数显示宽高和有效的中心偏移。")

    local colors = {}
    for i = 1, count do
        local x, y, w, h, index = table.unpack(MARKER.rects[i])
        assert(math.type(x) == "integer" and math.type(y) == "integer"
            and math.type(w) == "integer" and math.type(h) == "integer"
            and x >= 0 and y >= 0 and w > 0 and h > 0 and x <= MARKER.w - w and y <= MARKER.h - h,
            "矩形超出网格或尺寸无效。请重新生成 data.lua。")
        local rgba = MARKER.palette[index]
        assert(type(rgba) == "table" and #rgba == 4, "矩形的调色板索引无效。请重新生成 data.lua。")
        if not colors[index] then
            for channel = 1, 4 do
                local value = rgba[channel]
                assert(math.type(value) == "integer" and value >= 0 and value <= 255,
                    "调色板颜色必须是 0 到 255 的整数。")
            end
            colors[index] = Color.FromRGBA(table.unpack(rgba))
        end
    end

    local parent = script.object
    pool = UI.pool(
        function()
            local tile = game.InstantiateClientUIControl(RECT_TEMPLATE_INDEX, parent)
            assert(tile and tile.alive, "无法实例化 MarkerRect。请核对当前关卡的图片模板索引。")
            return tile
        end,
        function(tile) tile:SetVisible(false) end,
        function(tile)
            if tile.alive then
                game.DestroyClientUIControl(tile)
            end
        end,
        count
    )

    local scale = math.min(DISPLAY_WIDTH / MARKER.w, DISPLAY_HEIGHT / MARKER.h)
    for i, rect in ipairs(MARKER.rects) do
        local x, y, w, h, index = table.unpack(rect)
        local tile = pool:acquire(i).control
        tiles[i] = tile
        tile:SetVisible(false)
        tile:SetAnchorMin(0.5, 0.5)
        tile:SetAnchorMax(0.5, 0.5)
        tile:SetPivot(0.5, 0.5)
        tile:SetSizeDelta(w * scale, h * scale)
        tile:SetAnchoredPosition(OFFSET_X + (x + w / 2 - MARKER.w / 2) * scale,
            OFFSET_Y + (MARKER.h / 2 - y - h / 2) * scale)
        tile.imageColor = colors[index]
        tile:SetActive(true)
    end
    setVisible(true)
    print("检查点已创建 " .. count .. " 个矩形。")
end

function OnStart()
    if started then
        return
    end
    started = true
    local ok, detail = pcall(drawMarker)
    if not ok then
        local cleared, cleanupError = pcall(clearMarker)
        if not cleared then
            printerr("检查点控件清理失败。", cleanupError)
        end
        error("检查点图元显示失败。请核对图片模板、脚本挂载和 data.lua。\n" .. tostring(detail), 0)
    end
end

function OnEnable()
    setVisible(true)
end

function OnDisable()
    setVisible(false)
end

function OnDestroy()
    clearMarker()
end
