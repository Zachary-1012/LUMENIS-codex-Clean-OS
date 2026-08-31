# 三仓库同步审计 + GitHub 深度研究报告（2026-08-31）

> 任务：Z-Brand Intelligence Platform 三仓审计 + 海内外成熟案例研究 + 技术择优。**本轮只审计/研究/沉淀文档，不改生产代码、不删文件、不重构、不切换 Owner。**
> 事实优先级：真实源码/DB/运行时 > 基线文档 > 开发日志 > 聊天结论。研究产物见 `docs/learning/`（8 份）。
> 只读交叉脚本：`scripts/inventory/feature_crosscheck.py`（只读连库、静态扫路由，不参与运行时）。

## 1. 三仓库最新 HEAD（实测）
| 仓库 | 角色 | 分支 | 本地 HEAD | 远程 HEAD | 同步 | 工作区 |
|---|---|---|---|---|---|---|
| Z-Brand-Core（ZBP） | 生产 SoT | main | `8fda223` | `8fda223` | 0/0 | 仅 DCC 子模块指针 `m`（未纳入提交） |
| Development-Command-Console（DCC，子模块） | 治理 SoT | main | `77dd1e4` | `023e2ba` | **落后 27 / 领先 0** | 脏 3 文件：M package.json、M server/learning-store.js、?? server/persistence.js（**非本任务产生，未整合**） |
| SICI-Core（SICI） | 研究/执行表面 | main | 本地原未克隆；本次只读克隆到 `D:\repo-audit\SICI-Core`（ZBC 工作区外） | `64eb6a7` | 克隆即最新 | 纯静态站点（index.html+js/css+sw.js），0 py / 11 md / 7 js |

- DCC 远程近 27 提交均为 docs（Gate/契约矩阵/命名基线/ZBIP 跨仓基线/XHS 安全策略），无运行时代码；本地 3 处脏改动需**单独授权**先审计去留再 rebase，不能与 ZBC 提交混做。
- 三仓远程最新提交都出现 "ZBIP cross-repository baseline"，而 ZBC 最新命名决议是顶层**用全称 Z-Brand Intelligence Platform、不新造缩写** → 跨仓命名待对齐（P3，不在 ZBC 仓内改）。

## 2. 架构核对结果
- 命名层级：ZBC 内已统一为四层（Z-Brand Intelligence Platform → ZBP/DCC/SICI 并列 → ZBP 内 CTH-POMS/ZBMP），与任务书一致。
- Feature 状态枚举：已正式 9 态（上一提交 8fda223），34 条实际状态全部合法、无未定义态。
- **多份并行基线文档（P2，文档层叠）**：根/docs 下并存 PRODUCTION_BASELINE_2026-08-31 与 _V3、PHASE1-INVENTORY 与 UPA-PHASE1-INVENTORY、consolidation-001 与 002、CURRENT_BASELINE 与 MASTER_DEVELOPMENT_BASELINE。建议用 ADR（LR-002）标 Superseded，不删历史。
- 红线能力 Owner 锁完好（subject_rules / aggregate_events / build_daily_report / 根 risk_engine / publish≠captured），本轮未发现被弱化。
- `.trae-cn/`（IDE 内置目录）被扫描到，应确认已被 .gitignore 忽略（P3）。

## 3. Feature 全链路交叉验证（34 条，脚本实测）
- 规模：真实路由 **341**（全仓静态，含蓝图；app.py 内 189）、真实表 **51**、py 413、前端模板 6。
- **DB：34 条声明的表 100% 真实存在（0 缺失）**。
- **Owner：凡登记到 .py 的模块文件全部真实存在（0 缺失）**；部分行用中文/模块名未写 .py 后缀（0/0 是登记写法，不是无代码）。
- API：脚本报 6 条"缺失"，逐条人工甄别：
  - 4 条为**蓝图 url_prefix 嵌套的静态扫描误报，API 真实存在**：/api/auth-recovery/*（auth_recovery_bp 前缀+/summary/tasks/health）、/v4/auth/*、/v4/version-center/*、/v4/settings/*（v4_bp 前缀=/v4）。
  - 2 条为**登记前缀不精确（P3，非缺功能）**：动态调度实际走 `/api/collect/schedule-status`+schedule_decisions（非 /api/schedule*）；熔断无独立 /api/circuit* REST，状态走文件 + 采集接口。
- 结论：**无"README 写完成但无代码/无表/无路由"的虚假 ACTIVE**；ACTIVE 项均有真实代码与数据支撑。Test/Evidence 列是当前主要短板（见 §10/11）。

## 4. Owner 冲突
- 无新增冲突；CAPABILITY-OWNERSHIP 已对报告/AI/采集/健康/高危入口/负面/配置/Cookie 做初判唯一 Owner，红线 Owner 已锁。重复实现均标 DUPLICATE/LEGACY 未删，符合"不能 100% 证明无用就保留"。

## 5. 重复能力（只登记，不删）
采集 5 代（生产 collector 链为唯一事实来源，collector_v2 23 文件 DEVELOPING 旁路）、AI 6 套（intelligence+ai_analyzer 为 Owner，云端 Legacy 默认关）、报告 12 路由（统计 Owner=daily_report）、健康 5 套（对外 API/内部自愈/平台健康职责不同非纯重复）、高危运行代码 3 入口、负面 2 套、双 risk_engine、分层 config。退出统一走"引用→调用链→运行依赖→替代→回归→Evidence"门槛。

## 6. API / Contract 问题
- P2：/api、/api/v2、/v4 多代契约并存，缺统一响应/错误/分页契约（登记 OPT-API，逐步版本化，旧接口 LEGACY 保留到前端切换）。
- P1（安全）：/api/developer/run、/api/dev/run-code、/api/config/run-code 三套可执行入口应收口为一个受控+权限+审计 Owner。
- P3：2 处 Feature 登记 API 前缀不精确（§3）。

## 7. DB 问题（51 表，只读核对，未改）
- P2：有 schema_version 表但缺成体系的可回滚迁移工具 → 候选 Alembic（LR-013），先对副本 autogenerate baseline 人工核对，绝不碰生产库。
- P3：swire_notes 空表（功能在建，不删）；生产库 notes 957 / note_review_history 8327 / events 427 / collection_logs 477 / event_graph 16 事件 1 关系 / topic_campaign_notes 120，历史数据完好。

## 8. UI 对应关系
- UI-FEATURE-MAP 已完成 IA/页面/交互/组件/6 断点（不含视觉）；UI 视觉施工⑨按既定顺序仍暂停。
- P1：统一 Auth 弹窗 auth_global.js 已挂 console/collect/settings/version_center 4 个 v4 子页，**主 SPA static/index.html 未挂（AUTH-01）**，A/B/C 强制失败自动弹窗分支未做 E2E。
- 手机/网页"显示不全"问题留待⑨一次性按 390/430/768/1024/1280/1440 处理，本轮不动 UI。

## 9. Runtime 对应（实测在跑，未重启未改动）
- 8201 生产旁路（run_supervised+app.py）healthz=ok/v5.9.9；8200 app.py v5.9.9（**两个重复实例 pid 18852/19916，清理待授权 P3**）；9222 Edge CDP 在线（Edg/152）；8301 Staging 已停；cloudflared 当前未开。
- 小红书：熔断 state=BLOCKED（12:18 20/20 拦截遗留，consecutive_risk=3，in_recovery），该态不发采集请求，符合"暂停"指令，未恢复、未触发。

## 10. Test 覆盖（P1/P2 短板）
- 仓内约 180 个测试文件，但缺**统一 L0–L10 编排入口**与 Staging 隔离的一键 E2E；红线回归集（主体/时间/报告）未固化为可重复 pytest 套件。建议按 TESTING-PATTERNS 建统一入口与 Evidence 归档。

## 11. Evidence 覆盖
- 表 app_evidence_records 已存在，但统一 Evidence 字段结构（EVIDENCE-PATTERNS §1）与 L0–L10 每级最小证据尚未成体系；Playwright trace/截图归档待接入。

## 12–13. GitHub 学习案例与横向比较（详见 docs/learning/）
- 33 条 Research（LR-20260831-001..033），star/license 均为 2026-08-31 GitHub API 一手；覆盖 A–S 全部方向。核心：Backstage 学 Catalog 模型、ADR 学决策固化、in-toto/SLSA 学证据链、Playwright 主浏览器、Crawlee 学队列/自适应限速、APScheduler 进程内调度、tenacity 网络退避、pytest 统一测试、waitress（Windows 生产 WSGI）、Alembic 可回滚迁移、sqlite-vec 零服务学习库、Style Dictionary 学 token、structlog/prometheus 可观测、watchdog 自动版本触发、uv 环境复现。
- 明确不采用：Celery、Nx、Scrapy、独立向量库、gunicorn/supervisor（Windows 不支持）、Backstage 平台本体、tree-sitter（当前正则足够）。

## 14. 当前最优技术方案（最小复杂度+最大可靠）
保持 **Flask + SQLite + Playwright + APScheduler**（现状即轻量最优，不换栈）；Windows 生产入口 waitress、进程守护沿用看门狗/可选 Docker 自愈；DB 迁移 Alembic；测试 pytest+Playwright trace；学习/语义检索 sqlite-vec（零额外服务）；治理用 ADR + Catalog 式 ID 外键；可观测先 structlog 再 /metrics；自身健壮性 tenacity/slowapi。AI 维持 Ollama-only + 规则兜底，永不为生命线。

## 15. 可优化项（只登记 OPT，本轮不施工）
OPT-001 tenacity 替代手写网络重试；OPT-002 waitress 作 Windows 生产 WSGI；OPT-003 sqlite-vec 学习/案例语义检索；OPT-004 structlog 统一日志键；OPT-005 slowapi 对外限流；OPT-006 watchdog 触发自动版本保存；OPT-007 prometheus /metrics；OPT-008 pydeps 交叉依赖图；OPT-009 uv 复现环境；OPT-010 AI 结果按内容hash+模型+prompt版本缓存去重；OPT-API 统一 v1 响应契约；OPT-DOC 并行基线 ADR 收敛。

## 16. 禁止修改项（DO NOT TOUCH）
生产 DB 数据与无 Gate 的 schema 变更；SUBJECT_WORDS/EXCLUDE/subject_hit/_subject_sql_and_values/aggregate_events/build_daily_report/根 risk_engine；publish_datetime≠captured_at；生产采集主链 collector.py（新链未灰度前不接管）；DCC 子模块工作区 3 处脏改动（未授权不动）；任何 cookie/.env/*.db/profile 入库；为整洁删除 LEGACY/DUPLICATE（未走退出门槛前）；UI 视觉（⑨未解除暂停前）；把 DCC/SICI 变成运行时依赖；直接复制第三方源码。

## 17. P0 / P1 / P2 / P3 清单
- **P0（生产/安全/数据正确性）：本轮未发现新增 P0。** 生产运行正常、红线口径完好、DB 完整、无虚假 ACTIVE、无真实 API 缺失。
- **P1（功能/稳定/安全）**：① AUTH-01 主 SPA 挂统一 Auth 弹窗并 E2E；② 三套"运行代码"高危入口收口（安全）；③ SCHED-01 动态调度影子转门控（**待你签字**）；④ 统一 pytest L0–L10 + Staging E2E 编排；⑤ DIM-01 双维度落库、EVT-01 三类事件四关系（既有业务工单）；⑥ DCC 落后远程 27 + 脏 3 文件的整合（需单独授权）。
- **P2（架构/维护）**：并行基线 ADR 收敛；Alembic 迁移 baseline；多代 API 契约版本化；重复能力按门槛退出；统一 Evidence 结构/structlog；Selenium 与 0 引用依赖回归后退出。
- **P3（文档/表达）**：跨仓 ZBIP 缩写对齐；2 处 Feature API 前缀登记；swire_notes 空表跟进；8200 重复实例清理（待授权）；.trae-cn 忽略确认；根目录 start_*.bat/.bak/日志收敛。

## 18. 下一阶段施工顺序
NOW → ① P1-① AUTH 弹窗挂主 SPA（工作量小、配合小红书恢复）；② P1-② 高危入口收口；③ 建 pytest 统一入口与红线回归集（先 L0–L5）。
NEXT → ④ SCHED-01 门控（签字后，先旁路对比影子决策再切）；⑤ DIM-01/EVT-01；⑥ DCC 整合（单独任务、先审 3 处脏改动）；⑦ Alembic 在 Staging 副本 baseline。
LATER → ⑧ UI 信息架构锁定→⑨ UI 一次性施工（侘寂黑白灰，6 断点，修显示不全）；⑩ L6–L10 E2E/Restart/Regression；⑪ OPT 候选按价值逐项 Staging；⑫ 固定域名/服务器与 Linux 路径。

【NOW】P1 中 AUTH-01 + 高危入口收口 + pytest L0–L5（均旁路/增量，不动红线与生产主链）。
【NEXT】SCHED-01 门控（待签字）、DIM-01/EVT-01、DCC 整合、Alembic 副本 baseline。
【LATER】UI ⑨、L6–L10、OPT 候选、固定公网。
【DO NOT TOUCH】见 §16。

## 本轮交付物
- 新增 `docs/learning/` 8 份：LEARNING-REGISTRY / CASE-STUDIES / TECHNOLOGY-COMPARISON / ARCHITECTURE-PATTERNS / EVIDENCE-PATTERNS / BROWSER-RESEARCH / TESTING-PATTERNS / DEPLOYMENT-PATTERNS。
- 新增只读脚本 `scripts/inventory/feature_crosscheck.py`。
- 本报告。**未改任何业务代码/DB/采集/UI/API/Runtime，未删文件。** 供你做第二层交叉验证后再决定哪些 OPT 真正落地。
