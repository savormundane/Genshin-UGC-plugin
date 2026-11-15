# Genshin-UGC

版本：3.6.0

面向《原神》千星奇域的开发工具包，包含五个核心Skill、共享参考资料、统一CLI与18项本地MCP操作。

| 技术领域 | 能力 |
| --- | --- |
| Editor | 工程对象、实体与模板、组件配置、平台规则和资源关联 |
| Graph Code | 节点图、复合节点、端口类型、执行流与数据流、编译 |
| Client Lua | 控件API、输入、生命周期、动画和单文件源码装配 |
| GIL | 原生容器检查、语义差异、安全修改、挂载、组装与回读 |
| Assets | 图像与图元转换、颜色和几何检查、成本分析与软件预览 |

共享工具覆盖协议、多人状态、存储、诊断、实验和可重建交付；包含可选Beyond模拟器及Ayaya无界面工具链。使用入口见[资料索引](references/README.md)，环境与CLI调用见[运行环境](references/runtime-environment.md)。

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
