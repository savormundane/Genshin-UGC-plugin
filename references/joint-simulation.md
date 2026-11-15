# 客户端与原生图联合模型

能力名：joint-simulation。scripts/joint_simulator.py在独立进程中创建多个Lua 5.3实例，并连接scripts/native_model.py读取最终GIL的受限执行器。需要lupa==2.8的lua53，默认有进程超时和回调指令预算。

场景schema=2，clients为{id,source,mapping?,canvas?,params?}数组，source可以是Lua或GIL。GIL直接提取精确匹配的内嵌脚本与模板绑定。server可声明source、graph_ids及initial，后者按玩家字符串ID保存变量。steps支持tick、invoke、cursor、key、lifecycle、signal、settle、reenter。signal明确source、target、name、params；客户端请求与原生输出共用确定性队列。

faults为{name,source?,target?,occurrence?,action,delay?}列表，action支持drop、duplicate、delay及以延迟实现的reorder。assertions为{client,path,equals}；observations为{client,path,name}，报告保留实际队列时间线、待投递包和原生工作量。

```text
python scripts/qianxing.py simulate - --scenario SCENE.json --timeout 30 --out NEW_REPORT.json
```

produce场景中的@level引用本轮最终GIL。原生模型支持已实现的信号、条件、局部变量、自定义变量、列表、结构体和成就计数子集；遇到未实现节点或常量形状失败，不以成功桩放行。settle复制当前模型数据库到模型持久层，reenter从该层重建；它们不是平台保存和重进证据。

不模拟真实渲染、完整调度、所有Tween或平台权限。输入通过指定控件投递，不自动完成像素命中；原有schema 1模型接口继续使用。验证覆盖两种客户端数量、真实最终图信号投递、独立状态、延迟与重复、错误节点和超时。

clock可给{start:0}明确初始模型时刻；时间仅由tick推进。中性配置为2客户端与3客户端的定向回包，分别注入重复和延迟；延迟包未等到就断言会失败，追加足够tick后通过。未知执行节点、目标缺失、处理器缺失、预算或超时均失败，失败结果保留最后步骤、时钟、信号队列轨迹及错误栈，不替换为成功桩。

列表构造／局部变量在单次事件中保留对象身份。自定义变量读取、列表取项、结构体拆分、局部变量及赋值保留容器引用；清除、插入、移除、修改和连接列表直接作用于该对象。负索引、越界索引与非列表输入失败。传输投递时复制调用方数据，已发出的回包保留发送时的数据快照，不随后续容器操作改变。原生图没有实际执行时报告native_graph_model=not_checked；未命中的传输故障也单独标为not_checked，不因场景完成而宣称已覆盖。

图的自身实体由最终GIL的实例挂载读取，同图多挂载分别执行。模板实例或独立图测试可在server.instances显式声明[{graph_id,owner_entity}]，重复实例与不存在的图拒绝；未绑定所属实体的图执行Get_Self_Entity会失败，不使用信号发送者代替。

监听信号的事件源实体为接收图所属实体，信号来源实体为本次发送者，两者分别输出。需要读取事件源GUID时，场景须提供server.entity_guids，例如{"21":10021,"22":10022}；模型不把运行实体编号当作GUID，也不返回固定占位值。未绑定所属实体或未提供所需GUID时失败。

服务端“发送信号”派发到所有已配置实例中匹配的服务端监听器，信号来源为发送图所属实体，不沿用最初客户端请求者；没有监听器时不产生回包。服务器内部派发加入同一FIFO与执行预算，容器参数保持引用；传输入口和定向客户端回包使用数据快照。内部FIFO时序是模型合同，不能推断宿主异步时序。只有已校准的“发送客户端脚本信号”角色生成定向客户端消息；客户端图的“向服务器节点图发送信号”节点出现在服务器执行链中会失败。

监听器由信号声明角色或已知通用监听节点300001的信号名识别；任意未知节点带同名元数据不会被当成事件入口。未知信号、外部请求参数个数错误、重复信号名或角色标识失败。服务端广播与最终编译图的两种多实例配置、循环预算和错误方向均有独立回归；这里不声明客户端技能图执行器已实现。

设置自定义变量按显式“是否触发事件”决定是否派发，省略时按官方默认true处理；同值设置也派发。事件只进入目标实体挂载且泛型匹配的自定义变量变化处理器，非容器提供变化前后快照，容器读取变化前后值会失败，须重新获取变量。直接修改容器不派发事件。模型使用确定性FIFO，在当前事件流程完成后处理已排队事件；整个事件链共用执行预算，循环触发不会无界运行。此队列顺序是离线模型合同，不声明真实宿主调度时序已验证。隐含布尔镜像字段与触发字段不一致时拒绝执行和静态审计。

上述容器及变量事件规则依据包内官方“自定义变量”第五节、“结构体”“字典”引用传递说明以及服务端事件／执行／查询节点签名。模型仍只覆盖登记节点，未实现节点、结构体默认值及未知变量默认类型明确失败。

有限循环模型按原生起始值和终止值的闭区间执行，每次先执行循环体，完成或跳出后执行完成出口。跳出节点须连接当前活跃循环的跳出输入；无效入口、非整数边界、递归进入同一活跃循环或超出执行预算失败。循环计数计入server_work，即使循环体为空也受预算限制。此支持不代表列表迭代循环或完整宿主调度已实现。

execution_status表示运行是否成功，acceptance表示是否满足场景验收。没有断言、配置的server.graph_ids未全部执行、服务端未执行或必需故障未命中时acceptance保持not_checked。faults条目的required默认true；只有明确非验收故障可设false，命中状态仍如实报告。produce要求声明的模拟acceptance=passed，否则回滚，不提交正式输出。观察实验可读取未验收的观察结果，但不得以此声称场景通过。

原生实体创建使用显式entity_created步骤，规则及边界见[native-lifecycle](native-lifecycle.md)。只对已配置图实例派发创建事件，不默认自动初始化所有图。报告新增lifecycle_events，其他生命周期未实现时不作通过声明。

客户端条目可增加variables，例如`[{"scope":"PlayerSelf","entity":42,"name":"Score"}]`，将官方Level/PlayerSelf/AvatarSelf范围明确绑定到原生模型实体。相同客户端的同一scope只能对应一个实体，scope/name不得重复。server.initial必须包含所有选定变量；这些初值在客户端OnInit前可读，不会因初始化而发送变化通知。变量缺失时拒绝，不能用nil假装宿主默认值。

步骤`{"op":"sync_variables","client":42,"notify":true}`从当前原生模型读取该客户端选定变量的快照，先更新全部选定值，再按声明顺序调用已注册的RegisterCustomVariableChangedHandler回调。回调仅接收范围和名称；当前值通过GetGlobalCustomVariableValue获取。notify必须显式声明；false更新值但不通知，true通知每个选中变量，包括值相同的快照。这是显式模型步骤，不自动推断原生事件是否应跨客户端同步，也不模拟网络复制延迟或自动发现玩家身份。

UnregisterCustomVariableChangedHandler取消该范围/名称的监听；脚本销毁清除监听并拒绝后续同步。原生实体移除后拒绝读取其同步快照。不同客户端使用独立Lua表，修改客户端快照不会写回服务器；需要写入仍通过项目声明的原生信号。报告variable_syncs记录同步时间、目标、范围和通知策略，不能当作宿主复制时序证据。

test_joint_variables覆盖PlayerSelf/AvatarSelf两套配置、服务端实际图写变量、初值、玩家隔离、监听/取消、销毁及非法选择，并以produce读取最终GIL。证据为Lua/原生子图模型和离线构建；编辑器与实机仍待验。
