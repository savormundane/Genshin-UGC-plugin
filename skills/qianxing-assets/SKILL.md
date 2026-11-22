---
name: qianxing-assets
description: 查找千星奇域原生3D模型、选择白盒形状，生成、转换和检查静态素材及图元数据，处理颜色、几何、透明度、资源依赖、成本和预览；播放与动作归客户端Lua，文件挂载归GIL。
---

# Assets

先确定输入、坐标空间、输出表示和项目预算。用 [素材试算](../../references/asset-generation.md) 的 `assets preview` 对照目标尺寸、控件数和透明边缘，选定参数后执行 `assets generate`。需要分层配额、误差目标或续算时用 `assets fit`，查看顶层 `quality` 和各层停止原因。按需执行 `assets check/diff`，将生成的 `data.lua` 接入工程已有控件模板。

| 任务 | 资料 |
| --- | --- |
| 位图、矩形、透明边缘与富文本 | [点阵指南](../../references/pixel-import-guide.md)、[富文本](../../references/rich-text-assets.md) |
| 校准的GIA图元导入 | [原生素材](../../references/native-assets.md)；不支持的投影、变换与依赖拒绝 |
| 合法性、转换保真与成本 | [素材检查](../../references/asset-inspection.md) |
| 原生模型与白盒预览 | [原生场景](../../references/native-scene.md)；`resources search --type model`、`resources_lookup`、`scene preview` |
| 资源目录及运行缓存 | [资源目录](../../references/resource-catalogue.md)、[容量缓存](../../references/runtime-assets.md) |
| 生成目录补字段 | [目录合并](../../references/workflows/generated-lua-catalog-merge/README.md) |
| 图片自动拟合与续算 | [通用拟合](../../references/asset-fit.md)：`assets fit`，透明轮廓、区域和分层输入 |
| 分层资料和历史附件 | [L2D参考](references/l2d-workflow.md)；案例编号、骨骼和预算不能直接套用 |

输出数据、来源关系和重建预览；资源ID不能推导出本地PNG加载能力。图元数量不是设备FPS。播放、动作和生命周期交给 [Client Lua](../client-controls-lua/SKILL.md)。遵循[来源规则](../../references/knowledge-reliability.md)和[验证边界](../../references/validation.md)，不为单张素材转换运行全量回归。
