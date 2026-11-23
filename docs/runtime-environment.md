# 独立运行环境

CLI 和插件 MCP 使用同一套本地工具。可复用已有 Python 或使用 uv。

[安装指南](installation.md) · [运行要求与支持范围](compatibility.md)

## 复用 PowerShell 安装器配置的环境

默认版本目录为 `%LOCALAPPDATA%\Genshin-UGC-Public\versions\<Agent>\<版本>`；安装时使用过 `-Root` 则以自选位置为准。

| 版本目录内的路径 | 用途 |
| --- | --- |
| `Genshin-UGC\scripts\qianxing.py` | 统一命令行入口。 |
| `runtime\Scripts\python.exe` | 安装器已配置的专用 Python。 |
| `runtime.json` | 记录 Python、项目目录和输出目录的绑定。 |

下面的命令从 Codex 的安装记录读取 Python 和 CLI 路径。Claude 将 `codex.json` 改为 `claude-code.json`。使用过 `-Root` 时，将 `$ugcInstallRoot` 改为实际安装根目录。

```powershell
$ugcInstallRoot = Join-Path $env:LOCALAPPDATA 'Genshin-UGC-Public'
$ugcState = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $ugcInstallRoot 'codex.json') | ConvertFrom-Json
$ugcPython = $ugcState.current.python
$ugcCli = Join-Path $ugcState.current.home 'Genshin-UGC\scripts\qianxing.py'
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

手动连接 MCP 时，让客户端通过 Node 启动插件的 `scripts/mcp_launcher.cjs`。文件工具通过 `UGC_PROJECT_ROOT` 和 `UGC_OUTPUT_ROOT` 访问两个独立的绝对目录。切换工程时更新这两个值并重启 MCP 或客户端。完整配置见[客户端适配](contributing/development.md#客户端适配)。

`UGC_RUNTIME_CONFIG` 也可指向本机已有的 `runtime.json`，沿用其中的 Python 与目录。另行设置的目录变量优先。

旧版本目录可保留用于回退；不要只移动其中的插件或运行环境子目录。[更新与回退](installation.md#回退与卸载)
