# 日常维护与 GitHub

这里说明一个人维护 Genshin-UGC 时，怎样提交更新、接收反馈和安排后续工作。打包命令与发布步骤见[打包与发布](maintenance.md)。

## 每个入口做什么

| 入口 | 在本项目中怎么用 |
| --- | --- |
| [README](../../README.md) | 给第一次访问的人说明用途、安装和首次使用。 |
| [路线图](../../ROADMAP.md) | 解释近期重点和后续方向；具体任务的状态留在 Issue 或看板。 |
| [Issues](https://github.com/savormundane/Genshin-UGC-plugin/issues) | 记录一个具体问题或改进任务，集中保存讨论、依据和完成条件。 |
| [Pull requests](https://github.com/savormundane/Genshin-UGC-plugin/pulls) | 展示一组准备合入的代码或文档修改，保留修改原因和差异。 |
| [Projects](https://github.com/savormundane/Genshin-UGC-plugin/projects) | 将已有 Issue、PR 按待做、进行中、已完成排列，方便看进度。 |
| Milestones | 当一次版本要做的事情已经明确时，将相关 Issue 和 PR 归到同一个版本目标下。 |
| [Releases](https://github.com/savormundane/Genshin-UGC-plugin/releases) | 提供用户实际下载安装的版本、完整 ZIP 和更新说明。 |

Issues 是任务本身，Projects 是这些任务的看板。它们与电脑里的工程文件夹、千星奇域地图项目没有直接对应关系。GitHub 的官方说明见 [Issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues)、[Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects) 和 [Milestones](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones)。

## 平时怎样更新

1. 开始前用 `git status` 确认本地正在修改的内容，保留好未提交的工作，再同步最新 `main`。
2. 围绕一个实际问题完成修改。明显的文案修正可以直接提交；涉及多个文件、功能调整或他人贡献时，用一个短期分支和 PR 保留完整修改记录。
3. 只选择与改动有关的[本地检查](development.md)。在提交或 PR 中写清改了什么、为什么，以及已经做过的检查。
4. 推送后查看 GitHub 上的文件或 PR；合并完成的短期分支即可结束这次工作。

提交说明写明具体结果即可，例如 `docs: clarify first-time setup` 或 `修复素材预算说明`。没有必要为每次改字先建 Issue，也不必凑提交次数或长期维护一个 `develop` 分支。

新贡献者使用 Fork 和 PR；仓库维护者可以直接在本仓库创建分支。操作说明见 [创建分支](https://docs.github.com/en/pull-requests/how-tos/commit-changes/managing-branches-within-your-repository) 和 [创建 PR](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request)。

## 怎样接收反馈

- **Bug：** 先理解用户在哪一步遇到问题。信息不足时只追问定位所需的版本、操作或报错，不要求对方先理解内部架构。
- **功能建议：** 先判断是否能帮助千星奇域创作者，以及能否复用现有能力。收到建议不等于承诺实现或排期。
- **准备做的任务：** 在 Issue 中写清目标、涉及范围和完成后用户能获得什么。修复它的 PR 可以关联该 Issue。
- **已完成、重复或暂不采纳：** 说明原因后关闭；关闭记录仍可供以后查找。

先使用已有标签即可。使用问答、作品展示和开放讨论可以放到仓库已有的 [Discussions](https://github.com/savormundane/Genshin-UGC-plugin/discussions)；可执行问题与任务保留在 Issues，避免重复登记。功能区别见 [Discussions 官方说明](https://docs.github.com/en/discussions/collaborating-with-your-community-using-discussions/about-discussions)。

## Projects 怎么开始

一个名为 **Genshin-UGC 开发计划** 的看板就能满足当前需要：

| 状态 | 放什么 |
| --- | --- |
| Todo（待做） | 已确认值得推进、但还没开始的任务。 |
| In progress（进行中） | 正在实际处理的任务。 |
| Done（已完成） | 已有对应成果或合并记录的任务。 |

从少量真正要做的 Issue 开始。路线图说明方向，Issue 保存任务细节，看板显示状态；同一份进度无需在多个 Markdown 文件里重复记录。

如仓库的 Projects 页还没有看板，可在个人主页的 Projects 中新建 Board，再通过仓库的 **Projects → Link a project** 关联。Project 和仓库需要属于同一用户或组织。也可以将该仓库设为 Project 的默认仓库。具体操作见 [创建 Project](https://docs.github.com/en/issues/planning-and-tracking-with-projects/creating-projects/creating-a-project) 和 [关联仓库](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/adding-your-project-to-a-repository)。

看板有单独的[可见性设置](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-visibility-of-your-projects)；面向社区的开发计划应设为公开。可以手动更新状态，也可以用 Projects 自带的状态规则，不需要为此增加 GitHub Actions。

## 什么时候发布新版本

日常提交可以持续积累；当有一组值得用户安装的功能、修复或兼容性改进时，再发布版本。纯文档更新通常可以直接随 `main` 提供，先在 [CHANGELOG](../../CHANGELOG.md) 的 `Unreleased` 中归纳。

决定发布时，再确定版本范围、同步版本号并按[打包与发布](maintenance.md)生成完整 ZIP。Tag 标识发布对应的源码提交，Release 提供该版本的说明和附件；下载用户应使用完整 ZIP。

只有下一版本的任务范围已经明确时才建立 Milestone，不提前承诺日期。GitHub Actions 继续保持手动触发。
