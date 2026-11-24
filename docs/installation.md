# 安装、更新与卸载

选择对应客户端的安装入口，也可以[从本地源码导入](#从本地目录导入)或[自行打包 ZIP](#自行打包-zip)。

完整工具支持 Windows x64。客户端从同一个插件目录加载 Skills 和 MCP。见[运行要求](compatibility.md#运行要求)。

[返回首页](../README.md)

## Marketplace

### Codex

[终端安装命令](../README.md#codex)

### Claude

[终端安装命令](../README.md#claude)

使用本地 MCP 时，选择支持本机工具的 Claude 会话。 [Claude 插件说明](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)

### DeepSeek Harness

[GitHub 直装](../README.md#deepseek-harness)

### Agent Plugins

其他支持 Agent Plugins 和本地 stdio MCP 的客户端，可通过其市场入口添加 `savormundane/miliastra-wonderland-plugin`，再安装 `miliastra-wonderland`。如果客户端提供的是本地目录导入，按[从本地目录导入](#从本地目录导入)操作。

## 运行依赖与工程目录

客户端启用插件后，通过 Node 启动本地 MCP。启动器依次查找运行绑定指定的 Python、当前虚拟环境、兼容的旧安装和 PATH 上的 Python。显式设置 `UGC_PYTHON` 时，使用该路径。找不到具备完整依赖的环境时，可由 PATH 上的 uv 按 `uv.lock` 准备环境，需要时也会获取受支持的 Python。首次缺少缓存时，uv 需要联网。 [uv 安装说明](https://docs.astral.sh/uv/getting-started/installation/)

- 用 `UGC_PYTHON` 指定已有 Python 的绝对路径。旧安装位于自选位置时，用 `MILIASTRA_WONDERLAND_INSTALL_ROOT` 指明原安装根。也可用 `UGC_RUNTIME_CONFIG` 直接选择旧的 `runtime.json`。
- 节点、API 与公开资料查询可直接使用。文件工具优先使用显式工程路径，其次使用客户端通过 MCP Roots 提供的会话目录。客户端未提供目录时，可沿用 `runtime.json`。只读查询只需要工程目录。写入默认按工程归档到本机插件数据目录，也可指定独立的输出目录。参见[切换工程](runtime-environment.md#连接-mcp-或切换工程)。

## 从 Genshin-UGC 迁移

从[首页](../README.md#安装)登记 Miliastra Wonderland 并安装。新插件 ID 为 `miliastra-wonderland`。确认新入口可用后，在客户端移除旧插件和市场。已有 Python、工程目录和输出可以继续使用。将 `UGC_RUNTIME_CONFIG` 指向原有的 `runtime.json` 即可复用配置。

- **DSH 旧安装**可按[当前直装地址](../README.md#deepseek-harness)重新登记。
- **旧 ZIP 或 PowerShell 登记**可保留本地副本供回退。需要重新安装时，使用当前市场、直装或[自行打包](#自行打包-zip)。

## 从本地目录导入

解压[仓库源码](https://github.com/savormundane/miliastra-wonderland-plugin/archive/refs/heads/main.zip)，或检出 GitHub 的 `main` 分支。选择包含插件清单的源码根目录。

| 客户端 | 导入入口 |
| --- | --- |
| Agent Plugins | 在客户端的目录导入入口选择包含 `plugin.json` 的根目录。 |

## 自行打包 ZIP

进入解压后的源码根目录，用 Python 按分发清单打包。命令把完整 Windows x64 ZIP 写到源码目录之外，并输出 SHA-256。

```powershell
python -B scripts/package_release.py --source . --out ../Miliastra-Wonderland-1.0.0-windows-x64.zip --layout plugin --archive-root miliastra-wonderland
```

可解压后[导入插件目录](#从本地目录导入)。需要用 PowerShell 登记时，从同一份源码目录传入本地包和打包命令给出的摘要。Claude 可将 `-Agent codex` 改为 `-Agent claude-code`。

```powershell
.\install.ps1 -Agent codex -Archive ..\Miliastra-Wonderland-1.0.0-windows-x64.zip -Sha256 '<打包输出的 SHA-256>'
```

## 回退与卸载

- **市场安装和直装**通过客户端管理更新和卸载。需要更换依赖时，启动器会交给 uv。
- **同版本重发**后，若客户端仍加载旧缓存，请从原入口卸载并重新安装。保留现有运行配置或通过 `UGC_RUNTIME_CONFIG` 指回原文件，便可继续使用原工程和解释器。
- **PowerShell 登记的 Codex 和 Claude**可从新版安装器升级。回退或卸载可用完整 ZIP 内的命令。改用 `-Agent claude-code` 即可操作 Claude，使用过 `-Root` 的用户应传入原值。
- **本地目录导入**通过客户端管理。升级时导入新目录，回退时重新指向保留的旧版本。

```powershell
# 回退到本机仍保留的版本
.\install.ps1 -Agent codex -Action rollback -Version '<旧版本>'

# 卸载当前登记的安装
.\install.ps1 -Agent codex -Action uninstall
```

卸载保留项目、输出和各版本的运行环境。清理旧版本目录前，确认其他客户端已停用该版本，并且无需回退。

## 安装自检

工具连不上时，在 Windows PowerShell 进入要检查的插件目录。若检查客户端安装的副本，可从 MCP 日志中的 `scripts\mcp_launcher.cjs` 路径找到其上两级目录。用 PowerShell 登记的插件可从[安装记录](runtime-environment.md#复用-powershell-安装器配置的环境)中的 `current.home` 找到 `miliastra-wonderland` 子目录。然后运行以下命令。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-install.ps1
```

能运行 Node 时，也可以直接执行 `node .\scripts\mcp_launcher.cjs --check`。

自检适用于市场、GitHub 直装、本地导入和 PowerShell 登记。它检查启动文件、Node.js 版本、已有 Python 环境及 PATH 上的 uv，遇到阻塞项时会显示失败环节、原始错误和下一步。自检只做本机探测。如果报告会由 uv 准备环境，请在依赖源可访问时重启客户端，再[查询第一个节点](../README.md#查询第一个节点)确认工具连通。MCP 连通后，可继续用 `doctor` 查看客户端实际采用的工程目录和依赖。

自检读取当前终端的 PATH、`UGC_PYTHON` 和 `UGC_RUNTIME_CONFIG` 等环境变量。客户端单独配置了解释器或绑定文件时，把同样的值设置到自检终端。使用 WinGet 的用户可运行 `winget install --id=astral-sh.uv -e` 安装 uv，再打开新终端检查 `uv --version`。 [uv 的 WinGet 安装说明](https://docs.astral.sh/uv/getting-started/installation/#winget)

## 失败后续装

| 遇到的问题 | 适用安装方式 | 下一步 |
| --- | --- | --- |
| 市场中找不到插件 | Codex CLI 或 Claude Code 的市场安装 | 核对[终端安装命令](../README.md#安装)中的 GitHub 仓库名和插件 ID。 |
| 直装地址无法加载 | DeepSeek Harness 的 GitHub 直装 | 核对直装地址和客户端版本，再到「插件 → 添加插件」重试。 [直装说明](../README.md#deepseek-harness) |
| 能看到 Skill，工具未连通 | 所有安装方式 | 先[运行安装自检](#安装自检)。修复后重启客户端，确认插件已启用并允许本地 MCP。使用自选旧安装根目录时，核对 `MILIASTRA_WONDERLAND_INSTALL_ROOT`。 |
| MCP 启动时缺少 Python 或依赖 | 所有安装方式 | 安装 uv 并确认新终端能运行 `uv --version`，或让 `UGC_PYTHON` 指向已配置依赖的解释器。修正旧绑定后重新打开客户端。 |
| 安装器找不到 Python，或提示工程与输出路径冲突 | 用 `install.ps1` 准备本地 ZIP | 缺少 Python 时，给原安装命令加 `-Python '<解释器绝对路径>'`。目录冲突时，为 `-Project` 和 `-Outputs` 选择互不包含的目录。 |
| 安装准备中断 | 用 `install.ps1` 准备本地 ZIP | 保留未完成的安装目录。按报错修复后，用同一安装命令加 `-Resume` 重跑。已进入 Claude 登记时，按错误提示核对客户端中的条目。 |
| 工程目录未绑定，或找不到输入文件 | 所有安装方式 | 打开包含输入的本地工程并授权，或按[工程绑定说明](runtime-environment.md#连接-mcp-或切换工程)配置目录。核对输入文件的路径和扩展名。 |
| 输出目录已存在 | 所有安装方式 | 在独立输出根目录下，给本次输出取一个尚未使用的目录名。 |
| 无法识别千星奇域版本 | 所有安装方式 | 核对游戏内版本和报错列出的已收录版本。目标版本尚未收录时，可附版本号和资料来源反馈。 |
| CLI 正常，客户端无法调用工具 | 所有安装方式 | 确认插件已启用，并核对 MCP 配置是否指向自检通过的插件目录。 [连接 MCP](runtime-environment.md#连接-mcp-或切换工程) |

仍无法解决时，提供插件版本、客户端、执行命令、自检失败环节和原始错误。可先删去路径、日志和截图中无需公开的内容。 [提交 Bug 反馈](https://github.com/savormundane/miliastra-wonderland-plugin/issues/new?template=bug_report.yml)
