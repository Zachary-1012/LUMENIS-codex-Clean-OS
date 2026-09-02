# GitHub 前沿研究：采集合规自适应 · AI 网关/路由 · Agent 可观测

> 研究日期：2026-09-03（本轮，持续链接 GitHub 研究学习链）
> 数据源：GitHub REST / 官方文档 / 一手 README，一手来源核实，不复制第三方代码
> 本轮落地：基于研究完成了 `collector_guard` 的 jitter + Retry-After 合规增强 + 修复 429 频控信号被吞的真实 bug（见文末落地记录）
> 关联总单：Zachary-OS-AI #11 / P1-A 采集合规 · P1-G AI 分层 · P0-D Observatory

---

## 主题一：采集合规自适应（对标 P1-A 采集稳定性 + 合规采集大模型诉求）

### CASE-1 Scrapling — 自适应 Web 采集框架
- **项目**：D4Vinci/Scrapling
- **License**：MIT 类（以仓库 LICENSE 为准）
- **解决什么问题**：单个请求到全量爬取的自适应采集；重点是 **AutoThrottle**（自适应延迟）与 Blocked Request Detection。
- **核心架构**：
  - Spider API（Scrapy 风格）+ 并发控制 + per-domain throttling + download delay
  - **AutoThrottle**：从网站响应速度自行调每域延迟；一旦开始被 block / rate-limit，**延迟加倍或遵循 Retry-After**；停止限速后逐渐提速
  - 会话多路（HTTP 会话 / stealthy headless 浏览器统一接口）
  - Checkpoint 持久化（Ctrl+C 优雅停机，重启续爬）
  - 流式产出 + 实时统计
- **对我们当前能力**：`collector_guard/rate_limiter.py` 已有动态限速（成功 ×0.9 收敛、失败 ×2 退避、冷却、持久化状态）。**缺口**：无 jitter 随机抖动、无 Retry-After 响应头感知。
- **领先点**：AutoThrottle 是"响应驱动"而非"猜测驱动"；多会话路由。
- **是否采用**：**部分吸收（本轮已落地）**——补 jitter + Retry-After；不引入其 stealth/bypass 能力（我们严守合规红线，不绕验证码/风控）。
- **吸收成本**：低（纯增量逻辑）。**风险**：低（不改采集语义）。
- **证据**：https://github.com/D4Vinci/Scrapling

### CASE-2 Polite Scraper 五习惯（link.sc 指南 + Firecrawl 防封指南）
- **核心结论（跨源一致）**：
  1. 每 host 限制并发（2 个并发对陌生站点是合理默认）
  2. **per-host rate-limit + jitter**：请求间隔随机化，避免"节拍器"（固定间隔是机器特征）
  3. 尊重 robots.txt / Crawl-delay
  4. **激进缓存**：最礼貌的请求是"不需要再发"的那个
  5. **背压**：429/503 = "慢下来"，遵循 `Retry-After` 头 + 指数退避 + 抖动；绝不紧循环重试
- **对我们当前能力**：我们有缓存、退避、冷却；缺 jitter 与 Retry-After 解析。
- **是否采用**：**采纳（本轮已落地 jitter + Retry-After）**。
- **证据**：https://link.sc/blog/how-to-build-a-polite-scraper ；https://www.firecrawl.dev/blog/web-scraping-mistakes-and-fixes

### CASE-3 GitHub API Pacer 模式（自适应限流器设计）
- **核心**：动态水位感知优于静态计数——解析 `X-RateLimit-Remaining` / `Retry-After` / `ETag`（304 缓存命中率可达 67%）；配额水位控制器（滑动窗口 + 指数加权衰减）+ 智能节拍器（动态 next-request-interval）+ 熔断决策器（连续 3 次 429 且 Retry-After>30 降级为只读缓存模式）。
- **对我们**：429 是"软信号"（WARNING），不是"硬熔断"——正是本轮修复的方向：429 必须被识别并传给限流器，而不是被空响应/健康分支吞掉。
- **是否采用**：**方法吸收**（动态水位 + 服务端指示优先）。
- **证据**：https://ask.csdn.net/questions/9487446 （方案性论述，非权威一手，仅作模式参考）

---

## 主题二：AI 网关 / 模型路由（对标 P1-G AI 分层 + MAX-EFFICIENCY）

### CASE-4 LiteLLM — 统一 LLM 网关（51.6k★）
- **项目**：BerriAI/litellm ｜ **License**：MIT（核心 OSS，Enterprise 付费）
- **解决什么**：100+ 提供商统一 OpenAI 接口；**Router**（retry/fallback/cooldown）；**虚拟密钥 per-key/team/user 预算**；guardrails；MCP 网关；8ms P95 @ 1k RPS。
- **对我们当前能力**：自研 `intelligence.py`（provider 映射 + 降级）+ `ai_budget.py`（Budget Manager）已覆盖其核心思想（统一接口、降级、预算）。
- **领先点**：虚拟密钥体系（Org→Team→User→Key）+ per-key 预算封顶 + cooldown 的 model fallback 链。
- **是否采用**：**不引入依赖**（自研已足够、避免重依赖）；**吸收思想**：fallback 链加 cooldown（对 unhealthy 模型冷却），per-key 预算封顶（我们已有 v4_workspace_keys + ai_budget）。
- **证据**：https://github.com/BerriAI/liteLLM ；https://openrouter.ai/blog/insights/llm-gateway/

### CASE-5 vLLM Semantic Router — 意图感知语义路由（5k★，Apache-2.0）
- **核心架构**：**Signal-Decision 插件链**——六类信号（Domain/Keyword/Embedding/Factual/Feedback/Preference）→ 决策引擎（AND/OR + priority）→ 路由决策 + 可插拔插件（semantic-cache/jailbreak/pii/hallucination/system_prompt）。
- **核心价值**：轻量分类器决定"该不该思考"——简单请求走 fast path，复杂请求走 CoT reasoning path。实测 ~10% 更高准确率、~50% 更低延迟、~50% 更少 token。
- **对我们当前能力**：我们的 AI Task Router（Rule→Cache→Local→Zachary→Zhipu→Doubao）目前是**静态优先级**，非语义路由。
- **领先点**：Signal-Decision 分离（观测信号与决策策略解耦）+ 意图驱动路由 + 语义缓存。
- **是否采用**：**思想吸收，暂不实现**——我们当前任务量不足以引入 embedding 分类器；但 **"Signal/Decision 分离" 设计模式**值得在 Observatory/ZELL 中借鉴（信号采集与决策策略解耦）。登记 BACKLOG T-P1G-01（未来当 AI 调用量大时可加意图路由层）。
- **证据**：https://github.com/vllm-project/semantic-router ；https://vllm.ai/blog/semantic-router

### CASE-6 Cost-first 网关观（awesome-ai-gateway / OpenRouter）
- **核心**：选模型 = 选"钱的放大倍数"。¥100 读 DeepSeek V4 Flash ≈ 2600 万中文字，GPT-5.5 Pro 仅约 5 万。LiteLLM=自托管默认，OpenRouter=托管默认。
- **对我们**：印证"智谱 glm-4.5-air 便宜大碗优先"策略正确；MAX-EFFICIENCY / LOW-Doubao-COST 模式的成本观正确。
- **证据**：https://github.com/RouteScope/awesome-ai-gateway

---

## 主题三：Agent 可观测 / Evidence / 学习闭环（对标 P0-D Observatory + ZELL）

### CASE-7 OTel GenAI Semantic Conventions（v1.41.1）
- **核心**：LLM client span（model/provider/tokens/finish_reason/latency）= **成本归因的单位**；agent span（reasoning unit）；events 承载 prompt/completion（挂 span 而非 attributes → 利于脱敏）；metrics 聚合（token/call/latency 按 model/operation 切片）。
- **对我们**：`ai_budget.jsonl` 已是"LLM span"思想的雏形；未来 structlog 统一字段应预留 `model/provider/tokens/latency/finish_reason`。
- **是否采用**：**思想吸收**（字段命名对齐），不引入 OTel 依赖（当前 print/GBK 日志够用，T-P1-4 structlog 时可对齐）。
- **证据**：https://www.xyzbytes.com/blog/agentops-opentelemetry-agent-observability ；https://github.com/o11y-dev/opentelemetry-skill

### CASE-8 TraceRoot — AI Agent 自愈观测层（YC S25）
- **项目**：traceroot-ai/traceroot（开源，BYOK）
- **核心**：Detectors（LLM-as-judge 扫 trace 找幻觉/工具失败/安全违规）+ Agentic Debugging（连源码+GitHub 历史定位失败行）+ **Datasets & Evals**（生产发现一键转 golden dataset，离线 eval 验证每个修复）。
- **对我们**：**这正是 Observatory + ZELL 的成熟对标**——"生产发现 → golden dataset → 离线 eval → 验证修复"循环。
- **是否采用**：**不引入依赖**；**吸收循环思想**（我们已有 zell_trace.jsonl + observatory_feed.py 骨架，未来补 golden dataset + 离线 eval）。
- **证据**：https://github.com/traceroot-ai/traceroot

### CASE-9 Tail-based Sampling（AgentOps/OTel 社区共识）
- **核心**：失败 trace 100% 采样、成功 1-10% 采样 → 控成本保信号。指标/计数全保真；span 结构保一段窗口；内容层仅失败/用户标记/少量成功。
- **对我们**：ai_budget 记账可借鉴"分层保留"：指标全保、审计结构保、内容抽样保。
- **证据**：https://www.xyzbytes.com/blog/agentops-opentelemetry-agent-observability

---

## 本轮落地记录（Research → Engineering → Evidence 闭环）

### T-P1A-04 jitter + Retry-After 合规增强（commit 见下）
- **问题**：① 采集器固定间隔 → "节拍器效应"（机器特征，polite scraper 五习惯明确要求随机化）；② 429 频控信号实际被吞——`analyzer.classify` 的 429 分支赋值 `_d` 后未 `return`，导致 429 状态下：空响应 → 误判 EMPTY(network_error)；有内容但无 `_RATE_PATTERNS` 匹配 → 误判 HEALTHY。**频控信号丢失会让采集器误以为成功继续猛发，反而加重风控。**
- **改动**（全部纯增强、可回滚、不改语义）：
  1. `collector_guard/analyzer.py`：`classify` 增 `retry_after=None` 参数；**修复 429 分支立即 `return`**（真实 bug）；429 返回回填 `retry_after`。
  2. `collector_guard/rate_limiter.py`：`wait_slot` 加 jitter（`random.uniform(0.7,1.3)`，构造参数 `jitter=True` 可关）；`on_failure(retry_after=None)` 冷却时长取 `max(退避, retry_after)`（服务端指示优先，非法值静默忽略）。
  3. `collector_guard/guard.py`：`_after_fail` 把 `cls.get('retry_after')` 传给 `on_failure`。
- **测试**：新增 `tests/test_guard_jitter_retryafter.py` 7 用例（jitter 范围/可关、retry_after 覆盖/更长者胜/非法忽略、analyzer 回填/缺省）。**全量回归 479+7 passed，零失败零 error。**
- **红线确认**：未弱化任何主体过滤/时间口径/熔断联动；jitter 与 Retry-After 均为"更礼貌更合规"，不改生产语义；jitter 默认开但可关。
- **Evidence**：测试文件 + 全量回归绿 + git commit。

### BACKLOG 新增
- **T-P1G-01**（观察）：未来 AI 调用量大时，参考 vLLM Semantic Router 引入意图路由层（Signal/Decision 分离 + fast/reasoning path），当前不实现。
- **T-P0D-03**（观察）：Observatory 未来补 golden dataset + 离线 eval（对标 TraceRoot），当前 zell_trace.jsonl + observatory_feed.py 骨架已够用。

---

## 方法沉淀
- **研究→落地闭环**：本轮研究（Scrapling/link.sc）→ 定位真实缺口（无 jitter、无 Retry-After）→ 补丁时**发现并修复 429 吞信号真实 bug** → 7 单测 + 全量回归 → Evidence。证明"研究驱动找缺口、缺口驱动修 bug"的链路有效。
- **合规边界**：只吸收"更礼貌"的能力（jitter、Retry-After、动态水位）；明确拒绝 stealth/bypass（Scrapling 的指纹伪造）——与 ZBIP 合规红线一致。
