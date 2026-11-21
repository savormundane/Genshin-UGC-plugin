# 参与贡献

感谢协助改进 Genshin-UGC。使用反馈、文档纠错、真实示例、平台资料更新和代码改动都很有帮助。当前方向见[路线图](ROADMAP.md)。

## 开始之前

- 先通过 [README](README.md) 和[使用文档](docs/README.md)了解项目；准备修改源码时再看[维护者文档](docs/contributing/README.md)。
- 先搜索已有 [Issue](https://github.com/savormundane/Genshin-UGC-plugin/issues) / [PR](https://github.com/savormundane/Genshin-UGC-plugin/pulls)，已有相同问题可以直接补充信息。涉及安全漏洞请先阅读 [SECURITY.md](SECURITY.md)。
- 本工具按千星奇域的 **工程检查、Graph Code、Client Lua、GIL、Assets** 能力域组织 Skill。协议、多人会话、存储与诊断属于可复用共享能力，不宜只因为某个具体游戏而新增 Skill。

## 报告问题与提出建议

通过 [Issue 表单](https://github.com/savormundane/Genshin-UGC-plugin/issues/new/choose)反馈即可，不需要先定位原因。

- **遇到问题：** 说明想完成什么、使用哪个客户端、在哪一步卡住，以及预期和实际结果。知道插件版本或有报错截图时一起提供；不确定的信息可以直说。
- **提出建议：** 说明具体使用场景和希望得到的结果。实现方案、平台依据和替代办法有的话再补充。
- **分享示例：** 说明输入、输出、使用方法和已经实际完成的检查，方便别人复用。

上传工程、GIL、日志或截图前，请清理令牌、账号信息和不想公开的内容。遇到与平台版本相关的问题时，再补充适用版本和资料来源。

## 提交变更

1. 从最新 `main` 建立短期分支；每个 PR 尽量聚焦一个问题。文案修正和明确的小问题可以直接提 PR，无需先开 Issue；影响核心能力或兼容性的方案先讨论范围。
2. 保持既有五领域路由清晰；共享逻辑放在共享层，不为单个历史项目创建通用入口。
3. 资料或 API 变更须注明来源、适用平台版本、证据类型与仍待验证的边界。优先参考 [知识可信度](references/knowledge-reliability.md) 和 [平台维护说明](references/architecture-maintenance.md)。
4. 更新受影响的文档，并按[改动范围选择检查](docs/contributing/development.md)。涉及文件生成时检查输出与回读；修正文档不需要重新安装整套插件或运行游戏。
5. 提交 PR，写明要解决的问题、修改后的行为和实际检查结果。静态检查、离线工具、编辑器导入和游戏运行分别记录，未完成的环节如实说明。

**不要求所有贡献者拥有游戏宿主环境。** 没有实测就如实标注“未检查”，而非声称通过。

## 提交建议

提交信息尽量说明实际修改，例如 `docs: clarify Graph Code verification`、`fix: preserve unknown GIL fields`。建议用英语短句但不强制 Conventional Commits。不要仅为追求提交次数而拆分一个完整修改。

## 版本与发布

日常修改可以先合入 `main`；有值得用户安装的功能或修复时，再由维护者发布版本。[版本记录](CHANGELOG.md)记录用户可感知的变化。Release 压缩包、版本标签、插件 manifest、安装命令及回退说明应相互一致。项目采用手动发布。

第一次参与 GitHub 项目，可以先看[日常维护与 GitHub](docs/contributing/github-workflow.md)；打包操作见[打包与发布](docs/contributing/maintenance.md)。

有关作者与第三方内容的现有记录见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
