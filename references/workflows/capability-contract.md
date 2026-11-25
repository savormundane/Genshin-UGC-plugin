# 领域与工具合同

助手按 Skill 选择工具和需要读取的资料。`references/` 记录来源、约束和操作步骤。`scripts/` 实现解析、生成、检查和报告。工具可以独立于 `skills/` 目录运行。完整分工见[能力索引](skill-map.md)，更新与兼容见[长期维护](../../docs/contributing/platform-maintenance.md)。

| 边界 | 交接内容 |
| --- | --- |
| 原生工程 → Miliastra Graph Code / Client Lua | 对象身份、目标平台与模式、变量／信号合同、已有配置约束 |
| Miliastra Graph Code → Miliastra GIL | 图源码、编译输出、信号／结构体声明、目标挂载和审计范围 |
| Client Lua → Miliastra GIL | 装配后的 Lua、源码映射、明确的 API 绑定与脚本目标 |
| Miliastra Assets → Client Lua / Miliastra GIL | 来源摘要、坐标／颜色／图层、资源依赖、输出表示与预算 |
| 任一领域 → 诊断／交付 | 实际输入和工具、产物摘要、执行检查及未覆盖范围 |

读取并遵守工程已有的接口约定。新增业务协议按项目需要设计，由助手实现。平台对象身份和字段写入需有资料或样本依据。GIL 只写入工具已支持的对象关系，未知格式的映射须先核对样本。

制作完整关卡可用[制作链](produce.md)组合配置中的阶段。局部改动只执行与改动有关的检查。按[验收说明](validation.md)分别记录模型、编译回读、编辑器、游戏内运行和人工验收。
