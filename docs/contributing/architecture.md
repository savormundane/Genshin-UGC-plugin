# 仓库结构与能力边界

Genshin-UGC 将千星奇域资料、Agent 工作方式和本地文件工具组织在同一个插件中。维护时先找到变化所属的工作对象，再更新对应实现和入口；不用为了新增一种玩法重新建一套目录。

## 先按读者找到入口

| 读者或任务 | 入口 | 内容放在哪里 |
| --- | --- | --- |
| 第一次了解和安装 | [README](../../README.md)、[使用文档](../README.md) | 项目价值、安装步骤、使用示例和常见问题放 `docs/`。 |
| Agent 接到创作任务 | [五领域路由](../../references/skill-map.md) | `skills/` 选择工作领域，`references/` 提供按需读取的技术资料。 |
| 开发者修改工具 | [脚本导航](../../scripts/README.md) | `scripts/` 的 CLI、MCP 和共用实现。 |
| 维护者整理方向和发布 | [贡献入口](README.md)、[发布流程](maintenance.md) | 日常规则放 `docs/contributing/`，阶段审查与维护记录放 `docs/maintenance/`。 |

## 顶层目录的职责

| 目录或文件 | 用途与维护边界 |
| --- | --- |
| `skills/` | 工程、Graph Code、Client Lua、GIL、Assets 五个稳定入口。Skill 负责引导，不重复粘贴完整 API 文档。 |
| `docs/` | 给使用者和贡献者阅读的指南；避免混入每次运行产生的报告。 |
| `references/` | 技术指南、共享流程、平台资料和来源说明。`official/` 是资料快照，`platform/` 是版本补充；运行时会按登记的路径和摘要读取部分正文。 |
| `scripts/` | 统一入口 `qianxing.py`、MCP 适配和功能模块。现有相对导入与打包使用这些路径，目录导航优先于批量搬迁。 |
| `vendor/` | 随包第三方工具和固定依赖：Ayaya 用于节点及文件工具，Beyond 用于可选软件模拟，luaparse 用于 Lua 解析。保留各自的来源和摘要清单。 |
| `runtime/` | 当前仅保存 `res/lua_template.lua` 模板；并非安装后生成的 Python 虚拟环境。 |
| `assets/` | 插件图标与标识，不保存具体游戏的美术素材。 |
| `examples/` | 可以公开复用的中性输入、制作说明与真实示例产物；与个人游戏项目分开。 |
| `plugin.json`、`mcp.json` | 通用插件声明与 MCP 入口。 |
| `.codex-plugin/`、`.claude-plugin/`、`.mcp.json` | 客户端适配声明；与根清单共用五个 Skills 和本地工具。 |
| `install.ps1`、`distribution.json` | Windows 安装入口与发行文件筛选规则。 |
| `.github/` | Issue/PR 模板和手动检查工作流。 |

具体游戏源码、规则和素材留在各自的游戏项目中。提炼后的中性示例可以随文档提供，但不要把一个游戏的协议编号、角色名或数值变成插件默认值。

## 五个领域如何协作

| 领域 | 负责的对象 | 典型实现入口 |
| --- | --- | --- |
| 工程 / Editor | 实体、模板、组件规则、资源与版本关系 | `project`、`platform`、`docs`、`resources` |
| Graph Code | 客户端和服务端节点、端口、执行流、数据流、编译 | `nodes`、`build` |
| Client Lua | 控件 API、输入、生命周期、脚本装配 | `knowledge api`、`client` |
| GIL | 容器、身份、挂载、局部修改与回读 | `native`、`level`、`inspect` |
| Assets | 图片、图元、颜色、转换与成本 | `assets` |

协议、存储、多人会话、诊断和制作链横跨多个领域，由共享模块提供。动画的运行逻辑归 Client Lua，素材转换归 Assets；它们不需要第六个 Skill。实际登记见 [capability_index.py](../../scripts/capability_index.py)，操作导航见 [scripts/README.md](../../scripts/README.md)。

## 2D 与原生 3D 的现状

五领域按平台对象划分，不按 2D/3D 划分。已有的节点图、实体索引和平台资料也能辅助原生 3D 玩法；但“查到接口”“检查配置”和“生成完整场景”具有不同范围。

| 工作 | 当前范围与依据 |
| --- | --- |
| 查运动器、镜头、碰撞等资料并设计节点逻辑 | [官方资料索引](../../references/official-index.md)、[平台版本目录](../../references/platform-profiles.md)和节点目录已有相关基础。 |
| 检查显式声明的组件配置 | [平台规则](../../references/platform-profiles.md)覆盖已登记的运动器组合、镜头接管、碰撞和扰动装置等规则；一般不等于这些组件已写入最终 GIL。 |
| 创建新 GIL 基底与客户端界面 | [结构生成](../../references/native-authoring.md)支持校准的地图配置、脚本映射和有限 UI 模板；当前地图范围为 1–20 格，不是任意地形或完整 3D 关卡生成器。 |
| 将 GIA 图元转换为客户端素材 | [原生素材导入](../../references/native-assets.md)支持特定投影的矩形与显式深度层，不包含任意空间旋转或通用 3D 模型导入。 |

后续 3D 能力应逐项扩展已有工程、节点和 GIL 工具，让明确的实体、组件和场景操作可以落地。完成了哪一种对象的操作，就公开说明哪一种，不用“完整支持 3D”概括局部能力。

## 修改应放在哪里

用户操作说明改 `docs/`；Agent 的技术路线改 `references/`；领域发现和任务分工改对应 `SKILL.md`；工具行为改 `scripts/`。更新平台原文或 API 正文时，同时核对来源登记与摘要，不能仅修改展示文字。

`vendor/beyond/node_modules/` 是随包 Windows 模拟器的固定依赖子集。Python 依赖由安装器按锁文件建立独立环境。ZIP、虚拟环境和日常运行报告放在仓库外；经过整理的公共示例产物随 `examples/` 保存。`.gitattributes` 保留文件字节，包括已有换行；不要在整理目录时顺带统一全部文件格式。[运行环境](../runtime-environment.md) · [第三方声明](../../THIRD_PARTY_NOTICES.md)

检查按实际影响选择，见[开发指南](development.md)。文档导航调整不需要触发完整安装、模拟器或游戏宿主回归。
