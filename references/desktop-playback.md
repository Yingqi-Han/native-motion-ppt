# 实机放映核对

设计视频先确定版式与节奏，原生 PPT 随后实现。最后一关是用户实际使用的桌面播放器。代码生成的 MP4、浏览器测量和 Office 导入都不能替代这一关。

## 录制条件

记录系统、WPS / PowerPoint 的完整版本、显示缩放、屏幕分辨率和录制帧率，并保存实际测试 PPTX 的 SHA-256。打开该文件的放映模式，不使用浏览器预览或静态 PDF 代替。

可用免费 OBS 的窗口或显示器采集，以 1920×1080、60fps 录制；记录实际设置。先录一次短片确认没有掉帧。硬件或播放器达不到60fps时，如实保留录制参数，不靠补帧生成所谓实测流畅视频。

自动版用于核对预定时序，手动版用于核对点击。手动点击时间可以不同；比较的是动作顺序、方向、边界与到位状态，不强求全片逐帧对齐。

## 柱状图复测

1. 从第1页开始放映，保留展开前的画面。
2. 手动版在标题到位后点击一次；自动版等待自行展开。
3. 录完整三根柱子的展开，再保留至少两秒到位画面。
4. 查看慢放与关键帧：柱底始终接触零线，展开边向上前进，没有过零线、回弹、突然消失或反向擦除；数值标签在各柱到位后出现。
5. 检查下一页切换，随后完整播放五页，确认触发与 Morph。单页通过不能代表整份文件通过。

录屏在裁切与缩放后会改变像素坐标。若要测量边界，先由静止轴线标定比例，再追踪柱子的下边缘；抗锯齿和压缩导致的1像素变化不能直接解释为几何位移。读视频实际时间戳，不根据设计源时间假装得到播放器进度。

## 留下可追溯的证据

把真实录屏另命名为 wps-player-recording.mp4 或 powerpoint-player-recording.mp4，保留原始录屏。记录测试文件校验值、播放器版本、日期、点击方式、实际视频参数、检查区间、结论与已知问题。修改 PPT 后重新录制，不沿用旧文件的通过结论。

delivery-provenance.json 中 target_desktop_playback 只有在有实际测试或明确用户反馈后才能填写相应结果。两者均没有时，status 为 pending_retest，recording 为 null。用户报告通过时可记 user_reported_pass，并保留原话、日期及明确的平台信息；没有用户录屏则 recording 仍为 null。不能凭口头反馈生成不存在的录屏，也不能将其他播放器录像填成目标平台录像。

交付时分别标明代码设计预演、可编辑 PPT 和真实录屏。若实机效果与设计不同，先调整原生实现，再同步更新源数据和设计视频；不要只修视频掩盖 PPT 的问题。

## Linux 无桌面环境

install_desktop_player.py 支持 Debian amd64，将签名 Debian 软件包放到指定工具目录。安装完成后再录制，不在放映时重装软件。保留环境原有的网络策略和代理；官方站点被拦截时使用可访问的其他播放器，明确它的验证范围。

```bash
python scripts/install_desktop_player.py --tools-root "$HOME/.local/share/native-motion-ppt/desktop"
python scripts/record_desktop.py output/science/wps-bar-retest-auto.pptx --tools-root "$HOME/.local/share/native-motion-ppt/desktop" --out output/native-playback --seconds 9
```

record_desktop.py 新建私有 Xvfb 显示器和独立用户配置，以只读方式打开原文件的副本，F5 开始放映，FFmpeg 捕获该显示器。录制前后核对源文件和副本校验值，保存录像来源、版本、动作与视频参数，最后退出。其他 Linux 已有 GUI LibreOffice、Xvfb、openbox、xdotool、FFmpeg 时可以省略 --tools-root。不会把浏览器或 PDF 画面写入录像。

手动版可通过多个 --click-at 指定录像开始后的按键时间。以下是五页科学示例的实际验证安排；它有意留出阅读停顿，长度不强求与30秒设计视频一致。

```bash
python scripts/record_desktop.py output/science/scientific.pptx --tools-root "$HOME/.local/share/native-motion-ppt/desktop" --out output/native-science --seconds 37 --click-at 2.5 --click-at 8 --click-at 9.5 --click-at 16 --click-at 22 --click-at 28 --click-at 29.5 --click-at 31.5
```

在确认录屏的入场区间和到位状态后，可对数据柱检查：

```bash
python scripts/check_desktop_bars.py output/native-science/player-recording.mp4 --pptx output/science/scientific.pptx --evidence output/native-science/playback-evidence.json --out output/native-science/qa --start 2.2 --end 7.8 --hold 7
```

该脚本根据录像实际时间戳解码，以到位帧标定柱底，检查色块下边和展开边的反向移动。时间参数须来自这次真实放映；不照搬到启动速度不同的录像。只检查第1页、命名数据柱、纯色填充和同画幅录屏；有裁切、字母盒或复杂图案时需另做标定。它要求捕获多个展开位置，防止把静态截图当作动画通过。

采集帧率与播放器重绘率分开；文件实际平均帧率低于60时如实记录，不通过插帧补足。录屏完成的初始状态为 recorded_pending_visual_review，查看真实帧后补上检查结果。
