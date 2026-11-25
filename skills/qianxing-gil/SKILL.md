---
name: qianxing-gil
description: 比较、审计和安全修改千星奇域 GIL/GIA，审阅后另存，处理图、资源与脚本挂载及回读。
---

# Qianxing GIL

| 任务 | 入口 |
| --- | --- |
| 检查容器、字段或已知引用 | `native_inspect` 读取容器，`native_audit` 审计已识别的类型和引用。按名称查找对象用 `project_inspect`。 |
| 比较现有文件 | `native_diff`。需要验证保护范围时传明确的允许字段。 |
| 局部修改后另存 | `project_inspect` 定位 → `native_plan` 生成计划 → 审阅确认 → `native_apply` 写到新目录 → `native_diff` 核对。 |

使用唯一对象键和实际字段范围。将 `project_inspect.inputs_sha256.input` 交给 `native_plan`。审阅 `result.difference` 后，`native_apply` 使用同一基底摘要和 `outputs_sha256["plan.json"]` 中的计划文件摘要。保留未知字段与受保护字节。 [审阅并另存](../../references/gil/native-changes.md#审阅并另存已有工程)

脚本、图和资源挂载按已校准的容器和引用处理。编译、挂载或模拟需要绑定到同一交付的最终 GIL 时，用 [produce](../../references/workflows/produce.md) 接通这些阶段并核对产物。 [原生结构与挂载](../../references/gil/native-authoring.md) · [容器诊断](../../references/gil/gil-format-diagnostics.md)

交付文件时写明变更、保存位置、使用方法和实际核对结果。编辑器导入及游戏运行按本次证据分别记录。 [交付反馈](../../references/workflows/validation.md#交付反馈)
