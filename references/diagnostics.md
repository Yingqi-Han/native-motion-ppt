# 验收诊断：解释原始结果

```bash
python scripts/nmp.py diagnose output/runs/previous --out output/diagnosis
```

适用于 v1.6+ 的双录制验收结构。帮助与诊断只用 Python 标准库；不要求播放器、浏览器或科学计算依赖。默认输出是旧运行的同级新目录，禁止将独立诊断写入原运行。新 full / record / check 运行在最终报告中自动加入 qa/diagnostics 链接。

浏览器视频定位使用支持 HTTP 字节范围的本地报告服务器。完整运行用 `python scripts/serve_report.py <运行目录>` 后点击诊断链接；独立诊断的 CLI 结果提供 serve_argv，或显式执行 `python scripts/serve_report.py <共同项目父目录> --entry diagnosis/diagnostics.html`。入口必须在所服务目录内；本地服务只监听 127.0.0.1。普通静态服务器的媒体定位能力需要另行确认。

diagnostics.json 保留原始 acceptance_status / automatic_acceptance_status、每项的 failed / pending、源报告路径及 SHA。diagnostic_integrity 表示解释所依赖的文件绑定是否一致，不是播放通过状态。原始报告、录像或源文件替换后，旧解释失效。verifier 会核对自动交付中的解释依赖。

- unsupported：现有算法不覆盖旋转、透明、复杂几何或无独立色轮廓等。重跑同一算法不会扩大覆盖；需要新的追踪方法或绑定实际帧的独立审阅。
- not_observed：可见帧、首屏活动、运动姿态或到位平台不足。先确认录屏和动画是否完整；不能用静态 XML 或稳定画面证明运动。
- capture：采集或可见性缺口。核对负载、遮挡和原始帧，必要时新录；不能据此直接认定播放器跳变。
- measured_issue：原始扫描测得的柱底偏移、回弹、跳变或 Morph 轮廓异常。保留阈值、帧号与原始状态，回看是否受遮挡影响；失败必须修复并复测。
- review：保留测量给出的具体建议，按真实片段判断；失败项修复并重测，不能用文字改为通过。
- evidence：录像/PPT/输入/源文件绑定或正式状态与原始测量矛盾。恢复原件或新建验收，不能手改校验值。

有实际异常 timestamp/frame_index 时才提供精确跳转。只有已识别页面的稳定区间时，按钮标为“页面上下文（非异常时刻）”；完全没有时序证据就不生成定位按钮。缺少对象或动画并不自动表示其失败。

页面身份/到位未建立时，关键帧提取仍可输出真实录像的上下文帧，并标记 context_only_not_page_identity。上下文抽帧不证明到位、运动或页序，不会消除原待检项，也不再因缺少 held-page 报告使流程额外失败。

旧版本文字 reason 可提供尽力解释，并标为 legacy_reason_or_check_state；新测量提供稳定 reason_code。诊断只增加解释，不改运动阈值、像素数据、审阅结果或原始验收。
