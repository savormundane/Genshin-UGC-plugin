# 客户端离线模型与环境自检

## 执行Lua模型

```text
python scripts/qianxing.py simulate client.lua --scenario SCENE.json --level LEVEL.gil --mapping main.lua --out SIMULATION.json
```

需要当前Python可导入lupa==2.8的lua53模块。解释器是执行依赖，模型代码随包内置，不调用其他项目的API桩。--level可选，提供时从实际文件读取模板GUID与脚本映射，不使用固定小序号。

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

项目测试与预览应复用其明确版本的宿主模型，不从别的测试截取零散mock或为通过而放行未知API。确认、撤回及迟到回复测试覆盖真实客户端与服务端状态转换，另对最终原生数据边做 [类型回读](native-dataflow-validation.md)；模拟回包不能证明原生处理已运行。窗口失焦和系统离场须有独立宿主证据，不能以生命周期注入代替。

## 游戏内环境自检

将scripts/client_diagnostics.lua的模块按当前内联方式接入开发脚本，调用 `Diagnostics.run({Rect=实际模板GUID})`。输出画布、运行时根控件及其脚本映射/状态，探测给定模板并尝试销毁探测实例，最后打印控件树；只用于开发诊断，不插入玩家文案。

API没有枚举整个编辑器模板库的方法，因此完整候选来自离线level inspect；不能编造运行时“所有模板已枚举”。模板探测会创建/销毁临时控件，应在开发试玩中调用；脚本可读到的挂载与状态不等于服务器或编辑器全部配置。必要时只读取画布和控件树，不运行探测。

## 开启客户端脚本日志

在千星沙箱的日志窗口中勾选“客户端脚本”，确认选择后发起试玩；脚本错误可双击对应日志条目查看。用print记录阶段和ID，printerr不会抛异常，debug.traceback只生成文本。卡死/循环而普通日志不能报告时，检查客户端脚本储存目录中的ErrorLog.txt；它只在相应错误出现时创建，不保证每次都有。

官方操作依据：[客户端控件和客户端脚本，第8节](official/概念介绍/客户端控件和客户端脚本__mhbgxf0nynww.md)。客户端节点图日志是另一套筛选对象，不能用其已勾选代替脚本日志开启。排障时绑定当前交付摘要、日志、触发步骤和设备，不靠多轮无版本猜测。
