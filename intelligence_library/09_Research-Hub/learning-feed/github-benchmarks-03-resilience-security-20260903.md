# GitHub 标杆学习 03 · 韧性熔断与 Agent 执行安全 · 2026-09-03

> 方法：经 github-remote 检索高星/前沿仓库，精读核心源码，提取可迁移范式，落地双子库并测试验证。
> 本轮主线：为 ZBC RiskEngine 补"熔断后自动恢复"闭环，并对照 Agent 代码执行安全标杆校准 dev_exec_guard。

## 一、熔断器标杆：pybreaker（danielfm/pybreaker，692★）

### 1. 核心范式：三态状态机 CLOSED → OPEN → HALF_OPEN → CLOSED
| 状态 | 行为 | 迁移条件 |
|---|---|---|
| CLOSED（闭合/正常） | 正常执行，失败计数累加 | 连续失败达 `fail_max` → OPEN |
| OPEN（断开/熔断） | **立即失败、不执行真实操作**（fail-fast） | 经过 `reset_timeout` 冷却 → HALF_OPEN |
| HALF_OPEN（半开/试探） | **只放行一次探测请求** | 成功达 `success_threshold` → CLOSED；任一失败 → 回 OPEN 并刷新冷却 |

### 2. 关键设计要点（源码级）
- **opened_at 时间戳**：进入 OPEN 时记录，`before_call` 用 `now < opened_at + reset_timeout` 判断是否仍在冷却；
- **success_threshold**：半开期需连续成功 N 次才完全闭合（默认 1，可调高更稳健），避免一次偶发成功就全量恢复；
- **excluded_exceptions**：业务异常（如"真实无内容"）不计入系统故障，区分 EMPTY 与 ERROR——与我们 collector 的 EMPTY 不加分口径一致；
- **Listener 观察者**：before_call/failure/success/state_change 钩子，天然可审计；
- **线程安全**：RLock 保护状态迁移；存储层可换内存/Redis（多实例共享熔断态）。

### 3. 对照发现的 ZBC 真实缺陷（已修复）
改造前 RiskEngine：连续风险分 + 硬信号一次熔断，但**熔断后 `_last_band` 不随时间解除**；
collector 熔断即 break、`_XHS_RISK` 单例跨 collect_all 复用 → **一旦熔断永久停采，只能重启进程**。
→ 落地：新增 opened_at / reset_timeout(默认300s) / HALF_OPEN 档 / half_open_success_threshold，
实现"熔断→冷却→半开试探→成功闭合/失败重熔"闭环，snapshot 增加 half_open 与 cooldown_remaining_s 可观测字段。
新增 5 项测试，全量回归 356 全过。

## 二、Agent 执行安全标杆：memkeeper-warden（teflon07）、secure-py-eval-harness

### 1. memkeeper-warden：能力代理 + 执行门（Rust）
- **Deny-by-default / fail-closed**：无策略默认拒绝，决策路径无网络、无 LLM（确定性）；
- **能力分类（typed capability）**：`fs:read <path>` / `fs:write <path>` / `exec <program>` / `net <host>`，路径 glob 防目录穿越与后缀伪造；
- **声明式策略 + 全量审计**：TSV 策略按调用方授权，**每次 allow/deny 追加审计日志**；
- **Dry-run 先行**：默认只记录不拦截，从真实流量建 allowlist，再切 enforce——低风险上线路径；
- **诚实的威胁模型边界**：明确"policy gate 不是 sandbox"；`bash -c '<内联>'` / `python3 -c` 只门控外层程序、不解析内部意图（已知限制），词法路径匹配不解析符号链接。

### 2. secure-py-eval-harness / fips-agents/code-sandbox
- AST 护栏（静态禁危险调用）+ Landlock/seccomp（内核级）+ NetworkPolicy 多层纵深；
- 状态 checkpoint/rollback、循环检测（cycle detection）、双层护栏、动态遥测。

### 3. 对 ZBC dev_exec_guard 的校准（现状已对齐的 + 后续可进化）
- 已对齐：生产环境默认拒绝（403）、dev 显式 opt-in、危险构造拦截、鉴权隔离（P1-9 已修）；
- **本轮已落地（第一项）**：每次 allow/deny 落**本地 JSONL 审计日志** `data/audit/dev_exec_audit.jsonl`
  （decision/outcome/reason/http_status/endpoint + 代码长度与 SHA256 前12位指纹，**不存代码全文防泄密**，
  data/* 已 gitignore 不进远端；审计旁路失败绝不阻塞主流程），两端点补 endpoint 溯源，+6 测试；
- **可进化（P2，剩余待办）**：
  1. ~~每次 allow/deny 落审计日志~~ ✅ 已完成；
  2. 提供 **dry-run 模式**（只记录不执行）用于先观察；
  3. 补一份**威胁模型说明文档**，明确"AST/关键字门控不等于沙箱"，`python -c` 内联代码的可见性边界；
  4. 内联代码执行考虑 AST 解析而非纯关键字匹配（对齐 secure-py-eval-harness）。

## 三、其他速览（备选范式）
| 仓库 | 星 | 可迁移点 |
|---|---|---|
| fabfuel/circuitbreaker | 523 | 装饰器式熔断，最轻量，适合给单函数加保护 |
| bagowix/interlock | 73 | **滑动窗口**计数（替代固定累加）、慢调用检测、sync+async 一体 |
| AhsanSheraz/pyresilience | 73 | retry/cb/timeout/fallback/bulkhead/ratelimit/cache 单装饰器（零依赖），Python 版 Resilience4j |
| sno-ai/llmix | 132 | LLM 调用层：缓存/重试/熔断/**key 轮换**/singleflight——对智谱单 key 场景的调用层有参考价值 |

## 四、本轮落地映射
| 学到的范式 | 落地位置 | 状态 |
|---|---|---|
| pybreaker HALF_OPEN 恢复闭环 | ZBC `collector_guard/risk_engine.py` + 5 测试 | ✅ 已落地并回归 |
| fail-closed / 能力分类 | dev_exec_guard 现状对照 | ✅ 已对齐 |
| 每次 allow/deny 可审计 | ZBC `dev_exec_core.py` JSONL 审计 + 两端点 endpoint + 6 测试 | ✅ 已落地并回归 |
| dry-run / 威胁模型文档 / AST 护栏 | dev_exec_guard 进化 | P2 待办 |
| 滑动窗口 / LLM key 轮换 | RiskEngine、智谱调用层 | P2 备选研究 |

*归属：Zachary-OS-AI learning-feed | 类型：外部标杆→内部落地 | 关联：P1-4、P1-9*

## §baldur 研究（2026-09-03 晚）— DLQ+恢复重放落地
- 标杆: baldurhq/baldur (Apache-2.0, 2026-06, Python 自愈可靠性层): 单装饰器编排 breaker+wall-clock budget+fallback+idempotency+DLQ; 零配置内存后端起步, 多worker才加Redis; 内置web console实时breaker状态+运行时kill switch; Prometheus/OTel metrics。
- 关键范式: 1) 墙钟总预算约束所有重试(SDK自身最坏=timeout×(retries+1)); 2) 不重试SDK已重试的,外层补breaker/budget/fallback/dedup; 3) DLQ只捕获出站基础设施失败用于恢复重放,业务拒绝永不入队。
- ZBC落地: collector_guard/dlq_replay.py 追加式JSONL死信队列(enqueue/list/ack/fail_retry/replay/stats, max_attempts超限dead保留审计) + tests 7过 + scripts/dlq_ops.py CLI + docs/DLQ-REPLAY.md(含collector最小接线指引)。补齐数据零丢失最后一环(熔断三层+DLQ重放四层互补)。
- 可复用清单: 后续可学 baldur 的 web console(kill switch/dry-run) 与 Prometheus metrics 到 ZBC 运维面。

## §baldur System-Control 研究（2026-09-03）— 运维控制面落地
- 范式: 1) Kill Switch=全局on/off, 翻转必带reason可问责, 持久化跨重启(重启仍disabled不静默重开自动化), 读失败fail-safe为enabled/live(不误禁用); 2) Dry-run=观察/演练, 评估全开动作全抑制记录would-have, 离开需confirm(不意外退出观察); 3) 每次翻转审计who/why/when。
- ZBC落地: collector_guard/runtime_switch.py(KillSwitch+Dry-run, 持久化+审计+fail-safe) + tests 8过 + 接线E2E验证4过(disabled请求0/dry_run请求0但决策记录完整/恢复) + scripts/runtime_switch_ops.py CLI + docs/RUNTIME-SWITCH.md。与用户暂停/RiskEngine/ResourceGuard四层互补(运维总闸为最高层)。
- 可复用: baldur 的 fleet-wide 共享状态(Redis后端, 多服务器一翻全翻)。

## §omnigent 研究（2026-09-03）— 多智能体编排 + Agent YAML 蓝本
- 标杆: omnigent-ai/omnigent (Apache-2.0, 2026-06, 9.6k★) meta-harness: 统一编排 Claude Code/Codex/Cursor/Hermes/自研agent; 会话跨设备(终端/浏览器/手机/桌面); 云沙箱host(Modal/E2B/K8s等)。
- 关键范式:
  1) Agent YAML 声明式: name/prompt/executor.harness/tools(function本地函数|mcp服务器|agent子代理); agent定义即配置, 子代理可inherit工具, "agents can build agents"。
  2) Policies三层治理: server-wide(admin)/per-agent(dev)/per-session(用户), 动作级allow/block/ask(暂停询问); 内置spend cap/tool-call cap/cost budget(硬上限+软告警阈值)。
  3) Polly范式: 多agent编排, 编码子代理并行git worktree, 跨厂商reviewer(diff由不同厂商agent评审)。
- OSAI应用: 可作为OSAI未来"工程agent编排"配置蓝本(Agent YAML规范已沉淀 baseline/AGENT-YAML-SPEC.md); Policies三层治理理念映射ZBC现有 AI Budget(ai_budget.py配额) + RuntimeSwitch(运维总闸) + ResourceGuard(资源层)。
- 未采用: 不引入omnigent运行时(OSAI无agent runtime, 且需Python3.12+多依赖); 只提取声明式配置+策略治理范式。

## §haystack 研究（2026-09-03）— 已记录未落地
- deepset-ai/haystack 26k★ context-engineered LLM编排: 模块化pipeline+显式retrieval/routing/memory控制。与ZBC当前轻量架构不匹配, 暂不引入(避免依赖膨胀), 保留为RAG类需求再评估。

## §OpenDQV 研究（2026-09-03 晚）— 数据质量门落地
- 标杆: OpenDQV/OpenDQV (MIT, 2026-03, contract-driven data quality validation) write-time enforcement: 写入前校验坏记录422拒绝(per-field errors), 不存payload; Contract YAML(name/version/owner/rules) + severity(error阻止/warning标记放行) + condition条件规则 + 批内unique; 三层治理=写入时(OpenDQV)/目录治理/管道监控(GX/Soda/dbt互补); MCP一等(agent发现契约/验证/解释失败, 无幻觉合规)。
- 哲学: "A 422 at the point of write is cheaper than a data incident three weeks later." "Trust is easier to build than to repair."
- ZBC落地: data_quality_gate.py 契约驱动写入前校验(not_empty/regex/min-max/range/length/allowed_values/date_format + severity + condition + 批内unique) + config/data-contracts/note|event|topic_snapshot 内置契约(对齐五时间模型) + tests 8过 + docs/DATA-QUALITY-GATE.md。三层数据治理=schema_registry(结构)/DataQualityGate(语义)/下游。
- 可复用: OpenDQV 规则集(checksum/compare/required_if/geospatial等)可按需扩展; MCP接入模式(agent可声明式发现ZBC数据契约)。

### §OpenDQV 落地补充（质量审计实测）
- scripts/quality_audit.py 存量审计（只读）：notes 300/300=100% 通过、events 300/300=100% 通过。
- 关键教训：首次 0% 通过是**契约误报**（DB publish_date 纯日期 vs 契约要求时分秒；events 无 event_type 列）——date_format 支持多格式 fallback + 建存量兼容契约 event_db.yaml 后 100%。
- 三层数据治理落地完成：schema_registry(结构) + DataQualityGate(语义/写入标准严格) + quality_audit(存量基线只读)。写入门接线段待 collector.py 空闲后接入。

### §17 Prompt-Cache 成本可观测（研究：llm-api-pricing / Rapid-MLX）
- 洞察：agent 实测 token mix 约 95.6% 为缓存输入，缓存读价比列表价低 ~6.5x——固定 system 前缀最大化缓存命中是 AI 降本第一手段（直接服务"智谱主力/配额最优"）。
- 落地 ZBC：ai_budget.record 扩展 --in/--out/--cache + summary.cache（hit_rate/in_tokens/out_tokens/cacheable_input_share），向后兼容。docs/AI-COST-CACHE.md。测试 2/2。ZBC de4a4ca。
- 下一步（评估后执行）：确认智谱 glm-4.7 缓存支持 → system prompt 收敛为固定前缀模板。

### §18 智谱缓存确认 + 采集调度动态间隔 + BERTopic c-TF-IDF（2026-09-03 三连落地）
- **智谱缓存确认**（官方 docs.bigmodel.cn/cn/guide/capabilities/cache）：隐式自动缓存，命中 token 按优惠价，响应返回 usage.prompt_tokens_details.cached_tokens；缓存优惠计费仅适用标准 API（资源包不适用），但机制仍加速响应。→ ZBC 落地 config/prompts/ 版本化固定前缀(4角色) + prompt_registry + 稳定性测试（改前缀必 bump version）。ZBC 1d6b09a。
- **采集调度动态间隔接线**（服务基线§9/§10动态熔断联动）：schedule_sleep_seconds = base×interval_multiplier（NORMAL1x/ADAPTIVE1.8x/COOLDOWN4x/FROZEN5x），collect_all 关键词间按 RiskEngine 六态动态 sleep，降频不停止恢复自升。ZBC fbd46ab。
- **BERTopic → 轻量 c-TF-IDF**（7814★）：提取可解释主题词算法（类内词频×逆类频率），纯标准库 2-gram+弱边过滤，零重依赖，服务 Topic 自动打标/事件摘要。演示正确识别"防晒/敏感/晒霜/spf"。ZBC 1d6b09a。

### §19 全量回归拦截 + schema 漂移根因修复（重要教训）
- 全量回归稳定复现 1 失败：test_report_deprecation[s/...generate]，报 sqlite3.OperationalError: no such column: negative_confirmed。
- 归因：代码引用 COALESCE(negative_confirmed,0)<>2 但 CREATE TABLE notes DDL 缺该列——存量生产 DB 经历史迁移 ALTER 添加，全新/临时 DB 建表缺列即报错。真实 schema 漂移（非本轮改动）。
- 根因修复：CREATE TABLE notes 补 'negative_confirmed INTEGER DEFAULT 0'（与 COALESCE 默认 0 语义一致，零行为改变），对齐"单一权威 DB Schema"。全量回归恢复 EXIT=0。
- 教训：全新建库必须与代码引用列完全对齐；回归要跑"全新 DB"路径才能暴露此类漂移。

### §20 四连落地：写入门软门 + AI Gateway + Topic事件 + SQLite任务队列（2026-09-03）
- **写入门质量软门**：insert_note 内部自动 enrich 标记（未传 status 时 ok/warning/error+score），标记不丢弃失败不阻断（数据零丢失），零侵入多采集入口。ZBC 8496ea3。
- **AI Gateway**（scripts/ai_gateway.py）：固定 system 前缀（prompt_registry）+ budget 统一记录（in/out token 估算 + cache 可观测预留）。智谱隐式缓存命中前提落地到真实调用。
- **Topic 聚类→事件摘要**（scripts/topic_cluster.py）：events 按 risk_level 分组 c-TF-IDF 主题词 + 每事件 topic_label，只读不改 DB；真实 DB 识别"太古汇/投诉"主题。ZBC 8496ea3。
- **SQLite 任务队列**（能力提取自 neotask 零依赖）：collector_guard/task_queue.py，enqueue/dequeue/ack/fail+优先级+延时+指数退避重试，补齐基线§10 Queue 层；调试实测延时到期才取/优先级正确/3次失败转failed。ZBC e741e22。

### §21 采集反检测研究评估 + Topic标签接入事件API（2026-09-03）
- 研究 invisible_playwright(1962★,2026-05 免费antidetect stealth) / undetected-chromedriver(12821★)：核心理念为 stealth 指纹(headless Firefox)。
- **评估结论：ZBC 现状更优，不引依赖**——ZBC 采集用「真人持久 Edge + CDP 通道」（真实浏览器指纹+人类 session，优于 stealth 库模拟），且 _ensure_cdp_online 自动拉起 headless=False。避免引重依赖（基线§8 AI/依赖最小化）。
- Topic 标签接入：/api/event-graph/events 每事件返回 topic_label(c-TF-IDF 只读内存增强)，前端/报告可消费。E2E 7 API PASS。ZBC 提交。

### §22 多路研究：outputguard 落地 + openlit/事件驱动/增量评估（2026-09-03 加大力度）
- **outputguard（52★, MIT, 2026-05）落地**：LLM 结构化输出 15 修复策略 + 校验 + 重试提示 + guarded_generate；288 OpenRouter 模型实测 100% 可用（22% 需修复，最高频 strip_fences/extract_json/fix_truncated）。→ ZBC 落地 scripts/json_repair.py（8 策略纯标准库）+ ai_gateway.chat_json（固定前缀+修复+失败重试+budget）。测试 8/8。ZBC ff4efe0。
- **openlit（2737★）评估**：OpenTelemetry-native LLM 观测，但依赖 ClickHouse/OTLP 全套——ZBC 已有 ai_budget JSONL 轻量观测 + observatory-feed，评估不引（避免重依赖，契合基线§8）。
- **事件驱动 pipeline / 增量计算**：多库低质量（0★ 小项目），评估无高价值，不引入。
- 原则再确认：研究加大力度=多路并行+精读提取+轻量落地；依赖最小化、能力提取为范式。

### §23 品牌/营销行业标杆研究 + 报告消费topic + QueueWorker（2026-09-03）
- **omnihawk**（免费开源自托管 AI 社媒监听/品牌监测平台）评估：与 ZBC 定位（自托管舆情监测）概念同源，验证「自托管 AI 社媒监听」范式成立；0★ 无架构价值，记录范式不引依赖。Social-Media-Dashboard(90★) 为 SaaS 全栈，评估不引。
- **报告体系消费 topic_label + 结构化数据**：report_engine.event_analysis 每项加 topic(c-TF-IDF 内存增强)，日报/周报/月报/年报直接消费——报告「Decision Information First」补主题维度。
- **TaskQueue 异步消费采集（Worker 层）**：collector_guard/queue_worker.py 通用消费循环（dequeue->processor->ack/fail，退避由 task_queue 内置）+ 采集 processor 工厂；生产按 collector 类型注册。测试 5/5。
- 触类旁通：报告=结构化数据消费端、队列=生产者消费者模式、主题聚类=文本挖掘——底层都是「数据管线分层 + 契约对接」，跨领域复用。
- ZBC 8077fdf。

### §24 品牌/营销/4A 知识库 + 报告模板消费topic + 调度入队接线（2026-09-03 加大力度）
- **新增 brand-marketing-knowledge-20260903.md**：品牌/产品/整合营销/4A 判断中枢——底层逻辑6条（品牌=管理认知、定位=经营战略、情绪共谋、资源内置、洞察先行、案例映射底层）+ 2026 最新案例剖析7例（蒙牛海信营销搭子/宜家Assemble the World/BCP SOS POS/汤臣杰逊全域陪跑等）+ 决策框架（做品牌/产品/展览三类询问路径）+ 可复用口诀。未来用户问品牌/产品/展览可一针见血作答，并可联动 ZBC 舆情数据量化认知变化。
- **报告 docx/xlsx 模板消费 topic 落版**：xlsx 事件分析加「主题标签」列、docx 加「主题标签」段，真实验证导出含值。
- **采集调度入队接线**：schedule_adapter.enqueue_next_round 打通 Scheduler->Queue->Worker 异步生产链路（与同步采集互补，默认不改）。队列三组测试 15/15。
- 触类旁通：营销=认知工程，舆情系统=认知仪表盘——两者天然闭环（定位框架×真实数据=可落地建议）。
- ZBC 提交后推。

### §25 营销知识库第二期 + 品牌诊断工具落地（2026-09-03）
- **brand-marketing-knowledge-02**：戛纳2026创意方法论10条(精确真实感/前2秒情绪契约/UGC操作系统化/速度变量/双轨velocity-quality/品牌勇气/用户行为变产品等) + 新品上市全生命周期(测种爆续/三板斧/冷启动测品/节奏管理) + 展览体验营销打法(Levi's丹宁典藏/英雄钢笔快闪/茅台剧本杀等7例+四件套规律)。
- **scripts/brand_insight.py 落地**：营销知识库框架×ZBC真实数据→品牌诊断简报(声量/情绪/主题词/风险+启发式建议)。兑现「用户做品牌/产品/展览给一针见血建议」目标的第一步工具化。真实DB验证(太古汇负面10%健康)。tests 3过。
- 触类旁通：知识库是「判断框架」、brand_insight 是「数据化执行」——框架×数据=可落地建议，正是咨询行业底层逻辑。

### §26 跨品类知识库 + 可比稿方案引擎（2026-09-03 维度拓宽）
- **brand-marketing-knowledge-03**：跨品类打法对照(餐饮/快消/美妆/汽车/文旅/城市/B2B/科技/金融, 决策特性→策略差异) + 10条可迁移规律(概念事件化/谐音双关/选址即表达/情绪日常化/UGC派样/票根经济/B2B先权威再销售/定位说最合适/KOC五步/AIGC参与式) + 可比稿提案10段结构 + 比稿加分技巧。
- **scripts/campaign_plan.py 落地**：可比稿方案引擎——输入品牌/品类/目标/预算/人群→10段完整提案骨架+2个创意方向+触点+风险。真能比稿的方案骨架(不是空泛建议)。10品类打法库。tests 4过。
- 能力升级：从「给建议」到「给可直接比稿的方案」；从单品类到跨品类。未来问品牌/产品/展览/任何品类→方案引擎×知识库×brand_insight数据佐证。

### §27 全球4A对标 + 数据驱动原创创意引擎（2026-09-03）
- **brand-marketing-knowledge-04**：全球4A顶级案例(Ogilvy Uva Uva Bombon实时解锁/Vaseline Originals共创产品/Oreo Cows Titanium/Coca-Cola AFK文化洞察/AXA产品即创意/Nike Rip The Script) + 全球方法论(实时文化连接/创作者即商业伙伴/文化敏捷=2026终极作弊码/病毒三要素/world-building/谜团营销/IRL) + 数据驱动创意判断链。
- **scripts/idea_generator.py 落地**：数据信号(主题词/情绪/风险/圈层/热点)×创意机制(6种)→生成原创口号+概念+圈层符号+时效+传播设计。从「融合」升级为「用真实数据生成新midea&idea」。负面自动切危机共情机制。测试7/7(含brand_insight噪音过滤)。
- 能力里程碑：问品牌/产品/展览/任何品类 → idea_generator(创意) × campaign_plan(比稿骨架) × brand_insight(数据佐证) 三件套。

### §28 高奢/重奢/小众调性特别篇 + 方案撰写脉络（2026-09-03）
- **brand-marketing-knowledge-05**：高奢底层逻辑(Hermes计算型稀缺/Chanel符号iconography/Goyard反互联网克制/Brunello信任小圈层/Ffern四季限量/Aesop小众审美定义者/观夏闻献反流量) + quiet luxury安静奢华 + 涨价=筛选客群 + 调性坐标(mass/premium/luxury) + 方案8章脉络(借鉴ZBC数据层/能力层/接口层/展示层/质量层/证据层)。
- **pitch_parser.py 落地**：方案需求文本/文件(txt/md/json/csv)→要素提取+16品类全球标杆对标+Gap+创意+8章方案脉络。**app.py 加 /api/creative/ideas + /api/creative/pitch-analyze(支持文件上传multipart)**。
- **idea_generator 升级**：新增高奢小众圈层(限量/稀缺/手作/仪式感/私密) + 调性坐标，luxury自动切「克制不追热点」。测试8/8 + API冒烟三路200。
- 能力里程碑：**用户给方案需求/文件 → pitch_parser 拆解对标 → idea_generator 原创创意 → campaign_plan 扩成比稿方案**。全链路可走。

### §29 真实案例拆解 + 视频脚本模板 + 多平台社媒运营（2026-09-03）
- **brand-marketing-knowledge-06**：8份真实方案精读(太古汇25年年度review/索尼Jennie大屏打卡/NIO蔚来播客/日谈公园/播客先声/uth又识/阳狮SOP)。核心提炼：爆款公式(热门事件×高级感视觉×品牌巧植入×福利驱动)、5栏目体系(Show/Bonus/Trending/Crush/Treasure Time)、KFS投放模型(达人1:3:6+KOC最优+聚光24h互动>20+搜索品专)、人群分层、播客三大入局方式+日谈5种合作模式、打卡=城市社交货币、创意六阶段SOP、阳狮广州爆款案例。
- **video_script.py 落地**：TVC/概念片/小红书/抖音 4类视频脚本生成器(每镜头场景/景别/时长/画面/音频/字幕/参考+标题候选+投放建议)。
- **social_ops.py 落地**：小红书/抖音/IG/FB/X/公众号 6平台运营传播策略生成器。测试5/5。
- 能力里程碑：方案需求 → pitch_parser拆解 → idea_generator创意 → video_script视频脚本 × social_ops平台运营 → campaign_plan比稿方案，全链路工具齐备。

### §30 2026 全球营销最新趋势研究（2026-09-03）
- **brand-marketing-knowledge-07**：全网+外网研究(AdTimes/Kantar/WARC/Cannes2026/Balistro/VML)。核心：创作者内容要证ROI(61%加码但看ROI而非点赞)、媒介选择即创意(Nike关社媒转OOH/Apple只做印刷/Amazon自广告)、文化影响力8大案例(Dove创作者接管3.4亿曝光/Patagonia供应链碳数据/Liquid Death听证会/Wendy's实时比分)、Cannes2026 GP打法(SOS POS数据即公益/Claude最小问题讲宏大命题/Heineken错失即话题)、社媒10趋势(创意占表现差异56%,AI-UGC/Lo-Fi/创始人叙事/互动广告/玩梗)、Agentic AI营销(Microsoft×Publicis ROI2X/Braze超个性化/Hyundai虚拟人20x/fifty-five AI焦点小组)。
- **落地**：BENCHMARKS 16品类全量更新(含2026新案例)、PLATFORMS 9平台(新增TikTok/YouTube/Threads)、VIDEO_TYPES 5类(新增TikTok organic开头+声效挑战)。测试9项全绿。
- 能力里程碑：16品类标杆×9平台运营×5类视频脚本×创意引擎×方案拆解全链路就绪，覆盖全球(含高奢/小众)+国内。

### §31 高奢深挖+TVC制作方法论+2026海外社媒算法 + 芥子须弥方法论总纲（2026-09-03）
- **研究**：quiet luxury(Goyard不解释主义/Hermes零代言人计算型稀缺/BV退出社媒/Margiela反广告/show object not lifestyle)；TVC制作8段(Brief→Concept3-5→Script(30s=75-90字)→Storyboard20-40帧→前期→拍摄→后期→交付,先情感后理性)；2026算法(全平台follow graph→interest graph,IG DM私发成头号信号/Reels触达30.81%,TikTok完播重看+跨垂类>3触达-45%,YouTube CTR×时长联合判,X Grok开源正向语气加权,FB首小时60-90min)。
- **知识库第八期=方法论总纲(芥子→须弥)**：L0原子技巧(钩子/景别/节奏/分发)→L1可复用公式(爆款/KFS/5栏目/视频结构/算法应对)→L2整合战役(人群×内容×渠道×节奏×场域×预算六维+造事造势造市/约束即故事/媒介即创意)→L3品牌世界观(稀缺模型/文化战略/调性坐标)；正向(战略下钻执行)+反向(案例抽象法则)双循环；每层映射到ZBC工具链。
- **落地**：social_ops 9平台加 algo_2026/algo_meta；video_script 加 PRODUCTION_WORKFLOW(8段)+SHOT_LANGUAGE(景别/运镜/节奏/光线)；工作台可视化新字段。修复被巡检覆盖丢失的pitch-analyze路由(0da1a53)。13项专项测试+全量回归EXIT=0。
