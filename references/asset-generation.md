# 内置素材生成

## 一个入口

素材由插件自有asset_core与asset_pipeline实现，共用图像处理、预算检查、预览及交付。Agent根据目标选择输出类型，用户无需选择框架。默认生成矩形控件数据；需要文本控件时选text。auto固定选择rectangles，不在预算超限时静默换路线或降低质量。

```text
python scripts/qianxing.py assets generate SOURCE.png --out NEW_DIRECTORY --target auto --step 2 --colors 96 --alpha-min 128 --max-controls 900
python scripts/qianxing.py assets generate SOURCE.png --out NEW_DIRECTORY --target text --width 64 --height 64 --columns 32 --max-bytes 4096 --cell 16 --max-controls 300
python scripts/qianxing.py assets generate SOURCE.json --out NEW_DIRECTORY --target rectangles
```

需要Python与Pillow。step为下采样步长；width/height成对给定时直接指定输出网格，不能与非默认step同时使用。所有预算来自当前任务，不把示例当平台限制。原图只读，多帧图先显式拆帧。网格上限1048576像素是本工具资源保护值。

## 共同处理与输出

先alpha阈值硬化、预乘BOX缩放、再硬化；对不透明像素做前景调色板量化。矩形和富文本使用完全相同的量化参考网格。矩形采用水平行程与纵向无损合并；富文本按连续不透明区域逐行分块，用color标签合并同色字符，每块按列数和UTF-8字节数双重限制。max-controls限制实际生成矩形/文本框总数，超限拒绝提交整个输出目录。

交付统一为asset.json（源摘要、坐标、格式和数据）、data.lua（当前格式运行数据）、preview.png（参考网格）、report.json（参数/预算/证据）和manifest.json（各产物摘要）。参数化源另保留source.json。采用临时生成后提交新目录，拒绝覆盖；不启动外部进程、不联网、不修改安装目录。

矩形坐标以左上网格像素为原点，Lua保留w/h/maxRects/palette/rects结构；富文本坐标为左上设计单位，Lua含tiles的坐标、尺寸、fontSize和text。cell是设计单位与建议字号，fit=auto按实际列数设置宽度，fixed按指定列数保留框宽。富文本字形、行距和内边距需按宿主校准，参考图不是实际文字渲染。

## 无需位图的基础图形

使用schema=1的JSON描述矩形、椭圆和线条，以列表顺序进行RGBA叠加，再进入相同编译核心。Agent可直接编写图标、背景块与简单装饰的参数源。此能力不等于复杂插画生成、位图几何拟合或其他工具原算法恢复。

```json
{
  "schema": 1,
  "size": [32, 32],
  "shapes": [
    {"kind": "rect", "box": [0, 0, 31, 31], "color": [20, 35, 61, 255]},
    {"kind": "ellipse", "box": [4, 4, 27, 27], "color": [210, 180, 90, 255]},
    {"kind": "line", "points": [8, 16, 23, 16], "width": 2, "color": [255, 255, 255, 255]}
  ]
}
```

坐标与通道为整数，box端点包含在范围内；按像素网格绘制，不含抗锯齿。画布每边至多4096、总像素至多1048576；形状至多10000项。非法字段、越界、未知图形或错误通道拒绝生成，不自动夹取坐标。

## 接入与兼容

客户端能力负责真实模板创建、坐标缩放及数据接入；动画能力消费帧/分层数据；文件能力负责有真实结构依据的GIA/GIL封装与挂载。当前生成器不直接写GIL。布局清点仍可用 `qianxing.py assets layouts SOURCE.gil`。

旧pixel_to_lua.py以及assets text/info/layouts继续兼容，矩形和文本算法已共用asset_core；旧入口保留各自既有参数与产物，不作为新任务的首选流程。格式细节见 [富文本数据](rich-text-assets.md)，动画见 [点阵运行时](pixel-runtime.md)。需要高级拟合时按当前分发实际提供的能力执行，不能把未随包提供的工具当作依赖。
