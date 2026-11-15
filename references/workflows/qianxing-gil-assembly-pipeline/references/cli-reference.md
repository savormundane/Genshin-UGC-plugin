# CLI Reference

## Command

```bash
PLUGIN_PYTHON -X utf8 -B private_extensions/run_ugc_file_tools.py tool --dangerous add_signal_definition_to_gil [OPTIONS]
```

在 Ayaya_Miliastra_Editor 根目录执行。插件内置 CLI 未把该子命令列入 `tool` 白名单，因此低层写回需要外部编辑器检出。

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--input-gil` | Yes | Base .gil file (use `empty_base_with_infra.gil` for new signals) |
| `--output-gil` | Yes | Output filename (forced to `ugc_file_tools/out/` directory) |
| `--spec-json` | Yes | Path to signal specification JSON file |
| `--template-gil` | No | Template .gil with signal node_def samples; auto-selected if omitted |
| `--bootstrap-template-gil` | No | Bootstrap template for empty base GILs (use `signal_node_def_templates.gil`) |
| `--param-build-mode` | No | `semantic` (default) or `template`. Semantic constructs ports from type_id rules |
| `--emit-reserved-placeholder-signal` | No | `--emit-reserved-placeholder-signal` / `--no-emit-reserved-placeholder-signal`. Controls whether to write a placeholder no-param signal entry when base has no signals. Default: true |

## Template File Paths

Relative to Ayaya editor root:

```
private_extensions/ugc_file_tools/builtin_resources/empty_base_samples/empty_base_with_infra.gil
private_extensions/ugc_file_tools/builtin_resources/seeds/signal_node_def_templates.gil
```

插件 vendor 内也有同名副本，但内置 CLI 不提供本写回子命令；不要把副本路径当作外部 CLI 的默认值。

## Output Rules

- Output is **always** written to `private_extensions/ugc_file_tools/out/` directory
- The `--output-gil` value is treated as a filename within that directory
- This prevents accidental overwriting of important samples or user files

## Complete Example

```bash
cd "<Ayaya_Miliastra_Editor>"

PLUGIN_PYTHON -X utf8 -B private_extensions/run_ugc_file_tools.py tool --dangerous add_signal_definition_to_gil \
  --input-gil "private_extensions/ugc_file_tools/builtin_resources/empty_base_samples/empty_base_with_infra.gil" \
  --output-gil my_signals.gil \
  --spec-json "<path>/signal_spec.json" \
  --bootstrap-template-gil "private_extensions/ugc_file_tools/builtin_resources/seeds/signal_node_def_templates.gil" \
  --param-build-mode semantic
```

## What Each Signal Generates

Each signal in spec.json produces **3 node definitions**:

1. **发送信号** (Send Signal) — client-side send
2. **监听信号** (Listen Signal) — client-side receive
3. **向服务器节点图发送信号** (Send to Server Node Graph) — client-to-server

Plus one **signal entry** in the GIL's signal table.

## Allocation Strategy

- `signal_index`: placeholder signal fixed at `2`; business signals from `8` ascending
- `node_def_id`: allocated based on base GIL's existing patterns, with `0x6000xxxx` default for empty bases
- Port indices: block allocation with width `16 + 3*param_count`

## Template Auto-Selection

When `--template-gil` is omitted, the tool searches in order:

1. Base GIL's own payload (extract no-param signal node_defs)
2. Bootstrap template GIL's payload
3. Local cache (`_signal_node_def_templates.cache.json`)
4. Built-in default templates

## Related

- [信号写回](signal-writeback.md) — base/bootstrap 选择与错误处理
- [spec.json 格式](spec-json-format.md) — type_id 映射与约束
- [GIL 组装流水线](../README.md) — 信号先于节点图的完整顺序
