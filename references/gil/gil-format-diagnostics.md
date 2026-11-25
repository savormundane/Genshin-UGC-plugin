# GIL 二进制结构诊断

## 跨 GIL 关联

UI 控件字段（在已观察的样本中包括字段 9、11、15）可能引用原 GIL 的模板和实体。复制字段会保留这些原引用。需要组合图、信号和 Lua 时，从当前项目基底开始，按[GIL 写回流程](native-authoring.md#将图信号和-lua-写入同一份-gil)处理关联并回读。

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

从插件根目录运行只读结构诊断：

```bash
python skills/miliastra-gil/scripts/diagnose_gil.py <path-to-gil>
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
