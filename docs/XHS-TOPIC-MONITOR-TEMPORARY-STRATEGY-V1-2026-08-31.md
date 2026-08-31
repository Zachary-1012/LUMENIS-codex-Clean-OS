# XHS Topic Monitor — Temporary Strategy V1

## 结论

当前国内小红书主账号状态为 `WARNING`，不是封禁。话题监测继续作为当前业务的临时保底能力，但不把当前采集方式定义为永久架构。

## 临时业务策略

```text
strategy = TEMPORARY
max_batches_per_day = 10
max_new_notes_per_batch = 10
dedup = true
```

每日最多 10 个监测批次；每批最多 10 个“新增”笔记进入后续分析。已存在的 note_id 直接去重，不重复进入分析链。

## 时间策略

不再在 `topic_campaign.py` 中把 09/11/13/15/17/19 等固定小时视为长期生产规则。任务触发应交由统一 Scheduler/Runtime；本策略只提供业务日配额与批次容量。

现有 `topic_campaign.py` 仍存在历史固定小时调度和独立每日 8 次配额，因此下一次接线时必须把这些旧值降级为兼容历史，不得继续作为新的唯一生产规则。

## 数据链

```text
Topic Task
  ↓
Runtime / Guard
  ↓
Source Adapter
  ↓
最多 10 个新 note
  ↓
Dedup
  ↓
现有 subject_filter
  ↓
现有 normalize / persist
  ↓
Risk / Event / Knowledge
```

不得修改既有主体口径红线。

## 数据源优先级

```text
1. official_api
2. licensed_provider
3. user_evidence
4. temporary_browser
```

当更优数据源可用时，只替换 Source Adapter，不修改 Core 上层分析链。

## 安全门禁

- 不自动点赞、评论、发布等改变账号状态的操作。
- 不实施 CAPTCHA/验证绕过、私有 API/签名逆向、指纹伪装、代理/IP 轮换等风控规避。
- 平台返回警告、验证、限制、阻断等状态时，由 Runtime/Guard/Scheduler 决定是否停止；临时策略不能覆盖平台状态。
- 10×10 是业务预算，不是平台风控保证。

## 退出条件

发现并通过验证的官方 API、合规 Provider 或稳定的用户 Evidence 数据源后，将 `temporary_browser` 降级为 fallback 或关闭。

## 与现有代码的适配

现有 Core 已经具备：
- `collector_v2` 的 normalize / deduplicate / persist / subject_filter 分层；
- `platform_adapters/scheduling` 的动态调度影子模式；
- XHS Runtime 六态状态机；
- XHS App Topic Adapter Feature Flag；
- App Evidence 能力。

本策略只补齐“临时业务预算”这一层，不重写现有采集核心。
