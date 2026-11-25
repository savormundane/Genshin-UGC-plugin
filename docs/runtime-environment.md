# 独立运行环境

CLI 和插件 MCP 使用同一套本地工具。可复用已有 Python 或使用 uv。

[安装指南](installation.md) · [运行要求与支持范围](compatibility.md)

## 启动时选择 Python

客户端用 Node 运行 `scripts/mcp_launcher.cjs`。启动器收到 `MILIASTRA_WONDERLAND_PYTHON` 时，只检查该绝对路径。否则按顺序检查运行绑定中的解释器、当前虚拟环境、插件安装根内的解释器和 PATH 上的 `python.exe`，再用 Windows 的 `py.exe` 查找兼容版本。

找不到已具备锁定依赖的解释器时，启动器用 PATH 上的 uv 创建独立环境。环境保存在插件安装根内，首次缺少缓存时需要联网。自选安装根用 `MILIASTRA_WONDERLAND_INSTALL_ROOT` 指定绝对路径。 [安装自检](installation.md#安装自检) · [uv 安装说明](https://docs.astral.sh/uv/getting-started/installation/)

## 复用 PowerShell 安装器配置的环境

默认版本目录为 `%LOCALAPPDATA%\Miliastra Wonderland\versions\<Agent>\<版本>`；安装时使用过 `-Root` 则以自选位置为准。

| 版本目录内的路径 | 用途 |
| --- | --- |
| `miliastra-wonderland\scripts\qianxing.py` | 统一命令行入口。 |
| `runtime\Scripts\python.exe` | 安装器已配置的专用 Python。 |
| `runtime.json` | 记录 Python、项目目录和输出目录的绑定。 |

下面的命令从 Codex 的安装记录读取 Python 和 CLI 路径。Claude 将 `codex.json` 改为 `claude-code.json`。使用过 `-Root` 时，将 `$miliastraInstallRoot` 改为实际安装根目录。

```powershell
$miliastraInstallRoot = Join-Path $env:LOCALAPPDATA 'Miliastra Wonderland'
$miliastraState = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $miliastraInstallRoot 'codex.json') | ConvertFrom-Json
$miliastraPython = $miliastraState.current.python
$miliastraCli = Join-Path $miliastraState.current.home 'miliastra-wonderland\scripts\qianxing.py'
& $miliastraPython $miliastraCli --help
```

## 只用 CLI

在包含 `pyproject.toml` 与 `uv.lock` 的插件目录执行。uv 按锁文件准备依赖，已有具备依赖的 Python 可以直接运行 `scripts/qianxing.py`。

```powershell
uv run --locked --no-build python -B .\scripts\qianxing.py --help
```

## 连接 MCP 或切换工程

手动连接 MCP 时，按[客户端适配](contributing/development.md#客户端适配)配置启动器。节点、API、平台文档和内置资源查询无需工程目录。文件工具依次使用显式工程路径、会话中由 MCP Roots 提供的已授权目录和 `runtime.json`。多个会话目录时，用输入的绝对路径选定一处。

从插件数据目录读取 `runtime.json`，也可用 `MILIASTRA_WONDERLAND_RUNTIME_CONFIG` 指定绑定文件的绝对路径。修改其中的 `project_root` 或 `output_root` 后，下一次工具调用会读取新值。环境变量 `MILIASTRA_WONDERLAND_PROJECT_ROOT`、`MILIASTRA_WONDERLAND_OUTPUT_ROOT` 或对应 CLI 参数提供固定覆盖。只读任务可省略输出根，写入默认在插件数据目录内按工程分开保存。用 `doctor` 查看目录、来源、候选和缺失项。

### 桌面端首次绑定本机工程

需要固定解释器或工程目录时，可给本机启动器配置 `runtime.json`。用 UTF-8 保存下列 JSON，将三个路径换成你的绝对路径。输出目录需要预先创建，并与工程目录和插件源码互不包含。

```json
{
  "schema": 1,
  "python": "C:\\千星环境\\Scripts\\python.exe",
  "project_root": "C:\\千星工程",
  "output_root": "C:\\千星输出"
}
```

可从连通后 `doctor` 的 `python_executable` 复制当前解释器路径。把文件保存到客户端为插件分配的数据目录。客户端允许向 MCP 传递自定义环境变量时，也可用 `MILIASTRA_WONDERLAND_RUNTIME_CONFIG` 指向该文件。然后调用 `doctor`，核对 `project_context.source`、`project_root` 和 `output_root`，再用自己的文件跑一次只读检查。已装好插件依赖的 Python 可通过[安装自检](installation.md#安装自检)验证。

### 从终端启动客户端

从工程目录启动客户端，让会话提供已授权的工程目录。客户端不提供工程目录时，使用上面的 `runtime.json`。Codex 的 MCP 子进程只继承指定的环境变量。让客户端的 PATH 可找到 uv 或已具备依赖的 Python，或者把专用解释器路径写入插件数据目录的 `runtime.json`。 [Codex 的环境继承规则](https://github.com/openai/codex/blob/rust-v0.171.0-alpha.13.2/codex-rs/rmcp-client/src/utils.rs#L16-L36)
