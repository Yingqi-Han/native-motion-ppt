# 可复用的动作与科学图形

从内容选动作。比较数值时保留共同坐标；讲时间过程时按采样顺序出现；解释实验条件时使用稳定主体跨页接续。重要数据出现后保持稳定，留给观众比较。

## 动作模块

实现位于 scripts/native_motion/recipes.py。函数返回副本，保留原始对象；已有动画发生冲突时明确报错。

| 函数 | 用途 | 关键约束 |
| --- | --- | --- |
| settled_drift | 主视觉小幅漂移，之后等待翻页 | 四段曲线接点切线连续，最终偏移为0，无无限循环 |
| wipe_in | 正值柱状图从底部展开 | 几何不变，单一原生擦除；方向 up，数值标签待展开后出现 |
| anchored_grow | 保留的复合变换接口 | 中心缩放依赖位移补偿同步；不作为 WPS 数据柱的默认方案 |
| fade_in | 标签、观测点或语义单元出现 | 数据点默认不移动，位置始终代表原始值 |
| reveal_sequence | 有顺序的采样点、线段出现 | 几何位置固定，只按顺序淡入 |

Morph 前先让主体回到静态布局，等待时间由页面与动作安排决定。内容页的讲解时间不能改变它的位置。品牌示例保留了用户认可的大球节奏；科研流程示例复用同一动作模块。

## 数据图形模块

实现位于 scripts/native_motion/figures.py。Figure.objects 放进页面，Figure.metadata 另存用于数据核对；不要把 metadata 塞进严格的页面 JSON。

```python
from native_motion.figures import bar_chart, Palette

figure = bar_chart(
    "latency", ["方法 A", "方法 B", "方法 C"], [52, 34, 21],
    [920, 385, 800, 425], [0, 60], "完成时间（s）",
    click=1, palette=Palette(),
)
slide["objects"].extend(figure.objects)
slide["clicks"] = [750]  # 预览模拟点击；手动 PPT 等实际点击
```

- bar_chart：正值柱状图，数值域从0开始。0值画成原生基线短线，不制造正柱高。负值与截断零点的域明确拒绝。
- line_chart：x 必须严格递增，所有点在声明域内。参考线保持可见；测量线段按观测顺序淡入。这是逐段出现，不是原生笔画绘制或连续拟合。
- dot_plot：展示原始观测，中位数与四分位区间由输入数据计算。四分位数使用 inclusive 方法；横向错开只用于分开点，不表示额外变量。
- process_flow 与 sample_network：说明条件和过程。示意网络不是物理分子模型；稳定对象及子对象 id 用于跨页匹配。

颜色、字体和画布位置由 Palette 与 box 控制。示例的纸色、深绿和衬线标题是一种选择，模块不强制其他项目沿用它。

所有图形都是可编辑的原生形状、曲线和文字；它们没有 Excel 图表工作簿。修改原始 CSV/列表后重新生成；PPT内也可以修改形状和文字，但这些修改不会自动回写数据。

## 五页演示

输入数据在 examples/data/scientific-demo.csv，全部是模拟数据。create_science_demo.py 生成 examples/scientific.json 及数据核对清单。

```bash
python scripts/build_demo.py --example science --video
```

输出位于 output/science/：手动与自动 PPT、30秒代码设计预演、实际页面 PDF、动态关键帧与检查记录。手动版按讲解点击；视频按 clicks 预演，不是 WPS / PowerPoint 放映录屏。

## 固定基线与播放器

旧 anchored_grow 使用绕中心缩放，同时向上位移补偿。只有两条通道的播放进度一致，柱底才固定。用户在 WPS 桌面报告越过零刻度后回弹；浏览器中的两条通道共用进度，未暴露这一问题。

默认柱状图现用 wipe_in：对象始终位于最终坐标，擦除从底部向上露出，不改变高度和位置。PPT 原生方向使用 preset 22 / subtype 4 / wipe(down)；filter 名称表示擦除边的定义，不能把视觉 up 直接写成 wipe(up)。实际 Impress 导入核对为 barWipe / topToBottom / reverse。

浏览器逐帧检查仍有价值，但不能证明 WPS 实机效果。v1.3.1修正版已获得用户“WPS播放正常”的反馈；v1.3.2增加独立Impress真实录屏，采样柱底稳定。用户反馈和本环境录像分别留档。其他项目需按 desktop-playback.md 实测，不能凭共用源数据推定所有播放器通过。

## 数据与运动检查

check_scientific.py 使用示例 CSV 列约定与生成清单，在实际 Chromium 中逐帧测量柱底，并核对曲线采样、中位数和观测点高度；检查轴线与标签没有动画。新数据来源应明确接入核对逻辑，不能将一次示例通过当作任意图表的证明。

```bash
python scripts/check_scientific.py --url http://localhost:3023/preview.html --out output/science/qa/data
python scripts/check_motion.py --url http://localhost:3023/preview.html --object sample-token --max-step 24 --out output/science/qa/motion
```

流程主体跨页移动约560设计像素；24px/帧阈值对应这类明确的位移。仍单独检查边界两侧的精确姿态，不能通过放宽速度阈值掩盖位置重置。

数据源 SHA-256 用于发现过期图形清单。超出坐标域的输入报错，不能静默裁剪。静态渲染检查同内容的多个刻度时，按文本框相交与位置匹配，避免将横轴0和纵轴0混淆；真实溢出仍需报错。
