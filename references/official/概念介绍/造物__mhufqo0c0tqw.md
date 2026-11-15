# 造物

# 一、造物的定义

造物是对人型生物、元素生物、深渊魔物、异种魔兽、小动物、机械战斗单位等的统称

造物可以自主对敌对*阵营*的实体做出反应，包含但不限于入战、追踪

阵营详见[阵营](./阵营__mhe1ixri46ta.md)

# 二、造物的特点

造物实体依赖编辑时配置的*行为模式*决定其行为逻辑，不可在运行时动态替换。

造物实体运行时仅生效一种行为模式，造物会在整个生命周期内严格依据模式执行行为。

造物实体运行时，默认携带和自身模型相等大小的*受击盒*，可以正确接收战斗信息。

造物实体遵循实体的一切通用规则。

# 三、造物的行为模式

造物实体的行为模式均来自于预先提供的行为池，不同造物实体支持配置的行为模式数量和内容不同，支持编辑时进行选择，不支持实体运行时动态切换。

每种行为模式都分为*未入战*和*入战*两部分逻辑，这两部分也提供了对应的模式配置，在不同的行为模式下分别提供不同的配置参数。

### (1)非入战

当造物创建后，默认处于非入战状态

当造物入战后，通过各种原因脱战，会重新回到非入战状态

### (2)入战

当造物通过*范围感知*或*视野检测*获取到敌对关系的实体时，造物会以对应实体为目标，从非入战状态切换为入战状态

# 四、造物的编辑

## 1.基础信息

菜单栏第一栏，为*基础信息*栏

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/7f29b50c-0d16-480e-b911-aa3ec271681b.png)

- **变换**

不支持空间X、Z轴的旋转，仅支持Y轴（水平朝向）的编辑

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/6526a255-3b70-4758-9fd5-46cad82a6f1d.png)

## 2.特化配置

菜单栏第二栏，为*特化配置*栏

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/867c0b3a-6734-4730-84f0-d729dde0d020.png)

### **(1)基础战斗属性**

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/64f024d8-2e74-41ab-bbf5-7720e414917f.png)

从等级属性和固定属性两方面，支持创作者(奇匠)对造物进行参数的调整、成长曲线的规划，详见[基础战斗属性](./基础战斗属性__mhvyqz9xwu0q.md)

### (2)仇恨配置

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/0c27d33a-f800-4f7e-b72c-34eda4d4b832.png)

详见[仇恨配置](./仇恨配置__mhw9ut96q96y.md)

### (3)常规设置

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/d198aa9b-6845-46a3-98ac-f0c1beccf81c.png)

详见[常规设置](./常规设置__mh3rgo0c16c8.md)

## **3.组件功**能

菜单栏第三栏，为通用组件栏

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/33e71fb7-23fe-4e8b-9ad5-e891e11492d2.png)

通过下方的“添加通用组件”按键，可以按需选择组件挂载。

每一种组件最多挂载一次。

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/b4fe0e09-adaa-43bb-8ac6-e4f96570ec5c.png)

造物实体支持添加多种组件功能，包括

- [选项卡](./选项卡__mh5jko05fzyw.md)
- [碰撞触发器](./碰撞触发器__mh8w69rzuc3i.md)
- [自定义变量](./自定义变量__mhso1b9wjica.md)
- [全局计时器](./全局计时器__mhawd6rl5kpy.md)
- [单位状态](./单位状态__mhd7nxrfa8im.md)
- [特效播放](./特效播放__mh4ppo02m1o8.md)
- [自定义挂接点](./自定义挂接点__mhmshmimtegs.md)
- [碰撞触发源](./碰撞触发源__mhn95di01j84.md)
- [音效播放器](./音效播放器__mhwiv89yra02.md)
- [背包组件](./背包组件__mh5y5001vqd4.md)
- [战利品](./战利品__mh63ox06afy8.md)
- [铭牌](./铭牌__mh5n160t2b6w.md)
- [文本气泡](./文本气泡__mhwtz297kp6a.md)
- [商店组件](./商店组件__mho6gviqhsqs.md)
- [扫描标签](./扫描标签__mhfc0lr1tcke.md)
- [小地图标识](./小地图标识__mh0pppib5eyc.md)

## 4.节点图功能

菜单栏第四栏，为*节点图*配置栏

![](https://act-webstatic.mihoyo.com/ugc-tutorial/knowledge/cn/zh-cn/mhufqo0c0tqw/86bb46c6-aaaa-4672-9eab-e6ec4cf0a587.png)

可引用预先配置的实体节点图，为造物添加逻辑功能
