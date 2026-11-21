# 独立运行环境

CLI 和插件 MCP 使用同一套本地工具。已经通过安装器安装的用户可以直接复用专用 Python；只使用命令行的用户再按下方步骤创建环境。

[安装指南](installation.md) · [第一次使用](getting-started.md) · [运行要求与支持范围](compatibility.md)

## 已安装插件：直接复用环境

默认版本目录为 `%LOCALAPPDATA%\Genshin-UGC-Public\versions\<Agent>\<版本>`；安装时使用过 `-Root` 则以自选位置为准。

| 版本目录内的路径 | 用途 |
| --- | --- |
| `Genshin-UGC\scripts\qianxing.py` | 统一命令行入口。 |
| `runtime\Scripts\python.exe` | 安装器已配置的专用 Python。 |
| `runtime.json` | 记录 Python、项目目录和输出目录的绑定。 |
| `cordis-bundle\` | DeepSeek Harness 的导入入口，其他接入方式没有此项。 |

Codex 用户可以用下面的 PowerShell 命令读取当前安装记录，并查询一个节点。Claude Code 将 `codex.json` 改为 `claude-code.json`；如果自选了 `-Root`，同时调整 `$ugcInstallRoot`。

```powershell
$ugcInstallRoot = Join-Path $env:LOCALAPPDATA 'Genshin-UGC-Public'
$ugcState = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $ugcInstallRoot 'codex.json') | ConvertFrom-Json
$ugcPython = $ugcState.current.python
$ugcCli = Join-Path $ugcState.current.home 'Genshin-UGC\scripts\qianxing.py'
& $ugcPython $ugcCli nodes '启动定时器' --scope server --limit 1
```

这段命令适用于当前仍有已登记安装的 Codex / Claude Code。DeepSeek Harness 或通用插件用户，使用准备命令输出的目录，在其所属版本目录找到上表中的 Python 与 CLI 即可。无需再次安装同一套依赖。

## 只用 CLI：从完整 ZIP 配置一次

下载[完整 Windows ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/latest)，解压后进入 `Genshin-UGC` 目录。先确认已有 Python 与 Node.js 满足[运行要求](compatibility.md)。以下示例将环境和个人文件放在 `C:\Qianxing`；可统一替换成自己的目录。

```powershell
# 按实际位置填写一个受支持的 Python 解释器。
$ugcBasePython = 'C:\实际路径\python.exe'
New-Item -ItemType Directory -Force 'C:\Qianxing\project' | Out-Null

# 运行环境目录必须是尚不存在的新目录。
& $ugcBasePython .\scripts\configure_runtime.py --python $ugcBasePython --runtime 'C:\Qianxing\runtime' --project 'C:\Qianxing\project' --outputs 'C:\Qianxing\outputs' --config 'C:\Qianxing\runtime.json'

& 'C:\Qianxing\runtime\Scripts\python.exe' .\scripts\qianxing.py nodes '启动定时器' --scope server --limit 1
```

配置命令按 `scripts/runtime-requirements.lock` 下载并安装锁定依赖，首次需要联网。项目目录需要提前存在，可以为空；输出目录由配置命令创建。项目与输出不能相同或互相包含。

同参数的未完成配置可在配置命令末尾加 `--resume` 继续。已经完成的运行环境不通过重复执行该命令来覆盖；遇到依赖报错时，可用专用 Python 运行 `scripts/qianxing.py doctor` 查看具体缺项。

## 连接 MCP 或切换工程

手动连接 MCP 时，让客户端通过 Node 启动插件的 `scripts/mcp_launcher.cjs`，并将 `UGC_RUNTIME_CONFIG` 指向实际 `runtime.json`。完整配置见[客户端适配](contributing/development.md#客户端适配)。

切换工程时，先准备两个独立的新项目、输出目录，再修改当前绑定的 `runtime.json` 中 `project_root` 和 `output_root` 的绝对路径，保留 `python` 与其他字段。重启该 MCP 连接或打开新会话使配置生效。不要同时让旧任务继续写入，也无需为此重装依赖。

旧版本目录可保留用于回退；不要只移动其中的插件或运行环境子目录。[更新与回退](installation.md#回退与卸载)
