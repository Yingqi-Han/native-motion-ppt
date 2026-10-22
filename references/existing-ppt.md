# 现有 PPT：先看内容，再应用分组

```bash
python scripts/nmp.py plan input.pptx --max-clicks 3 --out output/plan
python scripts/nmp.py enhance input.pptx --plan output/plan/plan.json --out output/enhanced.pptx
```

plan 输出 inventory.json、可编辑 plan.json 与 plan-review.html。HTML 的框图是原生对象坐标示意，不是幻灯片渲染或实播。查看实际页面，再按论点与图表注释核对 groups；不要把布局规则的草案称为语义已验证。

生成规则保留标题、脚注、背景与不确定对象；包含关系帮助把卡片背景和文字放在同一点击内，按阅读位置排列信息块。原生组合保持整体，图表/表格整体淡入；旋转、画布外及未知对象不猜动作。单个文本框保持完整，不拆段落或改写文字。--max-clicks 限制草案的点击数，多个单元可能共用一次点击，需要按讲解目标审阅。

v2 plan 用 source_pptx_sha256 绑定源文件，slides[].groups 继续使用顶层对象 ID。允许编辑分组，不能改绑 SHA 使旧计划套用新文件。子对象不能代替父组合 ID；重复、缺失、布尔 ID、错误页码或空组会在写输出前拒绝。animation 配置仅支持整体 fade、duration_ms（100–3000）与 stagger_ms（0–1000）。这种淡入不移动图表坐标和文字，仍须真实播放器验证。

增强直接从原 ZIP 复制非目标成员，只为选中页替换/添加 p:timing。报告记录实际变化的成员、源/输出/计划 SHA，并核对目标页的其他 XML、母版、关系、图片、备注与未知成员。已有动画整页保留；无动画目标的页面也不重写。数字签名 PPT 拒绝编辑，避免误称签名仍有效。原稿和已有输出不覆盖。

普通增强报告的 desktop_playback 仍为 pending。原生 JSON 项目可用 accept 的完整自动流程；任意导入 PPT 不会被虚构成有对应 JSON 的项目，也不会擅自改成自动翻页。对增强文件按 [WPS 实播](wps-playback.md) 真实录制，核对每次点击前/后、静态文字、图片和已有动画，再附实测报告。自动播放的旧动画需要单独设计和验证。

复现仓库自制样本（含两栏卡片、组合图表、图片、备注与已有动画）：

```bash
python scripts/create_existing_demo.py --out output/existing/source.pptx
python scripts/nmp.py plan output/existing/source.pptx --max-clicks 2 --out output/existing/plan
```

这只是明确标注的模拟回归，不是用户真实业务项目；后续真实输入须取得授权并独立记录其播放结论。
