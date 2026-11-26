# 通用图片拟合

`assets fit` 逐步搜索更接近原图的图元组合。输入为单张图片或明确列出图层的 JSON，每张图最多 262,144 像素。工具在解码前检查总像素数，超限时报告文件名和尺寸并停止。骨骼拆分和游戏内素材接入需另行处理。

```text
python scripts/qianxing.py assets fit icon.png --spec fit.json --out NEW_DIRECTORY
python scripts/qianxing.py assets fit icon.png --spec fit.json --steps 500 --out PARTIAL
python scripts/qianxing.py assets fit icon.png --spec fit.json --resume PARTIAL/state.json --out CONTINUED
```

配置示例：

```json
{"schema":2,"shapes":["circle","ellipse","line","rect"],"budget":80,"max_controls":1000,"alpha_min":1,"work":4000,"seed":7,"target_error":0.001,"anchor":[0,0],"gia":true}
```

圆和椭圆与坐标轴对齐，线条仅支持水平或垂直的一像素线。坐标以图像左上角为原点，`box` 不包含右边界和下边界，`anchor` 为像素锚点。旋转、投影和未知配置均会被拒绝。`budget` 限制拟合图元数，`max_controls` 限制转换后的矩形控件数。`work` 限制候选评估总数，`steps` 只控制本次运行的评估次数。

目标是降低预乘 RGBA 的归一化均方误差。输入、参数、种子与 Pillow 版本固定时，工具从粗到细尝试候选，并局部调整已选图元，只接受误差降低的结果。候选不得覆盖 Alpha 低于阈值的像素。报告列出误差变化、评估次数、图元数和矩形控件数。是否达到目标应以实际拟合报告为准，与其他工具的质量比较需用同一输入实测。

`regions` 使用 `[[left,top,right,bottom],...]`，限制新增或调整图元的范围。用 `--initial PREVIOUS/state.json` 在已有图元上继续优化，可明确调整预算、区域或配置。`--resume` 要求输入和配置摘要与检查点一致。每次只能选择一种方式，输出必须写入新目录。超限或失败时不提交结果。

分层清单示例为 `{"schema":1,"layers":[{"name":"base","source":"base.png"},{"name":"detail","source":"detail.png"}]}`。列表顺序决定绘制顺序。图片路径相对于清单所在目录，且不能越出该目录。各层共用参数和锚点，分别记录预算、误差和检查点。

每层输出 `primitives.json`、`preview.png`、`asset.json` 和 `data.lua`，顶层输出 `catalog.json`、`state.json` 和摘要清单。Lua 沿用矩形数据格式，可按 [点阵帧动画](animation.md#点阵帧) 接入调用方的控件模板。工具先把拟合曲线栅格化，再将结果无损合并为矩形。预览与矩形数据一致，原图的拟合误差和宿主的矢量能力需另行判断。

Schema 2 的 `refinement` 报告标出拟合丢失的前景像素数、透明区域外溢像素数和误差最高的五块区域。先看 `preview.png`，再按 `worst_regions[].box` 选择要细化的区域。把该框写入 `regions`，用上一次的 `state.json` 作为 `initial` 另存。框坐标仍是源图像素。

## 生成可挂载的 Lua 和软件预览

用当前关卡已有的客户端容器和可着色的白色实心图片模板。在 schema 2 的拟合配置中补入 `mount`。关卡路径相对该配置文件，`sha256` 来自工程检查，`template` 和 `control` 用准确名称或整数标识。

```json
{"mount":{"gil":"level.gil","sha256":"工程检查返回的关卡摘要","template":"MarkerRect","control":"CheckpointMarker","width":144,"height":144}}
```

工具从 GIL 回读实际图片模板索引和容器，遇到同名目标或无法回读的关联时请求准确标识。宽高是显示框的设计单位，图元等比居中。分层输入使用同尺寸画布，按由底到顶的顺序装入一份 Lua。已有独立拟合流程仍可传入 `mount: {template_index, width, height}`。

`asset_fit` 或 CLI `assets fit` 产出 `mounted.lua`、`beyond.json` 和 `beyond-project.json`。绑定 GIL 时，把拟合输出的 `catalog.json` 和 Lua 交给 [GIL 挂载计划](../gil/native-authoring.md#将生成的-lua-挂到现有关卡)，审阅后另存新关卡。需要预览时，传拟合结果的 `beyond.json` 路径及摘要，调用 MCP `simulate` 并设 `preview=true`。CLI 可用 `simulate preview FIT_OUT/beyond.json --out NEW_DIRECTORY`。

Beyond 在软件布局中声明同索引的矩形图片模板，核对摘要后执行生成的 Lua。用 `preview.png`、`render.json` 和 `external-simulation.json` 核对控件、画面和日志。回读 GIL 以核对原生模板引用和挂载，实际贴图与画面需在编辑器和游戏中验证。修改 Lua 后，用新的源码摘要更新预览配置。 [检查点样例](../../samples/creator-demos/png/README.md#拟合并预览可挂载的-lua)

`catalog.json` 和交付清单汇总各层的误差、矩形数、`stop_reason` 与 `target_reached`。顶层 `quality` 列出未达目标的层。制作链在 `evidence.asset_fit_quality` 引用同一结论和各素材报告。预算内的近似结果可按检查点继续迭代。制作任务的拟合条目可声明 `"require_target": true`。任一图层未达到误差目标时，制作返回该层的实际误差与停止原因，并取消交付。

设为 `gia=true` 时，工具将同一份矩形数据按经过校准的 XY 平面结构封装。空图无法生成 GIA。产物保留来源、颜色、坐标和锚点，并通过导入器回读。编辑器和设备仍待验证。导入空工程后核对颜色、边缘、大小和锚点，再在目标设备检查控件预算、实际画面和帧率。

schema 2 的制作配置可在 `assets` 中添加 `{"name":"icon","kind":"fit","source":"icon.png","spec":"fit.json"}`，结果保存到 `fitted-assets/icon`。便携交付会收集分层清单和图片，重建按 [执行确认](../workflows/portable-delivery.md) 操作。旧 GE 资料和可用能力见 [兼容边界](animation.md)。

## Schema 2：交付预算与残差搜索

新任务使用 schema 2。旧检查点可用 `--initial` 将已有图元作为 schema 2 搜索的起点。 [旧配置的退出版本](../../docs/contributing/development.md#旧配置的退出版本)

```json
{"schema":2,"shapes":["rect","ellipse","circle","line"],"budget":80,"max_controls":1000,"max_total_controls":1500,"work":4000,"seed":7,"target_error":0.001,"gia":true}
```

`max_controls` 是每层的矩形上限，`max_total_controls` 是整批的总上限。省略总上限时，默认取图层数乘以每层上限。总预算平均分配，余数按图层输入顺序分配，各层均不得超过 `max_controls`。总预算小于图层数时拒绝运行，未用完的额度保留在原图层。预算由调用方按本次交付要求指定。

搜索75%按预乘RGBA残差加权采样，25%均匀采样；每三次候选安排一次局部优化，图元预算用尽后持续局部优化。轮换早期及后期图元，保持透明层序。只接受预算内误差降低，或误差相同但矩形更少的候选；不以模糊容差降低画质。透明轮廓与regions仍保护不可修改区域。初始结果超预算直接拒绝，导出前再次核对；未知旋转仍拒绝。

`primitives.json` 记录误差和成本的变化、图元数、矩形数，以及 `palette_size`、`lua_utf8_bytes`、`control_budget`、`stats` 和 `stop_reason`。`catalog.json` 记录各层配额、`total_controls` 和 `total_lua_utf8_bytes`。`target_reached=false` 表示误差未达目标，可按任务要求交付预算内的近似结果，并注明未达标。`work_done` 是候选尝试数，`stats` 分别统计候选渲染、成本计算、因超预算而拒绝的候选，以及局部调整尝试，不计初始化或从检查点恢复的重建。实际耗时只用于开发对照。

schema 2 检查点绑定算法、Pillow 版本、配置、输入和初始数据，并保存随机状态、轮换位置和历史。任何一项不匹配都会拒绝恢复。旧检查点可以用 schema 1 继续恢复，也可明确指定 `--initial`，将已有结果作为新算法的起点。用 `--initial` 启动的任务可直接用新检查点 `--resume`。旧检查点仅能恢复其中保存的初始来源。

Lua与GIA仍使用已校准矩形表达，preview是软件重建。原生曲线、任意旋转、编辑器和设备表现继续待验。

## 一致区域候选

schema 2新任务使用residual-budget-2：每四次尝试中的非局部候选，可沿采样点扩展轴对齐矩形，要求区域允许、Alpha一致且RGB各通道与采样点差不超过32；颜色取区域均值。它占用原work的一次尝试，仍经过完整误差、透明区域和矩形预算检查，不改变原图或添加量化后处理。只在允许rect时启用。

主要减少平坦半透明区域的小图元叠加碎片；不保证渐变等所有素材改善。旧residual-budget-1检查点继续使用原算法与随机序列，不自动迁移；显式initial可开始新算法。
