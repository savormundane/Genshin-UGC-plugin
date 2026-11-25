# 中性协议接入示例

共享流程连接Graph Code与Client Lua，容器挂载由GIL处理。业务权威、阶段和成员规则属于项目，不随示例指定玩法。

两套声明配置：
- [有序命令](examples/ordered.json)：单整数请求、连续序号。
- [状态快照](examples/snapshot.json)：向量状态、允许跳过旧快照序号。

配置交给现有produce的protocol配置，或在Python中先用production_core.protocol验证，再调用protocol_codegen.generate输出原生信号资源、wire.json与client_bridge.lua。依赖包内核心及实际编译后端；不能在未核对最终挂载时声称已连通。

生成信号含session_key、round_id、sequence_id信封，字段顺序以wire为准；旧项目协议不自动迁移。客户端用生成桥注册和发送；服务端Graph Code根据生成定义接收并验证真实来源身份，业务状态更新与响应另由项目实现。快照不是任意Lua表通信。

检查重复／缺口／旧修订、两端类型及最终回读；模型只证明声明逻辑。具体合同与类型见[协议schema 2](../../protocol-v2.md)，组装见[组装流程](../../qianxing-gil-assembly-pipeline/README.md)。
