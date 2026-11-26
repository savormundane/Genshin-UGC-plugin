# 技术领域与共享能力

| Skill | 工作对象 |
| --- | --- |
| [Miliastra Editor](../../skills/miliastra-editor/SKILL.md) | 工程对象、平台规则、界面和客户端 Lua |
| [Miliastra Graph Code](../../skills/miliastra-graph-code/SKILL.md) | 客户端／服务端节点图、复合节点、端口和编译 |
| [Miliastra GIL](../../skills/miliastra-gil/SKILL.md) | 容器、修改计划、挂载、保护字段和写后读回校验 |
| [Miliastra Assets](../../skills/miliastra-assets/SKILL.md) | 图像、图元、转换、预算和预览 |

[任务索引](../README.md)按工作内容列出直接入口。工具索引以 [capability_index.py](../../scripts/capability_index.py) 和 [capabilities.py](../../scripts/capabilities.py) 为准。`plan.entrypoints` 与 CLI `capabilities.architecture.task_entrypoints` 使用同一索引，MCP `capabilities` 列出会话能用的工具。

`plan --kind diagnosis --target-domain editor|graph|client|gil|assets` 可给出已知诊断对象的工具入口。位置未明时先运行共享的 [diagnose](project-diagnosis.md)，随后按结果选择领域。读取 `diagnosis.entrypoint`、`diagnosis.target_domain` 时注意旧计划 schema 2 的顶层 `primary` 在对象未定时仍保留历史值。旧工作流所有者见源码的 `LEGACY_OWNERS`。

需要从一个领域继续另一个领域时，沿用[实际工程对象和输入](capability-contract.md)。项目玩法、协议编号、数据和文案留在所属工程。
