# Genshin-UGC

> 面向《原神》千星奇域创作者的社区开发工具包：让 AI Agent 按平台能力查资料、检查工程、生成与验证可交付文件。非米哈游官方项目。

**导航：** [安装](#快速安装) · [使用场景](#从需求到结果) · [支持范围](#支持环境与验证边界) · [文档与参与](#文档与参与)

**3.6.1 · 《原神》千星奇域开发工具包**

五个核心 Skill、可追溯平台资料、统一 CLI、18 项本地 MCP 操作，以及随包的离线工具与可选模拟器。

| 领域 | 可以做什么 |
| --- | --- |
| Editor | 工程对象、实体与模板、组件规则、资源关联 |
| Graph Code | 节点图、复合节点、端口类型、执行流与数据流、编译 |
| Client Lua | 控件 API、输入、生命周期、动画、单文件源码装配 |
| GIL | 容器检查、语义差异、安全修改、挂载、组装与回读 |
| Assets | 图像与图元转换、颜色和几何检查、成本分析、软件预览 |

协议、多人状态、存储、诊断和可重建交付由共享工具支持。入口见[资料索引](references/README.md)。这是社区工具，不是官方编辑器或官方 MCP 服务。

## 从需求到结果

安装后，在 Codex 或 Claude Code 中描述目标，并让 Agent 明确引用的资料、生成文件和验证范围：

| 任务 | 示例提问 |
| --- | --- |
| 工程诊断 | “先只读检查这个千星奇域项目的实体、组件、资源引用，列出问题与依据。” |
| 节点逻辑 | “为这个玩法设计 Graph Code 节点流程，检查端口类型与数据流，再说明可交付文件。” |
| 客户端 Lua | “查询当前 Client Lua API 后实现控件交互，检查生命周期与输入限制。” |
| GIL 修改 | “比较原始 GIL 与目标修改，保留未知字段，并回读检查变更。” |
| 素材制作 | “检查这张图片能否转换为目标图元格式，先给出限制、成本与可预览结果。” |

这些是**输入示例**，不代表每种任务均经编辑器导入或游戏宿主实测。工具检查与实机验收的边界见[验证说明](references/validation.md)，更多示例见[使用场景](docs/examples.md)。

## 快速安装

完整工具链当前支持 **Windows x64**。先安装 Python 3.10–3.12、Node.js 22+，以及 Codex 或 Claude Code；安装器不会替你安装全局软件。

在 PowerShell 中运行一条命令：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v3.6.1/install.ps1'))) -Agent codex
```

Claude Code 将末尾参数改成 `-Agent claude-code`。首次会询问现有项目目录和独立输出目录，也可传入 `-Project`、`-Outputs` 和 `-Python`。Python 依赖首次安装需要联网；使用锁定版本并安装到插件专用环境。

安装器下载固定版本 ZIP、校验 SHA-256、保留完整目录、配置运行环境，并调用客户端原生插件安装入口。不会仅复制 Skill，也不会修改其他插件的配置。安装后重启客户端；客户端仍可能要求启用或信任本地 MCP。

喜欢先检查脚本，可以从 [Release](https://github.com/savormundane/Genshin-UGC-plugin/releases/tag/v3.6.1) 下载 `install.ps1`、完整 ZIP 和 `SHA256SUMS.txt`，查看脚本后执行：

```powershell
.\install.ps1 -Agent codex -Archive .\Genshin-UGC-3.6.1-windows-x64.zip -Sha256 '<SHA256SUMS.txt 中的 ZIP 摘要>'
```

## 首次使用

1. 确认客户端能发现五个 Skill 和本插件 MCP 工具。
2. 请 Agent 查询一个已知 API 或对指定项目做诊断，再执行文件制作。
3. 输出写入安装时选择的独立目录；原始 GIL 不作为默认覆盖目标。

也可解压 ZIP 后直接使用 CLI，配置方法见[独立运行环境](references/runtime-environment.md)与[安装说明](references/installation.md)。

## 支持环境与验证边界

| 项目 | 边界 |
| --- | --- |
| Windows x64 | 完整包的目标平台；包含平台相关模拟器依赖 |
| Codex | 原生插件注册；实际加载以当前客户端检查为准 |
| Claude Code | 提供原生插件适配；未实测的客户端版本不宣称已验证 |
| 其他客户端或系统 | 可阅读资料、按需使用工具；不承诺完整运行兼容 |

静态检查、离线 Lua／节点模型、软件预览、编辑器导入、游戏宿主表现和用户验收分别判断。安装器的 MCP 查询与 PNG 检查不代表游戏实测，也不证明所有 API 都被模拟器实现。

## 更新与卸载

安装不会后台自动更新。新版本发布后，运行该版本安装命令；每个版本保留独立目录，拒绝覆盖已有同版本目录。详细的回退、卸载、失败重试和手动安装见[安装说明](references/installation.md)。

## 常见问题

- **找不到 Python？** 使用 `-Python '你的 Python 可执行文件路径'`；Windows 应用商店占位命令不等于已安装解释器。
- **客户端没有发现插件？** 重启客户端，检查其插件列表和 MCP 状态；不要把命令返回成功视为宿主加载证明。
- **输出目录为什么不能在项目里？** 当前 MCP 的读取与写入根目录合同要求两者分离。
- **可以直接加载任意 PNG 或模拟全部游戏行为吗？** 不可以；转换和原生字段支持以已校准格式及官方 API 为依据，未知部分明确拒绝或保留待验。

## 文档与参与

- [人类开发者文档入口](docs/README.md)：项目结构、适配状态与典型任务
- [资料与工作流索引](references/README.md)：平台知识、各领域技术指南及验证方法
- [参与贡献](CONTRIBUTING.md)：报告问题、提交资料修正、提出能力建议与 PR 流程
- [版本变更](CHANGELOG.md)：已公开版本的主要变化
- [安全问题反馈](SECURITY.md)：安全问题的非公开报告方式

欢迎通过 [Issues](https://github.com/savormundane/Genshin-UGC-plugin/issues) 反馈可复现问题。公开反馈请注意清除项目中的敏感信息。

## 致谢与来源

感谢以下作者与项目提供的代码、资料和技术研究：

- [AyayaXiaowang / Ayaya_Miliastra_Editor](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor)：Graph Code及GIA/GIL离线工具链。
- [1475505 / miliastra-beyond-simulator](https://github.com/1475505/miliastra-beyond-simulator)：客户端Lua及UI软件模拟后端。
- [1475505 / Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)：千星奇域文档整理与版本资料来源。
- [没空放肆 / GEIMG](https://docs.lumkfs.cn/GEIMG-WIKI/Download/)：[拟L2D知识库](https://docs.lumkfs.cn/GEIMG-WIKI/EG-L2D/)、附件及GE图像工具；对应文件的许可状态见下方声明。
- [8itlab / genshin-miliastra-mcp](https://github.com/8itlab/genshin-miliastra-mcp)：千星工具与MCP方案研究参考。
- [genshin-ts](https://github.com/josStorer/genshin-ts)、[NodeEditorPack](https://github.com/Wu-Yijun/Genshin-Impact-Miliastra-Wonderland-Code-Node-Editor-Pack)、Genshin-Impact-UGC-File-Converter及[perfectPixel](https://github.com/theamusing/perfectPixel)：Ayaya所记录的定义、转换与图像处理相关成果。
- [script-1024 / genshin-miliastra-file-format](https://github.com/script-1024/genshin-miliastra-file-format)、[luern0313 / UGC-File-Generate-Utils](https://github.com/luern0313/UGC-File-Generate-Utils)：GIL/GIA格式及生成工具研究参考。
- [luaparse](https://github.com/fstirlitz/luaparse)、Fengari、PixiJS、protobufjs、NAPI-RS Canvas及其他运行依赖：详见[第三方声明](THIRD_PARTY_NOTICES.md)。
- 米哈游[奇匠学院](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhtakr07vej4)：平台与客户端API原始资料。

## 许可证与联系

本项目自有代码采用[GNU GPL v3.0](LICENSE)（GPL-3.0-only）。第三方代码、工具、文档及素材保留各自权利与许可；根许可证不替它们重新授权。

部分第三方文件目前尚未核实再分发授权，不能据此视为GPL内容；具体范围、来源与状态见[第三方声明](THIRD_PARTY_NOTICES.md)及[来源清单](PUBLIC_SOURCES.json)。公开可下载、署名或收录均不表示原作者背书。

如发现来源、署名或许可记录存在遗漏，请通过[Issue](https://github.com/savormundane/Genshin-UGC-plugin/issues)提供相关文件路径和依据，以便核实、更正或移除。

