# Native Motion PPT v1.6.1 · 发布检查

2026-10-15 的独立仓库整理版。93 项 Python unittest、11 项 Node 时间线检查均通过；skill 结构验证通过。原有 89 项行为回归继续保留，新增包版本一致性、源码 ZIP 确定性与实际安装、归档篡改拒绝及嵌套输出自打包保护。

本版新增 source-only 分发，实际运行 package_skill.py --source-only 与 verify_delivery.py，验证 ZIP CRC、完整成员清单、逐文件 SHA、版本及解压后的全新安装。源码包和安装器排除 .git、.github、showcase、dist、生成输出、缓存和私有播放器配置。

原生导出、桌面录屏、阶段识别、运动检测与 assets 中 58 个现有文件和 v1.6.0 逐字节相同，见 docs/engine-provenance.json。改动限包版本读取、安装/分发脚本及仓库组织，没有将旧录像套用到新的播放行为。

实际 WPS 证据覆盖五页科学示例及独立两页项目的点击、自动翻页、柱底、主体运动和原生 Morph，原始 SHA 与范围见 docs/verification.md 和 showcase/manifest.json。完整原始验收工程预备作为 Release 的独立附件；showcase 只是原样摘录。

历史 v1.5.0 / v1.6.0 检查记录保存在 docs/history/，其中路径和环境描述保留历史上下文。CI 工作流已配置，远端是否执行及结果需发布后单独核对。本地自动检查不认证 Windows WPS、PowerPoint，也不替代真实 WPS 放映。
