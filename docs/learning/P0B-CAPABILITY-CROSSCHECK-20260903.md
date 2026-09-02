# P0-B Capability Registry 源码级交叉验证（glm-5.3）

> 日期：2026-09-03 | 模型：glm-5.3 | 消耗：per_call 1次
> 目的：核对「文档声称已落地」与「真实源码」是否一致（防假闭环）

---

Let me analyze each file against the claimed capabilities carefully, only using the provided source code headers.

1. **system_health_api.py** = 系统健康监控（统一监控面板/状态文件/API）
   - Docstring says: "系统控制中心 API v1.0, 5层闭环架构 - 第四层：运行状态闭环, 功能：统一监控面板，实时显示所有模块状态"
   - Has Flask Blueprint, HEALTH_STATUS_FILE defined as JSON status file
   - Claims: unified monitoring panel ✓ (docstring), status file ✓ (HEALTH_STATUS_FILE), API ✓ (Blueprint)
   - Conclusion: OK

2. **resident_health.py** = 驻场浏览器健康三层探测(L1端口/L2 CDP/L3登录态)+自动恢复
   - Docstring explicitly describes: L1 端口存活, L2 CDP 连通, L3 登录态有效
   - Status levels: HEALTHY/NEEDS_LOGIN/CDP_DEGRADED/DOWN with auto-recovery descriptions
   - Mentions 自动恢复 in title: "双身份独立健康检查 + 自动恢复 + 状态持久化"
   - Conclusion: OK (three-layer probing explicitly documented; auto-recovery described in docstring, though actual implementation not shown—but docstring is quite detailed about the recovery mechanism. The claim matches the docstring. However, we only see docstring, not code. The docstring is detailed enough that I'd say OK, though strict verification of implementation would need code body. The task says "该文件头是否确实实现了文档声称的能力" - judging from the header. The docstring explicitly claims these features. For OK I should be confident. The header clearly describes L1/L2/L3 and auto recovery. I'll say OK but note implementation body not shown? Actually the instruction says only based on given source headers. The docstring explicitly matches. OK.

3. **collector_guard/metrics.py** = 采集侧性能指标
   - Docstring: "GuardMetrics：线程安全的采集指标（成功率、平均/分位延迟、近期结果），仅内存，可选落盘"
   - Code shows: threading.RLock, deque for latency, ok, total, success, failure, last_success_at, last_failure_at, last_error, record() method
   - This matches "采集侧性能指标" - success rate, latency percentiles
   - Conclusion: OK

4. **collector_guard/risk_engine.py** = 风险引擎六态生命周期+熔断冷却恢复+半开探测
   - Docstring describes: 与 state.py 的离散七态互补... wait, it says "与 state.py 的离散七态互补" — the state.py has SEVEN states, and this module provides continuous 0-100 risk score mapped to five tiers:
     - 0-29 NORMAL, 30-49 WATCH, 50-69 THROTTLED, 70-84 COOLDOWN, 85-100 CIRCUIT_OPEN
   - That's FIVE risk tiers (档位), not six states. The claim says "六态生命周期" (six-state lifecycle). The docstring says state.py has 七态, and this module has five tiers.
   - Claim: 风险引擎六态生命周期+熔断冷却恢复+半开探测
   - Evidence: 熔断 (CIRCUIT_OPEN) ✓, 冷却 (COOLDOWN) ✓, 恢复 ("风险分随成功/健康响应衰减...健康→升高→熔断→恢复检查→逐渐恢复 的闭环") ✓
   - But "六态" is not confirmed: docstring mentions 七态 and 五档. "半开探测" (half-open probing) - the docstring says "走恢复检测" and "恢复检查" but doesn't explicitly say "半开" (half-open). Circuit breaker half-open state is a specific pattern. The docstring says "熔断（停止任务，走恢复检测，不无限重试）" which suggests recovery detection but not explicitly half-open.
   - So: 六态 mismatch (七态/五档), 半开探测 not explicitly confirmed. Conclusion: 疑似失实 or 需补证. The tier count discrepancy is notable: claim says six states but evidence shows five tiers / seven states mentioned. "熔断冷却恢复" is confirmed. "半开探测" needs more evidence.
   - I'd say 疑似失实 on the state count (六态 vs 七态/五档), and 半开探测 needs verification. Actually more precisely: the claimed "六态生命周期" is not supported — the module itself defines 5 档位 and references state.py's 七态. So partial mismatch → 疑似失实 (数量口径不符) or 需补证. Given the explicit count discrepancy, I'll mark 疑似失实 with note that 熔断/冷却/恢复 are confirmed but 六态 and 半开探测 unconfirmed/mismatched.

5. **database.py** = 54表,五时间模型(发布/采集/事件/更新/快照分离),metric_snapshots指标时序
   - Header shows: "SQLite 数据层（v4 修复版）", imports, DB_PATH env var, SCHEMA starts with notes table
   - No evidence of: 54 tables, five time models, metric_snapshots table
   - Only the beginning of SCHEMA (notes table) is shown
   - Conclusion: 需补证 (cannot confirm 54 tables, five time models, metric_snapshots from the header alone)

6. **data_query_api.py** = 只读查询API
   - Docstring: "数据查询 API 蓝图（app.py 巨石拆分 · 第 1 批，P1-10）。只搬迁"纯只读、仅依赖 database 模块 + Flask"的查询接口"
   - Code: register_data_query_api(app), Blueprint, /api/stats endpoint
   - This matches "只读查询API" ✓
   - Conclusion: OK

7. **platform_adapters/safe_collection.py** = 无公害采集契约层(脱敏/限速/审计)
   - Docstring: PII 脱敏 redact_text / redact_record, CollectionHygienePolicy + RateGovernor, build/validate_collection_audit, run_offline_pipeline
   - 脱敏 ✓ (redact_text/redact_record), 限速 ✓ (RateGovernor), 审计 ✓ (build/validate_collection_audit)
   - Conclusion: OK

8. **runtime_bin.py** = 统一node解析器(env→which→内置→系统路径)
   - Docstring explicitly: 解析顺序 1. NODE_EXE/ZBC_NODE_PATH 2. PATH中的node (shutil.which) 3. 项目内置nodejs/node(.exe) 4. 操作系统常见安装路径
   - Exactly matches env→which→内置→系统路径
   - Conclusion: OK

9. **internal_browser_stream.py** = 内置浏览器CDP Screencast SSE实时流
   - Docstring: "实时画面流（Screencast over SSE）... Page.startScreencast... SSE 把最新帧推给前端"
   - Matches: CDP Screencast ✓, SSE ✓, real-time streaming ✓, reference counting, single daemon thread, reconnect
   - Conclusion: OK

10. **dev_exec_core.py** = 代码执行沙箱+JSONL审计+guard闸门
    - Docstring: "GAP-04 三 run-code 统一收口核心", describes three execution endpoints, execute_dev_code_safe(), "统一安全闸门、统一执行环境、统一返回格式"
    - Claims: 代码执行沙箱 — the docstring says "受限命名空间 exec" and "统一执行环境" but doesn't explicitly say "沙箱" (sandbox). Hmm. "受限命名空间 exec" suggests a restricted namespace execution, which is a form of sandboxing. But strictly, "沙箱" is not explicitly mentioned.
    - JSONL审计 — not mentioned in the header. Imports include hashlib, json, shutil, datetime. No explicit mention of JSONL audit log in the docstring.
    - guard闸门 — "统一安全闸门" is mentioned ✓
    - So: 沙箱 partially supported (受限命名空间 exec ≈ 沙箱语义 but word not used; "统一执行环境"), JSONL审计 not confirmed in header, guard闸门 confirmed (统一安全闸门).
    - Conclusion: 需补证 (JSONL审计无头部证据；沙箱仅有"受限命名空间"间接暗示) — I'd say 需补证 for the JSONL audit part. The overall capability "代码执行统一收口+安全闸门" is confirmed, but "JSONL审计" specifically is not evidenced. Mark as 需补证.

Let me be precise:

1. system_health_api.py — OK. Docstring states 统一监控面板 + HEALTH_STATUS_FILE 状态文件 + Flask Blueprint API，三项均有头部证据。

2. resident_health.py — OK. Docstring 明确 L1端口/L2 CDP/L3登录态三层探测 + 状态分级(HEALTHY/NEEDS_LOGIN/CDP_DEGRADED/DOWN) + 自动恢复(重启/拉起)。头部自述完整，但实现体未展示——严格来说 docstring 声称了，代码体没看到。Task says "该文件头是否确实实现了文档声称的能力" — 只能依据头部。头部声明与声称能力完全一致。OK。

3. collector_guard/metrics.py — OK. 类实现可见（部分代码体），成功率/延迟/近期结果 via deque + record()，线程安全 via RLock。与"采集侧性能指标"匹配。

4. collector_guard/risk_engine.py — 疑似失实/口径不符。五档(NORMAL/WATCH/THROTTLED/COOLDOWN/CIRCUIT_OPEN)而非声称"六态"；state.py 是"七态"。熔断/冷却/恢复闭环有据，但"六态生命周期"与"半开探测"头部无据（"恢复检测"≠明确半开）。结论：疑似失实（态数口径不符）+半开探测需补证。Hmm, which to pick? The