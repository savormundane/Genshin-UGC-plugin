# 知识可信度

入口为 `python scripts/qianxing.py knowledge api QUERY`、`knowledge sources` 和 MCP `api_lookup`。后者沿用 `symbol` 参数，可传正式符号、英文片段或中文用途。输出包含正式符号、原文说明和行号、摘要、推导标记及冲突说明。非精确匹配最多返回 20 项。

`match_basis` 标记候选的命中依据。枚举结果保留正式枚举名，命中的成员及其原文行见 `matched_values`。零结果时，`retry_hint` 提供重查提示。

## 中文查询

- 平台规则走 `docs_search`。提取「定时器」「控件」「图元」等平台术语，按版本查询，检查请求版本、来源版本和继承标记。没有选定版本且结论取决于版本时，先确认目标版本。
- Lua API 走 `api_lookup`。先查用途或已知正式符号。复合问法可拆成「按钮点击」和「隐藏控件」分别查。采用候选前核对正式符号、说明和适用依据。中文短语只用于检索。
- Graph Code 走 `nodes_lookup`。先按客户端或服务端作用域查「启动定时器」「创建实体」等动作，再核对端口。PNG 转图元需要看效果和控件数时使用 [`asset_preview`](local-mcp.md)。
- 首次无匹配时，换用更短的平台术语、已知别名或正式名称再查。仍无匹配时说明这次未在所选资料中找到，并指出可补充的版本、作用域或正式名称。对平台能力的判断以有依据的资料为准。

## 来源和适用范围

`documented` 表示包内文档明确记载，`derived` 表示根据属性、描述或关联枚举补出的合同，参数合同未确认时标为unknown；未知查询返回 `not_checked`。参数的 `parameter_enforced` 区分可据原文及对应属性阻断的规则和仅提示的推导。查询成功不是宿主可用证明。API原文的发布版本和官方来源未独立核实时保持空值，不赋予虚构日期或官方认证。

原文、整理说明和实测分别管理。官方平台资料通过 `docs search/show/diff` 查询版本、原始URL、摘要；7.2继承的旧资料明确标为未重新验证。遇到资料冲突，保留两方依据并限制结论到明确支持的范围；不要从标准Lua或其他引擎补造行为。

来源索引将 `client_api` 整理稿关联到官方文档 `mhtakr07vej4` 的 7.1 镜像。2026-09-23 是该文档在 7.1 指南更新日志中的日期。签名查询、快照和静态检查读取同一份已核验整理稿。平台更新时先用 `docs show mhtakr07vej4 --version VERSION` 找到所选原文，在候选中审阅整理稿，再用 `knowledge snapshot/diff` 核对签名、字段、枚举和回调变化。

维护时先比较来源正文，再检查签名、枚举、生命周期及适用环境；有依据才更新 `scripts/knowledge-sources.json` 的摘要和元数据，随后执行 API/来源相关专项。不能为消除错误而单独刷新摘要。保留原始资料和署名；指南只链接事实，不另行维护完整API副本。

图片资源ID不代表本地PNG加载能力；官方数量上限、工程预算与设备性能是不同证据。编辑器、宿主及用户验收通过显式人工记录附带产物摘要、环境和范围，不由离线测试推断。

依赖：包内API和来源索引；静态Lua检查另需Node/luaparse。例：`knowledge api game.GetUICanvasSize` 返回原文声明；`knowledge api game.LoadAnyLocalPNG` 返回未确认；原文摘要变化会拒绝查询。只读操作，不挂载或修改游戏文件。

增量维护使用knowledge snapshot与knowledge diff，见[平台更新与兼容](architecture-maintenance.md)。旧api文本检索保留输入输出字段，并附来源完整性与检索范围；它不替代签名查询。
