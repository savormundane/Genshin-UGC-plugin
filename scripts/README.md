# 工具导航

终端从 [qianxing.py](qianxing.py) 进入。MCP 通过 [mcp_launcher.cjs](mcp_launcher.cjs)、[mcp_service.py](mcp_service.py) 和 [mcp_bridge.py](mcp_bridge.py) 调用同一套核心。[MCP 接入与参数](../references/local-mcp.md)

| 任务 | CLI | 核心源码 |
| --- | --- | --- |
| 查询节点、平台与 Lua API | `nodes`、`docs`、`platform`、`knowledge` | [node_build.py](node_build.py)、[platform_profiles.py](platform_profiles.py)、[knowledge.py](knowledge.py) |
| 阅读工程和定位对象 | `project`、`resources`、`ids` | [project_index.py](project_index.py)、[resource_catalogue.py](resource_catalogue.py)、[id_registry.py](id_registry.py) |
| 编译节点图 | `build` | [node_build.py](node_build.py)、[ayaya_bridge.py](ayaya_bridge.py) |
| 修改和回读 GIL/GIA | `native`、`level` | [native_core.py](native_core.py)、[native_changes.py](native_changes.py)、[level_authoring.py](level_authoring.py) |
| 装配和静态检查 Lua | `client` | [client_assembly.py](client_assembly.py)、[client_check.py](client_check.py)、[client_api.py](client_api.py) |
| 转换和检查素材 | `assets` | [asset_pipeline.py](asset_pipeline.py)、[asset_fit_v2.py](asset_fit_v2.py)、[native_assets.py](native_assets.py) |
| 整合与核验交付 | `produce`、`verify` | [production_core.py](production_core.py)、[production_v2.py](production_v2.py)、[portable_delivery.py](portable_delivery.py)、[delivery_verify.py](delivery_verify.py) |
| 排障与本地模拟 | `diagnose`、`logs`、`simulate`、`beyond` | [project_diagnosis.py](project_diagnosis.py)、[joint_simulator.py](joint_simulator.py)、[beyond_backend.py](beyond_backend.py) |

`capabilities` 查看实现范围及验证层，`doctor` 检查当前依赖。[能力与验证结果](../references/validation-evidence.md)

[配置开发环境和运行检查](../docs/contributing/development.md) · [打包与发布](../docs/contributing/maintenance.md)
