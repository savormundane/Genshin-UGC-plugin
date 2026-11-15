# spec.json Format

## Schema

```json
{
  "signals": [
    {
      "signal_name": "string (required)",
      "params": [
        {
          "param_name": "string (required)",
          "type_id": "int or string (required)",
          "struct_id": "int (required when type_id=25 or 26)"
        }
      ]
    }
  ]
}
```

**Aliases**: `"name"` can be used instead of `"signal_name"` or `"param_name"`; `"type"` can be used instead of `"type_id"`.

此表描述外部低层原生写回格式，不能推导客户端ServerSignal可直接发送结构体。客户端桥只使用[协议合同](../../../protocol-v2.md)明确支持的类型。

## type_id Mapping

| type_id | Chinese Name | Description |
|---------|--------------|-------------|
| 1 | 实体 | Entity |
| 2 | GUID | GUID |
| 3 | 整数 | Integer |
| 4 | 布尔值 | Boolean |
| 5 | 浮点数 | Float |
| 6 | 字符串 | String |
| 7 | GUID列表 | GUID list |
| 8 | 整数列表 | Integer list |
| 9 | 布尔值列表 | Boolean list |
| 10 | 浮点数列表 | Float list |
| 11 | 字符串列表 | String list |
| 12 | 三维向量 | Vector3 |
| 13 | 实体列表 | Entity list |
| 15 | 三维向量列表 | Vector3 list |
| 17 | 阵营 | Camp/Faction |
| 20 | 配置ID | Config ID |
| 21 | 元件ID | Component ID |
| 22 | 配置ID列表 | Config ID list |
| 23 | 元件ID列表 | Component ID list |
| 24 | 阵营列表 | Camp list |
| 25 | 结构体 | Struct (requires `struct_id`) |
| 26 | 结构体列表 | Struct list (requires `struct_id`) |
| 27 | 字典 | **FORBIDDEN** for signal params |

**type_id resolution**: accepts raw integer (`3`), digit string (`"3"`), or Chinese type name (`"整数"`).

## Constraints

1. **Dict (type_id=27) is forbidden** for signal parameters
2. **Struct params (type_id 25/26) require `struct_id`** — omitting it raises `ValueError`
3. Signals are sorted by `signal_name` before processing for deterministic allocation
4. Signals already existing in the base GIL (matched by name) are skipped

## Examples

### No parameters

```json
{
  "signals": [
    {
      "signal_name": "signal_game_start",
      "params": []
    }
  ]
}
```

### Integer parameters

```json
{
  "signals": [
    {
      "signal_name": "signal_move",
      "params": [
        {"param_name": "target_row", "type_id": 3},
        {"param_name": "target_col", "type_id": 3}
      ]
    }
  ]
}
```

### Mixed types

```json
{
  "signals": [
    {
      "signal_name": "signal_player_action",
      "params": [
        {"param_name": "player_id", "type_id": 3},
        {"param_name": "action_name", "type_id": 6},
        {"param_name": "is_critical", "type_id": 4},
        {"param_name": "position", "type_id": 12}
      ]
    }
  ]
}
```

### Multiple signals

```json
{
  "signals": [
    {
      "signal_name": "signal_move",
      "params": [
        {"param_name": "row", "type_id": 3},
        {"param_name": "col", "type_id": 3}
      ]
    },
    {
      "signal_name": "signal_wall",
      "params": [
        {"param_name": "row", "type_id": 3},
        {"param_name": "col", "type_id": 3},
        {"param_name": "direction", "type_id": 3}
      ]
    },
    {
      "signal_name": "signal_game_over",
      "params": [
        {"param_name": "winner", "type_id": 3}
      ]
    }
  ]
}
```
