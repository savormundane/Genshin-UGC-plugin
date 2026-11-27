# 客户端 Lua 接口索引

这是插件用于接口查询、静态检查与离线模拟的符号表。类型推导和适用范围随工具结果返回。接口的公开出处为奇匠学院的[客户端控件 API](https://act.mihoyo.com/ys/ugc/tutorial/detail/mhtakr07vej4)。

在 MCP 中用 api_lookup 查询完整签名、读写权限和依据。未补充说明的符号可直接用名称查询。使用平台资源编号或绑定事件前，在目标版本核对实际可用性。

## 1.ClientUIAnimationControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `animationId` | integer | 读写 | — |
| `layer` | UIAnimationLayer | 读写 | — |
| `playSoundEffect` | boolean | 读写 | — |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `ClientUIAnimationControl:PlayAnimation()` | — | — |
| `ClientUIAnimationControl:StopAnimation()` | — | — |

## 2.ClientUIBaseControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `active` | boolean | 只读 | 控件激活状态。 |
| `activeInHierarchy` | boolean | 只读 | — |
| `alive` | boolean | 只读 | 控件句柄是否仍然有效。 |
| `anchorMaxX` | number | 读写、Tweenable | — |
| `anchorMaxY` | number | 读写、Tweenable | — |
| `anchorMinX` | number | 读写、Tweenable | — |
| `anchorMinY` | number | 读写、Tweenable | — |
| `anchoredPositionX` | number | 读写、Tweenable | 锚定位置的横坐标。 |
| `anchoredPositionY` | number | 读写、Tweenable | 锚定位置的纵坐标。 |
| `canControllerFocus` | boolean | 读写 | — |
| `id` | integer | 只读 | — |
| `localRotationX` | number | 读写、Tweenable | — |
| `localRotationY` | number | 读写、Tweenable | — |
| `localRotationZ` | number | 读写、Tweenable | — |
| `localScaleX` | number | 读写、Tweenable | — |
| `localScaleY` | number | 读写、Tweenable | — |
| `localScaleZ` | number | 读写、Tweenable | — |
| `name` | string | 读写 | — |
| `parent` | ClientUIBaseControl | 读写 | — |
| `pivotX` | number | 读写、Tweenable | — |
| `pivotY` | number | 读写、Tweenable | — |
| `prefabIndex` | integer | 只读 | — |
| `sizeDeltaX` | number | 读写、Tweenable | — |
| `sizeDeltaY` | number | 读写、Tweenable | — |
| `visible` | boolean | 只读 | 控件可见状态。 |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `ClientUIBaseControl:AddKeyEventListener(eventType, callback)` | — | 注册按键事件监听。 |
| `ClientUIBaseControl:AddNavigationEventListener(eventType, callback)` | — | — |
| `ClientUIBaseControl:FindChild(path)` | ClientUIBaseControl | 按路径查找子控件。 |
| `ClientUIBaseControl:GetAnchorMax()` | x, y | — |
| `ClientUIBaseControl:GetAnchorMin()` | x, y | — |
| `ClientUIBaseControl:GetAnchoredPosition()` | x, y | 读取控件在锚点坐标系内的位置。 |
| `ClientUIBaseControl:GetChild(name)` | ClientUIBaseControl | 按名称查询直接子控件。 |
| `ClientUIBaseControl:GetChildren()` | ClientUIBaseControl[] | — |
| `ClientUIBaseControl:GetControllerNavigation(navigationDir)` | navigationMode, navigationTarget | — |
| `ClientUIBaseControl:GetLocalRotation()` | x, y, z | — |
| `ClientUIBaseControl:GetLocalScale()` | x, y, z | — |
| `ClientUIBaseControl:GetPivot()` | x, y | — |
| `ClientUIBaseControl:GetScript(scriptMappingId)` | Script | 按脚本映射编号取得脚本句柄。 |
| `ClientUIBaseControl:GetScriptByPath(scriptPath)` | Script | 按路径查找已挂载脚本。 |
| `ClientUIBaseControl:GetScripts()` | Script[] | — |
| `ClientUIBaseControl:GetSiblingIndex()` | integer | — |
| `ClientUIBaseControl:GetSizeDelta()` | x, y | — |
| `ClientUIBaseControl:RemoveAllKeyEventListeners()` | — | — |
| `ClientUIBaseControl:RemoveAllNavigationEventListeners()` | — | — |
| `ClientUIBaseControl:RemoveKeyEventListener(eventType, callback)` | — | — |
| `ClientUIBaseControl:RemoveKeyEventListeners(eventType)` | — | — |
| `ClientUIBaseControl:RemoveNavigationEventListener(eventType, callback)` | — | — |
| `ClientUIBaseControl:RemoveNavigationEventListeners(eventType)` | — | — |
| `ClientUIBaseControl:SetActive(active)` | — | 切换激活状态，停用会影响控件及挂载脚本。 |
| `ClientUIBaseControl:SetAnchorMax(x, y)` | — | — |
| `ClientUIBaseControl:SetAnchorMin(x, y)` | — | — |
| `ClientUIBaseControl:SetAnchoredPosition(x, y)` | — | 调整控件相对锚点的位置。 |
| `ClientUIBaseControl:SetAsFirstSibling()` | boolean | — |
| `ClientUIBaseControl:SetAsLastSibling()` | boolean | — |
| `ClientUIBaseControl:SetControllerNavigation(navigationDir, navigationMode, navigationTarget)` | — | — |
| `ClientUIBaseControl:SetLocalRotation(x, y, z)` | — | — |
| `ClientUIBaseControl:SetLocalScale(x, y, z)` | — | — |
| `ClientUIBaseControl:SetPivot(x, y)` | — | — |
| `ClientUIBaseControl:SetSiblingIndex(index)` | boolean | — |
| `ClientUIBaseControl:SetSizeDelta(x, y)` | — | 调整控件相对锚点区域的宽高差。 |
| `ClientUIBaseControl:SetVisible(visible)` | — | 控制控件显示或隐藏。 |

## 3.ClientUIContainerControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `disableCursorEventPassthrough` | boolean | 读写 | — |
| `disableKeyEventPassthrough` | boolean | 读写 | — |
| `isolateNavigation` | boolean | 读写 | — |
| `showCursor` | boolean | 读写 | — |

## 4.ClientUICursorEventAreaControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `raycastTarget` | boolean | 读写 | — |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `ClientUICursorEventAreaControl:AddCursorEventListener(eventType, callback)` | — | 为可交互区域绑定光标事件。 |
| `ClientUICursorEventAreaControl:RemoveAllCursorEventListeners()` | — | — |
| `ClientUICursorEventAreaControl:RemoveCursorEventListener(eventType, callback)` | — | — |
| `ClientUICursorEventAreaControl:RemoveCursorEventListeners(eventType)` | — | — |
| `ClientUICursorEventAreaControl:SimulateCursorClick()` | — | — |

## 5.ClientUIFullscreenAnimationControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `animationId` | integer | 读写 | — |
| `playSoundEffect` | boolean | 读写 | — |

## 6.ClientUIGridScrollerControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `interactable` | boolean | 读写 | — |
| `itemCount` | integer | 只读 | — |
| `itemPrefabIndex` | integer | 读写 | — |
| `layoutConstraint` | ScrollLayoutConstraint | 只读 | — |
| `layoutConstraintFixedCount` | number | 只读 | — |
| `raycastTarget` | boolean | 读写 | — |
| `scrollDirection` | ScrollDirection | 只读 | — |
| `scrollProgress` | number | 读写、Tweenable | — |
| `showScrollBar` | boolean | 读写 | — |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `ClientUIGridScrollerControl:GetContentLength()` | number | — |
| `ClientUIGridScrollerControl:GetItemIndex(control)` | integer | — |
| `ClientUIGridScrollerControl:GetItemSize()` | x, y: number | — |
| `ClientUIGridScrollerControl:GetItemSpacing()` | x, y: number | — |
| `ClientUIGridScrollerControl:GetPadding()` | top, bottom, left, right: number | — |
| `ClientUIGridScrollerControl:RefreshItems(itemCount, refreshCallback)` | — | 用回调更新滚动网格当前需要展示的条目。 |
| `ClientUIGridScrollerControl:ScrollToItemAt(index, scrollAlignType)` | — | — |

## 7.ClientUIImageControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `enableMask` | boolean | 读写 | — |
| `enableSoftEdge` | boolean | 读写 | — |
| `fillAmount` | number | 读写、Tweenable | — |
| `fillHorizontalType` | ImageFillHorizontalType | 读写 | — |
| `fillRadial90Type` | ImageFillRadial90Type | 读写 | — |
| `fillRadialType` | ImageFillRadialType | 读写 | — |
| `fillType` | ImageFillType | 读写 | — |
| `fillVerticalType` | ImageFillVerticalType | 读写 | — |
| `horizontalSoftRange` | number | 读写、Tweenable | — |
| `imageColor` | ColorValue | 读写、Tweenable | — |
| `imageId` | integer | 只读 | — |
| `imageSource` | ImageSource | 只读 | — |
| `imageType` | ImageType | 读写 | — |
| `reverseMaskArea` | boolean | 读写 | — |
| `softEdgeMode` | ImageMaskSoftEdgeMode | 读写 | — |
| `softEdgeWidthX` | number | 读写、Tweenable | — |
| `softEdgeWidthY` | number | 读写、Tweenable | — |
| `verticalSoftRange` | number | 读写、Tweenable | — |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `ClientUIImageControl:SetFillHorizontal(fillHorizontalType, fillAmount)` | — | — |
| `ClientUIImageControl:SetFillRadial180(fillRadialType, fillAmount)` | — | — |
| `ClientUIImageControl:SetFillRadial360(fillRadialType, fillAmount)` | — | — |
| `ClientUIImageControl:SetFillRadial90(fillRadial90Type, fillAmount)` | — | — |
| `ClientUIImageControl:SetFillUnused()` | — | — |
| `ClientUIImageControl:SetFillVertical(fillVerticalType, fillAmount)` | — | — |
| `ClientUIImageControl:SetImage(imageSource, imageId)` | — | 按图像来源枚举及平台资源编号选取图片。 |
| `ClientUIImageControl:SetSoftEdgeWidth(widthX, widthY)` | — | — |

## 8.ClientUIKeyHintControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `controllerKeyCode` | ControllerKeyCode | 读写 | — |
| `keyboardKeyCode` | KeyboardKeyCode | 读写 | — |

## 9.ClientUIPresetButtonControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `clickAudioId` | integer | 读写 | — |
| `interactable` | boolean | 读写 | — |
| `raycastTarget` | boolean | 读写 | — |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `ClientUIPresetButtonControl:AddCursorEventListener(eventType, callback)` | — | 为预设按钮绑定光标事件，例如点击。 |
| `ClientUIPresetButtonControl:RemoveAllCursorEventListeners()` | — | — |
| `ClientUIPresetButtonControl:RemoveCursorEventListener(eventType, callback)` | — | — |
| `ClientUIPresetButtonControl:RemoveCursorEventListeners(eventType)` | — | — |
| `ClientUIPresetButtonControl:SimulateCursorClick()` | — | — |

## 10.ClientUIReferenceControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `referencedPrefabIndex` | integer | 只读 | — |

## 11.ClientUITextBoxControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `adaptiveFontSize` | boolean | 读写 | — |
| `bgColor` | ColorValue | 读写、Tweenable | — |
| `enableOutline` | boolean | 读写 | — |
| `fontColor` | ColorValue | 读写、Tweenable | — |
| `fontSize` | integer | 读写、Tweenable | — |
| `horizontalAlignment` | TextHorizontalAlignment | 读写 | — |
| `minimumFontSize` | integer | 读写、Tweenable | — |
| `outlineColor` | ColorValue | 读写、Tweenable | — |
| `text` | string | 读写 | 控件显示的文本。 |
| `verticalAlignment` | TextVerticalAlignment | 读写 | — |

## 12.ClientUITextWindowControl

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `adaptiveFontSize` | boolean | 读写 | — |
| `bgColor` | ColorValue | 读写、Tweenable | — |
| `enableOutline` | boolean | 读写 | — |
| `fontColor` | ColorValue | 读写、Tweenable | — |
| `fontSize` | integer | 读写、Tweenable | — |
| `horizontalAlignment` | TextHorizontalAlignment | 读写 | — |
| `interactable` | boolean | 读写 | — |
| `minimumFontSize` | integer | 读写、Tweenable | — |
| `outlineColor` | ColorValue | 读写、Tweenable | — |
| `showScrollBar` | boolean | 读写 | — |
| `text` | string | 读写 | 文本视窗的内容。 |
| `verticalAlignment` | TextVerticalAlignment | 读写 | — |

## 13.Color

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `Color.FromRGB(r: number, g: number, b: number)` | ColorValue | — |
| `Color.FromRGBA(r: number, g: number, b: number, a: number?)` | ColorValue | — |
| `Color.ToRGBA(colorValue: ColorValue)` | r, g, b, a: number | — |

## 14.CursorEventData

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `dragging` | boolean | 只读 | — |
| `touchId` | integer | 只读 | — |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `CursorEventData:GetPressUIPos()` | x, y: number | — |
| `CursorEventData:GetUIPos()` | x, y: number | — |
| `CursorEventData:GetUIPosDelta()` | x, y: number | — |

## 15.EnumItem

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `EnumType` | string | 只读 | — |
| `FullName` | string | 只读 | — |
| `Name` | string | 只读 | — |

## 16.Script

| 字段 | 类型 | 权限 | 用途 |
| --- | --- | --- | --- |
| `alive` | boolean | 只读 | — |
| `enabled` | boolean | 读写 | — |
| `object` | any | 只读 | — |
| `path` | string | 只读 | — |
| `scriptMappingId` | integer | 只读 | — |

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `Script:EnableUpdate(enabled: boolean)` | — | 打开或关闭脚本的逐帧更新。 |
| `Script:GetParam(paramName: string)` | any | — |
| `Script:Invoke(funcName: string, ...: any)` | — | — |
| `Script:RegisterCustomVariableChangedHandler(entityType: CustomVariableEntityType, customVariableName: string, callback: fun(entityType: CustomVariableEntityType, customVariableName: string))` | — | — |
| `Script:RegisterServerSignalHandler(signalName: string, callback: fun(signalName: string, signalParams: any[]))` | — | 注册用于接收服务端信号的回调。 |
| `Script:UnregisterCustomVariableChangedHandler(entityType: CustomVariableEntityType, customVariableName: string)` | — | — |
| `Script:UnregisterServerSignalHandler(signalName: string)` | — | — |

## 17.ServerSignal

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `ServerSignal:AddBool(boolValue: boolean)` | — | — |
| `ServerSignal:AddBoolList(boolListValue: boolean[])` | — | — |
| `ServerSignal:AddConfigId(configIdValue: integer)` | — | — |
| `ServerSignal:AddConfigIdList(configIdListValue: integer[])` | — | — |
| `ServerSignal:AddEntity(entityValue: integer)` | — | — |
| `ServerSignal:AddEntityList(entityListValue: integer[])` | — | — |
| `ServerSignal:AddFloat(floatValue: number)` | — | — |
| `ServerSignal:AddFloatList(floatListValue: number[])` | — | — |
| `ServerSignal:AddGuid(guidValue: integer)` | — | — |
| `ServerSignal:AddGuidList(guidListValue: integer[])` | — | — |
| `ServerSignal:AddInt(intValue: integer)` | — | — |
| `ServerSignal:AddIntList(intListValue: integer[])` | — | — |
| `ServerSignal:AddParam(paramType: ParamType, paramValue: any)` | — | — |
| `ServerSignal:AddPrefabId(prefabIdValue: integer)` | — | — |
| `ServerSignal:AddPrefabIdList(prefabIdListValue: integer[])` | — | — |
| `ServerSignal:AddString(stringValue: string)` | — | — |
| `ServerSignal:AddStringList(stringListValue: string[])` | — | — |
| `ServerSignal:AddVector3(vector3Value: table)` | — | — |
| `ServerSignal:AddVector3List(vector3ListValue: table[])` | — | — |
| `ServerSignal:SendSignal()` | — | — |

## 18.Tween

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `Tween:Complete()` | — | — |
| `Tween:Kill(complete: boolean)` | — | — |
| `Tween:Pause()` | — | — |
| `Tween:Play()` | Tween | — |
| `Tween:Restart()` | — | — |
| `Tween:Resume()` | — | — |
| `Tween:SetEase(easeType: EaseType)` | Tween | — |
| `Tween:SetLoops(times: integer)` | Tween | — |
| `Tween:SetOnComplete(onComplete: fun())` | Tween | — |
| `Tween:SetOnStepComplete(onStepComplete: fun())` | Tween | — |
| `Tween:SetRelative(relative: boolean)` | Tween | — |

## 19.TweenSequence

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `TweenSequence:Append(tween: Tween)` | TweenSequence | — |
| `TweenSequence:AppendCallback(callback: fun())` | TweenSequence | — |
| `TweenSequence:AppendInterval(interval: number)` | TweenSequence | — |
| `TweenSequence:Complete()` | — | — |
| `TweenSequence:Insert(time: number, tween: Tween)` | TweenSequence | — |
| `TweenSequence:InsertCallback(time: number, callback: fun())` | TweenSequence | — |
| `TweenSequence:Join(tween: Tween)` | TweenSequence | — |
| `TweenSequence:Kill(complete: boolean)` | — | — |
| `TweenSequence:Pause()` | — | — |
| `TweenSequence:Play()` | TweenSequence | — |
| `TweenSequence:Restart()` | — | — |
| `TweenSequence:Resume()` | — | — |
| `TweenSequence:SetLoops(times: integer)` | TweenSequence | — |
| `TweenSequence:SetOnComplete(onComplete: fun())` | TweenSequence | — |
| `TweenSequence:SetOnStepComplete(onStepComplete: fun())` | TweenSequence | — |

## 20.debug

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `debug.traceback([message[, level]])` | string | 获取当前 Lua 调用栈文本。 |

## 21.game

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `game.DestroyClientUIControl(control: ClientUIBaseControl)` | — | — |
| `game.FindClientUIRoot(nodeName: string)` | ClientUIBaseControl | — |
| `game.GetClientUIControl(controlId: integer)` | ClientUIBaseControl | — |
| `game.GetClientUIRoots()` | ClientUIBaseControl[] | — |
| `game.GetControllerFocus()` | ClientUIBaseControl | — |
| `game.GetControllerLeftStickAxis()` | horizontal, vertical: number | — |
| `game.GetControllerRightStickAxis()` | horizontal, vertical: number | — |
| `game.GetCursorUIPos()` | x, y: number | — |
| `game.GetDevice()` | Device | 读取当前输入设备类型。 |
| `game.GetGlobalCustomVariableValue(entityType: CustomVariableEntityType, customVariableName: string)` | any | — |
| `game.GetLanguageType()` | LanguageType | — |
| `game.GetStageMode()` | StageMode | 读取本局关卡模式。 |
| `game.GetText(textMapId: string)` | string | — |
| `game.GetUICanvasSize()` | x, y: number | 读取 UI 画布尺寸。 |
| `game.InstantiateClientUIControl(controlPrefabIndex: integer, parent: ClientUIBaseControl)` | ClientUIBaseControl | — |
| `game.IsAudioAlive(audioInstanceId: integer)` | boolean | — |
| `game.IsLevelTimePaused()` | boolean | — |
| `game.IsTestPlay()` | boolean | — |
| `game.PauseLevelTime(pause: boolean)` | — | — |
| `game.PlayAudio2D(audioId: integer)` | integer | — |
| `game.PrintClientUITree()` | — | 输出客户端控件层级。 |
| `game.ServerSignal(signalName: string)` | ServerSignal | — |
| `game.SetControllerFocus(control: ClientUIBaseControl)` | — | — |
| `game.StopAudio(audioInstanceId: integer)` | — | — |
| `game.Tween(object: any, tweenDataTable: table, duration: number)` | Tween | — |
| `game.TweenSequence()` | TweenSequence | — |

## 22.math

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `math.isinf(n)` | boolean | — |
| `math.isnan(n)` | boolean | — |

## 23.全局API

| 调用 | 返回 | 用途 |
| --- | --- | --- |
| `Color(r: number, g: number, b: number, a: number?)` | ColorValue | 按参数构造颜色。 |
| `print(...)` | — | 写入普通调试日志。 |
| `printerr(...)` | — | 写入错误级别日志，脚本继续执行。 |
| `typeof(value)` | string | 查询运行环境识别的值类型。 |

## 24.枚举

| 枚举 | 成员 | 用途 |
| --- | --- | --- |
| `Enum.ControllerKeyCode` | `CraftspersonKey1` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey2` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey3` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey4` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey5` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey6` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey7` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey8` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey9` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey10` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey11` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey12` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey13` | — |
| `Enum.ControllerKeyCode` | `CraftspersonKey14` | — |
| `Enum.ControllerKeyCode` | `SprintKey` | — |
| `Enum.ControllerKeyCode` | `JumpKey` | — |
| `Enum.ControllerKeyCode` | `InteractKey` | — |
| `Enum.ControllerKeyCode` | `NormalAttackKey` | — |
| `Enum.ControllerKeyCode` | `CharacterSkill1Key` | — |
| `Enum.ControllerKeyCode` | `CharacterSkill2Key` | — |
| `Enum.ControllerKeyCode` | `CharacterSkill3Key` | — |
| `Enum.ControllerKeyCode` | `CharacterSkill4Key` | — |
| `Enum.ControllerKeyCode` | `MenuConfirmKey` | — |
| `Enum.ControllerKeyCode` | `MenuBackKey` | — |
| `Enum.ControllerKeyCode` | `None` | — |
| `Enum.ControllerNavigationDir` | `Up` | — |
| `Enum.ControllerNavigationDir` | `Down` | — |
| `Enum.ControllerNavigationDir` | `Left` | — |
| `Enum.ControllerNavigationDir` | `Right` | — |
| `Enum.ControllerNavigationEventType` | `Confirm` | — |
| `Enum.ControllerNavigationEventType` | `Cancel` | — |
| `Enum.ControllerNavigationEventType` | `Focus` | — |
| `Enum.ControllerNavigationEventType` | `LostFocus` | — |
| `Enum.ControllerNavigationEventType` | `RightStickUp` | — |
| `Enum.ControllerNavigationEventType` | `RightStickDown` | — |
| `Enum.ControllerNavigationEventType` | `RightStickRight` | — |
| `Enum.ControllerNavigationEventType` | `RightStickLeft` | — |
| `Enum.ControllerNavigationEventType` | `LeftStickUp` | — |
| `Enum.ControllerNavigationEventType` | `LeftStickDown` | — |
| `Enum.ControllerNavigationEventType` | `LeftStickRight` | — |
| `Enum.ControllerNavigationEventType` | `LeftStickLeft` | — |
| `Enum.ControllerNavigationMode` | `None` | — |
| `Enum.ControllerNavigationMode` | `NearestControl` | — |
| `Enum.ControllerNavigationMode` | `Specified` | — |
| `Enum.CursorEventType` | `CursorDown` | — |
| `Enum.CursorEventType` | `CursorUp` | — |
| `Enum.CursorEventType` | `CursorEnter` | — |
| `Enum.CursorEventType` | `CursorExit` | — |
| `Enum.CursorEventType` | `CursorDrag` | — |
| `Enum.CursorEventType` | `CursorBeginDrag` | — |
| `Enum.CursorEventType` | `CursorEndDrag` | — |
| `Enum.CursorEventType` | `CursorClick` | 完成点击时发出光标事件。 |
| `Enum.CustomVariableEntityType` | `Level` | — |
| `Enum.CustomVariableEntityType` | `PlayerSelf` | — |
| `Enum.CustomVariableEntityType` | `AvatarSelf` | — |
| `Enum.Device` | `KeyboardAndMouse` | — |
| `Enum.Device` | `Mobile` | — |
| `Enum.Device` | `Controller` | — |
| `Enum.Device` | `MobileController` | — |
| `Enum.EaseType` | `Linear` | — |
| `Enum.EaseType` | `InSine` | — |
| `Enum.EaseType` | `OutSine` | — |
| `Enum.EaseType` | `InOutSine` | — |
| `Enum.EaseType` | `InQuad` | — |
| `Enum.EaseType` | `OutQuad` | — |
| `Enum.EaseType` | `InOutQuad` | — |
| `Enum.EaseType` | `InCubic` | — |
| `Enum.EaseType` | `OutCubic` | — |
| `Enum.EaseType` | `InOutCubic` | — |
| `Enum.EaseType` | `InQuart` | — |
| `Enum.EaseType` | `OutQuart` | — |
| `Enum.EaseType` | `InOutQuart` | — |
| `Enum.EaseType` | `InQuint` | — |
| `Enum.EaseType` | `OutQuint` | — |
| `Enum.EaseType` | `InOutQuint` | — |
| `Enum.EaseType` | `InExpo` | — |
| `Enum.EaseType` | `OutExpo` | — |
| `Enum.EaseType` | `InOutExpo` | — |
| `Enum.EaseType` | `InCirc` | — |
| `Enum.EaseType` | `OutCirc` | — |
| `Enum.EaseType` | `InOutCirc` | — |
| `Enum.EaseType` | `InBack` | — |
| `Enum.EaseType` | `OutBack` | — |
| `Enum.EaseType` | `InOutBack` | — |
| `Enum.EaseType` | `InElastic` | — |
| `Enum.EaseType` | `OutElastic` | — |
| `Enum.EaseType` | `InOutElastic` | — |
| `Enum.EaseType` | `InBounce` | — |
| `Enum.EaseType` | `OutBounce` | — |
| `Enum.EaseType` | `InOutBounce` | — |
| `Enum.ImageFillHorizontalType` | `Left` | — |
| `Enum.ImageFillHorizontalType` | `Right` | — |
| `Enum.ImageFillRadial90Type` | `BottomLeft` | — |
| `Enum.ImageFillRadial90Type` | `TopLeft` | — |
| `Enum.ImageFillRadial90Type` | `TopRight` | — |
| `Enum.ImageFillRadial90Type` | `BottomRight` | — |
| `Enum.ImageFillRadialType` | `Bottom` | — |
| `Enum.ImageFillRadialType` | `Left` | — |
| `Enum.ImageFillRadialType` | `Top` | — |
| `Enum.ImageFillRadialType` | `Right` | — |
| `Enum.ImageFillType` | `Unused` | — |
| `Enum.ImageFillType` | `Horizontal` | — |
| `Enum.ImageFillType` | `Vertical` | — |
| `Enum.ImageFillType` | `Radial90` | — |
| `Enum.ImageFillType` | `Radial180` | — |
| `Enum.ImageFillType` | `Radial360` | — |
| `Enum.ImageFillVerticalType` | `Bottom` | — |
| `Enum.ImageFillVerticalType` | `Top` | — |
| `Enum.ImageMaskSoftEdgeMode` | `Percentage` | — |
| `Enum.ImageMaskSoftEdgeMode` | `Pixel` | — |
| `Enum.ImageSource` | `StaticReference` | 按静态资源编号引用图片。 |
| `Enum.ImageSource` | `Item` | — |
| `Enum.ImageSource` | `Equipment` | — |
| `Enum.ImageSource` | `Skill` | — |
| `Enum.ImageSource` | `UnitStatus` | — |
| `Enum.ImageSource` | `Faction` | — |
| `Enum.ImageSource` | `Currency` | — |
| `Enum.ImageSource` | `Prefab` | — |
| `Enum.ImageType` | `Basic` | — |
| `Enum.ImageType` | `Stretch` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey1Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey2Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey3Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey4Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey5Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey6Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey7Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey8Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey9Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey10Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey11Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey12Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey13Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey14Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey15Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey16Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey17Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey18Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey19Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey20Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey21Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey22Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey23Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey24Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey25Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey26Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey27Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey28Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey29Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey30Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey31Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey32Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey33Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey34Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey35Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey36Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey37Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey38Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey39Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey40Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey41Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey42Down` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey43Down` | — |
| `Enum.KeyEventType` | `KeyboardMoveForwardKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardMoveBackwardKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardMoveLeftKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardMoveRightKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardSwitchToWalkOrRunKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardSprintKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardJumpKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardDropKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardOpenShortcutWheelKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardInteractKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardNormalAttackKeyDown` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill1KeyDown` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill2KeyDown` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill3KeyDown` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill4KeyDown` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey1Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey2Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey3Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey4Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey5Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey6Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey7Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey8Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey9Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey10Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey11Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey12Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey13Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey14Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey15Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey16Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey17Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey18Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey19Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey20Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey21Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey22Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey23Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey24Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey25Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey26Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey27Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey28Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey29Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey30Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey31Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey32Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey33Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey34Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey35Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey36Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey37Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey38Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey39Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey40Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey41Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey42Up` | — |
| `Enum.KeyEventType` | `KeyboardCraftspersonKey43Up` | — |
| `Enum.KeyEventType` | `KeyboardMoveForwardKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardMoveBackwardKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardMoveLeftKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardMoveRightKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardSwitchToWalkOrRunKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardSprintKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardJumpKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardDropKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardOpenShortcutWheelKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardInteractKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardNormalAttackKeyUp` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill1KeyUp` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill2KeyUp` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill3KeyUp` | — |
| `Enum.KeyEventType` | `KeyboardCharacterSkill4KeyUp` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey1Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey2Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey3Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey4Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey5Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey6Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey7Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey8Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey9Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey10Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey11Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey12Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey13Down` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey14Down` | — |
| `Enum.KeyEventType` | `ControllerSprintKeyDown` | — |
| `Enum.KeyEventType` | `ControllerJumpKeyDown` | — |
| `Enum.KeyEventType` | `ControllerInteractKeyDown` | — |
| `Enum.KeyEventType` | `ControllerNormalAttackKeyDown` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill1KeyDown` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill2KeyDown` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill3KeyDown` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill4KeyDown` | — |
| `Enum.KeyEventType` | `ControllerMenuConfirmKeyDown` | — |
| `Enum.KeyEventType` | `ControllerMenuBackKeyDown` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey1Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey2Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey3Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey4Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey5Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey6Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey7Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey8Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey9Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey10Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey11Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey12Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey13Up` | — |
| `Enum.KeyEventType` | `ControllerCraftspersonKey14Up` | — |
| `Enum.KeyEventType` | `ControllerSprintKeyUp` | — |
| `Enum.KeyEventType` | `ControllerJumpKeyUp` | — |
| `Enum.KeyEventType` | `ControllerInteractKeyUp` | — |
| `Enum.KeyEventType` | `ControllerNormalAttackKeyUp` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill1KeyUp` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill2KeyUp` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill3KeyUp` | — |
| `Enum.KeyEventType` | `ControllerCharacterSkill4KeyUp` | — |
| `Enum.KeyEventType` | `ControllerMenuConfirmKeyUp` | — |
| `Enum.KeyEventType` | `ControllerMenuBackKeyUp` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey1` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey2` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey3` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey4` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey5` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey6` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey7` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey8` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey9` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey10` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey11` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey12` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey13` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey14` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey15` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey16` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey17` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey18` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey19` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey20` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey21` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey22` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey23` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey24` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey25` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey26` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey27` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey28` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey29` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey30` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey31` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey32` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey33` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey34` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey35` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey36` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey37` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey38` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey39` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey40` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey41` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey42` | — |
| `Enum.KeyboardKeyCode` | `CraftspersonKey43` | — |
| `Enum.KeyboardKeyCode` | `MoveForwardKey` | — |
| `Enum.KeyboardKeyCode` | `MoveBackwardKey` | — |
| `Enum.KeyboardKeyCode` | `MoveLeftKey` | — |
| `Enum.KeyboardKeyCode` | `MoveRightKey` | — |
| `Enum.KeyboardKeyCode` | `SwitchToWalkOrRunKey` | — |
| `Enum.KeyboardKeyCode` | `SprintKey` | — |
| `Enum.KeyboardKeyCode` | `JumpKey` | — |
| `Enum.KeyboardKeyCode` | `DropKey` | — |
| `Enum.KeyboardKeyCode` | `OpenShortcutWheelKey` | — |
| `Enum.KeyboardKeyCode` | `InteractKey` | — |
| `Enum.KeyboardKeyCode` | `NormalAttackKey` | — |
| `Enum.KeyboardKeyCode` | `CharacterSkill1Key` | — |
| `Enum.KeyboardKeyCode` | `CharacterSkill2Key` | — |
| `Enum.KeyboardKeyCode` | `CharacterSkill3Key` | — |
| `Enum.KeyboardKeyCode` | `CharacterSkill4Key` | — |
| `Enum.KeyboardKeyCode` | `None` | — |
| `Enum.LanguageType` | `LanguageNone` | — |
| `Enum.LanguageType` | `LanguageEng` | — |
| `Enum.LanguageType` | `LanguageChs` | — |
| `Enum.LanguageType` | `LanguageCht` | — |
| `Enum.LanguageType` | `LanguageFra` | — |
| `Enum.LanguageType` | `LanguageDeu` | — |
| `Enum.LanguageType` | `LanguageSpa` | — |
| `Enum.LanguageType` | `LanguagePor` | — |
| `Enum.LanguageType` | `LanguageRus` | — |
| `Enum.LanguageType` | `LanguageJpn` | — |
| `Enum.LanguageType` | `LanguageKor` | — |
| `Enum.LanguageType` | `LanguageTha` | — |
| `Enum.LanguageType` | `LanguageVie` | — |
| `Enum.LanguageType` | `LanguageInd` | — |
| `Enum.LanguageType` | `LanguageTur` | — |
| `Enum.LanguageType` | `LanguageIta` | — |
| `Enum.ParamType` | `Entity` | — |
| `Enum.ParamType` | `EntityList` | — |
| `Enum.ParamType` | `Int` | — |
| `Enum.ParamType` | `IntList` | — |
| `Enum.ParamType` | `Bool` | — |
| `Enum.ParamType` | `BoolList` | — |
| `Enum.ParamType` | `Float` | — |
| `Enum.ParamType` | `FloatList` | — |
| `Enum.ParamType` | `String` | — |
| `Enum.ParamType` | `StringList` | — |
| `Enum.ParamType` | `Vector3` | — |
| `Enum.ParamType` | `Vector3List` | — |
| `Enum.ParamType` | `Guid` | — |
| `Enum.ParamType` | `GuidList` | — |
| `Enum.ParamType` | `ConfigId` | — |
| `Enum.ParamType` | `PrefabId` | — |
| `Enum.ParamType` | `ConfigIdList` | — |
| `Enum.ParamType` | `PrefabIdList` | — |
| `Enum.ScrollAlignType` | `Bottom` | — |
| `Enum.ScrollAlignType` | `Center` | — |
| `Enum.ScrollAlignType` | `Top` | — |
| `Enum.ScrollDirection` | `Horizontal` | — |
| `Enum.ScrollDirection` | `Vertical` | — |
| `Enum.ScrollLayoutConstraint` | `AutoWrap` | — |
| `Enum.ScrollLayoutConstraint` | `Fixed` | — |
| `Enum.StageMode` | `Beyond` | — |
| `Enum.StageMode` | `Classic` | — |
| `Enum.TextHorizontalAlignment` | `Left` | — |
| `Enum.TextHorizontalAlignment` | `Middle` | — |
| `Enum.TextHorizontalAlignment` | `Right` | — |
| `Enum.TextVerticalAlignment` | `Top` | — |
| `Enum.TextVerticalAlignment` | `Middle` | — |
| `Enum.TextVerticalAlignment` | `Bottom` | — |
| `Enum.UIAnimationLayer` | `AboveAllControls` | — |
| `Enum.UIAnimationLayer` | `BelowAllControls` | — |

## 25.脚本生命周期

| 回调 | 参数 | 用途 |
| --- | --- | --- |
| `OnDestroy()` | — | 脚本销毁回调。 |
| `OnDisable()` | — | 脚本停用回调。 |
| `OnEnable()` | — | 脚本启用回调。 |
| `OnInit()` | — | 脚本初始化回调。 |
| `OnLevelUpdate(dt)` | — | 随关卡时间逐帧更新，受关卡时停影响。 |
| `OnStart()` | — | 脚本启动回调。 |
| `OnUpdate(dt)` | — | 脚本逐帧更新的回调，关卡时停期间也可调用。 |
