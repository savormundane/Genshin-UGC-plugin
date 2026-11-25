---
name: miliastra-graph-code
description: 查询千星奇域节点签名和端口，编写、检查和编译客户端／服务端 Graph Code 与复合节点。
---

# Miliastra Graph Code

| 任务 | 入口 |
| --- | --- |
| 查节点、作用域和端口 | `nodes_lookup`，例如按服务端作用域查「创建实体」或「启动定时器」。 |
| 检查单个节点图或复合节点的源码 | `graph_check`。已有制作配置或具名绑定时，传入相应的 `job` 或 `bindings`。 |
| 单独编译 GIA | CLI `qianxing.py build SPEC --out NEW_DIRECTORY`。 [构建参数与示例](../../references/graph-code/node-graph-workflow.md) |

整句无命中时，改查中文短词、别名或正式名称，再核对节点作用域。结果以编译器定义为依据，`port_evidence` 只支持已校准的版本和端口。涉及平台规则时查目标版本。 [中文查询](../../references/platform/knowledge-reliability.md#中文查询)

编写时按实际类型、端口和事件连接，检查图变量、结构体与复合引脚。 [编写规则](../../references/graph-code/graph-authoring.md) · [语法](../../references/graph-code/graph-code-syntax.md) · [编译错误](../../references/graph-code/validation-fixes.md)

独立交付图或只检查源码时走上表。需要引用本轮新建对象并与 Lua、GIL 一起交付时，按 [produce 的具名绑定](../../references/workflows/produce.md#按名称连接制作阶段) 协作。文件挂载交给 [Miliastra GIL](../miliastra-gil/SKILL.md)，客户端控件和脚本交给 [Miliastra Editor](../miliastra-editor/SKILL.md#client-lua)。

交付文件时写明变更、保存位置、用法和本次检查。编译、回读、模型与宿主结果按实际证据记录。 [验证与交付](../../references/workflows/validation.md#交付反馈)
