"""边缘探针：把「白描边」这件事量出来，并输出放大对照图。

结论先行（本脚本的作用就是验证它）：超拟合的轮廓外溢只有 0.9%（见 edge_clean.py），
所以用户看到的浅色描边**不是几何问题，是颜色问题** —— 由拟合输入造成：
超拟合先把部件图 Lanczos 放大 3 倍，而 PIL 的 resize 不做预乘 alpha，
原图透明区的 RGB（多为白/黑）被卷进轮廓最外 1~3px 的半透明像素，
拟合器照着这些偏亮像素取样，于是轮廓最外一圈被拟成浅色。

本脚本做三件事：
  ① 量「轮廓内侧 0~3px 环带」的颜色误差，以及它是不是单向偏亮（比源图更白）
  ② 量外溢质量（复算 edge_clean 的结论，交叉验证）
  ③ 出放大对照图：源图 / 超拟合 / 按源图校正颜色后
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

import l2d_raster as raster


def erode(mask, iterations):
    """3x3 二值腐蚀（不引 scipy：这个环境里只有 numpy/PIL）。"""
    m = mask.astype(bool).copy()
    for _ in range(max(0, iterations)):
        p = np.pad(m, 1, constant_values=False)
        m = (p[0:-2, 0:-2] & p[0:-2, 1:-1] & p[0:-2, 2:] &
             p[1:-1, 0:-2] & p[1:-1, 1:-1] & p[1:-1, 2:] &
             p[2:, 0:-2] & p[2:, 1:-1] & p[2:, 2:])
    return m

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPLIT = ROOT / "parts"
HF = ROOT / "parts" / "_超拟合_10k"


def source_composite(w=411, h=600):
    """按绘制顺序（编号大→小）合成 26 个原图层的硬边参考。"""
    acc_a = np.zeros((h, w), np.float64)
    acc_c = np.zeros((h, w, 3), np.float64)
    for p in sorted(SPLIT.glob("part_*.png"), key=lambda q: -int(q.stem[5:9])):
        arr = np.asarray(Image.open(p).convert("RGBA"), np.float64)
        a = arr[:, :, 3] / 255.0
        acc_c = acc_c * (1 - a[..., None]) + arr[:, :, :3] * a[..., None]
        acc_a = acc_a + (1 - acc_a) * a
    return acc_a, np.clip(acc_c, 0, 255)


def hf_shapes():
    """超拟合图元，按绘制顺序（编号大→小）拼接。"""
    out = []
    for d in sorted(HF.iterdir(), key=lambda q: -int(q.name[5:9]) if q.name.startswith("part_") else 0):
        if d.is_dir() and d.name.startswith("part_"):
            out += json.loads((d / "shapes.json").read_text(encoding="utf-8"))["shapes"]
    return out


def fixed_shapes(min_inside=0.12, radius=2, strength=1.0, drop=True, trim=True):
    """按原图硬 alpha 修好的图元：剔溢出 + 缩回轮廓 + 轮廓颜色拉回真值。

    逐部件处理（剔溢出只认本层自己的 alpha —— 它定义了这层的内容在哪），
    但**缩边界认整身并集**：只有超出整个角色轮廓的部分才会在暗背景上显出浅色描边，
    超出本层却被上层盖住是正常的，缩了会白掉内容。
    """
    import edge_clean as EC
    union = EC.union_mask(SPLIT)
    out, stats = [], []
    for d in sorted(HF.iterdir(), key=lambda q: -int(q.name[5:9]) if q.name.startswith("part_") else 0):
        if not (d.is_dir() and d.name.startswith("part_")):
            continue
        num = int(d.name[5:9])
        png = next(SPLIT.glob(f"part_{num:04d}_*.png"))
        sh = json.loads((d / "shapes.json").read_text(encoding="utf-8"))["shapes"]
        mask = EC.mask_of(png)
        rgb, al = EC.rgb_of(png)
        kept, cs = EC.clean_part(sh, mask, min_inside) if drop else (list(sh), {"dropped": 0})
        kept, ts = EC.trim_part(kept, union) if trim else (kept, {"trimmed": 0})
        kept, rs = EC.restore_edge_colors(kept, mask, rgb, al, radius, strength)
        out += kept
        stats.append((d.name, cs, ts, rs))
    return out, stats


def ring_mask(mask, px):
    """轮廓内侧 0~px 的一圈（用二值腐蚀取差集）。"""
    er = erode(mask, px + 1)
    return mask & ~er


def unpremult(rgb, a):
    """raster.rasterize 返回的是**预乘 alpha** 的颜色（composite over transparent），
    比较/铺底前必须先除回来 —— 否则轮廓上半透明像素会被二次乘 alpha、显得偏暗，
    把"白边"这件事量反（本项目踩过一次）。"""
    return rgb / np.clip(a, 0.004, 1.0)[..., None]


def on_bg(rgb, al, bg):
    """把（未预乘的）颜色按 alpha 合成到不透明底色上。"""
    return np.clip(rgb * al[..., None] + np.array(bg) * (1 - al[..., None]), 0, 255)


def stats_ring(rec_a, rec_c, ref_a, ref_c, mask, px=3):
    """环带内：重建 vs 源的颜色误差，以及「偏亮」的占比（两边都先还原成非预乘色）。"""
    r = ring_mask(mask, px) & (ref_a > 0.9) & (rec_a > 0.9)
    if r.sum() == 0:
        return None
    d = unpremult(rec_c, rec_a)[r] - unpremult(ref_c, ref_a)[r]
    lum = d.mean(axis=1)
    return {
        "px": int(r.sum()),
        "abs_err": float(np.abs(d).mean()),
        "signed_lum": float(lum.mean()),
        "brighter_ratio": float((lum > 8).mean()),
        "darker_ratio": float((lum < -8).mean()),
        # 直接数「明显偏亮」的像素 —— 这就是用户看到的白描边
        "white_px": int((lum > 25).sum()),
        "dark_px": int((lum < -25).sum()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "edge_diagnosis.png"))
    ap.add_argument("--min-inside", type=float, default=0.12)
    ap.add_argument("--radius", type=int, default=2, help="轮廓颜色修正的作用半径（源图像素）")
    ap.add_argument("--strength", type=float, default=1.0)
    args = ap.parse_args()

    ref_a, ref_c = source_composite()
    mask = ref_a > 0.5
    shapes = hf_shapes()
    a, c = raster.rasterize(shapes, 411, 600)
    u_ref = unpremult(ref_c, ref_a)          # 后面多处要用，先还原成非预乘色

    print(f"图元 {len(shapes)} 个；轮廓遮罩 {int(mask.sum())} px")
    outside = float((a * (~mask)).sum())
    print(f"轮廓外溢质量：{outside:,.0f}（重建总质量 {a.sum():,.0f}，"
          f"{outside / max(1e-9, a.sum()) * 100:.3f}%）")

    # 环带逐层：看误差是否随「越靠外」而变大 —— 若变大，即典型的放大卷边
    print("\n轮廓内侧环带（越靠外越小圈）：")
    for px in (0, 1, 2, 3, 6):
        s = stats_ring(a, c, ref_a, ref_c, mask, px)
        if s:
            print(f"  {px}px: {s['px']:>6} px   |Δ|={s['abs_err']:5.2f}  "
                  f"带符号亮度={s['signed_lum']:+6.2f}  偏亮(>8)={s['brighter_ratio'] * 100:5.1f}%"
                  f"  明显偏亮(>25)={s['white_px']:>5} px")

    # ── 修正后：剔溢出 + 轮廓颜色拉回真值 ──
    fx, fstats = fixed_shapes(args.min_inside, args.radius, args.strength)
    fa, fc = raster.rasterize(fx, 411, 600)
    print(f"\n修复：图元 {len(shapes)} → {len(fx)}"
          f"（删 {sum(s[1].get("dropped", 0) for s in fstats)}，"
          f"缩回 {sum(s[2].get('trimmed', 0) for s in fstats)}，"
          f"改色 {sum(s[3]['changed'] for s in fstats)}，"
          f"平均下调 {np.mean([s[3]['mean_shift'] for s in fstats if s[3]['changed']] or [0]):.1f}/通道）")
    f_out = float((fa * (~mask)).sum())
    print(f"轮廓外溢：{outside:,.0f} → {f_out:,.0f}")
    print("修复后环带：")
    for px in (0, 1, 2, 3, 6):
        s = stats_ring(fa, fc, ref_a, ref_c, mask, px)
        if s:
            print(f"  {px}px: {s['px']:>6} px   |Δ|={s['abs_err']:5.2f}  "
                  f"带符号亮度={s['signed_lum']:+6.2f}  偏亮(>8)={s['brighter_ratio'] * 100:5.1f}%"
                  f"  明显偏亮(>25)={s['white_px']:>5} px")
    b3 = stats_ring(a, c, ref_a, ref_c, mask, 1)
    f3 = stats_ring(fa, fc, ref_a, ref_c, mask, 1)
    if b3 and f3:
        print(f"  → 最外 1px 环的「明显偏亮」像素：{b3['white_px']} → {f3['white_px']}"
              f"（降 {100 - f3['white_px'] / max(1, b3['white_px']) * 100:.0f}%）")
    # 全域 RMSE（轮廓内两者都覆盖处），防止"修了边、坏了里面"
    inner = erode(mask, 3) & (ref_a > .9) & (a > .5) & (fa > .5)
    for name, arr, al in (("未修", c, a), ("修复", fc, fa)):
        e = unpremult(arr, al)[inner] - u_ref[inner]
        print(f"  内部(离轮廓>3px) RMSE {name}: {np.sqrt((e ** 2).mean()):.2f}")

    # 外圈 0~3px 的图元颜色 vs 源图同位置：直接验证"拟成了浅色"
    print("\n外圈(0~3px)按源图校正的可行性：")
    ring = ring_mask(mask, 3)
    ys, xs = np.nonzero(ring)
    print(f"  环带像素 {len(ys)}，源图不透明且重建也覆盖的："
          f"{int(((ref_a[ring] > .9) & (a[ring] > .5)).sum())}")

    # 对照图：源 / 超拟合 / 白底 / 差异（红=重建偏亮、蓝=偏暗）
    u_rec, u_ref = unpremult(c, a), unpremult(ref_c, ref_a)
    rgb8 = np.clip(u_rec, 0, 255).astype(np.uint8)
    ref8 = np.clip(u_ref, 0, 255).astype(np.uint8)

    diff = np.full((a.shape[0], a.shape[1], 3), 26, np.uint8)
    vis = mask & (a > 0.35) & (ref_a > 0.35)
    dl = u_rec.mean(axis=2) - u_ref.mean(axis=2)
    diff[..., 0] = np.where(vis & (dl > 10), 255, 26)
    diff[..., 2] = np.where(vis & (dl < -10), 255, 26)
    diff[..., 1] = np.where(vis & (np.abs(dl) <= 10), 90, 26)

    panels = [("源图", on_bg(ref8, ref_a, (26, 28, 34)).astype(np.uint8)),
              ("未修", on_bg(rgb8, a, (26, 28, 34)).astype(np.uint8)),
              ("修复", on_bg(np.clip(unpremult(fc, fa), 0, 255).astype(np.uint8), fa,
                            (26, 28, 34)).astype(np.uint8)),
              ("修复·白底", on_bg(np.clip(unpremult(fc, fa), 0, 255).astype(np.uint8), fa,
                                (255, 255, 255)).astype(np.uint8))]
    clipped = float(((fa * mask) * (~mask)).sum())
    print(f"  （参考）若再按轮廓裁一刀，外溢质量可到 {clipped:,.0f} —— 但 HTML 已按要求"
          f"去掉轮廓遮罩，这里只看纯数据级修复的效果")
    # 只取轮廓外缘的小窗口放大 6 倍 —— 白描边在整身上只有 1~3px，不放大看不出来
    crops = [("头发外缘", 70, 130, 105, 165), ("肩部外缘", 300, 360, 115, 175),
             ("靴子外缘", 515, 575, 160, 220)]
    Z = 6
    rows = []
    for _cname, y0, y1, x0, x1 in crops:
        row = [np.kron(arr[y0:y1, x0:x1], np.ones((Z, Z, 1), np.uint8)) for _p, arr in panels]
        rows.append(np.concatenate(row, axis=1))
    gap = np.full((6, rows[0].shape[1], 3), 70, np.uint8)
    sep = np.concatenate([x for pair in zip(rows, [gap] * len(rows)) for x in pair][:-1], axis=0)
    Image.fromarray(sep).save(args.out)
    print(f"\n对照图（列：{' / '.join(p for p, _ in panels)}；行：{'、'.join(c[0] for c in crops)}）")
    print(f"写出 {args.out}")


if __name__ == "__main__":
    main()
