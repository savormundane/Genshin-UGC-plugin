# Beyond 按钮预览

把 [preview.json](preview.json)、[project.json](project.json) 和 [button.lua](button.lua) 复制到已授权的工程目录，准备新的输出位置，然后发送下面的请求。 [工程绑定](../../docs/runtime-environment.md#连接-mcp-或切换工程)

> 请用当前工程的 preview.json 做 Beyond 预览，模拟点击 Action，把画面、点击断言和 Lua 日志给我看。

助手计算配置文件的 SHA-256，调用 `simulate` 并设 `preview=true`。配置把 Lua 挂到根容器，模拟点击 `Action`。正常时断言通过，日志记录 `Button clicked`。

| 文件 | 用途 |
| --- | --- |
| `preview.png` | 查看软件渲染画面，客户端支持时会随 MCP 响应附上。 |
| `render.json` | 核对控件和渲染几何数据。 |
| `external-simulation.json` | 核对断言、Lua 执行结果和事件日志。 |

## 命令行复现

从插件根目录用[已配置的 Python](../../docs/runtime-environment.md#只用-cli)执行。预览使用随包的 Beyond 后端和 Node。 [Beyond 运行要求](../../docs/compatibility.md#运行要求)

```text
python scripts/qianxing.py simulate preview samples/beyond-button/preview.json --out NEW_PREVIEW
```

修改 Lua 后更新 `scripts[].sha256`，每次预览选择新的输出位置。可将预期日志改成其他文字来练习检查失败诊断。MCP 将失败结果保存在名称带 `.diagnostics` 的目录。 [诊断产物](../../references/workflows/beyond-backend.md)

示例验证范围是 Beyond 软件预览和模拟点击。界面在编辑器及游戏内的表现另行验证。
