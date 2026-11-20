# 分层素材与拟 L2D

共享的 [L2D 资料目录](../../../references/l2d/README.md) 保留原资料、Python 附件和 Lua/HTML 模板。历史云端写入说明只供查阅。本工作流面向图元驱动的动画。

按任务取用：

- [输入检查](../../../references/l2d/01-前置-拆分.md)与[附件说明](../../../references/l2d/attachments/README.md)。
- [历史拟合资料](../../../references/l2d/02-拟合-从PNG到图元.md)与当前的 [assets fit 分层清单](../../../references/asset-fit.md)。
- [数据转换](../../../references/l2d/03-数据格式-图元与导出.md)、[游戏重建](../../../references/l2d/04-在游戏里重建.md)和 [API 速查](../../../references/l2d/07-API速查与验证状态.md)。
- [动作与骨骼](../../../references/l2d/05-动作与骨骼.md)、[Tween](../../../references/l2d/10-补间动画-Tween.md)和[父容器](../../../references/l2d/11-层级与骨骼-父容器.md)。
- [边缘与画质](../../../references/l2d/06-边缘与画质.md)、[踩坑清单](../../../references/l2d/08-踩坑清单.md)和[整体案例](../../../references/l2d/09-端到端SOP与检查表.md)。

先检查 Python 环境。当前插件不携带GE。附件通常需 Python 3.10+、Pillow、NumPy；Lua 验证还需 lupa、luaparser。不要声称这些依赖已随插件安装。

附件只读参考，当前拟合使用assets fit。`l2d_fit_batch.py` 会往 parts 目录写产物，传工作副本；superfit 默认多 worker、按历史编号分预算，必须先检查映射与总成本。l2d_build_showcase.py、l2d_build_anim.py 含案例画布、部件编号和骨骼语义，不能只换 --source 就保证任意角色可用。部分脚本有固定默认目录，先读源码/--help，显式设置输入输出。模板的占位符需构建脚本替换，模板本身不是完整 Lua。

验收：统一图层画布与层序，检查透明边缘、外溢、内部画质；还原缩放后的坐标与半径；展示动画预览，记录每帧写入量。实机确认资源 ID、容器、Update 回调、Tween 和父子继承行为；离线桩函数不能证明实际帧率。不要引用原案例的 3000/9941 个控件或帧率作为当前素材的测量结果。
