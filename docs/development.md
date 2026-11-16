# 本地检查与提交前验证

当前完整插件以 Windows x64 为主要运行目标。下面的仓库静态检查使用 Python 标准库与 Node.js，不要求启动游戏编辑器；它们无法代替完整安装及游戏宿主测试。

在仓库根目录运行：

```powershell
python scripts/check_repository.py
python -m compileall -q scripts
node scripts/test_gil.mjs
```

- `check_repository.py`：检查插件版本字段一致性、必要清单及主要 Markdown 的本地链接。
- `compileall`：检查本项目 Python 脚本是否可被解释器解析，不代表运行时依赖齐全。
- `test_gil.mjs`：执行仓库现有 GIL 字节回读、Lua 替换及异常输入的局部测试，不代表所有 GIL 实例被覆盖。

GitHub Actions 的 [Repository checks](../.github/workflows/repository-check.yml) **仅支持手动启动**（`workflow_dispatch`），普通 push 和 PR 不自动消耗 Actions 配额。

涉及完整安装、MCP 工具、模拟器、实际游戏文件的变动，需结合 [安装说明](../references/installation.md) 与 [验证边界](compatibility.md)另行检查。不得用上述静态检查代替实机验收。
