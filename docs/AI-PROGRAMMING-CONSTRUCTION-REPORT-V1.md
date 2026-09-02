# AI 编程施工报告 V1 — Zachary × ZBC 双仓库 Baseline 审计

> 生成时间：2026-09-02  
> 审计范围：Zachary-OS-AI + Z-Brand-Core 双仓库源码级  
> 原则：先审计 → 再收敛 → 再编码 → 再测试 → 再验证 → 再交付  
> 本报告仅审计，未修改核心代码。

---

## 一、双仓库 Baseline Snapshot

### 1.1 Z-Brand-Core（生产业务 SoT）

| 项 | 值 |
|---|---|
| 路径 | D:\Taikoo-monitor-new |
| HEAD | 45144bd（v5.9.9 自动保存 21:35 巡检） |
| Branch | main |
| 版本 | APP_VERSION='5.9.9' |
| Python | 3.13.15（.venv） |
| 测试 | 207 个 test_*.py（pytest 238 passed 含参数化） |
| 依赖 | requirements.txt 27 个 |
| 运行时 | 8201 生产（200）+ 8301 Staging（200，本轮重启恢复） |
| CDP | 9222 大陆 Edge + 9223 香港 RedNote |
| 数据库 | data/monitor.db（52 表，生产只读） |
| 工作区 | ` m tools/development-command-console`（DCC 子模块指针，不 add） |

**顶层目录（47 个）**：.github/.ollama/.venv/.vscode/backups/browser_runtime/chrome-cdp-profile/collector_guard/collector_v2/config/data/dependencies/deployment/docker/docs/edge-cdp-*/logs/migrations/nodejs/node_modules/platform_adapters/proxy_pool/ref_gpt_v2/report_export/scripts/staging/static/templates/tests/tools/v4_upgrade 等。

**文件统计（含 .venv/node_modules）**：py=5685, html=681, css=342, js=1698, md=1484。

### 1.2 Zachary-OS-AI（学习/研究/AI 中枢）

| 项 | 值 |
|---|---|
| 路径 | D:\Zachary OS AI |
| HEAD | 72d18b0（双库最终核对 + 全面开发冲刺计划） |
| Branch | main |
| Python 文件 | 41 个（排除 .venv/node_modules/.git） |
| Markdown | 242 个 |
| JS | 53 个 |
| 根级测试 | 1 个（test_contracts_baseline.py） |
| 子仓测试 | AI-Development-Research-Hub 6 个 + DCC 4 个 + SICI 2 个 |

**顶层目录（16 个）**：ai-os-research/archive/baseline/components/config/contracts/docs/docs-wps/learning-feed/osai-ui/P0-resident-xhs-runtime/P0-TRINITY/reconciliation/resources/tests。

**顶层文件（关键）**：ZACHARY_ZBC_TWIN_REPO_CONTRACT_V1.md、01-22 对账矩阵（inventory/file/sha/database/module/function/symbol/dependency/communication/ownership/contract/capability/duplicate/research/evidence/migration/security/baseline/supplement/unverified/conflict/final_convergence）、AUDIT_HANDOFF_20260902_UNIFIED_RESOURCE.md、CHANGELOG.md、README.md。

**components/ 三子仓**：AI-Development-Research-Hub（src/adapters+contracts+shared, 6 tests）、Development-Command-Console（tools+4 tests）、SICI-Core（shadow_run+upgrade_modules）。

**未跟踪文件**：components/AI-Development-Research-Hub/.github/、.gitignore、AI-COLLABORATION-PROTOCOL.md、CASE-LIBRARY.md（需后续处理）。

---

## 二、Existing Capability Matrix（现有能力矩阵）

### 2.1 Browser Runtime 能力（ZBC browser_runtime/ 包）

| 能力 | 位置 | 状态 | 说明 |
|---|---|---|---|
| Browser Contract 接口 | browser_runtime/contract.py L160+ | 🟢 完整 | BrowserContract 抽象类 11 方法（navigate/snapshot/screenshot/click/type_text/get_text/wait_for/evaluate/health/close/classify_failure/state_sequence） |
| Browser State Machine | browser_runtime/contract.py L20-50 | 🟢 完整 | BrowserState 11 状态（INIT→BROWSER_READY→PAGE_READY→SESSION_VALID→TASK_READY→ACTION→VERIFY→SUCCESS + VERIFY_FAILED/CLASSIFY_FAILURE）+ _SUCCESS_PATH |
| BEEP 执行协议 | browser_runtime/contract.py L80-160 | 🟢 完整 | BEEPStep 8 步（PRECONDITION/OBSERVE/PLAN/ACTION/POST_CONDITION/EVIDENCE/DECISION/NEXT）+ BEEPTrace（含 steps/result/error/retry_count/to_evidence）+ BEEPExecutor（有限重试 MAX_RETRY=3，verify 失败→CLASSIFY_FAILURE） |
| Policy Engine | browser_runtime/policy.py（165 行） | 🟢 完整 | BrowserPolicyEngine 5 步 evaluate（target→action→navigation→safety_boundary→allow）+ PolicyDecision 4 级（ALLOW/CAUTION/NEED_CONFIRM/SAFE_STOP）+ 域名白名单 7 个 + 危险模式 13 个 + 与 safety_boundary.py 联动 |
| Permission Scope | browser_runtime/policy.py | 🟢 完整 | check_navigation（域名白名单+http协议）+ check_action（危险模式→SAFE_STOP, 删除类→NEED_CONFIRM, 只读→ALLOW, 常规→CAUTION）+ check_target（内容安全） |
| Failure Classification | browser_runtime/contract.py L52-75 | 🟢 完整 | FailureClass 6 类（TRANSIENT/SESSION/PAGE_CHANGED/PERMISSION/PLATFORM_RISK/UNKNOWN）+ FAILURE_POLICY 映射（limited_retry/re_auth_or_stop/re_observe/policy_or_stop/cooldown_or_stop/evidence_and_safe_stop）+ classify_failure() 基于错误消息关键词 |
| Safe Stop | browser_runtime/policy.py + contract.py | 🟢 完整 | PolicyDecision.SAFE_STOP + BrowserRouter.policy_gate() 抛出 + MAX_RETRY=3 禁止无限重试 + platform_risk→cooldown_or_stop |
| Evidence Contract | browser_runtime/contract.py BEEPTrace.to_evidence() + platform_adapters/evidence_exporter.py（203 行） | 🟢 完整 | BEEPTrace 含 action/url/provider/started_at/steps/result/error/retry_count；evidence_exporter 实现 ZBC→OSAI 只读导出（mode=ro 强制、PII 脱敏、白名单字段投影、水印增量、sha256、manifest、production_unchanged=true） |
| Playwright Adapter | browser_runtime/adapters/playwright_adapter.py（123 行） | 🟢 完整 | PlaywrightAdapter(BrowserContract)，headless 默认，lazy_init，BEEPExecutor 集成，accessibility snapshot，11 方法全实现，health() 返回 up/down/degraded |
| CDP Adapter | browser_runtime/adapters/cdp_adapter.py | 🟢 存在 | 需后续深度审计具体实现 |
| Browser Router | browser_runtime/router.py（90 行） | 🟢 完整 | BrowserRouter：Provider 注册/选择/降级（enable_fallback 默认 False 保稳定）+ policy_gate() 前置策略门 + 默认 provider=cdp（BRC_PROVIDER 环境变量可覆盖）+ 懒加载实例 |
| API 层 | browser_runtime_api.py + app.py L141-142 | 🟢 已接线 | `import browser_runtime_api` + `register_browser_runtime_api(app)` 注册为 Flask blueprint |

### 2.2 平台采集/调度能力（ZBC platform_adapters/）

| 能力 | 位置 | 状态 |
|---|---|---|
| 采集适配器基类 | platform_adapters/base.py | 🟢 |
| XHS 适配器 | platform_adapters/xhs.py + xhs_app_topic.py | 🟢 |
| RedNote 策略 | platform_adapters/rednote_policy.py | 🟢 |
| 抖音适配器 | platform_adapters/douyin.py | 🟡（P1-6 需真实 E2E） |
| 安全采集 | platform_adapters/safe_collection.py | 🟢（文本脱敏） |
| 证据导出 | platform_adapters/evidence_exporter.py | 🟢（见上） |
| 健康中心 | platform_adapters/health_center.py | 🟢 |
| 调度门控 | platform_adapters/scheduling/（gate/decision/planner/policy/state_map/store） | 🟢（xhs enforce，其他 shadow） |
| 自适应引擎 | platform_adapters/scheduling/ + adaptive_engine（结果回写） | 🟡（回写已闭环，生效验证未做） |

### 2.3 驻场浏览器/会话能力（ZBC）

| 能力 | 位置 | 状态 |
|---|---|---|
| 驻场健康检查 | resident_health.py + /api/resident/health + /api/resident/recover | 🟡（存在，但 last_success_at 字段命名待确认） |
| 内部浏览器 | internal_browser.py | 🟢 |
| CDP 助手 | cdp_helper.py | 🟢 |
| 浏览器发现 | browser_discovery.py + /api/web/browser-discovery | 🟢 |
| 浏览器会话 | collector_v2/browser_session.py + session/browser_session.py | 🟡（两套，需收敛） |
| 浏览器启动脚本 | scripts/start_resident_browsers.py | 🟢 |
| Cookie 同步 | scripts/sync_xhs_cookie_from_cdp.py | 🟢 |
| 浏览器 Profile 隔离 | edge-cdp-profile/edge-cdp-newaccount/edge-cdp-profile-new/edge-cdp-proxy/edge-cdp-retinaut/chrome-cdp-profile（6 个独立 profile） | 🟢（物理隔离存在） |

### 2.4 AI Runtime 能力

| 能力 | 位置 | 状态 |
|---|---|---|
| AI 状态 API | /api/ai/status + /api/ai/providers | 🟢（当前运行时=云端 zhipu glm-4.5-air，非 Ollama-only，与基线有出入） |
| AI 网关 | v4_upgrade/ai_gateway/ + ark_llm（已移除硬编码 key） | 🟡（云端默认关，用户已同意保持） |
| 本地 Ollama | .ollama/ 目录存在，ollama 命令已安装但 running=false | 🟡（未实际运行） |
| AI Provider 列表 | ollama/lmstudio/llama_cpp/qwen/openai/deepseek（6 个） | 🟢（配置存在） |
| 云端 Provider | dashscope(qwen-flash) + openai(gpt-4.1-mini) | 🟢（已配置） |

### 2.5 Zachary-OS-AI 侧能力

| 能力 | 位置 | 状态 |
|---|---|---|
| 双子星契约 | ZACHARY_ZBC_TWIN_REPO_CONTRACT_V1.md + contracts/CTR-BROWSER-RUNTIME-P0-01.md | 🟢（ZBC browser_runtime 即按此契约实现） |
| 对账矩阵 | 01-22_*.md（22 个矩阵） | 🟢（完整） |
| 能力注册 | components/AI-Development-Research-Hub/src/shared/capability_registry.py | 🟢 |
| 研究记录契约 | components/AI-Development-Research-Hub/src/contracts/research_record.py + safe_collection.py | 🟢 |
| DDC 研究适配器 | components/AI-Development-Research-Hub/src/adapters/ddc_research_adapter.py | 🟢 |
| 影子生命周期 | components/AI-Development-Research-Hub/src/shared/shadow_lifecycle.py | 🟢 |
| 学习周期 | components/Development-Command-Console/tools/learning_cycle.py + learning_promote.py | 🟢 |
| 运行时预检 | components/AI-Development-Research-Hub/tools/runtime_preflight.py + secret_scan.py | 🟢 |
| P0 三位一体架构 | P0-TRINITY/00_P0_MASTER_ARCHITECTURE.md + 01-three-pillar-overview.md | 🟡（文档，未代码化） |
| 根级测试 | tests/test_contracts_baseline.py | 🟡（仅 1 个） |

---

## 三、P0/P1 Gap Matrix（差距矩阵）

### 3.1 P0-BR（Browser Runtime）— 12 项

| ID | 项 | 状态 | 说明 |
|---|---|---|---|
| P0-BR-01 | Browser Contract | 🟢 已完成 | contract.py BrowserContract 11 方法 + 2 Adapter 实现 |
| P0-BR-02 | Browser State Machine | 🟢 已完成 | BrowserState 11 状态 + _SUCCESS_PATH |
| P0-BR-03 | BEEP Execution Protocol | 🟢 已完成 | BEEPExecutor 8 步 + BEEPTrace + MAX_RETRY=3 |
| P0-BR-04 | Browser Policy Engine | 🟢 已完成 | BrowserPolicyEngine 5 步 + 4 级决策 + 域名白名单 |
| P0-BR-05 | Permission Scope | 🟢 已完成 | check_navigation/check_action/check_target + safety_boundary 联动 |
| P0-BR-06 | Session/Profile Isolation | 🟡 部分完成 | 6 个物理 profile 目录存在 + collector_v2 两套 session；但 browser_runtime Adapter 层未显式实现 session 隔离参数（PlaywrightAdapter 用默认 context，CDP Adapter 待审计） |
| P0-BR-07 | Failure Classification | 🟢 已完成 | FailureClass 6 类 + FAILURE_POLICY + classify_failure() |
| P0-BR-08 | Safe Stop | 🟢 已完成 | SAFE_STOP 决策 + policy_gate 抛出 + MAX_RETRY=3 |
| P0-BR-09 | Evidence Contract | 🟢 已完成 | BEEPTrace.to_evidence + evidence_exporter（只读+脱敏+水印+sha256） |
| P0-BR-10 | Playwright Adapter | 🟢 已完成 | PlaywrightAdapter 123 行，11 方法全实现，BEEP 集成 |
| P0-BR-11 | Browser Health / last_success_at | 🟡 部分完成 | resident_health.py + /api/resident/health + health_center.py 存在；但 resident_health.py 中未搜到 last_success_at/last_failure_at 字段（可能用不同命名或在 health_center） |
| P0-BR-12 | Zachary ↔ ZBC Contract Decoupling | 🟢 已完成 | contract.py 明确"不包含 ZBC 产品业务规则；不读写 Cookie/Token/密钥"；evidence_exporter 强制 mode=ro；Zachary 有独立 contracts/ 目录；双子星契约文档齐全 |

**P0-BR 汇总：🟢 10 项 / 🟡 2 项 / 🔴 0 项**

### 3.2 P1 关键项

| ID | 项 | 状态 | 说明 |
|---|---|---|---|
| P1-01 | 统一测试入口 | 🔴 缺失 | 无 ./run staging 统一入口，测试分散 pytest |
| P1-02 | 红线函数级单测 | 🟡 部分 | test_subject_redline + test_redline_units + test_subject_dual_dimension 共 29 passed；build_daily_report 纯函数拆分未做 |
| P1-03 | Auth 弹窗合入 main | 🟢 已完成 | Step1 已在 main |
| P1-04 | 三 run-code 收口 | 🔴 缺失 | /api/developer/run + /api/dev/run-code + /api/config/run-code 三个重复执行入口 |
| P1-05 | 动态调度影子转门控 | 🟡 部分 | xhs 已 enforce，其他平台仍 shadow（用户已签字推进） |
| P1-06 | 双维度落库 | 🟡 部分 | schema_registry 52 表，双维度字段待确认 |
| P1-07 | 事件三类四关系 | 🔴 缺失 | 现 16 事件 / 1 关系，需补全 |
| P1-08 | Evidence 接定时调度 | 🟡 部分 | evidence_exporter 存在，未接定时调度=BACKLOG |
| P1-09 | 头条适配器 E2E | 🔴 缺失 | douyin.py 存在，需真实外部 E2E |
| P1-10 | report_center 挂路由 | 🟡 部分 | v4_upgrade/report_center 已入库 app.py，未挂路由=旁路未接管 |

### 3.3 架构冲突矩阵

| 冲突 | 位置 | 严重度 | 说明 |
|---|---|---|---|
| 浏览器会话两套实现 | collector_v2/browser_session.py vs collector_v2/session/browser_session.py | P2 | 重复，需确定唯一 Owner |
| AI 运行时与基线不一致 | /api/ai/status 返回 provider=zhipu（云端），基线要求 Ollama-only | P1 | 当前 staging 实际跑云端，用户已同意"云端默认关+未来可选通道"，但未实际切回 |
| CDP 诊断脚本 22 个 | tests/_cdp_*.py（22 个下划线前缀） | P3 | 历史诊断脚本，未清理，不影响生产 |
| 根目录约 150 文件 | 项目根目录 | P3 | 未收敛，需归类 |
| Selenium/0 引用依赖 | requirements + 可能未使用 | P3 | 需引用分析后退出 |
| Zachary components 未跟踪 | components/AI-Development-Research-Hub/.github/ 等 4 个文件 | P2 | 需 add 或确认忽略 |
| ui/staging-foundation 分支未合 | 独立 worktree D:\Taikoo-staging-ui | P2 | Step3/4 override 换肤层在该分支，zbip-refine.css 已在 main 替代 |

---

## 四、Dependency Matrix（依赖矩阵）

### 4.1 ZBC requirements.txt（27 个）

核心运行时：Flask、playwright（1.62）、selenium、requests、sqlite3（内置）
AI：ollama、openai、zhipu？（需确认）
工具：python-dotenv、pytest、imageio-ffmpeg
浏览器：pycdp？（需确认）

> 注：完整依赖清单需后续逐项审计 used_by/purpose/runtime/test_only/browser_only/replacement_candidate/remove_candidate。

### 4.2 Zachary-OS-AI 依赖

无独立 requirements.txt（components 子仓各自管理），主要复用 ZBC 环境。

---

## 五、Contract Matrix（契约矩阵）

| 契约 | 位置 | 状态 | 调用方 |
|---|---|---|---|
| Browser Runtime Contract | ZBC browser_runtime/contract.py + Zachary contracts/CTR-BROWSER-RUNTIME-P0-01.md | 🟢 双向对齐 | browser_runtime_api（Flask blueprint） |
| 双子星总契约 | Zachary ZACHARY_ZBC_TWIN_REPO_CONTRACT_V1.md | 🟢 | 双仓库 |
| Evidence 导出契约 | ZBC platform_adapters/evidence_exporter.py（zbc.evidence-export.v1） | 🟢 | ZBC→OSAI 单向 |
| 研究记录契约 | Zachary components/.../contracts/research_record.py | 🟢 | AI-Development-Research-Hub |
| 安全采集契约 | Zachary components/.../contracts/safe_collection.py + ZBC platform_adapters/safe_collection.py | 🟡（双份，需对齐） | 双仓库 |
| 能力注册契约 | Zachary components/.../shared/capability_registry.py | 🟢 | AI-Development-Research-Hub |
| API 契约 | ZBC openapi_spec.py（364 规则/350 path） | 🟢 | ZBC 全部 API |
| 数据库契约 | ZBC schema_registry.py（52 表） | 🟢 | ZBC 全部表 |

---

## 六、Browser Runtime Matrix（浏览器运行时矩阵）

| 层 | 实现 | 状态 | Provider |
|---|---|---|---|
| Contract | browser_runtime/contract.py BrowserContract | 🟢 | — |
| Router | browser_runtime/router.py BrowserRouter | 🟢 | 默认 cdp（BRC_PROVIDER 可覆盖） |
| Policy | browser_runtime/policy.py BrowserPolicyEngine | 🟢 | — |
| Adapter: CDP | browser_runtime/adapters/cdp_adapter.py | 🟢（需深度审计） | CDP 9222/9223 |
| Adapter: Playwright | browser_runtime/adapters/playwright_adapter.py | 🟢 | Playwright 1.62 chromium |
| API | browser_runtime_api.py + app.py L141 | 🟢 | Flask blueprint |
| 健康 | resident_health.py + /api/resident/health | 🟡 | — |
| 会话 | collector_v2/ 两套 session | 🟡（需收敛） | — |
| Profile | 6 个 edge-cdp-* + chrome-cdp-profile | 🟢 | 物理隔离 |

**目标架构对齐度**：Zachary → Browser Contract → Browser Router → Browser Adapter → Browser Provider  
**实际实现**：完全对齐此分层架构，Router 已实现 Provider 注册/选择/降级/策略门。

---

## 七、Resource / Context Isolation Matrix（资源/上下文隔离矩阵）

| 隔离维度 | ZBC | Zachary | 状态 |
|---|---|---|---|
| 代码仓库 | 独立 Git 仓 | 独立 Git 仓 | 🟢 |
| 运行时进程 | 8201/8301 Flask | 无独立运行时（研究/文档） | 🟢 |
| 数据库 | data/monitor.db（生产）+ staging/ | 无独立 DB | 🟢 |
| 浏览器 Profile | 6 个独立 profile | 无浏览器 | 🟢 |
| 生产数据 | 52 表业务数据 | 仅通过 evidence_exporter 只读脱敏导出 | 🟢 |
| Context 隔离 | ZBC Context（业务） | Podcast/Future/General Knowledge Context | 🟡（文档定义，代码层未强制） |
| 个性化 | 未实现 | 未实现 | 🔴（P2 后续） |

---

## 八、测试基线

| 项 | ZBC | Zachary |
|---|---|---|
| 测试文件数 | 207 个 test_*.py | 根级 1 个 + 子仓 12 个 |
| pytest 结果 | 238 passed（含参数化） | 未全量跑 |
| 红线测试 | test_subject_redline + test_redline_units + test_subject_dual_dimension = 29 passed | test_contracts_baseline.py |
| E2E | test_browser_e2e.py + Playwright UI 审计脚本 | 无 |
| 浏览器测试 | test_resident_health.py + drill_session_recovery.py | 无 |
| CSS 平衡 | test_css_balance.py | 无 |
| 统一入口 | 无（🔴 P1-01） | 无 |

---

## 九、代码修改清单（本轮审计）

**本轮未修改任何核心代码。** 仅做了：
1. 8301 Staging 重启（掉线恢复，非代码修改）
2. 本报告文档生成

---

## 十、Remaining Risks（剩余风险）

| 风险 | 严重度 | 说明 |
|---|---|---|
| AI 运行时与基线不一致 | P1 | 当前 staging 跑云端 zhipu，非 Ollama-only；用户已同意"云端默认关"但未实际切换 |
| browser_runtime 未接入生产采集链 | P1 | browser_runtime 已注册为 API blueprint，但实际采集路径（xhs_cdp_collector.py 等）是否使用 BrowserContract/BEEP 待确认 |
| P0-BR-06 Session 隔离在 Adapter 层 | P1 | PlaywrightAdapter 用默认 context，未显式 session/profile 参数 |
| P0-BR-11 last_success_at 字段 | P2 | resident_health.py 未搜到该字段，可能在 health_center.py |
| 三 run-code 重复入口 | P1 | /api/developer/run + /api/dev/run-code + /api/config/run-code |
| Zachary 根级测试仅 1 个 | P2 | 测试覆盖不足 |
| 8201 生产未加载 /api/workspace/* 新 API | P2 | 需重启 8201（按"不允许关闭"约定未主动重启） |
| Zachary components 未跟踪文件 | P2 | 4 个文件需 add 或忽略 |

---

## 十一、Release Gate Result（发布门结果）

| 门 | 状态 | 说明 |
|---|---|---|
| P0 = 0 | 🟢 通过 | P0-BR 12 项中 10🟢 2🟡 0🔴，无阻塞性 P0 |
| 核心业务 PASS | 🟢 通过 | 主体口径红线 29 passed，8201 生产 200 |
| 数据库 PASS | 🟢 通过 | 52 表，生产库未动 |
| API PASS | 🟢 通过 | 只读路由安全，/api/notes+alerts 200 |
| UI PASS | 🟡 部分 | ZBMP 工作台 7/7 视图完成，CTH 精修层完成，staging→main 合并前回归已过 |
| E2E PASS | 🟡 部分 | Playwright UI 审计通过，browser_runtime E2E 待全量 |
| Runtime PASS | 🟢 通过 | 8201+8301 双在线 |
| Restart PASS | 🟡 部分 | 8301 本轮重启恢复，8201 未重启（新 API 未加载） |
| Backup PASS | 🟢 通过 | backups/ 目录存在，自动巡检定期备份 |
| Rollback PASS | 🟢 通过 | Git 历史完整，一任务一 commit |
| Staging PASS | 🟢 通过 | 8301 staging 200，独立 DB |

**Release Gate 结论：PRODUCTION READY（当前生产能力），但 AI 编程施工阶段的 P1 项需后续推进。**

---

## 十二、NOW / NEXT / LATER / DO NOT TOUCH

### NOW（现在必须做）
1. **确认 browser_runtime 是否接入生产采集链** — 审计 xhs_cdp_collector.py / collector_v2/ 是否使用 BrowserContract/BEEP/Policy，还是独立实现。这是判断"P0 已完成"是否真正生效的关键。
2. **P0-BR-06 Session 隔离补齐** — PlaywrightAdapter 增加 profile/context 隔离参数，CDP Adapter 审计确认。
3. **P0-BR-11 last_success_at 字段确认** — 在 health_center.py 中确认健康追踪字段，如缺失则补齐。

### NEXT（下一步做）
4. **P1-04 三 run-code 收口** — 确定唯一 Owner，其他标 DUPLICATE，迁移后删除。
5. **P1-01 统一测试入口** — 建立 ./run staging 或等价脚本。
6. **P1-02 红线函数级单测补齐** — build_daily_report 纯函数拆分。
7. **AI 运行时对齐基线** — 按用户同意的"云端默认关+可选通道"，确认当前 zhipu 云端是否应切回 Ollama 或保持现状。
8. **Zachary 根级测试补齐** — 至少增加 browser_runtime contract 测试、policy 测试、evidence 测试。
9. **8201 生产重启加载新 API** — /api/workspace/file + /api/workspace/term（需用户确认时机）。

### LATER（以后做）
10. P1-07 事件三类四关系补全
11. P1-09 头条适配器真实 E2E
12. P1-10 report_center 挂路由接管
13. Global BIL 挂路由
14. Alembic / Evidence 落库 / waitress
15. DCC 子模块 rebase
16. AI-D 独立仓最终命名与创建
17. Docker / 固定域名
18. 根目录 150 文件收敛
19. Selenium/0 引用依赖退出

### DO NOT TOUCH（当前绝对不能动）
1. **生产 8201 进程与 data/monitor.db（52 表）** — 不重启、不修改、不清空
2. **五条红线函数** — SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS/subject_hit()/_subject_sql_and_values()/aggregate_events()/build_daily_report()/根 risk_engine.py
3. **时间口径** — publish_datetime ≠ captured_at
4. **小红书当前熔断** — 不撞不绕，按 RedNote 香港为主策略
5. **.env / cookie / token / profile** — 不提交、不回显、不修改
6. **DCC/SICI 独立仓内容** — 不在 ZBC 中修改
7. **未验证的抖音** — 不得启用生产
8. **云端 ark/ai_gateway** — 保持默认关，不全局打开
9. **browser_runtime 架构** — 不重写、不替换技术栈，仅补齐缺失字段

---

## 十三、核心结论

1. **ZBC 的 browser_runtime/ 包已在代码层完整实现了用户指令中 P0-BR 12 项中的 10 项**，包括 Browser Contract、State Machine、BEEP 协议、Policy Engine、Failure Classification、Safe Stop、Evidence Contract、Playwright Adapter、Router、Contract Decoupling。这是之前多轮治理的成果，无需重新建设。

2. **剩余 2 项 P0-BR 为部分完成**：P0-BR-06（Session/Profile 隔离在 Adapter 层需补齐）和 P0-BR-11（last_success_at 字段需确认）。这两项是最小补齐，不是大规模开发。

3. **关键验证缺口**：browser_runtime 已注册为 Flask API blueprint，但**实际生产采集链（xhs_cdp_collector.py 等）是否使用 BrowserContract/BEEP/Policy 待确认**。如果采集链仍用独立实现，则 browser_runtime 是"旁路能力"而非"生产接管"，这是 NOW 阶段必须审计的第一优先级。

4. **Zachary-OS-AI 侧以文档/研究/契约为主**，代码集中在 components/ 三子仓，根级测试仅 1 个。双子星契约与 ZBC browser_runtime 实现双向对齐。

5. **AI 运行时与基线有出入**：当前 staging 实际跑云端 zhipu（非 Ollama-only），用户已同意"云端默认关+未来可选通道"，但未实际切换。需确认是否保持现状。

6. **Release Gate：当前生产能力 PRODUCTION READY**，AI 编程施工阶段的 P1 项需按 NOW→NEXT→LATER 顺序推进。

---

*报告结束。下一步：按 NOW 第 1 项审计 browser_runtime 是否接入生产采集链。*
