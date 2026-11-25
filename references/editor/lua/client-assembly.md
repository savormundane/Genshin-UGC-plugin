# Lua源码装配

`client-assembly` 使用 Python 标准库，将源码装配成单个 Lua 文件，并输出 `source-map.json` 和输入摘要。装配后的脚本无需访问宿主文件系统或调用 `require`。实现位于 `scripts/miliastra/client/assembly.py`。

```text
python scripts/qianxing.py client assemble CLIENT.json --out NEW_DIRECTORY
python scripts/qianxing.py client locate source-map.json 120
python scripts/qianxing.py client locate source-map.json 120 --gil FINAL.gil
```

CLIENT为schema=2，sources是有序{id,source,requires?}数组。source相对配置文件；依赖必须在此前出现，重复ID和错误顺序拒绝，不自动重排片段。modules是可选{name,as}数组，支持runtime、ui、algorithms、multiplayer、storage；as是非关键字Lua变量名，不能重复。

每个模块包装成局部函数，立即调用并取返回值。业务源码按配置顺序拼接，并记录各片段的实际行号。源文件只读。模块间作用域与业务片段的局部变量可见性由源码决定；不能直接拼接任意带顶层return的独立模块，需使用modules或自行声明明确的封装。

produce schema 2使用client:{assembly:路径}，兼容client:{source:路径}。与GIL组合时必须给出gil.mapping。制作链检查实际内嵌代码等于所选最终源码，并将同一正文输出为 `client.lua`。包含模板别名前缀时同步平移行号映射并记录generated_prefix_lines、embedded_source_sha256及embedded_mapping；locate加--gil会核对摘要，拒绝用旧行号映射定位新的 GIL。

[最终Lua检查](client-check.md)可独立编译装配正文或最终GIL所有映射，并按摘要绑定的source-map定位语法错误；produce schema 2在最终写回后自动执行。它不执行被检正文，API与引用检查另列状态。

可编辑项为源码顺序、依赖和模块别名。测试覆盖两种源码内容、依赖逆序、重复、Lua执行与行号回查；宿主错误日志解析只处理数据，不执行日志文本。

清单示例为 {schema:2,modules:[{name:ui,as:UI}],sources:[{id:state,source:state.lua},{id:view,source:view.lua,requires:[state,UI]}]}；另一配置可将algorithms命名为Algorithms并装配两个观察片段。正式JSON需给字符串加双引号。把view移到state之前会直接失败；locate对生成包装行返回null，对原始行返回文件与从1开始的行号。最终源码语法仍由Lua5.3检查，装配器不推测顶层return或自动改变作用域。

## 项目生成的 Lua 数据目录

在项目自己的生成器中合并外部 JSON。先用相同输入在独立目录复现当前生成物，比较文件摘要。无法复现时，先定位生成器、输入或执行条件的变化。

使用稳定键确定全量或子集映射，在生成期拒绝重复键、未知目标和缺失的必需值。明确哪些字段可覆盖，子集外记录保留原值。列数或类型检查通过后再输出文件，保持序列化顺序，动态字符串键使用 `["key"] = value`，并按 Lua 字符串规则转义。

用 Lua 检查或实际下游任务加载新生成物，抽查不同 ID 范围，比较记录总数、分类分布和必需值，确认旧白名单或缓存没有屏蔽新字段。交付清单和规则摘要由当前生成链产出。归档对照和重建见[工程诊断](../../workflows/project-diagnosis.md#交付文件与清单不一致)。
