# 项目结构

| 目录或文件 | 职责 |
| --- | --- |
| `skills/` | 工程检查、Graph Code、Client Lua、GIL 和素材五个领域的助手入口。 |
| `docs/` | 安装、使用和贡献指南。 |
| `references/` | 平台资料、API 正文、共享工作流和验证说明。 |
| `scripts/` | CLI、MCP、文件处理、制作和检查工具。 |
| `vendor/` | 随包第三方工具与运行依赖。 |
| `runtime/` | Lua 模板资源，当前为 `runtime/res/lua_template.lua`。 |
| `assets/` | 插件图标与标识。 |
| `plugin.json`、`mcp.json` | 根插件清单与本地 MCP 配置。 |
| `.codex-plugin/`、`.claude-plugin/` | 客户端适配清单。 |
| `install.ps1` | Windows 安装入口。 |

协议、存储、多人会话、诊断和交付流程由多个领域共用。工程检查的 Skill ID 仍为 `qianxing-editor`，节点逻辑和客户端执行分别归对应领域。[能力路由](../../references/skill-map.md)

`vendor/beyond/node_modules/` 是随包 Windows 模拟器的固定依赖子集。更新时同步核对来源、版本、摘要和运行结果。Python 运行环境由安装器按锁文件单独建立。生成的 ZIP 和虚拟环境放在仓库外。[运行环境](../runtime-environment.md) · [第三方声明](../../THIRD_PARTY_NOTICES.md)
