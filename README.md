# 千星奇域开发插件

Miliastra Wonderland 是面向原神「千星奇域」创作者的非官方 AI 插件。用中文对话查询资料、检查或制作工程文件，再将产物导入千星奇域编辑器或接入项目。

千星奇域是封闭平台。平台规则按目标版本查原文，原生文件操作限于已校准的样本范围。编译、文件回读、软件预览、编辑器导入和游戏内运行分别核对。 [来源判断](references/platform/knowledge-reliability.md) · [验证分层](docs/compatibility.md#验证分层)

[安装](#安装) · [快速开始](#快速开始) · [使用产物](#使用产物)

## 可以做什么

| Skill | 适用任务 |
| --- | --- |
| [Miliastra Editor](skills/miliastra-editor/SKILL.md) | 查平台规则和 Lua API，定位关卡对象、制作布景、检查 [Client Lua](skills/miliastra-editor/SKILL.md#client-lua)。 |
| [Miliastra Graph Code](skills/miliastra-graph-code/SKILL.md) | 查询节点端口，编写、检查和编译节点图。 |
| [Miliastra GIL](skills/miliastra-gil/SKILL.md) | 对导出的关卡文件（GIL）审阅修改计划，另存并回读核对。 |
| [Miliastra Assets](skills/miliastra-assets/SKILL.md) | 比较 PNG 转图元的预览和控件数，生成素材或拟合得到可挂载的 Lua。 |

查询、素材试算和局部修改可直接调工具。把节点图、Lua 或素材装到同一份关卡，或按配置重建交付时，使用 [`produce`](references/workflows/produce.md)。 [能力与工具入口](references/README.md)

修改已有工程时，可以从同一次对象查询继续编译 GIA、审阅改动并另存关卡。拟合素材也能直接绑定基底里的图片模板和容器，保留软件预览和实际挂载的核对结果。 [工程修改](references/gil/native-changes.md#审阅并另存已有工程)

## 安装

插件支持 **Agent Plugins、Claude、DSH** 三种协议。 [协议与客户端](docs/compatibility.md#安装协议与客户端)

| 客户端 | 市场安装 |
| --- | --- |
| ChatGPT/Codex | 打开「插件」，从工作区市场安装 **Miliastra Wonderland**。 [导入工作区市场](docs/installation.md#chatgptcodex) |
| Claude | 在「自定义 → 插件 → 添加市场」输入 `savormundane/miliastra-wonderland-plugin`，然后安装 **Miliastra Wonderland**。 |
| DeepSeek Harness | npm 包发布后，在「插件 → 添加插件」输入 `miliastra-wonderland`。 |
| Agent Plugins | 在支持 GitHub 市场的客户端添加 `savormundane/miliastra-wonderland-plugin`，安装 `miliastra-wonderland`。 |

**本地安装**。在 [GitHub Releases](https://github.com/savormundane/miliastra-wonderland-plugin/releases) 选择附有 Agent Plugins ZIP 的版本。只有源码附件时，可解压后导入插件目录。 [本地安装](docs/installation.md#本地安装) · [CLI 安装](docs/installation.md#cli-安装)

完整本地工具面向 Windows x64。 [运行要求](docs/compatibility.md#运行要求) · [安装自检](docs/installation.md#安装自检)

**当前版本 `1.2.0`**。 [发行与下载](https://github.com/savormundane/miliastra-wonderland-plugin/releases/tag/v1.2.0) · [版本记录](CHANGELOG.md)

## 快速开始

### 查询第一个节点

启用插件后，在支持本地 MCP 的会话里发送下面的请求。查询节点无需准备工程文件。 [首次工具验证](docs/installation.md#首次工具验证)

> 请使用千星奇域插件查询服务端「创建实体」节点，列出输入和输出端口，用中文解释它的用途，并注明资料依据。版本依据不明确的部分请直接说明。

本机实际调用 `nodes_lookup`，在服务端节点库中匹配到 1 条结果。

- 输入为「流程入」「目标GUID（GUID）」和「单位标签索引列表（整数列表）」，输出只有「流程出」。
- 用途是按 GUID 创建已预先布设在场景里的实体。`source` 指向随包编译器定义。`port_evidence` 对应 7.1 版官方文档的两项值输入。 [官方《执行节点》](references/platform/official/节点介绍/执行节点__mhw66orrrfkm.md#2-创建实体)

看到实际工具调用和上述端口结果，表示本地工具已连通。接下来可以[跟做中文教程](samples/creator-demos/README.md)。

### 只读查看已有的关卡

打开包含关卡的工程目录，给助手 `.gil` 路径和要找的对象。用公开样例跟做[只读检查](samples/creator-demos/README.md)，找不到输入时核对[工程绑定](docs/runtime-environment.md#连接-mcp-或切换工程)。

## 使用产物

有文件输出时，从助手回复里的路径或文件链接打开。使用插件默认位置时，文件按工程保存在本机插件数据目录。需要固定保存位置时，可[绑定独立输出目录](docs/runtime-environment.md#连接-mcp-或切换工程)。

- **关卡和节点图**。在编辑器中导入另存的 GIL 副本并核对改动。节点图或资源（GIA）按相应类型导入，再挂载到目标对象。 [关卡复核](references/gil/native-changes.md#人工再导出核对)
- **Lua 和图元素材**。按交付说明将 Lua 接到目标客户端控件。 [Lua 接入](references/editor/lua/client-assembly.md) · [PNG 试算与生成](references/assets/image-to-primitives.md#单张-png-试算与生成)

## 参与项目

[反馈问题](https://github.com/savormundane/miliastra-wonderland-plugin/issues/new/choose) · [交流与建议](https://github.com/savormundane/miliastra-wonderland-plugin/discussions) · [参与贡献](CONTRIBUTING.md) · [安全问题报告](SECURITY.md)

## 更多文档

- **MCP**。查看本地工具签名、输入摘要和文件路径规则。[MCP 工具](docs/mcp.md)
- **终端工具**。在终端直接编译节点图、检查 GIL 或复现工具报错。[在终端运行工具](docs/runtime-environment.md#只用-cli)
- **插件开发**。查看源码入口、按改动选择本地检查。[本地开发与检查](docs/contributing/development.md)

## 致谢

- 感谢 **AyayaXiaowang** 及贡献者提供节点图编译和 GIA 导出的工具链基础。 [Ayaya_Miliastra_Editor](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor)
- 感谢 **1475505** 及贡献者提供 Beyond 的离线 Lua 模拟和界面渲染实现，并整理千星奇域资料镜像。规则原文来自米哈游「奇匠学院」。 [Beyond](https://github.com/1475505/miliastra-beyond-simulator) · [Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)
- 感谢 **没空放肆** 编写 GEIMG 的图元处理指南和拟 L2D 案例，并授权以 MIT 许可随插件分发对应资料。 [GEIMG Wiki](https://docs.lumkfs.cn/GEIMG-WIKI/) · [拟 L2D 案例](https://docs.lumkfs.cn/GEIMG-WIKI/EG-L2D/)
- 感谢 **8itlab** 及贡献者采集音效、特效的面板信息并分享场景样本。插件的资源图鉴和布景参考使用了这些记录。 [genshin-miliastra-mcp](https://github.com/8itlab/genshin-miliastra-mcp)
- 感谢 **Crazyfourrrrrrrrrrr** 分享静态 GIA 与坐标转换研究，以及 **Ayn1631** 分享白盒枢轴的做法，供插件的布景和预览参考。 [XingGou](https://github.com/Crazyfourrrrrrrrrrr/XingGou) · [Miliastra-Tools](https://github.com/Ayn1631/Miliastra-Tools)
- 感谢 **script-1024**、**luern0313** 及社区贡献者分享 GIL/GIA 文件格式与生成工具研究。 [genshin-miliastra-file-format](https://github.com/script-1024/genshin-miliastra-file-format) · [UGC-File-Generate-Utils](https://github.com/luern0313/UGC-File-Generate-Utils)

Lua 语法解析复用了 Oskar Schöldström 的 luaparse。随包代码、资料及依赖的完整来源和许可见[第三方声明](THIRD_PARTY_NOTICES.md)。

## 许可证

本项目自有代码采用 GPL-3.0-only。随包的第三方代码、资料和素材保留各自的权利与许可。

[许可证](LICENSE) · [来源清单](PUBLIC_SOURCES.json)
