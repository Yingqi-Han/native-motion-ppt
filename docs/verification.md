# 验证与实播证据

2026-10-15，v1.6.0 在 Debian amd64 的国际版 WPS Presentation Linux **11.1.0.11723.XA** 上完成两套项目的真实点击与自动放映。v1.6.1 是独立仓库和分发整理；原生导出、桌面采集、运动检测与 assets 对应文件和实测版本逐字节一致，见 [引擎来源清单](engine-provenance.json)。包版本读取和分发脚本另行检查。

| 项目 | 五页科学示例 | 独立两页回归 |
|---|---|---|
| 画布与采集 | 1920×1080，60fps | 1280×720，30fps |
| 内容 | 三柱、曲线、分布、流程主体 | 两柱、独立蓝色主体，无固定页码 |
| 最终检查 | 24 通过，0 失败，0 待检查 | 22 通过，0 失败，0 待检查 |
| 点击 / 自动录像 | 44.50 / 37.85 秒 | 16.90 / 16.37 秒 |
| 柱底最大偏差 | 点击 0px，自动 1px | 点击 / 自动 0px |
| 主体 Morph | 点击 61、自动 62 种中间轮廓 | 点击 / 自动均有连续中间轮廓 |

自动版操作仅含 F5，后续顺序由实际画面识别。原生 Morph 还使用同构建的无对象动画诊断实录排除淡切回退。采集帧率不等同于播放器重绘率。

## 查看原始实录摘录

- 五页主示例：[点击录像](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/science-check/player-recording.mp4) / [自动录像](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/science-check/player-recording-auto.mp4) / [点击 PPT](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/science-check/deck.pptx) / [自动 PPT](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/science-check/deck-auto.pptx)。
- 两页独立项目：[点击录像](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/generic-record/player-recording.mp4) / [自动录像](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/generic-record/player-recording-auto.mp4) / [点击 PPT](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/generic-record/deck.pptx) / [自动 PPT](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/generic-record/deck-auto.pptx)。
- 实际采集证据、acceptance 原件与关键帧见 [showcase](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/README.md)，逐文件哈希见 [摘录清单](https://github.com/Yingqi-Han/native-motion-ppt/blob/main/showcase/manifest.json)。

showcase 是便于浏览的原样摘录，没有复制全部 QA 依赖，不能作为完整运行目录执行 verify_acceptance.py。完整 HTML 交互报告、对象曲线、诊断、审阅记录、阶段实现快照、日志和独立可校验工程见 Release 附件 [wps-v1.6.0-delivery.zip](https://github.com/Yingqi-Han/native-motion-ppt/releases/download/v1.6.1/wps-v1.6.0-delivery.zip)。上传后的服务器 SHA 与原件一致：`218b5bf942f80c2ffd59f429814641b4edd71c5ea2e681456bf07a952d0c65b3`。所有摘录 SHA 与该完整证据中的同名文件保持一致。

代码设计视频为 Remotion 预演；此处展示的四份录像均为真实 WPS GUI 屏幕采集。录像保留启动编辑器、短暂黑帧或字体提示，放映阶段另行检查。原始采集 JSON 中的 pending 字段反映采集时状态；最终 automatic/review/final 状态在 acceptance.json 分别记录。

## 范围与限制

仅认证本次固定 Linux WPS 构建和文件，Windows WPS、Microsoft PowerPoint 尚无实机结果。自动轮廓检查支持可测独立色形状及部分组合；文本形变、透明、任意旋转、遮挡及相同页面歧义可能保留待检查。

v1.6.0 检测器开发曾误吸收中性背景箭头；推荐 science-check 是修正后的同录像复算结果，中间开发结果没有套用最终结论。五页 PPT 保留真实复录过的 1400ms Morph，没有把建议时长当作实测。

源码与打包回归见 [QA_REPORT.md](../QA_REPORT.md)。CI 检查不运行 WPS，也不能扩展这些实播结论。
