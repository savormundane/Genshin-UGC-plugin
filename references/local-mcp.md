# 本地MCP服务

本地stdio服务连接插件现有读取、审计和制作核心，不连接原神编辑器或游戏进程。原神官方未开放的运行态查询、编辑器控制及实机操作不由本服务模拟为已实现。

## 依赖与启动

按[独立运行环境](runtime-environment.md)显式创建插件专用Python环境并安装锁定依赖。工具查询和doctor不自动安装依赖。下面是配置完成后仍兼容的直接CLI入口，python应替换为专用解释器路径。

```text
python scripts/qianxing.py mcp serve --project PATH_TO_PROJECT --output-root PATH_TO_OUTPUTS
```

两个目录必须已存在且互不包含，输出目录不得与插件源码重叠。也可通过UGC_PROJECT_ROOT和UGC_OUTPUT_ROOT环境变量指定；缺失时拒绝启动。包内mcp.json通过Node启动器读取独立runtime.json中的解释器和目录绑定；直接CLI入口仍可显式传参。宿主实际加载与SDK协议调用分别验证。

协议只走stdout，执行日志走stderr或请求临时日志，不混入协议输出。当前提供十八个具名工具：

| 工具 | 参数与行为 |
| --- | --- |
| doctor | 只读检查执行依赖 |
| capabilities | 返回当前实现和证据边界 |
| docs_search | version、query：检索固定版本资料 |
| native_inspect / native_audit / project_inspect | input、sha256：读取或审计指定原生文件 |
| client_check | input、sha256，可选contract与contract_sha256：编译最终正文及API检查 |
| produce | spec、sha256、output：执行已有制作链 |
| native_diff / experiment_compare | input、sha256、other、other_sha256：原生差异或成对观察比较，直接返回报告 |
| native_plan | input、sha256、spec、spec_sha256、output：生成plan.json；source依赖使用显式绝对路径，后续apply继续核对摘要 |
| simulate | spec、sha256、output：schema 2联合场景；在独立工作进程执行，零断言或必需覆盖不足不提交 |
| experiment_run | spec、sha256、output：观察实验，开发／保留种子合同不变；失败不提交 |
| logs_diagnose | spec、sha256：只读解析JSONL及关联产物 |
| verify | input、sha256、rebuild、portable：input必须是交付manifest.json；两个开关为显式布尔，重建使用请求临时目录 |
| native_apply | input、sha256、plan、plan_sha256、output：执行已有摘要绑定原生计划 |

input/spec/plan/contract相对工程根目录，或为工程/输出根内绝对路径。output相对输出根目录，必须是尚不存在的新目录，其父目录须存在。sha256均为对应输入文件原始字节摘要；plan_sha256参数是计划文件摘要，计划内部的语义摘要由原生核心继续核对。

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

每次调用创建输出根下独立临时目录，以固定Python工作进程执行。输入开始/结束核对摘要，成功且通过提交前取消检查后才将产物目录改名为正式输出。已有目录不覆盖。取消时终止本次工作进程，Windows同时终止其进程树；清理仅限该请求的临时目录。成功提交为同步边界，此后到达的取消不能撤回已经提交的产物。

进度依次报告输入绑定、核心运行、结果检查三个阶段。报告不假装掌握底层编译百分比，调用方可以没有进度回调。

路径检查和工作进程的Python文件访问审计用于发现越界依赖，不是操作系统沙箱。Graph Code等工程源码及后端仍须可信；由其自行启动的任意第三方程序不因本工具而获得完整沙箱保证。Python依赖目录与插件自身是允许读取的运行资源。

## 验证与手工交付

开发专项test_mcp_service.py使用真实SDK stdio，覆盖两种中性控件工程的新建GIL和两套已有图的重编号迭代、CLI/MCP读取结果一致、摘要/路径拒绝。只读工具专项补齐doctor、capabilities、docs_search、native_audit、project_inspect和client_check，合计十六个工具均有实际stdio调用。环境诊断返回结果不代表所有依赖可用；能力查询成功不代表全部能力已验收。

独立Bridge专项覆盖嵌套输入越界、取消不提交及临时目录清理；SDK内存传输与实际stdio专项分别取消调用并核对不提交、不残留临时目录。stdio专项还检查输入不变及同一服务取消后可继续响应。宿主UI中的取消通知仍待验，不把SDK客户端测试写成Codex宿主验收。通过PYTHONPATH指定依赖时使用绝对目录，因为工作进程在工程目录执行。

将产物GIL在编辑器中人工导入，核对图和脚本挂载，运行最小交互并记录日志；涉及存储时退出后重新进入回读。将再导出的GIL另存后使用native diff对照。编辑器、平台真实保存重进、运行表现以及Codex/其它宿主加载本MCP均保持待验。

SDK依据：[官方Python SDK](https://py.sdk.modelcontextprotocol.io/)、[进度](https://py.sdk.modelcontextprotocol.io/handlers/progress/)、[取消](https://py.sdk.modelcontextprotocol.io/handlers/cancellation/)。固定依赖和开发安装证据位于development，不能把开发机安装视为用户环境已安装。

新增入口专项使用两种中性配置，串联修改计划与应用、独立模拟、实验比较、日志关联和交付重建；覆盖无断言、错误断言、嵌套依赖越界、摘要不符及已有输出拒绝。所有生成操作仅在核心status为passed时提交；实验passed=false也视为失败。

## V3.5新增入口与启动

`api_lookup(symbol)` 查询来源、原文行、推导类型和冲突；`diagnose(spec, sha256)` 只读执行显式配置的环境、Lua、GIL和素材检查。复用CLI核心，沿用摘要绑定和依赖根边界。安装后的默认入口使用[专用运行环境](runtime-environment.md)，不依赖系统python命令。SDK stdio调用与Codex宿主实际加载分别记录。
