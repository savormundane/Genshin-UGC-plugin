# 富文本点阵与布局清点

## 选择路线

新任务统一使用 [内置素材生成](image-to-primitives.md) 的 assets generate，选择矩形或text输出。旧assets_text.py保留兼容参数和产物，算法已纳入共享asset_core；输出彩色方块富文本和文本框数据，不能未经用户同意替换已有交付格式。已有数据的播放由动画工作流负责；存档写入由存档工作流负责。

## 使用

需要 Python 与 Pillow；布局清点使用包内离线工具链，不依赖 Pillow。

```text
python scripts/qianxing.py assets info SOURCE.png
python scripts/qianxing.py assets text SOURCE.png --out NEW_DIRECTORY --width 64 --height 64 --columns 32 --max-bytes 4096 --alpha-min 128 --cell 16 --fit auto
python scripts/qianxing.py assets layouts SOURCE.gil
```

原图只读；输出目录必须不存在。多帧图片必须先显式拆帧。网格上限1048576像素为工具资源保护值，非平台限制。预乘BOX缩放后按alpha阈值二值化；透明位置不生成字符，按连续不透明片段逐行分块，相同RGB连写为一个color标签。每块同时受列数和UTF-8字节预算约束（包含标签），不足容纳一个像素时拒绝输出。参数应来自当前宿主和目标预算，不把默认值当作官方限制。

fit=auto按实际列数设置框宽；fit=fixed按指定列数保留框宽。它们是本工具的布局策略，不等同于其他工具的v1/v2实现。坐标原点在左上，cell是设计单位和建议字号；方块字形宽高、内边距、行距和缩放仍需当前宿主校准。

## 产物与接入

- tiles.json：源摘要、网格、块坐标/尺寸、富文本、字号、文本框数和总字节数。
- data.lua：相同块数据，供客户端按实际模板创建文本控件，不包含虚构模板ID。
- preview.png、preview.html：采样网格参考图，不能作为游戏中文字渲染效果或导入验收。

将块文本、字号、位置和尺寸交给客户端工作流，使用已有文本模板并关闭会改变像素排布的字号自适应。官方界面布局资料明确支持color标签；方块字形覆盖、尺寸与设备效果仍需编辑器及实机验证。

layouts只读列出包内解码器识别的无parent字段504的UI根记录GUID和名称，排除已知的控件库根记录。输出的是已知结构下的布局根记录，不扫描猜测任意整数，也不保证所有未来版本的布局语义。重复GUID、未知根结构或损坏文件拒绝处理。

## GIL/GIA边界

本工具不直接将富文本块写入GIL。需要先取得实际布局、文本模板、设备坐标和字段样本，再由miliastra-gil执行局部写入、字段保护及回读。当前不能将tiles.json当成Ayaya UI bundle直接导入；HTML参考图也不是编辑器UI工程。

GIA的classic/unlimited名称只证明外部工具具有该接口，不能据此推断转换字段、数量限制或兼容性。未提供并核验双模式样本时不修改模式标志；已有GIA读写、节点编译和封装沿用原工具。不得将接口清单或静态字符串分析描述为已恢复原算法或已实现模式转换。
