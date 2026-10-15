# Native Motion PPT

制作原生可编辑动态 PPT，共用 JSON 生成 PPTX 和 Remotion 设计预演，并用真实桌面放映核对结果。

An agent skill for editable animated PowerPoint, shared JSON/Remotion previews, and evidence-backed desktop playback acceptance.

[下载 v1.6.1 安装包](https://github.com/Yingqi-Han/native-motion-ppt/releases/download/v1.6.1/native-motion-ppt-v1.6.1.zip) · [完整 WPS 实播验收工程](https://github.com/Yingqi-Han/native-motion-ppt/releases/download/v1.6.1/wps-v1.6.0-delivery.zip) · [Release 与校验清单](https://github.com/Yingqi-Han/native-motion-ppt/releases/tag/v1.6.1)

当前发布版 **v1.6.1**，MIT 许可。支持分步动画、逐字出现、运动路径、缩放/旋转、跨页 Morph，以及点击/自动双版本。WPS 实播结论限 Linux 11.1.0.11723；[范围与真实录像](docs/verification.md) 分别记录，Windows WPS 和 Microsoft PowerPoint 尚未实测。

## 安装

```bash
git clone https://github.com/Yingqi-Han/native-motion-ppt.git
cd native-motion-ppt
python scripts/install_skill.py --workspace /path/to/your/project
```

安装到目标项目的 `.agents/skills/native-motion-ppt`。升级时加 `--upgrade`，安装器核对受管理文件并备份旧版，发现本地修改会保留并停止覆盖。也可直接使用本仓库的 [SKILL.md](SKILL.md)。

Python 3.10+；先安装依赖：

```bash
python -m pip install -r requirements.txt
python scripts/doctor.py
```

浏览器预览采样需要 Chromium 和 Playwright；Remotion 视频需要 Node.js 20+。实际页面渲染需 LibreOffice，真实 WPS 验收另需对应 GUI 工具链、官方 WPS 和完整字体。依赖说明见 [工作流程](references/workflow.md) 和 [WPS 安装与实播](references/wps-playback.md)。

## 从最小示例开始

```bash
python scripts/motion_ppt.py validate examples/minimal.json
python scripts/motion_ppt.py build examples/minimal.json --out output/deck.pptx
python scripts/motion_ppt.py build examples/minimal.json --out output/deck-auto.pptx --auto
python scripts/motion_ppt.py preview examples/minimal.json --out output/preview --remotion
```

文字、图形、组合和动画均保留为原生对象。JSON 使用设计像素和毫秒；默认画布 1920×1080，导出时换算为 PPT 单位。修改源 JSON 后重新生成。

| 示例 | 用途 |
|---|---|
| [minimal.json](examples/minimal.json) | 最小原生动画与预览 |
| [demo.json](examples/demo.json) | 六镜头、组合图形和连续运动 |
| [scientific.json](examples/scientific.json) | 五页模拟数据图表与科学流程 |
| [wps-generic-regression.json](examples/wps-generic-regression.json) | 独立两页、无页码、柱图与 Morph 回归 |
| [roles-portrait.json](examples/roles-portrait.json) | 竖版与语义编排 |

## 完整 WPS 验收

按 [WPS 实播准备](references/wps-playback.md) 安装并完成首次 GUI 检查，再运行：

```bash
python scripts/accept_project.py examples/scientific.json \
  --out output/runs --profile science --target-player wps-desktop \
  --desktop-tools-root "$HOME/.local/share/native-motion-ppt/desktop" \
  --wps-root "$HOME/.local/share/native-motion-ppt/wps" \
  --wps-profile "$HOME/.local/share/native-motion-ppt/wps-profile"
```

生成点击/自动 PPT、设计视频、两份实际 WPS 录屏、关键帧、对象运动检查、HTML 报告和完整项目 ZIP。缺少所选播放器时保持待检查；视觉审阅绑定实际录像和帧的 SHA，审阅后最终验收才可通过。`--strict` 让待检查必需项返回退出码 2，失败返回 1。

修改检查器后可用 `--resume <旧运行> --mode check` 复算原录像；需要重新采集时用 `--mode record` 并传播放器路径。两者都创建新目录。改变源数据后运行完整 full。命令、状态和结构化审阅见 [验收流程](references/acceptance.md)。

代码预演由浏览器/Remotion 生成，真实放映录像来自指定 GUI 播放器。两者来源分别记载；采集帧率不等同于播放器重绘率。

## 编辑现有 PPT

```bash
python scripts/motion_ppt.py inspect input.pptx --out output/inventory.json
python scripts/motion_ppt.py enhance input.pptx --plan plan.json --out output/enhanced.pptx
python scripts/motion_ppt.py check output/enhanced.pptx --out output/qa --allow-images --render
```

语义分组计划、已有动画保留规则和能力边界见 [SKILL.md](SKILL.md)。图表使用可编辑形状，不带可自动同步的 Excel 图表工作簿。模拟数据只用于演示。

## 开发与发布

```bash
python -m unittest discover -s tests -v
node --test tests/test_timeline.mjs
python scripts/validate_skill.py
python scripts/package_skill.py --source-only --out dist
python scripts/verify_delivery.py dist
```

源码发布包无需预先生成演示工程；包含清单、SHA 校验和全新安装验证。GitHub 的 CI 运行同样检查，版本标签触发源码发布。完整项目交付使用 `accept_project.py`；旧多示例打包方式仍保留，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

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
