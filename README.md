# Genshin-UGC

让 AI 助手参与《原神》千星奇域创作。用它查节点和 Lua API、制作界面素材，也能读取已有地图、检查挂载关系并另存局部修改。

**当前版本 `4.1.2`** · 完整安装包面向 Windows x64 · 非官方社区项目

[下载完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.1.2/Genshin-UGC-4.1.2-windows-x64.zip) · [安装指南](docs/installation.md) · [使用文档](docs/README.md)

## 安装并试一次查询

确认本机已有 Python、Node.js 和可用的 `codex` 命令，然后在 PowerShell 运行下方命令。用 Claude Code 时，将末尾改为 `-Agent claude-code`。[运行要求](docs/compatibility.md)

```powershell
& ([scriptblock]::Create((Invoke-RestMethod 'https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/v4.1.2/install.ps1'))) -Agent codex
```

选择一个项目目录和一个互不包含的输出目录。没有现成工程时，项目目录可以为空。安装后在新会话启用插件，按首次使用指南查询服务端的“启动定时器”。[首次使用与预期结果](docs/getting-started.md)

DeepSeek Harness、其他本地插件客户端，以及手动安装、更新和卸载见[安装指南](docs/installation.md)。只用终端可直接配置[独立运行环境](docs/runtime-environment.md)。

## 用于实际创作

- **接手已有工程**。读取 GIL 的实体、模板、图和脚本关系，生成局部修改计划并另存文件。[检查和修改 GIL](docs/examples.md#局部修改-gil)
- **制作逻辑、界面和素材**。查询节点签名、用项目声明快检并编译 Graph Code，检查和预览 Client Lua，试算 PNG 图元的控件预算。[按任务查找](docs/examples.md)
- **辅助原生 3D 制作**。查询模型，生成独立静态 GIA，布设原生物件，配置机关、玩法资源与 HUD。[原生场景](references/native-scene.md) · [三维实体](references/native-entity-transform.md) · [支持范围](docs/compatibility.md) · [开发路线](ROADMAP.md)

`main` 用于浏览与贡献源码。[版本记录](CHANGELOG.md)的 `Unreleased` 标记尚未进入正式下载包的改动。生成文件的编辑器导入和实际游戏表现以相应验证为准。

## 参与项目

[反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues/new/choose) · [参与贡献](CONTRIBUTING.md) · [技术参考](references/README.md)

项目代码采用 GPL-3.0-only，随包第三方内容适用各自的权利和许可。感谢 Ayaya、Beyond、Miliastra-knowledge、奇匠学院及社区贡献。[许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [来源清单](PUBLIC_SOURCES.json) · [安全问题](SECURITY.md)
