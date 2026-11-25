# 原生玩法制作

用 GIL 交付可以继续在编辑器中修改的物件、规则、职业、技能、经济和界面。Editor 选定对象及配置，Graph Code 编译事件与行为，GIL 维护身份、引用和文件交付。所述新增场景制作范围为 7.2 超限模式。

## 组织一次工程修改

1. 从目标模式的副本开始。用 `project inspect LEVEL.gil --scope scene` 确认实例、元件和图，用 `scene inspect LEVEL.gil` 查看预设点、地形和环境。通过 `nodes_lookup` 确认事件、节点作用域和参数。
2. 把下面的操作写进 schema 2 补丁。用 `native plan` 审阅生成的身份、变化和基底摘要，再用 `native apply --plan` 另存。MCP 使用同样的操作数据。创建顺序有依赖时，把被引用对象的操作放在前面。 [原生修改合同](../gil/native-changes.md)
3. 用 schema 2 的 `build` 编译 Graph Code，`mounts` 按图名和工程对象 ID 挂普通服务端图。用 `produce` 一次交付最终 GIL、场景和图源码。需要引用本次编译图的技能可以在 `native.after_graphs` 阶段登记。 [制作链](../workflows/produce.md)

在模板或实例作用域中使用真实 ID。输入 `entity_key` 可引用同补丁中生成的一只普通实例，`template_key` 可引用同补丁中生成的元件。`produce` 的构建挂载也接受先前放置操作报告中的 `entity_key`。图内写死的 GUID 继续引用原对象。用于复用的机关图可以通过「获取自身实体」指定运行实例。 [场景制作](native-scene.md)

## 角色、造物、战斗

| 操作 | 写入内容 | 顶层字段 |
| --- | --- | --- |
| `set_native_class` | 用 `class_id` 选择已有职业。按需给 `attributes` 中的 `health`、`attack`、`defence`、`stamina`，或给 `movement` 中的 `jump`、`sprint`、`climb`、`glide`。用明确的 `layout_id`、`camera_id` 关联现有资源。 | 15 |
| `native_skill` | `name` 和 `graph` 创建瞬发角色技能。图以 ID 或唯一名称选择，角色技能图使用客户端作用域。可给已规划的 `skill_id` 供服务端图绑定。给定同关卡 `creature_skill_witness` 时，生成沿用其模型和动画轨道的造物技能，图须为造物技能类别。 | 6、15、16 |
| `native_creature_graph` | `kind: "skill"` 和 `source_graph` 将已编译的「开始 → 通知服务器」图用于造物技能。先用 `kind: "status"` 与 `skill_slot` 创建执行指定技能序号的状态图，再用 `kind: "decision"` 与 `status_graph` 创建进入该状态的决策图。每项给 `name`。 | 6、10 |
| `set_creature_skill_set` | 给已有配套组件的造物 `template_id` 配置 `decision_graph`、同模型的 `skills` 和可选 `cooldown_seconds`。序号按技能列表从 1 排列。 | 4 |
| `native_combat` | 在 `section`、`entity_id` 上添加 `attack:{name,coefficient,added_damage}` 或 `hurtbox:{size_m,offset_m,health}`。攻击为直接攻击，受击盒为本地 XYZ 米制盒形。已有受击盒需另行保留和选择。 | 4 或 5 |
| `native_unit_status` | 用 `name` 新建可由节点施加的单位状态。效果选 `outline:"green"`、`outline:"white"` 或 `speed_percent`。可给 `status_id`、`stack_limit`。 | 6、15、16 |
| `set_native_faction_relations` | `faction_id`、`hostile_to` 设置一个已有阵营对其它阵营的关系。运行时可通过角色创建事件、玩家序号和「修改实体阵营」安排队伍。 | 11 |

角色模板上的「实体创建时」可用「添加角色技能」将已登记的技能配置 ID 放入 `技能1-E` 等槽位。技能图调用「通知服务器节点图」，角色模板上的「技能节点调用时」接收参数。攻击者须配置同名能力单元。对已有受击盒和生命配置的目标发起攻击后，在目标图的「受到攻击时」更新可见性或状态。已有 Graph Code 的布尔和整数筛选类别仍可通过构建描述中的 `category` 选择。 [职业](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhodlcrpht3q) · [角色技能](https://act.mihoyo.com/ys/ugc/tutorial/detail/mho81frl33im) · [服务端执行节点](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhw66orrrfkm)

## 经济与原生界面

- `economy_config` 的 `resources` 按依赖顺序填写 `currency`、`item`、`backpack`、`shop`。每项有 `key`、可选 `name`。用 `resource_id` 更新已登记的同类型资源。道具可写 `icon_id`、`max_stack`、`description`，背包可写 `capacity`。商店 `sell`、`buy` 条目用 `item`、`currency`、`price`，出售项可设 `stock`。引用使用原生 ID 或在本操作里已经声明的键。创建操作需允许字段 6、15。 [道具](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhbgx0rspbqu) · [商店](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhi9s7isvp50)
- `native_economy_binding` 把 `kind:"backpack"` 或 `kind:"shop"` 连到指定模板或动态实例，写入对应字段 4 或 5。背包可给 `holdings:[{resource_id,amount}]`。使用 `create_native_drop` 从同关卡普通模板 `source_template_id` 制作 `item_id` 的拾取模板，可设 `amount`、`pickup_size_m`。之后用 `kind:"loot"`、`drop_template_id` 和道具 `holdings` 绑定战利品。若该模板在同一补丁中带 `key` 创建，填写 `drop_template_key`。创建拾取模板需要字段 4、6。
- `add_native_variables` 在 `template_id` 声明整数、布尔、浮点、字符串默认值，供节点图和界面绑定。 `add_native_global_timer` 用 `name`、`seconds` 和可选 `countdown` 创建计时器，`section` 与 `entity_id` 选玩家模板或关卡实体。用「启动全局计时器」启动。写入字段 12 与持有者所在字段。
- `native_hud` 用 `controls` 写文字、交互按钮、进度条、计时器、计分板到原生布局。每项提供 `name`、`kind`、`position_px`、`size_px`，使用 1600×900 中心坐标，Y 向上。可给 `group_name` 建立原生控件组，`layout_id` 选择布局，`player_template_id` 选择绑定变量的玩家模板。写入字段 9。用 `set_native_hud_control` 按 `template_id` 修改现有控件及对应副本的位置、尺寸、文字、名称或初始可见性。 [原生界面布局](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhozt0r74ng6)

| 控件 `kind` | 专用参数与行为 |
| --- | --- |
| `text` | `text`，可选 `font_size`。 |
| `button` | 可选 `key_index`，默认 1。在玩家模板监听「界面控件组触发时」。独立按钮使用 `control_id`，组内按钮使用操作返回的 `group_id`。 |
| `progress` | `current`、`minimum`、`maximum` 均填写玩家模板已声明的整数变量名称。 |
| `timer` | `timer` 填写已有全局计时器名称。 |
| `scoreboard` | `variable` 填写玩家整数变量，`player_count` 指定显示的玩家槽数。 |

原生经济的制作路径是进入范围后让 Graph Code 修改角色背包的货币，再由玩家图打开指定商店。兑换条件和库存来自原生商店记录。可用控制组按钮或角色触发为玩家打开商店。

## 多人推进与存档

`set_native_player_group` 按 `group_id` 配置 `min_players`、`max_players`，范围须落在己方已保存的玩家槽内。`add_respawn_points` 用 `player_template_id` 和带 `point_id`、`name` 的 `points` 配置复苏点。可设 `initially_active`，或在踩到检查点后使用「激活复苏点」。写入范围分别为字段 11 以及字段 4、11。

`set_native_revive` 用 `player_template_id` 选择已有复苏设置，可改 `lives`、整数 `delay_seconds`、`automatic`、`show_screen`、`health_percent` 和 `fall_loss_percent`。所选字段写到玩家模板所在字段 4。角色的复苏、倒下和异常掉落事件可继续由业务图处理。

配置 `storage:{spec,transport:"server",host_section:4}` 生成原生存档槽、信号和图。在同一个玩家模板上挂载业务图。图发送的请求按信号来源玩家路由。收回包时再次选择玩家和请求号后更新个人状态。存档确认之后再推进合作目标和结算。schema 3 的同字段布局升级可配置 `compatible_record_version`，保留结构、槽位 ID 和字典，打开新会话时回写记录版本。 [服务端存档和迁移](../workflows/storage-authoring.md#原生服务端存档)

## 样本与覆盖范围

形状、职业技能、原生按钮和计分板字段以随包节点资料、官方模板及 8itlab 的原生记录研究核对。当前造物状态图写入覆盖单入口的决策、执行指定技能、以及通过技能向服务端发通知。复杂动画时间轴、重组任意造物决策、更多原生控件或模式须以实际记录校准。保存重进、匹配、伤害和控件显示以对应编辑器与游戏行为为准。 [8itlab 原生记录参考](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/scene-save.mjs)
