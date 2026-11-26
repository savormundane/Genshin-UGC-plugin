# 组合制作与交付

## 什么时候用 produce

用 `produce` 把相互依赖的产物接到同一份交付。例如先布设机关，再用本轮对象标识编译并挂载节点图，最后嵌入 Lua 和检查最终 GIL。查询、单张图元转换和审阅现有工程修改可直接走[对应任务](../README.md)。从零设计玩法时先按[阶段式制作](staged-production.md)确定实现与验收，再写实际配置。

```text
python scripts/qianxing.py produce JOB.json --out NEW_DIRECTORY --summary
python scripts/qianxing.py verify NEW_DIRECTORY
```

MCP 的 `produce` 接收同一配置的路径、SHA-256 校验值和新输出目录，参数及回执见 [MCP 工具](../../docs/mcp.md)。普通构建可以用同一配置和新的输出目录复跑。需要迁移交付后重建时，使用[可迁移交付](portable-delivery.md)。

## 制作配置

新任务使用顶层 `"schema":2`，按需声明至少一个制作阶段。各子配置有独立 schema，路径相对各自配置文件解析。旧任务见 [顶层 schema 1 配置](produce-schema1.md)。

| 阶段 | 字段与入口 |
| --- | --- |
| 客户端 | `client.source` 指向单文件，或用 `client.assembly` [装配脚本](../editor/lua/client-assembly.md)。`client_check.spec` 可声明额外的 [Lua API 和绑定检查](../editor/lua/client-check.md)。 |
| 关卡基底 | `level.spec` [创建新关卡](../gil/native-authoring.md)，或用 `native.base` 和 `native.spec`／`native.plan` [修改已有 GIL](../gil/native-changes.md)。`native` 与 `level` 互斥，`spec` 与 `plan` 二选一。 |
| 图、协议与存档 | `graphs.spec` [编译或替换节点图](../graph-code/node-graph-workflow.md)；`graphs.include_sources:true` 交付可编辑图源码。`protocol` 声明[信号合同](protocol-v2.md)，用 `protocol_native:true` 生成原生声明。`storage.spec` [生成存档](storage-authoring.md)，可选客户端或服务端传输。 |
| 场景与素材 | `scene.spec` 创建[静态场景 GIA](../editor/native-scene.md)，`scene.whitebox` 导出白盒。`assets` 可生成[单件或批量图元](../assets/image-to-primitives.md)、[拟合素材](../assets/asset-fit.md)或导入 [GIA 素材](../assets/native-assets.md)。`animation` 负责[帧数据](../assets/animation.md)。 |
| Lua 写回与界面 | `gil.mapping` 选择最终脚本的唯一映射名。Lua 写回以最近产出的 GIL 为基底；图阶段只输出 GIA 时沿用它的输入 GIL。`ui.spec` 声明[原生界面检查或调整](../editor/native-ui-layout.md)。 |
| 检查与观察 | `platform.spec`、`project.spec` 和 `resources.spec` 分别执行[平台规则](../platform/platform-profiles.md)、[工程对象和引用](../editor/project-index.md)及[资源](../platform/resource-catalogue.md)检查。`simulation.spec`、`beyond.spec`、`experiment.spec` 分别接入[联合模型](joint-simulation.md)、[Beyond](beyond-backend.md)和[观察实验](algorithms-experiments.md)。 |

```json
{
  "schema": 2,
  "native": {"base": "entrance.gil", "plan": "reviewed-plan.json"},
  "graphs": {"spec": "graphs.json", "include_sources": true}
}
```

图、存档或 Lua 阶段若显式指定基底，其 SHA-256 校验值必须和当前 GIL 一致。构建失败时核对报告指出的阶段、路径和摘要，再用新输出目录重跑。

### 按名称连接制作阶段

给实体、模板、经济配置、拾取模板及 HUD 控件指定 `key`，控件组用 `group_key`。制作链在根目录的 schema 2 `bindings.json` 写入具名键、工程对象键、实际 ID 和最终 GIL 的 `gil_sha256`。具名键必须唯一，且对象须在引用阶段前创建。

- 支持具名引用的配置字段可用 `{"ref":"类型:键"}`。例如挂图目标用 `{"ref":"entity:gate"}`，白盒模板用 `{"ref":"template:sign"}`。Graph Code 用 `native_id("currency:coin")`，编译副本解析为整数，交付保留原始源码。数字 ID 仍可用。编译器检查基底、对象类别和实际身份。 [图绑定与校验](../graph-code/node-graph-workflow.md)
- 基底变化时，从目标工程读取对象键或[重绑已有绑定](../graph-code/node-graph-workflow.md)。无 GIL 的快检和独立 GIA 构建可用 schema 1 绑定表，绑定身份为待查。
- `place_static_scene` 的 `source:"@scene"` 指向本轮布景 GIA；重复布设与下一轮基底的 `layout-bindings.json` 用法见[原生场景](../editor/native-scene.md#重复布设)。
- 拟合阶段用 `kind:"fit"` 命名并绑定基底、图片模板与容器。随后在 `bind_client_lua` 用 `source:"@asset:NAME"` 接入生成的 Lua，声明新增的 `mapping` 及允许改动的字段 `9`、`50`。批量素材用 `kind:"batch"` 接续预算试算，结果在 `asset-batches/<name>/`。导入 GIL 时，`append_client_ui.asset_data` 指向其中的 `data.json`。 [拟合挂载合同](../assets/asset-fit.md#生成可挂载的-lua-和软件预览) · [追加客户端界面](../gil/native-authoring.md#追加客户端界面模块)

`native.after_graphs` 可引用第二份 schema 2 补丁，其 `base_sha256:"@level"` 绑定初次写入和编译后的 GIL。用它给新编译的技能图追加原生技能等后置资源。仍须声明 `allowed_top_level_fields`。结果见 `native-final-report.json` 和 `native-final-diff.json`。 [原生玩法](../editor/native-gameplay.md)

## 写入、模拟与交付

工具核对输入与环境，生成源码和素材，再处理原生基底、严格编译与挂载、Lua 嵌入及最终检查。声明的模型和实验随后运行。任一必需阶段失败、输入变化或输出路径冲突都会阻止提交正式目录。

生成最终 GIL 后，工程检查读取本轮 `level.gil` 的已校准引用。若声明了 `project.spec`，配置中应有且仅有一个 `@level` 输入。最终 Lua 语法检查覆盖 GIL 的全部映射和交付目录中的 Lua，结果写入 `client-check.json`。语法错误、非法正文编码或缺少必需的 Lua 5.3 编译器会阻止提交。额外 API 和引用检查由 `client_check` 声明。平台配置检查的 `artifact_verified=false` 表示只核对了声明，GIL 配置另做回读。

`simulation` 与 `beyond` 可用 `@level` 指向最终 GIL，相关报告写明匹配的文件摘要和脚本映射。仅当所需参与者均与最终 GIL 同源时，场景的 `artifact_scope` 才为 `final_gil`。外部或混合输入的模型结果仍可查，相应最终产物状态保留为 `not_checked`。联合场景的 `simulation.json` 将本轮 `level.gil` 记录为相对交付目录的路径，外部输入仍记录实际绝对路径。

`environment.json` 记录依赖与能力组指纹。`dependency-graph.json` 的 `external_and_tool_inputs` 登记输入和工具摘要，各阶段记录新增输入、依赖和产物变化。交付文件和其角色以 `manifest.json` 为准。用 [verify](portable-delivery.md#验证与边界) 核对清单，再按[交付反馈](validation.md#交付反馈)报告实际检查范围。
