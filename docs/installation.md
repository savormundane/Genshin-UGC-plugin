# 安装、更新与卸载

选择[市场安装](#市场安装)、[CLI 安装](#cli-安装)或[本地安装](#本地安装)。 [支持的协议](compatibility.md#安装协议与客户端) · [运行要求](compatibility.md#运行要求)

[返回首页](../README.md)

## 市场安装

### ChatGPT/Codex

参见[首页安装说明](../README.md#安装)或 [Codex CLI 安装](#codex-cli)。

### Claude

在「自定义 → 插件 → 添加市场」选择从仓库添加，输入 `savormundane/miliastra-wonderland-plugin`，然后安装 **Miliastra Wonderland**。 [Claude 插件市场](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)

### DeepSeek Harness

在「插件 → 添加插件」的「包名或地址」中粘贴仓库地址。安装完成后点「立即启用」。

```text
https://github.com/savormundane/miliastra-wonderland-plugin
```

此方式从仓库默认分支安装。支持的 DSH 版本见 [`package.json` 中的 `engines.dsh`](https://github.com/savormundane/miliastra-wonderland-plugin/blob/main/package.json)。

### Agent Plugins

在支持 GitHub 市场的客户端添加 `savormundane/miliastra-wonderland-plugin`，安装 `miliastra-wonderland`。也可使用[本地安装](#本地安装)。

## CLI 安装

### Codex CLI

在终端登记市场并安装。

```powershell
codex plugin marketplace add savormundane/miliastra-wonderland-plugin
codex plugin add miliastra-wonderland@miliastra-wonderland
```

用 `codex plugin list` 确认已启用，再运行 `codex` 开启会话。 [Codex CLI 插件命令](https://learn.chatgpt.com/docs/developer-commands)

### Claude Code

在终端登记市场并安装。

```powershell
claude plugin marketplace add savormundane/miliastra-wonderland-plugin
claude plugin install miliastra-wonderland@miliastra-wonderland
```

也可在 Claude Code 会话里运行下面两条命令。

```text
/plugin marketplace add savormundane/miliastra-wonderland-plugin
/plugin install miliastra-wonderland@miliastra-wonderland
```

运行 `claude plugin list` 查看启用状态，然后开启新会话。 [Claude Code 插件说明](https://code.claude.com/docs/en/plugins/install)

### DeepSeek Harness 命令行

在终端将插件安装到 DSH 的 Web 配置。

```powershell
dsh plugin --profile web add https://github.com/savormundane/miliastra-wonderland-plugin
```

## 本地安装

### 从本地目录导入

在[本版发行页](https://github.com/savormundane/miliastra-wonderland-plugin/releases/tag/v1.2.0)下载 **Agent Plugins Windows x64 ZIP**。客户端支持导入 ZIP 时直接上传，支持目录导入时解压到独立目录并选择包含 `plugin.json` 的目录。 [Agent Plugins 规范](https://agent-plugins.org/specification)

### 用 PowerShell 安装本地 ZIP

要用安装器为 Codex 或 Claude Code 登记本地运行环境，在解压目录的 PowerShell 中运行以下命令。保留原 ZIP，填入其路径和 GitHub 发行附件的 SHA-256。Claude Code 使用 `-Agent claude-code`。

```powershell
.\install.ps1 -Agent codex -Archive '<ZIP 的绝对路径>' -Sha256 '<SHA-256>'
```

按提示选择已有工程和独立输出目录。安装完成后开启新会话，做[首次工具验证](#首次工具验证)。

## 首次工具验证

启用插件后，在支持本地 MCP 的会话中[查询「创建实体」](../README.md#作为知识库使用)。如果 `nodes_lookup` 找到一条服务端节点记录并列出以下端口，说明工具已连通。

- 输入为「流程入」「目标GUID（GUID）」和「单位标签索引列表（整数列表）」。
- 输出为「流程出」。

该节点按 GUID 创建场景中预先布设的实体。`source` 指向随包编译器定义，`port_evidence` 对应 7.1 版官方文档的两项值输入。 [官方《执行节点》](../references/platform/official/节点介绍/执行节点__mhw66orrrfkm.md#2-创建实体)

Claude 的 Chat 可使用 Skill。本地 MCP 在 Cowork 或 Claude Code 中验证。 [Claude 本地工具支持](https://support.claude.com/en/articles/13837440-use-plugins-in-claude)

处理关卡或素材时，在客户端打开并授权工程目录。[工程绑定](runtime-environment.md#连接-mcp-或切换工程)

## 回退与卸载

- **市场安装**在各客户端的插件页管理。更新后开启新会话，确认工具能正常调用。
- **CLI 安装**使用同一客户端的插件命令管理。Codex CLI 可用 `codex plugin marketplace upgrade miliastra-wonderland` 刷新已登记的市场。
- **同版本重新发布**后，若客户端仍加载旧缓存，请按原安装方式卸载并重装。保留现有运行配置，或用 `MILIASTRA_WONDERLAND_RUNTIME_CONFIG` 指定原配置文件，即可继续使用原工程和解释器。
- **PowerShell 登记的 Codex 和 Claude**可从新版安装器升级。回退或卸载可用完整 ZIP 内的命令。改用 `-Agent claude-code` 即可操作 Claude，使用过 `-Root` 的用户应传入原值。
- **本地目录导入**通过客户端管理。升级时导入新目录，回退时重新指向保留的旧版本。

```powershell
# 回退到本机仍保留的版本
.\install.ps1 -Agent codex -Action rollback -Version '<旧版本>'

# 卸载当前登记的安装
.\install.ps1 -Agent codex -Action uninstall
```

当前版本的 Python 无法启动时，回退会尝试目标版本保留的解释器，再查找系统中兼容的 Python。也可以给回退或卸载命令加上 `-Python '<可用 Python 的绝对路径>'`。回退在目标版本的运行环境通过自检后才切换登记。

卸载保留项目、输出和各版本的运行环境。清理旧版本目录前，确认其他客户端已停用该版本，并且无需回退。

## 安装自检

工具连不上时，在 Windows PowerShell 进入要检查的插件目录。若检查客户端安装的副本，可从 MCP 日志中的 `scripts\mcp_launcher.cjs` 路径找到其上两级目录。用 PowerShell 登记的插件可从[安装记录](runtime-environment.md#复用-powershell-安装器配置的环境)中的 `current.home` 找到 `miliastra-wonderland` 子目录。然后运行以下命令。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-install.ps1
```

能运行 Node 时，也可以直接执行 `node .\scripts\mcp_launcher.cjs --check`。

自检会核对启动文件、Node.js、现有 Python 的版本和依赖，以及 PATH 上的 uv。处理报告指出的问题后，重启客户端并[验证工具](#首次工具验证)。 [解释器选择](runtime-environment.md#启动时选择-python)

自检读取当前终端的 PATH、`MILIASTRA_WONDERLAND_PYTHON` 和 `MILIASTRA_WONDERLAND_RUNTIME_CONFIG` 等环境变量。客户端单独配置了解释器或绑定文件时，把同样的值设置到自检终端。使用 WinGet 的用户可运行 `winget install --id=astral-sh.uv -e` 安装 uv，再打开新终端检查 `uv --version`。 [uv 的 WinGet 安装说明](https://docs.astral.sh/uv/getting-started/installation/#winget)

## 失败后续装

| 遇到的问题 | 适用安装方式 | 下一步 |
| --- | --- | --- |
| 市场中找不到插件 | ChatGPT/Codex 或 Claude | 核对仓库名和插件 ID，确认市场已导入。 [市场安装](#市场安装) |
| 添加市场时 Claude 报错 | Claude 或 Claude Code | 用仓库根地址重试。若看到组织限制提示，核对允许的市场来源。Claude Code 可对同一份已解压源码运行 `claude plugin validate .`，定位具体清单或路径。 |
| 添加 DeepSeek Harness 插件时报错 | DeepSeek Harness | 使用完整的 [GitHub 仓库地址](#deepseek-harness)，并核对 DSH 版本。 |
| Claude Chat 里有 Skill，调用不到节点查询 | Claude | 在 Cowork 新建任务并允许本地工具，再做[首次工具验证](#首次工具验证)。 |
| 能看到 Skill，工具未连通 | 所有安装方式 | 确认插件已启用并允许本地 MCP，运行[安装自检](#安装自检)。 |
| MCP 启动时缺少 Python 或依赖 | 所有安装方式 | 让客户端在 PATH 上能找到 uv，再重新打开客户端。已有专用 Python 时，可用[运行绑定](runtime-environment.md#桌面端首次绑定本机工程)指定解释器。 |
| 安装器找不到 Python，或提示工程与输出路径冲突 | 用 [PowerShell 安装本地 ZIP](#用-powershell-安装本地-zip) | 缺少 Python 时，给原安装命令加 `-Python '<解释器绝对路径>'`。目录冲突时，为 `-Project` 和 `-Outputs` 选择互不包含的目录。 |
| 安装准备中断 | 用 [PowerShell 安装本地 ZIP](#用-powershell-安装本地-zip) | 保留未完成的安装目录。按报错修复后，用同一安装命令加 `-Resume` 重跑。已进入 Claude 登记时，按错误提示核对客户端中的条目。 |
| 工程目录未绑定，或找不到输入文件 | 所有安装方式 | 打开包含输入的本地工程并授权，或按[工程绑定说明](runtime-environment.md#连接-mcp-或切换工程)配置目录。核对输入文件的路径和扩展名。 |
| 输出目录已存在 | 所有安装方式 | 在独立输出根目录下，给本次输出取一个尚未使用的目录名。 |
| 无法识别千星奇域版本 | 所有安装方式 | 核对游戏内版本和报错列出的已收录版本。目标版本尚未收录时，可附版本号和资料来源反馈。 |
| CLI 正常，客户端无法调用工具 | 所有安装方式 | 确认插件已启用，并核对 MCP 配置是否指向自检通过的插件目录。 [连接 MCP](runtime-environment.md#连接-mcp-或切换工程) |

仍无法解决时，附上自检失败环节和原始错误。 [提交 Bug 反馈](https://github.com/savormundane/miliastra-wonderland-plugin/issues/new?template=bug_report.yml) · [报告问题指引](../CONTRIBUTING.md)
