# WPS Linux 真实实播

2026-10-15（Asia/Shanghai）在 Debian 13 amd64、WPS Presentation GUI 11.1.0.11723 实测。官方包版本为 11.1.0.11723.XA，大小 318892996 字节，SHA-256 见 assets/wps-official-package.json。仅证明此 Linux 构建，不代表 Windows、中国版或最新版本。

## 安装与首次启动

先核对当前云环境网络策略，实测官方完整下载 URL。保留代理与 TLS 校验；禁止通过镜像或代理绕过被拒绝的域名。安装器仅展开到任务工具目录，检查 wpp 与实际 Qt XCB 插件的依赖。

```bash
python scripts/install_wps.py --root "$HOME/.local/share/native-motion-ppt/wps"
python scripts/install_desktop_player.py --tools-root "$HOME/.local/share/native-motion-ppt/desktop"
```

只需依赖工具时，后一个命令同时安装的 Impress 不会成为 WPS 证据。未发现缺失库时不要另找不同 ABI 的库替代 vendor Kso Qt。安装、录制、分析顺序执行，避免重装正在使用的文件，也避免重负载分析干扰采集。

完整 Noto Sans/Serif CJK SC 需事先安装。实测独立 XDG_DATA_HOME 会改变 fontconfig 的用户字体搜索位置：把附带的 SpaceGrotesk-SemiBold.ttf 放入 `~/.fonts/`（本次已验证），或实际配置使用的 `XDG_DATA_HOME/fonts/`，刷新 fc-cache、重启 WPS，查看标题、页码和数字。只看当前 shell 的 fc-match 不够。公式字体警告与本文件用字分开记录；不能从弹窗推断文件内缺字。

```bash
mkdir -p ~/.fonts
cp assets/fonts/SpaceGrotesk-SemiBold.ttf ~/.fonts/
fc-cache -f ~/.fonts
python scripts/prepare_wps.py /path/deck.pptx --tools-root "$HOME/.local/share/native-motion-ppt/desktop" --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile" --out output/wps-first-launch --seconds 120
```

prepare_wps.py 保持真实私有 X11 GUI，session.json 记录 DISPLAY、xdotool 和工具库路径，latest.png 可随时查看。用这些参数在另一终端运行 xdotool 处理已看清的许可、关联或警告对话框；不自动点击未知付费或登录选项。用户已有安装授权时不重复询问。保存首次窗口与 About 的真实截图。结束此准备进程后再录屏；不并行使用同一配置。WPS 私人配置必须位于交付目录外，不进 Git/ZIP。

## v1.6 主入口

优先使用 accept_project.py 的 WPS 后端，完整调用见 acceptance.md。它串行完成点击/自动录制、隔离诊断与分析，不再需要针对五页写专项脚本。下面的 record_wps.py 仍可单独诊断 GUI。

## 分别录制点击版和自动版

```bash
python scripts/record_wps.py /path/deck.pptx --tools-root "$HOME/.local/share/native-motion-ppt/desktop" --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile" --out output/wps-click --seconds 44.5 --show-after 1 --click-at 4.25 --click-at 9.5 --click-at 12.75 --click-at 18.5 --click-at 26.5 --click-at 34.5 --click-at 37.75 --click-at 39.1
python scripts/record_wps.py /path/deck-auto.pptx --tools-root "$HOME/.local/share/native-motion-ppt/desktop" --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile" --out output/wps-auto --seconds 38 --show-after 1
```

这些时间只对应本次五页示例。其他项目先根据内容安排，并在录像中复核。查看 editor-before-show.png、show-start.png 和真实到位帧，确认没有对话框遮挡。录屏默认状态为 recorded_pending_visual_review，保存这一原始记录，另写绑定录像 SHA 的审阅结论。

WPS 自带的旧 libstdc++ 仅放入播放器进程环境，不能污染 FFmpeg。record_wps.py 已隔离两者。请求 60fps 不保证播放器重绘 60 次；记录实际帧数、平均帧率与 PTS，不插帧。失败目录不复用，保留错误日志并选新输出目录。

对象分析继续使用 check_native_motion.py。自动版没有翻页按键，以真实画面观察页面身份和转场开始；页码可能到 Morph 中途才更新。上一页主体漂移的窗口须在实际转场前截止，Morph 单独检查；不要把阅读停顿和随后的跨页运动误报成页内卡顿。

## 原生 Morph

```bash
python scripts/motion_ppt.py build examples/wps-morph-diagnostic.json --out output/morph.pptx
python scripts/record_wps.py output/morph.pptx --tools-root "$HOME/.local/share/native-motion-ppt/desktop" --wps-root "$HOME/.local/share/native-motion-ppt/wps" --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile" --out output/morph-capture --seconds 9 --show-after 1 --click-at 4
python scripts/check_native_morph.py output/morph-capture/player-recording.mp4 --pptx output/morph.pptx --evidence output/morph-capture/playback-evidence.json --start 3 --end 7 --out output/morph-audit.json
```

隔离文件必须是两页同名 `!!` 纯色矩形，无对象动画，只靠原生 Morph 转场。检查器从实际录像像素与 PTS 测量实心中间姿态，拒绝淡切双影、静止、过期证据及对象路径冒充。它只支持示例的从左向右位置与尺度变化，阈值不是普遍流畅度标准。本次复录为 41 个不同实心中间姿态，实际过渡约 1.58 秒。

本次五页主文件的 0.8 秒 Morph 实录有 15 个中间姿态、最大中心步长约 64px；另存 1.4 秒原生 Morph 修正版并重新录制。不要仅改检查阈值来宣布更平滑。

主文件仍须检查真实跨页主体轨迹。复杂组合的检查范围、停留与采集误差单独说明；不能凭 Morph XML 或隔离矩形通过就笼统宣布所有效果兼容。test_wps_morph.py 的合成单元测试只检验检测器拒绝误报的能力，永远不作为播放器证据。
