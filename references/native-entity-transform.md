# 读取与修改三维实体

源码版支持读取 GIL 中已摆放的普通三维物件，区分直接引用平台模板的物件和由自定义元件实例化的物件。已有实例的世界变换可经修改计划另存为新 GIL。这项操作见变更记录的 `Unreleased`。

## 定位对象与模型

```text
python scripts/qianxing.py project inspect LEVEL.gil
python scripts/qianxing.py project consumers LEVEL.gil --kind entity --id 1077936130
```

也可调用 `project_inspect` 并传入 `selector: {"key":"level/entity/1077936130"}`。从实际工程取得对象 ID。模板和实例各有独立的键，即使使用相同数字。读取 `target.spatial` 和 `dependencies`。

| 数据 | 解释 |
| --- | --- |
| `template.scope` 与 `template.id` | `platform` 指向平台模板，`project` 指向当前工程的自定义元件。 |
| `model` | `type: "template"` 与 `id` 是原生资源身份。直接摆放取实例定位器，元件实例取已确认模板的模型定位器。文件本身只证明引用，目录可用性仍显示 `resource_verified: false`。 |
| `static` 与 `component_types` | 物件的静态标记及原生组件类型编号。图挂载和模板关系由工程索引提供。 |
| `transform.space` | `world` 是实例世界坐标，`template_default` 是模板记录，`owner_local` 是装饰物相对所属实体或模板的坐标。独立物件 GIA 用 `asset_world` 表示包内位置，导入后的身份以 GIL 为准。 |
| `transform_editable` | 是否识别到可按当前合同修改的实例变换。 |

三个向量使用原生 XYZ，Y 向上。位置 `position_m` 以米为单位，对应原生放置枢轴。`rotation_deg` 为编辑器保存的 XYZ 绝对角度。`scale` 是各轴的倍率。向量按 float32 编码。模板和实例读取各自的记录，装饰物需与所属对象的双向归属一致才会列出。

## 沿 X 移动并旋转

先读原始值，再填写目标绝对向量。假设原位置为 `[2,4,-6]`，姿态只有 Y 轴的 15°。沿世界 X 移动 2 米并绕 Y 转 90°，可用以下补丁。ID 和摘要取自实际工程。

```json
{
  "schema": 2,
  "base_sha256": "填入原始GIL的SHA256",
  "allowed_top_level_fields": [5],
  "operations": [{
    "op": "set_entity_transform",
    "section": 5,
    "entity_id": 1077936130,
    "position_m": [4, 4, -6],
    "rotation_deg": [0, 105, 0]
  }]
}
```

`position_m`、`rotation_deg`、`scale` 至少提供一项。每项须有三个分量，缩放按 float32 编码后仍须为正。对已倾斜的对象，填写编辑器目标 XYZ 角。任意姿态的世界轴旋转合成需有对应坐标校准。

```text
python scripts/qianxing.py native plan LEVEL.gil --spec PATCH.json --out PLAN.json
python scripts/qianxing.py native apply LEVEL.gil --plan PLAN.json --out EDITED.gil
python scripts/qianxing.py native diff LEVEL.gil EDITED.gil --allow-fields 5
```

MCP 可用 `project_inspect` 返回的 `inputs_sha256.input` 调用 `native_plan`，把补丁直接作为 `patch`。审阅 `result.difference.spatial_objects` 后，用输出目录中的 `plan.json` 与 `outputs_sha256["plan.json"]` 调用 `native_apply`。应用报告返回目标前后值，`native_diff` 可用 `allowed_top_level_fields: [5]` 检查保护范围。[MCP 操作顺序](local-mcp.md#审阅并另存已有工程)

## 格式依据与范围

GIL 放置实例位于章节 5，变换读写 kind 1 组件的三个向量。模板默认变换位于章节 4，装饰物位于章节 27。独立普通物件 GIA 核对资源、实例和平台模板定位器的一致性。当前物件身份范围为 `0x40400001` 至 `0x404fffff`。模板、装饰物和 GIA 在这一阶段提供读取。其他单位类型、父子布设组、资源替换和运行时运动保留现有通用索引或上层工具。

本地检查涵盖文件回读与字节保护。编辑器导入和游戏内效果需要实际验证。后续静态场景可复用这里的模型身份和世界变换，从独立静态物件 GIA 封装开始。

[官方实体摆放指南](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhnffmieeqbg) · [8itlab 物件与元件](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/scene-save.mjs) · [XingGou 静态 GIA](https://github.com/Crazyfourrrrrrrrrrr/XingGou/blob/5e05593e1c392c2a65885317111a1fa8425f7854/core/static_gia.py) · [XingGou 坐标转换](https://github.com/Crazyfourrrrrrrrrrr/XingGou/blob/5e05593e1c392c2a65885317111a1fa8425f7854/core/coordinates.py)
