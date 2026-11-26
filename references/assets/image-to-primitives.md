# 图片转图元

先确定目标尺寸和控件预算。单张 PNG 可走本地 MCP。自定网格、富文本、参数化图形或共用多图预算可用下面的终端命令。分层拟合及续算见[拟合配置](asset-fit.md)。

## 单张 PNG 试算与生成

1. 将 PNG 放入客户端已授权的工程目录。调用 `asset_preview`，传入 `input`、新目录 `output` 和任务需要的 `max_controls`。例如将 `checkpoint-marker.png` 试算到 `marker-review`，设定 20 个控件的预算。
2. 工具依次展示参考方案、首选推荐以及更省控件的可用方案，标签注明控件数与预算状态。参考方案采用原尺寸或指定采样网格。同一候选只展示一次。没有可用候选时，查看参考方案和报告诊断。还可以在 `result.candidates` 查看全部试算结果，打开各候选的 `display_preview`。路径相对于返回的 `output`。
3. 调用 `asset_generate`。继续使用同一 `input`，以 `inputs_sha256.input` 为 `sha256`。把试算输出目录下 `report.json` 的绝对路径作为 `report`，从 `outputs_sha256["report.json"]` 取 `report_sha256`。填入确切的 `candidate` 名称和新的 `output`，例如 `marker-material`。源图或报告改变后，重新试算再选方案。
4. 核对 `result.controls` 和最终参考图。文件摘要见 `outputs_sha256`。按[输出格式](#共同处理与输出)接入客户端界面，在目标宿主检查显示。

[跟做 PNG 样例](../../samples/creator-demos/png/README.md) · [MCP 工具与路径规则](../../docs/mcp.md) · [已有制作配置](../workflows/produce.md)

## 单张素材的命令行

`asset_core` 和 `asset_pipeline` 负责图像处理、预算检查、预览和输出。默认生成矩形控件数据，需要文本控件时选 `text`。`auto` 固定选择 `rectangles`，超预算时会报告原因，由调用方决定是否调整参数。

```text
python scripts/qianxing.py assets preview SOURCE.png --max-controls 900 --min-grid 32 18 --max-error 0.04 --display 1600 900 --out NEW_PREVIEW
```

`preview` 接受与 `generate` 相同的生成参数。超预算时按宽高比逐档缩小网格，并在每档比较原色数和减半色数。最多试算 14 组，可用 `--min-grid` 保留最低分辨率。`report.json` 给出各组控件数、预算和误差达成情况、透明边缘变化以及最多三个可用建议。只推荐同时满足声明约束的候选。默认按原参数的网格比较，也可指定目标显示尺寸。误差是归一化的预乘 RGBA MSE，富文本以量化网格作为参考。

从 `recommendations` 或 `candidates` 取满足约束且保留可见内容的候选名称。原文件移动后可显式传入新路径。生成时核对源摘要并重算实际控件预算。有可见内容的原图若在转换后得到零控件，工具会提示调整参数，并在写入前停止。全透明原图可以生成零控件数据，报告标明 `has_foreground: false`。

```text
python scripts/qianxing.py assets generate --from-preview NEW_PREVIEW/report.json --candidate NAME --out NEW_DIRECTORY
```

```text
python scripts/qianxing.py assets generate SOURCE.png --out NEW_DIRECTORY --target auto --step 2 --colors 96 --alpha-min 128 --max-controls 900
python scripts/qianxing.py assets generate SOURCE.png --out NEW_DIRECTORY --target text --width 64 --height 64 --columns 32 --max-bytes 4096 --cell 16 --max-controls 300
python scripts/qianxing.py assets generate SOURCE.json --out NEW_DIRECTORY --target rectangles
```

需要 Python 与 Pillow。step 为下采样步长。width 与 height 成对指定输出网格，使用时 step 须为默认值。单帧位图最多 16,777,216 源像素，输出网格最多 1,048,576 像素。工具在解码前检查两项。超限时按提示预处理源图或调整网格，多帧图先显式拆帧。控件预算由当前任务提供。

## 多素材共用控件预算

```text
python scripts/qianxing.py assets batch preview BATCH.json --out REVIEW
python scripts/qianxing.py assets batch generate REVIEW/report.json --out GENERATED
```

```json
{
  "schema": 1,
  "max_controls": 240,
  "assets": [
    {"key": "frame", "source": "frame.png", "weight": 1, "min_grid": [8, 8]},
    {"key": "action", "source": "action.png", "weight": 4, "max_error": 0.04}
  ]
}
```

每项可指定 `display`、`min_grid`、`max_error` 和生成选项 `options`。预览先为每项选择满足约束且控件最少的候选，再比较每增加一个控件能让加权误差降低多少，据此分配剩余预算。预算不足时查看 `minimum_controls`。找不到可用候选时，按报告中的素材键调整输入或约束。

生成时核对源摘要、实际控件数和参考图摘要。`catalog.json` 给出各项资源，`data.json` 汇集 Lua 可用的数据。已有试算报告也可通过 MCP `produce` 生成，在配置的 `assets` 中加 `{"name":"hud","kind":"batch","source":"REVIEW/report.json"}`。已有 GIL 的 Lua 脚本可通过 [`append_client_ui`](../gil/native-authoring.md#追加客户端界面模块) 使用这份数据。

## 分层拟合与续算

用 [`assets fit`](asset-fit.md) 输入图像与显式配置，查看误差、透明轮廓和最终控件数，再按需要细化或从检查点续算。软件预览用于选方案，动画的素材准备、Lua 播放与 GIL 挂载见 [图元动画接入](animation.md)。

## 共同处理与输出

先按 Alpha 阈值将像素分为透明和不透明两类。对预乘 Alpha 的像素做 BOX 缩放后再次二值化，最后量化不透明前景的颜色。矩形与富文本共用这份量化网格。矩形先按行合并同色连续像素，再纵向合并。富文本逐行分块，同时受列数和 UTF-8 字节数限制。`max-controls` 限制实际生成的控件数。超限时，报告会给出当前网格和控件数。可缩小网格或减少矩形色数，也可根据文本控件的容量调整分块上限。需要指定误差目标、分层配额或从检查点恢复时用 [assets fit](asset-fit.md)。

结果包括 `asset.json`（源摘要、坐标、格式和数据）、`data.lua`（运行数据）、`preview.png`（参考网格）、`report.json`（参数、预算和证据）和 `manifest.json`（各产物摘要）。参数化输入还会保留 `source.json`。工具在临时目录生成文件，完成后保存到新目录。整个流程可离线执行，无需启动外部进程，也不会修改安装目录。

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

客户端负责创建实际模板、换算坐标并接入数据，动画使用帧或分层数据。GIA/GIL 封装和挂载需按已确认的文件结构另行处理。查看布局可用 `qianxing.py assets layouts SOURCE.gil`。

`pixel_to_lua.py` 和 `assets text/info/layouts` 保留各自的参数与产物。矩形和富文本转换共用 [素材核心](../../scripts/miliastra/assets/core.py)。 [富文本数据](rich-text-assets.md) · [点阵帧动画](animation.md#点阵帧)
