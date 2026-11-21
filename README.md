# Genshin-UGC

**让 AI 助手参与《原神》千星奇域创作：查平台资料，写节点和 Lua，处理工程文件与素材。**

Genshin-UGC 把五个领域的 Skill、可追溯的平台资料和本地工具装进同一个插件。你描述制作目标，助手根据工程与平台资料调用工具，交付代码、文件和必要的检查结果。

**当前版本 `4.1.0`** · Windows x64 · Codex / Claude Code / DeepSeek Harness / 通用 Agent Plugins 接入 · 社区项目，独立于米哈游

[**开始使用**](docs/getting-started.md) · [下载完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.1.0/Genshin-UGC-4.1.0-windows-x64.zip) · [使用文档](docs/README.md) · [开发路线](ROADMAP.md) · [反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues/new/choose)

## 能帮你完成什么

| 你的任务 | 提供的输入 | 可以得到的结果 |
| --- | --- | --- |
| 看懂、接手已有工程 | 工程目录或 `.gil` 文件 | 模板、实体、节点图与资源引用的只读报告 |
| 编写节点逻辑 | 玩法规则、目标对象与平台版本 | 节点和端口查询、Graph Code、编译产物与连接检查 |
| 制作客户端界面 | 控件目标、已有脚本或交互要求 | Client Lua 源码、API 查询、源码装配与检查 |
| 修改或比较工程文件 | 原始 GIL、明确的修改目标 | 差异报告、局部修改计划、另存的文件与回读结果 |
| 制作图像素材 | PNG、矩形预算或分层素材 | 图元数据、Lua、软件预览、误差与成本报告 |

五个领域共享协议、多人会话、存储、动画和制作工具，助手按任务组合使用。每项能力的输入、产出和后续操作见[使用示例](docs/examples.md)。

### 看一个实际产物

[蓝金徽章案例](examples/hello-assets/README.md)包含原始 PNG、制作命令、Lua 数据、预览和报告。下图是插件实际生成的软件预览：128×128 输入转换成 **9 个矩形**，预算为 16 个，Lua 数据为 245 字节。

![插件实际生成的蓝金徽章软件预览](examples/hello-assets/generated/preview.png)

这是用于看清输入、成本和产物格式的最小案例。已有 4.1.0 工具可以处理[示例输入](examples/hello-assets/input.png)；示例文件随当前源码提供，尚未收入已发布的 4.1.0 ZIP。

### 为什么把这些能力放在一起

- **根据资料制作。** 节点签名、客户端 API 和平台版本规则有明确来源，查询与制作使用同一套资料。
- **接着已有工程做。** 读取真实对象和脚本映射，按支持的操作修改并另存文件，保留原始输入。
- **交付可继续使用的成果。** 除了建议，还可以交付源码、GIA/GIL、素材和报告；按本次任务选择检查。

本地检查与软件预览说明它们覆盖的结果；编辑器导入和游戏内表现另行判断。完整范围见[运行要求与支持范围](docs/compatibility.md)。

## 安装

需要 Windows x64、Python、Node.js 和对应 AI 客户端，具体版本见[运行要求](docs/compatibility.md)。首次安装联网下载锁定的 Python 依赖。

**Codex**：确认 `codex` 命令可用，在 PowerShell 运行：

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.0/install.ps1'))) -Agent codex
```

**Claude Code**：确认 `claude` 命令可用，将末尾参数改为 `-Agent claude-code`。

安装时选择一个工程目录和一个输出目录，例如 `C:\Qianxing\project` 与 `C:\Qianxing\outputs`。**还没有工程也可以先建两个空目录试用**；两个目录不能互相包含。装完后新开会话并启用插件。

| 其他使用方式 | 操作入口 |
| --- | --- |
| DeepSeek Harness | [准备 Cordis Bundle 并加载](docs/installation.md) |
| 支持 Agent Plugins 的客户端 | [准备本地插件目录并导入](docs/installation.md) |
| 只用 CLI，或手动解压完整 ZIP | [配置独立运行环境](docs/runtime-environment.md) |
| 更新、回退、卸载或排查安装问题 | [安装指南](docs/installation.md) |

普通使用者下载 **Release 的完整 Windows ZIP**；GitHub 自动生成的 `Source code` 包主要用于阅读和开发。完整安装步骤与各客户端差异都集中在安装指南。

## 第一次使用

无需准备私人地图，先把下面这段发给已启用插件的助手：

> 请调用 Genshin-UGC 的 `nodes_lookup` 查询服务端“启动定时器”节点。告诉我各输入端口的类型，并解释定时器序列 `[1, 3, 5, 7]` 的含义。

工具返回的输入应包含目标实体、定时器名称、是否循环和浮点数列表形式的定时器序列。这个序列表示从启动起第 1、3、5、7 秒触发事件。具体返回结构与下一步的素材任务见[首次使用指南](docs/getting-started.md)。

已经有工程时，从一个具体目标开始，例如“只读检查这张地图的挂载关系”或“把这张图标转换成矩形素材”。不用先读完所有技术资料。

## 支持哪些创作

- **2D 与界面制作**：节点逻辑、客户端 Lua、图元、动画及相关工程文件处理。
- **原生 3D 场景开发辅助**：已有实体、运动器、镜头、碰撞等平台资料、节点能力和部分声明配置检查。自动写入与生成目前只覆盖已实现的结构，完整 3D 场景生成仍是[后续方向](ROADMAP.md)。
- **已有工程维护**：查询、诊断、差异比较和已支持字段的局部修改。未知格式与字段按工具合同处理。

完整发行包以 Windows x64 为目标。客户端接入方式、其他系统和各项检查的适用范围见[运行要求与支持范围](docs/compatibility.md)。

## 找文档、提建议、参与开发

| 你现在想做什么 | 去哪里 |
| --- | --- |
| 安装后开始做第一个任务 | [开始使用](docs/getting-started.md) |
| 按任务寻找教程与命令 | [使用文档](docs/README.md) |
| 查询平台规则、API 与制作合同 | [技术参考](references/README.md) |
| 看下一步重点、认领具体工作 | [开发路线](ROADMAP.md) · [Issues](https://github.com/savormundane/Genshin-UGC-plugin/issues) |
| 报错、提需求或指出文档看不懂 | [反馈入口](https://github.com/savormundane/Genshin-UGC-plugin/issues/new/choose) |
| 修改代码、资料或文档 | [贡献指南](CONTRIBUTING.md) · [项目结构](docs/contributing/architecture.md) |
| 了解已经发布了什么 | [版本记录](CHANGELOG.md) · [Releases](https://github.com/savormundane/Genshin-UGC-plugin/releases) |

欢迎分享具体使用场景与卡住的步骤。无法判断问题属于哪个技术领域也可以反馈；不需要先学会所有术语。

## 致谢与许可

感谢 [Ayaya](https://github.com/AyayaXiaowan/Ayaya_Miliastra_Editor)、[miliastra-beyond-simulator](https://github.com/1475505/miliastra-beyond-simulator)、[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)、[GEIMG](https://docs.lumkfs.cn/GEIMG-WIKI/Download/)、奇匠学院及社区贡献的工具、资料与研究。

自有代码采用 GPL-3.0-only，第三方内容保留各自的权利、许可与署名。[许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [来源清单](PUBLIC_SOURCES.json) · [安全问题](SECURITY.md)
