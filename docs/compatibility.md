# 运行要求与支持范围

[安装指南](installation.md)

## 运行要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | 完整工具面向 Windows x64。发行 ZIP 包含 Beyond 的 Windows 原生模块。通过 Git 或 Cordis 安装时，首次使用 Beyond 会下载并校验原生模块。 |
| Python | CPython 3.11–3.14。启动器优先使用已装好依赖的环境，找不到合适环境时使用 PATH 上的 uv。 |
| Node.js | 插件 MCP 启动器需要 22+。DeepSeek Harness 接入需要 24.9+，也须满足所用 DSH 版本自身的 Node.js 要求。 |
| 客户端 | 文件和素材工具需要支持本地 stdio MCP 的会话。也可在终端运行 CLI。 |

Python 依赖由 `pyproject.toml` 和 `uv.lock` 锁定。详见[解释器选择](runtime-environment.md#启动时选择-python)和[工程绑定](runtime-environment.md#连接-mcp-或切换工程)。

## 安装协议与客户端

| 协议 | 客户端与安装入口 |
| --- | --- |
| Agent Plugins | [ChatGPT/Codex](installation.md#chatgptcodex)、[Codex CLI](installation.md#codex-cli)及[通用 Agent Plugins 客户端](installation.md#agent-plugins)。 |
| Claude | [Claude](installation.md#claude) 和 [Claude Code](installation.md#claude-code)。 |
| DSH | 在 [DeepSeek Harness 插件页](installation.md#deepseek-harness)添加 GitHub 仓库地址，通过 Cordis Bundle 接入。 |

[安装自检](installation.md#安装自检) · [独立 CLI](runtime-environment.md#只用-cli)

## 验证分层

按实际产物记录静态检查、离线模型与预览、编辑器导入、游戏内运行和试玩结果。 [验证等级与报告状态](../references/workflows/validation.md)
