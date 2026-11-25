-- Generated data and the mount settings are local to the assembled script.
local tiles = {}
local started = false

local function show(visible)
    for _, tile in ipairs(tiles) do
        if tile.alive then
            tile:SetVisible(visible)
        end
    end
end

function OnDestroy()
    for _, tile in ipairs(tiles) do
        if tile.alive then
            game.DestroyClientUIControl(tile)
        end
    end
    tiles = {}
end

function OnStart()
    if started then
        return
    end
    started = true
    local ok, detail = pcall(function()
        for _, layer in ipairs(LAYERS) do
            local scale = math.min(MOUNT.width / layer.w, MOUNT.height / layer.h)
            local colors = {}
            for i, rgba in ipairs(layer.palette) do
                colors[i] = Color.FromRGBA(table.unpack(rgba))
            end
            for _, rect in ipairs(layer.rects) do
                local x, y, w, h, index = table.unpack(rect)
                local tile = game.InstantiateClientUIControl(MOUNT.template_index, script.object)
                assert(tile and tile.alive, "无法创建矩形。请核对图片模板索引和关卡控件预算。")
                tiles[#tiles + 1] = tile
                tile:SetVisible(false)
                tile:SetAnchorMin(0.5, 0.5)
                tile:SetAnchorMax(0.5, 0.5)
                tile:SetPivot(0.5, 0.5)
                tile:SetSizeDelta(w * scale, h * scale)
                tile:SetAnchoredPosition((x + w / 2 - layer.w / 2) * scale,
                    (layer.h / 2 - y - h / 2) * scale)
                tile.imageColor = colors[index]
                tile:SetActive(true)
            end
        end
    end)
    if not ok then
        OnDestroy()
        error(detail, 0)
    end
    show(true)
    print("已创建 " .. #tiles .. " 个拟合矩形。")
end

function OnEnable()
    show(true)
end

function OnDisable()
    show(false)
end
