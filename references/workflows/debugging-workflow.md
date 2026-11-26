# 工程排障

先用实际触发步骤和交付文件的 SHA-256 校验值定位首个失败环节。比如客户端已经发送请求时，下一步核对服务端是否收到、以哪个实体身份处理、实际回复了什么。选与故障相关的工具和证据。

| 现象 | 路径 |
| --- | --- |
| 工具启动失败、Lua 语法或产物异常 | [安装自检](../../docs/installation.md)、[工程只读诊断](project-diagnosis.md) |
| 初始化报错、控件缺失或点击后无回调 | [启动模型与游戏内自检](client-simulation.md)，再按[软件预览](beyond-backend.md)检查布局和输入 |
| 已有试玩日志，需定位打印或源码行 | [日志诊断](log-diagnostics.md) |
| 信号发出后状态未生效，或最终图的端口类型不符 | [联合模型](joint-simulation.md)和[最终原生数据流](../graph-code/native-dataflow-validation.md) |
| 保存后仍读到旧值或跨次重进异常 | [存储诊断](storage-authoring.md)，按首次读取、业务更新、写入确认及同一发布关卡重进逐段取证 |
| PNG 重建粗糙、坐标偏移或控件超预算 | [素材检查](../assets/asset-inspection.md) |
| 文件与交付记录不一致 | [交付文件与清单核对](project-diagnosis.md#交付文件与清单不一致) |

按[验证等级](validation.md)记录所执行的检查，涉及玩家路径的改动用[游玩记录](playability-workflow.md)覆盖相关设备和操作。
