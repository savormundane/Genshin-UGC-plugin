# GIL 二进制结构诊断

## 跨 GIL 关联

UI 控件字段（在已观察的样本中包括字段 9、11、15）可能引用原 GIL 的模板和实体。复制字段会保留这些原引用。需要组合图、信号和 Lua 时，从当前项目基底开始，按[GIL 写回流程](native-authoring.md#将图信号和-lua-写入同一份-gil)处理关联并回读。

## GIL 文件格式

### 头部（20 字节）

头部由 5 个按大端序（big-endian）编码的 `uint32` 字段组成。

| 偏移 | 含义 |
|------|------|
| 0-3  | header[0] = payload_size + 20（文件总大小减去 trailer） |
| 4-7  | header[1]，已校准 GIL 为 1 |
| 8-11 | header[2]，已校准 GIL 为 806 |
| 12-15| header[3]，已校准 GIL 为 2 |
| 16-19| header[4] = payload_size |

当前写入校准以头部中间三个值 `(1, 806, 2)` 识别 GIL。显式支持静态 GIA 的入口可接受 `(1, 806, 3)`。这些值来自已验证的容器样本，其官方命名和更广的版本语义尚待确认。

### Payload（protobuf 编码）

头部之后是标准 protobuf 编码的字段序列。每个字段：

- tag = varint(field_number << 3 | wire_type)
- wire_type 0: varint
- wire_type 2: length-delimited（varint length + bytes）
- wire_type 5: fixed 32-bit
- wire_type 1: fixed 64-bit

### 尾部（4 字节）

主解析器要求 payload 之后恰好有 `00 00 06 79` 四个字节，同时核对文件长度与两个头部长字段。头部、长度、尾部和 protobuf 的基本检查通过后，仍需按入口确认写入所需的容器和字段布局。

## 诊断脚本

从插件根目录运行只读结构诊断：

```bash
python skills/miliastra-gil/scripts/diagnose_gil.py samples/creator-demos/gil/entrance.gil
```

输出示例：

```
File: samples/creator-demos/gil/entrance.gil (7959 bytes)
Scope: bounded raw field inspection; native semantics and host compatibility not checked
Header: [7955, 1, 806, 2, 7935]
  header[0] = payload_size + 20 = 7955
  header[4] = payload_size = 7935
Payload fields: 41
  field 2, wire 2, 8 bytes
  field 3, wire 2, 0 bytes
  field 4, wire 2, 59 bytes
  ...
Trailer: 4 bytes
```

查看已知关卡对象优先用 `python scripts/qianxing.py inspect INPUT.gil` 或 MCP `project_inspect`。若需要原始字段列表，可使用 [`gil-toolkit.mjs inspect`](gil-tooling.md)。本页诊断脚本供主解析器无法识别文件时调查字段长度和边界，可以列出剩余尾部字节数。它不核对主解析器要求的尾部标记，也不判定能否写入或导入。
