# 安装、更新与卸载

选择[市场安装](#市场安装)、[CLI 安装](#cli-安装)或[本地安装](#本地安装)。 [支持的协议](compatibility.md#安装协议与客户端) · [运行要求](compatibility.md#运行要求)

[返回首页](../README.md)

## 市场安装

### ChatGPT/Codex

在提供 Codex 插件目录的客户端中打开「插件」，选择 **Miliastra Wonderland** 市场并安装。需要先登记 GitHub 市场时，运行 [Codex CLI](#codex-cli) 中的第一条命令，然后重新打开插件目录。会话能启动本机 MCP 时即可[验证工具](#首次工具验证)。 [ChatGPT 插件说明](https://learn.chatgpt.com/docs/plugins)

### Claude

在「自定义 → 插件 → 添加市场」选择从仓库添加，输入 `savormundane/miliastra-wonderland-plugin`，然后安装 **Miliastra Wonderland**。组织账号若限制可添加的市场，由管理员在插件设置中开放。Chat 可使用 Skill，调用本地文件工具时请使用能连接本机的 Cowork 会话或 [Claude Code](#claude-code)。 [Claude 插件市场](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) · [Claude 插件能力范围](https://claude.com/docs/plugins/platform-support)

### DeepSeek Harness

在「插件 → 添加插件」的「包名或地址」中输入 npm 包名。安装完成后点「立即启用」。

```text
dsh-miliastra-wonderland
```

[npm 包页](https://www.npmjs.com/package/dsh-miliastra-wonderland) · [DSH 运行要求](compatibility.md#运行要求) · [更新方法](#回退与卸载)

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

## 本地安装

### 从本地目录导入

在[本版发行页](https://github.com/savormundane/miliastra-wonderland-plugin/releases/tag/v1.3.1)下载 **Agent Plugins Windows x64 ZIP**。客户端支持导入 ZIP 时直接上传，支持目录导入时解压到独立目录并选择包含 `plugin.json` 的目录。 [Agent Plugins 规范](https://agent-plugins.org/specification)

### 用 PowerShell 安装本地 ZIP

已安装兼容的 Python 和目标客户端时，可在解压目录用 PowerShell 安装并登记。保留原 ZIP，填入它的路径和发行附件公布的 SHA-256。Claude Code 使用 `-Agent claude-code`。安装器会为该版本配置专用 Python 环境，首次准备依赖可能需要联网。 [运行要求](compatibility.md#运行要求)

```powershell
.\install.ps1 -Agent codex -Archive '<ZIP 的绝对路径>' -Sha256 '<SHA-256>'
```

按提示选择已有工程和独立输出目录。安装完成后开启新会话，做[首次工具验证](#首次工具验证)。

## 首次工具验证

启用插件后，在可启动本地 MCP 的会话中发送下面这句话。查询随包资料无需提供工程文件。

> 请使用千星奇域插件查询服务端「创建实体」节点，列出输入和输出端口，并说明它的用途和资料来源。

如果 `nodes_lookup` 找到服务端节点并列出以下端口，说明工具已连通。

- 输入为「流程入」「目标GUID（GUID）」和「单位标签索引列表（整数列表）」。
- 输出为「流程出」。

该节点按 GUID 创建场景中预先布设的实体。`source` 指向随包编译器定义，`port_evidence` 对应 7.1 版官方文档的两项值输入。 [官方《执行节点》](../references/platform/official/节点介绍/执行节点__mhw66orrrfkm.md#2-创建实体)

接下来可跟做[创作者教程](../samples/creator-demos/README.md)。处理关卡或素材时，先[授权工程目录](runtime-environment.md#连接-mcp-或切换工程)。

## 回退与卸载

- **市场安装**在各客户端的插件页管理。市场从登记的来源同步，发行 ZIP 则对应选定版本。更新后开启新会话，确认工具能正常调用。
- **DeepSeek Harness** 可在支持更新的版本中打开插件详情，检查并安装新版。此前通过 GitHub 地址安装的用户，卸载旧条目后用 [npm 包名](#deepseek-harness)重新安装并启用。 [DSH 更新说明](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/client/ui-plugin-manager/README.md#updating-a-registry-bundle)
- **CLI 安装**使用同一客户端的插件命令管理。Codex CLI 可用 `codex plugin marketplace upgrade miliastra-wonderland` 刷新已登记的市场。
- **市场或 CLI 安装**遇到同版本重新发布且客户端仍加载旧缓存时，请按原安装方式卸载并重装。保留现有运行配置，或用 `MILIASTRA_WONDERLAND_RUNTIME_CONFIG` 指定原配置文件，即可继续使用原工程和解释器。
- **PowerShell 登记的 Codex 和 Claude**可从新版安装器升级。回退或卸载可用完整 ZIP 内的命令。改用 `-Agent claude-code` 即可操作 Claude，使用过 `-Root` 的用户应传入原值。
- **本地目录导入**通过客户端管理。升级时导入新目录，回退时重新指向保留的旧版本。

```powershell
# 回退到本机仍保留的版本
.\install.ps1 -Agent codex -Action rollback -Version '<旧版本>'

# 卸载当前登记的安装
.\install.ps1 -Agent codex -Action uninstall
```

当前版本的 Python 无法启动时，回退会尝试目标版本保留的解释器，再查找系统中兼容的 Python。也可以给回退或卸载命令加上 `-Python '<可用 Python 的绝对路径>'`。回退在目标版本的运行环境通过自检后才切换登记。

PowerShell 卸载保留项目、输出和各版本的运行环境。重新启用已保留的同版本时，可复制安装器提示中的回退命令，继续使用原安装文件和运行配置。清理旧版本目录前，确认其他客户端已停用该版本，并且无需回退。

## 安装自检

工具连不上时，在 Windows PowerShell 进入要检查的插件目录。若检查客户端安装的副本，可从 MCP 日志中的 `scripts\mcp_launcher.cjs` 路径找到其上两级目录。用 PowerShell 登记的插件可从[安装记录](runtime-environment.md#复用-powershell-安装器配置的环境)中的 `current.home` 找到 `miliastra-wonderland` 子目录。然后运行以下命令。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-install.ps1
```

能运行 Node 时，也可以直接执行 `node .\scripts\mcp_launcher.cjs --check`。

自检会核对启动文件、Node.js、现有 Python 的版本和依赖，以及 PATH 上的 uv。如果结果只有 uv 可用，可先[准备 Python 环境](runtime-environment.md#提前准备-python-环境)。处理报告指出的问题后，重启客户端并[验证工具](#首次工具验证)。

自检使用当前终端的 PATH 和环境变量。客户端单独配置了 Python 或运行绑定文件时，在自检终端使用同样的值。 [解释器选择](runtime-environment.md#启动时选择-python)

## 失败后续装

| 遇到的问题 | 适用安装方式 | 下一步 |
| --- | --- | --- |
| 市场中找不到插件 | ChatGPT/Codex 或 Claude | 核对仓库名和插件 ID，确认市场已导入。 [市场安装](#市场安装) |
| Claude 市场验证失败 | Claude | 查看市场的「同步错误详情」。可临时使用 [Claude Code](#claude-code) 安装并调用本地工具。 |
| 添加 DeepSeek Harness 插件时报错 | DeepSeek Harness | 核对 [npm 包名](#deepseek-harness)和 DSH 版本。 |
| Claude Chat 里有 Skill，调用不到节点查询 | Claude | 在 Cowork 新建任务并允许本地工具，再做[首次工具验证](#首次工具验证)。 |
| 能看到 Skill，工具未连通 | 所有安装方式 | 确认插件已启用并允许本地 MCP，运行[安装自检](#安装自检)。 |
| MCP 首次启动超时，或缺少 Python 依赖 | 所有安装方式 | 先在终端[准备 Python 环境](runtime-environment.md#提前准备-python-环境)，再打开客户端。若仍超时，核对[客户端时限](mcp.md#调整客户端超时)。 |
| 安装器找不到 Python，或提示工程与输出路径冲突 | 用 [PowerShell 安装本地 ZIP](#用-powershell-安装本地-zip) | 缺少 Python 时，给原安装命令加 `-Python '<解释器绝对路径>'`。目录冲突时，为 `-Project` 和 `-Outputs` 选择互不包含的目录。 |
| 安装准备中断 | 用 [PowerShell 安装本地 ZIP](#用-powershell-安装本地-zip) | 保留未完成的安装目录。按报错修复后，用同一安装命令加 `-Resume` 重跑。已进入 Claude 登记时，按错误提示核对客户端中的条目。 |
| 工程目录未绑定，或找不到输入文件 | 所有安装方式 | 打开包含输入的本地工程并授权，或按[工程绑定说明](runtime-environment.md#连接-mcp-或切换工程)配置目录。核对输入文件的路径和扩展名。 |
| 输出目录已存在 | 所有安装方式 | 在独立输出根目录下，给本次输出取一个尚未使用的目录名。 |
| 无法识别千星奇域版本 | 所有安装方式 | 核对游戏内版本和报错列出的已收录版本。目标版本尚未收录时，可附版本号和资料来源反馈。 |
| CLI 正常，客户端无法调用工具 | 所有安装方式 | 确认插件已启用，并核对 MCP 配置是否指向自检通过的插件目录。 [连接 MCP](runtime-environment.md#连接-mcp-或切换工程) |

仍无法解决时，附上自检失败环节和原始错误。 [提交 Bug 反馈](https://github.com/savormundane/miliastra-wonderland-plugin/issues/new?template=bug_report.yml) · [报告问题指引](../CONTRIBUTING.md)
