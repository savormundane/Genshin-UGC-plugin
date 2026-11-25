# runtime-assets

按名称加载素材数据，以矩形数量限制缓存容量。装配清单的modules加入`{"name":"assets","as":"Assets"}`，源码requires加入Assets；produce的client.assembly自动内联模块，不需要文件系统或require。

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

目录、加载函数与素材由项目提供；rect_count必须与导入data.rects连续序列长度完全一致。容量统计矩形，不代表Lua内存字节或宿主控件数量。source是加载器自定的标识，模块不解析路径。加载器必须同步返回只读数据，不创建宿主对象、不回调缓存、不修改目录；错误向调用者传播，旧缓存保留。该模块验证容量合同，不重新验证导入器已保证的颜色、图层或几何。

每次acquire返回独立身份句柄，同名数据只加载一次。未释放句柄固定对应缓存项；容量不足且均被占用时返回nil及原因。只驱逐无人引用的最久未使用项；释放后可再次加载。重复/跨缓存释放返回false，失效句柄读取报错。data返回共享只读约定数据，调用者不得修改或在释放后继续使用。trim解除缓存引用，实际内存回收由Lua负责；不管理控件销毁。

stats返回rectangles、capacity、entries及pinned矩形数。未知名称、单项超限、占用容量不足返回失败；加载结果数量不符报错且不驱逐旧缓存。没有默认页面、主题或素材。

test_runtime_assets覆盖两种权重、占用拒绝、重复引用/释放、错误加载旧缓存保留、回收重载及两套produce最终Lua执行和输入不变。证据为Lua模型及离线构建；编辑器和实机尚未验证。原生图片组件校准为独立待办，不是此矩形数据模块的依赖。
