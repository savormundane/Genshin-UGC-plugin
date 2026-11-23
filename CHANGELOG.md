# 变更记录

记录影响创作者的公开变更。旧版演进可通过仓库的提交历史追溯。

## Unreleased

- MCP 支持会话工程目录及运行绑定热读，只读查询无需指定输出目录。
- 内联修改计划复用已验证摘要，写入阻塞报告可定位的对象、字段和目标引用。
- 新增全场俯视和侧视对照，并支持模拟进入已校准盒形触发区后执行挂载图。

- 统一插件、市场和运行入口为 Miliastra Wonderland，安装标识为 `miliastra-wonderland`。保留旧运行配置和素材产物的读取支持。

- 安装入口和项目链接更新为更名后的 GitHub 仓库地址。
- Codex 和 Claude 提供终端安装命令，DeepSeek Harness 通过 GitHub 直装。
- 精简技术参考与旧依赖文件，修正源码下载入口，自行打包时排除本地配置。

## 1.0.0

- Genshin-UGC 更名为 Miliastra Wonderland。发行从 1.0.0 重新编号，沿用原市场、仓库和插件 ID。
- Codex、Claude、DeepSeek Harness 与通用 Agent Plugins 共用四个 Skill 和一个插件目录。Client Lua 由 Qianxing Editor 提供。
- 市场或直装可复用 CPython 3.11–3.14，缺依赖时由 uv 准备。Release 提供源码，完整 Windows ZIP 可自行打包。
- 接入 MCP 后可直接查节点、API、平台资料和内置资源。打开工程后按名称和类型查找对象，并用同一输入摘要接续另存修改。
- 3D 布设可按布局键反复更新并保留实例身份。编辑器重新导出后可审阅具名绑定，联合模拟可复跑失败场景。
- 多份素材可共享控件预算。已有客户端原型库支持追加容器、按钮、脚本和素材数据。
