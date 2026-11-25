# 本地开发与检查

按任务从[工具导航](../../scripts/README.md)定位模块。修改工具时核对 CLI、MCP 和包内引用。更新平台资料时核对[来源与摘要](../../references/platform/knowledge-reliability.md)。

从仓库根运行以下命令。只改文档时，系统 Python 就能运行仓库检查。

```powershell
python -B scripts/check_repository.py
```

需要运行插件、修改 MCP 或调试生成工具时，用支持的 Windows、Python 和 Node.js 环境。已有插件专用 Python 可直接复用，也可在检出目录创建专用环境。[运行要求](../compatibility.md) · [复用已安装的环境](../runtime-environment.md)

```powershell
uv sync --locked --no-build
$ugcPython = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $ugcPython -B scripts/qianxing.py doctor
```

## 按改动选检查

| 改了什么 | 在仓库根运行 |
| --- | --- |
| 文档、安装链接、清单 | `python -B scripts/check_repository.py` |
| Python 脚本 | `python -m compileall -q scripts` |
| GIL 容器和 Lua 替换 | `node scripts/test_gil.mjs` |
| MCP、原生修改计划 | `& $ugcPython -B scripts/test_mcp_native_workflow.py -v` |
| 中文 API 检索、资料与节点查询 | `& $ugcPython -B scripts/test_chinese_lookup.py -v` |
| 三维物件读取、变换与字段保护 | `& $ugcPython -B scripts/test_native_entity_transform.py -v` |
| 安装器与各客户端配置 | `& $ugcPython -B scripts/test_agent_protocols.py -v`、`& $ugcPython -B scripts/test_distribution.py -v` |
| 打包和版本校验 | `python -B scripts/test_release.py -v` |

使用已有专用 Python 时，将 `$ugcPython` 设为该解释器的绝对路径。公开测试会生成自己的输入。本地检查即可用于 PR，编辑器导入和游戏运行按任务记录。[验证分层](../compatibility.md#验证分层)

## 复现已有工程的修改流程

```powershell
& $ugcPython -B scripts/test_mcp_native_workflow.py -v
```

脚本生成一个继承模板参数 `ActivationDelay=7` 的最小工程，通过真实 stdio 查询引用、生成计划并另存为 `12`。随后校验保护字段的原始字节、过期输入拒绝和来源变更。成功输出 `OK`。[输入与断言](../../scripts/test_mcp_native_workflow.py) · [MCP 操作合同](../mcp.md#审阅并另存已有工程)

## Windows 长路径

检出目录较深时，可用 `git -c core.longpaths=true clone https://github.com/savormundane/miliastra-wonderland-plugin.git` 并选用较短的目标路径，例如 `C:\src\miliastra-wonderland-plugin`。

## 客户端适配

客户端启动 Node 和 `scripts/mcp_launcher.cjs`。解释器选择与工作目录绑定见[独立运行环境](../runtime-environment.md)。

- Codex 读取 `.codex-plugin/plugin.json` 和 `mcp.json`，通用接入读取根 `plugin.json` 和 `mcp.json`。
- Claude Code 读取 `.claude-plugin/plugin.json` 和 `.mcp.json`。可用 `claude plugin validate <目录>` 检查声明。
- DeepSeek Harness 从插件根目录的 `package.json` 和 `cordis.patch.yml` 加载 Skills 与 MCP。

宿主安装步骤见[安装指南](../installation.md)。维护其他接入方式时，可核对 [Agent Plugins 规范](https://agent-plugins.org/specification) · [Claude Code 插件参考](https://code.claude.com/docs/en/plugins-reference) · [DeepSeek Harness Bundle 参考](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.2.2-rc.5/packages/preset/agent-preset/skills/dsh-doc/references/host-plugin.md)。
