# 本地 MCP 服务

stdio 服务提供本地文件读取、审计和制作工具。编辑器导入和游戏内运行按[验证等级](../references/workflows/validation.md)单独核对。

## 依赖与启动

客户端用 Node 运行 `scripts/mcp_launcher.cjs`。手动连接时，把启动器的绝对路径传给 `node`。已装好插件依赖的 Python 也能直接启动 stdio 服务。只查询随包资料时，可省略下面两个目录参数。 [运行要求](compatibility.md#运行要求) · [工程绑定](runtime-environment.md#连接-mcp-或切换工程) · [Codex 手动配置示例](#调整客户端超时)

```text
python scripts/qianxing.py mcp serve --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

协议消息通过 stdout 发送，执行日志使用 stderr 或请求的临时日志文件。

## 工具与参数

下面按用途说明常用输入和输出。字段类型、默认值和工具标注以 `tools/list` 为准。用 `capabilities` 核对当前加载版本的任务入口。 [创作者教程](../samples/creator-demos/README.md) · [单项工具与制作配置](../references/workflows/skill-map.md)

| 工具 | 参数与行为 |
| --- | --- |
| doctor | 返回依赖状态、当前加载路径、版本和 `plugin.capability_groups` 的分组校验值。用 CLI `doctor --compare PLUGIN_ROOT` 定位同版本的文件差异 |
| capabilities | 返回插件版本、可用任务和对应工具。用 CLI `capabilities` 查看完整清单，可加 `--evidence REPORT` 核对本地验证记录 |
| api_lookup | symbol。接受客户端 Lua 的正式符号、英文片段或中文用途。返回正式符号、原文说明、来源与推导状态 |
| diagnose | spec、sha256。按配置执行只读的环境、Lua、GIL 和素材检查 |
| docs_search | version、query。接受中文问题或关键词，返回匹配资料的原文片段和来源版本 |
| nodes_lookup | query、scope、limit 均可选。查询 Graph Code 调用、作用域、签名和端口。scope 为 all、client 或 server，limit 默认 20，范围 1 到 100 |
| graph_check | input 指向一张 Graph Code 源文件。可给 job 载入制作任务，或给 bindings 提供具名绑定。sha256、job_sha256、bindings_sha256 可选，工具返回直接输入和实际读取的项目依赖的校验值 |
| graph_build | spec、output，可选 sha256。使用 schema 1 配置编译独立 GIA，并返回产物及 SHA-256 校验值。用于已有 GIL 时，把 GIA 交给 native_plan 审阅，再用 native_apply 另存 |
| resources_lookup | version 必填。默认查询模型和模板 ID，可通过 resource_type 查询音效 `sound` 或特效 `effect`。指定 catalogue 时读取经授权的补充目录 |
| native_inspect / native_audit | input，可选 sha256。读取或审计指定原生文件 |
| scene_preview | input、output，可选 sha256。读取场景草案 JSON 或 GIL 布局，返回俯视图、侧视图及产物校验值。GIL 可用 before 和 before_sha256 对照 |
| scene_catalogue | input、sha256、version、mode、output。从实际 GIL/GIA 提取布景模板和样本校验值，生成 models.json |
| scene_build | spec、sha256、output。按已审阅的布景配置和样本证据生成静态 scene.gia，写入后重新读取并校验 |
| asset_preview | input、output，可选 sha256、max_controls、step。试算单张 PNG 的矩形图元方案并写出预览文件，返回各方案的控件数、误差、预算和路径，附 `report.json` 的校验值 |
| asset_generate | input、sha256、report、report_sha256、candidate、output。用已选候选生成矩形图元或试算报告指定的素材，返回参考 PNG、实际控件数和产物校验值 |
| asset_fit | input、spec、output。用内置拟合处理图片或分层清单，返回误差、边缘检查和控件数。可选 sha256、spec_sha256、steps、resume、resume_sha256、initial、initial_sha256。配置 mount 可用实际 GIL 解析模板和目标控件，并生成 Lua 和软件预览配置 |
| project_inspect | input，可选 sha256、scope。用 query、kind、limit 搜索对象，用 selector、transitive 查精确目标和关系，或用 summary 查看对象数。`scope="scene"` 查询 3D，`scope="gameplay"` 查询玩法资源 |
| client_check | input，可选 sha256、mapping、contract、contract_sha256。对 Lua 文件或 GIL 中的 Lua 源码做编译检查。可选择单个 GIL 映射，按相应约定检查 API 用法 |
| produce | spec、sha256、output，可选 summary。执行已有制作配置并校验交付 |
| native_diff | input、other，可选 sha256、other_sha256、allowed_top_level_fields。给出允许范围时，核对其余字段的原始字节 |
| experiment_compare | input、sha256、other、other_sha256。读取两份观察报告，按相同种子和策略配对比较，不写文件 |
| native_plan | input、sha256、output 加一个 patch 对象，或加 spec 和 spec_sha256 文件参数。可选 summary。输出可审阅的 plan.json 和文件校验值 |
| simulate | spec、sha256、output。默认执行联合场景或复跑此前失败。传 preview=true 时运行 Beyond 软件预览并附上已生成的 PNG，失败时一并返回诊断 |
| experiment_run | spec、sha256、output。按配置中的种子和策略运行 Lua 模拟，将观察报告保存到新的输出目录 |
| logs_diagnose | spec、sha256。只读解析 JSONL 或支持的编辑器二进制调试日志，并返回可核对的关联证据 |
| verify | input 指向交付 manifest.json，sha256 必填。artifacts_only、portable、rebuild 默认为 false。仅产物校验独立运行。重建还需 portable=true 和 trusted_inputs_sha256 |
| native_apply | input、sha256、plan、plan_sha256、output。核对文件校验值，按审阅过的修改计划执行并另存 |

在对话中先展示工具返回的预览图，再说明检查结果和下一步。结构化结果保留文件路径及校验值。Beyond 即使附上画面，检查是否通过也以 `status` 为准。 [Beyond 诊断产物](../references/workflows/beyond-backend.md)

## 文件路径和校验值

输入可以使用相对工程根目录的路径，或工程根、输出根内的绝对路径。`output` 指向输出根内尚不存在的目录，其父目录须存在。工具可创建按工程生成的默认输出根。若目录经过 Windows 目录联接或符号链接，请改用文件夹的实际位置。 [工程与输出根目录](runtime-environment.md#连接-mcp-或切换工程)

`sha256` 对应输入文件原始字节。`native_apply` 的 `plan_sha256` 参数核对计划文件字节，计划内的同名字段核对计划内容。

省略可选校验值时，工具自行计算并在 `inputs_sha256` 按参数名返回。编辑既有 GIL 时可把 `inputs_sha256.input` 交给 `native_plan`。配置诊断、修改计划、原生写入和重建须提供各自的必填校验值。

调用步骤见 [PNG 试算与生成](../references/assets/image-to-primitives.md#单张-png-试算与生成) · [拟合与预览](../references/assets/asset-fit.md#生成可挂载的-lua-和软件预览) · [静态布景](../references/editor/native-scene.md) · [诊断日志](../references/workflows/log-diagnostics.md#读取编辑器调试日志) · [审阅并另存已有工程](../references/gil/native-changes.md#审阅并另存已有工程)。

## CLI 与 MCP 共同约定

```text
python scripts/qianxing.py mcp call request.json --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

```json
{"schema":2,"operation":"native_inspect","arguments":{"input":"level.gil","sha256":"填写实际文件的 SHA-256 校验值"}}
```

CLI 和 MCP 共用同一套任务调度逻辑。结果包含 `schema`、`operation`、`status`、`result` 和 `output`。参数错误由 SDK 返回。执行失败时，工具会返回结构化的结果和诊断信息，CLI 则以非零退出码退出。产物报告记录检查范围和结果。

## 取消和输出保护

每次调用都在独立临时目录内用指定的 Python 工作进程执行。需要写文件时，产物先暂存在输出根目录内。工具在任务开始和结束时核对输入文件的校验值，确认执行成功且任务未取消后，再将暂存目录改名为正式输出目录。已有目录不覆盖。取消时终止本次工作进程，Windows 同时终止其进程树。清理仅限该请求的临时目录。

进度依次报告输入核对、任务执行和结果检查。普通操作默认时限 120 秒，编译、制作、拟合、应用和重建为 900 秒。可分别设置 `MILIASTRA_WONDERLAND_MCP_TIMEOUT_SECONDS` 和 `MILIASTRA_WONDERLAND_MCP_BUILD_TIMEOUT_SECONDS`，范围为大于 0 且不超过 3600 秒。

工作进程通过路径检查和 Python 文件访问审计发现越界依赖，并允许读取插件及 Python 运行资源。编译、制作或重建时只使用可信的 Graph Code 等工程源码和后端。工作进程以及它们启动的程序受当前系统账号的权限约束。

## 调整客户端超时

启动时限和工具时限由客户端分别控制。首次启动超时时，先在客户端之外[准备 Python 环境](runtime-environment.md#提前准备-python-环境)。长任务仍被中断时，将客户端工具时限设得比插件的任务时限稍长，以便客户端收到结果或诊断。

**Codex** 手动连接本机 MCP 时，可在 `config.toml` 使用下面的条目。将路径换成当前插件目录内启动器的绝对路径。两个时限都以秒为单位。已有手动连接条目时，直接调整该条目的两个时限。 [Codex MCP 配置](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

```toml
[mcp_servers.miliastra-wonderland-local]
command = "node"
args = ['C:\插件\miliastra-wonderland\scripts\mcp_launcher.cjs']
startup_timeout_sec = 120
tool_timeout_sec = 960
env_vars = [
  "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
  "MILIASTRA_WONDERLAND_PYTHON", "MILIASTRA_WONDERLAND_RUNTIME_CONFIG",
  "MILIASTRA_WONDERLAND_PROJECT_ROOT", "MILIASTRA_WONDERLAND_OUTPUT_ROOT",
  "MILIASTRA_WONDERLAND_INSTALL_ROOT", "MILIASTRA_WONDERLAND_BEYOND_NATIVE_ROOT",
  "MILIASTRA_WONDERLAND_MCP_TIMEOUT_SECONDS", "MILIASTRA_WONDERLAND_MCP_BUILD_TIMEOUT_SECONDS",
]
```

同时启用了从 GitHub 市场安装的插件时，可停用插件自带的 MCP 服务，继续使用插件的 Skills。通过 PowerShell 创建过独立市场的用户，可用 `codex plugin list --json` 找到对应的插件 ID，并替换下方的 ID。复用原运行绑定时，让手动服务通过 `MILIASTRA_WONDERLAND_RUNTIME_CONFIG` 读取原 `runtime.json`。

```toml
[plugins."miliastra-wonderland@miliastra-wonderland".mcp_servers.miliastra-wonderland]
enabled = false
```

**Claude Code** 可在启动客户端的 PowerShell 中设置 `$env:MCP_TIMEOUT = '120000'`，将握手等待设为 120 秒。若此前收紧了工具时限，可在同一终端设置 `$env:MCP_TOOL_TIMEOUT = '960000'`。这两个变量由 Claude Code 读取，单位为毫秒。服务器单独声明 `timeout` 时，工具时限以该声明为准。 [Claude Code 超时设置](https://code.claude.com/docs/en/mcp#time-limits-on-mcp-tool-calls)

**DeepSeek Harness** 通过 Cordis 的 `toolCallTimeoutMs` 配置 MCP 工具时限。随插件安装的值见 [Cordis 接入配置](../cordis.patch.yml)。

## 便携交付重建

用 `verify` 先检查交付清单，再由调用方确认可信输入和重建范围。`trusted_inputs_sha256` 将批准绑定到这组输入。完整调用顺序、校验值和重建产物以[便携交付与重建](../references/workflows/portable-delivery.md)为准。
