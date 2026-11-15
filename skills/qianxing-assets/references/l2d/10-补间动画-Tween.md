# 10 · 补间动画（Tween）：能省掉什么、不能省什么

**结论先说**：目标软件**有**完整的一套补间 API（DOTween 风格），所有我们要用的控件字段都标了 Tweenable。
它能**砍掉整个空转负载**（呼吸那部分），但**砍不掉视点跟随那部分**。
前提是一个尚未确认的点：`tweenDataTable` 的格式——这是唯一的卡点，用附带的探测脚本一次问清。

---

## 10.1 API 有什么（已确认）

```lua
--- 为对象的 Tweenable 字段创建补间动画
game.Tween(object, tweenDataTable, duration)   --> Tween
game.TweenSequence()                           --> TweenSequence
```

**Tween 方法**：`SetEase(EaseType)`、`SetRelative(bool)`、`Play/Pause/Resume/Restart/Complete()`、
`Kill(complete)`、`SetOnComplete(fn)`、`SetOnStepComplete(fn)`、`SetLoops(times)`
（文档写"**负数表示无限循环**"）。

**TweenSequence 方法**：`Append(tween)`、`Join(tween)`、`Insert(time, tween)`、
`AppendInterval(sec)`、`AppendCallback(fn)`、`InsertCallback(time, fn)`、
`Play/Pause/Resume/Restart/Complete/Kill/SetOnComplete/SetOnStepComplete/SetLoops`。

**EaseType** 有 31 种（`Linear`、`InSine/OutSine/InOutSine`、`InQuad`…`InBounce`）。

### 哪些字段能补间（这是关键）

| 控件 | 字段 | 我们拿它做什么 |
|---|---|---|
| `ClientUIBaseControl` | `anchoredPositionX/Y` | 呼吸位移、骨骼位移 |
| | `sizeDeltaX/Y` | 眨眼压缩、变粗细 |
| | `localRotationX/Y/Z` | 呼吸旋转、摆臂、甩发 |
| | `localScaleX/Y/Z` | （备选实现手段） |
| `ClientUIImageControl` | `imageColor` | 眨眼淡出、整体透明度 |
| | `softEdgeWidthX/Y`、`fillAmount` 等 | （用不到） |

**也就是说：我们逐帧写的每一个字段，都在 Tweenable 名单里。**

---

## 10.2 唯一卡点：`tweenDataTable` 的格式

签名是确认的（PDF 与转录件一致），但**这张"创建"表的内容拿不到**：

| 材料 | 情况 |
|---|---|
| API PDF | 文字层里"创建"只有**标题**（表格是位图）；而 Tween 那一页在 `api_pages` 抽取时**恰好缺失**（p11 不在） |
| 现有转录件 `Lua_API_关键接口速查.md` | 只有签名，没有表结构 |
| 使用指南 docx | **完全没提** Tween（正文约 145 段，含 Tween/补间 0 处） |
| 工具自带文档 | 只有字段级的 `Tweenable` 标记，没有用法示例 |
| 工作区内所有 .lua | 没有任何调用 `game.Tween` 的样例 |

所以只能实机问 —— 用 **`attachments/l2d_tween_probe.lua`**（附带的探测脚本）：
它按 6 个阶段依次问清 A 格式 / B 循环 / C 序列往返 / D 控件数组 / E Kill 语义 / F **谁在驱动**，
每段打一行结论，最后给汇总。把日志发回来就能确定实现方式。

**最可能的候选**（脚本会逐个试）：

| 候选 | 说明 |
|---|---|
| ① `{x=…, y=…}` | 用简写字段名 |
| ② `{anchoredPositionX=…, anchoredPositionY=…}` | **最可能**：直接照 Tweenable 字段名 |
| ③ `{anchoredPosition={x, y}}` | 用复合字段 |
| ④ `{ {field="anchoredPositionX", to=…} }` | 数组 + field/to |
| ⑤ `{anchoredPositionX={to=…}}` | 字段名 → 目标对象 |

---

## 10.3 能省掉什么：负载账

先看现在的负载（9941 个控件，`updateStride=2` = 30Hz）：

| 状态 | 写入/帧 | 写入/秒 | 由什么构成 |
|---|---|---|---|
| **鼠标不动**（游戏里绝大多数时间） | 866 | **52k** | 几乎全是**呼吸** |
| 鼠标移动 | 3286 | 197k | 呼吸 + 骨骼场 + 头部形变 |
| 不做任何跳过 | 9941 | 596k | 全量 |

### 补间能砍掉的

**呼吸**是纯周期运动，跟交互无关 —— 正好是补间最擅长的：

```lua
-- 每个部件一个"出去→回来"的两段序列，无限循环
local q = game.TweenSequence()
q:Append(game.Tween(part0, {anchoredPositionY = y + amp}, T/2):SetEase(Enum.EaseType.InOutSine))
q:Append(game.Tween(part0, {anchoredPositionY = y      }, T/2):SetEase(Enum.EaseType.InOutSine))
q:SetLoops(-1):Play()
```

- 26 个部件 → **26 个序列 / 52 个补间**，**创建一次，之后引擎自己跑**
- 由此空转写入从 **866 次/帧（52k/秒）→ 0**
- 顺带省掉脚本侧的呼吸运算（每帧 9941 个图元 × 约 20 次浮点）

> ⚠️ 注意 API 里**没有 yoyo 参数**（`SetLoops(times)` 只有一个参数）。
> 要"出去再回来"就得用**两段序列**（上面那样）。探测脚本的 B 段会确认
> `SetLoops(-1, LoopType)` 这种第二参数到底收不收。

### 补间砍不掉的：视点跟随

视点跟随的三个分量（虹膜滑动 / 头部柱面形变 / 躯干位移场）都是**逐图元**的，
目标值随光标位置变化。用补间要付的代价是：**每次光标变化都要新建 N 个补间**（N ≈ 9941）。

- 光标每帧都在动的话：9941 × 30 = 30 万次补间创建/秒，还带对象分配 ——
  **不会比现在的 19.7 万次属性写入便宜**，很可能更贵。
- 光标不动的时候：现在是 **0 写入**（已有 epsilon 闸门），补间也没有额外收益。

**所以视点跟随保持现在的逐帧写法**（`gazeEps` 闸门 + `posEps` 写入缓存 + stride 降频）。

### 净效果

| | 现在 | 补间化呼吸之后 |
|---|---|---|
| 空转（鼠标不动） | 52k 写入/秒 | **≈0**（只有眨眼那几十帧） |
| 交互（鼠标移动） | 197k 写入/秒 | 197k 写入/秒（不变） |

**为什么这仍是大改善**：游戏里角色绝大多数时间处于"鼠标不动"的空转状态，
而进关卡顿/耗电也正是被这种**持续**负载拖出来的。把持续负载打到 0，
只在玩家真的在动鼠标时才花销，是这轮优化的真正价值。

### 额外红利（待 D 段确认）

如果 `game.Tween` 的 `object` 接受**一组控件**，那连"26 个部件"都能并成 1 个补间。
探测脚本的 D 段会问清楚。

---

## 10.4 眨眼：可选，收益小

眨眼的形状是"快速压缩 → 保持 → 慢速张开"，用序列能表达：

```
Append(压缩 0.06s, InQuad) → Append(张开 0.09s, OutQuad) → [随机间隔] → 循环
```

- 眼内容 335 个控件 × 2 个字段 → 用**一个** tween 同时补位置和尺寸（如果格式支持多字段）
- 但**随机间隔**没法纯靠序列表达：要么固定节奏、要么预先烘一段"含 N 次随机眨眼"的长序列
  再循环（每轮略重复，间隔若烘成 30~60 秒基本看不出来）、要么保留逐帧回调、用完成回调续排
- **建议**：先不动。

理由：眨眼只在眨眼那几帧写入（约占 1.5% 时间），**平均成本很低**；
而它依赖随机数与状态机，改成补间反而更绕。等呼吸改完、空转确实打到 0 之后再评估。

---

## 10.5 如果探测结果是"脚本泵驱动"（❌）

那意味着补间只是**引擎提供的便利写法**，推进仍依赖脚本的逐帧回调 —— 收益就只剩
"省掉自己写插值代码"，**省不掉调用**。这种情况下：

- 空转负载不会变成 0，最多是每帧写 26 个部件的补间目标（比现在写近万个图元省得多，
  但比 0 差）
- 这时更值得走的是另一条路：**把静止姿态烘成一张整身贴图 + 条带位移**
  （见 `04-在游戏里重建.md` 的"想同时降静态成本"一节），但要先确认贴图资源与
  RenderTexture 类能力是否存在

所以 F 段的答案决定了后续路线，**这是最该先问的一件事**。

---

## 10.6 落地顺序（等探测结果回来再做）

1. **先探测**：跑 `l2d_tween_probe.lua`，拿到日志
2. 若 A 段命中 + F 段是"引擎驱动"：
   - 加一个 `ktween(obj, data, dur)` **包装器**：按 A 段结论拼 data、并缓存命中格式；
     格式不认时**自动回退**到现有的逐帧写法（和按键/光标事件一样做多兼容）
   - 呼吸改走补间（`CFG.breathViaTween = "auto"`）；开启后 `partMotion` 里不再叠加呼吸项
   - 验收：空转 `writes/frame` 应降到个位数；呼吸幅度与原来一致（逐帧对照 `GetStatus`）
3. 若 A 命中但 F 是"脚本泵"：改成"每帧只写 26 个部件的补间目标"，
   并重新量负载，再决定是否继续
4. 若 A 全不命中：把候选格式再扩几种（形如 `{property=…, value=…}`、
   `{"anchoredPositionX", value}` 位置参数等），或去找**未裁切的官方文档**

---

## 10.7 规则 / 不变量

- 我们把补间用在**"与交互无关"的运动**上（呼吸、待机摆动、风吹这类周期动作）；
  交互驱动的动作也可以改补间，代价见 10.3。
- **与交互相关的逐图元形变（视点跟随）** 我们保持逐帧写法 —— 补间化会更贵（10.3 有账）。
- 需要"出去再回来"时用**两段序列**（API 里没有 yoyo 参数，除非 B 段证明收第二参数）。
- 销毁控件前**要 Kill 自己的补间**（探测脚本 E 段会确认 Kill 是否真的能停住）。
- 格式不确定时**不要硬编码**：用包装器 + 回退，先跑探测再落地。
- ⚠️ 未验证：`tweenDataTable` 格式、是否引擎驱动、`imageColor` 补间的实际表现、
  以及补间在 `PauseLevelTime(true)` 下会不会跟着暂停。
