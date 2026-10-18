# 验证与实播证据

## v1.7.0：产品介绍与项目进展

2026-10-18，两套新示例在固定国际版 Linux WPS **11.1.0.11723.XA** 完成真实点击/自动放映，并用本版检测器复验。画布 1600×900，采集 30fps；采集帧率不代表播放器重绘率。每套最终 **22 通过、0 失败、0 待检查**，技术自动结果与视觉审阅分别保留。

| 项目 | 产品介绍 | 项目进展 |
|---|---|---|
| 页数 / 柱数 | 3 / 2 | 3 / 3 |
| 点击 / 自动录像 | 28.30 / 26.30 秒 | 28.30 / 26.30 秒 |
| 柱底最大偏差（点击 / 自动） | 1 / 1px | 0 / 0px |
| Morph 中间轮廓（点击 / 自动） | 66 / 66 | 73 / 76 |
| Morph 最大中心步长（点击 / 自动） | 55.5 / 55.5px | 56 / 57px |

每套都检查柱展开、首屏主体运动、跨页 Morph 与到位后有限漂移；自动版仅输入 F5，三页顺序来自实际像素。主文件 Morph 加上无对象动画的隔离实录诊断共同验收。三页的真实联系表、完整页面和 Morph 关键帧经视觉审阅，绑定两份录像及实际帧 SHA。

- 产品：[点击实录](../showcase/v1.7/product/player-recording.mp4) / [自动实录](../showcase/v1.7/product/player-recording-auto.mp4) / [点击 PPT](../showcase/v1.7/product/deck.pptx) / [自动 PPT](../showcase/v1.7/product/deck-auto.pptx) / [最终报告](../showcase/v1.7/product/REPORT.md)。
- 进展：[点击实录](../showcase/v1.7/progress/player-recording.mp4) / [自动实录](../showcase/v1.7/progress/player-recording-auto.mp4) / [点击 PPT](../showcase/v1.7/progress/deck.pptx) / [自动 PPT](../showcase/v1.7/progress/deck-auto.pptx) / [最终报告](../showcase/v1.7/progress/REPORT.md)。
- [机器摘要及源/PPT/录像 SHA](verification-v1.7.json) / [摘录逐文件清单](../showcase/v1.7/manifest.json)。摘录缺少完整 QA 依赖，完整校验应解压 Release 工程。

完整工程：[wps-v1.7.0-delivery.zip](https://github.com/Yingqi-Han/native-motion-ppt/releases/download/v1.7.0/wps-v1.7.0-delivery.zip)，70,532,193 字节，SHA-256 `31998859350969e143cd7edb3a90ba1c69f3df4ae9689664c886ed0e9bdd44b3`。内含 product / progress 的独立 acceptance-delivery.zip、完整源/PPT/设计视频/实录/检查/审阅/实现快照，以及本轮回归原件。解压内层 ZIP 后，用其 project/scripts/verify_acceptance.py 检查运行目录。

本轮保留了两类开发中间结果：产品的首屏晚展开使旧窗口漏扫早期主体；进展的旧页文字/网格遮罩把实际 180px 高圆形截成 70px，引发双影误报。前者复用原始录像在新运行检查；后者既对原始录像独立重算阶段（失败 → 通过，录像 SHA 相同），又做完整新录制验收。未改配色、源数据、录像或放宽阈值。原先失败的报告仍是失败原件，不能作为最终通过工程；失败状态传播另有行为回归。

启动编辑器提示、短暂黑/暗帧保留，放映画面单独检查。示例数据与流程均为模拟内容。此处不认证 Windows WPS、Microsoft PowerPoint，复杂文本形变、透明/旋转/遮挡与同色组合仍可能待检查。CLI 的 Linux/Windows CI 只认证核心工作流，详见 [发布检查](../QA_REPORT.md)。历史 v1.6.1 引擎来源清单不代表本轮实现。

---

# 历史：v1.6.0 / v1.6.1

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
