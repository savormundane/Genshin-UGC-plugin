# 完整安装、回退与手动接入

安装包保留五个 Skill 共同使用的根目录。不要只复制 `skills/`；共享 references、scripts、vendor 和运行工具也是输入。

## 自动安装

使用根 README 的 PowerShell 命令。参数：`-Agent codex|claude-code`、`-Version x.y.z`、`-Project`、`-Outputs`、`-Python`、`-Root`。默认安装根为当前用户 LocalAppData 下的 `Genshin-UGC-Public`。

基础环境要求 Windows x64、Python 3.11–3.12、Node.js 22+ 和支持插件命令的客户端。专用环境依据 `scripts/runtime-requirements.lock` 安装；首次需要联网。缺依赖会明确退出，不自动改变系统 Python、Node 或其他插件。

项目必须存在，输出目录必须与其分离。安装器为每个客户端和版本创建独立完整目录、Python 环境与 runtime.json，通过 MCP 描述的 `UGC_RUNTIME_CONFIG` 显式绑定。它不使用已有自用环境的默认 runtime.json。

安装前执行本地 MCP 工具发现、两个 API 查询和随包模拟器 PNG 检查。之后调用客户端原生 marketplace 与 plugin 命令。客户端重启后的技能加载、MCP 信任和实际对话调用仍需在客户端确认；游戏编辑器与实机不在安装器检查范围内。

## 回退与卸载

使用已下载的 install.ps1，或解压后直接运行 `scripts/install_public.py`。回退只接受安装器历史中保留的版本，先复查运行环境，再切换注册。

```powershell
python -X utf8 -B .\scripts\install_public.py rollback --agent codex --root "$env:LOCALAPPDATA\Genshin-UGC-Public" --version 3.7.0
python -X utf8 -B .\scripts\install_public.py uninstall --agent codex --root "$env:LOCALAPPDATA\Genshin-UGC-Public" --version 3.7.0
```

卸载仅撤销该安装器记录的插件和 marketplace 注册，保留版本目录及专用环境用于回退。确认不再需要后，可手动删除安装根；项目和输出目录不是插件缓存，不随卸载删除。不要手动删除客户端的其他插件缓存。

依赖或运行检查失败时不会注册新插件；失败目录保留供诊断。重试前确认该目录没有启用，删除该次失败的版本目录即可。客户端注册失败时会尝试移除本次新增注册；若客户端本身无法完成清理，按错误信息在其插件管理界面移除本次条目，旧版本目录仍保留。

## 手动接入

1. 下载完整 ZIP 与 SHA256SUMS.txt，核对 `Get-FileHash -Algorithm SHA256` 后解压。
2. 按[运行环境](runtime-environment.md)调用 `scripts/configure_runtime.py`，传入专用 Python 环境路径、项目、输出和独立 config 路径。
3. 为本插件 MCP 显式设置 `UGC_RUNTIME_CONFIG` 指向该 config，使用 Node 调用 `scripts/mcp_launcher.cjs`。
4. 支持完整插件的客户端加载整个根目录。Codex 使用 `.codex-plugin/plugin.json`、`mcp.json`；Claude Code 使用 `.claude-plugin/plugin.json`、`.mcp.json`。Claude 的根目录变量为 `${CLAUDE_PLUGIN_ROOT}`，Codex 为 `${PLUGIN_ROOT}`。自动安装器生成这些本机绑定；手动方式需自行填写，不能照搬未绑定的默认值。

无法接入插件的客户端仍可使用完整目录中的 CLI；不把这称为该客户端已完整兼容。

## 适配依据

- Codex：安装时核对本机 `codex plugin --help`、`plugin marketplace add --help` 与 `plugin add --help`。
- Claude Code：[插件清单](https://code.claude.com/docs/en/plugins-reference)、[本地 marketplace](https://code.claude.com/docs/en/plugin-marketplaces)。
- README 与安装体验参考：[Vercel Skills](https://github.com/vercel-labs/skills)、[Superpowers](https://github.com/obra/superpowers)、[Anthropic Skills](https://github.com/anthropics/skills)。仅参考组织方式，没有复制其实现或承诺全客户端兼容。

## 失败后续装

保留失败目录，用相同参数增加 `-Resume`（Python入口为 `--resume`）。安装器核对版本、ZIP摘要、客户端、安装及输入输出目录，只恢复已登记且未进入激活阶段的版本；已激活或归属不明的目录拒绝覆盖。原安装与回退版本保持。依赖安装采用 `--require-hashes --only-binary=:all:`，不自动升级pip。摘要检查仅证明下载内容一致，不是独立签名。
