# Lua源码装配

能力名：client-assembly。scripts/client_assembly.py使用Python标准库，输出单文件Lua、source-map.json和输入摘要；不要求宿主文件系统或require。

```text
python scripts/qianxing.py client assemble CLIENT.json --out NEW_DIRECTORY
python scripts/qianxing.py client locate source-map.json 120
python scripts/qianxing.py client locate source-map.json 120 --gil FINAL.gil
```

CLIENT为schema=2，sources是有序{id,source,requires?}数组。source相对配置文件；依赖必须在此前出现，重复ID和错误顺序拒绝，不自动重排片段。modules是可选{name,as}数组，支持runtime、ui、algorithms、multiplayer、storage；as是非关键字Lua变量名，不能重复。

模块包装为局部函数立即执行的返回值，业务源码按明确顺序拼接，并记录每段实际行号。源文件只读。模块间作用域与业务片段的局部变量可见性由源码决定；不能直接拼接任意带顶层return的独立模块，需使用modules或自行声明明确的封装。

produce schema 2使用client:{assembly:路径}，兼容client:{source:路径}。与GIL组合时必须给出gil.mapping。制作链检查实际内嵌代码等于所选最终源码，并输出同正文client.lua。包含模板别名前缀时同步平移行号映射并记录generated_prefix_lines、embedded_source_sha256及embedded_mapping；locate加--gil会核对摘要，拒绝将旧行号映射套新GIL。

[最终Lua检查](client-check.md)可独立编译装配正文或最终GIL所有映射，并按摘要绑定的source-map定位语法错误；produce schema 2在最终写回后自动执行。它不执行被检正文，API与引用检查另列状态。

可编辑项为源码顺序、依赖和模块别名。测试覆盖两种源码内容、依赖逆序、重复、Lua执行与行号回查；宿主错误日志解析只处理数据，不执行日志文本。

中性清单示例：{schema:2,modules:[{name:ui,as:UI}],sources:[{id:state,source:state.lua},{id:view,source:view.lua,requires:[state,UI]}]}；另一配置可将algorithms命名为Algorithms并装配两个观察片段。正式JSON需给字符串加双引号。把view移到state之前会直接失败；locate对生成包装行返回null，对原始行返回文件与从1开始的行号。最终源码语法仍由Lua5.3检查，装配器不推测顶层return或自动改变作用域。
