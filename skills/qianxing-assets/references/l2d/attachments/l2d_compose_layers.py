"""按顺序合成同尺寸图层，并统计"每层实际露出来多少像素"。

两件事（对应知识库 01 的 1.5②③）：
  ① 合成一张对照图 —— 提前发现层序错了 / 位置偏了
  ② 统计每层叠加后被上层盖住多少 —— 露出 0px 的层不能删（动画一动就会露），但拟合预算可以给最低

绘制顺序：文件名编号**从大到小**（数字小的在上层）。

用法：
    py -3 l2d_compose_layers.py <图层目录> --out 对照.png
    py -3 l2d_compose_layers.py <图层目录> --bg 32,34,40     # 铺深色底，看得清白边
    py -3 l2d_compose_layers.py <图层目录> --ref 原画.png     # 和原画并排，检查错位
"""
import argparse
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load_layers(d: Path):
    """返回 [(编号, 名字, ndarray)]，按绘制顺序（编号从大到小）。"""
    out = []
    for p in sorted(d.glob("part_*.png")):
        m = re.match(r"part_(\d{4})", p.stem)
        if not m:
            continue
        out.append((int(m.group(1)), p.name, np.asarray(Image.open(p).convert("RGBA"), np.float64)))
    out.sort(key=lambda t: -t[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="图层目录（part_NNNN_*.png）")
    ap.add_argument("--out", default="compose.png", help="输出的对照图")
    ap.add_argument("--bg", default="", help="底色 R,G,B；留空 = 透明底")
    ap.add_argument("--ref", default="", help="原画，提供则并排对照")
    ap.add_argument("--zoom", type=int, default=2, help="放大倍数（默认 2，方便看边缘）")
    args = ap.parse_args()

    layers = load_layers(Path(args.dir))
    if not layers:
        print(f"没找到图层：{args.dir}/part_*.png")
        return 2
    h, w = layers[0][2].shape[:2]
    for num, name, arr in layers:
        if arr.shape[:2] != (h, w):
            print(f"✗ {name} 尺寸 {arr.shape[1]}x{arr.shape[0]} ≠ {w}x{h}")
            return 1

    # 合成（over）：acc = acc*(1-a) + c*a
    acc_a = np.zeros((h, w))
    acc_c = np.zeros((h, w, 3))
    exposed = []
    for num, name, arr in layers:
        a = arr[:, :, 3] / 255.0
        own = a > 0.5
        exposed.append((num, name, int(own.sum()), int((own & (acc_a < 0.5)).sum())))
        acc_c = acc_c * (1 - a[..., None]) + arr[:, :, :3] * a[..., None]
        acc_a = acc_a + (1 - acc_a) * a

    print(f"图层 {len(layers)} 个，画布 {w}x{h}")
    print(f"{'编号':<6}{'层':<34}{'自身px':>9}{'露出px':>9}{'被盖住':>8}")
    for num, name, own, exp in exposed:
        hidden = 100 - exp * 100 // max(1, own)
        flag = "   ← 几乎全被盖住（不能删，动画会露）" if exp * 100 // max(1, own) <= 2 else ""
        print(f"{num:<6}{name[:33]:<34}{own:>9}{exp:>9}{hidden:>7}%{flag}")

    def to_img(a, c, bg):
        rgb = np.clip(c, 0, 255)
        if bg is not None:
            b = np.array(bg, np.float64)
            rgb = rgb * a[..., None] + b * (1 - a[..., None])
            al = np.full((h, w), 255.0)
        else:
            al = np.clip(a * 255, 0, 255)
        return Image.fromarray(
            np.dstack([rgb, al]).astype(np.uint8), "RGBA" if bg is None else "RGB")

    bg = tuple(int(v) for v in args.bg.split(",")) if args.bg else None
    mine = to_img(acc_a, acc_c, bg)

    panels = [mine]
    if args.ref:
        ref = Image.open(args.ref).convert("RGBA")
        if ref.size != (w, h):
            ref = ref.resize((w, h), Image.LANCZOS)
        panels.insert(0, to_img(np.asarray(ref, np.float64)[:, :, 3] / 255.0,
                                np.asarray(ref, np.float64)[:, :, :3], bg))

    z = max(1, args.zoom)
    gap = 8
    W = sum(p.width for p in panels) + gap * (len(panels) - 1)
    out = Image.new("RGB", (W, h), (60, 60, 66))
    x = 0
    for p in panels:
        out.paste(p.convert("RGB"), (x, 0))
        x += p.width + gap
    if z > 1:
        out = out.resize((out.width * z, out.height * z), Image.NEAREST)
    out.save(args.out)
    print(f"\n写出 {args.out}（{len(panels)} 格并排"
          f"{'：原画 | 合成' if args.ref else '：仅合成'}{f'，放大 {z}×' if z > 1 else ''}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
