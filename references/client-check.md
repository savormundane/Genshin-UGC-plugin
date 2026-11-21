# 最终Lua检查

能力名：client-check。使用lupa.lua53编译Lua 5.3文本，不执行被检查正文。入口为`qianxing.py client check`及produce schema 2的最终检查阶段。覆盖语法、全部内嵌脚本映射及摘要绑定的错误行定位；显式合同启用[客户端API检查](client-api-check.md)。工程引用交叉检查仍保持not_checked。

## 独立检查

```text
python scripts/qianxing.py client check client.lua
python scripts/qianxing.py client check level.gil --out NEW_REPORT.json
python scripts/qianxing.py client check level.gil --mapping main.lua
python scripts/qianxing.py client check level.gil --source-map source-map.json
```

Lua输入检查该文件；GIL默认检查所有脚本映射，包括未挂载或没有另存为Lua文件的映射。`--mapping`为完整映射名，只检查选定脚本，报告scope=selected_mapping，不能代替完整产物检查。映射不存在、不唯一、GIL客户端关联异常或未知扩展名直接拒绝。报告路径必须尚不存在，不覆盖原始输入或已有报告。

返回status与每份正文的原始字节摘要、解码文本摘要、编译器版本和诊断。语法错误返回failed和非零退出码；没有脚本的GIL返回not_applicable，不能称为脚本编译通过。空Lua正文是合法的空程序，仍实际编译。缺少lupa.lua53时有脚本的检查失败，不跳过为通过。不会安装依赖或更改全局环境。

脚本正文必须使用已校准的字节字段编码。错误字段类型或与文本编码混用时直接拒绝，不能把读取不到的正文当成合法空脚本。

## 两种中性配置

第一种：新建关卡的level spec登记`main.lua`和`helper.lua`，根控件挂载main.lua，两个正文均为合法Lua。执行`produce`后，client-check.json中level.gil应有两条passed脚本记录。将helper.lua改为`function Broken(`，即使它没有挂载，最终制作也必须失败且正式输出目录不出现。

第二种：已有GIL包含`panel.lua`和`worker.lua`。只替换panel.lua时，仍须检查worker.lua；将worker.lua破坏后，`client check --mapping panel.lua`可以通过，但不带`--mapping`的完整检查及produce必须失败。改回合法正文后，显式portable制作可在原输入路径不可用时独立重建。

上面是参数化检查场景，使用[原生结构生成](native-authoring.md)的源码映射及[原生维护](native-maintenance.md)的已有基底合同，不携带游戏页面或布局。

## 行号与装配

`--source-map`接受[Lua源码装配](client-assembly.md)生成的schema 2映射。检查正文必须匹配assembled_source_sha256；内嵌GIL优先核对embedded_source_sha256，并按embedded_mapping绑定唯一脚本。多个脚本且未声明绑定时拒绝；段落重叠、越界及未知版本也拒绝。摘要标识所检正文，不是数字签名或对外部编辑映射来源的认证。

编译错误同时保留完整编译器信息、最终正文行号和能确定的原模块行号。错误在生成前缀、段落间隔或文件末尾时，origin可为null，不强行归到邻近模块。一个脚本的映射不会用于另一个脚本。源文件无需存在于原路径，行号来自随交付保存且绑定正文的映射。

## 制作与证据

produce schema 2在原生修改、挂载和Lua写回之后，检查最终level.gil的全部映射及交付目录中的Lua文件；Graph Code中间目录不作为客户端Lua输入。该检查在模拟、实验及正式输出提交之前执行。失败时保留原输入，不提交正式目录。已有schema 1入口行为不变。

client-check.json属于证据文件；清单和依赖图记录本阶段及其输入。可迁移交付比较Lua/GIL正文，报告则保留各轮检查结果。source-map若属于装配流程，会在最终GIL正文核对后用于错误定位。

语法通过不证明game API存在、权限正确、控件/变量/协议/资源有效，也不证明生命周期或实机运行。报告static层与lua_model、editor、host分开；API和引用交叉检查尚未实现的部分不标通过。

交付时导入最终 GIL，核对实际脚本挂载并收集宿主日志。
