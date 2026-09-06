# 双子库全面源码级审计报告 — 2026-09-03（零号序列执行）

> 基线：GitHub 双子库当前最新（ZBC `3032034` + 清理 commit `2b4fe22` / OSAI `ea553bd`）
> 方法：本地源码 + Git 跟踪状态双轨核验；事实优先级「GitHub 最新 > 本地源码 > 可运行状态 > Git Commit」
> 边界：序境-Core=Production Truth；序境-Intelligence=Research/AI；双库经 Contract/Evidence/Audit 协作

---

## 一、审计范围与口径

| 维度 | 覆盖 |
|---|---|
| 源码 | ZBC 924 个 .py（根目录 96 活跃模块 + collector_v2 25 + platform_adapters 18 + scripts 47 + browser_runtime 8） |
| 数据 | monitor.db 62 张表（事件/KOS/营销节点/Web/专题/审计全覆盖） |
| 契约 | contracts/global + contracts/kos 共 6 份 v1 契约 |
| 前端 | templates 5 页 + static 93 文件 |
| 依赖 | requirements.txt 31 项（含 waitress） |
| 治理 | 00-GOVERNANCE + AGENTS.md V2.0 + 零号序列 |

## 二、架构健康确认（PASS）

1. **一套 Core 无复制**：collector_v2（新一代独立入口 `python -m collector_v2.run_*`）与 collector_automation/web_monitor_v570 职责清晰；`ark_llm` 为 legacy 但 try/except 安全关闭（仅 import 无 `.` 调用），智谱为唯一外接 provider。
2. **版本一致 5.9.9**：VERSION / app.py APP_VERSION / package.json / base.html 页头页脚全对齐。
3. **品牌红线保留**：`ACTIVE_BRAND=guangzhou_taikoo_hui`（生产安全默认，不得弱化）；hainan_cdf 为可切换 profile（`ZBC_ACTIVE_BRAND` 生效），中免按配置品牌接入。
4. **密钥零入库**：`.env` 未跟踪；GitHub 跟踪清单仅 `.env.example`；本报告签署前已删除本地 `.env.bak-*` 密钥残留。
5. **DB 结构完整**：62 表覆盖事件/KOS/营销节点/Web 监测/专题/安全审计/证据链。
6. **实时采集链路已修复**：`collector_v2/pipeline/subject_filter.py` 已含模块级 `filter_subject(notes, subject_hit)`（用户并行线修复），live_engine ImportError 已闭合。

## 三、本轮已按规则生产（commit `2b4fe22`）

| 项 | 处置 | 依据 |
|---|---|---|
| 根目录 37 个 .bak 备份（app.py.bak-*×8、kos_engine.py.bak-*×6、kos_routes.py.bak-*×4、run_supervised.bak-*×4 等） | 归档 `archive/2026-09-backups/`（gitignore 拦截不入库，保留证据） | 零号序列「废弃资产统一归档，禁止污染生产路径」+ 已核实无 import 引用 |
| `.env.bak-20260902` / `.env.bak-d7`（含真实 API Key / Cookie / SMTP 密码） | **删除** | 用户已授权密钥/ Cookie 残留处置 + 安全红线「Cookie/Token/API Key 永不进仓库」 |
| `kos_engine.py.bak_zhipu_20260904`（我上轮施工备份被误跟踪） | `git rm` + 归档 | 备份无入库价值，保留本地证据 |
| `app_backup_v589.py`（251KB 根目录备份） | 归档 | 无引用备份 |
| `web_monitor_v570.py` | **保留** | 被 app.py L78/2730/2740 实际调用（活跃依赖） |

## 四、规则冲突发现（需用户确认，Zero Sequence 保护项）

### 🔴 GAP-A：专题采集频率超零号序列红线

- **零号序列（最新权威）**：自动采集每日 00:00 一次、12:00 一次，**每天最多 2 次**；其余全部默认手动（手动单次 ≤30min）。
- **生产实际**：
  - 主舆情：`auto_collect_hours=[8,10,12,14,16,18,20,22,23]` 仅作历史参考，实际由 **ShadowPlanner 门控**（`ZBC_SCHED_GATE_MODE=enforce`，GAP-05 用户签字 2026-09-02）动态决策 → **合规**。
  - 专题：`topic_campaign.py` **独立 daemon 线程** `CAMPAIGN_COLLECT_HOURS=[9,11,13,15,17,19]`（6 点/天），独立配额每日上限 8 次（含手动），不受 ShadowPlanner 门控 → **超红线（6-8 次/天 > 2 次/天）**。
- 依据：topic_campaign.py L4-6/81-82/644/764；app.py L4492/4506/4539-4549。
- **处置：已获本人显式授权例外（2026-09-03）** → 专题采集维持 6 点/天 [9,11,13,15,17,19] 独立配额（每日上限 8 次含手动）。授权已固化到 ZBC `00-GOVERNANCE/TWIN_EXECUTION_GATE.md`（Authorized exception 条款）+ `topic_campaign.py` 顶部注释，**GAP 闭合**。未来变更需重新授权。

## 五、其他待确认（非阻塞）

| 项 | 状态 | 建议 |
|---|---|---|
| OSAI `archive/desktop-legacy/2026-08/` 2.5GB 历史备份 | 无密钥、未跟踪、已归档态 | 保留（历史证据）；如需释放空间由用户决策 |
| app.py 332KB 单文件庞大 | 活跃、稳定、全量回归通过 | 不重构（高风险，稳定优先） |
| docs/ 568 文件 | 文档资产，非生产路径 | 由文档治理另行收敛 |

## 六、边界合规声明

- 未动 ZBC 生产 DB（62 表只读核验）；未恢复四库；未建第三核心库。
- OSAI 研究侧未写 ZBC 生产代码（本轮仅为审计 + 本地清理，无生产代码变更）。
- 采集频率冲突**未擅改**（Zero Sequence 保护，待用户确认）。
- 全部变更（`2b4fe22`）已 push ZBC 并同步；审计报告本身为研究侧 Evidence。

## 七、下一动作（按用户确认推进）

1. [x] 用户确认 GAP-A 专题采集频率处置 → **授权例外，维持 6 点/天独立配额（2026-09-03）**，已固化治理
2. [ ] 如需：OSAI archive 2.5GB 释放
3. [ ] NEXT_ENGINEERING_QUEUE P1（Runtime/Recovery 等）按最新基线继续
