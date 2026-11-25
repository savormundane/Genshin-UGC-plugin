# 原生差异与修改计划

能力名：native-changes。入口为qianxing.py native diff/plan及apply --plan，核心位于scripts/miliastra/native/changes.py，依赖Python标准库及包内原生定义。diff支持同格式GIL或GIA比较；修改计划复用[原生维护](native-maintenance.md)已校准的GIL补丁操作，不扩展未知格式写入。

```text
python scripts/qianxing.py native diff BEFORE.gil AFTER.gil --allow-fields 10 --out DIFF.json
python scripts/qianxing.py native plan BEFORE.gil --spec PATCH.json --out PLAN.json
python scripts/qianxing.py native apply BEFORE.gil --plan PLAN.json --out NEW.gil
```

输出文件须不存在，父目录由调用方准备；已有文件与原始输入不覆盖。plan在内存执行补丁和最终检查，仅保存可审阅JSON，不生成或覆盖正式GIL。原有apply --spec保持兼容，--spec与--plan互斥。

## 审阅并另存已有工程

1. 用 `project_inspect` 按名称查找。遇到同名对象时先列出候选，再用完整对象键或明确的 `selector` 核对目标和引用。保存本次返回的 `inputs_sha256.input`。
2. 调用 `native_plan`，传原文件 `input`、上述 `sha256` 和新的 `output`。内联 `patch` 使用 schema 2，声明 `allowed_top_level_fields` 和 `operations`。服务从已校验的输入填入基底摘要。使用补丁文件时传 `spec` 和 `spec_sha256`。
3. 审阅 `result.difference`，核对计划操作和保护字段。确认后调用 `native_apply`，传同一基底及其摘要、审阅目录中的 `plan.json`、`outputs_sha256["plan.json"]` 所示的 `plan_sha256` 和新的输出目录。
4. 用 `native_diff` 比较原文件和另存的 `level.gil`，复用同一允许字段范围。核对应用报告中的实际操作、审计结果和输出摘要。需要静态核对交付清单时，向 `verify` 传入 `manifest.json` 及其摘要。

基底或补丁来源变化后重新生成并审阅计划。文件回读和编辑器导入分开记录。 [从样例操作](../../samples/creator-demos/gil/README.md#审阅并另存)

## 差异内容与保护范围

diff报告包含对象增加/删除/修改、引用变化、节点类型/版本/端口及已识别整数/标识/字符串常量变化、脚本正文摘要，以及每个已读取对象和顶层字段的原始字节摘要。未知值载体保留value_bytes，不猜测其语义。字段顺序和容器非长度参数变化单独列出，bytes_equal比较完整文件。

node_connection按使用者→提供者比较，忽略仅改变连线存储端的serialized_at；输入端、输出端或双端的等价记录不制造语义变化，但serialized_objects和top_level_fields仍显示实际字节变化。

--allow-fields显式列出允许变化的顶层字段。其余字段按原顺序连接的完整原始字节，以及容器非长度参数与尾部必须相同；变化则protected.unchanged=false，status=failed，退出码2。空--allow-fields表示不允许修改任何顶层字段；不提供该选项时只做比较，不声称保护范围已检查。长度字段由合法容器长度核验，不要求修改后的长度与原文件相等。

完整原始字节变化不会被“对象语义相同”隐藏。complete_semantic_diff仍为false，unindexed列出任意组件、自定义变量、动态Lua标识等当前未完整解析范围；不把这些变化判为无影响。结构无法读取时直接失败。最终原生/工程引用检查不通过也不能获得成功差异状态；editor与host保持not_checked。

涉及原生玩法的补丁还可在 `gameplay_records` 中比较职业、技能、道具、商店、环境资源、全局计时器、玩家组和复苏点的身份与记录摘要。`gameplay_references` 列出已校准引用的增删。`native plan --summary` 在终端显示摘要和保护范围，完整计划保存在 `--out` 指定的文件。由 `native apply` 的报告读取具名对象实际分配的 ID。 [原生玩法制作](../editor/native-gameplay.md)

## 内容绑定的计划

PATCH 使用现有 schema 2、base_sha256、allowed_top_level_fields 及 operations 合同。写入 GIL 及 `section_from` 的来源均须匹配已用样本校准的容器头，且来源的目标字段须唯一。`replace_graph` 保留目标图 ID、名称和既有引用。`section_from` 仅用于显式整段替换。计划要求 `strict_audit=true` 或省略该字段。

MCP 内联 `native_plan` 可省略 `patch.base_sha256`，服务用已验证的 `sha256` 填入计划。文件补丁保持原合同。预检或结果审计阻止写入时，`diagnostics` 给出阶段、已知对象键和名称、关系、字段与目标 ID。先按 `next_step` 找到并修复阻塞，再用变更后的摘要重新规划。

PLAN的schema为2、kind为native-change-plan，包含：

- patch：补丁内容，来源文件改为稳定的@input:N令牌。
- inputs：令牌对应的source路径与内容sha256。路径相对PLAN文件。
- result_sha256：执行已审阅补丁后必须得到的完整GIL摘要。
- difference：同一基底、来源和补丁实际产生的差异与保护核验。
- plan_sha256：补丁、来源内容摘要、预期结果及差异报告的共同摘要。

apply --plan先核对计划和所有来源内容，再执行现有补丁，核对完整结果摘要与差异报告，并检查读取期间来源未变。基底变化、来源变化、缺失/多余令牌、修改计划正文、错误预期结果或最终引用失败均不写正式输出。计划摘要用于一致性检查，不是数字签名或外部审批证明。

输入路径不进入plan_sha256，便于完整工程迁移；来源内容摘要始终绑定。只有将令牌指向字节相同的文件才保持同一计划。修改来源正文必须重新生成并检查计划，不自动重新签署旧计划。

`arrange_instances` 将布局文件与可选的 `previous_bindings` 一并绑定。`arrangements` 也纳入计划摘要，`--summary` 会显示每次布设操作的分类和变换。应用时重新校验来源、操作预览与输出 GIL 摘要。[重复布设](../editor/native-scene.md#重复布设)

两种中性使用方式：第一种替换选定节点图，允许字段10并保护其它图及字段；第二种精确准备脚本映射区段，通过显式section_from替换字段50。后者会替换整段，须先在来源文件保留所有仍需使用的映射，不能当作自动合并。实际ID、脚本和字段范围由当前工程确定。

## 局部编辑

先用 `project inspect` 确认模板或实例身份和变量名称，用 `native inspect` 确认计时器节点位置。将基底 SHA-256 和相应字段加入 PATCH，再使用上面的 plan/apply 命令。下列两项可独立使用。

| operation | allowed_top_level_fields | 参数与回读 |
| --- | --- | --- |
| `set_custom_variable_default` | 模板 `[4]`，实例 `[5]` | `{"op":"set_custom_variable_default","section":4,"entity_id":42,"name":"Count","value":8}`。精确选定已有变量，保留名称与类型描述符。接受对应的 JSON 整数、布尔、有限浮点或字符串。实例需已有该变量的覆盖条目。应用报告列出修改前后的值。 |
| `set_timer_sequence` | `[10]` | `{"op":"set_timer_sequence","source":"platform.json","timer_id":"timer-a"}`。配置与 `platform check` 共用，须有对应 `native_bindings`，并匹配既有普通图、节点、实体及计时器名。序列写入使用 float32，编码后也须满足间隔并以正时间点结束。连线入参、歧义目标和无法保留的序列项拒绝写入。应用后可执行 `platform check platform.json --gil NEW.gil` 核对。 |

模板默认值用于继承该值的实例，已有覆盖继续生效。计时器编辑保留循环项、连线及挂载。新建计时器逻辑沿用 Graph Code 编译。两项写入均保留目标以外的内容，编辑器和游戏运行结果按实际验证记录。

## 制作链与迁移重建

produce schema 2的native阶段可以选择base+plan：

```json
{
  "schema": 2,
  "native": {"base":"before.gil","plan":"review/plan.json"},
  "portable": {}
}
```

base与plan相对制作配置解析，inputs.source相对计划文件解析。native.spec和native.plan只能选其一；native仍与level新建互斥。计划约束native阶段的输出；若另有图编译、Lua嵌入或存储阶段，这些后续修改继续按各自合同和最终审计核验，不能将native阶段摘要冒充完整制作链最终摘要。

native-report.json记录实际应用和输入摘要；native-diff.json及native-plan.json保留审阅证据。交付目录内的计划副本属于记录，来源路径仍以输入计划为基准，重新应用请使用原计划或portable收纳后的输入计划。portable收纳基底、计划及所有令牌来源，只重写路径，保持plan_sha256和结果摘要；verify --portable在原工程目录不可用时仅静态核对；显式重建需按portable-delivery指南提供摘要确认。

任何必需检查失败不提交正式目录。现有输出拒绝覆盖，原输入保持只读。公开仓库提供[计划、应用与回读复现](../../docs/contributing/development.md#复现已有工程的修改流程)。编辑器再导出文件可以作为diff的AFTER输入，但该比较本身不能证明文件由编辑器实际产生或已完成实机验收。

## 人工再导出核对

保留交付目录中的原始level.gil、清单、源码映射和报告。人工导入该文件，在编辑器中核对挂载并完成本次需要的运行步骤；另存再导出文件为reexport.gil，不覆盖交付原件。记录实际编辑器版本、操作和结果，尚未操作的项目保留待验。

```text
python scripts/qianxing.py native diff delivery/level.gil reexport.gil --out reexport-diff.json
python scripts/qianxing.py client check reexport.gil --out reexport-client.json
```

第一次对比不设置allow-fields，先查看全部变化。bytes_equal只回答字节是否完全相同。status=passed表示当前已实现的结构检查通过，不表示没有变化，也不证明编辑器兼容。检查objects、references、serialized_objects、top_level_fields、field_order_changed和envelope；未知字节仍必须审阅，不能因已解析对象没有变化而略过。需要保护特定范围时再使用明确的allow-fields；保护范围失败不能通过扩大白名单消除。

新建工程重点核对脚本映射、图挂载和资源引用是否在再导出后仍存在。成熟工程迭代还需核对选定修改之外的对象和引用是否保持。名称相同不代表对象ID相同，字段重排也不自动代表语义等价；complete_semantic_diff始终为false。

client check默认只编译再导出文件的所有内嵌Lua，不执行正文。需要API/引用检查时提供与再导出正文匹配的显式合同，不能复用已不匹配的摘要。运行日志对应哪个产物，就在[结构化日志诊断](../workflows/log-diagnostics.md)中绑定哪个产物和构建ID；原交付与再导出的事件不可因脚本名相同而混用。编辑器重新写入Lua后，旧行号映射可能失效，不能强行套用。

有存储时另记实际退出/重进和回读结果；差异报告、日志可解析或离线模型通过均不替代这一证据。此流程复用已实现的CLI，不自动操作编辑器，也不新增“已实机通过”的标记。
