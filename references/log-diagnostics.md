# 结构化日志诊断

`python scripts/qianxing.py logs diagnose diagnostic.json --out diagnosis.json`

该入口用于制作链交付后的人工运行反馈。将日志与实际交付Lua或GIL的摘要、构建ID、脚本映射绑定，再按玩家、会话、槽位、请求分组。读取输入，不写入存档；输出文件必须不存在。无需宿主文件系统或require，不执行日志中的代码或命令。

## 配置与接入点

```json
{
  "schema": 2,
  "logs": ["events.jsonl"],
  "bindings": [
    {"build_id": "neutral-build", "artifact": "client.lua", "mapping": null, "source_map": "source-map.json"}
  ]
}
```

路径相对配置目录。第一种配置用于装配后的单文件Lua；第二种配置将artifact改为最终`level.gil`，mapping改为其唯一脚本映射名，例如`main.lua`。同一文件的不同映射分别绑定。source_map可省略；提供时必须与实际正文摘要匹配，可使用client assemble输出的行号映射。GIL映射需与client check接受的内嵌映射一致，不能用旧版源文件猜测行号。

每行一个JSON事件：

```json
{"build_id":"neutral-build","artifact_sha256":"替换为最终文件的64位小写SHA256","mapping":null,"line":12,"message":"write timeout","level":"error","player":"p1","session":"s1","slot":0,"request":7,"phase":"write","graph_instance":"graph-a/entity-1","revision":3,"fields":{}}
```

必需字段为build_id、artifact_sha256、mapping、message。line是最终Lua正文的正整数行号；level可用debug/info/warning/error。关联字段允许字符串或整数；fields为数据对象。不同玩家、会话、构建、文件或映射不会合并。请求分组缺少字段时保持缺失，不推断玩家或请求身份。

## 结果与边界

- `passed`仅表示所有事件可解析且绑定匹配；错误日志仍计入observed_error_count，不能据此声称游戏通过。
- 不匹配摘要、未知构建、无法解析的行或空日志返回not_checked；未解析文本原样保留。不自动尝试执行或修复日志。
- 错误字段、未知schema、陈旧行号映射直接拒绝。输入摘要在结束时再次核对。
- 每个绑定和事件分别报告artifact_syntax；编译检查只编译正文，不执行。语法失败不阻止对失败产物的日志归因。
- origin为空表示没有可用源行映射，包括装配包装行，不伪造原模块行号。
- editor和host始终not_checked。请求聚合不证明保存成功；真实保存回读、旧值确认与跨次重进继续使用storage diagnose及人工证据。

依赖与client check一致，包括Lua 5.3编译后端。构建阶段继续使用produce的最终正文检查；logs diagnose是交付后只读诊断，不作为尚未运行宿主的构建阶段。

按本页格式导出项目事件，并用对应交付的源映射定位代码。宿主原始日志可保留在项目中供对照。

## 实例与修订关联

可选graph_instance必须为非空字符串，由项目提供稳定且唯一的实例标识；revision为非负整数，不接受布尔。二者直接参与分组，不从fields中猜测。不同实例或修订绝不合并；相同身份的多个阶段仍属于同组。缺少任一字段的旧事件仍可归属产物，但instance_revision_correlation为not_checked，correlation_missing列出缺失项。显式身份不证明已与原生图自动匹配。
