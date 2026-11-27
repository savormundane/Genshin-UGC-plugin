# 千星奇域开发插件

Miliastra Wonderland 是面向原神「千星奇域」创作者的非官方 AI 插件。用中文对话查询资料、检查或制作工程文件，再将产物导入千星奇域编辑器或接入项目。

[安装](#安装) · [快速开始](#快速开始) · [更多文档](#更多文档)

## 可以做什么

| Skill | 适用任务 |
| --- | --- |
| [Miliastra Editor](skills/miliastra-editor/SKILL.md) | 查平台规则和 Lua API，定位关卡对象、制作布景、检查 [Client Lua](skills/miliastra-editor/SKILL.md#client-lua)。 |
| [Miliastra Graph Code](skills/miliastra-graph-code/SKILL.md) | 查询节点端口，编写、检查和编译节点图。 |
| [Miliastra GIL](skills/miliastra-gil/SKILL.md) | 对导出的关卡文件（GIL）审阅修改计划，另存并回读核对。 |
| [Miliastra Assets](skills/miliastra-assets/SKILL.md) | 比较 PNG 转图元的预览和控件数，生成素材或拟合得到可挂载的 Lua。 |

## 安装

插件支持 **Agent Plugins、Claude、DSH** 三种协议。 [协议与客户端](docs/compatibility.md#安装协议与客户端)

| 客户端 | 市场安装 |
| --- | --- |
| ChatGPT/Codex/Claude | 在「插件 → 添加市场」输入 `savormundane/miliastra-wonderland-plugin` |
| DeepSeek Harness | 在「插件 → 添加插件」输入 `dsh-miliastra-wonderland` |
| Agent Plugins | 在支持 GitHub 市场的客户端添加 `savormundane/miliastra-wonderland-plugin` |

**其他安装方式**。[本地安装](docs/installation.md#本地安装) · [CLI 安装](docs/installation.md#cli-安装)

完整本地工具面向 Windows x64。 [运行要求](docs/compatibility.md#运行要求) · [安装自检](docs/installation.md#安装自检)

**当前版本 `1.3.2`**。 [发行与下载](https://github.com/savormundane/miliastra-wonderland-plugin/releases/tag/v1.3.2) · [版本记录](CHANGELOG.md)

## 快速开始

启用插件后，在支持本地工具的会话里选一种方式开始。

### 作为知识库使用

直接问节点、Lua API 或平台规则，无需准备工程文件。

> 千星奇域的服务端「创建实体」节点怎么用？请列出输入和输出端口，注明适用版本和资料来源。

### 从零开始做原型

打开一个空目录作为工程，用一句话说清要做的玩法和玩家的操作，就可以开始做第一版。

> 帮我从零做一个单人挑战原型，点「开始挑战」后显示开始提示，直接生成可编辑的原型文件和软件预览。

### 审计、理解和修改已有项目

打开已有工程，提供关卡文件或源码，告诉助手你想弄清楚什么、准备改什么。

> 先只读检查这份 GIL，说明入口机关和节点图、脚本的关系，再为把入口机关的等待值改为 12 准备修改计划，等我确认后另存并核对差异。

## 参与项目

- 分享做法、交流项目经验或提出新想法。[交流与建议](https://github.com/savormundane/miliastra-wonderland-plugin/discussions)
- 遇到报错、结果不符或资料有误，附上插件版本和能复现问题的步骤。[反馈问题](https://github.com/savormundane/miliastra-wonderland-plugin/issues/new/choose)
- 欢迎补充平台资料、制作公开样例、纠正文档或提交代码。[参与贡献](CONTRIBUTING.md)
- 发现安全问题，可以通过私密渠道报告。[安全问题报告](SECURITY.md)

## 更多文档

- **使用文档**。查工程绑定、产物用法、MCP 和终端工具。[文档目录](docs/README.md)
- **公开样例**。跟做按钮预览、关卡审阅、Lua 排错或图片转图元。[样例目录](samples/README.md)
- **技术参考**。查平台资料来源、格式、工具流程和验证范围。[参考目录](references/README.md)

## 致谢

- Ayaya 为节点图工具链提供了基础，Beyond 提供离线模拟和界面预览。[Ayaya](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor) · [Beyond](https://github.com/1475505/miliastra-beyond-simulator)
- 感谢 Miliastra-knowledge 整理平台资料。[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)
- 感谢没空放肆分享 GEIMG 的图元处理资料和拟 L2D 案例，并授权随插件分发。[GEIMG Wiki](https://docs.lumkfs.cn/GEIMG-WIKI/) · [拟 L2D 案例](https://docs.lumkfs.cn/GEIMG-WIKI/EG-L2D/)
- 感谢 8itlab 及贡献者整理音效、特效资料和场景样例。[genshin-miliastra-mcp](https://github.com/8itlab/genshin-miliastra-mcp)
- 感谢 XingGou 分享静态 GIA 和坐标转换的研究，Miliastra-Tools 分享白盒枢轴的做法。[XingGou](https://github.com/Crazyfourrrrrrrrrrr/XingGou) · [Miliastra-Tools](https://github.com/Ayn1631/Miliastra-Tools)
- 感谢社区分享千星奇域文件格式和生成工具的研究。[genshin-miliastra-file-format](https://github.com/script-1024/genshin-miliastra-file-format) · [UGC-File-Generate-Utils](https://github.com/luern0313/UGC-File-Generate-Utils) 

## 许可证

本项目自有代码采用 GPL-3.0-only。随包的第三方代码、资料和素材保留各自的权利与许可。

[许可证](LICENSE) · [来源清单](PUBLIC_SOURCES.json) · [第三方声明](THIRD_PARTY_NOTICES.md)
