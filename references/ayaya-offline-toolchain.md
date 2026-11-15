# Graph Code、HTML UI 与 GIL/GIA 底层工具链

完整节点图制作优先使用 [统一构建工作流](node-graph-workflow.md)。以下入口用于单步诊断、资源转换及 HTML UI 分支。

使用包内 `vendor/ayaya` 的离线源码完成节点图与 UI 文件交付，无需另行安装 Ayaya 编辑器或提供原仓库路径。插件原有 `gil-toolkit.mjs` 继续负责准确命中的内嵌 Lua 替换，本链路负责节点图与资源级转换。

## 接入与环境

上游：[Ayaya_Miliastra_Editor](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor)。按当地仓库的源码与许可使用；上游声明 GPLv3，各第三方组件保留独立许可。包内包含经筛选的上游 GPLv3 源码、节点定义、静态 Workbench 页面和文件写回所需的校准 seed；不包含上游游戏项目资源库。源码改动、原文件/分发文件摘要见 `vendor/ayaya/VENDORED.json`，许可证及署名见同目录 LICENSE、LICENSES 和 NOTICE.md。

命令中的 `PYTHON` 为实际 Python 可执行文件，`PLUGIN` 为本包根；输入与输出采用实际绝对路径。使用 Python 3.10–3.12，文件解析、图校验、GIL/GIA 生成链路仅用标准库；HTML 浏览器排版为可选依赖。接入脚本仅用标准库，不安装依赖，不启动 GUI、不执行 OCR、截图识别或游戏鼠标键盘自动化。不要为文件转换直接安装整个 GUI requirements；先用具体入口帮助定位所需依赖，缺少模块时单独处理该链路。

    PYTHON PLUGIN/scripts/ayaya_bridge.py doctor
    PYTHON PLUGIN/scripts/ayaya_bridge.py --tool export_project_graphs_to_gia tool -- --help

默认输出 JSON 命令计划；增加位于 action 之前的 `--execute` 才调用。解释器不同则传 `--python Python可执行文件`。`doctor` 仅核对目录入口，不证明依赖或导出可用。选项 `--input/--output/--project/--tool/--package-id` 均放在 action 之前；action 后只放上游参数。

## Graph Code 到节点图

Graph Code 是节点图 DSL，不是任意 Python。根据当前节点注册表选择节点，核对 builtin/composite 引用、端口、类型、事件和信号参数；不要通过 Python 业务运行成功推断节点图能导入。具体节点规则由当前注册表与官方资料共同核对，不把第三方校验器当官方规范。

图代码位于包内工具识别的项目存档资源作用域中。输入先做严格单图校验，再按项目核对 GUID、资源引用、挂载与 UI 变量：

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --input 图源码.py validate-file
    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --package-id 项目名 validate-project
    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --package-id 项目名 validate-ui

需要检查中间模型：

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool export_graph_model_json_from_graph_code tool -- --graph-code 图源码.py --output-json 新模型.json

直接生成节点图 GIA：

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool export_project_graphs_to_gia tool -- --project-root 项目存档目录 --graph-code 图源码.py --out-dir 本次独立输出名 --pack

既有信号定义读取当前项目；新信号由Agent设计并同步声明与调用；有需要时指定 `--base-gil-for-signal-defs`。涉及 UIKey、实体和元件引用时选择对应 UI 导出记录、ID 参考与覆盖表；不能填 0 或跳过校验冒充完成。GIA 导入后仍需正确挂载，生成文件不等于已挂载到游戏实体。

## 项目写回 GIL

先读当前 CLI 的 `project import --help`，确认选定内容、merge/overwrite、节点模板与信号定义。接入脚本提供使用新输出的项目写回：

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --project 项目存档目录 --input 基底.gil --output 新输出.gil project-import

该操作会处理该项目已支持的资源，不只是单张图；先核对选择范围，按需要通过上游 `--selection-json` 或 `--skip-*` 限定。不要将诊断用途的 pure-json 最小写回当成完整交付。基底及节点/record 样本应与目标类型匹配，保留原始文件，回读检查写回范围。文件输出通常被收口到包内 vendor/ayaya/private_extensions/ugc_file_tools/out；绝对输出路径可能被上游重定向，须以报告路径为准。接入层拒绝原位覆盖、新输出已存在、注入原地图及跳过校验选项；它不是上游全部参数的安全沙箱。上游工具可在其自身工作区写缓存及中间产物。

## GIA 回读与差异

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool parse_gia_to_graph_ir tool -- --input-gia 输入.gia --output-dir 本次回读目录 --check-header
    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool gia_graph_ir_to_gia tool -- --input-ir 单图IR.json --output 新输出.gia

Graph IR 与 GraphModel JSON 不可直接互换；依据具体入口的输入模式转换。比较节点、执行/数据边、端口具体类型、信号绑定及变量定义，不只比较文件能否解压。结构体绑定、字典键值类型、客户端/服务端图作用域应与样本一致。未知字段保留能力按当前路径逐项验证，不继承另一个解析器的保证。

## HTML UI 到文件

HTML 是本链路 UI 源码，修改后重新生成 bundle；不直接维护过期 bundle。先限定项目存档、页面和画布尺寸，再执行：

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool export_ui_workbench_bundles_from_html tool -- --project-root 项目存档目录 --html 页面.html --pc-canvas-size 1920x1080

此工具将 bundle 写入该项目 UI源码 下的 `__workbench_out__`；不是只读操作。它需要 Playwright 和 Chromium 用于浏览器排版计算，不依赖 OCR，也不操作游戏窗口；未准备此环境时，其余节点图/GIL/GIA流程仍可单独使用。HTML/CSS 支持范围以 Workbench 导出的控件类型为准，不承诺任意网页无损转换。

生成 bundle 后，通过上述项目写回命令将 UI 控件资源写入新的 GIL。界面资源的 GIA 封装按当前 GIA 类型与模板处理，不将节点图 Graph IR 转换器用于 UI 控件模板。变量绑定、多状态控件、UI GUID 映射和信号派发必须回读核对；HTML 控件资源不是客户端 Lua 脚本控件，不混用 API。

Playwright 与 Chromium 仅用于 HTML/CSS 布局计算，依赖清单在 vendor/ayaya/requirements-headless.txt。核心文件链路不需要它们；不会安装 PyQt、RapidOCR、ONNX、OpenCV、keyboard 或鼠标控制库。

## 验证层次

依次记录：入口与依赖检查、严格图校验、资源作用域检查、导出及报告实际落盘路径、回读语义差异、编辑器导入、实际运行。帮助命令成功只证明 CLI 可加载，不证明生成链路成功。解析器、模拟器与游戏表现冲突时，以真实编辑器样本和运行证据定位差异，不跳过校验硬写。

新协议/图逻辑与必要文件适配由Agent按 [主动实现约定](implementation-policy.md) 设计并制作；已有配置读取兼容，缺少通用命令时补工具后继续交付。
