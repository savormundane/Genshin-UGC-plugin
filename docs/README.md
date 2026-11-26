# 文档目录

[插件首页](../README.md) · [中文任务教程](../samples/creator-demos/README.md) · [技术参考](../references/README.md)

## 安装和使用

| 想做什么 | 入口 |
| --- | --- |
| 安装、升级、卸载或做安装自检 | [安装指南](installation.md) |
| 核对操作系统、运行依赖和客户端协议 | [兼容性](compatibility.md) |
| 配置解释器、工程和输出目录 | [运行环境](runtime-environment.md) |
| 调用工具，查参数、路径和输出规则 | [MCP 工具](mcp.md) |
| 跟做资料查询、原型或已有工程任务 | [公开样例](../samples/README.md) · [创作者教程](../samples/creator-demos/README.md) |

## 使用产物

从工具结果中的保存位置打开交付。编辑器中的工作步骤按产物类型查对应指南。

- **关卡与节点图**。导入另存的 GIL，按修改摘要核对对象及引用。独立 GIA 导入后挂到目标对象。 [关卡复核](../references/gil/native-changes.md#人工再导出核对) · [图制作与写回](../references/graph-code/node-graph-workflow.md)
- **Lua 与图元素材**。按交付说明挂载脚本，核对控件、坐标和控件数，再对照预览检查效果。 [Lua 装配](../references/editor/lua/client-assembly.md) · [图片转图元](../references/assets/image-to-primitives.md)

## 开发与维护

| 想了解什么 | 入口 |
| --- | --- |
| 任务入口、源码分工与上游集成边界 | [工程架构](contributing/architecture.md) · [源码索引](../scripts/README.md) |
| 开发环境、当前检查与旧配置退出计划 | [本地开发](contributing/development.md) |
| 维护版本资料、API 合同和用例 | [平台资料维护](contributing/platform-maintenance.md) |
| 更新上游、检查成品和定版发行 | [维护与发行](contributing/maintenance.md) |
| 提交 Issue、样例或代码改动 | [参与贡献](../CONTRIBUTING.md) |

当前实现以源码和配置为准。正式发布的版本记录见 [CHANGELOG](../CHANGELOG.md)。原文、版本及第三方资料的归属见 [技术参考](../references/README.md) 和 [第三方声明](../THIRD_PARTY_NOTICES.md)。
