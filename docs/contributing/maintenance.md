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

提交中的文件名必须与 [公开文件清单](../../public-files.txt)一致。清单只登记经审查的路径。检查器同时拦截凭据和本机路径的常见形态，人工负责核对用途、隐私与许可。仅用已验证的提交准备正式分发。 [提交前检查](../../CONTRIBUTING.md)

许可待核时，CI 仍在 Windows 运行器内构建候选并检查 ZIP。公开工件上传、依赖该工件的 DSH 验收，以及正式发布暂停。已移出新版的原文记录在 `excluded_unverified_files`，公开树和归档核对路径及校验值。

- **可移植 Windows ZIP 和 Cordis 包**。共有排除规则来自 [distribution.json](../../distribution.json)。规则变化后运行 `python -B scripts/marketplace_release.py` 同步生成的文件，再核对 `package.json` 与实际 npm 文件清单。 [npm 收录规则](https://docs.npmjs.com/files/package.json/#files)
- **Windows ZIP**。从候选产出，核对完整性、根目录清单、四个 Skill、许可证及锁定的 Canvas 模块和 ICU 数据。在空目录解包，用成品做启动自检、MCP 节点查询和 Beyond 软件预览。用户的安装入口见安装指南。 [本地安装](../installation.md#本地安装)
- **Git 市场与 Cordis**。以对应提交的文件核对市场声明和依赖。DSH 验收从发行候选下载同一份 TGZ，核对提交、版本和 SHA-256 后安装并调用 MCP。变更 Canvas 或下载链路时，另测首次获取、校验与离线缓存复用。 [运行环境](../runtime-environment.md)
- **来源记录**。被移出的上游文件、保留的依赖及许可证以机器清单为准。发行材料核对实际分发内容。 [来源清单](../../PUBLIC_SOURCES.json) · [第三方声明](../../THIRD_PARTY_NOTICES.md)

## 定版与发行

根目录 `plugin.json` 是发行版本的来源。确认目标版本和 `Unreleased` 内容后，在以远端 `main` 为基线的任务分支运行以下命令。它同步插件与 npm 清单、安装器、版本链接，并将待发行条目归入指定版本。

```powershell
python -B scripts/prepare_release.py --set-version 1.3.2
```

1. 审阅定版差异并按分支规则合入 `main`。日常 push 和 PR 运行 CI，检查仓库、Windows 运行边界、成品 MCP 和原生 DSH，构建产物由 Actions 短期保存。 [CI 工作流](../../.github/workflows/ci.yml) · [本地检查](development.md)
2. 在 GitHub 的 Actions 打开 **Release → Run workflow**，选择 `main`，填入已同步的版本。默认关闭 `publish` 时预检同一提交并构建 ZIP、Cordis 包和校验记录，可审阅产物。
3. 获得正式发布授权后，从同一提交运行 Release 并打开 `publish`。工作流为选定提交创建 `v版本`、验证草稿中的 Windows ZIP 与 SHA-256，再公开 GitHub Release。之后 npm 阶段以可信发布上传本次验过的 Cordis 包，再从 Registry 下载比对。
4. 查看 Git 标签、GitHub 下载件和 npm 公开版本。从正式安装入口分别记录客户端验收；CI 的 MCP 和软件预览范围不含编辑器导入、游戏内运行或桌面图形界面。上传中断时复用同次工作流的产物重跑失败 job。已有标签必须指向同一提交，已公开成品的字节必须匹配。 [Release 工作流](../../.github/workflows/release.yml) · [回退与卸载](../installation.md#回退与卸载)

若 GitHub Release 已公开，且需以更新后的工作流补发 npm，在 `main` 运行 **Release**，开启 `publish` 并将 `npm_candidate_run` 填为原 Release 的运行 ID。工作流用版本标签和公开 ZIP 的 SHA-256 核对原验收产物，随后发布同一份 Cordis 包。原运行的产物须仍在保留期内。

### 首次连接 npm 可信发布

使用 npm 包的维护者账号，在 `dsh-miliastra-wonderland` 的 **Settings → Trusted publishers** 新增 GitHub Actions 发布者。

| 设置 | 值 |
| --- | --- |
| Organization / user | `savormundane` |
| Repository | `miliastra-wonderland-plugin` |
| Workflow filename | `release.yml` |
| Environment | `npm` |
| Allowed action | `Allow npm publish` |

GitHub **Settings → Environments** 中的 `npm` 环境将部署分支限定为 `main`。工作流通过 OIDC 取短期授权，无需配置 npm token。npm 包已存在，首次绑定还需在两天内完成一次成功的正式发布，宜在下一版即将发布时配置。预检无需 npm 绑定。 [npm 可信发布](https://docs.npmjs.com/trusted-publishers/)

npm 会将账户邮箱写入公开 Registry 元数据。用专门供项目公开的地址维护 npm 账户。在 GitHub **Settings → Secrets and variables → Actions → Secrets** 中设置仓库级 Secret `NPM_PUBLIC_CONTACT_EMAIL`，填入维护者批准公开的邮箱。新版本公开后核对来源字段、可信发布证明和维护者联系信息。历史版本中同一维护者已公开的地址按继承处理，新增地址须与批准值一致。 [npm 账户资料](https://docs.npmjs.com/managing-your-profile-settings/) · [历史元数据说明](https://docs.npmjs.com/threats-and-mitigations/#by-registering-an-expired-email-domain)

更新依赖锁时，在仓库根运行以下命令。

```text
uv lock
uv export --locked --no-dev --no-emit-project --no-header --format requirements-txt --output-file scripts/runtime-requirements.lock
```
