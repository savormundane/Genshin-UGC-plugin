# 工具导航

终端入口为 [qianxing.py](qianxing.py)。[mcp_launcher.cjs](mcp_launcher.cjs) 启动同一份 CLI，MCP 的服务、任务转发和工程绑定在 [miliastra/mcp](miliastra/mcp)。MCP 工作进程的入口在 [mcp_worker.py](mcp_worker.py)。[MCP 接入与参数](../docs/mcp.md)

| 任务 | CLI | 核心源码 |
| --- | --- | --- |
| 查询节点、平台与 Lua API | `nodes`、`docs`、`platform`、`knowledge` | [node_build.py](node_build.py)、[platform_profiles.py](platform_profiles.py)、[knowledge.py](knowledge.py) |
| 阅读工程和定位对象 | `project`、`resources`、`ids` | [project_index.py](project_index.py)、[resource_catalogue.py](resource_catalogue.py)、[id_registry.py](id_registry.py) |
| 编译节点图 | `build` | [node_build.py](node_build.py)、[ayaya_bridge.py](ayaya_bridge.py) |
| 维护已校准的节点规则 | `nodes`、`graph check` | [版本证据](node-contracts.json)、[规则加载](node_contracts.py) |
| 修改和回读 GIL/GIA | `native`、`level` | [miliastra/native](miliastra/native)、[level_authoring.py](level_authoring.py) |
| 装配和静态检查 Lua | `client` | [miliastra/client](miliastra/client) |
| 转换和检查素材 | `assets` | [miliastra/assets](miliastra/assets)、[矩形 GIA 封装](miliastra/native/assets.py) |
| 生成存储合同 | `storage` | [storage.py](miliastra/storage.py)、[Schema 3 适配器](miliastra/storage_v3.py) |
| 整合与核验交付 | `produce`、`verify` | [制作阶段](miliastra/production.py)、[制作入口与共享阶段](production_core.py)、[交付验证](delivery_verify.py) |
| 排障与本地模拟 | `diagnose`、`logs`、`simulate`、`beyond` | [project_diagnosis.py](project_diagnosis.py)、[joint_simulator.py](joint_simulator.py)、[beyond_backend.py](beyond_backend.py) |

用 `capabilities` 查看功能及各层验证状态，用 `doctor` 检查当前依赖。[能力与验证结果](../references/workflows/validation-evidence.md)

已有工程工具可继续通过 `asset_pipeline.py`、`asset_core.py` 和 `client_check.py` 调用对应实现。插件内部直接从 `miliastra` 导入。

[配置开发环境和运行检查](../docs/contributing/development.md) · [打包与发布](../docs/contributing/maintenance.md)
