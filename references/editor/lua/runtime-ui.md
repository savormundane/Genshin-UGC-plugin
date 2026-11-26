# 客户端UI运行支持

`runtime-ui` 是位于 `scripts/runtime_ui.lua` 的可内联 Lua 5.3 模块，通过 `client assemble` 在配置中加入 `"modules": [{"name": "ui", "as": "UI"}]` 接入客户端。调用方按实际 API 提供创建、重置、销毁和控件操作。 [Lua 源码装配](client-assembly.md)

- properties()：write(control,method,...)通过官方控件方法提交变化的参数并返回是否实际写入；相同参数不重复写。参数表按值快照，须为无环值；控件复用或外部修改后forget(control)使缓存失效。
- pool(create,reset,destroy,capacity,properties?)：acquire(owner)返回带generation的句柄，release只接受当前句柄，valid检查对象身份，close销毁全部控件。传入属性缓存时复用和释放同步失效。
- queue()：add(owner,priority,operations,valid)、cancel(owner)、tick(createBudget,writeBudget)。操作声明creates、writes和run；调度前核对两个预算，前台高优先，同优先FIFO，操作失败时保留当前游标。调用方须按每项操作实际需要的 API 调用量填写预算。
- position_owner()：claim、write、release。drag包装move、finish和cancel；拖动持有位置权限时，拒绝来自常规渲染的位置写入。取消、失焦或生命周期中断调用cancel并清理监听。
- overlay(capture,restore,pause)：只保存一次来源上下文，open重复不覆盖，close恢复来源并解除暂停。上下文应包含所需选择／分页；不要复制整局数据。
- scope()：listen(control,Cursor或Key,event,callback)保留官方注册回调引用；add(cleanup)登记拖动取消等中断动作，close反向清理且可重复调用。由OnDisable、OnDestroy及实际输入中断调用；不假定隐藏或失焦会自动清理。

例如，单控件复用可使用容量 1，列表池可使用容量 3；每帧分别给创建1／写入2与创建3／写入6预算。操作的run只执行其声明的工作，缓存跳过写入时预算可保守计数。释放旧句柄后再释放它会被拒绝；拖动期间普通位置写入也被拒绝。list(items,key)的key应含该项的内容修订，避免只用不变ID导致内容更新被跳过。
- list(update,hide)：以调用方提供的稳定内容键按需刷新，隐藏尾部；内容变化必须改变键。

基础属性去重和逆序清理继续使用production_runtime.lua的dirty、scope。计时／暂停使用algorithms.clock，关卡暂停与脚本更新权限遵循API。

预算来自当前设备和任务，示例值只用于说明调度方式。模型工作量、软件排版与原生帧时间分别记录。验收覆盖两种池容量、旧句柄、任务取消、拖动／渲染竞争、覆盖层返回及销毁清理。
