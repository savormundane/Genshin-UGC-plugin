# 平台资料与合同维护

维护对象包括平台资料索引、插件自有规则说明、Lua API 符号与已有样本支持的格式。先确认版本、模式及证据类型。资料版本未知时保留空值。 [来源判断](../../references/platform/knowledge-reliability.md)

## 更新资料并核对影响

1. 从仓库根运行 `python -B scripts/qianxing.py knowledge snapshot`，将 JSON 输出保存为开发记录。核对官方出处和原文校验值。授权待核的原文保留在发布目录外。
2. 对照签名、权限、生命周期、适用模式与行为约束。已登记的版本可用 `docs diff --from VERSION --to VERSION` 对比原文校验值。持有校验值匹配的副本时，可用 `--source-root` 比较原文。冲突保留各自依据。
3. 核对后更新版本索引、Lua API 文件校验值及节点端口绑定。沿用旧版依据时保留 `requested_version`、`source_version` 和 `inherited`。 [版本索引](../../scripts/platform-sources.json) · [知识源](../../scripts/knowledge-sources.json) · [节点端口](../../scripts/node-contracts.json)
4. 分发内容变化时同步来源清单及许可说明。将许可待核且不随包的原文记入 `excluded_unverified_files`，核对源码树和实际归档均未收录。 [公开来源清单](../../PUBLIC_SOURCES.json)
5. 再保存一份快照，运行 `python -B scripts/qianxing.py knowledge diff BEFORE.json AFTER.json`。核对来源变化、API 合同变化、推荐用例以及覆盖缺口。用对应版本和公开样例复测。

来源和实现影响涉及公开测试时，在 [公开验证清单](../../scripts/validation-contract.json) 登记实际存在的用例。从 `scripts/` 目录用 `python -B -m unittest MODULE.CLASS.METHOD` 运行推荐用例。仓库检查会核对引用的文件和方法。 [本地检查](development.md#按改动选检查)

## 兼容与迁移

既有配置、已交付的信号和存档按各自 schema 及项目规则读取。字段含义或必填项发生变化时，按目标版本设计显式选择或迁移，产物另存并附差异。 `plan` 继续识别当前任务名，历史工作流 `owner` 通过能力登记解析。 [能力登记](../../scripts/capability_index.py) · [旧配置的退出版本](development.md#旧配置的退出版本)

原生文件读写须以匹配的版本、容器和实际对象为依据。迁移后核对要求保护的字段、引用关系及失败回滚。 [原生修改计划](../../references/gil/native-changes.md) · [存档迁移](../../references/workflows/storage-migration.md)
