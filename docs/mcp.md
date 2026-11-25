# 本地 MCP 服务

stdio 服务提供本地文件读取、审计和制作工具。编辑器导入和游戏内运行按[验证等级](../references/workflows/validation.md)单独核对。

## 依赖与启动

客户端用 Node 运行启动器，也可用具备锁定依赖的 Python 直接启动 stdio。 [环境依赖](compatibility.md#运行要求) · [工程绑定](runtime-environment.md#连接-mcp-或切换工程)

```text
python scripts/qianxing.py mcp serve --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

协议使用 stdout，执行日志使用 stderr 或请求临时日志。以 `tools/list` 返回的参数和 `capabilities` 报告的能力为准。

| 工具 | 参数与行为 |
| --- | --- |
| doctor | 返回依赖状态、当前加载路径、版本、原能力指纹和 `plugin.capability_groups` 分组摘要。用 CLI `doctor --compare PLUGIN_ROOT` 定位同版本的文件差异 |
| capabilities | 返回当前实现和证据边界 |
| api_lookup | symbol。接受客户端 Lua 的正式符号、英文片段或中文用途。返回正式符号、原文说明、来源与推导状态 |
| diagnose | spec、sha256。按配置执行只读的环境、Lua、GIL 和素材检查 |
| docs_search | version、query：检索固定版本资料 |
| nodes_lookup | query、scope、limit 均可选。查询 Graph Code 调用、作用域、签名和端口。scope 为 all、client 或 server，limit 默认 20，范围 1 到 100 |
| graph_check | input 指向一张 Graph Code 源文件。可给 job 载入制作任务，或给 bindings 提供具名绑定。sha256、job_sha256、bindings_sha256 可选，工具返回直接输入和实际读取的项目依赖摘要 |
| resources_lookup | version 必填。可选 query、mode（默认 beyond）、limit（默认 20）、catalogue、catalogue_sha256。默认查询模型和模板 ID，设置 resource_type 可查音效 `sound` 或特效 `effect` |
| native_inspect / native_audit | input，可选 sha256。读取或审计指定原生文件 |
| scene_preview | input、output，可选 sha256。绘制场景草案 JSON 或 GIL 的点位及可识别轮廓。GIL 可用 before 和 before_sha256 对照 |
| scene_catalogue | input、sha256、version、mode、output。从实际 GIL/GIA 提取布景模板和样本摘要，生成 models.json |
| scene_build | spec、sha256、output。按已审阅的布景配置和样本证据生成静态 scene.gia，校验回读 |
| asset_preview | input、output，可选 sha256、max_controls、step。试算单张 PNG 的矩形图元方案，返回各方案的控件数、误差、预算结果及预览路径，附 `report.json` 的摘要 |
| asset_generate | input、sha256、report、report_sha256、candidate、output。用已选候选生成矩形图元或试算报告指定的素材，返回参考 PNG、实际控件数和产物摘要 |
| asset_fit | input、spec、output。用内置拟合处理图片或分层清单，返回误差、边缘检查和控件数。可选 sha256、spec_sha256、steps、resume、resume_sha256、initial、initial_sha256。配置 mount 可生成 Lua 和 Beyond 预览配置 |
| project_inspect | input，可选 sha256、scope。用 query、kind、limit 搜索对象，用 selector、transitive 查精确目标和关系，或用 summary 查看对象数。`scope="scene"` 查询 3D，`scope="gameplay"` 查询玩法资源 |
| client_check | input，可选 sha256、mapping、contract、contract_sha256。编译 Lua 正文，可选择单个 GIL 映射或检查 API 合同 |
| produce | spec、sha256、output，可选 summary。执行已有制作配置并校验交付 |
| native_diff | input、other，可选 sha256、other_sha256、allowed_top_level_fields。给出允许范围时，核对其余字段的原始字节 |
| experiment_compare | input、sha256、other、other_sha256。直接返回成对观察比较 |
| native_plan | input、sha256、output 加一个 patch 对象，或加 spec 和 spec_sha256 文件参数。可选 summary。输出可审阅的 plan.json 和文件摘要 |
| simulate | spec、sha256、output。默认执行联合场景或复跑此前失败。传 preview=true 时执行 Beyond 配置并返回软件 PNG、控件树、日志和产物摘要 |
| experiment_run | spec、sha256、output：观察实验，开发／保留种子合同不变；失败不提交 |
| logs_diagnose | spec、sha256。只读解析 JSONL 或支持的编辑器二进制调试日志，并返回可核对的关联证据 |
| verify | input 指向交付 manifest.json，sha256 必填。artifacts_only、portable、rebuild 默认为 false。仅产物校验独立运行。重建还需 portable=true 和 trusted_inputs_sha256 |
| native_apply | input、sha256、plan、plan_sha256、output：执行已有摘要绑定原生计划 |

输入文件路径相对工程根目录，或使用工程根、输出根内的绝对路径。output 指向输出根内尚不存在的目录。父目录须存在，按工程生成的默认输出根可由工具创建。sha256 均为对应输入文件的原始字节摘要。`plan_sha256` 参数核对计划文件字节，计划内的同名字段核对计划语义。

带可选摘要的工具在省略时自行计算，并在 `inputs_sha256` 按参数名返回。编辑既有 GIL 时可把 `inputs_sha256.input` 交给 `native_plan`。配置诊断、修改计划、原生写入和重建继续使用各自的必填摘要。

调用步骤见 [PNG 试算与生成](../references/assets/image-to-primitives.md#单张-png-试算与生成) · [拟合与预览](../references/assets/asset-fit.md#生成可挂载的-lua-和软件预览) · [静态布景](../references/editor/native-scene.md) · [诊断日志](../references/workflows/client-simulation.md#读取编辑器调试日志) · [审阅并另存已有工程](../references/gil/native-changes.md#审阅并另存已有工程)。

## CLI 与 MCP 共同合同

```text
python scripts/qianxing.py mcp call request.json --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

```json
{"schema":2,"operation":"native_inspect","arguments":{"input":"level.gil","sha256":"填写实际文件摘要"}}
```

CLI 和 MCP 复用同一调度，结果包含 `schema`、`operation`、`status`、`result` 和 `output`。参数错误由 SDK 返回工具错误，执行失败返回结构化结果和诊断，CLI 对应非零退出。任务的检查范围和结果由产物报告记录。

## 取消和输出保护

每次调用在独立临时目录内用固定 Python 工作进程执行，写入任务在输出根内暂存。输入开始和结束时核对摘要，成功且通过提交前取消检查后才将产物目录改名为正式输出。已有目录不覆盖。取消时终止本次工作进程，Windows 同时终止其进程树。清理仅限该请求的临时目录。

进度依次报告输入绑定、核心运行和结果检查。普通操作默认时限 120 秒，制作、拟合、应用和重建为 900 秒。可分别设置 `MILIASTRA_WONDERLAND_MCP_TIMEOUT_SECONDS` 和 `MILIASTRA_WONDERLAND_MCP_BUILD_TIMEOUT_SECONDS`，范围为大于 0 且不超过 3600 秒。

路径检查和工作进程的Python文件访问审计用于发现越界依赖，不是操作系统沙箱。Graph Code等工程源码及后端仍须可信；由其自行启动的任意第三方程序不因本工具而获得完整沙箱保证。Python依赖目录与插件自身是允许读取的运行资源。

## 便携交付重建

使用相同清单和摘要按以下顺序调用。 [重建边界](../references/workflows/portable-delivery.md)

1. 对交付 `manifest.json` 调用 `verify`，传入其 `sha256`、`portable=true` 和 `rebuild=false`。
2. 展示静态报告和待执行的工程输入，让调用方审阅并明确批准该次重建。
3. 获得批准后仍使用同一清单和摘要，传入 `portable=true`、`rebuild=true` 以及报告中的 `trusted_inputs_sha256`。输入变化时重新静态核对及审阅。自动化流程只拿到摘要时停在静态核对。
