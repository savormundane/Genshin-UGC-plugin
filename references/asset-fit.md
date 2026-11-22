# 通用图片拟合

`assets fit` 使用自有逐步搜索。输入单张图片或显式分层 JSON，每张图最多 262,144 像素。工具在解码前检查宽乘高，超限时报告文件名和尺寸并停止制作。不自动拆分骨骼或加载本地图片到游戏。

```text
python scripts/qianxing.py assets fit icon.png --spec fit.json --out NEW_DIRECTORY
python scripts/qianxing.py assets fit icon.png --spec fit.json --steps 500 --out PARTIAL
python scripts/qianxing.py assets fit icon.png --spec fit.json --resume PARTIAL/state.json --out CONTINUED
```

配置示例：

```json
{"schema":1,"shapes":["circle","ellipse","line","rect"],"budget":80,"max_controls":1000,"alpha_min":1,"work":4000,"seed":7,"target_error":0.001,"anchor":[0,0],"gia":true}
```

圆与椭圆轴对齐；线限水平或垂直一像素线。坐标为图像左上原点，box右／下端不包含；anchor为像素锚点。旋转、投影及未知配置拒绝。budget限制拟合图元数，max_controls限制转换后的矩形控件数。work为最多评估的候选数，steps仅控制当前运行的工作量，不改变全局预算。

目标为预乘RGBA归一化均方误差。固定输入、参数、种子与Pillow版本下，从粗到细提出候选，尝试已接受图元的局部调整，只接受降低误差的结果。禁止覆盖alpha低于阈值的像素；这会限制可用候选，不保证达到目标。报告给出误差下降序列、工作量、图元与矩形成本，不保证任意图片达到其他工具的拟合质量。

regions为`[[left,top,right,bottom],...]`，限制新增／调整范围。`--initial PREVIOUS/state.json`在已有图元上继续优化，可显式换预算、区域或配置；`--resume`只接受输入和配置摘要相同的检查点。两者不能同时使用。所有输出必须是新目录，超限或失败不提交。

分层输入：`{"schema":1,"layers":[{"name":"base","source":"base.png"},{"name":"detail","source":"detail.png"}]}`。顺序即绘制顺序，路径相对清单且不能越界。各层共用参数和锚点，独立预算、误差与检查点。

每层输出primitives.json、preview.png、asset.json、data.lua，顶层输出catalog.json、state.json及摘要清单。Lua复用矩形合同，通过[点阵运行支持](pixel-runtime.md)接入调用方的控件模板。曲线先重建为像素，再无损合并为矩形；预览与矩形数据一致，不等于原图无损或宿主矢量曲线。

`catalog.json` 和交付清单汇总各层的误差、矩形数、`stop_reason` 与 `target_reached`。顶层 `quality` 列出未达目标的层。制作链在 `evidence.asset_fit_quality` 引用同一结论和各素材报告。预算内的近似结果可按检查点继续迭代。

gia=true使用相同矩形数据与已校准XY平面封装；空图拒绝GIA输出。保留来源、颜色、坐标和锚点，并用导入器回读。编辑器与设备仍待验：空工程导入后核对颜色、边缘、大小和锚点，再在目标设备检查控件预算。软件PNG不代表实际视觉验收或FPS。

制作链schema 2可用assets项`{"name":"icon","kind":"fit","source":"icon.png","spec":"fit.json"}`，输出到fitted-assets/icon。portable收集分层清单及图片，重建遵守[执行确认](portable-delivery.md)。旧GE资料与未替代能力见[兼容边界](ge-asset-compatibility.md)。

## Schema 2：交付预算与残差搜索

显式使用schema 2启用新算法；schema 1保持旧搜索与检查点行为，不自动迁移。

```json
{"schema":2,"shapes":["rect","ellipse","circle","line"],"budget":80,"max_controls":1000,"max_total_controls":1500,"work":4000,"seed":7,"target_error":0.001,"gia":true}
```

max_controls是每层矩形上限；max_total_controls是批次总上限，省略时等于层数乘以每层上限。总预算平均分配，余数按输入层顺序分配，各层不超过max_controls；总预算小于层数拒绝。固定配额不跨层借用，未用额度不自动转移。预算是调用方的交付要求，不是官方硬限制。

搜索75%按预乘RGBA残差加权采样，25%均匀采样；每三次候选安排一次局部优化，图元预算用尽后持续局部优化。轮换早期及后期图元，保持透明层序。只接受预算内误差降低，或误差相同但矩形更少的候选；不以模糊容差降低画质。透明轮廓与regions仍保护不可修改区域。初始结果超预算直接拒绝，导出前再次核对；未知旋转仍拒绝。

primitives.json记录误差/成本历史、图元数、矩形数、palette_size、lua_utf8_bytes、control_budget、stats和stop_reason。catalog.json记录各层配额、total_controls、total_lua_utf8_bytes。target_reached=false意味着误差目标未达到，不冒充质量验收；仍可交付预算内近似结果。work_done是候选尝试数，stats分别记录实际候选渲染、成本计算、预算拒绝和局部尝试；不含初始化与检查点恢复重建。墙钟耗时仅用于开发对照，不混入确定性产物。

schema 2检查点绑定算法、Pillow版本、配置、输入与初始数据，保存随机状态、轮换位置和历史；不匹配拒绝。旧检查点通过schema 1继续恢复，或显式--initial作为新算法起点。--initial开始的任务可直接用新检查点--resume，不必再次提供initial。旧历史检查点若未保存初始来源，不能凭空恢复该来源。

Lua与GIA仍使用已校准矩形表达，preview是软件重建。原生曲线、任意旋转、编辑器和设备表现继续待验。

## V3.7.2 一致区域候选

schema 2新任务使用residual-budget-2：每四次尝试中的非局部候选，可沿采样点扩展轴对齐矩形，要求区域允许、Alpha一致且RGB各通道与采样点差不超过32；颜色取区域均值。它占用原work的一次尝试，仍经过完整误差、透明区域和矩形预算检查，不改变原图或添加量化后处理。只在允许rect时启用。

主要减少平坦半透明区域的小图元叠加碎片；不保证渐变等所有素材改善。旧residual-budget-1检查点继续使用原算法与随机序列，不自动迁移；显式initial可开始新算法。
