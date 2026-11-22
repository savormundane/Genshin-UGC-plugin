---
name: qianxing-editor
description: 设计和检查千星奇域原生3D场景、工程对象、实体、模板、组件配置及资源关联，查询平台版本规则；节点程序、客户端Lua和GIL文件处理分别交给对应领域。
---

# Editor

负责平台工程与配置语义。先读取实际工程和目标平台版本／模式，通过 `qianxing.py project inspect`、`docs search/show`、`platform profile/check` 核对对象和规则。声明配置检查不等于最终GIL已落地，已校准原生绑定需最终回读。

| 任务 | 按需资料 |
| --- | --- |
| 关卡经济、技能、拾取与原生 HUD | 用 `project inspect --scope gameplay` 定位资源和引用者，通过 [原生玩法制作](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/native-gameplay.md) 配置 |
| 原生3D静态场景、编辑布景与关卡配置 | [原生场景](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/native-scene.md)；先查模型证据，独立场景用 `scene build`，已有 GIL 用 `native plan/apply` |
| 机关、角色技能、商店、原生 HUD 和多人进度 | [原生玩法制作](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/native-gameplay.md)。先用写入操作创建资源，再编译和挂载行为图，用 `produce` 交付 GIL。 |
| 实体、模板、消费者与挂载关系 | [工程索引](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/project-index.md)、[结构生成](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/native-authoring.md) |
| 版本、组件规则、经典／超限 | [平台规则](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/platform-profiles.md)、[官方索引](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/official-index.md) |
| 资源身份和自定义编号 | [资源目录](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/resource-catalogue.md)、[ID登记](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/id-registry.md) |
| 原生UI配置 | [校准的矩形布局](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/native-ui-layout.md) |
| 模板／实例默认值、定时器序列 | [原生局部修改](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/native-changes.md#局部编辑) |
| 存储、成就、迁移 | [存储生成](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/storage-authoring.md)、[显式迁移](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/storage-migration.md) |
| 完整工程跨域接入 | [能力路由](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/skill-map.md)、[制作链](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/production-v2.md)；只执行配置声明的阶段 |

节点逻辑由Graph Code处理，控件运行由Client Lua处理，容器修改由GIL处理。按原生对象身份选择经过校准的变换、组合和组件范围。无编辑器GUI控制能力；人工导入和实机证据按[验证边界](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/validation.md)记录。

使用 MCP `project_inspect` 的 `scope="scene"` 查询关卡实体、元件、初始变换和图挂载，并取得基底摘要。已识别实例通过 `set_entity_transform` 另存初始变换，基底与结果均须通过全局审计。控件脚本运行时签名查 [Client Lua](../client-controls-lua/SKILL.md)，节点签名查 [Graph Code](../qianxing-graph-code/SKILL.md)。

已摆放物件也可按 [三维实体变换](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/native-entity-transform.md) 核对模型、坐标和保护范围。
