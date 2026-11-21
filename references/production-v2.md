# 可执行制作与交付验证

能力名：production-v2。入口qianxing.py produce、doctor、capabilities及verify，依赖随阶段检查，不自动安装依赖或修改全局配置。现有schema 1命令保持兼容。

schema 2支持client、level、storage、native、assets、protocol、protocol_native、animation、graphs、gil、simulation、experiment、platform、project，至少一项；可增加portable配置启用[可迁移制作与重建](portable-delivery.md)。client选择source或assembly；其余阶段以spec路径引用同名指南中的配置。native选择base，以及spec或[摘要绑定plan](native-changes.md)其中之一；与level新建互斥。所有配置相对各自文件解析，输出必须是新目录。

可选 beyond 阶段见[模拟器后端](beyond-backend.md)，以 spec 指定场景；支持 `@level` 绑定本轮最终GIL和默认随包后端的portable交付。外部Lua模型与软件预览独立报告，任一必需断言失败不提交输出。

最终GIL在模拟前自动执行[工程对象与引用检查](project-index.md)，核对已校准客户端层级、脚本及原生引用。project.spec可以声明其它GIL/GIA和必需关系；存在最终GIL时清单必须恰有一个@level输入，不能只验证无关参考文件。失败不提交；未索引引用仍在报告中列出，不证明任意ID迁移安全。

随后执行[最终Lua检查](client-check.md)：编译最终GIL全部脚本映射及交付目录Lua，包含没有单独导出的脚本。缺少必需Lua 5.3编译器、非法正文编码或语法错误阻止提交；没有脚本时为not_applicable。client-check.json属于静态证据，不代表API/引用交叉检查或宿主运行通过。

platform通过spec执行[平台版本与配置检查](platform-profiles.md)，未通过或未检查阻止生成提交。通过仅证明显式配置规则，报告artifact_verified=false，不代替最终GIL的平台配置回读；配置、目录和原文摘要纳入依赖，portable支持独立迁移。

执行顺序为输入核对→源码与资源→原生基底→严格图构建／替换→Lua嵌入→最终原生审计→声明的模拟／实验→清单。生成存储时将同源图和资源纳入图构建；已有图替换通过build schema 2声明。gil给出精确mapping；有图时默认消费图输出。失败不提交产物目录。

```text
python scripts/qianxing.py doctor
python scripts/qianxing.py capabilities
python scripts/qianxing.py produce JOB.json --out NEW_DIRECTORY
python scripts/qianxing.py verify NEW_DIRECTORY
```

交付清单绑定源配置、Lua、工具、编译后端及产物摘要。`verify` 校验当前文件与清单。对带可迁移输入的产物，先用 `--portable` 校验随附输入，再按需要审阅并显式重建。重建按 `artifacts` 交付角色比较正文，包含 JSON 和生成源码。[可迁移交付与重建](portable-delivery.md)

environment.json记录生成前的依赖检查；dependency-graph.json记录实际有序阶段、输入／工具、阶段产物及依赖边。资源先生成再创建／修改基底，随后严格构图与嵌入；最终client.lua须与指定GIL映射正文相同。模拟场景使用@level读取此最终产物。required阶段失败时输出目录不提交，已有输出路径拒绝覆盖；输入变化也拒绝提交。

两种中性整合配置可以分别采用单整数槽与双槽布尔／列表布局，变化模板别名、记录版本、素材数量及开发／保留集。失败用例包括未知schema、缺环境、源变更、输出已存在、原生审计错误及最终场景断言失败。独立重建比对交付正文，运行报告中的路径和耗时分别保留。

capabilities默认只报告可用源码和支持范围；通过--evidence指定checks.json时，只有源码、规则、测试支撑文件、后端及实际必需用例全部匹配才显示对应离线证据。证据schema 3及失败规则见[验证证据闭环](validation-evidence.md)。doctor只检查当前Python、Node、Pillow、Lua与后端入口，不以模块存在推断宿主通过。

人工验收：在千星奇域导入本轮最终GIL，核对图及UI挂载；启用客户端日志，执行首次操作、重开与关闭；有存储时按同玩家、同发布关卡完成首次读、实际进度、写入回读、结算及重进读取。保留文件摘要、设备和实际结果，未执行项保持not_checked。
