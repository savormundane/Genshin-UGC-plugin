# 工程对象与引用索引

`project-index` 的入口为 `scripts/project_index.py` 和 `qianxing.py project`，依赖 Python 标准库和随包原生定义。只读GIL/GIA或显式多文件清单；原生语义与客户端映射检查复用现有读取器。

```text
python scripts/qianxing.py project inspect LEVEL.gil
python scripts/qianxing.py project search LEVEL.gil QUERY --scope scene --kind entity --limit 20
python scripts/qianxing.py project inspect LEVEL.gil --scope scene
python scripts/qianxing.py project inspect LEVEL.gil --scope scene --key level/entity/1077936389
python scripts/qianxing.py project inspect LEVEL.gil --scope gameplay --summary --out gameplay.json
python scripts/qianxing.py project inspect LEVEL.gil --scope gameplay --kind currency --id 1115684865
python scripts/qianxing.py project check PROJECT.json
python scripts/qianxing.py project consumers LEVEL.gil --kind script --name main.lua
python scripts/qianxing.py project consumers LEVEL.gil --key level/graph/ordinary/1073741900 --transitive
```

inspect和check输出同一结构化报告，包含objects、references、issues、unresolved及每个输入产物的sha256。passed返回0；failed或not_checked返回2。报告不写回输入，也不证明编辑器导入或宿主运行。

## 场景范围

`--scope scene` 读取单个 GIL 或 GIA 的对象、变换与可识别的挂载。MCP `project_inspect` 对应参数为 `scope="scene"`。可用实际返回的 `key` 查询实体、元件模板或装饰物的已知依赖和引用者。索引保留名称、身份和未解析原因，`spatial` 有内容时区分摆放实例 `world`、模板默认 `template_default` 和装饰物 `owner_local`。模型定位器的可用性需结合资源目录核对。

`checks.scene_index` 表示本次读取结果，`checks.spatial_coverage` 记录未解析项，`checks.graph_audit` 为 `not_checked`。写入资格由严格原生审计和完整工程引用检查决定。精确变换、单位和写入用法见[原生场景](native-scene.md)。

## 玩法引用

`--scope gameplay` 定位职业、技能、道具、货币、背包、商店、环境、光源、拾取模板和计时器。可由货币反查商店价格，由技能定位正确类别的图，也可从实体查看背包、商店和掉落的已知引用。报告的引用依据来自已校准的原生字段。完整工程检查会报告已确认的悬空目标或类型冲突，并阻止制作任务提交。平台默认项和动态计算的图常量属于覆盖范围之外。

`--summary` 返回对象数、关系数和诊断。加 `--out` 可同时写出完整报告。带选择器时返回目标、已知引用者和依赖。

## 对象身份和查询

先用 `search` 按名称查找，也可传完整对象键或原生 ID。精确项排在部分名称匹配前。同名对象分别显示，`total_matches` 和 `truncated` 标明结果是否截断。用选中的 `key` 接续 `inspect` 或 `consumers`。`status` 表示查询结果，`index_status` 保留索引检查结论。

MCP 对应 `project_inspect(input, query, scope, kind, limit)`。输入摘要省略时由工具记录，`inputs_sha256.input` 可传给后续 `native_plan`。

对象key由文件命名空间、kind、作用域和id组成，每段使用URL百分号编码。例如level/graph/ordinary/1073741900与level/graph/composite/1073741900不同；level/template/1086324737与level/entity/1086324737也不同。脚本、控件、声明、结构体、存档模板/槽位、信号及GIA资源均保留自身命名空间。以inspect返回的完整key作为后续选择器，不按名称或数字猜选对象。

consumers默认返回直接引用者，--transitive沿反向引用继续追踪图、挂载实体等；循环引用不会无限遍历。--name、--id可以搭配--kind，但最终必须唯一；多个文件中的同名脚本、同号普通/复合图均报告歧义。node_connection统一从使用者指向提供者，输入端、输出端或两端记录得到同一依赖关系；location保留input_port、output_port和serialized_at原始记录位置。双端记录合并，同一端的重复记录报错。流程连接表示下游对上游的依赖，不代替运行时执行顺序。

已读取的关系包括节点声明/具体类型、通用信号的实际声明、图连接与复合接口、结构体描述/默认值、存档槽位、信号角色、图库和图挂载、GIA依赖及资源正文、已校准实体模板引用、控件父子/模板/根控件、UI登记与脚本挂载。检查重复身份、悬空和歧义引用、父子不一致与父级循环、模板双向关联及根控件绑定。对未保存子列表的对象，保留缺失状态。

平台内置模板仅记录外部身份并标记resource_verified=false；文件内声明以实际文件为准。[原生自定义变量](native-variables.md)区分模板默认值、实例覆盖及结构体引用，支持继承/覆盖消费者查询。任意组件内容、变量访问及标识值目标、无类型数字常量、动态Lua标识及平台资源目录尚未全部索引，complete_reference_index固定为false，unindexed明确列出范围。迁移 ID 时仍需核对这些未索引的引用。

## 多文件清单与必需关系

配置schema为2，未知版本/字段拒绝。每个artifact名称非空且唯一，source相对该清单解析；可用sha256绑定输入版本。同一文件可在不同命名空间中检查，不自动推断跨文件ID等价。

```json
{
  "schema": 2,
  "artifacts": [
    {"name":"level","source":"current.gil"},
    {"name":"library","source":"structures.gia"}
  ],
  "required_references": []
}
```

新建工程可以检查最终关卡及独立结构体库；已有工程迭代可以检查当前关卡及单独的参考GIL。两者使用各自文件实际身份，不复制旧游戏协议或对象ID。

需要保留的挂载可加入required_references，每项包含source、target和relation。例如将inspect返回的一条script_mount关系的这三个字段原样纳入清单。检查要求两端唯一且恰有一条该关系；关系消失、改指其他目标或重复均失败。空required_references仍执行全部内置引用检查，只是不增加工程专有要求。

反例：按同名脚本查询多个文件会产生歧义；修改输入但仍使用旧sha256拒绝；删掉必需脚本挂载失败；仅把relation改成graph_mount不能得到成功；损坏控件父级、根控件或模板引用，即使图审计通过也不能交付。

## 制作链与可迁移输入

produce schema 2在Lua嵌入及最终原生审计之后、模拟之前自动检查最终level.gil。可增加project.spec携带额外参考文件和必需关系：

```json
{
  "schema": 2,
  "level": {"spec":"level.json"},
  "project": {"spec":"project.json"},
  "portable": {}
}
```

此时project.json的artifacts必须恰有一项source为@level，它绑定本轮最终GIL，不能以无关参考文件代替。@level只能在produce已有最终产物时使用；独立project命令使用实际文件路径。已有工程可将level阶段替换为native的base/spec阶段，project合同相同。

project-report.json记录最终文件摘要、对象及引用，project_references阶段只有passed才允许提交。任何引用检查失败都撤销本轮暂存输出，原始输入和已有输出保持。project配置与外部参考文件进入输入依赖；portable收纳它们并在原工程目录不可用时重新执行检查。报告用于记录检查证据。字节比较以实际交付文件为准。

开发侧的 `test_project_index.py` 单独检查两套界面与脚本配置、两份原始 GIA 的结构体校准、两个存档布局、动态信号、同号对象、层级与挂载故障、多文件 CLI、必需关系，以及新建和已有两类关卡的制作与迁移重建。`editor` 和 `host` 始终保持 `not_checked`，人工导入后的回读证据单独记录。

[节点图变量声明与默认值](../graph-code/native-graph-variables.md)保留图作用域、类型和默认值摘要，并记录显式结构体消费者。静态读写消费者使用graph_variable_read/write关系，动态名称单列访问记录；动态目标、实体覆写及未显式保存的结构体身份仍列unindexed，不按形状推断迁移目标。

对象身份、引用查询与修改计划可通过[公开回归](../../docs/contributing/development.md#复现已有工程的修改流程)复现。
