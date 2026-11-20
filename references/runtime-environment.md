# 独立运行环境

Python 3.11–3.12、Node.js 22+。DeepSeek Harness 需要 Node.js 24.9 或以上。随包Beyond保留Windows x64本地依赖；Python依赖安装到插件专用虚拟环境，不借用游戏环境，不安装到系统Python。

```text
EXISTING_PYTHON scripts/configure_runtime.py --python EXISTING_PYTHON --runtime NEW_RUNTIME_DIRECTORY --project PROJECT_ROOT --outputs SEPARATE_OUTPUT_ROOT --config RUNTIME_CONFIG
```

配置命令必须显式执行；已有runtime目录拒绝覆盖。安装使用 `scripts/runtime-requirements.lock` 的精确版本，目前锁定Windows环境；其他平台需要单独验证，不能宣称随包二进制跨平台可用。配置文件记录解释器、项目根和互不包含的输出根；失败时不会切换现有配置。

MCP清单以Node运行 `scripts/mcp_launcher.cjs`。公开安装由各协议入口显式设置 `UGC_RUNTIME_CONFIG`。手动接入可按[安装说明](installation.md)绑定配置；启动时清除外部Python路径注入，不下载或安装软件。缺配置给出明确错误。切换工程时显式更新绑定的project/output根。

CLI使用配置中的Python绝对路径运行 `scripts/qianxing.py`。`doctor` 报告实际解释器、Node版本、依赖版本及导入结果；在所选客户端的插件或 MCP 列表检查实际加载结果。更新插件后使用新会话核对工具是否可见。

安装后核对版本目录、所有文件摘要和一次真实stdio调用；可选Beyond另调用最小场景。打包、安装文件一致、stdio协议可调用、Agent 客户端发现、编辑器导入及游戏运行是不同验证层。锁定依赖的升级需要显式安装与相关专项，不随查询自动更新。

跨版本复用运行环境时核对依赖锁和doctor；环境目录版本名不是插件版本。旧环境保持可恢复，不因升级插件自动重建或删除。回退步骤见[长期维护](architecture-maintenance.md)。

锁定运行依赖不再支持 Python 3.10，安装前即拒绝。wheel 使用 SHA-256 与 `--require-hashes --only-binary=:all:`，不自动升级 pip。首次失败可使用相同参数及 `--resume` 恢复未完成的专用环境；已有有效配置拒绝覆盖。
