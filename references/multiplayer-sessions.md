# 多人会话与恢复

runtime_sessions.lua提供独立Lua会话、成员屏障、有序命令和恢复检查点，不包含回合玩法、投票政策、时间限制或默认协议编号。使用client assemble的模块声明，通过produce.client.assembly内联至单文件，不需要require或宿主文件系统。

```json
{"schema":2,"modules":[{"name":"sessions","as":"Sessions"}],"sources":[{"id":"app","source":"app.lua","requires":["Sessions"]}]}
```

```lua
local room=Sessions.create{session="neutral-session",members={10,20},phase="planning"}
local ok,reason=room:command(10,{
  session="neutral-session",revision=1,sequence=1,action="confirm",value=true
})
```

另一种中性配置可使用members={"alpha","beta"}和独立session字符串。成员允许非负Lua整数或非空字符串，数组无洞且不重复；顺序属于成员快照合同。phase由项目定义，不预置游戏阶段。

## 状态与命令

- view()返回深复制状态；ready()/done()分别检查全员确认和全员完成，空成员集合始终不通过。
- command(sender,packet)的sender必须来自真实传输来源绑定，不能直接相信客户端声明的席位。模块只检查成员身份，不提供服务器认证。
- packet包含session、revision、sequence、action，可选value。action为confirm/complete/withdraw；confirm必须提供布尔value，其余不允许value。
- 每个成员、每个修订独立从sequence=1开始连续递增。遗漏、过期和乱序拒绝；与最后一次已接受命令完全相同的重发返回true,"duplicate"，不重复推进状态。同序号不同内容拒绝。
- complete只有在所有成员已确认后才接受。withdraw或confirm(false)创建新修订，清空全部确认/完成/命令序号，使旧修订在途包失效；这与旧barrier的单成员撤回不同，必须显式选择。
- roster(ids)用新成员快照创建新修订，即使列表相同也视为明确重置；advance(phase)显式进入新阶段并创建新修订。成员变化及阶段切换不由工具自动决定。

session必须相同，不能通过restore切换到另一个会话；新会话创建新对象。revision和serial是正/非负int32计数器；sequence是正int32。计数器耗尽时拒绝变化，不能静默回绕。

## 检查点

checkpoint(state)复制项目给出的可公开状态，更新serial并返回schema 2完整快照，包含会话、修订、阶段、成员顺序、确认/完成集合和各成员最后命令。项目负责同时捕获业务状态；模块不推断该状态与场景或存储是否一致。

restore(snapshot)先完整校验，最后才替换当前状态。返回true及独立复制的业务状态，或false与wrong_session/stale_snapshot/revision_identity_conflict。未知schema、异常集合、非成员确认、完成集合与确认不一致、缺失命令记录、重复成员、循环/带元表/过深表、非有限数值直接报错且不覆盖当前状态。

快照serial必须严格大于当前值，revision不得回退；同修订内phase和成员顺序必须一致。重复或迟到快照不会回滚已处理命令。更新修订的权威快照可以恢复成员变化。恢复后下一条命令仍须按保存的sequence连续发送。

快照是本地Lua数据，不是任意结构体通信实现。使用实际官方支持的标量、向量、标识和列表协议传递时，项目须显式设计编码/字段规则。写入存储也需调用存储能力；本模块不宣称检查点已持久化或真实重进可恢复。

旧runtime_multiplayer.lua的barrier保持原行为。不要把sessions字段追加进旧线上信号后声称兼容。

联机交付时用游戏内试玩核对服务器接线、重发、玩家退出和恢复。Lua 模型结果用于判断所覆盖的会话状态。
