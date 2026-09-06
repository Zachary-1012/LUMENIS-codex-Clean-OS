# P0-B 自动对账报告 — Capability ↔ 源码（可复跑）

- 运行时间：2026-09-04 04:42
- 源：`OSAI config/skills-registry.json`（schema 1.0.0）↔ 双子库源码
- 规则：只读核验；MISSING=声称文件不存在；PASS=文件在且符号可验；N/A=目录型定位

## 一、production_capabilities 对账（9 条）

| ID | 名称 | 声称 location | status | 核验 | 符号抽样 |
|---|---|---|---|---|---|
| PROD-01 | 主系统入口 | `ZBC/app.py` | active | PASS | _load_dotenv, _thread_excepthook, brand_knowledge_stats |
| PROD-02 | AI 网关 (智谱驱动) | `ZBC/intelligence.py` | active | PASS | _env, _get_json, _installed_hints |
| PROD-03 | 事件聚合权威 | `ZBC/event_graph.py` | active | PASS | _get_db, _now, _text_tokens |
| PROD-04 | 日报生成 (AI 摘要) | `ZBC/daily_report.py` | active | PASS | calculate_risk_index, calculate_brand_health_score, _collection_health |
| PROD-05 | 笔记 AI 复核 | `ZBC/ai_filter.py` | active | PASS | assess_content_quality, detect_noise_type, ai_secondary_review |
| PROD-06 | 安全扫描器 (含 Agent/AI 供应链) | `ZBC/security_scanner.py` | active | PASS | SecurityScanner |
| PROD-07 | 浏览器运行时 (P0) | `ZBC/browser_runtime/ + browser_runtime_api.py` | active | PASS | register_browser_runtime_api |
| PROD-08 | Agent 安全层 | `ZBC/agent_security.py` | active | PASS | is_instruction_attempt, sanitize_input, validate_tool_call |
| PROD-09 | AI 学习引擎 | `ZBC/ai_learning_engine.py` | review | PASS | AILearningEngine, WebSentimentSearch, get_ai_learning_engine |

## 二、research_capabilities 对账（10 条）

| ID | 名称 | 声称 location | status | 核验 |
|---|---|---|---|---|
| RESEARCH-01 | P0 小红书 Resident Runtime 研究 | `P0-resident-xhs-runtime/` | completed | PASS |
| RESEARCH-02 | OS-AI 白皮书与技术雷达 | `ai-os-research/01-whitepaper.md, 02-capability-radar.md` | active | PASS |
| RESEARCH-03 | 架构 2030 与路线图 | `ai-os-research/04-architecture-2030.md, 11-roadmap.md` | active | PASS |
| RESEARCH-04 | 体验引擎 (Experience Engine) | `ai-os-research/05-experience-engine.md` | active | PASS |
| RESEARCH-05 | 研究与代码转化 (Research-to-Code) | `ai-os-research/06-research-to-code.md` | active | PASS |
| RESEARCH-06 | AI 浏览器运行时 (AI Browser) | `ai-os-research/07-ai-browser.md` | active | PASS |
| RESEARCH-07 | 主动智能 (Proactive Intelligence) | `ai-os-research/08-proactive-intelligence.md` | active | PASS |
| RESEARCH-08 | 安全/权限/沙箱 (Safety-Permission-Sandbox) | `ai-os-research/09-safety-permission-sandbox.md` | active | PASS |
| RESEARCH-09 | 评估框架 (Evaluation Framework) | `ai-os-research/10-evaluation-framework.md` | active | PASS |
| RESEARCH-10 | CTH-POMS / ZBMP 报告 | `ai-os-research/16-cth-poms-report.md, 17-zbmp-report.md` | active | PASS |

## 三、contracts 对账

- `contracts/CTR-BROWSER-RUNTIME-P0-01.md` → PASS
- `baseline/FINAL-AUDIT-AND-SPRINT-PLAN-20260902.md` → PASS
- `ZACHARY_ZBC_TWIN_REPO_CONTRACT_V1.md` → PASS

## 四、结论

- production_capabilities：9 条，MISSING 0 条
- research_capabilities：10 条，MISSING 0 条
- contracts：3 条
- 对账结果仅作只读核验；MISSING 项需人工判断（location 描述过时 or 路径拼写），不自动改 registry。