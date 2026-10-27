# 声波科普：先视频，后 PPT

这是独立原创科普动画成片的源工程，不是 WPS 录屏。参考与事实来源在 src/story.json，中文脚本和旁白均为本项目重新制作，未使用参考视频片段。所有场景单独注册，可在 Studio 打开；粒子阵列由同一个模型模板控制。

```bash
npm ci
npm run studio
npm run render -- --browser-executable=/path/to/chromium
```

默认画面 1920×1080、30fps、74秒。public/audio 为合成中文旁白和本项目生成的220/440Hz纯音。外部TTS模型与播放器不打包。字幕是 Caption JSON 与 SRT，按实际音频长度分句近似对齐，未做词级强制对齐。

先完成视频与物理/音频/画面检查，封存 VIDEO_LOCK.json，再制作对应 PPT。PPT 是使用已知对象和分镜重新制作的原生教学版本，不声称 MP4 无损转为原生动画。
