# 工程只读诊断

在终端执行 `python scripts/qianxing.py diagnose CHECKS.json --format json`，需要纯文本时使用 `--format text`。MCP 的 `diagnose` 接收配置文件路径和 SHA-256，使用同一套检查及目录访问规则。诊断只读工程文件，不运行项目 Lua 或构建。

```json
{"schema":1,"checks":[{"kind":"environment"},{"kind":"lua","source":"client/main.lua"},{"kind":"asset","source":"assets/icon/asset.json","budget":{"controls":80}}]}
```

路径相对配置文件。`kind` 支持 environment、lua、native、asset；lua可提供已有客户端 `contract`，native读取GIL并执行现有语义审计。输出记录输入摘要、各项详情、严重程度、覆盖范围和分层状态。必需检查失败退出2，未知覆盖保持 `not_checked`；未执行其他检查不填通过。

UI开销提示从Lua语法树寻找更新回调中的创建/属性更新调用，包含源行；接收对象或执行频率可能未知，因此仅为风险提示。`controls` 是项目配置的控件预算。平台上限和实际帧率须另行核对。键盘、触屏和真实设备体验仍需实测。

人工证据通过可选 `manual_evidence` 文件关联：

```json
{"schema":1,"records":[{"artifact":"level.gil","sha256":"实际64位摘要","layer":"host","status":"passed","environment":"设备与客户端版本","source":"对应运行记录","scope":"实际操作及观察范围"}]}
```

layer仅允许editor、host、user_acceptance；status支持passed、failed、not_checked、not_applicable。摘要与当前产物不匹配时，工具保留原始记录，将对应结果标为待验。人工报告须关联实际产物，并与工具执行的离线检查和软件预览分别列出。

依赖及安装见[独立运行环境](../../docs/runtime-environment.md)。未知schema、未知检查类型和MCP越界依赖拒绝。通常只列此次修改涉及的检查；完整交付使用现有全套验证入口。该诊断无需工程新增固定目录或改造生成链。

## 交付文件与清单不一致

先确定首个失败的断言、生成器、输入、工具及已产生的输出；执行命令前确认写入位置。用 `verify DIRECTORY --artifacts-only` 核对交付文件和清单的摘要。源码摘要、规则摘要和产物摘要覆盖的对象可能不同，版本号相同也无法确认来自同一次构建。

| 现象 | 核对 |
| --- | --- |
| 源码、Lua、GIL 或资源摘要不同 | 查构建声明的实际输入、最终内嵌正文与挂载。修正源配置后在新目录生成，回读预期变化和受保护字段。 |
| 证据过期 | 查源码、后端、用例和报告范围；按[验证证据](validation-evidence.md)重跑受影响的检查。 |
| 未找到工具或版本不受支持 | 查声明依赖、路径基准和工具清单，确认是配置遗漏还是实现范围。 |
| 独立重建有差异 | 核对随附输入、后端指纹和文件用途，定位路径、时间或排序造成的差异。 [可迁移重建](portable-delivery.md) |

用[实际产物的验证记录](validation.md#交付反馈)报告问题位置、修复和本次检查结果。只读诊断不执行项目生成器；需要在新目录重建时使用[已声明的制作链](produce.md)。
