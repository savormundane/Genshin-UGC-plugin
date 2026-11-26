# 直接制作节点图

## 从需求到图源码

按 [能力合同](../workflows/capability-contract.md) 确定由哪一端维护状态，再选择实现方式。一个游戏可以同时使用客户端 Lua、原生节点图和资源配置。

1. 用 `python scripts/qianxing.py inspect 当前基底.gil` 查看节点图、信号、Lua 和工具识别出的挂载。也可传入模板目录进行只读统计。报告覆盖已识别的容器字段，未列出的内容需另行确认。原始模板只读，默认保留在原处。
2. 写明从事件入口、条件、状态读写到动作的完整流程，以及完成、失败和重置时的处理。注明目标实体、变量类型、信号字段及顺序、权限和跨会话生命周期。明确哪些请求由客户端发出，哪些结果由服务端确认。
3. 用 `python scripts/qianxing.py nodes "实体创建时" --scope server` 查询实际节点签名；按需要查函数/别名、输入/输出和具体端口类型，再读对应节点实现与官方说明。不从其他图的标题猜类型 ID。
4. 编写 Graph Code 类，并在文档字符串中声明 `graph_id`、`graph_name` 和 `graph_type`。客户端图还需指定技能节点图、过滤器等类别，并使用相应的客户端事件。所需信号、结构体和复合资源先在项目资源中定义。
5. 编辑过程中用 `graph check SOURCE.py --job JOB.json` 或 MCP `graph_check` 载入制作任务的声明，按诊断的原始文件、行号和端口修正。准备交付时用 `build` 生成 GIA/GIL 并回读。

## 统一命令

以下命令从插件根目录执行。从其他目录执行时，使用脚本的绝对路径。完整插件环境见 [运行要求](../../docs/compatibility.md#运行要求)。节点图、GIL 和 GIA 的核心流程只用 Python 标准库。请在当前项目下另建输出目录，避免将产物写入插件源码或安装缓存。

    python scripts/qianxing.py plan --kind game --interface lua --multiplayer --format both
    python scripts/qianxing.py inspect 当前基底.gil --out 新清点报告.json
    python scripts/qianxing.py nodes "打印字符串" --scope server
    python scripts/qianxing.py graph check graphs/server.py
    python scripts/qianxing.py build build.json --out 当前项目的新交付目录

先由 Skill 分析需求，再用 `plan` 根据已确定的任务类型列出分工。仅修改 Lua 时选 `kind=lua`、`format=source`。制作节点图模块时选 `kind=nodes`。`inspect` 只读输入，报告必须保存到新路径。

`graph check --job` 读取制作任务的 `graphs.spec`、项目资源、存档和协议声明。单图检查与完整构建使用同一套资源合并和信号常量校验。相同路径的文件内容不同，或者同 ID、同名定义发生冲突时，报告会列出双方来源。提供基底后还会核对外部绑定。编辑单张图时可先做单图检查，挂载及导出回读由完整构建完成。

省略 `--job` 时，无法解析的项目专用信号或事件处理器显示 `not_checked`，已确认的语法和端口错误仍会失败。需要本轮制作分配的具名 ID 显示待绑定。

### 换用编辑器重新导出的 GIL

```text
python scripts/qianxing.py graph bind NEW.gil --from OLD.gil --bindings OLD_BINDINGS.json --out NEW_BINDINGS.json
```

旧表必须是与 `OLD.gil` 摘要匹配的 schema 2。对象类型、原生 ID、对象键和记录摘要都一致时，旧键自动沿用。若记录有改动、ID 重分配或出现歧义，报告列出原身份和候选，退出码为 2。用 `--spec CHOICES.json` 补充明确选择，例如 `{"currency:coin":"level/currency/1115684867"}`。所有键都有确定目标后才生成新表。

把新 GIL 和新绑定表填入图构建配置，继续 `graph check --job`、`build` 或 `produce`。原生修改也以新 GIL 重新生成计划。

## 构建描述 schema 1

以下是结构示例，路径和合同取自当前项目，不把示例作为默认玩法：

```json
{
  "schema": 1,
  "graphs": [
    {"source": "graphs/server.py", "scope": "server"},
    {"source": "graphs/client.py", "scope": "client", "category": "技能节点图"}
  ],
  "formats": ["gia", "gil"],
  "base_gil": "source/current.gil",
  "include_sections": ["graphs"],
  "allowed_top_level_fields": [10]
}
```

相对路径以 `build.json` 所在目录为基准。只生成 GIA 时，设置 `formats=["gia"]`，可省略 `base_gil`。直接运行 `build` 生成 GIL 时，必须提供当前基底。`produce` 的 `level` 阶段可以提供本次生成的基底，并且只允许写入明确指定的顶层字段。字段 10 是当前已识别布局中的节点图段，其他格式需单独核对。字段 50 用于独立的 Lua 替换流程，节点图构建不会替换脚本。

默认只新增明确列出的图。要修改已有同名图，请用有样本依据的局部补丁流程。需要信号、结构体、实体或模板时，设置 `project_resources` 和 `include_sections`，按需选择 `graphs`、`signals`、`structs`、`templates` 或 `instances`。所有图源码都在 `graphs` 中明确声明，辅助资源目录只放图所需的资源。HTML UI 通过离线工具链生成当前 bundle，再按其资源导出流程更新。

编译使用可信的工程来源。信号的 `SIGNAL_ID`、`SIGNAL_PAYLOAD`，以及结构体的 `STRUCT_ID`、`STRUCT_PAYLOAD` 和局内存档的 `STRUCT_TYPE` 使用顶层常量声明。导出和写回从这些声明静态读取数据，无法读取时会指出文件和字段。

`max_stored_nodes` 是本次任务可选的离线节点预算。复合节点展开后的数量以编辑器为准，项目经验倍率只适用于对应项目。

需要验证图已挂载到实体时，可在 `required_mounts` 中逐项指定 `graph_name` 和 `entity_id`。这些标识来自当前文件，或由 Agent 根据已核验的结构创建的资源。构建命令只核对这些绑定。需要新增宿主或挂载时，先按有样本依据的流程写回，再核验。报告只确认明确检查过的挂载，能否游玩需另行验证。缺少指定绑定时，构建会拒绝交付。

## 运行与结果

编译在临时副本中执行。包内工具、原始模板、游戏源码和基底保留原样。完成后将 `sources`、`models`、`logs` 和 `build-report.json` 写入新目录，按请求附上 `gia`、`level.gil`。已有输出、重复的图 ID 或名称、严格校验失败、修改超出允许范围，或缺少指定挂载时，构建会拒绝交付。

回读比较图集合、执行/数据连接、已声明变量、数据输入类型与常量，并验证原始输入摘要、基底原有图及受保护字段的原始字节和顺序。未使用的隐式端口与空变量占位按格式语义处理，不将占位当业务数据。新图写回若继承校准样本的额外变量，仅在该变量未被源码声明且不出现在节点记录中时移除，并记录到 compiler_template_normalization；疑似被引用时拒绝交付。不能把这些静态检查当作已证明玩法正确、模板版本兼容或实机通过。对当前内置编译器不支持的节点/类型，先比较真实样本和声明，使用存档工作流做有依据的局部补丁，不放宽校验冒充支持。

## 从真实制作中抽取的约束

- 多张图应按入口事件、状态职责和宿主拆分，图间联系通过明确的变量/信号合同表达；不可删除执行节点、事件入口或写操作来降低节点数。
- 同类只读查询去重前核对实体目标、作用域、采样时机与扇出；静态相同不代表运行时相同。具体扇出阈值需样本或编辑器证据。
- 整数常量、泛型包装和声明参数类型必须一致；修改结构体字段时联动其关联节点定义及端口，不能只改可读配置。
- “创建实体”按GUID创建已布设实体，官方合同没有数据输出。包内后端的模拟返回值不作为平台端口，统一节点目录只展示流程输出；Graph Code将它作为语句调用，需要实体引用时另用“以GUID查询实体”。赋值或嵌套使用其返回值会在构建前拒绝；“创建元件”的实体输出是另一个节点的合同，不混用。
- 图变换不假定节点数组按依赖排序；完成转换后重接最终集合中的新增消费者，保留需要原始容器类型的边。回读时检查源输出声明至目标输入的实际类型，不只核对引用存在；方法见 [原生数据流检查](native-dataflow-validation.md)。
- “已有存档配置”“客户端序列化成功”和“平台跨会话真实读写”是三个阶段。未连接平台节点时不能用本地记录冒充已保存。
- 真实时间、关卡时间、客户端表现时间和服务器资格计时分开设计；重新开始、离开、重连和倍速的重置规则明确在合同中。
- 保留用户当前音乐、映射、UI模板及挂载。原始基底后续发生修改时重新读取；不能用历史空模板覆盖新增配置。

底层转换参数和 HTML 操作见 [离线工具链](ayaya-offline-toolchain.md)。API 和平台设置见 [官方索引](../platform/README.md)。

实际事件、分支、循环、变量与信号连接按 [节点逻辑设计](graph-authoring.md) 实施；信号声明和兼容规则见[平台接口与工程合同](../workflows/implementation-policy.md)。
