# 工程架构

Miliastra Wonderland 将千星奇域创作中的资料检索、工程检查、编辑计划、构建和验证接到本地工具。四个 Skill 是任务指引，CLI 和 MCP 是两种调用入口，工程操作由同一套领域实现处理。 [用户入口](../../README.md) · [工具导航](../../scripts/README.md)

## 从请求到产物

| 层级 | 职责 | 入口 |
| --- | --- | --- |
| 任务指引 | Editor 负责平台语义、工程定位、界面和 Client Lua。Graph Code 负责节点图。GIL 负责容器检查和编辑。Assets 负责素材与资源。 | [四个 Skill](../../skills/) · [任务流程](../../references/README.md) |
| 客户端接入 | 各客户端清单启动同一个 Node 启动器。启动器核对本机解释器和依赖，用 CLI 的 MCP 入口启动 stdio 服务 | [启动器](../../scripts/mcp_launcher.cjs) · [CLI](../../scripts/qianxing.py) · [部署说明](../installation.md) |
| MCP 请求 | 服务定义参数和结果。会话绑定确定工程根和输出根，转发层处理路径、输入校验值和时限，独立工作进程执行已登记的操作 | [服务与工作区](../../scripts/miliastra/mcp/) · [工作进程](../../scripts/mcp_worker.py) · [工具约定](../mcp.md) |
| 领域实现 | 源码、素材、关卡和平台资料分别由所属领域处理。终端命令及 MCP 的单项工具可直接调用这些实现 | [实现索引](../../scripts/README.md) |
| 组合与交付 | `produce` 顺序装配任务配置中声明的阶段，由各阶段生成或校验产物。共享 I/O 逻辑跟踪输入，输出经过检查后再提交到指定位置。便携重建另核对包内原始输入、运行环境与授权校验值 | [组合制作](../../references/workflows/produce.md) · [便携交付](../../references/workflows/portable-delivery.md) |

项目配置引用具体文件、对象和要执行的阶段。只查资料、检查 Lua 或试算图片时，使用对应工具即可。多阶段任务需要共用本轮生成的 GIL、资源映射或交付清单时，才使用组合制作。输入文件保留，修改计划、另存和读回核对分别承担定位、写入与验收职责。 [审阅并另存 GIL](../../references/gil/native-changes.md)

工程处理与组合制作直接复用领域入口。协议字段和类型在 `protocol_types.py` 校验，GIL Lua 写回复用 `level_authoring.py` 的容器编码，API 文本与结构化查询由 `knowledge.py` 提供。现有工程使用的旧导入入口继续可用。 [源码定位](../../scripts/README.md)

## 随插件运行的上游能力

| 上游 | 当前集成边界 | 插件承担的工作 |
| --- | --- | --- |
| Ayaya | 固定版本的无界面编译器、节点实现和必要的格式样本 | 节点知识和版本校准、绑定与工程暂存、GIA/GIL 写回范围、受保护字段和读回核对 |
| Beyond | 随包 Lua 执行、信号和控件会话，经 Canvas 2D 生成软件画面 | 选择最终 GIL 和绑定的 Lua、控制预览输入和检查条件、返回截图、执行状态与诊断 |
| luaparse | Lua AST 解析器 | 客户端 API 检查、引用定位、脚本装配和本地诊断 |

Graph Code 通过固定的编译入口读取随包 Ayaya 源码。每次构建使用独立的工程暂存目录，模型、GIA、GIL 与信号模板缓存归当前作业。插件在读取产物后核对节点、声明、连接及保护字段。节点定义和原生样本仍是编译及格式依据。 [编译适配器](../../scripts/ayaya_bridge.py) · [节点图工作流](../../references/graph-code/node-graph-workflow.md)

Beyond 默认从包内预览进程调用无界面实现。浏览器绘图库和独立上游应用已从当前分发移除。常规 Windows ZIP 随包携带锁定的 Canvas 文件，Git 和 Cordis 安装按锁下载后复用缓存。插件的 Lua 模型和联合模型用于验证已声明、已覆盖的项目逻辑。模拟报告须说明使用的模型。 [Beyond 预览](../../references/workflows/beyond-backend.md) · [联合模拟](../../references/workflows/joint-simulation.md) · [第三方声明](../../THIRD_PARTY_NOTICES.md)

## 平台事实与设计边界

- **规则来源**。千星奇域的版本规则来自对应版本的官方正文。编译器定义用于说明编译器接受的节点和类型。逆向得到的写入规则绑定可复验样本、容器家族、对象和字段。工作流先检查证据，有歧义时保留诊断。 [来源判断](../../references/platform/knowledge-reliability.md)
- **扩展方式**。可独立使用的能力落在所属领域，已有操作可经 CLI 和 MCP 共用。项目专有玩法、协议字段和资源留在项目配置。跨阶段调度由制作入口处理，避免领域实现依赖总调度。
- **验证结论**。检查源码或文件、执行模型、生成软件预览、编辑器导入和游戏内运行分别留证。观察实验是可运行的本地工具，实验结果只覆盖所用输入和模型。 [验证层级](../compatibility.md#验证分层) · [通用算法与观察实验](../../references/workflows/algorithms-experiments.md)
- **兼容与变更**。已弃用的配置仍按现有实现读取，退出计划记录在开发指南。计划、旧发行与本机安装各有独立记录。上游版本更新须重新验证引用、产物和授权范围。 [旧配置的退出版本](development.md#旧配置的退出版本) · [上游更新与发行](maintenance.md)

[本地开发与检查](development.md) · [平台资料维护](platform-maintenance.md)
