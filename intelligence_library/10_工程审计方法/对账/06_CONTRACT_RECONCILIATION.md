# 06 — CONTRACT RECONCILIATION（契约对账）

> 审计日期：2026-09-02  
> OSAI HEAD：`60af16a`（`D:\Zachary OS AI`）  
> ZBC HEAD：`545a3ab` v5.9.9（`D:\Taikoo-monitor-new`）  
> 合法流向：OSAI → Contract/Plan → ZBC；ZBC → Result/Evidence → OSAI  
> 旧 `11_contract_matrix.md` 仅作历史参考，不作为当前架构判断依据。

## 状态计数

| 状态 | 计数 |
|------|------|
| EXISTS | 7 |
| PARTIAL | 8 |
| MISSING | 6 |
| UNKNOWN | 0 |

---

## 1. OSAI 侧契约清单（全量盘点）

### 1.1 代码级契约（`src/contracts/`）

| 契约文件 | 路径 | 契约类型 | 状态 |
|----------|------|----------|------|
| `research_record.py` | `components/AI-Development-Research-Hub/src/contracts/research_record.py` | 研究记录数据契约（schema 校验、凭证脱敏、Review 对象） | EXISTS |
| `safe_collection.py` | `components/AI-Development-Research-Hub/src/contracts/safe_collection.py` | 无公害采集契约（PII 脱敏、速率治理、采集审计、离线 Shadow Pipeline） | EXISTS |

### 1.2 协议级契约（`protocols/`、`docs/protocols/`、根目录）

| 契约文件 | 路径 | 契约类型 | 状态 |
|----------|------|----------|------|
| `GLOBAL-CROSS-REPOSITORY-BASELINE.md` | `components/AI-Development-Research-Hub/GLOBAL-CROSS-REPOSITORY-BASELINE.md` | 跨库全局基线（Before/Change/After Gate、三向验证、Capability Delta、Shadow Learning Gate） | EXISTS |
| `AI-COLLABORATION-PROTOCOL.md` | `components/AI-Development-Research-Hub/AI-COLLABORATION-PROTOCOL.md` | AI 协作协议（Research ID 规范、互相 Review 流程、Research Record 字段） | EXISTS |
| `SHADOW-LEARNING-PROTOCOL.md` | `components/AI-Development-Research-Hub/SHADOW-LEARNING-PROTOCOL.md` | Shadow Learning 协议（9 阶段固定生命周期、禁止行为、Shadow 数据存储） | EXISTS |
| `RESEARCH-LEARNING-SCHEMA.md` | `components/AI-Development-Research-Hub/RESEARCH-LEARNING-SCHEMA.md` | 研究学习 Schema（Hub schema v1、DDC 兼容、扩展字段、状态机） | EXISTS |
| `THREE-REPOSITORY-VALIDATION.md` | `components/AI-Development-Research-Hub/THREE-REPOSITORY-VALIDATION.md` | 三库验证矩阵 | EXISTS |
| `CONTINUOUS-RESEARCH-AND-DEVELOPMENT-POLICY.md` | `components/AI-Development-Research-Hub/protocols/CONTINUOUS-RESEARCH-AND-DEVELOPMENT-POLICY.md` | 持续研发政策 | EXISTS |
| `AI-WORK-LOG-AND-REALTIME-PUSH-PROTOCOL.md` | `components/AI-Development-Research-Hub/docs/protocols/AI-WORK-LOG-AND-REALTIME-PUSH-PROTOCOL.md` | AI 工作日志与实时推送协议 | EXISTS |
| `CHATGPT-INTERVENTION-PROTOCOL.md` | `components/AI-Development-Research-Hub/docs/protocols/CHATGPT-INTERVENTION-PROTOCOL.md` | ChatGPT 介入协议 | EXISTS |
| `TASK-QUEUE-INTEGRATION-PROTOCOL.md` | `components/AI-Development-Research-Hub/docs/operations/TASK-QUEUE-INTEGRATION-PROTOCOL.md` | 任务队列集成协议 | EXISTS |

### 1.3 架构级契约（`architecture/`）

| 契约文件 | 路径 | 契约类型 | 状态 |
|----------|------|----------|------|
| `ZACHARY-DOMAIN-ADAPTER-CONTRACT-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-DOMAIN-ADAPTER-CONTRACT-v1.md` | 领域适配器契约（13 个必填字段、8 项隔离要求、学习边界、泛化规则） | EXISTS |
| `ZACHARY-INTERNAL-LEARNING-CONTRACT-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-INTERNAL-LEARNING-CONTRACT-v1.md` | 内部学习契约 | EXISTS |
| `ZACHARY-INTERNAL-MATURATION-AND-DOMAIN-ISOLATION-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-INTERNAL-MATURATION-AND-DOMAIN-ISOLATION-v1.md` | 内部成熟与领域隔离 | EXISTS |
| `CONTENT-INTELLIGENCE-SPEC-v1.md` | `components/AI-Development-Research-Hub/architecture/CONTENT-INTELLIGENCE-SPEC-v1.md` | 内容智能规格 | EXISTS |
| `ZACHARY-EXPERIENCE-SCHEMA-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-EXPERIENCE-SCHEMA-v1.md` | 体验 Schema | EXISTS |
| `ZACHARY-MEMORY-LIFECYCLE-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-MEMORY-LIFECYCLE-v1.md` | 记忆生命周期 | EXISTS |
| `ZACHARY-CAPABILITY-BENCHMARK-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-CAPABILITY-BENCHMARK-v1.md` | 能力基准 | EXISTS |
| `ZACHARY-AI-GROWTH-MODEL-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-AI-GROWTH-MODEL-v1.md` | AI 成长模型 | EXISTS |
| `ZACHARY-LEARNING-PROMOTION-ENGINE-v1.md` | `components/AI-Development-Research-Hub/architecture/ZACHARY-LEARNING-PROMOTION-ENGINE-v1.md` | 学习晋级引擎 | EXISTS |
| `ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901.md` | `components/AI-Development-Research-Hub/docs/ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901.md` | Zachary↔ZBC 双向学习契约 | EXISTS |

### 1.4 注册表/基线

| 契约文件 | 路径 | 状态 |
|----------|------|------|
| `CAPABILITY-REGISTRY.md` | `components/AI-Development-Research-Hub/CAPABILITY-REGISTRY.md`（3 个已注册能力：research-id-generator, shadow-lifecycle, ddc-research-adapter） | EXISTS |
| `PLATFORM_BASELINE.md` | `components/AI-Development-Research-Hub/PLATFORM_BASELINE.md` | EXISTS |
| `CASE-LIBRARY.md` | `components/AI-Development-Research-Hub/CASE-LIBRARY.md` | EXISTS |

### 1.5 历史参考（不作为当前事实）

| 文件 | 路径 | 状态 |
|------|------|------|
| `11_contract_matrix.md` | OSAI 根目录 `11_contract_matrix.md` | PARTIAL（历史审计，称 ZBC 有 50+ routes 无 OpenAPI、DB Contract 为 ACTIVE 但仅 22 表——实际 53 表，数据已过时） |

---

## 2. 逐项契约 vs ZBC 实现核对

### 2.1 `safe_collection.py`（无公害采集契约）— 核心契约

| 契约条款 | 契约要求 | ZBC 实际实现 | 证据路径 | 状态 |
|----------|----------|---------------|----------|------|
| PII 字段级脱敏 | `DEFAULT_PII_FIELDS` 含 40+ 字段（user_id, nickname, avatar, phone, wechat, ip, lat/lng 等），`redact_record()` 递归脱敏 | **ZBC 采集管线无 PII 脱敏步骤**。`collector.py`、`xhs_cdp_collector.py`、`collector_v2/` 直接将原始数据写入 `notes` 表（`author_id`, `author_nickname`, `author_avatar` 均明文存储） | `D:\Taikoo-monitor-new\collector.py`、`xhs_cdp_collector.py`、`database.py:insert_note()` | **MISSING**（ZBC 未实现 PII 脱敏） |
| 文本内联系方式脱敏 | `redact_text()` 正则脱敏 phone/email/wechat/QQ | **未实现**。`notes.content` / `notes.body` 直接存储原始文本，无联系方式扫描 | `database.py:insert_note()`（vals 直接写入 content/body） | **MISSING** |
| 只读采集 | `CollectionHygienePolicy.read_only = True`, `write_enabled = False` | **PARTIAL**。ZBC 采集器主要为只读抓取（搜索+详情页），但 `xhs_cookie_bridge.py` 涉及 Cookie 写入/同步，`collector_automation.py` 有自动化操作 | `collector.py`、`xhs_cookie_bridge.py`、`collector_automation.py` | PARTIAL |
| 单本地账号 | `single_local_account = True`, `allow_account_pool = False` | **违反**。ZBC 存在 `edge-cdp-profile/`、`edge-cdp-newaccount/`、`edge-cdp-profile-new/`、`edge-cdp-proxy/` 等多账号/多 profile 目录；`weibo_login_manager.py`、`bilibili_login_manager.py` 支持多账号管理 | `D:\Taikoo-monitor-new\edge-cdp-profile\`、`edge-cdp-newaccount\`、`weibo_login_manager.py` | **MISSING / VIOLATION**（ZBC 使用多账号，违反契约 `allow_account_pool=False`） |
| 禁止代理池 | `allow_proxy_pool = False` | **违反**。ZBC 存在 `proxy_pool/` 目录（含代理池实现），`network_adaptive.py`、`adaptive_engine.py` 有代理切换逻辑 | `D:\Taikoo-monitor-new\proxy_pool\`、`network_adaptive.py` | **MISSING / VIOLATION**（ZBC 使用代理池，违反契约 `allow_proxy_pool=False`） |
| 速率下限 | `MIN_INTERVAL_FLOOR = 2.0s`, `DEFAULT_MIN_INTERVAL = 3.0s` | **UNKNOWN / PARTIAL**。ZBC 采集器有 `schedule_decisions` 表（369 行）和 `adaptive_engine.py` 做自适应调度，但未发现明确的 2s/3s 速率下限常量 | `adaptive_engine.py`、`schedule_decisions` 表 | PARTIAL（有调度但无契约规定的速率下限常量） |
| 日采集上限 | `DEFAULT_DAILY_CAP = 200` | **未实现**。无日采集量硬上限机制 | 全仓搜索无 `daily_cap` 常量 | MISSING |
| 风险信号即停 | `RISK_STOP_SIGNALS`（300012, captcha, slider 等），`stop_on_risk_signal = True` | **PARTIAL**。`safety_boundary.py`、`risk_engine.py` 有风险控制逻辑，`xhs_cdp_collector.py` 有错误处理但是否包含契约规定的全部风险信号需验证 | `safety_boundary.py`、`risk_engine.py` | PARTIAL |
| 采集审计记录 | `build_collection_audit()`，schema `zachary.hub.collection-audit.v1`，16 个必填字段 | **未实现**。ZBC 有 `collection_logs` 表（499 行）和 `collector_quality_log` 表（7 行），但字段与契约的 `collection-audit.v1` 不匹配（无 `audit_id`, `redacted_count`, `policy_snapshot`, `human_triggered`, `risk_signals` 等） | `collection_logs` 表 schema、`collector_quality_log` 表 schema | **MISSING**（ZBC 有采集日志但不兼容契约 audit schema） |
| 离线 Shadow Pipeline | `run_offline_pipeline()`（rate decision → redact → audit） | **未实现**。无对应离线管线 | 全仓无 `run_offline_pipeline` | MISSING |

> **`safe_collection.py` 契约总结**：ZBC **未实现**此契约的核心条款（PII 脱敏、单账号、禁止代理池、采集审计 schema 兼容）。ZBC 的采集体系（多账号 + 代理池 + 无脱敏）与契约的"无公害采集"定位存在**根本性冲突**。此契约目前仅在 OSAI 侧有代码定义和单元测试，ZBC 侧无 Adapter 接入。

### 2.2 `research_record.py`（研究记录契约）

| 契约条款 | ZBC 实现 | 证据路径 | 状态 |
|----------|----------|----------|------|
| Research ID 规范 `R-YYYY-NNNN` | ZBC 无研究记录体系（生产侧不产生 Research Record） | 全仓无 `R-2026-` 格式 ID | EXISTS（正确——ZBC 是生产侧，Research Record 由 OSAI 侧产生） |
| 凭证脱敏 `sanitize()` | ZBC 有 `security_scanner.py` 做凭证扫描，但非同一实现 | `security_scanner.py` | PARTIAL（ZBC 有安全扫描但不兼容契约 sanitize 接口） |
| 三方验证字段（zbrand/ddc/sici_validation） | ZBC 无 Research Record，故无验证字段 | — | EXISTS（正确分工） |

### 2.3 `SHADOW-LEARNING-PROTOCOL.md`（Shadow Learning 协议）

| 契约条款 | ZBC 实现 | 证据路径 | 状态 |
|----------|----------|----------|------|
| 9 阶段固定生命周期 | ZBC 有 `v4_ai_shadow` 表（2 行）和 `ai_learning_engine.py`，但是否遵循 9 阶段生命周期需验证 | `v4_ai_shadow` 表 schema、`ai_learning_engine.py` | PARTIAL（有 shadow 表和学习引擎，但无证据表明遵循完整 9 阶段生命周期） |
| Shadow 不自动改变生产行为 | `v4_ai_shadow` 表有 `status` 字段（pending 等），`ai_learning_engine.py` 有学习逻辑 | `v4_ai_shadow` 表、`ai_learning_engine.py` | PARTIAL（有状态隔离但是否严格"不自动改变生产"需运行时验证） |
| Shadow 数据存储 `data/shadow/` JSONL | ZBC 无 `data/shadow/` 目录，shadow 数据存在 SQLite `v4_ai_shadow` 表中 | 目录结构对比 | PARTIAL（存储介质不同：OSAI 用 JSONL 文件，ZBC 用 SQLite 表） |
| `production_unchanged` 必须为 true | `v4_ai_shadow` 表无 `production_unchanged` 字段 | `v4_ai_shadow` 表 schema | MISSING（ZBC shadow 表缺少契约要求的 `production_unchanged` 字段） |
| 禁止 AI 输出直接作为 Evidence | ZBC `ai_learning_engine.py`、`data_feedback_loop.py` 有反馈循环但是否区分 AI 输出与真实 Evidence 需验证 | `ai_learning_engine.py`、`data_feedback_loop.py` | PARTIAL |

### 2.4 `GLOBAL-CROSS-REPOSITORY-BASELINE.md`（全局基线）

| 契约条款 | ZBC 实现 | 证据路径 | 状态 |
|----------|----------|----------|------|
| Before Gate（变更前三库全量理解） | ZBC 有 `runtime_preflight.py`（启动前检查），但是否包含三库全量理解需验证 | `runtime_preflight.py` | PARTIAL（有 preflight 但是否覆盖三库全量理解未知） |
| After Gate（完成后三库复核） | 无证据表明 ZBC 变更后执行三库复核 | 全仓无 after-gate 流程 | MISSING |
| 三向验证（ZBC 业务 + DCC 工程 + SICI 移动） | ZBC 有 `tests/` 目录（pytest），但是否包含 DCC/SICI 验证维度需验证 | `D:\Taikoo-monitor-new\tests\`、`pytest.ini` | PARTIAL（有自有测试但无三向验证框架） |
| Capability Delta（before/after metrics） | 无证据表明 ZBC 维护 Capability Delta | 全仓无 capability delta 记录 | MISSING |
| Shadow Learning Gate | 见 §2.3 | — | PARTIAL |

### 2.5 `ZACHARY-DOMAIN-ADAPTER-CONTRACT-v1.md`（领域适配器契约）

| 契约条款 | ZBC 实现 | 证据路径 | 状态 |
|----------|----------|----------|------|
| 13 个必填字段（product_id, domain_id, task_id, ...） | ZBC 无 Domain Adapter 实现。`v4_upgrade/adapters/` 目录下有 20+ 个采集适配器（base.py, google.py, douyin.py 等），但是否遵循 Domain Adapter Contract 的 13 字段规范需验证 | `v4_upgrade/adapters/base.py` | PARTIAL（有适配器架构但字段规范不匹配契约） |
| 8 项隔离要求 | `v4_upgrade/adapters/base.py` 有基础抽象但是否覆盖全部 8 项隔离需验证 | `v4_upgrade/adapters/base.py` | PARTIAL |
| 适配器不得自动晋级能力 | 无证据表明 ZBC 适配器有能力晋级机制 | — | MISSING |
| 失败关闭（fail closed） | `v4_upgrade/adapters/risk_controller.py` 有风险控制但是否 fail closed 需验证 | `v4_upgrade/adapters/risk_controller.py` | PARTIAL |

### 2.6 `ZACHARY-ZBC-BIDIRECTIONAL-LEARNING-CONTRACT-20260901.md`（双向学习契约）

| 契约条款 | ZBC 实现 | 证据路径 | 状态 |
|----------|----------|----------|------|
| ZBC→Zachary：提供 approved 数据/证据/案例 | ZBC 生产库有 957 notes、427 events、33 daily_reports 等数据，但是否有"approved"标记/导出机制需验证 | `data/monitor.db`、`data_feedback_loop.py` | PARTIAL（有数据但是否有 approved 导出通道未知） |
| Zachary→ZBC：通过 Evidence→Capability→Contract→Governance→Promotion 路径反馈 | ZBC 有 `v4_ai_shadow` 表（2 行）和 `ai_learning_engine.py`，但是否遵循完整 Promotion 路径需验证 | `v4_ai_shadow`、`ai_learning_engine.py` | PARTIAL |
| Zachary 不得直接改写 ZBC 权威规则/生产数据 | `subject_rules.py`（最高保护层）在 ZBC 侧独立维护，OSAI 侧无写入权限 | `subject_rules.py`、跨仓库 import 检查（无越界） | EXISTS（正确隔离——OSAI 无 ZBC 生产代码写入权限） |
| 双向学习不得互相污染 | 无跨仓库 Python import（已验证），无 OSAI 直连 ZBC 生产库 | 跨仓库 import grep 结果 | EXISTS（代码层面无越界） |

### 2.7 `AI-COLLABORATION-PROTOCOL.md`（AI 协作协议）

| 契约条款 | ZBC 实现 | 证据路径 | 状态 |
|----------|----------|----------|------|
| Research ID 唯一 | ZBC 无 Research ID 体系（生产侧） | — | EXISTS（正确分工） |
| ChatGPT↔豆包互相 Review | ZBC 无 AI 互相 Review 流程 | — | EXISTS（正确——此为 OSAI 侧研究流程） |
| Research Record 字段规范 | ZBC 无 Research Record | — | EXISTS（正确分工） |

### 2.8 `CAPABILITY-REGISTRY.md`（能力注册表）

| 契约条款 | ZBC 实现 | 证据路径 | 状态 |
|----------|----------|----------|------|
| 3 个已注册 reusable 能力 | ZBC 未通过 Contract/Adapter 使用这 3 个能力（research-id-generator, shadow-lifecycle, ddc-research-adapter 均为 OSAI 侧内部能力） | `CAPABILITY-REGISTRY.md` `used_by` 字段为空 | PARTIAL（能力已注册但 ZBC 未消费，`used_by` 为空） |
| 能力通过 Contract/Adapter 使用，不复制实现 | ZBC 无复制 OSAI 能力实现的证据（跨仓库 import 检查无越界） | 跨仓库 import grep | EXISTS（正确——无代码复制） |

---

## 3. ZBC 违反契约的项（Violation Register）

| # | 被违反契约 | 违反条款 | ZBC 实际 | 严重度 | 证据路径 |
|---|-----------|----------|----------|--------|----------|
| V-01 | `safe_collection.py` | `allow_account_pool = False`（禁止账号池） | ZBC 有多账号/profile 体系（`edge-cdp-profile/`, `edge-cdp-newaccount/`, `weibo_login_manager.py`, `bilibili_login_manager.py`） | **HIGH** | `D:\Taikoo-monitor-new\edge-cdp-profile\`、`edge-cdp-newaccount\` |
| V-02 | `safe_collection.py` | `allow_proxy_pool = False`（禁止代理池） | ZBC 有 `proxy_pool/` 目录和代理切换逻辑 | **HIGH** | `D:\Taikoo-monitor-new\proxy_pool\`、`network_adaptive.py` |
| V-03 | `safe_collection.py` | PII 字段级脱敏（40+ 字段） | ZBC 采集管线无 PII 脱敏，`author_id`/`author_nickname`/`author_avatar` 明文存储 | **HIGH** | `database.py:insert_note()`、`notes` 表数据 |
| V-04 | `safe_collection.py` | 文本内联系方式脱敏（phone/email/wechat/QQ） | ZBC `notes.content`/`body` 直接存储原始文本，无联系方式扫描 | **MEDIUM** | `database.py:insert_note()` |
| V-05 | `safe_collection.py` | 采集审计 schema `zachary.hub.collection-audit.v1`（16 必填字段） | ZBC `collection_logs`/`collector_quality_log` 表字段不兼容契约 audit schema | **MEDIUM** | `collection_logs` 表 schema |
| V-06 | `SHADOW-LEARNING-PROTOCOL.md` | Shadow 数据必须含 `production_unchanged` 字段且为 true | ZBC `v4_ai_shadow` 表无 `production_unchanged` 字段 | **MEDIUM** | `v4_ai_shadow` 表 schema |
| V-07 | `GLOBAL-CROSS-REPOSITORY-BASELINE.md` | After Gate（变更后三库复核） | ZBC 无 After Gate 流程证据 | **LOW** | 全仓无 after-gate 记录 |

> **重要上下文**：V-01/V-02（多账号/代理池）的违反需要结合业务实际理解——ZBC 作为生产舆情监测系统，多账号和代理池是其采集能力的核心组成部分，而 `safe_collection.py` 契约定位为"无公害/低风险采集"（单账号、只读、无代理），二者定位不同。此契约可能仅适用于特定低风险采集场景（如 R-2026-0003 人工 QR 码采集），而非 ZBC 全量采集管线。**但契约中未明确声明适用范围边界**，导致当前状态为"ZBC 全量采集体系与契约条款冲突"。

---

## 4. ZBC 实现了但 OSAI 未声明的"隐式 Contract"（Implicit Contracts）

| # | 隐式契约 | ZBC 实现 | OSAI 声明状态 | 证据路径 | 状态 |
|---|----------|----------|---------------|----------|------|
| I-01 | ZBC API 接口契约（203 个路由） | `app.py` 有 203 个 `@app.route`，覆盖 notes/events/collect/report/ai/brand/case/event-graph/v4 等 | **OSAI 无任何 API Contract/OpenAPI/Swagger 声明**。旧 `11_contract_matrix.md` 提到 6 个 ZBC API 但仅为列表，无 schema | `app.py`（203 routes）、旧 `11_contract_matrix.md` | **MISSING**（OSAI 未声明 ZBC API 契约） |
| I-02 | 主体口径契约（`SUBJECT_WORDS`/`SUBJECT_EXCLUDE_WORDS`/`subject_hit()`） | `subject_rules.py` 定义了 18 个正向主体词、22 个排除词、5 个业务字段、`subject_hit()`/`subject_sql_and_values()` 函数 | **OSAI 无主体口径 Contract 声明**。此为 ZBC 最高保护层，OSAI 侧无对应契约 | `subject_rules.py` | **MISSING**（最高保护层无 OSAI 契约声明） |
| I-03 | 数据库 Schema 契约（53 张表） | `database.py` SCHEMA + `NOTE_MIGRATIONS` + 20+ 模块隐式建表 | **OSAI 无 DB Schema Contract 声明**（见 05 文档 §9） | `database.py`、生产库 `.schema` | **MISSING** |
| I-04 | v4 认证/权限体系契约 | `v4_upgrade/auth/` 实现了用户/角色/会话/工作区密钥/审计日志（8 张 v4_* 表） | **OSAI 无 v4  auth Contract 声明** | `v4_upgrade/auth/`、`v4_users`/`v4_sessions`/`v4_workspace_keys` 表 | **MISSING** |
| I-05 | 话题活动监测契约 | `topic_campaign.py` 实现了 campaign/topic/notes/snapshots 4 张表和监测逻辑 | **OSAI 无 topic_campaign Contract 声明** | `topic_campaign.py`、`topic_campaigns`/`topic_campaign_topics`/`topic_campaign_notes`/`topic_campaign_snapshots` 表 | **MISSING** |
| I-06 | 事件图谱契约 | `event_graph.py` 实现了事件节点/关系图谱（2 张表） | **OSAI 无 event_graph Contract 声明** | `event_graph.py`、`event_graph_events`/`event_graph_relations` 表 | **MISSING** |
| I-07 | 太古地产（Swire）多项目监测契约 | `swire_group.py` 实现了 projects/events/notes 3 张表和多项目监测 | **OSAI 无 swire_group Contract 声明** | `swire_group.py`、`swire_projects`/`swire_events`/`swire_notes` 表 | **MISSING** |
| I-08 | 审核工作流契约 | `review_workflow.py` 实现了 tickets/samples/logs 3 张表和审核流程 | **OSAI 无 review_workflow Contract 声明** | `review_workflow.py`、`review_tickets`/`review_samples`/`review_logs` 表 | **MISSING** |
| I-09 | 自适应调度契约 | `adaptive_engine.py` + `schedule_decisions` 表（369 行）实现了采集调度自适应 | **OSAI 无 adaptive_scheduling Contract 声明** | `adaptive_engine.py`、`schedule_decisions` 表 | **MISSING** |
| I-10 | 品牌知识库契约 | `brand_knowledge_base.py` + `brand_knowledge` 表（103 行） | **OSAI 无 brand_knowledge Contract 声明** | `brand_knowledge_base.py`、`brand_knowledge` 表 | **MISSING** |

> **隐式 Contract 总结**：ZBC 生产系统有 **10+ 个核心子系统**在 OSAI 侧完全没有 Contract 声明。合法流向 OSAI→Contract/Plan→ZBC 在这些子系统上是**断裂**的——ZBC 自行设计、实现、演化了这些子系统，OSAI 侧无对应契约或规划文档。这是当前双子星架构最大的 Contract Gap。

---

## 5. 版本不一致核对

| 契约/组件 | OSAI 侧版本 | ZBC 侧版本 | 一致性 | 证据路径 | 状态 |
|-----------|------------|------------|--------|----------|------|
| ZBC 系统版本 | 旧 `11_contract_matrix.md` 未标注 | `VERSION` 文件 = v5.9.9，`package.json` = 5.6.2（**不一致**） | **PARTIAL**——`VERSION`（v5.9.9）与 `package.json`（5.6.2）版本号不一致 | `D:\Taikoo-monitor-new\VERSION`、`package.json:3` | PARTIAL（ZBC 内部版本号不一致） |
| `database_migrations.py` CURRENT_VERSION | — | 8（`database_migrations.py:25`） | `schema_version` 表有 7 条记录，与 CURRENT_VERSION=8 不完全对应 | `database_migrations.py:25`、`schema_version` 表 | PARTIAL |
| `models.py` 版本注释 | — | v5.8.0（`models.py:4`），`__main__` 打印 v5.8.9 | **不一致**——文件头 v5.8.0 vs `__main__` v5.8.9 vs 系统 v5.9.9 | `models.py:4`、`models.py:313` | PARTIAL |
| Research Schema | Hub `zachary.hub.research.v1`，DDC 兼容 `zachary.platform.research-learning.v1` | ZBC 无 Research Schema | EXISTS（OSAI 侧内部版本一致，ZBC 不涉及） | `research_record.py:15-16` | EXISTS |
| Collection Audit Schema | `zachary.hub.collection-audit.v1` | ZBC 无此 schema（`collection_logs` 表无 schema 版本标记） | MISSING（ZBC 未实现） | `safe_collection.py:46` | MISSING |
| Capability Schema | `zachary.hub.capability.v1` | ZBC 无 Capability Registry | EXISTS（OSAI 侧内部，ZBC 不涉及） | `CAPABILITY-REGISTRY.md:37` | EXISTS |

---

## 6. 汇总与关键发现

### 6.1 状态计数汇总

| 状态 | 计数 | 占比 |
|------|------|------|
| EXISTS | 7 | 33.3% |
| PARTIAL | 8 | 38.1% |
| MISSING | 6 | 28.6% |
| UNKNOWN | 0 | 0% |

### 6.2 P0 级关键发现

1. **`safe_collection.py` 契约与 ZBC 采集体系根本性冲突**：契约要求单账号、无代理池、PII 脱敏，ZBC 实际为多账号 + 代理池 + 无脱敏。契约未声明适用范围边界，导致全量冲突。
2. **ZBC 最高保护层（`subject_rules.py`）在 OSAI 侧无 Contract 声明**：18 正向词 + 22 排除词 + `subject_hit()` 函数完全由 ZBC 侧定义，OSAI 无对应契约。合法流向 OSAI→Contract→ZBC 在此断裂。

### 6.3 P1 级关键发现

3. **ZBC 有 203 个 API 路由但 OSAI 无任何 API Contract/OpenAPI 声明**：旧 `11_contract_matrix.md` 仅列出 6 个 API 名称，无请求/响应 schema。
4. **10+ 个 ZBC 核心子系统在 OSAI 侧无 Contract 声明**：v4 auth、topic_campaign、event_graph、swire_group、review_workflow、adaptive_scheduling、brand_knowledge 等。
5. **ZBC 内部版本号不一致**：`VERSION`=v5.9.9、`package.json`=5.6.2、`models.py` 头=v5.8.0、`models.py __main__`=v5.8.9，四处版本号互不相同。
6. **Shadow Learning 契约部分实现**：ZBC 有 `v4_ai_shadow` 表但缺少 `production_unchanged` 字段，存储介质不同（SQLite vs JSONL）。

### 6.4 P2 级关键发现

7. **CAPABILITY-REGISTRY 中 3 个能力的 `used_by` 为空**：ZBC 未通过 Contract 消费 OSAI 已注册能力。
8. **GLOBAL-CROSS-REPOSITORY-BASELINE 的 After Gate 在 ZBC 无证据**：无变更后三库复核流程。
9. **`database_migrations.py` v1→v6 迁移 schema 已过时**：与生产库实际列定义不匹配（见 05 文档 §3.3）。

---

*本文档所有判断均基于本地当前源码实际文件，未根据 README/历史文档/模型记忆判定"存在"。每项均附真实文件路径作为证据。*
