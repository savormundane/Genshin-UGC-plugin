# Genshin-UGC

Genshin-UGC 帮你用 AI 助手制作《原神》千星奇域关卡。它把节点目录、客户端 Lua API 和离线工具放在本机，方便你从查资料走到可以检查的产物。

**Windows x64** · Codex / Claude Code / DeepSeek Harness · 社区项目，独立于米哈游 · **当前版本 `4.1.0`** · [下载完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.1.0/Genshin-UGC-4.1.0-windows-x64.zip)

- **先查再写。** 查节点能用在哪类图、有哪些端口，或查 Lua API 的参数和返回值。
- **留着原件改。** 在已支持的 GIL 格式中，可替换指定 Lua 映射、调整已有标量默认值或定时器序列，另存后回读核对。
- **先在本地排错。** 检查 Lua 语法、节点连线和素材控件预算，必要时生成软件预览。

> 本地检查通过后，仍需在千星奇域编辑器中导入，并进游戏验证实际效果。

## 快速安装

1. 准备 Windows x64、Python 3.11 或 3.12、Node.js 22+，确认在 PowerShell 中可以运行 `codex`。首次安装需要联网下载锁定的 Python 依赖。
2. 在 PowerShell 中运行 Codex 安装命令。

   ```powershell
   & ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent codex
   ```

3. 选择已有工程目录，再选择一个与它互不包含的输出目录。安装完成后新开会话，确认插件已启用。

Claude Code、DeepSeek Harness、VS Code 等客户端的接入步骤，以及手动安装、更新、回退和卸载，见[安装指南](docs/installation.md)。

## 首次使用

在新会话中试一次节点查询。

> 查一下服务端“启动定时器”节点。告诉我调用方式、各输入端口的类型，并指出序列应该传什么。

随包工具的实际查询命中一个服务端节点。

| 查询结果 | 值 |
| --- | --- |
| 作用域 | 服务端（`server`） |
| Graph Code 调用 | `启动定时器(game, 目标实体, 定时器名称, 是否循环, 定时器序列)` |
| 数据输入 | 目标实体（实体）、定时器名称（字符串）、是否循环（布尔值）、定时器序列（浮点数列表） |

定时器序列填从小到大排列、以秒为单位的时间点，例如 `[1, 3, 5]`。命令行可用 `python scripts/qianxing.py nodes 启动定时器 --scope server --limit 1` 查询同一目录。[编译、写回与素材示例](docs/examples.md)

## 常见问题

- **该下载哪个包？** 手动安装请选上方完整 ZIP。GitHub 自动生成的源码包供浏览和开发。
- **可以只用 CLI 吗？** 可以。解压完整 ZIP 后配置专用 Python，再运行 `scripts/qianxing.py`。[独立运行环境](docs/runtime-environment.md)
- **安装途中找不到 Python 或工具未出现？** Python 可通过 `-Python` 指定真实解释器路径。安装完成后，新开会话确认插件和本地工具可见。[安装排障](docs/installation.md#失败后续装)

## 文档与反馈

[使用文档](docs/README.md) · [参与贡献](CONTRIBUTING.md) · [版本记录](CHANGELOG.md)

感谢 [Ayaya](https://github.com/AyayaXiaowan/Ayaya_Miliastra_Editor)、[miliastra-beyond-simulator](https://github.com/1475505/miliastra-beyond-simulator)、[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)、[GEIMG](https://docs.lumkfs.cn/GEIMG-WIKI/Download/)、奇匠学院及社区贡献的工具、资料与研究。自有代码采用 GPL-3.0-only。第三方内容保留各自的权利、许可与署名。[许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [来源清单](PUBLIC_SOURCES.json)
