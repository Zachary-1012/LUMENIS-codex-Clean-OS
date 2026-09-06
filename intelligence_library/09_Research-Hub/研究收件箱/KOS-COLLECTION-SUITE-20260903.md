# KOS 采集功能全套增强｜设计与落地研究沉淀

- 日期：2026-09-03
- 对应 ZBC 实现：feat(kos) 552eb82（ownership gate + HCG）+ d5280fc（relevance + interaction + AI_SUGGESTED）
- 智谱 per_call 额度使用：5 次（API 验证 / 链路审查 / relevance 设计 / AI_SUGGESTED+interaction 设计 / 落地审查 6/6 PASS）
- Owner：Zachary OS AI（研究）→ Z-Brand-Core（生产落地）

## 一、设计决策（智谱第 2/3/4 次审查产出）

### 1. 主体归属 Gate（内容相关 ≠ 主体归属）
- 确定性映射 subject_type → ownership_class：
  - official → OFFICIAL（conf 0.95，DIRECT，免复核）
  - media/institution → MEDIA（0.85，DIRECT）
  - kos → INDEPENDENT_KOL_KOC（0.6，INDEPENDENT，须人工复核）
  - normal_user → UGC_CONSUMER（0.6，UGC，须复核）
  - 空 → UNKNOWN（0.3，须复核）
- 纯判定视图，不写 kos_profiles、不改广州口径；AI 不越权。

### 2. AI_SUGGESTED 归属标记（AI 只给建议，人工复核生效）
- 流程：AI 建议 → AI_SUGGESTED → 人工复核 → VERIFIED → 生效
- 字段：ownership_class + ai_status(SUGGESTED/VERIFIED) + confidence + evidence_hint
- 当前实现：ai_status=RULE（规则判定）；AI 建议机制字段就位，人工确认端点后续。

### 3. content_relevance_score（Precision 信号，不替代主体、不丢数据）
- 命中加权：标题 3 / 正文 2 / 作者+source_keyword 1；归一化 0-1。
- 排除词命中 → 0 分 + need_recheck（不自动拒入库，人工复核）。
- 低分不拒入库，仅作 KOS 排序/分层/Precision 评估信号。
- 纯规则、确定性、零 AI 运行时依赖。

### 4. interaction_pattern（KOS 识别证据）
- 从 notes 按作者聚合：likes/comments/collects/shares 均值 + 中位 engagement、active/emerging/quiet。
- 不新增生产字段，复用现有 notes 表。

### 5. 统一香港账号采集
- KOS 采集默认 CDP = cdp_url_for(XHS_RETINAUT_NAME) = http://127.0.0.1:9223（香港 RedNote）。
- body.cdp_url 可显式覆盖（大陆/其他身份）。
- 品牌主体过滤 subject_hit_for_brand(brand_key) 不因通道变化而弱化。

## 二、红线合规（智谱第 5 次审查 6/6 PASS）
1. 主体归属映射规则明确，AI 状态有复核机制 — PASS
2. relevance 规则清晰，不拒入库仅作排序信号 — PASS
3. 互动模式聚合不新增生产字段 — PASS
4. 状态机完整（AI_GENERATED→…→SUCCESS/FAILED），生成≠已发送有审计 — PASS
5. 香港账号采集默认值可覆盖，品牌主体过滤 — PASS
6. 广州太古汇口径明确，时间戳未混淆 — PASS

## 三、可复用组件（Capability Registry）
- `kos_engine.content_relevance_score(note, brand_keywords, exclude_keywords)`：确定性 relevance 信号
- `kos_engine.get_interaction_pattern(author_id, brand, limit)`：互动模式聚合
- `kos_engine.brand_kos_account(brand, author_id)`：单账号 360° 视图
- `kos_engine.ownership_for(profile, brand, ...)`：主体归属判定视图
- `kos_execution`：HCG 状态机 + 审计表（migration v9）
- API：/api/kos/brand、/api/kos/ownership、/api/kos/account、/api/kos/execution*

## 四、下一步（ZBC 侧登记）
- AI_SUGGESTED 人工复核 UI/持久化端点
- 品牌真实采集恢复后 relevance/interaction 校准
- 评论智能（情感-专业度二维）增强（智谱设计可用）
- 运营建议（回复/邀约）模板优化

## 五、AI_SUGGESTED 人工复核闭环（ZBC b82357f）
- 人工确认优先：ownership_confirm 写入 data/private/kos_ownership_overrides.json（不碰 DB），ownership_for 对已确认账号返回 VERIFIED（conf 0.9, needs_manual_review=False）。
- 规则路径输出 ai_status=RULE；AI 只给建议（AI_SUGGESTED），人工确认后转 VERIFIED 才生效，AI 不越权。
- 端点：POST /api/kos/ownership/confirm、GET /api/kos/ownership/overrides。
- 已实测：confirm->TARGET_ENTITY_KOS by zachary；红线（广州 subject_hit=True）不受影响。

## 六、评论智能增强（ZBC 13dc1ae）
- 确定性信号：_comment_sentiment（pos/neu/neg/mixed）、_purchase_signal（strong/weak/none）、_cooperation_signal（yes/no，发现潜在 KOS/商务合作）。
- analyze_comments 每条评论新增 sentiment/purchase_signal/cooperation_signal/needs_review；reply_suggestion 复用 generate_reply（单一事实源，高风险→NO_REPLY 空）。
- 原则：AI 仅增强不越权；生成≠已发送（HCG 状态机）；现有结构不破坏。
- 已实测：真实 141 条评论全带新字段+真实模板。

## 七、KOS 品牌中心 UI 接入（ZBC b1a2b98 + a84534d）
- 前端显性化后端能力：renderKosRows 共享渲染（归属类徽标+互动彩色点 active/emerging/quiet+relevance+待复核+归属按钮）；KOSConfirmOwnership 黑白灰极简 modal（7 类归属，人工确认→/api/kos/ownership/confirm→VERIFIED）。
- 广州 TOP KOS 改用 /api/kos/ownership 渲染（带信号）；非广州复用 renderKosRows。
- 浏览器实测：5 个真实广州 KOS 全带归属/待复核/relevance/互动点；modal 渲染正常；console 零报错。
- 原则：纯前端展示，数据口径/采集/五条红线零改动。

## 八、智谱高效使用五层优化（ZBC 1c0318c）
- 基线：单次智谱 ~600ms（不慢）；慢=串行+无连接复用+简单任务也走智谱+固定 max_tokens。
- 五层：①并发 chat_batch（ThreadPoolExecutor，4任务624ms vs 串行~2.4s，快~4x）②确定性缓存（md5，上限512，命中省100%token）③模型分层（HIGH/CRITICAL→ZHIPU_STRONG_MODEL如glm-4.7）④任务分级 _LEVEL_CONFIG（low30s/medium60s/high90s/critical120s+max_tokens+temperature）⑤预算护栏（ai_resource_packs.check_quota per_call，超额降级不硬崩）。
- _chat 增加 timeout=None 向后兼容参数，现有业务函数零改动。
- 下一步：现有业务函数逐一切到 chat(level=...) 获得分级/缓存收益；确认 ZHIPU_STRONG_MODEL 启用强模型。

## 九、ZHIPU_STRONG_MODEL=glm-4.7 已启用（ZBC 537fa8d）
- .env 追加 ZHIPU_STRONG_MODEL=glm-4.7（HIGH/CRITICAL 任务用 glm-4.7，LOW/MEDIUM 用 glm-4.5-air 省时省钱）。
- 强模型改动态读取 _strong_model()，避免模块 import 时序问题（.env 后加载也能读到）。
- 经验：.env 键名不在 app.py _load_dotenv 覆盖白名单时，追加即可生效；验证需先 load .env 到 os.environ 再 import 模块。
- git 运维经验：push 被拒（远程有其他会话的 docs 提交）时，先 stash 全部未提交改动（含 tests）再 rebase origin/main，成功后 pop 恢复，未提交工作零丢失。

## 十、8 个高频业务函数接入高效层（ZBC b8baf54）
- review_note/summarize_event/translate_text/analyze_sentiment/extract_keywords → medium+缓存（确定性任务）；test_connection → low+缓存；generate_summary → medium 不缓存（内容生成保多样性）；generate_report → high（glm-4.7 强模型）。
- 实测 analyze_sentiment 缓存：2279ms→0ms，结果一致（省 100% token）。
- 模式：业务函数统一从 _chat(2元组) 切到 chat(3元组)，fallback 逻辑保留（raw 空走规则兜底），预算护栏超额自动降级不硬崩。

## 十一、search_enhance 接入分级（ZBC bdb45d0）
- search_enhance(query, context='', max_results=5, model=None, level='medium')：level→联网搜索超时 30/60/90/120s；model None→ZHIPU_SEARCH_MODEL（默认 web-search-pro）。
- 实测 e2e 真实搜索 1175ms（low），3 条带来源结果；search_std 100 次配额检查/记录不变。
- 经验：独立联网搜索不走 _chat，但同样受益于 level 参数化（超时分级）；ZHIPU_SEARCH_MODEL 环境变量可切换搜索模型。

## 十二、vision_chat 分级+预算接入（ZBC acab40e）
- vision_chat(..., model=None, level='medium')：level→超时 60/90/120/180s（视觉较慢分档大）；model None→ZHIPU_VISION_MODEL（glm-4.6v）。
- 预算：估算图 tokens（<200KB→1500/1MB→3000/3MB→6000/≥3MB→10000）检查 glm_4_6v 600万配额；成功后优先记录 API 真实 usage.total_tokens。
- 实测：真实调用 947ms，total_used=60（真实 usage 比估算更准，1x1 小图仅 60 tokens）；AI 资源包面板 ⚡ 自动显示 glm_4_6v。
- 至此智谱全链路分级+预算齐：chat 8函数（并发/缓存/分级/强模型）+ search_enhance（超时分级/模型切换）+ vision_chat（分级/预算/真实用量）。require_confirmation 已于 2026-09-04 取消（视觉不强制每次确认，见十三节纪律）。

## 十三、视觉模型使用纪律（用户确认 2026-09-04）
- 原则：视觉模型（glm-4.6v）不省着用——追求单次调用最高效率/最高价值（一次分析到位，不缩水、不降采样）；但不可滥用（不重复调用、无价值调用坚决不做）。
- 2026-09-04 用户取消每次确认（require_confirmation=False），保留"不可滥用"纪律；使用判断交由执行方（效率优先，但重复/无价值调用不做）。
- 当前 vision_chat：配额护栏仅拦截保护（600万充足不误拦），记录真实 usage.total_tokens；功能完整不受限。
- 高价值用法：UI 设计审计（布局/配色/间距）、案例视觉分析、图片内容理解。禁止：重复分析同一截图、琐碎无意义调用。
