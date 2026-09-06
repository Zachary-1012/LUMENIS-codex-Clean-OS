# ZBC 统一生命周期契约 V1.0

> 工单：ZBC-LIFECYCLE-CONTRACT-V1
> 日期：2026-09-07
> 状态：ACTIVE
> 权威实现：`runtime_guardian.py`（根目录，51KB+）
> 对齐：AGENTS.md §3 / §13 / §17

---

## 1. 目标

建立 ZBC 全系统统一的长运行模块生命周期管理契约，确保：
- 所有长运行模块有统一的状态机、注册、心跳、检查点、重试、DLQ 机制
- 禁止无限自动重启（Retry Limit + Cooldown + CircuitBreaker + DLQ）
- 死进程可被收割（Reaper），历史记录可被归档（Archive）
- 系统生命线不绑定任何单一组件

---

## 2. 生命周期状态机（10态）

```
CREATED → STARTING → RUNNING → PAUSED → RESUMING → STOPPING → STOPPED → DEAD → ARCHIVED
```

| 状态 | 含义 | 可转换到 |
|------|------|----------|
| CREATED | 已注册，未启动 | STARTING, STOPPING |
| STARTING | 启动中，获取资源/租约 | RUNNING, STOPPING, DEAD |
| RUNNING | 正常运行中，定期心跳 | PAUSED, STOPPING, DEAD |
| PAUSED | 已暂停，保留租约和上下文 | RESUMING, STOPPING, DEAD |
| RESUMING | 恢复中，从 checkpoint 恢复 | RUNNING, PAUSED, STOPPING, DEAD |
| STOPPING | 停止中，释放资源 | STOPPED, DEAD |
| STOPPED | 已正常停止，可重启或归档 | STARTING, ARCHIVED |
| DEAD | 异常死亡（心跳超时/崩溃），可恢复或归档 | ARCHIVED, STARTING |
| ARCHIVED | 已归档，终态，从活跃列表移除 | （无） |

### 与历史 WorkerStatus 的兼容映射

| WorkerStatus（旧） | LifecycleState（新） |
|---------------------|----------------------|
| idle | created |
| running | running |
| recovering | resuming |
| failed | stopping |
| stopped | stopped |
| dead | dead |

---

## 3. 必须实现的生命周期方法

所有长运行模块必须实现以下方法（通过 `LifecycleMixin` 或直接调用 `RuntimeGuardian`）：

| 方法 | 状态转换 | 说明 |
|------|----------|------|
| `create()` | → CREATED | 注册 worker，分配 worker_id |
| `start()` | CREATED→STARTING→RUNNING | 获取租约，启动心跳，标记 started_at |
| `heartbeat()` | （RUNNING 保持） | 定期发送心跳（默认 10s），续期租约 |
| `checkpoint()` | （不改变状态） | 保存执行位置到 checkpoints 表 |
| `pause()` | RUNNING→PAUSED | 暂停执行，保留上下文 |
| `resume()` | PAUSED→RESUMING→RUNNING | 从 checkpoint 恢复执行 |
| `stop()` | →STOPPING→STOPPED | 优雅停止，释放租约，标记 ended_at |
| `cleanup()` | →STOPPED | 释放租约，清理内存引用 |
| `archive()` | STOPPED/DEAD→ARCHIVED | 归档历史记录，从活跃列表移除 |

### RuntimeGuardian 权威接口

```python
from runtime_guardian import get_guardian, LifecycleState

g = get_guardian("my_module")
wid = g.lifecycle_create("my_worker", domain_id="cth", product_id="CTH")
g.lifecycle_start(wid)
g.heartbeat(wid)
g.save_checkpoint(run_id="run_001", worker_id=wid, position="page=3")
g.lifecycle_pause(wid)
g.lifecycle_resume(wid)
g.lifecycle_stop(wid)
g.lifecycle_archive(wid)
```

---

## 4. 必须字段（runtime_guardian_workers 表）

| 字段 | 类型 | 说明 |
|------|------|------|
| worker_id | TEXT UNIQUE | 全局唯一 worker 标识 |
| worker_name | TEXT | 可读名称（如 xhs_collector_20260907_031653） |
| domain_id | TEXT | 双域核心：cth / zbmp / system |
| product_id | TEXT | 双域核心：CTH / ZBMP / SYSTEM |
| status | TEXT | 生命周期状态（10态） |
| lease_owner | TEXT | 租约持有者（pid-xxxx） |
| run_id | TEXT | 当前运行 ID |
| checkpoint_id | TEXT | 最新检查点 ID |
| last_success_at | TEXT | 最后成功时间 |
| last_heartbeat_at | TEXT | 最后心跳时间 |
| last_checkpoint_at | TEXT | 最后检查点时间 |
| failure_count | INTEGER | 累计失败次数 |
| retry_count | INTEGER | 当前重试次数 |
| recovery_reason | TEXT | 状态变更原因 |
| metadata | TEXT(JSON) | 扩展字段（started_at, ended_at, lease_expires_at 等） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 最后更新时间 |

---

## 5. 生命周期覆盖范围（10类模块）

| # | 模块 | 文件 | 接入状态 | 接入方式 |
|---|------|------|----------|----------|
| 1 | 采集 Worker | collector.py / collector_automation.py / collector_guard/ | ✅ 已接入 | collector_automation 完整接入（注册/租约/心跳线程/checkpoint/清理） |
| 2 | 调度器 | scheduler（内置 APScheduler） | ✅ 旁路 | 通过 collector_automation 触发采集时自动接入 |
| 3 | AI 任务 | ai_task_engine.py | ✅ LifecycleMixin | 任务执行时注册 worker + 心跳 |
| 4 | AI Browser 会话 | ai_browser_runtime.py | ✅ LifecycleMixin | 会话创建时注册，关闭时 cleanup |
| 5 | 报告生成 | report_engine.py / report_api.py | ✅ LifecycleMixin | 报告任务注册 + 心跳 |
| 6 | 数据导入 | historical_data_importer.py | ✅ LifecycleMixin | 导入任务注册 + checkpoint |
| 7 | 内容生成 | ad_intelligence/ / podcast/ / topic_campaign.py | ✅ LifecycleMixin | 内容任务注册 |
| 8 | Skill 执行 | skill_execution_chain.py | ✅ LifecycleMixin | Skill 链执行注册 |
| 9 | Agent 运行 | agent_runtime_adapter.py | ✅ LifecycleMixin | Agent 会话注册 |
| 10 | 定时任务 | cron/scheduled tasks | ✅ 旁路 | 通过触发的模块间接接入 |

---

## 6. 每个模块必须有的生命周期能力

### 6.1 Lease（租约）
- worker 必须持有租约才能运行
- 租约 TTL 默认 60 秒，采集 worker 120 秒
- 租约过期自动释放，Reaper 回收
- 同一 worker 同一时刻只有一个持有者

### 6.2 Heartbeat（心跳）
- 运行中 worker 必须定期心跳（默认 10 秒）
- 连续错过 3 次心跳（30s）标记为可疑
- 超过 60 秒无心跳由 Reaper 标记 DEAD
- 心跳同时续期租约

### 6.3 Checkpoint（检查点）
- 长任务定期保存检查点（位置、状态、元数据）
- 存储到 `runtime_guardian_checkpoints` 表
- 支持从最新检查点恢复执行
- 任务完成时保存 completed 检查点

### 6.4 Reaper（收割死进程）
- 后台线程每 30 秒执行一次回收周期
- 回收过期租约
- 回收心跳超时的僵死 worker（标记 DEAD）
- app.py 启动时自动启动 Reaper

### 6.5 Retry（重试）
- 默认最大重试 3 次
- 指数退避：1s → 2s → 4s → 8s（封顶 60s）
- 重试次数记录到 retry_count
- 失败次数累计到 failure_count

### 6.6 CircuitBreaker（熔断器）
- 连续失败 5 次触发熔断（OPEN）
- 熔断后冷却 300 秒
- 冷却后转 HALF_OPEN，放行一次试探
- 试探成功 → CLOSED，失败 → 重新 OPEN

### 6.7 DLQ（死信队列）
- 超过重试上限的任务进入 `runtime_guardian_dlq` 表
- 不自动重启，必须人工确认后重放
- DLQ 状态：pending → processing → done / dead / archived
- 支持按域隔离查询

### 6.8 Resume（恢复）
- 从最新 checkpoint 恢复执行
- `ResumeManager.resume_from_checkpoint(run_id, resume_fn)`
- 恢复失败不自动重试，由调用方决定

---

## 7. 禁止无限自动重启（硬红线）

```
任务失败
  ↓
第1次重试（等待1s）
  ↓
第2次重试（等待2s）
  ↓
第3次重试（等待4s）
  ↓
超过 max_retries=3 → 进入 DLQ
  ↓
人工确认 → 重放（最多 max_attempts 次）
  ↓
重放失败 → DLQ 标记 dead（不再自动处理）
```

- **Retry Limit**：默认 3 次，可按模块配置
- **Cooldown**：指数退避 2^n 秒，封顶 60s
- **Circuit Breaker**：连续 5 次失败熔断 300s
- **DLQ**：超过重试上限进入死信队列，不自动重启
- **人工恢复**：DLQ 任务必须人工确认后才能重新执行

---

## 8. 数据库表

### 8.1 runtime_guardian_workers（worker 注册表）
- 所有长运行模块的 worker 注册于此
- 状态机 10 态
- 双域核心：domain_id / product_id

### 8.2 runtime_guardian_checkpoints（检查点表）
- 长任务的执行位置快照
- 关联 run_id / worker_id
- 支持 resume

### 8.3 runtime_guardian_dlq（死信队列表）
- 超过重试上限的失败任务
- 人工重放机制
- 双域核心：domain_id / product_id

### 8.4 zbc_lifecycle_tracking（生命周期追踪表）
- 已有，记录模块级生命周期事件
- 与 runtime_guardian_workers 互补

---

## 9. UI 展示

### System/Runtime 页面
- 路由：`/system/runtime`（页面）+ `/api/runtime/workers`（API）
- 展示所有 worker 的生命周期状态
- 按状态分组：running / paused / stopped / dead / archived
- 显示：worker_name、status、last_heartbeat_at、failure_count、domain_id
- 支持手动 archive dead workers
- 显示 DLQ 统计和熔断器状态

### API
```
GET /api/runtime/workers          # 列出所有 worker（排除 archived）
GET /api/runtime/workers?status=running  # 按状态过滤
GET /api/runtime/summary          # 生命周期汇总
POST /api/runtime/workers/<id>/archive  # 归档 worker
POST /api/runtime/archive-dead    # 批量归档 dead worker（>24h）
```

---

## 10. 测试

### tests/test_lifecycle_contract.py
- 状态转换合法性测试（合法/非法转换）
- 完整生命周期流程测试（create→start→pause→resume→stop→archive）
- 心跳超时测试
- 检查点保存与恢复测试
- 重试 + 指数退避测试
- DLQ 入队与重放测试
- 熔断器状态转换测试
- Reaper 回收测试
- 双域隔离测试
- archive_dead_workers 批量归档测试

---

## 11. 与其他 Shard 协调

| Shard | 协调内容 |
|-------|----------|
| I Shard | 全量功能审计收敛，runtime_guardian 相关模块由 K Shard 处理 |
| J Shard | AI Provider 切换，AI 任务生命周期与 fallback 链协调 |
| H Shard | 内容制作激活，内容生成模块生命周期协调 |
| G Shard | Adaptive UI，UI 展示接入 Adaptive 组件 |

---

## 12. 硬约束（不可违反）

1. 不修改 SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit()
2. 不破坏数据库（125表），新增表用 CREATE TABLE IF NOT EXISTS
3. 不破坏 AI Core（ai_task_engine.py）/ AI Browser（ai_browser_runtime.py）的调用链
4. 不破坏采集主链路（小红书采集）
5. runtime_guardian.py（根目录）为权威实现，collector_guard/ 和 OSAI 的小版本合并或适配，不删除权威版本
6. 禁止无限自动重启，必须有 Retry Limit + DLQ
7. 不自动 merge main
8. 代码必须自研
9. 微信跳过

---

## 13. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| V1.0 | 2026-09-07 | 初始版本：10态状态机 + 生命周期方法 + 10类模块覆盖 + Retry/DLQ/CircuitBreaker |
