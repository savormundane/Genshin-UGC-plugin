# 独立运行环境

CLI 和插件 MCP 使用同一套本地工具。可复用已有 Python 或使用 uv。

[安装指南](installation.md) · [运行要求与支持范围](compatibility.md)

## 复用 PowerShell 安装器配置的环境

默认版本目录为 `%LOCALAPPDATA%\Miliastra Wonderland\versions\<Agent>\<版本>`；安装时使用过 `-Root` 则以自选位置为准。

| 版本目录内的路径 | 用途 |
| --- | --- |
| `miliastra-wonderland\scripts\qianxing.py` | 统一命令行入口。 |
| `runtime\Scripts\python.exe` | 安装器已配置的专用 Python。 |
| `runtime.json` | 记录 Python、项目目录和输出目录的绑定。 |

下面的命令从 Codex 的安装记录读取 Python 和 CLI 路径。Claude 将 `codex.json` 改为 `claude-code.json`。使用过 `-Root` 时，将 `$ugcInstallRoot` 改为实际安装根目录。

```powershell
$ugcInstallRoot = Join-Path $env:LOCALAPPDATA 'Miliastra Wonderland'
$ugcState = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $ugcInstallRoot 'codex.json') | ConvertFrom-Json
$ugcPython = $ugcState.current.python
$ugcCli = Join-Path $ugcState.current.home 'miliastra-wonderland\scripts\qianxing.py'
& $ugcPython $ugcCli --help
```

通过客户端市场或直装安装的用户，可从下方源码目录运行 CLI。

## 只用 CLI

在包含 `pyproject.toml` 与 `uv.lock` 的插件目录执行。uv 按锁文件准备依赖，已有具备依赖的 Python 可以直接运行 `scripts/qianxing.py`。

```powershell
uv run --locked --no-build python -B .\scripts\qianxing.py --help
```

可在源码目录运行 CLI。需要完整 Windows ZIP 时，按[自行打包](installation.md#自行打包-zip)生成。

## 连接 MCP 或切换工程

手动连接 MCP 时，让客户端通过 Node 启动插件的 `scripts/mcp_launcher.cjs`。支持 MCP Roots 的客户端可直接使用会话中已授权的工程目录。多个目录时，用输入的绝对路径选定一处。

客户端未提供目录时，从插件数据目录读取 `runtime.json`，也可用 `UGC_RUNTIME_CONFIG` 选定旧绑定文件。修改文件中的 `project_root` 或 `output_root` 后，下一次工具调用会读取新值。Python 路径在启动时选择。显式 `UGC_PROJECT_ROOT`、`UGC_OUTPUT_ROOT` 或对应 CLI 参数作为固定覆盖。只有读文件时可省略输出目录，写文件默认在插件数据目录内按工程分开保存。用 `doctor` 查看当前来源及缺失项。 [客户端适配](contributing/development.md#客户端适配)

从终端启动客户端时，也可以先设定工程路径。以 Codex CLI 为例，把下面的路径换成实际包含输入文件的目录，再从同一个 PowerShell 窗口打开 Codex。

```powershell
$env:UGC_PROJECT_ROOT = 'C:\千星项目'
codex
```

如果 MCP 还未连通，先[运行安装自检](installation.md#安装自检)。

旧版本目录可保留用于回退；不要只移动其中的插件或运行环境子目录。[更新与回退](installation.md#回退与卸载)
