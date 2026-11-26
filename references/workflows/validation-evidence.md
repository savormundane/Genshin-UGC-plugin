# 能力与验证结果

MCP `capabilities` 返回轻量的任务和工具索引。CLI 可查看详细的实现、来源路径、覆盖规则和证据状态。需要判断当前执行的是源码还是安装缓存时，用 `doctor` 核对 `plugin.path`、`plugin.version` 和 `plugin.capability_sha256`。

```text
python scripts/qianxing.py doctor --compare PLUGIN_ROOT
python scripts/qianxing.py capabilities
python scripts/qianxing.py capabilities --evidence CHECKS.json --tests-root TEST_DIRECTORY
```

`--platform` 和 `--mode` 选择资料配置，结果中的 `platform_version_verified` 仍为 `false`。`layers` 分开记录规则、生成、回读和模型等验证层。 `not_registered` 表示该能力层没有验证规则，`not_checked` 表示缺少足以判定该层的证据。

`--evidence` 接受开发验证入口生成的 schema 3、`scope: public` 报告。检查会比对实际源码和支撑文件、验证合同、环境及后端指纹、测试执行与所需用例。默认从插件源码旁的 `development/` 读取开发合同和专项用例，其他位置用 `--tests-root` 指定。缺项或摘要不一致时，从 `evidence_problems` 查原因；对应层仍为 `not_checked`。

日常贡献从[公开仓库的本地检查](../../docs/contributing/development.md)开始。旧报告按原适用范围保存；复查使用新报告并写明变更和覆盖。编辑器导入、实际游戏运行和玩家验收用[对应产物的验证记录](validation.md)判定。
