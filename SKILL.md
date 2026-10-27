---
name: native-motion-ppt
description: 制作、美化、重做原生可编辑动态 PPT；添加分步动画、逐字出现、运动路径、缩放旋转与 Morph。共用数据生成 Remotion 设计视频及 PPTX，一键真实放映录屏、抽帧检查、验收与交付。Use for native animated PowerPoint, editable motion slides, shared Remotion/PPT workflows and real playback acceptance.
---

# Native Motion PPT · v1.8.0

把内容、版式和运动一起设计。交付能继续编辑的 PPTX，动画由 PowerPoint 对象、时序与转场完成。

## 先选路线

- **现成 PPT，主要加动画：** inspect → 看实际页面 → 按语义制定分组计划 → enhance → check。
- **重做、美化或新建：** 看内容和受众 → 设计页面与镜头 → 编写共用 JSON → build → preview → check → 迭代。
- **Remotion / 视频发展为 PPT：** 优先读取原有对象、文字、图形和时间数据。只有 MP4 时，抽关键帧并重建对象；明确这是重新制作，不能承诺恢复原动画。
- **视频与 PPT 双输出：** 先用同一份 JSON 制作设计视频，再导出对应原生 PPT，最后在目标桌面播放器放映核对。设计视频必须标为代码预演；只有实际放映录屏才能标为 PPT 播放视频。
- **先参考科普案例做视频，再做 PPT：** 按[科普视频优先流程](references/science-video-first.md)查阅在线参考、核对科学模型、重新编写分镜和讲解，先完成原创动画成片与检查并封存 `VIDEO_LOCK.json`，之后才制作对应原生 PPT 和 WPS 实录。主片是独立科普视频；PPT 设计预演和 WPS 放映录像分别标记，不能混用来源。

用户已提供主题、方向或参考时，直接推进。不要反复询问是否继续；沿用已授权的目标。保留用户原稿，输出新文件。

用户反馈“动画一般”“不惊艳”时，先按[设计与运动](references/design-and-motion.md)制作 15—25 秒的视觉样片：一个明确主体、一处有意义的动作接续或跨页重组、可辨认的节奏和停留，再用目标播放器实播展示。基础淡入的验收通过不能代替视觉质量；“惊艳”保留为用户的审美判断。原创例子见 `examples/cinematic-focus.json`，它走重做路线，现成 PPT 的保护增强仍只加整体淡入。

## 新用户项目入口

优先使用 `scripts/nmp.py`，说明见 [第一次使用](references/first-project.md)。帮助、创建和诊断不加载第三方依赖；导出与预览生成使用 requirements-core.txt，完整验收再使用 requirements.txt。

```bash
python scripts/nmp.py new output/my-project --template product
python scripts/nmp.py doctor --for build
python scripts/nmp.py build output/my-project
python scripts/nmp.py preview output/my-project
```

默认 minimal 使用随包字体；product、progress 和 science 是可修改的内容/动作示例。模板用于启动与复现，不替代受众分析、数据核对和视觉设计。原生导出成功后仍须实际播放，build-report 中的 desktop_playback 保持 pending。

`--template cinematic` 提供三页连续主体样片：聚拢 → 原生 Morph 变为数据柱 → 同一图表扩展到全幅并突出最高值。用 `python scripts/nmp.py new output/motion-study --template cinematic` 创建可编辑项目。模板使用明确标注的模拟数据；改数值时要同步对应页几何和标签，不能只改数字或把镜头重排误作数值变化。

完整流程用 `nmp.py accept <项目> --player wps`，播放器路径、实际字体、所需依赖按阶段预检；复验用 `accept --resume <旧运行> --mode record/check`。`enhance` 对已有 PPT 做保护原稿的增强和结构检查。高级脚本和下述参数继续保留。

## 一键制作与验收

依赖就绪后优先使用 accept_project.py。每次在新的运行目录中完成：源文件检查 → 代码预演 → 设计视频 → 原生PPT → 实际页面与动画导入 → 私有显示器放映录屏 → 逐帧识别活动与停稳 → 真实对象运动检查 → 报告 → 完整可编辑工程包及校验。

```bash
python scripts/accept_project.py examples/scientific.json --out output/runs --profile science --desktop-tools-root "$HOME/.local/share/native-motion-ppt/desktop" --target-player wps-desktop --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile"
```

一般项目省略 --profile science。--actor 指定连续主体；科学示例默认检查 sample-token。GUI未安装时可加 --install-desktop 和 --desktop-tools-root，安装完成后再录制。--target-player 真正选择后端；WPS 使用 record_wps.py，Impress 使用 record_desktop.py。所选播放器缺失时明确待检查，不静默替换。PowerPoint 后端当前未实现。

输出包含 deck.pptx、deck-auto.pptx、design-preview.mp4、player-recording.mp4（点击实录）、player-recording-auto.mp4（自动实录）、report.html、REPORT.md、acceptance.json 与 acceptance-delivery.zip。原稿不改；旧录像与新PPT通过校验值隔离。失败留日志，未执行项目标为待检查；有待检查项不等于运行失败，也不能宣布全部通过。--strict 让待检查的必需项返回退出码2，失败为1。

查看本次实际页面与录像关键帧后，可追加明确的审阅记录并重封交付包，不重新渲染：
```bash
python scripts/finalize_acceptance.py <运行目录> --visual-review-note "本次实际页面与录像关键帧的具体审阅结论"
```

v1.6.0 分别记录 automatic_status、reviewed_status 与最终 status。审阅绑定本次点击/自动两份录像和实际帧证据；不能将另一播放器或自动失败改写为通过。方法与范围见 [一键验收](references/acceptance.md)。

### 只重录 / 只检查

```bash
python scripts/accept_project.py --resume output/runs/previous --mode record --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile" --desktop-tools-root "$HOME/.local/share/native-motion-ppt/desktop"
python scripts/accept_project.py --resume output/runs/previous --mode check
```

两者都创建新运行目录，保留旧证据。record 复用已核对的源/PPT/实际参考，仅重录并分析；check 复用同一录像，只重新分析，不启动播放器、不构建或渲染。依赖校验值不一致时拒绝复用。编辑源数据后运行 full。

页面身份用实际参考匹配，入场与内容展开从录像活动识别；Morph 到位由对象轮廓及真实停稳区间确定，页内漂移独立分析，原始扫描提示保留。相同页面、遮挡、无可靠轮廓的 Morph 保持待检查。无需针对五页示例手填页码、色值、裁剪或阶段时间。

时长建议可运行 `python scripts/advise_motion.py project.json --out advice.json`，根据位移、尺度与对象数量提出起点，不改源文件、不当作实播结论。科学示例已采用实测的 1400ms；其他项目仍看讲解目的和实播。

## 开始前

1. 找到本 SKILL.md 所在目录；下文脚本路径均相对该目录。
2. 阅读 [工作流程](references/workflow.md)。制作新页面时再读 [设计与运动](references/design-and-motion.md)；编辑 JSON 时读 [数据格式](references/data-contract.md)。
3. Python 3.10+。核心依赖见 requirements-core.txt，完整依赖见 requirements.txt。实际页面检查另需 LibreOffice；动态采样需 Playwright 和 Chromium。视频端需 Node.js 20+ 与生成项目自己的 npm 依赖。
4. 先运行 `nmp.py doctor --for <任务>`，需要真实播放器时指定 --player 与源项目。缺少某项时按修复命令处理或完成其他独立工作，报告实际验证范围，不能把“生成了文件”写成“检查了放映”。

## 新建 / 重做

先为每页写一句它要让观众看懂的事，再决定视觉重点和动作。不要先选通用模板。

共用数据使用 assets/spec.schema.json。1920×1080 是默认设计坐标，字体大小也按这一坐标填写；PPT 中换算成可编辑的实际尺寸。

最小运行：
```bash
python scripts/doctor.py
python scripts/motion_ppt.py validate examples/minimal.json
python scripts/motion_ppt.py review examples/minimal.json --out output/review.json
python scripts/motion_ppt.py build examples/minimal.json --out output/deck.pptx
python scripts/motion_ppt.py preview examples/minimal.json --out output/preview --remotion
python scripts/motion_ppt.py check output/deck.pptx --out output/qa --render --import-check
```

手动报告保留 clicks。需要自动播放时，用 --auto 另导出一份：按 clicks 中约定的时间触发动画，设置自动翻页，末页停留。

完整六镜头示例：examples/demo.json。用 create_demo.py 可重新生成原创几何和粒子数据。

### 图表与科研流程

先读 [动作与科学图形模块](references/motion-library.md)。recipes.py 复用停稳漂移、固定几何的擦除入场和顺序淡入；figures.py 从输入数据生成可编辑柱状图、采样曲线、观测分布和流程示意。柱状图用单一原生擦除，不再靠中心缩放与位移补偿同步来固定柱底。

```bash
python scripts/build_demo.py --example science --video --target-player wps-desktop
```

五页示例使用明确标注的模拟数据，输入CSV可修改。数据域不能静默裁剪；柱状图保留零基线，比较坐标不移动，统计标注从原始观测计算。图形为原生形状，没有Excel图表工作簿；不能声称它会自动同步PPT内的数据修改。

### 按内容角色编排

静态对象可声明 role：title、body、data、visual、caption、label、decoration。body/data 用 reveal_group 指定同一次出现的语义单元，避免只按坐标猜顺序。

```bash
python scripts/motion_ppt.py choreograph project.json --mode click --fit-duration --out output/timed.json
python scripts/motion_ppt.py review output/timed.json --out output/review.json
```

已有动画保留，未编排对象才补入场；Morph 中同名主体不会重复入场。--fit-duration 为动画结束后留出停顿；实际讲解仍需按内容留阅读时间。竖版示例见 examples/roles-portrait.json。

## 给现有 PPT 加动画

优先使用 [现有 PPT 方案与保留规则](references/existing-ppt.md)：

```bash
python scripts/nmp.py plan input.pptx --out output/plan
# 查看实际幻灯片和 plan-review.html，核对并编辑 plan.json 的分组
python scripts/nmp.py enhance input.pptx --plan output/plan/plan.json --out output/enhanced.pptx
```

plan 是布局辅助草案，不声称理解业务语义。代理可在已授权任务内查看实际页面、修订分组并继续，不必另行请求执行许可。标题、脚注和不确定对象默认静态，原生组不拆开；新增动作为整体淡入。方案绑定源 PPT 的 SHA，源文件改变后须重新生成。增强只修改目标页的 p:timing，逐成员核对其他 ZIP 内容与目标页非时序 XML；已有动画整页按字节保留。

```bash
python scripts/motion_ppt.py inspect input.pptx --out output/inventory.json
python scripts/motion_ppt.py enhance input.pptx --plan plan.json --out output/enhanced.pptx
python scripts/motion_ppt.py check output/enhanced.pptx --out output/qa --allow-images --render
```

计划格式：
```json
{"slides":[{"slide":1,"groups":[[4,5],[6,7]]}]}
```

数字是 inspect 返回的顶层对象 id。每个组对应一次点击，组内错开 100ms。先按论点、图表及其注释等语义单元分组，避免逐行点击。

不提供 plan 时，脚本按字号和坐标估计标题与阅读顺序，默认分成两次点击。这只是便捷起点。已有动画的页面默认跳过；确认需要替换的页面可在副本上用 --replace-animation。原有图片可以保留；不新增视频或 GIF 来代替原生动画。

## 共用数据预览与 Remotion

```bash
python scripts/motion_ppt.py preview project.json --out output/preview --remotion
python -m http.server 3020 --directory output/preview
```

打开 /preview.html。预览由对象和时间数据重建，不是 PowerPoint 录屏。

Remotion 项目在 output/preview/remotion：安装其 package.json 的依赖，npm run studio。已注册全片与各场景，所有运动按 useCurrentFrame() 求值，未使用 CSS 时间动画。编辑源 JSON 后重新生成项目；它是数据驱动项目，Studio 不会把修改自动写回 JSON。

用户要求视频交付时再运行 npm run render。系统 Chromium 路径可用 Remotion 的 --browser-executable 参数替换。

## 真实播放器检查

失败/待检原因可用 `python scripts/nmp.py diagnose <验收运行> --out output/diagnosis` 生成独立解释。新验收报告也会自动链接问题列表。区分当前不支持、未观察到、采集缺口和测得异常；有实际时间才提供异常跳转，页面上下文明确另标。解释不修改原始 verdict，也不通过放宽阈值消除待检。见 [验收诊断](references/diagnostics.md)。

WPS Linux 的官方包安装、首次启动、环境隔离与实播入口已经在 11.1.0.11723.XA 实测。按 [WPS 实播](references/wps-playback.md) 执行 `install_wps.py` → `prepare_wps.py` → `record_wps.py`；点击版、自动版分别录制，再运行对象与原生 Morph 检查。原生 Morph 的隔离诊断必须没有对象动画，并从实心中间姿态排除淡切。不要将本次 Linux 结论扩大到其他版本。

`accept_project.py` 保留 Impress 为默认后端；WPS 已接入主入口，显式 `--target-player wps-desktop --wps-root ... --wps-profile ...` 即选择真实 WPS。

目标 WPS / PowerPoint 可用时，优先用它实际放映。Linux 没有图形桌面时，可以安装 GUI Impress 与 Xvfb，用 record_desktop.py 放映并捕获屏幕。它复制原文件到独立目录，以只读方式打开；记录输入动作、播放器版本、源文件与录像校验值，最后关闭独立显示器。安装和录制顺序执行，不在播放器运行时重装其文件。

```bash
python scripts/install_desktop_player.py --tools-root "$HOME/.local/share/native-motion-ppt/desktop"
python scripts/record_desktop.py output/science/wps-bar-retest-auto.pptx --tools-root "$HOME/.local/share/native-motion-ppt/desktop" --out output/native-playback --seconds 9
```

安装器用于 Debian amd64，把签名仓库的软件包展开到指定目录，不改系统包；其他系统用自己的 GUI 播放器安装方式。录屏完成后运行check_native_motion.py，逐帧扫描活动与稳定区间，追踪柱形和独立几何主体，定位跳变、回弹及停顿；交互式曲线可跳到录像对应时间。查看真实帧后再写审阅结论。范围与阈值见[实播运动分析](references/playback-motion.md)。check_desktop_bars.py继续提供指定数据柱的窄条像素检查，调用见[实机放映核对](references/desktop-playback.md)。

采集设置60fps不代表播放器每秒重绘60次；保留实际录像的帧数、平均帧率和时间戳。其他播放器的录屏只能证明其自身结果。目标平台的用户反馈另记，不能由 Impress 通过推定 WPS / PowerPoint 通过。

## 运动规则

- 内容出现顺序跟随讲解逻辑；普通页面优先 1–3 次点击。
- 同一主体跨页变化，用稳定 id 和 Morph；新主体用自然的入场或淡切。
- 给动作留停顿：主要内容到位后，至少留出能读完的时间。
- 逐字效果用于短标题；正文按句子或语义块出现。
- 漂浮、呼吸、旋转只给少量背景或主视觉；数据和正文通常保持稳定。
- 粒子、纵深和雕塑用于确有作用的重点页，数量由实际流畅度决定。
- 先调路径、时长、缓动和动作关系，再增加效果。详见设计参考。

## 每次交付前

1. validate：解决结构错误、字体替换、缺字和文字尺寸警告。review：检查文本框重叠、对比度、画布边界、被截断的动画和停留时间。
2. check：检查 ZIP/XML、对象与时序 ID、动画目标、图片/媒体数量。
3. --render：渲染全部实际页面，检查漏字、文字越界、字体、主体位置和留白；可解析的未旋转顶层文字还检查真实字形是否溢出文本框。
4. --import-check：记录 Impress 是否保留路径、旋转缩放和逐字动作。
5. 主体连续运动时运行 check_motion.py，对位置、尺度和切换边界做逐帧检查；再运行 check_preview.py，按真实动作起止、转场中点和末尾停留采样；查看拼图，检查可见文字边界、无效几何及异常。
6. 在用户指定的 WPS / PowerPoint 桌面版本完整放映，检查 Morph、触发顺序、字距、循环和翻页。按 [实机放映核对](references/desktop-playback.md)录屏并记录版本、PPTX 校验值及结果。没有该环境时按 [验证范围](references/qa-and-compatibility.md)如实记录，目标播放器状态保持待复测。
7. 交付 PPTX、源 JSON、生成代码、静态 PDF/关键帧和 QA 结果；用户要求视频时附 MP4，并注明是设计预演还是实机放映录屏。附依赖与字体说明。

用户实测反馈见 [反馈记录](references/field-feedback.md)；已复现的问题与预防规则在 tests/fixtures/known-cases.json。只记录用户明确提供的播放器与设备，不推定跨平台兼容。

```bash
python scripts/check_preview.py --url http://localhost:3020/preview.html --out output/qa/dynamic
```

具体平台与未覆盖对象见 [实测兼容范围](references/compatibility-matrix.md)。

## 能力边界

v1.8.0 支持文字、矩形与圆角、圆/椭圆、线、多边形、M/L/C/Q/Z 原生复合曲线、组合对象；淡入淡出、整对象擦除入场/退场、直线和多段三次曲线路径、旋转、缩放、短标题逐字、重复与自动往返；淡切、推移、擦除、Morph。包含现成 PPT 方案与保留校验、分层依赖诊断、项目入口、Linux GUI放映录屏、真录像检查与可追溯验收。

安装已有版本时使用 install_skill.py --workspace <目录> --upgrade。只更新安装记录中未被修改的文件，自动保存旧版；发现用户修改时保留原文件并停止覆盖。没有记录的旧版本先核对来源并保存副本。

组合内部子对象保持静态，动画加给父组合。SVG 中任意滤镜、遮罩、复杂形变、网页交互、真实 GLB 模型和音频不在本导出器范围；需要时明确设计替代方案或扩展后端。复杂三维外观可由原创投影面片构成，但仍是二维原生形状。

不要声称 MP4 无损转成原生 PPT，也不要声称浏览器或 LibreOffice 已证明 WPS / Microsoft PowerPoint 的实际放映行为。共用数据不能保证不同播放器逐帧一致。

