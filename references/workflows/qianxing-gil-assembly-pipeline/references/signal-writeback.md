# 信号写回 GIL

用 `add_signal_definition_to_gil` 把信号定义（含类型参数）写入 `.gil`。每个信号生成 3 个节点定义：发送 / 监听 / 向服务器节点图发送，并在信号表中新增一条 entry。

## 前置条件

- 该低层写回子命令需要一份 Ayaya_Miliastra_Editor 检出；插件内置 CLI 未暴露 `add_signal_definition_to_gil`
- Python 3.11–3.12，命令在编辑器根目录执行
- 输出会被强制写入编辑器的 `private_extensions/ugc_file_tools/out/`，`--output-gil` 只给文件名

## spec.json

```json
{
  "signals": [
    {
      "signal_name": "signal_example",
      "params": [
        {"param_name": "player_id", "type_id": 3},
        {"param_name": "score", "type_id": 3}
      ]
    }
  ]
}
```

完整 type_id 映射、结构体参数和约束见 [spec.json 格式](spec-json-format.md)。要点：

- `signal_name` 必须与 Graph Code 中的 `signal_id` 一致；写回引擎用 `signal_name` 查找 node_def。
- 参数数组用 `params`，每项用 `param_name` 与 `type_id`；`name` / `type` 是别名。
- 字典类型（type_id=27）禁止用于信号参数；结构体参数必须提供 `struct_id`。
- 已存在于 base GIL 的同名信号会被跳过。

这里的 spec.json 是 CLI 格式；Graph Code 的 `SIGNAL_PAYLOAD` 使用 `signal_id` + `parameters` + `parameter_type`，两者用途不同，不要混用字段名。

## 选择 base 与 bootstrap

| 场景 | `--input-gil` | `--bootstrap-template-gil` |
|------|---------------|----------------------------|
| 新信号集 / 空壳 base | `empty_base_with_infra.gil` | `signal_node_def_templates.gil` |
| 已有项目 GIL 补信号 | 项目 GIL | 通常省略；报 node_def 不匹配时改用上一行 |

不要把项目 GIL 当作 bootstrap 模板。它会报：

```
ValueError: node def name mismatch: expected '向服务器节点图发送信号', got '发送客户端脚本信号'
```

## 命令

```bash
cd "<Ayaya_Miliastra_Editor>"
PLUGIN_PYTHON -X utf8 -B private_extensions/run_ugc_file_tools.py tool --dangerous add_signal_definition_to_gil \
  --input-gil "private_extensions/ugc_file_tools/builtin_resources/empty_base_samples/empty_base_with_infra.gil" \
  --output-gil with_signals.gil \
  --spec-json "<信号 spec.json>" \
  --bootstrap-template-gil "private_extensions/ugc_file_tools/builtin_resources/seeds/signal_node_def_templates.gil" \
  --param-build-mode semantic
```

关键参数：

- `--dangerous` 必须放在 `tool` 之后、子命令之前。
- `--param-build-mode semantic`（默认）按 type_id 规则构造参数口，不需要模板覆盖每个参数类型；`template` 则要求模板覆盖所有类型。
- `--template-gil` 可选，用于指定带信号 node_def 样本的模板；省略时按 base → bootstrap → 缓存 → 内置默认顺序查找。
- `--bootstrap-template-gil` 在 input 是空壳或缺少顶层 payload 段时提供基底。

完整参数与分配策略见 [CLI Reference](cli-reference.md)。

## 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| `node def name mismatch` | base 缺少正确的信号基础设施 node_def | 用 `empty_base_with_infra.gil` + `signal_node_def_templates.gil` |
| `该工具标记为【危险写盘】...必须显式添加 --dangerous` | 标志位置错误或缺失 | `tool --dangerous add_signal_definition_to_gil ...` |
| `Dict type forbidden` / type_id=27 | 信号参数用了字典 | 改用结构体（25/26）或标量/列表类型 |
| 参数数量为 0 | spec 的 `params` 为空或字段名错误 | 确认使用 `params` + `param_name`/`type_id` |

## 写回后

写回结果只包含信号与 node_def，不含客户端 Lua。后续：

1. 以该 GIL 为 `--template-gil` 执行节点图写回；
2. 用 `gil-toolkit.mjs replace-lua` 或项目写回嵌入 Lua；
3. 用 `inspect_gil_signals` 核对 signal entry 与节点图参数 pin 数量。

完整顺序见 [GIL 组装流水线](../README.md)。
