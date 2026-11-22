# Beyond 按钮预览

从插件根目录用[专用 Python](../../docs/runtime-environment.md)执行。预览使用随包的 Beyond 后端和 Node。

```text
python scripts/qianxing.py simulate preview samples/beyond-button/preview.json --out NEW_PREVIEW
```

`preview.json` 将 [button.lua](button.lua) 挂到 [project.json](project.json) 的根容器。模拟点击 `Action` 后会记录 `Button clicked`。查看 `preview.png`、`render.json` 和 `external-simulation.json` 可分别读取画面、控件树及断言结果。

复制这三个输入到自己的目录即可调整控件、事件和断言。修改 Lua 后更新 `scripts[].sha256`。将 `case.asserts` 设为空数组可以只看画面，将预期日志改成其他文字可以查看失败诊断。输出使用新的路径。画面属于 Beyond 软件预览，编辑器导入和设备表现须单独验证。
