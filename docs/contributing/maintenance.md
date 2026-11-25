# 定版与发行

1. 从待发行提交准备候选。以根 `plugin.json` 为候选版本来源，同步宿主清单、PowerShell 安装器、文档定版链接和 CHANGELOG 标题。
2. 从候选运行 `python -B scripts/marketplace_release.py` 生成市场及 DSH 包清单。DSH 从仓库根目录读取 Bundle 清单。
3. 从候选提交运行 `python -B scripts/check_repository.py` 和[相关本地检查](development.md)。打包验证可按[自行打包](../installation.md#自行打包-zip)操作。
4. 正式发布时快进推送候选提交，以该提交建立新标签并发布源码 Release。核对 Latest、标签和各客户端入口。ZIP 自行打包。

Python 依赖有变更时运行 `uv lock`，并用 `uv export --locked --no-dev --no-emit-project --no-header --format requirements-txt --output-file scripts/runtime-requirements.lock` 同步本地安装器的依赖锁。

发行前核对 [来源登记](../../PUBLIC_SOURCES.json) 中的文件、分组、摘要和再分发状态。逐项确认发行范围，记录有明确依据的许可变更和未确认项的处理决定。来源、公开可访问性及再分发许可分别登记。仓库检查核对记录和文件的一致性。

## 分发内容核对

分发排除项统一在 [distribution.json](../../distribution.json) 维护。Windows ZIP 直接读取目录前缀和文件路径，`scripts/marketplace_release.py` 将两类规则写入 Cordis 使用的 `package.json`。改动规则后重新生成清单，`scripts/check_repository.py` 会检查生成结果。npm 仍按自己的规则收录 `package.json`、README 和许可证等必含文件。 [npm 文件清单规则](https://docs.npmjs.com/files/package.json/#files)

当前排除的三个第三方目录位于 `vendor/beyond/node_modules/`。Git 源码保留原文件和摘要，运行检查按 [Beyond 清单](../../vendor/beyond/bundle.json) 核对保留文件。移出条目及原始摘要见 [PUBLIC_SOURCES.json](../../PUBLIC_SOURCES.json) 的 `distribution_changes`。

| 排除路径 | 核对依据 | 文件数 | 原始字节 | ZIP 压缩数据字节 |
| --- | --- | ---: | ---: | ---: |
| `gifuct-js/demo/` | 网页演示及 GIF，包运行入口为 `lib/index.js` | 7 | 3,752,188 | 3,721,239 |
| `js-binary-schema-parser/example/` | 由依赖自身的示例命令读取，包运行入口为 `lib/index.js` | 4 | 3,134,323 | 3,128,823 |
| `fengari/test/` | 上游 Jest 用例及夹具，运行入口为 `src/fengari.js` | 49 | 835,224 | 108,367 |
| 合计 | 三组均通过成品验证 | 60 | 7,721,735 | 6,958,429 |

基线 `993f94d` 与本轮减包验证快照 `ae91d214` 的体积如下。Git 市场行是 Git 树的文件字节合计。源码下载行用本地 `git archive --format=zip` 测量，托管下载和 Git 传输的字节数以实际服务为准。

| 渠道 | 基线字节 | 验证快照字节 |
| --- | ---: | ---: |
| Git 市场源码树 | 94,613,156 | 94,621,002 |
| Git 源码 ZIP 归档 | 36,425,229 | 36,428,220 |
| Windows 安装 ZIP | 36,433,668 | 29,463,982 |
| Cordis `npm pack` | 33,904,622 | 26,947,641 |

上述快照的两种安装包均从干净目录解包复验，60 个路径均已省略，Beyond 运行文件及许可证的摘要匹配清单。安装自检、真实 MCP stdio 的五个教程和 Beyond 点击断言均通过，软件预览记录 `Button clicked`。

当前 Canvas Windows x64 原生模块与 ICU 数据由版本化 Release 资产分发。原文件摘要仍登记在 Beyond 运行清单，另用 [native-canvas.json](../../vendor/beyond/native-canvas.json) 锁定资产地址、ZIP 摘要和两个文件摘要。更新时核对上游版本、许可证、待打包文件和已发布资产的下载摘要。完整 ZIP 成品须包含这两个路径，Git 与 Cordis 的成品须实测首次下载和离线缓存复用。 [Canvas 0.1.100 资产](https://github.com/savormundane/miliastra-wonderland-plugin/releases/tag/beyond-canvas-v0.1.100)
