# 验证证据闭环

能力名：validation-evidence。由开发入口run_validation.py采集，qianxing.py capabilities读取；共用scripts/validation-contract.json中的套件、运行规则和必需用例清单。不改变游戏的运行合同。

## 执行与读取

从工作区根执行，输出必须是尚不存在的路径；Python及Lua、Pillow、Node依赖由当前环境提供。

```text
python -X utf8 -B toolkit/plugins/development/run_validation.py --out NEW_DIRECTORY
python -X utf8 -B scripts/qianxing.py capabilities --evidence NEW_DIRECTORY/checks.json
```

checks.json使用证据schema 3。它关联源码与结构检查输入、测试正文和支撑脚本、fixtures、运行规则、Python及其标准库/扩展、Lua/Pillow包和Node摘要。UGC_LUA_TEST_PATH指定的测试依赖也单独记录；读取证据时须使用相同依赖。不会安装环境、更新全局配置或改写历史报告。

每个套件由独立进程执行，输出同名.cases.json及日志。unittest记录实际用例ID和结果；非unittest脚本仅记录script通过，不能代替具名必需用例。跳过、预期失败、空unittest运行、隐藏在exit=False后的失败与重复ID均不能作为通过。capabilities同时核对用例文件、结构报告及其摘要，只有当前证据和该能力的必需用例全部满足时显示offline_evidence=passed。

scripts/capability-layers.json按规则、生成、回读、Lua模型、原生图模型分别登记scope和required_cases。capabilities仅在证据有效且该层所有必需用例实际通过时标记该层passed；未登记的层保持not_registered/not_checked。editor和host不能由离线用例认证。--platform与--mode仅选择[平台上下文](platform-profiles.md)，不证明产物平台版本。

## 修改合同与选择检查

新增套件写入suites；能力所需用例以“文件名::类名.方法名”写入coverage。新增运行时读取的Markdown登记到runtime_rules；其他开发夹具登记development_inputs。不得为消除失败删除必要覆盖项。

--changed按导入关系选择检查；运行规则、未知依赖、Lua、JSON或验证基础设施变化保守全选。普通说明Markdown只做结构检查；客户端API与official目录中的规则Markdown会影响行为检查。最终版本运行全部套件。

正例：两种中性配置的实际用例均执行且证据依赖未变，可提供对应能力证明。反例：夹具修改、后端改变、用例跳过、仅运行部分必要用例、旧schema报告或用例文件缺失，均不能显示完整能力通过。专项测试由test_v32_regressions.py覆盖，实际编译与模型证据仍由各自套件提供。

这些摘要用于发现过期或不一致的本地证据，不是对不可信报告的数字签名。证据范围只覆盖已执行的离线规则；static、lua_model、native_graph_model、compilation_readback、software_preview、editor、host分别报告，编辑器及实机状态不会由此升级。
