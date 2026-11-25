# 图元动画接入

输入包括图像或现有图元数据、目标界面的坐标和尺寸，以及当前工程的控件预算。用 Assets 准备图元，要播放时接入 Client Lua，需要更新已有 GIL 时按 GIL 工具审阅挂载。普通按钮或窗口的 Tween 见 [Editor 的 Client Lua 入口](../../skills/miliastra-editor/SKILL.md#client-lua)。

## 点阵帧

已有调色板和矩形数据时，直接按 [点阵运行时](../editor/lua/pixel-runtime.md) 接入。按最大帧的矩形数建立固定控件池，分批初始化。切帧更新已有块并隐藏多余块，镜像围绕共同锚点。帧选择读取项目的玩法状态。需要从图片准备数据时，先 [把 PNG 转成图元](image-to-primitives.md)，点阵数据的来源和格式见 [点阵指南](pixel-import-guide.md)。

## 分层图元与拟L2D

1. **准备并拟合。** 按 [分层输入检查](geimg/l2d/01-前置-拆分.md) 核对各部件的遮挡、公共画布、坐标和共同锚点。用 [`assets fit`](asset-fit.md) 处理显式分层输入，查看每层误差、透明轮廓、总控件数和停止原因。需要时按检查点续算，细化 [透明边缘与画质](geimg/l2d/06-边缘与画质.md)。
2. **核对输出。** 对照预览检查图层顺序、外溢和内部细节，确认缩放后坐标和半径回到预期空间。交接时注明源图摘要、坐标、尺寸、层序、锚点、控件预算及所选方案。旧图元记录和导出结构见 [格式参考](geimg/l2d/03-数据格式-图元与导出.md)。
3. **接入 Lua 播放。** 按 [客户端 API](../platform/community/client-controls-api.md) 和 [客户端装配](../editor/lua/client-assembly.md) 确认脚本与模板，再装配数据和实现动作。父容器处理共同变换，局部形变可用连续位移场减轻接缝。呼吸、眨眼、视点和动作切换完成后应恢复至预期状态。补间字段以对应 API 为准，父级旋转、裁剪和透明度传递在目标宿主核对。格式与实现参考见 [游戏重建](geimg/l2d/04-在游戏里重建.md) · [动作与骨骼](geimg/l2d/05-动作与骨骼.md) · [Tween](geimg/l2d/10-补间动画-Tween.md) · [父容器](geimg/l2d/11-层级与骨骼-父容器.md)。
4. **检查并挂载。** 用 `client_check` 编译 Lua。对已有 GIL 的已识别挂载目标，先定位对象，再用 `native_plan` 审阅修改，确认后用 `native_apply` 另存。图元、Lua 和节点图需要绑定同一份最终关卡时，使用 [`produce` 制作流程](../workflows/produce.md)。
5. **交付与验收。** 检查静止、切帧、镜像、动作切换、关闭和重开。报告本轮控件总量、每帧 API 写入量以及实际执行的检查。复用控件、缓存未变属性、隐藏非当前视角并限制初始化批量。模板挂载、资源 ID、回调和设备性能按实际宿主验证。 [UI 运行支持](../editor/lua/runtime-ui.md) · [验收标准](../workflows/validation.md)

## GEIMG 资料与兼容

插件的现行拟合入口是 [`assets fit`](asset-fit.md)，覆盖透明轮廓、区域细化、续算、显式分层输入和矩形预览。矩形 Lua 与已校准 GIA 按各自工具接入。GEIMG 专有的拟合策略、GUI、账号与云端功能以 [原工具手册](geimg/geimg-manual.md) 和原工具为准。旧 `shapes`、`manifest`、`metrics` 及模板供格式对照和历史重建分析。[原拟 L2D 资料与附件](geimg/l2d/README.md)

使用历史附件时先复制到工作区，核对依赖与 `--help` 后显式指定输入和输出。部分脚本需要独立的 Python 3.10+、Pillow、NumPy，Lua 验证另需 `lupa` 和 `luaparser`。其中 `l2d_fit_batch.py`、`l2d_superfit.py` 依赖外部 GE，前者会写入 parts 目录，后者按原案例部件编号分预算并运行多个 worker。`l2d_build_showcase.py` 和 `l2d_build_anim.py` 含案例画布、部件和骨骼绑定。使用模板时由对应脚本替换占位符。按当前素材与工作副本核对实际预算，案例数值留作参考。 [附件说明](geimg/l2d/attachments/README.md) · [原工具拟合](geimg/l2d/02-拟合-从PNG到图元.md) · [API 速查](geimg/l2d/07-API速查与验证状态.md) · [原案例检查](geimg/l2d/09-端到端SOP与检查表.md)

## 共享参考的读取时机

播放问题按 [调试方法](../workflows/debugging-workflow.md) 定位；不同领域交接时跟随 [能力合同](../workflows/capability-contract.md) 和 [接口定义](../workflows/implementation-policy.md)。动作表现从项目权威状态读取。逻辑结算由项目规则推进，动画交付按 [游玩检查](../workflows/playability-workflow.md) 核对操作反馈。
