# Native Motion PPT

制作原生可编辑动态 PPT，共用 JSON 生成 PPTX 和 Remotion 设计预演，并用真实桌面放映核对结果。

An agent skill for editable animated PowerPoint, shared JSON/Remotion previews, and evidence-backed desktop playback acceptance.

[下载 v1.8.0 安装包](https://github.com/Yingqi-Han/native-motion-ppt/releases/download/v1.8.0/native-motion-ppt-v1.8.0.zip) · [完整 WPS 实播验收工程](https://github.com/Yingqi-Han/native-motion-ppt/releases/download/v1.8.0/wps-v1.8.0-delivery.zip) · [Release 与校验清单](https://github.com/Yingqi-Han/native-motion-ppt/releases/tag/v1.8.0)

当前源码 **v1.8.0**，MIT 许可。新增现成 PPT 的分组草案、源文件绑定与逐成员保留校验，以及可定位的待检原因说明。支持分步动画、逐字出现、运动路径、缩放/旋转、跨页 Morph，以及点击/自动双版本。WPS 实播结论限 Linux 11.1.0.11723；[范围与真实录像](docs/verification.md) 分别记录，Windows WPS 和 Microsoft PowerPoint 尚未实测。

## 安装

```bash
git clone https://github.com/Yingqi-Han/native-motion-ppt.git
cd native-motion-ppt
python scripts/install_skill.py --workspace /path/to/your/project
```

安装到目标项目的 `.agents/skills/native-motion-ppt`。升级时加 `--upgrade`，安装器核对受管理文件并备份旧版，发现本地修改会保留并停止覆盖。也可直接使用本仓库的 [SKILL.md](SKILL.md)。

Python 3.10+；原生导出与预览工程生成只需核心依赖：

```bash
python -m pip install -r requirements-core.txt
python scripts/nmp.py doctor --for build
```

需要浏览器抽帧、视频和真实放映时再安装 `requirements.txt`。浏览器采样需要 Chromium 和 Playwright；Remotion 视频需要 Node.js 20+。静态页面渲染需 LibreOffice，真实 WPS 验收另需 GUI 工具链、官方 WPS 和完整字体。`doctor --for preview/render/browser/video/analysis/playback/acceptance` 分别给出缺项和修复命令；完整说明见 [第一次使用](references/first-project.md)。

## 从最小示例开始

```bash
python scripts/nmp.py new output/my-first-deck
python scripts/nmp.py build output/my-first-deck
python scripts/nmp.py preview output/my-first-deck
```

`new`、`--help` 和 `doctor` 在尚未安装第三方包时也能运行。默认最小项目使用随包的 Latin 字体；中文示例另需完整 Noto CJK。修改新项目中的 project.json 后重新 build，新的独立输出目录会同时包含点击版与自动版，不覆盖旧文件。build 成功只认证导出和结构检查，真实播放仍待录制。文字、图形、组合和动画保留为原生对象；JSON 单位为设计像素和毫秒。

| 示例 | 用途 |
|---|---|
| [starter-minimal.json](examples/starter-minimal.json) | `new` 默认；仅用随包字体启动 |
| [product-intro.json](examples/product-intro.json) | `new --template product`；产品介绍、柱图与跨页主体 |
| [project-update.json](examples/project-update.json) | `new --template progress`；进展、流程与行动依赖 |
| [cinematic-focus-zoom.json](examples/cinematic-focus-zoom.json) | `new --template cinematic`；扇形聚拢、连续 Morph、全幅图表聚焦 |
| [cinematic-focus.json](examples/cinematic-focus.json) | 保留的三页视觉样片；主体重组与固定基线展开 |
| [minimal.json](examples/minimal.json) | 保留的中文最小原生示例 |
| [demo.json](examples/demo.json) | 六镜头、组合图形和连续运动 |
| [scientific.json](examples/scientific.json) | 五页模拟数据图表与科学流程 |
| [wps-generic-regression.json](examples/wps-generic-regression.json) | 独立两页、无页码、柱图与 Morph 回归 |
| [roles-portrait.json](examples/roles-portrait.json) | 竖版与语义编排 |

## 完整 WPS 验收

按 [WPS 实播准备](references/wps-playback.md) 安装并完成首次 GUI 检查，再运行：

```bash
python scripts/nmp.py new output/my-product --template product
python scripts/nmp.py accept output/my-product --player wps \
  --tools-root "$HOME/.local/share/native-motion-ppt/desktop" \
  --wps-root "$HOME/.local/share/native-motion-ppt/wps" \
  --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile"
```

生成点击/自动 PPT、设计视频、两份实际 WPS 录屏、关键帧、对象运动检查、HTML 报告和完整项目 ZIP。缺少所选播放器时保持待检查；视觉审阅绑定实际录像和帧的 SHA，审阅后最终验收才可通过。`--strict` 让待检查必需项返回退出码 2，失败返回 1。

修改检查器后可用 `nmp.py accept --resume <旧运行> --mode check` 复算原录像；需要重新采集时用 `--mode record` 并传播放器路径。check 不要求播放器、浏览器或重新渲染，两者均创建新目录。改变源数据后运行完整 full。高级 `accept_project.py` 入口继续可用；命令、状态和结构化审阅见 [验收流程](references/acceptance.md)。

失败或待检时可运行 `python scripts/nmp.py diagnose <验收目录> --out output/diagnosis`，查看原因、建议和真实片段定位。新验收报告自动提供该入口；解释不改原始状态，无时间证据时不生成异常跳转。详见 [验收诊断](references/diagnostics.md)。

代码预演由浏览器/Remotion 生成，真实放映录像来自指定 GUI 播放器。两者来源分别记载；采集帧率不等同于播放器重绘率。

## 编辑现有 PPT

```bash
python scripts/nmp.py plan input.pptx --max-clicks 3 --out output/plan
# 查看实际页面，核对并编辑 output/plan/plan.json
python scripts/nmp.py enhance input.pptx --plan output/plan/plan.json --out output/enhanced.pptx
```

布局规则先提出可审阅草案，保留标题、上下文与不确定对象，原生组合不拆开。计划绑定源 SHA；增强只改选中页的动画时序，核对其他包成员、非时序 XML 和已有动画按原样保留。生成报告的实际播放状态仍待验证。规则与范围见 [现有 PPT](references/existing-ppt.md)。图表使用可编辑形状，不带可自动同步的 Excel 图表工作簿。模拟数据只用于演示。

## 开发与发布

```bash
python -m unittest discover -s tests -v
node --test tests/test_timeline.mjs
python tests/smoke_core_cli.py --isolated
python scripts/validate_skill.py
python scripts/package_skill.py --source-only --out dist
python scripts/verify_delivery.py dist
```

源码发布包无需预先生成演示工程；包含清单、SHA 校验和全新安装验证。CI 检查 Python 3.10/3.12，并在 Linux/Windows 的干净核心依赖环境验证项目创建、双版导出、预览生成及已有动画保留；这些检查不认证 Windows WPS。版本标签触发源码发布。完整项目交付使用 accept；旧多示例打包方式仍保留，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

| 目录 | 内容 |
|---|---|
| `scripts/` | 原生导出、预览、桌面采集和验收 |
| `assets/` | 数据 schema、共用时间线、字体与 Remotion 模板 |
| `examples/` | 可编辑输入及模拟数据 |
| `references/` | 制作、设计、格式、播放器与检查说明 |
| `tests/` | 行为回归 |
| `docs/` | 验证范围、版本说明和历史检查 |
| `showcase/` | 原样保留的实际 WPS 录像、PPT 与证据摘录；安装时排除 |

`output/`、`dist/`、缓存、播放器、下载包与私人 profile 不进入 Git。第三方字体许可见 `assets/fonts/`；Remotion 与 WPS 的许可分别适用。
