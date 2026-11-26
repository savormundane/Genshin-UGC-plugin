# 显式存档迁移

`runtime_migration.lua` 按项目声明的版本顺序转换 QX 编码记录，返回原始字节和转换后的候选字节。模块只处理数据，实际保存由调用方发起。通过 `client assemble` 声明 `migration` 模块，可经 `produce.client.assembly` 内联。`codec` 来自 `storage` 模块或满足同一接口的项目实现。

```json
{"schema":2,"modules":[{"name":"storage","as":"Storage"},{"name":"migration","as":"Migration"}],"sources":[{"id":"app","source":"app.lua","requires":["Storage","Migration"]}]}
```

```lua
local old=Storage.codec({},1024,1)
local current=Storage.codec({"value","enabled"},1024,2)
local migration=Migration.create{target=2,versions={
 [1]={codec=old,validate=function(v)return type(v)=="number"end,
      next=2,upgrade=function(v)return {value=v,enabled=true}end},
 [2]={codec=current,validate=function(v)
      return type(v)=="table" and type(v.value)=="number" and type(v.enabled)=="boolean"
      end}}}
local candidate=migration:prepare(old:encode(7))
-- candidate.original保持原字节；candidate.candidate供显式写入流程使用。
```

版本为 1 至 65535 的整数。每个旧版本都须沿严格递增的 `next` 链达到目标版本。`validate` 必须返回 `true`。`upgrade` 由项目实现，须避免外部副作用。模块不能回滚回调自行产生的副作用。每步验证结果，再由目标codec编码、容量检查和解码验证。遇到未知版本、版本链断开或循环、存档异常、转换错误或超限时，模块会报错并拒绝生成候选。当前版本通过校验后直接返回原字节。

返回source_version、target_version、original、candidate、changed和steps。模块本身不写存储。生成的schema 3客户端适配器另提供以下提交入口：

```lua
-- tx为storage build/produce生成的客户端适配器实例，已完成read/open。
local ticket,backup=tx:prepare_migration(migration,1,80)
-- 1为integer_list字段序号，80为目标原生整数个数。
local request=tx:commit_migration(ticket,false)
-- 由既有信号回调处理write回读；调用commit返回不代表已保存。
```

票据内部绑定当前适配器实例（其game发送来源与固定槽位）、会话、修订、请求序列和原始正文；跨实例/槽位、重新读取、关闭、重复使用及正文变更均拒绝。玩家身份由真实game信号来源决定，不接受客户端任意填写的玩家ID作为授权。prepare要求整数列表字段采用equal确认，检查目标codec、字数、字段与整个记录容量。commit通过现有schema 3预期修订写入，读取旧值不能通过确认，失败不清空本地旧缓存。`backup.original` 是独立保存的原始字符串，写入确认成功前需保留。写入失败时应保留原存档，不能写入默认数据。这份备份只在本地 Lua 数据中。

适用前提是原生外层布局、协议及record_version仍可成功read/open，旧QX正文位于兼容布局的整数列表字段。此入口不迁移外层结构体、槽位或原生record_version；原生服务器拒绝的旧布局仍需单独设计显式转换，不能绕过兼容检查。迁移目标QX版本必须匹配当前生成器record_version，字典须能被当前生成器codec解码。未实现任意历史线上协议自动升级。

编辑字段为版本、字典、容量、校验器和转换函数。字典追加与版本兼容由对应codec合同负责；不同版本可显式提供不同字典。在副本中检查多步转换、超限、旧值保护、跨槽位票据和重复提交，再用[存储诊断](storage-authoring.md)核对真实回读和重进。受限信号模型仅支持迁移逻辑和客户端处理路径的结论。
