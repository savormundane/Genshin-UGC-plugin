# 第三方声明

根目录GPL-3.0-only适用于本项目自有代码。以下内容保留原作者权利；不得将整仓库理解为所有文件都已获得同一许可。

## 随包代码

| 内容 | 来源与许可 | 本项目中的使用 |
| --- | --- | --- |
| Ayaya | [上游](https://github.com/AyayaXiaowang/Ayaya_Miliastra_Editor)，[GPLv3](vendor/ayaya/LICENSE) | 选定的无界面子集；修改和文件摘要见[NOTICE](vendor/ayaya/NOTICE.md)与[VENDORED](vendor/ayaya/VENDORED.json) |
| Beyond | [上游](https://github.com/1475505/miliastra-beyond-simulator)，[GPL-3.0-only](vendor/beyond/LICENSE) | 固定提交02a5ea2cd38bb5bcf7a7ce6dd745be3bb1ae655c；所选源码、依赖及原字节摘要见[bundle](vendor/beyond/bundle.json) |
| luaparse | Oskar Schöldström，[MIT](vendor/luaparse/LICENSE) | Lua语法解析器 |
| Genshin-Impact-UGC-File-Converter | にゃが，[MIT](vendor/ayaya/LICENSES/Genshin-Impact-UGC-File-Converter.MIT.txt) | Ayaya保留的转换器版权声明 |
| genshin-ts | josStorer，[MIT](vendor/ayaya/LICENSES/genshin-ts.MIT.txt) | Ayaya定义与报告相关来源 |
| NodeEditorPack | Wu-Yijun，[MIT](vendor/ayaya/LICENSES/NodeEditorPack.MIT.txt) | Ayaya节点定义相关来源 |
| perfectPixel | theAmusing，[MIT](vendor/ayaya/LICENSES/perfectPixel.MIT.txt) | Ayaya保留的图像处理相关声明 |

第三方模块的版权、许可证文本及原始头注释保留。GPL代码使用和分发应遵循其源码及通知义务；参考过一个项目不表示它的所有实现都被打包。Beyond内的源码和构建脚本随选定子集保留，依赖版本与路径见PUBLIC_SOURCES.json。

## 原始资料与授权待核项

| 内容 | 已知来源 | 当前状态 |
| --- | --- | --- |
| GE手册、知识快照与历史模板（不含GE程序） | [没空放肆下载页](https://docs.lumkfs.cn/GEIMG-WIKI/Download/) | 已确认发布者线索；未核实再分发许可，不属于本项目GPL授权 |
| 拟L2D正文、附件与模板 | [没空放肆知识库](https://docs.lumkfs.cn/GEIMG-WIKI/EG-L2D/) | 章节和附件对应；精确下载包身份与再分发许可待核，不属于本项目GPL授权 |
| 点阵像素图处理与导入指南 | 原始下载出处待核 | 作者与许可待核，不冒称原创或GPL |
| 客户端API整理文档 | [相关官方页面](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhtakr07vej4) | 本地整理稿来源与再分发许可待核 |
| 官方正文及版本镜像 | 米哈游；[Miliastra-knowledge](https://github.com/1475505/Miliastra-knowledge) | 平台资料权利与工具代码许可分开；未确认镜像正文的再分发许可 |

逐文件范围和SHA-256见[PUBLIC_SOURCES.json](PUBLIC_SOURCES.json)。这些文件已收录，但许可状态仍是未确认；该声明不是原作者授权或免责承诺。资料中的实测数字属于原作者对应场景，不能视为本插件或任意生成项目的宿主验证。

## 参考研究

感谢[genshin-miliastra-mcp](https://github.com/8itlab/genshin-miliastra-mcp)、[genshin-miliastra-file-format](https://github.com/script-1024/genshin-miliastra-file-format)与[UGC-File-Generate-Utils](https://github.com/luern0313/UGC-File-Generate-Utils)。本节仅表示研究参考，不声称打包了它们完整的代码或获得额外许可。

## 随包Node依赖

| 包 | 版本 | 包声明的许可证 | 随包许可文件 |
| --- | --- | --- | --- |
| @napi-rs/canvas | 0.1.100 | MIT | [LICENSE](vendor/beyond/node_modules/@napi-rs/canvas/LICENSE) |
| @napi-rs/canvas-win32-x64-msvc | 0.1.100 | MIT | 参见包元数据及所属上游许可 |
| @pixi/colord | 2.9.6 | MIT | 参见包元数据及所属上游许可 |
| @types/earcut | 3.0.0 | MIT | [LICENSE](vendor/beyond/node_modules/@types/earcut/LICENSE) |
| @webgpu/types | 0.1.74 | BSD-3-Clause | [LICENSE](vendor/beyond/node_modules/@webgpu/types/LICENSE) |
| @xmldom/xmldom | 0.8.15 | MIT | [LICENSE](vendor/beyond/node_modules/@xmldom/xmldom/LICENSE) |
| earcut | 3.2.3 | ISC | [LICENSE](vendor/beyond/node_modules/earcut/LICENSE) |
| eventemitter3 | 5.0.4 | MIT | [LICENSE](vendor/beyond/node_modules/eventemitter3/LICENSE) |
| fengari | 0.1.5 | MIT | [LICENSE](vendor/beyond/node_modules/fengari/LICENSE) |
| gifuct-js | 2.1.2 | MIT | [LICENSE](vendor/beyond/node_modules/gifuct-js/LICENSE) |
| ismobilejs | 1.1.1 | MIT | [LICENSE](vendor/beyond/node_modules/ismobilejs/LICENSE) |
| js-binary-schema-parser | 2.0.3 | MIT | [LICENSE](vendor/beyond/node_modules/js-binary-schema-parser/LICENSE) |
| long | 5.3.2 | Apache-2.0 | [LICENSE](vendor/beyond/node_modules/long/LICENSE) |
| parse-svg-path | 0.2.0 | MIT | [LICENSE](vendor/beyond/node_modules/parse-svg-path/LICENSE) |
| pixi.js | 8.20.0 | MIT | [LICENSE](vendor/beyond/node_modules/pixi.js/LICENSE) |
| protobufjs | 8.7.2 | BSD-3-Clause | [LICENSE](vendor/beyond/node_modules/protobufjs/LICENSE) |
| qxqy-lua-runtime | 0.1.0 | GPL-3.0-only | 参见包元数据及所属上游许可 |
| qxqy-server | 0.1.0 | GPL-3.0-only | 参见包元数据及所属上游许可 |
| qxqy-studio | 0.1.0 | GPL-3.0-only | 参见包元数据及所属上游许可 |
| readline-sync | 1.4.10 | MIT | [LICENSE](vendor/beyond/node_modules/readline-sync/LICENSE) |
| sprintf-js | 1.1.3 | BSD-3-Clause | [LICENSE](vendor/beyond/node_modules/sprintf-js/LICENSE) |
| tiny-lru | 11.4.7 | BSD-3-Clause | [LICENSE](vendor/beyond/node_modules/tiny-lru/LICENSE) |
| tmp | 0.2.7 | MIT | [LICENSE](vendor/beyond/node_modules/tmp/LICENSE) |

Python依赖按scripts/runtime-requirements.lock安装，不把所需依赖冒称随包包含；其各自许可仍然适用。

如需更正署名、来源或许可记录，请通过仓库Issue提供对应文件和依据。

Beyond 的 `.gitattributes` 保留原始字节，避免 Git 换行转换影响依赖校验。Windows ZIP 和 Cordis 打包省略三个第三方示例及测试目录。运行清单、移出条目的原始摘要和来源见 [PUBLIC_SOURCES.json](PUBLIC_SOURCES.json) 的 `distribution_changes`。
