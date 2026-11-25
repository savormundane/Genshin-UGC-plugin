-- ============================================================================
-- UI 层：背景（纯色大圆铺满）+ 两侧按钮 / 说明 / 参数文字 + 拖动条
--
-- 拖 动 条 的 实 现（API 里没有现成 slider，必须自己搭）
--   可用拼装件：图片控件（外观）+ 光标检测区（命中与拖动事件）。
--   三种可做法，这里用的是第 ① 种：
--     ① 绝对映射（本文件用的）：拖动事件里取 CursorEventData:GetUIPos()，
--        换算到 anchoredPosition 空间后，直接映射成轨道上的比例。
--        优点：滑块永远跟手，不会累积漂移；手指/光标滑出轨道也不丢。
--     ② 相对增量：用 GetUIPosDelta() 累加位移。写法最短，但会漂（取整 + 丢帧），
--        而且滑得快时容易跟不上。
--     ③ 轮询：按住时每帧用 game.GetCursorUIPos() 取位置。省掉拖动事件，
--        但仍需要一个"按下/抬起"的事件来知道是否在拖。
--   三个都依赖同一个事实：**光标坐标是「画布左下角原点」，控件位置是「容器中心原点」**，
--   相差半个画布，比较前必须转换（这里用 toAnchor 统一处理）。
-- ============================================================================

local UISPEC = __UISPEC__

local UI = {         -- 运行时状态
  pool = {},         -- 所有 UI 控件（销毁时要一起收）
  bg = {},           -- 背景圆（要排在最底层）
  fg = {},           -- 面板/按钮/文字（要排在角色之上）
  sliders = {},      -- 拖动条：{set=函数, label=文本框, get=当前值函数}
  texts = {},        -- 需要动态刷新的文字
  keyBindings = {},  -- 已注册的按键监听（销毁时按 (事件,回调) 精确摘掉）
  z = 0,             -- 下一个同级索引（排在角色之上）
}

local function cfgColor(v)
  return Color.FromRGBA(math.floor(v / 0x1000000) % 256, math.floor(v / 0x10000) % 256,
                        math.floor(v / 0x100) % 256, v % 256)
end

-- 光标事件回调的签名文档**没有写死**，所以这里做成签名无关：
--   (cursorEventData) / (control, cursorEventData) / (x, y) / () 全都吃。
-- 归一后统一返回「画布左下角原点」坐标；实在拿不到就退回 game.GetCursorUIPos() 轮询。
-- 这样即使运行时什么都不传，拖动条依然跟手（用轮询补位）。
local SIGNATURE_LOGGED = false
local function readCursorPos(...)
  local nums, data = {}, nil
  for i = 1, select("#", ...) do
    local v = select(i, ...)
    local tv = type(v)
    if tv == "number" then
      nums[#nums + 1] = v
    elseif tv == "table" then
      if v.GetUIPos ~= nil then data = v
      elseif data == nil and v.dragging ~= nil then data = v end   -- CursorEventData 的字段
    end
  end
  local src = nil
  if data ~= nil then
    local ok, a, b = pcall(function() return data:GetUIPos() end)
    if ok then
      if type(a) == "number" and type(b) == "number" then
        if not SIGNATURE_LOGGED then
          SIGNATURE_LOGGED = true
          print("[GEIMG] 光标坐标来源：CursorEventData:GetUIPos()")
        end
        return a, b, "data"
      elseif type(a) == "table" and type(a.x) == "number" then
        return a.x, a.y, "data.xy"
      end
    end
  end
  if #nums >= 2 then
    if not SIGNATURE_LOGGED then
      SIGNATURE_LOGGED = true
      print("[GEIMG] 光标坐标来源：事件回调直接给的两个数")
    end
    return nums[1], nums[2], "args"
  end
  if game.GetCursorUIPos ~= nil then
    local ok, x, y = pcall(function() return game.GetCursorUIPos() end)
    if ok and type(x) == "number" and type(y) == "number" then
      if not SIGNATURE_LOGGED then
        SIGNATURE_LOGGED = true
        print("[GEIMG] 光标坐标来源：game.GetCursorUIPos() 轮询（回调没给坐标）")
      end
      return x, y, "poll"
    end
  end
  return nil, nil, "none"
end

-- 注册光标事件：枚举名不对就不注册（不同版本枚举可能不同名），并只提示一次
local function uiOn(area, ...)
  local names = { ... }
  for _, name in ipairs(names) do
    local et = Enum.CursorEventType and Enum.CursorEventType[name]
    if et ~= nil and area.AddCursorEventListener ~= nil then
      return et
    end
  end
  return nil
end

-- 光标坐标（画布左下原点）→ 控件坐标（容器中心原点，Y 向上）
local function toAnchor(ux, uy)
  return ux - CX, uy - CY
end

-- 一张图片控件（背景圆、面板底、按钮底、轨道、滑块都用它）
local function uiImage(x, y, w, h, c, z)
  if CFG.imagePrefabId == 0 then return nil end
  local ctl = game.InstantiateClientUIControl(CFG.imagePrefabId, root)
  if ctl == nil then return nil end
  ctl:SetAnchorMin(0.5, 0.5)
  ctl:SetAnchorMax(0.5, 0.5)
  ctl:SetPivot(0.5, 0.5)
  ctl:SetAnchoredPosition(x, y)
  ctl:SetSizeDelta(w, h)
  ctl:SetImage(Enum.ImageSource.StaticReference, CFG.circleAssetId)
  ctl.imageType = Enum.ImageType.Stretch
  ctl.imageColor = cfgColor(c)
  ctl:SetVisible(true)
  if ctl.SetSiblingIndex ~= nil then ctl:SetSiblingIndex(UI.z) end
  UI.z = UI.z + 1
  UI.pool[#UI.pool + 1] = ctl
  UI.fg[#UI.fg + 1] = ctl
  return ctl
end

-- 一段文字（说明、参数值都用它）
local function uiText(x, y, w, h, size, c, align, s)
  if CFG.textPrefabId == 0 then return nil end
  local ctl = game.InstantiateClientUIControl(CFG.textPrefabId, root)
  if ctl == nil then return nil end
  ctl:SetAnchorMin(0.5, 0.5)
  ctl:SetAnchorMax(0.5, 0.5)
  ctl:SetPivot(0.5, 0.5)
  ctl:SetAnchoredPosition(x, y)
  ctl:SetSizeDelta(w, h)
  ctl.text = s or ""
  ctl.fontSize = size
  ctl.fontColor = cfgColor(c)
  if align == "left" then ctl.horizontalAlignment = Enum.TextHorizontalAlignment.Left
  elseif align == "right" then ctl.horizontalAlignment = Enum.TextHorizontalAlignment.Right
  else ctl.horizontalAlignment = Enum.TextHorizontalAlignment.Middle end
  ctl.verticalAlignment = Enum.TextVerticalAlignment.Middle
  ctl:SetVisible(true)
  if ctl.SetSiblingIndex ~= nil then ctl:SetSiblingIndex(UI.z) end
  UI.z = UI.z + 1
  UI.pool[#UI.pool + 1] = ctl
  UI.fg[#UI.fg + 1] = ctl
  return ctl
end

-- 命中区（按钮点击、拖动条拖动都靠它）
local function uiArea(x, y, w, h)
  if CFG.areaPrefabId == 0 then return nil end
  local ctl = game.InstantiateClientUIControl(CFG.areaPrefabId, root)
  if ctl == nil then return nil end
  ctl:SetAnchorMin(0.5, 0.5)
  ctl:SetAnchorMax(0.5, 0.5)
  ctl:SetPivot(0.5, 0.5)
  ctl:SetAnchoredPosition(x, y)
  ctl:SetSizeDelta(w, h)
  if ctl.raycastTarget ~= nil then ctl.raycastTarget = true end   -- 不打开收不到光标事件
  ctl:SetVisible(true)
  if ctl.SetSiblingIndex ~= nil then ctl:SetSiblingIndex(UI.z) end
  UI.z = UI.z + 1
  UI.pool[#UI.pool + 1] = ctl
  UI.fg[#UI.fg + 1] = ctl
  return ctl
end

-- ── 拖动条 ──
local SLIDER_SETTER = {
  swing   = function(v) GAZE.swing = v end,
  yaw     = function(v) GAZE.yaw = v end,
  pitch   = function(v) GAZE.pitch = v end,
  swingY  = function(v) GAZE.swingY = v end,
  motion  = function(v) CFG.motionScale = v end,
  breath  = function(v) CFG.baseAmp = v end,
  amp     = function(v) CFG.ampScale = v end,
  speed   = function(v) CFG.speed = v end,
  period  = function(v) CFG.period = v end,
  -- 骨骼旋钮：身体转动是连续位移场，这两个数直接决定"转多少 / 有多立体"
  bodyAmp = function(v) BONE.bodyAmp = v end,
  depthK  = function(v) BONE.depthK = v end,
  -- 骨骼总开关：关掉会退回"按部件权重绕脚底倾角"的旧路径，方便对比
  boneOn  = function(v) BONE.on = (v > 0.5) end,
}

local function uiSlider(spec)
  local trackC = 0x39415AFF
  local knobC  = 0x5AA9FFFF
  uiImage(spec.x, spec.y, spec.w, 8, trackC)                       -- 轨道
  local knob = uiImage(spec.x, spec.y, 22, 22, knobC)              -- 滑块
  local label = uiText(spec.x, spec.y + 26, spec.w, 24, 18, 0xE6E8EFFF, spec.al or "left",
                       (spec.label or "") .. "  " .. tostring(spec.val))
  local area = uiArea(spec.x, spec.y, spec.w + 24, 40)             -- 命中区加高，好点
  local half = spec.w / 2
  local lo, hi = spec.min, spec.max

  local function apply(v)
    if v < lo then v = lo end
    if v > hi then v = hi end
    local t = (hi > lo) and ((v - lo) / (hi - lo)) or 0
    if knob ~= nil then knob:SetAnchoredPosition(spec.x - half + t * spec.w, spec.y) end
    if label ~= nil then
      label.text = (spec.label or "") .. "  " .. string.format(spec.fmt or "%.1f", v)
    end
    local set = SLIDER_SETTER[spec.ch]
    if set ~= nil then set(v) end
  end
  apply(spec.val)

  if area ~= nil and area.AddCursorEventListener ~= nil then
    local function onEvent(...)
      local ux, uy = readCursorPos(...)
      if ux == nil then return end
      local ax = toAnchor(ux, 0)                      -- 只关心水平位置
      local t = (ax - (spec.x - half)) / spec.w
      apply(lo + t * (hi - lo))
    end
    for _, nm in ipairs({ "CursorDown", "CursorDrag", "CursorClick" }) do
      local et = uiOn(area, nm)
      if et ~= nil then area:AddCursorEventListener(et, onEvent) end
    end
  end
  UI.sliders[#UI.sliders + 1] = { spec = spec, apply = apply }
end

-- ── 按钮 ──
local function uiButton(spec)
  uiImage(spec.x, spec.y, spec.w, spec.h, spec.c or 0x2A3346FF)
  uiText(spec.x, spec.y, spec.w, spec.h, 20, 0xE6E8EFFF, "middle", spec.label or "")
  local area = uiArea(spec.x, spec.y, spec.w, spec.h)
  if area ~= nil and area.AddCursorEventListener ~= nil then
    local et = uiOn(area, "CursorClick", "Click")
    if et ~= nil then area:AddCursorEventListener(et, function(...)
      local cmd = spec.cmd or ""
      local kind, arg = string.match(cmd, "^(%a+):(.*)$")
      if kind == "act" then
        PlayAction(arg)
      elseif kind == "preset" then
        SetPreset(arg)
      elseif kind == "gaze" then
        SetGaze(arg ~= "0")
      elseif kind == "blink" then
        SetBlink(arg)
      elseif kind == "animate" then
        SetAnimate(arg ~= "0")
      elseif kind == "cmd" then
        if arg == "blinkOnce" and BlinkOnce ~= nil then BlinkOnce() end
      elseif kind == "tog" then
        if arg == "animate" then SetAnimate(not CFG.animate)
        elseif arg == "gaze" then SetGaze(not CFG.gaze)
        elseif arg == "blink" then
          CFG.blink.auto = not CFG.blink.auto
          if CFG.blink.auto then blink.next = bt + 0.3 end
        end
      end
    end) end
  end
end

-- ── 组装 ──
function UIBuild()
  if CFG.imagePrefabId == 0 then
    print("[GEIMG] UI 未建：CFG.imagePrefabId 还是 0（图片控件模板）")
    return
  end
  if CFG.textPrefabId == 0 then
    print("[GEIMG] 注意：CFG.textPrefabId 是 0，文字控件建不出来")
  end
  if CFG.areaPrefabId == 0 then
    print("[GEIMG] 注意：CFG.areaPrefabId 是 0，按钮点不动、拖动条拖不了")
  end
  local n0 = 0
  -- 背景：纯色大圆铺满（一个直径 1900 的圆就能盖住 1600x900：半对角线只有 918）
  for _, c in ipairs(UISPEC.bg or {}) do
    local im = uiImage(c[1], c[2], c[3], c[4], c[5])
    if im ~= nil then UI.bg[#UI.bg + 1] = im; UI.fg[#UI.fg] = nil end
    n0 = n0 + 1
  end
  for _, t in ipairs(UISPEC.texts or {}) do uiText(t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[8]) end
  for _, b in ipairs(UISPEC.buttons or {}) do uiButton(b) end
  for _, s in ipairs(UISPEC.sliders or {}) do uiSlider(s) end
  uiBuildHelp()
  uiBindKeys()
  print(string.format("[GEIMG] UI 建好：背景圆 %d 个，共 %d 个控件", n0, #UI.pool))
end

-- 角色铺完后重排同级索引：背景 → 角色 → UI（绘制顺序即数组顺序，没有 zIndex）
function UIReindex()
  local z = 0
  local function put(list)
    for i = 1, #list do
      local c = list[i]
      if c ~= nil and c.alive and c.SetSiblingIndex ~= nil then
        c:SetSiblingIndex(z); z = z + 1
      end
    end
  end
  put(UI.bg)                       -- 最底
  local n = #RAW
  for i = 1, n do                  -- 角色
    local c = pool[i]
    if c ~= nil and c.alive and c.SetSiblingIndex ~= nil then c:SetSiblingIndex(z) end
    z = z + 1
  end
  put(UI.fg)                       -- UI 压在角色之上
  UI.z = z
  print("[GEIMG] 层序重排完成：背景 " .. #UI.bg .. " · 角色 " .. n .. " · UI " .. #UI.fg)
end

-- ============================================================================
-- 快捷键 + 屏幕文字（状态 / 功能）
--
-- 键位与浏览器预览页（l2d_preview.html）**完全一致**，方便照着预览的手感写进游戏：
--   1~6 预设（待机/摆动/风吹/眯眼笑/说话/全停）、7~0 一次性动作（摇头/点头/惊讶/摆臂）
--   U 眨一下、Y 保持闭眼、Z 视点跟随、G 动画总开关、H 功能表开关
--
-- 游戏侧的按键是「奇匠按键」（Enum.KeyboardKeyCode.CraftspersonKey1..43）：
--   Key1..10 = 数字 1~0，Key11..15 = U / Z / Y / G / H
-- 对应的事件是 Enum.KeyEventType.KeyboardCraftspersonKey<N>Down（Down 系列值 0..42）。
--
-- ⚠️ **两个待实机验证的点**：
--   ① 这些按键会不会被游戏本身的界面抢走（奇匠模式下的数字键/字母键有可能已被占用）；
--   ② 键事件挂在哪个控件上才能收到 —— 这里做成了多路注册（根容器 + 全屏命中区），
--      哪一路先成功就用哪一路，并在日志里写明。回调返回 true 表示"消费该事件"，
--      只有真的绑上去了才返回 true，免得把游戏自己的按键吃掉。
-- ============================================================================

local KEYACTS = {
  -- {事件名 或 奇匠按键序号, 屏幕上的键名, 功能说明, 执行}
  {1,  "1", "待机",     function() SetPreset("idle") end},
  {2,  "2", "摆动",     function() SetPreset("swayIdle") end},
  {3,  "3", "风吹",     function() SetPreset("wind") end},
  {4,  "4", "眯眼笑",   function() SetPreset("smile") end},
  {5,  "5", "说话",     function() SetPreset("talk") end},
  {6,  "6", "全停",     function() uiAllOff() end},
  {7,  "7", "摇头",     function() PlayAction("shake") end},
  {8,  "8", "点头",     function() PlayAction("nodOnce") end},
  {9,  "9", "惊讶",     function() PlayAction("surprise") end},
  {10, "0", "摆臂",     function() PlayAction("wave") end},
  {11, "U", "眨一下",   function() BlinkOnce() end},
  {12, "Z", "视点跟随", function() SetGaze(not CFG.gaze) end},
  {13, "Y", "保持闭眼", function() uiToggleHold() end},
  {14, "G", "动画开关", function() SetAnimate(not CFG.animate) end},
  {15, "H", "功能表",   function() uiToggleHelp() end},
  -- 跳跃用**空格**（枚举里的 KeyboardJumpKeyDown），不是奇匠按键，所以直接写事件名。
  -- ⚠️ 回调返回 true = 消费该事件：如果这一关的空格本来就是"角色跳跃"，
  --    绑上去可能会把这个键吃掉。实机若发现角色跳不了了，先注释掉这一行试。
  {"KeyboardJumpKeyDown", "空格", "跳跃", function() PlayAction("jump") end},
}

UI.lastKey = "—"
UI.lastKeyT = -99
UI.helpOn = true

function uiAllOff()
  SetPreset("allOff")
  SetAnimate(false)
  print("[GEIMG] 全停：呼吸/眨眼/动作归零，逐帧回调已关（按 G 或点「动画开关」恢复）")
end

function uiToggleHold()
  if CFG.blink.hold then
    SetBlink("open")
  else
    SetBlink("hold")
  end
end

function uiToggleHelp()
  UI.helpOn = not UI.helpOn
  if UI.help ~= nil and UI.help.alive then UI.help:SetVisible(UI.helpOn) end
end

-- 屏幕文字：功能表 + 实时状态。两行说明 + 三行状态，都放在角色上方的空白区。
function uiBuildHelp()
  if UISPEC.help == nil or CFG.textPrefabId == 0 then return end
  local c = UISPEC.help
  UI.help = uiText(c[1], c[2], c[3], c[4], c[5], c[6], c[7], uiHelpText())
end

function uiHelpText()
  local parts = {}
  for _, a in ipairs(KEYACTS) do
    parts[#parts + 1] = "[" .. a[2] .. "]" .. a[3]
  end
  local st = GetStatus()
  local acts = (st.acts or 0) > 0 and ("｜动作 " .. st.acts .. " 个") or ""
  return table.concat(parts, " ")
      .. "\n视点 " .. string.format("%+.2f %+.2f", st.gazeX or 0, st.gazeY or 0)
      .. "｜眨眼 " .. string.format("%.2f", st.blinkL or 0)
      .. (CFG.blink.hold and "(保持)" or (CFG.blink.auto and "(自动)" or "(关)"))
      .. "｜动画 " .. (CFG.animate and "开" or "关")
      .. acts
      .. "\n图元 " .. st.total .. "｜帧 " .. st.frames
      .. "｜写入 " .. string.format("%.0f", st.writesPerFrame or 0) .. "/帧"
      .. "｜首帧 " .. string.format("%.1f", st.firstMs or 0) .. "ms"
      .. "｜上一步 " .. UI.lastKey
end

-- 注册按键：先试根容器；根容器不行才铺一块**角落里的**小命中区兜底。
-- 兜底区故意做小（300x60，放在左下角）：全屏命中区会跟按钮/拖动条抢光标事件。
function uiBindKeys()
  local KeyEventType = Enum and Enum.KeyEventType
  if KeyEventType == nil then
    print("[GEIMG] 快捷键：Enum.KeyEventType 不存在，快捷键不可用（按钮/拖动条不受影响）")
    return
  end

  local function tryOn(ctl, name)
    if ctl == nil or ctl.AddKeyEventListener == nil then return 0 end
    local n, firstErr = 0, nil
    for _, a in ipairs(KEYACTS) do
      -- a[1] 可以是奇匠按键序号（数字），也可以是事件名（字符串）
      local key = (type(a[1]) == "string") and a[1]
                  or ("KeyboardCraftspersonKey" .. a[1] .. "Down")
      local et = KeyEventType[key]
      if et ~= nil then
        local callback = function(...)
          UI.lastKey = a[2] .. " · " .. a[3]
          UI.lastKeyT = t
          a[4]()
          return true          -- 消费该事件（只在真的绑上时返回 true）
        end
        local ok, err = pcall(function() ctl:AddKeyEventListener(et, callback) end)
        if ok then
          n = n + 1
          -- 记下来，销毁时按 (事件, 回调) 精确摘掉，不动容器上其他脚本的监听
          UI.keyBindings[#UI.keyBindings + 1] = { ctl = ctl, et = et, callback = callback }
        elseif firstErr == nil then
          firstErr = tostring(err)
        end
      end
    end
    print(string.format("[GEIMG] 快捷键绑在「%s」：成功 %d / %d 个（1~0 + U/Z/G/H/空格）",
                        name, n, #KEYACTS))
    if n == 0 and firstErr ~= nil then
      print("[GEIMG]   注册失败原因：" .. firstErr)
    end
    return n
  end

  if tryOn(root, "容器 " .. tostring(CFG.containerName)) > 0 then
    UI.keyTarget = "容器"
    return
  end
  local area = uiArea(-620, -420, 300, 60)          -- 角落兜底，不挡按钮
  if tryOn(area, "角落按键区") > 0 then
    UI.keyTarget = "角落按键区"
    return
  end
  print("[GEIMG] 快捷键：所有候选控件都注册失败 —— 只能点按钮")
end

-- 每帧刷新（每 10 帧一次）：功能表 + 状态文字
function UIUpdate(dt)
  if UISPEC.help ~= nil then
    if UI.help == nil then
      uiBuildHelp()
    elseif UI.help.alive and UI.helpOn then
      UI.help.text = uiHelpText()
    end
  end
  if UISPEC.status ~= nil then
    local c = UISPEC.status
    local st = GetStatus()
    if UI.status == nil then
      UI.status = uiText(c[1], c[2], c[3], c[4], c[5], c[6], c[7], "")
    end
    if UI.status ~= nil and UI.status.alive then
      UI.status.text = string.format(
        "图元 %d｜帧 %d｜首帧 %.1fms｜写入 %.0f/帧\n预设通道 摆动%.2f 说话%.2f｜视点 %+.2f %+.2f｜%s%s",
        st.total, st.frames, st.firstMs, st.writesPerFrame or 0,
        st.chSway or 0, st.chTalk or 0, st.gazeX or 0, st.gazeY or 0,
        st.jumping and "跳跃中 " or "", UI.lastKey)
    end
  end
end

-- 销毁时的收尾：**只摘掉本脚本注册的按键监听**（容器上可能还挂着别的脚本的监听，
-- 整片移除会把别人的一起弄掉），再销毁本脚本建的 UI 控件。
function UICleanup()
  for i = #UI.keyBindings, 1, -1 do
    local b = UI.keyBindings[i]
    if b.ctl and b.ctl.alive and b.ctl.RemoveKeyEventListener ~= nil then
      b.ctl:RemoveKeyEventListener(b.et, b.callback)
    end
  end
  UI.keyBindings = {}
  for i = #UI.pool, 1, -1 do
    local c = UI.pool[i]
    if c and c.alive then game.DestroyClientUIControl(c) end
  end
  UI.pool = {}
end
