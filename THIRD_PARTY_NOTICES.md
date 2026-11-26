# 第三方声明

本项目自有代码采用 GPL-3.0-only。第三方代码、资料和素材适用各自声明的权利和许可。

## 随包代码

| 内容 | 来源与许可 | 本项目中的使用 |
| --- | --- | --- |
| Ayaya | [上游](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor)，[GPLv3](vendor/ayaya/LICENSE) | 选定的无界面子集；修改和文件摘要见[NOTICE](vendor/ayaya/NOTICE.md)与[VENDORED](vendor/ayaya/VENDORED.json) |
| Beyond | [上游](https://github.com/1475505/miliastra-beyond-simulator)，[GPL-3.0-only](vendor/beyond/LICENSE) | 无界面预览源码。上游提交见[修订锁](scripts/beyond-revision.json)，随包文件及其校验值见[bundle](vendor/beyond/bundle.json) |
| luaparse | Oskar Schöldström，[MIT](vendor/luaparse/LICENSE) | Lua语法解析器 |
| Genshin-Impact-UGC-File-Converter | にゃが，[MIT](vendor/ayaya/LICENSES/Genshin-Impact-UGC-File-Converter.MIT.txt) | Ayaya保留的转换器版权声明 |
| genshin-ts | josStorer，[MIT](vendor/ayaya/LICENSES/genshin-ts.MIT.txt) | Ayaya定义与报告相关来源 |
| NodeEditorPack | Wu-Yijun，[MIT](vendor/ayaya/LICENSES/NodeEditorPack.MIT.txt) | Ayaya节点定义相关来源 |
| perfectPixel | theAmusing，[MIT](vendor/ayaya/LICENSES/perfectPixel.MIT.txt) | Ayaya保留的图像处理相关声明 |

第三方模块的版权、许可证文本及原始头注释保留。GPL代码使用和分发应遵循其源码及通知义务；参考过一个项目不表示它的所有实现都被打包。Beyond 随包保留无界面预览的 Lua 执行、控件布局、场景和信号、GIA 读写及 Canvas 绘制源码。依赖版本和原始文件摘要见 [PUBLIC_SOURCES.json](PUBLIC_SOURCES.json)。

## GEIMG 资料

没空放肆授权以 MIT 许可分发随包的 GEIMG 手册、知识快照及拟 L2D 案例中由作者提供的正文、脚本和模板。授权由插件维护者取得，适用文件以 [PUBLIC_SOURCES.json](PUBLIC_SOURCES.json) 的 `licensed_files` 为准。拟 L2D 的文件名与章节对应上游案例，随包文件以本地摘要标识。 [GEIMG Wiki](https://docs.lumkfs.cn/GEIMG-WIKI/) · [拟 L2D 案例](https://docs.lumkfs.cn/GEIMG-WIKI/EG-L2D/) · [MIT 许可全文](references/assets/geimg/LICENSE.txt)

## 原始资料与授权待核项

| 内容 | 已知来源 | 当前状态 |
| --- | --- | --- |
| 客户端API整理文档 | [相关官方页面](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhtakr07vej4) | 本地整理稿来源与再分发许可待核 |
| 官方正文及版本镜像 | 米哈游；[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge) | 平台资料权利与工具代码许可分开；未确认镜像正文的再分发许可 |

本节表格对应 [PUBLIC_SOURCES.json](PUBLIC_SOURCES.json) 中的 `permission_unverified_files`。第三方资料中的实测数字仅适用于原作者对应的环境和样本。

## 参考研究

内置的[音效与特效图鉴](references/platform/resource-catalogue.md#查询音效和特效)筛选并归一化了 8itlab 和贡献者采集的面板名称、编号、类别及标示时长。目录保留固定提交、来源与版本依据。随包内容为文字观察，米哈游保留音频、图像和游戏素材的权利。 [上游第三方声明](https://github.com/8itlab/genshin-miliastra-mcp/blob/70470757d6fcb319c5afec13b178c87f2d8d54b3/THIRD_PARTY_NOTICES.md) · [上游 MIT 许可](references/platform/8itlab-MIT.txt)

感谢[genshin-miliastra-mcp](https://github.com/8itlab/genshin-miliastra-mcp)、[genshin-miliastra-file-format](https://github.com/script-1024/genshin-miliastra-file-format)与[UGC-File-Generate-Utils](https://github.com/luern0313/UGC-File-Generate-Utils)。本节仅表示研究参考，不声称打包了它们完整的代码或获得额外许可。

## 随包Node依赖

| 包 | 版本 | 包声明的许可证 | 随包许可文件 |
| --- | --- | --- | --- |
| @napi-rs/canvas | 0.1.100 | MIT | [LICENSE](vendor/beyond/node_modules/@napi-rs/canvas/LICENSE) |
| @napi-rs/canvas-win32-x64-msvc | 0.1.100 | MIT | 参见包元数据及所属上游许可 |
| fengari | 0.1.5 | MIT | [LICENSE](vendor/beyond/node_modules/fengari/LICENSE) |
| long | 5.3.2 | Apache-2.0 | [LICENSE](vendor/beyond/node_modules/long/LICENSE) |
| protobufjs | 8.7.2 | BSD-3-Clause | [LICENSE](vendor/beyond/node_modules/protobufjs/LICENSE) |
| readline-sync | 1.4.10 | MIT | [LICENSE](vendor/beyond/node_modules/readline-sync/LICENSE) |
| sprintf-js | 1.1.3 | BSD-3-Clause | [LICENSE](vendor/beyond/node_modules/sprintf-js/LICENSE) |
| tmp | 0.2.7 | MIT | [LICENSE](vendor/beyond/node_modules/tmp/LICENSE) |

Python 依赖按安装器的锁文件安装，适用各自的许可。 [依赖锁](scripts/runtime-requirements.lock)

如需更正署名、来源或许可记录，请通过仓库Issue提供对应文件和依据。

分发变更、移出条目的原 SHA-256、随包 Node 版本与许可文件路径由来源清单登记。 [PUBLIC_SOURCES.json](PUBLIC_SOURCES.json) · [上游维护与发行](docs/contributing/maintenance.md)
