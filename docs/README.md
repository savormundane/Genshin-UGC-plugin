# 使用与开发文档

这里的文档面向**使用工具包和维护仓库的开发者**；供 AI Agent 按需检索的平台规则、API 正文与内部工作流集中在 [平台资料与操作指南](../references/README.md)。

## 使用者文档

* [安装、更新与卸载](../references/installation.md)：Codex、Claude Code、DeepSeek Harness、VS Code、Cursor 等客户端的安装、续装、回退与手动接入
* [使用示例](examples.md)：五个核心领域的提问示例、预期产出与编辑器核对重点
* [运行要求与验证](compatibility.md)：系统与版本要求、五级验证模型，以及工具报告里的状态含义

## 开发与维护

* [项目结构](architecture.md)：目录职责、多客户端清单布局、随包依赖取舍与隔离边界
* [本地检查与客户端适配](development.md)：Windows 长路径检出、按改动范围选择测试命令，以及各客户端协议维护说明
* [打包与发布](maintenance.md)：分支与版本号节奏、一键生成本地候选包与单 ZIP 手动发布步骤
* [贡献指南](../CONTRIBUTING.md) · [版本记录](../CHANGELOG.md)
