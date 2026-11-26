# 参与贡献

欢迎报告问题、补充资料和样例、纠正文档或提交代码。

- **报告问题**。先查已有条目。附上插件版本、客户端或调用方式、预期结果、实际报错及最小复现。上传日志、截图和工程前移除账号、令牌和私人数据。 [Issues](https://github.com/savormundane/miliastra-wonderland-plugin/issues) · [私密安全报告](SECURITY.md)
- **补充资料或样例**。指出条目和应用范围，附官方页面、适用版本，或可公开复查的原生样本。写明复现步骤和实际完成的检查。 [平台资料维护](docs/contributing/platform-maintenance.md) · [公开样例](samples/README.md)
- **提交改动**。从 `main` 建立分支，根据任务选择领域模块。PR 说明行为或文档改动，列出实际执行的检查和证据。平台规则、写入范围、上游依赖有变化时，附上对应来源与版本。 [开发指南](docs/contributing/development.md) · [工程架构](docs/contributing/architecture.md)
- **公开范围**。提交前运行 `python -B scripts/check_public_scope.py --index`，并审查暂存差异和提交身份。新文件按用途和许可逐项审查后才加入[公开文件清单](public-files.txt)。个人协作规则、真实配置、原始日志和私有工程保存在源码目录之外。 [分发检查](docs/contributing/maintenance.md#分发内容核对)
