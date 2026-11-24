---
name: qianxing-editor
description: 设计和检查千星奇域原生 3D 场景、实体、模板、组件、资源关联及原生界面；编写、解释和修复客户端 Lua，查询控件 API，处理输入、事件、生命周期、动画和脚本装配。
---

# Qianxing Editor

按任务选择[原生工程](#原生工程)或 [Client Lua](#client-lua)。

## 原生工程

负责平台工程与配置语义。平台资料可直接查 `docs_search` 或 `docs search/show`。查看已有工程时，先用 `project search INPUT QUERY` 或 MCP `project_inspect` 的 `query` 找到对象键，再按范围检查引用。原生绑定用产物回读核对。

中文问题先提取平台术语，例如用「定时器」查时序规则。按任务指定版本，回复中标明请求版本和资料来源版本。零结果按[中文查询](../../references/knowledge-reliability.md#中文查询)改用短词、别名或正式名称重查。

| 任务 | 按需资料 |
| --- | --- |
| 机关、关卡经济、角色技能、拾取、原生 HUD 与多人进度 | 用 `project inspect --scope gameplay` 定位资源和引用者。按[原生玩法制作](../../references/native-gameplay.md)创建或配置资源，再编译和挂载行为图，用 `produce` 交付 GIL。 |
| 原生 3D 场景、布景与关卡配置 | 独立静态场景用 [`scene build`](../../references/native-scene.md)，已有 GIL 用 [`arrange_instances`](../../references/native-scene.md#重复布设) 批量布设并用 `scene_preview` 查看前后差异。 |
| 实体、模板、消费者与挂载关系 | [工程索引](../../references/project-index.md)、[结构生成](../../references/native-authoring.md) |
| 版本、组件规则、经典／超限 | [平台规则](../../references/platform-profiles.md)、[官方索引](../../references/official-index.md) |
| 资源身份和自定义编号 | [资源目录](../../references/resource-catalogue.md)、[ID登记](../../references/id-registry.md) |
| 原生 UI 配置 | 用[矩形布局](../../references/native-ui-layout.md)编辑已有控件，或[追加客户端界面模块](../../references/native-authoring.md#追加客户端界面模块)。 |
| 模板／实例默认值、定时器序列 | [原生局部修改](../../references/native-changes.md#局部编辑) |
| 存储、成就、迁移 | [存储生成](../../references/storage-authoring.md)、[显式迁移](../../references/storage-migration.md) |
| 完整工程跨域接入 | [能力路由](../../references/skill-map.md)、[制作链](../../references/production-v2.md)；只执行配置声明的阶段 |

节点逻辑交给 [Qianxing Graph Code](../qianxing-graph-code/SKILL.md)，容器读写交给 [Qianxing GIL](../qianxing-gil/SKILL.md)。按原生对象身份选择经过校准的变换、组合和组件范围。无编辑器GUI控制能力；人工导入和实机证据按[验证边界](../../references/validation.md)记录。

使用 MCP `project_inspect` 的 `scope="scene"` 查询关卡实体、元件、初始变换和图挂载，并取得基底摘要。已识别实例通过 `set_entity_transform` 另存初始变换，基底与结果均须通过全局审计。

已摆放物件也可按 [三维实体变换](../../references/native-entity-transform.md) 核对模型、坐标和保护范围。

## Client Lua

先确认 Lua 5.3 脚本、绑定与调用环境。通过 MCP `api_lookup` 或 `qianxing.py knowledge api QUERY` 查符号、签名和原文行。标为 `derived` 的类型只作查询提示，按所用版本核对实际参数、返回值及调用行为。复合任务按动作拆查，例如先查「按钮点击」，再查「隐藏控件」。零结果按[中文查询](../../references/knowledge-reliability.md#中文查询)重试。编写后用 `client_check` 或 `client check` 检查源码，或通过 `mapping` 选定现有 GIL 中的单个脚本。提供 API 合同可同时核对调用和已声明引用。

用 `simulate check INPUT` 检查启动日志和第一条异常。看界面或验收联合场景时，选择[软件预览或场景检查](../../references/client-simulation.md)。

| 任务 | 资料及工具 |
| --- | --- |
| API、生命周期、控件、输入、普通Tween | [运行规则](references/runtime-rules.md)、[API正文](references/client-controls-api.md)；`client check` |
| 多文件源码与宿主错误行定位 | [有序装配](../../references/client-assembly.md)；`client assemble` |
| 控件池、预算、拖动、暂停与清理 | [UI运行模块](../../references/runtime-ui.md) |
| 点阵帧和分层动作 | [动画接入](../../references/workflows/qianxing-animation/README.md)；素材转换归 [Qianxing Assets](../qianxing-assets/SKILL.md) |
| 信号、多人或存储 | [协议](../../references/protocol-v2.md)、[多人流程](../../references/workflows/qianxing-multiplayer/README.md)、[存储](../../references/storage-authoring.md)；只选涉及项 |
| 生成Lua目录补字段 | [目录合并](../../references/workflows/generated-lua-catalog-merge/README.md) |
| 失败或交付失配 | [只读诊断](../../references/project-diagnosis.md)、[交付排障](../../references/workflows/qianxing-release-integrity-triage/README.md) |

运行模块局部内联，不要求宿主文件系统或require。最终交付检查内嵌正文；只修改源码时无需运行完整制作链。来源冲突和证据规则见[知识可信度](../../references/knowledge-reliability.md)与[验证边界](../../references/validation.md)。

有文件输出时，最终回复包含产物与改动、保存位置、使用方法和本次检查结果。 [交付反馈](../../references/validation.md#交付反馈)
