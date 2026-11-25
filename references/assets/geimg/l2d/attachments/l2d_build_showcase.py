"""构建「GEIMG 图元级动态预览」单文件 HTML。

输入：
  parts/part_*/shapes.json      GEIMG 导出的图元（space = source_image_pixels）
  parts/part_*.png              原图层（用于合成参考图 + 硬边基准）
  parts/_summary.json           版本与预算信息（写进页面标题）
  attachments/l2d_rig.json                    呼吸参数（按部件编号关联）
  ../attachments/templates/l2d_export.template.lua   Lua 渲染模板（导出用）

输出：
  l2d_preview.html（默认）或 --out 指定的名字

数据行格式与 GE-IMG Tool 导出的 Lua 完全一致： "t|x|y|w|h|rotDeg|RRGGBBAA"
  t: c=circle / e=ellipse / l=line ；坐标是源图像素；rotDeg 是顺时针角度。

眨眼几何全部从数据推出来，不手写：
  眼内容（虹膜+眼白）的上下沿 → 压缩轴心与压缩比
  眼睑线（睫毛/眼线）的中心   → 下移量，使其在闭合时落在压缩后的眼睛上

## 两个数据源

  --source 指向图元目录，--mask-source 指向**原始手扣 PNG**目录。分开是为了支持超拟合：
  `fit_10k` 只有图元、没有 PNG（PNG 还在 `parts`），而边缘清理、
  参考图、虹膜安全范围都必须用原始硬边 PNG。
"""
import argparse
import base64
import io
import json
import math
import re
from pathlib import Path

from PIL import Image

import l2d_edge_clean as EC

HERE = Path(__file__).resolve().parent                 # tools
ROOT = HERE.parent                                     # 本项目
SPLIT = ROOT / "parts"                          # 当前图元源（可由 configure 改）
MASK_SRC = ROOT / "parts"                        # 原始硬边 PNG 目录
EDGE_FIX = True                                        # 是否做边缘清理/颜色修正
RIG = HERE / "l2d_rig.json"
LUA_TPL = HERE / "templates" / "l2d_export.template.lua"
TPL = HERE / "templates" / "l2d_showcase.template.html"

CW, CH = 411, 600

# 眨眼/视点用到的部件：虹膜（可移）、眼白（当裁剪掩膜）、眼睑线、眉毛
#   虹膜与眼白必须分成两个角色 —— 视点只移虹膜，眼白要留在原地当掩膜。
EYE_PARTS = {"eyeL": (9, 10), "eyeR": (11, 12)}
IRIS_PART = {"eyeL": 9, "eyeR": 11}
SCLERA_PART = {"eyeL": 10, "eyeR": 12}
LID_PARTS = {"eyeL": (6, 7), "eyeR": (8,)}
BROW_PARTS = {"eyeL": (2,), "eyeR": (3,)}
# 说话要用到嘴：一张闭合的小嘴，纵向放大即可读成"张开"
MOUTH_PART = 4


def configure(source=None, mask_source=None, edge_fix=None):
    """切换数据源。构建脚本按参数调用，两个版本（普通 / 超拟合）互不覆盖。"""
    global SPLIT, MASK_SRC, EDGE_FIX
    if source is not None:
        SPLIT = Path(source)
    if mask_source is not None:
        MASK_SRC = Path(mask_source)
    if edge_fix is not None:
        EDGE_FIX = bool(edge_fix)


# 手工补充的图元：有些细节太小，逐部件拟合必然漏掉（预算都花在大面积上了），
# 从原画量出来后在这里补上。键 = 部件编号，值 = 追加到该部件末尾的图元。
MANUAL_SHAPES = {
    13: [   # 脸：鼻子的小点。原画实测 bbox 3x3 像素，中心 (248,267)，
            # 色 #CCB3A2（周围皮肤 #FDF0DF）。补在末尾 → 画在脸之上。
            # 超拟合版同样漏了它（该处只有一个半径 8.65 的肤色补丁），所以两个源都要补。
        {"t": "circle", "x": 248.0, "y": 267.0, "r": 1.5,
         "rx": 0.0, "ry": 0.0, "a": 0.0, "rgba": [204, 179, 162, 255]},
    ],
}


def with_manual(num, shapes):
    """把手工图元追加到该部件末尾（画在原有图元之上）。"""
    extra = MANUAL_SHAPES.get(num)
    return list(shapes) + list(extra) if extra else shapes


def part_dirs():
    """按编号从大到小（数字小的在上层 → 先画大的）。"""
    out = []
    for d in SPLIT.iterdir():
        if d.is_dir() and re.match(r"part_\d{4}", d.name):
            out.append((int(d.name[5:9]), d))
    out.sort(key=lambda t: -t[0])
    return out


def mask_png(num):
    """该部件的原始硬边 PNG（边缘清理与虹膜范围都要用）。"""
    p = next(MASK_SRC.glob(f"part_{num:04d}_*.png"), None)
    if p is None:
        raise SystemExit(f"找不到部件 {num:04d} 的原始 PNG（在 {MASK_SRC}）")
    return p


EDGE_STATS = {}          # 最近一次 load_all 的边缘处理统计


def load_all(verbose=False):
    """读全部部件的图元，做边缘处理，返回 {num: [shapes…]}。

    边缘处理三步（都在内存里做，不改 `shapes.json`，原始拟合结果可回溯）：
      ① 剔掉整块落在原图透明区里的图元
      ② 把**跨出轮廓**的图元缩回轮廓内 ← 这一步才是去掉"白色描边"的关键
      ③ 把贴着轮廓的图元颜色按原图真值往暗里修（放大卷边会让它们偏亮）

    为什么不能只靠①：真正画出浅色描边的是一半在里、一半在外的图元 —— 轮廓是硬切的，
    而圆/椭圆是拼接的，边缘总有图元鼓出去 1~3px。Lua 没有 stencil 掩膜，只能在这里解决。
    """
    EDGE_STATS.clear()
    out = {}
    union = EC.union_mask(MASK_SRC) if EDGE_FIX else None
    for num, d in part_dirs():
        j = json.loads((d / "shapes.json").read_text(encoding="utf-8"))
        assert j["space"] == "source_image_pixels", d
        shapes = j["shapes"]
        if EDGE_FIX:
            png = mask_png(num)
            mask = EC.mask_of(png)
            rgb, al = EC.rgb_of(png)
            shapes, cs = EC.clean_part(shapes, mask)        # 剔溢出：用本层自己的 alpha
            shapes, ts = EC.trim_part(shapes, union)        # 缩边界：用整身并集
            shapes, rs = EC.restore_edge_colors(shapes, mask, rgb, al)
            EDGE_STATS[num] = {**cs, **ts, **rs}
        out[num] = with_manual(num, shapes)
    return out


def load_shapes(num):
    """单个部件（带手工图元），供 iris_safe_range 之类零散用途。"""
    for n, d in part_dirs():
        if n == num:
            return with_manual(num, json.loads((d / "shapes.json").read_text(
                encoding="utf-8"))["shapes"])
    return []



def shape_bbox(shapes):
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for s in shapes:
        if s["t"] == "circle":
            rx = ry = s["r"]
        else:
            rx, ry = s["rx"], s["ry"]
            ca, sa = abs(math.cos(s["a"])), abs(math.sin(s["a"]))
            rx, ry = rx * ca + ry * sa, rx * sa + ry * ca
        x0 = min(x0, s["x"] - rx); x1 = max(x1, s["x"] + rx)
        y0 = min(y0, s["y"] - ry); y1 = max(y1, s["y"] + ry)
    return x0, y0, x1, y1


def raw_rows(shapes):
    """GEIMG 图元 → Lua 紧凑行。"""
    rows = []
    for s in shapes:
        t = s["t"]
        r, g, b, a = s["rgba"]
        if t == "circle":
            w = h = s["r"] * 2.0
            rot = 0.0
        else:
            w, h = s["rx"] * 2.0, s["ry"] * 2.0
            rot = -math.degrees(s["a"])          # 画布 Y 向下 → Lua Y 向上，取负
        code = {"circle": "c", "ellipse": "e", "line": "l"}[t]
        rows.append(f"{code}|{s['x']:.2f}|{s['y']:.2f}|{w:.2f}|{h:.2f}|{rot:.2f}|"
                    f"{r:02X}{g:02X}{b:02X}{a:02X}")
    return rows


def reference_png():
    """按绘制顺序合成 26 个原图层（它们是二值 alpha 的硬边图）。"""
    import numpy as np
    acc_a = None
    acc_c = None
    for num, d in part_dirs():
        png = mask_png(num)
        im = Image.open(png).convert("RGBA")
        if im.size != (CW, CH):
            raise SystemExit(f"{png.name} 尺寸 {im.size} != {(CW, CH)}")
        arr = np.asarray(im, dtype=np.float64)
        a = arr[:, :, 3:4] / 255.0
        rgb = arr[:, :, :3]
        if acc_a is None:
            acc_a = a[:, :, 0].copy()
            acc_c = rgb * a
        else:
            acc_c = acc_c * (1 - a) + rgb * a
            acc_a = acc_a + (1 - acc_a) * a[:, :, 0]
    out = np.dstack([np.clip(acc_c, 0, 255), np.clip(acc_a * 255, 0, 255)])
    buf = io.BytesIO()
    Image.fromarray(out.astype("uint8"), "RGBA").save(buf, "PNG", optimize=True)
    return buf.getvalue(), acc_a


def body_rig(by_num, motion):
    """从数据推出「骨骼位移场」的锚点 —— 不手填坐标。

    场的形式（见 骨骼算法研究稿）：越往上水平位移越大，脚底恒为 0。
      s(y) = clamp((yGround − y) / (yGround − yNeck), 0, 1)
      Δx   = gx · bodyAmp · s(y) · (1 + depthK · d(x))     d(x)=(x−Cx)/Rx ∈[−1,1]
    脚底 s=0 ⇒ 自动钉住，不需要给腿单独权重（上一版按部件给权重，在腰部撕开过 4.2px）。
    """
    def bbox(nums):
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        for n in nums:
            for s in by_num.get(n, []):
                r = s.get("r", 0.0) if s["t"] == "circle" else max(s.get("rx", 0), s.get("ry", 0))
                x0 = min(x0, s["x"] - r); x1 = max(x1, s["x"] + r)
                y0 = min(y0, s["y"] - r); y1 = max(y1, s["y"] + r)
        return x0, y0, x1, y1

    def group_bb(names):
        nums = [n for n in by_num if motion[n]["group"] in names]
        return bbox(nums) if nums else None

    legs = group_bb({"legs"})
    body = group_bb({"body", "armL", "armR"})
    head = group_bb({"head"})
    if legs is None or body is None or head is None:
        return None
    y_ground = legs[3]                      # 脚底
    y_hip = legs[1]                         # 髋线 = 腿部件的上沿：位移场的 0 点
    y_neck = head[3]                        # 下巴/脖子：位移场饱和处
    if y_hip - y_neck < 40:                 # 数据异常时退回文档里的经验值
        y_ground, y_hip, y_neck = 599.0, 480.0, 303.0
    return {
        "yGround": round(y_ground, 1), "yHip": round(y_hip, 1), "yNeck": round(y_neck, 1),
        "yTop": round(head[1], 1),
        "cxTorso": round((body[0] + body[2]) / 2, 1),
        "rxTorso": round((body[2] - body[0]) / 2, 1),
        "headBbox": [round(v, 1) for v in head],
    }


def iris_safe_range():
    """量出"虹膜整块都落在合法区内"的最大位移 —— 不依赖引擎掩膜时的可用范围。

    合法区按正确遮挡关系取：**眼白 ∪ 睫毛 ∪ 眼线**，另给一组放宽版
    （再并上眉毛/前发/花饰——它们画在虹膜之上，虹膜滑进去会被盖住而不是露在皮肤上）。
    虹膜上沿本来就超出眼白上沿（那块被睫毛盖着），所以只按眼白算会得到 0。
    """
    import numpy as np

    def a(num):
        im = np.asarray(Image.open(mask_png(num)).convert("RGBA"))
        return im[:, :, 3] > 8

    out = {}
    for side in ("eyeL", "eyeR"):
        iris = a(IRIS_PART[side])
        if iris is None:
            continue
        strict = a(SCLERA_PART[side]).copy()
        for i in LID_PARTS[side]:
            strict |= a(i)
        loose = strict.copy()
        for i in (BROW_PARTS[side] + (1, 0)):
            m = a(i)
            if m is not None:
                loose |= m
        ys, xs = np.nonzero(iris)
        iy0, iy1, ix0, ix1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        area = int(iris.sum())

        def scan(allowed, R=14):
            r = {"left": 0, "right": 0, "up": 0, "down": 0}
            for dy in range(-R, R + 1):
                for dx in range(-R, R + 1):
                    if (dx and dy) or (not dx and not dy):
                        continue
                    sh = np.zeros(allowed.shape, bool)
                    sl_y = slice(iy0 + dy, iy1 + dy)
                    sl_x = slice(ix0 + dx, ix1 + dx)
                    if sl_y.start >= allowed.shape[0] or sl_x.start >= allowed.shape[1] \
                       or sl_y.stop <= 0 or sl_x.stop <= 0:
                        continue
                    sh[sl_y, sl_x] = iris[iy0:iy1, ix0:ix1]
                    if int((sh & allowed).sum()) == area:
                        if dx < 0:
                            r["left"] = max(r["left"], -dx)
                        elif dx > 0:
                            r["right"] = max(r["right"], dx)
                        elif dy < 0:
                            r["up"] = max(r["up"], -dy)
                        else:
                            r["down"] = max(r["down"], dy)

            return r

        out[side] = {"strict": scan(strict), "loose": scan(loose),
                     "iris_bbox": [int(ix0), int(iy0), int(ix1), int(iy1)]}
    return out


def blink_geometry(by_num):
    """从图元数据推出眨眼几何。返回 (eyes, roles, mouth)。"""
    eyes = {}
    roles = {}
    for side, (ai, bi) in EYE_PARTS.items():
        ex = shape_bbox(by_num[ai] + by_num[bi])
        lid_parts = LID_PARTS[side]
        lx = shape_bbox(sum((by_num[i] for i in lid_parts), []))
        eyes[side] = {
            "top": round(ex[1], 1),
            "bot": round(ex[3], 1),
            "cx": round((ex[0] + ex[2]) / 2, 1),
            "lidCy": round((lx[1] + lx[3]) / 2, 1),
        }
        for i in (ai, bi):
            roles[str(i)] = ("iris:" if i == IRIS_PART[side] else "eye:") + side
        for i in lid_parts:
            roles[str(i)] = "lid:" + side
        for i in BROW_PARTS[side]:
            if i in by_num:
                roles[str(i)] = "brow:" + side
    mx = shape_bbox(by_num[MOUTH_PART])
    mouth = {
        "cx": round((mx[0] + mx[2]) / 2, 1),
        "cy": round((mx[1] + mx[3]) / 2, 1),
        "h": round(mx[3] - mx[1], 1),
    }
    # 嘴**不**给角色：保持静态（按 talk 纵向张开会变"厚嘴唇"）。
    # 不给角色 = 普通部件，只跟随头部运动与柱面形变。
    return eyes, roles, mouth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="l2d_preview.html")
    ap.add_argument("--tpl", default=str(TPL))
    ap.add_argument("--source", default=None, help="图元目录（默认 parts）")
    ap.add_argument("--mask-source", default=None, help="原始硬边 PNG 目录（默认 parts）")
    ap.add_argument("--no-edge-fix", action="store_true",
                    help="不做边缘清理/轮廓颜色修正（用于对照）")
    args = ap.parse_args()
    configure(args.source, args.mask_source, not args.no_edge_fix)

    rig = json.loads(RIG.read_text(encoding="utf-8"))
    motion = {p["num"]: p for p in rig["parts"]}

    by_num = load_all(verbose=False)
    if EDGE_STATS:
        dropped = sum(s["dropped"] for s in EDGE_STATS.values())
        trimmed = sum(s["trimmed"] for s in EDGE_STATS.values())
        changed = sum(s["changed"] for s in EDGE_STATS.values())
        print(f"边缘处理：剔溢出 {dropped} 个 / 缩回轮廓 {trimmed} 个 / 轮廓改色 {changed} 个"
              f"（源 {SPLIT.name}）")

    parts = []
    total = 0
    for num, d in part_dirs():
        rows = raw_rows(by_num[num])
        total += len(rows)
        m = motion.get(num)
        if m is None:
            raise SystemExit(f"rig.json 缺少部件 {num}")
        parts.append({
            "num": num,
            "name": m["name"],
            "group": m["group"],
            "w": m["w"],
            "delay": m["delay"],
            "rot": m["rot"],
            "pivot": m["pivot"],
            "raw": "\n".join(rows),
        })

    eyes, roles, mouth = blink_geometry(by_num)
    safe = iris_safe_range()
    for p in parts:
        p["role"] = roles.get(str(p["num"]), "")

    # 眨眼 / 说话用到的控件在 RAW 里的连续下标区间（1-based，含首含尾）——
    # 导出 Lua 时可以直接按区间批量改 anchoredPosition / sizeDelta。
    ranges = {side: {} for side in EYE_PARTS}
    ranges["mouth"] = None
    cursor = 0
    for p in parts:
        n = len(p["raw"].split("\n"))
        r = roles.get(str(p["num"]), "")
        if r == "mouth":
            ranges["mouth"] = [cursor + 1, cursor + n]
        elif r:
            kind, side = r.split(":")
            ranges[side][kind] = [cursor + 1, cursor + n]
        cursor += n

    ref_bytes, ref_a = reference_png()
    ref_band = int(((ref_a > 0.10) & (ref_a < 0.90)).sum())

    lua_src = LUA_TPL.read_text(encoding="utf-8")
    assert lua_src.count("__CFG__") == 1 and lua_src.count("__RAW__") == 1, "Lua 模板占位标记异常"
    # 防呆：这段文本会被 JSON 内联进 HTML 的 <script> 里。若误把 HTML 自身读进来，
    # 里面的 <script> 会让解析器进入 double-escaped 状态、吞掉 </script>，脚本整个不执行。
    assert "<script" not in lua_src and "</script" not in lua_src and len(lua_src) < 60_000, \
        f"Lua 模板内容可疑（{len(lua_src)} 字节）：是不是把 HTML 模板读进来了？"

    version = ""
    summ = SPLIT / "_summary.json"
    if summ.exists():
        version = f"{total} 图元"

    body = body_rig(by_num, motion)
    scale = min(1120.0 / CW, 630.0 / CH)
    data = {
        "canvas": {"w": CW, "h": CH},
        "label": version,
        "source": SPLIT.name,
        "motion": {"period": rig["period"], "amp": rig["amp"]},
        "body": body,
        "blink": {
            "enabled": True,
            "duration": 0.15,
            "minGap": 2.2,
            "maxGap": 5.2,
            "maxClose": 0.92,
            "closeAt": 0.78,          # 闭合位置：从眼睛上沿往下 78% 处（≈下眼睑）
            "browFollow": 0.0,
            "doubleChance": 0.16,
            "eyeSkew": 0.012,         # 左右眼相位差（秒），避免完全同步
            "eyes": eyes,
            "mouth": mouth,
            "ranges": ranges,
            # 不依赖引擎掩膜时虹膜可用的位移范围（从原图 alpha 量出来的）
            "iris_safe": safe,
        },
        "lua": {
            "scale": scale,
            "offsetX": 800 - CW * scale / 2,
            "offsetY": 450 - CH * scale / 2,
            "sourceHeight": CH,
            # decode 要把画布空间坐标（左下原点、Y 向上）转成相对容器中心的
            # anchoredPosition，两者相差半个画布 —— 少这一步角色会整体窜到右上角
            "canvasW": 1600,
            "canvasH": 900,
            "containerName": "GEIMG_Canvas",
            "imagePrefabId": 0,
            "circleAssetId": 100002,   # 固定资源 ID（用户提供）
            "budgetPerFrame": 40,
            "alphaMax": 255,
        },
        "parts": parts,
        "ref": "data:image/png;base64," + base64.b64encode(ref_bytes).decode("ascii"),
        "luaTemplate": lua_src,
    }

    html = Path(args.tpl).read_text(encoding="utf-8")
    assert html.count("/*__DATA__*/") == 1, "模板缺少 __DATA__ 占位"
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*__DATA__*/", js)
    out = ROOT / args.out
    out.write_text(html, encoding="utf-8")

    print(f"部件 {len(parts)} 个，图元 {total} 个（源：{SPLIT.name}"
          f"{'，边缘已修正' if EDGE_FIX else '，边缘未修正'}）")
    if body:
        print(f"骨骼位移场锚点：脚底 y={body['yGround']}  脖子 y={body['yNeck']}  "
              f"躯干中心 x={body['cxTorso']} 半宽 {body['rxTorso']}")
    print(f"眨眼几何： L 眼 y[{eyes['eyeL']['top']},{eyes['eyeL']['bot']}] 眼睑中心 {eyes['eyeL']['lidCy']}"
          f"  |  R 眼 y[{eyes['eyeR']['top']},{eyes['eyeR']['bot']}] 眼睑中心 {eyes['eyeR']['lidCy']}")
    print(f"嘴部几何： 中心 ({mouth['cx']},{mouth['cy']}) 高 {mouth['h']}")
    for sd, v in safe.items():
        st, lo = v["strict"], v["loose"]
        print(f"虹膜安全位移 {sd}: 严格(眼白∪睫毛∪眼线) 左{st['left']} 右{st['right']} 上{st['up']} 下{st['down']} | "
              f"放宽(+眉/前发/花饰) 左{lo['left']} 右{lo['right']} 上{lo['up']} 下{lo['down']}")
    print(f"参考图 PNG {len(ref_bytes)/1024:.0f} KB，二值 alpha 校验：半透明像素 {ref_band}")
    print(f"Lua 映射 scale={scale:.6f} offsetX={800 - CW*scale/2:.3f} offsetY={450 - CH*scale/2:.3f}"
          f"（画布 1600x900，decode 会减半画布得到容器中心原点）")
    print(f"写出 {out.name}  {out.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()

