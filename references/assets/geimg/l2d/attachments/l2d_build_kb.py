"""把「知识库」拼成一个单文件，方便整份喂给 AI 或一次性打印。

多文件适合人读（按需翻），单文件适合整份投喂。两者内容一致，以多文件为准；
单文件是**生成物**，不要直接改它 —— 改完多文件重跑这个脚本。

用法：
    py -3 build_kb.py            # 拼成 知识库/_全文.md 并校验链接
    py -3 build_kb.py --check    # 只校验（文件是否齐全、README 里的链接是否都指得到）
"""
import argparse
import re
import sys
from pathlib import Path

KB = Path(__file__).resolve().parent.parent / "知识库"
ORDER = [
    "README.md",
    "01-前置-拆分.md",
    "02-拟合-从PNG到图元.md",
    "03-数据格式-图元与导出.md",
    "04-在游戏里重建.md",
    "05-动作与骨骼.md",
    "06-边缘与画质.md",
    "07-API速查与验证状态.md",
    "08-踩坑清单.md",
    "09-端到端SOP与检查表.md",
    "10-补间动画-Tween.md",
    "11-层级与骨骼-父容器.md",
]


def check():
    ok = True
    for name in ORDER:
        p = KB / name
        if not p.exists():
            print(f"  ✗ 缺文件：{name}")
            ok = False
    # README 里表格中的相对链接是否都指得到
    readme = (KB / "README.md").read_text(encoding="utf-8")
    for m in re.finditer(r"\]\((?!https?:)([^)#]+)\)", readme):
        target = m.group(1)
        if not (KB / target).exists():
            print(f"  ✗ README 里的链接指不到：{target}")
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不生成")
    args = ap.parse_args()

    print(f"知识库目录：{KB}")
    if not check():
        print("校验失败")
        return 1
    print(f"  ✓ {len(ORDER)} 个文件齐全，README 里的相对链接都能指到")
    if args.check:
        return 0

    parts = []
    for name in ORDER:
        text = (KB / name).read_text(encoding="utf-8")
        # 单文件里把内部链接展开成锚点注释（拼起来后相对链接就没意义了）
        text = re.sub(r"\]\((?!#)([^)#]+)\.md\)", r"](\1.md)", text)
        parts.append(f"\n\n<!-- ===== {name} ===== -->\n\n{text.rstrip()}\n")
    head = ("# 知识库全文（生成物，勿手改）\n\n"
            "> 由 `attachments/l2d_build_kb.py` 从同目录的多份文件拼成，便于整份投喂给 AI。\n"
            "> 修改请改多文件版本后重跑脚本。\n")
    out = KB / "_全文.md"
    body = head + "".join(parts)
    out.write_text(body, encoding="utf-8")

    chars = len(body)
    print(f"  ✓ 写出 {out.name}：{chars/1024:.0f} KB，约 {chars/1.6:.0f} 字"
          f"（10 个文件合并）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
