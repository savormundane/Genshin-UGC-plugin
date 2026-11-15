"""逐个动作 / 逐个预设地量「它到底动了多少」，用来判断某个动作有没有被改坏。

为什么需要：verify_lua_anim.py 只检查"动作在播"，而一个动作完全可以在播却什么都不动
（比如通道被别的开关挡住、或者被新加的骨骼分支提前 return 掉）。
这里对每个动作单独跑一遍，量代表图元的位移与旋转峰值，跟基线（什么都不播）比。

用法：
    py -3 verify_actions.py --lua l2d_anim_10k.lua
    py -3 verify_actions.py --lua _参考_别人实机版_l2d_theater.lua
"""
import argparse
import math
import re
import sys
from pathlib import Path

from lupa import LuaRuntime

from l2d_verify_anim import install

ROOT = Path(__file__).resolve().parent.parent
DT = 1.0 / 60

# 每个动作/预设用哪几个部件来判断"动了没有"
WATCH = {"head": 13, "face_body": 15, "armR": 24, "hair": 1, "leg": 21}


def part_range(src, num):
    m = re.search(r"\{ n=%d, f=(\d+), t=(\d+)" % num, src)
    return (int(m.group(1)), int(m.group(2))) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lua", default="l2d_anim_10k.lua")
    args = ap.parse_args()
    path = ROOT / args.lua
    src = path.read_text(encoding="utf-8")
    EXPECT = len(re.findall(r'^  "[cel]\|', src, re.M))
    cfg = {"canvasW": float(re.search(r"canvasW\s*=\s*(\d+)", src).group(1)),
           "canvasH": float(re.search(r"canvasH\s*=\s*(\d+)", src).group(1))}

    controls, keybinds = [], []
    L = LuaRuntime(unpack_returned_tuples=True)
    state = install(L, controls, cfg, keybinds)
    L.execute(src)
    G = L.globals()
    G["OnInit"]()
    G["OnStart"]()
    ui_n = len(controls)
    frames = 0
    while len(controls) < ui_n + EXPECT and frames < 1500:
        G["OnUpdate"](DT)
        frames += 1
    if len(controls) - ui_n != EXPECT:
        print(f"✗ 图元数不符：{len(controls) - ui_n} / {EXPECT}")
        return 1
    idx = {k: ui_n + part_range(src, n)[0] - 1 for k, n in WATCH.items()}

    def settle(preset="idle", chans=None):
        G["SetPreset"](preset)
        G["SetBlink"]("off")
        G["SetGaze"](False)
        for c in ("sway", "turn", "nod", "wind", "armR", "talk", "eyeOpen", "browRaise"):
            G["SetChannel"](c, 0)
        if chans:
            for c, v in chans.items():
                G["SetChannel"](c, v)
        for _ in range(40):
            G["OnUpdate"](DT)

    def measure(frames_n=90):
        """量这段时间内各观察部件的位移/旋转峰值，以及"有效位移"的控件数。"""
        base = {k: (controls[i]["x"], controls[i]["y"], controls[i]["rot"]) for k, i in idx.items()}
        mx = {k: 0.0 for k in idx}
        rot = {k: 0.0 for k in idx}
        for _ in range(frames_n):
            G["OnUpdate"](DT)
            for k, i in idx.items():
                c = controls[i]
                if c["x"] is None or base[k][0] is None:
                    continue
                d = math.hypot(c["x"] - base[k][0], c["y"] - base[k][1])
                if d > mx[k]:
                    mx[k] = d
                dr = abs(c["rot"] - base[k][2])
                if dr > rot[k]:
                    rot[k] = dr
        return mx, rot

    CASES = [("基线(什么都不播)", {}),
             ("动作 摇头", {"act": "shake"}), ("动作 点头", {"act": "nodOnce"}),
             ("动作 惊讶", {"act": "surprise"}), ("动作 摆臂", {"act": "wave"}),
             ("动作 跳跃", {"act": "jump"}),
             ("预设 摆动", {"preset": "swayIdle"}), ("预设 风吹", {"preset": "wind"}),
             ("预设 说话", {"preset": "talk"}), ("预设 眯眼笑", {"preset": "smile"}),
             ("通道 转头", {"ch": {"turn": 1.0}}), ("通道 点头", {"ch": {"nod": 1.0}}),
             ("通道 摆臂", {"ch": {"armR": 1.0}}), ("通道 睁眼", {"ch": {"eyeOpen": 1.0}})]

    print(f"=== {path.name} · 逐动作位移峰值（画布像素 / 度）===")
    print(f"{'用例':<18}" + "".join(f"{k:>12}" for k in WATCH) + "   （单位 px，括号内为旋转度）")
    rows = {}
    for label, spec in CASES:
        if spec.get("act"):
            settle()
            # 动作要从干净状态起播，且先把动画打开
            G["SetAnimate"](True)
            ok = G["PlayAction"](spec["act"])
            mx, rot = measure(int(1.6 / DT))
        else:
            settle(spec.get("preset", "idle"), spec.get("ch"))
            mx, rot = measure(int(1.2 / DT))
        rows[label] = (mx, rot)
        cells = "".join(f"{mx[k]:>7.2f}({rot[k]:>3.1f})" for k in WATCH)
        print(f"{label:<18}{cells}")
    print("\n判读：任何一列全是 0.00 就说明那个通道没接上；"
          "对照两版同一行的数字即可看出哪个动作被改坏。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
