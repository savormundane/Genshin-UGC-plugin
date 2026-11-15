# 附件说明

知识库正文里用 `attachments/xxx` 引用的脚本都在这里。**这些是可直接运行的参考实现**，
不是伪代码；跑之前请看清楚用法（下面两条是常见卡点）。

- **工具本体（`GE_IMG_Tool.exe`）不随本包发布**：凡是要调用它的脚本（`l2d_fit_batch.py`、
  `l2d_superfit.py`），都用 `--exe "<路径>"` 指定，或者设环境变量 `GEIMG_EXE`；
  两者都不给时，按 PATH 里的 `GE_IMG_Tool.exe` 找。
- **脚本里的数值（预算表、阈值、倍数）是我们这一轮的取值**，是起点不是门槛；
  换素材/换机器按知识库 `02` 的 2.4（判断方法）、2.8（同屏图元预算）、2.9（benchmark）重新定。

## 依赖关系（谁 import 谁）

```
l2d_check_layers.py                     独立
l2d_compose_layers.py                   独立
l2d_build_assembly.py                   独立（生成单文件 HTML）
l2d_build_kb.py                         独立（把知识库拼成单文件）

l2d_fit_batch.py                        独立（调用 GEIMG 可执行文件；含放大前填色）
l2d_superfit.py  ──import──> l2d_fit_batch.py

l2d_raster.py                           独立（把图元栅格化，验收用）
l2d_edge_clean.py                       独立（剔溢出 / 缩边界 / 改色）
l2d_edge_probe.py ──import──> l2d_raster.py

l2d_build_showcase.py ──import──> l2d_edge_clean.py
                      ──读────>  templates/l2d_showcase.template.html
                      ──读────>  templates/l2d_export.template.lua
l2d_build_anim.py     ──import──> l2d_build_showcase.py
                      ──读────>  templates/l2d_anim.template.lua
                      ──读────>  templates/l2d_ui.template.lua
l2d_verify_anim.py                      独立（需要 lupa + luaparser）
l2d_verify_actions.py ──import──> l2d_verify_anim.py
l2d_verify_theater_keys.py              独立
```

## 用法（示例）

```bash
# 0) 环境：Python 3.10+，pip install pillow numpy；验证脚本还需要 lupa luaparser
#    工具本体：下载/取得 GE_IMG_Tool.exe 后，用 --exe 指路（或 export GEIMG_EXE=…）
py -3 l2d_check_layers.py  parts/                    # 手扣层自检
py -3 l2d_compose_layers.py parts/ --bg 32,34,40 --out compose.png

py -3 l2d_superfit.py      --parts parts/ --out fit_10k/ --workers 6 \
                           --exe "/path/to/GE_IMG_Tool.exe"          # 拟合（万元素预算）
py -3 l2d_fit_batch.py     --parts parts/ --exe "/path/to/GE_IMG_Tool.exe"   # 逐部件拟合
py -3 l2d_edge_clean.py    --source fit_10k --mask-source parts --out edge_report.json
py -3 l2d_edge_probe.py    --out edge_diagnosis.png

py -3 l2d_build_anim.py     --source fit_10k --mask-source parts                             --out l2d_anim.lua --out-ui l2d_theater.lua
py -3 l2d_build_showcase.py --source fit_10k --out l2d_preview.html

py -3 l2d_verify_anim.py --lua l2d_anim.lua
py -3 l2d_verify_actions.py --lua l2d_anim.lua
py -3 l2d_verify_theater_keys.py --lua l2d_theater.lua
```

> 不想用这些封装也可以：拟合与导出本身都在 `GE_IMG_Tool.exe` 的命令台上完成
> （`fit recommend` → `advanced set …` → `fit shapes` → `fit start` → `inspect` →
> `next` → `export dataset`），本包的脚本只是把"26 个部件并行 + 放大 + 坐标换算"
> 这些重复劳动包了起来。命令台用法见工具手册 `docs/GEIMG_AI上手提示词.md`。

## 关于 `templates/` 里的三个文件

`l2d_anim.template.lua`、`l2d_ui.template.lua`、`l2d_export.template.lua` 是**待填充的模板**，
里面有 `__CFG__` / `__RAW__` / `__PARTS__` 这类占位符 ——
**它们单独拿去解析会报语法错**，这是正常的（占位符不是合法 Lua）。
由 `l2d_build_anim.py` / `l2d_build_showcase.py` 读入并替换占位符之后，才是可运行的脚本。
真要看产物长什么样，跑一次构建、看生成的 `l2d_anim*.lua`。

## 需要你这边补的东西

| 缺什么 | 说明 |
|---|---|
| **GEIMG 拟合工具本体** | `l2d_fit_batch.py` / `l2d_superfit.py` 调用的是它的命令行，本包不含可执行文件；用 `--exe` / `GEIMG_EXE` 指定 |
| **API 类型定义 stub** | 知识库 `07` 的最高可信来源。**本包不放**：那份文件的头注释里写了目标平台名称，属于不该公开的信息 |
| **示例数据集与图层** | 本包只有脚本，没有随附素材 |
| **`lua-control-frame-animation.zip`**（官方帧动画示例） | 如果拿得到，很可能直接给出 `tweenDataTable` 的真实写法 —— 现在卡的就是这个（见知识库 `10`） |

脚本里的默认目录名（`parts/`、`fit_10k/` 等）是通用的示例名，和本项目实际用的名字不同；
按你自己的目录组织改参数即可。
