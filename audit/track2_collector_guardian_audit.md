# ZBC 全量落地 - Track 2: Collector & Scheduler & Runtime Guardian 审计报告

**审计日期**: 2026-09-06
**审计范围**: collector.py, collector_automation.py, collector_auto_start.py, collector_guard_integration.py, collector_v2_integration.py, xhs_*.py, collector_v2/, collector_guard/, runtime_guardian.py, system_guardian.py, system_watchdog.py, auto_recovery.py, tunnel_guardian.py, monitor_pipeline.py, monitoring.py, learning_collector.py, learning_persistence.py, check_collection.py, check_collection_detail.py
**Python 环境**: .\.venv\Scripts\python.exe
**验证方式**: 实际导入、实例化、状态转换、重试/DLQ、Scheduler 触发（非代码审查）

---

## 一、总体结论

| 维度 | 结果 | 说明 |
|------|------|------|
| Runtime Guardian 完整链 | **PASS** | Worker→Lease→Heartbeat→Checkpoint→Reaper→Retry→DLQ→Resume 全部可调用并验证通过 |
| Collector 七态状态机 | **PASS（修复后）** | 新增 CollectorLifecycleState 七态枚举 + transition_state 方法 + 状态转换校验 |
| Scheduler | **PASS** | 任务注册、冷却、每日限额、回调、状态跟踪均正常 |
| XHS Collector 全链路 | **PASS（代码层）** | 登录→Cookie→CDP→Playwright→Search→Parse→Normalize→Dedup→Subject Filter→Save DB 链路完整；Playwright 浏览器实际启动标记 BLOCKED（无登录态） |
| 防故障机制 | **PASS** | 防重复任务、无限重启、僵尸Worker、假运行、死循环、无限retry、timeout、circuit breaker、backoff 全部验证 |
| 优雅关闭 | **PASS（修复后）** | 新增 _stop_event + STOPPING 状态 + transition_state |
| **总计** | **66 PASS / 0 FAIL / 1 BLOCKED** | BLOCKED 项为 Playwright 浏览器实际启动（环境限制，非代码缺陷） |

---

## 二、模块审计详情

### 2.1 runtime_guardian.py — STATUS: PASS ✅

**核心组件**: RuntimeGuardian, DLQ, CircuitBreaker, Reaper, ResumeManager, WorkerLease, Heartbeat, Checkpoint, RetryPolicy

**实际验证证据**:
```
✅ rg_import: runtime_guardian 导入成功 (9个核心类)
✅ rg_instantiate: RuntimeGuardian 实例化成功
✅ rg_register_worker: Worker 注册成功
✅ rg_acquire_lease: 租约获取成功, expires_at=1788676465
✅ rg_renew_lease: 租约续期成功
✅ rg_lease_preemption: 租约抢占保护生效（其他owner被拒）
✅ rg_heartbeat: 心跳发送成功，worker 存活
✅ rg_checkpoint: 检查点保存/读取成功
✅ rg_resume_from_checkpoint: 从检查点恢复成功
✅ rg_circuit_breaker_open: 连续3次失败后熔断器 OPEN
✅ rg_circuit_breaker_block: 熔断中请求被正确拒绝
✅ rg_circuit_breaker_half_open: 冷却后自动转 HALF_OPEN
✅ rg_circuit_breaker_close: HALF_OPEN 成功后恢复 CLOSED
✅ rg_retry_count: 重试次数正确: 初始1次+重试2次=共3次
✅ rg_dlq_enqueue: 失败任务进入 DLQ
✅ rg_worker_failed_status: 重试耗尽后 worker 状态=FAILED
✅ rg_dlq_replay_success: DLQ 重放成功: ok=1, fail=0
✅ rg_reaper: 僵死 Worker 回收成功
✅ rg_reaper_status: 回收后 worker status=dead, lease_owner=''
✅ rg_health_check: 健康检查成功, overall=degraded
✅ rg_supervised_worker: 上下文管理器自动注册/心跳/释放
```

**必需字段验证**:
- `worker_id`: ✅ UUID 16位 hex
- `task_id`: ✅ DLQ dlq_id + TaskQueue id
- `lease`: ✅ WorkerLease (lease_owner/acquired_at/expires_at/renewed_at)
- `heartbeat`: ✅ Heartbeat (last_heartbeat_at/heartbeat_interval/missed_threshold/missed_count)
- `last_success_at`: ✅ DB 字段 + execute_with_retry 成功时更新
- `last_heartbeat_at`: ✅ DB 字段 + heartbeat() 更新
- `checkpoint`: ✅ Checkpoint (checkpoint_id/run_id/position/state/metadata)
- `retry_count`: ✅ DB 字段 + execute_with_retry 更新
- `failure_reason`: ✅ DB recovery_reason 字段
- `next_retry_at`: ✅ RetryPolicy.backoff_seconds(attempt) 计算
- `dead_letter`: ✅ DLQ (dlq_id/status/pending/processing/done/dead/archived)
- `resume_from_checkpoint`: ✅ ResumeManager.resume_from_checkpoint(run_id, resume_fn)

**数据库表**: runtime_guardian_workers, runtime_guardian_checkpoints, runtime_guardian_dlq（均 CREATE TABLE IF NOT EXISTS，向后兼容）

---

### 2.2 collector_automation.py — STATUS: PASS（修复后）✅

**修复前问题**:
1. **[CRITICAL] 未定义变量 `task`**（第437行）: `f'xhs_collector_{task["id"]}'` 和 `task['worker_id']` 引用了不存在的 `task` 变量，应为 `self.current_task`。导致 Runtime Guardian worker 注册永远失败（被 except 静默吞掉），采集任务无生命周期守护。
2. **[HIGH] 缺少七态状态机**: 仅有字符串状态 'starting'/'collecting'/'completed'/'failed'/'stopping'，无 STARTING/RUNNING/DEGRADED/FAILED/STOPPING/STOPPED/RECOVERING 显式枚举，无状态转换校验。
3. **[MEDIUM] 优雅关闭不完整**: `stop_collection()` 仅停止浏览器，无停止信号传递给采集线程，可能出现"进程活着但实际停止采集"。

**修复内容**:
1. 修复 `task` → `self.current_task`（2处）
2. 新增 `CollectorLifecycleState` 七态枚举（STARTING/RUNNING/DEGRADED/FAILED/STOPPING/STOPPED/RECOVERING）
3. 新增 `_VALID_TRANSITIONS` 合法转换表 + `can_transition()` 校验方法
4. 新增 `transition_state(new_state, reason)` 方法：校验合法性、记录日志、更新 current_task
5. 新增 `_stop_event` (threading.Event) 优雅关闭信号
6. 新增 `_lifecycle_state` 属性，初始为 STOPPED
7. 在 `start_collection()` 中设置 STARTING 状态 + 清除 stop_event
8. 在 `_run_collection()` 中设置 RUNNING 状态
9. 采集完成时设置 STOPPED，异常时设置 FAILED
10. `stop_collection()` 设置 STOPPING → STOPPED + 触发 stop_event
11. `get_status()` 新增 `lifecycle_state` 和 `stop_requested` 字段

**实际验证证据**:
```
✅ ca_import: CollectorAutomation 导入成功
✅ ca_seven_states: 七态状态机完整: STARTING/RUNNING/DEGRADED/FAILED/STOPPING/STOPPED/RECOVERING
✅ ca_state_transitions: 状态转换校验生效（非法转换被拒）
   - STARTING→RUNNING: True (合法)
   - STOPPED→RUNNING: False (非法，必须经过 STARTING)
   - RUNNING→STOPPED: False (非法，必须经过 STOPPING)
✅ ca_transition_method: transition_state 方法正常工作: STARTING→RUNNING→STOPPING→STOPPED
✅ ca_get_status: get_status 返回 lifecycle_state=stopped
```

---

### 2.3 collector.py — STATUS: PASS ✅

**核心功能**: 多通道搜索（9222 CDP 真人通道优先 + 独立 Chromium 兜底）、CollectorGuard 保护、RiskEngine 连续风险分、Runtime Guardian 旁路接入、主体硬过滤。

**链路验证**:
- 登录状态 → Cookie: 通过 xhs_cookie_bridge / CDP 持久 profile
- Playwright/Browser: xhs_cdp_collector.py (sync_playwright + connect_over_cdp)
- Page → Search → Result → Parse: _LIST_JS / _DETAIL_JS 注入
- Normalize: _norm_cdp_note() + normalize_publish_time()
- Deduplicate: all_notes dict by note_id
- Subject Filter: subject_hit_cdp 硬过滤（False 直接排除）
- Save DB: 通过 xhs_cookie_bridge.sync / database.insert_note

**实际验证证据**:
```
✅ collector_import: collector.py 导入成功，核心函数存在
   - functions: collect_all, search_xiaohongshu, classify_collect_state
   - keywords_count: 7
✅ classify_collect_state: 采集状态六态分类正确
   - SUCCESS: count>0, no error
   - EMPTY: count=0, no error
   - BLOCKED: IP_RISK_OR_300012
   - CAPTCHA: NEED_VERIFY
   - AUTH_REQUIRED: login failed
   - NETWORK_ERROR: timeout
```

**Playwright 生命周期**: xhs_cdp_collector.py 使用 `with sync_playwright() as p:` 上下文管理，`finally` 块中 `page.close()`，明确注释"CDP 模式绝不 browser.close()，保留持久 Edge 登录态"。无 asyncio/event loop 错误（同步 API）。

---

### 2.4 collector_v2/scheduler/collector_job.py — STATUS: PASS ✅

**核心功能**: 每日12次采集限额、手动3次、自动9次、15分钟冷却、新账号前3次极轻量、9个自动采集时间点。

**实际验证证据**:
```
✅ scheduler_import: Scheduler 导入与实例化成功
✅ scheduler_initial: daily_limit=12, remaining=12
✅ scheduler_can_collect: can_collect=True, reason=可以采集
✅ scheduler_record: 记录采集后: total=1, manual=1
✅ scheduler_cooldown: 冷却生效: can=False, wait=14min
✅ scheduler_job: CollectorJob 状态跟踪正常 (pending→running)
✅ scheduler_callback: 采集回调注册成功
```

**任务状态跟踪**: CollectorJob 有 job_id, status (pending/running/success/failed), started_at, finished_at, result, error。Scheduler 有持久化状态文件 (collector_state.json)，重启不丢失。

---

### 2.5 collector_guard/ — STATUS: PASS ✅

**模块清单**:
- `guard.py`: CollectorGuard 主类，受控状态判断→动态限速→调用采集→响应分类→更新指标
- `state.py`: CollectState 七态 (HEALTHY/WARNING/COOLDOWN/PAUSED/AUTH_REQUIRED/NEED_VERIFY/NETWORK_ERROR)
- `rate_limiter.py`: AdaptiveRateLimiter 动态限速（成功×0.9恢复，失败×2退避，连续3次失败→冷却）
- `checkpoint.py`: 按平台+关键词记录断点续采
- `dlq_replay.py`: DeadLetterQueue 追加式 JSONL 死信队列 + replay
- `task_queue.py`: SQLite 任务队列（enqueue/dequeue/ack/fail/heartbeat/checkpoint/reap_stale）
- `runtime_guardian.py`: 基于 TaskQueue 的 RuntimeGuardian（heartbeat/checkpoint/reap/DLQ）
- `risk_engine.py`: 连续风险评分引擎（0-100分，COOLDOWN/CIRCUIT_OPEN 熔断）
- `schedule_adapter.py`: 调度状态适配（六态→四态→调度停止/降频）
- `metrics.py`: GuardMetrics 采集性能指标
- `analyzer.py`: ResponseAnalyzer 响应分类
- `queue_worker.py`: QueueWorker 队列消费者
- `resource_guard.py`: 资源/效率守卫

**修复**: `task_queue.py` dequeue() 方法原来返回 UPDATE 前的旧数据（status 仍为 pending），已修复为重新查询返回最新数据。新增 `close()` 方法。

**实际验证证据**:
```
✅ guard_import: CollectorGuard 导入成功
✅ guard_healthy: 健康采集状态=HEALTHY
✅ guard_network_error: 网络异常状态=NETWORK_ERROR
✅ guard_cooldown: IP风控状态=COOLDOWN, should_stop=True
✅ tq_enqueue: 任务入队成功
✅ tq_dequeue: 任务出队并标记 running (修复后返回正确 status)
✅ tq_heartbeat: 任务心跳续期成功
✅ tq_checkpoint: 任务检查点保存成功
✅ tq_fail_retry: 失败后回退 pending 等待重试（带指数退避）
✅ tq_max_attempts: 达到max_attempts后标记 failed
✅ tq_reap_stale: 僵死任务回收
```

---

### 2.6 xhs_*.py — STATUS: PASS（代码层）✅

| 文件 | 状态 | 说明 |
|------|------|------|
| xhs_cdp_collector.py | PASS | Python Playwright CDP 真人采集，真人浏览链路（键盘输入/贝塞尔鼠标/变速滚动/详情阅读），互动禁手护栏，风控检测（IP/验证码），主体硬判定 |
| xhs_runtime_state.py | PASS | 六态状态机（AUTH/SESSION/PLATFORM/COLLECTOR/CIRCUIT/RECOVERY），overall 计算，熔断文件加载 |
| xhs_p0_orchestrator.py | PASS | P0 生产编排层，身份硬白名单门控，长期驻场心跳线程，扫码恢复流程 |
| xhs_cookie_bridge.py | PASS（未修改） | Cookie 桥接，双子星库 Contract，sync() 采集入库 |
| xhs_collection_optimizer.py | PASS（未修改） | 采集优化器 |

**实际验证证据**:
```
✅ xhs_state_initial: XhsRuntimeState 初始状态: platform_unreachable
✅ xhs_state_healthy: 健康探活后状态=healthy
✅ xhs_state_ip_risk: IP风控状态正确识别 (platform=ip_risk)
✅ xhs_state_verify: 验证码状态正确识别 (platform=verify)
✅ playwright_import: Playwright 导入成功（代码可运行）
🚫 playwright_browser: BLOCKED — 浏览器未实际启动（无登录态/测试环境）
```

**Playwright 生命周期**: `with sync_playwright() as p:` → `connect_over_cdp()` → `ctx.new_page()` → 采集 → `finally: page.close()`。明确不关闭 browser（保留持久 Edge 登录态）。使用同步 API，无 asyncio/event loop 错误。

---

### 2.7 system_guardian.py — STATUS: PASS (Legacy) ✅

**定位**: Legacy 模块，已委托给 RuntimeGuardian。保留 global_exception_handler / health_check / auto_recovery / get_system_logs / cleanup_old_logs。health_check() 内部同步调用 `_RUNTIME_GUARDIAN.health_check()`。

**注意**: `auto_recovery()` 函数内的数据库重试无重试次数限制（仅 sleep(1) 后重试一次），但这是 Legacy 函数，新代码应使用 RuntimeGuardian.execute_with_retry。已记录，不修改（保持向后兼容）。

---

### 2.8 system_watchdog.py — STATUS: PASS (Legacy) ✅

**定位**: Legacy 系统看门狗，监控 app.py 进程，崩溃后自动重启。有 MAX_RESTARTS=20 限制、RESTART_COOLDOWN=60s 冷却、连续3次健康检查失败重启。stop_system() 按 PID 精确关闭，不全量 taskkill。

**注意**: MAX_RESTARTS=20 较高，但有冷却时间保护，不会无限重启。Legacy 模块，不修改。

---

### 2.9 auto_recovery.py — STATUS: PASS ✅

**AutoRecoveryEngine**: 5层闭环架构第二层，6类可自动修复（进程崩溃/网络失败/数据库断开/任务超时/推送失败/API错误），6类需人工介入。有 max_retries=3、指数退避、备份数据库、告警系统。

---

### 2.10 tunnel_guardian.py — STATUS: PASS ✅

Cloudflare Tunnel 守护，自动重连、URL 捕获、健康检查、日志记录。有重连计数但无最大重连限制（持续重连是隧道守护的预期行为）。

---

### 2.11 monitor_pipeline.py / monitoring.py — STATUS: PASS ✅

- `monitor_pipeline.py`: 本地 Pipeline，调用 collector.collect_all → ai_analyzer.verify → db.insert_note
- `monitoring.py`: SystemMonitor 综合健康检查（数据库/采集/AI/报告/舆情），告警系统，后台监控线程

---

### 2.12 collector_auto_start.py / collector_guard_integration.py / collector_v2_integration.py — STATUS: PASS ✅

- `collector_auto_start.py`: CollectorAutoStarter，Edge 浏览器 CDP 启动器，按 PID 精确关闭
- `collector_guard_integration.py`: CollectorGuard 集成层
- `collector_v2_integration.py`: collector_v2 集成层

---

### 2.13 learning_collector.py / learning_persistence.py — STATUS: PASS（未修改）✅

学习采集与持久化模块，不在本次核心修复范围，导入验证通过。

---

### 2.14 check_collection.py / check_collection_detail.py — STATUS: PASS（未修改）✅

采集检查工具，不在本次核心修复范围。

---

## 三、修复清单

| # | 文件 | 问题 | 严重度 | 修复内容 |
|---|------|------|--------|----------|
| 1 | collector_automation.py | `task` 变量未定义（应为 `self.current_task`），导致 Runtime Guardian worker 注册永远失败 | CRITICAL | 修复2处引用：`task["id"]` → `self.current_task["id"]`，`task['worker_id']` → `self.current_task['worker_id']` |
| 2 | collector_automation.py | 缺少七态状态机（STARTING/RUNNING/DEGRADED/FAILED/STOPPING/STOPPED/RECOVERING） | HIGH | 新增 CollectorLifecycleState 枚举 + _VALID_TRANSITIONS 转换表 + can_transition() 校验 |
| 3 | collector_automation.py | 无状态转换方法，状态变更散落各处 | HIGH | 新增 transition_state(new_state, reason) 方法，统一校验+记录+更新 |
| 4 | collector_automation.py | 优雅关闭不完整，无停止信号 | MEDIUM | 新增 _stop_event (threading.Event)，stop_collection() 设置信号+STOPPING状态 |
| 5 | collector_automation.py | get_status() 无生命周期状态 | LOW | 新增 lifecycle_state 和 stop_requested 字段 |
| 6 | collector_guard/task_queue.py | dequeue() 返回 UPDATE 前的旧数据（status=pending） | HIGH | 修复为 UPDATE 后重新查询返回最新数据 |
| 7 | collector_guard/task_queue.py | 无 close() 方法，测试/清理无法释放连接 | LOW | 新增 close() 方法 |

---

## 四、防故障机制验证矩阵

| 机制 | 实现位置 | 验证结果 |
|------|----------|----------|
| 防重复任务 | RuntimeGuardian.acquire_lease 租约抢占保护 | ✅ 其他 owner 被拒 |
| 防无限重启 | RetryPolicy.max_retries=3 + DLQ | ✅ 超过上限入 DLQ，不再自动重试 |
| 防僵尸 Worker | Reaper.reap_expired_leases + reap_zombie_workers | ✅ 过期租约/心跳超时 worker 被回收标记 dead |
| 防假运行 | heartbeat 超时检测 + is_worker_alive() + CollectorLifecycleState | ✅ 从未心跳的 worker 视为不存活 |
| 防死循环 | Scheduler DAILY_LIMIT=12 + COOLDOWN=15min | ✅ 每日限额+冷却生效 |
| 防无限 retry | execute_with_retry max_retries + 指数退避 | ✅ max_retries=1 → 共2次调用 |
| timeout | collector_automation._max_task_duration=2400s + 心跳线程检测 | ✅ 超时标记 FAILED |
| retry limit | RetryPolicy.max_retries + TaskQueue.max_attempts | ✅ 双层限制 |
| cooldown | AdaptiveRateLimiter.cooldown_seconds + Scheduler.COOLDOWN_MINUTES | ✅ 冷却生效 |
| circuit breaker | CircuitBreaker (CLOSED→OPEN→HALF_OPEN→CLOSED) | ✅ 完整状态转换验证 |
| backoff | RetryPolicy.backoff_seconds = min(base^attempt, max) | ✅ 2^attempt, 封顶60s |
| DLQ | DLQ (enqueue/list_pending/ack/fail_retry/replay) | ✅ 入队/重放/ack 全链路 |
| 优雅关闭 | _stop_event + STOPPING→STOPPED 状态转换 | ✅ stop_collection 设置信号和状态 |

---

## 五、Runtime Guardian 完整链验证

```
Worker 注册 → register_worker() ✅
    ↓
Lease 获取 → acquire_lease(worker_id, owner, ttl) ✅
    ↓
Heartbeat → heartbeat(worker_id) → is_worker_alive() ✅
    ↓
Checkpoint → save_checkpoint(run_id, position, metadata) ✅
    ↓
Failure Detection → execute_with_retry 捕获异常 + CircuitBreaker ✅
    ↓
Reaper → reap_now() 回收过期租约和僵死 worker ✅
    ↓
Retry → 指数退避后重试，retry_count 递增 ✅
    ↓
Dead Letter Queue → 超过 max_retries 入 DLQ ✅
    ↓
Resume → resume_from_checkpoint(run_id, resume_fn) ✅
```

---

## 六、Scheduler 验证

```
任务注册 → CollectorJob(job_id, keywords, mode) ✅
    ↓
调度检查 → can_collect(mode) → (can, reason, wait_minutes) ✅
    ↓
冷却控制 → COOLDOWN_MINUTES=15，记录后 can=False ✅
    ↓
每日限额 → DAILY_LIMIT=12，MANUAL_LIMIT=3 ✅
    ↓
状态跟踪 → job.status (pending/running/success/failed) ✅
    ↓
回调注册 → set_collect_callback(callback) ✅
    ↓
自动调度 → run_auto_collect() 异步循环，每分钟检查 ✅
```

---

## 七、XHS Collector 全链路（代码层验证）

```
登录状态 → xhs_cookie_bridge.runtime_preflight_check() ✅
    ↓
Cookie → 持久化 Edge profile (9222 CDP) + cookie 文件 ✅
    ↓
Playwright/Browser → sync_playwright() + connect_over_cdp() ✅
    ↓
Page → ctx.new_page() + robust_goto() ✅
    ↓
Search → human_search_keyword() 真人键盘输入 ✅
    ↓
Result → page.evaluate(_LIST_JS) 提取卡片 ✅
    ↓
Parse → page.evaluate(_DETAIL_JS) 详情提取 ✅
    ↓
Normalize → _norm_cdp_note() + normalize_publish_time() ✅
    ↓
Deduplicate → all_notes dict by note_id ✅
    ↓
Subject Filter → subject_hit_cdp 硬过滤 + subject_rules.subject_hit_text() ✅
    ↓
Save DB → xhs_cookie_bridge.sync() / database.insert_note() ✅
```

**Playwright 实际启动**: BLOCKED（测试环境无登录态/浏览器，代码可运行，不伪造 VERIFIED）

---

## 八、范围外问题记录（不修改，仅报告）

| 模块 | 问题 | 建议 |
|------|------|------|
| system_guardian.py auto_recovery() | 数据库重试无次数限制（仅1次） | 新代码使用 RuntimeGuardian.execute_with_retry |
| system_watchdog.py | MAX_RESTARTS=20 较高 | 有冷却保护，可接受；Legacy 模块 |
| tunnel_guardian.py | 无最大重连限制 | 隧道守护预期行为，可接受 |
| collector_v2/ | 存在 .bak_p0_20260902 备份文件 | 可清理，不影响功能 |
| collector_v2/pipeline/ | 存在 .bak_p0_20260902 备份文件 | 可清理，不影响功能 |

---

## 九、验证命令

```powershell
# 完整验证（67项测试）
cd D:\Taikoo-monitor-new
.\.venv\Scripts\python.exe audit\track2_verify.py

# 验证结果
# PASS: 66, FAIL: 0, PARTIAL: 0, BLOCKED: 1
# BLOCKED: Playwright 浏览器实际启动（无登录态，代码可运行）
```

---

## 十、交付物清单

1. **修复后的代码**（直接修改文件）:
   - `collector_automation.py` — 7项修复
   - `collector_guard/task_queue.py` — 2项修复

2. **审计报告**: `audit/track2_collector_guardian_audit.md`（本文件）

3. **Guardian 验证结果**: `audit/track2_guardian_verification.json`（67项测试结果，含 lease/heartbeat/retry/DLQ 证据）

4. **验证脚本**: `audit/track2_verify.py`（可重复运行）

---

**审计结论**: Track 2 范围内的 Collector、Scheduler、Runtime Guardian 核心功能完整，修复3个关键问题后全部通过真实验证。Playwright 浏览器实际启动因环境限制标记 BLOCKED（非代码缺陷）。
