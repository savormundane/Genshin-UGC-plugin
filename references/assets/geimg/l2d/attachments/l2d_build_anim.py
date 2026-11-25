"""生成「图元动画」自包含 Lua。

与 build_lua_showcase.py 共用同一套数据提取（图元、呼吸 rig、眨眼几何、虹膜安全范围），
但产物是**可直接放进游戏的 .lua**，而且**带完整动画**（呼吸/眨眼/视点跟随/骨骼动作/一次性动作）。

两个数据源都支持（互不覆盖）：
    py -3 build_lua_anim.py                      # 普通：parts → l2d_anim.lua / l2d_theater.lua
    py -3 build_lua_anim.py --preset superfit    # 超拟合：_超拟合_10k → l2d_anim_10k.lua …
"""
import argparse
import json
import math
import re
from pathlib import Path

import l2d_build_showcase as B

ROOT = Path(__file__).resolve().parent.parent          # 本项目
TPL = Path(__file__).resolve().parent / "templates" / "l2d_anim.template.lua"

# 图元数超过这个数就默认降频（10k 图元每帧全写 = 60 万次属性写入/秒，实测会卡）
STRIDE_THRESHOLD = 4000

# 跳跃骨架锚点（源图像素，Y 向下）：髋 392 → 膝 480 → 踝 560，角色中线 x=218。
# 这是**别人在实机上调出来**的值，不是从数据推的 —— 它是观感参数（决定下蹲/外张
# 权重在身体上怎么分布），换个角色要重新调；所以这里保持原样，不自动换算。
JUMP_RIG = {"hipY": 392, "kneeY": 480, "ankleY": 560, "centerX": 218}

PRESETS = {
    "normal":   {"source": None, "out": "l2d_anim.lua", "out_ui": "l2d_theater.lua"},
    "superfit": {"source": "fit_10k",
                 "out": "l2d_anim_10k.lua", "out_ui": "l2d_theater_10k.lua"},
}


def ui_spec_lua():
    """UI 布局。坐标用 anchoredPosition 空间（容器中心原点，Y 向上）：
    画布 1600x900 → x∈[-800,800]、y∈[-450,450]。"""
    BG = [(0, 0, 1900, 1900, 0x0E141EFF),        # 直径 1900 的圆足以盖满整屏（半对角线 918）
          (-560, 250, 900, 900, 0x16202EFF),
          (560, -240, 860, 860, 0x16202EFF),
          (620, 240, 820, 820, 0x1A2434FF),
          (-620, -250, 800, 800, 0x1A2434FF),
          (-620, 10, 350, 840, 0x1B1E26F0),       # 左面板底（半透明椭圆≈圆角面板）
          (620, 10, 350, 840, 0x1B1E26F0)]        # 右面板底
    TEXTS = [(-620, 404, 320, 36, 22, 0x98A0B4FF, "middle", "特 殊 动 作"),
             (620, 404, 320, 36, 22, 0x98A0B4FF, "middle", "参 数 调 节"),
             (-620, -352, 320, 64, 14, 0x7A8296FF, "middle",
              "按钮：点一下触发 / 拖动条：按住拖动或点轨道跳转"),
             (620, -352, 320, 64, 14, 0x7A8296FF, "middle",
              "拖动条直接写参数 / 即时生效")]
    BTNS_L = [("摇头", "act:shake", 0x2A3346FF), ("点头", "act:nodOnce", 0x2A3346FF),
              ("惊讶", "act:surprise", 0x2A3346FF), ("摆臂", "act:wave", 0x2A3346FF),
              ("眨一下眼", "cmd:blinkOnce", 0x3A4A6AFF), ("强制睁眼", "blink:off", 0x3A4A6AFF),
              # 最后一个动作：跳跃。放在末行，和「强制睁眼」各占半宽，右下角留出空间
              ("跳跃 [空格]", "act:jump", 0x426B68FF)]
    BTNS_R = [("待机", "preset:idle", 0x2A3346FF), ("摆动", "preset:swayIdle", 0x2A3346FF),
              ("风吹", "preset:wind", 0x2A3346FF), ("眯眼笑", "preset:smile", 0x2A3346FF),
              ("全停", "preset:allOff", 0x3A2A2AFF), ("动画开关", "tog:animate", 0x3A4A6AFF)]
    SL_L = [("swing", "头部摆幅", 0.0, 24.0, 6.0, "%.1f"), ("yaw", "头部转角", 0.0, 20.0, 7.0, "%.1f"),
            ("swingY", "俯仰幅度", 0.0, 12.0, 4.0, "%.1f"), ("breath", "呼吸幅度", 0.0, 8.0, 1.2, "%.2f")]
    # 右列多两根「骨骼」旋钮：身体转动是连续位移场，改这两个数就能直接看手感
    SL_R = [("bodyAmp", "身体转动", 0.0, 16.0, 6.0, "%.1f"), ("depthK", "立体压缩", 0.0, 0.8, 0.25, "%.2f"),
            ("motion", "总幅度", 0.0, 3.0, 1.0, "%.2f"), ("amp", "动作强度", 0.0, 3.0, 1.0, "%.2f"),
            ("speed", "播放速度", 0.0, 3.0, 1.0, "%.2f"), ("period", "呼吸周期", 1.2, 8.0, 3.6, "%.1f")]

    def btn_lua(x, y, label, cmd, c, w=300):
        return ('{x=%g, y=%g, w=%g, h=46, c=0x%08X, label="%s", cmd="%s"}'
                % (x, y, w, c, label, cmd))

    def sl_lua(x, y, ch, label, lo, hi, val, fmt):
        return ('{x=%g, y=%g, w=300, ch="%s", label="%s", min=%g, max=%g, val=%g, fmt="%s"}'
                % (x, y, ch, label, lo, hi, val, fmt))

    L = []
    L.append("  bg = {")
    for c in BG:
        L.append("    {%g, %g, %g, %g, 0x%08X}," % c)
    L.append("  },")
    L.append("  texts = {")
    for t in TEXTS:
        L.append('    {%g, %g, %g, %g, %d, 0x%08X, "%s", "%s"},' % t)
    L.append("  },")
    L.append("  buttons = {")
    # 左列 7 个：前 5 个整宽（y=345…113），末行两个半宽并排（y=55）——
    # 直接往下排第 7 个会压到第一条拖动条的标签上（实测布局会撞）
    for i, (lab, cmd, c) in enumerate(BTNS_L[:5]):
        L.append("    " + btn_lua(-620, 345 - i * 58, lab, cmd, c) + ",")
    for j, (lab, cmd, c) in enumerate(BTNS_L[5:]):
        L.append("    " + btn_lua(-698 + j * 156, 55, lab, cmd, c, w=144) + ",")
    for i, (lab, cmd, c) in enumerate(BTNS_R):
        L.append("    " + btn_lua(620, 345 - i * 58, lab, cmd, c) + ",")
    L.append("  },")
    L.append("  sliders = {")
    for i, (ch, lab, lo, hi, val, fmt) in enumerate(SL_L):
        L.append("    " + sl_lua(-620, -40 - i * 78, ch, lab, lo, hi, val, fmt) + ",")
    # 右列 6 根 → 间距压到 68，最后一根落在 y=-360（状态文字在 -424，不重叠）
    for i, (ch, lab, lo, hi, val, fmt) in enumerate(SL_R):
        L.append("    " + sl_lua(620, -20 - i * 68, ch, lab, lo, hi, val, fmt) + ",")
    L.append("  },")
    # 屏幕文字两块：
    #   help = 快捷键功能表 + 实时状态，放在角色上方的空白带（角色顶边 ≈ y+315，两侧按钮在 |x|>470）
    #   status = 底部一行状态（角色底边 ≈ y-315，拖动条到 -360）
    L.append('  help = {0, 396, 860, 86, 15, 0xD8DEEAFF, "middle"},')
    L.append('  status = {0, -424, 900, 56, 15, 0x7A8296FF, "middle"},')
    NL = chr(10)
    return "{" + NL + NL.join(L) + NL + "}"

GROUPS = ["head", "bangs", "hairBack", "tailL", "tailR", "ribbon", "body", "armL", "armR", "legs"]
GI = {g: i for i, g in enumerate(GROUPS)}


def lua_num(v):
    """Lua 数字字面量：整数不带小数点，浮点保留足够精度。"""
    if isinstance(v, int):
        return str(v)
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=sorted(PRESETS), default="normal")
    ap.add_argument("--source", default=None, help="覆盖 preset 的图元目录")
    ap.add_argument("--mask-source", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--out-ui", default=None, help="空字符串 = 不生成剧场版")
    ap.add_argument("--no-edge-fix", action="store_true")
    args = ap.parse_args()

    ps = PRESETS[args.preset]
    src = args.source or ps["source"]
    if src is not None:
        B.configure(ROOT / src, args.mask_source, not args.no_edge_fix)
    elif args.mask_source or args.no_edge_fix:
        B.configure(None, args.mask_source, not args.no_edge_fix)

    out_path = ROOT / (args.out or ps["out"])
    out_ui = ps["out_ui"] if args.out_ui is None else args.out_ui

    rig = json.loads(B.RIG.read_text(encoding="utf-8"))
    motion = {p["num"]: p for p in rig["parts"]}

    by_num = B.load_all(verbose=True)
    body = B.body_rig(by_num, motion)
    if body is None:
        raise SystemExit("推不出骨骼锚点：rig.json 的组划分与数据对不上")
    eyes, roles, mouth = B.blink_geometry(by_num)
    safe = B.iris_safe_range()

    # ── RAW + PARTS（部件顺序 = 绘制顺序，编号从大到小）──
    raw_rows = []
    parts = []
    cursor = 0
    for num, d in B.part_dirs():
        rows = B.raw_rows(by_num[num])
        raw_rows.extend(rows)
        m = motion[num]
        f, t = cursor + 1, cursor + len(rows)
        cursor += len(rows)

        e = {"n": num, "f": f, "t": t,
             "px": lua_num(m["pivot"][0]), "py": lua_num(m["pivot"][1]),
             "w": lua_num(m["w"]), "delay": lua_num(m["delay"]),
             # Lua 的 GN 表是 1-based，这里必须 +1，否则按组权重整体错位一位
             "rot": lua_num(m["rot"]), "g": GI[m["group"]] + 1}
        role = roles.get(str(num))
        if role:
            if role == "mouth":                       # 嘴没有"左右"，只需要中线与俯仰参考
                e["role"] = '"mouth"'
                e["geo"] = "{cy=%s}" % lua_num(mouth["cy"])
            else:
                kind, side = role.split(":")
                e["role"] = '"%s"' % kind
                e["side"] = '"%s"' % side
                ev = eyes[side]
                e["geo"] = "{top=%s, bot=%s, lidCy=%s, cy=%s}" % (
                    lua_num(ev["top"]), lua_num(ev["bot"]), lua_num(ev["lidCy"]),
                    lua_num((ev["top"] + ev["bot"]) / 2))
        parts.append(e)

    # ── IRIS_SAFE（严格版：眼白∪睫毛∪眼线；无掩膜时虹膜只能走这个范围）──
    def safe_tbl(side):
        s = safe[side]["strict"]
        return "{l=%d, r=%d, u=%d, d=%d}" % (s["left"], s["right"], s["up"], s["down"])
    # ── armR 通道按部件编号定向 ──
    armr = [p["n"] for p in parts if motion[p["n"]]["group"] == "armR"]

    # ── CFG ──
    CW, CH = B.CW, B.CH
    scale = min(1120.0 / CW, 630.0 / CH)
    n_shapes = len(raw_rows)
    stride = 2 if n_shapes > STRIDE_THRESHOLD else 1
    cfg = f"""local CFG = {{
  containerName = "GEIMG_Canvas",   -- 客户端控件容器的名称
  -- ↓ 这三个是**别人实机跑通**的值（同一套场景；换场景要按编辑器里实际的模板 ID 改）
  imagePrefabId = 1073741850,       -- 图片控件模板索引ID（图元/背景/按钮底/轨道/滑块都用它）
  textPrefabId = 1073741851,        -- 文本框控件模板索引ID（说明与参数文字）
  areaPrefabId = 1073741849,        -- 光标检测区模板索引ID（按钮点击、拖动条拖动）
  circleAssetId = 100002,           -- 图元用的圆形贴图资源ID（固定可用）
  strategy = "instantiate",         -- instantiate=运行时创建；pool=用容器里预摆的控件
  budgetPerFrame = 40,              -- 每帧实例化多少个，防进关卡顿
  alphaMax = 255,                   -- 整体透明度上限（0-255）

  -- 画布映射：源图像素 → 画布空间（左下原点、Y 向上）
  scale = {scale:.6f},
  offsetX = {800 - CW * scale / 2:.3f},
  offsetY = {450 - CH * scale / 2:.3f},
  sourceHeight = {CH},
  flipY = true,
  -- 容器尺寸：控件位置用「容器中心原点」，要在映射结果上再减 canvasW/2、canvasH/2。
  -- 运行时会优先用 game.GetUICanvasSize()；这里只是取不到时的回退。
  canvasW = 1600,
  canvasH = 900,
  -- centerX = 800, centerY = 450,   -- 需要手工标定时解除注释

  -- ── 动画 ──
  animate = true,                   -- false = 只铺图元不驱动动画（铺完就关逐帧回调）
  speed = 1.0,                      -- 动画整体速度
  -- 每 N 帧更新一次。图元 {n_shapes} 个 → 每帧全写就是 {n_shapes} 次属性写入，
  -- 60fps 下 {n_shapes * 60 // 1000} 千次/秒；指南说这种量级会拖慢进关/卡顿，所以默认降频。
  updateStride = {stride},
  gazeEps = 0.004,                  -- 视点变化小于这个量就不重写骨骼场（鼠标停住 → 零写入）
  posEps = 0.35,                    -- 单图元位移小于这个源像素数就不调 API（亚像素，看不见）
  skipBelow = 0.5,                  -- 位移小于这个源像素数的部件不写回（省 API 调用）
  period = {lua_num(rig['period'])},                       -- 呼吸周期（秒）
  -- 呼吸基准幅度（源像素）。原 rig 给的是 3.6，但在游戏里放大到 1.05 倍后
  -- 头肩竖直起伏达到 15px 峰峰；实测期望效果只有 ~3px，所以压到 1.2。
  baseAmp = 1.2,
  ampScale = 1.0,
  motionScale = 1.0,                -- ★ 所有位移/旋转的总幅度旋钮（先调这个找手感）
  chAmp = 1.0,                      -- 动作通道总强度
  gaze = true,                      -- 视点跟随鼠标（轮询 game.GetCursorUIPos）
  -- ── 跳跃（幅度单位：源像素 / 度）──
  -- 数值来自实机试出来的版本：起跳 64px、下蹲 24px、膝盖外张 10px、摆臂 12°、发梢滞后 3.5°
  jump = {{ height=64, crouch=24, knee=10, arm=12, hair=3.5 }},
  ch = {{ sway=0, turn=0, nod=0, wind=0, armR=0, talk=0, eyeOpen=0, browRaise=0 }},
  blink = {{ auto=true, dur=0.150, gapMin=2.2, gapMax=5.2, maxClose=0.92,
             closeAt=0.78, browFollow=0, fade=1.0, skewMs=12,
             doubleChance=0.16, hold=false, manual=0 }},
}}"""

    raw_lua = ",\n".join('  "%s"' % r for r in raw_rows)

    parts_lua = []
    for e in parts:
        bits = [f'n={e["n"]}', f'f={e["f"]}', f't={e["t"]}',
                f'px={e["px"]}', f'py={e["py"]}', f'w={e["w"]}',
                f'delay={e["delay"]}', f'rot={e["rot"]}', f'g={e["g"]}']
        if "role" in e:
            bits.append(f'role={e["role"]}')
            if "side" in e: bits.append(f'side={e["side"]}')
            bits.append(f'geo={e["geo"]}')
        parts_lua.append("  { " + ", ".join(bits) + " },")
    parts_lua = "\n".join(parts_lua)

    iris_lua = "{ eyeL = %s, eyeR = %s }" % (safe_tbl("eyeL"), safe_tbl("eyeR"))
    armr_lua = ", ".join(f"[{n}]=1" for n in armr)

    tpl = TPL.read_text(encoding="utf-8")
    for ph in ("__CFG__", "__RAW__", "__PARTS__", "__IRIS_SAFE__", "__ARMR_PARTS__",
               "__YGROUND__", "__YHIP__", "__YNECK__", "__YTOP__",
               "__CXTORSO__", "__RXTORSO__",
               "__JUMPHIP__", "__JUMPKNEE__", "__JUMPANKLE__", "__JUMPCX__"):
        assert tpl.count(ph) == 1, f"模板占位 {ph} 出现 {tpl.count(ph)} 次"
    out = (tpl.replace("__CFG__", cfg)
              .replace("__RAW__", raw_lua)
              .replace("__PARTS__", parts_lua)
              .replace("__IRIS_SAFE__", iris_lua)
              .replace("__ARMR_PARTS__", armr_lua)
              .replace("__YGROUND__", lua_num(body["yGround"]))
              .replace("__YHIP__", lua_num(body["yHip"]))
              .replace("__YNECK__", lua_num(body["yNeck"]))
              .replace("__YTOP__", lua_num(body["yTop"]))
              .replace("__CXTORSO__", lua_num(body["cxTorso"]))
              .replace("__RXTORSO__", lua_num(body["rxTorso"]))
              .replace("__JUMPHIP__", lua_num(JUMP_RIG["hipY"]))
              .replace("__JUMPKNEE__", lua_num(JUMP_RIG["kneeY"]))
              .replace("__JUMPANKLE__", lua_num(JUMP_RIG["ankleY"]))
              .replace("__JUMPCX__", lua_num(JUMP_RIG["centerX"])))
    # 占位符必须全部替换掉（除注释里的说明性下划线外，不应再有 __XXX__ 形式的标记）
    left = re.findall(r"__[A-Z_]{3,}__", out)
    assert not left, f"还有未替换的占位符: {set(left)}"
    out_path.write_text(out, encoding="utf-8")

    print(f"部件 {len(parts)} 个，图元 {n_shapes} 个（源：{B.SPLIT.name}），"
          f"默认 updateStride={stride}")
    print(f"骨骼锚点：脚底 y={body['yGround']} 脖子 y={body['yNeck']} "
          f"躯干 x={body['cxTorso']}±{body['rxTorso']}")
    if B.EDGE_STATS:
        print(f"边缘处理：剔溢出 {sum(s['dropped'] for s in B.EDGE_STATS.values())} 个 / "
              f"缩回轮廓 {sum(s.get('trimmed', 0) for s in B.EDGE_STATS.values())} 个 / "
              f"轮廓改色 {sum(s['changed'] for s in B.EDGE_STATS.values())} 个")
    print(f"虹膜安全范围：{iris_lua}")
    print(f"armR 通道定向部件：{armr}")
    print(f"写出 {out_path.name}  {out_path.stat().st_size/1024:.0f} KB")

    if not out_ui:
        return
    # ── 带 UI 的版本：背景铺满 + 两侧按钮/文字/拖动条 ──
    ui_path = ROOT / out_ui
    ui_tpl = (Path(__file__).resolve().parent / "templates" / "l2d_ui.template.lua").read_text(encoding="utf-8")
    assert ui_tpl.count("__UISPEC__") == 1
    NL = chr(10)
    ui_out = out + NL + NL + ui_tpl.replace("__UISPEC__", ui_spec_lua())

    ui_path.write_text(ui_out, encoding="utf-8")
    print(f"写出 {ui_path.name}  {ui_path.stat().st_size/1024:.0f} KB（含 UI 层）")


if __name__ == "__main__":
    main()
