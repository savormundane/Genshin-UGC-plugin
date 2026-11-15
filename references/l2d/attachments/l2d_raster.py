"""
把 shapes.json 栅格化到指定画布——评估"用户实际看到什么"的公共底座。

为什么需要它：引擎的 preview.png 是在**拟合分辨率**下渲染的（x3 就是 1233x1800）。
把它缩回 411x600 来量"过渡带"，那个缩放本身会把边缘糊开，于是 ×3 的过渡带
反而比 ×1 更差——这是度量假象，不是拟合结果。正确的比法是：把每个图元按
**源图像素尺度**直接画到 411x600 上（坐标系除以倍数即可），
这也正是最终 Lua/沙箱里画出来的样子（画布 scale≈1.05）。

栅格化用"到椭圆边界的近似像素距离 → clip(0.5-dist,0,1)"做约 1px 抗锯齿，
与 Unity/UI 画椭圆的观感一致；关键在于**所有被测对象用同一个栅格化器**，比较才公平。
"""
import json
import math
from pathlib import Path

import numpy as np


def load_shapes(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["shapes"]


def rescale(shapes, div: float):
    """把图元坐标/半径除以 div，从拟合分辨率空间回到源图像素空间。"""
    if div == 1:
        return shapes
    out = []
    for s in shapes:
        t = dict(s)
        t["x"] = s["x"] / div
        t["y"] = s["y"] / div
        for k in ("r", "rx", "ry"):
            if k in s:
                t[k] = s[k] / div
        out.append(t)
    return out


def rasterize(shapes, w: int, h: int, out_scale: int = 1):
    """
    按数组顺序叠加（下标 0 在最底层）。返回 (alpha[H,W], rgb[H,W,3])，范围 0..1 / 0..255。

    out_scale：输出放大倍数（1 = 画布就是 w×h）。放大时用同样的连续数学，
    只是采样更密——相当于"在更高分辨率下看同一份矢量数据"。
    """
    W, H = w * out_scale, h * out_scale
    acc_a = np.zeros((H, W), np.float64)
    acc_c = np.zeros((H, W, 3), np.float64)

    for s in shapes:
        r, g, b, a8 = s["rgba"]
        a = a8 / 255.0
        if a <= 0:
            continue
        if s["t"] == "circle":
            rx = ry = s.get("r", 0.0)
            ang = 0.0
        else:
            rx, ry = s.get("rx", 0.0), s.get("ry", 0.0)
            ang = s.get("a", 0.0)
        if rx <= 0 or ry <= 0:
            continue

        cx, cy = s["x"] * out_scale, s["y"] * out_scale
        RX, RY = rx * out_scale, ry * out_scale
        ca, sa = abs(math.cos(ang)), abs(math.sin(ang))
        ex = RX * ca + RY * sa + 2
        ey = RX * sa + RY * ca + 2
        x0, x1 = max(0, int(cx - ex)), min(W, int(cx + ex) + 2)
        y0, y1 = max(0, int(cy - ey)), min(H, int(cy + ey) + 2)
        if x1 <= x0 or y1 <= y0:
            continue

        ys, xs = np.mgrid[y0:y1, x0:x1]
        dx, dy = xs - cx, ys - cy
        u = dx * math.cos(-ang) - dy * math.sin(-ang)
        v = dx * math.sin(-ang) + dy * math.cos(-ang)
        k = np.sqrt((u / RX) ** 2 + (v / RY) ** 2)
        dist = (k - 1.0) * min(RX, RY)          # 到边界的近似像素距离
        cov = np.clip(0.5 - dist, 0.0, 1.0)      # 约 1px 过渡
        eff = cov * a
        if not eff.any():
            continue
        sub = acc_a[y0:y1, x0:x1]
        acc_c[y0:y1, x0:x1] = (acc_c[y0:y1, x0:x1] * (1 - eff[..., None])
                               + np.array([r, g, b], np.float64) * eff[..., None])
        acc_a[y0:y1, x0:x1] = sub + (1 - sub) * eff

    return np.clip(acc_a, 0, 1), np.clip(acc_c, 0, 255)


def composite(parts_shapes, w=411, h=600, out_scale=1):
    """
    按"编号大的先画（在底层）"叠加多个部件，返回整身 (alpha, rgb)。
    parts_shapes: [(编号int, shapes), …]
    """
    W, H = w * out_scale, h * out_scale
    acc_a = np.zeros((H, W), np.float64)
    acc_c = np.zeros((H, W, 3), np.float64)
    for num, shapes in sorted(parts_shapes, key=lambda t: -t[0]):
        a, c = rasterize(shapes, w, h, out_scale)
        acc_c = acc_c * (1 - a[..., None]) + c * a[..., None]
        acc_a = acc_a + (1 - acc_a) * a
    return acc_a, acc_c


def to_rgba(alpha, rgb, bg=(32, 32, 36)):
    """合成到不透明背景上，返回 PIL Image（RGB）——用于"看图"，不能用于叠加。"""
    from PIL import Image
    a = alpha[..., None]
    b = np.array(bg, np.float64)
    out = rgb * a + b * (1 - a)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def to_rgba_image(alpha, rgb):
    """
    保留 alpha 的 RGBA 图——**叠加/合成必须用这个**。

    踩过的坑：把重绘的 preview 用 to_rgba（铺底色的 RGB）写出去，再拿去逐层叠加时，
    每层都是整张不透明的深色，于是下面所有层被完全盖住，成品里只剩最上面那个部件。
    拼合脚本的配准校验当场把 26 个部件全报成错位，才暴露出来。
    """
    from PIL import Image
    arr = np.zeros((*alpha.shape, 4), np.uint8)
    arr[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    arr[..., 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")
