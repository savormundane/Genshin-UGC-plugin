---
name: miliastra-editor
description: 查找千星奇域工程对象、引用、平台规则和资源，设计原生场景及界面，查询客户端 API、编写和修复 Lua，处理控件输入、事件和动画播放。
---

# Miliastra Editor

按用户要查或要改的对象直接选工具。命令行示例均为 `qianxing.py` 的子命令。

| 任务 | 入口 |
| --- | --- |
| 找出生点、变量、模板或引用 | `project_inspect` 传 `query`。同名候选先列出，再按所选对象键追引用。 |
| 查平台规则和资源 | `docs_search` 查目标版本资料，`resources_lookup` 查模型或模板。 [平台规则](../../references/platform/platform-profiles.md) · [资源目录](../../references/platform/resource-catalogue.md) |
| 查 Lua API、检查或修复 Lua | `api_lookup` 查正式符号与来源，`client_check` 定位并复检。已有 GIL 可按 `mapping` 检查其中一个脚本。 |
| 装配多段 Lua | CLI `client assemble` 输出合并后的脚本和源码映射。 [装配方法](../../references/editor/lua/client-assembly.md) |
| 布设或核对场景、原生界面 | `project_inspect` 查实体和挂载。用 `scene_catalogue` 从样本提取布景模板，`scene_preview` 看草案，审阅后用 `scene_build` 另存静态场景 GIA。 [原生场景](../../references/editor/native-scene.md) · [UI 矩形布局](../../references/editor/native-ui-layout.md) |
| 预览 Lua 或检查试玩输出 | `simulate` 传 Beyond 配置和 `preview=true`，看画面、控件和日志。查看编辑器导出用 `logs_diagnose`。 [软件预览](../../references/workflows/beyond-backend.md) · [调试日志](../../references/workflows/client-simulation.md#读取编辑器调试日志) |

## 原生工程

[工程索引](../../references/editor/project-index.md)说明对象键和引用。涉及机关、资源、技能或计时器时按实际对象和基底核对允许的操作。已验证变换和布局可回读。容器修改、计划和另存由 [Miliastra GIL](../miliastra-gil/SKILL.md) 处理，节点编写由 [Miliastra Graph Code](../miliastra-graph-code/SKILL.md) 处理。多个阶段共用同一交付时，按实际依赖选择 [produce 配置](../../references/workflows/produce.md)。 [原生玩法制作](../../references/editor/native-gameplay.md)

## Client Lua

返回 API 签名和依据。将中文整句拆成动作或术语重查，例如「按钮点击」「隐藏控件」。按资料所覆盖的版本核对参数和返回值，`derived` 类型只作检索线索。编写或修复后用 `client_check` 复检，软件预览和游戏内验证分别记录。涉及动画时素材由 [Miliastra Assets](../miliastra-assets/SKILL.md) 准备。 [Lua 运行规则](../../references/editor/lua/runtime-rules.md) · [中文查询](../../references/platform/knowledge-reliability.md#中文查询)

交付文件时写明变更、保存位置、用法和本次检查。 [交付反馈](../../references/workflows/validation.md#交付反馈)
