# 安装、更新与卸载

选择对应客户端的安装入口。也可以使用 [PowerShell 安装](#powershell-安装)、[完整 Windows ZIP](#手动接入)或[独立命令行](runtime-environment.md)。

安装前核对 [Windows x64、Python 和 Node.js 要求](compatibility.md#运行要求)。首次准备环境需要联网获取锁定的 Python 依赖。

[返回首页](../README.md)

## Marketplace

客户端安装插件后，工程处理工具还需要[安装本地运行环境](#安装本地运行环境)。

### Codex

在终端添加市场并安装插件。

```text
codex plugin marketplace add savormundane/Genshin-UGC-plugin
codex plugin add genshin-ugc-public@genshin-ugc
```

添加市场后，也可从 Codex 的插件列表选择 Genshin-UGC。

### Claude

在 **Customize → Plugins → Add → Add marketplace** 添加 `savormundane/Genshin-UGC-plugin`，再从市场安装 Genshin-UGC。也可在终端添加同一个条目。

```text
claude plugin marketplace add savormundane/Genshin-UGC-plugin
claude plugin install genshin-ugc-public@genshin-ugc
```

使用本地 MCP 时，选择支持本机工具的 Claude 会话。完整 ZIP 用于解压后安装，Claude 的插件上传有文件数限制。 [Claude 插件说明](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) · [ZIP 上传要求](https://platform.claude.com/docs/en/manage-claude/plugins-api#upload-requirements)

### DeepSeek Harness

当前入口面向 `0.2.2-rc.5`。

#### 直接安装

在 **插件 → 添加插件**（**Plugins → Add plugin**）粘贴下面的完整地址并确认，安装完成后启用 **Genshin-UGC**。

```text
git+https://github.com/savormundane/Genshin-UGC-plugin.git#main&path:/marketplace/genshin-ugc
```

#### 从市场安装

1. 在 **Plugins → Experimental plugins** 启用 **Custom plugin indexes**。
2. 在 **Discover → Add index source** 添加下方地址。
3. 选择 **Genshin-UGC** 安装。

```text
https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/main/marketplace/dsh-index.json
```

### Agent Plugins

其他支持 Agent Plugins 和本地 stdio MCP 的客户端，可通过其市场入口添加 `savormundane/Genshin-UGC-plugin`，再安装 `genshin-ugc-public`。如果客户端提供的是本地目录导入，按[从本地目录导入](#从本地目录导入)操作。

### 安装本地运行环境

下面的 PowerShell 命令下载完整工具包，创建插件专用的 Python 环境并安装依赖。安装器会记录工具读取工程和保存产物所用的[项目目录和输出目录](#准备输入与输出目录)。各客户端可共用同版本的环境。

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.2/install.ps1'))) -Agent agent-plugins
```

安装完成时显示 `prepared` 和 `runtime_smoke: passed`。

客户端需能找到 `node`。安装时使用 `-Root` 自选位置的用户，应在启动客户端前将 `UGC_PUBLIC_INSTALL_ROOT` 设为同一个绝对路径。

### 准备输入与输出目录

- **项目目录**存放工具可读取的工程、Lua 或图片等输入。目录须提前创建。
- **输出目录**用于保存报告和生成文件，由安装器创建。项目目录与输出目录必须互不包含，例如 `C:\Qianxing\project` 和 `C:\Qianxing\outputs`。

也可用 `-Project` 和 `-Outputs` 指定这两个目录。默认安装根为 `$env:LOCALAPPDATA\Genshin-UGC-Public`。

## PowerShell 安装

已有 `codex` 命令的用户可用下方命令准备环境并登记插件。Claude 用户将末尾替换为 `-Agent claude-code`，需要可用的 `claude` 命令。

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.2/install.ps1'))) -Agent codex
```

选择[项目和输出目录](#准备输入与输出目录)。安装完成时显示 `installed` 和 `runtime_smoke: passed`。

### 从本地目录导入

| 客户端 | 准备和导入 |
| --- | --- |
| DeepSeek Harness | 将上方 PowerShell 命令的末尾替换为 `-Agent deepseek-harness`。在 **Plugins → Add plugin** 选择输出中的 `bundle_directory`。 |
| Agent Plugins | 按[安装本地运行环境](#安装本地运行环境)运行命令，在客户端的本地目录导入入口选择输出中的 `plugin_directory`。 |

客户端按绝对路径读取整个版本目录中的运行环境和配置。单独配置本地 MCP 见[客户端适配](contributing/development.md#客户端适配)。

## 手动接入

1. 从 [4.1.2 Release](https://github.com/savormundane/Genshin-UGC-plugin/releases/tag/v4.1.2) 下载 `Genshin-UGC-4.1.2-windows-x64.zip`。请在 Release 附件中选择完整包，`Source code` 提供源码。
2. 从 [Release 附件信息](https://docs.github.com/en/rest/releases/assets)取得 ZIP 的 SHA-256，用 `Get-FileHash -Algorithm SHA256` 核对本地文件。
3. 保留原 ZIP，将它解压到同一父目录。进入解压出的 `Genshin-UGC` 目录运行下方命令，按客户端选用 `-Agent codex`、`claude-code`、`deepseek-harness` 或 `agent-plugins`。

```powershell
.\install.ps1 -Agent codex -Archive ..\Genshin-UGC-4.1.2-windows-x64.zip -Sha256 '<GitHub 显示的 ZIP SHA-256>'
```

DSH 或 Agent Plugins 安装完成后，还需在客户端[导入目录](#从本地目录导入)。

## 回退与卸载

- **市场安装**通过客户端管理更新和卸载。升级后[安装对应版本的运行环境](#安装本地运行环境)。
- **PowerShell 登记的 Codex 和 Claude**可从新版安装器升级。回退或卸载可用完整 ZIP 内的命令。改用 `-Agent claude-code` 即可操作 Claude，使用过 `-Root` 的用户应传入原值。
- **本地目录导入**通过客户端管理。升级时先准备并验证新目录，回退时重新指向保留的旧版本。

```powershell
# 回退到本机仍保留的版本
.\install.ps1 -Agent codex -Action rollback -Version '<旧版本>'

# 卸载当前登记的安装
.\install.ps1 -Agent codex -Action uninstall
```

卸载保留项目、输出和各版本的运行环境。清理旧版本目录前，确认其他客户端已停用该版本，并且无需回退。

## 失败后续装

| 遇到的问题 | 检查方式 |
| --- | --- |
| 市场中找不到插件 | 核对所用客户端的仓库名或 DSH 索引 URL。DSH 需启用 **Custom plugin indexes**。必要时使用 [PowerShell 安装](#powershell-安装)。 |
| 能看到 Skill，工具未连通 | 确认[本地运行环境](#安装本地运行环境)已安装，客户端能找到 `node` 并允许本地 MCP。若用过 `-Root`，核对 `UGC_PUBLIC_INSTALL_ROOT` 后重启客户端。 |
| 插件版本和运行环境不符 | 以客户端显示的插件版本为准，准备对应版本的环境。 |
| 找不到 Python 或目录冲突 | 按[运行要求](compatibility.md#运行要求)检查 Python，必要时用 `-Python` 指定解释器绝对路径。确认[项目和输出目录](#准备输入与输出目录)互不包含。 |
| 安装中断 | 保留失败目录，用相同参数加 `-Resume` 重跑。Claude 登记后若启用中断，按错误提示核对客户端中的条目。 |
| CLI 正常，客户端无法调用工具 | 检查插件是否启用、MCP 配置是否指向准备好的版本。 [连接 MCP](runtime-environment.md#连接-mcp-或切换工程) |

仍无法解决时，通过 [Bug 反馈](https://github.com/savormundane/Genshin-UGC-plugin/issues/new?template=bug_report.yml)提供版本、客户端、执行命令和第一条错误信息。可先删去路径、日志和截图中无需公开的内容。
