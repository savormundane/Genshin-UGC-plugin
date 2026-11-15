# 技术领域与共享能力

五个核心入口按平台工作对象组织，能力清单由 `qianxing.py capabilities` 的 architecture 字段提供。源登记为 scripts/capability_index.py，工具和指南沿用 scripts/capabilities.py；两者在检查时核对，不将存在实现标为执行通过。

| 领域 | 入口 | 工作对象 |
| --- | --- | --- |
| Editor | [工程配置](../skills/qianxing-editor/SKILL.md) | 实体、模板、组件、资源关联、平台约束 |
| Graph Code | [节点程序](../skills/qianxing-graph-code/SKILL.md) | 客户端／服务端图、复合节点、类型和连线 |
| Client Lua | [客户端](../skills/client-controls-lua/SKILL.md) | Lua、生命周期、控件、输入、动画运行与装配 |
| GIL | [原生文件](../skills/qianxing-gil/SKILL.md) | 容器、身份、挂载、保护字节和回读 |
| Assets | [素材](../skills/qianxing-assets/SKILL.md) | 图像、图元、颜色、转换、成本与预览 |

[多人](workflows/qianxing-multiplayer/README.md)、[动画](workflows/qianxing-animation/README.md)、[存储](storage-authoring.md)、[组装](workflows/qianxing-gil-assembly-pipeline/README.md)、[目录合并](workflows/generated-lua-catalog-merge/README.md)、[诊断](workflows/qianxing-release-integrity-triage/README.md)是按需组合的流程或工具，不新增平台领域。

使用 `plan --kind nodes|lua|gil|assets|editor` 选择直接领域；game、animation及--multiplayer旧参数保留，storage、protocol、diagnosis选择共享流程。support仅列可选协作方，不要求全部加载、运行或读取所有官方资料。节点任务主入口为Graph Code；动画运行主入口为Client Lua；未知故障先diagnose，按发现对象进入领域。完整制作继续复用produce。

旧工作流schema 1的十个owner均可读取，结果附resolved_owners，原记录不重写；五个退役Skill名解析到共享工作流。显式调用旧Skill的用户改用对应核心入口；不假定宿主自动重定向。

新增节点、控件、组件规则通常只扩展现有资料、工具和验证。只有独立且稳定的平台工作对象无法归入五领域时才考虑新Skill。工程玩法、协议编号和文案留在项目。
