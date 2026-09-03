# SQLite 任务队列（Queue 层）· 2026-09-03

> 研究来源：**neotask**（neopen/neotask, 2026-03, Python 零依赖异步任务队列, Celery 轻量替代）。
> 能力提取：SQLite 后端 + 优先级 + 延时 + 指数退避重试，零第三方依赖。
> 服务基线 §10「动态熔断联动 Scheduler/Queue/Worker」的 Queue 层。

## 一、为什么

ZBC 采集已有同步调度（collect_all）+ DLQ 死信重放 + 调度动态间隔。补齐 Queue 层：
把批量任务（关键词采集、事件分析、报告生成）入队，Worker 按优先级/时间消费，
失败指数退避重试（对齐 baldur/neotask 范式），数据落盘 SQLite 可恢复（数据零丢失）。

## 二、能力（collector_guard/task_queue.py）

| 方法 | 说明 |
|---|---|
| enqueue(task_type, payload, priority, delay) | 入队（delay 为延时任务） |
| dequeue() | 原子取到期最高优先级任务并标记 running（防多 worker 重复） |
| ack(id) / fail(id, error) | 完成确认 / 失败退避重试（attempts 上限转 failed） |
| stats() / list_by_status() | 状态计数（Observatory 消费）/ 运维列表 |

- 优先级数字越小越先；失败指数退避 2^attempts 秒；max_attempts 可配（默认 3）。
- 纯 sqlite3，零依赖；默认 data/task_queue.db（gitignore 保护）。

## 三、验证

- 单测 4/4（enqueue/dequeue/ack、优先级排序、延时+退避重试+上限转 failed、stats）
- 调试实测：延时到期才可取、优先级正确、3 次失败转 failed
