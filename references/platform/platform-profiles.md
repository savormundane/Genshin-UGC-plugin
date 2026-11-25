# 平台版本与配置检查

能力名：platform-profiles。入口为qianxing.py docs、platform和capabilities。使用Python标准库，资料与规则随插件提供，不需要网络或宿主文件系统。它检查显式声明的配置；不据此宣称已验证GIL的平台版本、组件写入或实机行为。

## 资料查询和版本选择

```text
python scripts/qianxing.py docs search "造物扰动装置" --version 7.2
python scripts/qianxing.py docs show mh74ae9fsg8i --version 7.2
python scripts/qianxing.py docs diff --from 7.1 --to 7.2
python scripts/qianxing.py docs diff --from 7.1 --to 7.2 --id mhnmcmipncrg
python scripts/qianxing.py platform profile --version 7.2 --mode classic
```

显式选择已登记的平台版本，目前有 7.1 和 7.2。模式为 classic（经典）或 beyond（超限）。search 按标题和正文匹配所有查询词，--limit 为 1 至 100。show 返回正文。diff 按文档 ID 和内容摘要比较，指定 --id 时附全文差异。

scripts/platform-sources.json 将文档 ID 映射到包内原文、来源类型、官方链接和摘要。资料沿 `base` 逐级回溯，取最近版本的声明。结果提供 requested_version、source_version 和 inherited。读取已选正文时检查文件和摘要，父级缺失或循环直接报错。diff 两侧保留来源，正文摘要相同时仍为 unchanged。正文差异包括排版变化。

新版本通过 `limits`、`mode_limits`、`conflicts` 记录规则差异。默认沿用已有规则。覆盖了某项规则的依据时，在 `rules` 中将该规则设为 true 以登记审定后的沿用或修订，或设为 false 停用。缺少审定记录时，该规则在新版本返回 not_checked。

## 配置合同

配置使用schema 2，必填version、mode和objects。对象id须唯一且非空；未知字段和类型拒绝。objects应覆盖本次要检查的对象，不能将局部数量当作整个关卡的总量。

| kind | 必填参数 | 检查范围 |
| --- | --- | --- |
| creature | skill_count | 非负整数；7.1最多50，7.2最多100 |
| movers | active | linear、rotation、target_rotation、path、point、level_path的同时生效组合 |
| timer | entity、sequence | 同一entity最多100个声明定时器；每序列1至100个非负有限时间点，严格递增，相邻间隔至少0.03秒 |
| photo_button | trigger、cooldown_origin | 7.2均为photo_close；classic最多两个声明拍照按钮 |
| combat_text_filter | entity_kind、filters_per_template | 7.2仅player；列表项为各模板内过滤器数，模板和单模板过滤器数均最多100 |
| prefab_group | members | 7.2每个成员包含唯一id及布尔dynamic，全部为动态单位 |

运动器枚举分别表示匀速直线、匀速旋转、朝向目标旋转、路径、定点和关卡路径。7.1资料对定点与两类旋转的正文和表格冲突，该组合返回not_checked；7.2明确不可叠加，返回failed。不得把旧版冲突自动判为可用。

第一套配置可检查经典模式的造物、运动器和定时器：

```json
{
  "schema": 2,
  "version": "7.1",
  "mode": "classic",
  "objects": [
    {"id":"creature-a","kind":"creature","skill_count":50},
    {"id":"movement-a","kind":"movers","active":["linear","point"]},
    {"id":"timer-a","kind":"timer","entity":"entity-a","sequence":[0.03,0.06,1]}
  ]
}
```

第二套配置可检查7.2超限模式中的拍照、过滤器和元件组：

```json
{
  "schema": 2,
  "version": "7.2",
  "mode": "beyond",
  "objects": [
    {"id":"photo-a","kind":"photo_button","trigger":"photo_close","cooldown_origin":"photo_close"},
    {"id":"filter-a","kind":"combat_text_filter","entity_kind":"player","filters_per_template":[2,4]},
    {"id":"group-a","kind":"prefab_group","members":[{"id":"part-a","dynamic":true},{"id":"part-b","dynamic":true}]}
  ]
}
```

将所选配置保存为platform.json，运行：

```text
python scripts/qianxing.py platform check platform.json
```

通过只表示列出的配置规则满足；报告scope为declared_configuration、artifact_verified为false，并附配置摘要和实际引用的文档摘要。空objects、旧版本没有登记的规则或资料冲突为not_checked；明确违反规则为failed。两者均返回非零退出码。非整数数量、未知字段等输入错误直接拒绝。

可选native_bindings将已声明timer对象关联到最终普通节点图，例如`"native_bindings":{"timer-a":{"graph":1073741900,"node":1,"entity":42,"name":"clock"}}`。键必须对应timer对象，graph/node必须唯一；同一逻辑entity不能绑定到不同实体编号。当前只支持已校准的开启定时器节点79，不以对象名称推断图或节点。

独立检查使用`docs check CONFIG.json --gil FINAL.gil`。produce的platform配置含native_bindings时，必须存在最终level.gil，并在所有原生修改及Lua写回后生成platform-native-report.json；任何绑定失败或not_checked均阻止提交。portable沿现有platform配置输入闭包携带绑定。

原生报告逐项核对目标实体常量、定时器名称常量和序列常量。序列按声明数值编码为float32后精确比较，不把二进制浮点误差当成不同配置；平台规则本身仍按原声明检查。输入端或输出端记录了数据连接时不使用残留常量冒充实际值，报告connected_timer_inputs/not_checked。节点缺失、歧义、引用错误或常量漂移失败；其他常量表示保持not_checked。

该检查不执行动态数据流、不验证目标实体运行时存在、不推断循环行为或实际同时开启的定时器数量。scope为selected_native_timer_constants，whole_artifact_verified保持false，unbound_objects列出尚未关联的声明；其他组件规则不能借此宣称已有原生回读。test_platform_native以7.1/7.2两套配置验证匹配、漂移、动态拒绝、最终产物摘要及制作回滚；编辑器和宿主仍待验。

反例：第一套skill_count改为51、时间点改为[1,1.01]；第二套trigger改为button_press，或成员dynamic为false，均不通过。将第二套version改为7.1时规则未登记，不能获得通过结果。

## 制作链接入

在现有produce schema 2任务增加platform字段，spec相对任务文件解析：

```json
{
  "schema": 2,
  "platform": {"spec":"platform.json"},
  "level": {"spec":"level.json"},
  "portable": {}
}
```

level.json使用[原生结构生成](../gil/native-authoring.md)的合同。platform在资源生成之前检查；failed或not_checked阻止正式输出提交。通过后输出platform-configuration.json和platform-report.json，记录配置、资料目录及所用原文依赖。配置正文属于交付产物并逐字节比较；检查报告属于证据。portable收纳配置、规则和资料，支持原输入目录不可用后的独立重建。

本阶段不会向level.gil写入上述对象，也不会把配置中的对象id绑定为原生GUID。组件原生生成、资源ID支持、生命周期和详细节点签名属于报告中的未检查范围；最终GIL仍须经过原生审计，平台字段是否落地另行核验。

## 分层能力证据

```text
python scripts/qianxing.py capabilities --platform 7.2 --mode classic
python scripts/qianxing.py capabilities --platform 7.2 --mode classic --evidence CHECKS_DIRECTORY/checks.json
```

每项能力提供rules、generation、readback、lua_model、native_graph_model、editor和host七层。implementation表示是否登记实现；status表示本轮证据状态。没有登记的层为not_registered/not_checked，不根据其他层通过推断成功。

通过证据必须满足[验证证据闭环](../workflows/validation-evidence.md)并实际执行该层required_cases。scope限定其覆盖范围，例如原生图模型仅覆盖已实现节点，不包含复合调用执行。选择平台仅附加配置上下文，platform_version_verified仍为false；编辑器和宿主不会由离线用例升级为通过。

宿主验证需导入实际文件，核对配置和运行表现。

## 7.2补充声明规则

以下kind同样放入objects，均要求唯一id。字段是声明合同，不是原生组件标签；只检查所声明的对象，不自动证明编辑器中的配置。7.1选择这些规则时返回not_checked。

| kind | 必需字段与语义 |
| --- | --- |
| disturbance | entity_kind=dynamic_object；devices每项index、type（launcher/tractor/force_field）、initial_active，可选expected_duration；selected_index、expected_active_index可为null。最多一个初始生效，空或不存在序号关闭全部。牵引器预期运行超过30秒失败，但不声称编辑字段最大值为30。 |
| push_collision | entity_kind=complex_creature、supported（true/false/null）、hook、shape（box/sphere/capsule）、center/scale/rotation三个有限XYZ向量、index、custom_native_enabled、controls_native。只有控制原生碰撞开关才要求开启自定义原生碰撞，不混同额外碰撞前置。supported=null表示需在编辑器确认，不根据名称猜支持。 |
| filter_semantics | active_templates、include/exclude/tags非重复字符串列表、expected_match布尔、owner_resolution=topmost_or_self、friendly_includes_self=false。计算全部包含、任意排除；最多一个模板生效。 |
| camera_takeover | entity_kind=object、skill_camera布尔、expected_during=skill、expected_after=configured_object。仅经典模式且明确适用技能镜头时检查接管和恢复，其他情况not_checked。 |
| clear_velocity | enabled、expected_clears_force均为布尔；清速度不清持续力，后者应为false。 |
| translations | languages非空语言列表、entries每项唯一id、origin（text/graph_variable/instance_override）、translations语言到文本映射；检查所需语言的空白或遗漏，不验证译文质量。 |
| arrival | radius非负有限数、accept_precise_sliding布尔；零半径触发精准移动／滑步，未明确接受则not_checked，不当作非法字段。 |

用 `platform check` 单独检查配置，在 `produce` 声明同一配置可复用检查。违反规则返回 `failed`，缺少适用依据返回 `not_checked`。必需阶段未通过时不提交正式输出。
