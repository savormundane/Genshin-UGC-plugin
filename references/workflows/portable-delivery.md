# 可迁移制作与重建

为交付目录保存项目输入、所用工具链和环境指纹，便于原工程移走后核对或重建。制作时在 [`produce` schema 2 配置](produce.md)中声明 `portable`，检查时使用 `verify`。

## 配置与使用

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

从制作配置所在目录解析路径。空的 `portable` 对象以配置所在目录为 `project` 根。外部工程输入要归属到 `roots` 中声明的某个根；`project` 和 `toolchain` 是保留名称。配置引用的脚本、图、GIL/GIA、素材、模拟、实验及图资源目录自动收集。将其他外部数据列在 `dependencies` 中，目录依赖收集非缓存文件。输入缺失、经过链接或超出声明范围时拒绝制作。

Windows 配置里的现有 8.3 短路径按文件的实际位置归入输入根，交付副本使用相对路径。新配置可以直接填写相对路径。

```text
python scripts/qianxing.py produce JOB.json --out NEW_DIRECTORY
python scripts/qianxing.py verify MOVED_DIRECTORY --portable --out NEW_REPORT.json
```

- `portable/original/` 保存工程输入的原始字节。
- `portable/workspace/` 保存构建用输入和当前插件的 `toolchain` 快照。已识别的配置路径改为副本之间的相对引用，源码、业务文本和协议保持原样。快照包含随包第三方依赖和许可证。
- `portable/portable.json` 记录原文件 SHA-256、配置路径调整、环境指纹和文件清单。

可迁移配置使用[随包 Beyond 后端](beyond-backend.md)，已声明的文件依赖会随交付收集，`@level` 在本轮 GIL 生成后绑定。Windows ZIP 内含的 Canvas 原生文件随工具链保存。从精简 Git 安装制作时，校验后的 Canvas 文件放入 `portable/native-canvas/`，重建按当前锁定值重新核对并加载。

## 验证与边界

| 目的 | 命令 | 检查范围 |
| --- | --- | --- |
| 在原工程位置核对交付 | `verify DIR` | 校验产物和原位置输入的 SHA-256。 |
| 移动后核对便携交付 | `verify DIR --portable` | 静态核对包内输入、清单、路径及校验值，给出 `trusted_inputs_sha256`。 |
| 只核对清单产物 | `verify DIR --artifacts-only` | 核对已登记的产物，在报告中把来源与重建标为 `not_checked`。 |

审阅源码并确认同意执行后，用静态报告返回的完整输入 SHA-256 重建。校验值用于绑定本次授权的输入。

```text
python scripts/qianxing.py verify MOVED_DIRECTORY --portable --rebuild --trusted-inputs-sha256 APPROVED_DIGEST
```

首次制作和显式重建由当前受信任的插件执行。归档内的工具链仅用于追溯与指纹比对。缺少输入确认、清单遗漏、文件越界、链接、工具链不匹配或后端指纹不同都会阻止重建。制作进程及图编译子进程检查文件读取范围，输入副本只读，生成和编译在独立可写目录中进行。这些是用于可信本地代码的依赖检查。环境由调用方提供，系统与运行依赖见[运行环境](../../docs/runtime-environment.md)。

重建所用的可信插件须与制作时记录的工具链文件范围和 SHA-256 一致。指纹包含随包文档，同版本的不同提交、分发包或文档改动也会影响比对。重建历史交付时，从匹配的源码提交或发布包恢复可信工具链。遇到 `portable.toolchain_mismatch` 可核对两份工具链指纹与文件差异，无法恢复时仍可用 `--portable` 静态核对。

`manifest.json` 的 `artifacts` 将文件标为 `delivery`、`evidence`、`intermediate` 或 `input_snapshot`。当前重建检查文件集合和角色，并对 `delivery` 的文件做字节比较，范围标为 `delivery_roles`。带路径、耗时的证据和中间报告由各轮清单校验，输入快照单独检查。无角色清单的历史报告沿用按扩展名比较的 `legacy_suffixes`。编辑器导入、保存重进及游戏内行为按[证据层级](validation.md)另行记录。
