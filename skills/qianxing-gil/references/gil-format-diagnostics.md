# GIL 二进制结构诊断

## WARNING: 禁止跨 GIL 字段合并

解析 GIL 的 protobuf 字段后，**不要**将一个 GIL 的字段复制到另一个 GIL。UI 控件字段（field 9/11/15 等）包含的模板 ID 和实体引用只在其原始 GIL 上下文中有效，合并后游戏无法加载主界面。此方法已在步步为营多人版项目中验证失败。

正确组装 GIL 的方式：

- 信号定义：由 [GIL 组装流水线](../../../references/workflows/qianxing-gil-assembly-pipeline/README.md) 编排（add_signal_definition_to_gil + bootstrap 模板）
- 节点图写回：同一组装流水线的节点图步骤
- 完整组装：从项目 base GIL 出发，使用项目写回或编辑器导入流程

## GIL 文件格式

### 头部（20 字节）

5 个 uint32 大端序（big-endian）：

| 偏移 | 含义 |
|------|------|
| 0-3  | header[0] = payload_size + 20（文件总大小减去 trailer） |
| 4-7  | header[1] = 版本号（通常为 1） |
| 8-11 | header[2] = 未知字段 |
| 12-15| header[3] = 未知字段（通常为 2） |
| 16-19| header[4] = payload_size |

### Payload（protobuf 编码）

头部之后是标准 protobuf 编码的字段序列。每个字段：

- tag = varint(field_number << 3 | wire_type)
- wire_type 0: varint
- wire_type 2: length-delimited（varint length + bytes）
- wire_type 5: fixed 32-bit
- wire_type 1: fixed 64-bit

### Trailer（可选）

payload 之后可能有尾部数据，保持原样复制即可。

## 诊断脚本

使用 `scripts/diagnose_gil.py` 解析 GIL 结构（从本技能目录执行）：

```bash
python scripts/diagnose_gil.py <path-to-gil>
```

输出示例：

```
File: example.gil (43612 bytes)
Header: [43608, 1, 806, 2, 43588]
  header[0] = payload_size + 20 = 43608
  header[4] = payload_size = 43588
Payload fields: 36
  field 2, wire 2, 27 bytes
  field 3, wire 2, 2 bytes
  field 4, wire 2, 1152 bytes
  ...
```

此脚本为只读诊断，不修改任何文件。优先使用 `gil-toolkit.mjs inspect`；只有在它无法解释结构时才使用本脚本。
