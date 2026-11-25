# 富文本点阵与布局清点

## 选择路线

新任务用 [内置素材生成](image-to-primitives.md) 的 `assets generate`，选择矩形或 `text` 输出。旧脚本 `assets_text.py` 继续接受原参数，生成彩色方块富文本和文本框数据。转换算法由 `asset_core` 提供。已有项目继续使用约定的交付格式，变更格式前应征得用户同意。播放已有数据按动画流程接入，写入 GIL 则按存档流程操作。

## 使用

需要 Python 与 Pillow；布局清点使用包内离线工具链，不依赖 Pillow。

```text
python scripts/qianxing.py assets info SOURCE.png
python scripts/qianxing.py assets text SOURCE.png --out NEW_DIRECTORY --width 64 --height 64 --columns 32 --max-bytes 4096 --alpha-min 128 --cell 16 --fit auto
python scripts/qianxing.py assets layouts SOURCE.gil
```

工具只读原图，输出目录必须是新目录。多帧图片需先拆帧。工具将网格限制在 1,048,576 像素以内，以控制资源开销。先对预乘 Alpha 的像素做 BOX 缩放，再按 Alpha 阈值二值化。每行按连续的不透明片段分块。同一片段内连续且 RGB 相同的像素共用一个 `color` 标签。每块必须同时满足列数和 UTF-8 字节预算，标签也计入字节数。预算连一个像素都放不下时，工具会拒绝输出。参数以当前宿主验证和项目预算为准。

fit=auto按实际列数设置框宽；fit=fixed按指定列数保留框宽。它们是本工具的布局策略，不等同于其他工具的v1/v2实现。坐标原点在左上，cell是设计单位和建议字号；方块字形宽高、内边距、行距和缩放仍需当前宿主校准。

## 产物与接入

- tiles.json：源摘要、网格、块坐标/尺寸、富文本、字号、文本框数和总字节数。
- data.lua：相同块数据，供客户端按实际模板创建文本控件，不包含虚构模板ID。
- preview.png、preview.html：采样网格参考图，不能作为游戏中文字渲染效果或导入验收。

将块文本、字号、位置和尺寸交给客户端工作流，使用已有文本模板并关闭会改变像素排布的字号自适应。官方界面布局资料明确支持color标签；方块字形覆盖、尺寸与设备效果仍需编辑器及实机验证。

`layouts` 只读列出包内解码器识别的 UI 根记录 GUID 和名称。这些根记录没有 `parent` 字段 504，已知的控件库根记录会被排除。其他版本的布局需按实际结构核对。遇到重复 GUID、未知根结构或损坏文件时，工具会拒绝处理。

## GIL/GIA边界

写入 GIL 时，先取得实际布局、文本模板、设备坐标和字段样本，再用 `miliastra-gil` 局部写入并回读，核对保护字段。`tiles.json` 供客户端接入，HTML 参考图供检查采样网格。通过 Ayaya 接入时，按其流程单独生成 UI bundle。

GIA的classic/unlimited名称只证明外部工具具有该接口，不能据此推断转换字段、数量限制或兼容性。未提供并核验双模式样本时不修改模式标志；已有GIA读写、节点编译和封装沿用原工具。不得将接口清单或静态字符串分析描述为已恢复原算法或已实现模式转换。
