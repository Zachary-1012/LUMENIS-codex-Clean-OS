# 序境｜DOUBAO_DELETE_REVIEW.md（豆包待人工删除清单）

> 状态：PENDING_HUMAN_REVIEW · NO-BLIND-DELETE
> 依据：《序境｜双子库全量收敛与产品研发总执行指令》第二十七/二十八/四十五节
> 日期：2026-09-04
> 规则：无法证明安全的文件一律不删除，进入本清单等待人工确认。删除前必须通过引用扫描 → 运行时依赖 → 测试 → Git 历史 → 确认无依赖。

---

## 一、根目录临时脚本（无生产引用，疑似一次性诊断）

| Path | Type | Reason | Reference Check | Runtime Dependency | Recommendation |
|---|---|---|---|---|---|
| `_reanalyze.py`（2.0KB, 2026-08-29） | Python 诊断脚本 | 一次性 ai_analyzer 数据诊断 | 无任何 .py 引用（grep 仅自引用） | 无（独立脚本） | ARCHIVE（git 已追踪）→ 人工确认后移入 99-ARCHIVE |
| `_pitch_dump.py`（3.3KB, 2026-09-03） | Python 诊断脚本 | 一次性 pitch dump 输出脚本 | 无任何 .py 引用 | 无（独立脚本） | ARCHIVE（未追踪）→ 人工确认后删除 |

## 二、根目录 .env 备份（含真实密钥，绝不可入库/外发）

| Path | Type | Reason | Reference Check | Runtime Dependency | Recommendation |
|---|---|---|---|---|---|
| `.env.bak-20260902`（7.1KB） | 环境变量备份 | 含真实 API Key/Cookie 配置 | 已 gitignore（.gitignore:163 `*.bak-*`） | 无（备份） | ARCHIVE → 人工确认后删除（本地保留一份即可） |
| `.env.bak-d7`（7.2KB） | 环境变量备份 | 同上 | 已 gitignore | 无（备份） | ARCHIVE → 人工确认后删除 |

## 三、app.py / 核心模块 .bak（git 已忽略，未入库）

> 均为开发过程备份，已被 gitignore（`*.bak-*`），不进入仓库；本地可择机清理，不影响任何运行。

| Path | Type | Reason | Recommendation |
|---|---|---|---|
| `app.py.bak-auth` / `app.py.bak-counter` / `app.py.bak-d3` / `app.py.bak-dualkeep` / `app.py.bak-guard` / `app.py.bak-zbc-logfix` / `app.py.bak_p0_20260902` / `app.py.bak_p0_20260902_094442` / `app.py.bak_zhipu_20260902` | 代码备份 | 开发期快照 | KEEP-本地（不删，成本极低；如需清理由人工决定） |
| `intelligence.py.bak-bizchat` / `.bak-efficient` / `.bak-vision` | 代码备份 | 高效层开发快照 | KEEP-本地（回滚锚点） |
| `kos_engine.py.bak-*`（5个）/ `kos_routes.py.bak-*`（4个）/ `run_supervised.py.bak-zbc-*`（4个）/ `topic_campaign.py.bak-zbc-insertfix*`（2个）/ `xhs_*.py.bak-*`（4个）/ `database_migrations.py.bak-hcg` / `subject_rules.py.bak-brand` / `xhs_cookie_search.js.bak-cdp` | 代码备份 | 各自模块开发快照 | KEEP-本地 |

## 四、结论

- **本次不执行任何 DELETE**：以上文件均无法当场证明"无任何历史 Evidence 价值"，全部保留/归档。
- 实际进入 git 仓库的仅有 `_reanalyze.py`（1 个），建议人工确认后归档。
- `.bak-*` 全部已在 .gitignore，不会污染仓库。
- 清理动作（删除/归档）仅在人工逐项确认后执行。
