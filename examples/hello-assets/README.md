# Hello Assets：把图片变成图元

一个不需要私人工程的完整小案例：从 128×128 的蓝金徽章 PNG，生成 **9 个矩形、Lua 数据和软件预览**。预算上限为 16 个矩形。

![本例实际生成的软件预览](generated/preview.png)

[回到第一次使用](../../docs/getting-started.md) · [素材生成格式](../../references/asset-generation.md)

## 这里有什么

| 文件 | 内容 |
| --- | --- |
| [source.json](source.json) | 徽章的参数化源：深蓝背景、金色方框、深蓝中心，全部由整数坐标矩形组成。 |
| [input.png](input.png) | 使用插件的 `asset_pipeline.procedural` 从上述源生成的输入 PNG。 |
| [generated/asset.json](generated/asset.json) | 坐标、调色板和 9 个矩形的数据。 |
| [generated/data.lua](generated/data.lua) | 可由后续控件代码读取的 Lua 数据表。 |
| [generated/preview.png](generated/preview.png) | 本次生成器输出的颜色与几何预览。 |
| [generated/report.json](generated/report.json) | 本次实际输入、参数、矩形数量和处理范围。 |
| [generated/manifest.json](generated/manifest.json) | 输入及生成文件的 SHA-256 摘要。 |

这是当前源码新增的示例，尚未包含在已经发布的 4.1.0 ZIP 中。已安装 4.1.0 的用户可以单独下载 `input.png`，使用现有工具处理，不必重新安装插件。

## 在 Windows 上自己做一次

1. 下载 [input.png](input.png) 到自己的项目目录，例如 `C:\Qianxing\project\hello-assets\input.png`。
2. 按[独立运行环境](../../docs/runtime-environment.md#已安装插件直接复用环境)定位已有专用 Python 和 `scripts\qianxing.py`，设置其中的 `$ugcPython`、`$ugcCli`。
3. 在 PowerShell 运行：

```powershell
& $ugcPython $ugcCli assets generate 'C:\Qianxing\project\hello-assets\input.png' --out 'C:\Qianxing\outputs\hello-assets' --target rectangles --width 128 --height 128 --colors 4 --max-controls 16
```

`--out` 必须是尚不存在的新目录。重做时换一个目录名，例如 `hello-assets-2`；生成器不会覆盖以前的结果。打开新目录中的 `preview.png`，并查看 `report.json` 的 `controls` 字段。

也可以把图片路径和上述目标交给能运行本地命令的助手，让它使用已安装的 Genshin-UGC 工具完成。

## 本次实际生成记录

在仓库根目录执行的命令：

```text
python -B scripts/qianxing.py assets generate examples/hello-assets/input.png --out examples/hello-assets/generated --target rectangles --width 128 --height 128 --colors 4 --max-controls 16
```

| 项目 | 本次结果 |
| --- | --- |
| 输入与输出网格 | 128×128 |
| 颜色上限 / 实际调色板 | 4 / 2 |
| 矩形预算 / 实际数量 | 16 / 9 |
| Lua 数据文件 | 245 字节 |
| 输入 PNG 的 SHA-256 | `49cb1d890d70503689a26589db3f51c53bbeb691aedaf7112362fbdef6956c42` |
| 运行环境 | Linux、Python 3.12.14、Pillow 13.0.0；使用当前仓库的 4.1.0 素材生成实现。 |

这些文件来自本次实际运行。运行环境使用已有 Pillow，与 Windows 发行锁定的 Pillow 版本不同；记录展示当前输入的制作结果，不要求不同依赖版本输出相同的 PNG 字节。

这是本地素材生成案例，没有安装完整 Windows 插件，也未导入千星奇域编辑器或进入游戏。`data.lua` 是素材数据，接入游戏时还需要控件创建、坐标与挂载逻辑；`preview.png` 是软件参考图。

## 输入 PNG 的来源

`source.json` 使用现有 schema 1 参数化图形格式。在仓库根目录，以下 Python 代码可重新得到输入图片；自行重做时请将输出位置改到自己的项目目录。

```python
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from asset_pipeline import procedural

source = Path("examples/hello-assets/source.json")
spec = json.loads(source.read_text(encoding="utf-8"))
procedural(spec).save("hello-assets-input.png")
```

本例只使用两种纯色和基础矩形，不依赖外部图片、游戏截图或私人素材。较复杂图片的矩形成本取决于尺寸、颜色和轮廓；可以据实际报告调整网格与预算。
