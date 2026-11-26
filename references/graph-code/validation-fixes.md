# Graph Code 常见验证错误修复

本页用示例说明 Ayaya CLI 校验 Graph Code 时的常见错误及修复方法。完整语法见 [Graph Code 语法参考](graph-code-syntax.md)。

## 1. `!=` 不能出现在 if 条件中

编译器会把 `!=` 改写成对相等比较结果的取反。写在 `if` 条件里会触发 `CODE_IF_DIRECT_LOGIC_NOT_CALL`。用 `==` 比较，并将原来的不相等分支放进 `else`。

```python
# 错误
if 当前修订 != 1:
    ...

# 正确 — 用 == 保留相同的分支行为
if 当前修订 == 1:
    pass
else:
    ...
```

## 2. `设置节点图变量` 必须带 `是否触发事件` 参数

`是否触发事件` 是必填关键字参数，省略会导致验证失败。一般设为 `False` 避免级联触发。

```python
# 错误
设置节点图变量(self.game, 变量名="当前修订", 变量值=2)

# 正确
设置节点图变量(self.game, 变量名="当前修订", 变量值=2, 是否触发事件=False)
```

## 3. 信号回调使用已登记的 ID 或完整显示名

假设当前工程定义的 `signal_id` 是 `signal_example_move`，`signal_name` 是 `移动请求`。`on_signal_example_move` 与 `on_移动请求` 均可编译，`on_收到移动请求` 会因未登记被拒绝。示例采用稳定 ID；使用显示名时应填写完整名称，并保证它在当前资源范围内可明确解析。`register_handlers` 中直接传信号字符串及 `self.on_…`，让导出器静态识别绑定。

```python
def register_handlers(self):
    self.game.register_event_handler("signal_example_move", self.on_signal_example_move,
                                     owner=self.owner_entity)
```

## 4. 信号处理函数的前三项来自固定端口

包内服务端「监听信号」登记的前三个参数是 `事件源实体`、`事件源GUID` 和 `信号来源实体`。声明顺序按固定端口，随后声明信号自身的字段。固定端口显式标注时应与节点定义一致。

```python
# 错误，缺少三个固定端口
def on_signal_example_move(self, 参数甲: "整数"):
    pass

# 正确，固定端口在前，信号字段在后
def on_signal_example_move(self, 事件源实体: "实体", 事件源GUID: "GUID", 信号来源实体: "实体",
                           参数甲: "整数"):
    打印字符串(self.game, 字符串="收到移动请求")
```

「实体创建时」只含 `事件源实体` 和 `事件源GUID` 两个数据输出，可按已知端口名称推导类型，也可显式标注。其他事件用 `nodes_lookup` 查询各自签名。

```python
def on_实体创建时(self, 事件源实体: "实体", 事件源GUID: "GUID"):
    pass
```

## 5. `发送信号` 关键字参数名必须匹配信号定义

`发送信号` 的关键字参数名必须与信号定义中的 `name` 字段完全一致，包括大小写和中英文。

```python
# 信号定义
SIGNAL_ID = "signal_example_state"
SIGNAL_PAYLOAD = {
    "signal_name": "状态通知",
    "parameters": [
        {"name": "当前修订", "parameter_type": "整数"},
        {"name": "状态值", "parameter_type": "整数"},
    ],
}

# 在图回调中调用时，参数名须与上面的声明一致
发送信号(self.game, 信号名="状态通知", 当前修订=1, 状态值=8)
```

## 6. 不能将比较结果赋值给类型变量

在这类比较和逻辑判断中，直接将 `==`、`and` 或 `or` 表达式写入 `if` 条件。将结果赋给带类型标注的变量会导致校验失败。

```python
# 错误
红1获胜: "布尔值" = 参数甲 == 0 and 当前 == 1
if 红1获胜:
    ...

# 正确 — 直接在 if 中判断
if 参数甲 == 0 and 当前 == 1:
    ...
```

## 7. 风格建议：复合条件拆为 early return

`if not X and Y:` 这类复合布尔条件通过校验后仍可能难以阅读。可先逐项检查前置条件，在不满足时提前返回。

```python
# 不推荐
if not 对局已结束 and 来源序号 == 当前修订:
    ...

# 推荐
if 对局已结束:
    return
if 来源序号 == 当前修订:
    pass
else:
    return
# 主逻辑
...
```
