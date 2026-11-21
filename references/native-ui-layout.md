# 原生UI矩形布局

为已有GIL或level阶段新生成的控件写入固定锚点RectTransform，配置按设备状态独立声明。不携带页面、主题、布局模板或玩家文案。输入只读，输出新目录；根GIL的字段9以外原始字节保持。

```text
python scripts/qianxing.py ui apply base.gil ui.json --out new-layout
```

```json
{
  "schema":2,
  "base_sha256":"填写输入GIL的SHA256",
  "canvas":{"0":[800,600],"1":[900,650],"2":[1000,700],"3":[1100,750]},
  "controls":[
    {"template":"Panel","states":{
      "0":{"rect":[10,20,100,50],"anchor":[0,1],"pivot":[0.25,0.75]},
      "1":{"rect":[20,30,120,60],"anchor":[0,1],"pivot":[0.25,0.75]}
    }}
  ]
}
```

canvas必须明确给出四个状态的尺寸，不推断状态编号对应的设备。states只修改选中状态，未选中状态原样保留。rect为所声明画布坐标中的左、上、宽、高，原点左上角。anchor和pivot分别在0至1之间，宽高必须为正。可显式设置allow_outside=true允许超出声明画布，报告仍逐项标记outside；默认越界失败。浮点数必须有限且绝对值不大于1e9，写入float32后的几何回读差异过大也拒绝。

目标可用唯一template名称，或用guid直接选定一个真实记录，不能同时提供两者。template选择同时写入模板记录与其库入口，避免只改库入口而实例化原模板。重复选择同一GUID、歧义模板名、缺失控件、缺失或重复状态、未校准RectTransform组件布局均拒绝。

第二种中性配置可使用area或text模板，anchor改为[1,0]，各状态使用不同矩形。container、area、text、image复用已校准矩形组件；本入口不创建输入监听、图片资产或文字内容，模板创建继续通过level阶段完成。

## 接入制作链

```json
{"schema":2,"level":{"spec":"level.json"},"ui":{"spec":"ui.json"}}
```

此时ui.json可将base_sha256写为`@level`，produce在基底创建或native修改后绑定当前摘要，再进行布局写入。直接ui apply不接受该占位值。也可指定明确摘要，摘要不一致即拒绝。

布局发生在图编译和Lua嵌入之前。最终GIL再按同一配置回读比较，若后续阶段覆盖布局则失败并撤销输出目录。ui-report.json记录最终文件摘要，portable制作会收集ui配置。所有必需阶段仍经过produce现有最终审计。

## 已校准范围与待验项

字段依据为包内Ayaya的ui_patchers/web_ui/web_ui_import_rect.py与layout/layout_templates_parts/shared_parts/rect_transform.py：状态值中502/503为固定锚点、504为锚定位置、505为尺寸、506为轴心。工具复用该坐标换算并独立解码实际写入浮点数，不按控件组件的数组序号猜测目标。其它组件、脚本挂载及未选中记录保持。

每个state可选scale:[sx,sy]，显式声明二维正缩放；省略时维持旧合同，只接受原单位缩放。rect仍是缩放前矩形，缩放绕pivot发生；报告visible_rect为缩放后的可见矩形，越界检查使用它。例如rect=[100,100,100,50]、pivot=[0.5,0.5]、scale=[2,0.5]得到visible_rect=[50,112.5,200,25]。scale字段使用包内ui/readable_dump.py的RectTransform 501→Vec3(1,2,3)定义，仅写X/Y，保留Z=1；实际float32回读与请求核对。零/负缩放、非有限值、深度缩放、旋转仍拒绝。

拉伸锚点、父子布局生成、原生画布缩放模式、导航和输入配置仍需后续校准及实现。声明canvas不能证明实际父容器尺寸，parent_geometry_verified保持false。本页不是整个C档UI能力完成声明。

canvas是调用者声明的几何边界，工具不写入实际画布设置，亦不证明目标运行时父容器尺寸、缩放和坐标关系。报告明确给出parent_geometry_verified=false、canvas_configuration_written=false。binary_readback通过仅证明写入字段回读；编辑器导入及实机始终not_checked。

修改后用同一画布和目标回读四态布局。最终父容器的尺寸及各设备表现需在编辑器或游戏中观察。

新增缩放专项覆盖两套非均匀缩放及不同轴心、最终GIL回读、重复应用一致、输入不变、缩放越界及省略非单位缩放配置拒绝。软件几何与二进制回读通过不等于编辑器或实机表现通过。

## 最终父容器本地尺寸核对

控件条目使用guid时可增加parent，指定当前实际父控件GUID，例如{"guid":123,"parent":456,"states":{...}}。模板名同时选中原型/入口两个不同对象，不能共用一个parent声明；需要父框架检查时分别按GUID配置。

读取最终UI记录的504父引用，核对显式关系、祖先存在且唯一、无循环，并读取父RectTransform对应状态的固定锚点尺寸。canvas四状态尺寸必须与父本地尺寸一致；两者不符拒绝输出。父容器同时在controls中修改时，核对最终修改后的尺寸，不依据处理顺序使用旧数据。拉伸父容器没有独立校准时拒绝，不套用其他引擎公式。

逐项报告parent、parent_size、parent_frame_verified。只有所有选中控件均声明并通过父框架检查时，总parent_frame_verified才为true；未声明的控件保持原有声明画布行为。该标记仅说明立即父容器的本地固定锚点尺寸，不证明祖先缩放/旋转后的屏幕边界、裁剪或真实宿主画布，parent_geometry_verified仍为false。父关系字段依据包内ui/guid_resolution.py，矩形读取依据readable_dump及现有RectTransform校准。

test_native_ui_parent覆盖两套控件、父引用/尺寸错误、父链循环、拉伸拒绝、同次父子修改的最终回读，以及produce失败回滚和输入不变。没有引入默认页面、布局或图片组件依赖。
