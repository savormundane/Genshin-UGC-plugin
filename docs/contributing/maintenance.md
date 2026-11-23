# 定版与发行

1. 统一插件清单、README、安装指南和 CHANGELOG 的版本，并将源码下载链接指向本次发行标签。运行 `python -B scripts/marketplace_release.py` 生成根目录的市场清单及 DSH 包清单。
2. 将定版源码提交到发行候选。DSH 从仓库根目录读取 Bundle 清单。
3. 从候选提交运行 `python -B scripts/check_repository.py` 和[相关本地检查](development.md)。打包验证可按[自行打包](../installation.md#自行打包-zip)操作。
4. 正式发布时快进推送候选提交，以该提交建立新标签并发布源码 Release。核对 Latest、标签和各客户端入口。ZIP 自行打包。

Python 依赖有变更时运行 `uv lock`，并用 `uv export --locked --no-dev --no-emit-project --no-header --format requirements-txt --output-file scripts/runtime-requirements.lock` 同步本地安装器的依赖锁。
