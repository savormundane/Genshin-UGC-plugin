# runtime-assets

模块按名称加载素材数据，以矩形数量限制缓存容量。在装配清单的 `modules` 中加入 `{"name":"assets","as":"Assets"}`，并在源码的 `requires` 中加入 `Assets`。`produce` 的 `client.assembly` 会将模块内联到最终 Lua，运行时无需访问文件系统或调用 `require`。

```lua
local cache = Assets.create{
  capacity=100,
  catalogue={marker={source="marker",rect_count=2}},
  load=function(source,name) return projectAssetData[source] end
}
local handle,reason=cache:acquire("marker")
if handle then
  local data=cache:data(handle) -- 按原始rects/layers顺序交给渲染器
  cache:release(handle) -- 页面或使用者结束后释放
end
cache:trim() -- 清除全部无人引用项
```

素材目录、加载函数和素材由项目提供。`rect_count` 必须等于导入数据中 `data.rects` 连续序列的长度。缓存容量按矩形数统计，Lua 内存用量和宿主控件数需分别测量。`source` 是加载器自定的标识，模块按原样传给加载函数。加载器必须同步返回只读数据，不得创建宿主对象、回调缓存或修改目录。加载失败时，错误传给调用者，旧缓存保留。模块检查容量，颜色、图层和几何由导入器检查。

每次调用 `acquire` 都返回独立的句柄。同名数据只加载一次。只要还有未释放的句柄，对应缓存项便会保留。需要腾出容量时，移除最久未使用且没有句柄引用的缓存项。仍无法腾出容量时，返回 `nil` 和原因。缓存项移除后可以重新加载。重复释放或跨缓存释放返回 `false`，使用失效句柄读取会报错。`data` 返回共享数据，调用者应将其视为只读，释放句柄后停止使用。`trim` 清除缓存中的引用，内存由 Lua 回收，控件由调用方销毁。

`stats` 返回 `rectangles`、`capacity`、`entries` 和仍被句柄引用的矩形数量 `pinned`。名称未知、单项超过上限或剩余容量不足时返回失败。实际加载数量与声明不符时会报错，旧缓存保留。页面、主题和素材均由项目提供。

`test_runtime_assets` 覆盖两种权重、容量不足时拒绝加载、重复引用和释放、加载失败后保留旧缓存，以及缓存项移除后的重新加载。离线执行两套 `produce` 生成的最终 Lua 后，也核对了输入保持原样。当前证据来自 Lua 模型和离线构建。编辑器和实机尚未验证，原生图片组件的校准另行进行。
