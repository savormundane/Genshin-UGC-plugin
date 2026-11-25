# 复杂类型协议

能力名：protocol-v2。通过produce.protocol和protocol_native接入scripts/protocol_codegen.py；Lua校验位于production_runtime.lua，多人集合原语位于runtime_multiplayer.lua。接口依据完整客户端API的ServerSignal章节和包内VarType定义。

schema 1保持原有四种标量与线上信封。schema 2仍使用有序signals、fields、phases，并在每个信号显式声明policy=ordered或snapshot。ordered要求连续序号，间隙拒绝；snapshot接受更大序号，拒绝重复与过期快照。不同用途不要共用一个序号通道。

类型包括integer、number、boolean、string、vector3、guid、entity、prefab_id、config_id及各自的_list。vector3使用{x,y,z}；列表为无洞有序数组。integer保持有符号32位；ID使用Lua整数，不能经过会丢精度的浮点转换。可选max_length限制字符串UTF-8字节数或列表长度，不改变平台原生容量。

同一合同输出原生信号资源、wire.json和client_bridge.lua；参数名前置session_key、round_id、sequence_id。旧项目只有明确选择后才迁移，不自动修改已有合同。结构体和字典不属于官方ServerSignal直接添加参数，需保留有依据的专用链路。

produce schema 2将server_to_client发送节点绑定为定向客户端信号。target默认signal_source，要求发送节点属于唯一可达的信号处理入口；也可指定field:字段名，从声明为entity的业务字段取目标。后者的实体权限与可见性由实际业务验证。没有可证明的目标时拒绝生成，不自动广播。

runtime_multiplayer.lua返回barrier(members)：revision、revise、roster、confirm、complete、ready、done、save、restore。撤回确认清除相应确认；修订和成员变化使旧确认失效。快照包含成员、确认及完成集合；调用方只加入允许公开的业务状态，不复制私有信息。

需要显式会话隔离、连续命令序号、冲突重发检查及完整恢复校验时，使用[多人会话与恢复](multiplayer-sessions.md)的sessions内联模块。该模块由项目显式启用，不自动迁移旧屏障或线上协议。快照是本地数据合同，不表示可通过ServerSignal直接发送任意表。

来源身份必须由真实传输层提供。模型可检查参数、集合和包顺序，不能证明宿主权限或真实网络行为。验证覆盖复杂类型往返、去重、间隙、成员变化、撤回及恢复。

中性合同可用ordered的整数命令通道与snapshot的向量／标识列表通道；字段数组保持发送顺序，每条通道独立维护序号。生成桥连续发送共享发送校验状态；收到第2条快照可以跨过缺失第1条，ordered第2条必须在第1条之后。错误列表元素、重复／旧序号、旧成员修订与过期检查点拒绝。撤回成员确认还清除其完成标记；整体阶段失效使用revise，不把集合原语当成业务状态机。

## 接入多人项目

[有序整数命令](../../samples/protocol/ordered.json)和[向量状态快照](../../samples/protocol/snapshot.json)可作为 `produce.protocol` 的输入。服务端图按生成的原生声明接收并验证来源、席位、阶段和取值范围，项目自行实现权威状态、结算和响应。确定性重放采用同一规则版本、随机源及遍历顺序，UI 状态留在客户端。

用[联合模型](joint-simulation.md)检查多端实例、不同收包顺序、超时、重连及成员变更。快照需要按接收方权限保留字段，可以改变隐藏字段并比较公开快照，检查是否泄露内容。持久存档使用[存储合同](storage-authoring.md)，协议和图写入关卡时按 [GIL 写回流程](../gil/native-authoring.md#将图信号和-lua-写入同一份-gil)核对最终挂载。
