# 2026-11-21 仓库审查与整理

## 结论与范围

当前插件已经具备明确的五领域架构、版本化资料、本地工具和完整发行流程。最有价值的改进是帮助新用户完成第一个任务，让贡献者快速找到修改入口，并把下一步投入连接到具体创作能力。

本次从公开仓库 `main` 的 `ed038e078a506eca1e8273790aa8cc9d1330919e` 开始；当时最新正式版本为 [4.1.0](https://github.com/savormundane/Genshin-UGC-plugin/releases/tag/v4.1.0)。按目录清点全树，阅读首页、文档、五领域入口、关键 CLI/MCP、安装、打包及制作调用链，再完成文档和示例整理。以下判断以该基线为依据。

## 审查发现与处理

| 发现 | 源码或文档依据 | 本次处理 |
| --- | --- | --- |
| 五个领域按平台工作对象划分，已有清晰分工。 | [领域登记](../../scripts/capability_index.py)、[技术路由](../../references/skill-map.md) | 保留五领域；多人、存储、动画和诊断继续由共享能力承担。 |
| 使用文档与维护者文档已分开，但第一次使用缺少完整路径。 | 基线 `docs/README.md`、`docs/installation.md` | 重写用户导航，增加[首次使用](../getting-started.md)，按任务连接输入、操作和产出。 |
| 安装文案容易让没有现成工程的人以为不能试用。 | [安装器](../../scripts/install_public.py)只要求项目目录存在、非整盘、与输出互不包含。 | 明确可以先用空目录做节点查询；给出同级目录示例。 |
| 已安装用户找不到现有专用环境；手动接入者可能只搬走插件子目录。 | 安装器的安装记录、`runtime.json` 与各客户端路径绑定。 | 增加环境复用命令，按 UTF-8 读取安装记录，说明保留整个版本目录。 |
| 技术参考存在多套制作说明与旧“十项分工”“动画技能”称呼。 | 基线 `references/README.md`、`production-workflow.md` | 按五领域和共享能力整理索引，保留原链接，明确制作总流程及当前 schema 2 配置入口。 |
| 第一方工具集中在一个目录，缺少维护者导航。 | 基线 `scripts/` 有 109 个文件。 | 新增[模块导航](../../scripts/README.md)，说明 CLI、MCP 与核心模块关系，保留稳定路径。 |
| 公开文档引用了未随仓库提供的开发采集器与部分测试。 | [证据合同说明](../../references/validation-evidence.md)、`scripts/validation-contract.json` | 明确公开检查入口与维护者工作区的区别，不将登记用例误写成已公开、已运行。 |
| 介绍以提问范例为主，缺少一组能直接查看的实际输出。 | 基线 `docs/examples.md` 没有完整样例资产。 | 制作并收录[蓝金徽章案例](../../examples/hello-assets/README.md)，包含输入、命令、Lua、预览和报告。 |
| GitHub 反馈表单对初学者偏技术化，缺少产品方向入口。 | 基线 Issue/PR 模板与维护者索引。 | 简化必填项，增加[路线图](../../ROADMAP.md)、[GitHub 日常维护](../contributing/github-workflow.md)，创建具体任务。 |

## 顶层组织决策

| 位置 | 负责内容 |
| --- | --- |
| 根 `README.md` | 项目定位、能力、实际样例、安装和主要入口。 |
| `docs/` | 使用者指南，按所处阶段和任务查找。 |
| `docs/contributing/` | 修改、协作、打包和发布的方法。 |
| `docs/maintenance/` | 阶段审查与组织决策记录。 |
| `examples/` | 中性、可复用的输入与真实产物。 |
| `references/` | Agent 与开发者按需读取的平台资料、技术合同和共享流程。 |
| `skills/`、`scripts/` | 保留既有领域入口和运行实现路径。 |
| `vendor/`、`runtime/`、`assets/` | 分别保留固定第三方依赖、Lua 模板和插件标识。 |
| `ROADMAP.md`、Issues、PR、Releases | 分别记录方向、任务、实现差异和已发布版本。 |

### 为什么没有大规模搬目录

基线共有 **5,195** 个 Git 跟踪文件，其中 **4,681** 个位于 `vendor/`；`runtime/` 只有一个 Lua 模板。文件数量主要来自随包第三方依赖，不能把它直接等同于第一方结构失控。

[打包工具](../../scripts/prepare_release.py)已经从干净 Git 提交导出并准备发行包；[目录职责](../contributing/architecture.md)说明了各依赖用途。现有来源清单和 `.gitattributes` 还保护精确字节与换行。保留路径并完善导航，当前比拆分依赖更有直接收益。

## 实际样例成果

[Hello Assets](../../examples/hello-assets/README.md)使用现有素材生成器完成了一次真实制作：128×128 的两色 PNG，输出 **9 个矩形**（预算 16）、**245 字节 Lua 数据**以及预览、报告和文件摘要。

本轮使用 Linux、Python 3.12.14、Pillow 13.0.0 的已有环境。生成结果是本地素材工具的实际产物；没有改动生成器，也没有据此声称完整 Windows 安装、千星奇域编辑器导入或游戏运行通过。示例文件尚未加入已发布的 4.1.0 ZIP，已安装用户可以下载输入图并用已有工具处理。

## GitHub 计划与设置

创建的任务包括：[素材示例 #2](https://github.com/savormundane/Genshin-UGC-plugin/issues/2)、[原生 3D 实体运动 #3](https://github.com/savormundane/Genshin-UGC-plugin/issues/3)、[贡献者复现入口 #4](https://github.com/savormundane/Genshin-UGC-plugin/issues/4)。素材示例由本次改动交付；其他任务留作后续，具体状态以 Issue 为准。

仓库已有 Description、Topics、Release 下载主页和 Discussions。本次没有重设这些选项，也没有增加空 Milestone 或自动工作流。

Projects 是 Issue/PR 的进度视图，不是源码文件夹。建议只维护一个 Todo / In progress / Done 看板，关联现有任务即可。本次查看时仓库尚未关联 Projects；当前连接不提供 Projects 写入接口，浏览器也没有登录态，因此**未创建线上看板**。具体创建与关联方式已写入[日常维护指南](../contributing/github-workflow.md#projects-怎么开始)，路线图与实际任务可以先独立使用。

## 后续投入顺序

1. 继续沉淀可以接手的工程案例，优先一份有原始 GIL、Lua、修改产物与差异说明的中性示例。
2. 从明确的实体运动任务扩展原生 3D 制作能力。已有平台资料和声明检查是基础；直接写入工程的能力按对象逐项建设。
3. 围绕真实需求公开小型复现输入与必要检查，帮助外部贡献者完成第一个改动。

各项的用户收益、当前依据和完成条件见[开发路线](../../ROADMAP.md)。现阶段无需建立完整团队治理、额外站点、并行 Wiki 或频繁运行的 CI 来替代实际功能与示例。

## 检查与交付记录

检查结果：

- `python -B scripts/check_repository.py` 通过，清单、安装器、版本记录、文档版本和本地链接一致。
- 补充核对本次变更的 20 份 Markdown 中 362 个本地链接，目标均存在；两个 Issue 表单的 YAML 和字段 ID 有效。
- 示例输入与输出文件的 SHA-256 均与生成清单一致。
- 保留已有 CRLF/LF，按原换行规则检查差异；确认未改动运行代码、五个 Skill、第三方依赖或工作流。

本次共涉及 30 个文件（17 个修改、13 个新增），包含实际示例文件。合并信息记录在对应 PR。没有触发 GitHub Actions，没有做完整安装、模拟器或游戏宿主回归，也没有改动插件版本、发布标签或既有 Release 附件。
