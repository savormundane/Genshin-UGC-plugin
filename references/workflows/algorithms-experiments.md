# 通用算法与观察实验

能力名：algorithms-experiments。scripts/runtime_algorithms.lua可通过client assemble内联；scripts/experiments.py运行独立Lua模型观察，不携带游戏策略、课程或经济参数。

Lua接口：rng(seed)及next/integer/restore；heap及push/pop（同优先级稳定）；shortest(start,goal,neighbors)返回路径、代价、工作量，neighbors返回有序{to,cost}；grid(width,height,blocked)提供四邻接适配；segment_distance、in_circle、in_rect；reservations的claim/release/expire；machine(initial,transitions)；clock的tick与paused；replay按非递减时间投递；cache(capacity,load,release)提供LRU与close。

路径邻接、障碍、预约存活条件、状态转换和随机流归属均由项目输入。RNG状态范围1..2147483646；每条业务随机流单独保存，测试策略不消耗权威流。最短路拒绝负代价，不承诺解决任意连续碰撞与多人避让问题。

```text
python scripts/qianxing.py experiment run EXPERIMENT.json --out NEW_DIRECTORY
python scripts/qianxing.py experiment compare BEFORE.json AFTER.json --out NEW_COMPARISON.json
```

EXPERIMENT采用schema=2，包含source、entry、development_seeds、holdout_seeds、split、policies、metrics及可选tuning。Lua入口以(seed,policy)调用，metrics是要读取的全局字段路径；每个观察使用独立模型。两个种子集必须去重且互斥，holdout不允许tuning。失败作为观察保留；模型耗时与业务工作量分别记录。

compare输入两份observations.json，要求同一分组、种子和策略集合，输出逐案例与数值差值。相同种子不自动构成等消费因果对照；保留集一旦用于调参便应重新划分独立验收样本。结果不能冒充真人策略、完整游玩时间或宿主FPS。

中性例可使用3×3避开中心格与4×2避开第二排第二格的路径查询，以及两条不同种子的独立随机流。实验配置可用开发种子[2,3]／保留种子[8]和策略[1,2]，另一配置选择保留集独立验证。负边代价、零RNG状态、重叠种子集及保留集调参均拒绝。观察失败保留调用参数、错误栈和最后一步／信号轨迹；failed结果的experiment run返回非零退出码。工作量由metrics中的项目指标提供，model_seconds单独记录模型进程耗时。
