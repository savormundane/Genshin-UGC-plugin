# 原生自定义变量索引

能力名：native-variables。scripts/native_variables.py读取GIL中已校准的模板默认变量与实例覆盖，接入native inspect/audit、project inspect/check/consumers、native diff/plan及produce最终审计。依赖Python标准库、包内字段读取与结构体定义，不需要宿主文件系统或require。

## 读取与查询

```text
python scripts/qianxing.py native inspect LEVEL.gil
python scripts/qianxing.py native audit LEVEL.gil
python scripts/qianxing.py project inspect LEVEL.gil
python scripts/qianxing.py project consumers LEVEL.gil --kind custom_variable --name Counter --transitive
```

native inspect的custom_variables返回section、entity_id、name、type_id、原始组/条目位置及描述符/默认值摘要。project对象的kind为custom_variable，key区分template/entity及所属ID；同名变量可存在于不同实体。同一实体或模板内重复名称失败，不按大小写折叠或替换中文名称。

按名称查到多个对象时必须使用inspect返回的完整key。例如level/custom_variable/template/1086324800/Counter与level/custom_variable/entity/1086324800/Counter是不同对象，数字只是说明命名空间的示例，实际ID来自当前文件。

模板从section4/entry8读取(1,1)变量组；实例从section5/entry7读取。组11中的重复字段1是变量条目，名称/类型/默认值/描述符分别是条目2/3/4/6。模板entry7是另一类组件数据，不能照搬实例路径。仅作用于GIL声明；GIA变量资源包装未校准，不声称已读取。

## 类型与引用检查

- 检查空名称、重复名称/变量组、缺失描述符或默认值、声明/默认值/嵌入描述的类型不一致及缺失值载体；未知类型或变量组类别列入unresolved，严格审计拒绝。
- 默认值采用实体变量值结构，与节点图VarBase常量分开。读取标准标量/列表、结构体/结构体列表、字典，以及包内写入器已定义的枚举/阵营载体；后两者的格式读取不证明所有编辑器模式可创建该变量。
- 结构体及结构体列表核对声明目标、默认值和嵌套内容中的身份；默认值内的值实例ID不当成结构体定义ID。即使没有节点读取，缺失依赖也失败。
- 字典条目描述符可以只保存部分子类型；每个显式字段必须与默认值的完整描述一致。再核对完整键值类型、数量和深层结构体引用；不能因字典为空或没有消费者而跳过。
- 嵌套默认值继续核对类型及载体。标量数值范围、精度、所有列表载荷编码和平台配额不由本次读取认证。

对象关系包含declares_custom_variable、inherits_custom_variable、overrides_custom_variable，以及指向结构体的类型/默认值引用。继承关系仅来自文件内明确且已校准的实体→模板引用；实例同名条目表示覆盖，没有同名覆盖则记录继承。不会合并或改写默认值，也不根据名称猜测其它实体。

官方允许服务端动态创建自定义变量；默认声明与动态访问不是同一集合。当前未完整解析节点/Lua中的变量访问和标识值指向的对象，报告保留custom_variable_access_and_literal_targets与其它unindexed范围，complete_reference_index=false。消费者结果不能用于承诺任意ID/变量改名安全。节点图变量仍有独立的图作用域，不能与实体变量合并。

## 两种中性配置与故障

第一种可以在模板声明整数Counter和结构体初值，在实例覆盖Counter并保存整数键的结构体字典。第二种使用字符串Label、结构体列表及字符串键的结构体列表字典。两种都必须由当前基底或已校准写入器准备合法声明、默认值和结构体表；本能力负责读取/检查，不增加未经校准的写入格式。

先检查模板和实例的同名变量是否分属正确作用域，再查询结构体消费者。更改实例默认值后，native diff同时报告变量描述/默认值摘要和原始条目字节变化；受保护字段仍按修改计划合同核对。

反例包括：同一实体复制同名条目；把整数声明改成布尔而保留原默认值；删除被变量引用的结构体；修改字典嵌套值的结构体ID；把模板组件字段当成实例覆盖。类型/依赖错误应拒绝，未校准表示应标明unresolved，不能默认为空变量集合。

## 制作与证据

produce使用最终GIL执行相同审计和工程索引，不需增加另一个变量配置。已有工程通过native.spec/plan继续迭代；任何必需检查失败都不提交正式输出。portable收纳原有基底和补丁，独立重建时重新执行变量检查。原始输入、默认值和无关字节不被本读取器修改。

独立检查test_native_variables.py覆盖两份保留的原始校准、两种中性配置、继承/覆盖、结构体消费者、重复/类型/深层身份故障、差异、真实CLI及原输入目录不可用后的produce/portable重建。原始摘录缺少依赖时保留失败，不修补原件。静态和回读证据与Lua/原生图执行模型分开；编辑器导入、真实生命周期、保存重进及实机保持待验。
