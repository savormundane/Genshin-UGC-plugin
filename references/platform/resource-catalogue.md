# 平台资源目录

可按平台版本查询资源，也可检查项目声明的资源用法。内置的经典模式角色编号来自已核对摘要的随包表格。查询结果附上官方页面、资料类型、版本、是否沿用旧版资料、行号和摘要。使用第三方镜像时，也会记录镜像链接和提交。游戏内验证状态单独记录。

```text
python scripts/qianxing.py resources search 神里 --version 7.2
python scripts/qianxing.py resources search 10000002 --version 7.2
python scripts/qianxing.py resources check uses.json --out resource-report.json
```

`search` 按名称、ID、类型或类别匹配，支持 `--type` 和 `--mode` 过滤，可多次传 `--catalogue custom.json` 追加项目目录。`check` 的输出文件必须是新路径，来源文件均只读。

## 查询音效和特效

用 `resources_lookup` 查音效时设 `resource_type="sound"`，查特效时设 `resource_type="effect"`。查询词可用空格分隔，例如「界面音效 按钮点击」或「循环特效 光环」。纯数字查询按完整 ID 匹配。

```text
python scripts/qianxing.py resources search "界面音效 按钮点击" --type sound --version 7.1
python scripts/qianxing.py resources search 10019173 --type effect --version 7.2
```

包内图鉴收录 147 条音效和 431 条特效的编辑器观察。2026-10-11 的观察日期位于官方 7.1 更新后和 7.2 更新前，具体客户端构建未记录。2026-11-07 的 26 条限时特效来自上游登记的 7.2.0 客户端。查询 7.2 时，7.1 条目可作为历史候选，`applicability` 为 `historical_observation`。名称截断以原记录为准，`reported_duration_s` 为面板标示时长。

图鉴返回每批原始来源、固定提交、版本依据和本地目录摘要。模式未知写为 `null`，实机状态为 `not_checked`。这些观察仅供检索。项目要在制作中引用资源，仍需提供与目标版本、模式匹配的项目资源声明和来源。 [音效源](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/scene/media/sounds.json) · [特效源](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/src/scene/media/effects.json) · [7.2.0 采集证据](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/docs/evidence/7.2/secret-fx-capture.json)

## 使用合同

```json
{"schema":2,"version":"7.2","mode":"classic","uses":[{"type":"character","id":10000002}]}
```

以下配置使用单独的图片资源目录。

```json
{
  "schema":2,"version":"7.2","mode":"classic",
  "catalogues":["resources.json"],
  "uses":[{"type":"image","id":900,"dimensions":[32,24],"require_dependencies":true,"accept_declared":true}]
}
```

`900` 是测试用的示例 ID。实际项目请在自定义的 `resources.json` 中填写已核实的资源编号、资料和来源摘要。

```json
{
  "schema":2,"version":"7.2",
  "resources":[{
    "type":"image","id":900,"name":"Neutral","mode":"both",
    "dimensions":[32,24],"dependencies":[],
    "source":{"path":"calibration.txt","sha256":"填写来源文件SHA256","line":1}
  }]
}
```

来源路径相对目录文件。支持character/image/template/sound/effect/item类型，ID必须为非负整数，类型与ID共同确定身份。同版本内同身份重复拒绝，不静默覆盖官方目录。mode为classic/beyond/both。dimensions为两维或三维正整数，未知写null。dependencies为`[{"type":"sound","id":800}]`，已知无依赖写空数组，未知写null；两者语义不同。

外部目录的来源文件摘要和行号必须存在，但工具不把“有来源文件”当作“该文件已证明每项属性”，其evidence固定为declared。默认使用此类资源返回not_checked；只有项目明确accept_declared=true才允许声明级合同通过。此选择不会升级来源证据或实机状态。

依赖按类型与ID遍历闭包并去重，不因循环无限递归。目录中缺少依赖、重复依赖及重复身份拒绝；使用合同检查闭包内每项的模式与声明证据。请求尺寸但资料未提供，或require_dependencies=true而依赖情况未知，均为not_checked。缺失使用资源、尺寸不符或模式不符为failed。

## 制作与证据

```json
{"schema":2,"resources":{"spec":"uses.json"},"level":{"spec":"level.json"}}
```

produce在生成前检查合同，failed或not_checked均不提交输出。成功交付resource-catalogue.json，其来源只包含内容摘要、行号和资料元信息，避免机器绝对路径影响独立重建的字节比较。resource-report.json另外保留完整路径、输入摘要和合同诊断，登记为证据文件。portable输入收集包含使用合同、外部目录及其来源文件。

默认检查范围是显式uses清单，artifact_references_verified=false；它不证明最终Lua/GIL已经引用这些资源，也不证明没有未声明引用。可按下一节开启客户端SetImage子集检查。完整客户端/原生资源引用提取仍待补齐。complete_platform_catalogue=false，使用合同内置经典角色编号，其余资源依赖项目显式提供的目录。角色尺寸与依赖未在表中给出，因此保留null，不猜测。

## 三维模型引用

`dimensions_evidence` 为 `sample_bound_measurement_record` 时，尺寸记录的摘要、模板 ID、尺寸、原生样本摘要、版本和模式相符，记录附有测量方法。只有这种来源可用于 `size_m`。只核对了模板 ID 和尺寸的旧记录为 `matching_measurement_record_only`，仍可供查阅。工具核对的是记录关联，测量方法与编辑器和游戏内的尺寸应按项目另行验证。 [静态场景](../editor/native-scene.md#查找模型并搭建静态场景)

`project inspect` 返回已识别物件的 `spatial.model`，身份沿用目录的 `type: "template"` 和 `id`。`spatial.template.scope: "project"` 表示工程内的元件身份。原生文件提供实际定位器，目录的版本、模式和来源按资源合同检查。[三维实体身份](../editor/native-entity-transform.md)

## 最终客户端图片引用

在uses.json中设置`"check_client":true`，制作任务同时声明`client_check:{"spec":"client-check.json"}`，使用[客户端API检查](../editor/lua/client-api-check.md)的源码摘要及类型绑定合同。缺少合同即拒绝，不能通过扫描文本猜测某个对象是图片控件。

`produce` 从最终 GIL 或最终单文件 Lua 的 API 分析结果中读取 `ClientUIImageControl.SetImage` 调用，并输出 `client-resource-report.json`。`Enum.ImageSource` 的映射为 `StaticReference` → `image`、`Item` → `item`、`Equipment` → `equipment`、`Skill` → `skill`、`UnitStatus` → `unit_status`、`Faction` → `faction`、`Currency` → `currency`、`Prefab` → `template`。外部目录接受这些类型，具体资源 ID 由项目提供。

已解析的来源和整数ID必须在uses中明确声明并已通过目录合同，未声明则失败并撤销正式输出。依赖闭包中的条目不自动成为可直接使用的资源。十进制/十六进制整数及一元负号、按位取反按Lua 5.3整数事实解释；尚未求值的表达式和动态ID保持not_checked，不把负ID误认为其正数文字。动态对象或不完整API分析同样不能通过。

此检查仅覆盖可解析的SetImage调用，不覆盖原生图片组件、其它资源API、间接项目函数或完整宿主资源加载；complete_reference_index仍为false。没有SetImage调用仅表示该检查范围内未发现引用，不能宣称所有资源引用通过。通过报告不改变外部资料的declared性质，也不改变编辑器/实机状态。

目录结果用于核对资源身份和依赖。资源的外观、适用模式和实际表现，以目标版本的编辑器检查和游戏内实测为准。

客户端专项使用StaticReference和Item两种来源，覆盖已声明资源、十六进制、负数、缺失ID、动态ID、未求值表达式、最终单文件Lua制作链和失败回滚。新增内嵌GIL专项使用StaticReference和Prefab两种来源，核对报告绑定最终GIL摘要、映射名称和资源类型，并拒绝正文改变后仍使用旧摘要合同。原生图片组件字段仍缺校准，不在此范围。
