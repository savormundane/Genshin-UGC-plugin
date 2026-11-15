"""验证「l2d_theater_*.lua」的新增部分：快捷键注册 + 屏幕文字（状态/功能）。

实机里 UI 依赖编辑器填三个 prefab ID，所以这里在源码文本上把它们填成假值再跑，
专门走 UI 那条路径（UIBuild → uiBuildHelp / uiBindKeys / UIUpdate）。

用法：py -3 verify_theater_keys.py [--lua l2d_theater_10k.lua]
"""
import argparse
import re
import sys
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lua", default="l2d_theater_10k.lua")
    args = ap.parse_args()
    path = ROOT / args.lua
    src = path.read_text(encoding="utf-8")

    # 实机由编辑器填；这里填假值以便走通 UI 路径
    src = re.sub(r"imagePrefabId = 0", "imagePrefabId = 9001", src, count=1)
    src = re.sub(r"textPrefabId = 0", "textPrefabId = 9002", src, count=1)
    src = re.sub(r"areaPrefabId = 0", "areaPrefabId = 9003", src, count=1)

    L = LuaRuntime(unpack_returned_tuples=True)
    bound, texts, areas = [], [], []

    class Ctl:
        def __init__(self, kind):
            self.kind, self.alive, self.text = kind, True, ""
            self.imageColor = None
            self.fontColor = None
            self.fontSize = 0
            self.raycastTarget = False

        def __getattr__(self, name):
            if name == "GetChildren":
                return lambda self=None: L.table()
            if name == "AddKeyEventListener":
                return lambda self, et, cb: bound.append((et, cb))   # 冒号调用会带 self
            if name in ("AddCursorEventListener",):
                return lambda self, *a: None
            if name.startswith("Set"):
                return lambda *a: None
            raise AttributeError(name)

    def mk(kind):
        c = Ctl(kind)
        (texts if kind == "text" else areas if kind == "area" else []).append(c)
        return c

    root_ctl = mk("root")            # 容器：FindClientUIRoot 要能返回它，
    root_ctl.name = "GEIMG_Canvas"   # 否则脚本会（正确地）拒绝建 UI 与绑按键
    game = L.table()
    game["InstantiateClientUIControl"] = lambda prefab, parent: mk(
        {9001: "img", 9002: "text", 9003: "area", 1073741850: "img",
         1073741851: "text", 1073741849: "area"}.get(prefab, "img"))
    for n in ("DestroyClientUIControl", "PrintClientUITree"):
        game[n] = lambda *a: None
    game["FindClientUIRoot"] = lambda n: root_ctl
    game["GetUICanvasSize"] = lambda: (1600, 900)
    game["GetCursorUIPos"] = lambda: (800, 450)

    script = L.table()
    script["alive"] = True
    script["object"] = root_ctl
    script["EnableUpdate"] = lambda self, on: None
    script["EnableTick"] = None

    enum = L.table()
    groups = (("ImageSource", ["StaticReference"]), ("ImageType", ["Basic", "Stretch"]),
              ("TextHorizontalAlignment", ["Left", "Middle", "Right"]),
              ("TextVerticalAlignment", ["Top", "Middle", "Bottom"]),
              ("CursorEventType", ["CursorDown", "CursorUp", "CursorEnter", "CursorExit",
                                   "CursorDrag", "CursorBeginDrag", "CursorEndDrag", "CursorClick"]))
    for grp, names in groups:
        enum[grp] = L.table()
        for i, nm in enumerate(names):
            enum[grp][nm] = i
    enum["KeyEventType"] = L.table()
    for i in range(1, 44):
        enum["KeyEventType"]["KeyboardCraftspersonKey%dDown" % i] = i - 1
    enum["KeyEventType"]["KeyboardJumpKeyDown"] = 49

    color = L.table()

    def mkcolor(r, g, b, a=255):
        t = L.table()
        t["r"], t["g"], t["b"], t["a"] = r, g, b, a
        return t
    color["FromRGBA"] = mkcolor

    for k, v in (("game", game), ("script", script), ("Enum", enum), ("Color", color)):
        L.globals()[k] = v

    L.execute(src)
    G = L.globals()
    G["OnInit"]()
    G["OnStart"]()
    for _ in range(20):
        G["OnUpdate"](1 / 60)

    ok = True
    print(f"① 按键监听：注册 {len(bound)} / 16 个（1~10 数字键 + U/Z/Y/G/H + 空格跳跃）")
    ok &= len(bound) == 16
    print(f"② 文字控件 {len(texts)} 个，命中区 {len(areas)} 个（命中区含按钮/拖动条/兜底按键区）")

    # 逐个触发，检查是否真的执行了对应功能
    fired = []
    for et, cb in bound:
        r = cb()
        fired.append((et, r))
    print(f"③ 16 个回调全部触发：返回 true 的 {sum(1 for _, r in fired if r is True)} 个"
          f"（true = 消费该事件）")
    for _ in range(30):
        G["OnUpdate"](1 / 60)
    st = G["GetStatus"]()
    print(f"④ 触发后：正在播的动作 {int(st['acts'])} 个，chSway={st['chSway']:.2f}")

    h = [t.text for t in texts if t.text and "[1]待机" in t.text]   # 帮助文字，不是按钮标签
    if h:
        print("⑤ 屏幕文字（功能 + 状态）：")
        for ln in h[0].split("\n"):
            print("   " + ln)
    else:
        print("⑤ ✗ 没找到帮助/状态文字")
        ok = False

    s = [t.text for t in texts if t.text and "预设通道" in t.text]  # 底部状态文字
    if s:
        print("⑥ 底部状态文字：")
        for ln in s[-1].split("\n"):
            print("   " + ln)

    print("结果：" + ("通过" if ok else "有问题"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
