# 原生GIA素材导入

能力名：native-assets。scripts/native_assets.py读取已校准矩形装饰结构，依赖Python与Pillow，不启动GE或外部进程。

```text
python scripts/qianxing.py assets import-gia SOURCE.gia --spec IMPORT.json --out NEW_DIRECTORY
```

IMPORT为schema=2，projection固定xy_x90，unit为当前源坐标的网格单位，max_controls为每项实际预算，可选names精确名称列表和anchor。当前校准为模板10009001、X旋转-90度的XY平面矩形；其他旋转／图元不猜测转换。

读取元件及依赖，检查位置、尺寸、颜色与网格；原始图元资源ID、完整位置／旋转／缩放、ARGB与深度层保存在primitives中。默认同一素材必须共面；多深度时显式声明layers，例如[-2,3]表示从后到前，顺序不能由Z值自动推断。所有实际深度必须出现在唯一有限数值列表中，未使用的声明层跳过；法向缩放仍须为1。不同深度共享网格与原点，逐层合并且不跨层合并，max_controls检查合计数量。

data.layers记录每层depth、从1开始的first_rect和rect_count，rects与palette按声明顺序排列，Lua保留相同结构。多层plane_z及source_anchor.world的Z为null，实际深度以primitives和data.layers为准。运行端按层顺序创建/叠放，不把深度值当成宿主自动层级。软件预览采用RGBA alpha合成；宿主透明混合及遮挡仍待验。

同层同色不透明矩形可无损行程合并；不同颜色重叠或半透明同色重叠明确拒绝，避免合并改变透明叠加。重叠图元须具有不同且显式排序的深度，不能人为修改源深度掩盖歧义。未知依赖、重复名称、错误尺寸和超预算拒绝整个输出。

产物包含catalog.json、每项asset.json、data.lua、preview.png及来源／参数清单；world_origin与unit保留到源坐标的对应关系，数据坐标为左上网格像素。预览是软件重建，不是原生截图。按矩形容量计费、引用保护及按需加载使用[runtime-assets](runtime-assets.md)；algorithms.cache保留通用按项缓存。角色目录和别名由项目提供，不随插件打包。

source_anchor保留源坐标原点在导入网格的位置；anchor是调用方指定的运行锚点。无损检查要求网格重建的中心与尺寸还原为完全相同的源float32，颜色保持原ARGB字节。额外未知图元组件拒绝处理。负例包括丢失依赖、未声明深度、偏离网格、额外旋转、同层不同颜色/半透明重叠或法向缩放，均拒绝输出。

接入点为produce schema 2的assets项：{name,kind:gia,source,spec}。数据进入现有素材／动画／客户端能力，GIL挂载仍需真实模板。验证覆盖两种尺寸、颜色精确保留、依赖缺失及不支持投影。

test_native_asset_layers覆盖两套尺寸/相反图层顺序、原始深度保留、produce输出同源、透明预览精确像素、缺失/重复深度、总容量以及同层半透明重叠拒绝。未扩展到任意空间投影、旋转或宿主图层自动推断。
