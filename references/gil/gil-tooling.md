# GIL 检查与脚本替换工具

查看常见关卡对象用 MCP `project_inspect`；审阅并另存 GIL 用 [GIL 制作流程](native-authoring.md)。本页 Node.js 工具用于检查原始字段，或精确替换已有映射的 Lua。它无需第三方依赖，支持的容器见 [GIL 二进制结构](gil-format-diagnostics.md#gil-文件格式)。`scripts/gil-toolkit.mjs` 是 ES 模块，可在 Node REPL 中通过 `import` 加载。

命令：

    node scripts/gil-toolkit.mjs inspect 输入.gil
    node scripts/gil-toolkit.mjs replace-lua 输入.gil 映射名称.lua 新脚本.lua 新输出.gil

将示例中的路径换成实际绝对路径，含空格时加引号。输出须使用新的文件路径；输出父目录须先创建。命令只替换准确匹配的内嵌脚本正文，不新增映射、不改实体挂载、不生成任意节点图、不修改音乐和其他关卡设置。

模块导出 parse、encode、container、inspect、replaceLua、writeNew、sha256。解析保留原始字段字节、字段顺序及重复字段；修改时仅更新嵌套长度和容器长度。脚本映射不唯一或正文缺失即拒绝。

`inspect` 的 `roundtripByteIdentical` 表示未修改的数据载荷经过解析、重编码后与输入逐字节相同。替换脚本后，字段 50 之外的字节、容器中间元数据和尾部均原样保留。测试还覆盖文件截断、过长整数、脚本缺失和重复、尝试覆盖原文件及输出已存在的情况。结构正确不证明Lua语法、编辑器可导入或游戏运行正常。

未知节点图应先核对真实编辑器样本和对应类型定义。不要把历史用于改图的硬编码脚本直接拿来修改新存档。

新增协议及已有工程定义遵循[平台接口与工程合同](../workflows/implementation-policy.md)。

需要明确交付中的装配依赖时，按 [制作配置](../workflows/produce.md) 绑定各阶段的实际产物。

[原生结构生成与脚本关联](native-authoring.md) 说明 `level create/bind/inspect`。[客户端模型与自检](../workflows/client-simulation.md) 说明 Lua 5.3 逻辑模型、画布和模板诊断，以及日志开启步骤。
