-- ============================================================================
-- GE-IMG Tool · Lua 渲染模板
--
-- 由 DatasetExporter 生成脚本时使用：文件里有两处占位标记，会被分别替换成配置块与数据块，
-- 其余原样输出。放在这里而不是写成 C# 字符串，是因为它本身就该是**可读、可校验的 Lua**。
-- （注意：这段注释里刻意不写出那两个标记的字面量——写了的话替换会把整块代码注进注释里，
--   生成出一份数据在注释里、跑不起来的脚本。生成器现在会在标记个数不为 1 时直接报错。）
--
-- 沙箱没有 io.*，所以数据必须内联——这就是下面那个数据块存在的理由。
-- ============================================================================

__CFG__

-- 紧凑数据: "t|x|y|w|h|rotDeg|rrggbbaa"
--   t: c=circle / e=ellipse / l=line
--   坐标是**源图像素**（画布换算在 decode 里做）；w/h 是外接尺寸；rotDeg 是顺时针角度
-- 数组顺序即绘制顺序（下标 1 在最底层）
local RAW = {
__RAW__
}

local pool, cursor, total = {}, 1, #RAW
local root, preplaced, warned = nil, nil, {}

local function warnOnce(key, msg)
  if warned[key] then return end
  warned[key] = true
  print("[GEIMG] " .. msg)
end

-- 找父节点：脚本通常挂在客户端控件容器上（script.object 就是容器）；
-- 挂错了层就沿 parent 向上找同名祖先。
local function ensureRoot()
  if root ~= nil and root.alive then return true end
  local node = script.object
  if node == nil then
    warnOnce("noObject", "找不到脚本宿主对象：请把脚本挂在客户端控件容器上")
    return false
  end
  if CFG.containerName ~= "" and node.name ~= CFG.containerName then
    local p = node
    while p ~= nil and p.name ~= CFG.containerName do p = p.parent end
    if p ~= nil then node = p end
  end
  root = node
  return true
end

-- 把一行数据解成画布坐标与颜色
local function decode(row)
  local t, x, y, w, h, rot, hex =
    string.match(row, "^(%a+)|([^|]+)|([^|]+)|([^|]+)|([^|]+)|([^|]+)|(%x+)$")
  if t == nil then return nil end
  x, y, w, h, rot = tonumber(x), tonumber(y), tonumber(w), tonumber(h), tonumber(rot)

  local cx = CFG.offsetX + x * CFG.scale
  local cy
  if CFG.flipY then
    cy = CFG.offsetY + (CFG.sourceHeight - y) * CFG.scale
  else
    cy = CFG.offsetY + y * CFG.scale
  end

  local c = tonumber(hex, 16)
  local a = c % 256
  local b = math.floor(c / 256) % 256
  local g = math.floor(c / 65536) % 256
  local r = math.floor(c / 16777216) % 256
  if CFG.alphaMax < 255 then a = math.floor(a * CFG.alphaMax / 255) end

  return { x = cx, y = cy, w = w * CFG.scale, h = h * CFG.scale,
           rot = rot, r = r, g = g, b = b, a = a }
end

-- 把解出来的变换与颜色写到一个控件上
local function apply(control, d)
  control:SetAnchorMin(0.5, 0.5)
  control:SetAnchorMax(0.5, 0.5)
  control:SetPivot(0.5, 0.5)
  control:SetAnchoredPosition(d.x, d.y)
  control:SetSizeDelta(d.w, d.h)
  if d.rot ~= 0 then control:SetLocalRotation(0, 0, d.rot) end
  control:SetImage(Enum.ImageSource.StaticReference, CFG.circleAssetId)
  control.imageType = Enum.ImageType.Stretch
  control.imageColor = Color.FromRGBA(d.r, d.g, d.b, d.a)
  control:SetVisible(true)
  return control
end

-- 策略 A：运行时创建（图元数不受编辑器预摆数量限制）
local function spawnInstantiate(d, index)
  local control = game.InstantiateClientUIControl(CFG.imagePrefabId, root)
  if control == nil then
    warnOnce("instantiateFail", "实例化失败：imagePrefabId 是否填对？（见 README）")
    return nil
  end
  apply(control, d)
  -- 显式设同级索引，保证绘制顺序与数据顺序一致（painter's algorithm）
  if control.SetSiblingIndex ~= nil then control:SetSiblingIndex(index - 1) end
  return control
end

-- 策略 B：用容器里预先摆好的图片控件（无实例化开销，但要先在编辑器里摆够数量）
local function spawnPool(d, index)
  if preplaced == nil then
    preplaced = root:GetChildren() or {}
    if #preplaced < total then
      warnOnce("poolShort", "容器里只找到 " .. #preplaced .. " 个子控件，需要 " .. total
                            .. " 个：请把预摆数量调大，或把 strategy 改成 instantiate")
    end
  end
  local control = preplaced[index]
  if control == nil then return nil end
  return apply(control, d)
end

local function spawn(d, index)
  if CFG.strategy == "pool" then return spawnPool(d, index) end
  return spawnInstantiate(d, index)
end

function OnStart()
  pool, cursor, preplaced = {}, 1, nil
  ensureRoot()
end

function OnUpdate(dt)
  if not ensureRoot() then return end
  local budget = CFG.budgetPerFrame
  while cursor <= total and budget > 0 do
    local d = decode(RAW[cursor])
    if d ~= nil then
      local control = spawn(d, cursor)
      if control ~= nil then pool[#pool + 1] = control end
    end
    cursor = cursor + 1
    budget = budget - 1
  end
  if cursor > total then
    print("[GEIMG] 图元铺完：" .. #pool .. "/" .. total)
    script:EnableTick(false)   -- 铺完就关掉逐帧回调，避免常驻开销
  end
end

function OnDestroy()
  if pool ~= nil then
    for i = 1, #pool do
      if pool[i] ~= nil and pool[i].alive then game.DestroyClientUIControl(pool[i]) end
    end
  end
  pool, root, preplaced = nil, nil, nil
end
