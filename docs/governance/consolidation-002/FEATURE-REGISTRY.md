# FEATURE-REGISTRY · 功能总账（Consolidation-002 / ⑤）

> 规则：以后任何代码改动先查 Feature ID；**无 ID 不允许直接新增功能**，先在此登记。
> 一个 Feature 绑定：产品 / Owner 模块（对应 ASSET-ID）/ API 组 / DB 表 / UI 页面 / 状态 / Evidence / 版本。
> **Feature 状态枚举（正式 9 态，状态列唯一合法取值）**
> - **ACTIVE**：已实现，并且通过当前要求的验证。
> - **DEVELOPING**：正在开发，尚未达到 ACTIVE。
> - **EXPERIMENTAL**：已经存在真实实现/实验能力，但尚未达到生产接管标准。
> - **PLANNED**：已经确定需要建设，但尚未实现。
> - **RESERVED**：提前占位，未来可能建设，当前不实施。
> - **LEGACY**：历史实现，当前不作为新 Owner。
> - **DUPLICATE**：已确认与其他能力重复，必须指向唯一 Owner。
> - **MIGRATION_REQUIRED**：已确认需要迁移，但迁移尚未完成。
> - **NOT_VERIFIED**：存在实现、声明或历史记录，但当前证据不足，不能判断为完成。
>
> 状态列括号内仅为备注（暂停原因/工单号/窗口等），不改变状态词本身。本表为 **Feature 9 态（不含 DEPRECATED）**；资产侧 10 态（含 DEPRECATED）见 `ASSET-REGISTRY.md`，两者适用对象不同、不得混用。
> 层级：Z-Brand Intelligence Platform（统一平台层）→ ZBP 品牌业务生产平台（本仓库，与 DCC/SICI 并列）→ CTH-POMS / ZBMP。
> 产品：CTH=CTH-POMS（广州太古汇舆情，生产主入口）；ZBMP=ZBP 内母平台增强层（共用 Core）。

## 一、CTH-POMS 生产功能（P0，红线域不得改口径）

### 采集监测 MON
| Feature ID | 功能 | Owner 模块 | API 组 | DB | UI | 状态 |
|---|---|---|---|---|---|---|
| FEATURE-CTH-MON-001 | 关键词笔记采集（小红书真人CDP） | collector.py / xhs_cdp_collector | /api/collect* | notes,collection_logs | collect | ACTIVE（当前按用户指令暂停） |
| FEATURE-CTH-MON-002 | 15周年专题监测 | topic_campaign.py | /api/topic-campaign/* | topic_campaign_notes | 专题页 | ACTIVE（窗口至10-07） |
| FEATURE-CTH-MON-003 | 采集调度（固定→动态） | platform_adapters/scheduling | /api/schedule* | schedule_decisions | console | DEVELOPING（影子，未门控=SCHED-01） |
| FEATURE-CTH-MON-004 | 采集健康/六态 | health_center.py | /api/platform-health | collection_logs | console 健康点 | ACTIVE |
| FEATURE-CTH-MON-005 | 全网搜索采集（搜狗/Google） | web_monitor / v4 adapters | /api/web-* | web_* | collect | EXPERIMENTAL |

### 主体 / 事件 / 风险（红线）
| Feature ID | 功能 | Owner | API | DB | 状态 |
|---|---|---|---|---|---|
| FEATURE-CTH-SUBJ-001 | 广州太古汇主体过滤 | subject_rules.py 🔴 | （内部） | notes.subject_hit | ACTIVE（口径锁） |
| FEATURE-CTH-SUBJ-002 | 主体类型/内容类型双维度 | subject_classifier.py | /api/subject-classifier/types | 落库未贯通 | DEVELOPING（DIM-01，禁 user_type=UGC） |
| FEATURE-CTH-EVT-001 | 事件聚合 | aggregate_events 🔴 | /api/events* | events(427) | ACTIVE |
| FEATURE-CTH-EVT-002 | 事件关系图谱 | event_graph.py | /api/event-graph/* | event_graph_events/relations | ACTIVE（三类+四关系未全=EVT-01） |
| FEATURE-CTH-EVT-003 | 负面确认/评审 | events 评审流 | /api/negative*、/api/event-review/* | note_review_history(8327) | ACTIVE（两套待④收敛） |
| FEATURE-CTH-RISK-001 | 风险判定/等级 | risk_engine.py 🔴 | /api/risk* | events | ACTIVE |
| FEATURE-CTH-RISK-002 | 熔断/冷却/300012识别 | collector_guard / xhs_cookie_bridge | /api/circuit* | xhs_circuit | ACTIVE（只识别不破解） |

### 笔记 / 报告
| Feature ID | 功能 | Owner | API | DB | 状态 |
|---|---|---|---|---|---|
| FEATURE-CTH-NOTE-001 | 笔记库/详情/评论/去重 | database.py + collector | /api/notes*、/api/comments* | notes(957) | ACTIVE |
| FEATURE-CTH-NOTE-002 | 空正文 CDP 回填 | backfill_detail_cdp | — | notes | PLANNED（253条待稳定网络） |
| FEATURE-CTH-RPT-001 | 日/周/月/专题报告 | daily_report.py 🔴 | /api/report* | events/notes | ACTIVE |
| FEATURE-CTH-RPT-002 | 报告导出(pdf/xlsx/docx) | report_export/* | /api/report/export | — | ACTIVE（多实现待④收敛） |

### 系统 / 认证
| Feature ID | 功能 | Owner | API | UI | 状态 |
|---|---|---|---|---|---|
| FEATURE-CTH-AUTH-001 | 统一 Auth 恢复弹窗（不跳页） | auth_recovery_center + auth_global.js | /api/auth-recovery/* | 全局 Modal | DEVELOPING（4 v4子页已挂，主SPA未挂=AUTH-01） |
| FEATURE-CTH-AUTH-002 | 登录/权限/安全问答 | v4 auth + app Basic | /v4/auth/* | 登录/设置 | ACTIVE（三级权限仅1 owner） |
| FEATURE-CTH-SYS-001 | 系统健康/看门狗/自愈 | system_health_api/guardian | /healthz,/api/system/health | console | ACTIVE |
| FEATURE-CTH-SYS-002 | 版本中心/Git 自动同步 | version_center/git_manager | /v4/version-center/* | version_center | ACTIVE（标题漏括号 bug=P0-FIX-1） |
| FEATURE-CTH-SYS-003 | 临时公网隧道 | tunnel_guardian(cloudflared) | — | — | ACTIVE（固定域名未固化） |

## 二、ZBMP 母平台增强功能（共用 Core，非独立服务）

| Feature ID | 功能 | Owner | API | DB | UI | 状态 |
|---|---|---|---|---|---|---|
| FEATURE-ZBMP-BRAND-001 | 品牌增删/管理 | brand_knowledge_base | /api/brand* | brand_* | 品牌库 | ACTIVE |
| FEATURE-ZBMP-BRAND-002 | 品牌营销案例库 | case_deep_analysis/public_opinion_cases | /api/cases* | case_* | 案例库 | ACTIVE（再添加更新/下钻事件库待完善） |
| FEATURE-ZBMP-BRAND-003 | 太古/怡和(swire)专题 | swire_group/swire_brand_mapper | /api/swire* | swire_notes(空) | DEVELOPING |
| FEATURE-ZBMP-COLL-001 | 抖音适配器(XHR拦截) | v4/adapters/douyin.py | registry | — | DEVELOPING（已真出10条，未接管） |
| FEATURE-ZBMP-COLL-002 | Instagram 适配器 | v4/adapters/instagram.py | registry | — | DEVELOPING（DOM通道，待真机复验） |
| FEATURE-ZBMP-COLL-003 | Google 海外采集(付费代理) | v4/adapters/google.py | registry | — | EXPERIMENTAL（8真结果，3中转链） |
| FEATURE-ZBMP-COLL-004 | 统一 Cookie 保险库 | cookie_vault.py | — | data/cookies/*.json | ACTIVE（不入库不入源码） |
| FEATURE-ZBMP-AI-001 | Zachary 机器人/AI 分析抽屉 | intelligence + ai_analyzer | /api/ai* | ai_* | 抽屉 | ACTIVE（Ollama-only，规则兜底） |
| FEATURE-ZBMP-AI-002 | AI Web Worker（豆包/ChatGPT Web） | 研究稿 | — | — | PLANNED（仅架构，Cookie≠API） |
| FEATURE-ZBMP-IMP-001 | 外部数据导入(pdf/word/excel) | v4_upgrade/importer(3py) | — | — | PLANNED（无前端/无专表） |
| FEATURE-ZBMP-SETT-001 | 苹果风设置/密钥「사랑해」ZBMP解锁 | settings_module | /v4/settings/* | system_config | ACTIVE（椭圆小窗） |
| FEATURE-ZBMP-WS-001 | 工作区/项目/活动层级(Workspace→Campaign) | 待建 | — | — | PLANNED（IA 见 UI-FEATURE-MAP） |
| FEATURE-ZBMP-FUT-001 | 微博/B站/快手/贴吧/知乎适配器 | platform_adapters 占位 | registry | — | RESERVED（enabled=false） |

## 三、Feature 与红线/工单交叉

- 红线 Feature（SUBJ-001/EVT-001/RPT-001/RISK-001）任何改动走 Release Gate + 主体口径回归，禁止为扩量取消过滤。
- 在建工单索引：AUTH-01（主SPA挂弹窗）、SCHED-01（影子转门控，待签字）、DIM-01（双维度落库）、EVT-01（三类事件四关系）、P0-FIX-1（版本号括号）。
- 新增功能流程：登记 Feature ID → 绑 Owner/API/DB/UI → 旁路实现 → Staging 回归 → 灰度 ACTIVE。
