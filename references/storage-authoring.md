# 存储与成就生成

能力名：storage-authoring。使用qianxing.py storage build|inspect|diagnose；生成器为scripts/storage_authoring.py，客户端事务与编码为scripts/runtime_storage.lua。依赖Python标准库；实际编译依赖包内Ayaya，Lua模型依赖lupa.lua53。

```text
python scripts/qianxing.py storage build STORAGE.json --out NEW_DIRECTORY
python scripts/qianxing.py storage inspect CURRENT.gil
python scripts/qianxing.py storage diagnose EVENTS.json
```

STORAGE使用schema=2，字段为name（ASCII标识符）、struct_id、template_id、graph_id、slots、capacity_bytes、fields，可选dictionary、previous_dictionary、achievements。三个ID是显式应用ID，生成前核对当前命名空间；slots为1..32，每槽一条结构体记录。fields为有序{name,type,default,confirm}；当前原生布局校准integer、boolean、integer_list。confirm为equal、min、max、contains_bits，后面三种只用于整数。容量由当前布局配置确定，不沿用其他游戏数字。

输出storage.py、resources、contract.lua、runtime.lua、client_adapter.lua和storage.json，附输入／产物清单。resources包含编译器使用的同源字段形状与局内存档定义；原生持久化种类由局内存档写回设置，不由DSL展示分类推断。produce schema 2通过storage:{spec:路径}接入；可消费本轮level或storage.base。原生声明、槽位、信号和生成图一起写回，最终回读检查。

原生请求按真实信号来源实体读写。信号名称为name_read_槽号、name_write_槽号及对应_reply；回复由最终原生图中的定向客户端信号节点发送，不能把全局广播当作Lua回包。client_adapter.lua返回function(game,script,slot,timeout,retries)，构建事务对象。调用read、write(values,exitIntent)、tick、cancel_exit和close；成功读取后才允许写入。旧读取不清除待确认写入；内容不符合确认策略保持等待；重试使用同一请求号。取消退出不取消在途保存。

编码器通过codec(dictionary,limit,version)提供encode/decode、words/from_words。键排序确定、词典只追加，压缩容量和原生整数容量分别检查。未知版本、损坏数据和超限拒绝，不截断或自动清档。fields中的确认策略描述回读验收，业务是否合并、取极值仍须在调用方明确。

record_version可显式设为1..65535，默认1；原生记录增加保留的qx_record_version字段。读写都先检查已有记录版本和记录数，不兼容时返回失败并保留原数据。qx_前缀和生成器局部变量名不可作为业务字段。integer_list可给max_items；默认capacity_bytes整除8。capacity_bytes同时限制应用逻辑载荷（版本及整数各8字节、布尔1字节、列表每项8字节）与编码正文；它不是未经测量的平台配额。生成报告给出默认载荷与预算，客户端和原生写入入口分别检查。

适配器另提供encode(value,wordCount)、decode(words)及write_encoded(value,fieldIndex,wordCount,exitIntent)。只将编码数据存入显式integer_list字段，写前核验已有非空编码可解码；未知版本／损坏正文不得直接覆写。词典兼容由previous_dictionary前缀检查约束。编码字段的words数量仍须满足该字段及整条记录预算。

空整型列表通过官方列表构造、局部引用和清除列表节点生成，不向严格DSL提交空列表字面量。拆分参数的列表占位仅供编译期类型推断，最终绑定去除非原生输入；原生声明与默认值仍是配置中的真实空列表。原生结构和帮助节点先按字段规则写入基底，常规存储构图只导入图与信号，避免再次结构导入改写已有声明。

基底尚无辅助声明时，生成器保留包内平台校准的辅助声明及其引用的三份结构体定义，作为后端导入所需的完整依赖；不携带校准文件的图、实体或存档布局。配置结构体ID若与不同内容的校准定义冲突则拒绝，不能静默重用身份。最终native audit同时检查存储结构体、辅助声明与槽位引用，未被图使用的资源也不能悬空。

成就配置为{id,name,goal}，独立于存储确认；不能从请求发出推断平台已授奖。diagnose输入是事件数组，字段player、request、phase、artifact_sha256及可选fields，输出按玩家、请求、交付摘要关联的分段时间线；它只整理已观察事实。

新建level时，存储图挂到生成器唯一匹配的校准控制器并登记图资源；已有base必须显式提供host_entity_id。生成图保持配置graph_id。成就使用tx.achievement:request(id)，原生计数后独立查询完成状态再回包；close移除其监听，不将本地发送成功视为确认。

验收包含空记录、异常记录、两种槽位配置、旧回复、内容不符、超时、容量边界、跨玩家隔离及原生图回读。编辑器保存、同一发布关卡重进和平台奖励仍需人工宿主证据。

## schema 3：会话与修订保护

新工程可显式设置schema=3，其余字段布局沿用schema 2。schema 2原有信号和记录保持兼容，不自动迁移既有记录。schema 3保留qx_record_version、qx_protocol、qx_session、qx_revision、qx_request五个整数元数据字段，逻辑头部为40字节；session、revision、ok及qx_前缀不得作为业务字段名。

信号使用name_v3_read_槽号、name_v3_open_槽号、name_v3_write_槽号及对应_reply。read请求为[request]，open为[request,session,revision]，write为[request,session,revision,业务字段...]；回复为[request,ok,session,revision,业务字段...]。revision在请求中是预期当前修订，在成功open/write回复中是更新后的修订。

客户端read成功后自动申请当前会话加一的open。服务端仅在预期修订和会话前驱匹配时接纳，保留业务内容并将修订加一；客户端ready=true后才能write。写入要求会话匹配、请求号大于已接纳请求、预期修订匹配；成功后修订加一。完全相同的重复写请求返回现存结果，不重复写入；相同请求号但内容不同、旧会话、旧修订拒绝。列表内容逐项精确比较，包含空列表。确认策略仍只决定客户端如何确认回读，不改变服务端的业务合并策略。

超时重试沿用相同请求、会话和预期修订。旧回复或修订不符不会确认当前写入；失败或超时后重新read/open才能继续写。取消退出意图不取消在途保存。应用通过tick推进超时，close注销read/open/write及成就监听。新会话会使旧会话的后续写入失效，不提供多个同时活跃写入者的自动合并。

原生读写入口检查记录数、协议及记录版本、非负元数据和声明容量；不兼容或超限旧记录保持原样。写入后另建读取链检查会话、请求和修订，再由客户端检查字段内容。逻辑保存成功仍不等于真实平台结算、重进持久化或成就授奖。

diagnose可额外接收slot、session、expected_revision、revision。使用任一新字段时必须同时提供slot和session；按玩家、槽位、会话、请求和交付摘要分组，避免重连后请求号复用混淆日志。旧日志格式继续可读，日志内容不会作为命令执行。

开发验证入口为development/test_storage_v3.py：两种中性配置实际编译到最终GIL，验证防重放、重复幂等、异常旧档保护、容量、回读失败和模型重进，并连接两个独立Lua实例注入丢包、重复与迟到回复。该证据仅属于编译回读和离线模型。
