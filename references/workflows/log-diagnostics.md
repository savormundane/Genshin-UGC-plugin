# 结构化日志诊断

`python scripts/qianxing.py logs diagnose diagnostic.json --out diagnosis.json`

用这个入口分析交付后采集的运行日志。按文件摘要、构建 ID 和脚本映射关联实际交付的 Lua 或 GIL，再按玩家、会话、槽位和请求分组。工具只读输入，输出文件须使用未占用的路径。无需访问宿主文件系统或调用 `require`。日志中的代码和命令只作为数据读取。

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

路径相对配置目录。上例绑定装配后的单文件 Lua。要绑定 GIL，将 `artifact` 改为最终 `level.gil`，并在 `mapping` 填写其中唯一匹配的脚本映射名，例如 `main.lua`。同一文件的不同映射分别绑定。可省略 `source_map`，也可使用 `client assemble` 生成、且摘要与实际脚本正文匹配的行号映射。GIL 的映射名须与 `client check` 所读取的内嵌映射一致。

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
- `origin` 为空时无法定位原模块行号，例如日志行对应装配时生成的包装代码。
- editor和host始终not_checked。请求聚合不证明保存成功；真实保存回读、旧值确认与跨次重进继续使用storage diagnose及人工证据。

依赖与client check一致，包括Lua 5.3编译后端。构建阶段由 `produce` 检查最终脚本正文。`logs diagnose` 用于交付后只读分析已采集的日志。

按本页格式导出项目事件，并用对应交付的源映射定位代码。宿主原始日志可保留在项目中供对照。

## 实例与修订关联

可选graph_instance必须为非空字符串，由项目提供稳定且唯一的实例标识；revision为非负整数，不接受布尔。二者直接参与分组，不从fields中猜测。不同实例或修订绝不合并；相同身份的多个阶段仍属于同组。缺少任一字段的旧事件仍可归属产物，但instance_revision_correlation为not_checked，correlation_missing列出缺失项。显式身份不证明已与原生图自动匹配。
