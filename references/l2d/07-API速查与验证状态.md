# 07 · API 速查与验证状态

**写脚本前先看这一页。**

> **这一节和其他章节性质不同**：这里是**环境事实**，不是我们的选择。
> API 就是这个样子，绕不开 —— 所以这一节里的"必须/不能"是真的必须。
> 但请注意**分成三段看**：已确认可用 / 未验证 / 明确不存在。**不要把"未验证"当事实用。**

最高可信来源：`（团队提供的 API 类型定义 stub）`（别人提供的可运行实例的 EmmyLua stub）。
其次：真机反馈。最不可信：从 PDF 整理的接口表里的**解释文字**（PDF 光栅表被截断过，
字段名/类型可信，解释列不可全信）。

---

## 7.1 已确认可用 【实测】

### 脚本生命周期

```lua
function OnInit()  end
function OnStart() end
function OnUpdate(dt) end
function OnDestroy() end

--- 控制当前脚本的 update 启用状态；false 关闭，true 重新启用
function Script:EnableUpdate(enabled) end
```

- **逐帧回调默认关闭**，必须自己 `script:EnableUpdate(true)`，否则 `OnUpdate` 一帧都不跑。
- 旧文档里的名字是 `EnableTick`（**已改名**）。保留回退有利于老运行时。

### game 命名空间

```lua
--- 获取 UI 画布尺寸（用于取容器中心；不要写死 1600×900）
game.GetUICanvasSize()                       --> w, h

--- ⚠️ 返回「画布左下角原点」坐标；控件位置用「画布中心原点」，两者差半画布
game.GetCursorUIPos()                        --> x, y

--- 实例化 UI 控件；parent 为 nil 时**静默失败**（返回 nil）
game.InstantiateClientUIControl(uiPrefabId, parent)  --> ClientUIBaseControl

--- 按名查找 UI 根
game.FindClientUIRoot(nodeName)              --> ClientUIBaseControl

game.DestroyClientUIControl(control)
game.PrintClientUITree()
```

### ClientUIBaseControl（基类）

```lua
-- 可读写、可 Tween
anchoredPositionX/Y      sizeDeltaX/Y      pivotX/Y
localScaleX/Y/Z          localRotationX/Y/Z
alive                    visible/enable/active

c:SetAnchoredPosition(x, y)
c:SetSizeDelta(w, h)
c:SetPivot(0.5, 0.5)          -- 注意字段叫 pivotX/pivotY，方法是 SetPivot
c:SetLocalRotation(0, 0, deg)
c:SetAnchorMin(0.5, 0.5)
c:SetAnchorMax(0.5, 0.5)
c:SetVisible(true)
c:SetSiblingIndex(i)          --> boolean（**会失败**，必须检查）

--- 按键事件：回调返回 boolean，true 表示**消费**该事件
c:AddKeyEventListener(eventType, callback)
c:RemoveKeyEventListener(eventType, callback)
c:RemoveKeyEventListeners(eventType)
c:RemoveAllKeyEventListeners()
```

- **基类没有 `alpha` / `opacity` / `zIndex` 字段**：透明度走图片控件的 `imageColor`，
  层序走 `SetSiblingIndex`。

### ClientUIImageControl

```lua
imageSource        -- 只读
imageId            -- 只读
imageType          -- Enum.ImageType.Basic(0) / Stretch(1)
imageColor         -- ColorValue，可读写、可 Tween
enableMask         -- 是否启用遮罩（**矩形区域**，不是图片 alpha 模板）
reverseMaskArea    -- 是否反转遮罩区域
enableSoftEdge     -- 是否启用边缘羽化
softEdgeMode       -- Enum.ImageMaskSoftEdgeMode.Percentage(0) / Pixel(1)
softEdgeWidthX/Y, horizontalSoftRange, verticalSoftRange
c:SetImage(Enum.ImageSource.StaticReference, circleAssetId)
```

⚠️ 注意：**没有 `maskArea` 这个字段**，只有 `reverseMaskArea`。
⚠️ 参考系说明见 `beyond_api.lua` 头部，字段注释里对掩膜的解释来自文档，不可全信。

### ClientUITextBoxControl

```lua
text, fontSize, fontColor, bgColor
enableOutline, outlineColor
horizontalAlignment    -- Enum.TextHorizontalAlignment.Left(0)/Middle(1)/Right(2)
verticalAlignment      -- Enum.TextVerticalAlignment.Top(0)/Middle(1)/Bottom(2)
adaptiveFontSize, minimumFontSize
```

⚠️ 未验证：`text` 里的换行符（`\n`）是否被渲染成多行。本项目按"是"来用，实机要确认一次。

### 枚举

```lua
Enum.ImageSource.StaticReference = 0
Enum.ImageType = { Basic = 0, Stretch = 1 }
Enum.TextHorizontalAlignment = { Left=0, Middle=1, Right=2 }
Enum.TextVerticalAlignment   = { Top=0,  Middle=1, Bottom=2 }
Enum.CursorEventType = {
  CursorDown=0, CursorUp=1, CursorEnter=2, CursorExit=3,
  CursorDrag=4, CursorBeginDrag=5, CursorEndDrag=6, CursorClick=7 }
```

### 按键枚举

`Enum.KeyboardKeyCode`（**键位物理序号**，1-based 语义）：
`CraftspersonKey1..10` = 数字 **1 2 3 4 5 6 7 8 9 0**；
`CraftspersonKey11..22` = **U Z Y G H I O P J K L V**；
`23..28` = F5~F10；`29` = `` ` ``；`40..43` = 右Ctrl / 右Shift / Backspace / CapsLock。
移动/交互键：`JumpKey=49`(空格) / `InteractKey=52`(F) / `NormalAttackKey=53`(鼠标左键) 等。

`Enum.KeyEventType`（**事件**，与上面不是同一张表）：
- 奇匠按键按下：`KeyboardCraftspersonKey1Down = 0` … `KeyboardCraftspersonKey43Down = 42`
- 移动/技能按下：`KeyboardJumpKeyDown = 49`、`KeyboardInteractKeyDown = 52` …
- 奇匠按键抬起：`KeyboardCraftspersonKey1Up = 58` …
- 手柄：`ControllerSprintKeyDown = 130` …

**用法**：

```lua
local et = Enum.KeyEventType["KeyboardCraftspersonKey" .. 3 .. "Down"]   -- 数字键 3
local et2 = Enum.KeyEventType["KeyboardJumpKeyDown"]                     -- 空格
ctl:AddKeyEventListener(et, function(...) PlayAction("nodOnce"); return true end)
```

**两点提醒**：
1. 返回 `true` = **消费该事件**。绑空格时如果这一关的空格本来就是"角色跳跃"，
   可能把这个键吃掉。不确定就先不绑。
2. 回调签名文档没写死。本项目做成了签名无关 + 多路兜底（见 `08` 的坑 9）。

### 层级 / 父容器（降负载的关键）

```lua
--- parent 是**读写**字段
control.parent = otherControl          -- 运行期搬家（是否生效待实机确认）

--- 创建时直接指定父级
game.InstantiateClientUIControl(uiPrefabId, parent)   --> ClientUIBaseControl

--- 子控件查询
c:GetChildren()        --> ClientUIBaseControl[]
c:GetChild(name)       --> ClientUIBaseControl
c:FindChild(path)      --> ClientUIBaseControl
```

- 控件类型里有专门的 **`ClientUIContainerControl`（容器节点，"用于组织子控件"）**，
  但它**没有** `children` / `childCount` 字段，只能走基类的 `GetChildren()`。
- 官方规范写明：**「父子层级中的位移、缩放、显隐、Alpha、镜像与裁剪效果由运行时 UI 层级共同决定；
  使用组合布局时应验证实际显示结果」** ⟶ 父控件变换会作用到子控件（"骨骼"的机制）。
  注意它列的是**位移/缩放/显隐/Alpha/镜像/裁剪**，**没提旋转** —— 而摆臂/甩发全靠旋转，必须实机确认。
- ⚠️ 未验证：单个父容器的**子控件数量上限**（规范里"受控件的子控件数"后半句被裁掉了）、
  子控件坐标是否相对父、父 alpha 是否传递、容器模板的 prefabId。
  → 见 `11-层级与骨骼-父容器.md` 与附件 `l2d_hier_probe.lua`。
- 另外：**服务器侧必须有「客户端控件容器」**，控件与脚本都依赖它（隐藏/关闭会导致其中控件不显示）。

### 颜色

```lua
Color.FromRGB(r, g, b)
Color.FromRGBA(r, g, b, a)     -- 0~255
Color.ToRGBA(colorValue)       --> r, g, b, a
```

### 补间动画（Tween）

签名与全部方法已确认，**所有我们要用的控件字段都标了 Tweenable**；
**但 `tweenDataTable` 的格式在所有材料里都缺失**（PDF 文字层只有标题、Tween 那页页图缺失），
所以只能实机探测 —— 详见 **`10-补间动画-Tween.md`** 与附件 `l2d_tween_probe.lua`。

```lua
game.Tween(object, tweenDataTable, duration)  --> Tween          -- ⚠️ 表格式未确认
game.TweenSequence()                          --> TweenSequence
t:SetEase(Enum.EaseType.InOutSine)  t:SetRelative(true)  t:SetLoops(-1)  t:Kill(false)
t:SetOnComplete(fn)
q:Append(t)  q:Join(t)  q:Insert(time, t)  q:AppendInterval(sec)  q:AppendCallback(fn)
```

Tweenable 字段（能补间的）：`anchoredPositionX/Y`、`sizeDeltaX/Y`、`localRotationX/Y/Z`、
`localScaleX/Y/Z`、`anchorMin/MaxX/Y`、`pivotX/Y`、`imageColor`、`softEdgeWidthX/Y`、`fillAmount`。

### 其它

`print(...)` / `printerr(...)` / `typeof(v)` / `math.isnan/isinf` / `debug.traceback`
—— 沙箱**禁了 `io.*`**，读不了外部文件，所以图元数据必须内联在源码里。

---

## 7.2 未验证 / 需要实机确认的

| 项 | 现状 | 怎么确认 |
|---|---|---|
| `enableSoftEdge` 默认值 | 本项目没设置，实机边缘硬度未知 | 实机看边缘；偏软就设 `false` |
| `enableMask` 的精确语义 | 文档说是"是否启用遮罩"，实际是矩形区域 | 需要一个能跑的场景试 |
| 按键会不会被游戏界面占用 | 数字键/字母键可能已被奇匠模式占用 | 绑上后实机按一下 |
| 键事件该挂在哪个控件上 | 本项目挂在容器根节点（多路兜底） | 看日志"快捷键绑在「…」：成功 N/M 个" |
| 文本框 `\n` 换行 | 按"支持"来用 | 实机看文字面板 |
| `GetUICanvasSize` 返回什么 | 按 1600×900 做回退 | 打印一次即可 |
| 光标事件回调签名 | 做成签名无关 | 日志里会打印"光标坐标来源：…" |
| 贴图资源 / RenderTexture | 没有 | 决定能否走"烘一张贴图 + 条带位移"路线 |
| prefab ID | 值是别人实机跑通的（`1073741850/51/49`），**换场景要改** | 编辑器里核对 |

---

## 7.3 明确不存在 / 已改名

| 写法 | 结论 |
|---|---|
| `EnableTick` | **已改名** `EnableUpdate` |
| `maskArea` | **不存在**，只有 `reverseMaskArea` |
| 基类的 `alpha` / `opacity` | **不存在**，用 `imageColor` |
| 基类的 `zIndex` | **不存在**，用 `SetSiblingIndex` |
| 现成的滑块控件 | **不存在**，要自己用"图片控件 + 光标检测区"拼（见下） |

---

## 7.4 拖动条怎么自己搭（没有现成 slider）

可用拼装件：**图片控件**（外观）+ **光标检测区**（命中与拖动）。

三种做法：

| 做法 | 说明 |
|---|---|
| **① 绝对映射（推荐）** | 拖动事件里取 `CursorEventData:GetUIPos()`，换算到控件空间后**直接映射**成轨道比例。滑块永远跟手，不会累积漂移，滑出轨道也不丢 |
| ② 相对增量 | 用 `GetUIPosDelta()` 累加。写法最短，但会漂（取整 + 丢帧），滑快了跟不上 |
| ③ 轮询 | 按住时每帧 `game.GetCursorUIPos()`。省掉拖动事件，但仍需要"按下/抬起"事件 |

三者都依赖同一个事实：**光标坐标是画布左下原点，控件位置是容器中心原点**，相差半个画布。

```lua
local function toAnchor(ux, uy)      -- 光标坐标 → 控件坐标
  return ux - CX, uy - CY
end
-- 拖动回调里
local ax = toAnchor(ux, 0)
local t  = (ax - (spec.x - spec.w / 2)) / spec.w      -- 轨道上的比例 0~1
apply(lo + t * (hi - lo))
```

**命中区不要铺满全屏**：会跟按钮/拖动条抢光标事件。本项目兜底的"按键接收区"故意做成
角落里的 300×60。
