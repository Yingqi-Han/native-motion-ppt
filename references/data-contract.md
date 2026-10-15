# 共用数据格式 v1 · v1.3.2 工具集

正式约束在 assets/spec.schema.json，命令 validate 会同时执行 schema 和语义检查。未知字段会报错。

## 文档与页面

- version：1。
- canvas：width、height 为正整数；fps 为1–120，默认60。
- theme：font、latin_font、background、foreground、accent。
- slides：按播放顺序排列；duration 单位毫秒，示例是每页2500ms。
- clicks：模拟点击的时间列表，递增且位于本页时长内。
- transition：kind=none/fade/push/wipe/morph，duration，direction=l/r/u/d。
- notes：讲者备注。
- 预览把非首场的入场转场包含在本场 duration 里。PPT自身的翻页、动画和转场计时仍由播放器执行。

## 对象

id 在同页唯一，用于编辑身份和跨页 Morph；只允许英文字母开头，以及字母、数字、下划线、点、短横。

box=[x,y,width,height] 为设计像素，普通对象宽高为正，线可为0高。组合的子对象坐标相对组合左上角。

kind 支持 text、rect、ellipse、line、polygon、path、group。fill 和 stroke 是不带#的六位RGB；几何填充可为none。opacity=0–1；rotation为度数。gradient 包含 from/to/angle。rect.radius 是圆角半径，按短边的一半限制。

text 增加 text、size、font、bold、align、spacing、line_height。JSON 中用换行转义，解析后的 text 必须是真实换行；不要把反斜杠和 n 当文字写进去。导出器不自动换行。line_height 是字号的倍数，PPT 输出固定点值行距，避免按字体自然行高再乘一次。预览按项目全部实际字体和粗细生成子集，并记录替换及缺字；PPTX 仍引用系统字体。

polygon.points 为相对本对象左上角的坐标，只支持直线边。不要用它假装支持任意SVG路径或滤镜。

path.d 支持绝对或相对 M/L/C/Q/Z；C 为三次贝塞尔，Q 为二次贝塞尔。可以有多个子轮廓；孔洞使用反向绕行的内轮廓。A/H/V/S/T 等命令不支持，必须先转换或简化；不会悄悄栅格化。坐标相对本对象左上角。图形路径与 animations.path 的运动轨迹是两个字段。

role 和 reveal_group 用于 choreograph：title/visual/caption 自动形成层级，body/data 按语义组出现；label/decoration 保持静态。已有 animations 不替换。

allow_overflow 标明有意出画布的对象；allow_overlap 标明有意重叠的文字框。只在设计确实需要时填写，仍要检查实际画面。

group.objects 为子对象；子对象不可有自己的动画。父组合可移动、旋转、缩放或入场。组透明度保持1；透明度和渐变加给子对象。

## 动画

kind=enter/exit/move/rotate/scale；at 和 duration 为毫秒。click=0 为自动，正整数引用 clicks 中的第几次点击。at 对点击动画是点击后的延迟。

enter 默认 from=[0,60]、to=[0,0]，同时淡入；exit 淡出；move 是偏移路径。from/to 为设计像素偏移。path 给2个点为直线，4个点为单段三次贝塞尔；7、10、13等 3n+1 个点为首尾相接的 n 段曲线（最多64个点），每段使用等长时间区间。用闭合曲线时同时检查首尾切线。与框的位置相加。

enter/exit 的 effect 默认为 fade；effect=wipe 为整对象原生擦除，direction=up/down/left/right 表示露出或收回的方向。wipe 的 from/to 必须是 [0,0]，不能叠加位移路径或 by_letter。柱状图使用 enter / wipe / up，位置和高度始终为最终几何。

rotate.degrees 是角度增量。scale 的 from/to 为[x比例,y比例]，必须为正。缩放绕中心。中心缩放与位移补偿的固定锚点依赖播放器两条通道同步；数据柱优先用单一擦除，不依赖这种复合变换。

loop=true 为持续循环；auto_reverse 默认true，形成往返。循环默认 accel=decel=0.5；明确指定时按指定值执行。单向循环需让路径首尾、缩放比例或旋转整周衔接，避免每轮跳回。入场/退场不允许循环。不要对同一属性堆叠不确定的同时动画；代表性场景先在PowerPoint中验证。

by_letter=true 仅支持单行文字入场/退场；letter_delay 默认35ms。中文短标题和ASCII标题是推荐输入；复杂组合字符应另行验证。

accel、decel 为0–1且和不超过1，映射到PPT的加减速比例；浏览器计算相同的分段进度曲线。

ambient=true 明确声明移动、缩放或旋转是环境运动，不是新的内容揭示；阅读停留从内容出现完成时算起。动作本身仍需在翻页前完成，除非声明循环。入场/退场不得标为 ambient。不要为避开检查而把重要图表变化标成环境动作。

## 例子

```json
{
  "id":"headline",
  "kind":"text",
  "text":"先看见重点。",
  "box":[112,420,1300,170],
  "size":100,
  "bold":true,
  "fill":"090B12",
  "animations":[
    {"kind":"enter","at":120,"duration":650,"from":[0,48],"by_letter":true,"letter_delay":55}
  ]
}
```

build 生成 manifest，记录源路径、对象与PowerPoint shape id映射及警告。preview 生成规范化 document.json、字体与共用时间线，便于独立调试。

