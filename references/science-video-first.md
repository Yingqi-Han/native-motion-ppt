# 从在线科普案例到原创视频，再到原生 PPT

用户明确说“先找例子做科普视频，视频做完再做 PPT”时，按这个顺序交付。先让内容和镜头讲清一个具体问题，再为课堂讲解调整节奏；不要先制作通用 PPT，再把放映录像当成用户要的原创视频。

## 已制作的例子：声音走了，空气也走了吗？

选择了 [University of Salford 的 Longitudinal Waves](https://salfordacoustics.co.uk/sound-waves/waves-transverse-introduction/longitudinal-waves) 教学页。它包含弹簧实验视频，以及 Dan Russell 用标记粒子区分局部往复与传播的示意。原理再核对 [Penn State 的波动教学页](https://www.acs.psu.edu/drussell/Demos/waves/wavemotion.html) 和 [UCLA Physics 的 Sound Waves](https://dbauer.physics.ucla.edu/5b/20-sound-waves/)。

借鉴的是观察方法：先盯住一个标记，再拉远看疏密变化。中文脚本、分镜、配色、图形、程序动画、字幕和音频重新制作，不使用参考作品的画面、配音或逐字翻译。

本次查阅范围为公开教学页文字、检索到的图示预览和来源链接。工具无法完整播放嵌入的 YouTube 片段或直接打开 GIF；不能声称逐帧看完原片或复刻了其全部镜头节奏。把访问范围记在项目研究说明中，后续能实际观看时再补具体镜头分析。

## 先核对科学表达

- 画面里的点代表小团空气的平均运动。真实分子的热运动未画出，不能把图示称为追踪单个分子的真实轨迹。
- 示例使用小振幅平面行波的示意模型，时间和位移均放大；没有模拟衰减、反射和二阶声流。压缩区对应位移空间梯度为负。
- 在同一种空气、同一温度的近似下比较 220 Hz 与 440 Hz，波速相同、波长成反比。20°C 空气取约 343 m/s，440 Hz 波长约 0.78 m。
- 画面慢放频率与真实可听频率分开标明。两段可听纯音实际使用 220/440 Hz，后面从编码后的成片中做 FFT 检查。

脚本与来源在 `examples/science-video/sound-story.json`，模型在 `scripts/native_motion/acoustics.py`，原创 Remotion 场景在 `assets/science-video/`。它是可重建的单个科普案例，不声称任意主题都能自动套用。

## 完成视频并封存

合成旁白使用独立环境中的 Sherpa ONNX / MeloTTS 中文模型，也可直接复用交付工程中的已生成音频。外部模型与环境放在工具目录，交付包保留生成音频、文本、来源和模型校验值。核心 PPT 导出依赖不增加 TTS 模型。

```bash
# 用独立 TTS Python 环境执行；模型下载来源见下方说明。
/path/to/tts-python scripts/synthesize_sound_narration.py \
  --story examples/science-video/sound-story.json \
  --model /path/to/vits-melo-tts-zh_en \
  --model-url https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-zh_en.tar.bz2 \
  --out output/sound-audio

python scripts/create_sound_video.py --audio-dir output/sound-audio --out output/sound-video
```

模型官方说明在 [Sherpa ONNX 的 VITS 模型页](https://k2-fsa.github.io/sherpa/onnx/tts/pretrained_models/vits.html)。本次使用的 MeloTTS 模型附 MIT 许可；保留其许可说明，模型本体不进入 skill 或实播包。独立 TTS 环境需要 `sherpa-onnx`、`soundfile`；准备视频还需完整 Noto Sans CJK SC 字体。

在生成项目目录运行 `npm ci`、`npm run studio`，先打开预览再调镜头。明确需要 MP4 交付时运行 `npm run render -- --browser-executable=/path/to/chromium`。该案例主片为 1920×1080、30fps、74 秒，包含中文合成旁白、句级字幕和两段原创纯音。它是独立科普成片，来源标记为 `original_authored_science_animation`；不是 PPT 放映录像。

```bash
# 先用 Remotion 将指定代表帧导出到新目录。
# 例如在视频项目中：remotion render src/index.tsx SoundJourney /path/to/reference-frames \
#   --frames=90,330,660,900,1260,1680,1950,2160 --image-format=png
python scripts/check_sound_video.py \
  --project output/sound-video \
  --video output/sound-video/out/sound-explainer.mp4 \
  --reference-frames /path/to/reference-frames \
  --out output/sound-video-qa \
  --lock output/VIDEO_LOCK.json \
  --visual-review-note "具体记录已查看的本次代表帧、科学表达、字幕与单位"
```

检查成片长度与音轨、八张编码后实际帧、放大后标记点的实际像素位置、两段纯音的频率，以及文本/音频/脚本绑定。先查看关键帧，检查字幕、图形、模型说明和单位，再通过必填的审阅参数记录具体依据；运行自动检查本身不代表有人看过画面。字幕时间以实际音频长度按句子分配，属于近似句级同步，不声称词级强制对齐。

`VIDEO_LOCK.json` 绑定完成的视频、脚本与通过的检查报告。源文件或视频变化后，旧锁不能继续使用；检查未通过时不生成锁。自动模型/编码检查不能代替审美判断或完整人工听审。

## 再做对应教学 PPT

```bash
python scripts/create_sound_ppt.py --video-lock output/VIDEO_LOCK.json --out output/sound-ppt
python scripts/nmp.py build output/sound-ppt --strict
python scripts/nmp.py accept output/sound-ppt --player wps \
  --tools-root /path/to/desktop-tools --wps-root /path/to/wps --wps-profile /path/to/private-profile
```

只有锁的三项校验都通过，才创建 PPT 项目。`video-to-ppt.json` 保存先视频后 PPT 的时间、源校验值和八段镜头到八页的映射。

PPT 的空气团、标记、箭头、公式和说明都重建为原生可编辑对象。连续流场在教学版中可定格；局部标记做有限往复并回到静态布局，公式和箭头按讲解展开。旁白稿与来源放在备注里。这是已知对象和分镜的重新制作，不声称 MP4 无损恢复为原生 PPT，也不把视频塞进幻灯片来代替对象。

PPT 导出后继续做实际页面、目标 WPS 的手动与自动放映、原生 Morph 隔离诊断及真实帧复核。原片主视频、PPT 设计预演和 WPS 实录分别保留来源和校验值。复杂组合或检测器不支持的对象保留待检，不从视频检查通过推定 WPS 通过。

最后交付：参考分析与事实表、原创科普视频、脚本/字幕/音频和编辑工程、对应原生 PPT、镜头到页面映射、真实 WPS 录像及检查报告。

## 本例实测记录

2026-10-27 的完整示例见 [sound-science-video-first 展示](../showcase/sound-science-video-first/README.md)。主片先封存，PPT 项目随后创建，二者以校验值和镜头映射绑定。

主片中的标记点在 70 个实际编码帧上，最大模型误差约 0.31px；两段音频窗口实测为 220/440Hz。国际 Linux WPS 11.1.0.11723.XA 的点击/自动录像均已完成；独立像素补测观察到标记约85px水平往复，纵向变化小于0.25px。八页、箭头/公式揭示及只发F5的自动翻页已查看实际帧。

通用页面匹配对第6页大字号公式仍待检；成组粒子 Morph 的自动轮廓方法也不覆盖。保留原始 pending，另附绑定两份录像与实际帧的审阅，不能宣布所有自动项通过。隔离的无对象动画 Morph 诊断通过，只证明该播放器的诊断场景。

此次同时修复辅助设计预演中的 SVG 宿主语言差异：根 SVG 明确使用与预览页一致的 zh-CN。原先失败运行留存；修复后单帧与浏览器参考一致，完整辅助视频44帧对照最大RMSE约3.27，沿用阈值5。此修复不把代码预演转成WPS实播证据。

## 视频迭代复查

用户反馈首版有问题后，新增对实际编码帧的切镜检查，确认旧片两处标记点跳位约107/119px，逐页进度条也在切镜时重置。原先八张代表帧和局部模型检查没有覆盖这些问题；旧报告与录像保留，不扩大它们的检查结论。

改进脚本是 `examples/science-video/sound-refined.json`：66秒，保留八段结构。镜头在同一世界坐标中连续推近和拉远；纵波段提高图形对比；频率段加入试听提示；公式随旁白句子揭示；进度条覆盖全片。使用逐句合成，字幕来自每句真实音频的样本边界，不按字数猜测。

```bash
/path/to/tts-python scripts/synthesize_sound_narration.py \
  --story examples/science-video/sound-refined.json --sentence-clips --speed 1 \
  --model /path/to/vits-melo-tts-zh_en \
  --model-url https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-melo-tts-zh_en.tar.bz2 \
  --out output/refined-audio
python scripts/create_sound_video.py --story examples/science-video/sound-refined.json \
  --audio-dir output/refined-audio --out output/refined-video
```

先在Studio查看画面，再按用户的成片交付要求导出。代表帧秒数读取故事的 `qa_sample_seconds`；重排场景后仍须检查所有切镜，不能仅替换帧编号。`check_sound_video.py` 对该修订版自动运行 `check_sound_edit.py`：用真实橙色像素检查切镜前后轨迹（相邻帧≤3px）、用编码帧检查全片进度（误差≤3px），再核对合成句子与编码后音轨的波形及字幕边界（相关系数≥0.96、偏移≤一帧）。沿用旧模型和编码对照阈值，不降低标准去消除失败。

音轨波形对照可以发现错误文件、时间偏移或丢失；它不证明科学文本正确、发音自然或完整人工听审，也不是词级ASR。主动查看文字、单位、模型与关键帧。新的主片检查、锁、PPT和目标播放器录像分别在新目录生成，不复用旧WPS验收来认证新版PPT。

最终66秒主片的实测记录：两处切镜附近的最大相邻帧位移为1.94/2.27px（旧片107/119px），进度条误差小于0.49px；15句编码旁白对源音频的最低归一化相关系数约0.99995，采样窗口未检出时移。主片实际标记模型误差小于0.31px，220/440Hz听辨通过。第一轮修订仍有3.31px的镜头尾部位移，原始失败保留；进一步平滑加速度后通过原有3px门槛。画面审阅还补了纵波标签的独立底色，避免文字叠在粒子上。证据见 [修订示例](../showcase/sound-science-refined/README.md)。这些数值说明具体回归检查通过，审美效果仍由观看决定。
