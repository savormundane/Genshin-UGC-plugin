# 本地检查与提交前验证

完整插件面向 Windows x64。仓库检查使用 Python 标准库与 Node.js，可在本机独立运行。

在仓库根目录按改动选择检查。只改文档时运行第一条。改动 Python 时检查语法，涉及 GIL 时运行相关回归。

```powershell
python scripts/check_repository.py
python -m compileall -q scripts
node scripts/test_gil.mjs
```

- `check_repository.py` 检查清单、安装器、README、安装指南的版本一致性，以及第一方 Markdown 本地链接。
- `compileall` 检查 Python 脚本能否被解释器解析。
- `test_gil.mjs` 对指定夹具测试 GIL 字节回读、Lua 替换及异常输入。

GitHub Actions 的 [Repository checks](../../.github/workflows/repository-check.yml) **仅支持手动启动**（`workflow_dispatch`），普通 push 和 PR 不自动消耗 Actions 配额。

涉及安装、MCP、模拟器或实际游戏文件的变动，选择对应的验证环节并记录结果。[安装说明](../installation.md) · [验证分层](../compatibility.md#验证分层)

修改打包或版本检查时运行 `python -B scripts/test_release.py`。若改动客户端适配，运行 `python -B scripts/test_agent_protocols.py`，再按[安装说明](../installation.md)检查对应入口。打包流程见[维护与发布](maintenance.md)。

## 复现已有工程的修改流程

在插件专用环境中执行以下命令。脚本生成一个小关卡，其中一个实例继承模板的整数参数 `ActivationDelay=7`。真实 MCP stdio 测试定位对象、预览修改、另存并确认参数变为 `12`，再逐字节核对保护范围。它也覆盖过期摘要和外部来源变化。

```powershell
python -B scripts/test_mcp_native_workflow.py -v
```

成功输出 `OK`。编辑器导入和机关行为需要用实际工程检查。[输入与断言](../../scripts/test_mcp_native_workflow.py) · [MCP 操作合同](../../references/local-mcp.md#审阅并另存已有工程) · [贡献任务 #4](https://github.com/savormundane/Genshin-UGC-plugin/issues/4)

## Windows 长路径

Windows 开发检出建议放在较短路径，例如 `C:\src\Genshin-UGC-plugin`，并使用 `git -c core.longpaths=true clone https://github.com/savormundane/Genshin-UGC-plugin.git`。首次克隆后可在该仓库运行 `git config core.longpaths true`，不必修改全局配置。若出现 `Filename too long`，使用较短的检出路径并确认依赖文件齐全。

## 客户端适配

用户操作见[安装指南](../installation.md)。以下信息用于维护清单、排查手动配置以及接入其他客户端。

- Codex 使用 `.codex-plugin/plugin.json` 和 `mcp.json`。通用 Agent Plugins 入口使用根 `plugin.json` 和 `mcp.json`，维护时参考 [Agent Plugins 规范](https://agent-plugins.org/specification)。
- Claude Code 使用 `.claude-plugin/plugin.json` 和 `.mcp.json`。可以用 `claude plugin validate <目录>` 检查声明。详见 [Claude Code 插件参考](https://code.claude.com/docs/en/plugins-reference)。
- DeepSeek Harness 从安装器生成的 Cordis Bundle 读取 Skills 和 stdio 配置。详见 [DeepSeek Harness 的 Bundle 参考](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.2-rc.5/packages/preset/agent-preset/skills/dsh-doc/references/host-plugin.md)。

手动使用完整解包目录时，先按[独立运行环境](../runtime-environment.md)创建配置。将 `UGC_RUNTIME_CONFIG` 指向配置文件，让客户端通过 Node 调用 `scripts/mcp_launcher.cjs`。未显式配置时，通用入口从 `${PLUGIN_DATA}/runtime.json` 读取配置，Claude Code 从 `${CLAUDE_PLUGIN_DATA}/runtime.json` 读取配置。项目与输出的绑定以实际生效的配置为准。

适配检查分别记录清单校验、stdio 调用和实际客户端加载。安装器的本地检查可以验证工具发现、API 查询与随包预览，客户端是否启用插件需在实际会话中确认。
