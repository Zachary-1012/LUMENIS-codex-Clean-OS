# GitHub 标杆学习 04 · 采集合规自适应 / AI 网关路由 / Agent 可观测 · 2026-09-03

> 方法：持续链接 GitHub 检索前沿/高星仓库，精读一手 README 与官方文档，提取可迁移范式，落地双子库并测试验证。
> 本轮主线：为 ZBC collector_guard 补"jitter 随机抖动 + Retry-After 服务端指示感知"，并修复一个真实频控信号被吞的 bug；研究 AI 网关/路由与 Agent 可观测标杆，沉淀进学习库。
> 完整研究文档：ZBC `docs/learning/GITHUB-FRONTIER-20260903-COLLECTOR-AIGATEWAY-OBSERVABILITY.md`；本文件为 OSAI learning-feed 同步副本（研究结果跨仓共享）。

## 一、采集合规自适应标杆（P1-A 采集稳定性 + 合规采集诉求）

### 1. Scrapling（D4Vinci/Scrapling，MIT 类）
- **核心范式 AutoThrottle**：延迟不靠猜——从网站响应速度自行调每域延迟；一旦被 block/rate-limit，**延迟加倍或遵循 Retry-After**；停止限速后逐渐提速（对域自适应）。
- 其他：多会话路由（HTTP/headless 统一接口）、Checkpoint 持久化、流式产出。
- **对照 ZBC**：`collector_guard/rate_limiter.py` 已有动态限速（成功 ×0.9 收敛、失败 ×2 退避、冷却、持久化）。**缺口：无 jitter 随机抖动、无 Retry-After 响应头感知。**

### 2. Polite Scraper 五习惯（link.sc / Firecrawl 跨源一致）
1. 每 host 限制并发（2 个对陌生站点是合理默认）；
2. **per-host rate-limit + jitter**：请求间隔随机化，避免"节拍器"（固定间隔是机器特征）；
3. 尊重 robots.txt / Crawl-delay；
4. **激进缓存**：最礼貌的请求是"不需要再发"的那个；
5. **背压**：429/503 = "慢下来"，遵循 `Retry-After` 头 + 指数退避 + 抖动，绝不紧循环重试。

### 3. GitHub API Pacer 模式（社区方案）
- 动态水位感知优于静态计数：解析 `X-RateLimit-Remaining` / `Retry-After` / `ETag`（304 缓存命中率可 67%）；配额水位控制器 + 智能节拍器 + 熔断决策器。
- **关键认知：429 是"软信号"（WARNING）而非"硬熔断"**——必须被识别并传给限流器，不能被空响应/健康分支吞掉。

### 落地（ZBC，本轮已实施 + 已测试）
- **真实 bug 修复**：`analyzer.classify` 的 429 分支赋值 `_d` 后未 `return` → 429 状态下空响应误判 EMPTY(network_error)、有内容但无 `_RATE_PATTERNS` 匹配误判 HEALTHY。**频控信号丢失会让采集器误以为成功继续猛发，反而加重风控。**
- **jitter**：`wait_slot` 等待在 `[0.7, 1.3] × interval` 随机化（构造参数 `jitter=True` 默认开、可关），规避节拍器效应。
- **Retry-After**：`on_failure(retry_after=None)` 冷却时长取 `max(退避, retry_after)`（服务端指示优先，非法值静默忽略）；`classify` 增 `retry_after` 参数，429 回填；guard `_after_fail` 透传。
- **测试**：新增 `tests/test_guard_jitter_retryafter.py` 7 用例；全量回归 479+7 passed 零失败零 error。
- **红线确认**：未弱化任何主体过滤/时间口径/熔断联动；jitter 与 Retry-After 均为"更礼貌更合规"；明确拒绝 Scrapling 的 stealth/bypass（指纹伪造）——守合规红线。

## 二、AI 网关 / 模型路由标杆（P1-G AI 分层 + MAX-EFFICIENCY / LOW-Doubao-COST）

### 1. LiteLLM（BerriAI/litellm，51.6k★，MIT）
- 100+ 提供商统一 OpenAI 接口；**Router**（retry/fallback/**cooldown**——对 unhealthy 模型冷却）；**虚拟密钥 per-key/team/user 预算**；guardrails；MCP 网关；8ms P95 @ 1k RPS。
- **对照 ZBC**：自研 `intelligence.py`（provider 映射 + 降级）+ `ai_budget.py`（Budget Manager）已覆盖核心思想。
- **结论**：不引入依赖；吸收"fallback 链加 cooldown + per-key 预算封顶"思想（我们已有 v4_workspace_keys + ai_budget）。

### 2. vLLM Semantic Router（vllm-project/semantic-router，5k★，Apache-2.0）
- **Signal-Decision 插件链**：六类信号（Domain/Keyword/Embedding/Factual/Feedback/Preference）→ 决策引擎（AND/OR + priority）→ 路由决策 + 可插拔插件（semantic-cache/jailbreak/pii/hallucination/system_prompt）。
- **核心价值**：轻量分类器决定"该不该思考"——简单请求 fast path、复杂请求 CoT reasoning path。实测 ~10% 高准确率、~50% 低延迟、~50% 少 token。
- **结论**：思想吸收（Signal/Decision 分离设计值得在 Observatory/ZELL 借鉴），暂不实现（任务量不足以引入 embedding 分类器）。登记 BACKLOG T-P1G-01。

### 3. Cost-first 网关观（RouteScope/awesome-ai-gateway + OpenRouter）
- 选模型 = 选"钱的放大倍数"：¥100 读 DeepSeek V4 Flash ≈ 2600 万中文字 vs GPT-5.5 Pro 仅约 5 万。
- **印证**：智谱 glm-4.5-air 便宜大碗优先策略正确；MAX-EFFICIENCY / LOW-Doubao-COST 成本观正确。

## 三、Agent 可观测 / Evidence / 学习闭环标杆（P0-D Observatory + ZELL）

### 1. OTel GenAI Semantic Conventions（v1.41.1）
- LLM client span（model/provider/tokens/finish_reason/latency）= **成本归因的单位**；agent span（reasoning unit）；events 承载 prompt/completion（挂 span 而非 attributes → 利于脱敏）；metrics 聚合（按 model/operation 切片）。
- **结论**：ai_budget.jsonl 已是 LLM span 思想雏形；未来 structlog 统一字段应预留 model/provider/tokens/latency/finish_reason。

### 2. TraceRoot（traceroot-ai/traceroot，YC S25，开源 BYOK）
- Detectors（LLM-as-judge 扫 trace 找幻觉/工具失败/安全违规）+ Agentic Debugging（连源码+GitHub 历史定位失败行）+ **Datasets & Evals**（生产发现一键转 golden dataset，离线 eval 验证每个修复）。
- **结论**：**Observatory + ZELL 的成熟对标**——"生产发现 → golden dataset → 离线 eval → 验证修复"循环。登记 BACKLOG T-P0D-03。

### 3. Tail-based Sampling（AgentOps/OTel 社区共识）
- 失败 trace 100% 采样、成功 1-10% 采样 → 控成本保信号；指标/计数全保真、span 结构保窗口、内容层抽样保。
- **结论**：ai_budget 记账可借鉴分层保留（指标全保 / 审计结构保 / 内容抽样保）。

## 四、其他速览（备选范式）
| 仓库 | 星 | 可迁移点 |
|---|---|---|
| apify/crawlee-python | 9479 | RequestQueue / 自动限速 / 去重（此前已登记） |
| laurentS/slowapi | 2051 | 对 API 限流，保护自身服务（对外 API 时） |
| BerriAI/litellm | 51.6k | Router cooldown + per-key budget（思想吸收） |
| vllm-project/semantic-router | 5k | Signal/Decision 分离 + 意图路由（思想吸收） |
| traceroot-ai/traceroot | YC25 | 生产发现→golden dataset→离线 eval（思想吸收） |

## 五、本轮闭环记录（Research → Engineering → Evidence）
1. 研究（Scrapling / link.sc / Firecrawl / LiteLLM / vLLM-SR / TraceRoot / OTel）→ 定位真实缺口（无 jitter、无 Retry-After）；
2. 补丁时发现并修复 429 吞信号真实 bug；
3. 新增 7 单测 + 全量回归 479+7 passed；
4. 研究文档落地 ZBC `docs/learning/` + LEARNING-REGISTRY 条目 + OSAI learning-feed 同步。
5. **合规边界**：只吸收"更礼貌"能力（jitter、Retry-After、动态水位）；明确拒绝 stealth/bypass，与 ZBIP 合规红线一致。
