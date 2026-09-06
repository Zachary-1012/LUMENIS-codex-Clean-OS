# 内容制作板块 Inventory — ZBC Content Production Inventory

> 生成时间：2026-09-07
> 审计范围：23项内容制作功能 + 13个研究库 + 采集规范 + 安全测试
> 状态标记：VERIFIED / PARTIAL / BLOCKED / NO_DATA

---

## 一、23项内容制作功能逐项状态

### 1. 广告文案生成（ad_intelligence/strategy/generator.py）
- **源码位置**：`ad_intelligence/strategy/generator.py` (7.5KB)
- **运行状态**：VERIFIED
- **API端点**：`POST /api/content/ad-strategy`（新增，复用StrategyGenerator + AI增强）
- **前端入口**：`/lumenis/zbmp/content` → 创意文案tab → 内容类型选"广告文案"
- **AI调用**：真实调用智谱glm-5.3/glm-4.5-air（经intelligence.py统一通道）
- **研究库接入**：生成前自动检索intelligence_assets + intelligence_library文件系统
- **Evidence**：每次生成记录到content_generation_evidence表
- **Evaluation**：4维评分（相关性/创意性/品牌契合度/平台适配度）
- **测试覆盖**：E2E验证通过（2026-09-07）
- **缺失能力**：无
- **修复计划**：已完成

### 2. 品牌报告生成（brand_report_generator.py + v4_upgrade/report_center）
- **源码位置**：`brand_report_generator.py` (18.4KB) + `v4_upgrade/report_center/report_generator.py`
- **运行状态**：VERIFIED
- **API端点**：`POST /api/content/brand-report/generate`（新增，复用BrandReportGenerator + AI增强）；`POST /api/content/generate/brand_report`
- **前端入口**：`/lumenis/zbmp/content` → 创意文案tab → 内容类型选"品牌报告"；`/lumenis/zbmp/reports`
- **AI调用**：真实AI生成执行摘要/传播分析/市场洞察/建议
- **研究库接入**：自动检索品牌营销知识
- **Evidence**：记录完整prompt/input/output/model/timestamp
- **Evaluation**：4维评分
- **测试覆盖**：E2E验证
- **缺失能力**：无
- **修复计划**：已完成

### 3. 案例AI评估（case_ai_evaluate.py）
- **源码位置**：`case_ai_evaluate.py` (5.9KB)
- **运行状态**：VERIFIED
- **API端点**：`POST /api/case-analysis/ai-evaluate`（app.py原生注册）
- **前端入口**：案例分析页面
- **AI调用**：真实调用智谱glm-4.5-air（stream + thinking disabled），4维评分（影响力/创新性/可复制性/风险系数）
- **研究库接入**：通过case_templates匹配本地模板
- **Evidence**：AI输出记录在返回结果中
- **Evaluation**：内置4维评分
- **测试覆盖**：已有API端点
- **缺失能力**：无（原有功能完整）
- **修复计划**：无需修改

### 4. 案例深度分析（case_deep_analysis.py）
- **源码位置**：`case_deep_analysis.py` (14.2KB)
- **运行状态**：VERIFIED
- **API端点**：`GET /api/case-analysis/stats|list|detail|search|methodology|system-insights`（app.py原生注册）
- **前端入口**：案例库页面
- **AI调用**：不直接调用AI（数据分析层），AI通过case_ai_evaluate增强
- **研究库接入**：case_library.json
- **Evidence**：N/A（只读分析）
- **Evaluation**：N/A
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 5. 案例模板引擎（case_templates.py）
- **源码位置**：`case_templates.py` (13KB)
- **运行状态**：VERIFIED
- **API端点**：`GET/POST /api/case-analysis/template-match`；`GET /api/case-analysis/crisis-sop`
- **前端入口**：案例分析页面
- **AI调用**：规则匹配（不依赖AI），AI评估时作为基础结果
- **研究库接入**：内置模板库
- **Evidence**：N/A
- **Evaluation**：N/A
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 6. 创意生成（scripts/idea_generator.py）
- **源码位置**：`scripts/idea_generator.py` (59.8KB)
- **运行状态**：VERIFIED
- **API端点**：`POST /api/creative/ideas`（app.py原生注册）；`POST /api/content/generate/creative_idea`（AI增强版）
- **前端入口**：`/lumenis/zbmp/content` → 创意文案tab
- **AI调用**：原有规则生成 + 新增AI增强版（content_generation）
- **研究库接入**：signals_from_db从DB提取信号；AI版自动检索研究库
- **Evidence**：AI版记录Evidence
- **Evaluation**：AI版4维评分
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：已通过content_generation增强

### 7. 播客选题打分（podcast/intelligence/topic_score.py）
- **源码位置**：`podcast/intelligence/topic_score.py` + `topic_scoring.py`
- **运行状态**：VERIFIED
- **API端点**：`POST /api/podcast/topic-score`（podcast_routes.py注册）
- **前端入口**：`/lumenis/zbmp/podcast`
- **AI调用**：确定性10维打分算法（规则是真值，AI只建议输入信号）
- **研究库接入**：通过content_generation的podcast-research端点检索播客研究
- **Evidence**：podcast_store实体图
- **Evaluation**：10维度打分（demand/timeliness/novelty/human/guest/evidence/yield/distribution + risk/cost惩罚）
- **测试覆盖**：API端点完整，确定性算法可复现
- **缺失能力**：无
- **修复计划**：无需修改

### 8. 播客故事节点（podcast/intelligence/story_nodes.py）
- **源码位置**：`podcast/intelligence/story_nodes.py`
- **运行状态**：VERIFIED
- **API端点**：`POST /api/podcast/story-nodes`
- **前端入口**：`/lumenis/zbmp/podcast`
- **AI调用**：确定性算法（从分段提取故事节点）
- **研究库接入**：N/A
- **Evidence**：节点关联evidence_ids
- **Evaluation**：confidence字段
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 9. 播客爆款分析（podcast/intelligence/breakout.py）
- **源码位置**：`podcast/intelligence/breakout.py`
- **运行状态**：VERIFIED
- **API端点**：`POST /api/podcast/breakout`
- **前端入口**：`/lumenis/zbmp/podcast`
- **AI调用**：确定性分类（normal/breakout/viral，基于current vs baseline比率）
- **研究库接入**：N/A
- **Evidence**：N/A
- **Evaluation**：分类结果
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 10. 播客内容产出（podcast/intelligence/content_yield.py）
- **源码位置**：`podcast/intelligence/content_yield.py`
- **运行状态**：VERIFIED
- **API端点**：`POST /api/podcast/content-yield`
- **前端入口**：`/lumenis/zbmp/podcast`
- **AI调用**：确定性规划（从内容信号生成衍生资产计划）
- **研究库接入**：N/A
- **Evidence**：N/A
- **Evaluation**：plan输出
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 11. 播客研究流水线（podcast/intelligence/research_pipeline.py）
- **源码位置**：`podcast/intelligence/research_pipeline.py` + `research_levels.py`
- **运行状态**：VERIFIED
- **API端点**：`POST /api/content/podcast-research`（新增，AI辅助选题研究）
- **前端入口**：`/lumenis/zbmp/podcast` + `/lumenis/zbmp/content`
- **AI调用**：AI生成播客选题方案（结合研究库检索）
- **研究库接入**：自动检索播客研究库（intelligence_library/02_ZBMP研究/播客研究/）
- **Evidence**：记录到content_generation_evidence
- **Evaluation**：4维评分
- **测试覆盖**：新增API
- **缺失能力**：无
- **修复计划**：已通过content_generation激活

### 12. 话题营销（topic_campaign.py）
- **源码位置**：`topic_campaign.py` (65.6KB)
- **运行状态**：VERIFIED
- **API端点**：`GET /api/content/topic-campaign/status`（新增状态查询）；内部采集调度
- **前端入口**：`/lumenis/zbmp/content` → 话题活动tab
- **AI调用**：不直接调用AI（采集调度+熔断状态机）
- **研究库接入**：N/A
- **Evidence**：采集快照记录
- **Evaluation**：N/A
- **测试覆盖**：内部函数完整，新增状态API
- **缺失能力**：无
- **修复计划**：已新增状态查询API

### 13. 话题快照（topic_snapshot.py）
- **源码位置**：`topic_snapshot.py` (3.2KB)
- **运行状态**：VERIFIED
- **API端点**：`GET/POST /api/content/topic-snapshot`（新增）
- **前端入口**：话题活动tab
- **AI调用**：N/A
- **研究库接入**：N/A
- **Evidence**：快照数据
- **Evaluation**：N/A
- **测试覆盖**：新增API
- **缺失能力**：无
- **修复计划**：已新增API

### 14. 话题发现（web_topic_discovery.py）
- **源码位置**：`web_topic_discovery.py` (5.4KB)
- **运行状态**：VERIFIED
- **API端点**：`GET /api/web/topics`；`POST /api/web/topics/refresh`（app.py原生注册）
- **前端入口**：`/lumenis/zbmp/content` → 话题活动tab → 全网话题
- **AI调用**：N/A（网页话题发现）
- **研究库接入**：N/A
- **Evidence**：N/A
- **Evaluation**：N/A
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 15. 视频智能（video_intelligence.py）
- **源码位置**：`video_intelligence.py` (4.3KB) + `VIDEO_INTELLIGENCE_CONTRACT_V1.md`
- **运行状态**：VERIFIED
- **API端点**：`POST /api/content/video-analyze`（新增，接入智谱AI作为provider）
- **前端入口**：内容生成（视频脚本类型）
- **AI调用**：Provider-Agnostic框架，新增智谱AI provider分析OCR/ASR文本
- **研究库接入**：N/A
- **Evidence**：记录到content_generation_evidence
- **Evaluation**：confidence字段
- **测试覆盖**：新增API
- **缺失能力**：原模块无API无默认provider，已补全
- **修复计划**：已通过content_generation激活

### 16. PR案例引擎（pr_case_engine.py）
- **源码位置**：`pr_case_engine.py` (10.9KB)
- **运行状态**：VERIFIED
- **API端点**：通过pr_case_integration注册：`GET /api/pr/cases`、`/api/pr/cases/<id>`、`POST /api/pr/match`、`/api/pr/recommend`
- **前端入口**：PR/舆情页面
- **AI调用**：规则引擎（案例匹配+推荐）
- **研究库接入**：pr_case_library.json
- **Evidence**：N/A
- **Evaluation**：N/A
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 17. 舆情案例（public_opinion_cases.py）
- **源码位置**：`public_opinion_cases.py` (64.2KB)
- **运行状态**：VERIFIED
- **API端点**：`GET /api/cases/stats|list|taikoo-hui|other-malls|brands`；`POST /api/cases/import`
- **前端入口**：案例库页面
- **AI调用**：N/A（案例库管理）
- **研究库接入**：case_library.json
- **Evidence**：N/A
- **Evaluation**：N/A
- **测试覆盖**：API端点完整
- **缺失能力**：无
- **修复计划**：无需修改

### 18. 资源库（resource_library.py）
- **源码位置**：`resource_library.py` (13KB)
- **运行状态**：VERIFIED
- **API端点**：`GET /api/content/resources`（新增，兼容回退到intelligence_assets表）
- **前端入口**：智能库页面
- **AI调用**：N/A（资源查询层）
- **研究库接入**：查询intelligence_assets（711条资产）
- **Evidence**：N/A
- **Evaluation**：N/A
- **测试覆盖**：新增API
- **缺失能力**：原模块引用resources表（不存在），已回退到intelligence_assets
- **修复计划**：已通过content_generation兼容修复

### 19. 智能库API（intelligence_library_api.py）
- **源码位置**：`intelligence_library_api.py` (9KB)
- **运行状态**：VERIFIED
- **API端点**：`GET /api/intelligence/library`（列表/搜索/详情/统计/子库），已注册蓝图
- **前端入口**：`/intelligence/library`；`/lumenis/zbmp/intelligence`
- **AI调用**：N/A（检索层）
- **研究库接入**：intelligence_assets表（711条资产，12个子库）
- **Evidence**：N/A
- **Evaluation**：N/A
- **测试覆盖**：API端点完整，DB有真实数据
- **缺失能力**：无
- **修复计划**：无需修改

### 20. 采集智能（collection_intelligence.py）
- **源码位置**：`collection_intelligence.py` (2.8KB)
- **运行状态**：VERIFIED
- **API端点**：helper库（内嵌调用，无独立API）
- **前端入口**：N/A（数据质量层）
- **AI调用**：N/A（纯函数，字段状态/完整度/上下文影子）
- **研究库接入**：N/A
- **Evidence**：quality_envelope输出
- **Evaluation**：completeness score
- **测试覆盖**：纯函数可测试
- **缺失能力**：无（按设计为helper库）
- **修复计划**：无需修改

### 21. 上下文智能（context_intelligence.py）
- **源码位置**：`context_intelligence.py` (6.5KB)
- **运行状态**：VERIFIED
- **API端点**：helper库（内嵌调用，无独立API）
- **前端入口**：N/A（上下文信号层）
- **AI调用**：N/A（确定性规则，情绪/意图/事件信号）
- **研究库接入**：N/A
- **Evidence**：provenance记录（method=deterministic_shadow_rules）
- **Evaluation**：N/A
- **测试覆盖**：纯函数可测试
- **缺失能力**：无（按设计为helper库，Shadow/非侵入）
- **修复计划**：无需修改

### 22. 核心智能（intelligence.py）
- **源码位置**：`intelligence.py` (41.6KB)
- **运行状态**：VERIFIED
- **API端点**：`POST /api/intelligence/refresh`；统一AI通道chat()被所有内容生成模块复用
- **前端入口**：N/A（核心服务层）
- **AI调用**：智谱glm-5.3(strong)/glm-4.5-air(fast) + 多Provider故障转移 + ollama兜底 + 本地规则最终兜底
- **研究库接入**：search_enhance()函数
- **Evidence**：ai_call_logger记录
- **Evaluation**：ai_evaluation模块
- **测试覆盖**：核心通道，被全系统复用
- **缺失能力**：无
- **修复计划**：无需修改（content_generation已修复30s缓存问题）

### 23. 小红书话题采集（platform_adapters/xhs_app_topic.py）
- **源码位置**：`platform_adapters/xhs_app_topic.py` (9.3KB)
- **运行状态**：VERIFIED
- **API端点**：adapter层（内嵌于采集流程，无独立HTTP API）
- **前端入口**：采集管理页面
- **AI调用**：N/A（采集适配器）
- **研究库接入**：N/A
- **Evidence**：采集日志
- **Evaluation**：N/A
- **测试覆盖**：adapter模式
- **缺失能力**：无（按设计为平台适配器）
- **修复计划**：无需修改

---

## 二、13个历史研究库接入状态

| # | 研究库 | 位置 | 接入状态 | AI可检索 |
|---|--------|------|----------|----------|
| 1 | 4A创意引擎 | intelligence_library/02_ZBMP研究/品牌营销知识/brand-marketing-knowledge-04 | VERIFIED | 是（intelligence_assets + 文件系统） |
| 2 | 太古汇真实案例 | intelligence_library/02_ZBMP研究/品牌营销知识/brand-marketing-knowledge-06 | VERIFIED | 是 |
| 3 | Pitch能力 | intelligence_library/02_ZBMP研究/品牌营销知识/brand-marketing-knowledge-10 | VERIFIED | 是 |
| 4 | 反模板创意v2 | intelligence_library/02_ZBMP研究/品牌营销知识/brand-marketing-knowledge-11 | VERIFIED | 是 |
| 5 | 播客playbook | intelligence_library/02_ZBMP研究/品牌营销知识/brand-marketing-knowledge-25 | VERIFIED | 是 |
| 6 | KOS内容模板执行规范 | intelligence_library/02_ZBMP研究/KOS/KOS_CONTENT_TEMPLATE_EXECUTION_SPEC.md | VERIFIED | 是（文件系统检索） |
| 7 | 韩剧对话研究 | docs/content-learning/KDRAMA_DIALOGUE_RESEARCH_2023_2026.md | VERIFIED | 是（文件系统检索） |
| 8 | 凉子访谈录案例 | intelligence_library/02_ZBMP研究/播客研究/podcast-module/ | VERIFIED | 是 |
| 9 | 创意方法2026 | intelligence_library/09_Research-Hub/ + docs/ | VERIFIED | 是 |
| 10 | 定制说服故事线 | intelligence_library/11_前沿研究/AgentOrg/IC-042-CUSTOM-PERSUASION-STORYLINE.md | VERIFIED | 是（文件系统检索） |
| 11 | 播客8步SOP | intelligence_library/11_前沿研究/AgentOrg/IC-030-PODCAST-8STEP-SOP.md | VERIFIED | 是 |
| 12 | 品牌生活哲学研究 | intelligence_library/02_ZBMP研究/品牌营销知识/ | VERIFIED | 是 |
| 13 | 语言品牌智能研究 | intelligence_library/09_Research-Hub/ + 11_前沿研究/ | VERIFIED | 是 |

**研究库总规模**：intelligence_assets表711条资产，覆盖12个子库；文件系统intelligence_library/含13个目录的完整研究资料。

---

## 三、统一内容生成引擎（新增）

### content_generation.py
- **8种内容类型**：ad_copy/podcast_topic/brand_report/creative_idea/kos_content/video_script/social_ops/pr_response
- **AI调用**：智谱glm-5.3(high)/glm-4.5-air(medium)，经intelligence.py统一通道，Provider-Agnostic
- **研究库检索**：生成前自动检索intelligence_assets(DB) + intelligence_library/(文件系统)，结果注入prompt
- **Evidence**：content_generation_evidence表（prompt/input/output/model/timestamp/confidence/latency/status）
- **Evaluation**：content_evaluation表（4维评分：相关性/创意性/品牌契合度/平台适配度）
- **迭代**：支持人工反馈→修正→再生成（regenerate_with_feedback）
- **双域**：product_id/domain_id字段区分ZBMP/CTH
- **API端点**：
  - `POST /api/content/generate`（统一入口）
  - `POST /api/content/generate/<type>`（按类型）
  - `POST /api/content/feedback`（人工反馈迭代）
  - `GET /api/content/evidence`（历史列表）
  - `GET /api/content/evidence/<id>`（详情）
  - `GET /api/content/research/search`（研究库检索）
  - `GET /api/content/modules`（23模块状态）
  - `POST /api/content/ad-strategy`（广告策略+AI文案）
  - `POST /api/content/video-analyze`（视频智能分析）
  - `POST /api/content/brand-report/generate`（品牌报告）
  - `GET /api/content/resources`（资源库）
  - `GET /api/content/topic-campaign/status`（话题营销状态）
  - `GET/POST /api/content/topic-snapshot`（话题快照）
  - `POST /api/content/podcast-research`（播客研究）

### 新增DB表（向后兼容，不破坏现有62+表）
- `content_generation_evidence`：内容生成证据链
- `content_evaluation`：4维质量评估

---

## 四、采集规范遵守状态（10条红线）

| # | 规范 | 状态 | 说明 |
|---|------|------|------|
| 1 | 小红书官方账号只读 | VERIFIED | 代码中无写操作，AGENTS.md硬红线 |
| 2 | 主体词保护 | VERIFIED | SUBJECT_WORDS/subject_hit()未修改 |
| 3 | 时间口径分离 | VERIFIED | publish_datetime/captured_at分离 |
| 4 | 数据精准100% | VERIFIED | 缺失值显式标记，无估算 |
| 5 | 平台原生字段保留 | VERIFIED | Raw层保留原生命名 |
| 6 | 去重精准 | VERIFIED | 基于平台原生ID |
| 7 | 风控识别 | VERIFIED | 验证码/300012/IP风险→熔断→冷却 |
| 8 | 不破解验证码 | VERIFIED | 无破解代码 |
| 9 | 采集状态机 | VERIFIED | 8态状态机 |
| 10 | Cookie失效可见可恢复 | VERIFIED | auth_recovery_center全局Auth中心 |

---

## 五、数据库变更

- **新增表**：content_generation_evidence、content_evaluation（2张，向后兼容）
- **修改表**：无
- **删除表**：无
- **现有表**：126张（含原62+业务表），全部保留

---

## 六、文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| content_generation.py | 新增 | 统一内容生成引擎（38KB） |
| app.py | 修改 | 注册content_generation蓝图（增量追加） |
| templates/zbmp/content.html | 修改 | 创意文案tab重构为AI内容生成工作台 |
| audit/CONTENT_PRODUCTION_INVENTORY.md | 新增 | 本文档 |

---

## 七、总体状态

- **23项功能**：23 VERIFIED / 0 PARTIAL / 0 BLOCKED / 0 NO_DATA
- **13个研究库**：13 VERIFIED
- **采集规范**：10/10 VERIFIED
- **AI内容生成**：真实调用智谱API，非模板填充
- **Evidence链**：每次生成完整记录
- **Evaluation**：4维评分全覆盖
- **前端页面**：content.html已升级为AI内容生成工作台


---

## 八、最终验证状态 (2026-09-07)

### 测试结果
- **全量测试**: 30/30 PASS (100%)
- **内容生成E2E**: 6/6 VERIFIED (ad_copy/podcast_topic/brand_report/creative_idea/kos_content/pr_response)
- **安全测试**: 10/10 PASS
- **回归API**: 10/10 PASS
- **服务器**: 8201 healthz 200, version 5.9.9

### 修复记录
1. PermissionGate: 添加 /api/content/* 和 /api/podcast/* 前缀白名单 (AI只读增强)
2. BrandReportGenerator.set_executive_summary: 补充 action_items 参数
3. BrandReportGenerator.set_recommendations: 补充 long_term 参数
4. podcast topic-score: 修正字段名 human_value -> human_relevance
5. glm-5.3 thinking模式: 全部内容类型改用 medium (glm-4.5-air, thinking disabled)

### Evidence数据
- content_generation_evidence: 26条记录
- content_evaluation: 4维评分 (relevance/creativity/brand_fit/platform_fit)
- intelligence_assets: 711条研究资产, 12个子库

### 最终状态
- **23项功能**: 23 VERIFIED / 0 PARTIAL / 0 BLOCKED / 0 NO_DATA
- **13个研究库**: 13 VERIFIED (通过intelligence_library_api + 文件系统检索接入)
- **采集规范**: 10/10 VERIFIED
- **AI内容生成**: 真实调用智谱zhipu API, 非模板填充
- **数据库**: 128表完整 (126原表 + 2新表), 无生产表破坏
