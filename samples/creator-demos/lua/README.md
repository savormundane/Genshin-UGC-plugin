# 排查一处 Lua 语法错误

把下列代码保存为已授权工程中的 `button.lua`。使用本地 MCP 的 `client_check` 编译检查，读取文件即可开始。

```lua
local function on_click()
    print("clicked")
```

> 请用千星奇域插件检查当前工程的 button.lua。指出 Lua 编译报错的位置，解释原因并给出可替换的完整代码。先保留我的源文件。

实测 `client_check` 返回 `lua_syntax`。编译器在第 3 行读到文件结束，提示缺少关闭第 1 行函数的 `end`。将修复后的版本另存为 `button-fixed.lua`。

```lua
local function on_click()
    print("clicked")
end
```

> 请用相同的工具重新检查 button-fixed.lua，告诉我语法是否通过。

再次调用 `client_check` 后，语法状态为 `passed`。这次验证的是 Lua 编译。接入真实控件时，继续核对控件 API 和事件挂载。 [客户端 Lua 接入](../../../references/client-assembly.md) · [软件模拟按钮点击](../../beyond-button/README.md)
