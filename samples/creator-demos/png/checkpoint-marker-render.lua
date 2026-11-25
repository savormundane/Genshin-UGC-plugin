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
