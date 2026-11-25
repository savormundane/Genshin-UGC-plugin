在 DeepSeek Harness 里查询千星奇域节点和 Lua API，检查关卡文件，制作节点图和图元素材。

## 先查一个节点

启用插件，打开能运行本地工具的会话，发送这句话。

> 使用千星奇域插件查一下服务端「创建实体」节点。列出输入和输出端口，并说明版本依据。

`nodes_lookup` 的结果应包含「目标 GUID」输入和「流程出」输出。查询随包资料时可以直接提问。需要检查或生成文件时，在会话里选择并授权工程目录。

## 处理自己的项目

- **检查关卡。** 提供 GIL 或 GIA 文件和要查找的对象，查看其中的实体、引用和配置。修改既有关卡时，先审阅计划，再另存副本。
- **制作玩法和界面。** 查询节点端口、检查 Lua、制作静态布景，或把图片拟合成图元，在 Beyond 中预览生成的脚本。

原生写入按对应版本的样本校准。Beyond 画面用于软件预览，游戏内效果以实测为准。

## 本地运行

完整功能面向 Windows x64。需要 DeepSeek Harness 0.2.2-rc.5 和 Node.js 24.9 或更高版本。Python 可使用装好依赖的 CPython 3.11–3.14，也可通过 PATH 上的 uv 准备运行环境。首次安装依赖可能需要联网。 [安装自检](https://github.com/savormundane/miliastra-wonderland-plugin/blob/main/docs/installation.md#安装自检) · [制作教程](https://github.com/savormundane/miliastra-wonderland-plugin/tree/main/samples/creator-demos)
