# DEPLOYMENT-PATTERNS · 部署 / 自愈 / 版本闭环

> 关键现实：**当前主机是 Windows**，gunicorn/supervisor 不支持 Windows（LR-025/026），必须给 Windows 可落地等价物；未来 Linux 云服务器再切换。取数 2026-08-31。

## 1. 两条运行路径
| 维度 | 当前 Windows（可立即落地） | 未来 Linux 云（标准生产） |
|---|---|---|
| WSGI | **waitress**（纯 Py 跨平台，LR-027） | gunicorn（多 worker） |
| 进程守护 | run_supervised 看门狗 / NSSM 注册服务 / Docker Desktop | systemd 或 supervisor |
| 自愈 | 看门狗探活重启；Docker restart:unless-stopped + healthcheck | systemd Restart=always / compose healthcheck |
| 反代/公网 | cloudflared（当前临时域名）→ 后续固定域名或反代 | nginx + HTTPS（证书自动续期） |
| 静态/媒体 | Flask send_from_directory 即可 | nginx 直出静态 |

## 2. 健康检查与自愈
- `/healthz` 最轻存活探针（已有，返回 ok/version）；分层检查 application/database/scheduler/filesystem/browser-runtime。
- 自愈策略：health 连续 N 次失败 → 受控重启 worker → 仍失败则告警并保留现场；不自动做危险恢复（不删库、不清 profile）。

## 3. 版本自动保存闭环（GitHub = 源码/版本中心，非数据库中心）
- 触发：watchdog（LR-028）检测到**源码文件**变化（去抖）或手动"立即保存版本"→ 生成变更摘要 → 安全闸暂存（只源码/模板/配置模板/迁移/文档，**绝不** cookie/.env/*.db/profile/原始数据）→ commit → 代理 push。
- 远程有新提交先 pull --rebase（保留历史），**严禁 force push**；网络失败有限退避、保留本地提交、不谎报。
- 历史版本可回滚；版本中心展示当前版本/同步状态/最近提交/历史/回滚。
- 已知 P0-FIX-1：scripts/daily_git_sync.py:72 `current_version` 漏括号致自动提交标题异常，待一行修复（本轮不改）。

## 4. 源码 vs 数据严格分运
- 上 GitHub：源码、HTML/CSS/JS、配置模板、requirements、迁移、版本/CHANGELOG/docs。
- 留服务器安全存储：各平台 cookie/session、API key、SECRET_KEY、管理员密码、.env、生产 *.db、浏览器 profile、采集原始大数据。
- 生产库只备份到受控位置 + 用迁移脚本管理结构，不直接推库。

## 5. 环境可复现
- 锁定 requirements（必要时 uv，LR-031，极速复现）；记录 Python 版本（当前 3.13.15 venv）；Staging 与生产同依赖版本。
- 配置优先级契约统一：运行时 override > 环境变量 > 配置文件 > 默认；分层 config 不互相覆盖。

## 6. 公网与安全
- 当前 cloudflared 临时域名适合演示/手机查看；长期需固定域名 + HTTPS + Basic/登录 + 限流（slowapi 候选）+ 最小暴露面。
- 高危"运行代码"入口（/api/developer/run 等三套）收口为一个受控、有权限与审计的 Owner（安全 P1，见 CAPABILITY-OWNERSHIP §5）。

## 7. 部署检查清单
构建可复现 → 迁移在 Staging 验证 → health 通过 → 红线回归 PASS → Evidence 归档 → 灰度 → 观察 → 全量；每步可回滚。
