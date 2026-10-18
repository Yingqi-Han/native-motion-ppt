# Native Motion PPT v1.7.0 · 发布检查

本轮新增统一项目入口、按任务诊断、核心依赖启动流程、产品/进展示例，并修复实播阶段识别与失败报告。117 项 Python unittest、11 项 Node 时间线检查通过，skill 结构验证通过。

隔离环境只安装 requirements-core.txt，实际执行 new、严格 build、preview 和 enhance，检查原稿及已有动画保留、随包字体匹配；确认未安装 NumPy、PyMuPDF、Playwright，未启动 Office 或浏览器。GitHub 的 Linux/Windows 核心任务和 Python 3.10/3.12 完整回归已通过：[检查记录](https://github.com/Yingqi-Han/native-motion-ppt/actions/runs/39116916502)。首次跨平台失败记录保留，修复 Windows UTF-8 读取并为中文示例检查安装完整字体，没有跳过失败断言。

实测从公开 v1.6.1 源码包安装后执行受管理升级，确认新入口字节、旧版备份和本地修改阻止覆盖。升级检查只证明安装器行为。

两套新示例的真实 WPS 点击/自动录像、原生柱展开、主体运动、Morph 与自动翻页分别检查；最终状态及校验清单见 [实播验证](docs/verification.md)。自动首屏晚展开误漏和旧页面遮罩截断主体的中间结果保留，代码修正后独立复验。失败状态传播另以退出码为 1 的实际子进程做行为回归，合成测试不计作播放器证据。

源码分发执行 source-only 打包和 verify_delivery.py，核对 ZIP CRC、成员清单、SHA、版本与解压后全新安装。实际 WPS 工程另行归档，保留源/PPT/双录像、采集证据、机器检查、结构化视觉审阅、实现快照、报告与可安装工程。

历史 v1.6.1 检查见 [原记录](docs/history/QA_REPORT-v1.6.1.md)，旧引擎来源清单仅解释 v1.6.1，不能认证本轮检测器。CI 与打包检查不认证 Windows WPS 或 Microsoft PowerPoint。
