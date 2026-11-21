# 本地工具导航

这里是插件的工具实现。普通使用从[安装指南](../docs/installation.md)开始；修改工具时先看[仓库结构](../docs/contributing/architecture.md)。多数操作通过 `qianxing.py` 进入，不需要逐个运行模块文件。

## 入口与调用关系

| 入口 | 作用 |
| --- | --- |
| [qianxing.py](qianxing.py) | CLI 命令分发，供终端与 Agent 调用。 |
| [mcp_launcher.cjs](mcp_launcher.cjs) → [mcp_service.py](mcp_service.py) → [mcp_bridge.py](mcp_bridge.py) | 启动固定版本的 Python 环境，把 MCP 工具参数送入同一套本地核心。 |
| [capability_index.py](capability_index.py) | 五领域和共享工作流的归属登记。 |
| [capabilities.py](capabilities.py) | 已实现操作、支持范围和环境查询；实现存在不等于本轮执行通过。 |

下例从仓库根运行。实际功能使用安装时配置的专用 Python；各命令的输入文件和参数见对应指南。

```powershell
& '<专用 Python 的绝对路径>' .\scripts\qianxing.py --help
& '<专用 Python 的绝对路径>' .\scripts\qianxing.py capabilities
```

## 按任务找代码

| 任务 | CLI 命令族 | 主要模块 | 技术说明 |
| --- | --- | --- | --- |
| 查询节点、API、平台版本 | `nodes`、`knowledge`、`docs`、`platform` | [node_build.py](node_build.py)、[knowledge.py](knowledge.py)、[platform_profiles.py](platform_profiles.py) | [节点](../references/graph-authoring.md)、[知识来源](../references/knowledge-reliability.md)、[平台规则](../references/platform-profiles.md) |
| 索引工程与资源 | `project`、`resources`、`ids` | [project_index.py](project_index.py)、[resource_catalogue.py](resource_catalogue.py)、[id_registry.py](id_registry.py) | [工程索引](../references/project-index.md) |
| 编译节点图 | `build` | [node_build.py](node_build.py)、[ayaya_bridge.py](ayaya_bridge.py) | [节点图制作](../references/node-graph-workflow.md) |
| 查看、比较和修改原生文件 | `inspect`、`native`、`level` | [native_core.py](native_core.py)、[native_changes.py](native_changes.py)、[level_authoring.py](level_authoring.py)、[gil-toolkit.mjs](gil-toolkit.mjs) | [局部修改](../references/native-changes.md)、[结构生成](../references/native-authoring.md) |
| Lua 装配和静态检查 | `client` | [client_assembly.py](client_assembly.py)、[client_check.py](client_check.py)、[client_api.py](client_api.py)、[client_variables.py](client_variables.py) | [装配](../references/client-assembly.md)、[最终 Lua 检查](../references/client-check.md) |
| 图片拟合与图元处理 | `assets` | [asset_pipeline.py](asset_pipeline.py)、[asset_core.py](asset_core.py)、[asset_fit_v2.py](asset_fit_v2.py)、[native_assets.py](native_assets.py) | [素材生成](../references/asset-generation.md)、[拟合](../references/asset-fit.md) |
| 协议、存档与 UI 运行支持 | `storage`、`ui`，以及制作配置 | [storage_authoring.py](storage_authoring.py)、[protocol_codegen.py](protocol_codegen.py)、[native_ui.py](native_ui.py)、`runtime_*.lua` | [协议](../references/protocol-v2.md)、[存储](../references/storage-authoring.md)、[UI](../references/runtime-ui.md) |
| 多项能力整合交付 | `produce`、`verify`、`workflow` | [production_core.py](production_core.py)、[production_v2.py](production_v2.py)、[portable_delivery.py](portable_delivery.py)、[delivery_verify.py](delivery_verify.py) | [制作入口](../references/production-workflow.md)、[当前配置合同](../references/production-v2.md) |
| 定向排障和可选模型 | `diagnose`、`logs`、`simulate`、`beyond`、`experiment` | [project_diagnosis.py](project_diagnosis.py)、[client_simulator.py](client_simulator.py)、[joint_simulator.py](joint_simulator.py)、[beyond_backend.py](beyond_backend.py) | [排障](../references/debugging-workflow.md)、[模拟范围](../references/client-simulation.md) |

单点修改直接用对应命令。只有任务涉及多个产物时才需要制作链；软件模拟和预览按具体问题选择，不是每个命令的前置步骤。

## 安装、发布与检查

| 工作 | 入口 |
| --- | --- |
| 创建专用环境、绑定工程与输出目录 | [configure_runtime.py](configure_runtime.py)、[install_public.py](install_public.py)；用户入口在根 `install.ps1`。 |
| 从已提交源码准备发行候选 | [prepare_release.py](prepare_release.py) 调用 [package_release.py](package_release.py)；见[发布流程](../docs/contributing/maintenance.md)。 |
| 检查版本、清单和文档链接 | [check_repository.py](check_repository.py)。 |
| 仓库随附的定向回归 | [test_gil.mjs](test_gil.mjs)、[test_agent_protocols.py](test_agent_protocols.py)、[test_distribution.py](test_distribution.py)、[test_release.py](test_release.py)、[test_release_behaviors.py](test_release_behaviors.py)。按改动选择，见[开发指南](../docs/contributing/development.md)。 |

`validation-contract.json`、`capability-layers.json`、`test-impact.json` 还登记了维护者开发工作区的测试名称；其完整测试源码和 `run_validation.py` 当前没有随本公开仓库提供。不要把清单中的用例名当作本地可执行文件，也不要把历史证据当作本轮结果。[证据读取说明](../references/validation-evidence.md)

## 依赖和路径约定

Python 依赖来自 `runtime-requirements.lock`；Ayaya、Beyond 和 luaparse 的随包内容位于 `vendor/`。目录内模块共享相对导入和固定资源路径，调整文件位置应同时处理调用方。日常新增能力优先扩展所属模块，跨领域逻辑使用共享模块，具体游戏内容留在游戏工程。
