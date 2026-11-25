---
name: miliastra-assets
description: 将 PNG 或分层图片转成千星奇域图元，比较候选预览和控件数，拟合、校验及生成素材。也可查原生模型与模板 ID。
---

# Miliastra Assets

单张 PNG 先用 `asset_preview` 给出候选预览、误差和控件数。选定候选后调用 `asset_generate`。复用同一 PNG、试算报告以及工具返回的两份摘要，输出到新目录。 [图片转图元](../../references/assets/image-to-primitives.md#单张-png-试算与生成)

| 任务 | 工具 |
| --- | --- |
| 多张图共用控件预算 | 终端 `assets batch preview/generate`。 [预算分配](../../references/assets/image-to-primitives.md#多素材共用控件预算) |
| 分层拟合、局部细化或续算 | `asset_fit`，查看每层误差、边缘检查和控件数。配置 `mount` 生成可挂载 Lua，再用 `simulate` 的 `preview=true` 看画面。 [拟合与挂载](../../references/assets/asset-fit.md) |
| 检查或对比素材文件 | 终端 `assets check/diff`。 [素材检查](../../references/assets/asset-inspection.md) |
| 查模型、音效、特效或白盒 | `resources_lookup` 查 ID 和来源，可传 `resource_type="sound"` 或 `"effect"`。用 `scene_preview` 看布局或枢轴草案。 [资源目录](../../references/platform/resource-catalogue.md) · [原生场景](../../references/editor/native-scene.md) |
| 把校准的 GIA 装饰转成图元数据 | 终端 `assets import-gia`，按已验证的几何投影和依赖范围转换。 [GIA 素材导入](../../references/assets/native-assets.md) |

图元交付附坐标、来源、预算、输出路径和重建预览。播放与动作接入 Editor 的 Client Lua，写入关卡时交给 GIL。素材和 Lua 或节点图需要绑定至同一份最终关卡时，通过已保存的制作配置调用 `produce`。 [动画接入](../../references/assets/animation.md) · [制作配置](../../references/workflows/produce.md)

已有 GIL 时，先定位实际容器和图片模板，再让 `asset_fit` 用 GIL 摘要绑定两者。调用 `native_plan` 时沿用同一 GIL 及摘要。用 schema 2 补丁，允许字段 `[9, 50]`，以拟合返回的 `result.mount.gil_binding.control_guid` 为目标，执行 `bind_client_lua`。操作里的 `source` 和 `fit_catalog` 分别指向拟合目录的 `mounted.lua` 和 `catalog.json`，`mapping` 使用用户确认的完整 Lua 文件名。检查保护字段后，再用计划及其摘要调用 `native_apply`。 [绑定拟合素材](../../references/assets/asset-fit.md#生成可挂载的-lua-和软件预览)

结果分别说明实际控件数、软件预览和已执行的检查。真实显示与设备性能以目标宿主的验收为准。
