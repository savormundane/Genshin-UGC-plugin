# 安装、更新与卸载

完整工具包适用于 Windows x64，需要 Python 3.11 或 3.12 和 Node.js 22 或更新版本。DeepSeek Harness 有单独的 Node.js 要求。首次安装需要联网。

安装时请选择已存在的千星奇域项目目录，以及一个与项目目录互不包含的输出目录。也可通过 `-Project` 和 `-Outputs` 指定路径。Python 若未加入 PATH，使用 `-Python` 指定解释器路径。默认安装位置为 `$env:LOCALAPPDATA\Genshin-UGC-Public`。

## Codex

确认 `codex` 命令可用，在 PowerShell 中运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent codex
```

安装完成后打开新会话，在插件列表中确认 Genshin-UGC 已启用，然后尝试 [README 中的例子](../README.md#首次使用)。

## Claude Code

确认 `claude` 命令可用，在 PowerShell 中运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent claude-code
```

打开 Claude Code 的新会话，在 `/plugin` 中确认插件已启用，再试一次 API 查询。

## DeepSeek Harness

使用适配的 DeepSeek Harness `0.2.2-rc.5` 和 Node.js 24.9 或更新版本。

1. 在 PowerShell 中运行以下命令，记下输出中 `bundle_directory` 对应的路径。

   ```powershell
   & ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent deepseek-harness
   ```
2. 在要使用的 DeepSeek Harness 配置中打开 **Plugins → Add plugin**，粘贴刚才的目录路径。
3. 启用插件后打开新会话，并试一次 API 查询。若客户端提示重启，重启后再试。

## 其他客户端

如果你的客户端可以导入本地插件，并能在当前 Windows 会话中运行本地工具，可以复用同一份安装包。先在 PowerShell 中准备插件：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent agent-plugins
```

记下输出的 `plugin_directory`，保留该目录旁的运行环境。接下来按所用客户端导入这个目录。

### VS Code

在 VS Code 命令面板运行 **Chat: Open Customizations**，选择 **Plugins**，点 **User** 或 **Workspace** 旁的 **+**，填入刚才的本地目录。用 Copilot 开启新会话，确认插件已启用并尝试一次 API 查询。[VS Code 的本地插件安装说明](https://code.visualstudio.com/docs/agent-customization/agent-plugins#install-a-plugin-from-source)

### 更多本地导入方式

- **GitHub Copilot CLI**　运行 `copilot plugin install "上一步输出的目录"`。[本地安装与检查](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating#test-your-plugin-with-github-copilot-cli)
- **Kiro**　在 Powers 面板选择 **Add Custom Power → Import power from a folder**，选择该目录。[Kiro 本地安装说明](https://kiro.dev/docs/powers/installation/#from-local-path)
- **Google Antigravity CLI**　运行 `agy plugin install "上一步输出的目录"`。[Antigravity 安装说明](https://antigravity.google/docs/marketplace)
- **Cursor**　把准备好的完整插件目录复制到 `~/.cursor/plugins/local/` 下。在副本的 `mcp.json` 中，把启动参数里的 `${PLUGIN_ROOT}` 改成 `${CURSOR_PLUGIN_ROOT}`，保留安装器写入的运行配置路径，再重载 Cursor。客户端需要允许本地插件导入。[Cursor 本地插件说明](https://cursor.com/docs/plugins#test-plugins-locally)
导入后打开新会话，试一次 API 查询，以实际能发现技能和调用本地工具为准。升级或卸载通过对应客户端管理。

### 通用客户端

1. 先运行[上面的准备命令](#其他客户端)，拿到完整插件目录和其中工具所需的运行环境。
2. 在你的客户端找「从本地目录安装插件」或等效功能，选择命令输出的 `plugin_directory`。若不确定客户端能加载什么，可以查[标准的客户端目录](https://agent-plugins.org/compatible-clients)或客户端自己的文档。
3. 打开新会话，确认能看到 Genshin-UGC 的技能，再让助手查询一个千星奇域 API，检查它能否调用本地工具。

如果客户端导入后只显示技能，但支持自行配置本地工具，可以按[手动配置](../docs/development.md#客户端适配)添加。只有终端或仅在远程运行时，可在 Windows 本机[单独使用命令行工具](runtime-environment.md)。

## 手动接入

1. 从 [4.0.0 下载页](https://github.com/savormundane/Genshin-UGC-plugin/releases/tag/v4.0.0)下载 `Genshin-UGC-4.0.0-windows-x64.zip`。安装器要求完整安装 ZIP，请在附件中选择这个文件。
2. 从 GitHub 的附件详情或 [Release API](https://docs.github.com/en/rest/releases/assets)取得 ZIP 的 SHA-256，用 `Get-FileHash -Algorithm SHA256` 核对。
3. 保留原 ZIP，解压到同一父目录，并在解压出的 `Genshin-UGC` 目录运行下面的命令。将 `-Agent` 改成相应客户端小节中给出的值。

   ```powershell
   .\install.ps1 -Agent codex -Archive ..\Genshin-UGC-4.0.0-windows-x64.zip -Sha256 '<GitHub 提供的 ZIP SHA-256>'
   ```

只使用命令行工具时，可按[独立运行环境](runtime-environment.md)配置。自建客户端接入见[开发者参考](../docs/development.md#客户端适配)。

## 回退与卸载

更新时使用新版本的安装命令。各版本使用独立目录。

Codex 和 Claude Code 可使用完整 ZIP 中的 `install.ps1` 执行回退或卸载。回退请选择曾由安装器安装且仍保留的版本。将示例中的版本、客户端和安装位置换成你要操作的目标：

```powershell
.\install.ps1 -Agent codex -Action rollback -Version 4.0.0
.\install.ps1 -Agent codex -Action uninstall -Version 4.0.0
```

若安装时传过 `-Root`，这里也要传入原值。卸载保留版本目录和专用环境以便回退。项目和输出目录保留。

DeepSeek Harness 与自行导入的其他客户端在自己的插件管理界面中移除或禁用插件。更新时先按对应步骤准备新版并确认可用，再在客户端移除旧版。回退时在客户端选择之前保留的目录。

## 失败后续装

- **找不到 Python**　安装 Python 3.11 或 3.12，或用 `-Python` 指定可执行文件。
- **安装中断**　保留失败目录，在原命令上加 `-Resume`，保持版本、安装包及其他参数相同。若提示现有版本已安装完成，请按回退步骤处理。Codex 可继续安装器已记录的启用步骤。Claude Code 若提示上次启用未完成，请按错误信息在客户端插件列表处理后再试。
- **客户端找不到工具**　打开新会话，检查插件是否已启用。若客户端要求批准本地工具，按界面提示检查后再启用。自行导入时，请用安装命令给出的目录，或按对应客户端说明使用准备好的副本。
- **文件已生成，需要确认游戏内效果**　按[运行要求与验证说明](../docs/compatibility.md)在千星奇域编辑器导入并试运行。
