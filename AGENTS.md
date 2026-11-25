# Miliastra Wonderland 开发约定

- 仓库根目录是 Codex、Claude、DeepSeek Harness 和通用 Agent Plugins 共用的插件入口。安装 ID 使用 `miliastra-wonderland`。四个 Skill 使用 `miliastra-editor`、`miliastra-graph-code`、`miliastra-gil` 和 `miliastra-assets`。面向创作者的入口见 [README](README.md)。
- Editor 管工程语义与 Client Lua，Graph Code 管节点编写和编译，GIL 管容器与回读，Assets 管原生模型和图元。CLI 与 MCP 复用相同实现。历史修改计划、具名绑定及交付清单按原合同读取。
- 插件维护任务入口、平台规则、工程对象语义、交付合同和回归样本。上游代码按编译、渲染或基础库的职责接入，调用集中在所属实现边界。维护修改需保留上游基线、许可和可复验的源码摘要。
- 原生写入须绑定输入摘要和唯一对象，输出到新路径并核对保护范围。平台规则、离线模型、编辑器和实机结果分别记录。代码或指南涉及新平台事实时，核对可用资料及具体版本。
- 千星奇域的官方正文只支持其中明确记载的规则。逆向结果以原生样本的摘要、版本或可识别的容器家族、对象和测试范围为限。编译器签名、推导类型和软件预览分别注明来源。证据缺失时停在只读检查并说明需要的资料或最小样本。项目自有的业务协议按项目约定设计。
- 交付的模型证据须标出实际输入摘要和映射。编辑器导入及游戏内观察须绑定本轮产物和实际环境。公开来源、可访问性、再分发许可分别记录。
- 提交前按影响选取[本地检查](docs/contributing/development.md)。保留官方文档、第三方许可和已登记来源。公开树使用可移植的相对路径，测试样本使用可公开的最小输入。
- 发行内容从明确的 Git 提交准备。[维护指南](docs/contributing/maintenance.md)记录各安装入口和源码 Release 的定版检查。普通开发用本地检查。
