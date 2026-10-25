# 第一次使用：从可编辑项目开始

在 skill 根目录执行；下文 `scripts/` 均相对该目录。帮助、创建项目和环境诊断只需要 Python 3.10+。

```bash
python scripts/nmp.py --help
python scripts/nmp.py new output/my-first-deck
python scripts/nmp.py doctor --for build
```

默认 minimal 使用随包的 Space Grotesk 字体和英文内容，避免第一次导出依赖系统中文字体。`--template product`、`--template progress` 和 `--template science` 提供中文通用示例；它们需要完整 Noto Sans CJK SC 和 Noto Serif CJK SC。模拟数据与文案都需要根据实际项目替换。

希望从连续主体与跨页编排开始时，用 `--template cinematic`：

```bash
python scripts/nmp.py new output/my-motion-study --template cinematic
python scripts/nmp.py build output/my-motion-study --strict
```

该模板使用 Noto Sans CJK SC 与随包 Latin 字体。三页依次为扇形聚拢、同名形状变为柱形、局部图表扩展到全画面并突出最高值。第二、三页保留同一组模拟数值，按各页共同尺度与零基线呈现。它是完整页面重新设计的起点，不会自动把任意现有 PPT 变为这种效果。修改数值时，应同步修改第二、三页相应柱高、标签与尺度；当前 JSON 不会自动计算数据关联。

## 只导出原生 PPT

```bash
python -m pip install -r requirements-core.txt
python scripts/nmp.py build output/my-first-deck
```

输出新的 `output/build-…/`，包含点击版、自动版、源 JSON 副本、结构检查和 build-report.json。不会覆盖旧运行。`passed` 仅指源与原生结构导出；desktop_playback 保持 pending。

编辑项目的 project.json；nmp.json 只保存模板来源与默认检查 profile。`new --title` 修改项目元数据，不批量替换各页标题。创建 science 项目时同时复制 CSV 与图形清单；改变数据后同步更新对应源文件。

## 预览与设计视频

```bash
python scripts/nmp.py preview output/my-first-deck
```

命令返回预览 HTML 和本地启动服务器的完整命令。预览生成只需要核心依赖和所用字体；浏览器抽帧、视频和真实放映再分别安装额外工具。

```bash
python -m pip install -r requirements.txt
python scripts/nmp.py doctor --for browser --spec output/my-first-deck
python scripts/nmp.py doctor --for video --spec output/my-first-deck
```

浏览器采样与设计视频共同识别 `NMP_BROWSER_EXECUTABLE`、系统 chromium/chromium-browser/google-chrome，或已经安装的 Playwright Chromium。显式路径错误会报错，避免静默使用另一套浏览器。生成 Remotion 项目的 `npm run render` 也可通过 `-- --browser-executable=/path/to/browser` 指定路径；没有显式路径时由 Remotion 管理浏览器。Node.js 需要 20+，doctor 检查实际版本。

## 中文字体与真实播放

Linux 可从系统官方仓库安装完整 Noto CJK，或从字体官方来源安装相应字体。随包 Latin 字体可用于预览，但 PPTX 仍引用系统字体，实际播放器需安装完整字体。不能将浏览器子集字体当作完整中文字体。

WPS 安装、首次 GUI 检查与 profile 准备见 [WPS 实播](wps-playback.md)。设置好后：

```bash
python scripts/nmp.py doctor --for acceptance --player wps --spec output/my-first-deck \
  --tools-root /path/to/desktop-tools --wps-root /path/to/wps --wps-profile /path/to/wps-profile
python scripts/nmp.py accept output/my-first-deck --player wps \
  --tools-root /path/to/desktop-tools --wps-root /path/to/wps --wps-profile /path/to/wps-profile
```

也可通过 NMP_DESKTOP_TOOLS、NMP_WPS_ROOT、NMP_WPS_PROFILE 设置上述路径；未指定时尝试用户目录 `.local/share/native-motion-ppt/{desktop,wps,wps-profile}` 中已经存在的目录。不会自动安装或接受首次许可窗口。WPS 不可用时保持待检查，不替换播放器。

完整流程生成报告后，查看两份实际录像和关键帧，再按 [验收流程](acceptance.md) 添加具体审阅依据。没有真实录屏时不能认证 Morph 或自动翻页。

```bash
python scripts/nmp.py accept --resume /path/to/previous-run --mode check
python scripts/nmp.py accept --resume /path/to/previous-run --mode record \
  --tools-root /path/to/desktop-tools --wps-root /path/to/wps --wps-profile /path/to/wps-profile
```

check 只要求分析依赖，不要求播放器或重新渲染。record 从父运行读取目标后端并重新采集，不能把另一播放器的录屏作为原目标的通过结论。所有复验生成新运行。

## 现有 PPT

```bash
python scripts/nmp.py enhance input.pptx --out output/enhanced.pptx --plan plan.json
```

plan 为 inspect 获得的顶层对象 ID 分组，格式见 SKILL.md。已有动画保留；原稿与已有输出不会覆盖。增强后会做包结构检查并保留原稿 SHA，实际播放状态仍待验证。
