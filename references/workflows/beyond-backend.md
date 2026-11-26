# Beyond 界面预览

界面预览由随包 Beyond 后端执行。需要 Windows x64 和 Node 22+。完整 Windows ZIP 携带 Canvas 原生模块和 ICU 数据，插件运行环境就绪后可以离线预览。Git 市场和 Cordis 安装在首次使用 Beyond 时下载这两个文件，校验后复用缓存。 [原生资产锁定清单](../../vendor/beyond/native-canvas.json)

```text
python scripts/qianxing.py simulate preview samples/beyond-button/preview.json --out NEW_PREVIEW
python scripts/qianxing.py beyond SPEC.json --out NEW_DIRECTORY
```

先用[按钮示例](../../samples/beyond-button/README.md)看 PNG、控件树和点击日志。`simulate preview` 始终请求软件画面，可省略断言。报告的 `checks.lua` 单独记录脚本挂载和运行错误。Lua 出错或已声明的断言失败时，命令返回非零，已生成的画面、控件树和日志保存在 `NEW_PREVIEW.diagnostics`。失败断言会记录预期值和实际值。`beyond` 和制作链入口用于正式场景检查，需要提供断言。

MCP 中用 `simulate`，传配置的路径和摘要并设 `preview=true`。工具会附上本次生成的 `preview.png`。通过时用 `output` 和 `outputs_sha256` 定位并核对文件。失败时看诊断原因，并用 `diagnostics_output` 和 `diagnostics_sha256` 找到已保存的画面和报告。诊断目录重名时仍可收到本次生成的图，用新名称重试即可保存。为 `asset_fit` 配置 `mount` 后，会生成可直接用于 `simulate` 的配置和供软件预览使用的图片模板。 [拟合预览示例](../../samples/creator-demos/png/README.md#拟合并预览可挂载的-lua)

可用 --backend PATH 指定同一提交的干净独立检出；缺依赖时失败，不自动安装。默认加载 vendor/beyond 并核对随包文件摘要。

即使关闭 PNG 输出，Beyond 的文字布局和部分交互仍需要 Canvas。只验证插件模型覆盖的逻辑时，使用 [联合模拟](joint-simulation.md)。

## GIL 控件转换及渲染

配置使用 schema 2，从 `gil` 和 `project` 中选择一项。使用 GIL 时，提供摘要、唯一的根控件 GUID 和指定画布。支持容器、文本框、交互区域，保留选中树的 GUID、名称、父子关系、四端变换和脚本挂载。转换不修改 GIL；输出供模拟器使用，不能回写为原生存档。转换范围从所选根控件开始，画布尺寸采用模拟器预设。

```json
{
  "schema": 2,
  "gil": {"source":"level.gil","sha256":"实际SHA256","root_guid":1073742081,"canvas":"pc-16-9"},
  "scripts": [{"source":"level.gil","sha256":"同一GIL摘要","mapping":"main.lua","control_guid":1073742081,"path":"main"}],
  "case": {"format":"qxqy-autotest","version":1,"name":"neutral","duration":0.1,"events":[],"asserts":[{"kind":"log","contains":"ready"}]},
  "render": true,
  "render_checks": [{"name":"Label","width":180,"height":60,"text":"READY"}]
}
```

canvas 当前允许 pc-16-9 和 mobile-16-9。scripts 必须准确覆盖选中树内全部原生挂载，从同一最终 GIL 按映射名提取 Lua；遗漏、重复或改挂到别的 GUID 都失败。脚本和 case.asserts 必须非空。模板库不自动展开，动态实例索引及整个关卡的宿主行为不在此转换范围内。

render:true 生成透明背景 preview.png 和 render.json；render_checks 按唯一名称核对最终绘制对象的 width、height、text。未指定检查只表示生成了预览，rendering 仍为 not_checked。区域和容器本身不绘制像素，其身份和层级可查 converted-project.json，空白图片不能证明交互正确。字体及排版由软件渲染器决定，不承诺与宿主逐像素相同。

未知组件、缺失或重复 GUID、父子不一致、缺少四端状态、非空旋转字段、错误摘要及错误挂载会拒绝。图片资源、输入开关等仍需原生样本校准。已识别组件仅按上游已知字段读取，未知 protobuf 字段的转换结果未经验证。源文件只读。内部 GIA 封装只供解析器复用，编辑器交付另走原生文件流程。

## 显式模拟工程及制作链

旧接口继续接受 project:"controls.json"，scripts 使用 source、sha256、controlId、controlAsset、path。project 是无内嵌脚本的 Authoring JSON；source 可为 Lua，或带唯一 mapping 的 GIL。该模式按配置中明确声明的工程、脚本和控件关系绑定。

制作链 schema 2 可添加 beyond:{"spec":"SPEC.json"}，backend 为可选路径。结果写入 beyond/external-simulation.json。绑定本轮生成 GIL 时，将 gil.source 和各 scripts[].source 设为 `@level`，对应 sha256 设为 `@level`（或给定必须匹配的精确摘要）。produce 在全部写回、原生审计及最终 Lua 检查之后绑定最终 level.gil，不读取旧基底。GUID 与 mapping 仍必须明确给出；最终报告的 final_gil_bindings 记录真实摘要。缺少最终 GIL、错误摘要或挂载不匹配会失败，不提交输出。独立 beyond 命令不能单独解析 @level。

任务增加 `"portable":{}` 后，交付目录包含模拟器配置、所引用的 GIL、Lua 和 Authoring JSON，以及完整插件工具链和随包后端。工具保留原始配置，调整工作副本中的路径，并在实际构建时绑定 `@level`。额外输入须位于 `portable.roots` 声明的目录内。该模式只接受随包默认后端，指定 `backend` 检出目录会被拒绝。`qianxing.py verify DELIVERY --portable` 仅静态核对；审阅后以 `--rebuild --trusted-inputs-sha256` 显式重建，比较 GIL、转换模型、PNG 和渲染清单的确定性正文。模拟执行日志属于证据，不要求跨轮路径或计时字节相同。Python/Lua 和 Node 的外部运行条件仍需满足，不声称完全独立的宿主模拟。

路径相对配置目录。已有输出、摘要不符、断言失败、依赖损坏和 45 秒超时不提交正式结果。报告区分 external_lua_model、software_preview、native_graph_model、editor、host；编辑器和实机始终待验。不运行浏览器、游戏 GUI 自动化或截图识别。

软件预览用于检查控件布局和渲染。涉及最终 GIL 时，按交付报告核对输入摘要。[第三方声明](../../THIRD_PARTY_NOTICES.md)

## 后端维护

随包源码以 GPL-3.0-only 分发。报告的 `backend_commit` 记录上游基线，`backend_bundle_sha256` 记录实际加载的本项目修订。每次运行都会核对修订及文件摘要。 [后端源码清单](../../vendor/beyond/bundle.json) · [修订锁定](../../scripts/beyond-revision.json)

在插件源码中编辑已有的 Beyond JavaScript 文件，再执行下方命令。将路径换成本次实际修改的文件，可列多个。待审目录需要位于源码外。

```text
python -B scripts/prepare_beyond_revision.py studio/play/session.js --reason "说明本次维护变更" --out ../beyond-review
```

检查待审目录生成的 `bundle.json`、`beyond-revision.json` 和 `PUBLIC_SOURCES.json`，审核后应用到同一提交。用 [按钮样例](../../samples/beyond-button/README.md)核对成功和失败的画面、日志与断言，也要核对随包 Canvas 摘要。 [本地检查](../../docs/contributing/development.md)
