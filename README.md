# Genshin-UGC

让 AI 助手帮你做《原神》千星奇域关卡：节点图、客户端 Lua、GIL 文件和图片素材。节点目录、客户端 API 和离线检查工具都装在你的电脑上，助手先查真实资料再动手，改完先在本机检查一遍。

**Windows x64** · Codex / Claude Code / DeepSeek Harness 等 · 社区项目，独立于米哈游 · **当前版本 `4.1.0`** · [下载完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.1.0/Genshin-UGC-4.1.0-windows-x64.zip)

- **先查再写。** 节点能用在哪类图、有哪些端口，Lua API 的参数和返回值，都从随包资料查，不靠猜。
- **改文件不动原件。** 修改 `.gil` 时另存新文件并回读核对，原文件保持不变。
- **交付前先过一遍。** 本地检查 Lua 语法、节点连线和素材控件预算，需要时生成软件预览。

> 本地检查通过，不等于在游戏里可用。产物仍需导入千星奇域编辑器，并进游戏验证。

## 能让助手做什么

| 你想做的事 | 助手会用到 | 可以这样说 |
| --- | --- | --- |
| 接手旧地图，看清里面有什么 | 工程检查（只读） | “只读检查 `level.gil`，列出模板和节点图的挂载关系。” |
| 写服务端或客户端的节点图 | Graph Code | “查一下‘启动定时器’节点，再写一个 60 秒倒计时。” |
| 写带交互的界面脚本 | Client Lua | “查按钮回调 API，写一个带点击反馈的 HUD 脚本并检查语法。” |
| 对比两版地图，或只换一段脚本 | GIL | “对比 `old.gil` 和 `new.gil`，把 `hud.lua` 替换进指定脚本，另存后回读。” |
| 把 PNG 图标转成图元 | 素材 | “按 200 个矩形预算拟合 `icon.png`，给我预览和误差汇总。” |

每个领域的完整示例见[使用示例](docs/examples.md)，术语见[术语表](docs/glossary.md)。

## 安装

**需要** Windows x64、Python 和 Node.js，版本见[运行要求与验证](docs/compatibility.md)。首次安装要联网下载锁定的 Python 依赖。

1. 确认你的客户端命令能在 PowerShell 中运行（`codex` 或 `claude`）。
2. 复制对应命令到 PowerShell 运行。

   | 客户端 | 命令 |
   | --- | --- |
   | Codex | `& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent codex` |
   | Claude Code | `& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent claude-code` |

3. 按提示选择已有工程目录，再选一个与它互不包含的输出目录，报告和生成文件会写到输出目录。
4. 装完后新开会话，确认插件已启用。

DeepSeek Harness、VS Code、Cursor 等客户端的接入，以及手动安装、更新、回退和卸载，见[安装指南](docs/installation.md)。

## 第一次使用

在新会话里把这段提示发给助手。

> 请调用 Genshin-UGC 的 `nodes_lookup` 查询服务端“启动定时器”节点。告诉我调用签名、各输入端口的类型，以及定时器序列该怎么填。

返回结果可对照下表。

| 项目 | 结果 |
| --- | --- |
| 调用 | `启动定时器(game, 目标实体, 定时器名称, 是否循环, 定时器序列)` |
| 数据输入 | 目标实体（实体）、定时器名称（字符串）、是否循环（布尔值）、定时器序列（浮点数列表） |
| 序列怎么填 | 从小到大排列、单位为秒的时间点，最多 100 个，例如 `[1, 3, 5, 7]` |

在客户端查看工具调用记录，确认 `nodes_lookup` 成功返回一个 `server` 节点。

也可以从命令行查询同一目录。进入解压后的 `Genshin-UGC` 目录，用专用环境的 `Scripts\python.exe` 运行下方命令。环境配置见[独立运行环境](docs/runtime-environment.md)。

```powershell
& '<专用 Python 的绝对路径>' .\scripts\qianxing.py nodes '启动定时器' --scope server --limit 1
```

## 常见问题

- **该下载哪个包？** 手动安装用上方的完整 ZIP。GitHub 自动生成的源码包只用于浏览和开发。
- **会改我的工程文件吗？** 不会直接改。需要修改时另存新文件，原文件保留。输出写在你选的输出目录。
- **可以只用命令行吗？** 可以。解压完整 ZIP，配置专用 Python 后运行 `scripts/qianxing.py`。见[独立运行环境](docs/runtime-environment.md)。
- **安装时找不到 Python，或装完看不到工具？** 用 `-Python` 指定真实的解释器路径，装完后新开会话再看。见[安装排障](docs/installation.md#失败后续装)。
- **它保证关卡在游戏里能跑吗？** 不保证。检查分五层，本地只覆盖前两层，见[运行要求与验证](docs/compatibility.md)。

## 文档与反馈

[使用文档](docs/README.md) · [参与贡献](CONTRIBUTING.md) · [版本记录](CHANGELOG.md)

感谢 [Ayaya](https://github.com/AyayaXiaowan/Ayaya_Miliastra_Editor)、[miliastra-beyond-simulator](https://github.com/1475505/miliastra-beyond-simulator)、[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)、[GEIMG](https://docs.lumkfs.cn/GEIMG-WIKI/Download/)、奇匠学院及社区贡献的工具、资料与研究。自有代码采用 GPL-3.0-only，第三方内容保留各自的权利、许可与署名。[许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [来源清单](PUBLIC_SOURCES.json)
