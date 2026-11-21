# 独立运行环境

如果只使用命令行，可解压完整 ZIP，在解压后的 `Genshin-UGC` 目录里配置专用 Python。配置前请核对[运行要求与验证](compatibility.md)中的操作系统、Python 和 Node.js 要求。

```text
EXISTING_PYTHON scripts/configure_runtime.py --python EXISTING_PYTHON --runtime NEW_RUNTIME_DIRECTORY --project PROJECT_ROOT --outputs SEPARATE_OUTPUT_ROOT --config RUNTIME_CONFIG
```

- `EXISTING_PYTHON` 是已有解释器的绝对路径，`NEW_RUNTIME_DIRECTORY` 是用来创建专用虚拟环境的新目录。
- `PROJECT_ROOT` 是已有工程目录，`SEPARATE_OUTPUT_ROOT` 是与它互不包含的输出目录。
- `RUNTIME_CONFIG` 是新配置文件路径。命令失败时保留原有配置，同参数的未完成安装可加 `--resume` 继续。

配置按 `scripts/runtime-requirements.lock` 校验并安装锁定的 wheel。工具使用专用环境，无需改全局 Python。用该环境中的 Python 运行 `scripts/qianxing.py doctor`，核对解释器、Node 版本和依赖导入结果。

手动连接 MCP 时，将 `UGC_RUNTIME_CONFIG` 指向配置文件。启动器用配置中的解释器、工程目录和输出目录。切换工程后重新配置绑定，打开新的客户端会话确认工具可见。[客户端适配](contributing/development.md#客户端适配)

旧环境可用于回退。跨版本复用前先对照依赖锁和 `doctor`，环境目录名可与插件版本不同。[更新与回退](installation.md#回退与卸载) · [长期维护](../references/architecture-maintenance.md)
