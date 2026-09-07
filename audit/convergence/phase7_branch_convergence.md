# Phase 7 — Branch Convergence Matrix（全分支收敛审计）

> **审计日期**：2026-09-07
> **仓库**：Zachary-1012/Z-Brand-Core（private）
> **本地路径**：`D:\Taikoo-monitor-new`
> **main HEAD**：`d72153fa28d232d6eb41542b906f7064729e8266`
> **审计模式**：严格只读（仅 `git log` / `git diff` / `git show` / `git branch` / `git fetch --prune`）
> **证据基线**：`git merge-base --is-ancestor` + `git rev-list --count main..branch` + `git diff --name-only main...branch`

---

## 1. 总览统计

| 指标 | 数值 |
|------|------|
| **唯一分支总数**（去重本地/远程同名，排除误识别的 `origin` 条目） | **97** |
| 本地分支（非 main） | 16 |
| 远程独有分支 | 81 |
| 非祖先分支（main 未完全包含） | 5 |
| 祖先分支（已完全进入 main） | 92 |

### A-F 分类统计

| 分类 | 定义 | 数量 | 占比 |
|------|------|------|------|
| **A** | 已完整进入 main，无独有资产 | 28 | 28.9% |
| **B** | main 部分吸收，仍有独有价值 commit/file | 2 | 2.1% |
| **C** | main 未吸收但存在有效资产（文档/配置） | 1 | 1.0% |
| **D** | research / experimental，不适合直接进生产 | 3 | 3.1% |
| **E** | stale，陈旧重复变体，已被 main 完全覆盖 | 62 | 63.9% |
| **F** | conflict / risk，含危险操作或主体口径弱化 | 1 | 1.0% |
| **合计** | | **97** | 100% |

### 行动清单统计

| 清单 | 数量 |
|------|------|
| **Merge Candidates**（建议合并，B/C 类） | 3 |
| **Deletion Candidates**（建议删除候选，A/E/D 类，仅记录不执行） | 90 |
| **Unresolved Conflicts**（F 类，禁止自动处理） | 1 |

---

## 2. 审计方法

### 2.1 分类判定规则（每条均有 git 证据支撑）

- **A 类判定**：`git merge-base --is-ancestor <branch> main` 返回 0 **且** `git rev-list --count main..<branch>` = 0 **且** `git diff --name-only main...<branch>` 为空。
- **B 类判定**：非祖先（`is-ancestor` 返回 1），独有 commit 包含产品价值代码，且无 P0 风险。
- **C 类判定**：非祖先，独有资产为文档/配置等非代码资产，有参考价值。
- **D 类判定**：分支内容为研究性质（如韩剧字幕翻译研究），与舆情监测核心业务无直接关联。
- **E 类判定**：祖先分支，但与同组另一分支指向完全相同的 commit（重复变体 / 自动保存 / final2/final3 冗余）。
- **F 类判定**：非祖先，且 diff 中检测到 P0 风险（主体口径弱化、数据库破坏性操作、硬编码密钥等）。

### 2.2 去重规则

本地分支与 `origin/<同名>` 分支若 `git rev-parse` 指向同一 commit，则视为同一唯一分支，在详情表中以 `[local+remote]` 标记。

---

## 3. 非祖先分支深度分析（5 个唯一分支）

> 以下 5 个分支是本次审计的核心关注对象。所有结论均基于 `git log main..branch` 和 `git diff main...branch` 的真实输出。

### 3.1 B 类：feat/lumenis-p0-p1-source-convergence

| 属性 | 值 |
|------|-----|
| 分支名 | `feat/lumenis-p0-p1-source-convergence` `[local+remote]` |
| 分类 | **B** — main 部分吸收 |
| 独有 commit 数 | 7 |
| 最后提交 | 2026-09-05 20:41:54 |
| merge-base | `6f15bac5cd0f` |
| 独有文件数 | 17 |
| 产品价值 | **中高** — LUMENIS 前端页面真实 API 绑定 + OSAI 跨核心调用链 + CI 修复 |
| 建议动作 | **建议合并**（需先 rebase 到最新 main，解决 132 个 behind commit） |

**独有 commit 清单**：

| Hash | 提交信息 | 价值评估 |
|------|----------|----------|
| `12350af` | feat(ui): bind 6 remaining LUMENIS pages to real APIs | 高 — 6 个页面从 mock 切换到真实 API |
| `b46cb98` | feat(ui): bind reports page to real daily_reports DB | 高 — 报告页接入真实数据库 |
| `1c4c443` | feat(ui): bind production cases and monitoring pages to real ZBC APIs | 中高 — 生产案例/监控页 API 绑定 |
| `93ccc12` | feat(cross-core): complete ZBC->OSAI invoke chain - VERIFY auth + 60s timeout | 中 — 跨核心调用链完善 |
| `904df01` | feat(cross-core): connect ZBC skill invoke to real OSAI SkillInvoker | 中 — Skill 调用器集成 |
| `be8b025` | ci(closeout): CI真正执行pytest + 双__main__块注释 + 迁移权威路径文档 + event_graph接入决策 | 中 — CI 修复 + 文档 |
| `b04c1e3` | test(audit): 新增序境OSAI边界与启动审计测试（TEST-01/02/05/06/07/09/10/20） | 中 — 新增 347 行审计测试 |

**独有关键文件**：
- `lumenis_frontend.py`（+144 行）— 前端 API 绑定核心
- `lumenis_skill_adapter.py`（+64 行）— OSAI Skill 适配器
- `tests/test_osai_boundary_audit.py`（+347 行，新增）— OSAI 边界审计测试
- `app.py`（+11 行）— 仅添加双 `__main__` 块注释，无实质性代码修改
- `docs/DATABASE_MIGRATION_AUTHORITY.md`（+62 行，新增）— 迁移权威路径文档
- `templates/production/*.html`（3 个模板，共 +348 行）— 生产页面模板
- `.github/workflows/platform-verify.yml`（±2 行）— CI 配置

**风险评估**：
- 主体口径：**无影响** — app.py 仅添加注释，`_subject_sql_and_values()` 未被修改
- 数据库：**无破坏性操作** — 仅文档，无 DDL/DML
- 密钥：**无硬编码** — 检测到的 `API_KEY` 关键词均为环境变量名称枚举（安全配置检测代码）
- 结论：**低风险，可合并**

---

### 3.2 B 类：origin/feat/lumenis-product-convergence

| 属性 | 值 |
|------|-----|
| 分支名 | `origin/feat/lumenis-product-convergence` |
| 分类 | **B** — main 部分吸收 |
| 独有 commit 数 | 4 |
| 最后提交 | 2026-09-06 04:37:06 |
| merge-base | `d7236f26d946` |
| 独有文件数 | 4 |
| 产品价值 | **中** — 含一个重要 bug 修复（移除硬编码数据库路径）+ 产品收敛文档 |
| 建议动作 | **建议合并**（优先合并 `auth_recovery_center.py` 修复，文档可选） |

**独有 commit 清单**：

| Hash | 提交信息 | 价值评估 |
|------|----------|----------|
| `0c9c198` | docs: record 2026-09-06 product convergence start | 低 — 文档记录 |
| `69ddb45` | docs: align README with product convergence master baseline | 低 — README 更新 |
| `f0940d9` | docs: add product convergence master execution baseline | 低 — 治理文档 |
| `59055bb` | **fix: remove production hardcoded auth recovery database path** | **高 — P0  bug 修复** |

**独有文件及差异**：

| 文件 | 变化 | 说明 |
|------|------|------|
| `auth_recovery_center.py` | ±13 行 | **核心修复**：将硬编码 `DB_PATH = r'D:\Taikoo-monitor-new\data\monitor.db'` 改为 `from database import DB_PATH`，消除开发机路径依赖 |
| `00-GOVERNANCE/LUMENIS-PRODUCT-CONVERGENCE-MASTER-V1-20260906.md` | +83 行（新增） | 产品收敛治理文档 |
| `CHANGELOG/2026-09-06-LUMENIS-PRODUCT-CONVERGENCE.md` | +32 行（新增） | 变更日志 |
| `README.md` | ±200 行 | README 对齐产品架构 |

**风险评估**：
- 主体口径：无影响
- 数据库：**修复硬编码路径**，是安全性改进
- 密钥：无
- 结论：**低风险，建议优先合并 auth_recovery_center.py 的修复**

---

### 3.3 C 类：origin/feat/lumenis-product-convergence-docs-final3

| 属性 | 值 |
|------|-----|
| 分支名 | `origin/feat/lumenis-product-convergence-docs-final3` |
| 分类 | **C** — main 未吸收但存在有效文档资产 |
| 独有 commit 数 | 2 |
| 最后提交 | 2026-09-06 04:35:44 |
| merge-base | `d7236f26d946` |
| 独有文件数 | 2 |
| 产品价值 | **低-中** — 纯文档资产，无代码变化 |
| 建议动作 | **可选合并文档**，分支本身可标记删除候选 |

**独有 commit**：
- `7a82add` — docs: align README with product convergence master baseline
- `9f1f0ec` — docs: establish product convergence master execution baseline

**独有文件**：
- `00-GOVERNANCE/LUMENIS-PRODUCT-CONVERGENCE-MASTER-V1-20260906.md`（+110 行）
- `README.md`（±201 行）

> 注意：此分支与 `origin/feat/lumenis-product-convergence` 的文档部分高度重叠。若合并 B 类分支，则此分支的文档资产已被覆盖。

---

### 3.4 D 类：origin/research/kdrama-fansub-study-20260903-final

| 属性 | 值 |
|------|-----|
| 分支名 | `origin/research/kdrama-fansub-study-20260903-final` |
| 分类 | **D** — research / experimental |
| 独有 commit 数 | 1 |
| 最后提交 | 2026-09-03 14:34:25 |
| merge-base | `b4ba2a89da28` |
| 独有文件数 | 1 |
| 产品价值 | **低** — 韩剧字幕翻译研究文档，与舆情监测核心业务无关 |
| 建议动作 | **转为正式文档资产或删除候选**，不建议合并到生产 main |

**独有 commit**：
- `10dd7c4` — docs: add K-drama fansub and Chinese subtitle translation study 2023-2026

**独有文件**：
- `docs/content-learning/KDRAMA_FANSUB_TRANSLATION_STUDY_2023_2026.md`（+92 行）

---

### 3.5 F 类：feat/zbc-full-upgrade-v1 ⚠️ 风险待审

| 属性 | 值 |
|------|-----|
| 分支名 | `feat/zbc-full-upgrade-v1` `[local+remote]` |
| 分类 | **F** — conflict / risk（主体口径弱化） |
| 独有 commit 数 | 11 |
| 最后提交 | 2026-09-06 13:36:55 |
| merge-base | `045d04259b4e` |
| 独有文件数 | 142 |
| diff 规模 | **+144,716 / -615 行** |
| 产品价值 | **高** — PermissionGate / Runtime Guardian / Repository Registry / 证据链 / 历史数据导入 / 大量审计测试 |
| 建议动作 | **禁止直接合并** — 必须先修复主体口径弱化问题，再逐模块评估合并 |

**独有 commit 清单**：

| Hash | 提交信息 | 说明 |
|------|----------|------|
| `0e1ff9a` | fix: resolve test failures from phase upgrades | 测试修复 |
| `d4485f6` | v5.9.9 自动保存版本（13:31 巡检） | 自动保存 |
| `f35c110` | feat(P0-P1): PermissionGate接入app.py写操作 + Evidence链完善 + 历史数据导入 | 核心功能 |
| `c5e48b2` | Shard E Batch3: Operations+Edge module verification (149 modules, 1222 functions) | 模块验证 |
| `dbbf986` | merge: resolve conflicts with remote auto-save | 冲突解决 |
| `431572c` | feat(P1-P2): Phase11-17 模块验证+API+SkillAgent+UI+Historical+CodeQuality | 多阶段升级 |
| `2b6a3f3` | Shard D Batch2: 智能+安全模块逐函数验证 (177 PARTIAL第二批) | 模块验证 |
| `fd96bb6` | feat(P1): Collector+Risk+AI+Evidence+Report+Evaluation 六阶段审计加固 | 审计加固 |
| `4501ff6` | v5.9.9 自动保存版本（12:23 巡检） | 自动保存 |
| `2775ed7` | feat(P0): Repository Registry + Runtime Guardian + PermissionGate + DB空表分类 | P0 功能 |
| `e9ef5ad` | feat(P0): Repository Registry + Runtime Guardian + PermissionGate + DB空表分类 | P0 功能（重复？） |

#### ⚠️ P0 风险：移除 `_subject_sql_and_values()` 主体过滤，违反广州太古汇主体口径 P0 红线

**风险等级**：P0 / CRITICAL
**风险类型**：主体口径弱化（统计查询移除主体词过滤）
**违反条款**：AGENTS.md 第 5 节「广州太古汇主体口径：P0 不得弱化」——必须保护 `app.py` / `risk_engine.py` 中 `_subject_sql_and_values()` 的所有下游 SQL 过滤。

**精确证据**（`git diff main...feat/zbc-full-upgrade-v1 -- app.py`）：

在 `app.py` 中检测到 **9 处 `_subject_sql_and_values()` 调用被移除**，分布在 **5 个核心统计函数**中：

| # | 受影响函数 | main 行号 | 移除的变量 | 原过滤条件 | 分支中过滤条件 |
|---|-----------|----------|-----------|-----------|---------------|
| 1 | `api_publish_buckets_v570()` | L2334 | `_pb_clause, _pb_params` | `is_taikoo_verified=1 AND relevance_status!='irrelevant' AND {主体词SQL}` | 仅 `is_taikoo_verified=1` |
| 2 | `api_global_trends_v570()` | L2345 | `_tg_clause, _tg_params` | 同上 | 仅 `is_taikoo_verified=1` |
| 3 | `api_notes_library_v571()` | L2376 | `_subj_clause, _subj_params` | 同上 | 仅 `is_taikoo_verified=1` |
| 4 | `api_negative_stats()` | L2889 | `_nc, _np` | 同上 | 仅 `is_taikoo_verified=1` |
| 5 | `api_dashboard_all()` — overview | L4022 | `_ov_clause, _ov_params` | 同上 | 仅 `is_taikoo_verified=1` |
| 6 | `api_dashboard_all()` — stats | L4059 | `_st_clause, _st_params` | 同上 | 仅 `is_taikoo_verified=1` |
| 7 | `api_dashboard_all()` — risk_alerts | L4102 | `_ra_clause, _ra_params` | 同上 | 仅 `is_taikoo_verified=1` |
| 8 | `api_dashboard_all()` — hot_topics | L4102 | `_ht_clause, _ht_params` | 同上 | 仅 `is_taikoo_verified=1` |
| 9 | `api_dashboard_all()` — pending_negative | L4153 | `_pn_clause, _pn_params` | 同上 | 仅 `is_taikoo_verified=1` |

**diff 摘录**（以 `api_publish_buckets_v570()` 为例）：
```diff
@@ -2368,10 +2334,8 @@ def api_brand_industry_run_v570():
 def api_publish_buckets_v570():
-        _pb_clause, _pb_params = _subject_sql_and_values()
-        _pb_base = f"is_taikoo_verified=1 AND COALESCE(relevance_status,'relevant')!='irrelevant' AND {_pb_clause}"
-        same=[dict(r) for r in conn.execute(f"SELECT * FROM notes WHERE {_pb_base} AND substr(COALESCE(publish_datetime,publish_date),1,10)=? ORDER BY collected_at DESC", tuple(_pb_params)+(date,)).fetchall()]
+        same=[dict(r) for r in conn.execute("SELECT * FROM notes WHERE is_taikoo_verified=1 AND substr(COALESCE(publish_datetime,publish_date),1,10)=? ORDER BY collected_at DESC",(date,)).fetchall()]
```

**未受影响的文件**（经 `git diff` 确认无变化）：
- `subject_rules.py` — **无变化**，`SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` / `subject_hit()` / `subject_sql_and_values()` 定义完整保留
- `risk_engine.py` — **无变化**
- `reprocess.py` — **无变化**，`aggregate_events()` / `build_cross_platform_events()` 主体过滤完整

**缓解因素（不构成豁免理由）**：
- `_subject_sql_and_values()` 函数本身仍存在（分支中保留 9 处其他调用，与 main 相同）
- `is_taikoo_verified=1` 标记在数据入库时通过 `subject_hit()` 设置，提供一层基础过滤
- 但 `_subject_sql_and_values()` 包含 `SUBJECT_WORDS` 多字段 OR 匹配 + `SUBJECT_EXCLUDE_WORDS` 一票否决的细粒度逻辑，仅靠 `is_taikoo_verified` 可能导致：
  - 历史数据中 `is_taikoo_verified` 标记不一致的笔记被错误纳入
  - `relevance_status='irrelevant'` 的笔记被错误纳入（原过滤有 `relevance_status!='irrelevant'` 条件）
  - 统计口径与日报/事件聚合不一致（日报/事件聚合仍使用完整主体过滤）

**🔒 Capability-Level Selective Recovery 策略**：

此分支**禁止整体合并**。即使包含 PermissionGate / Runtime Guardian 等高价值资产，也只允许逐功能挑选（selective recovery），且遵守以下硬约束：

1. **主体过滤相关代码一律不得回收进 main** —— 包括但不限于 `app.py` 中上述 9 处被修改的查询、任何弱化 `_subject_sql_and_values()` 的变更、任何移除 `relevance_status` 过滤的变更
2. **可选择性回收的资产**（需单独 cherry-pick 并通过主体口径回归测试）：
   - `permission_gate.py` / `ad_intelligence/permission_gate.py` — 权限门控
   - `runtime_guardian.py` — 运行时守护
   - `repository_registry.py` / `core/repository_registry.py` — 仓库注册
   - `evidence_chain.py` / `evidence_store.py` — 证据链
   - `historical_data_importer.py` — 历史数据导入
   - `security_boundary.py` / `safety_boundary.py` — 安全边界
   - 对应的单元测试文件
3. **禁止回收的资产**：
   - `app.py` 中任何涉及主体过滤的修改
   - `audit/_*.json` / `audit/_*.py` 中间产物
   - `tests_*_result.txt` 测试输出垃圾
4. **每个选择性回收的子模块必须**：
   - 独立 cherry-pick 到新分支
   - 通过主体口径回归测试（dashboard / trends / notes_library / negative_stats 数值与 main 一致）
   - 不引入对弱化版查询的依赖

**其他风险检查**：
- 数据库迁移：**安全** — 所有变更为 `ALTER TABLE ADD COLUMN`（向后兼容）和 `CREATE TABLE IF NOT EXISTS`，无 `DROP TABLE` / `DELETE FROM` 实际执行
- 检测到的 `DROP TABLE` / `TRUNCATE` / `DELETE FROM` 关键词均为 `permission_gate.py` / `security_boundary.py` 中的**安全黑名单定义**（用于拦截危险操作），非实际执行
- 硬编码密钥：**无** — 检测到的 `token_usage` / `API_KEY` 均为变量名或环境变量枚举
- 审计垃圾文件：分支包含大量 `audit/_*.json`（如 `_module_scan_raw.json` 56,321 行）/ `audit/_*.py` / `tests_*_result.txt` 等中间产物，合并前必须清理

**合并前置条件（如未来考虑整体合并）**：
1. 恢复 9 处被移除的 `_subject_sql_and_values()` 调用（含 `relevance_status!='irrelevant'` 条件）
2. 清理 `audit/` 目录下的 `_` 前缀中间文件和 `tests_*_result.txt`
3. 逐模块 rebase 到最新 main（当前 behind 84 commits）
4. 主体口径回归测试通过（dashboard/trends/notes_library/negative_stats 数值与 main 完全一致）

---

## 4. A 类分支详情（28 个 — 已完整进入 main）

> 以下分支均通过 `git merge-base --is-ancestor` 确认为 main 的祖先，`git log main..branch` 为空，`git diff main...branch` 无实质差异。

| # | 分支名 | 最后提交时间 | 最后提交信息（截断） | 独有文件 |
|---|--------|-------------|---------------------|----------|
| 1 | `feat/keyboard-shortcuts-modal` `[local+remote]` | 2026-09-01 16:35 | feat(ui): 新增键盘快捷键帮助窗口 | 0 |
| 2 | `feat/lumenis-internal-beta-closure` `[local+remote]` | 2026-09-06 02:12 | v5.9.9 自动保存版本（02:12 巡检） | 0 |
| 3 | `feat/lumenis-p0-convergence` `[local+remote]` | 2026-09-05 05:30 | v5.9.9 自动保存版本（05:30 巡检） | 0 |
| 4 | `feat/lumenis-p1-full-product-ui` `[local+remote]` | 2026-09-05 15:49 | feat(p1): LUMENIS Full Product Visual Foundation | 0 |
| 5 | `feat/lumenis-phase2-foundation` `[local+remote]` | 2026-09-05 13:53 | feat(collectors): 多平台采集全能力升级 | 0 |
| 6 | `feat/lumenis-phase3-runtime-ui` `[local+remote]` | 2026-09-05 14:20 | feat(zhihu): 知乎采集改用浏览器CDP模式 | 0 |
| 7 | `feat/lumenis-phase3-skill-runtime` `[local+remote]` | 2026-09-05 14:39 | chore: 补全ad_intelligence子包和tests的__init__.py | 0 |
| 8 | `feat/lumenis-v2-domain-convergence` `[local only]` | 2026-09-06 05:43 | v5.9.9 自动保存版本（05:43 巡检） | 0 |
| 9 | `feat/lumenis-v3-risk-fix` `[local+remote]` | 2026-09-05 14:59 | V3 risk fix: ZBC Skill Hub backend API | 0 |
| 10 | `feat/zb-runtime-preflight` `[local+remote]` | 2026-09-01 11:00 | docs(audit): ZB-RUNTIME-PREFLIGHT-001 独立审计报告 | 0 |
| 11 | `lumenis-dual-domain-v3` `[local+remote]` | 2026-09-07 04:47 | v5.9.9 自动保存版本（04:47 巡检） | 0 |
| 12 | `lumenis-full-refinement-v2` `[local+remote]` | 2026-09-06 15:38 | refinement: final audit script and command_home fixes | 0 |
| 13 | `lumenis-full-runtime-convergence` `[local+remote]` | 2026-09-06 15:06 | docs: finalize audit report with PR #27 | 0 |
| 14 | `ui/staging-foundation` `[local+remote]` | 2026-09-01 17:57 | docs(ui): merge-to-main evidence | 0 |
| 15 | `origin/aqrjrr-codex/-zbc` | 2026-09-06 13:27 | feat: add lease-based runtime guardian | 0 |
| 16 | `origin/codex` | 2026-09-06 13:11 | fix: make test initialization safe and portable | 0 |
| 17 | `origin/docs/engineering-loop-contract-v1` | 2026-09-05 02:36 | docs: add bounded engineering loop contract | 0 |
| 18 | `origin/feat/i18n-ko-en-zh-v6`（i18n 组代表） | 2026-09-03 14:11 | feat(engine): 高奢克制叙事句库4组 + 创意工作台前端 | 0 |
| 19 | `origin/feat/lumenis-product-convergence-docs`（docs 组代表） | 2026-09-06 04:12 | v5.9.9 自动保存版本（04:12 巡检） | 0 |
| 20 | `origin/feat/lumenis-v2-domain-convergence-readme-followup` | 2026-09-06 04:40 | docs: fully converge ZBC README | 0 |
| 21 | `origin/feat/podcast-table-system-v1`（podcast 组代表） | 2026-09-03 20:07 | feat(podcast): add deterministic content yield planner | 0 |
| 22 | `origin/feat/system-fusion-first-instruction`（fusion 组代表） | 2026-09-05 04:05 | docs: add LUMENIS engineering governance | 0 |
| 23 | `origin/fusion-exec`（fusion-exec 组代表） | 2026-09-05 04:05 | docs: add LUMENIS engineering governance | 0 |
| 24 | `origin/integration/rd-data-function-ui-baseline` | 2026-09-04 06:43 | governance: lock synchronized ZBP and CTH completion gate | 0 |
| 25 | `origin/p0-continuation-audit`（p0-cont 组代表） | 2026-09-06 13:27 | Merge pull request #26 from Zachary-1012/aqrjrr-codex/-zbc | 0 |
| 26 | `origin/research/context-intelligence-20260901` | 2026-09-01 21:35 | test(intelligence): cover context and comment event signals | 0 |
| 27 | `origin/research/zachary-ai-context-convergence-20260901` | 2026-09-02 21:53 | merge(research): resolve conflict - keep main's test | 0 |
| 28 | `origin/system-fusion-first-execution-20260905`（exec 组代表） | 2026-09-05 04:05 | docs: add LUMENIS engineering governance | 0 |

**A 类证据确认**：所有 28 个分支均满足 `is_ancestor=true` + `ahead_count=0` + `unique_file_count=0`。

---

## 5. D 类分支详情（3 个 — research / experimental）

| # | 分支名 | 最后提交 | 独有 commit | 独有文件 | 内容性质 | 建议 |
|---|--------|---------|------------|----------|----------|------|
| 1 | `origin/research/kdrama-fansub-study`（study 组代表） | 2026-09-03 14:29 | 0（已合并） | 0 | 韩剧对白研究文档，已进入 main | 保留参考，分支可删 |
| 2 | `origin/research/kdrama-fansub-study-20260903-final` | 2026-09-03 14:34 | 1 | 1 | 韩剧字幕翻译研究文档（+92行），未合并 | 转为 docs/content-learning/ 正式资产或删除 |
| 3 | `origin/research/kdrama-fansub-translation-2023-2026`（translation 组代表） | 2026-09-03 14:29 | 0（已合并） | 0 | 韩剧字幕翻译研究，已进入 main | 保留参考，分支可删 |

> D 类分支内容与 Z-Brand 舆情监测核心业务（广州太古汇品牌传播/市场情报）无直接关联，属于旁支研究。建议将有价值的研究文档归档到 `docs/content-learning/` 后删除分支。

---

## 6. E 类分支详情（62 个 — stale 重复变体）

> 以下分支均为已合并分支的重复变体（与同组代表分支指向完全相同的 commit），无独有资产。全部标记为**删除候选**（仅记录，不执行删除）。

### 6.1 i18n 系列重复变体（7 个）

均与 `origin/feat/i18n-ko-en-zh-v6` 指向同一 commit（`4cb2cc19fdde`，2026-09-03 14:11:58）：

- `origin/feat/i18n-ko-en-zh-v6-impl`
- `origin/feat/i18n-ko-en-zh-v6-impl2`
- `origin/feat/i18n-ko-en-zh-v6-impl3`
- `origin/feat/i18n-ko-en-zh-v6-research`
- `origin/feat/i18n-ko-en-zh-v6-research-final`
- `origin/feat/i18n-ko-en-zh-v6-research-final2`
- `origin/feat/i18n-ko-en-zh-v6-research-final3`

### 6.2 product-convergence-docs 重复变体（7 个）

均与 `origin/feat/lumenis-product-convergence-docs` 指向同一 commit（`d7236f26d946`，2026-09-06 04:12:18）：

- `origin/feat/lumenis-product-convergence-docs-final`
- `origin/feat/lumenis-product-convergence-docs-final2`
- `origin/feat/lumenis-product-convergence-docs-final4`
- `origin/feat/lumenis-product-convergence-docs-final5`
- `origin/feat/lumenis-product-convergence-docs2`
- `origin/feat/lumenis-product-convergence-docs3`
- `origin/feat/lumenis-product-convergence-docs4`

### 6.3 podcast 系列重复变体（6 个）

均与 `origin/feat/podcast-table-system-v1` 指向同一 commit（`206ca6c751bf`，2026-09-03 20:07:07）：

- `origin/feat/podcast-table-system-v2` ～ `origin/feat/podcast-table-system-v7`

### 6.4 system-fusion-first-instruction 重复变体（5 个）

均与 `origin/feat/system-fusion-first-instruction` 指向同一 commit（`511b819d8c2a`，2026-09-05 04:05:48）：

- `origin/feat/system-fusion-first-instruction-20260905`
- `origin/feat/system-fusion-first-instruction-20260905-b`
- `origin/feat/system-fusion-first-instruction-final`
- `origin/feat/system-fusion-first-instruction-final2`
- `origin/feat/system-fusion-first-instruction-v1`

### 6.5 fusion-exec 重复变体（6 个）

均与 `origin/fusion-exec` 指向同一 commit（`511b819d8c2a`，2026-09-05 04:05:48）：

- `origin/fusion-exec-2` ～ `origin/fusion-exec-7`

### 6.6 p0-continuation 重复变体（1 个）

- `origin/p0-continuation-full-audit`（与 `origin/p0-continuation-audit` 同一 commit）

### 6.7 system-fusion-first-execution 重复变体（1 个）

- `origin/system-fusion-first-execution-20260905-x`（与 `origin/system-fusion-first-execution-20260905` 同一 commit）

### 6.8 kdrama-fansub-study 重复变体（13 个）

均与 `origin/research/kdrama-fansub-study` 指向同一 commit（`b4ba2a89da28`，2026-09-03 14:29:49），`-20260903-final` 除外（D 类）：

- `origin/research/kdrama-fansub-study-20260903`
- `origin/research/kdrama-fansub-study-20260903-a`
- `origin/research/kdrama-fansub-study-final-2` ～ `origin/research/kdrama-fansub-study-final-12`（共 11 个）

### 6.9 kdrama-fansub-translation 重复变体（16 个）

均与 `origin/research/kdrama-fansub-translation-2023-2026` 指向同一 commit（`b4ba2a89da28`，2026-09-03 14:29:49）：

- `origin/research/kdrama-fansub-translation-2023-2026-01` ～ `-10`（10 个）
- `origin/research/kdrama-fansub-translation-2023-2026-final`
- `origin/research/kdrama-fansub-translation-2023-2026-research`
- `origin/research/kdrama-fansub-translation-2023-2026-research2`
- `origin/research/kdrama-fansub-translation-2023-2026-v2` ～ `-v4`（3 个）

**E 类小计**：7 + 7 + 6 + 5 + 6 + 1 + 1 + 13 + 16 = **62 个**

---

## 7. Merge Candidates 清单（建议合并，3 个）

> 以下分支建议在满足前置条件后合并。**仅建议，不执行。**

### MC-1：feat/lumenis-p0-p1-source-convergence（优先级：高）

- **分类**：B
- **需合并的增量**：7 个 commits（`b04c1e3` → `12350af`），17 个文件
- **核心价值**：
  - LUMENIS 6 个前端页面绑定真实 API（`lumenis_frontend.py` +144 行）
  - 报告页接入 `daily_reports` 真实数据库
  - ZBC → OSAI 跨核心 Skill 调用链（`lumenis_skill_adapter.py` +64 行）
  - OSAI 边界审计测试（`tests/test_osai_boundary_audit.py` +347 行）
  - CI 真正执行 pytest
- **前置条件**：rebase 到最新 main（behind 132 commits），解决冲突后回归测试
- **风险**：低

### MC-2：origin/feat/lumenis-product-convergence（优先级：高，仅代码部分）

- **分类**：B
- **需合并的增量**：重点合并 commit `59055bb`（auth_recovery_center.py 硬编码路径修复）
- **核心价值**：
  - **P0 bug 修复**：`auth_recovery_center.py` 中将硬编码开发机路径 `D:\Taikoo-monitor-new\data\monitor.db` 改为统一从 `database.DB_PATH` 导入
  - 产品收敛治理文档（可选）
- **前置条件**：无，可直接 cherry-pick `59055bb`
- **风险**：无（是安全性修复）

### MC-3：origin/feat/lumenis-product-convergence-docs-final3（优先级：低，可选）

- **分类**：C
- **需合并的增量**：2 个 commits，2 个文档文件
- **核心价值**：产品收敛 master 文档 + README 对齐
- **前置条件**：若已合并 MC-2，则文档部分已覆盖，此分支可跳过
- **风险**：无

---

## 8. Deletion Candidates 清单（建议删除候选，90 个）

> **仅记录，不执行删除。** 所有删除操作需用户明确授权后通过 `git branch -d` / `git push origin --delete` 执行。

### 8.1 A 类已合并分支（28 个）— 可安全删除

所有 A 类分支内容已完全进入 main，删除不影响任何代码资产。建议保留最近 1-2 个活跃分支作为回滚参考，其余可清理。

（完整列表见第 4 节）

### 8.2 E 类重复变体（62 个）— 强烈建议删除

所有 E 类分支与同组代表分支指向完全相同的 commit，无任何独有资产。建议批量删除。

（完整列表见第 6 节）

**删除候选总计**：28（A）+ 62（E）= **90 个**

> 注意：D 类中的 2 个已合并研究分支（`kdrama-fansub-study`、`kdrama-fansub-translation-2023-2026`）也可纳入删除候选，但建议先确认研究文档已在 main 中归档。若纳入，删除候选总数为 92。

---

## 9. Unresolved Conflicts 清单（F 类，1 个）

> **禁止自动处理。** 以下分支存在 P0 风险，必须人工审查后决定。

### UC-1：feat/zbc-full-upgrade-v1 ⚠️

- **风险类型**：主体口径弱化（P0）
- **冲突点**：`app.py` 中 9 处 `_subject_sql_and_values()` 调用被移除，涉及 `api_dashboard_all()`、`api_global_trends_v570()`、`api_notes_library_v571()`、`api_negative_stats()`、`api_brand_industry_*()` 等核心统计路由
- **危险内容**：统计查询从 `is_taikoo_verified=1 AND relevance_status!='irrelevant' AND {主体词过滤}` 弱化为仅 `is_taikoo_verified=1`
- **来源**：分支 `f35c110` / `fd96bb6` 等 P0-P1 升级 commit 中引入
- **其他问题**：
  - 包含大量 `audit/_*.json` 中间产物（如 `_module_scan_raw.json` 56,321 行）
  - 包含 `tests_*_result.txt` 测试输出垃圾文件
  - behind main 84 个 commits，rebase 冲突面大
- **产品价值**：高（PermissionGate / Runtime Guardian / 证据链 / 历史数据导入）
- **处理建议**：
  1. **禁止直接 merge**
  2. 先恢复主体过滤（9 处 `_subject_sql_and_values()`）
  3. 清理审计中间文件
  4. 拆分为独立子分支逐模块合并（PermissionGate → Runtime Guardian → 证据链 → 历史数据导入）
  5. 每个子分支单独做主体口径回归测试

---

## 10. 审计结论与建议

### 10.1 关键发现

1. **仓库分支冗余严重**：97 个唯一分支中 62 个（63.9%）是重复变体，建议批量清理。
2. **5 个非祖先分支中，1 个有 P0 风险**：`feat/zbc-full-upgrade-v1` 弱化了广州太古汇主体口径，必须修复后才能合并。
3. **2 个分支有立即合并价值**：
   - `feat/lumenis-p0-p1-source-convergence`（前端 API 绑定 + OSAI 集成）
   - `origin/feat/lumenis-product-convergence`（auth_recovery_center 硬编码路径修复）
4. **研究分支与核心业务无关**：韩剧字幕翻译研究系列（34 个分支）建议归档文档后清理。
5. **自动保存巡检分支泛滥**：多个 lumenis 分支的最后 commit 是"v5.9.9 自动保存版本"，建议建立自动保存分支的生命周期管理策略。

### 10.2 建议执行顺序

1. **立即**：cherry-pick `59055bb`（auth_recovery_center 硬编码路径修复）到 main
2. **短期**：rebase 并合并 `feat/lumenis-p0-p1-source-convergence`
3. **中期**：拆分 `feat/zbc-full-upgrade-v1`，修复主体口径后逐模块合并
4. **清理**：批量删除 62 个 E 类重复变体 + 28 个 A 类已合并分支
5. **治理**：建立分支命名规范和自动过期策略，避免 final2/final3/v2/v3 式冗余

### 10.3 证据文件

- 原始分支数据：`audit/convergence/raw_branch_data.json`
- 非祖先分支深度分析：`audit/convergence/deep_analysis.json`
- 审计脚本：`audit/convergence/audit_branches.py`、`audit/convergence/deep_analyze.py`

---

## 11. Main Subject 链路完整性验证

> 本节独立验证 main 分支（HEAD=`d72153fa`）当前的主体过滤链路是否完整，作为 F 类分支风险的对照基线。验证方法：`git show main:<file>` + `git grep -n` 只读检查。

### 11.1 验证结论

| 链路节点 | 位置 | 状态 | 证据 |
|----------|------|------|------|
| `SUBJECT_WORDS` 词表 | `subject_rules.py` | ✅ 完整 | 词表存在，含多组主体词 |
| `SUBJECT_EXCLUDE_WORDS` 排除词表 | `subject_rules.py` | ✅ 完整 | 一票否决排除词表存在 |
| `subject_hit()` 函数 | `subject_rules.py` | ✅ 完整 | 五字段任一命中 + 排除词一票否决逻辑存在 |
| `subject_sql_and_values()` 函数 | `subject_rules.py` | ✅ 完整 | SQL 子句生成函数存在 |
| `_subject_sql_and_values()` 包装器 | `app.py` | ✅ 完整 | 定义存在，共 **9 处**调用（含定义） |
| `aggregate_events()` 事件聚合 | `reprocess.py:153` | ✅ 完整 | 受保护兼容名 → 委托 `build_cross_platform_events()` |
| `build_cross_platform_events()` 权威实现 | `reprocess.py:109` | ✅ 完整 | 使用 `db.get_notes({'verified':True}, 2000, 0)` 只消费已验证笔记 |
| `build_daily_report()` 日报入口 | `risk_engine.py:296` | ✅ 完整 | 纯委托 → `daily_report.generate_daily_digest()` |
| `generate_daily_digest()` 日报生成 | `daily_report.py:558` | ✅ 完整 | 通过 `db.get_notes_by_date_range()` + `db.get_events()` 获取主体过滤后数据 |

### 11.2 关键链路详情

#### 11.2.1 入库时主体标记（数据层）

`app.py` 中数据入库时通过 `subject_hit()` 设置 `is_taikoo_verified`：
```python
n['is_taikoo_verified']=1 if ok else 0
```
其中 `ok` 来自 `subject_hit(full_text)` 的返回值。这确保了进入数据库的笔记已通过主体词过滤。

#### 11.2.2 查询时主体过滤（应用层）

`app.py` 中 `_subject_sql_and_values()` 被 9 处核心查询调用，包括：
- 仪表盘总览（`api_dashboard_all()`）
- 全局趋势（`api_global_trends_v570()`）
- 笔记库（`api_notes_library_v571()`）
- 负面统计（`api_negative_stats()`）
- 发布桶统计（`api_publish_buckets_v570()`）
- AI 分析队列（未分析笔记筛选）

每个查询的过滤条件为：
```sql
is_taikoo_verified=1 AND COALESCE(relevance_status,'relevant')!='irrelevant' AND {主体词SQL子句}
```

#### 11.2.3 事件聚合主体过滤

`reprocess.py` 中 `build_cross_platform_events()` 的口径红线（代码注释明确标注）：
```python
# 口径红线（不得弱化）：
#   1) 只消费 is_taikoo_verified=1 的笔记与已验证 web mention（主体硬过滤后的输入）；
#   2) risk_level/risk_score 来自数据（risk_score 取 max、负面计数），AI 仅 summarize/translate 增强；
#   3) 发布时间与采集时间分别用于 first/last_seen，不得混淆。
```
实际查询：`db.get_notes({'verified':True}, 2000, 0)` — `verified=True` 对应 `is_taikoo_verified=1`。

#### 11.2.4 日报主体过滤

`risk_engine.py:296`：
```python
def build_daily_report(date_str=None):
    return daily_report.generate_daily_digest(date_str)
```
`daily_report.py:558` 的 `generate_daily_digest()` 通过 `db.get_notes_by_date_range()` 和 `db.get_events()` 获取数据，这两个数据库层函数内置 `is_taikoo_verified=1` 过滤。

### 11.3 与 F 类分支的对比

| 维度 | main（当前） | feat/zbc-full-upgrade-v1 |
|------|-------------|--------------------------|
| `subject_rules.py` | 完整 | **无变化**（完整） |
| `app.py` 中 `_subject_sql_and_values()` 调用数 | 9 处 | 9 处（但**分布不同**：5 个统计函数中的 9 处被移除，其他位置保留） |
| `api_dashboard_all()` 主体过滤 | 完整（5 处调用） | **被移除**（5 处全部移除） |
| `api_global_trends_v570()` 主体过滤 | 完整 | **被移除** |
| `api_notes_library_v571()` 主体过滤 | 完整 | **被移除** |
| `api_negative_stats()` 主体过滤 | 完整 | **被移除** |
| `api_publish_buckets_v570()` 主体过滤 | 完整 | **被移除** |
| `relevance_status!='irrelevant'` 条件 | 存在 | **被移除** |
| `aggregate_events()` / `build_cross_platform_events()` | 完整 | **无变化**（完整） |
| `build_daily_report()` / `generate_daily_digest()` | 完整 | **无变化**（完整） |

### 11.4 验证结论

**main 分支的 subject 链路完整且健康**。主体过滤在三个层面均有保障：
1. **入库层**：`subject_hit()` → `is_taikoo_verified` 标记
2. **查询层**：`_subject_sql_and_values()` → 9 处核心 SQL 查询
3. **聚合/报告层**：`build_cross_platform_events()` / `generate_daily_digest()` → 只消费已验证数据

**F 类分支 `feat/zbc-full-upgrade-v1` 的风险是局部的**：仅影响 `app.py` 中 5 个统计 API 函数的查询过滤，未触及 `subject_rules.py` 词表定义、`reprocess.py` 事件聚合、`daily_report.py` 日报生成。但这 5 个函数是仪表盘和趋势统计的核心入口，弱化后会导致前端展示数据与日报/事件数据口径不一致，属于 P0 风险。

---

*报告生成时间：2026-09-07 | 审计工具：git 2.x（只读模式）| 分类标准：A-F 六类收敛矩阵*
