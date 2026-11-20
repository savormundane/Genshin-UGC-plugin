# 完整安装、回退与手动接入

安装包保留五个 Skill 共同使用的根目录。不要只复制 `skills/`；共享 references、scripts、vendor 和运行工具也是输入。

## 自动安装

使用根 README 的 PowerShell 命令。参数：`-Agent codex|claude-code|agent-plugins|deepseek-harness`、`-Version x.y.z`、`-Project`、`-Outputs`、`-Python`、`-Root`。默认安装根为当前用户 LocalAppData 下的 `Genshin-UGC-Public`。

基础环境要求 Windows x64、Python 3.11–3.12 和 Node.js 22+。DeepSeek Harness `0.2.2-rc.5` 需要 Node.js 24.9 或以上。Codex 和 Claude Code 的自动注册需要相应 CLI。专用环境依据 `scripts/runtime-requirements.lock` 安装；首次需要联网。缺依赖会明确退出，不自动改变系统 Python、Node 或其他插件。

项目必须存在，输出目录必须与其分离。安装器为每个客户端和版本创建独立完整目录、Python 环境与 runtime.json，通过 MCP 描述的 `UGC_RUNTIME_CONFIG` 显式绑定。它不使用已有自用环境的默认 runtime.json。

安装或准备时执行本地 MCP 工具发现、两个 API 查询和随包模拟器 PNG 检查。Codex 和 Claude Code 之后调用原生 marketplace 与 plugin 命令。其他入口标记为 `pending_host_registration`。宿主加载与对话调用需要在实际客户端验证；安装器检查不涵盖游戏编辑器和实机。

## 宿主原生注册

- **Agent Plugins 1.0.0** — 执行 `-Agent agent-plugins`。在支持该标准和 stdio 的宿主中导入返回的 `plugin_directory`，例如在 VS Code 的 Agent Customizations 中选择从本地目录安装，再用 Copilot harness 启用插件。保持安装目录可读，重新打开会话确认五个 Skills 和 MCP。直接导入未经准备的 ZIP 解包目录时，根 `mcp.json` 会读取宿主分配的 `${PLUGIN_DATA}/runtime.json`；可用 `scripts/configure_runtime.py` 显式创建该配置。
- **DeepSeek Harness Cordis** — 执行 `-Agent deepseek-harness`。打开目标 profile 的 Plugins → Add plugin，选择返回的 `bundle_directory`。Bundle 使用同一安装中的五个 Skills 和 stdio 程序；保留 `plugin_directory` 和其旁边的专用环境。应用完成后，在支持 Skills 的会话中检查五个入口并调用 `mcp__genshin_ugc__doctor`。若宿主显示需重启，重启该 profile 再验证。
- **Claude Code Plugin** — 使用 `-Agent claude-code` 自动准备并注册，或用 Claude Code 加载已配置的目录。根 `.mcp.json` 使用 `${CLAUDE_PLUGIN_ROOT}` 定位启动器；手动接入时可把显式配置写到该客户端为插件分配的 `${CLAUDE_PLUGIN_DATA}/runtime.json`。可以用 `claude plugin validate <目录>` 检查元数据和 MCP 声明。

新增两种准备模式由宿主管理启用、禁用和回退。升级时选择新的版本目录或 Bundle，确认其可用后再移除旧注册；已准备完成的目录拒绝覆盖，未完成时可用原参数和 `-Resume` 恢复。安装器不编辑 VS Code 设置或 Harness profile。

## 回退与卸载

Codex 和 Claude Code 可使用完整 ZIP 中的 install.ps1，或解压后直接运行 `scripts/install_public.py`。回退只接受安装器历史中保留的版本，先复查运行环境，再切换注册。

```powershell
python -X utf8 -B .\scripts\install_public.py rollback --agent codex --root "$env:LOCALAPPDATA\Genshin-UGC-Public" --version 4.0.0
python -X utf8 -B .\scripts\install_public.py uninstall --agent codex --root "$env:LOCALAPPDATA\Genshin-UGC-Public" --version 4.0.0
```

卸载仅撤销该安装器记录的插件和 marketplace 注册，保留版本目录及专用环境用于回退。确认不再需要后，可手动删除安装根；项目和输出目录不是插件缓存，不随卸载删除。不要手动删除客户端的其他插件缓存。

依赖或运行检查失败时会保留失败目录。使用原参数加 `-Resume` 恢复安装准备。客户端注册失败时会尝试移除本次新增注册；若客户端本身无法完成清理，按错误信息在其插件管理界面移除本次条目，旧版本目录仍保留。

## 手动接入

1. 从对应 Release 下载完整 Windows ZIP，在附件详情或 [Release API](https://docs.github.com/en/rest/releases/assets) 读取该 ZIP 的 `sha256:` 摘要。用 `Get-FileHash -Algorithm SHA256` 核对后解压。
2. 按[运行环境](runtime-environment.md)调用 `scripts/configure_runtime.py`，传入专用 Python 环境路径、项目、输出和独立 config 路径。
3. 为本插件 MCP 显式设置 `UGC_RUNTIME_CONFIG` 指向该 config，使用 Node 调用 `scripts/mcp_launcher.cjs`。
4. 按[宿主原生注册](#宿主原生注册)导入完整目录或 Cordis Bundle。Codex 使用 `.codex-plugin/plugin.json` 和 `mcp.json`，Agent Plugins 使用根 `plugin.json` 和 `mcp.json`，Claude Code 使用 `.claude-plugin/plugin.json` 和 `.mcp.json`。DeepSeek Harness 从准备模式生成的 Bundle 读取 Skills 路径与 stdio 配置。

无法接入插件的客户端仍可使用完整目录中的 CLI；不把这称为该客户端已完整兼容。

## 适配依据

- Codex：安装时核对本机 `codex plugin --help`、`plugin marketplace add --help` 与 `plugin add --help`。
- Agent Plugins：[1.0.0 规范](https://agent-plugins.org/specification)。
- DeepSeek Harness：[Cordis Bundle](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.2-rc.5/packages/preset/agent-preset/skills/dsh-doc/references/host-plugin.md)。
- Claude Code：[插件清单](https://code.claude.com/docs/en/plugins-reference)、[本地 marketplace](https://code.claude.com/docs/en/plugin-marketplaces)。
- README 与安装体验参考：[Vercel Skills](https://github.com/vercel-labs/skills)、[Superpowers](https://github.com/obra/superpowers)、[Anthropic Skills](https://github.com/anthropics/skills)。仅参考组织方式，没有复制其实现或承诺全客户端兼容。

## 失败后续装

保留失败目录，以相同版本、ZIP 摘要、客户端和安装及输入输出目录参数加 `-Resume`（Python 入口为 `--resume`）。四种入口均可恢复依赖安装和启动检查阶段。Codex 还可恢复安装器已登记的激活阶段。续装会核对候选文件、安装器生成的配置及实际 marketplace 来源，复用能确认归属的注册。新版启用且安装记录写入成功后，才清理旧版注册并保留其目录用于回退。

如输出提示来源不同、查询失败或清理失败，请按提示核对该版本的 Codex 注册后重试同一命令。已完成安装的版本应使用回退或新版本目录。Claude Code 的激活中断保留人工恢复方式。依赖安装采用 `--require-hashes --only-binary=:all:`。SHA-256 可验证下载内容一致性。
