# 定版与发行

1. 统一插件清单、README、安装指南和 CHANGELOG 的版本。运行 `python -B scripts/marketplace_release.py` 生成根目录的市场清单及 DSH 包清单。
2. 提交定版源码。运行 `python -B scripts/marketplace_release.py --dsh-source COMMIT`，将 DSH 索引固定到该提交，再提交索引。两次提交的可安装内容一致。
3. 从第二个提交运行 `python -B scripts/check_repository.py` 和[相关本地检查](development.md)。打包验证可按[自行打包](../installation.md#自行打包-zip)操作。
4. 正式发布时快进推送两个提交，在第二个提交建立新标签并发布源码 Release。核对 Latest、标签和各客户端入口。ZIP 自行打包。

Python 依赖有变更时运行 `uv lock`，并用 `uv export --locked --no-dev --no-emit-project --no-header --format requirements-txt --output-file scripts/runtime-requirements.lock` 同步本地安装器的依赖锁。
