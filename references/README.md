# 技术参考索引

[安装指南](../docs/installation.md) · [工具导航](../scripts/README.md)

## 从任务进入

| 当前任务 | 首先阅读 |
| --- | --- |
| 判断任务由谁处理 | [五领域与共享能力](skill-map.md) |
| 查已有工程、组件或平台版本 | 下方“工程 / Editor” |
| 写节点、Lua、改文件或做素材 | 下方对应领域 |
| 制作或整合多个产物 | [制作总流程](production-workflow.md)，再按需读取当前 [produce 配置](production-v2.md) |
| 定位已知故障 | [排障流程](debugging-workflow.md)，按失败对象进入专项 |

## 工程 / Editor

- [平台版本与配置检查](platform-profiles.md)
- [平台资源目录](resource-catalogue.md)
- [工程对象与引用索引](project-index.md)
- [原生 3D 场景](native-scene.md)
- [三维实体读取和变换](native-entity-transform.md)
- [原生玩法制作](native-gameplay.md)
- [编辑器配置](editor-configuration.md)
- [原生 ID 分配登记](id-registry.md)
- [原生自定义变量索引](native-variables.md)
- [原生 UI 矩形布局](native-ui-layout.md)

## Graph Code / 节点图

- [节点设计和连接](graph-authoring.md)
- [严格构建与回读](node-graph-workflow.md)
- [Graph Code 语法](graph-code-syntax.md)
- [节点图变量声明、默认值与访问](native-graph-variables.md)
- [原生数据流与跨次存档排障](native-dataflow-validation.md)
- [底层工具与 HTML 分支](ayaya-offline-toolchain.md)
- [图验证常见修复](../skills/qianxing-graph-code/references/validation-fixes.md)
- [GraphModel 导出](workflows/qianxing-gil-assembly-pipeline/references/graph-model-export.md)

## Client Lua / 客户端脚本

- [完整客户端 API](../skills/client-controls-lua/references/client-controls-api.md)
- [知识可信度与 API 查询](knowledge-reliability.md)
- [Lua 源码装配](client-assembly.md)
- [最终 Lua 检查](client-check.md)
- [客户端 API 检查](client-api-check.md)
- [UI 运行支持](runtime-ui.md)
- [离线 Lua 模型、自检与日志](client-simulation.md)
- [客户端综合指南](../skills/client-controls-lua/references/integrated-guide.md)

## GIL / 原生文件

- [参数化生成、GUID 与脚本挂载](native-authoring.md)
- [容器检查与精确 Lua 替换](gil-tooling.md)
- [原生结构维护](native-maintenance.md)
- [原生差异与修改计划](native-changes.md)
- [二进制诊断](../skills/qianxing-gil/references/gil-format-diagnostics.md)
- [参数化生成入口](../skills/qianxing-gil/references/template-generation.md)
- [GIL 组装 CLI](workflows/qianxing-gil-assembly-pipeline/references/cli-reference.md)

## Assets / 素材与动画数据

- [统一素材核心](asset-generation.md)
- [通用拟合与分层续算](asset-fit.md)
- [素材检查与差异](asset-inspection.md)
- [原生 GIA 素材导入](native-assets.md)
- [素材按需加载与容量缓存](runtime-assets.md)
- [富文本点阵和布局清点](rich-text-assets.md)
- [点阵播放与控件池](pixel-runtime.md)
- [点阵像素指南](pixel-import-guide.md)
- [高级拟合兼容](ge-asset-compatibility.md)
- [单张图片到图元](../skills/qianxing-assets/references/workflow.md)
- [分层素材接入](../skills/qianxing-assets/references/l2d-workflow.md)

动画的素材制作归 Assets，播放、输入与生命周期归 Client Lua；组合方法见[动画工作流](workflows/qianxing-animation/README.md)。

## 共享能力：协议、存档与运行模型

- [复杂类型协议](protocol-v2.md)
- [多人会话与恢复](multiplayer-sessions.md)
- [存储与成就生成](storage-authoring.md)
- [显式存档迁移](storage-migration.md)
- [原生计时器模型](native-timers.md)
- [原生创建与移除生命周期模型](native-lifecycle.md)
- [客户端与原生图联合模型](joint-simulation.md)
- [算法与观察实验](algorithms-experiments.md)
- [可选外部模拟器后端](beyond-backend.md)
- [信号写回](workflows/qianxing-gil-assembly-pipeline/references/signal-writeback.md)
- [信号 spec 格式](workflows/qianxing-gil-assembly-pipeline/references/spec-json-format.md)
- [中性协议接入示例](workflows/qianxing-multiplayer/references/implementation-template.md)

## 共享流程：制作与交付

完整制作统一从[制作总流程](production-workflow.md)进入。以下页面各管一个层次，不是必须依次完成的多套流程。

| 层次 | 阅读时机 |
| --- | --- |
| [一句话需求编排](one-sentence-workflow.md)、[主动实现与缺项处理](implementation-policy.md) | 把创作意图落实成设计与可执行任务时。 |
| [阶段式实施](staged-production.md)、[跨能力输入输出合同](capability-contract.md) | 任务较复杂，需要协调多个领域时。 |
| [当前 produce 配置与交付](production-v2.md) | 需要用 schema 2 整合源码、文件和资源时；这是当前制作配置入口。 |
| [统一 produce 及运行支持](production-core.md) | 查基础制作核心及 schema 1 兼容配置时；不另开一套制作流程。 |
| [可迁移制作与重建](portable-delivery.md) | 明确需要异地重建或可迁移交付时。 |
| [操作反馈与游玩检查](playability-workflow.md) | 设计或排查实际操作体验时。 |

## 来源、环境与排障

- [官方文档](official-index.md)
- [三个核心依据与冲突处理](sources-and-conflicts.md)
- [平台更新、兼容与恢复](architecture-maintenance.md)
- [独立运行环境](../docs/runtime-environment.md)
- [本地 MCP 服务](local-mcp.md)
- [工程只读诊断](project-diagnosis.md)
- [结构化日志诊断](log-diagnostics.md)
- [证据等级与验收](validation.md)
- [能力与验证结果](validation-evidence.md)
- [可选制作案例与历史观察](production-experience.md)

平台资料的路径和摘要见[来源清单](../PUBLIC_SOURCES.json)。
