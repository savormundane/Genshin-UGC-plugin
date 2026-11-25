---
name: qianxing-assets
description: 将 PNG 或分层图片转成千星奇域图元，比较候选预览和控件数，拟合、校验及生成素材。也可查原生模型与模板 ID。
---

# Qianxing Assets

单张 PNG 先用 `asset_preview` 给出候选预览、误差和控件数。选定候选后调用 `asset_generate`。复用同一 PNG、试算报告以及工具返回的两份摘要，输出到新目录。 [图片转图元](../../references/assets/image-to-primitives.md#单张-png-试算与生成)

| 任务 | 工具 |
| --- | --- |
| 多张图共用控件预算 | 终端 `assets batch preview/generate`。 [预算分配](../../references/assets/image-to-primitives.md#多素材共用控件预算) |
| 分层拟合或续算 | 终端 `assets fit`，看每层误差、实际控件数和停止原因。 [拟合配置](../../references/assets/asset-fit.md) |
| 检查或对比素材文件 | 终端 `assets check/diff`。 [素材检查](../../references/assets/asset-inspection.md) |
| 查原生模型、模板 ID 和白盒 | `resources_lookup` 查 ID 和样本依据。终端 `scene preview --template-id` 查看白盒，`scene export-whitebox` 导出几何。 [原生场景](../../references/editor/native-scene.md) |
| 把校准的 GIA 装饰转成图元数据 | 终端 `assets import-gia`，按已验证的几何投影和依赖范围转换。 [GIA 素材导入](../../references/assets/native-assets.md) |

图元交付附坐标、来源、预算、输出路径和重建预览。播放与动作接入 Editor 的 Client Lua，写入关卡时交给 GIL。素材和 Lua 或节点图需要绑定至同一份最终关卡时，通过已保存的制作配置调用 `produce`。 [动画接入](../../references/assets/animation.md) · [制作配置](../../references/workflows/produce.md)

结果分别说明实际控件数、软件预览和已执行的检查。真实显示与设备性能以目标宿主的验收为准。
