# 原生ID分配登记

登记工具支持确定性 ID 分配、预留和基底绑定，也可对已校准的服务端图重编号。省略 `remap` 时，`ids apply` 只输出登记文件。声明 `remap` 后，还会生成修改后的 `level.gil`。工程级图 ID 以及实体、控件、脚本和结构体等引用的重映射仍待实现。

```text
python scripts/qianxing.py ids plan base.gil allocation.json --out allocation-plan
python scripts/qianxing.py ids apply base.gil allocation-plan/plan.json --out allocation-registry
```

输入只读，输出目录须使用尚不存在的路径。工具在临时目录完成操作后提交输出。`plan` 输出 `plan.json`，`apply` 输出 `registry.json`，两者均附输入与产物清单。

```json
{
  "schema": 2,
  "base_sha256": "填写基底文件的SHA256",
  "namespaces": [
    {"name":"logic","kind":"node","scope":["ordinary",1073741900],"minimum":1,"maximum":100},
    {"name":"events","kind":"node","scope":["ordinary",1073741900],"minimum":1,"maximum":100}
  ],
  "reservations": [{"namespace":"logic","name":"future","id":50}],
  "requests": [
    {"namespace":"logic","name":"entry"},
    {"namespace":"events","name":"handler","id":20}
  ]
}
```

另一个示例可选择不同的图，例如 `scope` 为`["ordinary",1073741901]`且范围20至80；分配与该图已有节点分别核对。也可为graph登记`scope:["ordinary"]`，或entity登记`scope:[]`。node的范围属于单图，graph区分ordinary/composite，storage_slot归属于单个存储模板；其余支持种类为无额外scope的definition、structure、template、entity、control、script、storage_template。

namespace仅是所有权名称，不能使同一原生域内相同ID合法共存。先登记已有对象与预留，再按requests的显式顺序取范围内最小可用ID；显式id冲突直接失败。保留requests顺序，不自动排序。范围是调用者给定的uint32子集，不意味着平台允许整个uint32范围，生成器仍须核对对应平台合同。

输出包含每项的kind、scope、name、namespace、id和计划摘要。apply重新读取基底并重新计算完整计划，拒绝基底漂移、计划篡改及重算结果不符。不扫描任意整数猜测引用；未知结构仍由工程索引报告，complete_reference_index保持false。因此该登记只检查已索引身份是否冲突。迁移未知资源引用或字段前仍需单独核对。

## 图内节点重编号与制作链

在上述配置中增加以下字段，将已有节点1迁到名为entry的分配结果：

```json
{"remap":[{"graph_kind":"ordinary","graph_id":1073741900,"nodes":[{"from":1,"namespace":"logic","name":"entry"}]}]}
```

目标分配必须属于同一graph_kind/graph_id的node命名空间，每个目标只能使用一次。plan输出附带native-plan.json，含修改前后摘要、语义差异和受保护字段摘要。apply重新核对计划，原生审计通过后才提交level.gil和native-report.json；未知格式或引用载体失败时不提交输出目录。

produce可直接使用该native-plan.json：

```json
{"schema":2,"native":{"base":"base.gil","plan":"allocation-plan/native-plan.json"}}
```

原生补丁也支持`{"op":"remap_nodes","graph_kind":"ordinary","graph_id":1073741900,"mapping":[{"from":1,"to":10}]}`。该操作可通过native plan/apply及produce执行；映射同时应用，因此显式交换两个已有节点编号不会产生中间碰撞。ID分配入口则只分配尚未占用的目标，不自动交换已有身份。

重编号修改节点身份、所有已存储执行/数据连接的远端节点号以及复合图接口的innerNodeId。节点定义ID、信号版本、结构体身份、端口编号和常量不因整数相等而替换。其它图及顶层字段保持原始字节；图中未变化的字段与连接保持原始字节，仅受影响的字段及其长度封装更新。

当前写入只接受GIL内已校准服务端图。未知图/节点/端口/连接字段、客户端绑定元数据、未校准图附属引用拒绝；不存在的源节点、冲突目标、重复源、悬空连接及复合接口拒绝。图内节点号要求正int32，不能将分配器一般uint32范围直接用于节点。复合接口的字节重映射有独立检查，实际复合图仍须通过最终声明和类型审计。

字段依据为包内Ayaya的record_codec.py连接写入规则及工作区保留的第三方gia.proto中GraphNode、NodeConnection、CompositePin定义；第三方定义不是官方宿主验收证据。实现没有运行时外部仓库依赖，也没有修改第三方文件。

登记和重映射属于离线文件操作。使用新编号前，回读实际连接和复合接口，并在编辑器里核对挂载。
