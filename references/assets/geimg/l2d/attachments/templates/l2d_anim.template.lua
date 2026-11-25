-- ============================================================================
-- GEIMG 图元动画 · 自包含 Lua
--
-- 做什么：把拟合出的图元用图片控件铺出来，然后**在游戏内驱动动画** ——
--         呼吸 / 眨眼 / 视点跟随鼠标 / 连续动作通道 / 一次性动作。
--
-- 数据内联：沙箱禁了 io.*，读不了外部文件，所以图元数据直接写在源文件里。
--
-- 坐标（两套参考系差半个画布，混用会让整个角色窜到画面一角，已实测踩过）：
--   源图像素 --(CFG 映射)--> 画布空间（左下原点、Y 向上）
--            --(减容器中心，见 CENTER)--> anchoredPosition（控件用「容器中心原点」）
--
-- 接口按可用实例 beyond_api.lua 校准：
--   · Script:EnableUpdate(enabled)      旧文档写的 EnableTick 已改名
--   · game.GetCursorUIPos()             左下原点，用前要减容器中心
--   · game.InstantiateClientUIControl(uiPrefabId, parent)
--   · 基类没有 alpha / zIndex：透明度走 imageColor，层序走 SetSiblingIndex
-- ============================================================================

__CFG__

-- 图元："t|x|y|w|h|rotDeg|rrggbbaa"（源图像素）
--   t: c=circle / e=ellipse / l=line；rotDeg 已是 Lua 侧角度（画布 Y 翻转后的）
--   数组顺序 = 绘制顺序（1 在最底层）
local RAW = {
__RAW__
}

-- 部件表：f/t = 图元下标区间（含），px/py = 旋转轴心，w/delay/rot = 呼吸参数，
--   g = 组索引（见 GN），n = 部件编号
--   带 role 的部件另有 role / side / geo（geo={top,bot,lidCy,cy}，嘴只有 cy）
--   role 取值：iris（虹膜，可随视点滑动）/ eye（眼白，随眨眼压缩淡出）/ lid（睫毛眼线）
--               / brow（眉毛）/ mouth（嘴）
local PARTS = {
__PARTS__
}
local GN = {"head","bangs","hairBack","tailL","tailR","ribbon","body","armL","armR","legs"}

-- ============================ 动画参数 ============================

local TAU, RAD = math.pi * 2, math.pi / 180

-- 连续通道：T=周期秒；dx/dy/rot=基础幅度（源图像素 / 度）；g=按组权重；
--   p=按部件编号定向（如摆臂只动某部件）；lag=true 时叠加该部件自身的 delay；
--   pivot=绕该全局点旋转（位移由部件轴心转过后算出，靠近轴心的部件几乎不动）
local CH = {
  sway = { T=5.2, rot=0.7, lag=true, pivot={205,588},
           g={ head=1, bangs=1.05, hairBack=1.2, tailL=1.3, tailR=1.3, ribbon=1.35,
               body=1, armL=0.85, armR=0.85, legs=0.3 } },
  turn = { T=7.6, dx=2.2, rot=0.4, lag=true, d0=0.05,
           g={ head=1, bangs=1, hairBack=0.3, tailL=0.12, tailR=0.12, ribbon=0.1, body=0.05 } },
  nod  = { T=6.4, dy=1.0, rot=0.5, lag=true,
           g={ head=1, bangs=1, hairBack=0.35, tailL=0.15, tailR=0.15, ribbon=0.12, body=0.08 } },
  wind = { T=3.1, dx=3.0, dy=0.8, rot=1.8, lag=true,
           g={ head=0.15, bangs=1, hairBack=1.15, tailL=1.2, tailR=1.2, ribbon=1.25,
               body=0.1, armL=0.1, armR=0.1 } },
  armR = { T=2.4, rot=5, p={ __ARMR_PARTS__ } },
}

-- 视点跟随：按组权重，软物用滞后值
-- 注意：实心部位（腿/身体/手臂）给**同一个值**，否则相邻图层会错开露出缝；
-- 头发/发尾/飘带可以更大——它们本来就是软物，也是"活气"的来源
-- 头部各组给 0：头的方向感全部交给柱面形变，避免"平移 + 形变"叠加成滑动
local GAZE_W = { head=0, bangs=0, hairBack=0, tailL=0, tailR=0,
                 ribbon=1.40, body=0.35, armL=0.35, armR=0.35, legs=0 }   -- 腿给 0：脚要钉在地上
local GAZE_LAG = { bangs=true, hairBack=true, tailL=true, tailR=true, ribbon=true }
-- 实测对照：期望效果里上半身水平位移只有 1px、下半身 0px，生命感来自发丝内部摆动。
-- 所以视点只给很小的头部位移（眼球才是看方向的主动作），身体几乎不参与。
-- 视点 = 头部柱面绕（主要）+ 虹膜（眼球）+ 身体极小的倾角。
-- 头部**不做整体平移** —— 平移是"滑动"，柱面绕才是"转头"。
local GAZE = {
  -- 柱面绕分两项：
  --   ① 压缩项 w·(cosθ−1)：让远端收窄、轮廓边缘几乎不动（θ 是名义转角）
  --   ② 摆幅项 (z/R)·swing：正前方摆得最多，向后按深度衰减 → 层间视差
  -- 两者解耦是因为"头部半宽"(157px, 含头发) 和"前后深度"(约一半) 不是一回事，
  -- 用同一个半径会让摆幅直接爆掉（实测会到 35~50px）。
  yaw=7.0, pitch=5.0,        -- 压缩项的名义角度（度）
  swing=6.0, swingY=4.0,     -- 正前方的最大水平/竖直摆幅（源像素）
  dx=0, dy=0, rot=0,         -- 头的整体平移：保持 0（旧版是 7px，那才是"漂浮木偶"的来源）
  leanRot=0.12, leanPivot={205,588},
  -- 绕脚底倾角只作用于"腰以上"：腿的轴心在髋部（离脚底 196px），跟着倾会平移半像素，
  -- 把脚也带跑。实测期望效果的脚是 0.00px，所以腿整组跳过倾角。
  -- 注：身体转动已改走下面的 BONE 连续场，leanRot 只在 BONE 关闭时当旧路径用。
  leanSkip = { legs = true },
}

-- ============================ 骨骼 ============================
-- 三套骨骼都是**连续位移场**，不是"按部件给权重"。
-- 为什么：相邻部件的变换不一致就一定开缝 —— 上一版身体转 1.6°、腿只转 0.48°，
-- 在 200px 力臂上就是 4px 裂缝（腰部被撕开过）。位移场是 (x,y) 的连续函数，
-- 相邻图元拿到的位移只差一点点，部件边界这个概念在算法里直接消失。
local BONE = {
  on = true,
  -- ① 躯干扭转：从脚底到脖子线性增强的水平位移。脚底 s=0 ⇒ 自动钉住
  bodyAmp = 6.0,             -- 胸口处的最大水平位移（源像素）
  depthK  = 0.25,            -- 伪深度：近侧多走一点，轮廓有轻微压缩 → 立体感
  tiltK   = 0.10,            -- 竖向歪斜（可关：0）
  -- ② 手臂骨：绕肩旋转，转角随"离肩距离"增长 → 读成肩→肘→手的分段弯
  armBend = 0.55,            -- 末端比根部多转的比例（0=整条刚性转，1=末端多转一倍）
  -- ③ 发丝骨：绕发根甩，越靠梢越晚越大幅度（跟随过冲）
  hairWhip = 0.85,
  headKeep = 0.25,           -- 头顶处躯干扭转残留的比例（脖子吸收掉剩下的 75%）
  yGround = __YGROUND__, yHip = __YHIP__, yNeck = __YNECK__, yTop = __YTOP__,
  cxTorso = __CXTORSO__, rxTorso = __RXTORSO__,
}

-- 躯干扭转斜坡。三段：
--   ① 髋线以下 = 0（腿脚钉住 —— 从脚底起坡会让大腿也平移 7px，实测过）
--   ② 髋线 → 脖子：0 → 1（胸口转得最多，"身体在转"就读出来了）
--   ③ 脖子 → 头顶：1 → headKeep（**脖子把大部分转角吃掉了**）
-- 第③段是关键：头本身已经有一整套柱面绕（内部形变），再叠加满幅整体平移就变成
-- "整颗头在横滑"——正是用户否掉的那个效果。让脖子吸收掉，头就只保留形变。
local function torsoRamp(y)
  if y >= BONE.yHip then return 0 end
  if y <= BONE.yNeck then
    local span2 = BONE.yNeck - BONE.yTop
    if span2 <= 1 then return BONE.headKeep end
    local t2 = (BONE.yNeck - y) / span2
    if t2 > 1 then t2 = 1 end
    return 1 + (BONE.headKeep - 1) * t2
  end
  local span = BONE.yHip - BONE.yNeck
  if span <= 1 then return 1 end
  return (BONE.yHip - y) / span
end

-- 躯干骨骼在 (x,y) 处的水平位移（源像素）。**垂直方向不动** —— 扭转不该把人拉高。
local function torsoDx(x, y, gx)
  if not BONE.on or gx == 0 then return 0 end
  local s = torsoRamp(y)
  if s <= 0 then return 0 end
  local d = 0
  if BONE.rxTorso > 1 then
    d = (x - BONE.cxTorso) / BONE.rxTorso
    if d < -1 then d = -1 elseif d > 1 then d = 1 end
  end
  return gx * BONE.bodyAmp * s * (1 + BONE.depthK * d)
end

-- 躯干骨骼的竖向分量（很轻的歪斜，避免"纯剪切的纸片感"）
local function torsoDy(x, y, gx)
  if not BONE.on or gx == 0 or BONE.tiltK == 0 then return 0 end
  local s = torsoRamp(y)
  if s <= 0 then return 0 end
  local d = 0
  if BONE.rxTorso > 1 then
    d = (x - BONE.cxTorso) / BONE.rxTorso
    if d < -1 then d = -1 elseif d > 1 then d = 1 end
  end
  return -gx * BONE.bodyAmp * BONE.depthK * BONE.tiltK * s * d
end

-- 虹膜可动范围（从原图 alpha 量出来的「整块都落在眼白∪睫毛∪眼线内」的极限）。
-- 引擎的 enableMask 是**矩形区域遮罩**（不是按图片 alpha 的 stencil），裁不出眼型，
-- 所以只能限幅 —— 代价是右视 / 下视虹膜基本不动，视点主要由头/身/发丝读出来。
local IRIS_SAFE = __IRIS_SAFE__

-- 一次性动作：dur 秒的包络（u=0..1），贡献叠加在连续通道之上
local function pulse(u, a, w)
  if u <= a or u >= a + w then return 0 end
  return math.max(0, math.min((u - a) / (0.25 * w), 1, (a + w - u) / (0.35 * w)))
end
local ACT = {
  shake    = { dur=1.15, ch={ turn = function(u) return 1.5 * math.sin(TAU*2.4*u) * math.sin(math.pi*u) end } },
  nodOnce  = { dur=1.05, ch={ nod  = function(u) return 1.8 * math.sin(TAU*2.0*u) * math.sin(math.pi*u) end } },
  surprise = { dur=1.6,  ch={ eyeOpen   = function(u) return 1.5 * pulse(u, 0.05, 0.34) end,
                              browRaise = function(u) return 1.5 * pulse(u, 0.05, 0.34) end,
                              nod       = function(u) return -1.6 * pulse(u, 0.05, 0.34) end } },
  wave     = { dur=1.8,  ch={ armR = function(u) return math.sin(TAU*2.6*u) * math.sin(math.pi*u) end } },
  -- 跳跃**不走正弦通道**：它有自己的关键帧轨迹（见 JUMP_KEYS），所以 ch 留空。
  -- 留空是安全的：channelOf 遍历 ACT[...].ch[name] 拿不到东西就等于不加贡献。
  jump     = { dur=1.35, ch={} },
}

-- 通道清单：每帧按这份清单重算有效值，**CFG.ch 里没写到的通道必须归零**。
-- 不能改成"遍历 CFG.ch"——那样切预设会留下上一套的值（实测：talk → allOff 之后 chTalk 还是 1，
-- 因为 allOff 把 CFG.ch 换成了空表，遍历等于什么都没做，chv 里的旧值就挂在那儿了）。
local CHANNELS = { "sway", "turn", "nod", "wind", "armR", "talk", "eyeOpen", "browRaise" }

-- 预设：一次改一批通道开关（blink/gaze 是开关而非通道）
local PRESET = {
  idle     = {},
  swayIdle = { sway=1 },
  talk     = { nod=0.7 },        -- 嘴已改静态，这个预设现在只做轻微点头
  wind     = { wind=1, sway=0.8 },
  smile    = { eyeOpen=-1 },
  allOff   = { blink=0, gaze=0 },
}

-- ============================ 运行时状态 ============================

local pool = {}          -- pool[i] = 第 i 个图元的控件
local shapes = {}        -- shapes[i] = {x,y,w,h,rd,r,g,b,a}
local total = 0
local cursor, done = 1, false
local root = nil
local preplaced = nil
local warned = {}

local t, bt = 0, 0       -- t=动画时钟；bt=眨眼时钟（独立，不受动画时钟跳变影响）
local acc = 0            -- 按 stride 累积的 dt
local chv = {}           -- 各通道当前有效值（开关 × 强度）
local acts = {}          -- 正在播的一次性动作 {{n=名, t0=起始}}
local blink = { next = 1.6, events = {}, vL = 0, vR = 0, count = 0, faded = false }
local gaze = { tx=0, ty=0, x=0, y=0, lagX=0, lagY=0 }
local CX, CY             -- 容器中心
local frames, firstMs = 0, -1
local rootFails = 0        -- 连续找不到容器的帧数（超限就停掉逐帧回调，别做哑巴脚本）
local writes, wFrames = 0, 0   -- 累计 API 写入次数 / 统计帧数（负载画像）
local lastWrites = 0           -- 最近一帧的写入次数（GetStatus 里看）
local lastGX, lastGY = 9e9, 9e9  -- 上次写骨骼场时的视点（用来判断"视点没动就别写"）
local uiBuilt = false          -- UI 是否已建（容器可能晚于 OnStart 才就绪）

-- 头部件组：这些部件要绕头部柱面做内部形变
local HEAD_GROUPS = { head=true, bangs=true, hairBack=true, tailL=true, tailR=true }
local HEAD = { hx=0, hy=0, rx=0, ry=0, ready=false }

-- 骨骼分组的成员：手臂绕肩弯、发丝/飘带绕根甩
local ARM_GROUPS = { armL=true, armR=true }
local HAIR_GROUPS = { bangs=true, hairBack=true, tailL=true, tailR=true, ribbon=true }

-- 层间深度系数：五官在球面前方（摆得多），后发/发尾在后（摆得少）→ 层间视差
local function wrapK(p)
  local r = p.role
  if r == "iris" then return 1.30 end
  if r == "eye" or r == "lid" or r == "brow" then return 1.14 end
  if r == "mouth" then return 1.10 end
  local g = GN[p.g]
  if g == "hairBack" then return 0.85 end
  if g == "tailL" or g == "tailR" then return 0.80 end
  if g == "bangs" then return 1.05 end
  return 1.0
end

local function warnOnce(key, msg)
  if warned[key] then return end
  warned[key] = true
  print("[GEIMG] " .. msg)
end

-- 关掉逐帧回调。接口改过名（旧文档 EnableTick，运行时 EnableUpdate），两个都试一遍。
local function stopTick()
  if script.EnableUpdate ~= nil then
    script:EnableUpdate(false)
  elseif script.EnableTick ~= nil then
    script:EnableTick(false)
  else
    warnOnce("noStopTick", "script 上既没有 EnableUpdate 也没有 EnableTick，关不掉逐帧回调")
  end
end

-- 打开逐帧回调。**必须自己开**：脚本的 update 开关默认是关的，
-- 不显式打开的话 OnUpdate 一帧都不会被调用 —— 图元铺不出来、动画更不会动。
local function startTick()
  if script.EnableUpdate ~= nil then
    script:EnableUpdate(true)
    return true
  elseif script.EnableTick ~= nil then
    script:EnableTick(true)
    return true
  end
  warnOnce("noStartTick", "script 上既没有 EnableUpdate 也没有 EnableTick，无法开启逐帧回调")
  return false
end

-- 容器中心：控件用「容器中心原点」，画布空间用「左下原点」，相差半个画布
local function resolveCenter()
  local w, h = CFG.canvasW or 1600, CFG.canvasH or 900
  if game.GetUICanvasSize ~= nil then
    local gw, gh = game.GetUICanvasSize()
    if gw ~= nil and gw > 0 and gh ~= nil and gh > 0 then w, h = gw, gh end
  end
  CX = CFG.centerX or (w * 0.5)
  CY = CFG.centerY or (h * 0.5)
  print(string.format("[GEIMG] 画布 %gx%g，容器中心 (%g, %g)", w, h, CX, CY))
end

-- 找父节点：优先用有文档保证的按名查找（FindClientUIRoot 返回的就是控件）；
-- script.object 的类型是 any，值可能不是控件，只能当回退，并且要自己沿 parent 向上找。
-- 两条路都没找到同名容器时返回 false：宁可"什么都不铺 + 打日志"，也不要往一个来路不明的对象里
-- 灌图元（宿主不是控件时 SetSiblingIndex 之类会直接报错，而日志落在 ErrorLog.txt 里，
-- 游戏里只表现为"没反应"）。
local function ensureRoot()
  if root ~= nil and root.alive then return true end
  if CFG.containerName ~= nil and CFG.containerName ~= "" and game.FindClientUIRoot ~= nil then
    local r = game.FindClientUIRoot(CFG.containerName)
    if r ~= nil then root = r; return true end
  end
  local node = script.object
  if node == nil then
    warnOnce("noObject", "找不到脚本宿主对象，也找不到名为 " .. tostring(CFG.containerName) .. " 的 UI 根")
    return false
  end
  if CFG.containerName == nil or CFG.containerName == "" then root = node; return true end
  local p, guard = node, 0
  while p ~= nil and p.name ~= CFG.containerName and guard < 32 do
    p = p.parent; guard = guard + 1        -- guard 防 parent 成环
  end
  if p == nil then
    warnOnce("noContainer", "没找到名为 " .. tostring(CFG.containerName) .. " 的容器：脚本宿主既不是它，"
                          .. "也没有这个祖先。请核对 CFG.containerName 与编辑器里的容器名")
    return false
  end
  root = p
  return true
end

-- 解析一行图元数据
local function decode(row)
  local tt, x, y, w, h, rot, hex =
    string.match(row, "^(%a+)|([^|]+)|([^|]+)|([^|]+)|([^|]+)|([^|]+)|(%x+)$")
  if tt == nil then return nil end
  local c = tonumber(hex, 16)
  local a = c % 256
  if CFG.alphaMax < 255 then a = math.floor(a * CFG.alphaMax / 255) end
  return {
    x = tonumber(x), y = tonumber(y), w = tonumber(w), h = tonumber(h),
    rd = tonumber(rot),
    r = math.floor(c / 16777216) % 256,
    g = math.floor(c / 65536) % 256,
    b = math.floor(c / 256) % 256,
    a = a,
  }
end

-- 头部柱面：用头部件组的并集 bbox 定中心与半径（一次算好，动画每帧复用）
local function prepareWrap()
  local x0, y0, x1, y1 = 1e9, 1e9, -1e9, -1e9
  for i = 1, #PARTS do
    local p = PARTS[i]
    if HEAD_GROUPS[GN[p.g]] then
      p.wrap = true
      p.kw = wrapK(p)
      for j = p.f, p.t do
        local sh = shapes[j]
        if sh ~= nil then
          if sh.x < x0 then x0 = sh.x end
          if sh.x > x1 then x1 = sh.x end
          if sh.y < y0 then y0 = sh.y end
          if sh.y > y1 then y1 = sh.y end
        end
      end
    end
  end
  if x1 < x0 then return end
  HEAD.hx, HEAD.hy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
  HEAD.rx, HEAD.ry = (x1 - x0) * 0.5, (y1 - y0) * 0.5
  HEAD.ready = true
  print(string.format("[GEIMG] 头部柱面：中心 (%.0f, %.0f) 半径 (%.0f, %.0f)",
                      HEAD.hx, HEAD.hy, HEAD.rx, HEAD.ry))
end

-- 骨骼预备（一次算好，动画每帧复用）：
--   · 每个部件吃不吃得到躯干扭转场（脚底以下 ramp 恒为 0 → 一帧都不用写）
--   · 手臂/发丝每个图元的**归一化离轴距离** t∈[0,1]，作为弯曲参数
-- t 只在加载时算一次 —— 它是几何量，与动画无关。放进每帧循环就是白烧 CPU。
local function prepareBones()
  local frozen = 0
  for i = 1, #PARTS do
    local p = PARTS[i]
    local g = GN[p.g]
    local rmax = 0
    for j = p.f, p.t do
      local sh = shapes[j]
      if sh ~= nil then
        local r = torsoRamp(sh.y)
        if r > rmax then rmax = r end
      end
    end
    p.rmax = rmax
    p.noTorso = (rmax <= 0)
    if p.noTorso then frozen = frozen + 1 end

    if ARM_GROUPS[g] or HAIR_GROUPS[g] then
      local dmax = 0
      for j = p.f, p.t do
        local sh = shapes[j]
        if sh ~= nil then
          local ax, ay = sh.x - p.px, sh.y - p.py
          local d = math.sqrt(ax * ax + ay * ay)
          if d > dmax then dmax = d end
        end
      end
      if dmax > 1 then                    -- 轴心离形状太近就不做弯曲（会抖）
        for j = p.f, p.t do
          local sh = shapes[j]
          if sh ~= nil then
            local ax, ay = sh.x - p.px, sh.y - p.py
            sh.t = math.sqrt(ax * ax + ay * ay) / dmax
          end
        end
        p.bone = ARM_GROUPS[g] and "arm" or "hair"
        p.blen = dmax
      end
    end
  end
  print(string.format("[GEIMG] 骨骼：躯干场 脚底 y=%g 脖子 y=%g（%d 个部件完全冻结）",
                      BONE.yGround, BONE.yNeck, frozen))
end

-- ============================ 跳跃 ============================
-- 来自别人**实机测试**后加进来的版本，这里按原样收进生成器（连同它的标定值）。
-- 与其它动作的区别：不走正弦通道，而是走一条**关键帧轨迹**，因为跳跃的节奏
-- （下蹲→蹬地→腾空→落地缓冲）不是正弦能表达的。
--
-- 骨骼锚点按源坐标 Y 向下标定（实测调出来的）：
--   髋 392 → 膝 480 → 踝 560，角色中线 x=218。
-- 权重用法：
--   jHip  = 髋部以下渐弱（越往下越不跟着下蹲），脚踝以下≈0 → 脚只跟根位移走
--   jKnee = 膝部权重，用来把小腿沿 x 向外撑开（下蹲时膝盖外张）
--   jSide = 相对中线的横向归一化，决定"往外撑"的方向
-- 绘制顺序不动：软蒙皮是跨图层的，按骨骼重新分父节点会把遮挡关系打乱。
local JUMP_RIG = { hipY = __JUMPHIP__, kneeY = __JUMPKNEE__, ankleY = __JUMPANKLE__,
                   centerX = __JUMPCX__ }
local jump = { active=false, age=0, height=0, crouch=0, arms=0, hair=0 }
-- 每行 = {秒, 下蹲系数, 摆臂系数, 发梢滞后系数}；三次平滑插值
-- （腾空高度不在这张表里，它是一条单独的抛物线，见 tickJump）
local JUMP_KEYS = {
  {0,     0,    0,     0},
  {0.22,  1,   -0.35,  0.2},
  {0.32,  0,    0.8,   0.6},
  {0.48,  0.25, 1,    -0.65},
  {0.60,  0.45, 0.8,  -1},
  {0.84,  0,    0.3,   0.5},
  {0.96,  0.75,-0.2,   1},
  {1.12, -0.12, 0.1,  -0.3},
  {1.35,  0,    0,     0},
}

local function jumpSample(age, col)
  if age <= 0 or age >= ACT.jump.dur then return 0 end
  for i = 2, #JUMP_KEYS do
    local a, b = JUMP_KEYS[i-1], JUMP_KEYS[i]
    if age <= b[1] then
      local u = (age - a[1]) / (b[1] - a[1])
      u = u * u * (3 - 2 * u)                 -- smoothstep：避免关键帧处速度突变
      return a[col] + (b[col] - a[col]) * u
    end
  end
  return 0
end

-- 每个图元预计算跳跃权重（几何量，只在加载时算一次）
local function prepareJump()
  for _, p in ipairs(PARTS) do
    p.jumpWasActive = false
    for i = p.f, p.t do
      local s = shapes[i]
      if s then
        local q = math.max(0, math.min(1, (s.y - JUMP_RIG.hipY) / (JUMP_RIG.ankleY - JUMP_RIG.hipY)))
        s.jHip = 1 - q * q * (3 - 2 * q)
        local ky = s.y <= JUMP_RIG.kneeY
          and (s.y - JUMP_RIG.hipY) / (JUMP_RIG.kneeY - JUMP_RIG.hipY)
          or (1 + (s.y - JUMP_RIG.kneeY) / (JUMP_RIG.ankleY - JUMP_RIG.kneeY))
        s.jKnee = math.sin(math.pi * 0.5 * math.max(0, math.min(2, ky))) ^ 2
        s.jSide = math.max(-1, math.min(1, (s.x - JUMP_RIG.centerX) / 22))
      end
    end
  end
end

-- 本帧的跳跃状态：从正在播的动作里找 jump，采样轨迹
local function tickJump()
  jump.active = false
  jump.height, jump.crouch, jump.arms, jump.hair = 0, 0, 0, 0
  for _, a in ipairs(acts) do
    if a.n == "jump" then
      local age = t - a.t0
      jump.active = age >= 0 and age < ACT.jump.dur
      jump.age = age
      local k = CFG.motionScale or 1
      jump.crouch = jumpSample(age, 2) * k
      jump.arms   = jumpSample(age, 3) * CFG.jump.arm * k
      jump.hair   = jumpSample(age, 4) * CFG.jump.hair * k
      -- 腾空段单独给一条抛物线：0.32s 起跳、0.84s 落地
      if age > 0.32 and age < 0.84 then
        local u = (age - 0.32) / 0.52
        jump.height = 4 * CFG.jump.height * u * (1 - u) * k
      end
      break
    end
  end
end

-- 源图像素 → anchoredPosition（含减容器中心）
local function place(c, sx, sy)
  c:SetAnchoredPosition(CFG.offsetX + sx * CFG.scale - CX,
                        CFG.offsetY + (CFG.sourceHeight - sy) * CFG.scale - CY)
end

local function spawn(d, index)
  local c
  if CFG.strategy == "pool" then
    if preplaced == nil then
      preplaced = root:GetChildren() or {}
      if #preplaced < total then
        warnOnce("poolShort", "容器里只找到 " .. #preplaced .. " 个子控件，需要 " .. total
                              .. " 个：把预摆数量调大，或把 strategy 改成 instantiate")
      end
    end
    c = preplaced[index]
    if c == nil then return nil end
  else
    c = game.InstantiateClientUIControl(CFG.imagePrefabId, root)
    if c == nil then
      warnOnce("instantiateFail", "实例化失败：imagePrefabId 填对了吗？")
      return nil
    end
  end
  c:SetAnchorMin(0.5, 0.5)
  c:SetAnchorMax(0.5, 0.5)
  c:SetPivot(0.5, 0.5)
  place(c, d.x, d.y)
  c:SetSizeDelta(d.w * CFG.scale, d.h * CFG.scale)
  if d.rd ~= 0 then c:SetLocalRotation(0, 0, d.rd) end
  c:SetImage(Enum.ImageSource.StaticReference, CFG.circleAssetId)
  c.imageType = Enum.ImageType.Stretch
  c.imageColor = Color.FromRGBA(d.r, d.g, d.b, d.a)
  c:SetVisible(true)
  -- 会返回 boolean，且"受父控件子控件数限制"——失败就是层序静默错乱，必须出声
  if c.SetSiblingIndex ~= nil then
    local ok = c:SetSiblingIndex(index - 1)
    if ok == false then
      warnOnce("siblingFail", "设置同级索引失败（index=" .. (index - 1)
                            .. "）：层序可能与数据顺序不一致，检查容器的子控件数量")
    end
  end
  return c
end

-- ============================ 动画 ============================

-- 通道有效值 = 连续开关 × 强度 + 正在播的一次性动作
local function channelOf(name)
  local v = chv[name] or 0
  for i = 1, #acts do
    local a = acts[i]
    local f = ACT[a.n].ch[name]
    if f ~= nil then
      local u = (t - a.t0) / ACT[a.n].dur
      if u >= 0 and u <= 1 then v = v + f(u) end
    end
  end
  return v
end

-- 眨眼：快闭慢睁；按 skew 给左右眼一点相位差
local function tickBlink(dt)
  bt = bt + dt
  local keep = {}
  for i = 1, #blink.events do
    if bt - blink.events[i] < CFG.blink.dur + 0.3 then keep[#keep+1] = blink.events[i] end
  end
  blink.events = keep
  if CFG.blink.auto and bt >= blink.next then
    blink.events[#blink.events+1] = bt
    if math.random() < CFG.blink.doubleChance then
      blink.events[#blink.events+1] = bt + CFG.blink.dur + 0.085
    end
    blink.count = blink.count + 1
    blink.next = bt + CFG.blink.gapMin
               + math.random() * math.max(0, CFG.blink.gapMax - CFG.blink.gapMin)
  end
  local function at(skew)
    local v = 0
    for i = 1, #blink.events do
      local u = (bt - blink.events[i] - skew) / CFG.blink.dur
      if u > 0 and u < 1 then
        local p
        if u < 0.4 then p = 0.5 - 0.5 * math.cos(math.pi * u / 0.4)
        else p = 0.5 + 0.5 * math.cos(math.pi * (u - 0.4) / 0.6) end
        if p > v then v = p end
      end
    end
    return v
  end
  local manual = CFG.blink.hold and 1 or CFG.blink.manual
  blink.vL = math.max(at(0), manual)
  blink.vR = math.max(at(CFG.blink.skewMs / 1000), manual)
end

-- 视点：轮询光标 → 减容器中心 → 归一化 → 快慢两条平滑（发丝用慢的）
local function tickGaze(dt)
  if CFG.gaze and game.GetCursorUIPos ~= nil then
    local px, py = game.GetCursorUIPos()
    if px ~= nil and py ~= nil then
      local nx, ny = (px - CX) / CX, (py - CY) / CY
      local m = math.sqrt(nx * nx + ny * ny)
      if m > 1 then nx, ny = nx / m, ny / m end
      gaze.tx, gaze.ty = nx, ny
    end
  else
    gaze.tx, gaze.ty = 0, 0
  end
  local k = math.min(1, dt * 9)
  local kl = math.min(1, dt * 4)
  gaze.x = gaze.x + (gaze.tx - gaze.x) * k
  gaze.y = gaze.y + (gaze.ty - gaze.y) * k
  gaze.lagX = gaze.lagX + (gaze.x - gaze.lagX) * kl
  gaze.lagY = gaze.lagY + (gaze.y - gaze.lagY) * kl
end

-- 某部件本帧的 (dx, dy, rot)：源图像素 / 度。
-- 额外返回 dynRot：**动态**转动（通道+视点，不含呼吸）—— 手臂/发丝骨骼按它做二次反向，
-- 呼吸是整体的慢起伏，不该当成甩动的驱动。
local function partMotion(p)
  local gname = GN[p.g]
  local dx, dy, rot = 0, 0, 0
  local dynRot = 0

  -- 呼吸
  local vB = math.sin(TAU * (t - (p.delay or 0)) / CFG.period)
  dy = dy - CFG.baseAmp * CFG.ampScale * p.w * vB
  rot = rot + (p.rot or 0) * vB

  -- 连续通道 + 一次性动作
  for name, ch in pairs(CH) do
    local amp = channelOf(name)
    if amp ~= 0 then
      local w
      if ch.p ~= nil then w = ch.p[p.n] or 0
      else w = (ch.g and ch.g[gname]) or 0 end
      if w ~= 0 then
        local d = ((ch.lag and p.delay) or 0) + (ch.d0 or 0)
        local v = math.sin(TAU * (t - d) / ch.T)
        if ch.pivot ~= nil then
          local deg = amp * w * (ch.rot or 0) * v
          local th = deg * RAD
          local c, s = math.cos(th), math.sin(th)
          local rx, ry = p.px - ch.pivot[1], p.py - ch.pivot[2]
          dx = dx + (rx * c - ry * s - rx)
          dy = dy + (rx * s + ry * c - ry)
          rot = rot + deg
          dynRot = dynRot + deg
        else
          dx = dx + amp * w * (ch.dx or 0) * v
          dy = dy + amp * w * (ch.dy or 0) * v
          rot = rot + amp * w * (ch.rot or 0) * v
          dynRot = dynRot + amp * w * (ch.rot or 0) * v
        end
      end
    end
  end

  -- 视点跟随：只保留发丝/飘带那一层滞后权重（实心部位交给下面的骨骼场）
  if CFG.gaze then
    local w = GAZE_W[gname] or 0
    if w ~= 0 then
      local gx = GAZE_LAG[gname] and gaze.lagX or gaze.x
      local gy = GAZE_LAG[gname] and gaze.lagY or gaze.y
      dx = dx + gx * w * GAZE.dx
      dy = dy + gy * w * GAZE.dy
      rot = rot + gx * w * GAZE.rot
      dynRot = dynRot + gx * w * GAZE.rot
    end
    -- BONE 关闭时的旧路径：绕脚底整体倾角
    if not BONE.on then
      local deg = (GAZE.leanSkip and GAZE.leanSkip[gname]) and 0 or (gaze.x * GAZE.leanRot)
      local th = deg * RAD
      local c, s = math.cos(th), math.sin(th)
      local rx, ry = p.px - GAZE.leanPivot[1], p.py - GAZE.leanPivot[2]
      dx = dx + (rx * c - ry * s - rx)
      dy = dy + (rx * s + ry * c - ry)
      rot = rot + deg
    end
  end
  -- 总幅度旋钮：一个数统调所有位移/旋转（先拿它找手感，再动单项）
  local k = CFG.motionScale or 1
  return dx * k, dy * k, rot * k, dynRot * k
end

-- 眼/眉/嘴的额外变换
local function faceExtra()
  local eo = channelOf("eyeOpen")
  local so = math.max(0.4, math.min(1.6, 1 + eo * 0.30))
  local talkOn = math.max(0, channelOf("talk"))
  local talk = 0
  if talkOn > 0 then
    talk = 0.62 * math.sin(TAU * t / 0.21) + 0.38 * math.sin(TAU * t / 0.34 + 1.7)
    talk = math.min(1, talkOn * math.max(0, talk))
  end
  return so, -channelOf("browRaise") * 4.2, talk
end

local function updatePart(p, so, browDy, talk, yaw, pitch, gChanged)
  local dx, dy, rot, dynRot = partMotion(p)
  local role = p.role
  local skip = CFG.skipBelow or 0
  -- 骨骼场这一帧动没动：视点没变 + 本体位移不到半个像素 → 整个部件一帧都不用写
  local boneQuiet = p.noTorso or (not gChanged) or (not CFG.gaze)
  -- 跳跃期间整个部件都不能被跳过；跳跃结束的那一帧还要**强制写一次**（eps=0），
  -- 否则最后一帧的位移小于 posEps 会被缓存吃掉，角色停在半空（实测踩过）
  local jumpDirty = jump.active or p.jumpWasActive
  local jumpRestore = p.jumpWasActive and not jump.active
  if not jumpDirty and role == nil and so == 1 and browDy == 0 and boneQuiet
     and math.abs(dx) <= skip and math.abs(dy) <= skip and math.abs(rot) <= 0.05 then
    return                                   -- 位移不到半个像素就不写，省一次 API 调用
  end

  -- 手臂 / 发丝的二次转动：越靠梢转得越多 → 读成肩→肘→手、发根→发梢的分段
  -- （只按振幅缩放，不做相位差；相位差留给 delay，两套一起上会互相打架）
  local extra = 0
  if p.bone == "arm" then extra = dynRot * BONE.armBend
  elseif p.bone == "hair" then extra = dynRot * BONE.hairWhip end

  -- 跳跃的整组转动：左右臂反向摆、发丝按中线分左右滞后甩
  local jrot = 0
  if jump.active then
    local group = GN[p.g]
    if group == "armL" then jrot = jump.arms
    elseif group == "armR" then jrot = -jump.arms
    elseif HAIR_GROUPS[group] then
      jrot = jump.hair * (p.px < JUMP_RIG.centerX and -1 or 1)
    end
  end
  local jca, jsa = math.cos(jrot * RAD), math.sin(jrot * RAD)
  local ca, sa = math.cos(rot * RAD), math.sin(rot * RAD)
  local cae, sae = math.cos((rot + extra) * RAD), math.sin((rot + extra) * RAD)
  -- 该部件的柱面绕参数（只有头部件需要）
  local wrap = p.wrap and HEAD.ready and (yaw ~= 0 or pitch ~= 0)
  local wa, wb, kca, ksa, kcb, ksb, wpx, wpy
  if wrap then
    wa = yaw * p.kw * RAD
    wb = pitch * p.kw * RAD
    kca, ksa = math.cos(wa), math.sin(wa)
    kcb, ksb = math.cos(wb), math.sin(wb)
    -- 摆幅项：正前方的最大位移（像素），按该层 k 与视点量缩放
    wpx = (GAZE.swing or 0) * p.kw * (CFG.gaze and gaze.x or 0) * (CFG.motionScale or 1)
    wpy = (GAZE.swingY or 0) * p.kw * (CFG.gaze and -gaze.y or 0) * (CFG.motionScale or 1)
  end
  -- 躯干扭转场：只跟 y 与视点有关，同一部件内逐图元求值（连续场 → 不会有缝）
  local tGx = (CFG.gaze and gaze.x or 0) * (CFG.motionScale or 1)
  local tOn = BONE.on and p.rmax > 0 and tGx ~= 0
  local v = 0
  if role == "iris" or role == "eye" or role == "lid" or role == "brow" then
    v = (p.side == "eyeL") and blink.vL or blink.vR
  end
  local sf = (role == "iris") and IRIS_SAFE[p.side] or nil
  local gx = sf and (gaze.x >= 0 and gaze.x * sf.r or gaze.x * sf.l) or 0
  local gy = sf and (gaze.y >= 0 and -gaze.y * sf.u or -gaze.y * sf.d) or 0
  -- gaze.y > 0 = 光标在角色**上方**（GetCursorUIPos 是左下原点、Y 向上），
  -- 所以向上看时虹膜要向上；而源图 Y 向下 → 取负号

  -- 淡出 / 还原按**部件**判定一次（放进图元循环里会被第一个图元清掉标志）
  local needFade, needRestore = false, false
  if role == "iris" or role == "eye" then
    if v > 0.002 then
      needFade = (CFG.blink.fade > 0)
    elseif p.wasFaded then
      needRestore = true
    end
  end

  for i = p.f, p.t do
    local s = shapes[i]
    local c = pool[i]
    if s ~= nil and c ~= nil and c.alive then
      local ox, oy = s.x - p.px, s.y - p.py
      -- 骨骼弯曲：转角随离轴心的距离增长，所以逐图元选 (ca,sa) 或带弯曲的那组
      local useBend = extra ~= 0 and (s.t or 0) > 0
      local cc, ss = ca, sa
      local bend = 0
      if useBend then
        bend = extra * s.t
        cc, ss = math.cos((rot + bend) * RAD), math.sin((rot + bend) * RAD)
      end
      local bx, by = 0, 0
      if tOn then
        bx = torsoDx(s.x, s.y, tGx)
        by = torsoDy(s.x, s.y, tGx)
      end
      local nx = p.px + dx + ox * cc - oy * ss + gx + bx
      local ny = p.py + dy + ox * ss + oy * cc + gy + by
      local nh = s.h
      local alpha = nil
      if wrap then
        -- ① 压缩：远端收窄、轮廓边缘几乎不动（不会和脖子/背景脱开）
        -- ② 摆幅：按深度 (z/R) 衰减，正前方最多；各层 k 不同 → 层间视差
        local w = s.x - HEAD.hx
        local zw = HEAD.rx * HEAD.rx - w * w
        local z = zw > 0 and math.sqrt(zw) or 0
        local u = s.y - HEAD.hy
        local zv = HEAD.ry * HEAD.ry - u * u
        local z2 = zv > 0 and math.sqrt(zv) or 0
        nx = nx + w * (kca - 1) + (z / HEAD.rx) * wpx
        ny = ny + u * (kcb - 1) + (z2 / HEAD.ry) * wpy
      end
      local needSize = (role ~= nil)        -- 带 role 的部件尺寸会变，每帧写（否则眨眼后会残留压缩）

      if role ~= nil then
        local e = p.geo
        if role == "iris" or role == "eye" or role == "lid" then
          local cy = e.cy
          local ty = e.top + CFG.blink.closeAt * (e.bot - e.top)
          if so ~= 1 then ny = cy + (ny - cy) * so end        -- 睁大 / 眯：绕眼睛中线
          if role == "lid" then
            if v > 0.002 then
              local lidOpen = cy + (e.lidCy - cy) * so
              ny = ny + v * (ty - lidOpen)                    -- 眼睑线落到闭合线
            end
          else
            if v > 0.002 then
              local sc = math.max(0.02, 1 - CFG.blink.maxClose * v)
              ny = ty + (ny - ty) * sc
              nh = math.max(0.5, nh * sc)
            end
            -- 淡出/还原按**部件**决定，不能按图元（写进循环会被第一个图元把标志清掉）
            if needFade then
              alpha = math.floor(s.a * math.max(0, 1 - CFG.blink.fade * v))
            elseif needRestore then
              alpha = s.a
            end
          end
        elseif role == "brow" then
          local ty = e.top + CFG.blink.closeAt * (e.bot - e.top)
          ny = ny + v * CFG.blink.browFollow * (ty - e.lidCy) + browDy
        end
        -- 嘴保持静态：按 talk 纵向张开会显得嘴唇很厚（用户反馈不好看），
        -- 所以这里不做任何形变，嘴只跟随头部运动与柱面形变
      end

      -- 跳跃放在**表情之后**：根位移要跟眼睛/睫毛/眉毛一起走，
      -- 否则眨眼时眼球留在原地、脸飞上去（顺序反了就会这样）
      if jump.active then
        if jrot ~= 0 then                       -- 整组转动（摆臂/甩发）
          local jx, jy = nx - p.px, ny - p.py
          nx = p.px + jx * jca - jy * jsa
          ny = p.py + jx * jsa + jy * jca
        end
        nx = nx + s.jSide * s.jKnee * CFG.jump.knee * jump.crouch   -- 膝盖外张
        ny = ny + s.jHip * CFG.jump.crouch * jump.crouch - jump.height
      end

      -- 写入缓存：与上次写下的位置差不到 posEps 就不调 API。
      -- 跳跃恢复帧把 eps 压到 0：必须精确写回原位，否则最后一帧的小位移
      -- 会被缓存吃掉，角色停在半空/半蹲（实测踩过）。
      local eps = jumpRestore and 0 or CFG.posEps
      local moved = (s.wx == nil) or (math.abs(nx - s.wx) > eps)
                    or (math.abs(ny - s.wy) > eps)
      if moved then
        place(c, nx, ny)
        s.wx, s.wy = nx, ny
        writes = writes + 1
      end
      if needSize or nh ~= s.h then c:SetSizeDelta(s.w * CFG.scale, nh * CFG.scale) end
      -- 旋转也逐图元缓存：相同角度不重复写（角度没变还写一次是纯浪费）
      local targetRot = s.rd - rot - (bend or 0) - jrot
      if s.wrot == nil or math.abs(targetRot - s.wrot) > 0.001 then
        c:SetLocalRotation(0, 0, targetRot)
        s.wrot = targetRot
      end
      if alpha ~= nil then
        c.imageColor = Color.FromRGBA(s.r, s.g, s.b, alpha)
      end
    end
  end
  p.gx, p.gy = gaze.x, gaze.y
  p.jumpWasActive = jump.active
  if needFade then p.wasFaded = true
  elseif needRestore then p.wasFaded = false end
end

-- ============================ 生命周期 ============================

function OnInit()
  math.randomseed(os.time())
end

function OnStart()
  shapes = {}
  for i = 1, #RAW do shapes[i] = decode(RAW[i]) end
  total = #RAW
  resolveCenter()
  prepareWrap()
  prepareBones()
  prepareJump()
  cursor, done, t, bt, acc = 1, false, 0, 0, 0
  acts, frames, firstMs, rootFails = {}, 0, -1, 0
  writes, wFrames, lastWrites = 0, 0, 0
  lastGX, lastGY = 9e9, 9e9
  chv = {}
  for i = 1, #CHANNELS do
    local k = CHANNELS[i]
    chv[k] = (CFG.ch and CFG.ch[k] or 0) * CFG.chAmp
  end
  if CFG.blink.auto then blink.next = 0.9 + math.random() * 1.5 end
  print(string.format("[GEIMG] 图元 %d 个，部件 %d 个，动画 %s",
                      total, #PARTS, CFG.animate and "开" or "关"))
  -- 关键：不管要不要动画，都得先打开逐帧回调 —— 图元是分帧铺的，铺完才谈得上动画。
  -- （脚本的 update 开关默认关闭，不显式打开就一帧都不会跑。）
  startTick()
  print("[GEIMG] EnableUpdate(true) —— 已打开逐帧回调")
  -- UI 层（背景/按钮/文字/拖动条）：在同名文件里定义，没有就跳过。
  -- **必须先确认容器找得到**：UIBuild 是往 root 里塞控件的，root 还是 nil 时
  -- InstantiateClientUIControl(prefab, nil) 会静默失败 —— UI 一个都建不出来，
  -- 而且按键监听是挂在控件上的，于是快捷键也一起失效（实测踩过）。
  -- 这里试一次，失败就交给 OnUpdate 每帧重试，直到容器就绪。
  uiBuilt = false
  if ensureRoot() and UIBuild ~= nil then UIBuild(); uiBuilt = true end
end

function OnUpdate(dt)
  if not ensureRoot() then
    -- 容器可能比脚本晚一帧就绪，先容忍一会儿；一直找不到就停掉逐帧回调并说明原因，
    -- 免得在游戏里变成一个每帧空转、又什么都不显示的哑巴脚本。
    rootFails = rootFails + 1
    if rootFails >= 60 then
      warnOnce("rootGiveUp", "连续 " .. rootFails .. " 帧都没找到容器，已停掉逐帧回调；"
                           .. "请核对 CFG.containerName 与脚本挂载位置")
      stopTick()
    end
    return
  end
  rootFails = 0

  -- 容器晚于 OnStart 才就绪时，UI 在这里补建（只建一次）
  if not uiBuilt and UIBuild ~= nil then
    UIBuild()
    uiBuilt = true
  end

  -- ① 分帧铺图元
  if not done then
    local budget = CFG.budgetPerFrame
    while cursor <= total and budget > 0 do
      local d = shapes[cursor]
      if d ~= nil then
        local c = spawn(d, cursor)
        if c ~= nil then pool[cursor] = c end
      end
      cursor = cursor + 1
      budget = budget - 1
    end
    if cursor > total then
      done = true
      print("[GEIMG] 图元铺完：" .. total .. " 个")
      -- 角色铺完了：按「背景 → 角色 → UI」重排同级索引
      if UIReindex ~= nil then UIReindex() end
      if not CFG.animate then
        stopTick()
        print("[GEIMG] 动画关闭 → EnableUpdate(false)，静态不再逐帧回调")
      end
    end
    return
  end
  if not CFG.animate then return end

  -- ② 动画（按 stride 降低更新频率，省性能）
  acc = acc + dt
  frames = frames + 1
  local stride = CFG.updateStride or 1
  if stride > 1 and frames % stride ~= 0 then return end

  local t0 = os.clock()
  local step = acc
  acc = 0
  t = t + step * CFG.speed
  tickBlink(step * CFG.speed)
  tickGaze(step)

  for i = 1, #CHANNELS do
    local k = CHANNELS[i]
    chv[k] = (CFG.ch and CFG.ch[k] or 0) * CFG.chAmp
  end

  local keep = {}
  for i = 1, #acts do
    if t - acts[i].t0 <= ACT[acts[i].n].dur then keep[#keep+1] = acts[i] end
  end
  acts = keep

  -- 头部偏航/俯仰（度）：由视点驱动
  local gx = CFG.gaze and gaze.x or 0
  local gy = CFG.gaze and gaze.y or 0
  -- 注：gaze.y 来源于 GetCursorUIPos（Y 向上），而源图坐标 Y 向下 → 取负
  local yaw = gx * (GAZE.yaw or 0) * (CFG.motionScale or 1)
  local pitch = -gy * (GAZE.pitch or 0) * (CFG.motionScale or 1)

  local so, browDy, talk = faceExtra()
  tickJump()
  -- 视点这一帧是否真的动了：没动 → 骨骼场贡献不变 → 相关部件整帧跳过
  -- （鼠标停住时这一步能把"每帧 1 万次写入"直接降到只剩呼吸要写的那几个部件）
  local gChanged = (math.abs(gaze.x - lastGX) > CFG.gazeEps)
                   or (math.abs(gaze.y - lastGY) > CFG.gazeEps)
  if gChanged then lastGX, lastGY = gaze.x, gaze.y end
  local w0 = writes
  for pi = 1, #PARTS do
    updatePart(PARTS[pi], so, browDy, talk, yaw, pitch, gChanged)
  end
  wFrames = wFrames + 1
  lastWrites = writes - w0

  if UIUpdate ~= nil and frames % 10 == 0 then UIUpdate(step) end

  if firstMs < 0 then
    firstMs = (os.clock() - t0) * 1000
    print(string.format("[GEIMG] 首帧动画耗时 %.1f ms（%d 个控件）—— 偏高就把 CFG.updateStride 调到 2，"
                        .. "或把 CFG.animate 关掉", firstMs, total))
  end
end

function OnDestroy()
  -- 先摘掉本脚本注册的按键监听（容器上可能还挂着别的脚本的监听，不能整片移除）
  if UICleanup ~= nil then UICleanup() end
  for i = 1, #pool do
    local c = pool[i]
    if c ~= nil and c.alive then game.DestroyClientUIControl(c) end
  end
  pool, shapes, root, preplaced, acts = {}, {}, nil, nil, {}
  uiBuilt, jump.active = false, false
  stopTick()                     -- 销毁了就别再逐帧回调
end

-- ============================ 对外接口 ============================
-- 全局函数，可用 script:Invoke("PlayAction", "shake") 调用

function PlayAction(name)
  if ACT[name] == nil then
    print("[GEIMG] 没有这个动作：" .. tostring(name))
    return false
  end
  -- 跳跃的三条前置：① 图元没铺完不播（控件还没建齐，动起来是残影）
  --                ② 不叠加：上一次还没落地就不接受新的，腾空高度不会累积
  --                ③ 动画开关关着就顺手打开（否则播了也看不到）
  if name == "jump" then
    if not done then
      return false
    end
    for _, a in ipairs(acts) do
      if a.n == "jump" and t - a.t0 < ACT.jump.dur then
        return false
      end
    end
    if not CFG.animate then
      CFG.animate = true
      startTick()
    end
  end
  acts[#acts+1] = { n = name, t0 = t }
  print("[GEIMG] 动作：" .. name)
  return true
end

function SetPreset(name)
  local p = PRESET[name]
  if p == nil then
    print("[GEIMG] 没有这个预设：" .. tostring(name))
    return
  end
  CFG.ch = {}
  for i = 1, #CHANNELS do CFG.ch[CHANNELS[i]] = 0 end
  for k, val in pairs(p) do
    if k == "blink" then CFG.blink.auto = (val ~= 0)
    elseif k == "gaze" then CFG.gaze = (val ~= 0)
    else CFG.ch[k] = val end
  end
  print("[GEIMG] 预设：" .. name)
end

function SetChannel(name, value)
  local known = false
  for i = 1, #CHANNELS do if CHANNELS[i] == name then known = true break end end
  if not known then
    print("[GEIMG] 没有这个通道：" .. tostring(name) .. "（可用：" .. table.concat(CHANNELS, " / ") .. "）")
    return
  end
  CFG.ch = CFG.ch or {}
  CFG.ch[name] = value or 0
end

function SetGaze(on) CFG.gaze = on and true or false end

-- 立刻眨一次（按钮用）
function BlinkOnce()
  blink.events[#blink.events + 1] = bt
  blink.count = blink.count + 1
end

-- 手动控制眨眼：SetBlink("hold") 保持闭眼、SetBlink(0.5) 指定闭合量、SetBlink("open") 恢复自动
function SetBlink(v)
  if v == "hold" then
    CFG.blink.hold, CFG.blink.auto = true, false
  elseif v == "open" then
    CFG.blink.hold, CFG.blink.auto, CFG.blink.manual = false, true, 0
  elseif v == "off" then
    CFG.blink.hold, CFG.blink.auto, CFG.blink.manual = false, false, 0
  else
    CFG.blink.hold = false
    CFG.blink.manual = tonumber(v) or 0
  end
end

function SetAnimate(on)
  CFG.animate = on and true or false
  -- 走 startTick() 而不是直接调 EnableUpdate：老运行时只有 EnableTick 时也要能重新打开
  if on then startTick() else stopTick() end
end

-- 运行状态快照：排查"到底在动没动"时很有用，直接 print 出来或喂给日志
function GetStatus()
  return {
    total = total, parts = #PARTS, done = done, frames = frames,
    t = t, bt = bt, firstMs = firstMs,
    blinkCount = blink.count, blinkL = blink.vL, blinkR = blink.vR,
    gazeX = gaze.x, gazeY = gaze.y, gazeLagX = gaze.lagX, gazeLagY = gaze.lagY,
    acts = #acts, chSway = chv.sway or 0, chTalk = chv.talk or 0,
    -- 负载画像：每帧平均写入次数 = 10k 图元方案的实际开销指标
    writes = writes, lastWrites = lastWrites,
    writesPerFrame = (wFrames > 0) and (writes / wFrames) or 0,
    -- 跳跃状态（外部想接"落地事件"之类的就轮询这个）
    jumping = jump.active, jumpHeight = jump.height, jumpAge = jump.age,
    -- 可调参数快照（拖动条改的就是它们，方便外部读取/日志）
    swing = GAZE.swing, yaw = GAZE.yaw, pitch = GAZE.pitch, swingY = GAZE.swingY,
    motion = CFG.motionScale, breath = CFG.baseAmp, amp = CFG.ampScale,
    speed = CFG.speed, period = CFG.period,
    bodyAmp = BONE.bodyAmp, depthK = BONE.depthK, boneOn = BONE.on,
  }
end
