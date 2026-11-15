# -*- coding: utf-8 -*-
"""把零件与自动拼接结果内联进「拼合台.html」，产出一个可以直接双击打开的单文件。

零件在这里被**裁到内容 bbox** 再转 base64 —— 导出的 PNG 带 2px padding，
内联时去掉它，HTML 里的 (w,h) 才等于真实内容尺寸、绕中心放置才自然。
"""
import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import assemble as asm  # noqa: E402

TEMPLATE = HERE / "templates" / "assembly.template.html"
OUT = ROOT / "拼合台.html"


def main():
    idx = json.loads((ROOT / "parts_index.json").read_text(encoding="utf-8"))
    names = {}
    nf = ROOT / "parts_names.json"
    if nf.exists():
        names = json.loads(nf.read_text(encoding="utf-8"))

    out_parts = []
    total = 0
    for it in idx["parts"]:
        im = Image.open(ROOT / "parts_final" / it["file"]).convert("RGBA")
        ox, oy = it["origin"]
        bx, by, bw, bh = it["atlas_bbox"]
        im = im.crop((bx - ox, by - oy, bx - ox + bw, by - oy + bh))
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
        raw = buf.getvalue()
        total += len(raw)
        out_parts.append({
            "id": it["id"],
            "name": names.get(str(it["id"]), it["file"]),
            "w": bw, "h": bh,
            "atlas_bbox": it["atlas_bbox"],
            "src": "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
        })

    layout = asm.build()
    zmap = {i["note"]: i["z"] for i in layout["instances"]}
    auto = {
        "canvas": layout["canvas"],
        "instances": [{k: v for k, v in i.items() if k != "note"} | {"note": i["note"]}
                      for i in layout["instances"]],
    }

    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__META__*/ null",
                        json.dumps({"atlas": idx["atlas"], "atlas_size": idx["atlas_size"],
                                    "parts_count": len(out_parts)}, ensure_ascii=False))
    html = html.replace("/*__PART_DATA__*/ []", json.dumps(out_parts, ensure_ascii=False))
    html = html.replace("/*__AUTO_LAYOUT__*/ null", json.dumps(auto, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")

    print(f"写出 {OUT}")
    print(f"  零件 {len(out_parts)} 个，内联 PNG {total/1024:.0f} KB，HTML {OUT.stat().st_size/1024:.0f} KB")
    print(f"  自动拼接图层 {len(auto['instances'])} 个")


if __name__ == "__main__":
    main()
