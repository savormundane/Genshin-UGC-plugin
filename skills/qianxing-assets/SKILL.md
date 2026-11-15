---
name: qianxing-assets
description: 生成、转换和检查千星奇域静态素材及图元数据，处理颜色、几何、透明度、资源依赖、成本和预览；播放与动作归客户端Lua，文件挂载归GIL。
---

# Assets

先确定输入、坐标空间、输出表示和项目预算。默认复用 [内置素材核心](../../references/asset-generation.md) 的 `qianxing.py assets generate`，按需使用 `assets check/diff`。

| 任务 | 资料 |
| --- | --- |
| 位图、矩形、透明边缘与富文本 | [点阵指南](../../references/pixel-import-guide.md)、[富文本](../../references/rich-text-assets.md) |
| 校准的GIA图元导入 | [原生素材](../../references/native-assets.md)；不支持的投影、变换与依赖拒绝 |
| 合法性、转换保真与成本 | [素材检查](../../references/asset-inspection.md) |
| 资源目录及运行缓存 | [资源目录](../../references/resource-catalogue.md)、[容量缓存](../../references/runtime-assets.md) |
| 生成目录补字段 | [目录合并](../../references/workflows/generated-lua-catalog-merge/README.md) |
| 可选GE高级拟合 | [兼容工作流](references/workflow.md)、scripts/Invoke-Geimg.ps1；核对实际可用后端 |
| 分层资料和历史附件 | [L2D参考](references/l2d-workflow.md)；案例编号、骨骼和预算不能直接套用 |

输出数据、来源关系和重建预览；资源ID不能推导出本地PNG加载能力。图元数量不是设备FPS。播放、动作和生命周期交给 [Client Lua](../client-controls-lua/SKILL.md)。遵循[来源规则](../../references/knowledge-reliability.md)和[验证边界](../../references/validation.md)，不为单张素材转换运行全量回归。
