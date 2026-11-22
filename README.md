# Genshin-UGC

让 AI 助手参与《原神》千星奇域创作。用它查节点和 Lua API、制作界面素材，也能读取已有地图、检查挂载关系并另存局部修改。

**当前版本 `4.1.2`** · 完整安装包面向 Windows x64 · 非官方社区项目

[下载完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.1.2/Genshin-UGC-4.1.2-windows-x64.zip) · [安装指南](docs/installation.md) · [使用文档](docs/README.md)

## 安装

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

在 **插件 → 添加插件** 粘贴下方地址，直接安装 **Genshin-UGC**。

```text
git+https://github.com/savormundane/Genshin-UGC-plugin.git#main&path:/marketplace/genshin-ugc
```

[DSH 市场安装](docs/installation.md#从市场安装)

其他兼容客户端可参考 [Agent Plugins 通用导入](docs/installation.md#agent-plugins)。

从市场或 DSH 直装后，工程读写、编译和素材处理还需要[安装本地运行环境](docs/installation.md#安装本地运行环境)。各客户端可共用同版本的环境。

[PowerShell 安装](docs/installation.md#powershell-安装) · [完整 ZIP 安装](docs/installation.md#手动接入) · [独立使用 CLI](docs/runtime-environment.md)

## Skills

| Skill | 适用任务 |
| --- | --- |
| [工程检查](skills/qianxing-editor/SKILL.md) | 查找关卡里的实体、模板和挂载关系。 |
| [Graph Code](skills/qianxing-graph-code/SKILL.md) | 确认节点签名，编写并检查节点图。 |
| [Client Lua](skills/client-controls-lua/SKILL.md) | 查询客户端 API，检查界面脚本。 |
| [GIL](skills/qianxing-gil/SKILL.md) | 审阅局部修改计划，另存 GIL 并核对差异。 |
| [素材](skills/qianxing-assets/SKILL.md) | 将 PNG 转成图元，比较候选方案的效果和控件预算。 |

## 参与项目

[反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues/new/choose) · [参与贡献](CONTRIBUTING.md) · [技术参考](references/README.md) · [版本记录](CHANGELOG.md)

项目代码采用 GPL-3.0-only，随包第三方内容适用各自的权利和许可。感谢 Ayaya、Beyond、Miliastra-knowledge、奇匠学院及社区贡献。[许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md) · [来源清单](PUBLIC_SOURCES.json) · [安全问题](SECURITY.md)
