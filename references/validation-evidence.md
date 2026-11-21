# 验证证据闭环

能力名：validation-evidence。由维护者开发工作区的 `run_validation.py` 采集，插件内的 `qianxing.py capabilities` 读取；共用 `scripts/validation-contract.json` 中的套件、运行规则和必需用例清单。不改变游戏的运行合同。

## 公开仓库与开发工作区

**本页的完整证据采集器和对应开发测试不随当前公开仓库提供。** `toolkit/plugins/development/` 是维护者工作区路径；仅克隆本仓库，不会得到该目录。`validation-contract.json`、`capability-layers.json` 和 `test-impact.json` 中出现的测试名是证据与影响范围登记，不表示这些测试文件均已公开，也不表示本轮执行过。

公开仓库已有的检查入口见[开发指南](../docs/contributing/development.md)和[工具导航](../scripts/README.md)。贡献者按改动使用这些入口即可，不需要为普通修改补齐整个维护者工作区。

没有证据目录时，`qianxing.py capabilities` 仍可查看已实现操作和范围；它不会据此声称执行通过。下面保留完整采集和读取方式，供持有相应工作区或既有证据的维护者使用。

## 采集与读取

在包含该开发目录的工作区根执行采集。输出必须是尚不存在的路径，Python 及 Lua、Pillow、Node 依赖由当前环境提供；实际目录以工作区文档为准。

```text
python -X utf8 -B toolkit/plugins/development/run_validation.py --out NEW_DIRECTORY
```

读取时进入插件根目录，并将证据路径换成采集输出的实际路径：

```text
python -X utf8 -B scripts/qianxing.py capabilities --evidence CHECKS_DIRECTORY/checks.json
```

checks.json使用证据schema 3。它关联源码与结构检查输入、测试正文和支撑脚本、fixtures、运行规则、Python及其标准库/扩展、Lua/Pillow包和Node摘要。UGC_LUA_TEST_PATH指定的测试依赖也单独记录；读取证据时须使用相同依赖。不会安装环境、更新全局配置或改写历史报告。

每个套件由独立进程执行，输出同名.cases.json及日志。unittest记录实际用例ID和结果；非unittest脚本仅记录script通过，不能代替具名必需用例。跳过、预期失败、空unittest运行、隐藏在exit=False后的失败与重复ID均不能作为通过。capabilities同时核对用例文件、结构报告及其摘要，只有当前证据和该能力的必需用例全部满足时显示offline_evidence=passed。

scripts/capability-layers.json按规则、生成、回读、Lua模型、原生图模型分别登记scope和required_cases。capabilities仅在证据有效且该层所有必需用例实际通过时标记该层passed；未登记的层保持not_registered/not_checked。editor和host不能由离线用例认证。--platform与--mode仅选择[平台上下文](platform-profiles.md)，不证明产物平台版本。

## 修改合同与选择检查

新增套件写入suites；能力所需用例以“文件名::类名.方法名”写入coverage。新增运行时读取的Markdown登记到runtime_rules；其他开发夹具登记development_inputs。不得为消除失败删除必要覆盖项。

开发侧采集器的 `--changed` 按导入关系选择检查；运行规则、未知依赖、Lua、JSON 或验证基础设施变化会保守全选。普通说明 Markdown 只做结构检查；客户端 API 与 official 目录中的规则 Markdown 会影响行为检查。需要生成完整离线能力证据时，才使用对应的完整套件；定向修改记录实际覆盖范围，不将全量采集作为每次修改的要求。当前选择器的具体行为以开发侧实现为准。

正例：两种中性配置的实际用例均执行且证据依赖未变，可提供对应能力证明。反例：夹具修改、后端改变、用例跳过、仅运行部分必要用例、旧schema报告或用例文件缺失，均不能显示完整能力通过。专项测试由test_v32_regressions.py覆盖，实际编译与模型证据仍由各自套件提供。

这些摘要用于发现过期或不一致的本地证据，不是对不可信报告的数字签名。证据范围只覆盖已执行的离线规则；static、lua_model、native_graph_model、compilation_readback、software_preview、editor、host分别报告，编辑器及实机状态不会由此升级。
