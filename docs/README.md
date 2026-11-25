# 使用文档

[插件首页](../README.md) · [中文任务教程](../samples/creator-demos/README.md) · [技术参考](../references/README.md)

| 想做什么 | 入口 |
| --- | --- |
| 安装、更新、卸载或排查启动问题 | [安装指南](installation.md) |
| 核对 Windows 依赖和客户端协议 | [运行要求](compatibility.md) |
| 绑定本地工程和输出目录，或单独运行 CLI | [运行环境](runtime-environment.md) |
| 查看 MCP 参数、摘要和文件路径规则 | [MCP 工具](mcp.md) |
| 核对平台资料、文件格式和支持范围 | [来源判断](../references/platform/knowledge-reliability.md) · [验证分层](compatibility.md#验证分层) |
| 修改源码、维护平台资料或参与发行 | [参与贡献](../CONTRIBUTING.md) |

## 使用产物

从助手返回的文件路径打开产物。需要选择保存位置时，见[工程与输出绑定](runtime-environment.md#连接-mcp-或切换工程)。

- **关卡与节点图**。导入另存的 GIL 并核对改动。独立 GIA 按资源类型导入后挂到目标对象。[关卡复核](../references/gil/native-changes.md#人工再导出核对) · [图制作与回写](../references/graph-code/node-graph-workflow.md)
- **Lua 与图元素材**。根据交付说明将 Lua 挂到对应控件，按预算和预览核对图元素材。[Lua 接入](../references/editor/lua/client-assembly.md) · [图片转图元](../references/assets/image-to-primitives.md)

## 仓库目录

| 目录 | 内容 |
| --- | --- |
| `docs/` | 用户指南、贡献者文档以及 DSH 客户端使用的中英文详情。 |
| [samples/](../samples/) | 创作者教程、公开样例及可复现的输入输出。 |
| [references/](../references/) | 平台原文、API 和格式参考，以及跨工具制作流程。 |
| [skills/](../skills/) | 编辑器、节点图、GIL 和素材四个 Skill 的任务指引。 |
| [scripts/](../scripts/) | MCP、CLI 和实现模块。两种入口复用相同的处理逻辑。 |
| [vendor/](../vendor/) | 随包运行的编译和预览依赖。锁定版本、许可与来源见[第三方声明](../THIRD_PARTY_NOTICES.md)。 |
| [assets/](../assets/) 和 [locale/](../locale/) | 插件图标与客户端语言资源。 |

根目录存放各客户端的插件清单、MCP 配置、依赖锁和安装器。[定版与发行](contributing/maintenance.md)
