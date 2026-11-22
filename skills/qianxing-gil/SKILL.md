---
name: qianxing-gil
description: 检查、比较和安全修改千星奇域GIL/GIA容器，处理脚本嵌入、图与资源挂载、保护字段、组装及最终回读；不代替节点程序或编辑器配置设计。
---

# GIL

负责已识别容器、对象身份、引用和字节保留。先用 `qianxing.py native inspect` 或 [GIL工具](../../references/gil-tooling.md)读取实际输入；修改绑定基底摘要、唯一目标及允许范围，输出新文件。未知字段保留，不猜测改写。

| 任务 | 按需资料与工具 |
| --- | --- |
| 原生场景及物件局部写回 | [场景 GIA 与 GIL 修改](../../references/native-scene.md)；核对模型引用、位置与对象身份 |
| 道具经济、职业技能、原生界面与存档写入 | [原生玩法制作](../../references/native-gameplay.md) |
| 比较和局部修改 | [原生修改](../../references/native-changes.md)；`native diff/plan/apply` |
| 图、信号、结构体、实体和模板挂载 | [原生维护](../../references/native-maintenance.md)、[详细操作](references/native-operations.md) |
| Lua嵌入与最终脚本检查 | [最终Lua检查](../../references/client-check.md) |
| 从图、信号和Lua组装 | [组装流程](../../references/workflows/qianxing-gil-assembly-pipeline/README.md)；优先build/produce，低层工具按需使用 |
| 错接与隐式端口 | [数据流审计](../../references/native-dataflow-validation.md)；`native audit` |
| 容器无法解释 | [低层诊断](references/gil-format-diagnostics.md)；只读字段探查不代表语义通过 |
| 产物失配和重建 | [交付排障](../../references/workflows/qianxing-release-integrity-triage/README.md)、[portable](../../references/portable-delivery.md) |

跨GIL迁移仅限工具明确支持的身份及引用，不直接复制带旧引用的字段，不承诺全工程ID重映射。最终文件审计覆盖新增消费者和挂载；编译回读、模型、编辑器导入和宿主运行按[验证边界](../../references/validation.md)分别报告。

使用 MCP 编辑现有工程时，以 `project_inspect` 的 `selector` 精确定位对象，将 `inputs_sha256.input` 传给 `native_plan`。审阅变更后，用 `outputs_sha256["plan.json"]` 调用 `native_apply`，最后用 `native_diff` 核对允许范围。 [调用合同](../../references/local-mcp.md)

已摆放物件也可按 [三维实体变换](../../references/native-entity-transform.md) 核对模型、坐标和保护范围。
