# 个人维护与手动发布

日常用一个 `main` 和短期工作分支即可。小幅文档修正可以直接提交；安装、文件格式或跨模块改动先用 PR 查看差异。外部贡献通过 PR。Issue 用于可复现问题与具体建议，不要求为每次小改动先建 Issue。保持 Actions 仅 `workflow_dispatch`，不要求自己审批自己的 PR，也不设置不存在的必需 CI。

提交前用 `git var GIT_AUTHOR_IDENT`、`git var GIT_COMMITTER_IDENT` 核对身份。姓名和邮箱在本仓库配置即可；邮箱使用 GitHub 已验证地址或账号专属 noreply 地址，不使用通用 `noreply@users.noreply.github.com`。

## 版本节奏

- 文档、Issue 模板等维护改动可以积累在 `Unreleased`，不必每次发 ZIP。
- 安装或运行行为修复使用新补丁版本；兼容能力增加使用次版本；破坏兼容才考虑主版本。
- 发布时同步三个 `plugin.json`、`install.ps1` 默认版本、README 的安装与下载链接，以及 CHANGELOG。`check_repository.py` 检查清单和安装器版本，发布者仍需核对文档链接与变化说明。
- 已发布 Tag 和同版本资产保持不变。有问题发布新补丁版本，不通过覆盖旧 ZIP 悄悄修复。源码主分支可以比最新 Release 多出未发布的维护提交。

## 一条命令准备本地发布包

需要 Git 与 Python 3.10+，无需安装插件运行依赖。先提交准备发布的更改，按改动运行[相关检查](development.md)，在仓库外写好简短更新说明，再运行：

```powershell
python -B scripts/prepare_release.py --notes ../release-notes.md --output ../release-candidate
```

输出目录必须尚不存在且位于仓库外。命令从当前干净的 Git 提交导出源码，复用打包器生成完整 `Genshin-UGC/` 布局，检查 ZIP 内容与源文件一致；不收录 `.git`、本地忽略文件或专用环境。保留原有分发排除规则和随包依赖。失败时不提交输出目录，也不改变插件安装或 GitHub。

产物为完整 ZIP、`install.ps1`、`SHA256SUMS.txt`、`release-notes.md` 和 `release-review.json`。最后一个文件记录来源提交与检查边界，不是安装通过证明。该命令不联网、不创建 Tag、不上传，不替代人工核对版本号是否已发布。仅从 Git 克隆的源码工作，不从已安装目录或下载 ZIP 再打包。

## 发布到 GitHub

最简单的方式是 GitHub 的 Releases → Draft a new release：

1. 确认候选与更新说明，推送准备发布的提交；在该提交建立 `vX.Y.Z` Tag，不移动已有 Tag。
2. 选择该 Tag，填写更新说明。上传 **完整 ZIP、install.ps1、SHA256SUMS.txt** 三个文件，先保留为草稿。
3. 确认三个附件上传完成、名称和大小正确，再点击发布。上传失败时检查现有附件，只补传失败项；不要覆盖已经发布的附件。
4. 从公开 Release 页面重新下载并核对 SHA-256，确认 README 的版本、下载和安装链接。需要时对该版本做一次隔离安装，记录客户端加载与游戏宿主哪些尚未验证。

已安装 GitHub CLI 的维护者也可使用其 [release create](https://cli.github.com/manual/gh_release_create)（`--draft --verify-tag --notes-file`）和 [release upload](https://cli.github.com/manual/gh_release_upload)，但不需要为此建立发布 Actions。先发布标签，再用 `--verify-tag`，可以避免 CLI 意外从默认分支自动创建标签。上传完整包可能需要数分钟；保留草稿到附件齐全，不因连接超时就改写版本历史。

## 仓库选项

首页 About 简介应说明“千星奇域、五领域 Skill、CLI/MCP 与离线工具”；Website 可以指向 Releases。Topics 使用 `genshin-impact`、`miliastra`、`codex`、`claude-code`、`mcp`、`lua`、`game-development`。不要写成官方项目或全客户端兼容。

保留 Issues，PR 推荐 Squash merge，可启用合并后自动删除已合并分支。Wiki/Projects 暂无使用需求时可以关闭；无需强制多人审批、长期 develop 分支或自动发布。仓库选项调整与新版本发布是两件事，不需要为改简介发布补丁版本。
