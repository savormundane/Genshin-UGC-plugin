# 通用图片拟合

`assets fit` 使用自有逐步搜索，不需要GE。输入图片或显式分层JSON，最大262144像素；不自动拆分骨骼或加载本地图片到游戏。

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

gia=true使用相同矩形数据与已校准XY平面封装；空图拒绝GIA输出。保留来源、颜色、坐标和锚点，并用导入器回读。编辑器与设备仍待验：空工程导入后核对颜色、边缘、大小和锚点，再在目标设备检查控件预算。软件PNG不代表实际视觉验收或FPS。

制作链schema 2可用assets项`{"name":"icon","kind":"fit","source":"icon.png","spec":"fit.json"}`，输出到fitted-assets/icon。portable收集分层清单及图片，重建遵守[执行确认](portable-delivery.md)。旧GE资料与未替代能力见[兼容边界](ge-asset-compatibility.md)。
