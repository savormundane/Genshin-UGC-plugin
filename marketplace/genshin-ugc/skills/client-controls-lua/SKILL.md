---
name: client-controls-lua
description: 编写、解释和修复千星奇域客户端Lua，处理控件API、生命周期、输入、事件、动画运行及单文件源码装配；原生编辑器配置和节点图分别使用对应领域。
---

# Client Lua

先确认 Lua 5.3 脚本、绑定与调用环境。通过 MCP `api_lookup` 或 `qianxing.py knowledge api SYMBOL` 查签名、原文行和推导项。编写后用 `client_check` 或 `client check` 检查源码，或通过 `mapping` 选定现有 GIL 中的单个脚本。提供 API 合同可同时核对调用和已声明引用。

用 `simulate check INPUT` 检查启动日志和第一条异常。看界面或验收联合场景时，选择[软件预览或场景检查](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/client-simulation.md)。

按当前任务读取，不预先加载全部资料：

| 任务 | 资料及工具 |
| --- | --- |
| API、生命周期、控件、输入、普通Tween | [运行规则](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/skills/client-controls-lua/references/runtime-rules.md)、[API正文](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/skills/client-controls-lua/references/client-controls-api.md)；`client check` |
| 多文件源码与宿主错误行定位 | [有序装配](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/client-assembly.md)；`client assemble` |
| 控件池、预算、拖动、暂停与清理 | [UI运行模块](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/runtime-ui.md) |
| 点阵帧和分层动作 | [动画接入](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/workflows/qianxing-animation/README.md)；素材转换归Assets |
| 信号、多人或存储 | [协议](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/protocol-v2.md)、[多人流程](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/workflows/qianxing-multiplayer/README.md)、[存储](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/storage-authoring.md)；只选涉及项 |
| 生成Lua目录补字段 | [目录合并](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/workflows/generated-lua-catalog-merge/README.md) |
| 失败或交付失配 | [只读诊断](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/project-diagnosis.md)、[交付排障](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/workflows/qianxing-release-integrity-triage/README.md) |

运行模块局部内联，不要求宿主文件系统或require。最终交付检查内嵌正文；只修改源码时无需运行完整制作链。来源冲突和证据规则见[知识可信度](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/knowledge-reliability.md)与[验证边界](https://github.com/savormundane/Genshin-UGC-plugin/blob/v4.1.2/references/validation.md)。
