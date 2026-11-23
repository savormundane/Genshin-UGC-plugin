
# GIL 组装流水线

把 Graph Code、信号定义和客户端 Lua 组装成一个自包含 `.gil`。本流程横跨 qianxing-graph-code（源码与验证）和 qianxing-gil（GIL 读写原语），负责写回顺序和交付前验证。

类型适配和图补丁必须回读最终文件，沿源输出声明检查目标输入；转换时新增节点不能遗漏重接，也不能把原始结构体列表边全部替换为字段列表边。具体见 [原生数据流检查](../../../native-dataflow-validation.md)。模型通过、节点引用存在和写入回包均不能代替该检查或跨次保存验证。

## 选择路径

### 首选：项目构建 / 项目写回

项目存档中已有节点图、信号、结构体或 UI 配置时，优先使用插件内置 Ayaya 的项目写回。以下命令从插件根目录执行；PLUGIN_PYTHON表示运行配置中的Python绝对路径：

```bash
PLUGIN_PYTHON -X utf8 -B scripts/qianxing.py build build.json --out <新交付目录>
```

`build.json` 的 `include_sections` 可选 `graphs` / `signals` / `structs` / `templates` / `instances`；含 `graphs` 以外的 section 时必须提供 `project_resources`。完整 schema、写回范围和挂载校验见 [节点图制作工作流](../../../node-graph-workflow.md)。

只做基底写回时：

```bash
PLUGIN_PYTHON -X utf8 -B scripts/ayaya_bridge.py --execute \
  --project <项目存档目录> --input <基底.gil> --output <新输出.gil> project-import
```

桥接层拒绝原位覆盖、输出已存在和跳过校验参数；写回范围用上游 `--selection-json` 或 `--skip-*` 限定。文件通常被收口到包内 `vendor/ayaya/private_extensions/ugc_file_tools/out`，以报告路径为准，不要假设 `--output` 的绝对路径就是落盘路径。

包内 `run_ugc_file_tools.py project import` 一次完成元件库、实体、结构体、信号、节点图和 UI 控件模板写回，信号相关的 `--signals-template-gil`、`--signals-bootstrap-template-gil`、`--signals-param-build-mode semantic`、`--no-signals-emit-reserved-placeholder-signal` 通过桥接层的 `--` 之后透传；有项目存档时不需要低层四步流水线。

### 低层手动：四步流水线

只有 GraphModel JSON、信号 spec 和 base GIL，或需要精确控制写回步骤时使用。`add_signal_definition_to_gil` 与 `graph_model_json_to_gil_node_graph` 在插件内置 CLI 中未作为 `tool` 子命令暴露，可使用包内vendor/ayaya后端：

```bash
export AYAYA="<插件根目录>/vendor/ayaya"
cd "$AYAYA"
```

以下顺序不可调换。

#### Step 1: 准备 base GIL

用结构化配置生成新基底，或读取当前项目已有GIL：

```bash
# 从本流程目录执行
PLUGIN_PYTHON scripts/qianxing.py level create LEVEL.json --out NEW.gil
```

base 需要包含基础设施段（header、实体框架等），不需要包含信号或节点图。完整模板列表与验证要求见 [模板生成参考](../../../../skills/qianxing-gil/references/template-generation.md)。

#### Step 2: 写入信号定义

使用 `add_signal_definition_to_gil` 把信号定义写入 GIL。**必须在节点图写回之前执行**，否则节点图中的信号 type_id 无法提升为 signal-specific runtime_id，服务器信号会错位或不触发。

```bash
PLUGIN_PYTHON -X utf8 -B private_extensions/run_ugc_file_tools.py tool --dangerous add_signal_definition_to_gil \
  --input-gil "private_extensions/ugc_file_tools/builtin_resources/empty_base_samples/empty_base_with_infra.gil" \
  --output-gil with_signals.gil \
  --spec-json "<信号 spec.json>" \
  --bootstrap-template-gil "private_extensions/ugc_file_tools/builtin_resources/seeds/signal_node_def_templates.gil" \
  --param-build-mode semantic
```

- 新信号集或空壳 base：使用 `empty_base_with_infra.gil` 作为 `--input-gil`，并显式提供 `--bootstrap-template-gil signal_node_def_templates.gil`。
- 已有项目 GIL：可以直接作为 `--input-gil`；已存在的同名信号会被跳过。若报 `node def name mismatch`，先用空基底 + bootstrap 写信号，再写节点图。
- 不要把项目 GIL 当作 bootstrap 模板；它缺少所需的 node_def 基底。
- `--param-build-mode semantic`（默认）按 type_id 规则构造参数口；`template` 需要模板覆盖所有参数类型。
- `--output-gil` 只给文件名，输出会被强制写入编辑器的 `ugc_file_tools/out/`。

spec.json 格式、type_id 映射和参数约束见 [信号写回](signal-writeback.md) 与 [spec.json 格式](spec-json-format.md)。

#### Step 3: 编译节点图

用 `graph_model_json_to_gil_node_graph` 把 GraphModel JSON 写入 GIL 的节点图段（field 10）：

```bash
PLUGIN_PYTHON -X utf8 -B private_extensions/run_ugc_file_tools.py tool --dangerous graph_model_json_to_gil_node_graph \
  --graph-json "<GraphModel.json>" \
  --template-gil with_signals.gil \
  --output-gil with_graph.gil \
  --template-graph-id <server_graph_id_int> \
  --new-graph-name "<节点图名称>" \
  --skip-precheck
```

- **不要用 `--pure-json` 交付**：该模式不克隆现有 node/record 模板，产出的节点图缺少 UI 依赖字段，只适合诊断。交付始终使用 template-based 模式（提供 `--template-gil`）。
- `--template-graph-id` 是模板 GIL 中用于取样的 server graph 的 graph_id_int；用 `gil-toolkit.mjs inspect` 或 `gil-generator.mjs inspect-structure` 查看。
- `--skip-precheck` 仅用于已知误报：信号节点通用 type_id 300000/300001/300002 在 Step 2 写入后被提升为 signal-specific runtime_id，但 precheck 仍按通用 type_id 查找模板样本而报缺口。不要用它掩盖真实节点模板缺失。
- `ayaya_bridge.py` 会拒绝 `--skip-precheck` 与 `--non-strict`；需要这些标志时只能直接调用编辑器 CLI，并在交付报告中记录原因。

GraphModel 的导出方式见 [GraphModel 导出](graph-model-export.md)。

#### Step 4: 嵌入 Lua 并验证

用 `gil-toolkit.mjs` 注入客户端/服务端 Lua 脚本，然后检查最终产物。以下命令从插件根目录执行；PLUGIN_PYTHON表示运行配置中的Python绝对路径：

```bash
# 替换服务端脚本
node scripts/gil-toolkit.mjs replace-lua \
  with_graph.gil "服务端脚本名" server_code.lua output.gil

# 替换客户端脚本
node scripts/gil-toolkit.mjs replace-lua \
  output.gil "客户端脚本名" client_code.lua output_final.gil

# 检查容器、字段与脚本映射
node scripts/gil-toolkit.mjs inspect output_final.gil

# 清点图/信号/Lua/挂载
PLUGIN_PYTHON -X utf8 -B scripts/qianxing.py inspect output_final.gil
```

在外部编辑器根目录检查信号表：

```bash
PLUGIN_PYTHON -X utf8 -B private_extensions/run_ugc_file_tools.py tool inspect_gil_signals --input-gil "<最终.gil>"
```

验证清单：

- [ ] `roundtripByteIdentical: true`（编解码无损）
- [ ] field 10 节点图非空
- [ ] signal entry 的 param_count 与节点图中信号节点的参数 pin 数量一致
- [ ] field 50 脚本映射包含客户端 Lua
- [ ] 实体挂载指向正确的 graph_id / graph_name
- [ ] `changed_top_level_fields` 或快照比较只包含预期字段
- [ ] 明确记录未验证项：编辑器导入、实机运行、原生结算

## 排序约束原理

`add_signal_definition_to_gil` 在 GIL 的 signal entries 中分配 signal_index 和对应的 node_def_id（send/listen/server 三连号）。`graph_model_json_to_gil_node_graph` 写回节点图时，会把 GraphModel 中信号节点的通用 type_id（300000/300001/300002）提升为已写入的 signal-specific node_def_id。顺序反过来时，节点图先写入找不到 signal entry 映射，type_id 无法提升，运行时按通用节点解释，导致端口错位或信号不触发。

## 常见问题排查

| 症状 | 原因 | 修复 |
|------|------|------|
| 节点图为空（field 10 无内容） | 使用了 `--pure-json` 模式 | 改用 template-based 模式，提供 `--template-gil` |
| 服务器信号报错 / 信号不触发 | 信号在节点图之后写入，type_id 不匹配 | 重新执行 Step 2 → Step 3，确保信号先行 |
| precheck 报 node_template_coverage 缺口 | 通用信号 type_id 300000/300001/300002 无模板样本 | 仅对已知误报加 `--skip-precheck`，并记录 |
| `add_signal_definition_to_gil` 报 node_def 构建失败 | 模板 GIL 不含无参信号基底 | 换用 `signal_node_def_templates.gil` |
| `node def name mismatch` | 项目 GIL 被当作 bootstrap 基底 | 用 `empty_base_with_infra.gil` + bootstrap 模板 |
| inspect 显示 signal param_count=0 但节点图有参数 pin | spec 参数未正确解析 | 检查 spec JSON 的 `params` 数组和 type_id |
| `--dangerous` 被拒绝 | 标志位置错误 | 放在 `tool` 之后、子命令之前 |
| 输出文件不在指定绝对路径 | 上游把输出收口到 `ugc_file_tools/out/` | 以命令报告的实际路径为准 |

## 工具路径

| 工具 | 位置 |
|------|------|
| `gil-toolkit.mjs` | 插件根 `scripts/gil-toolkit.mjs`；本流程目录用 `scripts/gil-toolkit.mjs` |
| 原生结构生成 | `scripts/qianxing.py level create` |
| `qianxing.py build` / `inspect` | 插件根 `scripts/qianxing.py`；本流程目录用 `scripts/qianxing.py` |
| `ayaya_bridge.py` | 插件根 `scripts/ayaya_bridge.py` |
| `project import`（信号+节点图+UI 一次写回） | 包内 `vendor/ayaya/private_extensions/run_ugc_file_tools.py project import --dangerous ...`，或用 `ayaya_bridge.py ... project-import` 包装 |
| `add_signal_definition_to_gil` | 外部 Ayaya 编辑器 `private_extensions/run_ugc_file_tools.py tool --dangerous ...` |
| `graph_model_json_to_gil_node_graph` | 同上 |
| `inspect_gil_signals` | 同上（只读工具，无需 `--dangerous`） |
| `signal_node_def_templates.gil` | 编辑器 `private_extensions/ugc_file_tools/builtin_resources/seeds/signal_node_def_templates.gil`；插件 vendor 内有副本 |

## 与其他技能的边界

- **qianxing-graph-code**：Graph Code 编写、Ayaya 验证、导出 GraphModel JSON。本流程从 JSON/源码产物开始。
- **qianxing-gil**：GIL 基础读写原语（inspect、replace-lua、模板生成、结构诊断）。本流程编排这些原语完成端到端组装。
- **Qianxing Editor**：编辑器内的脚本映射、挂载、UI 配置及 Lua 5.3 客户端控件代码编写。
- **共享多人流程（Graph Code / Client Lua）**：协议、信号合同与状态机设计。本流程只负责把已定义的信号与图写入 GIL。

schema 2可在同一 [制作链](../../../production-v2.md) 调度 [原生图替换与挂载](../../../native-maintenance.md)、[保存／成就](../../../storage-authoring.md) 及 [源码装配](../../../client-assembly.md)。严格编译之后仍审计最终GIL，指定模型读取实际产物；必需阶段失败不提交正式输出。
