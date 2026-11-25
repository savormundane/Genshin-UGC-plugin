-- ============================================================================
-- 补间（Tween）探测脚本 —— 独立运行，不改动生产脚本
--
-- 为什么需要它：
--   `game.Tween(object, tweenDataTable, duration)` 的**签名**是确认的（PDF 与转录件一致），
--   我们要用的字段（anchoredPositionX/Y、sizeDeltaX/Y、localRotationZ、imageColor）
--   也都标了 Tweenable。**唯一缺的是 `tweenDataTable` 的格式**：
--   PDF 文字层里"创建"那节只有标题（表格是位图，而 Tween 那一页恰好缺失），
--   转录件只有签名，工具文档里也只有字段级标记。所以只能实机问。
--
-- 依次问 6 件事，每件打一行结论：
--   A. tweenDataTable 怎么写（试 5 种候选，哪种真的让控件动）
--   B. 循环 / 相对 / yoyo
--   C. 两段序列能否做出平滑往返（呼吸要的就是"出去再回来"）
--   D. object 能不能一次传一组控件
--   E. Kill 的语义
--   F. **谁在驱动补间**（最关键）：关掉逐帧回调后补间还跑不跑
--
-- 用法：填好 CFG 的两个 ID → 挂到有 GEIMG_Canvas 容器的场景 → 看 [TWEEN] 日志
--       （F 段需要你**看画面**回答一句）
-- ============================================================================

local CFG = {
  containerName = "GEIMG_Canvas",
  imagePrefabId = 1073741850,   -- 图片控件模板索引ID（用实机跑通的那个）
  circleAssetId = 100002,       -- 圆贴图资源ID

  baseX = -380, baseY = 60, step = 110, size = 80,
  hold = 0.8,    -- A 段每种格式的观察时长
  loops = 2.4,   -- B 段循环观察时长
  engine = 4.0,  -- F 段慢速补间的时长（便于肉眼观察）
}

local root, seq = nil, nil
local ctl, res = {}, {}
local N = 5                      -- A 段的候选个数
local function log(s) print("[TWEEN] " .. s) end
local function ok(s)  print("[TWEEN] ✅ " .. s) end
local function bad(s) print("[TWEEN] ❌ " .. s) end
local function tip(s) print("[TWEEN] ⚠️  " .. s) end

local function ensureRoot()
  if root ~= nil and root.alive then return true end
  if game.FindClientUIRoot ~= nil then
    local r = game.FindClientUIRoot(CFG.containerName)
    if r ~= nil then root = r; return true end
  end
  return false
end

local function mk(idx, color)
  local c = game.InstantiateClientUIControl(CFG.imagePrefabId, root)
  if c == nil then return nil end
  c:SetAnchorMin(0.5, 0.5); c:SetAnchorMax(0.5, 0.5); c:SetPivot(0.5, 0.5)
  c:SetSizeDelta(CFG.size, CFG.size)
  c:SetAnchoredPosition(CFG.baseX, CFG.baseY - (idx - 1) * CFG.step)
  c:SetImage(Enum.ImageSource.StaticReference, CFG.circleAssetId)
  c.imageType = Enum.ImageType.Stretch
  c.imageColor = Color.FromRGBA(color[1], color[2], color[3], 255)
  c:SetVisible(true)
  return c
end

local function gx(c) return c ~= nil and c.anchoredPositionX or nil end
local function gy(c) return c ~= nil and c.anchoredPositionY or nil end
local function frames(dt, seconds) return math.max(1, math.floor(seconds / dt + 0.5)) end

-- 起一个补间；失败时把原因写进 res[tag]
local function start(obj, data, dur, tag)
  local pok, t = pcall(function() return game.Tween(obj, data, dur) end)
  if not pok then res[tag] = "抛异常：" .. tostring(t); return nil end
  if t == nil then res[tag] = "返回 nil"; return nil end
  pcall(function() t:SetEase(Enum.EaseType.Linear) end)
  pcall(function() t:Play() end)
  return t
end

-- ── A 段候选：每个都是"给定目标 x，产出 tweenDataTable"的函数 ──────────
local TX = CFG.baseX + 220
local CAND = {
  { "① {x=…, y=…}",                    function(tx) return { x = tx, y = CFG.baseY } end },
  { "② {anchoredPositionX=…, …Y=…}",  function(tx) return { anchoredPositionX = tx, anchoredPositionY = CFG.baseY } end },
  { "③ {anchoredPosition={x, y}}",     function(tx) return { anchoredPosition = { tx, CFG.baseY } } end },
  { "④ {{field=\"anchoredPositionX\", to=…}}",
                                        function(tx) return { { field = "anchoredPositionX", to = tx } } end },
  { "⑤ {anchoredPositionX={to=…}}",    function(tx) return { anchoredPositionX = { to = tx } } end },
}

-- ── 阶段机 ────────────────────────────────────────────────────────────
local P = { ph = "boot", f = 0 }

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

  if ph == "boot" then
    for i = 1, N do
      ctl[i] = mk(i, { 90, 140, 220 })
      if ctl[i] == nil then
        bad("InstantiateClientUIControl 返回 nil：CFG.imagePrefabId 对吗？")
        script:EnableUpdate(false)
        return
      end
    end
    ctl.loop = mk(N + 1, { 220, 160, 90 })
    ctl.seq  = mk(N + 2, { 150, 220, 150 })
    log(string.format("建好 %d 个探测控件；A 段开始（tweenDataTable 写法）", N + 2))
    P.ph, P.f, P.i = "A_start", 0, 0

  -- ══ A ══
  elseif ph == "A_start" then
    P.i = P.i + 1
    if P.i > N then
      if res.mk == nil then
        bad("A 段 5 种写法全部无效。逐条失败原因见上；"
            .. "说明 tweenDataTable 是别的结构（需要未裁切的官方文档）")
        P.ph, P.f = "B_start", 0
      else
        ok("A 段命中：" .. res.formatA .. "（后续测试都用它）")
        P.ph, P.f = "B_start", 0
      end
      return
    end
    P.x0 = gx(ctl[P.i])
    P.tk = start(ctl[P.i], CAND[P.i][2](TX), CFG.hold, "A" .. P.i)
    log(string.format("A%d 试 %s", P.i, CAND[P.i][1]))
    P.ph, P.f = "A_wait", 0

  elseif ph == "A_wait" then
    if P.f >= frames(dt, CFG.hold) then
      local i, x0, x1 = P.i, P.x0, gx(ctl[P.i])
      if x1 ~= nil and x0 ~= nil and math.abs(x1 - x0) > 1 then
        ok(string.format("A%d %s → x %.1f → %.1f", i, CAND[i][1], x0, x1))
        if res.mk == nil then
          res.mk, res.formatA = CAND[i][2], CAND[i][1]
        end
      else
        bad(string.format("A%d %s → 没动（x=%s；%s）", i, CAND[i][1], tostring(x1),
            tostring(res["A" .. i] or "已调用但无效果")))
      end
      P.ph, P.f = "A_start", 0
    end

  -- ══ B：循环 / 相对 / yoyo ══
  elseif ph == "B_start" then
    if res.mk == nil then
      tip("B 段跳过（A 段未确定格式）"); P.ph, P.f = "C_start", 0; return
    end
    local c = ctl.loop
    P.b0 = gx(c)
    local t = start(c, { anchoredPositionX = 80 }, 0.4, "B")
    if t == nil then
      bad("B 段起补间失败：" .. tostring(res.B)); P.ph, P.f = "C_start", 0; return
    end
    res.relOK = pcall(function() t:SetRelative(true) end)
    res.loopOK = pcall(function() t:SetLoops(-1) end)
    P.btk = t                       -- 记下来，E 段之前要 Kill，否则它会一直给 x 加偏移
    local yoyoOK, yoyoErr = pcall(function() t:SetLoops(-1, 1) end)
    res.yoyo = yoyoOK
    log(string.format("B 段：SetRelative=%s  SetLoops(-1)=%s  第二参数(yoyo)=%s",
        tostring(res.relOK), tostring(res.loopOK),
        yoyoOK and "接受" or ("拒绝（" .. tostring(yoyoErr) .. "）")))
    P.ph, P.f = "B_wait", 0

  elseif ph == "B_wait" then
    if P.f >= frames(dt, CFG.loops) then
      local d = (gx(ctl.loop) or 0) - (P.b0 or 0)
      if d > 100 then
        ok(string.format("B 段循环生效：%.1fs 内 x 累计 %.1f（单周期只有 80）", CFG.loops, d))
      elseif d > 1 then
        tip(string.format("B 段：x 只走了 %.1f → 像只跑一轮，SetLoops(-1) 可能没生效", d))
      else
        bad("B 段：x 没变 → 「相对 + 循环」这条组合不通")
      end
      P.ph, P.f = "C_start", 0
    end

  -- ══ C：两段序列往返 ══
  elseif ph == "C_start" then
    if res.mk == nil then
      tip("C 段跳过"); P.ph, P.f = "D_start", 0; return
    end
    local c = ctl.seq
    P.c0 = gx(c) or 0
    local up = start(c, res.mk(P.c0 + 90), 0.5, "C_up")
    local dn = up ~= nil and start(c, res.mk(P.c0), 0.5, "C_dn") or nil
    if up == nil or dn == nil then
      bad("C 段：序列里的补间起不来 → " .. tostring(res.C_up or res.C_dn))
      P.ph, P.f = "D_start", 0; return
    end
    local sok, s = pcall(function()
      local q = game.TweenSequence()
      q:Append(up); q:Append(dn); q:SetLoops(-1); q:Play()
      return q
    end)
    res.seqOK = sok
    if not sok then
      bad("C 段：TweenSequence 不可用 → " .. tostring(s))
    else
      seq = s
      log("C 段：已建『出去→回来』两段序列并 SetLoops(-1)，看 x 是否来回")
    end
    P.ph, P.f, P.samp = "C_wait", 0, {}

  elseif ph == "C_wait" then
    if P.f % 12 == 0 then P.samp[#P.samp + 1] = gx(ctl.seq) end
    if P.f >= frames(dt, 2.0) then
      local mn, mx = math.huge, -math.huge
      for _, v in ipairs(P.samp) do
        if v ~= nil then mn = math.min(mn, v); mx = math.max(mx, v) end
      end
      if mx > mn + 20 then
        ok(string.format("C 段往返生效：x 在 %.1f ~ %.1f 摆动（峰峰 %.1f）", mn, mx, mx - mn))
      else
        bad(string.format("C 段：x 几乎没动（%.1f ~ %.1f）→ 序列循环不通", mn, mx))
      end
      P.ph, P.f = "D_start", 0
    end

  -- ══ D：一组控件 ══
  elseif ph == "D_start" then
    if res.mk == nil then
      tip("D 段跳过"); P.ph, P.f = "E_start", 0; return
    end
    P.dy = { gy(ctl[1]), gy(ctl[2]) }
    local pok = pcall(function()
      local tk = game.Tween({ ctl[1], ctl[2] }, { anchoredPositionY = CFG.baseY - 200 }, 0.6)
      if tk ~= nil then pcall(function() tk:Play() end) end
    end)
    res.arrayCall = pok
    log("D 段：试 game.Tween(控件数组, {anchoredPositionY=…})")
    P.ph, P.f = "D_wait", 0

  elseif ph == "D_wait" then
    if P.f >= frames(dt, 0.6) + 2 then
      local want = { CFG.baseY, CFG.baseY - CFG.step }
      local moved = 0
      for i = 1, 2 do
        local y = gy(ctl[i])
        if y ~= nil and math.abs(y - want[i]) > 1 then moved = moved + 1 end
      end
      if moved == 2 then
        ok("D 段：object 接受控件数组 → **一次补间驱动多个控件**（省负载的额外红利）")
      elseif moved == 1 then
        tip("D 段：只有第一个动了 → 传数组大概只取首个元素，不能靠它批量")
      else
        bad("D 段：数组形式无效（" .. (res.arrayCall and "没抛异常但没效果" or "抛了异常") .. "）")
      end
      P.ph, P.f = "E_start", 0
    end

  -- ══ E：Kill 语义（先清掉前面还在跑的东西，否则测不准）══
  elseif ph == "E_start" then
    if P.btk ~= nil then pcall(function() P.btk:Kill(false) end) end
    if seq ~= nil then pcall(function() seq:Kill(false) end); seq = nil end
    if res.mk == nil then
      tip("E 段跳过"); P.ph, P.f = "F_start", 0; return
    end
    local c = ctl[5]                 -- 用 A 段那个"已经跑完"的控件，避免和 B 的循环抢
    local t = start(c, res.mk((gx(c) or 0) + 300), 2.0, "E")
    if t == nil then
      tip("E 段起补间失败：" .. tostring(res.E)); P.ph, P.f = "F_start", 0; return
    end
    P.etk, P.e1, P.ectl = t, nil, c
    log("E 段：起 2 秒补间，0.4 秒后 Kill(false)，看是否立刻停住")
    P.ph, P.f = "E_kill", 0

  elseif ph == "E_kill" then
    if P.f >= frames(dt, 0.4) then
      pcall(function() P.etk:Kill(false) end)
      P.e1 = gx(P.ectl)
      P.ph, P.f = "E_wait", 0
    end

  elseif ph == "E_wait" then
    if P.f >= frames(dt, 1.5) then
      local now = gx(P.ectl)
      if now ~= nil and P.e1 ~= nil and math.abs(now - P.e1) < 1 then
        ok("E 段：Kill(false) 之后停住了（清理语义正常）")
      else
        bad("E 段：Kill 之后还在动 → 销毁控件前要自己 Kill，否则会继续跑")
      end
      P.ph, P.f = "F_start", 0
    end

  -- ══ F：谁在驱动（最关键；这一段之后就没有 OnUpdate 了）══
  elseif ph == "F_start" then
    log("════════ F 段：判断『谁在驱动补间』 ════════")
    log(string.format("马上起一个 %.1f 秒的慢速补间（橙色圆横向移动），然后关掉逐帧回调。", CFG.engine))
    log("请盯着那块橙色圆：")
    log(string.format("  · 它继续走完 %.1f 秒 → 补间由**引擎**驱动 ✅（这才是省负载的前提）", CFG.engine))
    log("  · 它立刻停住不动   → 补间靠脚本逐帧泵 ❌（省 Lua 代码，但省不掉调用）")
    local c = ctl.loop
    P.fx0 = gx(c)
    local t = start(c, res.mk ~= nil and res.mk(CFG.baseX + 520) or { anchoredPositionX = CFG.baseX + 520 },
                   CFG.engine, "F")
    if t == nil then
      bad("F 段起补间失败：" .. tostring(res.F) .. " → 无法判断驱动器")
      report()
      script:EnableUpdate(false)
      return
    end
    pcall(function()
      t:SetOnComplete(function()
        ok(string.format("F 段结论：逐帧回调关闭后补间仍然完成 → **引擎驱动**（x %.1f → %.1f）",
            P.fx0 or -1, gx(c) or -1))
      end)
    end)
    report()
    script:EnableUpdate(false)   -- ★ 关掉逐帧回调；之后靠你肉眼回答 F 段
  end
end

-- 汇总（在关掉逐帧回调之前打印）
function report()
  log("════════ 探测汇总 ════════")
  log("A tweenDataTable 可用写法 : " .. tostring(res.formatA or "未确定（5 种都无效）"))
  log("B SetRelative / SetLoops  : " .. tostring(res.relOK) .. " / " .. tostring(res.loopOK)
      .. "；yoyo 第二参数=" .. (res.yoyo and "接受" or "拒绝"))
  log("C TweenSequence           : " .. tostring(res.seqOK))
  log("D 控件数组                : " .. (res.arrayCall and "调用未抛异常" or "抛异常"))
  log("E Kill 语义               : 见上面 E 段那行")
  log("F 驱动器                  : 见上面 F 段那行（或你肉眼看到的结果）")
  log("把这整份日志发回来，我就能把呼吸改成引擎补间驱动（预期：空转写入降到 0）")
end

function OnDestroy()
  for _, c in pairs(ctl) do
    if c ~= nil and c.alive then game.DestroyClientUIControl(c) end
  end
  ctl = {}
  if seq ~= nil then pcall(function() seq:Kill(false) end) end
end
