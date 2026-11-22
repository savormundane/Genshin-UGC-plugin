# 安装、更新与卸载

选择对应客户端的安装入口。也可以使用 [PowerShell 安装](#powershell-安装)、[完整 Windows ZIP](#手动接入)或[独立命令行](runtime-environment.md)。

完整工具支持 Windows x64。客户端从同一个插件目录加载 Skills 和 MCP。见[运行要求](compatibility.md#运行要求)。

[返回首页](../README.md)

## Marketplace

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
git+https://github.com/savormundane/Genshin-UGC-plugin.git#main
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

## 运行依赖与工程目录

客户端启用插件后，通过 Node 启动本地 MCP。启动器优先使用已选的 Python、当前虚拟环境、PATH 中的 Python 或兼容的旧安装。找不到具备完整依赖的环境时，由 PATH 上的 [uv](https://docs.astral.sh/uv/getting-started/installation/) 按 `uv.lock` 准备环境，必要时也由 uv 获取受支持的 Python。启动过程无需运行 PowerShell 安装器。首次缺少缓存时，uv 需要联网。

- 用 `UGC_PYTHON` 指定已有 Python 的绝对路径。旧安装位于自选位置时，用 `UGC_PUBLIC_INSTALL_ROOT` 指明原安装根。也可用 `UGC_RUNTIME_CONFIG` 直接选择旧的 `runtime.json`。
- 节点、API 与公开资料查询可直接使用。文件工具需要通过 `UGC_PROJECT_ROOT` 和 `UGC_OUTPUT_ROOT` 指定两个已存在且互不包含的绝对目录，分别用于读取工程和保存结果。旧的共享 `agent-plugins` 绑定可自动沿用，其他旧安装可显式选用其 `runtime.json`。修改环境变量后重启客户端。参见[切换工程](runtime-environment.md#连接-mcp-或切换工程)。

## 从旧入口迁移

- **Codex、Claude 与 Agent Plugins 市场**沿用原市场和插件名。在客户端刷新市场并更新。若客户端仍缓存同版本的旧目录，从原市场卸载插件再重新安装。
- **DSH 旧直装**的地址末尾包含 `&path:/marketplace/genshin-ugc`。卸载旧登记，再粘贴上方[新的直装地址](#直接安装)。已经添加索引的用户仍可使用原索引 URL。旧路径随重复插件目录删除；需要回退时，可用下面的固定提交地址恢复旧入口。
- **旧 ZIP 或 PowerShell 登记**可继续使用。改用新版市场或直装时，可先停用旧条目，保留它的 Python、工程绑定及产物。

```text
git+https://github.com/savormundane/Genshin-UGC-plugin.git#10a2c1e15e06b0f87b64cdf2dfb033592fd3637d&path:/marketplace/genshin-ugc
```

## PowerShell 安装

此备用入口使用正式发布的 ZIP 并登记插件。Claude 用户将末尾替换为 `-Agent claude-code`，需要可用的 `claude` 命令。

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.2/install.ps1'))) -Agent codex
```

按提示选择[项目和输出目录](#运行依赖与工程目录)。安装完成时显示 `installed` 和 `runtime_smoke: passed`。

### 从本地目录导入

| 客户端 | 准备和导入 |
| --- | --- |
| DeepSeek Harness | 在 **Plugins → Add plugin** 选择包含 `package.json` 与 `cordis.patch.yml` 的插件根目录。对旧正式 ZIP，可用 `-Agent deepseek-harness` 准备后选择输出中的 `bundle_directory`。 |
| Agent Plugins | 在客户端的目录导入入口选择包含 `plugin.json` 的插件根目录。旧正式 ZIP 可通过 `-Agent agent-plugins` 准备，再导入输出中的 `plugin_directory`。 |

## 手动接入

1. 从 [4.1.2 Release](https://github.com/savormundane/Genshin-UGC-plugin/releases/tag/v4.1.2) 下载 `Genshin-UGC-4.1.2-windows-x64.zip`。请在 Release 附件中选择完整包，`Source code` 提供源码。
2. 从 [Release 附件信息](https://docs.github.com/en/rest/releases/assets)取得 ZIP 的 SHA-256，用 `Get-FileHash -Algorithm SHA256` 核对本地文件。
3. 解压 ZIP。包含根目录客户端入口的包可直接从解压后的 `Genshin-UGC` [目录导入](#从本地目录导入)。如需安装器协助登记，可在解压目录运行下方命令，按客户端选用 `-Agent codex`、`claude-code`、`deepseek-harness` 或 `agent-plugins`。

```powershell
.\install.ps1 -Agent codex -Archive ..\Genshin-UGC-4.1.2-windows-x64.zip -Sha256 '<GitHub 显示的 ZIP SHA-256>'
```

## 回退与卸载

- **市场安装和直装**通过客户端管理更新和卸载。需要更换依赖时，启动器会交给 uv。
- **PowerShell 登记的 Codex 和 Claude**可从新版安装器升级。回退或卸载可用完整 ZIP 内的命令。改用 `-Agent claude-code` 即可操作 Claude，使用过 `-Root` 的用户应传入原值。
- **本地目录导入**通过客户端管理。升级时导入新目录，回退时重新指向保留的旧版本。

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
| 能看到 Skill，工具未连通 | 确认客户端能找到 `node` 和已有 Python 环境或 `uv`，并允许本地 MCP。旧环境使用过 `-Root` 时，核对 `UGC_PUBLIC_INSTALL_ROOT` 后重启客户端。 |
| Python 依赖不匹配 | 检查 `UGC_PYTHON` 或显式绑定的旧环境。也可取消这两项，交给 uv 按锁文件准备。 |
| 找不到 Python 或目录冲突 | 按[运行要求](compatibility.md#运行要求)检查 Python，必要时用 `-Python` 指定解释器绝对路径。确认[项目和输出目录](#运行依赖与工程目录)互不包含。 |
| 安装中断 | 保留失败目录，用相同参数加 `-Resume` 重跑。Claude 登记后若启用中断，按错误提示核对客户端中的条目。 |
| CLI 正常，客户端无法调用工具 | 检查插件是否启用、MCP 配置是否指向预期的插件目录。 [连接 MCP](runtime-environment.md#连接-mcp-或切换工程) |

仍无法解决时，通过 [Bug 反馈](https://github.com/savormundane/Genshin-UGC-plugin/issues/new?template=bug_report.yml)提供版本、客户端、执行命令和第一条错误信息。可先删去路径、日志和截图中无需公开的内容。
