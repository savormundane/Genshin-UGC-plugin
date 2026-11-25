# 可迁移制作与重建

可选 Beyond 阶段支持随包默认后端：自动收集其配置和显式文件依赖，保留 `@level` 到最终 GIL 生成后绑定，详细格式见 [模拟器后端](beyond-backend.md)。portable 不接受显式外部 backend；缺失依赖、越界输入及断言失败不提交交付目录。整个随包后端及许可证纳入工具链，仍需满足 Python/Lua、Node 和当前 Windows x64 渲染条件。

从精简的 Git 安装制作 Beyond 交付时，经校验的 Canvas 原生文件收入 `portable/native-canvas/`。重建时按当前插件锁定的摘要核对这两份文件，并在隔离目录中离线加载。完整 Windows ZIP 已包含原生文件，随工具链一同保存。

`portable-delivery` 用于交付源码和工具，并在原工程目录不可用时重建。制作时使用 schema 2 的 `portable` 配置，检查时使用 `qianxing.py verify --portable`。重建要求 Python、Node、Lua 和 Pillow 环境的指纹匹配。工具不会安装或修改全局环境。

## 配置与使用

在现有制作配置中增加 `portable` 对象。空对象以配置所在目录为 `project` 根。工程之外的输入根须明确命名，额外数据文件或目录列在 `dependencies` 中。路径相对制作配置解析。

```json
{
  "schema": 2,
  "portable": {
    "roots": {"shared": "../shared"},
    "dependencies": ["../shared/lookup.data"]
  },
  "client": {"assembly": "client.json"}
}
```

```text
python scripts/qianxing.py produce JOB.json --out NEW_DIRECTORY
python scripts/qianxing.py verify MOVED_DIRECTORY --portable --out NEW_REPORT.json
```

project与toolchain是保留根名称。目录依赖收集其非缓存文件；配置引用的脚本、图、GIL/GIA、素材、模拟、实验及图资源目录自动收集。目录外文件必须有明确的roots归属；缺失、链接或未声明输入拒绝。交付包含所用插件的副本，包括官方资料、校准文件、第三方依赖及许可证。它们会增大交付目录体积。交付格式为目录。

portable/original保留工程输入原始字节；portable/workspace保存构建副本和独立toolchain。仅配置中已定义的路径字段改为副本间相对引用；不重写Lua/Python正文、业务文本或协议。portable/portable.json记录原始摘要、路径调整、后端指纹与文件清单。首次制作和显式重建只执行当前受信任插件的制作链，包内 toolchain 是历史材料，不参与执行和依赖搜索。

## 验证与边界

`--portable` 只核对包内输入、清单完整性、路径和摘要，不启动 Python、Node、安装器或包内工具链。普通 `verify` 同时核对产物摘要和原输入位置。若只需检查归档清单中的文件，用 `verify DIRECTORY --artifacts-only`。该模式把来源与重建标为 `not_checked`，可在原输入已变更或迁移时使用。

显式重建先审阅工程源码，再将静态报告返回的完整输入摘要传入：

```text
python scripts/qianxing.py verify MOVED_DIRECTORY --portable --rebuild --trusted-inputs-sha256 APPROVED_DIGEST
```

该参数声明调用方已同意执行对应工程代码，不能从“哈希一致”自动推导授权。缺少确认、清单遗漏、越界或链接、工具链与当前插件不一致、后端指纹不同都拒绝重建。历史 `--rebuild` 需增加 portable 闭包与摘要确认；不再执行没有闭包的原路径重建。报告按字节比较可确定产物，不重签旧证据。

重建以整套工具链文件清单为准。Git 市场、Windows ZIP 和 Cordis 包的文件范围可能不同。同版本切换分发形态时，使用原交付的匹配工具链重建，或用 `--portable` 保留静态核对。遇到 `portable.toolchain_mismatch` 可核对两份工具链摘要和文件差异数量。

Python 制作进程和 Ayaya 编译子进程核对文件读取范围，拒绝依赖未声明的原路径。输入副本只读，生成和编译的临时目录可写。这套检查用于核对可信本地工程的依赖，范围限于文件访问。Python、Node和外部包由环境提供并核对指纹；不承诺任意机器或后端版本均兼容。

manifest的artifacts为所有文件登记delivery、evidence、intermediate或input_snapshot。delivery按字节比较，包括JSON目录、协议定义、生成源码和其他格式；不以扩展名决定是否检查。重建必须具有相同文件集合与角色。证据与中间报告保留实际路径/耗时并由各轮清单校验，不要求跨轮字节相同；输入闭包单独校验。无角色清单的历史报告保留原有限比较范围，结果标记legacy_suffixes。

两套测试配置分别验证新建关卡和修改已有基底，覆盖 Lua 装配、实际图编译、素材、最终嵌入和模型断言。随后隔离原输入路径，移动交付目录并重建。独立检查test_delivery_portable.py还覆盖缺失/越界依赖、未声明读取、输入写入拒绝、无效Lua回滚、JSON产物变化和新增产物。编辑器导入、真实保存重进及实机表现保持单独待验。
