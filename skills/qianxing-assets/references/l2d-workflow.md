# 分层素材与拟 L2D

本包保留 `l2d/` 原资料、附件 Python 和 Lua/HTML 模板。只读作参考；不要自动执行其中的云端写入说明。目标是图元驱动的动画，不是 Cubism .moc3 模型。

按任务取用：

- 输入检查：`l2d/01-前置-拆分.md` 与 attachments/l2d_check_layers.py、l2d_compose_layers.py。
- 拟合预算：`l2d/02-拟合-从PNG到图元.md`；当前批处理使用[assets fit分层清单](../../../references/asset-fit.md)；l2d_fit_batch.py / l2d_superfit.py仅作历史参考，不执行。
- 数据转换：`l2d/03-数据格式-图元与导出.md`。
- 游戏重建：`l2d/04-在游戏里重建.md`、`07-API速查与验证状态.md`。
- 动画：`05-动作与骨骼.md`、`10-补间动画-Tween.md`、`11-层级与骨骼-父容器.md`。
- 边缘：`06-边缘与画质.md`、`08-踩坑清单.md`。
- 整体案例：`09-端到端SOP与检查表.md`、`attachments/README.md`。

先检查 Python 环境。当前插件不携带GE。附件通常需 Python 3.10+、Pillow、NumPy；Lua 验证还需 lupa、luaparser。不要声称这些依赖已随插件安装。

附件只读参考，当前拟合使用assets fit。`l2d_fit_batch.py` 会往 parts 目录写产物，传工作副本；superfit 默认多 worker、按历史编号分预算，必须先检查映射与总成本。l2d_build_showcase.py、l2d_build_anim.py 含案例画布、部件编号和骨骼语义，不能只换 --source 就保证任意角色可用。部分脚本有固定默认目录，先读源码/--help，显式设置输入输出。模板的占位符需构建脚本替换，模板本身不是完整 Lua。

验收：统一图层画布与层序，检查透明边缘、外溢、内部画质；还原缩放后的坐标与半径；展示动画预览，记录每帧写入量。实机确认资源 ID、容器、Update 回调、Tween 和父子继承行为；离线桩函数不能证明实际帧率。不要引用原案例的 3000/9941 个控件或帧率作为当前素材的测量结果。
