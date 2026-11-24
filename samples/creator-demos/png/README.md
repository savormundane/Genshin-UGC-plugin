# 把 PNG 转成图元素材

用 [v1.0.0](https://github.com/savormundane/miliastra-wonderland-plugin/tree/v1.0.0) 将一张自制的透明 PNG 转为矩形图元。先比较效果，再在最多 20 个图元的预算内选择方案。

## 对 AI 怎么说

下载[原图 checkpoint-marker.png](checkpoint-marker.png)，放进本机 AI 对话可以读取的工程目录。

<img src="checkpoint-marker.png" width="96" alt="原始透明底检查点标记">

> 请用千星奇域插件把当前工程的 checkpoint-marker.png 转成矩形图元素材，最多 20 个控件。先比较原尺寸和候选方案的预览、控件数与误差，再按报告选择保真度最高的可用推荐方案，生成图元数据和 Lua 文件。告诉我产物放在哪、接下来怎么用。

## 实际调用

实跑时，Codex 通过临时测试入口依次调用了下方两条首发版命令。该入口只转发本样图的试算和生成。日常复现可让有终端权限的助手运行同样的命令。

从 v1.0.0 源码根目录用装好依赖的 Python 运行。示例中的输入和输出路径请换成自己的路径，并使用新的输出目录。

```powershell
$markerPng = 'C:\我的关卡\checkpoint-marker.png'
$markerOut = 'C:\我的输出\checkpoint-demo'
python -X utf8 -B scripts/qianxing.py assets preview $markerPng --max-controls 20 --display 144 144 --out "$markerOut\preview"
python -X utf8 -B scripts/qianxing.py assets generate --from-preview "$markerOut\preview\report.json" --candidate grid-25 --out "$markerOut\generated"
```

换图时，从新报告的 `recommendations` 里选候选名称。

## 看到了什么

原图是 24 × 24 的透明底标记。预览统一按 144 × 144 的显示尺寸生成。试算共生成 14 个候选，这里列出原尺寸和两个预算内方案。

| 方案 | 离线软件预览 | 网格 | 矩形控件数 | 图像误差 |
| --- | --- | --- | --- | --- |
| 原尺寸 | ![原尺寸图元预览](preview-original.png) | 24 × 24 | 155 | 0 |
| 首推 `grid-25` | ![11 个矩形图元的预览](preview-grid-25.png) | 6 × 6 | **11** | 约 0.04412 |
| 更省控件的 `grid-12.5` | ![5 个矩形图元的预览](preview-grid-12-5.png) | 3 × 3 | 5 | 约 0.06782 |

选中的 `grid-25` 是预算内误差最低的推荐项。原图中央的十字在缩小网格后失去了清晰轮廓，这是减少控件的代价。生成时重新核对了源图摘要，实际生成 11 个矩形图元。误差是报告中的归一化预乘 RGBA 均方误差，值越小越接近参考图。

## 接下来怎么用

打开 [asset.json](generated/asset.json) 查看调色板和矩形坐标，或把 [data.lua](generated/data.lua) 交给工程里的 Lua 矩形图元绘制逻辑。接入时按目标容器的显示尺寸缩放，并计入容器等其他控件。[生成报告](generated/report.json)和[文件摘要清单](generated/manifest.json)可用于核对产物。

本次通过了离线预览、生成和控件预算检查。千星奇域编辑器中的接入和游戏内显示待实测。 [素材接入说明](../../../references/asset-generation.md#接入与兼容)
