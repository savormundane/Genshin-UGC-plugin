# 试玩日志诊断

用 `logs_diagnose` 读取编辑器导出的二进制调试日志，或关联项目自行记录的 JSONL 事件。将输入放进已授权的工程目录，MCP 调用传诊断配置的路径和 SHA-256 校验值。CLI 输出可另存到新文件。

```text
python scripts/qianxing.py logs diagnose DIAGNOSTIC.json --out NEW_REPORT.json
```

工具通过文件分析日志，日志中出现的代码、命令和打印文字按数据处理。采集客户端脚本日志的操作见[开启日志](client-simulation.md#开启客户端脚本日志)。

## 读取编辑器调试日志

```json
{
  "schema": 2,
  "logs": [{"path": "playtest.bytes", "format": "editor-debug-log", "offset": 0, "limit": 100}],
  "bindings": []
}
```

每个二进制日志最多 64 MiB。`offset` 从 0 开始，按识别出的打印记录分页，`limit` 可为 1 至 1000，用 `editor_logs[].next_offset` 取下一页。报告保留客户端 Lua 或节点图的打印原文、记录位置，以及记录中可读的图 ID、实体 ID 和时间。未识别项计入 `ignored_record_count`，图轨迹中的字符串不计作打印。

二进制格式依据社区对双长度封套及 1.22.2、1.23.2 字段路径的观察。插件用合成样本检查读取、分页和拒绝条件。二进制日志可以帮助定位打印，但构建归属、严重程度、编辑器导入与游戏内验收标为 `not_checked`。 [社区格式观察](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/debug-log.mjs)

## 配置与接入点

JSONL 用于把事件和交付的 Lua 或 GIL 关联。每个路径相对诊断配置目录。

```json
{
  "schema": 2,
  "logs": ["events.jsonl"],
  "bindings": [
    {"build_id": "neutral-build", "artifact": "client.lua", "mapping": null, "source_map": "source-map.json"}
  ]
}
```

上例绑定装配后的单文件 Lua。要绑定 GIL，使用最终 `level.gil`，并在 `mapping` 填写唯一匹配的脚本映射名，可从 `client check` 获取。同一 GIL 的不同映射需要分别绑定。`source_map` 可省略。声明时使用 `client assemble` 生成、SHA-256 与实际脚本正文匹配的行号映射。

每行记录一个 JSON 事件。

```json
{"build_id":"neutral-build","artifact_sha256":"替换为最终文件的小写 SHA-256","mapping":null,"line":12,"message":"write timeout","level":"error","player":"p1","session":"s1","slot":0,"request":7,"phase":"write","graph_instance":"graph-a/entity-1","revision":3,"fields":{}}
```

必需字段为 `build_id`、`artifact_sha256`、`mapping`、`message`。`line` 为最终 Lua 正文的正整数行号，`level` 可为 `debug`、`info`、`warning` 或 `error`。关联字段允许字符串或整数，`fields` 为数据对象。分组按明确声明的构建、文件、映射、玩家、会话、槽位、请求等字段进行。缺失的身份不推测。

## 结果与边界

- `passed` 表示 JSONL 事件可解析且绑定匹配，错误日志仍计入 `observed_error_count`。
- 校验值不匹配、未知构建、无法解析的行或空日志得到 `not_checked`。未解析文本原样保留。
- 错误字段、未知 schema 或过期行号映射会被拒绝。分析结束后再次核对输入 SHA-256。
- 绑定报告 `syntax`，事件报告 `artifact_syntax`。只编译 Lua 5.3 正文，语法失败仍可分析已有日志。
- `origin` 为空时无法定位原模块行号，例如日志对应装配时生成的包装代码。
- `editor` 和 `host` 均为 `not_checked`。保存、回读及重进分别用[存储诊断](storage-authoring.md)和对应的实际记录确认。

## 实例与修订关联

可选的 `graph_instance` 为项目提供的非空、稳定实例标识，`revision` 为非负整数。二者直接参与分组，无需从 `fields` 提取。不同实例或修订单独分组。缺少任一字段的旧事件仍可关联产物，此时 `instance_revision_correlation` 为 `not_checked`，`correlation_missing` 列出缺失项。将实例身份与原生图对照属于后续核查。
