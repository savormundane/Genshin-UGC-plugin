# 审阅并另存一次 GIL 局部修改

将合成样例 [entrance.gil](entrance.gil) 复制到本机会话能读取的工程目录。另存还需独立输出位置。 [工程绑定](../../../docs/runtime-environment.md#连接-mcp-或切换工程)

## 只读查找关卡对象

> 请用千星奇域插件只读查看当前工程的 entrance.gil。查找 ActivationDelay，告诉我变量定义属于哪个模板、场景中哪个实例继承它，以及识别到的引用关系。

`project_inspect` 先查变量名，再定位模板和继承实例。结果应包含模板 ID **1086324737**（`0x40C00001`）、实例 ID **1077936129**（`0x40400001`）、继承关系和输入文件的 SHA-256。

## 审阅并另存

> 请把当前工程 entrance.gil 中入口机关模板的 ActivationDelay 默认值改为 12。先定位变量、所属模板和继承它的实例，给出待审计划和允许修改的范围。等我确认后再另存。

定位后用 `native_plan` 生成本次的 `plan.json`，绑定输入 SHA-256。审阅计划时确认只有一项操作，允许修改的顶层字段为 `4`。 [待审计划样例](review/plan.json)

确认计划只涉及所需变量后，再继续。

> 我确认刚才的计划。请按这份计划把 entrance.gil 另存为 edited/level.gil。核对原文件的 SHA-256、前后差异和写入值，并告诉我怎么用另存文件。

## 看到了什么

`native_apply` 应生成另存的 `level.gil`，应用报告记录 `ActivationDelay` 从 **7 改为 12**。用 `native_diff` 核对字段差异，再以 `project_inspect` 重新读取变量和继承关系。 [另存文件样例](edited/level.gil)

| 检查项 | 结果 |
| --- | --- |
| 输入文件 | 原始 `entrance.gil` 的 SHA-256 与应用前一致 |
| 另存文件 | SHA-256 与待审计划预计的结果一致 |
| [前后差异](diff.json) | 顶层只变动字段 `4`，保护范围内的字节一致 |
| 新文件回读 | 变量值摘要与差异报告一致，继承实例仍指向该模板变量 |

用 `native_plan` 返回的 `outputs_sha256["plan.json"]` 给 `native_apply` 的 `plan_sha256` 参数提供文件校验值。计划和应用报告中名为 `plan_sha256` 的字段记录计划内容的校验值。 [MCP 路径和校验值](../../../docs/mcp.md#文件路径和校验值)

## 接下来怎么用

将自己这次另存的 GIL 导入编辑器，检查变量值和实际挂载。复现时使用本次工具返回的标识和校验值，选择一个新的输出目录。 [关卡复核步骤](../../../references/gil/native-changes.md#人工再导出核对) · [工具调用顺序](../../../references/gil/native-changes.md#审阅并另存已有工程)

随附的计划、另存文件和差异报告保留 [v1.0.0](https://github.com/savormundane/miliastra-wonderland-plugin/tree/v1.0.0) 的文件回读与差异检查记录。编辑器导入和游戏内运行按自己的关卡另行验证。
