# 连续 Morph 与全幅聚焦：真实 WPS 样片

源码提交 `53b9afc` 增加 `nmp.py new --template cinematic`。三页依次为扇形聚拢、同名原生形状重组为柱形、相同六项模拟数据展开至全幅并突出 88。这里保存实际国际 Linux WPS 11.1.0.11723.XA 的证据摘录，不能代表 Windows WPS / PowerPoint。

[22 秒真实 WPS 节选](preview-wps.mp4) · [自动 PPT](deck-auto.pptx) · [手动 PPT](deck.pptx) · [源 JSON](source.json)

视频从原始自动录像的 1.2 秒开始，保留到 23.2 秒，只裁掉启动编辑器及末尾部分停留并重编码，无变速或插帧。原片：[自动](automatic/player-recording.mp4)、[手动](manual/player-recording.mp4)。自动版只发送 F5；手动版以空格翻页。

## 检查范围

完整运行的最终状态是 **19 项通过、0 项失败、3 项待检**。[原始检查状态](checks/acceptance-original-paths.json)与[简表](checks/summary.json)分别保留。六个到位页面对照通过，自动翻页通过；两份真实录像的联系表和两次转场中段已人工查看，视觉审阅通过。

主文件的复杂渐变形状、文字 Morph 轨迹不在通用自动检测器的完整覆盖范围，因此手动阶段、自动阶段、主文件 Morph 三项继续待检；不宣传为全项通过。另一次[隔离原生 Morph 诊断](diagnostic/morph-audit.json)通过，测得 40 个不同实心中间姿态，只证明该隔离矩形的位置与尺度变化。

[自动实帧联系表](automatic/contact.jpg) · [手动实帧联系表](manual/contact.jpg) · [自动转场中段 7.8 秒](automatic/frame-03.png)

## 已修复的遮挡

[第一版自动录像](rejected-v1/player-recording.mp4)在 7.8 秒出现不透明标签底色切到移动柱形的现象，已记录为视觉失败。[原帧](rejected-v1/automatic-7.8s.png)、PPT、源 JSON 和原始失败审阅都保留在 rejected-v1/。

修订去掉底色，改为缩短参考线以避开大号数字，再从头执行完整制作流程并重新录制两种放映。没有复用旧录像或放宽阈值。新的真实转场帧未再显示这类切口。

## 文件映射与复算边界

这是仓库证据摘录，不是完整验收工程；不能直接对本目录运行 verify_acceptance.py。原始证据和报告保留原有工作区路径及内容，不重写原始判定。对应关系：

| 完整运行路径 | 本摘录 |
| --- | --- |
| project.json | source.json |
| player-recording.mp4 | manual/player-recording.mp4 |
| player-recording-auto.mp4 | automatic/player-recording.mp4 |
| playback-evidence.json | manual/playback-evidence.json |
| playback-evidence-auto.json | automatic/playback-evidence.json |
| qa/cinematic-review/wps-preview.mp4 | preview-wps.mp4 |
| qa/cinematic-review/frames/{mode}/ | {mode}/；仅保留联系表、时间表及选定原帧 |

manifest.json 绑定每个摘录文件的 SHA。完整本地工程包另外交付，包括原始两路录屏、隔离诊断、源码、代码预演和全部报告。代码预演与 WPS 录屏的来源始终分开。

140 个 Python、11 个 Node 回归、核心依赖隔离 smoke 与源码包新安装校验通过。这些检查不是审美评分，也不扩展播放器兼容范围。
