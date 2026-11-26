# 运行要求与支持范围

[安装指南](installation.md)

## 运行要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | 完整工具面向 Windows x64。 |
| Python | CPython x64 3.11–3.14。MCP 启动器可复用已装好依赖的环境，或通过 PATH 上的 uv 准备环境。PowerShell 安装器需要已有兼容的 Python。 |
| Node.js | MCP 启动器与 Beyond 预览需要 x64 Node.js 22 或以上。DeepSeek Harness 接入需要 24.9 或以上，并须满足所用 DSH 版本自身的 Node.js 要求。 |
| DeepSeek Harness | 支持版本以 [`engines.dsh`](../package.json) 为准。 |
| 客户端 | 在支持本地 stdio MCP 的会话中调用工具，或在终端运行 CLI。能载入 Skill 的客户端也可用随包说明辅助创作。 |

Python 版本和依赖以 [`pyproject.toml`](../pyproject.toml) 与 [`uv.lock`](../uv.lock) 为准。发行 ZIP 内含 Beyond 的 Windows 原生模块。通过 Git 或 Cordis 安装时，Beyond 首次使用会查找已校验的本地模块，缺少时下载。 [启动配置](runtime-environment.md) · [Beyond 首次下载](runtime-environment.md#beyond-首次下载代理)

## 安装协议与客户端

| 协议 | 客户端与安装入口 |
| --- | --- |
| Agent Plugins | [ChatGPT/Codex](installation.md#chatgptcodex)、[Codex CLI](installation.md#codex-cli)及[通用 Agent Plugins 客户端](installation.md#agent-plugins)。 |
| Claude | [Claude](installation.md#claude) 和 [Claude Code](installation.md#claude-code)。 |
| DSH | 在 [DeepSeek Harness 插件页](installation.md#deepseek-harness)按 npm 包名安装，通过 Cordis Bundle 接入。 |

[安装自检](installation.md#安装自检) · [独立 CLI](runtime-environment.md#只用-cli)

## 验证分层

按实际产物记录静态检查、离线模型与预览、编辑器导入、游戏内运行和试玩结果。 [验证等级与报告状态](../references/workflows/validation.md)
