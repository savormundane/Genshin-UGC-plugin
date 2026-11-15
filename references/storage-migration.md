# 显式存档迁移

runtime_migration.lua按项目声明的版本链迁移QX编码记录，返回原始字节和候选字节，不直接调用宿主或写入存储。使用client assemble的migration模块，经produce.client.assembly内联；codec来自storage模块或符合相同接口的项目实现。

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

版本为1..65535整数；每个旧版本必须沿严格递增的next到达目标，不自动猜测跳转。validate必须返回true；upgrade是项目源码，必须无外部副作用。模块不能回滚回调自行产生的副作用。每步验证结果，再由目标codec编码、容量检查和解码验证。未知版本、断链、循环、异常档、错误转换及超限直接报错，不产生可提交候选；当前版本通过校验后保持原字节。

返回source_version、target_version、original、candidate、changed和steps。模块本身不写存储。生成的schema 3客户端适配器另提供以下提交入口：

```lua
-- tx为storage build/produce生成的客户端适配器实例，已完成read/open。
local ticket,backup=tx:prepare_migration(migration,1,80)
-- 1为integer_list字段序号，80为目标原生整数个数。
local request=tx:commit_migration(ticket,false)
-- 由既有信号回调处理write回读；调用commit返回不代表已保存。
```

票据内部绑定当前适配器实例（其game发送来源与固定槽位）、会话、修订、请求序列和原始正文；跨实例/槽位、重新读取、关闭、重复使用及正文变更均拒绝。玩家身份由真实game信号来源决定，不接受客户端任意填写的玩家ID作为授权。prepare要求整数列表字段采用equal确认，检查目标codec、字数、字段与整个记录容量。commit通过现有schema 3预期修订写入，读取旧值不能通过确认，失败不清空本地旧缓存。backup.original是独立字符串，在成功确认前保留；失败不得写默认档。备份不等于平台独立备份槽。

适用前提是原生外层布局、协议及record_version仍可成功read/open，旧QX正文位于兼容布局的整数列表字段。此入口不迁移外层结构体、槽位或原生record_version；原生服务器拒绝的旧布局仍需单独设计显式转换，不能绕过兼容检查。迁移目标QX版本必须匹配当前生成器record_version，字典须能被当前生成器codec解码。未实现任意历史线上协议自动升级。

编辑字段为版本、字典、容量、校验器和转换函数。字典追加与版本兼容由对应codec合同负责；不同版本可显式提供不同字典。无平台保存重进证据。test_runtime_migration覆盖数值→表→新表多步转换、单步配置、未知版本/断链/异常转换/容量拒绝、原始数据保留以及两套produce装配后Lua执行。生成适配器专项覆盖两套配置、跨槽位票据、过期读取、重复提交、旧值确认、成功/失败回读及关闭失效；该专项使用受限信号替身，不是原生图联合执行或宿主测试。
