# 技术领域与共享能力

四个 Skill 按任务分工。运行 `qianxing.py capabilities`，从 `architecture` 查能力分工。`scripts/capability_index.py` 登记任务入口，`scripts/capabilities.py` 汇总工具和指南。检查会核对两者是否一致，执行结果以实际验证记录为准。

| Skill | 工作对象 |
| --- | --- |
| [Miliastra Editor](../../skills/miliastra-editor/SKILL.md) | 原生工程、平台规则、原生界面和 [Client Lua](../../skills/miliastra-editor/SKILL.md#client-lua) |
| [Miliastra Graph Code](../../skills/miliastra-graph-code/SKILL.md) | 客户端／服务端图、复合节点、类型和连线 |
| [Miliastra GIL](../../skills/miliastra-gil/SKILL.md) | 容器、身份、挂载、保护字节和回读 |
| [Miliastra Assets](../../skills/miliastra-assets/SKILL.md) | 图像、图元、颜色、转换、成本与预览 |

[多人协议](protocol-v2.md)、[动画](../assets/animation.md)、[存储](storage-authoring.md)、[GIL 组装](../gil/native-authoring.md#将图信号和-lua-写入同一份-gil)、[项目数据目录](../editor/lua/client-assembly.md#项目生成的-lua-数据目录)和[工程诊断](project-diagnosis.md)可按实际任务组合。

使用 `plan --kind nodes|lua|gil|assets|editor` 选择直接领域；game、animation及--multiplayer旧参数保留，storage、protocol、diagnosis选择共享流程。`support` 列出可按任务选用的辅助 Skill。节点任务用 Miliastra Graph Code，动画运行用 Miliastra Editor 的 Client Lua。问题位置未明时先用 `diagnose`，再根据诊断对象选择工具。需要把多个相关产物交到同一份关卡时，使用 `produce`。

`plan.entrypoints` 与 `capabilities.architecture.task_entrypoints` 提供同一套 CLI 和 MCP 入口。查平台资料可直接使用内置查询。已有工程先按名称定位对象，随后按对象键核对关系并准备修改。交付多个关联产物时用 `produce`。

诊断对象已知时使用 `plan --kind diagnosis --target-domain editor|graph|client|gil|assets`。`--task-mode ui|assets|delivery` 也可提供已有工作流线索。新调用方读取 `diagnosis.entrypoint` 与 `diagnosis.target_domain`。对象未定时运行共享 `diagnose`，根据发现的输入再选领域。为保留 schema 2，顶层 `primary` 在对象未定时仍保留历史值。

新增节点、控件、组件规则通常只扩展现有资料、工具和验证。只有独立且稳定的平台工作对象无法归入现有入口时才考虑新Skill。工程玩法、协议编号和文案留在项目。
