# 客户端离线模型与环境自检

## 启动检查、预览与场景

```text
python scripts/qianxing.py simulate check client.lua
python scripts/qianxing.py simulate check LEVEL.gil --mapping main.lua
python scripts/qianxing.py simulate preview samples/beyond-button/preview.json --out NEW_PREVIEW
python scripts/qianxing.py simulate run SCENE.json --out NEW_REPORT.json
```

`check` 执行已建模的启动回调，返回脚本身份、日志和首条失败的源行。GIL 只有一份脚本时自动选中，多份时用 `--mapping` 精确选择。`preview` 使用 [Beyond 软件预览](beyond-backend.md)，可先看画面再编写断言。`run` 读取 [schema 2 联合场景](joint-simulation.md)，以场景中声明的路径为准。空断言或必需覆盖不足时，`run` 报告 `not_checked` 并返回非零退出码。MCP `simulate` 返回同样的结论。

## 既有单脚本场景

```text
python scripts/qianxing.py simulate client.lua --scenario SCENE.json --level LEVEL.gil --mapping main.lua --out SIMULATION.json
```

使用[专用 Python 环境](../../docs/runtime-environment.md)中的 Lua 5.3 模块。模型代码随包提供。传入 `--level` 时从实际 GIL 读取模板 GUID 与脚本映射。

也可直接模拟交付文件中的脚本：

```text
python scripts/qianxing.py simulate LEVEL.gil --mapping main.lua --scenario SCENE.json --timeout 10
```

GIL作为源码时，工具直接提取精确匹配的内嵌正文和模板索引；另给--level会拒绝，避免来源冲突。源码Lua配--level只借用绑定数据，报告source_matches_embedded_mapping明确其是否与内嵌脚本同源；false不能作为该GIL已通过逻辑回归的证据。模板的container/text/image/area类型来自绑定回读。

SCENE.json包含整数schema=1、可选canvas（默认1600×900）、params对象、steps与assertions。模型启动顺序为OnInit→OnStart→启用时OnEnable；这是当前模型的确定性约定，不代表已复现完整宿主时序。根控件SetActive、script.enabled会触发模型启停转换；SetVisible只影响输入和表现，不停止OnUpdate。EnableUpdate控制两种更新，时停仅阻止OnLevelUpdate。OnInit/OnStart不能通过lifecycle重复触发，重开应invoke真实重置函数。

步骤op包括tick（dt）、lifecycle（OnEnable/OnDisable/OnDestroy）、invoke（name及args）、cursor/key（control字段路径、event及可选data）、signal（name、有序params）。signal只注入模拟回包；AddInt/AddFloat/AddBool/AddString及AddParam记录类型和有序参数，SendSignal仅记录请求，不执行服务器图或真实通信。销毁后不再投递脚本回调。

```json
{"schema":1,"steps":[{"op":"signal","name":"reply","params":[1]}],"assertions":[{"path":"counter","equals":1}]}
```

枚举从完整API文档提取，模型值为符号而非宿主ABI数值，点击用CursorClick。CursorEventData支持dragging、touchId、GetUIPos/GetPressUIPos/GetUIPosDelta，输入data使用ui_x/ui_y、press_x/press_y、delta_x/delta_y、dragging和touch_id；它不自动进行像素命中或坐标变换。父级隐藏/未激活、area的raycastTarget=false会阻断注入。父级变更同步维护层级并拒绝循环，同级索引从0起；返回的子列表为快照。输入监听和批量移除按文档命名执行。当前仅area模拟光标监听，不把其他控件缺少的API默认放行。

断言读取全局标量或点分字段，不执行表达式，boolean与number严格区分。已支持文本内容、字号、字色和常用图片颜色字段的存储与类型检查，不证明排版、裁剪或颜色视觉正确。字段默认值仅是模型初态，不等于从任意GIL完整重建所有控件参数。未知或只读字段不能随意写入；string.dump不可用，math.isnan/isinf可用，os仅模型化clock。

每次模拟运行于独立进程，默认10秒超时，可用--timeout指定0.05..120秒；超时终止该子进程，不能被Lua里的pcall无限吞掉。另保留回调指令预算和64MiB Lua内存限制。输入须为有限JSON，错误schema、NaN、失败断言和未实现API均失败，不生成通过报告。报告含layer=simulation、源码摘要、是否匹配内嵌正文、sent_signals及已通过断言。

本模型不支持真实渲染、Tween、完整宿主调度、全部控件字段、平台存档和原生服务端执行。遇到未实现API先区分模型缺项与业务错误，再扩展相应合同与回归；不将模型通过当编辑器或实机验收。

项目测试与预览应复用其明确版本的宿主模型，不从别的测试截取零散mock或为通过而放行未知API。双端模型测试覆盖适用于当前协议的状态转换与迟到回复，另对最终原生数据边做 [类型回读](../graph-code/native-dataflow-validation.md)；模拟回包不能证明原生处理已运行。窗口失焦和系统离场须有独立宿主证据，不能以生命周期注入代替。

## 游戏内环境自检

将scripts/client_diagnostics.lua的模块按当前内联方式接入开发脚本，调用 `Diagnostics.run({Rect=实际模板GUID})`。输出画布、运行时根控件及其脚本映射/状态，探测给定模板并尝试销毁探测实例，最后打印控件树；只用于开发诊断，不插入玩家文案。

API没有枚举整个编辑器模板库的方法，因此完整候选来自离线level inspect；不能编造运行时“所有模板已枚举”。模板探测会创建/销毁临时控件，应在开发试玩中调用；脚本可读到的挂载与状态不等于服务器或编辑器全部配置。必要时只读取画布和控件树，不运行探测。

## 开启客户端脚本日志

在千星沙箱的日志窗口中勾选“客户端脚本”，确认选择后发起试玩；脚本错误可双击对应日志条目查看。用print记录阶段和ID，printerr不会抛异常，debug.traceback只生成文本。卡死/循环而普通日志不能报告时，检查客户端脚本储存目录中的ErrorLog.txt；它只在相应错误出现时创建，不保证每次都有。

官方操作依据：[客户端控件和客户端脚本，第8节](../platform/official/概念介绍/客户端控件和客户端脚本__mhbgxf0nynww.md)。客户端节点图日志是另一套筛选对象，不能用其已勾选代替脚本日志开启。排障时绑定当前交付摘要、日志、触发步骤和设备，不靠多轮无版本猜测。

## 读取编辑器调试日志

将编辑器导出的二进制调试日志放进已授权工程。用下面的诊断配置调用 MCP `logs_diagnose`，传入配置路径与 SHA-256。命令行可用 `python scripts/qianxing.py logs diagnose diagnose.json`。

```json
{"schema":2,"logs":[{"path":"playtest.bytes","format":"editor-debug-log","limit":100}],"bindings":[]}
```

每份日志最多 64 MiB。`offset` 从 0 开始，按识别出的打印记录分页；`editor_logs[].next_offset` 给出下一页，`limit` 可为 1 到 1000。报告保留客户端 Lua 或节点图的打印原文、记录位置，以及记录中可读的图 ID、实体 ID 和时间。未识别项计入 `ignored_record_count`，图轨迹中的字符串不计作打印。普通 JSONL 输入继续使用 `logs` 中的路径字符串。

二进制格式依据社区对双长度封套与 `1.22.2`、`1.23.2` 字段路径的观察。目前本插件以合成样本检查读取、分页与拒绝条件，报告中的构建匹配、编辑器和实机状态留待独立证据。打印正文按数据处理，无法仅按文本判断错误等级。 [格式观察](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/debug-log.mjs)
