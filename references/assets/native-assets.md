# 原生GIA素材导入

原生素材导入由 `scripts/miliastra/native/assets.py` 实现，支持经过校准的矩形装饰结构。导入依赖 Python 和 Pillow，无需启动 GE 或其他外部进程。

```text
python scripts/qianxing.py assets import-gia SOURCE.gia --spec IMPORT.json --out NEW_DIRECTORY
```

`IMPORT.json` 使用 `schema=2`，`projection` 固定为 `xy_x90`。`unit` 为源坐标中的网格单位，`max_controls` 为每项素材的实际控件预算。可选的 `names` 列出准确名称，`anchor` 指定锚点。当前校准覆盖模板 10009001 中绕 X 轴旋转 −90 度的 XY 平面矩形。其他旋转或图元的转换需要新的校准样本。

导入时读取元件和依赖，检查位置、尺寸、颜色和网格。`primitives` 保留原始图元的资源 ID、完整位置、旋转、缩放、ARGB 和深度层。同一素材默认必须共面。包含多个深度时，在 `layers` 中按从后到前的顺序显式列出，如 `[-2,3]`。实际深度必须出现在列表中，列表项须为互不重复的有限数值。工具跳过未使用的声明层。法向缩放仍须为 1。不同深度共享网格和原点，矩形只在同层内合并，`max_controls` 检查全部图层的控件总数。

`data.layers` 记录每层的 `depth`、从 1 开始的 `first_rect` 和 `rect_count`。`rects` 与 `palette` 按声明顺序排列，Lua 保留相同结构。多层素材的 `plane_z` 和 `source_anchor.world` 的 Z 值为 `null`，各层深度见 `primitives` 和 `data.layers`。运行时按声明的顺序创建和叠放控件。软件预览按 RGBA 的 Alpha 通道合成，宿主如何混合透明像素和处理遮挡仍待验证。

同层同色不透明矩形可无损行程合并；不同颜色重叠或半透明同色重叠明确拒绝，避免合并改变透明叠加。重叠图元须具有不同且显式排序的深度，不能人为修改源深度掩盖歧义。未知依赖、重复名称、错误尺寸和超预算拒绝整个输出。

产物包含 `catalog.json`，以及每项素材的 `asset.json`、`data.lua`、`preview.png` 和来源及参数清单。数据坐标以网格左上像素为原点，`world_origin` 和 `unit` 用于换算回源坐标。`preview.png` 是软件重建结果。按需加载、矩形容量统计和引用保护见 [runtime-assets](runtime-assets.md)。`algorithms.cache` 提供通用的按项缓存。角色目录和别名由项目提供。

source_anchor保留源坐标原点在导入网格的位置；anchor是调用方指定的运行锚点。无损检查要求网格重建的中心与尺寸还原为完全相同的源float32，颜色保持原ARGB字节。额外未知图元组件拒绝处理。负例包括丢失依赖、未声明深度、偏离网格、额外旋转、同层不同颜色/半透明重叠或法向缩放，均拒绝输出。

接入点为produce schema 2的assets项：{name,kind:gia,source,spec}。数据进入现有素材／动画／客户端能力，GIL挂载仍需真实模板。验证覆盖两种尺寸、颜色精确保留、依赖缺失及不支持投影。

`test_native_asset_layers` 覆盖两套尺寸和相反图层顺序，核对原始深度、`produce` 产物的来源和透明预览的像素。还检查缺失或重复的深度、总容量上限，以及同层半透明图元重叠时报错。其他空间投影、旋转和宿主图层顺序需要单独验证。
