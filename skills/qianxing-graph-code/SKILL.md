---
name: qianxing-graph-code
description: 编写和修复千星奇域客户端／服务端节点图及复合节点，处理Graph Code DSL、执行流、数据流、端口类型和编译；不负责Lua控件与GIL容器写回。
---

# Qianxing Graph Code

先用 MCP `nodes_lookup` 或 `qianxing.py nodes QUERY --scope server|client` 确认图作用域、调用签名与端口。编写后用 MCP `graph_check` 或 `graph check SOURCE.py --job JOB.json` 核对制作任务的信号与项目声明。需要交付图文件时，用 `qianxing.py build` 编译。客户端控件的 Lua API 见 [Qianxing Editor · Client Lua](../qianxing-editor/SKILL.md#client-lua)。

- 编写、验证、导出：[操作指南](references/workflow-details.md)、[语法](../../references/graph-code-syntax.md)、[编译错误](references/validation-fixes.md)。复用Ayaya桥接，不执行项目业务源码冒充静态验证。
- 变量、端口及结构体身份：[图变量](../../references/native-graph-variables.md)、[数据流审计](../../references/native-dataflow-validation.md)。区分节点定义与平台已确认语义。
- 制作原生机关、技能、商店交互和多人关卡时，用 [原生玩法制作](../../references/native-gameplay.md) 中的资源 ID 和挂载合同。
- 从已有 GIL 测试实体计时器或匀速直线运动时，用 `simulate run` 或 MCP `simulate`，查询真实挂载并对位置作断言。 [联合模型](../../references/joint-simulation.md)
- 跨客户端信号：[协议](../../references/protocol-v2.md)、[多人流程](../../references/workflows/qianxing-multiplayer/README.md)；业务协议由项目声明。
- 存储及成就：[存储生成](../../references/storage-authoring.md)；确认流程不冒充真实重进或平台授奖。
- 通过 [制作链的具名绑定](../../references/production-v2.md) 写 `native_id("currency:coin")` 等引用，单独校验可指定 `graph check SOURCE.py --bindings BINDINGS.json`。
- 文件挂载由 GIL 领域处理。相关模型与回读按[验证边界](../../references/validation.md)报告，普通图修复不自动触发完整制作。

执行命令使用[专用Python](../../docs/runtime-environment.md)，不依赖系统默认解释器。
