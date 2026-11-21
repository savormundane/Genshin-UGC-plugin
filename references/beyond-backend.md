# 可选外部模拟器后端

能力名：beyond-backend。插件随包提供固定提交 02a5ea2cd38bb5bcf7a7ce6dd745be3bb1ae655c 的 miliastra-beyond-simulator 源码、GPL-3.0-only 许可证和 Windows x64 运行依赖。需要 Node 22+，无需另外下载模拟器或安装 npm 包。其他系统的原生渲染依赖尚未随包提供。默认模拟后端不变。

```text
python scripts/qianxing.py beyond SPEC.json --out NEW_DIRECTORY
```

可用 --backend PATH 指定同一提交的干净独立检出；缺依赖时失败，不自动安装。默认加载 vendor/beyond 并核对随包文件摘要。

## GIL 控件转换及渲染

配置 schema 2；gil 与 project 二选一。GIL 模式要求摘要、唯一根 GUID 和显式画布。支持容器、文本框、交互区域，保留选中树的 GUID、名称、父子关系、四端变换和脚本挂载。转换不修改 GIL；输出供模拟器使用，不能回写为原生存档。根的外部父级明确排除，画布尺寸来自模拟器预设，并非读取到的官方画布。

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

未知组件、缺失或重复 GUID、父子不一致、缺少四端状态、非空旋转字段、错误摘要及错误挂载会拒绝。图片资源、输入开关等原生校准继续待办。已识别组件内采用上游有限字段语义读取，未知 protobuf 字段不宣称完整保真；原始文件始终只读。内部 GIA 信封仅用于复用解析器，不作为编辑器交付。

## 显式模拟工程及制作链

旧接口继续接受 project:"controls.json"，scripts 使用 source、sha256、controlId、controlAsset、path。project 是无内嵌脚本的 Authoring JSON；source 可为 Lua，或带唯一 mapping 的 GIL。该模式只提供显式模拟工程绑定。

制作链 schema 2 可添加 beyond:{"spec":"SPEC.json"}，backend 为可选路径。结果写入 beyond/external-simulation.json。绑定本轮生成 GIL 时，将 gil.source 和各 scripts[].source 设为 `@level`，对应 sha256 设为 `@level`（或给定必须匹配的精确摘要）。produce 在全部写回、原生审计及最终 Lua 检查之后绑定最终 level.gil，不读取旧基底。GUID 与 mapping 仍必须明确给出；最终报告的 final_gil_bindings 记录真实摘要。缺少最终 GIL、错误摘要或挂载不匹配会失败，不提交输出。独立 beyond 命令不能单独解析 @level。

任务增加 `"portable":{}` 即可携带模拟器配置、所引用的 GIL/Lua/Authoring JSON，以及完整插件工具链和随包后端。原始配置保留，工作副本路径重定位，@level 标记留到实际构建时绑定；额外输入须位于 portable.roots 声明范围。portable 当前只允许默认随包后端，显式 backend 检出不属于此合同，会拒绝。`qianxing.py verify DELIVERY --portable` 仅静态核对；审阅后以 `--rebuild --trusted-inputs-sha256` 显式重建，比较 GIL、转换模型、PNG 和渲染清单的确定性正文。模拟执行日志属于证据，不要求跨轮路径或计时字节相同。Python/Lua 和 Node 的外部运行条件仍需满足，不声称完全独立的宿主模拟。

路径相对配置目录。已有输出、摘要不符、断言失败、依赖损坏和 45 秒超时不提交正式结果。报告区分 external_lua_model、software_preview、native_graph_model、editor、host；编辑器和实机始终待验。不运行浏览器、游戏 GUI 自动化或截图识别。

软件预览用于检查控件布局和渲染。涉及最终 GIL 时，按交付报告核对输入摘要，并在千星奇域中确认实际挂载和效果。[第三方声明](../THIRD_PARTY_NOTICES.md)
