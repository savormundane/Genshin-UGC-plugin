# 原生 3D 场景

## 查找模型并搭建静态场景

使用专用 Python 运行命令。场景以千星奇域 7.2 超限模式为生成目标。源文件来自同版本、同模式的编辑器导出。选取小型布景中实际用到的原生物件并导出 GIA，或提供含这些静态物件的 GIL 副本。目录生成会核对物件、定位器和原生模板 ID；版本和模式由提供样本的人确认。

```text
python scripts/qianxing.py scene catalogue scene-sample.gia --version 7.2 --mode beyond --out models.json
python scripts/qianxing.py resources search 围墙 --type model --version 7.2 --mode beyond --catalogue models.json
```

也可调用 MCP `resources_lookup`。传入 `version`，按需给 `query`、`mode` 和项目中的 `catalogue`。结果中的 `selection` 用于选择资源。

| 值 | 用法 |
| --- | --- |
| `native_verified` | 在关联的原生样本中读到了静态物件与平台模板的绑定。保存样本和目录供重建。 |
| `preview_only` | 用作搜索线索。先在目标编辑器查找并导出带该物件的样本。 |
| `whitebox_recipe` | 可另用白盒组合制作外观。 |

选择查询结果的模板 ID 后建立 `layout.json`。下面用石台演示格式，使用时以自身目录里已核对的 ID 为准。

```json
{
  "schema": 1,
  "version": "7.2",
  "mode": "beyond",
  "catalogues": ["models.json"],
  "offset_m": [0, 0, 0],
  "objects": [
    {
      "key": "terrace-west",
      "name": "遗迹 · 西侧石台",
      "template_id": 20001038,
      "position_m": [-2.5, 0, 3],
      "rotation_deg": [0, 35, 0],
      "scale": [1.5, 1, 0.8]
    }
  ]
}
```

- `key` 在布局内唯一。调整物件时保留它，以便对照输出映射。
- `position_m` 和 `offset_m` 采用原生世界 XYZ，Y 向上。位置加整体偏移后写入；`rotation_deg` 按编辑器原生 XYZ 角度写入。
- `scale` 可省略，默认 `[1,1,1]`。按记录中的实测尺寸摆放时，提供 `size_m` 并省略 `scale`。模型目录须包含 `dimensions` 和 `dimensions_source`。后者用 `path` 和 `sha256` 绑定 JSON 记录，内含 `template_id`、三轴正值 `dimensions_m`、原生样本摘要 `sample_sha256`、相同 `version` 和 `mode`，以及说明测量环境及方法的 `method`。只有模板 ID 和尺寸的旧记录仍可查看，使用此类记录布置时请直接指定 `scale`。导入时在目标编辑器中复核实际尺寸。

```text
python scripts/qianxing.py scene build layout.json --out scene-output
python scripts/qianxing.py scene inspect scene-output/scene.gia
```

`scene.gia` 按独立静态单位组织。`scene.json` 可继续编辑，`scene-resources.json` 将布局键关联到包内记录、模板 ID 和回读变换。保留原布局位置及目录引用，或移动布局时按新目录调整 `catalogues`。`manifest.json` 绑定输入样本、目录和输出摘要。按 `IMPORT.md` 在编辑器的资产导入导出管理中加载并转存，存档后取用编辑器实际分配的身份。

制作链 schema 2 中用 `"scene": {"spec": "layout.json"}` 执行同一生成器，输出位于 `scene/`。在同一任务的修改补丁中使用 `place_static_scene` 和 `"source":"@scene"` 可以把布局写入 GIL 基底。补丁的 `prototypes` 按平台模型 ID 映射到基底里具有相同模型的静态实例。使用 portable 时，目录、GIA/GIL 样本和尺寸记录须位于声明的输入根内。

## 修改已有 GIL

先用 `scene inspect LEVEL.gil` 查看场景、触发器和关卡配置，或用 `project inspect LEVEL.gil --scope scene` 查询原生物件、自定义元件实例与已知挂载。配置为 `native plan` 的 schema 2 用法，绑定原始 GIL 的 `base_sha256` 和表中所需的 `allowed_top_level_fields`，再用 `native apply --plan` 写出新的 GIL。步骤和保护范围见[原生修改](native-changes.md)。

| 操作 | 对象与参数 | 可写章节 |
| --- | --- | --- |
| `place_static_scene` | 以 `source` 选择已生成的静态 GIA，按 `prototypes` 复用同模型实例，指定 `version:"7.2"`、`mode:"beyond"` 和可选整体 `offset_m`。 | 5、6 |
| `duplicate_entities` | `copies` 逐项给 `key`、`name`、`source_entity_id` 和可选变换。保留原模板与已有图挂载。适用于已校准的普通实例。 | 5、6 |
| `arrange_instances` | 以布局键创建和更新同一批实例。支持显式物件和等距直线阵列。见[重复布设](#重复布设)。 | 5、新建时加 6 |
| `place_model_instances` | 从同版本模式的 `source` GIL 中选择普通原生平台模型实例。每个 `instances` 条目填写 `key`、`name`、`model_entity_id`、`position_m`。 | 5、6 |
| `create_object_templates` | 从 `source` 绑定纯动态原生模型样本，给 `version`、`mode`。 `templates` 每项为 `key`、`name`、`model_entity_id`，可选 `scale` 和支持的白盒 `parts`。 | 4、6、27 |
| `instantiate_object_templates` | `instances` 项逐个设置 `template_id` 或同一补丁前序的 `template_key`，再给 `key`、`name`、`position_m` 及可选变换。实例装饰物使用独立 ID 并保留模板来源。 | 5、6、27 |
| `set_object_transform` | `section:5` 与 `entity_id` 选择一个已放置的普通静态对象，给 `position_m`、`rotation_deg`、`scale` 中要改的值。 | 5 |
| `set_entity_transform` | `section:5` 和 `entity_id` 选择已有实例，支持已识别的平台物件与本地元件实例。提供要改的 `position_m`、`rotation_deg` 或 `scale`。基底和结果均须通过严格原生审计与工程引用检查。 | 5 |
| `append_decorations` | `section:4` 与 `entity_id` 选择已有装饰列表的动态白盒或空模型元件。`parts` 每项给 `shape_id`、`name`、局部 `position_m`，可选 `rotation_deg`、`scale`、`color_rgb`、`solid`。 | 4、27 |
| `set_decoration` | `section`、`entity_id`、`decoration_id` 唯一定位现有零件，再给要改的局部变换或 `color_rgb`。 | 27 |
| `add_box_trigger` | `entity_id` 选择已有图组件、尚无触发器的普通动态场景对象。可传 `section:4` 编辑模板。设置 `size_m` 和可选 `offset_m`。触发器 ID 为 1，匹配进入的角色实体。 | 4 或 5 |
| `add_native_movers` | `entity_id` 与 `version:"7.2"`、`mode:"beyond"`。 `motions` 填有名称的直线运动或路径，路径项可给 `waypoints:[{position_m,rotation_deg,seconds}]` 和 `loop`。 `position_m` 为初始物件的相对偏移。独立使用 `follow:true` 加跟随组件并由节点图分配目标。 | 4 或 5 |
| `set_linear_motion` | `entity_id`、`motion_id` 选择已有的直线运动器，显式给 `version`、`mode`、`seconds` 与 `displacement_m`。保留运动器身份和启动设置。 | 5 |
| `set_native_preset_state` | `section`、`entity_id` 与 `state_id` 选择模型已有的状态记录，写入对应模型的 `value`。取值以该模型预设为准。运行时可用实体创建图设置初始模型显示，并用同一组节点切换可见性。 | 4 或 5 |
| `set_scene_camera` | `camera_id` 选择已有模板，给 `distance_m` 或 `fov_deg`。更新已校准的关联距离，保留镜头类型和安装关系。 | 18 |
| `set_scene_point` | `point_id` 选择已有预设点或被出生点引用的预设点，给 `position_m` 或 `rotation_deg`。 | 11 |
| `add_scene_points` | 为 `points` 的每项填写 `name`、`position_m`、可选 `rotation_deg` 和 `point_id`。添加后可绑定为复苏检查点。 | 11 |
| `set_terrain_cells` | `terrain_id`、`version:"7.2"`、`mode:"beyond"`。`cells` 每项提供 `index:[x,z]` 和可选矩形另一角 `to:[x,z]`，以及要改的层数、材质、水体、路径或直线斜坡。 | 7 |
| `set_fixed_environment_hour` | `environment_id`、`hour` 调整已有无曲线固定天空的时间项。 | 15 |
| `set_point_light` | `light_id`，提供 `position_m`、`radius_m`、`range_m`、`intensity` 中要改的值。环境与光源的既有链接保留。 | 15 |
| `add_point_light` | `environment_id`、`name`、`position_m` 创建点光源并登记到指定环境。可设 `radius_m`、`range_m`、`intensity`。 | 6、15 |

`set_entity_transform` 使用场景查询返回的 `spatial.transform`。向量均按原生 XYZ 顺序，Y 向上。位置单位为米，旋转为原生角度，缩放各轴为正数。只改指定向量，保留目标的其余组件。用 `native diff --allow-fields 5` 检查输出，`spatial_objects` 给出已识别的空间差异。动态物件写入的是初始布设，运行中节点图仍可更新它。

### 重复布设

在已有 7.2 超限 GIL 中选择可复制的普通静态实例或机关作为原型。使用 `scene inspect` 或 `project inspect --scope scene` 取得 `source_entity_id`。在 schema 2 原生补丁中加入 `{"op":"arrange_instances","source":"layout.json"}`，并按需允许字段 5 和 6。路径相对补丁文件，MCP 内联补丁的路径相对工程根。

```json
{
  "schema": 1,
  "version": "7.2",
  "mode": "beyond",
  "offset_m": [2, 0, 0],
  "objects": [
    {"key": "gate", "source_entity_id": 1077936130, "name": "Gate", "position_m": [4, 0, 1]}
  ],
  "arrays": [
    {"key_prefix": "posts", "source_entity_id": 1077936129, "start_m": [0, 0, 0], "step_m": [0, 0, 2], "count": 3}
  ]
}
```

`objects` 和 `arrays` 可以同时使用。阵列按步进向量生成 `posts/0001`、`posts/0002` 等键。`count: 0` 代表本轮阵列没有布设项。整体偏移叠加到显式位置和阵列位置。`rotation_deg`、`scale` 可按物件或阵列填写。新建时未指定的变换沿用原型，`name` 默认使用布局键。已有键只更新声明的变换，保留名称、模板、组件及图挂载。原型应与已有实例的模板、模型和静态类型一致。

计划中的 `arrangements` 列出创建、变换更新、无变化和保留项，以及对应的实例 ID 和操作前后变换。应用后保留输出 GIL 和 `layout-bindings.json`。MCP 与 `produce` 将映射写入交付目录。CLI `native apply` 在 JSON 报告的 `layout_bindings` 中返回同格式映射，可将该对象另存为 JSON。

下一轮使用上轮输出 GIL 作为基底，更新补丁的 `base_sha256`，并在操作中填入 `"previous_bindings":"layout-bindings.json"`。调整已有实例时保留其布局键，新增实例使用新键。布局中省略的旧键显示为 `retained`，实例及映射仍可供后续使用。每轮使用新的计划和输出路径。`produce` 的后续挂图可用 `{"ref":"entity:gate"}`，详见[制作链](production-v2.md#按名称连接制作阶段)。

白盒形状 ID 支持长方体 `10009001`、球体 `10009002`、圆柱 `10009008` 和圆锥 `10009009`。颜色为 `#RRGGBB`。新增装饰写到元件，场景已有实例的装饰列表独立保留。`scene preview LEVEL.gil --template-id ID --out PREVIEW` 用 Pillow 绘制俯视和侧视中零件的轴对齐近似。

省略 `--template-id` 可预览 GIL 中读到的实体世界坐标。运行 `scene preview LEVEL.gil --before OLD.gil --out PREVIEW` 或 MCP `scene_preview` 可按原生对象键对照新增、移动、旋转和移除。共用比例的 `top.png` 和 `side.png` 以原点标记实体，符合条件的白盒另绘按缩放计算的单位包围盒近似。`layout.json` 与返回摘要的 `coverage` 分别统计当前和对照文件中的索引实体、有世界坐标的实体、仅有原点而无法绘制轮廓的实体、缺少世界坐标的实体与未解析记录。模型尺寸、编辑器导入和游戏运行需另行核对。触发路线可按[联合模拟](joint-simulation.md#盒形触发路线)检查离线模型。

`scene export-whitebox LEVEL.gil --template-id ID --out OUTPUT` 将原点空模型元件的白盒零件另存为独立 `whitebox.gia`。它随包记录形状、局部变换、颜色和依赖索引。使用 `"scene":{"whitebox":{"source":"@level","template_id":ID}}` 可在制作任务最终 GIL 上执行相同导出。交互、组件和每个实例的修改由 GIL 版本承载。 [原生玩法制作](native-gameplay.md)

查看地形栅格时用 `scene inspect LEVEL.gil --terrain-id ID`。每格 5 米，每层 2.5 米，可读取格心、顶部高度、水面、路径及斜坡。平格用顶部高度定位布景，斜坡的落点高度需要按落点复核。写入只改已有格。材质使用 `grass`、`tile`、`sand`、`stone_wall`、`snow`。地块 `layers` 加上 `water_layers` 的合计从 1 到 20。道路用 `path:true`，水体用 `water_layers`，直线斜坡用 `slope` 的 `+z`、`+x`、`-z`、`-x` 或 `flat`，方向对应下降的一侧。水体和道路、直线斜坡分格布设。先保存关卡副本，再按需要烘焙寻路。

交互的图和 Lua 通过已有[制作链](production-v2.md)装配。用 `nodes_lookup` 查看“进入碰撞触发器时”和“获取角色归属的玩家实体”的编译器端口声明，再与目标版本资料或已有工程证据核对。节点图挂到这只触发对象。需要只提示进入者时，声明 `server_to_client` 信号，以业务参数中的玩家实体做定向目标。用已有 HUD 控件的 Lua 映射注册和注销信号处理，参见[复杂类型协议](protocol-v2.md)与[客户端装配](client-assembly.md)。

### 房间入口示例

选一个尺寸明确的触发区，先用已有组件，或按本页生成盒形触发器。下面的服务端图应挂在触发器所属实体上。

```python
"""
graph_id: qianxing_scene_entrance
graph_name: SceneEntrance
graph_type: server
"""
from app.runtime.engine.graph_prelude_server import *

class SceneEntrance:
    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

    def on_进入碰撞触发器时(self, 进入者实体, 进入者实体GUID, 触发器实体, 触发器实体GUID, 触发器序号):
        观察玩家 = 获取角色归属的玩家实体(self.game, 进入者实体)
        发送信号(self.game, 信号名="room_entered", session_key="room", round_id=1, sequence_id=1, viewer=观察玩家, entered=True)

    def register_handlers(self):
        return
```

在 `produce` 中启用 `protocol_native:true`，用 schema 2 声明下面的信号。`graphs.spec` 指向该服务端图的构建配置。先用读回的图 ID 与触发器所属实体 ID 建立 `mount` 计划，再核对最终存档中的图、信号和挂载。

```json
{
  "schema": 2,
  "signals": [
    {
      "name": "room_entered",
      "direction": "server_to_client",
      "policy": "ordered",
      "target": "field:viewer",
      "fields": [
        {"name": "viewer", "type": "entity"},
        {"name": "entered", "type": "boolean"}
      ],
      "phases": ["ready"]
    }
  ]
}
```

在关卡的既有 HUD 准备名为 `RoomEntryHint` 的根控件。用实际 Lua 映射把脚本装配到对应 GIL 中，进入触发区后此控件应显示。第五个参数是 `entered`，前三个是现有协议的信封字段。

```lua
local hint
local signal = "room_entered"

function OnInit()
    hint = game.FindClientUIRoot("RoomEntryHint")
    if hint then
        hint:SetVisible(false)
    end
    script:RegisterServerSignalHandler(signal, function(_, params)
        if hint and params[5] == true then
            hint:SetVisible(true)
        end
    end)
end

function OnDestroy()
    script:UnregisterServerSignalHandler(signal)
end
```

## 原生范围与检查

GIA 构建回读对象、模型定位器、静态标记及 float32 变换。GIL 修改的范围由计划绑定，已知配置逐项回读。平台编辑器中的摆放、保存和游戏内交互各自记录。组合的子零件、地形曲面及光照预览以游戏为准。原生场景生成模板、动态元件组、带曲线天空和转角斜坡需要各自的格式对照。

文件字段与模式的依据见[官方实体摆放](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhnffmieeqbg)、[官方模型配置](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhrutdio6904)、[8itlab 物件封装](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/scene/blocks.mjs)、[8itlab 场景记录](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/scene-save.mjs)和 [XingGou 静态 GIA](https://github.com/Crazyfourrrrrrrrrrr/XingGou/blob/5e05593e1c392c2a65885317111a1fa8425f7854/core/static_gia.py)。
