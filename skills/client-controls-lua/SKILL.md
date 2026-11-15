---
name: client-controls-lua
description: 编写、解释和修复千星奇域客户端Lua，处理控件API、生命周期、输入、事件、动画运行及单文件源码装配；原生编辑器配置和节点图分别使用对应领域。
---

# Client Lua

工作对象是千星奇域客户端Lua 5.3和运行时控件。先确认脚本、绑定与调用环境；API用法通过 `qianxing.py knowledge api SYMBOL` 查询签名、原文行和未知／推导项，再读取相关API章节。不能从标准Lua或其他引擎补造宿主能力。

按当前任务读取，不预先加载全部资料：

| 任务 | 资料及工具 |
| --- | --- |
| API、生命周期、控件、输入、普通Tween | [运行规则](references/runtime-rules.md)、[API正文](references/client-controls-api.md)；`client check` |
| 多文件源码与宿主错误行定位 | [有序装配](../../references/client-assembly.md)；`client assemble` |
| 控件池、预算、拖动、暂停与清理 | [UI运行模块](../../references/runtime-ui.md) |
| 点阵帧和分层动作 | [动画接入](../../references/workflows/qianxing-animation/README.md)；素材转换归Assets |
| 信号、多人或存储 | [协议](../../references/protocol-v2.md)、[多人流程](../../references/workflows/qianxing-multiplayer/README.md)、[存储](../../references/storage-authoring.md)；只选涉及项 |
| 生成Lua目录补字段 | [目录合并](../../references/workflows/generated-lua-catalog-merge/README.md) |
| 失败或交付失配 | [只读诊断](../../references/project-diagnosis.md)、[交付排障](../../references/workflows/qianxing-release-integrity-triage/README.md) |

运行模块局部内联，不要求宿主文件系统或require。最终交付检查内嵌正文；只修改源码时无需运行完整制作链。来源冲突和证据规则见[知识可信度](../../references/knowledge-reliability.md)与[验证边界](../../references/validation.md)。
