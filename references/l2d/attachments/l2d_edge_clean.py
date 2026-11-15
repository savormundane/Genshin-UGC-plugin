"""按原图硬 alpha 剔除「溢出轮廓」的图元，并给出可审计的量化报告。

## 为什么需要它

超拟合是在**放大 3 倍**的部件图上做的（`_upscaled/part_*_x3.png`），而放大用的是
Lanczos。PIL 的 resize **不做预乘 alpha**：原图透明区的 RGB（往往是白或黑）会被卷进
轮廓最外 1~3px 的半透明像素里，拟合器再把这些偏亮的像素当内容去拟合 ——
结果就是成品轮廓外侧多出一圈浅色小图元（用户看到的"白色描边"）。

这条链路上能改的三处：
  ① 拟合输入（改 `superfit.py` 的放大方式，需要重跑，不是本轮范围）
  ② **拟合输出**：把落在该部件原始 alpha 之外的图元剔掉 ← 本文件
  ③ 显示层：合成后整体按原图硬 alpha 裁剪（HTML 可做，Lua 无 stencil 掩膜做不了）

②是唯一对 Lua 也有效的办法，所以这里是重点。判据只用**空间**（在不在原图内容里），
不看颜色 —— 按"白色"去删会误伤花朵、衣服金边和瞳孔高光，实测那三处本来就有大片
近白像素。

## 判据

对每个图元按自身椭圆形状均匀撒点，统计落在该部件原始 alpha 内的比例 `inside`：

  · `inside < --min-inside`（默认 0.12）→ 判为溢出，删除
  · 其余保留；**不做缩放修剪**（缩了会在轮廓上啃出缺口，比一圈浅边更难看）

保守取 0.12 的理由：图元是拟合出来的近似，边缘本来就允许有误差；真正的溢出是
"整块都在透明区里"，那种图元的 inside 基本是 0~0.05，两者分得很开（见报告直方图）。
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_SOURCE = ROOT / "parts" / "_超拟合_10k"
DEFAULT_MASK = ROOT / "parts"

# 判定用的采样密度（每轴的格子数，总采样 = N²）
GRID = 9


def erode(mask, iterations):
    """3x3 二值腐蚀（本环境只有 numpy/PIL，不引 scipy）。"""
    m = mask.astype(bool).copy()
    for _ in range(max(0, iterations)):
        p = np.pad(m, 1, constant_values=False)
        m = (p[0:-2, 0:-2] & p[0:-2, 1:-1] & p[0:-2, 2:] &
             p[1:-1, 0:-2] & p[1:-1, 1:-1] & p[1:-1, 2:] &
             p[2:, 0:-2] & p[2:, 1:-1] & p[2:, 2:])
    return m


def dist_inside(mask, radius):
    """每像素到轮廓的距离（只算内侧，0=边界，>=radius 一律记 radius，外部记 -1）。"""
    d = np.zeros(mask.shape, np.int32)
    m = mask.copy()
    for k in range(1, radius + 1):
        m = erode(m, 1)
        d[m] = k
    return np.where(mask, d, -1)


def mask_of(png: Path) -> np.ndarray:
    """部件原始 PNG 的硬 alpha（手扣层是严格二值，阈值只防万一）。"""
    return np.asarray(Image.open(png).convert("RGBA"))[:, :, 3] >= 128


def rgb_of(png: Path):
    """部件原始 PNG 的 RGB 与 alpha（颜色修正的真值来源）。"""
    a = np.asarray(Image.open(png).convert("RGBA"))
    return a[:, :, :3].astype(np.float64), a[:, :, 3]


def union_mask(mask_dir: Path, nums=None) -> np.ndarray:
    """整身轮廓：所有部件 alpha 的并集。"""
    acc = None
    for p in sorted(mask_dir.glob("part_*.png")):
        if nums is not None and int(p.stem[5:9]) not in nums:
            continue
        m = mask_of(p)
        acc = m if acc is None else (acc | m)
    return acc


def shape_axes(s: dict):
    """图元 → (rx, ry, 弧度)。circle 没有 a 字段。"""
    if s["t"] == "circle":
        r = float(s.get("r", 0.0))
        return r, r, 0.0
    return float(s.get("rx", 0.0)), float(s.get("ry", 0.0)), float(s.get("a", 0.0))


def probe_shape(s, mask, dist, src_rgb, src_a, radius=2, grid=GRID, scale=1.0):
    """一次撒点算出图元的三件事：在不在内容里、离轮廓多近、覆盖处的原图颜色。

    在**图元局部坐标**里均匀撒点（按椭圆归一化，天然是等面积权重），再旋转变换回
    画布坐标。比"取几个轮廓点"稳，也不会被细长 ellipse 骗。
    `scale` 用来评估"把这个图元缩到多少倍"，修剪时靠它做二分。
    """
    rx, ry, ang = shape_axes(s)
    rx, ry = rx * scale, ry * scale
    if rx <= 0 or ry <= 0:
        return None
    h, w = mask.shape
    ca, sa = math.cos(ang), math.sin(ang)
    tot = hit = 0
    dmin = 1 << 30
    cols = []
    for iy in range(grid):
        v = ((iy + 0.5) / grid * 2 - 1) * ry
        for ix in range(grid):
            u = ((ix + 0.5) / grid * 2 - 1) * rx
            if (u / rx) ** 2 + (v / ry) ** 2 > 1.0:
                continue
            tot += 1
            x = int(round(s["x"] + u * ca - v * sa))
            y = int(round(s["y"] + u * sa + v * ca))
            if not (0 <= x < w and 0 <= y < h):
                continue
            if mask[y, x]:
                hit += 1
                if dist[y, x] < dmin:
                    dmin = dist[y, x]
                if src_a[y, x] >= 128:
                    cols.append(src_rgb[y, x])
    if tot == 0:
        return None
    cx, cy = int(round(s["x"])), int(round(s["y"]))
    center_in = 0 <= cx < w and 0 <= cy < h and bool(mask[cy, cx])
    true_rgb = np.mean(cols, axis=0) if cols else None
    return {"inside": hit / tot, "center_in": center_in,
            "dmin": (dmin if dmin < (1 << 30) else radius), "true_rgb": true_rgb}


def _probe_quiet(s, mask, dist, grid, scale):
    """只问"在内容里的比例"，不带颜色采样（修剪时要跑很多次，省掉取色）。"""
    blank_rgb = np.zeros((*mask.shape, 3))
    blank_a = np.zeros(mask.shape, np.uint8)
    pr = probe_shape(s, mask, dist, blank_rgb, blank_a, grid=grid, scale=scale)
    return pr["inside"] if pr else 0.0


def trim_part(shapes, mask, max_out=0.02, min_scale=0.55, grid=9, tol=0.02):
    """把**跨出轮廓**的图元缩回轮廓内。

    为什么必须有这一步：删掉"整块在轮廓外"的图元（clean_part）不够 ——
    真正画出那圈浅色描边的是**一半在里、一半在外**的图元：轮廓是硬切的，
    而圆/椭圆是拼接的，边缘总有几个图元鼓出去 1~3px。在暗背景上，鼓出去的
    那几像素就是用户看到的"白色描边"。Lua 侧没有 stencil 掩膜，只能在这里解决。

    做法：绕**图元自己的中心**缩小（不移动中心，所以不会把内容挪位），
    二分找最大的缩放比 f，使露在轮廓外的面积 ≤ max_out。缩到底还超标才交给
    clean_part 去删（那种通常是真的溢出，不是边界鼓包）。

    代价：`max_out` 是"宁可轮廓略瘦一点，也不要外面挂一圈浅边"的取舍；
    2% 是实测出来的 —— 再小会把勾线啃出缺口。
    """
    dist = dist_inside(mask, 4)
    out = []
    trimmed = 0
    shrink_sum = 0.0
    outside_before = outside_after = 0.0
    touched = 0
    for s in shapes:
        ins = _probe_quiet(s, mask, dist, grid, 1.0)
        if ins >= 1.0 - max_out:
            out.append(s)
            continue
        touched += 1
        outside_before += (1.0 - ins)
        lo, hi = min_scale, 1.0
        best = min_scale
        for _ in range(5):
            mid = 0.5 * (lo + hi)
            if _probe_quiet(s, mask, dist, grid, mid) >= 1.0 - max_out:
                best = mid
                lo = mid
            else:
                hi = mid
        if best >= 0.995:
            out.append(s)
            continue
        t = dict(s)
        if t["t"] == "circle":
            t["r"] = s["r"] * best
        else:
            t["rx"] = s["rx"] * best
            t["ry"] = s["ry"] * best
        out.append(t)
        trimmed += 1
        shrink_sum += (1.0 - best)
        outside_after += (1.0 - _probe_quiet(t, mask, dist, grid, 1.0))
    return out, {"trimmed": trimmed, "touched": touched,
                 "mean_shrink": (shrink_sum / trimmed if trimmed else 0.0),
                 "outside_before": round(outside_before, 1),
                 "outside_after": round(outside_after, 1)}


def clean_part(shapes, mask, min_inside=0.12):
    """剔除溢出图元。返回 (保留, 统计)。

    统计里带直方图，便于事后判断阈值选得是否合理（而不是只看一个"删了多少"）。
    """
    dist = dist_inside(mask, 4)
    blank_rgb = np.zeros((*mask.shape, 3), np.float64)
    blank_a = np.zeros(mask.shape, np.uint8)
    kept, dropped = [], []
    hist = [0] * 10                       # inside 按 0.1 分箱
    low_alpha_drop = 0
    for s in shapes:
        pr = probe_shape(s, mask, dist, blank_rgb, blank_a)
        r = pr["inside"] if pr else 0.0
        hist[min(9, int(r * 10))] += 1
        if r < min_inside:
            dropped.append({"x": round(s["x"], 1), "y": round(s["y"], 1),
                            "inside": round(r, 3), "center_in": pr["center_in"] if pr else False,
                            "rgba": s.get("rgba")})
            if s.get("rgba", [0, 0, 0, 255])[3] < 64:
                low_alpha_drop += 1
        else:
            kept.append(s)
    st = {"total": len(shapes), "kept": len(kept), "dropped": len(dropped),
          "low_alpha_dropped": low_alpha_drop, "hist": hist,
          "sample_dropped": dropped[:12]}
    return kept, st


def restore_edge_colors(shapes, mask, src_rgb, src_a, radius=2, strength=1.0):
    """把"被白边污染"的轮廓图元颜色拉回原图真值。

    为什么只改轮廓：污染源是 ×3 Lanczos 放大（原图透明区是纯白，PIL 不做预乘 alpha，
    白色被卷进轮廓最外 1~3px），所以被污染的是**贴着轮廓**的那批图元；内部图元
    拟合得很好（实测内部环带误差远低于轮廓带），不该动。

    判据与做法：
      · 只处理"图形边界贴到轮廓"（inside<1）或中心离轮廓 ≤radius 的图元
      · 真值 = 该图元**自身覆盖范围内**原图不透明像素的均值（不是单点取样，抗噪）
      · **只往暗里修**：白边污染只会让图元比真值更亮，所以逐通道只下调、不上调 ——
        这样即使真值和拟合值本来就有偏差，也不会把已经对的地方改坏

    返回 (新图元表, 统计)。原表不动，便于对比。
    """
    dist = dist_inside(mask, radius + 1)
    out = []
    changed = 0
    shift_sum = 0.0
    for s in shapes:
        pr = probe_shape(s, mask, dist, src_rgb, src_a, radius=radius)
        if pr is None or pr["true_rgb"] is None:
            out.append(s)
            continue
        touches = pr["inside"] < 0.999 or pr["dmin"] <= radius
        # 越靠边、污染越重，权重越大；离轮廓 2px 以外基本没被污染
        w = 1.0 - max(0, min(radius, pr["dmin"])) / (radius + 1.0)
        w *= strength
        if not touches or w <= 0.01:
            out.append(s)
            continue
        cur = np.array(s["rgba"][:3], np.float64)
        tgt = pr["true_rgb"]
        new = np.where(cur > tgt, cur + (tgt - cur) * w, cur)   # 只下调
        d = float(np.abs(new - cur).mean())
        if d < 0.5:
            out.append(s)
            continue
        t = dict(s)
        t["rgba"] = [int(round(v)) for v in new] + [s["rgba"][3]]
        out.append(t)
        changed += 1
        shift_sum += d
    return out, {"changed": changed, "mean_shift": (shift_sum / changed if changed else 0.0)}


def load_parts(source: Path, mask_dir: Path, min_inside=0.12, nums=None, trim=True):
    """遍历部件目录 → {num: {"shapes":…, "clean":…, "stats":…}}（部件顺序 = 编号大→小）。

    两个 mask 用在不同环节，别混：
      · **本部件自己的 mask** → 剔溢出。部件的原始 alpha 定义了这层的内容在哪，
        落在外面的图元就是拟合噪声（而且动画时可能露出来）。
      · **整身并集 mask** → 缩边界。因为"超出本层、但被上层盖住"是正常的：
        只有**超出整个角色轮廓**的那部分才会在暗背景上显出浅色描边。

    处理顺序：先剔溢出、再缩边界、最后改色（缩边界改了尺寸，颜色取样必须排在它后面）。
    """
    out = {}
    union = union_mask(mask_dir, nums)
    for d in sorted(source.iterdir()):
        if not (d.is_dir() and d.name.startswith("part_")):
            continue
        num = int(d.name[5:9])
        if nums is not None and num not in nums:
            continue
        mp = next(mask_dir.glob(f"part_{num:04d}_*.png"), None)
        if mp is None:
            raise SystemExit(f"找不到部件 {num:04d} 的原始 PNG（{mask_dir}）")
        shapes = json.loads((d / "shapes.json").read_text(encoding="utf-8"))["shapes"]
        m = mask_of(mp)
        kept, st = clean_part(shapes, m, min_inside)
        if trim:
            kept, ts = trim_part(kept, union)
            st.update(ts)
        else:
            st.update({"trimmed": 0, "touched": 0, "mean_shrink": 0.0,
                       "outside_before": 0.0, "outside_after": 0.0})
        st["name"] = d.name
        st["mask_px"] = int(m.sum())
        out[num] = {"shapes": shapes, "clean": kept, "mask": m, "stats": st}
    return out


def outside_mass(shapes, mask):
    """把图元栅格化后，统计落在 mask 之外的 alpha 质量（= 用户看到的轮廓外浅边）。

    用项目共用的 raster 栅格化器（与验收图的画法一致），保证这个数字和肉眼看到的一致。
    """
    import raster
    a, _ = raster.rasterize(shapes, mask.shape[1], mask.shape[0])
    outside = a * (~mask)
    return float(outside.sum()), float(a.sum())


def report(args):
    parts = load_parts(Path(args.source), Path(args.mask_source), args.min_inside)
    union = union_mask(Path(args.mask_source), set(parts))

    tot_all = sum(v["stats"]["total"] for v in parts.values())
    tot_drop = sum(v["stats"]["dropped"] for v in parts.values())
    dirty = 0
    rows = []
    for num in sorted(parts, reverse=True):
        v = parts[num]
        if v["stats"]["dropped"] == 0:
            rows.append((num, v["stats"], None, None))
            continue
        dirty += 1
        raw = [s for s in v["shapes"]]
        # 逐部件比较：溢出质量（整身 mask 更有意义，但逐部件能量出"这层往哪溢出"）
        m_out, m_tot = outside_mass(raw, union)
        c_out, c_tot = outside_mass(v["clean"], union)
        rows.append((num, v["stats"], (m_out, m_tot), (c_out, c_tot)))

    print(f"部件 {len(parts)} 个，图元 {tot_all} 个，判为溢出 {tot_drop} 个"
          f"（{tot_drop / max(1, tot_all) * 100:.2f}%），涉及 {dirty} 个部件")
    tot_trim = sum(v["stats"].get("trimmed", 0) for v in parts.values())
    ob = sum(v["stats"].get("outside_before", 0) for v in parts.values())
    oa = sum(v["stats"].get("outside_after", 0) for v in parts.values())
    print(f"跨出轮廓被缩回：{tot_trim} 个图元；露在外面的面积占比合计 "
          f"{ob:.1f} → {oa:.1f}（相对各图元面积）")
    print(f"整身轮廓遮罩：{int(union.sum())} px\n")
    print(f"{'部件':<26}{'总':>6}{'删':>6}{'缩':>6}  {'直方图(inside 0.0→1.0)':<22}")
    for num, st, raw, cln in rows:
        h = "".join(str(min(9, v)) if v else "." for v in st["hist"])
        print(f"{st['name'][:25]:<26}{st['total']:>6}{st['dropped']:>6}"
              f"{st.get('trimmed', 0):>6}  {h:<22}")

    print("\n整身溢出质量（alpha 和，越小越干净）：")
    all_raw = [s for v in parts.values() for s in v["shapes"]]
    all_clean = [s for v in parts.values() for s in v["clean"]]
    o1, _ = outside_mass(all_raw, union)
    o2, _ = outside_mass(all_clean, union)
    print(f"  未清理 {o1:,.0f}  →  清理后 {o2:,.0f}（降 {100 - o2 / max(1e-9, o1) * 100:.1f}%）")

    if args.out:
        Path(args.out).write_text(json.dumps({
            "source": str(args.source), "mask_source": str(args.mask_source),
            "min_inside": args.min_inside,
            "total_shapes": tot_all, "dropped": tot_drop,
            "outside_alpha_before": o1, "outside_alpha_after": o2,
            "parts": {str(k): v["stats"] for k, v in parts.items()},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n写出 {args.out}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="按原图硬 alpha 清理溢出图元")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--mask-source", default=str(DEFAULT_MASK))
    ap.add_argument("--min-inside", type=float, default=0.12)
    ap.add_argument("--out", default="")
    report(ap.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
