# 千星奇域阶段式制作

完整玩法、跨领域修改与交付可按以下顺序推进。接口查询或单项修改直接走[任务入口](../README.md)。工具负责读取、检查和构建已声明的内容，设计和实现仍由项目的开发者或协作者负责。

## 理解工程与验收目标

查看项目说明、现有源码、构建入口和基底清单。辨认用户要保留的逻辑、原始数据和交付文件，确定目标版本、平台模式及玩家设备。修复任务用明确的输入和操作复现首个失败；证据与文件对不上时先做[只读诊断](project-diagnosis.md#交付文件与清单不一致)。

把需求写成可观察的行为，例如重复提交只结算一次、隐藏页不继续接收输入、重开后计时器重置。已有系统沿用实际变量、信号、存档和挂载约定，新增入口明确其范围和调用方。记录会影响验收的产品判断，把玩法内容、配置和进度留在本项目。 [接口与工程合同](implementation-policy.md)

## 分工与实现

按[领域交接](capability-contract.md)说明 Lua、Graph Code、资源及写回的输入与输出。先确认谁拥有规则状态，再确定操作如何变成事件，谁发送和处理信号，以及谁消费结果更新界面。节点、字段、实体 ID 和原生挂载都从资料或实际工程确认。缺少证据时先做可验证的部分，并留下需要的最小样本。

新玩法先完成进入、首个操作、状态推进、反馈、结果与重开。项目要求使用原生节点或多人通信时，最小闭环包含所需的节点图和真实协议。按已有项目的规模扩展内容和美术，每个增量验证受影响的入口。修复先复测原来的失败动作，再核对相邻状态。

## 组装、回读与交付

先对照需求检查实际操作，再核查 API、生命周期、节点端口、身份、预算和基底校验值。需要一次交付多个相关产物时，用 [produce](produce.md) 声明阶段，按报告回读最终 GIL 的脚本、图、引用和保护字段。

沿玩家路径检查最终文件，所用设备、实测方法和报告字段见[游玩检查](playability-workflow.md)。按[交付反馈](validation.md#交付反馈)汇总产物、用法及证据。涉及保存重进、编辑器导入及宿主操作时按实际执行记录结果。

## 阶段与证据检查命令

```text
python scripts/qianxing.py workflow guide --kind feature
python scripts/qianxing.py workflow guide --kind fix
python scripts/qianxing.py workflow check PLAN.json
python scripts/qianxing.py verify OUTPUT
```

`guide` 提供 `feature`、`fix`、`ui`、`assets`、`delivery` 五类阶段。复杂任务需要恢复或交接时可保存计划。`check` 核对阶段顺序、需求覆盖、依赖、所有者和证据校验值。产物与输入清单用 `verify` 单独核对。旧的 `workflow check --report` 选项使用带 `files_sha256` 的历史制作报告。

```json
{
  "schema": 1,
  "domain": "genshin-qianxing-ugc",
  "kind": "fix",
  "goal": "修复当前奇域重开后的输入状态",
  "requirements": [{"id": "R1", "acceptance": "重开后的首个输入能执行"}],
  "steps": [{"id": "S1", "phase": "inspect", "owner": "miliastra-editor", "requires": [], "requirements": ["R1"], "status": "pending"}]
}
```

`done` 步骤需提供 `evidence` 数组，每项含 `kind`（`source`、`static`、`simulation`、`editor`、`host`）、`path` 和 `sha256`。`blocked` 步骤用 `blocker` 说明缺少的输入。校验通过说明记录完整且文件匹配，行为结论仍以对应实测为准。
