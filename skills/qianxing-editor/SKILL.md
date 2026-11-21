---
name: qianxing-editor
description: 设计和检查千星奇域工程对象、实体、模板、组件配置及资源关联，查询平台版本规则；节点程序、客户端Lua和GIL文件处理分别交给对应领域。
---

# 工程检查

负责平台工程与配置语义。先读取实际工程和目标平台版本／模式，通过 `qianxing.py project inspect`、`docs search/show`、`platform profile/check` 核对对象和规则。声明配置检查不等于最终GIL已落地，已校准原生绑定需最终回读。

| 任务 | 按需资料 |
| --- | --- |
| 实体、模板、消费者与挂载关系 | [工程索引](../../references/project-index.md)、[结构生成](../../references/native-authoring.md) |
| 版本、组件规则、经典／超限 | [平台规则](../../references/platform-profiles.md)、[官方索引](../../references/official-index.md) |
| 资源身份和自定义编号 | [资源目录](../../references/resource-catalogue.md)、[ID登记](../../references/id-registry.md) |
| 原生UI配置 | [校准的矩形布局](../../references/native-ui-layout.md) |
| 模板／实例默认值、定时器序列 | [原生局部修改](../../references/native-changes.md#局部编辑) |
| 存储、成就、迁移 | [存储生成](../../references/storage-authoring.md)、[显式迁移](../../references/storage-migration.md) |
| 完整工程跨域接入 | [能力路由](../../references/skill-map.md)、[制作链](../../references/production-v2.md)；只执行配置声明的阶段 |

节点逻辑由Graph Code处理，控件运行由Client Lua处理，容器修改由GIL处理。未知字段、动态对象和缺失校准明确列为未覆盖，不按旧项目名称推断身份。无编辑器GUI控制能力；人工导入和实机证据按[验证边界](../../references/validation.md)记录。

使用 MCP `project_inspect` 读取所选工程并取得基底摘要。控件脚本运行时签名查 [Client Lua](../client-controls-lua/SKILL.md)，节点签名查 [Graph Code](../qianxing-graph-code/SKILL.md)。
