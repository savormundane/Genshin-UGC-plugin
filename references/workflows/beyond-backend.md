# Beyond 界面预览

用随包 Beyond 检查控件布局、Lua 行为及软件画面。回执里的 `external_lua_model` 和 `software_preview` 分别记录行为与画面。安装方式与 Canvas 准备见[运行环境](../../docs/runtime-environment.md)。

```text
python scripts/qianxing.py simulate preview samples/beyond-button/preview.json --out NEW_PREVIEW
python scripts/qianxing.py beyond SPEC.json --out NEW_DIRECTORY
```

[按钮示例](../../samples/beyond-button/README.md)可用来检查 PNG、控件树和点击日志。`simulate preview` 始终请求画面，可只观察结果。`beyond` 和 `produce` 的 Beyond 阶段要求非空的 `case.asserts`，用来做场景检查。断言或 Lua 执行失败时，预览命令返回非零退出码，已生成的画面、控件树和日志会保存到 `NEW_PREVIEW.diagnostics`。Lua 挂载和运行错误记录在 `checks.lua`。

在 MCP 中用 `simulate` 并设 `preview=true`。参数、图片与诊断目录见 [MCP 工具参数](../../docs/mcp.md)。拟合素材的 `mount` 可生成可供预览的配置。 [拟合预览示例](../../samples/creator-demos/png/README.md#拟合并预览可挂载的-lua)

## GIL 控件转换及渲染

配置使用 schema 2，在 `gil` 和 `project` 中选择一项，`scripts` 至少声明一个脚本。读 GIL 时声明文件校验值、唯一的根控件 GUID 和画布预设。转换从根控件读取已校准的容器、文本框和交互区域，保留 GUID、名称、父子关系、四端变换和脚本挂载。

```json
{
  "schema": 2,
  "gil": {"source": "level.gil", "sha256": "实际 SHA-256 校验值", "root_guid": 1073742081, "canvas": "pc-16-9"},
  "scripts": [{"source": "level.gil", "sha256": "同一 GIL 的 SHA-256 校验值", "mapping": "main.lua", "control_guid": 1073742081, "path": "main"}],
  "case": {"format": "qxqy-autotest", "version": 1, "name": "neutral", "duration": 0.1, "events": [], "asserts": [{"kind": "log", "contains": "ready"}]},
  "render": true,
  "render_checks": [{"name": "Label", "width": 180, "height": 60, "text": "READY"}]
}
```

随包 Beyond 的 `case.duration` 是可选的最短运行时间，单位为秒，须为非负有限数字。预览按固定步长推进到 `duration`、最后一个事件时间和最后一个断言时间中最晚的一项。没有事件和断言时，也可仅凭 `duration` 观察逐帧变化。断言在 `at` 指定的秒数到达后的首个时间步执行，省略 `at` 时在启动时检查。断言失败会提前结束。

`canvas` 支持 `pc-16-9` 和 `mobile-16-9`。`scripts` 须精确覆盖选中树下的全部原生挂载，按映射名从同一份 GIL 提取脚本。未知组件、重复或缺失 GUID、父子关系不符、变换缺项及当前未校准的非空旋转字段会拒绝转换。`converted-project.json` 是只读转换的中间结果，编辑器交付仍用原生文件流程。

`render:true` 输出透明背景的 `preview.png` 和 `render.json`。`render_checks` 按唯一名称比较 `width`、`height`、`text`，省略时即使有图片，绘制断言仍为 `not_checked`。容器和交互区域可在控件树查看。软件画面使用本地字体和布局，点击命中及游戏内显示按[相应验证](validation.md)记录。

## 显式模拟工程及制作链

也可以用 `project:"controls.json"` 指定无内嵌脚本的 Authoring JSON。`scripts` 每项声明 `source`、`sha256`、`controlId`、`controlAsset` 和 `path`。脚本可用独立 Lua，或给出唯一 `mapping` 从 GIL 读取。路径相对该 Beyond 配置目录。

组合任务以 `beyond.spec` 指定配置。在其中将 `gil.source` 和各脚本的 `source` 设为 `@level`，把校验值设为 `@level` 或精确匹配的 SHA-256，即可绑定本轮最终 GIL。GUID 与映射仍须明确。结果见 `beyond/external-simulation.json` 的 `final_gil_bindings`。必需断言失败时制作链拒绝提交。 [组合制作](produce.md)

独立命令可用 `--backend PATH` 指定与锁定提交一致的干净上游检出，用于对照。默认从包内固定入口启动，核对源码修订与依赖。需要迁移交付时选择包内默认后端，并按[可迁移交付](portable-delivery.md)核对和重建。Beyond 的文字布局和部分交互也依赖 Canvas。要检查插件自己的 Lua 及原生图模型，可用[联合模拟](joint-simulation.md)。

## 后端维护

包内源码、上游基线、锁定的 Canvas 资产与修订登记见 [Beyond 源码修订](../../docs/contributing/maintenance.md#beyond-源码修订)。报告的 `backend_commit` 和 `backend_bundle_sha256` 分别标识上游基线和已加载的本地修订。
