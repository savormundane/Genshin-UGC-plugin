# 本地MCP服务

本地stdio服务连接插件现有读取、审计和制作核心，不连接原神编辑器或游戏进程。原神官方未开放的运行态查询、编辑器控制及实机操作不由本服务模拟为已实现。

## 依赖与启动

按[独立运行环境](../docs/runtime-environment.md)显式创建插件专用Python环境并安装锁定依赖。工具查询和doctor不自动安装依赖。下面是配置完成后仍兼容的直接CLI入口，python应替换为专用解释器路径。

```text
python scripts/qianxing.py mcp serve --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

节点、API、平台文档和内置资源查询可在启动后直接使用。文件工具按显式工程路径、会话 MCP Roots、`runtime.json` 的顺序选择工程。会话有多个根时，用输入绝对路径选择其中一处。输出可显式设置，也可使用插件数据目录内按工程分开的默认路径。只读请求使用独立临时目录，无需创建输出目录。`doctor` 的 `project_context` 记录目录、来源、候选及缺失项。 [工程绑定](../docs/runtime-environment.md#连接-mcp-或切换工程)

协议走 stdout，执行日志走 stderr 或请求临时日志。实际工具清单由 `capabilities` 报告。

| 工具 | 参数与行为 |
| --- | --- |
| doctor | 返回依赖状态、当前加载路径、版本、原能力指纹和 `plugin.capability_groups` 分组摘要。用 CLI `doctor --compare PLUGIN_ROOT` 定位同版本的文件差异 |
| capabilities | 返回当前实现和证据边界 |
| api_lookup | symbol。查询客户端 Lua API、来源与推导状态 |
| diagnose | spec、sha256。按配置执行只读的环境、Lua、GIL 和素材检查 |
| docs_search | version、query：检索固定版本资料 |
| nodes_lookup | query、scope、limit 均可选。查询 Graph Code 调用、作用域、签名和端口。scope 为 all、client 或 server，limit 默认 20，范围 1 到 100 |
| graph_check | input 指向一张 Graph Code 源文件。可给 job 载入制作任务，或给 bindings 提供具名绑定。sha256、job_sha256、bindings_sha256 可选，工具返回直接输入和实际读取的项目依赖摘要 |
| resources_lookup | version、query、mode、limit。查模型候选和原生样本中的模板 ID。可选 catalogue 和 catalogue_sha256，未给摘要时由服务计算 |
| native_inspect / native_audit | input，可选 sha256。读取或审计指定原生文件 |
| scene_preview | input、output，可选 before、sha256、before_sha256。绘制全场布局及前后对照，输出 PNG 和 layout.json |
| asset_preview | input、output，可选 sha256、max_controls、step。试算单张 PNG 的矩形图元方案，返回各方案的控件数、误差、预算结果及预览路径 |
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

input/spec/plan/contract相对工程根目录，或为工程/输出根内绝对路径。output相对输出根目录，必须是尚不存在的新目录，其父目录须存在。sha256均为对应输入文件原始字节摘要；plan_sha256参数是计划文件摘要，计划内部的语义摘要由原生核心继续核对。

带可选摘要的工具在省略时自行计算，并在 `inputs_sha256` 按参数名返回。编辑既有 GIL 时可把 `inputs_sha256.input` 交给 `native_plan`。配置诊断、修改计划、原生写入和重建继续使用各自的必填摘要。

`asset_preview` 的 `result.candidates` 包含各方案的 `controls` 和相对于 `output` 的 `display_preview`。MCP 随响应附上原方案和一个低控件数备选的缩略 PNG（有备选时）。指定 `max_controls` 后，查看候选的 `within_budget` 和报告的 `recommendations` 选择方案。输出目录的 `report.json` 可交给 [assets generate](asset-generation.md)。预览以离线参考图为准，游戏内渲染待实测。

## 审阅并另存已有工程



1. 调用 `project_inspect`，例如传入 `{"input":"level.gil","selector":{"kind":"template","id":1086324737}}`。复用 `inputs_sha256.input`。追踪一个模板参数时，可选中变量的完整 `key` 并开启 `transitive`。
2. 给 `native_plan` 传入基底的 `input`、`sha256` 和新 `output`，将包含 `allowed_top_level_fields` 和 `operations` 的 schema 2 对象作为 `patch`。工具会写入已验证的 `base_sha256`。若内联补丁也提供该字段，两处摘要须一致。内联 `source` 相对当前工程。文件补丁沿用自身的基底摘要和路径规则，并在调用中提供 `spec_sha256`。
3. 审阅 `result.difference`。确认后调用 `native_apply`，使用同一基底和新输出目录。用计划 `output` 目录下的 `plan.json` 作为 `plan`，用 `outputs_sha256["plan.json"]` 作为 `plan_sha256`。
4. `native_apply` 返回另存的 `level.gil`、实际操作和审计结果，以及 `outputs_sha256`。用 `native_diff` 的 `allowed_top_level_fields` 核对保护范围，或将 `manifest.json` 和对应摘要交给 `verify` 做静态完整性检查。计划和应用清单均记录外部来源摘要。

摘要错配、路径和参数冲突会返回具体原因。保护检查失败时仍可读取 `result.protected`。编辑器重存后可以[重新比较](native-changes.md#人工再导出核对)。

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

公开仓库的 stdio 检查可复现一次完整的关卡参数编辑。编辑器导入和实际游戏运行需要对应的工程证据。[公开复现](../docs/contributing/development.md#复现已有工程的修改流程) · [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/)

## 便携交付重建

重建需要审阅待执行的工程输入并确认摘要。静态检查结果包含这个摘要。[重建边界](portable-delivery.md)

Portable 调用顺序：

1. 对交付 `manifest.json` 调用 `verify`，传入其 `sha256`、`portable=true` 和 `rebuild=false`。
2. 展示静态报告和待执行的工程输入，让调用方审阅并明确批准该次重建。
3. 获得批准后仍使用同一清单和摘要，传入 `portable=true`、`rebuild=true` 以及报告中的 `trusted_inputs_sha256`。输入变化时重新静态核对及审阅。自动化流程只拿到摘要时停在静态核对。
