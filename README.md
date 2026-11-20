# Genshin-UGC

面向《原神》千星奇域创作者的社区开发插件。让 AI 助手查平台资料、检查工程、编写节点图和 Lua，并处理 GIL 文件与素材。本项目与米哈游官方无关。

## 能做什么

- **编辑器工程**　检查实体、模板、组件和资源引用。
- **节点图**　编写和编译 Graph Code，检查端口和数据流。
- **客户端 Lua**　查询控件 API，编写交互和动画，组合 Lua 源码。
- **GIL 文件**　比较、修改和组装文件，读回结果核对变更。
- **素材**　转换图片和图元，估算成本并生成本地预览。

## 快速安装

完整工具包适用于 **Windows x64**。请先安装 Python 3.11 或 3.12、Node.js 22 或更新版本，以及要使用的客户端。首次安装需要联网。

**Codex**　确认其命令行工具可用，然后在 PowerShell 中运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent codex
```

使用 [Claude Code](references/installation.md#claude-code) 或 [DeepSeek Harness](references/installation.md#deepseek-harness) 时，按对应指南安装。安装时选择千星奇域项目目录，再选择一个与项目分开的输出目录。

[下载完整 Windows x64 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.0.0/Genshin-UGC-4.0.0-windows-x64.zip) · [手动安装、更新和卸载](references/installation.md) · [所有版本](https://github.com/savormundane/Genshin-UGC-plugin/releases)

## 首次使用

安装后打开新会话，给助手一个具体的文件或任务。例如：

- 「帮我检查这个 GIL 的资源引用，先只读。」
- 「查一下千星奇域的 `game.GetUICanvasSize`，给我一个 Lua 使用示例。」

让助手说明检查结果和生成文件的位置。要确认导入和游戏内效果，请在千星奇域编辑器中检查生成文件。[更多使用示例](docs/examples.md)

## 更多文档

- [使用与排障](references/installation.md)
- [平台资料与操作指南](references/README.md)
- [开发与贡献](docs/README.md)
- [版本记录](CHANGELOG.md)
- [反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues)

## 致谢与许可证

感谢 Ayaya、miliastra-beyond-simulator、Miliastra-knowledge、GEIMG、奇匠学院及相关项目提供的工具、资料和研究。完整署名和来源见[第三方声明](THIRD_PARTY_NOTICES.md)。

项目自有代码采用 [GPL-3.0-only](LICENSE)。第三方内容沿用各自的权利与许可，来源和授权状态见[来源清单](PUBLIC_SOURCES.json)。
