---
name: qianxing-assets
description: 查找千星奇域原生3D模型、选择白盒形状，生成、转换和检查静态素材及图元数据，处理颜色、几何、透明度、资源依赖、成本和预览；播放与动作归客户端Lua，文件挂载归GIL。
---

# Qianxing Assets

先确定输入、坐标空间、输出表示和项目预算。单张 PNG 转矩形图元时，用 MCP `asset_preview` 比较预览、控件数和预算。候选确定后，用 `asset_generate` 生成数据。继续使用同一张 PNG、试算报告和工具返回的两份摘要，交付到新目录。 [MCP 调用顺序](../../references/local-mcp.md#单张-png-试算与生成)

可用终端时，`assets preview/generate` 还支持自定网格和富文本。多项素材共用控件预算时用 `assets batch preview/generate`。分层拟合或续算用 `assets fit`，查看顶层 `quality` 和停止原因。已有相应制作配置时，MCP `produce` 可执行批量生成或拟合。按需运行 `assets check/diff`，再将数据接入客户端界面。 [素材任务与客户端能力](../../references/asset-generation.md#素材任务与客户端能力)

| 任务 | 资料 |
| --- | --- |
| 位图、矩形、透明边缘与富文本 | [点阵指南](../../references/pixel-import-guide.md)、[富文本](../../references/rich-text-assets.md) |
| 校准的GIA图元导入 | [原生素材](../../references/native-assets.md)；不支持的投影、变换与依赖拒绝 |
| 合法性、转换保真与成本 | [素材检查](../../references/asset-inspection.md) |
| 原生模型、白盒元件及预览 | [原生场景](../../references/native-scene.md)。使用 `resources_lookup` 选择模型。用 `scene preview --template-id` 核对元件几何，用 `scene export-whitebox` 导出白盒形状。 |
| 资源目录及运行缓存 | [资源目录](../../references/resource-catalogue.md)、[容量缓存](../../references/runtime-assets.md) |
| 生成目录补字段 | [目录合并](../../references/workflows/generated-lua-catalog-merge/README.md) |
| 图片自动拟合与续算 | [通用拟合](../../references/asset-fit.md)：`assets fit`，透明轮廓、区域和分层输入 |
| 分层资料和历史附件 | [L2D参考](references/l2d-workflow.md)；案例编号、骨骼和预算不能直接套用 |

输出数据、来源关系和重建预览；资源ID不能推导出本地PNG加载能力。图元数量不是设备FPS。播放、动作和生命周期交给 [Qianxing Editor · Client Lua](../qianxing-editor/SKILL.md#client-lua)。遵循[来源规则](../../references/knowledge-reliability.md)和[验证边界](../../references/validation.md)，不为单张素材转换运行全量回归。

有文件输出时，最终回复包含产物与改动、保存位置、使用方法和本次检查结果。 [交付反馈](../../references/validation.md#交付反馈)
