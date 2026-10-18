# v1.6.0 一键制作与验收

先确定内容、版式和运动目的，再由入口执行与留证。设计视频、原生文件、真实放映及人工视觉判断分别记录。

```bash
python scripts/accept_project.py examples/scientific.json --out output/runs --profile science --target-player wps-desktop --desktop-tools-root "$HOME/.local/share/native-motion-ppt/desktop" --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile"
```

`--target-player` 真正选择播放器。WPS 缺失时保留待检查，不用 Impress 代替。PowerPoint 当前没有真实后端；Linux 结论不扩大到 Windows。WPS 安装、首次 GUI 准备见 [WPS 实播](wps-playback.md)。profile 是外部私人目录，不进交付。

## 三种运行

- full：源审阅、浏览器设计检查、设计 MP4、点击/自动原生 PPT、实际静态参考、目标双录制、必要的隔离 Morph、阶段与对象检查、报告和工程包。
- record：`--resume <v1.6运行> --mode record`，从已验证输入/PPT/参考创建新目录，仅重录和检查；不再渲染设计视频、重建 PPT。仍需播放器参数。
- check：`--resume <v1.6运行> --mode check`，创建新目录复用同一真实录像，只运行分析与报告，不启动播放器。无需 WPS/GUI 安装参数。

快路径核对父运行的 ZIP/清单与输入绑定，记录 lineage；不覆盖父运行。源 JSON 改变时拒绝旧证据，必须 full。默认新目录是父运行同级；可用 --out/--run-name 指定。失败日志与旧录像保留。

```bash
python scripts/accept_project.py --resume output/runs/previous --mode record --desktop-tools-root "$HOME/.local/share/native-motion-ppt/desktop" --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile"
python scripts/accept_project.py --resume output/runs/previous --mode check
```

## 实际阶段

独立 Office 参考与真实缩略帧识别页序、稳定匹配和画面活动，不依赖固定页码位置。自动版只发 F5，页序必须在像素中出现。相同/过于接近的页面可能无法独立判断，保持待检查。

自动首屏使用与实际 F5 输入相交或在其后的首段画面活动建立扫描窗口，避免最后一组柱展开掩盖早期主体运动。phase-audit v2 绑定采集证据 SHA 和输入时间；录屏 PTS 与输入时钟可能有启动偏差，该窗口是像素分析范围，不是播放器内部的精确入场时间。没有可靠活动时保持待检查。

Morph 用同名主体的源静态框与颜色限定搜索区域，不调用源动画求值器。轮廓来自录像像素，实测到位平台把 incoming Morph 与页内漂移分开；原始完整扫描的状态和提示保留。无可靠色轮廓、透明、遮挡、文字及复杂形变需复核，不能仅凭 XML 通过。主文件轮廓检查和没有对象动画的隔离诊断都满足，才允许相关 Morph 自动通过。

v1.7 的独立矩形/椭圆按实际颜色连通区域测量，避免已消失的旧页面文字/网格框截断新位置的主体；组合主体仍保留排除框和更保守的范围。检测命令返回失败时，原始报告的失败状态也写入正式检查项，保留原始错误和日志；不能用报告整理把失败变成通过。

qa/manual 和 qa/automatic 分别保存 phases、motion、playback；observed-phases.json 给出入场/展开复合活动、Morph、页内运动与稳定停留候选。稳定候选不证明观众读完或理解，讲解质量需审阅。

## 自动、审阅、最终状态

每项记录 automatic_status、reviewed_status、status。自动原始结果不被人工覆盖；审阅只增加绑定当前证据的独立结论。自动失败需修复和复测，不能用文字改为通过；另一播放器不能被审阅成目标播放器。

视觉审阅在 v1.6.0 为必需项。因此技术自动检查可以通过，而最终验收仍待审。查看两份真实关键帧与录像后：

```bash
python scripts/finalize_acceptance.py <运行目录> --visual-review-note "具体查看了哪些画面、对象及动作，结论是什么"
```

该便捷命令同时绑定点击/自动两份录像和两份真实联系表。复杂复核使用 `--review-file`：

```json
{
  "reviewer": "审阅者",
  "recordings": {"manual": "本次录像SHA256", "automatic": "本次自动录像SHA256"},
  "reviews": [{"check_id": "visual-review", "status": "passed", "note": "具体审阅结论", "evidence": ["qa/manual/playback/native-contact.jpg", "qa/automatic/playback/native-contact.jpg"]}]
}
```

外部阶段还保存 scripts/assets 的实现指纹与源码快照，检测器迭代后可追溯当时算法。

reviews/ 中的不可变记录包含原始状态、最终审阅状态、记录时间及所有证据哈希。替换录像、帧或机器测量后旧审阅失效。check-only 的新分析默认重新审阅，不自动套用父运行的人工作品结论。

## 交付与退出码

报告含实际播放器、点击/自动两个视频、自动与审阅列、对象曲线、真实关键帧、阶段与范围。ZIP 含可编辑源与完整 skill、PPT、设计视频及真实录像；排除播放器、安装包、私人配置、input 副本、缓存、node_modules。

```bash
python scripts/verify_acceptance.py <运行目录>
```

默认 0 表示流程执行完成；1 为执行/检查失败；`--strict` 下必需项待检查返回 2。未完成视觉审阅时不得宣布最终通过。采集 fps 与播放器重绘率分别记载，不插帧制造流畅结论。
