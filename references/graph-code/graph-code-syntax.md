# Graph Code 语法参考

## 数据类型

| 类型名 | 说明 | 示例 |
|--------|------|------|
| `整数` | 整数值 | `0`, `100`, `-1` |
| `浮点数` | 浮点值 | `0.0`, `3.14` |
| `布尔值` | 真/假 | `True`, `False` |
| `字符串` | 文本 | `"hello"`, `"信号名"` |
| `实体` | 游戏实体引用 | 通过获取实体类节点获得 |
| `GUID` | 全局唯一标识符 | 通过 GUID 类节点获得 |
| `三维向量` | 3D 坐标/方向 | `(0.0, 1.0, 2.0)` 元组语法糖 |
| `阵营` | 阵营标识 | 通过阵营类节点获得 |
| `元件ID` | 元件配置 ID | 整数形式 |
| `配置ID` | 通用配置 ID | 整数形式 |
| `整数列表` | 整数数组 | `[1, 2, 3]` |
| `布尔值列表` | 布尔数组 | `[True, False]` |
| `浮点数列表` | 浮点数组 | `[1.0, 2.0]` |
| `字符串列表` | 字符串数组 | `["a", "b"]` |
| `实体列表` | 实体数组 | 通过获取实体列表类节点获得 |
| `结构体` | 复合数据类型 | 需先定义结构体 |
| `字典` | 键值对 | 需指定键值类型 |
| `整数-整数字典` | 特定类型字典 | 键为整数，值为整数 |
| `整数-整数列表字典` | 特定类型字典 | 键为整数，值为整数列表 |

## 节点图元数据（docstring 必填字段）

```python
"""
graph_id: server_项目名_唯一标识       # 全局唯一，建议用英文下划线命名
graph_name: 中文显示名                  # 编辑器中显示的名称
graph_type: server                      # server 或 client
description: 功能描述                    # 可选，说明此图的作用
"""
```

## 复合节点元数据

```python
"""
composite_id: composite_功能名          # 全局唯一
node_name: 中文显示名                    # 节点面板中显示的名称
node_description: 功能说明               # 节点描述
scope: server                           # server 或 client
"""
```

## 节点调用语法

调用节点时，第一个参数传入 `self.game`。

```python
# 算术运算
结果: "整数" = 加法运算(self.game, 左值=1, 右值=1)
差值: "浮点数" = 减法运算(self.game, 左值=10.0, 右值=3.5)

# 变量操作
值: "整数" = 获取自定义变量(self.game, 目标实体=self.owner_entity, 变量名="变量名")
设置自定义变量(self.game, 目标实体=self.owner_entity, 变量名="变量名", 变量值=新值, 是否触发事件=False)

# 节点图变量
值: "整数" = 获取节点图变量(self.game, 变量名="变量名")
设置节点图变量(self.game, 变量名="变量名", 变量值=新值, 是否触发事件=False)

# 信号
发送信号(self.game, 信号名="信号名")

# 服务端实体位置与旋转查询
位置, 旋转 = 获取实体位置与旋转(self.game, 目标实体=self.owner_entity)
```

## 语法糖映射

编译器按图的作用域和已识别的参数类型改写支持的表达式。直接调用改写所得节点时，用 `nodes_lookup` 核对该端的端口。

| 表达式 | 包内编译器行为 |
| --- | --- |
| `a + b`、`a - b`、`a * b`、`a / b` | 加法、减法、乘法和除法节点。四种节点的入参均为 `左值` 和 `右值`。 |
| `a == b`、`a > b` | 使用相等或数值比较节点。`a > b` 在服务端为 `数值大于`，在客户端为 `是否大于`。 |
| `a and b`、`a or b`、`not a` | 逻辑与、或、非节点，端口名称随作用域变化。 |
| `列表[序号]`、`len(列表)` | `获取列表对应值` 与 `获取列表长度`，端口名称随作用域变化。 |
| 列表切片、`sum`、`any`、`all`、三元表达式 | 部分可推导类型的写法依赖已登记的共享复合节点。用 `graph check` 核对当前图能否改写。 |
| `(0.0, 1.0, 2.0)` | 用在已知三维向量端口，按向量常量解析。 |

## 控制流

```python
# 分支（→ 分支节点）
if 条件:
    ...
else:
    ...

# 列表遍历（→ 列表遍历节点）
for 元素 in 列表:
    ...

# 范围循环（→ 循环节点）
for i in range(10):
    ...

# 多分支（→ 多分支/switch 节点）
match 值:
    case 0:
        ...
    case 1:
        ...
    case _:  # 默认分支
        ...

# 退出循环（→ 退出循环节点）
break
```

`if` 的条件不能直接使用 `!=`，因为改写后的逻辑非运算会触发 `CODE_IF_DIRECT_LOGIC_NOT_CALL`。用 `==` 比较，并将不相等时的处理写进 `else`。详见 [Graph Code 常见验证错误修复](validation-fixes.md)。

包内编译后端把 `range` 的两个边界直接写入原生有限循环，两端均包含。遍历长度为 `n` 的列表时，先用节点计算 `last=n-1`，再写 `range(0,last)`。上下界必须是简单变量或常量。检查最终原生循环的端口，并用空列表和列表末项验证遍历范围。

## 事件系统

### 常用事件

以下为包内服务端节点定义的部分端口。编写回调前用 `nodes_lookup` 查询完整签名；信号的附加端口以工程声明为准。

| 事件节点 | 数据输出 |
| --- | --- |
| `实体创建时` | `事件源实体`、`事件源GUID` |
| `实体销毁时` | `事件源实体`、`事件源GUID`、`位置`、`朝向`等 |
| `自定义变量变化时` | `事件源实体`、`事件源GUID`、`变量名`、`变化前值`、`变化后值`，容器类型无前后值 |
| `监听信号` | `事件源实体`、`事件源GUID`、`信号来源实体`，随后是所选信号定义的字段 |

显式声明 `事件源GUID` 时，其类型为 `"GUID"`。

### 注册事件

```python
def register_handlers(self):
    # 基础注册
    self.game.register_event_handler("实体创建时", self.on_实体创建时, owner=self.owner_entity)
    
    # 用项目中已声明的信号 ID 选择监听目标
    self.game.register_event_handler("signal_example_move", self.on_signal_example_move, owner=self.owner_entity)
```

## 复合节点引脚声明

```python
@flow_entry()
def 方法名(self, 参数1: "整数"):
    # 流程引脚
    流程入("流程入")                       # 入口
    流程出("完成")                         # 出口
    
    # 数据引脚
    数据入("参数1", pin_type="整数")       # 输入引脚
    数据出("结果", pin_type="整数", variable="结果")  # 输出引脚
    
    # 实现逻辑
    ...
    return 结果
```

## GRAPH_VARIABLES 配置

```python
GRAPH_VARIABLES: list[GraphVariableConfig] = [
    GraphVariableConfig(
        name="变量名",              # 变量标识
        variable_type="整数",       # 数据类型
        default_value=0,            # 默认值
        description="变量说明",      # 描述
        is_exposed=False,           # 是否暴露为外部参数
    ),
]
```

## 常见验证错误

| 错误类型 | 说明 | 修复方式 |
|----------|------|----------|
| 类型不匹配 | 端口连接的数据类型不一致 | 检查变量类型标注，确保与节点端口类型匹配 |
| 端口未连接 | 必填输入端口没有连线 | 为所有必填端口提供值或连接 |
| 未知节点 | 使用了不存在的节点名 | 检查节点名拼写，确认在 prelude 中已导入 |
| 事件参数不匹配 | 事件处理函数参数与事件定义不一致 | 按事件定义调整参数列表 |
| graph_id 重复 | 多个文件使用相同的 graph_id | 确保每个节点图的 ID 全局唯一 |
| 类型标注缺失 | 变量没有类型标注 | 添加 `: "类型名"` 标注 |
| 信号参数不匹配 | 发送信号的参数与信号定义不一致 | 按信号定义调整参数 |
| 复合节点引脚缺失 | 复合节点缺少必要的引脚声明 | 添加 `数据入`/`数据出`/`流程入`/`流程出` |

## 信号定义文件

```python
SIGNAL_ID = "signal_example_move"
SIGNAL_PAYLOAD = {
    "signal_name": "移动请求",
    "parameters": [
        {"name": "参数甲", "parameter_type": "整数"},
    ],
}
```

## 结构体定义文件

```python
STRUCT_ID = "200001"
STRUCT_PAYLOAD = {
    "type": "Struct",
    "struct_name": "结构体示例",
    "struct_ype": "basic",
    "fields": [
        {"field_name": "计数", "param_type": "整数", "default_value": {"value": 0}},
    ],
}
```

此示例采用已通过基础结构体写回测试的声明格式。`struct_ype` 是该格式中的字段名。实际 ID 必须来自工程并确认为可用。信号、基础结构体及局内存档结构体的导出或写回从顶层声明读取数据。 [构建与项目资源](node-graph-workflow.md#构建描述-schema-1)

## 完整文件示例

### 节点图文件结构

```python
"""
graph_id: server_example_counter
graph_name: 计数示例
graph_type: server
description: 初始化节点图变量
"""

from app.runtime.engine.graph_prelude_server import *

GRAPH_VARIABLES: list[GraphVariableConfig] = [
    GraphVariableConfig(name="计数", variable_type="整数", default_value=0),
]

class Counter:
    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

    def on_实体创建时(self, 事件源实体: "实体", 事件源GUID: "GUID"):
        结果: "整数" = 加法运算(self.game, 左值=1, 右值=1)
        设置节点图变量(self.game, 变量名="计数", 变量值=结果, 是否触发事件=False)

    def register_handlers(self):
        self.game.register_event_handler("实体创建时", self.on_实体创建时, owner=self.owner_entity)
```

### 复合节点文件结构

```python
"""
composite_id: composite_功能名
node_name: 显示名称
node_description: 功能说明
scope: server
"""

from app.runtime.engine.graph_prelude_server import *
from engine.nodes.composite_spec import composite_class, flow_entry

@composite_class
class 功能名:
    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

    @flow_entry()
    def 方法名(self, 参数1: "整数", 参数2: "整数"):
        数据入("参数1", pin_type="整数")
        数据入("参数2", pin_type="整数")
        数据出("结果", pin_type="整数", variable="结果")
        结果: "整数" = 加法运算(self.game, 左值=参数1, 右值=参数2)
        return 结果
```

## Ayaya 项目资源目录

| 类型 | 路径 |
|------|------|
| 共享节点图 | `assets/资源库/共享/节点图/<server\|client>/` |
| 共享复合节点 | `assets/资源库/共享/复合节点库/` |
| 项目节点图 | `assets/资源库/项目存档/<项目名>/节点图/<server\|client>/` |
| 项目复合节点 | `assets/资源库/项目存档/<项目名>/复合节点库/` |
| 信号定义 | `assets/资源库/项目存档/<项目名>/管理配置/信号/` |
| 结构体定义 | `assets/资源库/共享/管理配置/结构体定义/` |

校验、编译和回读见 [节点图制作流程](node-graph-workflow.md)。
