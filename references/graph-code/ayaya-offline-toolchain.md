# Graph Code、HTML UI 与 GIL/GIA 底层工具链

编译、挂载和回读普通节点图用 [统一构建工作流](node-graph-workflow.md)。本页用于单步诊断、资源转换及 HTML UI 排版。

包内 `vendor/ayaya` 可离线生成节点图和 UI 文件，无需另行安装 Ayaya 编辑器或提供上游仓库路径。内嵌 Lua 的精确定位和替换使用 `gil-toolkit.mjs`，节点图和资源转换使用本页入口。

## 接入与环境

上游 [Ayaya_Miliastra_Editor](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor) 声明 GPLv3，各第三方组件保留各自的许可。插件内提供所需的上游 GPLv3 源码、节点定义、静态 Workbench 页面和用于文件写回的校准样本。上游游戏项目资源库由原仓库提供。源码改动、原文件和分发文件的校验值见 [集成清单](../../vendor/ayaya/VENDORED.json)，许可证和署名见同目录的 `LICENSE`、`LICENSES` 和 `NOTICE.md`。

将命令中的 `PYTHON` 替换为实际的 Python 可执行文件，将 `PLUGIN` 替换为插件根目录。输入和输出使用绝对路径。完整插件环境见 [运行要求](../../docs/compatibility.md#运行要求)。接入脚本、文件解析、图校验以及 GIL/GIA 生成只用 Python 标准库。HTML 浏览器排版所需的依赖单独安装。运行文件转换前，可用对应入口的帮助确认依赖。接入脚本不会安装依赖、启动 GUI、调用 OCR、识别截图或操作游戏窗口。

    PYTHON PLUGIN/scripts/ayaya_bridge.py doctor
    PYTHON PLUGIN/scripts/ayaya_bridge.py --tool export_project_graphs_to_gia tool -- --help

默认只输出 JSON 命令计划，可先查看工作目录、输入和输出。在操作名之前加 `--execute` 才会执行。未经独立暂存的上游命令可能在所选工具树内写入缓存、中间文件和输出。需要运行这类命令时，用 `--repo` 指向有权限写入的工具副本，并指定独立项目或输出；插件的普通 `build` 会自动管理作业工作区。指定其他解释器时使用 `--python Python可执行文件`。`doctor` 只核对目录入口，依赖和导出功能需另行检查。`--input`、`--output`、`--project`、`--tool` 和 `--package-id` 放在操作名之前，上游参数放在操作名之后。

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

该操作可处理项目中受支持的多类资源。执行前检查选择范围，必要时通过上游 `--selection-json` 或 `--skip-*` 缩小范围。`pure-json` 最小写回用于诊断。正式交付时，用与目标类型匹配的基底、节点和记录样本，保留原件并回读写回范围。文件通常写到包内 `vendor/ayaya/private_extensions/ugc_file_tools/out`，绝对路径也可能被上游重定向，实际位置以报告为准。接入层会拒绝原位覆盖、已存在的输出、注入原地图和跳过校验选项。其保护范围限于接入层检查的参数，上游仍可在自身工作区写入缓存和中间产物。

## GIA 回读与差异

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool parse_gia_to_graph_ir tool -- --input-gia 输入.gia --output-dir 本次回读目录 --check-header
    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool gia_graph_ir_to_gia tool -- --input-ir 单图IR.json --output 新输出.gia

Graph IR 与 GraphModel JSON 不可直接互换；依据具体入口的输入模式转换。比较节点、执行/数据边、端口具体类型、信号绑定及变量定义，不只比较文件能否解压。结构体绑定、字典键值类型、客户端/服务端图作用域应与样本一致。未知字段保留能力按当前路径逐项验证，不继承另一个解析器的保证。

## HTML UI 到文件

HTML 是本链路 UI 源码，修改后重新生成 bundle；不直接维护过期 bundle。先限定项目存档、页面和画布尺寸，再执行：

    PYTHON PLUGIN/scripts/ayaya_bridge.py --execute --tool export_ui_workbench_bundles_from_html tool -- --project-root 项目存档目录 --html 页面.html --pc-canvas-size 1920x1080

工具将 bundle 写到项目 UI 源码目录下的 `__workbench_out__`。HTML/CSS 支持范围以 Workbench 导出的控件类型为准。

生成 bundle 后，通过上述项目写回命令将 UI 控件资源写入新的 GIL。界面资源的 GIA 封装按当前 GIA 类型与模板处理，不将节点图 Graph IR 转换器用于 UI 控件模板。变量绑定、多状态控件、UI GUID 映射和信号派发必须回读核对；HTML 控件资源不是客户端 Lua 脚本控件，不混用 API。

Playwright 与 Chromium 仅用于 HTML/CSS 布局计算。可选依赖见 [上游无界面依赖清单](../../vendor/ayaya/requirements-headless.txt)，其中保留上游对 Python 3.10–3.12 的说明。核心文件流程无需浏览器依赖，也不会安装 PyQt、RapidOCR、ONNX、OpenCV、`keyboard` 或鼠标控制库。

## 验证层次

依次记录入口与依赖检查、严格图校验、资源作用域检查、实际导出路径和报告路径、回读差异、编辑器导入及实际运行。帮助命令通过只说明 CLI 可加载，生成流程应单独验证。解析器、模拟器与游戏表现不一致时，用实际编辑器样本和运行证据定位差异，写入前保留校验。

新增协议及已有工程定义遵循[平台接口与工程合同](../workflows/implementation-policy.md)。
