# Genshin-UGC

Genshin-UGC 是面向《原神》千星奇域创作者的非官方社区插件，为 AI 助手提供平台资料和本地工程工具，覆盖原生 3D 场景、节点图、客户端 Lua 和界面素材。

有现成关卡时，可以读取 GIL，查找实体、模板和挂载关系，审阅并另存局部修改。从创作需求开始时，可以搭建静态场景、编译节点图、编写控件脚本或生成图元，交付可继续编辑的文件。

## 安装

### 运行要求

完整工具支持 **Windows x64**。本地 MCP 需要 **Node.js 22+**，DeepSeek Harness 接入使用 **Node.js 24.9+**。启动器优先复用装好依赖的 **CPython 3.11–3.14** 环境，找不到时由 PATH 上的 `uv` 按锁文件准备。 [运行要求与支持范围](docs/compatibility.md#运行要求)

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
git+https://github.com/savormundane/Genshin-UGC-plugin.git#main
```

### 其他客户端

支持 Agent Plugins 和本地 MCP 的客户端，可按客户端提供的方式添加仓库市场或导入完整插件目录。 [Agent Plugins 安装说明](docs/installation.md#agent-plugins)

### 下载与离线安装

**当前版本 `4.1.2`**

手动安装请下载完整 ZIP，再按指南接入。指南也包含 PowerShell 备用安装、更新和回退。 [下载完整 ZIP](https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v4.1.2/Genshin-UGC-4.1.2-windows-x64.zip) · [手动安装](docs/installation.md#手动接入) · [版本记录](CHANGELOG.md)

## Skills

| Skill | 适用任务 |
| --- | --- |
| [Qianxing Editor](skills/qianxing-editor/SKILL.md) | 查看和配置关卡对象与原生界面，查询 API、编写和检查 [Client Lua](skills/qianxing-editor/SKILL.md#client-lua)。 |
| [Qianxing Graph Code](skills/qianxing-graph-code/SKILL.md) | 确认节点签名，编写并检查节点图。 |
| [Qianxing GIL](skills/qianxing-gil/SKILL.md) | 审阅局部修改计划，另存 GIL 并核对差异。 |
| [Qianxing Assets](skills/qianxing-assets/SKILL.md) | 将 PNG 转成图元，比较候选方案的效果和控件预算。 |

## 技术参考

平台版本规则、节点签名、Lua API、原生文件格式与制作流程可按主题查阅。需要在终端直接编译节点图、检查 GIL 或复现工具报错时，可以运行插件自带的命令行工具。 [技术参考索引](references/README.md) · [在终端运行工具](docs/runtime-environment.md#只用-cli)

## 参与项目

- **报告问题**。请说明所用客户端、插件版本、预期结果和实际报错。有可公开的最小复现时一并附上。 [反馈问题](https://github.com/savormundane/Genshin-UGC-plugin/issues/new/choose) · [安全问题报告](SECURITY.md)
- **交流与建议**。欢迎分享制作方法、交流插件用法，或讨论下一步值得补齐的能力。 [GitHub Discussions](https://github.com/savormundane/Genshin-UGC-plugin/discussions)
- **参与贡献**。欢迎修正文档、补充有版本依据的平台资料、提交可复现样本和修复代码。 [贡献指南](CONTRIBUTING.md)

## 致谢

- Ayaya 为节点图工具链提供了基础，Beyond 提供离线模拟和界面预览。 [Ayaya](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor) · [Beyond](https://github.com/1475505/miliastra-beyond-simulator)
- 感谢奇匠学院提供官方平台资料，也感谢 Miliastra-knowledge 对资料的整理。 [奇匠学院文档索引](references/official-index.md) · [Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)
- 感谢 GEIMG 的图元处理资料，以及社区公开分享的千星奇域文件格式研究。 [GEIMG 资料](https://docs.lumkfs.cn/GEIMG-WIKI/Download/) · [第三方声明](THIRD_PARTY_NOTICES.md)

## 许可证

本项目自有代码采用 GPL-3.0-only。随包的第三方代码、资料和素材保留各自的权利与许可。 [许可证](LICENSE) · [来源清单](PUBLIC_SOURCES.json)
