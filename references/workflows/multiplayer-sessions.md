# 多人会话与恢复

`runtime_sessions.lua` 提供独立 Lua 会话、全员确认与完成检查、有序命令和恢复检查点。回合玩法、投票规则、时间限制和协议编号由项目定义。用 `client assemble` 声明模块，可经 `produce.client.assembly` 内联到单文件，无需调用 `require` 或访问宿主文件系统。

```json
{"schema":2,"modules":[{"name":"sessions","as":"Sessions"}],"sources":[{"id":"app","source":"app.lua","requires":["Sessions"]}]}
```

```lua
local room=Sessions.create{session="neutral-session",members={10,20},phase="planning"}
local ok,reason=room:command(10,{
  session="neutral-session",revision=1,sequence=1,action="confirm",value=true
})
```

也可使用 `members={"alpha","beta"}` 和另一个 `session` 字符串。成员标识可为非负 Lua 整数或非空字符串。数组不得有空位或重复项，成员顺序属于快照的一部分。`phase` 由项目定义。

## 状态与命令

- view()返回深复制状态；ready()/done()分别检查全员确认和全员完成，空成员集合始终不通过。
- command(sender,packet)的sender必须来自能确认真实发送方的传输层，客户端自行填报的席位不能作为依据。模块只检查成员身份，不提供服务器认证。
- packet包含session、revision、sequence、action，可选value。action为confirm/complete/withdraw；confirm必须提供布尔value，其余不允许value。
- 每个成员、每个修订独立从sequence=1开始连续递增。遗漏、过期和乱序拒绝；与最后一次已接受命令完全相同的重发返回true,"duplicate"，不重复推进状态。同序号不同内容拒绝。
- complete只有在所有成员已确认后才接受。withdraw或confirm(false)创建新修订，清空全部确认/完成/命令序号，使旧修订在途包失效；这与旧barrier的单成员撤回不同，必须显式选择。
- roster(ids)用新成员快照创建新修订，即使列表相同也视为明确重置；advance(phase)显式进入新阶段并创建新修订。成员变化及阶段切换不由工具自动决定。

session必须相同，不能通过restore切换到另一个会话；新会话创建新对象。revision和serial是正/非负int32计数器；sequence是正int32。计数器耗尽时拒绝变化，不能静默回绕。

## 检查点

`checkpoint(state)` 复制项目提供的可公开状态，更新 `serial`，并返回完整的 schema 2 快照。快照包含会话、修订、阶段、成员顺序、确认与完成集合，以及各成员最后一条命令。项目须同时记录业务状态，并自行核对它与场景或存储是否一致。

restore(snapshot)先完整校验，最后才替换当前状态。返回true及独立复制的业务状态，或false与wrong_session/stale_snapshot/revision_identity_conflict。未知schema、异常集合、非成员确认、完成集合与确认不一致、缺失命令记录、重复成员、循环/带元表/过深表、非有限数值直接报错且不覆盖当前状态。

快照serial必须严格大于当前值，revision不得回退；同修订内phase和成员顺序必须一致。重复或迟到快照不会回滚已处理命令。更新修订的权威快照可以恢复成员变化。恢复后下一条命令仍须按保存的sequence连续发送。

快照供本地 Lua 使用。项目需要通过信号传递时，须使用官方支持的标量、向量、标识或列表，并明确编码和字段规则。保存检查点需要调用存储工具，持久化和真实重进恢复均需游戏内验证。

旧runtime_multiplayer.lua的barrier保持原行为。不要把sessions字段追加进旧线上信号后声称兼容。

联机交付时用游戏内试玩核对服务器接线、重发、玩家退出和恢复。Lua 模型结果用于判断所覆盖的会话状态。
