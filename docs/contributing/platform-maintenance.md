# 平台资料与合同维护

Skill 维护任务入口与领域约束，平台事实以[原文和校准记录](../../references/platform/knowledge-reliability.md)为依据。

## 来源更新

分别记录插件版本、目标平台版本和模式、资料来源版本、合同 schema 及后端版本。文档版本未知时保持空值。获取时间和官方更新时间分别记录。沿用旧版资料时，保留 `requested_version`、`source_version` 和 `inherited`。

1. 用已配置的 Python 运行 `qianxing.py knowledge snapshot`，将输出的 JSON 保存到新的开发证据文件。该命令只输出数据。
2. 按需取得新资料，保存到独立位置后对照原文。平台正文用 `docs diff --from VERSION --to VERSION` 对比。流程不会自动联网抓取资料。
3. 审查签名、权限、生命周期、适用模式和行为约束。文档冲突同时保留依据；新文档不自动覆盖已确认的不同运行环境。
4. 确认依据后，更新原文、来源目录和摘要。路径或链接变化与内容变化分别记录。核对原文后再更新摘要。
5. 再保存一份快照，用 `knowledge diff BEFORE.json AFTER.json` 列出来源和 API 合同的变化、受影响的功能及建议运行的检查。差异报告供审查使用，测试需另行运行。API 删除或变更时，应核对兼容性。宿主版本的兼容情况仍需验证。
6. 按建议和实际源码依赖执行定向回归。无法判断语义影响时扩大检查范围；普通说明改动只核对结构与链接。

## 合同与迁移

保留现有配置与已交付协议的语义。变更字段含义或必填项时升级 schema 或要求显式选择平台。未知 schema 返回诊断，迁移结果另存并附差异。 [配置退出版本](development.md#旧配置的退出版本)

`plan` 保留已有输入参数。`routing_schema=2` 标出主入口，`support` 列出按需参与的能力。历史工作流的 `owner` 通过登记解析，已有配置可继续读取。

原生文件或游戏存档迁移需要与目标版本匹配的字段合同。 [原生计划](../../references/gil/native-changes.md) · [存档迁移](../../references/workflows/storage-migration.md)
