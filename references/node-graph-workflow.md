# 直接制作节点图

## 从需求到图源码

先按 [能力合同](capability-contract.md) 选定权威端和实现层。完整游戏可能同时需要客户端 Lua、原生图和资源配置；不能把所有逻辑强塞进同一种语言。

1. 使用 `python scripts/qianxing.py inspect 当前基底.gil` 清点当前图、信号、Lua 和已识别的挂载；可传入模板目录作只读统计。工具只解析已识别的容器字段，未列出不代表不存在；原始模板始终只读。默认不复制模板到插件。
2. 写出事件入口→条件→状态读写→动作→完成/失败/重置；标明实体目标、变量类型、信号字段/顺序、权限和跨会话生命周期。保持客户端请求与服务器确认的边界。
3. 用 `python scripts/qianxing.py nodes "实体创建时" --scope server` 查询实际节点签名；按需要查函数/别名、输入/输出和具体端口类型，再读对应节点实现与官方说明。不从其他图的标题猜类型 ID。
4. 编写 Graph Code 类结构源码及 docstring 中的 graph_id、graph_name、graph_type。客户端图还须明确技能/过滤器等类别，不能沿用服务器事件模型。必要的信号、结构体和复合资源先在支持资源中定义。
5. 编辑过程中用 `graph check SOURCE.py --job JOB.json` 或 MCP `graph_check` 载入制作任务的声明，按诊断的原始文件、行号和端口修正。准备交付时用 `build` 生成 GIA/GIL 并回读。

## 统一命令

下列命令从插件根目录执行；其他工作目录使用脚本绝对路径。完整环境要求 Python 3.11–3.12。节点图/GIL/GIA核心链路仅用标准库。输出到当前项目的新目录，不写入插件源码或安装缓存。

    python scripts/qianxing.py plan --kind game --interface lua --multiplayer --format both
    python scripts/qianxing.py inspect 当前基底.gil --out 新清点报告.json
    python scripts/qianxing.py nodes "打印字符串" --scope server
    python scripts/qianxing.py graph check graphs/server.py
    python scripts/qianxing.py build build.json --out 当前项目的新交付目录

plan 根据已判定的任务类型列出责任分工，不是自然语言需求解析器；需求分析由技能完成。仅修改 Lua 时选择 kind=lua、format=source，不触发节点图制作。图模块选择 kind=nodes。inspect 不会修改输入，已有报告拒绝覆盖。

`graph check --job` 读取制作任务的 `graphs.spec`、项目资源、存档与协议声明。快检与构建共用资源合并和信号常量检查。同路径的不同内容，以及同 ID 或同名的冲突定义会报告两侧来源。有明确基底时会核对外部绑定。快检可在编辑单张图时使用，挂载和导出回读由完整构建完成。

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

相对路径按 build.json 所在目录解析。仅生成 GIA 时 formats=["gia"]，可不提供 base_gil。直接调用build生成GIL必须提供当前基底；使用produce的level阶段时可自动提供本轮生成基底，且写回范围只能是明确允许的顶层字段。字段10在本工具已识别布局中是节点图段，不将这个编号推断到其他格式。字段50保留给独立 Lua 替换流程，节点图构建不能顺带替换脚本。

默认仅新增明确列出的图，已有同名图需要使用有样本依据的局部补丁流程，不通过新图入口覆盖。需要信号、结构体、实体或模板资源时，设置 project_resources 和 include_sections，选择 graphs/signals/structs/templates/instances；支持资源目录不携带其他图源码，所有图在 graphs 中显式声明。HTML UI 先按离线工具链生成当前 bundle，再走其资源导出流程，不通过节点图构建伪装成已更新 UI。

max_stored_nodes 是可选的当前任务离线节点预算；不能替代编辑器复合节点展开计数，也不设置项目经验倍率为平台通用限制。

交付需要验证实体挂载时，可增加 `required_mounts`，每项包含 graph_name 和 entity_id。这些标识来自当前文件或Agent按已核验结构创建的资源；此构建命令只核验绑定。需要新增宿主或挂载时，由Agent另行完成有依据的写回步骤再核验，不把本命令的边界当作整个任务不能继续的理由。没有此合同时，报告不会声称挂载已验证或关卡可玩；要求的绑定缺失会拒绝完成交付。

## 运行与结果

编译在临时隔离副本内执行，不修改包内工具、原始模板、游戏源码或用户基底。完成后将 sources、models、gia（请求时）、level.gil（请求时）、logs 与 build-report.json 一次性交付到新目录。已有输出、重复图 ID/名称、严格校验错误、超出允许范围的修改及缺少指定挂载均被拒绝。

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

配套低层参数与 HTML 操作查 [离线工具链](ayaya-offline-toolchain.md)，API 和平台设置查 [官方索引](official-index.md)。

实际事件、分支、循环、变量与信号连接按 [节点逻辑设计](graph-authoring.md) 实施；信号声明和兼容规则见[平台接口与工程合同](implementation-policy.md)。
