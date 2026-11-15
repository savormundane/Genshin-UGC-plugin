"""图层自检：手扣完（PS 导出后）立刻跑一遍，确认这组图层符合流水线的前提。

检查四项（对应知识库 01 的"导出后自检"）：
  ① 所有层尺寸一致
  ② 有没有中间 alpha（有 = 混进了抗锯齿，见知识库 06）
  ③ 透明区的 RGB 是什么颜色（它会在拟合放大时卷进边缘，见知识库 02）
  ④ 编号是否连续、有没有重号

用法：
    py -3 l2d_check_layers.py <图层目录>
    py -3 l2d_check_layers.py <图层目录> --expect 411x600
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="图层目录（part_NNNN_*.png）")
    ap.add_argument("--expect", default="", help="期望尺寸，如 411x600；不填则取第一层")
    ap.add_argument("--core-alpha", type=int, default=32, help="核心阈值（保留参数，统计用）")
    args = ap.parse_args()

    d = Path(args.dir)
    files = sorted(d.glob("part_*.png"))
    if not files:
        print(f"没找到图层：{d}/part_*.png")
        return 2

    expect = None
    if args.expect:
        w, h = args.expect.lower().split("x")
        expect = (int(w), int(h))

    nums, sizes, transparent_rgb = [], Counter(), []
    bad = 0
    print(f"{'文件':<40}{'尺寸':>12}{'中间alpha':>11}{'不透明px':>10}  透明区RGB")
    for p in files:
        a = np.asarray(Image.open(p).convert("RGBA"))
        al = a[:, :, 3]
        mid = int(((al > 0) & (al < 255)).sum())
        solid = int((al >= 250).sum())
        tr = al == 0
        rgb_mean = (
            tuple(int(v) for v in a[:, :, :3][tr].mean(axis=0).round(0)) if tr.any() else None
        )
        if rgb_mean:
            transparent_rgb.append(rgb_mean)
        m = re.match(r"part_(\d{4})", p.stem)
        if m:
            nums.append(int(m.group(1)))
        sizes[(a.shape[1], a.shape[0])] += 1
        if expect and (a.shape[1], a.shape[0]) != expect:
            bad += 1
        print(f"{p.name:<40}{a.shape[1]}x{a.shape[0]:<7}{mid:>11}{solid:>10}  {rgb_mean}")

    print()
    ok = True

    # ① 尺寸
    if len(sizes) == 1:
        w, h = next(iter(sizes))
        print(f"① 尺寸：{len(files)} 层全部为 {w}x{h} ✓")
        if expect and (w, h) != expect:
            print(f"   ✗ 与期望 {expect[0]}x{expect[1]} 不符")
            ok = False
    else:
        print(f"① 尺寸：✗ 不一致 —— {dict(sizes)}（下游坐标会全乱）")
        ok = False

    # ② 中间 alpha
    mid_total = 0
    for p in files:
        al = np.asarray(Image.open(p).convert("RGBA"))[:, :, 3]
        mid_total += int(((al > 0) & (al < 255)).sum())
    if mid_total == 0:
        print("② alpha：全部为二值（0/255）✓ —— 可以按知识库 06 的「硬边」路线走")
    else:
        pct = mid_total / max(1, sum(int((np.asarray(Image.open(q).convert("RGBA"))[:, :, 3] > 0).sum()) for q in files)) * 100
        print(f"② alpha：⚠ 有 {mid_total} 个中间 alpha 像素（{pct:.2f}%）——")
        print("   说明混进了抗锯齿/羽化。要么回去关掉「消除锯齿」重新导出，")
        print("   要么接受「软边」路线（知识库 06 里两种路线的判据不同）")

    # ③ 透明区 RGB
    if transparent_rgb:
        r = int(np.mean([c[0] for c in transparent_rgb]))
        g = int(np.mean([c[1] for c in transparent_rgb]))
        b = int(np.mean([c[2] for c in transparent_rgb]))
        note = ""
        if min(r, g, b) > 230:
            note = "← 近白：拟合放大前必须先把透明区染成邻居颜色（知识库 02/06）"
        elif max(r, g, b) < 25:
            note = "← 近黑：同样会卷进边缘，只是方向相反"
        print(f"③ 透明区 RGB：均值 ({r}, {g}, {b})  {note}")

    # ④ 编号
    if nums:
        dup = [n for n, c in Counter(nums).items() if c > 1]
        missing = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        rng = f"{min(nums):04d}~{max(nums):04d}"
        msg = f"④ 编号：{len(nums)} 个，范围 {rng}"
        if dup:
            msg += f"  ✗ 重号 {sorted(dup)}"
            ok = False
        if missing:
            msg += f"  缺号 {[f'{m:04d}' for m in missing]}（正常，人工删过层就会有）"
        if not dup:
            msg += " ✓"
        print(msg)

    print("\n结论：" + ("可以进入拟合阶段（知识库 02）" if ok else "先修上面标 ✗ 的问题"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
