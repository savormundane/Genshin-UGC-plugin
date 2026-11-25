# 把 PNG 转成图元素材

将一张公开的透明 PNG 转为矩形图元。在最多 20 个图元的预算内选择方案，再把随附的 Lua 样例接入千星奇域界面。

## 对 AI 怎么说

下载[原图 checkpoint-marker.png](checkpoint-marker.png)，放进本机 AI 对话可以读取的工程目录。

<img src="checkpoint-marker.png" width="96" alt="原始透明底检查点标记">

> 请用千星奇域插件把当前工程的 checkpoint-marker.png 转成矩形图元素材，最多 20 个控件。先比较原尺寸和候选方案的预览、控件数与误差，再按报告选择保真度最高的可用推荐方案，生成图元数据和 Lua 文件。告诉我产物放在哪、接下来怎么用。

## 用本地 MCP 复现

在已授权的工程目录放入样图，准备独立输出位置，再发送上面的提示。助手调用 `asset_preview` 比较预算和预览，选择方案后用 `asset_generate` 写入新目录。 [MCP 参数与摘要](../../../references/assets/image-to-primitives.md#单张-png-试算与生成)

工具依次返回「原尺寸参考」`original`（155 个控件，超预算）、「首选推荐」`grid-25`（11 个控件，预算内）和「更省控件」`grid-12.5`（5 个控件，预算内）。

在关闭终端工具的 Codex 会话中验证了这两步。对选中的 `grid-25`，从生成的 Lua 中读回了 11 个矩形。用同一份试算报告在命令行生成，五个交付文件逐字节一致。

## 用终端复现

下方对照图和交付文件来自 [v1.0.0](https://github.com/savormundane/miliastra-wonderland-plugin/tree/v1.0.0) 的 CLI 实测。从对应版本的源码根目录运行，替换输入和输出路径，并使用新的输出目录。

```powershell
$markerPng = 'C:\我的关卡\checkpoint-marker.png'
$markerOut = 'C:\我的输出\checkpoint-demo'
python -X utf8 -B scripts/qianxing.py assets preview $markerPng --max-controls 20 --display 144 144 --out "$markerOut\preview"
python -X utf8 -B scripts/qianxing.py assets generate --from-preview "$markerOut\preview\report.json" --candidate grid-25 --out "$markerOut\generated"
```

换图时，从新报告的 `recommendations` 里选候选名称。

## 看到了什么

原图是 24 × 24 的透明底标记。试算共生成 14 个候选。下表使用首发版 CLI 生成的 144 × 144 对照图，列出原尺寸和两个预算内方案。

| 方案 | 离线软件预览 | 网格 | 矩形控件数 | 图像误差 |
| --- | --- | --- | --- | --- |
| 原尺寸 | ![原尺寸图元预览](preview-original.png) | 24 × 24 | 155 | 0 |
| 首推 `grid-25` | ![11 个矩形图元的预览](preview-grid-25.png) | 6 × 6 | **11** | 约 0.04412 |
| 更省控件的 `grid-12.5` | ![5 个矩形图元的预览](preview-grid-12-5.png) | 3 × 3 | 5 | 约 0.06782 |

选中的 `grid-25` 在预算内误差最低。网格变粗后控件数量减少，原图中央十字的轮廓也变得模糊。生成时重新核对了源图摘要，共生成 11 个矩形图元。报告使用归一化预乘 RGBA 均方误差，值越小越接近参考图。

## 拟合并预览可挂载的 Lua

将原图和 [fit.json](fit.json) 放入会话已授权的工程，然后发送下面的请求。

> 用内置拟合处理 checkpoint-marker.png，使用 fit.json，最多 20 个矩形。保留可挂载 Lua，再用 Beyond 预览这份 Lua。告诉我实际控件数、边缘遗漏和误差目标是否达成。

1. 用 `asset_fit` 传入原图和 `fit.json`，输出到新目录。查看 `image/preview.png`、`catalog.json` 里的实际误差和建议细化区域。
2. 用 `simulate` 传入交付的 `beyond.json` 绝对路径和对应摘要，设 `preview=true`。打开 `preview.png` 查看画面，读 `render.json` 和 `external-simulation.json` 核对控件及日志。
3. 将 `mounted.lua` 中的 `template_index` 设置为当前关卡图片模板索引，按下面的挂载步骤映射该文件。样例配置中的索引用于随输出生成的软件模板。

本次用 20 个矩形，实测误差约 0.04499，目标为 0.035。Beyond 日志确认创建 20 个矩形，控件树和拟合图在 144 × 144 的显示区域逐像素核对通过。简单图标也可用上面的 11 控件网格方案。 [拟合配置和局部细化](../../../references/assets/asset-fit.md#生成可挂载的-lua-和软件预览)

已有导出的 GIL 时，可说「将这张 PNG 拟合到这个关卡的 CheckpointMarker 容器，使用现有 MarkerRect 图片模板，最多 20 个控件。先预览，确认后另存」。工具按实际文件解析模板和容器，并将拟合结果交给同一关卡的挂载计划。检查点样例的拟合与回读回归确认 Lua 正文一致，原文件保持原字节。软件预览模拟同一份 Lua，关卡的实际画面在编辑器及游戏中确认。 [从 GIL 绑定拟合](../../../references/assets/asset-fit.md#生成可挂载的-lua-和软件预览) · [审阅并应用挂载](../../../references/gil/native-authoring.md#将生成的-lua-挂到现有关卡)

## 接下来怎么用

[checkpoint-marker.lua](checkpoint-marker.lua) 已包含 `grid-25` 的 11 个矩形和绘制代码。将它保存到本机，先在一张测试关卡里接入。

### 准备一个挂载节点和图片模板

1. 在「界面控件组管理 → 界面布局」添加**客户端控件容器**，保持它激活且可见。选中它，从「画布设置 → 前往编辑」进入详情。添加一个客户端**容器节点**，命名为 `CheckpointMarker`，居中放置，宽高各填 **144**。
2. 在「界面控件组库 → 客户端控件模板」添加一个**图片**，将它作为根控件存为模板 `MarkerRect`。图片源选「静态引用」，选一张可着色、白色实心、直角的单图。把尺寸临时调成长方形，确认图片能铺满矩形，然后关闭遮罩、边缘羽化和进度填充。
3. 在模板库点选 `MarkerRect` 的图片根控件，抄下本关卡显示的**控件模板索引**。在下载的 Lua 中查找 `RECT_TEMPLATE_INDEX`，把 `0` 换成这个整数。 [官方控件设置](../../../references/platform/official/概念介绍/客户端控件和客户端脚本__mhbgxf0nynww.md) · [图片设置](../../../references/platform/official/概念介绍/图片控件__mh2oih9jou22.md)

### 挂载并试玩

1. 在客户端脚本资源管理器中「新建脚本映射」，命名为 `checkpoint-marker.lua`，将映射路径关联到刚改好的本地 Lua 文件。
2. 回到 `CheckpointMarker` 节点，在「脚本」页签点击「添加脚本」，选择该映射。保存关卡，在千星沙箱日志窗口勾选「客户端脚本」，开始试玩。
3. 正常时，节点中央出现蓝绿色标记，浅色横带位于中间，四周为透明区域。日志会显示「检查点已创建 11 个矩形。」如果有这条日志但画面空白，先检查客户端控件容器是否可见，再检查模板图片是否能显示并着色。没有这条日志时，核对 `CheckpointMarker` 的挂载和脚本映射路径，查看日志中的具体错误。 [软件对照图](preview-grid-25.png)

### 换图、调尺寸或挪位置

- **换图。** 用前面的试算和生成流程取得新的 `data.lua`。在 `checkpoint-marker.lua` 的 `MARKER DATA` 区域，用新 `data.lua` 的全文替换 `local MARKER = (function()` 与 `end)()` 之间的 `return {...}`。保留外层包装，保存后重新试玩。脚本映射继续关联这一份完整 Lua。
- **尺寸和位置。** `DISPLAY_WIDTH` 和 `DISPLAY_HEIGHT` 控制显示框。默认 **144 × 144**，样例的 6 × 6 网格每格为 24 个设计单位。`OFFSET_X`、`OFFSET_Y` 以挂载节点中心为基准，向右和向上为正。代码会将素材从左上原点转成父节点中心坐标。
- **预算。** 此样例最多创建 20 个图元控件，布局中的容器另计。收到超预算提示时，回到试算选择控件更少的方案。要查看原始调色板、网格坐标和实际控件数，打开 [素材数据](generated/asset.json) 和 [生成报告](generated/report.json)。

### 验证记录

已用临时 GIL 回读图片模板与脚本挂载，通过 Lua 5.3 编译及离线控件模型。按模型输出的 11 个矩形重建画面，与软件对照图一致。模型中停用会隐藏图元，重新启用复用原控件。编辑器接入和游戏内显示待试玩验证。

维护样例时，将 `ui` 模块、生成的 `generated/data.lua` 和绘制源码依次交给 `client assemble`，生成可挂载的单个 Lua 文件。 [绘制源码](checkpoint-marker-render.lua) · [装配与回读检查](../../../scripts/test_release_behaviors.py)
