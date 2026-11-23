# 千星奇域制作流程

本页是多能力制作的统一入口。完整制作、复杂修改和多阶段排障由 qianxing-editor 协调，按需使用[阶段式制作](staged-production.md)组织需求、设计、最小闭环、实施和交付。单点查询和局部修改直接进入对应领域。

需要工具整合多个产物时，使用当前[produce schema 2 配置](production-v2.md)。[基础制作核心](production-core.md)保留基础说明和 schema 1 兼容用途；两者不是需要重复执行的流程。

制作前确认目标平台版本和模式、原生或 Lua 入口、已有基底及目标产物。多人同步、存档及自定义资源按玩法需要接入。

## 按当前任务进入

| 任务 | 工作流 |
| --- | --- |
| 职责与阶段交接 | [Skills 与共享能力](skill-map.md)、[能力合同](capability-contract.md) |
| 工程定义与接口 | [平台接口与工程合同](implementation-policy.md) |
| 事件、节点与严格编译 | [图设计](graph-authoring.md)、[节点图构建](node-graph-workflow.md) |
| 新基底、UI模板和Lua映射/挂载 | [参数化生成](native-authoring.md) |
| 素材、协议、动画、图与Lua整合 | [当前 produce 配置](production-v2.md) |
| 位图或参数图形 | [统一素材](asset-generation.md)、[富文本分支](rich-text-assets.md) |
| 帧和已有分层数据动作 | [点阵运行时](pixel-runtime.md)、[动画工作流](workflows/qianxing-animation/README.md) |
| 操作反馈、输入与目标设备 | [体验与游玩检查](playability-workflow.md) |
| Lua逻辑、自检与日志 | [客户端模型](client-simulation.md)、[调试](debugging-workflow.md) |
| 文件和宿主证据 | [验证等级](validation.md) |

所有阶段共享同一需求、权威状态、协议、标识和证据，避免分别猜测信号或模板ID。完整新玩法先打通进入→操作→规则推进→结果→重开；单人不自动增加网络、原生3D不由Lua界面原型代替。

已有项目读取当前基底并保护用户改动；新项目在已支持结构范围内参数化生成，不克隆完整游戏。HTML、素材、动画与高级拟合按需参与，不要求用户挑选框架。所有工具和资料见 [完整索引](README.md)。

## 按改动选择检查

保留所用工具要求的类型检查、输入摘要、输出保护与回读。额外检查围绕实际改动和已发现的问题选择：资料查询不触发完整制作，局部 Lua 修改不自动重建无关素材。原生文件另存前核对基底摘要和保护范围。

## 交付

交付源码、GIA/GIL、必要资源和可定位报告。静态、编译、回读、挂载、模型、编辑器和实机分别记录，未验收项明确标注。
