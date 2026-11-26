# 素材检查与差异

单份素材用 `python scripts/qianxing.py assets check INPUT` 检查，两份素材用 `assets diff OLD NEW` 比较。工具只读输入并输出 JSON，依赖 Pillow 和现有素材处理模块，无需挂载到游戏。

支持单帧图像、schema 1 参数化图形，以及 `miliastra-wonderland-assets` schema 1 的矩形和富文本数据。旧素材仍可读取。工具检查尺寸、颜色、调色板、矩形是否越界或重叠，以及声明的控件数量。报告包含透明与半透明像素数、颜色数、实际控件数、文件大小和 RGBA 摘要。控件上限按实际数量核对，富文本逐块检查 UTF-8 字节数。超限时报告实际值、上限和超限图块的索引。旧产物缺少声明时，对应检查标为 `not_checked`。

两份输入可以采用不同的受支持格式。工具将它们转为统一的 RGBA 表示，再比较摘要和统计结果。摘要不同说明像素有差异，美术效果仍需查看图像。宿主能否直接加载 PNG 需单独验证。试算候选用 `assets preview`，选定后用 `assets generate`。导入已校准的 GIA 矩形装饰用 `assets import-gia`。 [图片转图元](image-to-primitives.md) · [GIA 素材导入](native-assets.md)

按参数化图形或生成素材的现有 schema 编辑字段。测试覆盖两种尺寸和颜色的参数化图形及其生成的 `asset.json`。矩形越界或重叠、控件数不符、schema 未知、单幅超过 1,048,576 像素时，检查失败。报告分别记录软件重建、平台兼容性、宿主渲染和设备性能。
