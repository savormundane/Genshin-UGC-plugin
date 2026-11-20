
# Python Graph Code 编写与验证

先读 [Graph Code 语法参考](../../../references/graph-code-syntax.md)。Graph Code 是用 Python 类结构描述节点图的 DSL，由 Ayaya 引擎解析为节点图并导出为 `.gil`/`.gia`。

本流程覆盖两种文件类型：**节点图**（server/client）和**复合节点**。信号定义和结构体定义也属于 Graph Code 体系，但语法更简单（字典声明式）。

## 前置条件

插件内置 Ayaya 工具链（vendor/ayaya），通过 scripts/ayaya_bridge.py 调用（在技能目录内则用 scripts/ayaya_bridge.py），无需外部安装。以下命令从插件根目录执行；PLUGIN_PYTHON表示运行配置中的Python绝对路径：

```bash
# 验证单个 Graph Code 文件
PLUGIN_PYTHON -X utf8 -B scripts/ayaya_bridge.py --execute --input <file_path> validate-file

# 规划模式（不执行，先看命令）
PLUGIN_PYTHON -X utf8 -B scripts/ayaya_bridge.py --input <file_path> validate-file
```

完整运行环境需要 Python 3.11–3.12。验证只做静态检查，不执行节点业务逻辑。若 bridge 报依赖缺失，先运行 doctor 核对入口。

## 核心语法

### 节点图文件结构

```python
"""
graph_id: server_项目名_功能描述
graph_name: 显示名称
graph_type: server
description: 功能说明
"""

from app.runtime.engine.graph_prelude_server import *

GRAPH_VARIABLES: list[GraphVariableConfig] = [
    GraphVariableConfig(name="变量名", variable_type="整数", default_value=0),
]

class 节点图类名:
    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

    def on_实体创建时(self, 事件源实体, 事件源GUID):
        结果: "整数" = 加法运算(self.game, 左值=1, 右值=1)
        设置自定义变量(self.game, 目标实体=self.owner_entity,
            变量名="变量名", 变量值=结果)

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

### 关键规则

- **类型标注**：用中文字符串标注，如 `"整数"` `"布尔值"` `"字符串"` `"实体"` `"三维向量"` `"整数列表"`
- **节点调用**：函数式，第一个参数始终是 `self.game`
- **事件处理**：方法名 `on_<事件名>`，在 `register_handlers()` 中注册
- **语法糖**：`1 + 1` 自动映射为 `加法运算`，`列表[1:4]` 映射为切片复合节点，`sum()` `any()` `all()` 映射为对应复合节点
- **控制流**：`if/else` → 分支节点，`for` → 循环节点，`match/case` → 多分支节点

## 验证命令

通过 scripts/ayaya_bridge.py 调用内置 Ayaya：

| 命令 | 用途 |
|------|------|
| `--execute --input <file> validate-file` | 验证单个文件 |
| `--execute --package-id <名> validate-project` | 验证项目存档（挂载、引用、GUID） |
| `--execute --package-id <名> validate-ui` | 验证 UI 配置 |
| `--tool export_graph_model_json_from_graph_code tool -- ...` | 导出图模型 JSON |
| `--tool export_project_graphs_to_gia tool -- ...` | 批量导出 GIA |

退出码：`0` = 通过，`1` = 存在错误。警告默认不失败。计划模式（不带 `--execute`）只输出将要执行的命令。

执行验证后，将错误信息逐条分析并给出修复建议。常见错误类型见 [语法参考](../../../references/graph-code-syntax.md#常见验证错误)，高频报错的错误写法与正确写法见 [常见验证错误修复](../references/validation-fixes.md)。完整桥接用法见 [离线工具链](../../../references/ayaya-offline-toolchain.md)。

## 文件放置

| 类型 | 路径 |
|------|------|
| 共享节点图 | `assets/资源库/共享/节点图/<server\|client>/` |
| 共享复合节点 | `assets/资源库/共享/复合节点库/` |
| 项目节点图 | `assets/资源库/项目存档/<项目名>/节点图/<server\|client>/` |
| 项目复合节点 | `assets/资源库/项目存档/<项目名>/复合节点库/` |
| 信号定义 | `assets/资源库/项目存档/<项目名>/管理配置/信号/` |
| 结构体定义 | `assets/资源库/共享/管理配置/结构体定义/` |

## 与其他技能的边界

- **本流程**：Python Graph Code 编写与验证
- **client-controls-lua**：Lua 5.3 客户端控件代码
- **qianxing-editor**：编辑器内的脚本映射、挂载和 UI 配置
- **qianxing-gil**：GIL/GIA 存档读写和 Lua 替换
- **qianxing-gil-assembly-pipeline**：把验证后的源码编译产物、信号和 Lua 组装为完整 GIL
- **共享多人流程（Graph Code / Client Lua）**：多人协议设计

Graph Code 编写完成后，由 qianxing-editor 配置挂载，由 qianxing-gil-assembly-pipeline 或 qianxing-gil 写入 `.gil`。

新增消费者或动态端口后，使用 [最终原生类型审计](../../../references/native-maintenance.md) 检查声明、显隐端口、结构体身份及版本。已有图替换通过build schema 2保留图ID和外部引用；仅支持已实现节点的 [联合模型](../../../references/joint-simulation.md) 不能替代宿主验收。
