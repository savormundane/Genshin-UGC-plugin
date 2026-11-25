# 千星奇域开发插件

Miliastra Wonderland 是面向原神「千星奇域」创作者的非官方 AI 辅助开发插件。

在支持本地工具的 AI 客户端里安装插件，用中文对话查询资料、检查或生成工程文件，再按产物说明导入千星奇域编辑器或接入项目。

千星奇域是封闭平台。平台规则按目标版本查原文，原生文件操作限于已校准的样本范围。编译、文件回读、软件预览、编辑器导入和游戏内运行分别核对。 [来源判断](references/platform/knowledge-reliability.md) · [验证分层](docs/compatibility.md#验证分层)

[安装](#安装) · [快速开始](#快速开始) · [使用产物](#使用产物)

## 可以做什么

| 想做什么 | 需要提供什么 | 会得到什么 | 客户端需要的能力 |
| --- | --- | --- | --- |
| 查平台规则、节点或 Lua API | 问题，涉及版本差异时附目标版本 | 中文解释、参数和资料依据 | 本地 MCP 查询 |
| 查看已有工程 | 导出的 `.gil` 文件、想找的对象 | 对象位置、已识别的引用和问题 | 本地 MCP 访问已授权工程 |
| 修改已有工程 | 基底文件、具体修改要求 | 另存的文件、修改摘要和差异 | 已支持的局部修改可通过本地 MCP 规划、应用和比较 |
| 制作界面或节点逻辑 | 需求、已有代码或工程（如有） | Lua 代码或节点图文件，以及相应检查结果 | 本地 MCP 可检查源码。编译节点图或组装交付可用终端命令，或通过 MCP 执行已有制作配置 |
| 转换单张 PNG | 工程目录中的 PNG 和控件预算 | 候选预览和控件数，选定后生成图元数据和 Lua 文件 | 本地 MCP 的 `asset_preview` 和 `asset_generate` |
| 拟合图片并预览挂载效果 | 图片或分层清单、控件预算、挂载配置 | 拟合报告、可挂载 Lua 和 Beyond 软件预览 | 本地 MCP 的 `asset_fit` 和 `simulate` |
| 制作静态布景 | 对应版本的 GIL/GIA 样本、模型和摆放要求 | 布景草案、可回读的 `scene.gia` | 本地 MCP 的 `scene_catalogue`、`scene_preview` 和 `scene_build` |

批量预算和自定网格可按任务选择终端命令或已有制作配置。 [素材任务与客户端能力](references/assets/image-to-primitives.md#素材任务与客户端能力)

查资料、试算素材和局部修改可直接走对应工具。需要把节点图、Lua 或素材装到同一份关卡，或者按同一配置重建交付时，用 [`produce` 制作流程](references/workflows/produce.md)。

## 安装

插件支持 **Agent Plugins、Claude、DSH** 三种协议。 [协议与客户端](docs/compatibility.md#安装协议与客户端)

| 客户端 | 市场安装 |
| --- | --- |
| ChatGPT/Codex | 打开「插件」，从工作区市场安装 **Miliastra Wonderland**。 [导入工作区市场](docs/installation.md#chatgptcodex) |
| Claude | 在「自定义 → 插件 → 添加市场」输入 `savormundane/miliastra-wonderland-plugin`，然后安装 **Miliastra Wonderland**。 |
| DeepSeek Harness | npm 包发布后，在「插件 → 添加插件」输入 `miliastra-wonderland`。 |
| Agent Plugins | 在支持 GitHub 市场的客户端添加 `savormundane/miliastra-wonderland-plugin`，安装 `miliastra-wonderland`。 |

**本地安装**。下一版将在 [GitHub Releases](https://github.com/savormundane/miliastra-wonderland-plugin/releases) 提供 Agent Plugins ZIP。客户端支持时可直接上传，或解压后导入插件目录。终端用户可查看 [CLI 安装](docs/installation.md#cli-安装)。

完整本地工具面向 Windows x64，需要 Node.js 22+（DSH 用 24.9+）以及具备依赖的 CPython 3.11–3.14 或 PATH 上的 `uv`。 [运行要求](docs/compatibility.md#运行要求) · [安装自检](docs/installation.md#安装自检)

**当前版本 `1.1.0`**。使用发行包时，按该版本的安装说明和教程操作。 [下载源码](https://github.com/savormundane/miliastra-wonderland-plugin/releases/tag/v1.1.0) · [版本记录](CHANGELOG.md)

## 快速开始

### 查询第一个节点

启用插件后，在能运行本地工具的会话里发送下面的请求。查询节点无需准备工程文件。 [首次工具验证](docs/installation.md#首次工具验证)

> 请使用千星奇域插件查询服务端「创建实体」节点，列出输入和输出端口，用中文解释它的用途，并注明资料依据。版本依据不明确的部分请直接说明。

本机实际调用 `nodes_lookup`，在服务端节点库中匹配到 1 条结果。

- 输入为「流程入」「目标GUID（GUID）」和「单位标签索引列表（整数列表）」，输出只有「流程出」。
- 用途是按 GUID 创建已预先布设在场景里的实体。`source` 指向随包编译器定义。`port_evidence` 对应 7.1 版官方文档的两项值输入。 [官方《执行节点》](references/platform/official/节点介绍/执行节点__mhw66orrrfkm.md#2-创建实体)

看到实际工具调用和上述端口结果，表示本地工具已连通。接着可以按任务跟做 [五个中文教程](samples/creator-demos/README.md)。如果助手无法调用插件，先[运行安装自检](docs/installation.md#安装自检)。

### 只读查看已有的关卡

在客户端打开包含关卡文件的工程目录，把下面的示例路径换成你的 `.gil` 文件路径。

> 请用千星奇域插件只读检查 `C:\我的关卡\练习 01.gil`，列出主要对象，找到名称含「出生点」的对象，并列出已识别的引用关系。有多个匹配时先列出候选。

确认返回的文件路径与所选关卡一致。若工具找不到工程目录，按[工程目录设置](docs/runtime-environment.md#连接-mcp-或切换工程)绑定 `project_root` 后重试。只读查看可以省略输出目录。

## 使用产物

有文件输出时，从助手回复里的路径或文件链接打开。使用插件默认位置时，文件按工程保存在本机插件数据目录。需要固定保存位置时，可[绑定独立输出目录](docs/runtime-environment.md#连接-mcp-或切换工程)。

- **关卡和节点图**。使用另存的 GIL 副本，按交付说明在编辑器中导入并核对改动。GIA 节点图或资源按相应类型导入，再挂载到目标对象。 [关卡复核](references/gil/native-changes.md#人工再导出核对)
- **Lua 和图元素材**。按交付说明将 Lua 接到目标客户端控件。可在具备素材工具的本地 MCP 客户端中试算 PNG，选定方案后拿到 `asset.json`、`data.lua` 和最终预览。 [PNG 试算与生成](docs/mcp.md#单张-png-试算与生成) · [Lua 接入](references/editor/lua/client-assembly.md)

回复还会说明生成了什么、改了哪里，以及本次完成了哪些检查。打开编辑器导入、到游戏里运行时，分别核对对应结果。 [验证分层](docs/compatibility.md#验证分层)

## Skills

| Skill | 适用任务 |
| --- | --- |
| [Miliastra Editor](skills/miliastra-editor/SKILL.md) | 查看关卡对象、对照 3D 布设并配置原生界面，查询 API、编写和检查 [Client Lua](skills/miliastra-editor/SKILL.md#client-lua)。 |
| [Miliastra Graph Code](skills/miliastra-graph-code/SKILL.md) | 确认节点签名，编写并检查节点图。 |
| [Miliastra GIL](skills/miliastra-gil/SKILL.md) | 审阅局部修改计划，另存 GIL 并核对差异。 |
| [Miliastra Assets](skills/miliastra-assets/SKILL.md) | 将 PNG 转成图元，比较候选方案的效果和控件预算。 |

## 参与项目

- **报告问题**。请附客户端、插件版本、预期结果和报错，可附公开的最小复现。[反馈问题](https://github.com/savormundane/miliastra-wonderland-plugin/issues/new/choose) · [安全问题报告](SECURITY.md)
- **交流与建议**。欢迎分享制作方法、交流插件用法，或讨论下一步值得补齐的能力。[GitHub Discussions](https://github.com/savormundane/miliastra-wonderland-plugin/discussions)
- **参与贡献**。欢迎修正文档、补充有版本依据的平台资料、提交可复现样本和修复代码。[贡献指南](CONTRIBUTING.md)

## 更多文档

- **技术参考**。查阅平台版本规则、节点签名、Lua API、原生文件格式与制作流程。[技术参考索引](references/README.md) · [术语表](docs/glossary.md)
- **终端工具**。在终端直接编译节点图、检查 GIL 或复现工具报错。[在终端运行工具](docs/runtime-environment.md#只用-cli)
- **插件开发**。查看源码入口、按改动选择本地检查。[开发者文档](docs/contributing/README.md)

## 致谢

- Ayaya 为节点图工具链提供了基础，Beyond 提供离线模拟和界面预览。[Ayaya](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor) · [Beyond](https://github.com/1475505/miliastra-beyond-simulator)
- 感谢 Miliastra-knowledge 整理平台资料。[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)
- 感谢 GEIMG 的图元处理资料。[GEIMG Wiki](https://docs.lumkfs.cn/GEIMG-WIKI/README/) 
- 感谢所有社区公开分享的千星奇域文件格式研究。[第三方声明](THIRD_PARTY_NOTICES.md)

## 许可证

本项目自有代码采用 GPL-3.0-only。随包的第三方代码、资料和素材保留各自的权利与许可。

[许可证](LICENSE) · [来源清单](PUBLIC_SOURCES.json)
