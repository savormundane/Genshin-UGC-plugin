# 组合制作与交付

## 什么时候用 produce

需要把多个阶段接到同一份关卡时，用 `produce` 执行已确定的制作配置。例如先布设机关，再用本轮实际产生的对象标识编译并挂载节点图，最后写入 Lua。需要按同一配置复跑，或要验证本轮最终 GIL 与软件模拟使用的是同一份产物，也从这里进入。

单项任务从[任务入口](../README.md)直接调用工具。比如 PNG 的试算和生成有独立入口，GIL 的局部修改用可审阅的[修改计划](../gil/native-changes.md)。已有工程以用户选定的基底为准，先确定目标平台版本和模式、需要的产物和允许修改的范围。完整新玩法可由 Editor 按[阶段式制作](staged-production.md)协调，先验证进入、操作、结果和重开，再按实际需求接入多人、存档和自定义资源。

用终端可执行下方命令。有本地 MCP 的客户端也可调用 `produce`，传入已保存的配置、配置文件摘要和新输出目录。检查实际产物与清单，用 `verify` 核对交付。需要把交付移到其他位置重建时，见[可迁移交付](portable-delivery.md)。

## 制作配置

新制作配置使用 schema 2，工具按所选阶段检查依赖。已有 [Schema 1 制作配置](produce-schema1.md)在 1.x 仍可独立执行，计划在 V2.0.0 移除该入口。

schema 2支持client、level、storage、native、assets、protocol、protocol_native、animation、graphs、gil、simulation、experiment、platform、project，至少一项；可增加portable配置启用[可迁移制作与重建](portable-delivery.md)。client选择source或assembly；其余阶段以spec路径引用同名指南中的配置。native选择base，以及spec或[摘要绑定plan](../gil/native-changes.md)其中之一；与level新建互斥。所有配置相对各自文件解析，输出必须是新目录。

可选 `scene` 阶段见[原生 3D 场景](../editor/native-scene.md)，以 `spec` 引用布局并生成独立 GIA。制作清单记录布局、目录、原生样本和产物摘要。

原生创作可在 `native.spec` 使用 `place_static_scene` 和 `"source":"@scene"` 把本次布局写到 GIL。用 `graphs.include_sources:true` 保留可编辑图源码。挂载使用图名、`section` 和 `entity_id`。实例也可用 `entity_key` 定位，或用 `"entity_id":{"ref":"entity:gate"}` 引用本轮布设的对象。

对于需要多次调整的布局，`native.spec` 或 `native.plan` 可使用 [`arrange_instances`](../editor/native-scene.md#重复布设)。后续图挂载沿用布局的 `entity:` 键。交付中的 `layout-bindings.json` 只包含布局实例，绑定完成挂图和后续编辑的最终 `level.gil`。下一轮将这两个文件作为基底和上一轮映射。布局与旧映射都进入交付输入记录和可迁移闭包。

`assets` 中的 `kind:"batch"` 从[预算试算报告](../assets/image-to-primitives.md#多素材共用控件预算)生成 `asset-batches/<name>/`。要将已生成的批量数据写进已有 GIL，用 [`append_client_ui`](../gil/native-authoring.md#追加客户端界面模块) 的 `asset_data` 引用该目录中的 `data.json`。

### 按名称连接制作阶段

给原生实体、模板、经济配置、拾取模板及 HUD 控件指定 `key`。控件组使用 `group_key`。制作链把具名键、工程对象键和实际 ID 写入交付根目录的 schema 2 `bindings.json`，同时登记交付 GIL 的 `gil_sha256`。同一具名键只能绑定一个对象。声明应出现在引用之前。

- 场景原型、复制来源、元件摆放、图挂载、商店物品和价格、持有物品与拾取模板可用 `{"ref":"类型:键"}`。例如商店价格的 `currency` 用 `{"ref":"currency:coin"}`。白盒导出可用 `"source":"@level","template_id":{"ref":"template:sign"}`。
- Graph Code 中使用 `native_id("currency:coin")`。编译副本解析为整数，交付保留原始源码。在图构建 JSON 中填写 `bindings` 路径时，构建核对当前基底摘要、对象类别、工程对象键和 ID。
- 基底变化后，从 `project inspect BASE.gil --scope gameplay` 查目标对象键。将 `{"currency:coin":"level/currency/1115684865"}` 这样的键映射写入选择器文件，运行 `graph bind BASE.gil --spec SELECTORS.json --out bindings.json`。无 GIL 上下文的快检和独立 GIA 构建仍可用 schema 1 表，报告绑定身份为待检查。
- 路径相对各自配置解析。手工填入的数字 ID 继续可用。补丁末尾的 `native.after_graphs` 可以使用前序键，并给新技能登记 `skill` 键。编译阶段使用该阶段已经存在的绑定。 [图编译与校验](../graph-code/node-graph-workflow.md)

`native.after_graphs` 可引用第二份 schema 2 补丁，使用 `base_sha256:"@level"` 绑定本轮编译和初始挂载后的 GIL。适用于创建引用刚编译技能图的原生技能。该阶段仍声明 `allowed_top_level_fields`，生成 `native-final-report.json` 和 `native-final-diff.json`，随后执行最终容器及引用检查。可用 `scene.whitebox` 从外部 GIL 或 `@level` 导出闭合的白盒几何 GIA。 [原生玩法制作](../editor/native-gameplay.md)

存档可选择 `transport:"server"`、`host_section:4`，将存档图挂到玩家模板并输出服务端信号定义。纯原生图和原生存档任务按实际产物判断 Lua 依赖。 [服务端存档](storage-authoring.md#原生服务端存档)

可选 `beyond` 阶段以 spec 指定场景，可用 `@level` 绑定本轮最终 GIL，随包后端支持可迁移交付。外部 Lua 模型和软件预览分别记录实际结果。GIL 摘要和选中的脚本挂载核对通过后，相关报告的 `artifact_scope` 为 `final_gil`，并记录 `final_gil_status`。使用独立项目预览时，仍可在外部证据中查看结果。任一必需断言失败不提交输出。 [模拟器后端](beyond-backend.md)

最终GIL在模拟前自动执行[工程对象与引用检查](../editor/project-index.md)，核对已校准客户端层级、脚本及原生引用。project.spec可以声明其它GIL/GIA和必需关系；存在最终GIL时清单必须恰有一个@level输入，不能只验证无关参考文件。失败不提交；未索引引用仍在报告中列出，不证明任意ID迁移安全。

随后执行[最终Lua检查](../editor/lua/client-check.md)：编译最终GIL全部脚本映射及交付目录Lua，包含没有单独导出的脚本。缺少必需Lua 5.3编译器、非法正文编码或语法错误阻止提交；没有脚本时为not_applicable。client-check.json属于静态证据，不代表API/引用交叉检查或宿主运行通过。

platform通过spec执行[平台版本与配置检查](../platform/platform-profiles.md)，未通过或未检查阻止生成提交。通过仅证明显式配置规则，报告artifact_verified=false，不代替最终GIL的平台配置回读；配置、目录和原文摘要纳入依赖，portable支持独立迁移。

执行顺序为输入核对→源码与资源→原生基底→严格图构建／替换→Lua嵌入→最终原生审计→声明的模拟／实验→清单。生成存储时将同源图和资源纳入图构建；已有图替换通过build schema 2声明。gil 指定精确的 mapping，自动消费最近产出的 GIL。仅产生 GIA 的图阶段继续传递进入该阶段的 GIL。图、存档或 Lua 阶段给出显式基底时，其 SHA-256 必须与当前 GIL 一致。基底冲突和输入变化会报告阶段、路径及两份摘要，失败时正式输出目录保留为空缺。

```text
python scripts/qianxing.py doctor --compare PLUGIN_ROOT
python scripts/qianxing.py capabilities
python scripts/qianxing.py produce JOB.json --out NEW_DIRECTORY --summary
python scripts/qianxing.py verify NEW_DIRECTORY
```

报告绑定源配置、Lua、工具、必要编译后端及产物摘要。普通交付可用同一 JOB 和新输出目录再次执行 `produce`，按清单中 `artifacts` 的交付角色核对摘要。只检查已归档产物时用 `verify NEW_DIRECTORY --artifacts-only`，结果中的来源与重建为 `not_checked`。可迁移交付先执行 `verify NEW_DIRECTORY --portable` 获取输入闭包摘要，再执行 `verify NEW_DIRECTORY --portable --rebuild --trusted-inputs-sha256 DIGEST`。重建使用随附输入闭包。路径和耗时属于当轮证据，模型、编译回读、软件预览与宿主结果各有状态。 [可迁移交付](portable-delivery.md)

`environment.json` 记录生成前的依赖和各能力组指纹。`dependency-graph.json` schema 3 的 `external_and_tool_inputs` 集中登记输入和工具摘要。每阶段通过 `inputs_added` 引用新增输入，并记录依赖边和产物变化。最终 `client.lua` 须与指定 GIL 映射正文相同。

内置联合模拟可用 `@level` 读取本轮最终 GIL。`simulation.json` 的 `inputs` 及客户端、服务端模型证据的 `source` 中，`level.gil` 相对于交付目录解析。外部输入仍使用实际绝对路径。报告记录所用文件的 SHA-256，Lua 另记录脚本映射。该类输入均与最终 GIL 绑定时，对应 `lua_model` 或 `native_graph_model` 才记录最终产物状态。外部或混合输入的实际模型结果保留在 `model_status` 与 `simulation.json` 中，最终产物状态为 `not_checked`。整个场景的 `simulation.artifact_scope` 需要所有参与者都绑定最终 GIL 才能标为 `final_gil`。必需阶段失败、已有输出路径或输入变化均拒绝提交。

两种中性整合配置可以分别采用单整数槽与双槽布尔／列表布局，变化模板别名、记录版本、素材数量及开发／保留集。失败用例包括未知schema、缺环境、源变更、输出已存在、原生审计错误及最终场景断言失败。独立重建比对交付正文，运行报告中的路径和耗时分别保留。

capabilities默认只报告可用源码和支持范围；通过--evidence指定checks.json时，只有源码、规则、测试支撑文件、后端及实际必需用例全部匹配才显示对应离线证据。证据schema 3及失败规则见[验证证据闭环](validation-evidence.md)。doctor 的 `plugin.path`、`plugin.version` 和 `plugin.capability_sha256` 可确认当前源码或安装缓存的执行身份。依赖检查覆盖当前 Python、Node、Pillow、Lua 和后端入口。

开发侧run_validation.py默认检查自用并执行完整相关套件，--changed接受改动路径，按Python导入关系与公共边界选择受影响检查。最终版本验收仍运行全套。新增输出、日志和失败记录进入development，不写冻结releases或已安装缓存。

人工验收：在千星奇域导入本轮最终GIL，核对图及UI挂载；启用客户端日志，执行首次操作、重开与关闭；有存储时按同玩家、同发布关卡完成首次读、实际进度、写入回读、结算及重进读取。保留文件摘要、设备和实际结果，未执行项保持not_checked。
