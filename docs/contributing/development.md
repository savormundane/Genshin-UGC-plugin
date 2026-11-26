# 本地开发与检查

从 [工程架构](architecture.md) 和 [工具导航](../../scripts/README.md) 找到负责模块。以 `origin/main` 为基线，按改动范围运行检查，提交并按分支保护规则推送，查看对应提交的 Actions 结果。 [GitHub Actions](https://github.com/savormundane/miliastra-wonderland-plugin/actions)

普通开发在 CHANGELOG 的 `Unreleased` 记录面向创作者的行为变更。版本同步、标签与分发包归[定版流程](maintenance.md#定版与发行)。临时产物放到源码外，核对验证结果后清理可重建的副本及已合并分支。 [变更记录](../../CHANGELOG.md)

## 配置开发环境

从仓库根运行以下命令。只修改文档时，可直接用支持的系统 Python 运行仓库检查。

```powershell
python -B scripts/check_repository.py
```

需要运行工具时，用支持的 Windows x64、Python 和 Node.js 环境。已有插件专用 Python 可直接复用，或在仓库根创建锁定的专用环境。 [兼容性](../compatibility.md) · [复用已安装的环境](../runtime-environment.md)

```powershell
uv sync --locked --no-build
$miliastraPython = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $miliastraPython -B scripts/qianxing.py doctor
```

检出路径过深时，可用 `git -c core.longpaths=true clone` 并选择较短的目标目录。修改 Python 源码时，可用 Ruff 0.15.0 对本次涉及的文件执行 `ruff format --check`。

## 按改动选检查

| 改了什么 | 在仓库根运行 |
| --- | --- |
| 文档、安装链接、清单 | `python -B scripts/check_repository.py` |
| Python 脚本 | `python -m compileall -q scripts` |
| GIL 容器和 Lua 替换 | `node scripts/test_gil.mjs` |
| MCP、原生修改计划和便携重建 | `& $miliastraPython -B scripts/test_mcp_native_workflow.py -v` |
| 图编译、信号与结构体写回 | `& $miliastraPython -B -m unittest discover -s scripts -p test_release_behaviors.py -v` |
| Beyond 原生资源、预览和失败诊断 | `& $miliastraPython -B scripts/test_beyond_native.py -v` |
| 中文 API 检索、资料与节点查询 | `& $miliastraPython -B scripts/test_chinese_lookup.py -v` |
| 物件变换与字段保护 | `& $miliastraPython -B scripts/test_native_entity_transform.py -v` |
| 安装器、声明和打包 | `& $miliastraPython -B scripts/test_agent_protocols.py -v`、`& $miliastraPython -B scripts/test_distribution.py -v`、`python -B scripts/test_release.py -v` |

`$miliastraPython` 为有锁定依赖的解释器绝对路径。完整公开 Python 用例可使用 `& $miliastraPython -B -m unittest discover -s scripts -v`。Beyond 测试可通过 `MILIASTRA_TEST_BEYOND_ARCHIVE` 指向已锁定的本地 Canvas ZIP。运行分发测试前按打包条件准备资产。测试输入用公开样例或由测试生成。 [Canvas 锁](../../vendor/beyond/native-canvas.json) · [公开验证清单](../../scripts/validation-contract.json) · [验证层级](../compatibility.md#验证分层)

### 复现已有工程的修改流程

运行上述 MCP 测试。用例经真实 stdio 把模板参数 `ActivationDelay` 改为 `12`，核对相关引用和保护字段，并检查过期输入会被拒绝。 [输入与断言](../../scripts/test_mcp_native_workflow.py) · [工具调用顺序](../../references/gil/native-changes.md#审阅并另存已有工程)

## 客户端适配

通用 Agent Plugins 读取根 `plugin.json` 和 `mcp.json`。Codex 读取 `.codex-plugin/plugin.json` 及其引用的 MCP 文件。Claude Code 读取 `.claude-plugin/plugin.json` 和 `.mcp.json`。DSH 通过 `package.json` 和 `cordis.patch.yml` 加载四个 Skill 和 MCP。 `locale/` 下的中英文资源及 `docs/dsh/` 下的详情用于 DSH 插件介绍。

修改客户端声明时，检查生成清单、包内路径和实际工具发现。通用功能继续复用同一实现。客户端特有入口接到已有功能，并在对应宿主复测。DSH 原生接入使用宿主允许的 Cordis 服务，Claude Code 可用 `claude plugin validate <目录>` 做清单校验，Codex 用隔离市场加载并查看工具。Claude 账户市场使用单独的客户端入口。 [市场与安装](../installation.md) · [运行环境](../runtime-environment.md) · [维护与发行](maintenance.md)

## 文档维护

| 信息 | 维护位置 |
| --- | --- |
| 安装入口、更新与排障 | [安装指南](../installation.md)。版本和依赖要求集中在 [兼容性](../compatibility.md)，解释器和目录绑定集中在 [运行环境](../runtime-environment.md)。 |
| 调用参数和结果 | [MCP 工具](../mcp.md) 和各领域参考，核对工具定义、CLI 帮助和回归。样例展示完成任务的方法。 |
| 平台原文、版本、许可与样本依据 | 原文按供应版本保留，[平台资料维护](platform-maintenance.md) 负责更新流程，来源清单以内容和路径绑定证据。 |
| 工具边界、开发协作和历史决策 | [工程架构](architecture.md)、[参与贡献](../../CONTRIBUTING.md)、本页的退出计划及 [CHANGELOG](../../CHANGELOG.md)。 |
| 更新上游与发布 | [维护与发行](maintenance.md)。各次发布与本机安装的结果随对应候选和版本留证。 |

在用页面迁移时，先查 Markdown 链接和代码中的路径或锚点引用，再更新调用方。长期入口可保留指向新位置的短说明。来源正文、旧发布和回归记录用于追溯对应版本。参数名、版本和证据状态引用工具实际值。正文使用 SHA-256 校验值、读回校验、客户端、编辑器、游戏环境等具体名称。

## 旧配置的退出版本

| 从 V1.2.0 起列为弃用的入口 | 计划移除 | 现有配置如何处理 |
| --- | --- | --- |
| `produce` 顶层 schema 1 任务 | V2.0.0 | 按 schema 2 改写任务并核对 GIL 映射和交付校验值。 [制作指南](../../references/workflows/produce.md) |
| `assets fit` 的 schema 1 配置和续跑 | V2.0.0 | 使用 schema 2 参数，可通过 `--initial` 导入旧检查点中的图元。 [拟合指南](../../references/assets/asset-fit.md) |

两种旧入口当前仍可执行。schema 2 的制作流程复用资源、图编译和 Lua 写回阶段。调整旧入口前使用原配置与公开样例复测。
