"""用真 Lua 运行时（lupa）实跑「图元动画*.lua」，并量出**每帧 API 写入次数**。

用法：
    py -3 verify_lua_anim.py                             # 默认跑 l2d_anim.lua
    py -3 verify_lua_anim.py --lua l2d_anim_10k.lua  # 超拟合版

检查项：
  ① 语法 ② 加载 ③ 图元铺满且数量正确 ④ 位置在容器内（坐标参考系对不对）
  ⑤ 呼吸在动 ⑥ 眨眼会闭合 ⑦ 视点跟光标 ⑧ 动作/预设 ⑨ 闭眼时眼部尺寸/alpha 且能还原
  ⑩ skipBelow 对写入量的影响 ⑪ 静态模式能关掉逐帧回调 ⑫ 脚本自己打开 EnableUpdate
  ⑬ 振幅画像 + 骨骼场（越往上动得越多、脚钉住）
  ⑭ 负载画像：待机（鼠标不动）/ 视点移动 / 全通道 三种状态的每帧写入次数
"""
import argparse
import math
import re
import sys
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parent.parent

DT = 1.0 / 60

# 用于振幅画像的部件：腿（应钉住）/ 躯干 / 头 / 虹膜
PROFILE_PARTS = {"leg": 21, "body": 15, "head": 13, "iris": 9}


def install(L, controls, cfg, keybinds=None):
    """把桩装进一个 LuaRuntime；控件记录写进 controls 列表。"""
    if keybinds is None:
        keybinds = []
    CX, CY = cfg["canvasW"] / 2, cfg["canvasH"] / 2
    root = L.table()
    root["alive"] = True
    root["name"] = "GEIMG_Canvas"
    # update 初始为关闭：模拟运行时里脚本的逐帧开关默认不开
    state = {"cursor": (CX, CY), "update": None, "updates_skipped": 0}

    def make_control(idx):
        rec = {"idx": idx, "x": None, "y": None, "w": None, "h": None, "rot": 0.0,
               "vis": False, "img": None, "sib": None, "calls": 0}
        controls.append(rec)
        c = L.table()
        rec["tbl"] = c
        c["alive"] = True
        # Lua 冒号调用会把 self 当第一个参数传进来，每个桩都要吃下 self
        c["SetAnchoredPosition"] = lambda self, x, y, r=rec: (
            r.__setitem__("x", float(x)), r.__setitem__("y", float(y)),
            r.__setitem__("calls", r["calls"] + 1))
        c["SetSizeDelta"] = lambda self, w, h, r=rec: (
            r.__setitem__("w", float(w)), r.__setitem__("h", float(h)))
        c["SetLocalRotation"] = lambda self, x, y, z, r=rec: r.__setitem__("rot", float(z))
        c["SetImage"] = lambda self, a, b, r=rec: r.__setitem__("img", (a, b))
        c["SetVisible"] = lambda self, v, r=rec: r.__setitem__("vis", bool(v))
        c["SetSiblingIndex"] = lambda self, i, r=rec: (r.__setitem__("sib", int(i)), True)[1]
        c["SetAnchorMin"] = lambda self, x, y: None
        c["SetAnchorMax"] = lambda self, x, y: None
        c["SetPivot"] = lambda self, x, y: None
        c["GetChildren"] = lambda self: L.table()
        # 剧场版会建 UI 并注册按键：这些也要有桩，否则 OnStart 里的 UIBuild 会炸
        c["AddKeyEventListener"] = lambda self, et, cb: keybinds.append((et, cb))
        c["RemoveKeyEventListener"] = lambda self, et, cb: None
        c["AddCursorEventListener"] = lambda self, et, cb: None
        c["imageColor"] = None
        return c

    game = L.table()
    game["InstantiateClientUIControl"] = lambda prefab, parent: make_control(len(controls) + 1)
    game["DestroyClientUIControl"] = lambda c: None
    game["FindClientUIRoot"] = lambda name: root
    game["GetUICanvasSize"] = lambda: (cfg["canvasW"], cfg["canvasH"])
    game["GetCursorUIPos"] = lambda: state["cursor"]
    game["PrintClientUITree"] = lambda: None

    script = L.table()
    script["alive"] = True
    script["object"] = root
    script["EnableUpdate"] = lambda self, on: state.__setitem__("update", bool(on))
    script["EnableTick"] = None
    script["GetParam"] = lambda n: None

    enum = L.table()
    enum["ImageSource"] = L.table(); enum["ImageSource"]["StaticReference"] = 0
    enum["ImageType"] = L.table(); enum["ImageType"]["Basic"] = 0; enum["ImageType"]["Stretch"] = 1
    for grp, names in (("TextHorizontalAlignment", ["Left", "Middle", "Right"]),
                       ("TextVerticalAlignment", ["Top", "Middle", "Bottom"]),
                       ("CursorEventType", ["CursorDown", "CursorUp", "CursorEnter", "CursorExit",
                                            "CursorDrag", "CursorBeginDrag", "CursorEndDrag", "CursorClick"])):
        enum[grp] = L.table()
        for i, nm in enumerate(names):
            enum[grp][nm] = i
    enum["KeyEventType"] = L.table()
    for i in range(1, 44):
        enum["KeyEventType"]["KeyboardCraftspersonKey%dDown" % i] = i - 1
    enum["KeyEventType"]["KeyboardJumpKeyDown"] = 49

    color = L.table()

    def _mkcolor(r, g, b, a=255):
        t = L.table()
        t["r"], t["g"], t["b"], t["a"] = r, g, b, a
        return t
    color["FromRGBA"] = _mkcolor

    for k, v in (("game", game), ("script", script), ("Enum", enum), ("Color", color)):
        L.globals()[k] = v
    return state


def part_range(src, num):
    m = re.search(r"\{ n=%d, f=(\d+), t=(\d+)" % num, src)
    if m is None:
        raise SystemExit(f"在 Lua 里找不到部件 {num} 的区间")
    return int(m.group(1)), int(m.group(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lua", default="l2d_anim.lua")
    ap.add_argument("--deadline", type=int, default=1500, help="铺图元最多等多少帧")
    args = ap.parse_args()

    lua_path = ROOT / args.lua
    src = lua_path.read_text(encoding="utf-8")
    EXPECT = len(re.findall(r'^  "[cel]\|', src, re.M))
    cfg = {
        "canvasW": float(re.search(r"canvasW\s*=\s*(\d+)", src).group(1)),
        "canvasH": float(re.search(r"canvasH\s*=\s*(\d+)", src).group(1)),
    }
    CX, CY = cfg["canvasW"] / 2, cfg["canvasH"] / 2
    print(f"=== {lua_path.name} · 图元 {EXPECT} 个 ===")

    try:
        from luaparser import ast as lua_ast
        lua_ast.parse(src)
        print("① 语法检查：通过（luaparser）")
    except Exception as e:
        print("① 语法检查：失败 ——", e)
        return 1

    controls = []
    L = LuaRuntime(unpack_returned_tuples=True)
    keybinds = []
    state = install(L, controls, cfg, keybinds)
    try:
        L.execute(src)
        print("② 加载：通过（真 Lua %s）" % L.eval("_VERSION"))
    except Exception as e:
        print("② 加载：失败 ——", e)
        return 1

    G = L.globals()
    G["OnInit"]()
    G["OnStart"]()
    print(f"⑫ 按键监听：注册 {len(keybinds)} 个")
    print(f"⑫ 逐帧回调：OnStart 之后 update_enabled={state['update']}"
          f"（脚本自己打开的；漏了这一步实机就一帧不跑）")
    assert state["update"] is True, "脚本没有在 OnStart 里打开逐帧回调"
    status = lambda: G["GetStatus"]()

    def step():
        """忠实模拟运行时：逐帧回调关着就不给 OnUpdate。"""
        if state["update"] is not True:
            state["updates_skipped"] += 1
            return False
        G["OnUpdate"](DT)
        return True

    # 剧场版会在 OnStart 先建一批 UI 控件（背景/按钮/文字/命中区）——那批不算图元。
    # 这里先记下 UI 数量，只对图元数量做校验，否则会把 89 个 UI 控件算进 9941 里。
    ui_n = len(controls)
    if ui_n:
        print(f"   （OnStart 已建 UI 控件 {ui_n} 个，不计入图元数）")
    frames, blocked = 0, 0
    while len(controls) < ui_n + EXPECT and frames < args.deadline:
        if step():
            frames += 1
        else:
            blocked += 1
            if blocked > 3:
                print("   ✗ 脚本没有自己打开 EnableUpdate → 实机会一帧都不跑")
                return 1
    print(f"③ 铺图元：{len(controls) - ui_n} / {EXPECT} 个，用 {frames} 帧（budgetPerFrame=40）")
    if len(controls) - ui_n != EXPECT:
        print("   ✗ 数量不符")
        return 1

    shapes_only = controls[ui_n:]
    snap = lambda: [(c["x"], c["y"]) for c in shapes_only]

    G["OnUpdate"](DT)
    a = snap()
    for _ in range(30):
        G["OnUpdate"](DT)
    b = snap()
    moved = sum(1 for i in range(len(a)) if abs(a[i][0] - b[i][0]) > 0.05 or abs(a[i][1] - b[i][1]) > 0.05)
    xs = [c["x"] for c in shapes_only]
    ys = [c["y"] for c in shapes_only]
    bad = sum(1 for c in shapes_only if abs(c["x"]) > CX or abs(c["y"]) > CY)
    print(f"④ 位置：X [{min(xs):.1f}, {max(xs):.1f}]  Y [{min(ys):.1f}, {max(ys):.1f}]"
          f"  超出半画布 ±({CX:g},{CY:g}) 的：{bad} 个")
    print(f"⑤ 呼吸：0.5 秒后 {moved} / {len(a)} 个控件位置变化")

    mx = 0.0
    for _ in range(600):
        G["OnUpdate"](DT)
        v = float(status()["blinkL"])
        if v > mx:
            mx = v
    st = status()
    print(f"⑥ 眨眼：10 秒触发 {int(st['blinkCount'])} 次，最大闭合 {mx:.3f}")

    for label, cur in (("右上", (CX + 700, CY + 400)), ("右下", (CX + 700, CY - 400)),
                       ("左上", (CX - 700, CY + 400)), ("中心", (CX, CY))):
        state["cursor"] = cur
        for _ in range(50):
            G["OnUpdate"](DT)
        s = status()
        print(f"⑦ 视点 {label}: gaze=({s['gazeX']:+.3f}, {s['gazeY']:+.3f})"
              f" 滞后=({s['gazeLagX']:+.3f}, {s['gazeLagY']:+.3f})")

    G["PlayAction"]("shake")
    G["PlayAction"]("surprise")
    G["SetPreset"]("talk")
    G["SetChannel"]("sway", 1.0)
    for _ in range(30):
        G["OnUpdate"](DT)
    s = status()
    print(f"⑧ 动作/预设：在播 {int(s['acts'])} 个，chSway={s['chSway']:.2f} chTalk={s['chTalk']:.2f}")
    G["SetPreset"]("allOff")
    G["PlayAction"]("wave")

    # 闭眼：眼部尺寸压缩 + alpha 淡出，恢复后要还原
    def eye_state():
        out = []
        for r in shapes_only:
            col = r["tbl"]["imageColor"]
            out.append((r["h"], (col["a"] if col is not None else None)))
        return out

    G["SetBlink"]("off")            # 确定性地完全睁眼（关掉自动眨眼）
    for _ in range(20):
        G["OnUpdate"](DT)
    opened = eye_state()
    G["SetBlink"](1)
    for _ in range(20):
        G["OnUpdate"](DT)
    shut = eye_state()
    # 注意：alpha 可能正好是 0，不能用真值判断（0 在 Python 里是假值）
    hshrink = sum(1 for i in range(len(shut))
                  if shut[i][0] is not None and opened[i][0] is not None
                  and shut[i][0] < opened[i][0] - 0.01)
    adrop = sum(1 for i in range(len(shut))
                if isinstance(shut[i][1], int) and isinstance(opened[i][1], int)
                and shut[i][1] < opened[i][1])
    print(f"⑨ 闭眼：{hshrink} 个控件高度被压缩、{adrop} 个 alpha 降低")
    G["SetBlink"]("off")
    for _ in range(20):
        G["OnUpdate"](DT)
    back = eye_state()
    arestore = sum(1 for i in range(len(shut))
                   if isinstance(shut[i][1], int) and isinstance(back[i][1], int)
                   and back[i][1] > shut[i][1])
    print(f"   恢复睁眼：{arestore} 个 alpha 已还原")

    # ── ⑬ 振幅画像 + 骨骼场 ──
    G["SetAnimate"](True)
    G["SetPreset"]("idle")
    G["SetBlink"]("off")
    G["SetGaze"](True)          # 前面的 allOff 把视点关了，这里重新打开
    G["SetChannel"]("sway", 0)  # 确保只剩 呼吸 + 视点
    for _ in range(30):
        step()
    ranges = {k: part_range(src, n) for k, n in PROFILE_PARTS.items()}
    # 每个部件取一个"代表图元"（区间的第一个）
    idx = {k: ui_n + r[0] - 1 for k, r in ranges.items()}   # 控件下标要加上 UI 偏移
    track = {k: [] for k in PROFILE_PARTS}
    N = 180
    for i in range(N):
        state["cursor"] = (CX + math.sin(i / N * 2 * math.pi) * 700, CY)
        step()
        for k, ci in idx.items():
            track[k].append((controls[ci]["x"], controls[ci]["y"]))
    print("⑬ 振幅画像（鼠标左右扫动 3 秒，画布像素；代表图元）")
    span = {}
    for k in PROFILE_PARTS:
        xs2 = [p[0] for p in track[k]]
        ys2 = [p[1] for p in track[k]]
        span[k] = (max(xs2) - min(xs2), max(ys2) - min(ys2))
        print(f"   {k:5} 水平 {span[k][0]:5.2f}px  竖直 {span[k][1]:5.2f}px"
              f"   x∈[{min(xs2):.2f}, {max(xs2):.2f}]")
    ok = span["leg"][0] <= 0.6 and span["body"][0] > span["leg"][0] and span["head"][0] >= span["body"][0]
    print(f"   骨骼场判读：脚{'钉住' if span['leg'][0] <= 0.6 else '在动 ✗'}"
          f"（{span['leg'][0]:.2f}px），躯干 {span['body'][0]:.2f}px，头 {span['head'][0]:.2f}px"
          f" → {'越往上动得越多 ✓' if ok else '梯度不对 ✗'}")

    # ── ⑭ 负载画像：三种状态下的每帧写入次数 ──
    def writes_for(seconds, move_mouse, setup=None):
        if setup:
            setup()
        before = float(status()["writes"])
        fr = int(seconds / DT)
        for i in range(fr):
            if move_mouse:
                state["cursor"] = (CX + math.sin(i / fr * 2 * math.pi) * 700,
                                   CY + math.cos(i / fr * 2 * math.pi) * 350)
            step()
        return (float(status()["writes"]) - before) / fr

    G["SetPreset"]("idle")
    G["SetChannel"]("sway", 0)
    still = writes_for(1.0, False)
    moving = writes_for(1.0, True)
    print("⑭ 负载画像（每帧 API 写入次数，控件共 %d 个）" % EXPECT)
    print(f"   鼠标不动（只剩呼吸）      {still:8.1f} 次/帧  → {still * 60:9.0f} 次/秒")
    print(f"   鼠标移动（骨骼场+呼吸）   {moving:8.1f} 次/帧  → {moving * 60:9.0f} 次/秒")
    st = status()
    print(f"   最近一帧 {int(st['lastWrites'])} 次；累计 {int(st['writes'])} 次 / {int(st['frames'])} 帧"
          f"（updateStride={int(re.search(r'updateStride = ([-0-9.]+)', src).group(1))}）")
    print(f"   对照：不做骨骼场跳过时，最坏情况是每帧全量 {EXPECT} 次"
          f"（{EXPECT * 60 / 1000:.0f} 千次/秒）")

    G["SetAnimate"](False)
    print(f"⑪ 静态模式：SetAnimate(false) → update_enabled={state['update']}（False = 已关逐帧回调）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
