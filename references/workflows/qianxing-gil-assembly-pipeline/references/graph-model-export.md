# GraphModel JSON 导出

Graph Code 必须先导出为 GraphModel JSON，才能写入 GIL 节点图段。导出的 JSON 包含节点、连线、端口类型和自动布局坐标。

## 首选：插件内置 Ayaya

以下命令从插件根目录执行；PLUGIN_PYTHON表示运行配置中的Python绝对路径：

```bash
PLUGIN_PYTHON -X utf8 -B scripts/ayaya_bridge.py --execute \
  --tool export_graph_model_json_from_graph_code tool -- \
  --graph-code <server_graph.py> \
  --output-json <graph_model.json>
```

`ayaya_bridge.py` 会拒绝 `--non-strict`、`--skip-precheck`、`--fix` 等跳过校验的参数。默认路径适合作为交付基线。

## 外部编辑器直连

需要 `--non-strict` 或更细的 CLI 参数时，在 Ayaya_Miliastra_Editor 根目录直接调用。先看帮助：

```bash
PLUGIN_PYTHON -X utf8 -B private_extensions/run_ugc_file_tools.py tool export_graph_model_json_from_graph_code --help
```

`--non-strict` 会跳过校准集之外的引擎 API 检查，只在确认代码有效但被严格模式误拒时使用，并在交付报告中记录。不要用它掩盖真实的类型或连线错误。

## 前置检查

- Graph Code 已通过 `validate-file`
- 信号定义 `.py` 与服务端节点图 `.py` 分目录存放；`sync_graph_code` 会扫描目录，把信号定义当节点图编译会失败或产生错误图
- 节点图 docstring 包含 `graph_id`、`graph_name`、`graph_type`
- 需要写入的信号已在 spec 中定义，且 `signal_name` 与 `signal_id` 一致

## 导出后验证

- JSON 中的节点数与源码中的调用数一致
- 执行线与数据线没有悬空引用
- 变量声明与 `GRAPH_VARIABLES` 一致
- 信号节点的参数顺序与信号定义一致
- 客户端图与服务端图的作用域没有混用

导出成功只证明模型生成成功，不证明 GIL 写回、编辑器导入或运行时行为。完整写回见 [GIL 组装流水线](../README.md)。
