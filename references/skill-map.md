# 技术领域与共享能力

四个核心入口按平台工作对象组织，能力清单由 `qianxing.py capabilities` 的 architecture 字段提供。源登记为 scripts/capability_index.py，工具和指南沿用 scripts/capabilities.py；两者在检查时核对，不将存在实现标为执行通过。

| Skill | 工作对象 |
| --- | --- |
| [Qianxing Editor](../skills/qianxing-editor/SKILL.md) | 原生工程、平台规则、原生界面和 [Client Lua](../skills/qianxing-editor/SKILL.md#client-lua) |
| [Qianxing Graph Code](../skills/qianxing-graph-code/SKILL.md) | 客户端／服务端图、复合节点、类型和连线 |
| [Qianxing GIL](../skills/qianxing-gil/SKILL.md) | 容器、身份、挂载、保护字节和回读 |
| [Qianxing Assets](../skills/qianxing-assets/SKILL.md) | 图像、图元、颜色、转换、成本与预览 |

[多人](workflows/qianxing-multiplayer/README.md)、[动画](workflows/qianxing-animation/README.md)、[存储](storage-authoring.md)、[组装](workflows/qianxing-gil-assembly-pipeline/README.md)、[目录合并](workflows/generated-lua-catalog-merge/README.md)、[诊断](workflows/qianxing-release-integrity-triage/README.md)是按需组合的流程或工具，不新增平台领域。

使用 `plan --kind nodes|lua|gil|assets|editor` 选择直接领域；game、animation及--multiplayer旧参数保留，storage、protocol、diagnosis选择共享流程。support仅列可选协作方，不要求全部加载、运行或读取所有官方资料。节点任务进入 Qianxing Graph Code，动画运行进入 Qianxing Editor 的 Client Lua；未知故障先diagnose，按发现对象进入领域。完整制作继续复用produce。

诊断对象已知时使用 `plan --kind diagnosis --target-domain editor|graph|client|gil|assets`。`--task-mode ui|assets|delivery` 也可提供已有工作流线索。新调用方读取 `diagnosis.entrypoint` 与 `diagnosis.target_domain`。对象未定时运行共享 `diagnose`，根据发现的输入再选领域。为保留 schema 2，顶层 `primary` 在对象未定时仍保留历史值。

旧版 schema 1 工作流照常读取，原记录不重写。旧 owner client-controls-lua 在 resolved_owners 中保留 client 技术域，并路由到 qianxing-editor。手动调用 Skill 时使用 qianxing-editor。更早的退役 Skill 名仍可解析到共享工作流。

新增节点、控件、组件规则通常只扩展现有资料、工具和验证。只有独立且稳定的平台工作对象无法归入现有入口时才考虑新Skill。工程玩法、协议编号和文案留在项目。
