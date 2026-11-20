# Genshin-UGC

> 面向《原神》千星奇域创作者的社区开发工具包：让 AI Agent 按平台能力查资料、检查工程、生成与验证可交付文件。非米哈游官方项目。

**导航：** [安装](#快速安装) · [使用场景](#从需求到结果) · [支持范围](#支持环境与验证边界) · [文档与参与](#文档与参与)

**4.0.0 · 《原神》千星奇域开发工具包**

[下载完整 Windows ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.0.0/Genshin-UGC-4.0.0-windows-x64.zip) · [所有版本](https://github.com/savormundane/Genshin-UGC-plugin/releases)

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

安装后，在已配置的客户端中描述目标，并让 Agent 明确引用的资料、生成文件和验证范围：

| 任务 | 示例提问 |
| --- | --- |
| 工程诊断 | “先只读检查这个千星奇域项目的实体、组件、资源引用，列出问题与依据。” |
| 节点逻辑 | “为这个玩法设计 Graph Code 节点流程，检查端口类型与数据流，再说明可交付文件。” |
| 客户端 Lua | “查询当前 Client Lua API 后实现控件交互，检查生命周期与输入限制。” |
| GIL 修改 | “比较原始 GIL 与目标修改，保留未知字段，并回读检查变更。” |
| 素材制作 | “检查这张图片能否转换为目标图元格式，先给出限制、成本与可预览结果。” |

这些是**输入示例**，不代表每种任务均经编辑器导入或游戏宿主实测。工具检查与实机验收的边界见[验证说明](references/validation.md)，更多示例见[使用场景](docs/examples.md)。

## 快速安装

完整工具链支持 **Windows x64**。准备 Python 3.11–3.12、Node.js 22+ 和所选客户端。DeepSeek Harness `0.2.2-rc.5` 需要 Node.js 24.9 或以上。

在 PowerShell 中运行一条命令：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.0.0/install.ps1'))) -Agent codex
```

把 `-Agent` 参数改为所选入口。

| 客户端或协议 | 参数 | 注册方式 |
| --- | --- | --- |
| Codex | `codex` | 安装器调用 Codex 插件命令 |
| Claude Code Plugin | `claude-code` | 安装器调用 Claude Code 插件命令 |
| Agent Plugins 1.0.0 | `agent-plugins` | 在兼容客户端中导入准备好的插件目录 |
| DeepSeek Harness Cordis | `deepseek-harness` | 在目标 profile 中添加准备好的 Bundle |

详见[宿主原生注册](references/installation.md#宿主原生注册)。首次会询问现有项目目录和独立输出目录，也可传入 `-Project`、`-Outputs` 和 `-Python`。Python 依赖首次安装需要联网；使用锁定版本并安装到插件专用环境。

安装器下载固定版本 ZIP，从 GitHub Release 读取 ZIP 的 SHA-256 并校验，再准备完整插件和专用运行环境。Codex 与 Claude Code 使用宿主原生命令注册；另外两种入口会输出待导入目录。客户端仍可能要求启用或信任本地 MCP。

也可以先下载[完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/tag/v4.0.0)，解压查看其中的 `install.ps1`。从 GitHub Release 附件详情取得 ZIP 的 SHA-256，保留原 ZIP 并在解包的插件目录运行：

```powershell
.\install.ps1 -Agent codex -Archive ..\Genshin-UGC-4.0.0-windows-x64.zip -Sha256 '<GitHub Release 显示的 ZIP SHA-256>'
```

安装中断后，保留版本目录并以相同版本、ZIP 摘要、客户端及目录参数加 `-Resume`。Codex 可以核对实际注册并继续已登记的激活，已完成的安装使用回退或新版本目录。SHA-256 用于内容一致性检查。详见[安装恢复](references/installation.md#失败后续装)。

## 首次使用

安装请选 Release 中的完整 ZIP。GitHub 自动生成的 **Source code (zip/tar.gz)** 是标签源码快照，不是安装器要求的 `Genshin-UGC/` 布局，也不适用于 `-Archive` 参数。

1. 确认客户端能发现五个 Skill 和本插件 MCP 工具。
2. 请 Agent 查询一个已知 API 或对指定项目做诊断，再执行文件制作。
3. 输出写入安装时选择的独立目录；原始 GIL 不作为默认覆盖目标。

也可解压 ZIP 后直接使用 CLI，配置方法见[独立运行环境](references/runtime-environment.md)与[安装说明](references/installation.md)。

## 支持环境与验证边界

| 项目 | 边界 |
| --- | --- |
| Windows x64 | 完整包的目标平台；包含平台相关模拟器依赖 |
| Codex | 使用现有 marketplace 和原生插件命令 |
| Claude Code Plugin | 原生清单与 stdio 配置；通过安装器注册或由宿主加载已配置目录 |
| Agent Plugins 1.0.0 | 兼容具备 Skills 和本地 stdio MCP 的宿主；从完整目录导入 |
| DeepSeek Harness Cordis | `0.2.2-rc.5` 适配目标；使用原生 Bundle 安装，Node.js 24.9 或以上 |
| 其他平台 | 可阅读资料、按各工具的环境要求运行 CLI |

静态检查、离线 Lua／节点模型、软件预览、编辑器导入、游戏宿主表现和用户验收分别判断。安装器的 MCP 查询与 PNG 检查不代表游戏实测，也不证明所有 API 都被模拟器实现。

## 更新与卸载

安装不会后台自动更新。新版本发布后，运行该版本安装命令；每个版本保留独立目录，拒绝覆盖已有同版本目录。详细的回退、卸载、失败重试和手动安装见[安装说明](references/installation.md)。

## 常见问题

- **找不到 Python？** 使用 `-Python '你的 Python 可执行文件路径'`；Windows 应用商店占位命令不等于已安装解释器。
- **客户端没有发现插件？** 重启客户端，检查其插件列表和 MCP 状态；不要把命令返回成功视为宿主加载证明。
- **输出目录为什么不能在项目里？** 当前 MCP 的读取与写入根目录合同要求两者分离。
- **可以直接加载任意 PNG 或模拟全部游戏行为吗？** 不可以；转换和原生字段支持以已校准格式及官方 API 为依据，未知部分明确拒绝或保留待验。

## 文档与参与

- [开发者文档入口](docs/README.md)：项目结构、适配状态与典型任务
- [维护与发布](docs/maintenance.md)：本地打包、版本核对与手动发布
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
- [没空放肆 / GEIMG](https://docs.lumkfs.cn/GEIMG-WIKI/Download/)：[拟L2D知识库](https://docs.lumkfs.cn/GEIMG-WIKI/EG-L2D/)、附件与历史格式参考；当前拟合不依赖GE程序，原资料声明保留。
- [8itlab / genshin-miliastra-mcp](https://github.com/8itlab/genshin-miliastra-mcp)：千星工具与MCP方案研究参考。
- [genshin-ts](https://github.com/josStorer/genshin-ts)、[NodeEditorPack](https://github.com/Wu-Yijun/Genshin-Impact-Miliastra-Wonderland-Code-Node-Editor-Pack)、Genshin-Impact-UGC-File-Converter及[perfectPixel](https://github.com/theamusing/perfectPixel)：Ayaya所记录的定义、转换与图像处理相关成果。
- [script-1024 / genshin-miliastra-file-format](https://github.com/script-1024/genshin-miliastra-file-format)、[luern0313 / UGC-File-Generate-Utils](https://github.com/luern0313/UGC-File-Generate-Utils)：GIL/GIA格式及生成工具研究参考。
- [luaparse](https://github.com/fstirlitz/luaparse)、Fengari、PixiJS、protobufjs、NAPI-RS Canvas及其他运行依赖：详见[第三方声明](THIRD_PARTY_NOTICES.md)。
- 米哈游[奇匠学院](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhtakr07vej4)：平台与客户端API原始资料。

## 许可证与联系

本项目自有代码采用[GNU GPL v3.0](LICENSE)（GPL-3.0-only）。第三方代码、工具、文档及素材保留各自权利与许可；根许可证不替它们重新授权。

部分第三方文件目前尚未核实再分发授权，不能据此视为GPL内容；具体范围、来源与状态见[第三方声明](THIRD_PARTY_NOTICES.md)及[来源清单](PUBLIC_SOURCES.json)。公开可下载、署名或收录均不表示原作者背书。

如发现来源、署名或许可记录存在遗漏，请通过[Issue](https://github.com/savormundane/Genshin-UGC-plugin/issues)提供相关文件路径和依据，以便核实、更正或移除。

