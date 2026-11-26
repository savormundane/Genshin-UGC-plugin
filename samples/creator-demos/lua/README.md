# 排查一处 Lua 语法错误

将下面两行代码保存为已授权工程中的 `button.lua`。本例只需读取工程的权限。

```lua
local function on_click()
    print("clicked")
```

> 请用千星奇域插件检查当前工程的 button.lua。指出 Lua 编译报错的位置，解释原因并给出可替换的完整代码。先保留我的源文件。

调用 `client_check` 后应看到 `lua_syntax`。编译器在第 3 行读到文件结束，提示缺少关闭第 1 行函数的 `end`。将修复版保存为 `button-fixed.lua`。

```lua
local function on_click()
    print("clicked")
end
```

> 请用相同的工具重新检查 button-fixed.lua，告诉我语法是否通过。

再次调用 `client_check`，语法检查应通过。将修复版合入自己的脚本后，还需核对控件 API、事件及挂载。 [客户端 Lua 接入](../../../references/editor/lua/client-assembly.md) · [软件模拟按钮点击](../../beyond-button/README.md)
