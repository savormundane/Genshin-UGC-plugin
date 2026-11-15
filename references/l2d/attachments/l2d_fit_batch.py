#!/usr/bin/env python3
"""
逐部件拟合 + 导出数据集（live2d 测试用）。

为什么要"逐部件拟合"而不是整图拟合一次：目标是后面做 Live2D —— 每个部件要能**独立**被
Lua 控制（位移/旋转/缩放/染色），所以图元必须按部件分开存。

**相对坐标与缩放在拟合上是自动一致的**，前提三条（本脚本都固定住了）：
  1. 所有部件 PNG 是同一画布尺寸、部件在原位 → 坐标同基准；
  2. 导出的坐标一律换算回**源图像素空间**（411x600）——见下"分辨率"一节；
  3. 各部件用同一套**影响颜色/边缘处理**的参数（模式 / 开关 / alpha 阈值）。
     预算、reserve-ratio、以及**拟合倍数**可以逐部件不同：前两者只影响图元数量与两阶段分配，
     后者在导出后被除回去，都不改变最终坐标空间。

## 分辨率：细线部件的关键杠杆（v5 新增）

引擎的图元尺寸**随图像尺寸缩放**，但尺寸有**绝对像素下限**（圆与线段各有各的下限，
量级是 1~3 个源像素）。在 411x600 上这些下限就是 2~3 个源像素，
而平涂角色的勾线只有 1~2px 宽 —— 于是**细线根本表达不出来**，只能糊成色块。

工具的判据（`fit recommend` 的建议里也是这条）：最细特征在拟合分辨率下要留 2~3px。
因为放大拟合**不增加图元预算**
（图元尺寸同步放大），这对细线是净收益、对平涂是中性，代价只有耗时。实测（同 120 图元）：

| 部件 | ×1 | ×3 |
|---|---|---|
| L-eye | 一个琥珀色块，瞳孔/高光糊在一起 | 瞳孔、高光环、下缘亮弧都出来了 |
| L-睫毛 | 睑褶细线消失、尖端钝 | 细线出现、尖端成形 |
| mouth | 8 个图元就"收敛"，没有嘴形 | 用满 45 个预算，嘴形与唇线可读 |

引擎**只会缩小不会放大**（`max-dim` 仅在超限时缩放），所以放大必须由本脚本
先把 PNG 放大再喂进去；导出的坐标再除以倍数换算回源图空间（`rescale_dataset`）。

## 图元预算怎么分（依据都可测）

**依据一：按"叠加后在成品里露出来的面积"，不是部件自身面积。**
逐部件拟合最容易犯的错是按自身像素分配，而**大部分像素可能被上层盖住、在成品里根本看不见**。
实测这批 26 个部件：自身合计 230,343 px，成品里只露出 109,870 px（52% 被遮住），且极不均——
  back-hair 自身 45,875 px 只露出 1,987 px（4%）；
  pantsi   自身  2,120 px 露出 0 px；
  前发     自身 53,019 px 露出 43,378 px（82%，成品里最大的一块可见面积）。

**依据二：按细节密度分档——平涂角色的观感几乎全在装饰线条与描边上。**
平色大块不需要多少图元（一块平涂色一个图元就够），而线稿、描边、饰品细节需要**高精度拟合**。
`reserve-ratio` 越大，留给精度阶段（尺寸 ×0.4 的小图元）的预算越多。实测同一部件、同样 380
图元下 reserve 20 vs 50：50 的发丝分股与尖端明显更清楚。所以线条/结构类部件一律给 **50**。

**依据三：预算要按实测拐点定，不按面积估。** 本表里几个关键数字是扫出来的（同级图元数）：

| 部件 | 结论 |
|---|---|
| L-arm | 70 → 180 是质变（蝴蝶结/袖口/绿环出现），180 → 320 几乎无变化 → 取 180 |
| face  | 100 / 200 / 320 三档几乎无差别（大片平滑皮肤 + 大半被头发盖住）→ 取下限 120 |
| L-leg | 90 → 150 → 260 持续变好（宝石、V 形带、靴筒成形）→ 取 260 |
| 衣服   | 180 → 280 → 420 持续变好（层叠与金边逐步出现）→ 取 400 |
| 前发   | 200 → 380 → 560 持续变好（发丝分股、尖端）→ 取 520 |
| eye-white | 强边缘像素为 0（纯平滑渐变）→ 给最小底 20/15 |
| pantsi | 成品里露出 0 px（但做 Live2D 一动就会露）→ 留 12 的底 |

露出面积≈0 的部件不给 0——做 Live2D 时肢体一动它就会露出来。

用法：
    py -3 l2d_fit_batch.py --parts "<拆分目录>" --exe "<GE_IMG_Tool.exe 路径>" [--limit N] [--reuse]
产物：每个部件一个数据集目录（<部件名>/），外加 _summary.json
"""
import argparse
import json
import re
import os
import subprocess
import sys
import time
from pathlib import Path

# 所有部件必须一致：影响颜色处理与边缘处理（不影响坐标空间，坐标统一由 rescale 保证）
FIT_SHAPES_MAX_DIM = 600      # ×倍数 后作为 max-dim；倍数=1 时即 411x600 不缩放
CANDIDATES = 64
SPEED = 5
ALTERNATE_INTERVAL = 30
ALPHA_THRESHOLD = 64          # 抗锯齿软边要算作内容，否则部件交界处会留缝（默认 128）

# ── 逐部件表：编号 → (预算, reserve-ratio, 拟合倍数, 依据) ──
# 倍数：细线部件（勾线/睫毛/眼线/五官）用 3，让 1~2px 的线在拟合分辨率下有 3~6px；
#       大片平涂/大色块用 1（放大对它是中性，白白花时间）。
PLAN = {
    # 编号      预算  reserve  倍数  依据
    "0000": (260, 50, 3, "装饰物：线条密集且 100% 露出；成品里第二大可见面积"),
    "0001": (520, 50, 3, "主体：成品里最大可见面积；实测 560 仍在变好，发丝分股靠精度阶段"),
    "0002": ( 70, 50, 3, "五官：眉毛是纯线条（1px）"),
    "0003": ( 50, 50, 3, "五官：眉毛（露出更少）"),
    "0004": ( 45, 50, 3, "五官：嘴；×3 下才会用满预算（×1 只出 8 个图元就收敛）"),
    "0006": (110, 50, 3, "五官：睫毛线稿 + 睑褶细线"),
    "0007": ( 70, 50, 3, "五官：眼线（纯线条，边缘密度 1.0）"),
    "0008": (100, 50, 3, "五官：睫毛+眼线，两道粗描边"),
    "0009": (150, 50, 3, "五官：虹膜——瞳孔/高光/内环是细结构，×3 才出得来"),
    "0010": ( 20, 25, 1, "眼白：360° 平滑渐变、强边缘 0、露出少 → 最小底"),
    "0011": (140, 50, 3, "五官：虹膜（同 0009）"),
    "0012": ( 15, 25, 1, "眼白：平滑渐变、强边缘 0"),
    "0013": (120, 30, 1, "大面积平滑 + 大半被头发盖住；实测 100/200/320 无差别 → 取下限"),
    "0014": ( 90, 50, 3, "小装饰：围巾，边缘密度 0.72"),
    "0015": (400, 50, 3, "主体：层叠 + 金边；实测 420 仍在变好"),
    "0016": (120, 50, 3, "飘带：细长轮廓"),
    "0017": ( 90, 50, 3, "装饰物：发饰"),
    "0018": (120, 50, 3, "飘带：细长轮廓"),
    "0019": (180, 50, 3, "次要大面积：手臂；实测拐点在 180（蝴蝶结/袖口在此出现）"),
    "0020": ( 12, 25, 1, "几乎被盖住（露出 0px）：留个底，动画一动会露出来"),
    "0021": (260, 50, 3, "次要大面积：腿；实测 260 仍在变好（宝石与 V 形带）"),
    "0022": (230, 50, 3, "次要大面积：腿（按露出面积与 0021 比例）"),
    "0023": ( 70, 30, 1, "次要大片：后布，边缘密度 0.10 → 平色为主"),
    "0024": (140, 50, 3, "次要：手臂（按露出面积与 0019 比例）"),
    "0025": ( 45, 25, 1, "大片平色且只露 4%：够铺色即可"),
    "0026": (100, 50, 3, "飘带：细长轮廓"),
}


def upscale_edge_aware(src_png: Path, dst_png: Path, scale: int, iters: int = 8):
    """放大部件图，先把透明区的 RGB 填成邻近内容色，再插值。

    问题：这批手扣层的透明区 RGB 是**纯白 (255,255,255)**（实测 26 个部件全是），
    而 PIL 的 resize 对 RGBA 四通道**各自独立**插值、不做预乘。于是白色被卷进轮廓最外
    1~3px，拟合器照着这些偏亮像素取样 → 成品轮廓外多出一圈浅色描边（用户报的"白色描边"）。

    修法对比（实测 part_0001_前发 ×3，最外圈 al<128 的 RGB 均值）：
      · 直接 Lanczos          → (248.6, 244.7, 242.1)   ← 卷白
      · 预乘→插值→反预乘      → (255.0, 255.0, 254.9)   ← **更糟**：Lanczos 的负瓣过冲
                                                        被 1/alpha 放大，边缘反而更白
      · **本函数（先填色再插值）** → 接近内容色，见 `_自检` 输出

    所以走"把透明区染成邻居的颜色"。它对拟合是**中性**的：拟合只看 alpha≥阈值的像素，
    这些像素的颜色一个都没改，改的只是透明区里"本来就不该被采样"的 RGB。
    """
    import numpy as np
    from PIL import Image

    im = Image.open(src_png).convert("RGBA")
    a = np.asarray(im, dtype=np.float64)
    rgb, al = a[:, :, :3].copy(), a[:, :, 3]
    known = al > 0
    for _ in range(iters):
        if known.all():
            break
        # 已知像素的颜色和 / 计数（用 pad 而不是 roll：roll 会让对边绕回来串色）
        acc = np.zeros_like(rgb)
        cnt = np.zeros(al.shape, np.float64)
        pk = np.pad(known, 1, constant_values=False)
        prgb = np.pad(rgb, ((1, 1), (1, 1), (0, 0)), mode="edge")
        H, W = known.shape
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                if dy == 1 and dx == 1:
                    continue                      # 自己：未知像素对自己没有贡献
                sk = pk[dy:dy + H, dx:dx + W]
                srgb = prgb[dy:dy + H, dx:dx + W]
                acc += srgb * sk[..., None]
                cnt += sk
        fill = (~known) & (cnt > 0)
        rgb[fill] = acc[fill] / cnt[fill][..., None]
        known = known | fill

    size = (im.width * scale, im.height * scale)
    out_rgb = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").resize(size, Image.LANCZOS)
    out_a = Image.fromarray(np.clip(al, 0, 255).astype(np.uint8), "L").resize(size, Image.LANCZOS)
    Image.merge("RGBA", (*out_rgb.split(), out_a)).save(dst_png)


def visible_pixels(path: Path) -> int:
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    alpha = im.getchannel("A")
    return sum(1 for v in alpha.getdata() if v >= 128)


def exposure_map(files: list) -> dict:
    """
    算每个部件"叠加后在成品里露出来的像素"。

    叠加顺序：编号大的在底层、编号小的在顶层（这批零件的编号就是这么设计的）。
    所以从上往下扫（编号升序），累计"已经在上面画过的层"的覆盖，得到每个部件露出多少。
    """
    import numpy as np
    from PIL import Image

    size = Image.open(files[0]).size
    covered = np.zeros((size[1], size[0]), dtype=np.uint8)
    exposed = {}
    for f in sorted(files):
        alpha = np.array(Image.open(f).convert("RGBA").getchannel("A"))
        own = alpha >= 128
        exposed[f.stem] = int((own & (covered < 128)).sum())
        covered = np.maximum(covered, alpha)
    return exposed


def part_id(name: str) -> str:
    """从 part_0013_face 里取出 0013。"""
    for token in name.split("_"):
        if token.isdigit() and len(token) == 4:
            return token
    return ""


def plan_for(name: str, exposed: int, edge_density: float):
    """
    取该部件的（预算, reserve-ratio, 倍数, 依据）。

    表里有就按表；表里没有（换了零件集）就退回一个保守公式：按露出面积与边缘像素数估，
    细线多的给高 reserve 与 3 倍分辨率。
    """
    pid = part_id(name)
    if pid in PLAN:
        return PLAN[pid]
    edge_px = int(exposed * max(edge_density, 0.02))
    budget = max(24, min(300, 24 + exposed // 90 + edge_px // 6))
    reserve = 50 if edge_density >= 0.25 else (35 if edge_density >= 0.10 else 25)
    scale = 3 if edge_density >= 0.25 else 1
    return budget, reserve, scale, f"表外部件：按露出 {exposed}px / 边缘 {edge_px}px 估算"


def run(exe: str, session_dir: str, args, *, json_out=False):
    # --no-gui：批处理不要开界面窗口。命令台会在长时间命令（fit start / region fit）前
    # 自动开窗让人看得见（见 Cli/VisibleWindow.cs），26 个部件并行时那是纯噪音。
    cmd = [exe] + args + ["--session-dir", session_dir, "--no-gui"]
    if json_out:
        cmd.append("--json")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def rescale_dataset(ds: Path, scale: int, src_png: Path):
    """
    把数据集从"放大后的拟合空间"换算回源图像素空间（411x600）。

    为什么必须做：下游（Lua / Live2D 装配 / composite-parts.py）都约定坐标是**源图像素**，
    且所有部件同一基准。放大 3 倍拟合时导出的是 1233x1800 空间的坐标，必须除回去。

    同时用换算后的图元重绘 preview.png：引擎给的 preview 是放大空间的（还含边缘补齐），
    留着它就是另一个"看着对、其实错位"的坑（本项目刚踩过一次拼合错位）。
    """
    import numpy as np
    from PIL import Image

    sj = ds / "shapes.json"
    if not sj.exists():
        return
    data = json.loads(sj.read_text(encoding="utf-8"))
    for s in data["shapes"]:
        s["x"] = round(s["x"] / scale, 3)
        s["y"] = round(s["y"] / scale, 3)
        for k in ("r", "rx", "ry"):
            if k in s:
                s[k] = round(s[k] / scale, 3)
    data["space"] = "source_image_pixels"
    data["note"] = (f"数组顺序即绘制顺序（下标 0 在最底层）；坐标是源图像素"
                    f"（拟合时放大 {scale} 倍，导出后已换算回来），画布换算见 manifest.canvas")
    sj.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    csv = ds / "shapes.csv"
    if csv.exists():
        lines = csv.read_text(encoding="utf-8").splitlines()
        if lines:
            head = lines[0].split(",")

            def idx(*names):
                for n in names:
                    if n in head:
                        return head.index(n)
                return -1

            ix, iy = idx("x"), idx("y")
            ir, irx, iry = idx("r"), idx("rx"), idx("ry")
            out = [lines[0]]
            for ln in lines[1:]:
                c = ln.split(",")
                if len(c) < len(head):
                    out.append(ln)
                    continue
                for i in (ix, iy, ir, irx, iry):
                    if i >= 0 and c[i]:
                        try:
                            c[i] = f"{float(c[i]) / scale:.3f}"
                        except ValueError:
                            pass
                out.append(",".join(c))
            csv.write_text("\n".join(out) + "\n", encoding="utf-8")

    # Lua 内联数据也要一起换算——否则 26 个部件里 6 个在 600 空间、20 个在 1800 空间，
    # 装配 Live2D 时必然对不上（shapes.json 是源图像素、Lua 还是放大空间，是最阴的一处不一致）。
    # 变换是纯线性的：坐标与 sourceHeight 除以倍数、CFG.scale 乘以倍数（offset 不变，
    # 因为 offsetX = 画布中心 - W*scale/2，而 W*scale 在换算前后相等）。
    lua = ds / "lua" / "geimg_render.lua"
    if lua.exists():
        txt = lua.read_text(encoding="utf-8")
        def fix_raw(m):
            parts = m.group(2).split("|")
            if len(parts) < 5:
                return m.group(0)
            for i in (1, 2, 3, 4):
                try:
                    parts[i] = f"{float(parts[i]) / scale:.2f}"
                except ValueError:
                    pass
            return f'{m.group(1)}"{parts[0]}|{"|".join(parts[1:])}"'
        txt = re.sub(r'(\s*)"([cel]\|[^"]+)"', fix_raw, txt)
        txt = re.sub(r"(sourceHeight\s*=\s*)([0-9.]+)",
                     lambda m: f"{m.group(1)}{float(m.group(2)) / scale:.0f}", txt)
        txt = re.sub(r"(\bscale\s*=\s*)([0-9.]+)(\s*,)",
                     lambda m: f"{m.group(1)}{float(m.group(2)) * scale:.6f}{m.group(3)}", txt, count=1)
        lua.write_text(txt, encoding="utf-8")

    # preview 一律用源图空间的图元重绘成 411x600（无边缘补齐），并在 manifest 里**显式声明**。
    # 为什么要统一：引擎给的 preview 是"拟合分辨率 + 边缘补齐"的（×3 时是 1341x1908），
    # 而下游按 411x600 摆放。两套空间混用正是本项目踩过的坑（拼合错位，看起来像描了白边）。
    # 声明字段比让下游猜 safe：旧数据集没有 preview 块时，下游会退回读 source.edge_padding。
    #
    # **必须写成带 alpha 的 RGBA**：preview 的用途是逐层叠加，若压成不透明图，
    # 每层都会把下面整层盖住（实测成品只剩最上面那个部件）。
    redrawn = False
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent
                              / "分析" / "live2d测试" / "tools"))
        from raster import rasterize, to_rgba, to_rgba_image
        src = Image.open(src_png).convert("RGBA")
        alpha, rgb = rasterize(data["shapes"], src.width, src.height)
        to_rgba_image(alpha, rgb).save(ds / "preview.png")          # 叠加用
        to_rgba(alpha, rgb, bg=(255, 255, 255)).save(ds / "preview_on_white.png")  # 看图用
        redrawn = True
    except Exception as ex:
        print(f"    ! preview 重绘跳过（{ex}）")

    mf = ds / "manifest.json"
    if mf.exists():
        m = json.loads(mf.read_text(encoding="utf-8"))
        m["preprocess"] = {
            "source_upscale": scale,
            "note": ("拟合前把源图放大该倍数（让 1~2px 的勾线在拟合分辨率下有 3~6px，"
                     "见本脚本顶部说明）；"
                     "shapes 的坐标已除以该倍数换算回源图像素"),
        }
        m["preview"] = {
            "space": "source_image_pixels" if redrawn else "fit_resolution",
            "edge_padding": 0 if redrawn else m.get("source", {}).get("edge_padding", 0),
            "redrawn_from_shapes": redrawn,
            "note": ("preview.png 已用换算后的图元按源图像素空间重绘（无边缘补齐），"
                     "可直接与源图 1:1 叠加" if redrawn
                     else "preview.png 是引擎原始产物（拟合分辨率 + 边缘补齐），"
                          "叠加前需按 source.edge_padding 裁掉四周"),
        }
        mf.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True, help="零件目录（同尺寸 PNG）")
    ap.add_argument("--exe", default=os.environ.get("GEIMG_EXE", "GE_IMG_Tool.exe"),
                    help="GE_IMG_Tool.exe 的路径（也可用环境变量 GEIMG_EXE 指定）")
    ap.add_argument("--sessions", default="sessions/_l2d")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 个（调试用）")
    ap.add_argument("--only", default="", help="只跑这些编号/名字片段（逗号分隔），便于单点重跑")
    ap.add_argument("--reuse", action="store_true", help="已有数据集的部件跳过")
    args = ap.parse_args()

    parts_dir = Path(args.parts)
    all_files = sorted(parts_dir.glob("part_*.png"))
    files = all_files
    if args.only:
        want = [w.strip() for w in args.only.split(",") if w.strip()]
        files = [f for f in files if any(w in f.stem for w in want)]
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"没找到部件：{parts_dir}")
        return 2

    exe = str(Path(args.exe).resolve())
    summary = []
    t_all = time.time()

    # 露出面积要按**全部**零件算（只跑子集时也要，否则露出量会算错）
    exposed_all = exposure_map(all_files)
    own_total = sum(visible_pixels(f) for f in all_files)
    exp_total = sum(exposed_all.values())
    print(f"露出面积：自身合计 {own_total} px，叠加后露出 {exp_total} px"
          f"（被上层遮住 {100 - exp_total * 100 // max(1, own_total)}%）")
    print("")

    for i, f in enumerate(files, 1):
        name = f.stem
        out_dir = parts_dir / name
        if args.reuse and (out_dir / "shapes.json").exists():
            print(f"[{i}/{len(files)}] {name} 已有数据集，跳过")
            continue

        sd = str(Path(args.sessions).resolve() / name)
        vis = visible_pixels(f)

        failed = False
        for step in (["session", "new"], ["set", "project-name", name],
                     ["set", "object-type", "ui_control"], ["next"]):
            code, out = run(exe, sd, step)
            if code != 0:
                print(f"    x {' '.join(step)} 失败（{code}）：{out.strip()[:200]}")
                failed = True
                break
        if failed:
            continue

        # 拿工具实测的边缘密度作为预算依据写进汇总。用 --input 直接分析源图，
        # 不需要先进步骤 2 加图（加了还要再换成放大图，白绕一趟）。
        code, out = run(exe, sd, ["fit", "recommend", "--input", str(f)], json_out=True)
        edge = 0.0
        try:
            rec = json.loads(out[out.index("{"):])["data"]
            edge = float(rec["image"]["edge_density"])
        except Exception:
            print("    ! 拿不到 recommend 的分析结果，按 0 处理")
        budget, reserve, scale, why = plan_for(name, exposed_all[name], edge)

        print(f"[{i}/{len(files)}] {name}  {vis}px 自身 / {exposed_all[name]}px 露出  "
              f"边缘密度 {edge:.3f}  预算 {budget}  预留 {reserve}%  ×{scale}  ← {why}")

        # 需要放大时换成放大后的 PNG（引擎只缩不放，必须自己先放大）
        feed = f
        if scale > 1:
            zoom_dir = parts_dir / "_upscaled"
            zoom_dir.mkdir(exist_ok=True)
            feed = zoom_dir / f"{name}_x{scale}.png"
            if not feed.exists():
                upscale_edge_aware(f, feed, scale)

        code, out = run(exe, sd, ["image", "add", str(feed)])
        if code != 0:
            print(f"    x image add 失败（{code}）：{out.strip()[:200]}")
            continue
        code, out = run(exe, sd, ["next"])
        if code != 0:
            print(f"    x next 失败（{code}）：{out.strip()[:200]}")
            continue

        for kv in (["fit", "mode", "transparent"],
                   ["advanced", "set", "max-dim", str(FIT_SHAPES_MAX_DIM * scale)],
                   ["advanced", "set", "reserve-ratio", str(reserve)],
                   ["advanced", "set", "candidates", str(CANDIDATES)],
                   ["advanced", "set", "speed", str(SPEED)],
                   ["advanced", "set", "edge-aware", "on"],
                   ["advanced", "set", "alternate-bg", "on"],
                   ["advanced", "set", "alternate-interval", str(ALTERNATE_INTERVAL)],
                   ["advanced", "set", "alpha-threshold", str(ALPHA_THRESHOLD)],
                   ["fit", "shapes", str(budget)]):
            code, out = run(exe, sd, kv)
            if code != 0:
                print(f"    x {' '.join(kv)} 失败（{code}）：{out.strip()[:200]}")
                failed = True
                break
        if failed:
            continue

        t0 = time.time()
        code, out = run(exe, sd, ["fit", "start", "--until", "full", "--ack-high-res"], json_out=True)
        elapsed = time.time() - t0
        if code != 0:
            print(f"    x 拟合失败（{code}）：{out.strip()[:200]}")
            continue

        run(exe, sd, ["next"])
        code, out = run(exe, sd, ["export", "dataset", "--out", str(out_dir)], json_out=True)
        if code != 0:
            print(f"    x 导出失败（{code}）：{out.strip()[:200]}")
            continue
        try:
            d = json.loads(out[out.index("{"):]).get("data", {})
            quality = d.get("quality", {})
        except Exception:
            d, quality = {}, {}

        # 坐标换算回源图像素空间 + 用源图空间重绘 preview（×1 时也要，
        # 否则各部件 preview 的空间不统一，下游又要靠猜）
        rescale_dataset(out_dir, scale, f)

        print(f"    ok {d.get('shape_count')} 图元  rmse {quality.get('rmse')}  "
              f"覆盖 {quality.get('coverage_percent')}%  拟合 {elapsed:.1f}s")
        summary.append({
            "part": name, "visible_px": vis, "exposed_px": exposed_all[name],
            "edge_density": round(edge, 4), "reserve_ratio": reserve,
            "upscale": scale, "why": why,
            "budget": budget, "shapes": d.get("shape_count"),
            "rmse": quality.get("rmse"), "match_percent": quality.get("match_percent"),
            "coverage_percent": quality.get("coverage_percent"),
            "fit_seconds": round(elapsed, 1), "dataset": name,
        })

    total = sum(s["shapes"] or 0 for s in summary)
    (parts_dir / "_summary.json").write_text(json.dumps({
        "settings": {
            "max_dim": FIT_SHAPES_MAX_DIM, "candidates": CANDIDATES, "speed": SPEED,
            "alternate_interval": ALTERNATE_INTERVAL, "alpha_threshold": ALPHA_THRESHOLD,
            "mode": "transparent", "edge_aware": True, "alternate_bg": True,
            "total_shapes": total,
            "budget_rule": "手写预算表（PLAN，编号→预算/reserve/倍数/依据）："
                           "线条类给 reserve 50 让精度阶段描线、细线部件再放大 3 倍拟合；"
                           "平涂大块给低 reserve 与 1 倍；表外部件按露出面积+边缘像素数估算",
            "coordinate_space": "全部数据集已换算回 411x600 源图像素；"
                                "拟合倍数记在 manifest.preprocess.source_upscale",
            "note": "max-dim / 模式 / 开关 / alpha 阈值对所有部件一致；"
                    "预算、reserve-ratio、拟合倍数按部件不同（都不改变最终坐标空间）",
        },
        "parts": summary,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n完成 {len(summary)} 个部件，合计 {total} 图元，用时 {(time.time()-t_all)/60:.1f} 分钟")
    n3 = sum(1 for s in summary if s["upscale"] == 3)
    print(f"  用 ×3 拟合的部件：{n3} 个；×1：{len(summary)-n3} 个")
    print(f"汇总：{parts_dir / '_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
