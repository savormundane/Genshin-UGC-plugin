# 旧版 schema 1 制作配置

本页用于阅读、重跑和迁移已有顶层 schema 1 制作配置。退出版本见[维护记录](../../docs/contributing/development.md#旧配置的退出版本)。新任务使用 [schema 2 制作配置](produce.md)。协议、动画、关卡等子配置使用各自的格式。

## 读取与重跑

```text
python scripts/qianxing.py produce production.json --out NEW_DIRECTORY
```

```json
{
  "schema": 1,
  "client": {"source": "client.lua"},
  "protocol": {
    "schema": 1,
    "signals": [{"name": "request_action", "direction": "client_to_server", "fields": [{"name": "choice", "type": "integer"}], "phases": ["ready"]}]
  },
  "animation": {"frames": [{"asset": "frame/asset.json", "duration": 0.1, "anchor": [0, 0]}], "max_controls": 100},
  "graphs": {"spec": "build.json"},
  "gil": {"use_graph_output": true, "mapping": "actual_mapping.lua"}
}
```

至少选择一个阶段。制作任务从 `production.json` 所在目录解析路径，图构建路径相对 `graphs.spec` 所指配置。按工程实际信号名称、字段与 Lua 映射填写。输出须为新目录。用 `--next` 为既有目录选择下一个编号，报告的 `output_directory` 记录实际位置。

| 字段 | 旧版行为和迁移时要保留的映射 |
| --- | --- |
| `client.source` | 保存现有 Lua。迁移可继续引用同一源码。 |
| `level.spec` | 可生成原生结构、模板及脚本映射。写出 `client-bindings.json` 和 `template_indices.lua`，映射的 `templates_as` 别名随 Lua 写回保留。[原生关卡制作](../gil/native-authoring.md) |
| `assets[]` 和 `animation` | 素材项接受 `name`、`source`、可选 `options`。动画帧可用 `@asset:name` 引用本轮生成的清单。按帧验证格式、尺寸和控件预算，同一动画使用一种图元格式。 |
| `protocol` | 输出 `protocol.json` 与 `protocol.lua`，按字段顺序保留信号定义。 |
| `protocol_native: true` | 须同时有 `protocol`。另生成原生信号资源、`wire.json` 和 `client_bridge.lua`；业务字段之前加 `session_key:string`、`round_id:integer` 与 `sequence_id:integer`。 |
| `graphs.spec` | 走同一图编译入口。没有显式 `base_gil` 时使用本轮的活动基底。显式基底须与活动基底一致。启用原生协议且构建图时，将资源并入 `project_resources` 并纳入信号写回。已有的顶层保护字段范围继续生效。 |
| `gil` | 通过 `use_graph_output: true` 选择 `graphs/level.gil`，或由 `base` 指定基底，两种选择互斥。均未指定时用本轮活动基底。必须给出唯一映射名；`gil.source` 省略时使用 `client.source`。迁移时用 schema 2 的 `gil.mapping` 和相应的 `client` 或 `gil.source` 明确来源。 |

Lua 按已有映射写回并保护其他脚本与字段。节点图、资源和实体挂载由原生或图构建阶段完成。图构建报告位于 `graphs/build-report.json`，挂载检查需要相应配置中的 `required_mounts`。

## 已有 Lua 模块

旧任务输出 `runtime.lua`，包含作用域清理 `scope`、差量更新 `dirty`、协议验证 `protocol` 和动画辅助 `player`、`rectangles`。项目在真实生命周期中调用，绘制、控件回收和传输来源由项目接入。

旧项目应保留已发布协议。标量协议支持有符号 32 位整数、浮点数、布尔和带可选 UTF-8 字节上限的字符串，信号可声明 `client_to_server`、`server_to_client` 或 `server_local`。 `runtime.protocol` 检查方向、阶段、会话、回合、载荷和序号，通过可信来源与信号拒绝重复或过期消息。允许乱序的消息和复杂数据类型要按实际合同维持各自策略。 [复杂类型和原生接入](protocol-v2.md)

## 报告与验证

旧版交付使用 `production-report.json`，其中的 `files_sha256` 与 `evidence` 可用 `workflow check PLAN.json --report OUTPUT/production-report.json` 核对。拥有 Lua 5.3 编译依赖时，旧流程对生成目录的独立 Lua 文件做语法检查（排除图构建目录），依赖缺失时该项为 `not_checked`。迁移后用 schema 2 的最终 Lua 检查与 `verify`。 [分层验证与交付记录](validation.md)
