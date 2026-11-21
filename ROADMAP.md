# 开发路线

Genshin-UGC 的目标是让创作者借助 AI 完成真正可继续编辑的千星奇域作品：基于平台资料理解工程、实现逻辑、生成或修改文件，并清楚说明尚需在编辑器或游戏内完成的步骤。

这里记录能力方向，不是版本承诺。已发布功能以 [README](README.md)、[使用文档](docs/README.md)和[Releases](https://github.com/savormundane/Genshin-UGC-plugin/releases)为准。

## 当前基础

- **五个核心领域**：工程检查（Editor）、Graph Code、Client Lua、GIL、Assets；协议、存储、多人和诊断属于共享能力。[能力索引](references/skill-map.md)
- **平台知识与版本**：官方资料索引、节点定义、客户端 API 及版本化规则。[平台资料](references/platform-profiles.md)
- **本地制作工具**：工程诊断、节点编译、Lua 装配、原生文件局部修改、素材处理及组合交付。[命令入口](scripts/README.md)
- **分发**：Windows x64 完整包与 Codex、Claude Code 等客户端接入。[安装说明](docs/installation.md)

## 优先方向

### 更完整地修改已有工程

继续扩展有依据的 GIL/GIA 修改、节点逻辑和 Lua 挂载能力，减少创作者在多个工具之间手动搬运的工作。每项能力需要明确输入工程、目标对象、修改范围和可继续编辑的输出，而不只是生成一段演示代码。

### 原生 3D 场景与交互

从已有工程中的具体实体运动任务开始，逐步覆盖运动器、镜头及碰撞等常见创作需求。现有平台资料与节点查询能力不等于完整场景生成。[相关任务 #3](https://github.com/savormundane/Genshin-UGC-plugin/issues/3)

### 真实创作成果与可复用性

仅展示具有实际创作价值的案例，提供清楚的输入、完整产物、复现方式和验证范围；简单工具冒烟结果不作为作品展示。外部贡献者的最小复现入口见[任务 #4](https://github.com/savormundane/Genshin-UGC-plugin/issues/4)。

## 参与

功能缺口、实际使用问题和创作需求可通过 [Issues](https://github.com/savormundane/Genshin-UGC-plugin/issues) 讨论；代码与文档贡献请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。
