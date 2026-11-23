# Miliastra Wonderland 开发约定

- 仓库根目录是 Codex、Claude、DeepSeek Harness 和通用 Agent Plugins 共用的插件入口。保留现有安装 ID 和四个 Skill 的路径。面向创作者的入口见 [README](README.md)。
- Editor 管工程语义与 Client Lua，Graph Code 管节点编写和编译，GIL 管容器与回读，Assets 管原生模型和图元。CLI 与 MCP 复用相同实现。历史修改计划、具名绑定及交付清单按原合同读取。
- 原生写入须绑定输入摘要和唯一对象，输出到新路径并核对保护范围。平台规则、离线模型、编辑器和实机结果分别记录。代码或指南涉及新平台事实时，核对可用资料及具体版本。
- 提交前按影响选取[本地检查](docs/contributing/development.md)。保留官方文档、第三方许可和已登记来源。公开树使用可移植的相对路径，测试样本使用可公开的最小输入。
- 发行内容从明确的 Git 提交准备。[维护指南](docs/contributing/maintenance.md)记录各安装入口和源码 Release 的定版检查。普通开发用本地检查。
