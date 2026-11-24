# 运行要求与支持范围

[安装指南](installation.md)

## 运行要求

| 项目 | 要求 |
| --- | --- |
| 操作系统 | 完整工具面向 Windows x64，随包模拟器依赖 Windows 原生模块。 |
| Python | CPython 3.11–3.14。启动器复用具备依赖的环境，缺依赖时使用 PATH 上的 uv。 |
| Node.js | 插件 MCP 启动器需要 22+，DeepSeek Harness 接入使用 24.9+。 |
| 客户端 | 可选择下表的接入方式，也可独立使用 CLI。 |

Python 依赖在 `pyproject.toml` 声明，并用 `uv.lock` 锁定。需要创建运行环境时，uv 将它放到插件目录之外，首次缺少缓存时需要联网。完整包包含 Windows 原生模拟器依赖。

## 客户端接入

已发布版本的验收基线是 V1.0.0 的[重发提交 `f80f8d8`](https://github.com/savormundane/miliastra-wonderland-plugin/commit/f80f8d83e7f22e20900c823d288b72da078beb20)。桌面安装步骤与当前源码验证见下方。

| 入口 | 仓库提供的能力 | 验收状态与适用边界 |
| --- | --- | --- |
| Codex CLI | 从终端添加市场并安装插件。 | 已验证 Windows x64 本地市场安装和 MCP 工具调用。 |
| Codex 桌面端 | 登记市场后在插件目录安装。 | 当前源码已通过隔离桌面后端的本地市场发现与安装，以及从安装缓存发起的 stdio 查询。桌面图形界面操作待验。 [安装步骤](installation.md#codex-桌面端) |
| Claude Code | 从终端添加市场并安装插件。 | 安装清单已检查。客户端安装和 MCP 工具调用待验。 |
| Claude 桌面端 | 从「自定义 → 插件」添加仓库市场并安装。 | 已核对市场清单与本地 stdio 启动。Claude 桌面客户端的同步、安装及调用待验。 [安装步骤](installation.md#claude-桌面端) |
| DeepSeek Harness | 从 GitHub 直接安装 Cordis Bundle。 | 安装清单已检查。GitHub 直装、Bundle 加载和节点查询待验。 |
| Agent Plugins | 提供通用插件清单、Skills 和本地 stdio MCP 配置。 | 导入方式和本地工具可用性取决于客户端的实现。 |
| 独立 CLI | 使用专用 Python 运行 `scripts/qianxing.py`。 | 不依赖 AI 客户端；具体命令仍需相应运行依赖和有效输入。 |

具体安装和导入操作集中在[安装指南](installation.md)，无需为同一个任务同时安装多个客户端。

平台资料、API、节点和内置资源查询无需工程目录。文件工具从客户端会话或[工程绑定](runtime-environment.md#连接-mcp-或切换工程)获取目录，写入时使用独立输出目录。可用 `doctor` 检查连接和目录来源。

重发版的千星奇域编辑器导入和游戏内运行待对应产物实测，详见[验证分层](#验证分层)。

## 平台与制作范围

四个 Skill 为 Qianxing Editor、Qianxing Graph Code、Qianxing GIL 和 Qianxing Assets。Client Lua 由 [Qianxing Editor](../skills/qianxing-editor/SKILL.md#client-lua) 提供。平台规则和文档查询应指定目标千星奇域版本；已收录资料、已实现的文件操作和实际游戏行为分别判断，不能将插件版本号当作千星奇域版本号。

要了解某个对象能做什么，先查[能力与资料索引](../references/README.md)，或让助手调用 `capabilities`。已有 GIL 的局部修改以已校准操作为范围；不把未知字段推断成可写字段。

## 验证分层

1. **静态检查**。解析语法和文件结构，核对已支持的字段、端口、API 签名及素材预算。
2. **离线模型与预览**。在本机运行已覆盖的 Lua、节点逻辑或软件渲染，检查模型行为和参考图。
3. **千星奇域编辑器导入**。实际打开产物，核对对象、挂载和脚本映射，并按需要保存再回读。
4. **游戏内运行**。在实际游戏里验证目标设备输入、渲染、多人同步和真实存档重进。
5. **试玩验收**。由创作者或试玩者确认手感与玩法是否达到制作目标。

每项结果适用于当次实际检查的输入和环节。这些层级用来解释结果，不是每次修改都要完成的全套流程。按实际改动和使用目标选择必要检查，遇到问题时优先检查出错环节。[详细验证说明](../references/validation.md)

## 报告状态

- `passed` 表示当前输入和范围内已执行并通过。
- `failed` 表示已执行，发现错误。
- `not_checked` 表示尚未执行或工具无法覆盖。
- `not_applicable` 表示该项与当前输入或工作流无关。
