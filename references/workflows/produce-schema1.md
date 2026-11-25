# Schema 1 制作配置

顶层 `produce` schema 1 任务从 V1.2.0 起列为弃用，计划在 V2.0.0 移除该入口。迁移时按 [Schema 2 制作指南](produce.md)调整任务和 GIL 映射。任务内的协议、动画和关卡配置各自使用对应指南的 schema。

schema 2的装配、原生修改、存储、联合模型与独立重建见 [可执行制作](produce.md)。下文保留schema 1的接口与兼容行为，新增复杂协议见 [协议schema 2](protocol-v2.md)。

Schema 1 配置通过 `qianxing.py produce` 执行。下列示例使用随包的 Lua 装配、素材和原生文件工具。

## 统一入口

```text
python scripts/qianxing.py api SetVisible
python scripts/qianxing.py produce production.json --out NEW_DIRECTORY
```

api直接检索完整客户端API，返回章节、行号、上下文和文档摘要，不编造同名接口。produce按客户端源码→level结构生成→素材→协议→动画→图构建→Lua写回顺序工作，记录所有输入和产物摘要；失败不提交最终目录，原始文件只读，输出必须为新目录。没有任意shell执行或自动安装依赖。

```json
{
  "schema": 1,
  "client": {"source": "client.lua"},
  "protocol": {
    "schema": 1,
    "signals": [{"name": "request_action", "direction": "client_to_server", "fields": [{"name": "choice", "type": "integer"}], "phases": ["ready"]}]
  },
  "animation": {"frames": [{"asset": "frame/asset.json", "duration": 0.1, "anchor": [0, 0]}], "max_controls": 100},
  "graphs": {"spec": "build.json"},
  "gil": {"use_graph_output": true, "mapping": "actual_mapping.lua"}
}
```

各阶段按需出现，至少一个。相对路径以production.json所在目录为基准；graphs.spec内部路径按其自身目录解析。gil可以消费显式图构建输出，或使用base指定当前GIL；两者不能同时指定。配置level且未指定base时，可使用本轮生成/整合的level.gil。gil.source可另给Lua，省略时使用client.source。示例信号是新设计示例，映射名称必须从当前文件读取，不能直接假定存在。produce整合已经编写的源码及合同，不是自然语言玩法生成器；Agent负责先按需求写出实际图/客户端/绑定适配。

## level生成与安全重跑

可添加 `"level": {"spec": "LEVEL.json"}`，先按 [原生生成](../gil/native-authoring.md) 创建平台结构、UI模板、脚本映射与挂载。graphs.spec没有base_gil时自动消费本轮基底；显式已有base_gil仍按当前合同使用，不擅自合并两个关卡。

脚本项的templates_as按本次GUID建立局部别名表，produce同时输出template_indices.lua；最终Lua写回保留相同绑定。输入源码不修改，生成目录记录实际摘要。创建脚本/UI关联不等于自动完成任意服务器图挂载。

默认输出必须不存在；--next选择新编号目录并在报告记录output_directory，不删除旧输出。至少包含一个实际阶段，只有level也可创建结构产物；结构生成不能被描述为完整玩法或已通过宿主验收。

## 客户端与协议

输出runtime.lua为独立Lua 5.3支持模块：scope按逆序释放清理回调且可重复关闭；dirty只在值变化且写入成功后更新缓存。由Agent把这些函数接到真实生命周期和控件API，不替代宿主的OnInit/OnUpdate/OnDestroy约定。

协议合同用有序fields，支持integer（有符号32位）、number、boolean和带可选UTF-8字节长度上限的string，拒绝重复信号/参数和未知字段。direction支持client_to_server、server_to_client、server_local。结构体、实体及列表通信保留原本图/样本链路，不假装标量校验器已覆盖所有平台类型。

runtime.protocol(contract,session,round)的accept(source,direction,phase,packet)核对信号、方向、阶段、会话/回合、正整数sequence、payload数量及类型，按可信source和信号拒绝重复/旧序号。source必须由真实传输层确认，不能用包中自报席位当认证；forget用于玩家生命周期清理。该策略适合顺序命令；允许乱序的快照/多通道协议应单独设计，不能直接套用丢旧包规则。

默认保留protocol.lua/json兼容输出。显式设置protocol_native=true后，同一合同生成原生信号资源、wire.json和client_bridge.lua；若同时构建图，资源自动合并入project_resources并启用signals写回，独立回读GIL注册参数的名称、类型和顺序。业务图仍由Agent编写，端到端检查不代替宿主权限或实际网络验收。

## 动画

消费内置素材的asset.json，检查格式、尺寸、矩形边界/调色板或文本块字段，拒绝混合矩形/富文本帧；计算最大帧控件池和总预算，输出animation.lua/json。每帧带duration、anchor及静态数据，所有数据内联，不在运行时读外部文件。

runtime.player(animation,draw,loop)按真实dt选择当前帧，跨帧时调用draw，支持循环和reset；不逐帧重建控件。runtime.rectangles(frame,scale,mirror,emit,hide,pool)计算锚点坐标、镜像、尺寸和调色板颜色，发给emit并隐藏池尾。emit/hide必须由Agent绑定实际控件方法，文本/分层骨骼仍按对应工作流接入；该模块没有把缺失素材变成已有动作。

## 原生文件写回

produce中的Lua写回由Python原生实现，无需Node执行。仅支持已核验的20字节头+protobuf+4字节尾GIL；按唯一映射命中正文，保留其他脚本、未知字段、顺序及头部中间元数据，回读比较实际Lua。空代码、重复映射、损坏容器及已有输出拒绝。旧gil-toolkit.mjs继续作为兼容入口与独立交叉核验器，不删除有效能力。

图逻辑、实体/挂载和资源变更使用既有严格图构建或Agent编写的有依据补丁；Python Lua写回本身不会创建挂载，也不承诺所有GIA格式。图构建报告位于graphs/build-report.json，整合报告从图构建的required_mounts核验结果汇总挂载证据；未给绑定合同时标记not_checked及原因，不冒充通过。

## 边界与依赖

常规协议、API、动画数据和Lua文件写回只需Python标准库；素材生成需要Pillow。图编译仍需包内Ayaya后端；HTML排版可选Playwright/Chromium；高级拟合按当前分发实际资源使用。它们是后端与可选能力，不要求用户自行选择维护多个制作框架。不得移除许可证、把包内第三方源码冒充独立重写、或声明全部算法已无依赖。

运行时模块已执行Lua5.3独立行为回归；produce在可导入lupa.lua53时检查输出Lua语法，无解释器时标记not_checked。真实生命周期、传输身份、字体命中、帧时间、原生存档及编辑器仍按实际证据验收。没有宿主验证不妨碍完成源码与文件交付，也不能伪造通过。


## 素材阶段与同源协议

production.json可添加assets列表，每项包含name、source和可选options；options对应assets generate参数。动画帧asset使用@asset:name引用本轮素材，未知名称/预算失败使整合回滚。

protocol_native=true为明确选择。原生线上参数在业务字段前添加session_key:string、round_id:integer、sequence_id:integer，业务字段不可重名。客户端桥以官方ServerSignal/Add*/SendSignal和RegisterServerSignalHandler实现发送/监听；可信source与当前phase由调用方提供。旧项目不自动迁移已有线上合同，未选择该项继续原数据导出行为。

节点源码从同一wire.json及resources生成的定义读取名称与参数。图构建必须明确允许真实变更字段：已核验信号基础设施涉及6/10/11/35，不能自动扩大用户给定的allowed_top_level_fields。缺少许可直接拒绝并报告实际变更字段。

produce报告schema=2增加evidence，以passed/failed/not_checked/not_applicable表达各阶段；旧布尔字段作为兼容投影保留。失败通过ProductionError.production_evidence及CLI的JSON错误返回，不提交半成品目录。Lua语法检查仅编译不执行用户脚本；编辑器和宿主状态不能由离线数据推断。

当前已核验后端采用发送、监听、向服务器发送三类原生定义；独立检查三类定义引用、参数端口顺序和编号唯一性。可选第四类回包定义存在时一并检查；缺少该类并不自动推断宿主Lua回包已验收。实际客户端桥已通过Lua5.3下的官方API替身测试，仍需宿主确认传输对象与权限。

[原生结构生成与脚本关联](../gil/native-authoring.md) 提供level create/bind/inspect及produce --next；[客户端模型与自检](client-simulation.md) 提供真实Lua5.3逻辑模型、画布/模板诊断和客户端脚本日志开启步骤。
