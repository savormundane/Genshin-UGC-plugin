---
name: miliastra-gil
description: 检查、比较和另存原神千星奇域（UGC）的关卡存档 GIL 或资源 GIA，审阅修改计划，挂载节点图、资源或脚本并校验写入结果。
---

# Miliastra GIL

| 任务 | 入口 |
| --- | --- |
| 检查容器、字段或已知引用 | `native_inspect` 读取容器，`native_audit` 审计已识别的类型和引用。按名称查找对象用 `project_inspect`。 |
| 比较现有文件 | `native_diff`。需要验证保护范围时传明确的允许字段。 |
| 局部修改后另存 | `project_inspect` 定位 → `native_plan` 生成计划 → 审阅确认 → `native_apply` 写到新目录 → `native_diff` 核对。 |
| 校验生成的布景 GIA | 用 `scene_catalogue` 绑定原生对象样本，再看 `scene_build` 写入后重新读取的结果、模板 ID 和 SHA-256 校验值。需要加入既有关卡时，先生成并审阅修改计划。 [场景证据](../../references/editor/native-scene.md) |

使用唯一对象键和实际字段范围。将 `project_inspect.inputs_sha256.input` 提供的原文件 SHA-256 校验值交给 `native_plan`。审阅 `result.difference` 后，`native_apply` 沿用原文件的校验值，并从 `outputs_sha256["plan.json"]` 取得计划文件的校验值。保留未知字段与受保护字节。 [审阅并另存](../../references/gil/native-changes.md#审阅并另存已有工程)

图编译输出可直接作为修改计划的 GIA 来源。拟合素材可用同一 GIL 核对图片模板和容器后，按计划挂载生成的 Lua，再重新读取文件核对脚本映射和模板绑定。 [Graph Code](../miliastra-graph-code/SKILL.md) · [素材挂载](../../references/assets/asset-fit.md#生成可挂载的-lua-和软件预览)

脚本、图和资源挂载按已校准的容器和引用处理。编译、挂载或模拟需要绑定到同一交付的最终 GIL 时，用 [produce](../../references/workflows/produce.md) 接通这些阶段并核对产物。 [原生结构与挂载](../../references/gil/native-authoring.md) · [容器诊断](../../references/gil/gil-format-diagnostics.md)

交付文件时写明变更、保存位置、使用方法和实际核对结果。编辑器导入及游戏运行按本次证据分别记录。 [交付反馈](../../references/workflows/validation.md#交付反馈)
