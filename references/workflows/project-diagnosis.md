# 工程只读诊断

入口：`python scripts/qianxing.py diagnose CHECKS.json --format json`；文本输出使用 `--format text`。MCP `diagnose` 接收配置路径和SHA-256，复用相同核心及根目录边界。不会执行项目Lua或触发制作。

```json
{"schema":1,"checks":[{"kind":"environment"},{"kind":"lua","source":"client/main.lua"},{"kind":"asset","source":"assets/icon/asset.json","budget":{"controls":80}}]}
```

路径相对配置文件。`kind` 支持 environment、lua、native、asset；lua可提供已有客户端 `contract`，native读取GIL并执行现有语义审计。输出记录输入摘要、各项详情、严重程度、覆盖范围和分层状态。必需检查失败退出2，未知覆盖保持 `not_checked`；未执行其他检查不填通过。

UI开销提示从Lua语法树寻找更新回调中的创建/属性更新调用，包含源行；接收对象或执行频率可能未知，因此仅为风险提示。项目controls预算是建议，不是官方硬限，也不是FPS测量。键盘、触屏和真实设备体验仍需实测。

人工证据通过可选 `manual_evidence` 文件关联：

```json
{"schema":1,"records":[{"artifact":"level.gil","sha256":"实际64位摘要","layer":"host","status":"passed","environment":"设备与客户端版本","source":"对应运行记录","scope":"实际操作及观察范围"}]}
```

layer仅允许editor、host、user_acceptance；status支持passed、failed、not_checked、not_applicable。摘要过期自动显示未验证，原始记录不改写；人工报告只作明确归属的记录，不冒充工具亲自观察。离线、软件预览与人工层分别报告。

依赖及安装见[独立运行环境](../../docs/runtime-environment.md)。未知schema、未知检查类型和MCP越界依赖拒绝。通常只列此次修改涉及的检查；完整交付使用现有全套验证入口。该诊断无需工程新增固定目录或改造生成链。
