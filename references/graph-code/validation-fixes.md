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

## 3. `on_` 方法名必须精确匹配 `signal_id`

`register_event_handler` 注册的回调方法名用 `"on_" + signal_id` 构成。方法名中的标识必须是信号 ID。

```python
# 错误 — 用了中文名
self.game.register_event_handler("signal_example_move", self.on_提交请求)
def on_提交请求(self, ...):

# 正确 — 用 signal_id
self.game.register_event_handler("signal_example_move", self.on_signal_example_move)
def on_signal_example_move(self, ...):
```

## 4. 信号处理函数必须包含 3 个自动注入的实体参数

引擎调用信号处理函数时，为前三个参数传入 `事件源实体`、`事件源GUID` 和 `信号来源实体`。函数签名必须声明这三个参数并标注类型，否则校验会报错。

```python
# 错误 — 只有信号自身定义的参数
def on_signal_example_move(self, 席位号: "整数", 参数甲: "整数", 参数乙: "整数"):

# 正确 — 前 3 个为引擎注入参数，带类型标注
def on_signal_example_move(self, 事件源实体: "实体", 事件源GUID: "整数", 信号来源实体: "实体",
                            参数甲: "整数", 参数乙: "整数"):
```

实体事件（如 `实体创建时`）同理，参数也需标注类型：

```python
# 错误
def on_实体创建时(self, 事件源实体, 事件源GUID):

# 正确
def on_实体创建时(self, 事件源实体: "实体", 事件源GUID: "整数"):
```

## 5. `发送信号` 关键字参数名必须匹配信号定义

`发送信号` 的关键字参数名必须与信号定义中的 `name` 字段完全一致，包括大小写和中英文。

```python
# 信号定义
SIGNAL_PAYLOAD = {
    "signal_id": "signal_example_state",
    "parameters": [
        {"name": "当前修订", "parameter_type": "整数"},
        {"name": "状态值", "parameter_type": "整数"},
        ...
    ]
}

# 错误 — 参数名不匹配
发送信号(self.game, 信号名="signal_example_state", 修订=1, 值=8)

# 正确 — 参数名与定义一致
发送信号(self.game, 信号名="signal_example_state", 当前修订=1, 状态值=8, ...)
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

## 7. `register_event_handler` 第一个参数必须是 `signal_id`

事件名使用信号的 `signal_id`（如 `"signal_example_move"`），不是 `signal_name`（如 `"中性示例_提交请求"`）。

```python
# 错误 — 用了 signal_name
self.game.register_event_handler("中性示例_提交请求", self.on_signal_example_move)

# 正确 — 用 signal_id
self.game.register_event_handler("signal_example_move", self.on_signal_example_move)
```

## 8. 风格建议：复合条件拆为 early return

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
