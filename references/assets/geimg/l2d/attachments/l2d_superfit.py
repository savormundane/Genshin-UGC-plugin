"""
万元素超级拟合：1 万图元预算 + 本轮所有实测结论，输出到独立目录。

配置取自本轮实测（每一项都有对照图）：
  · **edge-aware 开**（要保住边缘形状就必须开，透明底 PNG 尤其是）。它拦住的是
    "图元被画进透明区、鼓到轮廓外"；关掉它会让溢出更明显（小部件甚至整块被灌满）。
    若遇到"勾线画不出来"，先按知识库 `02` 的 2.2 那节的假设对照复现一次，再决定。
  · 细结构部件 **×3 分辨率**：图元尺寸有绝对像素下限（圆约 2 源像素、线约 1 源像素），
    411×600 下这些下限比勾线还宽 → 1~2px 的线表达不出来。
  · reserve-ratio **50**：让精度阶段（小图元）拿一半预算，我们观察到发丝分股更好
    （工具手册里另一组误差口径的对照认为差异在波动内 —— 这是取舍，不是定论）。
  · 预算按实测拐点分配：小部件（五官/眼白）饱和很快，给多了收益递减（实测 mouth 120 图元
    跑了 1505s 而 45 图元只要 3.7s，且质量无差别）；大部件（前发/衣服/腿）到 v5 的预算时
    仍在变好，这轮给足。

并行：每个部件一个独立进程 + 独立会话，互不干扰。

用法：
    py -3 l2d_superfit.py --parts "<拆分目录>" --exe "<GE_IMG_Tool.exe 路径>" [--workers 6] [--only 0001]
    （--exe 也可以用环境变量 GEIMG_EXE 指定；两者都不给就用 PATH 里的 GE_IMG_Tool.exe）
"""
import argparse
import importlib.util
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
# 工具本体（命令行）的路径：--exe > 环境变量 GEIMG_EXE > PATH
DEFAULT_EXE = os.environ.get("GEIMG_EXE", "GE_IMG_Tool.exe")


def load_batch_module():
    """复用同目录 l2d_fit_batch.py 的 run / upscale_edge_aware / rescale_dataset。

    知识库里这两个脚本是配套的：l2d_fit_batch.py 是逐部件拟合的完整实现，
    本脚本在它之上加"万元素预算 + 逐部件并行 + 这一轮的参数结论"。
    """
    p = TOOLS / "l2d_fit_batch.py"
    spec = importlib.util.spec_from_file_location("l2d_fit_batch", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# 编号 → (预算, 倍数, 依据)
# 小部件给足即止：它们饱和很快，超配只会让引擎空转（实测 mouth 120 图元 1505s vs 45 图元 3.7s）。
PLAN = {
    "0000": ( 780, 3, "成品里第二大可见面积，线条密集"),
    "0001": (1700, 3, "成品里最大可见面积；v5 到 560 仍在变好，这轮给足"),
    "0002": ( 120, 3, "五官：眉毛（纯线条，饱和快）"),
    "0003": (  90, 3, "五官：眉毛"),
    "0004": (  60, 3, "五官：嘴（45 图元即饱和）"),
    "0006": ( 220, 3, "五官：睫毛 + 睑褶细线"),
    "0007": ( 140, 3, "五官：眼线（边缘密度 1.0）"),
    "0008": ( 220, 3, "五官：两道粗描边"),
    "0009": ( 300, 3, "五官：虹膜（瞳孔/高光/内环）"),
    "0010": (  60, 1, "眼白：平滑渐变、强边缘 0"),
    "0011": ( 280, 3, "五官：虹膜"),
    "0012": (  50, 1, "眼白：平滑渐变"),
    "0013": ( 480, 1, "脸：大片平滑皮肤 + 下巴/耳轮廓"),
    "0014": ( 260, 3, "围巾：边缘密度 0.72"),
    "0015": (1250, 3, "主体：层叠 + 金边；v5 到 420 仍在变好"),
    "0016": ( 350, 3, "飘带：细长轮廓"),
    "0017": ( 260, 3, "发饰"),
    "0018": ( 350, 3, "飘带"),
    "0019": ( 480, 3, "手臂：实测拐点 180（蝴蝶结/袖口在此出现）"),
    "0020": (  40, 1, "被盖住：留底，动画会露"),
    "0021": ( 780, 3, "腿：v5 到 260 仍在变好"),
    "0022": ( 700, 3, "腿"),
    "0023": ( 200, 1, "后布：平色为主"),
    "0024": ( 410, 3, "手臂"),
    "0025": ( 150, 1, "后发：大片平色"),
    "0026": ( 300, 3, "飘带"),
}

BASE_MAX_DIM = 600
CANDIDATES = 64
SPEED = 5
ALPHA_THRESHOLD = 64
ALTERNATE_INTERVAL = 30


def part_id(name: str) -> str:
    for t in name.split("_"):
        if t.isdigit() and len(t) == 4:
            return t
    return ""


def fit_part(args, batch, src_png: Path, work: Path, session_root: Path):
    name = src_png.stem
    pid = part_id(name)
    budget, scale, why = PLAN[pid]
    out_dir = work / name
    sd = session_root / name

    big = src_png
    if scale > 1:
        up = work / "_upscaled" / f"{name}_x{scale}.png"
        up.parent.mkdir(parents=True, exist_ok=True)
        if not up.exists():
            # 先把透明区 RGB 染成邻居颜色，再做 Lanczos 放大：直接插值会把纯白透明区
            # 卷进轮廓最外 1~3px，拟合器照着偏亮像素取样 → 成品带一圈浅色描边。
            # （预乘再插值反而更糟，实测对比见 l2d_fit_batch.upscale_edge_aware 的注释。）
            batch.upscale_edge_aware(src_png, up, scale)
        big = up

    steps = [["session", "new"], ["set", "project-name", name],
             ["set", "object-type", "ui_control"], ["next"],
             ["image", "add", str(big)], ["next"],
             ["fit", "mode", "transparent"],
             ["advanced", "set", "max-dim", str(BASE_MAX_DIM * scale)],
             ["advanced", "set", "reserve-ratio", "50"],
             ["advanced", "set", "candidates", str(CANDIDATES)],
             ["advanced", "set", "speed", str(SPEED)],
             ["advanced", "set", "edge-aware", "on"],    # 要保住边缘形状就开（见知识库 02 的 2.0）
             ["advanced", "set", "alternate-bg", "on"],
             ["advanced", "set", "alternate-interval", str(ALTERNATE_INTERVAL)],
             ["advanced", "set", "alpha-threshold", str(ALPHA_THRESHOLD)],
             ["fit", "shapes", str(budget)]]
    for s in steps:
        code, out = batch.run(args.exe, str(sd), s)
        if code != 0:
            return name, None, f"{' '.join(s)} 失败({code}): {out.strip()[:140]}"

    t0 = time.time()
    code, out = batch.run(args.exe, str(sd), ["fit", "start", "--until", "full", "--ack-high-res"])
    el = time.time() - t0
    if code != 0:
        return name, None, f"拟合失败({code}): {out.strip()[:140]}"

    batch.run(args.exe, str(sd), ["next"])
    code, out = batch.run(args.exe, str(sd), ["export", "dataset", "--out", str(out_dir)])
    if code != 0:
        return name, None, f"导出失败({code}): {out.strip()[:140]}"

    batch.rescale_dataset(out_dir, scale, src_png)      # 坐标/Lua/preview 统一回源图空间

    n = len(json.loads((out_dir / "shapes.json").read_text(encoding="utf-8"))["shapes"])
    return name, {"part": name, "budget": budget, "shapes": n, "upscale": scale,
                  "sec": round(el, 1), "why": why}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True, help="零件目录（读取 part_*.png）")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--exe", default=DEFAULT_EXE,
                    help="GE_IMG_Tool.exe 的路径（也可用环境变量 GEIMG_EXE 指定）")
    ap.add_argument("--sessions", default=None, help="会话根目录")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    batch = load_batch_module()
    parts_dir = Path(args.parts)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    session_root = Path(args.sessions) if args.sessions else out_root / "_sessions"

    files = sorted(parts_dir.glob("part_*.png"))
    if args.only:
        want = [w.strip() for w in args.only.split(",") if w.strip()]
        files = [f for f in files if any(w in f.stem for w in want)]

    total_budget = sum(PLAN[part_id(f.stem)][0] for f in files)
    print(f"部件 {len(files)} 个，预算合计 {total_budget} 图元；并行 {args.workers} 进程")
    print(f"工具：{args.exe}")
    print("配置：edge-aware 开（要保边就开）/ reserve 50 / 细结构部件 ×3\n")

    results, errors = [], []
    t_all = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fit_part, args, batch, f, out_root, session_root): f for f in files}
        done = 0
        for fut, f in futs.items():
            name, rec, err = fut.result()
            done += 1
            if err:
                errors.append((name, err))
                print(f"[{done}/{len(files)}] {name}  x {err}")
            else:
                results.append(rec)
                print(f"[{done}/{len(files)}] {name}  {rec['shapes']} 图元  ×{rec['upscale']}  "
                      f"{rec['sec']}s")

    total = sum(r["shapes"] for r in results)
    (out_root / "_summary.json").write_text(json.dumps({
        "settings": {"mode": "transparent", "max_dim_base": BASE_MAX_DIM,
                     "candidates": CANDIDATES, "speed": SPEED,
                     "reserve_ratio": 50, "edge_aware": True,
                     "alternate_bg": True, "alternate_interval": ALTERNATE_INTERVAL,
                     "alpha_threshold": ALPHA_THRESHOLD,
                     "total_shapes": total, "budget_total": total_budget,
                     "note": "edge-aware 开（要保住边缘形状就开）。"
                             "本文件早期曾把这项写成 false 而实际发给引擎的是 on，"
                             "与 manifest/session 冲突——以 manifest/session 为准；"
                             "差异排查方法见知识库 02 的 2.2"},
        "parts": sorted(results, key=lambda r: r["part"]),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n完成 {len(results)} 个部件，合计 {total} 图元，"
          f"用时 {(time.time()-t_all)/60:.1f} 分钟")
    if errors:
        print(f"失败 {len(errors)} 个：")
        for n, e in errors:
            print(f"  {n}: {e}")
    print(f"输出目录：{out_root}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
