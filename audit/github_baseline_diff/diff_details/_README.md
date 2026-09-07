# 前端/API 相关文件差异说明

## 结论：无差异

本地 `main` 分支与 `origin/main` 在 **tracked 文件层面完全一致**（同一 commit `ff9c31a`，`git diff --stat origin/main` 输出为空）。

因此以下前端/API 关键文件均无本地与远程差异：

- `app.py`
- `lumenis_frontend.py`
- `templates/cth/*`
- `static/js/*`
- `risk_engine.py`
- `daily_report.py`
- `ui_view_model.py`
- `viz_api.py`
- `viz_data_provider.py`

## 未跟踪文件说明

本地仅有 49 个未跟踪文件，全部位于 `audit/` 目录下，属于审计脚本与 API 响应快照，**不参与运行时代码**：

- `audit/api_audit.py` — 只读 API 响应采集脚本
- `audit/_db_tables_snapshot.json` — 数据库表结构快照
- `audit/api_responses/*.json` — 47 个 API 响应快照文件

这些文件不会影响前端页面渲染或 API 行为。

## 对"页面显示不准确"的启示

由于本地与远程代码完全一致，**前后端代码不一致不是页面显示不准确的原因**。应从以下方向排查：

1. 运行时状态：服务是否重启、是否加载了最新代码
2. 数据库状态：数据是否为空、表结构是否与代码期望一致
3. 浏览器缓存：前端静态资源是否被缓存
4. 配置/环境变量：`.env` 中配置是否正确
5. 数据口径：主体过滤、时间口径是否导致数据为 0
