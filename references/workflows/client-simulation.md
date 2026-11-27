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

直接以 GIL 为输入时，从指定映射提取脚本正文和模板索引，此时不能再传 `--level`。以 Lua 源文件为输入时，`--level` 只提供绑定数据。报告的 `source_matches_embedded_mapping` 标明源文件正文是否与内嵌脚本一致。为 `false` 时，结果只适用于外部 Lua。`container`、`text`、`image` 和 `area` 模板类型均来自绑定回读。

SCENE.json包含整数schema=1、可选canvas（默认1600×900）、params对象、steps与assertions。模型启动顺序为OnInit→OnStart→启用时OnEnable；这是当前模型的确定性约定，不代表已复现完整宿主时序。根控件SetActive、script.enabled会触发模型启停转换；SetVisible只影响输入和表现，不停止OnUpdate。EnableUpdate控制两种更新，时停仅阻止OnLevelUpdate。OnInit/OnStart不能通过lifecycle重复触发，重开应invoke真实重置函数。

步骤op包括tick（dt）、lifecycle（OnEnable/OnDisable/OnDestroy）、invoke（name及args）、cursor/key（control字段路径、event及可选data）、signal（name、有序params）。signal只注入模拟回包；AddInt/AddFloat/AddBool/AddString及AddParam记录类型和有序参数，SendSignal仅记录请求，不执行服务器图或真实通信。销毁后不再投递脚本回调。

```json
{"schema":1,"steps":[{"op":"signal","name":"reply","params":[1]}],"assertions":[{"path":"counter","equals":1}]}
```

枚举从完整API文档提取，模型值为符号而非宿主ABI数值，点击用CursorClick。CursorEventData支持dragging、touchId、GetUIPos/GetPressUIPos/GetUIPosDelta，输入data使用ui_x/ui_y、press_x/press_y、delta_x/delta_y、dragging和touch_id；它不自动进行像素命中或坐标变换。父级隐藏/未激活、area的raycastTarget=false会阻断注入。父级变更同步维护层级并拒绝循环，同级索引从0起；返回的子列表为快照。输入监听和批量移除按文档命名执行。当前仅area模拟光标监听，不把其他控件缺少的API默认放行。

断言读取全局标量或点分字段，不执行表达式，boolean与number严格区分。已支持文本内容、字号、字色和常用图片颜色字段的存储与类型检查，不证明排版、裁剪或颜色视觉正确。字段默认值仅是模型初态，不等于从任意GIL完整重建所有控件参数。未知或只读字段不能随意写入；string.dump不可用，math.isnan/isinf可用，os仅模型化clock。

每次模拟在独立进程中运行，默认 10 秒超时。可用 `--timeout` 设置 0.05 至 120 秒。超时会终止子进程，Lua 的 `pcall` 无法拦截。模型还限制回调指令数和 Lua 内存（64 MiB）。JSON 中的数值须为有限数。schema 错误、断言失败或调用未实现的 API 均会失败。报告包含 `layer=simulation`、源码摘要、与内嵌正文的匹配结果、`sent_signals` 及通过的断言。

本模型不支持真实渲染、Tween、完整宿主调度、全部控件字段、平台存档和原生服务端执行。遇到未实现API先区分模型缺项与业务错误，再扩展相应合同与回归；不将模型通过当编辑器或实机验收。

项目测试与预览应复用版本明确的宿主模型。未知 API 应报告覆盖缺口。双端模型测试检查当前协议的状态转换和迟到回复，最终 GIL 的数据连线另做[类型回读](../graph-code/native-dataflow-validation.md)。原生服务端处理、窗口失焦和系统离场仍需对应的宿主证据。

## 游戏内环境自检

将scripts/client_diagnostics.lua的模块按当前内联方式接入开发脚本，调用 `Diagnostics.run({Rect=实际模板GUID})`。输出画布、运行时根控件及其脚本映射/状态，探测给定模板并尝试销毁探测实例，最后打印控件树；只用于开发诊断，不插入玩家文案。

API没有枚举整个编辑器模板库的方法，因此完整候选来自离线level inspect；不能编造运行时“所有模板已枚举”。模板探测会创建/销毁临时控件，应在开发试玩中调用；脚本可读到的挂载与状态不等于服务器或编辑器全部配置。必要时只读取画布和控件树，不运行探测。

## 开启客户端脚本日志

在千星沙箱的日志窗口中勾选“客户端脚本”，确认选择后发起试玩；脚本错误可双击对应日志条目查看。用print记录阶段和ID，printerr不会抛异常，debug.traceback只生成文本。卡死/循环而普通日志不能报告时，检查客户端脚本储存目录中的ErrorLog.txt；它只在相应错误出现时创建，不保证每次都有。

客户端脚本和客户端节点图的日志分别启用。排障时记录当前交付文件的校验值、日志、触发步骤和设备。 [官方《客户端控件和客户端脚本》第 8 节](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhbgxf0nynww)

## 读取编辑器调试日志

用日志诊断查看编辑器打印，也可用同一工具关联工程自己的 JSONL 日志。 [读取编辑器调试日志](log-diagnostics.md#读取编辑器调试日志)
