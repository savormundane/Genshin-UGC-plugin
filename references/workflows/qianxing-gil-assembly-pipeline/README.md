# GIL 组装流水线

将 Graph Code、信号与 Lua 组装为 GIL，或排查写回、挂载、类型和 precheck 错误时，读取[组装流程](references/workflow-details.md)。优先复用现有 produce/build 和最终回读；仅修改 Lua 或单个图时使用对应局部入口。

按改动范围选择检查，完整交付才执行全部适用验证。静态、模型、编译回读、编辑器、宿主和用户验收分别报告；已有输出使用新目录保护，未知格式不猜测改写。
