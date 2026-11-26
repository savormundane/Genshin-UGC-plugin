# 平台资料与合同维护

更新对象包括官方正文、项目使用的 API 整理资料、编译器规则和已有样本支持的格式。先确认版本、模式及证据类型。获取时间、原文更新时间、资料版本、插件版本和 schema 各自记录。资料版本未知时保留空值。 [来源判断](../../references/platform/knowledge-reliability.md)

## 更新资料并核对影响

1. 从仓库根运行 `python -B scripts/qianxing.py knowledge snapshot`，将 JSON 输出保存为新的开发记录。准备新资料时保留原文和出处。工具按随包资料工作。
2. 对照签名、权限、生命周期、适用模式与行为约束。已登记的版本可用 `python -B scripts/qianxing.py docs diff --from VERSION --to VERSION` 对比。冲突同时保留各自依据。
3. 核对内容后更新相应的绑定。版本资料查 [platform-sources.json](../../scripts/platform-sources.json)，知识源和 API 整理资料查 [knowledge-sources.json](../../scripts/knowledge-sources.json)，节点版本与端口校准查 [node-contracts.json](../../scripts/node-contracts.json)。沿用旧版正文时保留 `requested_version`、`source_version` 和 `inherited`。
4. 涉及分发内容的变化同步 [公开来源清单](../../PUBLIC_SOURCES.json) 和受影响的许可说明。正文变更、本地路径变更和链接变更分别核对摘录及校验值。
5. 再保存一份快照，运行 `python -B scripts/qianxing.py knowledge diff BEFORE.json AFTER.json`。核对来源变化、API 合同变化、推荐用例以及覆盖缺口。用对应版本和公开样例复测。

来源和实现影响涉及公开测试时，在 [公开验证清单](../../scripts/validation-contract.json) 登记实际存在的用例。从 `scripts/` 目录用 `python -B -m unittest MODULE.CLASS.METHOD` 运行推荐用例。仓库检查会核对引用的文件和方法。 [本地检查](development.md#按改动选检查)

## 兼容与迁移

既有配置、已交付的信号和存档按各自 schema 及项目规则读取。字段含义或必填项发生变化时，按目标版本设计显式选择或迁移，产物另存并附差异。 `plan` 继续识别当前任务名，历史工作流 `owner` 通过能力登记解析。 [能力登记](../../scripts/capability_index.py) · [旧配置的退出版本](development.md#旧配置的退出版本)

原生文件读写须以匹配的版本、容器和实际对象为依据。迁移后核对要求保护的字段、引用关系及失败回滚。 [原生修改计划](../../references/gil/native-changes.md) · [存档迁移](../../references/workflows/storage-migration.md)
