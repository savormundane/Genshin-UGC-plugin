# GIL 检查与脚本替换工具

scripts/gil-toolkit.mjs 是 Node.js ES 模块，也可通过可用的 Node REPL import。无需第三方依赖。仅支持当前验证的 GIL 容器，不把格式推断外推至所有版本/GIA。

命令：

    node scripts/gil-toolkit.mjs inspect 输入.gil
    node scripts/gil-toolkit.mjs replace-lua 输入.gil 映射名称.lua 新脚本.lua 新输出.gil

四个路径使用实际绝对路径并正确引号。新输出不得与输入相同或已经存在；输出父目录须先创建。命令只替换准确匹配的内嵌脚本正文，不新增映射、不改实体挂载、不生成任意节点图、不修改音乐和其他关卡设置。

模块导出 parse、encode、container、inspect、replaceLua、writeNew、sha256。解析保留原始字段字节、字段顺序及重复字段；修改时仅更新嵌套长度和容器长度。脚本映射不唯一或正文缺失即拒绝。

验证依据：真实项目GIL的原始载荷读写字节一致；替换脚本后字段50之外字节一致，容器中间元数据和尾部保留；测试截断、过长整数、缺失和重复脚本、原文件覆盖及输出已存在。结构正确不证明Lua语法、编辑器可导入或游戏运行正常。

未知节点图应先核对真实编辑器样本和对应类型定义。不要把历史用于改图的硬编码脚本直接拿来修改新存档。

新协议/图逻辑与必要文件适配由Agent按 [主动实现约定](implementation-policy.md) 设计并制作；已有配置读取兼容，缺少通用命令时补工具后继续交付。

跨能力执行与交付由 [内部制作核心](production-core.md) 的统一produce入口处理；兼容命令保留，当前核心和后端边界见该工作流。

[原生结构生成与脚本关联](native-authoring.md) 提供level create/bind/inspect及produce --next；[客户端模型与自检](client-simulation.md) 提供真实Lua5.3逻辑模型、画布/模板诊断和客户端脚本日志开启步骤。
