# 本地MCP服务

本地stdio服务连接插件现有读取、审计和制作核心，不连接原神编辑器或游戏进程。原神官方未开放的运行态查询、编辑器控制及实机操作不由本服务模拟为已实现。

## 依赖与启动

按[独立运行环境](runtime-environment.md)显式创建插件专用Python环境并安装锁定依赖。工具查询和doctor不自动安装依赖。下面是配置完成后仍兼容的直接CLI入口，python应替换为专用解释器路径。

```text
python scripts/qianxing.py mcp serve --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

节点、API、平台文档和内置资源查询可在启动后直接使用。文件工具按显式工程路径、会话 MCP Roots、`runtime.json` 的顺序选择工程。会话有多个根时，用输入绝对路径选择其中一处。输出可显式设置，也可使用插件数据目录内按工程分开的默认路径。只读请求使用独立临时目录，无需创建输出目录。`doctor` 的 `project_context` 记录目录、来源、候选及缺失项。 [工程绑定](runtime-environment.md#连接-mcp-或切换工程)

协议走 stdout，执行日志走 stderr 或请求临时日志。实际工具清单由 `capabilities` 报告。

| 工具 | 参数与行为 |
| --- | --- |
| doctor | 返回依赖状态、当前加载路径、版本、原能力指纹和 `plugin.capability_groups` 分组摘要。用 CLI `doctor --compare PLUGIN_ROOT` 定位同版本的文件差异 |
| capabilities | 返回当前实现和证据边界 |
| api_lookup | symbol。接受客户端 Lua 的正式符号、英文片段或中文用途。返回正式符号、原文说明、来源与推导状态 |
| diagnose | spec、sha256。按配置执行只读的环境、Lua、GIL 和素材检查 |
| docs_search | version、query：检索固定版本资料 |
| nodes_lookup | query、scope、limit 均可选。查询 Graph Code 调用、作用域、签名和端口。scope 为 all、client 或 server，limit 默认 20，范围 1 到 100 |
| graph_check | input 指向一张 Graph Code 源文件。可给 job 载入制作任务，或给 bindings 提供具名绑定。sha256、job_sha256、bindings_sha256 可选，工具返回直接输入和实际读取的项目依赖摘要 |
| resources_lookup | version、query、mode、limit。查模型候选和原生样本中的模板 ID。可选 catalogue 和 catalogue_sha256，未给摘要时由服务计算 |
| native_inspect / native_audit | input，可选 sha256。读取或审计指定原生文件 |
| scene_preview | input、output，可选 before、sha256、before_sha256。绘制已解析的实体点位及白盒轮廓，输出 PNG、layout.json 和覆盖摘要 |
| asset_preview | input、output，可选 sha256、max_controls、step。试算单张 PNG 的矩形图元方案，返回各方案的控件数、误差、预算结果及预览路径，附 `report.json` 的摘要 |
| asset_generate | input、sha256、report、report_sha256、candidate、output。用已选候选生成矩形图元或试算报告指定的素材，返回参考 PNG、实际控件数和产物摘要 |
| project_inspect | input，可选 sha256、scope。用 query、kind、limit 搜索对象，用 selector、transitive 查精确目标和关系，或用 summary 查看对象数。`scope="scene"` 查询 3D，`scope="gameplay"` 查询玩法资源 |
| client_check | input，可选 sha256、mapping、contract、contract_sha256。编译 Lua 正文，可选择单个 GIL 映射或检查 API 合同 |
| produce | spec、sha256、output：执行已有制作链 |
| native_diff | input、other，可选 sha256、other_sha256、allowed_top_level_fields。给出允许范围时，核对其余字段的原始字节 |
| experiment_compare | input、sha256、other、other_sha256。直接返回成对观察比较 |
| native_plan | input、sha256、output 加一个 patch 对象，或加 spec 和 spec_sha256 文件参数。输出可审阅的 plan.json 和文件摘要 |
| simulate | spec、sha256、output。执行 schema 2 场景，或以失败报告复跑其原始输入。失败返回 `result.diagnostics` 和可用的 `result.replay`，通过时提交输出 |
| experiment_run | spec、sha256、output：观察实验，开发／保留种子合同不变；失败不提交 |
| logs_diagnose | spec、sha256：只读解析JSONL及关联产物 |
| verify | input 指向交付 manifest.json，sha256 必填。artifacts_only、portable、rebuild 默认为 false。仅产物校验独立运行。重建还需 portable=true 和 trusted_inputs_sha256 |
| native_apply | input、sha256、plan、plan_sha256、output：执行已有摘要绑定原生计划 |

input/spec/plan/contract/report 相对工程根目录，或为工程根或输出根内的绝对路径。output 相对输出根目录，必须是尚不存在的新目录，其父目录须存在。sha256 均为对应输入文件的原始字节摘要。plan_sha256 参数是计划文件摘要，计划内部的语义摘要由原生核心继续核对。

带可选摘要的工具在省略时自行计算，并在 `inputs_sha256` 按参数名返回。编辑既有 GIL 时可把 `inputs_sha256.input` 交给 `native_plan`。配置诊断、修改计划、原生写入和重建继续使用各自的必填摘要。

## 单张 PNG 试算与生成

用 `asset_preview` 比较候选，选好后用 `asset_generate`。参数、摘要和交付文件见[单张 PNG 试算与生成](../references/assets/image-to-primitives.md#单张-png-试算与生成)。

## 审阅并另存已有工程

从 `project_inspect` 定位对象，用 `native_plan` 生成待审计划。确认后用 `native_apply` 另存，按实际保护范围核对差异。[调用步骤](../references/gil/native-changes.md#审阅并另存已有工程)
## CLI与MCP共同合同

```text
python scripts/qianxing.py mcp call request.json --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

```json
{"schema":2,"operation":"native_inspect","arguments":{"input":"level.gil","sha256":"填写实际文件摘要"}}
```

CLI call与MCP同一Bridge调度，结果封装为schema、operation、status、result、output。读取结果与现有核心一致；未知操作、输入摘要不符、越界路径和已有输出拒绝。没有任意shell、Python代码或任意命令参数入口。

produce复用实际制作链，native_apply复用native_changes.apply_plan；不能用调用成功替代报告内的not_checked或failed。stdio工具参数错误由SDK返回工具错误，核心工作失败返回结构化failed和诊断；CLI对应非零退出。

## 取消和输出保护

每次调用在独立临时目录内用固定 Python 工作进程执行，写入任务在输出根内暂存。输入开始和结束时核对摘要，成功且通过提交前取消检查后才将产物目录改名为正式输出。已有目录不覆盖。取消时终止本次工作进程，Windows 同时终止其进程树。清理仅限该请求的临时目录。

进度依次报告输入绑定、核心运行和结果检查。普通操作默认时限 120 秒，制作、应用和重建为 900 秒。可分别设置 `UGC_MCP_TIMEOUT_SECONDS` 和 `UGC_MCP_BUILD_TIMEOUT_SECONDS`，范围为大于 0 且不超过 3600 秒。

路径检查和工作进程的Python文件访问审计用于发现越界依赖，不是操作系统沙箱。Graph Code等工程源码及后端仍须可信；由其自行启动的任意第三方程序不因本工具而获得完整沙箱保证。Python依赖目录与插件自身是允许读取的运行资源。

## 本地复现

公开仓库的 stdio 检查可复现一次完整的关卡参数编辑。编辑器导入和实际游戏运行需要对应的工程证据。[公开复现](contributing/development.md#复现已有工程的修改流程) · [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/)

## 便携交付重建

重建需要审阅待执行的工程输入并确认摘要。静态检查结果包含这个摘要。[重建边界](../references/workflows/portable-delivery.md)

Portable 调用顺序：

1. 对交付 `manifest.json` 调用 `verify`，传入其 `sha256`、`portable=true` 和 `rebuild=false`。
2. 展示静态报告和待执行的工程输入，让调用方审阅并明确批准该次重建。
3. 获得批准后仍使用同一清单和摘要，传入 `portable=true`、`rebuild=true` 以及报告中的 `trusted_inputs_sha256`。输入变化时重新静态核对及审阅。自动化流程只拿到摘要时停在静态核对。
