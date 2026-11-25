# 原生结构生成、脚本映射与挂载

## 从结构化输入生成

使用平台字段类型、默认玩家/队伍/环境配置和创建算法构建新载荷，不读取完整游戏GIL，不继承旧玩法的节点图、脚本或挂载。`platform_schema.py` 保存经校准的字段类型和平台默认配置。地图、UI、脚本及其关联由 `level_authoring.py` 生成。它不是任意版本格式的完整实现，也没有通过编辑器或实机证明生成关卡可玩。

```text
python scripts/qianxing.py level create LEVEL.json --out NEW.gil
python scripts/qianxing.py level inspect NEW.gil
python scripts/qianxing.py inspect NEW.gil
```

LEVEL.json：

```json
{
  "schema": "qianxing-level-spec/v1",
  "id": "new_level",
  "map_size": [20, 20],
  "scripts": [{"name": "main.lua", "source": "client.lua"}],
  "root_script": "main.lua",
  "templates": [
    {"name": "Rect", "kind": "container", "size": [100, 100]},
    {"name": "Label", "kind": "text", "size": [100, 40]},
    {"name": "Image", "kind": "image", "size": [80, 80]},
    {"name": "HitArea", "kind": "area", "size": [100, 100]}
  ]
}
```

source相对配置文件。地图当前只允许已校准的1..20格范围，固定平台地图坐标；不把它称为自动地形/关卡内容生成器。id是顶层字段2的存档标识，不是游戏内显示名。关卡创建使用 `qianxing.py level create`。scripts创建字段50的映射与正文；root_script挂到新建客户端根控件。templates创建可实例化模板，运行时代码依据回读结果取GUID。

统一制作配置可包含 `"level": {"spec": "LEVEL.json"}`。produce先生成新基底，随后graphs未显式指定base_gil时自动使用它；现有图写回仍按类型、字段保护和挂载合同验证。gil阶段的mapping仍是完整名称，不猜测。未声明任何图时，生成文件的字段10为空，不会残留完整游戏逻辑。完整新玩法仍须实际编写Lua/Graph Code并接入真实事件，结构生成不等于玩法实现。

## Lua按名称使用模板

脚本项可增加 `"templates_as": "UI_TEMPLATES"`。生成器会按本次实际分配的GUID，在该脚本正文前创建同名局部表，使源码直接使用 `game.InstantiateClientUIControl(UI_TEMPLATES.Rect, script.object)`。别名须为有效Lua变量名，不能是关键字；不要求用户手抄大数索引，也不在原始源码中写死ID。

回读报告template_indices提供本次声明的模板名→GUID，template_aliases记录每个脚本的别名。produce含level阶段时还输出template_indices.lua；后续gil写回按相同表补齐前缀，不会把绑定在最后一步覆盖掉。发现不同或已过期的生成前缀时，工具会拒绝写入。此时用原始 Lua 重新生成，避免叠加旧表。原始源码不修改，内嵌正文摘要按实际生成内容记录。

## 模板GUID与相互关联

调用 `InstantiateClientUIControl` 时，用模板记录的 GUID 作为模板索引。实际存档可能出现1073743580这一数量级，具体值由当前文件决定；禁止把示例数值固定给其他文件。

在已核验的UI section9中，502是记录集合，记录501为GUID；带种类标记的组/库记录通过meta13的501指向模板记录GUID，模板记录通过meta14的501 packed-ID列表反向关联组。meta13也可能表示其他链表引用；解析器只在明确的501=3、502=3元信息形态中将它视为模板指针。回读输出templates里的instantiation_index及reciprocal_reference_verified。

## 新建映射和挂载

```text
python scripts/qianxing.py level bind CURRENT.gil --control CONTROL_GUID --script extra.lua --mapping extra.lua --out NEW.gil
```

先新建完整.lua名称映射，按当前脚本命名空间分配无冲突GUID，再挂到真实存在的控件。已有同名映射拒绝重复注册；更新正文使用replace-lua。

字段50/1条目：1=脚本GUID、2=显示名、3=完整映射文件名、5=Lua正文。UI脚本组件的外层属性501=63、类型502=83，其503覆盖消息内501=65；该覆盖的74消息中502/1/1引用脚本GUID。这里的“65”是嵌套属性标记，不是简单的UI记录字段65。更新保留其他组件和原有脚本引用，不改其他顶层字段；关联回读缺失、重复或不闭合即拒绝。

## 追加客户端界面模块

已有客户端原型库的 GIL 可通过 `native plan/apply` 增加容器和预设按钮模板，并给指定的现有客户端容器追加一份 Lua 映射。原生补丁允许顶层字段 `9`、`50`。以 `project inspect` 或 `level inspect` 核对实际挂载 GUID。

```json
{
  "op": "append_client_ui",
  "source": "panel.lua",
  "mapping": "panel.lua",
  "mount_guid": 1073745924,
  "container": {"name": "Panel", "size": [320, 200]},
  "button": {"name": "Confirm", "size": [150, 50]},
  "asset_data": "GENERATED/data.json"
}
```

两个模板分别注册到现有客户端原型库。脚本可用 `game.InstantiateClientUIControl(qx_templates.container, script.object)` 和 `qx_templates.button` 创建界面实例。可用 `templates_as` 更换模板表名称。可选的 `asset_data` 接受[批量素材](../assets/image-to-primitives.md#多素材共用控件预算)生成的 `data.json`，在脚本中通过 `qx_assets.<素材键>` 使用。Lua 源和素材数据都纳入密封计划。应用报告给出新模板和脚本映射，可用 `simulate check RESULT.gil --mapping panel.lua` 验证启动。

## 将生成的 Lua 挂到现有关卡

用 [图片拟合](../assets/asset-fit.md#生成可挂载的-lua-和软件预览) 从目标关卡读取图片模板和客户端容器，再用 `native_plan` 审阅挂载。把返回的 `mount.gil_binding.control_guid` 用在操作中。原生补丁使用相同的关卡摘要，允许顶层字段 `9`、`50`。

```json
{"op":"bind_client_lua","control_guid":1073745924,"source":"fitted/mounted.lua","mapping":"marker.lua","fit_catalog":"fitted/catalog.json"}
```

应用计划时会重验关卡、目标控件、图片模板和 Lua 的摘要。已有同名映射时拒绝新增。单独挂载 Lua 时可省略 `fit_catalog`，仍需确认唯一客户端容器和完整的 `.lua` 映射名。应用后检查另存的 `level.gil` 和报告里的控件、脚本标识及正文摘要。

## 精确替换与错误定位

replace-lua / produce.gil.mapping均按完整字符串相等匹配，含.lua后缀。例如main不匹配main.lua。匹配失败会列出实际映射名；不自动按子串猜选，避免覆盖错误脚本。

inspect单文件返回schema=qianxing-inspect/v2、file/graphs/client_bindings等顶层字段；目录返回同一schema及files数组。统一CLI的--collection可显式保留单文件files数组结构。绑定报告schema为qianxing-client-bindings/v1，含scripts、controls、templates、script_bindings和diagnostics。

## 将图、信号和 Lua 写入同一份 GIL

用 [produce](../workflows/produce.md) 从同一配置连接基底、图、信号、Lua 和最终回读。单独增补节点图时，用 [build](../graph-code/node-graph-workflow.md#构建描述-schema-1) 指定基底和允许写入的顶层字段。已有项目资源可用 [Ayaya 项目写回](../graph-code/ayaya-offline-toolchain.md#项目写回-gil)，并明确选择需要的资源范围。

在已校准的 Ayaya 写回链中，信号定义先于依赖它的节点图写入，以便把通用信号节点类型映射到该文件内的信号定义。信号参数名、顺序、类型及关联图的实际端口须一起回读；找不到模板或信号定义时，先核对项目基底、当前声明和模板来源。GraphModel JSON 的中间诊断用 [离线工具链](../graph-code/ayaya-offline-toolchain.md#graph-code-到节点图)。

回读最终文件的脚本映射、实体挂载以及[图数据流](../graph-code/native-dataflow-validation.md)。对 GIL 中同号的普通图、复合图、模板或实例，使用[对象索引](../editor/project-index.md)读取完整对象键，按目标范围核对引用。

## 安全重跑与验证层级

```text
python scripts/qianxing.py produce JOB.json --out OUTPUT --next
```

默认输出已存在即拒绝并显示解决方法。--next自动选择OUTPUT-2、OUTPUT-3等新目录，不删除或覆盖原输出，实际目录写入production-report的output_directory。失败仍回滚本次临时目录。

生成结果的确定性、字段引用完整性、脚本回读和 Lua 模型断言均为离线证据。编辑器能否导入、宿主启动时能否加载脚本、素材显示和真机性能须分别验收。平台固定配置取自已核验格式校准，未知版本/宿主规则不靠虚构字段补齐。完整游戏模板不参与生成，也不进入发布包。
