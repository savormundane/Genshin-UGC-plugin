# 千星奇域开发插件

Miliastra Wonderland 是面向原神「千星奇域」创作者的非官方 AI 辅助开发插件。它给 AI 助手提供带版本依据的平台资料和本地工程工具，覆盖原生 3D 场景、节点图、客户端 Lua 和界面素材。

可以直接查询节点、API 和平台规则。有现成关卡时，可以搜索 GIL 中的实体、模板和挂载关系，审阅并另存局部修改。从创作需求开始时，可以搭建静态场景、编译节点图、编写控件脚本或生成图元，交付可继续编辑的文件。

## Skills

| Skill | 适用任务 |
| --- | --- |
| [Qianxing Editor](skills/qianxing-editor/SKILL.md) | 查看关卡对象、对照 3D 布设并配置原生界面，查询 API、编写和检查 [Client Lua](skills/qianxing-editor/SKILL.md#client-lua)。 |
| [Qianxing Graph Code](skills/qianxing-graph-code/SKILL.md) | 确认节点签名，编写并检查节点图。 |
| [Qianxing GIL](skills/qianxing-gil/SKILL.md) | 审阅局部修改计划，另存 GIL 并核对差异。 |
| [Qianxing Assets](skills/qianxing-assets/SKILL.md) | 将 PNG 转成图元，比较候选方案的效果和控件预算。 |

## 安装

### 运行要求

完整工具目前仅支持 **Windows x64**。本地 MCP 需要 **Node.js 22+**，DeepSeek Harness 接入使用 **Node.js 24.9+**。启动器优先复用装好依赖的 **CPython 3.11–3.14** 环境，找不到时由 PATH 上的 `uv` 按锁文件准备。 [运行要求与支持范围](docs/compatibility.md#运行要求)

### Codex

```text
codex plugin marketplace add savormundane/miliastra-wonderland-plugin
codex plugin add miliastra-wonderland@miliastra-wonderland
```

### Claude

```text
claude plugin marketplace add savormundane/miliastra-wonderland-plugin
claude plugin install miliastra-wonderland@miliastra-wonderland
```

### DeepSeek Harness

在 **插件 → 添加插件** 粘贴下方地址，直接安装 **Miliastra Wonderland**。

```text
git+https://github.com/savormundane/miliastra-wonderland-plugin.git#main
```

### 其他客户端

支持 Agent Plugins 和本地 MCP 的客户端，可按客户端提供的方式添加仓库市场或导入完整插件目录。

[Agent Plugins 安装说明](docs/installation.md#agent-plugins)

### 源码下载

**当前版本 `1.0.0`**

[下载源码](https://github.com/savormundane/miliastra-wonderland-plugin/archive/refs/heads/main.zip) · [自行打包 ZIP](docs/installation.md#自行打包-zip) · [版本记录](CHANGELOG.md)

## 参与项目

- **报告问题**。请附客户端、插件版本、预期结果和报错，可附公开的最小复现。[反馈问题](https://github.com/savormundane/miliastra-wonderland-plugin/issues/new/choose) · [安全问题报告](SECURITY.md)
- **交流与建议**。欢迎分享制作方法、交流插件用法，或讨论下一步值得补齐的能力。[GitHub Discussions](https://github.com/savormundane/miliastra-wonderland-plugin/discussions)
- **参与贡献**。欢迎修正文档、补充有版本依据的平台资料、提交可复现样本和修复代码。[贡献指南](CONTRIBUTING.md)

## 更多文档

- **技术参考**。查阅平台版本规则、节点签名、Lua API、原生文件格式与制作流程。[技术参考索引](references/README.md) · [术语表](docs/glossary.md)
- **终端工具**。在终端直接编译节点图、检查 GIL 或复现工具报错。[在终端运行工具](docs/runtime-environment.md#只用-cli)
- **插件开发**。查看源码入口、按改动选择本地检查。[开发者文档](docs/contributing/README.md)

## 致谢

- Ayaya 为节点图工具链提供了基础，Beyond 提供离线模拟和界面预览。[Ayaya](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor) · [Beyond](https://github.com/1475505/miliastra-beyond-simulator)
- 感谢 Miliastra-knowledge 整理平台资料。[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge)
- 感谢 GEIMG 的图元处理资料。[GEIMG Wiki](https://docs.lumkfs.cn/GEIMG-WIKI/README/) 
- 感谢所有社区公开分享的千星奇域文件格式研究。[第三方声明](THIRD_PARTY_NOTICES.md)

## 许可证

本项目自有代码采用 GPL-3.0-only。随包的第三方代码、资料和素材保留各自的权利与许可。

[许可证](LICENSE) · [来源清单](PUBLIC_SOURCES.json)
