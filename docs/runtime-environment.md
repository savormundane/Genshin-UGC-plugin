# 独立运行环境

CLI 和插件 MCP 使用同一套本地工具。可复用已有 Python 或使用 uv。

[安装指南](installation.md) · [运行要求与支持范围](compatibility.md)

## 启动时选择 Python

客户端用 Node 运行 `scripts/mcp_launcher.cjs`。设了 `MILIASTRA_WONDERLAND_PYTHON` 时，启动器只检查该绝对路径。否则按以下顺序检查解释器的版本、架构和依赖。

1. 运行绑定中的 `python`。
2. `VIRTUAL_ENV` 指向的虚拟环境。
3. 安装根目录内各版本保留的 Python。
4. 此锁文件对应的已准备环境。
5. PATH 上的 `python.exe`，再查 Windows 的 `py.exe`。

均不可用时，启动器通过 PATH 上的 uv 在安装根目录内准备锁定环境。默认根目录为 `%LOCALAPPDATA%\Miliastra Wonderland`，可通过 `MILIASTRA_WONDERLAND_INSTALL_ROOT` 改为其他绝对路径。缺少本地依赖缓存时需要联网。 [安装自检](installation.md#安装自检) · [uv 安装说明](https://docs.astral.sh/uv/getting-started/installation/)

## 提前准备 Python 环境

在插件目录运行以下命令，提前检查或准备 Python。随后打开客户端进行[首次工具验证](installation.md#首次工具验证)。若自定义了安装根目录，准备环境和启动客户端都应使用同一路径。

```powershell
node .\scripts\mcp_launcher.cjs --setup
```

### 使用 PyPI 镜像

uv 的项目锁文件包含依赖源。切换索引后，如果 `--locked` 报告锁文件需要更新，可以使用随包的依赖清单从镜像安装同版本的 wheel，并校验 SHA-256。下面以清华镜像和已安装的 CPython 3.12 x64 为例。 [uv 锁定规则](https://docs.astral.sh/uv/concepts/projects/sync/#checking-the-lockfile) · [pip 哈希校验](https://pip.pypa.io/en/stable/topics/secure-installs/) · [清华 PyPI 镜像](https://mirrors.tuna.tsinghua.edu.cn/help/pypi/)

```powershell
$miliastraVenv = Join-Path $env:LOCALAPPDATA 'Miliastra Python'
py -3.12 -m venv $miliastraVenv
$miliastraPython = Join-Path $miliastraVenv 'Scripts\python.exe'
& $miliastraPython -m pip install --require-hashes --only-binary=:all: `
  -r .\scripts\runtime-requirements.lock -i https://pypi.tuna.tsinghua.edu.cn/simple
```

安装成功后，将 `$miliastraPython` 的实际路径填入[运行绑定](#桌面端首次绑定本机工程)的 `python`，或在客户端给 MCP 启动器设置 `MILIASTRA_WONDERLAND_PYTHON`。镜像须提供锁定的版本和对应的 Windows wheel。

### Beyond 首次下载代理

已装好 Python 后，Beyond 首次预览仍可能需要单独下载 Canvas。可在启动客户端前设置 `HTTPS_PROXY`、`HTTP_PROXY` 或 `NO_PROXY`，由客户端传给 MCP。若已解包对应版本的 Canvas 文件，可将 `MILIASTRA_WONDERLAND_BEYOND_NATIVE_ROOT` 设为其绝对路径。目录内的相对路径和 SHA-256 以[锁定清单](../vendor/beyond/native-canvas.json)为准。

## 复用 PowerShell 安装器配置的环境

默认版本目录为 `%LOCALAPPDATA%\Miliastra Wonderland\versions\<Agent>\<版本>`。安装时使用过 `-Root` 的话，以当时指定的位置为准。

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

手动连接 MCP 时，参见[启动与客户端配置](mcp.md#依赖与启动)。查询随包的节点、API、平台文档和资源无需工程目录。本地文件工具按以下规则选择工程和输出位置。

| 目录 | 选择顺序 |
| --- | --- |
| 工程 | CLI 参数或 `MILIASTRA_WONDERLAND_PROJECT_ROOT` → 会话通过 MCP Roots 提供的已授权目录 → 运行绑定的 `project_root`。多个已授权目录时，用输入的绝对路径选定其中一个。 |
| 输出 | CLI 参数或 `MILIASTRA_WONDERLAND_OUTPUT_ROOT` → 适用于该工程的 `output_root` → 插件数据目录下按工程生成的 `outputs` 子目录。只读任务可省略。 |

插件数据目录优先使用客户端提供的插件数据目录，其次使用安装根目录。调用 `doctor` 可查看选中的目录、配置来源及缺失项。 [文件路径约定](mcp.md#文件路径和校验值)

### 桌面端首次绑定本机工程

需要固定解释器或工程目录时，用 UTF-8 保存下列 JSON 并替换绝对路径。手动指定的输出根目录需预先创建，并与工程目录和插件源码互不包含。只需绑定解释器时可省略两个目录字段。

```json
{
  "schema": 1,
  "python": "C:\\千星环境\\Scripts\\python.exe",
  "project_root": "C:\\千星工程",
  "output_root": "C:\\千星输出"
}
```

将文件保存到客户端分配的插件数据目录，或用 `MILIASTRA_WONDERLAND_RUNTIME_CONFIG` 指明绝对路径。无客户端数据目录时，工具可从安装根目录读取 `runtime.json` 的工程设置。要让启动器也读取该文件的解释器设置，显式指定该配置文件。

修改 `project_root` 或 `output_root` 后，下一次工具调用读取新值。修改解释器或启动环境变量后需重新启动客户端。用 `doctor` 核对 `python_executable` 和 `project_context`，再挑一个工程文件做只读检查。

### 从终端启动客户端

从工程目录启动客户端。会话支持 MCP Roots 时可直接选择并授权当前目录，否则配置上面的 `runtime.json`。终端中的环境变量需由客户端传给 MCP 子进程，可参考 [Codex 手动配置示例](mcp.md#调整客户端超时)。
