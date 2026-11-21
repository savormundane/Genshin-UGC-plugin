# 项目结构

公开仓库提供插件源码、固定依赖、使用文档和贡献者可运行的检查。提交复现时使用可公开的最小输入。个人工程、安装缓存、运行配置和维护记录保存在本机。

| 目录 | 负责什么 |
| --- | --- |
| `skills/` | Agent 的五个技术领域入口。 |
| `references/` | 领域技术说明、共享流程、平台资料与来源。 |
| `scripts/` | CLI、MCP、生成和检查工具。[按任务找代码](../../scripts/README.md) |
| `runtime/` | 随源码交付的运行模板。 |
| `vendor/` | 固定版本的 Ayaya、Beyond 和 Lua 解析器。[第三方声明](../../THIRD_PARTY_NOTICES.md) |
| `docs/` | 安装、使用和开发者文档。 |
| `.github/` | Issue、PR 模板与手动检查。 |

## 工具与领域

`scripts/qianxing.py` 是 CLI 入口。MCP 的启动器读取本机运行配置，stdio 工具把参数交给同一套核心模块。具体操作以[工具导航](../../scripts/README.md)和[本地 MCP 合同](../../references/local-mcp.md)为准。

五个 Skill 按平台对象划分。工程检查负责实体、组件和引用，Graph Code 负责节点逻辑，Client Lua 负责脚本和控件，GIL 负责文件解析和写回，Assets 负责素材转换。协议、多人、存储和诊断共用工具。[领域能力索引](../../references/skill-map.md)

2D 界面与原生 3D 共用对象身份、引用、节点和交付工具。当前原生写入以已校准的容器、图、脚本、局部字段和图元为范围。运动器、镜头和碰撞的声明规则可用于设计检查。更多原生创作能力见[开发路线](../../ROADMAP.md)。

## 修改入口

改体验与命令示例时从 `docs/` 开始。改工具时同时核对它的 CLI、MCP、Skill 和包内相对路径。更新平台原文或 API 时，核对来源登记与摘要。[知识来源](../../references/knowledge-reliability.md)

插件清单和 `install.ps1` 定义客户端接入。`distribution.json` 定义打包范围。正式 ZIP 从清洁的 Git 提交导出。[打包与发布](maintenance.md)
