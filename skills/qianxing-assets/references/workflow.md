# 单张图片到图元

以下是 GEIMG 命令参数，均通过 `Invoke-Geimg.ps1 -SessionDirectory ... -CommandArgs @('命令','参数',...)` 调用。所有输出路径使用工作区绝对路径；所有命令沿用同一 session-dir。首次运行可能需自解压。

实测拟合命令的 stdout 会先输出多条 JSON 事件（ev=phase/progress/done），最后才是多行 JSON 信封。不要对整段 stdout 直接 json.loads/ConvertFrom-Json；使用 JSON 流解码，取末尾含 ok 的对象并结合进程退出码判断。包装脚本原样透传该事件流。

1. `info` 与 `status` 检查版本和可用命令；拟合任务 `gui.open` → `ai.begin --note 任务描述`。
2. 第一步：`set project-name 名称`、`set object-type ui_control`（或用户需要的 asset_group），然后 `next`。
3. 第二步：`image add 图片绝对路径`、`image info`，查看原图；必要时 `image view --grid --out 网格输出目录`。然后 `next`。
4. 第三步：`fit recommend`。透明图通常 `fit mode transparent`、`advanced set edge-aware on`；其他参数先查 `advanced list`。预算要按整张图或同屏所有部件计算。不要把参考案例 10000 图元套到每个素材。
5. `fit shapes N` → `fit start --until full --timeout 60`。大于 500 的拟合长边需确认成本并按错误提示加 `--ack-high-res`。后台运行附 `--no-gui`。耗时操作使用可返回进度的执行方式。退出码 7 时读 `fit status`，有已保存进度才 `fit resume --timeout 60`。
6. `inspect --out 检查目录 --mode split`，打开返回的 PNG 实际看；先看轮廓和最差块，再看脸、文字等目标关键点。需要修补时读取 `image view --grid` 或 metrics 的源图矩形，`region add face x,y,w,h --kind face --note 描述` → `region report face` → `region fit face --shapes N` → `region inspect face`。先跑满全局，不为跳过前置条件而随意加 --force。
7. `review status` 显示需要评审的区域；无区域时 can_finish=false，即使只判整体也需 `region add whole 0,0,源图宽,源图高` 登记全图。看图后才 `review set 名称 --verdict ok --checklist 实际检查结果`，未满意填 needs-work。can_finish 为真后 `next` 到第四步。工具本身可在 can_finish=false 时 next/export，不代表质量合格；若这样导出务必标明草稿。
8. `export dataset --out 数据集目录`；有真实编辑器 ID 才加 `--prefab-id ID --asset-id ID`。随后检查 shapes/manifest/metrics、预览与 lua/geimg_render.lua。未绑定 ID 的 Lua 需编辑器配置。
9. 已开始托管的会话在 finally/清理步骤调用 `ai.end`。

## 错误恢复

| 退出码 | 应对 |
|---|---|
| 2 | 参数错误或尚未实现；检查 info/help，不猜参数 |
| 3 | 步骤错误；看 status/available，避免盲目 back |
| 4 | 前置条件不满足；读 error.hint 后改变操作，不原样重试 |
| 5 | 检查文件、编码、会话锁与路径；不要删用户已有会话 |
| 6 | 当前动作需要网络或注册；本地拟合和 dataset 导出可独立使用 |
| 7 | 超时/取消；检查已有进度，区分用户取消与自动时间片结束 |

`fit shapes` 不能直接减少已有图元。重拟合应新建会话保留上一版；局部可研究 region optimize（只删不补）。不要未经任务需要清空用户会话。

## 资料索引

详细参数与示例见 [原工具手册](geimg-manual.md)；其中联网反馈要求不自动执行。`geimg_kb_snapshot.json` 是随包历史快照，不能称为最新云端规则。实时 CLI 返回优先于旧示例。
