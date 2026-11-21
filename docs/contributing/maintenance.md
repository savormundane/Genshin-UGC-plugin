# 打包与发布

发布前核对三份插件清单、安装器默认版本、README、安装指南及 CHANGELOG。手动从仓库根运行 `python scripts/check_repository.py`，可检查当前版本、下载链接、安装命令及第一方 Markdown 链接。普通文档改动可先记在 `Unreleased`，公开源码可先于最新正式包更新。

## 准备本地发布包

使用 Git 和 Python 3.11 或 3.12。打包脚本只用标准库和 Git，无需创建插件运行环境。先提交准备发布的更改，按改动运行[本地检查](development.md)，在仓库外写好更新说明，再运行打包命令。

```powershell
python -B scripts/prepare_release.py --notes ../release-notes.md --output ../release-candidate
```

输出目录须为仓库外的新路径。命令从干净的 Git 提交导出源码，按分发规则生成完整 ZIP。成功时输出 Windows x64 ZIP、`release-notes.md` 和 `release-review.json`。审阅文件记录来源提交、资产摘要和打包检查结果。安装和客户端加载需另行验证。

## 发布到 GitHub

1. 选择准备发布的提交，推送提交并建立新的 `vX.Y.Z` 标签。既有标签与发布附件保留。
2. 用新标签建立 Release 草稿并填写说明，上传唯一的完整 Windows x64 ZIP。安装脚本随 ZIP 和标签源码提供。
3. 确认附件名称、大小和 SHA-256 与审阅结果一致，再公开 Release。传输中断时从原草稿核对并补传缺失项。
4. 从公开页面重新下载 ZIP，核对 SHA-256，并试读 README 和安装指南中的当前版本链接。按变更范围选择安装和运行检查。

仓库的 [Repository checks](../../.github/workflows/repository-check.yml) 可手动启动。若使用 GitHub CLI 建立草稿，先推送标签，再使用 `--draft --verify-tag --notes-file`。[GitHub CLI 发布命令](https://cli.github.com/manual/gh_release_create)
