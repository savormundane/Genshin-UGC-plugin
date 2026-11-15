# 客户端API检查

能力名：client-api-check。使用包内固定版本luaparse 0.3.1解析Lua 5.3语法树，Python读取官方客户端API目录并检查词法作用域、宿主成员、字段权限、枚举、调用方式、参数数量和已确定类型。不执行Lua正文。依赖Node与最终语法检查所需的lupa.lua53；不自动安装。解析器原文、MIT许可证及来源摘要保存在vendor/luaparse。

## 接口与合同

```text
python scripts/qianxing.py client check client.lua --contract check.json
python scripts/qianxing.py client check level.gil --contract check.json --source-map source-map.json
```

check.json使用schema 2，scripts逐一列出被检查的映射：

```json
{"schema":2,"scripts":[{"mapping":null,"source_sha256":"正文的64位SHA256","bindings":[]}]}
```

Lua文件的mapping为null；GIL使用精确映射名，默认必须覆盖全部映射。source_sha256计算方式为原始正文以UTF-8-sig解码后重新编码UTF-8的SHA256，保留CRLF，不做换行归一化。可从不带contract的client check报告中读取text_sha256。未知版本、陈旧正文、遗漏或重复映射拒绝。检查合同不是数字签名。

bindings可为局部变量或函数参数声明补充类型，例如`{"range":[6,13],"type":"ClientUITextBoxControl"}`。range是最终解码正文重新编码UTF-8后的零起始字节区间，右端不包含；必须准确命中唯一声明。字符串参数可声明value以解析动态成员名；integer参数也可声明Lua 5.3有符号64位整数value，以检查明确绑定的模板索引，布尔值/浮点数/越界整数拒绝。与已推断类型/值冲突的绑定拒绝；基类控件可显式细化为具体控件类型。声明是项目提供的静态前提，不证明运行时实参或控件类型，不能替代模型或宿主证据。

## 两套使用配置

新建工程：将`script:EnableUpdate(false)`等客户端源码加入level spec，为最终每个脚本登记摘要，produce任务增加`"client_check":{"spec":"check.json"}`。设置`script.enabled="false"`应报告类型错误并阻止正式输出。

已有工程：用native基底与修改配置制作，合同覆盖最终GIL的全部脚本，包括未挂载映射。通过bindings给通用控件参数声明类型，再检查具体字段和基类方法。替换正文后沿用旧摘要、漏掉辅助映射或提供错误声明区间均拒绝。portable自动携带合同和工具依赖，原输入路径不可用时仍可重建。

纯客户端制作的检查对象是build/client.lua；有最终level.gil时检查其全部映射。所有松散Lua仍执行语法检查，API合同只作用于明确的最终客户端。没有对应产物时拒绝。

## 报告与边界

variable_references检查GetGlobalCustomVariableValue及注册/移除变量变化监听。API合同可声明`"variable_targets":{"Level":{"kind":"entity","id":123}}`，支持Level、PlayerSelf、AvatarSelf范围，kind为entity或template。绑定是项目提供的静态前提，必须依据当前工程配置填写，不能仅根据同名实体推断运行时身份。

检查从最终GIL读取变量声明：实体自身声明优先；没有自身声明时，读取已校准的本地模板引用并检查继承声明。目标缺失/重复、变量缺失/重复、声明类型或默认值错误为failed；未绑定范围、动态名称、外部/未知模板继承、无GIL数据为not_checked。未知范围及非法目标合同拒绝执行。调用没有相关变量API时为not_applicable。检查保留原生type_id和声明位置，不把API返回any推断成具体Lua值类型，也不证明运行时玩家/角色选择、变量当前值和回调时序。

test_client_variables包含Level/PlayerSelf两套声明与继承、监听、动态及异常反例，以及Level/AvatarSelf两套最终GIL和produce输入不变/失败不提交验证。运行时身份仍须编辑器配置与实机独立确认。

client-check.json逐脚本输出api报告，包括已解析调用、API文档摘要、解析器摘要、声明绑定、errors与unresolved；可绑定源映射回到原模块行。未知调用、动态环境、未解析类型或列表元素返回not_checked，必需API阶段因此不能提交。明确错误返回failed。默认未提供合同的旧入口仍只执行语法检查。

解析区分局部同名变量、宿主别名、实例冒号/显式接收者与命名空间点号，处理多返回值及括号截断。紧凑控件表的省略类型结合本篇API中的字段、事件枚举和回调说明解析，保留类型依据行；不存在依据时不猜类型。integer字面值保留原文，避免JavaScript大整数精度损失。

此词法检查不证明跨函数运行路径、容器动态修改、监听清理或Tween时序。参数顺序、模板和资源需对应的工程交叉检查，不能把词法API检查通过当作完整客户端验收。工程引用、运行模型、编辑器和实机分别报告。开发侧test_client_api.py覆盖两套配置、反例、CLI、制作链和独立重建。

GIL合同检查还会将已解析的ServerSignal、RegisterServerSignalHandler和UnregisterServerSignalHandler调用名称与最终GIL信号登记表对照。signal_references记录逐调用映射、行号、名称和解析结果；名称缺失或歧义为failed，动态名称为not_checked，两者均阻止必需阶段提交。参数顺序采用下述直线流程检查，信号方向需要显式协议合同，实际送达另验；运行时控件ID也不能当作存档GUID查找。没有相关调用时为not_applicable，完整references状态仍保持not_checked。

API合同可增加protocol，内容与produce的protocol schema 1/2相同。制作任务同时声明protocol和client_check时，自动将该协议绑定到最终检查并写入client-api-contract.json；检查文件若另外声明不同协议，生成前拒绝。独立client check使用合同内的protocol。没有显式协议时保留旧行为，不推测方向。

protocol_references要求ServerSignal对应client_to_server，注册/移除服务端信号监听对应server_to_client；server_local不能作为客户端通信。调用未声明的名称或方向错误为failed，动态名为not_checked。若输入是GIL，还逐项核对声明协议的全部信号及有序字段名/类型，包括生成器既有session_key、round_id、sequence_id信封；缺失、歧义、字段漂移均失败。Lua输入没有原生数据时native_layout保持not_checked。方向依据是项目合同，不宣称原生格式包含方向标记；阶段、目标、回调解包及实际送达仍待各自模型/宿主验证。test_client_protocol覆盖整数/向量两套合同、方向/字段/重复/动态反例及制作失败不提交、输入不变。

template_references将InstantiateClientUIControl第一参数与最终GIL的instantiation_index对照，要求唯一模板及有效反向关联。该索引是模板GUID，不是数组序号。静态缺失/歧义/损坏绑定为failed，无法确定的动态索引为not_checked；均阻止必需客户端检查阶段提交。可使用摘要绑定的integer声明提供项目前提，不执行Lua求值或猜测动态表。GetClientUIControl参数为运行时ID，不按文件GUID误查；父控件存活性、动态实例及FindClientUIRoot运行结果仍待独立验证。无模板创建调用为not_applicable，完整references保持not_checked。

已支持单次声明、所有引用均为直接字段读取的局部常量表，例如生成器templates_as注入的UI_TEMPLATES。支持Panel=123和["Panel"]=123形式及局部同名变量隔离；只读取可静态确定的标量字段，不执行Lua。任何字段写入（包括动态键或方法定义）、重新赋值、将表赋给别名、传给函数或返回都会在全局分析前取消该表的常量推断；不会因为创建调用先出现就忽略后面的修改。嵌套/数组/动态键表及跨函数传递仍需项目显式合同，不声称完整数据流分析。

参数检查进一步覆盖同一词法作用域内的直线发送流程：按ServerSignal对象的创建位置追踪别名及AddInt/AddFloat/AddString等18种添加方法，在SendSignal处与最终原生登记的类型序列对照。packets给出expected与actual，数量、顺序和类型不一致为failed。分支、循环、短路条件、goto、跨函数使用、传给未知函数、动态AddParam或同对象重复发送保留not_checked；不猜测宿主是否清空发送对象。没有发送点时不宣称参数验证通过。该范围不证明监听回调解包、协议方向或实际送达。
