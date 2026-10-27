# 声音科普：连续镜头与实测字幕修订

[观看66秒新版](sound-explainer-improved.mp4) · [旧版对照](previous/sound-explainer.mp4) · [自检报告](REPORT.md)

修复标记点切镜跳位、逐页进度重置、字幕估时/摘要回跳、粒子对比不足和试听提示缺失。

- 实际编码帧：两处切镜附近最大相邻帧位移1.94/2.27px，旧片107/119px；保留3px门槛。
- 15句旁白的采样片段与源音频最低相关系数约0.99995，窗口未检出时移；字幕取自独立合成句子的样本边界。
- 实际音轨220/440Hz听辨、粒子模型和编码参考对照通过。首轮修订3.31px失败记录在完整交付中保留。

[实际成片画面](encoded-review-final/contact.jpg) · [切镜连续帧](video-qa-final/edit/actual-cuts.jpg) · [旧片失败复现](before-edit-check/edit-quality.json)

[新版原生PPT](wps/deck.pptx) · [自动版](wps/deck-auto.pptx) · [真实WPS手动录像](wps/player-recording.mp4) · [自动录像](wps/player-recording-auto.mp4)

[视频编辑工程](video-v3/) · [镜头到PPT映射](ppt-final/video-to-ppt.json) · [问题与迭代记录](ISSUES_AND_REVISIONS.json)

主片是原创科普动画；WPS录像独立留证。这里是公开证据摘录，完整便携工程与原始QA在本轮ZIP中交付。播放器、外部模型、私人配置与node_modules均不上传。WPS完整状态和待复核范围见报告，不能从主片检查通过推定PPT全部自动通过。
