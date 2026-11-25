# Beyond 按钮预览

在安装了插件的本机对话里，可以这样问。

> 请运行随包的 Beyond 按钮预览，模拟点击 Action，把生成的预览图和点击日志给我看。

这个任务使用 `simulate preview`。用 v1.0.0 源码验证时，点击断言通过，日志记录了 `Button clicked`。打开输出目录中的 `preview.png` 查看软件预览，在 `external-simulation.json` 中核对断言结果。要继续制作界面或修改关卡，可跟做 [PNG 转图元](../creator-demos/png/README.md) 或 [GIL 局部修改](../creator-demos/gil/README.md)。

## 命令行复现

从插件根目录用[专用 Python](../../docs/runtime-environment.md)执行。预览使用随包的 Beyond 后端和 Node。

```text
python scripts/qianxing.py simulate preview samples/beyond-button/preview.json --out NEW_PREVIEW
```

`preview.json` 将 [button.lua](button.lua) 挂到 [project.json](project.json) 的根容器。模拟点击 `Action` 后会记录 `Button clicked`。查看 `preview.png`、`render.json` 和 `external-simulation.json` 可分别读取画面、控件树及断言结果。

复制这三个输入到自己的目录即可调整控件、事件和断言。修改 Lua 后更新 `scripts[].sha256`。将 `case.asserts` 设为空数组可以只看画面，将预期日志改成其他文字可以查看失败诊断。输出使用新的路径。画面属于 Beyond 软件预览，编辑器导入和设备表现须单独验证。
