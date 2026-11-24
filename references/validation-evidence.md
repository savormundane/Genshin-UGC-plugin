# 能力与验证结果

查看当前源码实现的操作、适用范围及状态。

```text
python scripts/qianxing.py capabilities
```

工具把规则、生成、回读和模型的证据分别列在 `layers` 中。`not_checked` 表示对应能力缺少与当前输入匹配的证据。`not_registered` 表示该层尚无登记的验证合同。用 `--platform` 和 `--mode` 可选择平台资料上下文。

`--evidence` 读取开发验证入口生成的 schema 3、`scope: public` 报告。校验以插件源码旁的 `development/` 为测试目录，会核对源码、工具环境、依赖摘要及必需用例。独立安装缺少开发测试目录、报告缺件或内容变化时，对应结果保持 `not_checked`。原生编辑器导入和实际游戏运行各自需要对应的观察记录。

日常贡献可直接从 GitHub 源码运行[本地检查](../docs/contributing/development.md)。对实际产物的静态检查、离线预览与编辑器验证见[验收说明](validation.md)。
