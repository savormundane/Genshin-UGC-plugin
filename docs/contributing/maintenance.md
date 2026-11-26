# 上游维护与发行

[工程架构](architecture.md)说明各后端的职责，本页负责上游修订、候选打包和正式发行。

## 更新上游

| 随包内容 | 基线和来源 | 回归入口 |
| --- | --- | --- |
| Ayaya 无界面工具链 | [VENDORED.json](../../vendor/ayaya/VENDORED.json) 记录选入文件和摘要，[NOTICE](../../vendor/ayaya/NOTICE.md) 记录裁剪与修改 | [图编译与 GIL 写回](development.md#按改动选检查) |
| Beyond 本地预览 | [修订锁](../../scripts/beyond-revision.json) 绑定上游提交和本地清单，[bundle.json](../../vendor/beyond/bundle.json) 记录运行文件和摘要 | [按钮预览和诊断](development.md#按改动选检查) |
| Canvas 原生资产 | [native-canvas.json](../../vendor/beyond/native-canvas.json) 绑定下载包和包内文件的 SHA-256 | [分发内容核对](#分发内容核对) |
| 平台资料及第三方参考 | [PUBLIC_SOURCES.json](../../PUBLIC_SOURCES.json) 记录来源、许可和当前分发差异 | [平台资料维护](platform-maintenance.md) |

1. 固定目标上游版本或提交，读取当前锁与本地改动记录，明确本次需要的模块和数据。
2. 在独立目录准备变更。核对保留的许可证和必要源码，比较已用的导入、格式样本和输出合同。不能确认用途的输入或依据应保留并注明。
3. 合并后登记新的文件摘要及变更依据。已有资料路径失效时，更新引用和来源清单。运行受影响的专项和真实产物对照，再做成品安装或解包核验。

Ayaya 更新保留节点定义和编译器所需的内置样本。重新准备无界面子集时，需要把既有的节点编译、声明读取、写回保护和输出范围逐项核对。Graph Code 的读取、单独 GIA、GIL 写回及实际 MCP 构建须分别复测。 [编译接入](../../scripts/ayaya_bridge.py)

### Beyond 源码修订

本地修订已有的 Beyond JavaScript 时，先编辑源码，再生成候选清单。将命令中的文件换成本次修改路径，待审目录使用源码外的新目录。

```text
python -B scripts/prepare_beyond_revision.py studio/play/session.js --reason "说明本次维护变更" --out ../beyond-review
```

核对生成的 `vendor/beyond/bundle.json`、`scripts/beyond-revision.json` 和 `PUBLIC_SOURCES.json`，审阅后与源码一并提交。新上游基线、文件增删或依赖变更时，先重新确定无界面运行文件，再登记摘要和来源。用按钮样例及专项测试核对渲染、Lua 失败诊断、控件树和连续交付。 [源码入口](../../scripts/beyond_worker.mjs) · [预览指南](../../references/workflows/beyond-backend.md)

## 分发内容核对

- **可移植 Windows ZIP 和 Cordis 包**。共有排除规则来自 [distribution.json](../../distribution.json)。规则变化后运行 `python -B scripts/marketplace_release.py` 同步生成的文件，再核对 `package.json` 与实际 npm 文件清单。 [npm 收录规则](https://docs.npmjs.com/files/package.json/#files)
- **Windows ZIP**。从候选产出，核对完整性、根目录清单、四个 Skill、许可证及锁定的 Canvas 模块和 ICU 数据。在空目录解包，用成品做启动自检、MCP 节点查询和 Beyond 软件预览。用户的安装入口见安装指南。 [本地安装](../installation.md#本地安装)
- **Git 市场与 Cordis**。以对应提交的文件或实际包核对客户端声明和依赖。安装后调用 MCP。变更 Canvas 或下载链路时，另测首次获取、校验与离线缓存复用。 [运行环境](../runtime-environment.md)
- **来源记录**。被移出的上游文件、保留的依赖及许可证以机器清单为准。发行材料核对实际分发内容。 [来源清单](../../PUBLIC_SOURCES.json) · [第三方声明](../../THIRD_PARTY_NOTICES.md)

## 定版与发行

1. 从明确的 Git 提交准备独立候选。根目录 `plugin.json` 是发行版本的来源，定版流程同步其它清单、安装器和使用文档中的定版链接。将 CHANGELOG 的待发行条目归入对应版本。
2. 检查候选差异、文件来源、实际运行和分发结果。Python 依赖变化时，更新 `uv.lock` 和安装器用的 `scripts/runtime-requirements.lock`，再用锁定环境复测。 [本地检查](development.md) · [锁文件](../../uv.lock)
3. 推送同一份定版源码，创建对应标签及 GitHub Release。采用 Windows ZIP 的发行核对公开附件的 SHA-256。依次核对正式标签、下载文件和各客户端安装所用提交。保存发行、安装和回退记录。 [版本记录](../../CHANGELOG.md) · [回退与卸载](../installation.md#回退与卸载)

更新依赖锁时，在仓库根运行以下命令。

```text
uv lock
uv export --locked --no-dev --no-emit-project --no-header --format requirements-txt --output-file scripts/runtime-requirements.lock
```
