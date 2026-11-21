# 安装、更新与卸载

完整工具包面向 **Windows x64**，需提前安装 **Python 3.11 或 3.12** 和 **Node.js 22+**（DeepSeek Harness 需 **Node.js 24.9+**）。首次安装需要联网拉取锁定的 Python 依赖。

安装时会提示输入两个目录（也可通过 `-Project`、`-Outputs` 参数传入）：
* **现有千星奇域项目目录**（读取输入用）
* **独立输出目录**（保存报告与生成文件，必须与项目目录互不包含）

如果 Python 未加入 PATH 或命中了商店占位符，用 `-Python` 指定真实解释器路径。默认安装根目录为 `$env:LOCALAPPDATA\Genshin-UGC-Public`（可用 `-Root` 修改）。

## 客户端与 `-Agent` 参数速查

| 客户端 | `-Agent` 参数 | 安装后操作 |
| --- | --- | --- |
| **Codex** | `codex` | 自动注册，新开会话确认已启用 |
| **Claude Code** | `claude-code` | 自动注册，新开会话在 `/plugin` 确认 |
| **DeepSeek Harness**（`0.2.2-rc.5`） | `deepseek-harness` | 记下 `bundle_directory`，在客户端添加插件目录（需 Node 24.9+） |
| **VS Code / Cursor / Copilot CLI / Kiro / Antigravity / 通用客户端** | `agent-plugins` | 记下 `plugin_directory`，按下方对应客户端导入 |

## Codex

确认 `codex` 命令可用后，在 PowerShell 运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent codex
```

完成后打开新会话，在插件列表确认 Genshin-UGC 已启用，再试 [README 中的例子](../README.md#首次使用)。

## Claude Code

确认 `claude` 命令可用后，在 PowerShell 运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent claude-code
```

打开新会话，在 `/plugin` 中确认插件已启用，试一次 API 查询确认本地工具连通。

## DeepSeek Harness

需要适配版本 DeepSeek Harness `0.2.2-rc.5` 和 **Node.js 24.9+**。

1. 在 PowerShell 运行准备命令，记下输出中的 `bundle_directory` 路径：

   ```powershell
   & ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent deepseek-harness
   ```

2. 在目标配置中打开 **Plugins → Add plugin**，粘贴刚才的目录路径。
3. 启用插件后开启新会话并试一次 API 查询；若客户端提示重启，重启后再试。

## 其他客户端

客户端能识别这类本地插件，并能在本机 Windows 会话中运行本地工具时，可以尝试复用同一份安装包。先在 PowerShell 运行准备命令：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent agent-plugins
```

记下输出的 `plugin_directory`，并**保留该目录旁边的运行环境目录**。接下来按所用客户端导入：

### VS Code

1. 打开命令面板运行 **Chat: Open Customizations**，切换到 **Plugins**。
2. 点击 **User** 或 **Workspace** 旁的 **+**，填入刚才的 `plugin_directory`。
3. 用 Copilot 开启新会话，确认插件已启用并试一次 API 查询。参考 [VS Code 本地插件安装说明](https://code.visualstudio.com/docs/agent-customization/agent-plugins#install-a-plugin-from-source)。

### 更多本地导入方式

* **GitHub Copilot CLI**：运行 `copilot plugin install "<plugin_directory>"`（参考 [Copilot CLI 插件文档](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating#test-your-plugin-with-github-copilot-cli)）。
* **Kiro**：在 Powers 面板选择 **Add Custom Power → Import power from a folder**，选中 `plugin_directory`（参考 [Kiro 本地安装说明](https://kiro.dev/docs/powers/installation/#from-local-path)）。
* **Google Antigravity CLI**：运行 `agy plugin install "<plugin_directory>"`（参考 [Antigravity 文档](https://antigravity.google/docs/marketplace)）。
* **Cursor**（需客户端允许本地插件导入，参考 [Cursor 插件说明](https://cursor.com/docs/plugins#test-plugins-locally)）：
  1. 将完整的 `plugin_directory` 复制到 `~/.cursor/plugins/local/` 下。
  2. 打开副本里的 `mcp.json`，将启动参数中的 `${PLUGIN_ROOT}` 改为 `${CURSOR_PLUGIN_ROOT}`，保留安装器写入的运行配置路径。
  3. 重载 Cursor。

导入后均需开启新会话并试一次 API 查询，以实际能发现技能和调用本地工具为准；升级或卸载通过对应客户端管理。

### 通用客户端

1. 先运行上方的 `-Agent agent-plugins` 准备命令，获取 `plugin_directory` 与配套运行环境。
2. 在客户端的「从本地目录安装插件」入口选中 `plugin_directory`（兼容列表可参考 [Agent Plugins 客户端目录](https://agent-plugins.org/compatible-clients)）。
3. 打开新会话，确认能看到 5 个 Skill，并让助手查询一个千星奇域 API 验证本地 MCP 工具可用。

如果客户端只加载了 Skill 但支持手动配本地 MCP，可按 [客户端适配](../docs/development.md#客户端适配) 补充配置；只需要命令行时，直接按 [独立运行环境](runtime-environment.md) 配置即可。

## 手动接入

如果想先下载包再本地核对安装：

1. 前往 [4.1.0 Release 页面](https://github.com/savormundane/Genshin-UGC-plugin/releases/tag/v4.1.0) 下载 `Genshin-UGC-4.1.0-windows-x64.zip`。
2. 在 GitHub Release 附件详情（或 [Release API](https://docs.github.com/en/rest/releases/assets)）查看该 ZIP 的 SHA-256，本机用 `Get-FileHash -Algorithm SHA256` 核对一致。
3. 保留原 ZIP，将其解压到同一父目录，进入解压出的 `Genshin-UGC` 目录运行（按需替换 `-Agent` 值）：

   ```powershell
   .\install.ps1 -Agent codex -Archive ..\Genshin-UGC-4.1.0-windows-x64.zip -Sha256 '<GitHub 显示的 ZIP SHA-256>'
   ```

只使用命令行工具见 [独立运行环境](runtime-environment.md)；自建客户端适配见 [客户端适配](../docs/development.md#客户端适配)。

## 回退与卸载

升级直接运行新版本的安装命令即可，各版本使用独立目录，互不覆盖。

**Codex 与 Claude Code** 可用完整 ZIP 内的 `install.ps1` 离线回退或卸载。将 `-Agent` 换成所用客户端，安装时若传过 `-Root`，这里传入原值。回退时用 `-Version` 选择仍保留的版本。卸载移除所选客户端当前登记的安装。

```powershell
# 回退到之前保留的某个版本
.\install.ps1 -Agent codex -Action rollback -Version 4.0.0

# 卸载所选客户端的当前安装
.\install.ps1 -Agent codex -Action uninstall
```

卸载保留项目、输出、版本目录和专用运行环境。同一安装根可以供多个客户端使用。清理旧文件前，请在对应客户端确认该版本已移除、没有其他客户端在用，也无需留作回退，再清理该客户端下对应的版本目录。

**DeepSeek Harness 与其他自行导入的客户端**：在对应客户端的插件管理界面移除或禁用。升级时先准备并验证新版，再移除旧版；回退时重新指向之前保留的旧版目录即可。

## 失败后续装

* **找不到 Python**：安装 Python 3.11 或 3.12，或直接用 `-Python` 指定真实 `python.exe` 路径。
* **安装中断**：保留失败目录，用完全相同的参数加上 `-Resume` 重跑即可。Codex 与 Claude Code 均支持依赖与冒烟检查阶段续装；Codex 还支持已登记的激活阶段续装。若提示版本已安装完成，请改用上方回退流程。Claude Code 若在启用阶段中断，按错误提示核对插件列表中的条目后再试。
* **客户端看不到工具**：新开会话检查插件是否已启用；如客户端弹出本地工具信任确认，核对后批准。手动导入时确保选的是准备命令输出的目录（或 Cursor 修改后的副本）。
* **产物已生成但需核对游戏内效果**：按 [运行要求与验证](../docs/compatibility.md) 导入千星奇域编辑器并进游戏试运行。
