# 发布到 GitHub

仓库目标：`Yingqi-Han/native-motion-ppt`，公开，默认分支 `main`。首次发布版本 `v1.6.1`。

发布前执行 CONTRIBUTING.md 的全部检查，并确认 VERSION 与标签一致。源码包在 dist/；原始 WPS 完整证据包保留原文件，不重封或改写哈希。

命令行需要 `gh` 与 Git，并具备目标账号的新建仓库、推送及 Release 权限。网络策略需允许 `github.com`、`api.github.com` 和上传附件所需的 `uploads.github.com`。不要在仓库或聊天中保存令牌。

首次新建仓库并上传：

```bash
gh api user --jq .login
gh repo create Yingqi-Han/native-motion-ppt --public \
  --description "Editable animated PPTX skill with real WPS playback acceptance" \
  --source . --remote origin --push
git push origin v1.6.1
```

标签触发 release.yml，先检查再发布源码 ZIP、manifest.json 和 package-check.json。若账号策略未允许 Actions，需要在仓库设置中启用后重跑；不能把本地通过写成远端 CI 通过。

在源码 Release 创建成功后，可追加原始实播交付：

```bash
gh release upload v1.6.1 /path/to/wps-v1.6.0-delivery.zip \
  --repo Yingqi-Han/native-motion-ppt
```

上传完成后核对仓库默认分支、远端 commit/tag、Release 文件名与大小，以及 Actions 结果。创建失败时保留本地 Git 历史和 dist/，配置修复后重试；不要覆盖碰巧同名的他人仓库。
