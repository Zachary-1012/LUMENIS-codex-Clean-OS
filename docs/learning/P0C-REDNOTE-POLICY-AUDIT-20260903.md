# 审计：RedNote 三端策略 SoT 是否为生产采集器消费（2026-09-03）

## 结论（事实，非推测）
- `platform_adapters/rednote_policy.py`（三端 kind 策略 SoT：topic/舆情/event + 香港保活 + 真人频率）
  目前**只有它自身和单测 `tests/test_rednote_policy.py` 引用**（grep 证实，见下）。
- 生产采集器**没有消费 `can_run_kind()` / `effective_policy()`**：
  - `topic_campaign.py`（话题端）：走 `gate_should_run`（GAP-05 影子门控），但**不读 rednote_policy 三端 kind**。
  - `collector_v2/scheduler/collector_job.py`（基础采集调度）：只有每日次数/冷却，无 kind 维度。
  - `collector_v2/xhs/*`、`platform_adapters/xhs.py`（舆情/事件笔记通道）：无 rednote_policy 引用。
- 含义：**用户拍板的三端开关（话题开/舆情开/事件关）当前只停留在策略文档层，未真正控制生产采集行为**。
  用户后续指令"事件笔记推进 / 话题端舆情笔记端开放"在代码层无对应门控生效。

## 证据（grep 结果）
- `grep -rln "can_run_kind|effective_policy|rednote_policy|REDNOTE_KIND" -- *.py`
  → 仅 `platform_adapters/rednote_policy.py` 和 `tests/test_rednote_policy.py`
- `topic_campaign.py:783-784` 消费的是 `gate_should_run`（平台级调度门控），非 kind 门控。

## 建议接入点（最小、可回滚、默认不改变行为）
1. **kind 门控接入**：在采集入口（建议 `topic_campaign.run_campaign` 或统一调度器）调用
   `effective_policy().can_run_kind(kind)`，作为三端硬门控（topic→话题端、public_opinion→舆情端、event→事件端）。
   默认保持现状：kind_enabled 默认 topic=True/public_opinion=True/event=False，即接入后行为不变，
   只是让"事件笔记推进"由 env `REDNOTE_KIND_EVENT=true` 真正可控。
2. **策略审计日志**：在采集入口记录每次 kind 判定（policy_kind / decided / policy_version），
   写日志 + Evidence，不改采集结果。
3. **保活接入**：`REDNOTE_DAILY_LOGIN_KEEPALIVE` 当前默认 False，接入 topic_campaign 或独立保活线程。

## 风险
- 直接接入 kind 门控会改变生产采集行为（虽是"收紧"），须用户拍板后实施。
- 本审计只登记，不改任何生产代码。

## 状态
- 审计完成，登记 Gap；接入施工需用户确认。
