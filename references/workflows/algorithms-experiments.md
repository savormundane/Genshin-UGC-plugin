# 通用算法与观察实验

通用算法与观察实验是当前可用的本地工具。可用 `client assemble` 内联 `scripts/runtime_algorithms.lua`。`scripts/experiments.py` 在独立 Lua 模型中执行实验，游戏策略、课程和经济参数由项目提供。

| Lua 接口 | 用途 |
| --- | --- |
| `rng(seed)` | 独立随机流，支持 `next`、`integer` 与 `restore`。 |
| `heap` | 稳定优先队列，同优先级按入队顺序处理。 |
| `shortest(start, goal, neighbors)`、`grid(width, height, blocked)` | 计算路径、代价与工作量。邻接由调用方给出有序的 `{to, cost}` 项，网格适配器提供四邻接。 |
| `segment_distance`、`in_circle`、`in_rect` | 基础几何检查。 |
| `reservations`、`machine(initial, transitions)` | 用 `claim`、`release`、`expire` 管理预约，按声明执行状态切换。 |
| `clock`、`replay`、`cache(capacity, load, release)` | 推进或暂停时钟，按非递减时间投递记录，维护可关闭的 LRU 缓存。 |

路径邻接、障碍、预约存活条件、状态转换和随机流归属均由项目输入。RNG状态范围1..2147483646；每条业务随机流单独保存，测试策略不消耗权威流。最短路拒绝负代价，不承诺解决任意连续碰撞与多人避让问题。

```text
python scripts/qianxing.py experiment run EXPERIMENT.json --out NEW_DIRECTORY
python scripts/qianxing.py experiment compare BEFORE.json AFTER.json --out NEW_COMPARISON.json
```

EXPERIMENT采用schema=2，包含source、entry、development_seeds、holdout_seeds、split、policies、metrics及可选tuning。Lua入口以(seed,policy)调用，metrics是要读取的全局字段路径；每个观察使用独立模型。开发集和保留集各自不能有重复种子，两组也不能重叠。`holdout` 禁止使用 `tuning`。报告保留失败的观察结果，并分别记录模型耗时和业务工作量。

`compare` 读取两份 `observations.json`。分组、种子和策略集合须一致，结果逐例给出差异和数值差。同一个种子也可能因策略不同而消耗不同数量的随机数，比较时需核对随机数的使用情况。用保留集调参后，应重新选取独立验收样本。结果不能冒充真人策略、完整游玩时间或宿主FPS。

在 MCP 中，用 `experiment_run` 返回的 `output` 定位 `observations.json`，将对应的 `outputs_sha256["observations.json"]` 传给 `experiment_compare`。若个别用例失败，整体状态为 `failed`，已完成的观察报告仍保存在输出目录。

示例可在 3×3 网格绕开中心格，在 4×2 网格绕开第二排第二格。可用两条不同种子的独立随机流分别测试。实验配置可用开发种子[2,3]／保留种子[8]和策略[1,2]，另一配置选择保留集独立验证。负边代价、零RNG状态、重叠种子集及保留集调参均拒绝。观察失败保留调用参数、错误栈和最后一步／信号轨迹；failed结果的experiment run返回非零退出码。工作量由metrics中的项目指标提供，model_seconds单独记录模型进程耗时。
