# 第一次使用

按[安装指南](installation.md)完成安装并在新会话启用插件。项目目录可以为空。

把这句话发送给助手：

> 请调用 Genshin-UGC 的 `nodes_lookup` 查询服务端“启动定时器”，告诉我调用签名、输入端口类型，以及序列 `[1, 3, 5, 7]` 的含义。

在客户端的工具调用记录中确认返回了 `server` 节点。该节点的调用签名为 `启动定时器(game, 目标实体, 定时器名称, 是否循环, 定时器序列)`，四个数据输入的类型依次为实体、字符串、布尔值和浮点数列表。示例表示启动后在第 1、3、5、7 秒触发。[随包节点定义](../vendor/ayaya/plugins/nodes/server/执行节点/启动定时器.py)

独立使用终端时，按[运行环境](runtime-environment.md)找到专用 Python，再在解压后的 `Genshin-UGC` 目录运行同一查询。

```powershell
& '<专用 Python 的绝对路径>' .\scripts\qianxing.py nodes '启动定时器' --scope server --limit 1
```

工具不可见时，核对插件是否启用和安装目录是否完整。[安装排障](installation.md#失败后续装)

有实际输入后，把 GIL、Lua 或图片放入安装时选择的项目目录，告诉助手目标和千星奇域版本。[创作任务示例](examples.md)
