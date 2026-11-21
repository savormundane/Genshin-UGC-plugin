---
name: qianxing-graph-code
description: 编写和修复千星奇域客户端／服务端节点图及复合节点，处理Graph Code DSL、执行流、数据流、端口类型和编译；不负责Lua控件与GIL容器写回。
---

# Graph Code

先用 MCP `nodes_lookup` 或 `qianxing.py nodes QUERY --scope server|client` 确认图作用域、调用签名与端口，再编写 DSL 并运行 `build`。Graph Code 使用受限 DSL，节点可编译只说明离线合同通过。客户端控件的 Lua API 见 [Client Lua](../client-controls-lua/SKILL.md)。

- 编写、验证、导出：[操作指南](references/workflow-details.md)、[语法](../../references/graph-code-syntax.md)、[编译错误](references/validation-fixes.md)。复用Ayaya桥接，不执行项目业务源码冒充静态验证。
- 变量、端口及结构体身份：[图变量](../../references/native-graph-variables.md)、[数据流审计](../../references/native-dataflow-validation.md)。区分节点定义与平台已确认语义。
- 跨客户端信号：[协议](../../references/protocol-v2.md)、[多人流程](../../references/workflows/qianxing-multiplayer/README.md)；业务协议由项目声明。
- 存储及成就：[存储生成](../../references/storage-authoring.md)；确认流程不冒充真实重进或平台授奖。
- 图编译使用 `qianxing.py build`；文件挂载由GIL领域处理。相关模型与回读按[验证边界](../../references/validation.md)报告，普通图修复不自动触发完整制作。

执行命令使用[专用Python](../../references/runtime-environment.md)，不依赖系统默认解释器。
