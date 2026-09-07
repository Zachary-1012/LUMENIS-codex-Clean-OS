# GitHub 远程基线核对报告

> 审计时间：2026-09-08
> 审计模式：只读（git fetch / log / diff / status / remote / branch）
> 本地仓库：`D:\Taikoo-monitor-new`
> 远程仓库：`https://github.com/Zachary-1012/Z-Brand-Core`

---

## 1. 远程地址与当前分支

| 项目 | 值 |
|---|---|
| 远程名称 | origin |
| fetch URL | `https://github.com/Zachary-1012/Z-Brand-Core.git` |
| push URL | `https://github.com/Zachary-1012/Z-Brand-Core.git` |
| 当前分支 | `main` |
| 远程 HEAD | `origin/HEAD -> origin/main` |
| 远程主线分支 | `main`（非 master） |

---

## 2. 本地最近 Commit

| Hash | 日期 | Message |
|---|---|---|
| `ff9c31a` | 2026-09-08 | v5.9.9 自动保存版本（00:41 巡检） |
| `c095c12` | 2026-09-08 | v5.9.9 定时同步版本（00:00） |
| `ab7fca4` | 2026-09-07 | fix(ui): 修复3个页面内联JS致命语法错误导致数据不渲染 |
| `3d8cb45` | 2026-09-07 | fix(routing): 根路由重定向到 /lumenis/ 修复首页404，补 /VERSION 路由，settings 浏览器面板接统一门面 browser-surface |
| `b6b9a81` | 2026-09-07 | v5.9.9 自动保存版本（22:36 巡检） |

**本地 HEAD 详情：**
- Hash: `ff9c31a4b02ab2e7170c89a205cb069ce6ae9b77`
- Author: Zachary-1012
- Date: 2026-09-08 00:41:54 +0800
- Message: v5.9.9 自动保存版本（00:41 巡检）

---

## 3. 远程主线最近 Commit

| Hash | 日期 | Message |
|---|---|---|
| `ff9c31a` | 2026-09-08 | v5.9.9 自动保存版本（00:41 巡检） |
| `c095c12` | 2026-09-08 | v5.9.9 定时同步版本（00:00） |
| `ab7fca4` | 2026-09-07 | fix(ui): 修复3个页面内联JS致命语法错误导致数据不渲染 |
| `3d8cb45` | 2026-09-07 | fix(routing): 根路由重定向到 /lumenis/ 修复首页404，补 /VERSION 路由，settings 浏览器面板接统一门面 browser-surface |
| `b6b9a81` | 2026-09-07 | v5.9.9 自动保存版本（22:36 巡检） |

**远程 HEAD 详情：**
- Hash: `ff9c31a4b02ab2e7170c89a205cb069ce6ae9b77`
- Author: Zachary-1012
- Date: 2026-09-08 00:41:54 +0800
- Message: v5.9.9 自动保存版本（00:41 巡检）

---

## 4. Commit 差距量化

| 维度 | 数量 | 说明 |
|---|---|---|
| 本地领先远程（`origin/main..HEAD`） | **0** | 本地无未推送的 commit |
| 远程领先本地（`HEAD..origin/main`） | **0** | 本地无落后的 commit |
| 本地与远程 HEAD 是否一致 | **是** | 同一 hash `ff9c31a` |

**本地领先远程的 commit 清单：** 无

**远程领先本地的 commit 清单（本地落后）：** 无

---

## 5. 未提交变更统计

### 5.1 总览

| 类别 | 数量 |
|---|---|
| 已修改的 tracked 文件（`git diff --name-only`） | **0** |
| 已暂存的文件（`git diff --cached --name-only`） | **0** |
| 未跟踪的文件（`git ls-files --others --exclude-standard`） | **49** |
| 被 .gitignore 忽略的文件 | **47,919** |

### 5.2 未跟踪文件清单（49 个，全部在 audit/ 目录）

| # | 文件路径 | 类型 |
|---|---|---|
| 1 | `audit/_db_tables_snapshot.json` | JSON 数据快照 |
| 2 | `audit/api_audit.py` | Python 审计脚本 |
| 3-49 | `audit/api_responses/*.json`（47 个文件） | API 响应快照 |

`audit/api_responses/` 下的 47 个文件为各 API 端点的响应 JSON 及对应的 meta.json，包括：
- `/api/overview`, `/api/status`, `/api/health`
- `/api/viz/overview.stats`, `/api/viz/overview.trend`, `/api/viz/risk.active`
- `/api/brand-stats`, `/api/brand-industry_stats`
- `/api/notes/library`, `/api/notes/publish-buckets`
- `/api/negative/pending`, `/api/negative-review_stats`
- `/api/cases/stats`, `/api/cases/taikoo-hui`
- `/api/collector_quality`, `/api/dashboard_changes`
- `/api/metrics_canonical`, `/api/platform-health`
- `/api/system_database`, `/api/system_health`
- `/api/trends_global`, `/api/weekly_events`
- `/lumenis/healthz`

### 5.3 敏感文件检查

| 检查项 | 结果 |
|---|---|
| `.env` 文件 | 未发现 |
| `*.db` / `*.sqlite` / `*.sqlite3` | 未发现 |
| Cookie / Token / Secret / Key / Credential 命名文件 | 未发现 |
| `*.pem` / `*.key` 私钥文件 | 未发现 |

**结论：未跟踪文件中无敏感凭证文件。** 但需注意 `audit/api_responses/*.json` 中可能包含业务数据（如笔记内容、评论数据），提交前应评估是否包含用户隐私信息。

### 5.4 被忽略文件说明

47,919 个被忽略文件主要包括：
- `audit/` 下的大量审计产物（MD 报告、JSON 数据、截图、视频帧）
- `__pycache__/` 目录
- `audit/screenshots/` 下的页面截图
- `audit/video_frames/` 和 `audit/video_frames_dense/` 下的视频帧
- `audit/feature_governance/`、`audit/convergence/` 等子目录的审计数据

这些文件已被 `.gitignore` 正确排除，不会进入版本控制。

---

## 6. 文件级差异清单（tracked 文件）

| 文件名 | 增行 | 删行 | 是否前端/API 相关 |
|---|---|---|---|
| **（无差异）** | — | — | — |

`git diff --stat origin/main` 输出为空，`git diff --name-only origin/main` 输出为空。

**本地所有 tracked 文件与远程主线完全一致，零文件差异。**

---

## 7. 前端/API 相关文件差异

由于 tracked 文件层面零差异，以下关键前端/API 文件均无本地与远程差异：

| 文件 | 差异状态 |
|---|---|
| `app.py` | 无差异 |
| `lumenis_frontend.py` | 无差异 |
| `templates/cth/*` | 无差异 |
| `static/js/*` | 无差异 |
| `risk_engine.py` | 无差异 |
| `daily_report.py` | 无差异 |
| `ui_view_model.py` | 无差异 |
| `viz_api.py` | 无差异 |
| `viz_data_provider.py` | 无差异 |

详细说明见 `diff_details/_README.md`。

---

## 8. 综合判断

### 8.1 本地是否落后于远程？

**否。** 本地 `main` 与 `origin/main` 指向同一 commit（`ff9c31a`），落后 0 个 commit，领先 0 个 commit。代码完全同步。

### 8.2 本地是否有大量未提交变更？

**有 49 个未跟踪文件，但无已修改的 tracked 文件。** 所有未跟踪文件均位于 `audit/` 目录，属于审计脚本和 API 响应快照，不参与运行时代码。这些文件不会影响系统行为。

### 8.3 差异是否集中在前端/API 相关文件？

**否。** tracked 文件层面零差异，前端/API 相关文件与远程完全一致。未跟踪文件虽包含 API 响应快照，但这些是只读审计产物，不是代码文件。

### 8.4 是否可能构成"页面显示不准确"的原因？

**不可能由本地/远程代码差异导致。** 理由：

1. 本地与远程代码完全一致（同一 commit、零文件差异），不存在"前后端版本不一致"的问题。
2. 未跟踪文件均为 audit 审计产物，不参与 Flask 路由、模板渲染或 API 响应。
3. 最近两个相关修复 commit（`ab7fca4` 修复 JS 语法错误、`3d8cb45` 修复路由重定向）已同时存在于本地和远程。

**"页面显示不准确"的可能原因应从以下方向排查（需进一步核实）：**

| 方向 | 排查要点 |
|---|---|
| 运行时状态 | Flask 服务是否已重启并加载最新代码？是否有旧进程占用端口？ |
| 浏览器缓存 | 前端 JS/CSS 是否被浏览器缓存？需硬刷新（Ctrl+Shift+R）验证 |
| 数据库状态 | 数据表是否为空？表结构是否与代码 ORM Model 一致？主体过滤是否导致数据为 0？ |
| 配置/环境 | `.env` 中数据库路径、端口、品牌配置是否正确？ |
| 数据口径 | `publish_datetime` vs `captured_at` 是否混淆？日报/周报时间窗口是否正确？ |
| API 响应 | 未跟踪的 `audit/api_responses/*.json` 显示多个 API 返回 73 字节（可能为 `{"ok":true}` 空响应），需核实这些 API 是否应返回数据但实际返回空 |

**特别注意：** `audit/api_responses/` 中多个 API 响应文件仅 73 字节（如 `get_api_brand-stats.json`、`get_api_status.json`、`get_api_system_database.json` 等），这可能意味着这些 API 返回了空数据或错误响应。如果页面依赖这些 API 渲染数据，空响应可能是"页面显示不准确"的直接原因。**建议优先检查这些 API 的实际返回内容。**

---

## 9. 审计操作记录

| 操作 | 命令 | 结果 |
|---|---|---|
| 确认远程 | `git remote -v` | origin → GitHub Z-Brand-Core |
| 列出分支 | `git branch -a` | 本地 16 分支，远程 80+ 分支 |
| 工作区状态 | `git status --short` | 3 个未跟踪目录项 |
| 本地最近 commit | `git log --oneline -5` | ff9c31a → b6b9a81 |
| 更新远程引用 | `git fetch origin --prune` | 成功，无新引用 |
| 本地领先 commit | `git log --oneline origin/main..HEAD` | 0 条 |
| 远程领先 commit | `git log --oneline HEAD..origin/main` | 0 条 |
| 文件差异统计 | `git diff --stat origin/main` | 空 |
| 差异文件名 | `git diff --name-only origin/main` | 空 |
| 未跟踪文件列表 | `git ls-files --others --exclude-standard` | 49 个文件 |
| 已修改 tracked 文件 | `git diff --name-only` | 0 个 |
| 已暂存文件 | `git diff --cached --name-only` | 0 个 |

**全程只读，未执行任何修改工作区或历史的 git 命令。**

---

## 10. 结论摘要

1. **代码同步状态：完全同步。** 本地 `main` 与 `origin/main` 同一 commit，零领先、零落后、零文件差异。
2. **未提交变更：49 个未跟踪文件，全部为 audit 审计产物，不影响运行时。** 无敏感凭证文件。
3. **前端/API 差异：无。** 所有关键前端/API 文件与远程完全一致。
4. **对"页面显示不准确"的判断：代码差异不是原因。** 建议从运行时状态、浏览器缓存、数据库数据、API 空响应等方向排查。特别关注 `audit/api_responses/` 中多个 73 字节的空响应文件。
