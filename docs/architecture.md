# 项目结构与职责边界

Genshin-UGC 是面向千星奇域的插件与本地工具链，不是官方编辑器或游戏运行时。

| 目录 / 文件 | 职责 |
| --- | --- |
| `skills/` | 按 Editor、Graph Code、Client Lua、GIL、Assets 能力域组织的 Agent 入口 |
| `references/` | 面向 Agent 的平台知识、规范、工作流与证据边界 |
| `scripts/` | CLI、MCP 服务、文件处理、运行编排与检查工具 |
| `vendor/` | 当前随源码维护的第三方代码及依赖子集 |
| `runtime/` | 发行工具依赖的辅助运行时和可执行资源 |
| `assets/` | 插件展示图标和标识 |
| `.codex-plugin/`、`.claude-plugin/` | 各客户端的插件适配声明 |
| `plugin.json`、`mcp.json` | 根插件元数据与 MCP 配置 |
| `install.ps1` | Windows 完整安装入口 |

不同能力域共享底层规则与工具。多人会话、存储、协议、诊断、版本与交付不是因为某个具体玩法而产生的独立 Skill，修改时应保持这条边界。

**源码、运行依赖、安装包是不同概念。** 当前仓库仍保留随包依赖与辅助二进制，不能在没有构建及安装回归的情况下直接移动或删除。后续可评估可重复构建、按需安装依赖，以及 Release 与源码树的分离。

更细的内部路由与设计依据见 [能力路由](../references/skill-map.md)和[维护指南](../references/architecture-maintenance.md)。

`vendor/beyond/node_modules/` 是已记录版本与文件摘要的 Windows 模拟器分发依赖，不是普通开发缓存；不要直接 `npm install` 覆盖这份子集。`runtime/GE_IMG_Tool.exe` 是已有工具链所用的辅助程序。当前两者继续随 Git 和完整 ZIP 保留，Python 环境则由安装器按锁文件单独建立。原始上游资料中“工具不随包发布”的表述描述其原包，本仓库的实际分发以当前树与完整 ZIP 为准。

构建出的 ZIP、校验文件和运行环境留在仓库外，通过 Release 分发。拆分二进制或改用 Git LFS 需要同步解决锁定下载、摘要、离线安装和恢复；当前不为缩小目录而增加这些安装条件，也不重写历史。新增本地 `node_modules/` 与缓存由 `.gitignore` 排除，已有随包模拟器依赖保留例外。
