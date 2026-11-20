# Genshin-UGC

面向《原神》千星奇域创作者的本地开发工具包，提供 **Codex**、**Claude Code**、**DeepSeek Harness** 和其他客户端的本地安装指引。

直接让通用 AI 写千星奇域的节点图或客户端 Lua，容易踩到三类坑：编造不存在的节点或控件 API、直接改 `.gil` 时弄坏未知字段、以及把图片转成图元时控件数超标。这个仓库把整理好的平台资料、客户端 API、离线节点图编译链、`.gil`/`.gia` 读写工具、自有图片拟合器和软件模拟器打包在一起——让 AI 先查真实资料再动手，产出文件先在本地过一遍静态检查和预览。

> 社区个人维护项目，独立于米哈游官方工具。

**当前版本：`4.0.0`** · [下载 Windows x64 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.0.0/Genshin-UGC-4.0.0-windows-x64.zip) · [快速安装](#快速安装) · [首次使用](#首次使用) · [完整文档](docs/README.md)

## 它能帮你解决什么

内置 5 个领域 Skill、统一 CLI（`scripts/qianxing.py`）、18 项本地 MCP 工具，以及随包的离线编译器与软件模拟器：

| 你手上有 | 可以用它做什么 |
| --- | --- |
| **现有千星工程或关卡** | 只读排查实体、模板、组件配置和资源引用，定位断链或版本规则冲突 |
| **一段玩法逻辑或节点图** | 按真实节点定义写服务端/客户端 Graph Code，核对端口类型、数据流和执行顺序，离线编译导出 `.gia` / `.gil` |
| **客户端界面或控件 Lua** | 查完真实控件 API 再写交互、输入、生命周期与动画，少踩编造接口的坑，支持多文件装配与语法检查 |
| **需要对比或修改的 `.gil`** | 对比两份 `.gil` 差异，在已支持的格式中替换指定脚本或修改局部字段，保留未修改的数据并回读确认 |
| **PNG 图片或图元素材** | 解码前检查尺寸上限，读取像素后按透明度和控件预算拟合，输出图元、`data.lua` 和预览图 |

共享工具还提供跨客户端协议、多人会话、存档结构和可重建交付的配置与检查。

## 快速安装

完整包面向 **Windows x64**，需提前准备好 **Python 3.11 或 3.12**、**Node.js 22+**（DeepSeek Harness 需 **Node.js 24.9+**）以及目标客户端。首次安装需要联网按哈希锁拉取 Python 依赖，安装器只为本插件建立独立虚拟环境，不改动全局环境。

### 选择你的客户端

| 客户端 | 安装方式 | 额外要求 / 说明 |
| --- | --- | --- |
| **Codex** | 一键 PowerShell（`-Agent codex`） | 确认 `codex` 命令可用，支持激活中断续装 |
| **Claude Code** | 一键 PowerShell（`-Agent claude-code`） | 确认 `claude` 命令可用，见 [Claude Code 安装](references/installation.md#claude-code) |
| **DeepSeek Harness** | 准备命令（`-Agent deepseek-harness`）后导入 | 需 Node.js 24.9+ 与 `0.2.2-rc.5`，见 [DeepSeek Harness 安装](references/installation.md#deepseek-harness) |
| **VS Code / Cursor / Copilot CLI / Kiro / Antigravity** | 准备命令（`-Agent agent-plugins`）后导入 | 复用同一份本地插件目录，见 [其他客户端](references/installation.md#其他客户端) |
| **其他支持本地插件的客户端** | 准备命令（`-Agent agent-plugins`） | 走 [通用客户端步骤](references/installation.md#通用客户端) |

以 **Codex** 为例，在 PowerShell 中运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent codex
```

使用 **Claude Code** 时，只需把末尾改为 `-Agent claude-code`。

安装过程中会让你指定两个目录（也可通过 `-Project` 和 `-Outputs` 参数直接传入）：
1. **现有项目目录**：你的千星工程所在路径，工具从中读取输入。
2. **独立输出目录**：保存报告和生成文件的路径，必须与项目目录互不包含，防止误覆盖原始文件。

装完后**新开一个客户端会话**，确认 Genshin-UGC 已启用，就可以直接试下面的例子。

[手动使用 ZIP 安装](references/installation.md#手动接入) · [更新、回退与卸载](references/installation.md#回退与卸载) · [安装排障与续装](references/installation.md#失败后续装)

## 首次使用

### 1. 先只读检查一份现有 `.gil`

把 `.gil` 放到安装时选择的项目目录里，直接告诉助手你想看什么：

> “先只读检查项目里的 `level.gil`，列出里面的 Lua 脚本和能识别的资源引用，告诉我哪些地方需要人工确认。”

确认报告没问题后，再让它把你的 Lua 脚本替换进指定脚本映射并另存新副本，顺便说明改了什么、回读核对了什么。最后把新文件导入千星奇域编辑器，实测受影响的交互。

### 2. 其他可以直接试的日常任务

* **写界面**：`“查一下 game.GetUICanvasSize，给我一个贴合当前文档的 Lua 示例，说明这段逻辑该放进哪个回调。”`
* **转素材**：`“检查项目里的 icon.png，按 200 个矩形预算估算并拟合成图元，先出一张本地预览图。”`
* **写节点图**：`“给双人抢分玩法写一套服务端节点图，核对完端口类型和数据流后导出 .gia。”`

更多分领域端到端例子见 [使用示例](docs/examples.md)。

## 常见问题与边界

* **应该下载哪个 ZIP？** 在 Release 附件中下载 `Genshin-UGC-4.0.0-windows-x64.zip`。GitHub 自动生成的 Source code 压缩包只供查看源码，目录结构不适用于安装器。
* **可以不装客户端插件、只用命令行吗？** 可以。解压完整 ZIP 后按 [独立运行环境](references/runtime-environment.md) 配置专用环境，直接调用 `scripts/qianxing.py`。
* **本地预览或检查通过后，能直接交付吗？** 本地检查和预览用来提前排掉语法、结构和预算问题；是否能正常导入要进千星奇域编辑器确认，实际手感和渲染表现要进游戏试运行。详见 [运行要求与验证](docs/compatibility.md)。
* **提示找不到 Python 怎么办？** Windows 上常见原因是命中了微软商店的占位 `python.exe`，直接通过 `-Python '你的 python.exe 真实路径'` 指定即可。

## 文档与反馈

* **使用与参考**：[完整文档入口](docs/README.md) · [安装指南](references/installation.md) · [运行要求与验证](docs/compatibility.md)
* **Agent 资料索引**：[平台资料与操作指南](references/README.md)
* **社区与记录**：[版本记录](CHANGELOG.md) · [参与贡献](CONTRIBUTING.md) · [安全反馈](SECURITY.md) · [反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues)

## 致谢与许可证

感谢 [Ayaya](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor)、[miliastra-beyond-simulator](https://github.com/1475505/miliastra-beyond-simulator)、[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)、[GEIMG](https://docs.lumkfs.cn/GEIMG-WIKI/Download/)、奇匠学院及相关社区项目提供的工具、资料与研究。完整署名和依赖清单见 [第三方声明](THIRD_PARTY_NOTICES.md)。

本项目自有代码采用 [GPL-3.0-only](LICENSE)。收录的第三方代码、资料与素材保留各自权利与许可，逐项来源和授权状态见 [来源清单](PUBLIC_SOURCES.json)。
