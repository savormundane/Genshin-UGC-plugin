# Genshin-UGC

让 AI 助手参与《原神》千星奇域创作。用它查节点和 Lua API、制作界面素材，也能读取已有地图、检查挂载关系并另存局部修改。

**当前版本 `4.1.2`** · 完整安装包面向 Windows x64 · 非官方社区项目

[下载完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.1.2/Genshin-UGC-4.1.2-windows-x64.zip) · [安装指南](docs/installation.md) · [使用文档](docs/README.md)

## 安装并试一次查询

### Codex

```text
codex plugin marketplace add savormundane/Genshin-UGC-plugin
codex plugin add genshin-ugc-public@genshin-ugc
```

### Claude

有 `claude` 命令时可直接在终端安装，也可在 [Claude 插件界面](docs/installation.md#claude)添加同一个市场。

```text
claude plugin marketplace add savormundane/Genshin-UGC-plugin
claude plugin install genshin-ugc-public@genshin-ugc
```

### DeepSeek Harness

在 **Discover → Add index source** 添加下方地址，然后安装 **Genshin-UGC**。[DSH 市场步骤](docs/installation.md#deepseek-harness)

```text
https://raw.githubusercontent.com/savormundane/Genshin-UGC-plugin/main/marketplace/dsh-index.json
```

其他兼容客户端可参考 [Agent Plugins 通用导入](docs/installation.md#agent-plugins)。

市场安装后，按指南[一次性准备本地工具](docs/installation.md#一次性准备本地工具)。各客户端可共用同版本的运行环境。准备完成后在新会话查询服务端「启动定时器」，确认工具连通。[首次使用与预期结果](docs/getting-started.md)

[PowerShell 安装](docs/installation.md#powershell-安装) · [完整 ZIP 安装](docs/installation.md#手动接入) · [独立使用 CLI](docs/runtime-environment.md)

## 用于实际创作

- **接手已有工程**。读取 GIL 的实体、模板、图和脚本关系，生成局部修改计划并另存文件。[检查和修改 GIL](docs/examples.md#局部修改-gil)
- **制作逻辑、界面和素材**。查询节点签名、用项目声明快检并编译 Graph Code，检查和预览 Client Lua，试算 PNG 图元的控件预算。[按任务查找](docs/examples.md)
- **辅助原生 3D 制作**。查询模型，生成独立静态 GIA，布设原生物件，配置机关、玩法资源与 HUD。[原生场景](references/native-scene.md) · [三维实体](references/native-entity-transform.md) · [支持范围](docs/compatibility.md) · [三维运动任务](https://github.com/savormundane/Genshin-UGC-plugin/issues/3)

`main` 用于浏览与贡献源码。[版本记录](CHANGELOG.md)的 `Unreleased` 标记尚未进入正式下载包的改动。生成文件的编辑器导入和实际游戏表现以相应验证为准。

## Skills

| Skill | 适用任务 |
| --- | --- |
| [工程检查](skills/qianxing-editor/SKILL.md) | 查找关卡里的实体、模板和挂载关系。 |
| [Graph Code](skills/qianxing-graph-code/SKILL.md) | 确认节点签名，编写并检查节点图。 |
| [Client Lua](skills/client-controls-lua/SKILL.md) | 查询客户端 API，检查界面脚本。 |
| [GIL](skills/qianxing-gil/SKILL.md) | 审阅局部修改计划，另存 GIL 并核对差异。 |
| [素材](skills/qianxing-assets/SKILL.md) | 将 PNG 转成图元，比较候选方案的效果和控件预算。 |

## 参与项目

[反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues/new/choose) · [参与贡献](CONTRIBUTING.md) · [技术参考](references/README.md)

项目代码采用 GPL-3.0-only，随包第三方内容适用各自的权利和许可。感谢 Ayaya、Beyond、Miliastra-knowledge、奇匠学院及社区贡献。[许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [来源清单](PUBLIC_SOURCES.json) · [安全问题](SECURITY.md)
