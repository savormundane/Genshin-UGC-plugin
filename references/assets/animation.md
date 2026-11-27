# 图元动画接入

准备图像或已有图元数据，并确定目标界面的坐标、尺寸和控件预算。用 Assets 生成图元，用 Client Lua 播放动画。更新已有 GIL 时，通过 GIL 工具审阅挂载计划。普通按钮和窗口的补间动画见 [Editor 的 Client Lua 入口](../../skills/miliastra-editor/SKILL.md#client-lua)。

## 点阵帧

1. **准备数据和模板。** 从 PNG 开始时先[试算并生成图元](image-to-primitives.md)。准备一个父容器以及可复用的矩形控件模板。使用已有数据时，核对每帧的矩形范围、调色板索引和模板。
2. **换算坐标。** 矩形记录 `{x, y, w, h, paletteIndex}` 的调色板索引从 1 开始。相对锚点的中心为 `x + w/2 - anchorX` 和 `anchorY - y - h/2`，两轴再乘显示比例。镜像只反转局部 X。碰撞范围由项目规则定义。
3. **复用控件。** 按矩形最多的一帧分配控件池，分批初始化。切帧时更新已有图块并隐藏多余项，移动角色时只移动父容器。装配完成后显示整组，禁用装饰图块的命中。分开处理可见与激活状态，分配失败时记录已有句柄和状态再恢复。 [UI 运行支持](../editor/lua/runtime-ui.md) · [客户端 API](../platform/client-api.md)
4. **核对实际表现。** 根据项目玩法状态选择素材已有动作，核对透明边缘、图层、触控行为、首次建池和切帧耗时。控件销毁级联与设备性能在目标游戏环境验证。图元与 Lua 需要和节点图一起交付时，使用 [`produce`](../workflows/produce.md)。

## 分层图元与拟L2D

1. **准备并拟合。** 按 [分层输入检查](geimg/l2d/01-前置-拆分.md) 核对各部件的遮挡、公共画布、坐标和共同锚点。用 [`assets fit`](asset-fit.md) 处理显式分层输入，查看每层误差、透明轮廓、总控件数和停止原因。需要时按检查点续算，细化 [透明边缘与画质](geimg/l2d/06-边缘与画质.md)。
2. **核对输出。** 对照预览检查图层顺序、透明区域外溢和内部细节，确认缩放后的坐标和半径符合目标界面的坐标系。交付时注明源图摘要、坐标、尺寸、图层顺序、锚点、控件预算和所选方案。旧图元记录和导出结构见 [格式参考](geimg/l2d/03-数据格式-图元与导出.md)。
3. **接入 Lua 播放。** 按 [客户端 API](../platform/client-api.md) 和 [客户端装配](../editor/lua/client-assembly.md) 确认脚本与模板，再装配数据和实现动作。父容器处理共同变换，局部形变可用连续位移场减轻接缝。呼吸、眨眼、视点和动作切换完成后应恢复至预期状态。补间字段以对应 API 为准，父级旋转、裁剪和透明度传递在目标宿主核对。格式与实现参考见 [游戏重建](geimg/l2d/04-在游戏里重建.md) · [动作与骨骼](geimg/l2d/05-动作与骨骼.md) · [Tween](geimg/l2d/10-补间动画-Tween.md) · [父容器](geimg/l2d/11-层级与骨骼-父容器.md)。
4. **检查并挂载。** 用 `client_check` 编译 Lua。对已有 GIL 的已识别挂载目标，先定位对象，再用 `native_plan` 审阅修改，确认后用 `native_apply` 另存。图元、Lua 和节点图需要绑定同一份最终关卡时，使用 [`produce` 制作流程](../workflows/produce.md)。
5. **交付与验收。** 检查静止、切帧、镜像、动作切换、关闭和重开。报告本轮控件总量、每帧 API 写入量以及实际执行的检查。复用控件、缓存未变属性、隐藏非当前视角并限制初始化批量。模板挂载、资源 ID、回调和设备性能按实际宿主验证。 [UI 运行支持](../editor/lua/runtime-ui.md) · [验收标准](../workflows/validation.md)

## GEIMG 资料与兼容

插件的现行拟合入口是 [`assets fit`](asset-fit.md)，覆盖透明轮廓、区域细化、续算、显式分层输入和矩形预览。矩形 Lua 与已校准 GIA 按各自工具接入。GEIMG 专有的拟合策略、GUI、账号与云端功能以 [原工具手册](geimg/geimg-manual.md) 和原工具为准。旧 `shapes`、`manifest`、`metrics` 及模板供格式对照和历史重建分析。[原拟 L2D 资料与附件](geimg/l2d/README.md)

需要复现原案例时，从工作副本使用附件，按附件说明配置依赖。部分旧拟合脚本需要另备 GE 可执行文件；预算、画布和骨骼来自各自案例。 [附件说明](geimg/l2d/attachments/README.md) · [原工具拟合](geimg/l2d/02-拟合-从PNG到图元.md) · [原案例检查](geimg/l2d/09-端到端SOP与检查表.md)

## 共享参考的读取时机

播放问题按 [调试方法](../workflows/debugging-workflow.md) 定位。需要跨领域协作时，按 [能力合同](../workflows/capability-contract.md) 和 [接口定义](../workflows/implementation-policy.md) 对接。动画根据项目的权威状态选择动作，结算由项目规则处理。交付时按 [游玩检查](../workflows/playability-workflow.md) 核对操作反馈。
