# DLQ + 恢复重放（Data Zero-Loss 增强）· 2026-09-03

> 研究来源：**baldurhq/baldur**（Apache-2.0，2026-06 发布的 Python 自愈可靠性层）。
> 提炼范式：单装饰器编排 breaker/budget/fallback/idempotency/DLQ；墙钟总预算约束全部重试；
> DLQ 只捕获"出站基础设施失败"用于恢复重放，业务拒绝永不入队。

## 一、为什么落地

ZBC 红线「数据零丢失」：采集关键词任务失败（风控/网络/登录失效）若只记日志，
恢复后无机制自动补采。DLQ 把失败任务**带上下文**捕获为追加式 JSONL，恢复期可重放，
任务永不丢失直到显式 ack/archive。

## 二、模块

| 文件 | 说明 |
|---|---|
| `collector_guard/dlq_replay.py` | `DeadLetterQueue`：enqueue/list_pending/ack/fail_retry/replay/stats |
| `tests/test_dlq_replay.py` | 7 测试（入队/业务拒绝不入队/ack 幂等/超阈值 dead/重放/持久化/空统计） |
| `scripts/dlq_ops.py` | 运维 CLI：stats/list/enqueue/replay/ack |
| 数据 | `data/collector_dlq.jsonl`（gitignore，本地保留） |

## 三、CLI

```bash
python scripts/dlq_ops.py stats                        # {pending, done, dead, total}
python scripts/dlq_ops.py list
python scripts/dlq_ops.py enqueue "广州太古汇" --error "security_page"
python scripts/dlq_ops.py replay <module:handler>     # handler(keyword, context)->成功ack/失败保留
python scripts/dlq_ops.py ack <task_id>
```

## 四、接入采集失败路径（最小 patch，待确认后接线）

在 `collector.py` 单关键词采集失败处（`gr.should_stop` / `_feed_risk_engine` 熔断分支）：

```python
# 失败分支（基础设施类失败）-> 入 DLQ
from collector_guard.dlq_replay import DeadLetterQueue
_dlq = DeadLetterQueue()
_dlq.enqueue(kw, error=error or gr.reason,
             context={"channel": "guard", "state": gr.state})
```

恢复期重放（如 `schedule_adapter` 判定 ramp_up / RECOVERING 半开后）：

```python
ok, fail = _dlq.replay(lambda kw, ctx: collect_keyword(kw))
```

注意：
- **业务拒绝不入队**：用户主动暂停、非法参数 → `is_business_rejection=True`。
- 失败重放达到 `max_attempts`（默认 5）标记 `dead` 保留审计，不再自动重放。
- 与 RiskEngine 六态 / ResourceGuard 联动：重放应在 `RECOVERING→RECOVERED`（半开放行）之后进行。

## 五、与现有熔断体系的关系（三层互补，不重复）

| 层 | 职责 | 数据丢失兜底 |
|---|---|---|
| CollectorGuard | 网络层守卫（should_stop/重试/回退） | — |
| RiskEngine | 连续风险分 + 六态熔断 | — |
| ResourceGuard + ScheduleAdapter | 资源/效率层四态 → 调度停止 | — |
| **DLQ + Replay** | **失败任务捕获 + 恢复重放** | **补上最后一环：数据零丢失** |

## 六、验证

- 单测 7/7 过（含持久化跨实例、业务拒绝、超阈值 dead）
- 全量回归 EXIT=0
- Evidence：`staging/baseline-evidence/`、git commit、OSAI learning-feed §13
