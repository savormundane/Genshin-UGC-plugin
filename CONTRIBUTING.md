# 参与贡献

感谢协助改进 Genshin-UGC。可从报错复现、文档纠错、平台版本差异、测试用例或代码改动开始。

## 开始之前

- 阅读 [README](README.md)、[项目结构](docs/contributing/architecture.md)与[支持状态](docs/compatibility.md)。
- 先搜索已有 Issue / PR，避免重复反馈。一般问题可创建 Issue；涉及安全漏洞请先阅读 [SECURITY.md](SECURITY.md)。
- 本工具按千星奇域的 **工程检查、Graph Code、Client Lua、GIL、Assets** 能力域组织 Skill。协议、多人会话、存储与诊断属于可复用共享能力，不宜只因为某个具体游戏而新增 Skill。

## 报告问题

请填写对应 Issue 模板，尽量提供：所用版本、操作系统、客户端及版本、目标千星奇域平台版本、精简复现步骤、预期与实际结果、可分享的错误日志。上传工程、GIL、日志或截图前，请清理令牌、账号信息和不想公开的内容。

说明问题发生在哪一层：静态分析、离线模拟、编辑器导入、游戏宿主运行，或人工游玩验收。**模拟器通过不等于真实游戏验证通过。**

## 提交变更

1. 从最新 `main` 建立短期分支；每个 PR 尽量聚焦一个问题。
2. 保持既有五领域路由清晰；共享逻辑放在共享层，不为单个历史项目创建通用入口。
3. 资料或 API 变更须注明来源、适用平台版本、证据类型与仍待验证的边界。优先参考 [知识可信度](references/knowledge-reliability.md) 和 [平台维护说明](references/architecture-maintenance.md)。
4. 更新相应文档与测试。运行 [本地检查](docs/contributing/development.md)；涉及文件生成时验证输出与回读，涉及游戏行为时记录实际宿主验证是否完成。
5. 提交 PR，写明变更目的、验证结果及未覆盖内容。

**不要求所有贡献者拥有游戏宿主环境。** 没有实测就如实标注“未检查”，而非声称通过。

## 提交建议

提交信息尽量说明实际修改，例如 `docs: clarify Graph Code verification`、`fix: preserve unknown GIL fields`。建议用英语短句但不强制 Conventional Commits。不要仅为追求提交次数而拆分一个完整修改。

## 版本与发布

发布由维护者控制；[版本记录](CHANGELOG.md)记录用户可感知的变化。Release 压缩包、版本标签、插件 manifest、安装命令及回退说明应相互一致。项目采用手动发布。具体步骤见[打包与发布](docs/contributing/maintenance.md)。

有关作者与第三方内容的现有记录见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
