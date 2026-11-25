# 定版与发行

1. 从待发行提交准备候选。以根目录的 `plugin.json` 为准，同步各客户端的清单、PowerShell 安装器、文档中的发行链接和变更记录的版本标题。运行 `python -B scripts/marketplace_release.py` 生成市场清单和 DSH 包清单。
2. 在候选目录运行[本地检查](development.md)，用 `npm pack` 核对 DSH 包的文件清单。发行前核对 [PUBLIC_SOURCES.json](../../PUBLIC_SOURCES.json) 的分组、摘要和许可状态。
3. 正式发布时快进推送候选提交，用同一提交创建标签和 Release，核对 Latest、附件摘要与安装入口。从[安装指南](../installation.md#deepseek-harness)所列地址在隔离 DSH 配置中安装，并调用一次 MCP 工具。

定版流程从候选提交生成 `Miliastra-Wonderland-<version>-agent-plugins-windows-x64.zip`。检查 ZIP 根目录的 `plugin.json`、`mcp.json` 和 `skills/`，核对 Windows x64 Canvas 文件和公开下载的 SHA-256。

留存定版源码、包摘要、依赖锁和运行绑定供回退。验证新安装时检查文件清单、解释器及实际 stdio 调用。 [回退与卸载](../installation.md#回退与卸载)

Python 依赖有变更时运行 `uv lock`，并用 `uv export --locked --no-dev --no-emit-project --no-header --format requirements-txt --output-file scripts/runtime-requirements.lock` 同步本地安装器的依赖锁。

## 分发内容核对

分发规则统一维护在 [distribution.json](../../distribution.json)，供 Windows ZIP 与 Cordis 共享。修改后重新生成 `package.json`，通过 `scripts/check_repository.py` 核对，并检查成品内容。npm 按自身规则收录 README 和许可证等必含文件。 [npm 文件清单规则](https://docs.npmjs.com/files/package.json/#files)

解包到干净的目录，核对运行文件和许可证是否齐全，再按[本地开发与检查](development.md)验证启动、MCP 和相关工作流。已排除的上游目录及摘要见 [PUBLIC_SOURCES.json](../../PUBLIC_SOURCES.json) 的 `distribution_changes`。 [V1.1.0 分发包精简记录](https://github.com/savormundane/miliastra-wonderland-plugin/blob/v1.1.0/docs/contributing/maintenance.md)

用 [native-canvas.json](../../vendor/beyond/native-canvas.json) 锁定 Windows x64 原生模块与 ICU 数据的资产地址和摘要。更新时核对上游版本、许可证、下载的资产和解包文件。完整 ZIP 须随包携带两份文件。Git 与 Cordis 的成品须实测首次下载及离线缓存复用。 [Beyond 运行文件清单](../../vendor/beyond/bundle.json)
