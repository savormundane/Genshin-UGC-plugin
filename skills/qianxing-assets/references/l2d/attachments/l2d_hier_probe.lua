-- ============================================================================
-- 层级 / 父容器 探测脚本 —— 独立运行，不改动生产脚本
--
-- 为什么需要它：
--   目标软件支持「同一骨骼的图元挂在一个父容器下，只对父容器做动画」：
--   `parent` 字段可读写、`game.InstantiateClientUIControl(prefabId, parent)` 直接指定父级，
--   API 里还有专门的 `ClientUIContainerControl`（容器节点，用于组织子控件）。
--   官方规范也写明「父子层级中的位移、缩放、显隐、Alpha、镜像与裁剪效果由运行时 UI 层级共同决定」。
--
--   走通的话负载模型会彻底改观：
--     现在 = 9941 个图元全是 root 的子控件，每帧要写几千次属性
--     之后 = 图元挂在 26 个部件的父容器下，每帧只写几十次（写父容器）
--
--   但有几件**决定怎么实现**的事，文档里没有（或只落在被裁切的表里），只能实机问：
--     A. 容器能不能实例化（需要编辑器给一个"容器节点"模板的 prefabId）
--     B. 子控件的 anchoredPosition 是**相对父容器**还是相对 root
--     C. 一个父容器能挂多少个子控件（规范里"受控件的子控件数"后半句被裁掉了）
--     D. 父容器的**旋转**会不会传给子控件（规范只列了位移/缩放/显隐/Alpha/镜像/裁剪，没提旋转）
--     E. 父容器 SetVisible(false) 会不会藏掉子控件
--     F. 父控件（若用图片控件当父）的 imageColor alpha 会不会乘到子控件
--     G. 运行期改 `child.parent` 能不能把子控件搬家
--
-- 用法：
--   1. 填 CFG 的 ID（containerPrefabId 尽量填编辑器里"容器节点"模板的 ID）
--   2. 挂到有 GEIMG_Canvas 容器的场景运行
--   3. A/C 会直接打印结论；B/D/E/F/G 需要你**看画面**逐条回答（脚本会打印清单）
-- ============================================================================

local CFG = {
  containerName = "GEIMG_Canvas",
  imagePrefabId = 1073741850,     -- 图片控件模板（子控件用）
  containerPrefabId = 0,          -- ★ 容器节点模板；填 0 则用图片模板兜底试
  circleAssetId = 100002,

  parentX = -300, parentY = 140,  -- 父容器位置（画布中心原点）
  secondX =  300, secondY = -160, -- 第二个容器（G 段搬家用）
  size = 70,
  rot = 30,                       -- D 段给父容器转多少度
  drip = 25,                      -- C 段每帧加多少个子控件（别一帧建太多）
  marks = { 300, 600, 1200, 2000, 3000 },   -- C 段的检查点
  wait = 1.6,                     -- 每个视觉问题的停留时间（秒）
}

local root, pA, pB, marker = nil, nil, nil, nil
local kids, res, seq = {}, {}, 0
local P = { ph = "boot", f = 0, want = 0 }
local function log(s) print("[HIER] " .. s) end
local function ok(s)  print("[HIER] ✅ " .. s) end
local function bad(s) print("[HIER] ❌ " .. s) end
local function ask(s) print("[HIER] ❓ " .. s) end
local function frames(dt, sec) return math.max(1, math.floor(sec / dt + 0.5)) end

local function ensureRoot()
  if root ~= nil and root.alive then return true end
  if game.FindClientUIRoot ~= nil then
    local r = game.FindClientUIRoot(CFG.containerName)
    if r ~= nil then root = r; return true end
  end
  return false
end

local function mk(prefab, parent, x, y, rgba)
  local c = game.InstantiateClientUIControl(prefab, parent)
  if c == nil then return nil end
  c:SetAnchorMin(0.5, 0.5); c:SetAnchorMax(0.5, 0.5); c:SetPivot(0.5, 0.5)
  c:SetSizeDelta(CFG.size, CFG.size)
  c:SetAnchoredPosition(x, y)
  pcall(function()
    c:SetImage(Enum.ImageSource.StaticReference, CFG.circleAssetId)
    c.imageType = Enum.ImageType.Stretch
    c.imageColor = Color.FromRGBA(rgba[1], rgba[2], rgba[3], rgba[4] or 255)
  end)
  c:SetVisible(true)
  return c
end

local function childCount(c)
  local pok, t = pcall(function() return c:GetChildren() end)
  if not pok or t == nil then return -1 end
  local n = 0
  for _ in pairs(t) do n = n + 1 end
  return n
end

local function go(ph, dt) P.ph, P.f = ph, 0 end

function OnInit() end

function OnStart()
  log("开始探测（容器 " .. CFG.containerName .. "）")
  if not ensureRoot() then
    bad("找不到容器：核对 CFG.containerName 与脚本挂载位置")
    return
  end
  script:EnableUpdate(true)
end

function OnUpdate(dt)
  if not ensureRoot() then return end
  P.f = P.f + 1
  local ph = P.ph

  -- ══ A：容器能不能建 ══
  if ph == "boot" then
    if CFG.containerPrefabId ~= 0 then
      pA = mk(CFG.containerPrefabId, root, CFG.parentX, CFG.parentY, { 120, 120, 130, 255 })
      if pA ~= nil then
        res.prefab = "容器模板 " .. CFG.containerPrefabId .. " 可用 ✓"
        ok("A 段：用 containerPrefabId 建出容器成功")
      else
        bad("A 段：containerPrefabId=" .. CFG.containerPrefabId ..
            " 建不出来 → 核对编辑器里那是不是「容器节点」模板")
      end
    end
    if pA == nil then
      pA = mk(CFG.imagePrefabId, root, CFG.parentX, CFG.parentY, { 120, 120, 130, 255 })
      if pA == nil then
        bad("A 段：连图片模板都建不出来 → 先解决 imagePrefabId")
        script:EnableUpdate(false); return
      end
      res.prefab = "未填容器模板，用图片模板兜底"
      ask("A 段：containerPrefabId 是 0 → 用图片模板兜底。"
          .. "**请确认编辑器里有没有专门的「容器节点」模板并填上 ID**")
    end
    pB = mk(CFG.imagePrefabId, root, CFG.secondX, CFG.secondY, { 130, 120, 120, 255 })
    log(string.format("A 段：两个父容器已建。子控件数（应为 0/0）：%d / %d",
        childCount(pA), childCount(pB)))
    -- 记号球：挂在父容器原点，用来肉眼判断坐标空间
    marker = mk(CFG.imagePrefabId, pA, 0, 0, { 255, 255, 255, 255 })
    if marker == nil then
      bad("A 段：子控件挂不上去 → 这个父容器不接受子控件，后面都不用测了")
      script:EnableUpdate(false); return
    end
    log("A 段：白色记号球已挂在父容器原点 (0,0)")
    go("C", dt)

  -- ══ C：滴灌式加子控件，找数量上限 ══
  elseif ph == "C" then
    if P.want >= #CFG.marks then
      log(string.format("C 段结束：单容器至少能挂 %d 个子控件（检查点最高 %d）",
          #kids, CFG.marks[#CFG.marks]))
      go("Q_intro", dt); return
    end
    local target = CFG.marks[P.want + 1]
    local n = 0
    while n < CFG.drip and #kids < target do
      local c = mk(CFG.imagePrefabId, pA, 0, 0, { 60, 70, 90, 0 })   -- alpha 0：只占位不显示
      if c == nil then
        bad(string.format("C 段：加到第 %d 个时**建不出来了**（GetChildren 报 %d）"
            .. " → 单容器子控件数上限就在这一档附近", #kids + 1, childCount(pA)))
        res.limit = #kids
        break
      end
      kids[#kids + 1] = c
      n = n + 1
    end
    if res.limit ~= nil then
      go("Q_intro", dt); return
    end
    if #kids >= target then
      ok(string.format("C 段：%d 个子控件挂载成功（GetChildren=%d）", #kids, childCount(pA)))
      P.want = P.want + 1
    end

  -- ══ Q：视觉问答（一次布置一个动作，留时间让人看）══
  elseif ph == "Q_intro" then
    ask("════════ 接下来 5 个问题请看画面，逐条回答 ════════")
    ask("B. 白色记号球现在的位置：在**灰块（父容器）那里**，还是在**画布正中间**？")
    ask("   （在父容器那里 = 子控件坐标是相对父的 ✓；在画布中间 = 相对 root）")
    ask("D. 马上给父容器转 " .. CFG.rot .. "°：**白球跟着转吗**？（灰块也会转）")
    go("Q_rot", dt)

  elseif ph == "Q_rot" then
    pcall(function() pA:SetLocalRotation(0, 0, CFG.rot) end)
    log(string.format("D 段：父容器已转 %g°，白球跟着转了吗？", CFG.rot))
    go("Q_rot_w", dt)

  elseif ph == "Q_rot_w" then
    if P.f >= frames(dt, CFG.wait) then
      pcall(function() pA:SetLocalRotation(0, 0, 0) end)
      pcall(function() pA:SetVisible(false) end)
      log("E 段：父容器已 SetVisible(false)，**白球（和灰块）消失了吗**？")
      go("Q_hide_w", dt)
    end

  elseif ph == "Q_hide_w" then
    if P.f >= frames(dt, CFG.wait) then
      pcall(function() pA:SetVisible(true) end)
      local pokF = pcall(function()
        pA.imageColor = Color.FromRGBA(120, 120, 130, 120)
      end)
      log("F 段：父控件 imageColor.alpha 已调到 120（调用是否成功：" .. tostring(pokF)
          .. "），**白球变淡了吗**？（灰块自己会变淡）")
      go("Q_alpha_w", dt)
    end

  elseif ph == "Q_alpha_w" then
    if P.f >= frames(dt, CFG.wait) then
      pcall(function() pA.imageColor = Color.FromRGBA(120, 120, 130, 255) end)
      local pokG = pcall(function() marker.parent = pB end)
      log("G 段：已把白球的 parent 改成右下角那个容器（调用是否成功：" .. tostring(pokG)
          .. "），**白球跑到右下角去了吗**？")
      go("Q_move_w", dt)
    end

  elseif ph == "Q_move_w" then
    if P.f >= frames(dt, CFG.wait) then
      log("════════ 探测汇总 ════════")
      log("A 容器实例化     : " .. tostring(res.prefab))
      log("C 单容器子控件数 : " .. (res.limit and ("上限约 " .. res.limit .. " 个")
                                         or ("至少 " .. #kids .. " 个（没撞到上限）")))
      log("B 坐标空间       : 见你肉眼回答")
      log("D 父旋转是否传递 : 见你肉眼回答")
      log("E 父显隐是否传递 : 见你肉眼回答")
      log("F 父 Alpha 传递  : 见你肉眼回答")
      log("G 运行期改父级   : 见你肉眼回答")
      log("把这份日志 + 那几句肉眼结论发回来，就能改成「父容器 + 骨骼层级」架构。")
      log("（预期收益：每帧写入从 866/3286 次降到几十次）")
      script:EnableUpdate(false)
    end
  end
end

function OnDestroy()
  local function kill(c) if c ~= nil and c.alive then game.DestroyClientUIControl(c) end end
  for _, c in ipairs(kids) do kill(c) end
  kill(marker); kill(pA); kill(pB)
end
