# Genshin-UGC

**《原神》千星奇域社区开发工具包**

在你常用的 AI 助手里查阅千星奇域资料、检查现有工程、编写节点图和 Lua，或制作可预览的素材。可以先做只读检查，也可以基于现有项目生成新文件并核对改动。

[下载 Windows x64 ZIP · 4.0.0](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.0.0/Genshin-UGC-4.0.0-windows-x64.zip) · [快速安装](#快速安装) · [使用示例](#首次使用) · [完整文档](docs/README.md)

本项目由社区维护，独立于米哈游官方工具。

## 能做什么

| 你手上有 | 可以用它做什么 |
| --- | --- |
| 一份现有工程或关卡 | 检查实体、模板、组件和资源引用，获取问题清单和修改建议。 |
| 一段玩法规则或节点图 | 编写或检查 Graph Code，核对节点的连接、数据类型及执行顺序。 |
| 一个客户端界面或一段 Lua | 查询控件 API，编写按钮交互和动画，检查 Lua 语法及已知 API 用法。 |
| 一个要比较或修改的 GIL 文件 | 对比两份 GIL，或把 Lua 替换到新副本中，再读回核对指定脚本。 |
| 一张图或现有图元素材 | 检查尺寸、颜色和透明度，估算图元成本，生成转换结果与本地预览。 |

## 快速安装

完整工具包适用于 **Windows x64**。准备 **Python 3.11 或 3.12**、**Node.js 22 或更新版本**和你选用的客户端。首次安装需要联网。

### Codex、Claude Code 与 DeepSeek Harness

使用 `codex` 时，确认命令行工具可用，然后在 PowerShell 中运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent codex
```

- [Claude Code 安装](references/installation.md#claude-code)也提供可直接复制的 PowerShell 命令。
- [DeepSeek Harness 安装](references/installation.md#deepseek-harness)需要 Node.js 24.9 或更新版本。运行准备命令后，在客户端选择插件目录。

### 其他客户端

- [VS Code、Cursor、GitHub Copilot CLI、Kiro 和 Google Antigravity](references/installation.md#其他客户端) 可以从同一份本地插件开始，按各自的步骤导入。
- **通用客户端** 如果它能导入本地插件并运行本机工具，可以走[通用安装步骤](references/installation.md#通用客户端)。

按提示选择现有的千星奇域项目目录，再选一个与项目互不包含的目录来保存报告和生成文件。安装后打开新会话，确认 Genshin-UGC 已启用，再试下面的例子。

[手动使用 ZIP 安装](references/installation.md#手动接入) · [更新、回退与卸载](references/installation.md#回退与卸载) · [安装排障](references/installation.md#失败后续装)

## 首次使用

### 先检查一个现有 GIL

把 GIL 放在安装时选择的项目目录里，然后告诉助手你想确认什么。例如：

> 先只读检查项目里的 `level.gil`。列出其中的 Lua 脚本和能识别的资源引用，告诉我哪里需要人工确认。先给报告。

如果检查结果明确，再要求它用你的 Lua 脚本替换指定映射，另存一份 GIL，并说明改了什么、读回检查了什么。把新文件导入千星奇域编辑器，实际试一次受影响的交互。

### 其他可以直接试的任务

- **做界面**　「查一下 `game.GetUICanvasSize`，给我一个贴合当前文档的 Lua 示例，说明把这段逻辑放在哪个回调里。」
- **做素材**　「检查项目里的 `icon.png`，估算转成图元后的数量，先给一张本地预览。」

[更多使用示例](docs/examples.md)

## 常见问题

**哪个 ZIP 用来安装？** 在 Release 附件中选择 `Genshin-UGC-4.0.0-windows-x64.zip`。GitHub 自动生成的 Source code 压缩包供查看源代码。

**可以只用命令行吗？** 可以。下载完整 ZIP 后按[独立运行环境](references/runtime-environment.md)配置，再使用对应的命令行工具。

**预览通过后能直接交付吗？** 预览适合检查转换结果。可导入性要在千星奇域编辑器里确认，交互和表现需要在游戏中试运行。[运行要求与验证](docs/compatibility.md)

## 文档与反馈

[平台资料与操作指南](references/README.md) · [开发与贡献](docs/README.md) · [版本记录](CHANGELOG.md) · [反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues)

## 致谢与许可证

感谢 [Ayaya](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor)、[miliastra-beyond-simulator](https://github.com/1475505/miliastra-beyond-simulator)、[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)、[GEIMG](https://docs.lumkfs.cn/GEIMG-WIKI/Download/)、奇匠学院及相关项目提供的工具、资料和研究。完整署名和来源见[第三方声明](THIRD_PARTY_NOTICES.md)。

项目自有代码采用 [GPL-3.0-only](LICENSE)。第三方内容沿用各自的权利与许可，来源和授权状态见[来源清单](PUBLIC_SOURCES.json)。
