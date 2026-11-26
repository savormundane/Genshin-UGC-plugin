---
name: miliastra-assets
description: 把 PNG、点阵图或分层图片转成原神千星奇域（UGC）图元，比较候选预览和控件数，拟合、校验及生成素材。也可查原生模型和模板 ID。
---

# Miliastra Assets

## 点阵图片处理

1. 从工程内的原始 PNG 开始，确认目标显示尺寸和控件预算。每个矩形占用一个图元控件，父容器和界面其他控件单独计入工程预算。
2. 用 `asset_preview` 比较候选画面、误差和实际控件数。先看主体轮廓、高对比线条和透明边缘，再选预算内的方案。超预算时比较较小网格，细节损失明显时用 `asset_fit` 分层处理。需要调整透明阈值或色数时用终端的 [图片转图元](../../references/assets/image-to-primitives.md) 参数。
3. 选定候选后用 `asset_generate` 生成。沿用原 PNG，`report` 指向试算目录的 `report.json`。用 `inputs_sha256.input` 填 `sha256`，用 `outputs_sha256["report.json"]` 填 `report_sha256`。传入所选 `candidate` 和新输出目录，再核对 `data.lua`、控件数和预览。
4. 挂载时使用当前 GIL 中确认可实例化的图片控件模板。矩形在 `data.lua` 中从左上角按网格定位，调色板索引从 1 开始。按目标容器的锚点和显示比例换算位置与尺寸。动画以矩形最多的一帧确定池大小，分批创建，切帧时更新已有图块并隐藏多余控件，镜像绕帧锚点处理。

[检查点图标样例](../../samples/creator-demos/png/README.md) · [点阵帧动画接入](../../references/editor/lua/pixel-runtime.md)

## 其他素材任务

| 任务 | 工具 |
| --- | --- |
| 多张图共用控件预算 | 终端 `assets batch preview/generate`。 [预算分配](../../references/assets/image-to-primitives.md#多素材共用控件预算) |
| 分层拟合、局部细化或续算 | `asset_fit`，查看每层误差、边缘检查和控件数。配置 `mount` 生成可挂载 Lua，再用 `simulate` 的 `preview=true` 看画面。 [拟合与挂载](../../references/assets/asset-fit.md) |
| 检查或对比素材文件 | 终端 `assets check/diff`。 [素材检查](../../references/assets/asset-inspection.md) |
| 查模型、音效、特效或白盒 | `resources_lookup` 查 ID 和来源，可传 `resource_type="sound"` 或 `"effect"`。用 `scene_preview` 看布局或枢轴草案。 [资源目录](../../references/platform/resource-catalogue.md) · [原生场景](../../references/editor/native-scene.md) |
| 把校准的 GIA 装饰转成图元数据 | 终端 `assets import-gia`，按已验证的几何投影和依赖范围转换。 [GIA 素材导入](../../references/assets/native-assets.md) |

图元交付附坐标、来源、预算、输出路径和重建预览。播放与动作接入 Editor 的 Client Lua，写入关卡时交给 GIL。素材和 Lua 或节点图需要绑定至同一份最终关卡时，通过已保存的制作配置调用 `produce`。 [动画接入](../../references/assets/animation.md) · [制作配置](../../references/workflows/produce.md)

已有 GIL 时，先定位实际容器和图片模板，再让 `asset_fit` 用 GIL 的 SHA-256 校验值绑定两者。调用 `native_plan` 时沿用同一 GIL 和校验值。用 schema 2 补丁，允许字段 `[9, 50]`，以拟合返回的 `result.mount.gil_binding.control_guid` 为目标，执行 `bind_client_lua`。操作里的 `source` 和 `fit_catalog` 分别指向拟合目录的 `mounted.lua` 和 `catalog.json`，`mapping` 使用用户确认的完整 Lua 文件名。检查保护字段后，再用计划文件及其校验值调用 `native_apply`。 [绑定拟合素材](../../references/assets/asset-fit.md#生成可挂载的-lua-和软件预览)

结果分别说明实际控件数、软件预览和已执行的检查。游戏内显示与设备性能以实测为准。
