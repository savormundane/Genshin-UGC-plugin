# 兼容与运行要求

以下入口共用五个 Skills 和本地 stdio MCP。

| 目标 | 当前公开说明 |
| --- | --- |
| Windows x64 | 完整发行包目标平台 |
| Python | 3.11–3.12，安装时创建独立环境 |
| Node.js | 22+；DeepSeek Harness 需要 24.9 或以上 |
| Agent Plugins 1.0.0 | 宿主须支持 Skills 与 stdio MCP，使用 `-Agent agent-plugins` 准备目录 |
| DeepSeek Harness Cordis | `0.2.2-rc.5`，使用 `-Agent deepseek-harness` 准备 Bundle |
| Claude Code Plugin | 使用 `-Agent claude-code` 调用原生安装入口 |
| Codex | 使用 `-Agent codex` 调用原生安装入口 |

## 验证级别

1. **静态检查**：语法、配置、文件结构或规则检查通过。
2. **离线工具**：CLI / MCP / 软件模拟的结果经检查。
3. **编辑器导入**：目标文件已在千星奇域编辑器中导入核对。
4. **游戏宿主**：相关行为已在实际游戏环境运行检查。
5. **使用者验收**：玩法体验及目标需求由使用者确认。

低级别不能自动代替高级别。比如 PNG 软件预览不证明游戏 UI 的实际效果，GIL 能回读也不等于所有玩法逻辑通过。

每次提交验证报告应写清：平台与客户端版本、用例、完成的级别、未完成的级别及已知限制。详细原则见 [验证依据](../references/validation.md)。
