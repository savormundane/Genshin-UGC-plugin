# 可迁移制作与重建

可选 Beyond 阶段支持随包默认后端：自动收集其配置和显式文件依赖，保留 `@level` 到最终 GIL 生成后绑定，详细格式见 [模拟器后端](beyond-backend.md)。portable 不接受显式外部 backend；缺失依赖、越界输入及断言失败不提交交付目录。整个随包后端及许可证纳入工具链，仍需满足 Python/Lua、Node 和当前 Windows x64 渲染条件。

能力名：portable-delivery。入口produce schema 2的portable配置与qianxing.py verify --portable。适用于独立交付源码和工具后，在原工程目录不可用时重建；依赖相同指纹的Python、Node、Lua/Pillow环境，不安装或修改全局环境。

## 配置与使用

在现有制作配置中增加portable对象即可启用；空对象使用配置所在目录为project根。工程以外的输入根显式命名，额外数据文件或目录列在dependencies中。这些路径相对制作配置解析。

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

project与toolchain是保留根名称。目录依赖收集其非缓存文件；配置引用的脚本、图、GIL/GIA、素材、模拟、实验及图资源目录自动收集。目录外文件必须有明确的roots归属；缺失、链接或未声明输入拒绝。自用插件完整随附，保留官方资料、校准、第三方与许可证；这会增加交付目录体积，不生成ZIP。

portable/original保留工程输入原始字节；portable/workspace保存构建副本和独立toolchain。仅配置中已定义的路径字段改为副本间相对引用；不重写Lua/Python正文、业务文本或协议。portable/portable.json记录原始摘要、路径调整、后端指纹与文件清单。首次制作和显式重建只执行当前受信任插件的制作链，包内 toolchain 是历史材料，不参与执行和依赖搜索。

## 验证与边界

`--portable` 只核对包内输入、清单完整性、路径和摘要，不启动 Python、Node、安装器或包内工具链。普通 verify 检查原输入位置。未知工具链版本仍可静态核对，但不代表可重建。

显式重建先审阅工程源码，再将静态报告返回的完整输入摘要传入：

```text
python scripts/qianxing.py verify MOVED_DIRECTORY --portable --rebuild --trusted-inputs-sha256 APPROVED_DIGEST
```

该参数声明调用方已同意执行对应工程代码，不能从“哈希一致”自动推导授权。缺少确认、清单遗漏、越界或链接、工具链与当前插件不一致、后端指纹不同都拒绝重建。历史 `--rebuild` 需增加 portable 闭包与摘要确认；不再执行没有闭包的原路径重建。报告按字节比较可确定产物，不重签旧证据。

Python制作进程和Ayaya编译子进程检查实际文件读取范围，禁止把原路径当作隐含依赖；输入副本不可写，生成与编译临时目录可写。该检查服务于可信本地工程的依赖完整性，不是运行不可信源码的操作系统沙箱。Python、Node和外部包由环境提供并核对指纹；不承诺任意机器或后端版本均兼容。

manifest的artifacts为所有文件登记delivery、evidence、intermediate或input_snapshot。delivery按字节比较，包括JSON目录、协议定义、生成源码和其他格式；不以扩展名决定是否检查。重建必须具有相同文件集合与角色。证据与中间报告保留实际路径/耗时并由各轮清单校验，不要求跨轮字节相同；输入闭包单独校验。无角色清单的历史报告保留原有限比较范围，结果标记legacy_suffixes。

两套中性配置分别验证新建关卡和修改已有基底：装配Lua、真实图编译、素材、最终嵌入、模型断言，随后让原输入路径不可用并移动交付目录重建。独立检查test_delivery_portable.py还覆盖缺失/越界依赖、未声明读取、输入写入拒绝、无效Lua回滚、JSON产物变化和新增产物。编辑器导入、真实保存重进及实机表现保持单独待验。
