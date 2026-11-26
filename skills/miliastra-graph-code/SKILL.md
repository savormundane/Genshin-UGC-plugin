---
name: miliastra-graph-code
description: 查原神千星奇域（UGC）节点图的节点签名、端口和事件，编写、检查与编译客户端或服务端 Graph Code 和复合节点。
---

# Miliastra Graph Code

| 任务 | 入口 |
| --- | --- |
| 查节点、作用域和端口 | `nodes_lookup`，例如按服务端作用域查「创建实体」或「启动定时器」。 |
| 检查单个节点图或复合节点的源码 | `graph_check`。已有制作配置或具名绑定时，传入相应的 `job` 或 `bindings`。 |
| 单独编译 GIA | `graph_build`。用 schema 1 构建配置取得 GIA、写入后的端口检查报告和产物 SHA-256 校验值。命令行可用 `qianxing.py build SPEC --out NEW_DIRECTORY`。 [构建参数](../../references/graph-code/node-graph-workflow.md) |
| 查试玩中的节点图打印 | 用 `logs_diagnose` 读取编辑器调试日志，按图 ID 和已知输入定位。 [导出日志读取](../../references/workflows/log-diagnostics.md#读取编辑器调试日志) |

整句无命中时，改查中文短词、别名或正式名称，再核对节点作用域。结果以编译器定义为依据，`port_evidence` 只支持已校准的版本和端口。涉及平台规则时查目标版本。 [中文查询](../../references/platform/knowledge-reliability.md#中文查询)

编写时按实际类型、端口和事件连接，检查图变量、结构体与复合引脚。 [编写规则](../../references/graph-code/graph-authoring.md) · [语法与完整文件示例](../../references/graph-code/graph-code-syntax.md#完整文件示例) · [编译错误](../../references/graph-code/validation-fixes.md)

编译使用可信的工程来源。信号和结构体资源中的 ID、类型和数据用顶层常量声明。

独立交付图或只检查源码时走上表。需要引用本轮新建对象并与 Lua、GIL 一起交付时，按 [produce 的具名绑定](../../references/workflows/produce.md#按名称连接制作阶段) 协作。文件挂载交给 [Miliastra GIL](../miliastra-gil/SKILL.md)，客户端控件和脚本交给 [Miliastra Editor](../miliastra-editor/SKILL.md#client-lua)。

修改已有图时，从目标工程核对图 ID、作用域和引用。编译后把 GIA 路径交给 `native_plan`，沿用原 GIL 的 SHA-256 校验值，审阅后另存，再重新读取并校验结果。 [修改计划](../../references/gil/native-changes.md#审阅并另存已有工程)

交付文件时写明变更、保存位置、用法和本次检查。分别记录编译、写入后的读取校验、模型测试、编辑器导入与游戏内运行。 [验证与交付](../../references/workflows/validation.md#交付反馈)
