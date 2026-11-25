在 DeepSeek Harness 里查询千星奇域节点和 Lua API，检查关卡文件，制作节点图和图元素材。

## 先查一个节点

启用插件，打开能运行本地工具的会话，发送这句话。

> 使用千星奇域插件查一下服务端「创建实体」节点。列出输入和输出端口，并说明版本依据。

找到 `nodes_lookup` 调用后，核对输出里的「目标 GUID」输入和「流程出」输出。首次查询随包资料时可直接提问。检查或制作文件时，在会话里选择并授权包含关卡的工作目录。

## 处理自己的项目

- **检查关卡。** 给出 GIL 或 GIA 文件和你关心的对象，查看识别出的实体、引用和配置。修改既有关卡时先审阅计划，产物另存。
- **制作玩法和界面。** 查询节点端口、检查 Lua、制作静态布景，或把图片拟合成图元，在 Beyond 中预览生成的脚本。

原生写入按对应版本的样本校准。Beyond 画面用于软件预览，游戏内效果以实测为准。

## 本地运行

完整能力面向 Windows x64。需要 DeepSeek Harness 0.2.2-rc.5、Node.js 24.9+，以及具备依赖的 CPython 3.11–3.14 或 PATH 上的 uv。首次准备 Python 依赖可能联网。 [安装自检](https://github.com/savormundane/miliastra-wonderland-plugin/blob/main/docs/installation.md#安装自检) · [制作教程](https://github.com/savormundane/miliastra-wonderland-plugin/tree/main/samples/creator-demos)
