# 09 · 端到端 SOP 与检查表

把整条链路串成可执行的步骤。命令以本项目为例（Windows + Git Bash）。

> **这一节是"我们跑过一遍的命令 + 检查点"**，不是唯一流程。
> 脚本名、目录名、参数都可以换；**要保住的是每个阶段的"检查点"** ——
> 那些才是保证最终效果的东西。数值一律当**参考量级**看，不要当及格线。
>
> **只用工具本体（不跑我们的 Python 封装）也能做完整条流水线**：
> 拟合与导出都在 `GE_IMG_Tool.exe` 的命令台上完成，等价命令序列是
> `fit recommend --json` → `advanced set …`（含 2.0 的三个开关）→ `fit shapes N` →
> `fit start --until full --ack-high-res`（长跑用 `--timeout 60` + `fit resume` 分段）→
> `inspect`（看图）→ `next` → `export dataset --out <目录>`。
> 细节见工具手册 `docs/GEIMG_AI上手提示词.md`；本节下面的 `attachments/*.py`
> 是我们为了批量跑 26 个部件、以及做边缘处理/构建/验证而写的封装。

**Python 路径**：下面命令里统一用 `$PY` 占位。本机当时没把 python 加进 PATH，
所以用的是解释器的绝对路径；你自己按环境改（`py -3`、`python3` 都行）。
```bash
PY="py -3"          # 按自己的环境改，例如 PY="/usr/bin/python3"
```

目录约定（相对知识库根目录）：
```
parts/                手扣的 26 层 PNG（源）
fit_10k/              超拟合图元数据集（10030 图元）
attachments/          本包附带的脚本
l2d_anim*.lua         交付物：自包含动画
l2d_theater*.lua      交付物：动画 + UI + 快捷键
l2d_preview*.html     调参与验收用的浏览器预览
```

---

## 阶段 0 · 准备（一次性）

```bash
# 1) 确认手扣层符合约定（同尺寸 / 二值 alpha / 编号即层序）
$PY attachments/l2d_check_layers.py parts/
```

**检查点**：所有部件同尺寸、`中间alpha=0`、透明区 RGB 是**纯白**（记住这个颜色，`06` 要用）。

```bash
# 2) 校正呼吸 rig（每个部件 w / delay / rot / pivot / group）
$PY attachments/l2d_rig_breath.py          # 或手工编辑 attachments/l2d_rig.json
```

---

## 阶段 1 · 拟合

```bash
# 单部件试参数（先小预算跑通，看质量拐点）
$PY attachments/l2d_superfit.py --parts "parts" --out "parts/_试跑" --only 0001 --workers 1

# 全量（26 部件并行 6 进程；10k 版耗时约 20 分钟量级）
$PY attachments/l2d_superfit.py --parts "parts" --out "fit_10k" --workers 6
```

**检查点**：
- `_summary.json` 里的 `total_shapes` 与预期一致
- 每个 `part_*/shapes.json` 的 `space` 必须是 `source_image_pixels`
- 抽 2~3 个部件把 `preview.png` 和原图叠一下，确认不错位

⚠️ `_summary.json` 里的 `edge_aware` 与 `manifest.json` 可能不一致（见 `02` 的 2.2）——
常规按"要保边就开"处理（见 `02` 的 2.0）；如果发现勾线断了/边缘画不出来，
再按那节的假设关掉对照跑一次，自己复现确认。

---

## 阶段 2 · 边缘处理（数据级）

```bash
# 出报告：剔了多少溢出、缩了多少边界、改色多少、外溢质量前后对比
$PY attachments/l2d_edge_clean.py --out "edge_report_10k.json"

# 出诊断对照图（源图/未修/修复，外缘放大 6 倍）
$PY attachments/l2d_edge_probe.py --out "edge_diagnosis.png"
```

**检查点**（本项目基线，异常时对比）：
- 剔溢出 ≈ 90 个、缩回轮廓 ≈ 633 个、轮廓改色 ≈ 3800 个
- 最外 1px 环「明显偏亮(>25)」像素 < 200
- 内部 RMSE（离轮廓 >3px）**不应变差**

这两步都**只在内存里做，不改 `shapes.json`**。

---

## 阶段 3 · 生成交付物

```bash
# 超拟合版（10k）：Lua + 剧场版
$PY attachments/l2d_build_anim.py --preset superfit

# 普通版（3518）：同样两条产物
$PY attachments/l2d_build_anim.py --preset normal

# 浏览器预览（两个版本各一份）
$PY attachments/l2d_build_showcase.py --source "../fit_10k" --out "l2d_preview_10k.html"
$PY attachments/l2d_build_showcase.py                                 --out "l2d_preview.html"
```

**构建脚本会自动做的事**：读 rig → 读图元 → 边缘处理 → 推骨骼锚点（脚底/髋线/脖子/头顶/躯干宽度）
→ 推眨眼几何 → 量虹膜安全范围 → 按图元数决定 `updateStride` → 填 CFG → 写出。

**检查点**（构建输出里会打印）：
```
部件 26 个，图元 9941 个（源：_超拟合_10k），默认 updateStride=2
骨骼锚点：脚底 y=594.5 脖子 y=318.9 躯干 x=214.5±98.0
边缘处理：剔溢出 90 个 / 缩回轮廓 633 个 / 轮廓改色 3841 个
虹膜安全范围：{ eyeL = {l=5, r=0, u=3, d=0}, eyeR = {l=0, r=0, u=7, d=0} }
```

---

## 阶段 4 · 自动验证（不进游戏就能查的）

```bash
# ① 运动与负载：14 项（语法/加载/铺图元/坐标/呼吸/眨眼/视点/动作/闭眼还原/负载/静态模式…）
$PY attachments/l2d_verify_anim.py      --lua l2d_anim_10k.lua
$PY attachments/l2d_verify_anim.py      --lua l2d_theater_10k.lua    # 剧场版会多报 UI/按键数量

# ② 逐动作位移量测：证明每个动作真的在动，且互不影响
$PY attachments/l2d_verify_actions.py       --lua l2d_anim_10k.lua

# ③ 剧场 UI 与快捷键：把 prefab ID 填成假值跑 UI 路径
$PY attachments/l2d_verify_theater_keys.py  --lua l2d_theater_10k.lua
```

**检查点**（本项目基线）：

| 项 | 期望 |
|---|---|
| 语法 / 加载 | 全部通过 |
| 铺图元 | 9941 / 9941，约 249 帧 |
| 位置范围 | 不超出半画布（0 个越界） |
| 闭眼 | 681 个控件压缩 + 681 个 alpha 降 + 681 个还原 |
| 骨骼场 | 脚 0.00px < 躯干 < 头，梯度单调 |
| 负载 | 空转 ≈866 次/帧、移动 ≈3286 次/帧（`updateStride=2`） |
| 按键 | 16/16 注册成功、回调全返回 true |
| 跳跃 | 整身位移 56~59px，与历史数字一致 |

⚠️ **这些验证用的是桩函数**，不含引擎真实开销。桩要尽量严格（见 `08` 元教训 1）。

---

## 阶段 5 · 浏览器验收

```bash
# 起个静态服务（本项目用 8743 端口）
$PY -m http.server 8743
# 打开 http://127.0.0.1:8743/l2d_preview_10k.html
```

**人眼检查项**：
- [ ] 切到「原 PNG」「叠影对照」「差异」三个视图，看轮廓是否对齐
- [ ] 放大镜（M）看边缘：硬边 vs 原图二值边，有没有白描边
- [ ] 鼠标在画布上移动：虹膜 / 头 / 身体 / 发丝是否分层运动，脚是否钉住
- [ ] 数字键 1~0：预设与动作是否生效，屏幕左上角是否显示状态
- [ ] H 键：功能表是否完整（含"游戏里空格=跳跃"的说明）
- [ ] 跳跃（游戏版空格）：起跳高度、下蹲、摆臂、落地缓冲
- [ ] 缩放窗口：布局是否错乱、面板是否溢出

---

## 阶段 6 · 真机

1. 把 `l2d_theater_*.lua` 放进编辑器/场景
2. **核对三个 prefab ID**（换场景必须改）：
   `imagePrefabId` / `textPrefabId` / `areaPrefabId`
3. 运行，看日志：
   ```
   [GEIMG] 画布 WxH，容器中心 (…, …)
   [GEIMG] 头部柱面：中心 (…) 半径 (…)
   [GEIMG] 骨骼：躯干场 脚底 y=… 脖子 y=…
   [GEIMG] 图元 9941 个，部件 26 个，动画 开
   [GEIMG] EnableUpdate(true) —— 已打开逐帧回调
   [GEIMG] 快捷键绑在「…」：成功 16 / 16 个
   [GEIMG] UI 建好：背景圆 7 个，共 92 个控件
   [GEIMG] 图元铺完：9941 个
   [GEIMG] 层序重排完成：背景 7 · 角色 9941 · UI …
   ```
4. **真机专属检查项**（预览测不出来）：
   - [ ] 角色位置是否正确（坐标参考系）
   - [ ] 边缘硬度是否和预览一致（否则试 `enableSoftEdge = false`）
   - [ ] 按键是否被游戏界面占用（尤其**空格**）
   - [ ] 拖动条是否跟手（日志会打印光标坐标来源）
   - [ ] 进关卡顿不卡；每帧写入次数（`GetStatus().writesPerFrame`）
   - [ ] 文本框的 `\n` 是否换行

---

## 交付检查表（复制走用）

```
[ ] 手扣层：同尺寸 / 二值 alpha / 编号即层序
[ ] shapes.json：space = source_image_pixels，无错位
[ ] 边缘处理报告：外溢质量下降、内部 RMSE 不变差
[ ] 构建输出：骨骼锚点 / 虹膜安全范围 / updateStride 都有打印
[ ] verify_lua_anim：14 项通过，负载数字在预期区间
[ ] verify_actions：每个动作都有非零位移，互不影响
[ ] verify_theater_keys：16/16 按键注册成功
[ ] 浏览器验收：轮廓/边缘/视点/眨眼/动作/快捷键
[ ] 真机：坐标对、边缘对、按键没被占、拖动条跟手、不卡
[ ] 文档：prefab ID、未验证项、已知取舍都写清楚
```

---

## 换一个新角色要改什么

| 要改的 | 在哪 | 说明 |
|---|---|---|
| 手扣层 | `parts/<新目录>/` | 必须满足 `01` 的四条约定 |
| 呼吸 rig | `attachments/l2d_rig.json` | 部件编号 → w/delay/rot/pivot/group **要重新配** |
| 拟合预算 | `attachments/l2d_superfit.py` 的 `PLAN` | 按新角色的边际收益重定 |
| 骨骼锚点 | **自动**（从数据推） | 脚底/髋线/脖子/头顶/躯干宽度 |
| 跳跃锚点 | `attachments/l2d_build_anim.py` 的 `JUMP_RIG` | **手工调的观感参数**，换角色要重调 |
| 动作幅度 | `CFG.jump` / `BONE` / `GAZE` | 视角色尺寸等比缩放 |
| prefab ID | `build_lua_anim.py` 的 CFG | 换场景要按编辑器实际值改 |
| 容器名 | `CFG.containerName` | 场景里的 UI 容器名 |

**不需要改的**：图元解析、坐标换算、控件创建、层序重排、眨眼几何推导、
虹膜安全范围、负载策略、边缘处理——这些全部从数据推。

---

## 常用命令速查

```bash
PY="py -3"

# 训练/检查
$PY attachments/l2d_edge_clean.py --out 报告.json          # 边缘处理报告
$PY attachments/l2d_edge_probe.py                          # 白描边诊断图
$PY attachments/l2d_verify_anim.py --lua <文件>         # 14 项运动+负载
$PY attachments/l2d_verify_actions.py  --lua <文件>         # 逐动作位移
$PY attachments/l2d_verify_theater_keys.py --lua <文件>     # UI + 快捷键

# 生成
$PY attachments/l2d_build_anim.py --preset superfit    # Lua + 剧场
$PY attachments/l2d_build_showcase.py --source <图元目录> --out <html>

# 预览
$PY -m http.server 8743
```
