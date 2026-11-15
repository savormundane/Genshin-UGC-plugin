# -*- coding: utf-8 -*-
"""呼吸动作的 rig 定义与离线预览渲染。

**绘制顺序由文件名决定**：`parts/` 里的文件名数字越小越靠上层，
所以绘制顺序是数字从大到小（part_0026 先画、part_0000 最后画）。

运动设计沿用 Live2D 的思路：
  * 一个**主参数** breath = sin(2πt/T)；
  * 各部件按「权重 w」跟随即时呼吸量（躯干 1.0、头 1.55、腿 0.22 —— 脚基本不动）；
  * 头发 / 发尾 / 飘带这类软物用**延迟的呼吸量**（sin(2π(t−delay)/T)）驱动，
    这就是次级运动（secondary motion）—— 它们比身体慢半拍，所以看起来"甩"起来；
  * 旋转绕各部件自己的**轴心 pivot**（挂在头发上就绕发根转，不是绕图片中心）。

同一份 rig 数据同时供 Python 预览与 HTML 使用（attachments/l2d_rig.json）。
"""
import json
import math
import re
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "parts"

CANVAS = (411, 600)
PERIOD = 3.6          # 一次完整呼吸的秒数
AMP = 3.6             # 呼吸位移基准幅度（像素，按 600 高的画布）

# 运动参数表：key = 文件名里的编号
#   group  仅作文档/分组用
#   w      呼吸位移权重
#   delay  次级运动延迟（秒）
#   rot    呼吸旋转幅度（度，正值 = 顺时针）
#   pivot  旋转轴心（画布坐标）—— 发丝挂发根、手臂挂肩点
MOTION = {
    26: ("ribbon",   1.20, 0.26,  3.6, (160, 300)),   # 后飘带
    25: ("hairBack", 1.10, 0.14,  2.2, (190,  95)),   # 后发
    24: ("armR",     0.90, 0.12, -1.6, (258, 318)),   # 右臂
    23: ("body",     1.00, 0.06,  0.0, (214, 380)),   # 后背布
    22: ("legs",     0.22, 0.06,  0.0, (240, 392)),   # 右腿
    21: ("legs",     0.22, 0.06,  0.0, (200, 392)),   # 左腿
    20: ("body",     0.55, 0.06,  0.0, (229, 390)),   # 短裤
    19: ("armL",     0.90, 0.12,  1.6, (166, 312)),   # 左臂
    18: ("tailL",    1.10, 0.20, -3.2, (168, 236)),   # 左发尾
    17: ("bangs",    1.70, 0.16,  2.6, (300, 245)),   # 发饰(叶)
    16: ("tailR",    1.10, 0.20,  3.2, (286, 200)),   # 右发尾
    15: ("body",     1.00, 0.06,  0.0, (214, 300)),   # 衣服
    14: ("body",     1.05, 0.08,  0.0, (216, 302)),   # 围巾
    13: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 脸
    12: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 右眼白
    11: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 右瞳
    10: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 左眼白
     9: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 左瞳
     8: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 右睫毛+眼线
     7: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 左眼线
     6: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 左睫毛
     4: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 嘴
     3: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 右眉
     2: ("head",     1.55, 0.04,  0.0, (207, 300)),   # 左眉
     1: ("bangs",    1.65, 0.08,  0.9, (200, 120)),   # 前发
     0: ("bangs",    1.70, 0.12, -1.6, (150, 120)),   # 头发花装饰
}
DEFAULT = ("body", 1.0, 0.06, 0.0, (CANVAS[0] // 2, CANVAS[1] // 2))


def discover(src=SRC):
    """扫描零件目录，按「数字从大到小」返回绘制顺序。

    返回 [(num, file, name), ...]
    """
    items = []
    for p in src.glob("*.png"):
        m = re.search(r"part_(\d+)", p.name)
        if not m:
            continue
        num = int(m.group(1))
        name = p.stem.split("_", 2)[-1]
        items.append((num, p.name, name))
    items.sort(key=lambda x: -x[0])      # 数字越大越先画 = 越靠下层
    return items


def build_rig(src=SRC):
    rig = []
    for num, fname, name in discover(src):
        g, w, d, r, pivot = MOTION.get(num, DEFAULT)
        rig.append({"num": num, "file": fname, "name": name, "group": g,
                    "w": w, "delay": d, "rot": r, "pivot": list(pivot)})
    return rig


def to_rig_json():
    return {
        "canvas": {"w": CANVAS[0], "h": CANVAS[1]},
        "period": PERIOD,
        "amp": AMP,
        "draw_order": "文件名编号从大到小（数字越小越靠上层）",
        "note": ("呼吸：breath=sin(2πt/T)；部件按权重 w 跟随；"
                 "软物用 sin(2π(t-delay)/T) 做次级运动；旋转绕 pivot"),
        "parts": build_rig(),
    }


def render_frame(t, src=SRC, canvas=CANVAS, scale=1.0):
    """按时间 t（秒）渲染一帧，返回 RGBA Image。"""
    W, H = canvas
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for p in build_rig(src):
        b = math.sin(2 * math.pi * (t - p["delay"]) / PERIOD)
        dy = -AMP * p["w"] * b
        rot = p["rot"] * b
        im = Image.open(src / p["file"]).convert("RGBA")
        if abs(rot) > 1e-6:
            im = im.rotate(-rot, resample=Image.BICUBIC, center=tuple(p["pivot"]))
        if abs(dy) > 1e-6:
            im = im.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -dy),
                              resample=Image.BICUBIC)
        out.alpha_composite(im)
    if scale != 1.0:
        out = out.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    return out


def render_flat(src=SRC, canvas=CANVAS):
    """不动的一帧（纯按绘制顺序叠），用来核对层次。"""
    W, H = canvas
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for p in build_rig(src):
        out.alpha_composite(Image.open(src / p["file"]).convert("RGBA"))
    return out


def main():
    (HERE / "rig.json").write_text(
        json.dumps(to_rig_json(), ensure_ascii=False, indent=1), encoding="utf-8")

    outdir = ROOT / "_过程产物"
    outdir.mkdir(exist_ok=True)

    # 静态层序核对
    flat = render_flat()
    bg = Image.new("RGB", flat.size, (235, 235, 240))
    bg.paste(flat, (0, 0), flat)
    bg.save(outdir / "_手动拆分_文件名倒序.png")

    # 分帧
    n = 6
    frames = [render_frame(PERIOD * i / n) for i in range(n)]
    cw, ch = CANVAS
    sheet = Image.new("RGB", (cw * 3 // 2, ch), (235, 235, 240))
    for i, fr in enumerate(frames):
        small = fr.resize((cw // 2, ch // 2), Image.LANCZOS)
        b = Image.new("RGB", small.size, (235, 235, 240))
        b.paste(small, (0, 0), small)
        sheet.paste(b, ((i % 3) * (cw // 2), (i // 3) * (ch // 2)))
    sheet.save(outdir / "_呼吸_分帧.png")

    # 位移对照
    a, b2 = render_frame(0.0), render_frame(PERIOD / 4)
    ov = Image.new("RGB", CANVAS, (255, 255, 255))
    ov.paste(Image.new("RGB", CANVAS, (255, 60, 60)), (0, 0),
             a.split()[3].point(lambda v: 100 if v > 40 else 0))
    ov.paste(Image.new("RGB", CANVAS, (40, 90, 255)), (0, 0),
             b2.split()[3].point(lambda v: 100 if v > 40 else 0))
    ov.save(outdir / "_呼吸_位移对照.png")
    print(f"rig.json 写出；部件 {len(build_rig())} 个；分帧/对照图已更新")


if __name__ == "__main__":
    main()
