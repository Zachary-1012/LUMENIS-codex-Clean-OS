# P0-C 采集链合规+稳定性深度审查（glm-5.3）

> 日期：2026-09-03 | 模型：glm-5.3 | 消耗：per_call 1次
> 目的：审查小红书采集链时间模型/主体过滤/熔断联动/合规边界/稳定性

---

让我仔细分析提供的源码片段，按照五个维度进行审查。

**1. 时间模型**

从 `_norm_cdp_note` 看：
- `publish_date` 从 `detail_publish_time`/`publish_time`/`publish_datetime` 提取，正则匹配 YYYY-MM-DD，只保留日期（丢失时分秒）。
- 输出字段：`publish_date`（仅日期字符串），`source_channel`，但没有看到 `captured_at` 字段被设置。片段中 `_norm_cdp_note` 返回的 dict 没有 `captured_at`。这是"采集时间"在采集侧未被显式落字段的证据（可能在 insert_note 层补，但源码未给出）。
- 发布时间被截断为日期（正则 `(\d{4}-\d{2}-\d{2})`），丢失时分秒精度 —— 对舆情监测的时间排序有影响，但不算混淆 publish/captured。
- 没有看到 event_time / updated_at / snapshot_time 字段。
- 关键问题：`_norm_cdp_note` 输出无 `captured_at`；如果下游 insert 用 `publish_date` 兜底为时间戳，就会混淆。源码未给出 insert_note，所以只能说"采集侧未见 captured_at 字段，依赖下游补齐，存在混淆风险；且发布时间降精度为日期"。

结论：时间模型部分分离——publish_date 独立提取自页面发布时间字段（正确来源），但未见 captured_at/event/updated/snapshot 字段，无法证明完整五时间分离；发布时间被截为日期粒度是降精度问题。

**2. 主体过滤**

红线：广州太古汇严格排除其他城市同名（如北京太古汇、上海太古汇、成都太古汇等）。

从 `_norm_cdp_note` 看：返回字段中有 `subject_hit_cdp': rec.get('subject_hit')`——即 CDP 详情采集阶段已有 subject_hit 判定，并透传。但是：
- 关键问题：`collect_all` 中 `all_notes` 累积 `gr.notes`（GuardResult.notes 来自 `_extract(raw)`，即 search_xiaohongshu 返回的 notes 列表）。片段中未见对入库前逐条走 subject_hit 过滤的代码——`collect_all` 片段在 `if gr.should_stop:` 后被截断，后续处理未知。但 `_norm_cdp_note` 只是把 `subject_hit` 透传为 `subject_hit_cdp`，没有看到过滤行为（如 `if not rec.get('subject_hit'): continue`）。
- 也就是说：证据显示 subject_hit 被记录/透传，但未见 collector 层在入库前基于它做硬过滤的代码路径。无法确认是否存在漏过滤路径；至少在给出的片段中，`_norm_cdp_note` 对 `subject_hit=False/None` 的记录不做排除，仅透传字段。
- 需要指出：无字段级过滤动作（无 `filter`/`continue`/条件丢弃），过滤责任疑似留给下游 insert 层；存在弱化风险。且 `_norm_cdp_note` 标题兜底逻辑（用正文首行当标题）可能引入城市名错位——若正文含"北京太古汇"字样用于标题，但 subject 判定基于原字段，标题兜底不影响 subject_hit 本身，但可能影响后续文本类过滤（如果下游用标题判断城市）。这算次要风险。

结论：片段显示 subject_hit 被透传（subject_hit_cdp），但未见 collector 侧入库前硬过滤代码；若依赖下游过滤则存在漏过滤风险（需指出证据边界）。

**3. 熔断/冷却联动**

链路：RiskEngine（连续分）→ classify_collect_state 六态 → CollectorGuard（离散七态）→ AdaptiveRateLimiter。

证据：
- `_feed_risk_engine`：把 guard_state/error/count 归一化六态，映射风险因子，record_failure/record_success，`snap['should_stop_request']` 为 True 时停止后续关键词并记录 results——串联点1。
- `collect_all` 中 `guard.run(...)` 包裹 search_xiaohongshu，`gr.should_stop` 时记录 error/guard_state——串联点2。
- guard.run 中：`if self.limiter.state in CollectState.STOP_REQUEST: return GuardResult(...)` 不发请求——串联点3（guard→limiter）。
- `_after_fail`: AUTH/VERIFY/COOLDOWN → `force_pause(st)`；其他 → `on_failure()`。
- RiskEngine 状态持久化 `data/collector_guard/xhs_risk_state.json`。

问题点：
a) **重复/嵌套问题**：`_feed_risk_engine` 里 `risk.record_failure(factor)` 后又 `risk.snapshot()`，`record_*` 返回 `(score, band, st)` 未被使用，然后又 snapshot——轻微冗余但不算错。
b) **恢复不立即全速**：`AdaptiveRateLimiter.on_success` 中 `self.interval = max(self.min_interval, self.interval * 0.9)` —— 每次成功收敛 10%，且 COOLDOWN/WARNING/PAUSED → HEALTHY。但注意：`wait_slot` 只在 `state == CollectState.COOLDOWN` 时取 `max(remaining_cooldown, interval)`，其他状态直接 `interval`。冷却到期后，`can_run` 只看 `cooldown_until`；但 `wait_slot` 里 COOLDOWN 状态等到冷却结束后 sleep 的 wait 是 `max(remaining_cooldown(), interval)`——到期后 remaining=0，wait=interval（可能是已翻倍的 interval，因为 on_failure 时 interval 翻倍了）。而状态从 COOLDOWN → HEALTHY 只能靠 on_success 触发。所以冷却到期后第一个请求：state 仍是 COOLDOWN？看 `can_run`：`time.time() >= self.cooldown_until` → True，guard.run 的检查是 `if self.limiter.state in CollectState.STOP_REQUEST`——STOP_REQUEST 包含哪些状态？未给出定义，推测含 COOLDOWN/PAUSED/CIRCUIT_OPEN/AUTH_REQUIRED/NEED_VERIFY。若 state 仍是 COOLDOWN（到期但没人调 on_success 重置 state），guard.run 会直接返回受控状态、不发请求——**冷却到期后可能死锁在 COOLDOWN 状态，无法自动恢复**！这是严重问题：`on_success` 是唯一把 COOLDOWN→HEALTHY 的路径（还有 force_pause 重设），但 guard.run 在 STOP_REQUEST 状态时直接 return，不调用 collect_fn，也就永远不会触发 on_success。除非有外部定时器到期重置 state。看 rate_limiter 源码：没有任何到期自动把 state 从 COOLDOWN 变回 HEALTHY 的代码（`can_run` 只返回 bool，不改 state；`wait_slot` 也不改 state）。所以：冷却到期后 state 仍为 COOLDOWN → guard.run 永远拦截 → 死锁。**除非** STOP_REQUEST 不含 COOLDOWN。但 `classify_collect_state` 里 `gs in ('COOLDOWN','PAUSED','CIRCUIT_OPEN') → 'BLOCKED'`，且 xhs_cookie_bridge 的 get_circuit_state 有 resume_ts 到期判断。guard.run 的拦截条件是 `self.limiter.state in CollectState.STOP_REQUEST`。CollectState 定义未给出。如果 STOP_REQUEST = {PAUSED, AUTH_REQUIRED, NEED_VERIFY}（不含 COOLDOWN），则冷却到期后 state=COOLDOWN 不在 STOP_REQUEST，会走 wait_slot，wait = max(remaining_cooldown=0, interval) = interval，且第一个请求成功后 on_success 把 COOLDOWN→HEALTHY。这个设计里 `wait_slot` 对 COOLDOWN 状态的处理（等到冷却结束+interval）暗示 COOLDOWN 不在 STOP_REQUEST（否则 wait_slot 的 COOLDOWN 分支永不执行）。嗯，这是矛盾：如果 COOLDOWN 在 STOP_REQUEST，guard.run 直接返回，wait_slot 的 COOLDOWN 分支死代码；如果不在，则 wait_slot 处理冷却等待。从代码自洽性看，wait_slot 有 COOLDOWN 分支说明设计上 COOLDOWN 不在 STOP_REQUEST。但 `classify_collect_state` 把 guard_state=COOLDOWN 归为 BLOCKED。无法定论 STOP_REQUEST 组成——需要在结论中标注"证据边界"。

安全恢复角度：冷却到期后 wait=interval（on_failure 已翻倍过，interval 至少 base*2，最大 base*16），不会全速；且 on_success 每次只收敛 10% 到 min。这满足"不立即全速"。但注意 `on_failure` 中 `self.interval = min(self.max_interval, max(self.interval * 2, self.base_interval * 2 ** 0))` —— `self.base_interval * 2**0 = base_interval`，即 interval 至少翻倍或回到 base，OK。

还有：冷却到期"恢复第一枪"是否有探测（half-open 探测）？没有 half-open 设计，直接按 interval 等待后发真实请求。可接受但非最优。

c) **风险因子表 `_RISK_FACTOR_BY_STATE` 未在片段中给出内容**——注释说 BLOCKED/CAPTCHA/AUTH 硬信号、NETWORK 累加，SUCCESS/EMPTY 不加分。但代码 `factor = _RISK_FACTOR_BY_STATE.get(state)`，`if factor: record_failure else record_success`——注意：**EMPTY 走 record_success**，即空结果被视为成功让风险分衰减。注释说"EMPTY 与真实无内容一致，交给 guard 节流"，但 EMPTY 让风险分衰减可能在被软性限流（返回空但实为风控）时误判恢复。这是设计权衡，可提一句：EMPTY 无法区分"真无内容"与"软风控空响应"，让风险分衰减可能提前解除熔断。不过 classify 已把 guard 硬状态优先归类，软空响应确实难判。可提示。

d) `_feed_risk_engine` 在熔断时 append 到 results 的记录 count 用的是当次 count——OK，真实记录。

e) RiskEngine 关闭时（`_XHS_RISK = False`）返回 None，`_feed_risk_engine` 恒 False——Feature Flag 行为一致，OK。但注意 `_get_xhs_risk_engine` 返回 `_XHS_RISK or None`，当 `_XHS_RISK=False` 时返回 None——OK。

f) **RiskEngine 与 CollectorGuard 是两条独立状态**：RiskEngine 的 should_stop_request 停止"后续关键词请求"，但它不写入 guard.limiter 的 force_pause——即 RiskEngine 判熔断后只停本轮循环，不把 guard 置于 PAUSED。下一轮 collect_all 开始时，guard.limiter 可能已恢复 HEALTHY，RiskEngine 自己的 state 持久化在 state_file。所以 RiskEngine 熔断不联动 limiter——联动是单向的（collect 结果→两者），RiskEngine 熔断不反馈给 limiter。这是一个联动缺口：RiskEngine 熔断只影响当次 collect_all 循环内，跨轮次依赖 RiskEngine 自身持久化状态（应该_stop_request 会在新一轮首个关键词后再次触发，因为 record 后 score 仍高）。其实每轮首个关键词会 record_failure/success，若 score 仍高则 stop——但如果首轮熔断后，第二轮首个关键词恰好 SUCCESS，record_success 衰减，可能 score 降到阈值下继续请求。这算合理设计还是缺口？RiskEngine 分数随成功衰减是设计意图。但"RiskEngine 熔断未写入 limiter.force_pause"意味着 guard 不知道 RiskEngine 已熔断，guard 的 wait_slot 间隔不会拉长。可以提：建议 RiskEngine 熔断时调用 guard.limiter.force_pause 联动。

g) 源码片段大量重复粘贴（脱敏拼接痕迹），不影响审查。

**4. 合规边界