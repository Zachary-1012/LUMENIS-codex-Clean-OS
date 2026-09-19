# Legacy Snapshot 拆解对照 + 前沿研究（2026-09-02）

> 双子星 OSAI 研究侧归档。本文件是「隔离目录未推送 ZBC 生产副本拆解 → 与双子库对照 → GitHub 前沿研究 → 可复用新方向」的完整记录。

## 一、隔离副本是什么

- 路径：`D:\Zachary OS AI\archive\_quarantine_secrets_20260902\taikoo-monitor-clean\`
- 本质：**ZBC 的 v5.3.1 时代历史快照**（旧版单体结构：app.py + collector.py + database.py + ai_analyzer.py + web_monitor.py + intelligence.py + monitor_pipeline.py + reprocess.py）
- 规模：1643 文件，顶层源码 16 个 py/js 文件 + 157 个源码文件（含 static/ 前端 + data/）
- 该副本从未推送 GitHub（.gitignore 拦截），与本次研究无关，仅作历史源码样本分析

## 二、隔离副本核心能力拆解

| 模块 | 职责 | 关键函数 | 当前主线状态 |
|---|---|---|---|
| web_monitor.py | 公开互联网舆情发现层 | google_news / gdelt / custom_rss / discover / feedback_keywords | ✅ 已迁移（同构） |
| intelligence.py | 多 Provider AI 抽象层 | _detect_local / _provider_config / review_note / summarize_event / translate_text | ✅ 已迁移+增强（redact_for_cloud 脱敏） |
| ai_analyzer.py | 规则+AI 分析 | verify_taikoo_location / analyze_sentiment / assess_risk / extract_topics / generate_daily_report | ✅ 已迁移 |
| collector.py | 小红书采集 | search_xiaohongshu / collect_all / import_from_file | ✅ 已迁移（collector_v2 重构） |
| database.py | 数据层 | 30+ 函数（insert_note/get_stats/get_hot_topics/get_historical_notes 等） | ✅ 全部存在（零缺失） |
| monitor_pipeline.py | 管线编排 | run / main | ✅ 已迁移 |
| reprocess.py | 跨平台事件聚合 | build_cross_platform_events / full_refresh / _event_key | ✅ 已迁移（reprocess.py 在主线） |
| web_monitor_v570.py | 品牌行业情报 | brand_queries / discover_brand_industry / get_brand_directory / get_industry_stats | ✅ 主线新能力（超越旧版） |
| context_intelligence.py | 上下文分析 | analyze_context / to_event_metadata | ✅ 主线新能力 |

## 三、对照结论

**隔离副本（v5.3.1）的所有核心能力 100% 已迁移到当前主线（v5.9.9-t2）且大多有增强：**
- 数据库层：旧版 30 个函数全部存在，主线另有 daily_digest / event_insight / collector_quality / find_duplicate_notes / link_event_mentions 等新表
- AI 层：主线新增 `redact_for_cloud`（云端脱敏）——比旧版更安全
- 发现层：主线新增 `web_monitor_v570`（品牌目录/行业统计/趋势话题）——比旧版更广
- 分析层：主线新增 `context_intelligence`（上下文语义分析）——比旧版更深

**结论：该历史快照无「有价值的未迁移能力」，隔离是安全的、可彻底删除的。**

## 四、GitHub 前沿研究（本文件核心增量）

### 4.1 事件检测升级方向（高价值，ADAPT）

**痛点**：CTH-POMS 当前事件聚合（reprocess.py build_cross_platform_events）基于 event_hint/关键词/_event_key 拼接分组，属**确定性规则聚合**——对同义异写、语义相近、跨平台同一事件的不同表述召回有限。

**前沿方案（2026 年生产级趋势）**：
- **语义嵌入**（sentence-transformers 多语言模型）→ 把每篇笔记/舆情转成向量
- **MinHash LSH 去重**（128 permutation, 4-gram, 0.85 Jaccard）→ 亚线性时间近似去重
- **BIRCH 增量聚类**（CF-Tree, O(n), partial_fit 流式）→ 内存友好、流式增量，无需全量重算
- **HDBSCAN 密度聚类**（min_cluster_size, 自动离群点检测）→ 无需预设簇数、发现任意密度事件
- 两阶段：BIRCH 预聚类压缩数据流 → HDBSCAN 在叶节点做密度聚类（moda.dev 150M 规模实践）

**开源参考**：
- `dukeblue1994-glitch/chronicle`（MIT）：HDBSCAN + MinHash LSH + 语义嵌入 + TF-IDF 摘要 + FastAPI + SQLite，生产级事件聚类时间线完整实现
- `QuantaOverflow/meridian`：UMAP + HDBSCAN + 多语言 E5 嵌入 + 自动参数优化
- arXiv 2601.20680：从 HDBSCAN 离线聚类升级为**在线/增量聚类**的生产叙事监控
- moda.dev 博客：BIRCH coreset → HDBSCAN 处理 150M 无标签聚类的工业实践

**对 CTH-POMS 的落地方式（ADAPT，非全盘替换）**：
1. **保留**现有 subject_rules 权威主体过滤（红线不碰）
2. 在验证通过后的笔记上，叠加语义嵌入 + BIRCH/HDBSCAN 事件聚类，替代/增强纯关键词 event_hint 分组
3. 事件证据链：cluster_id → 成员笔记 → 语义摘要 → 风险等级（沿用现有 upsert_event 表）
4. 先做离线重聚类验证（Golden Dataset），再上增量流式
5. 技术栈建议：sentence-transformers（多语言嵌入，可用本地小模型）+ hdbscan + scikit-learn Birch；无需 GPU（TF-IDF 兜底）

### 4.2 舆情事件生命周期追踪（ADAPT）
- chronicle roadmap 明确"Event evolution tracking over time"
- 语义聚类天然支持：事件随时间演化、合并、分裂、消亡
- 对 CTH-POMS：从"静态事件快照"升级为"事件时间线/生命周期视图"——直接服务 舆情日历 + 事件中心 + 报告

### 4.3 多语言舆情（MONITOR）
- chronicle 未来方向含 multi-language；现有 web_monitor 已支持 Google News/GDELT 多语言源
- 若未来需要海外品牌舆情，语义嵌入（多语言模型）是统一入口

### 4.4 增量去重升级（RESEARCH_MORE）
- 现有 find_duplicate_notes 为确定性规则（simhash 已有雏形）
- 前沿：语义级去重（同义改写/图文转载识别）——可作 P2 候选

## 五、分级决策汇总

| 方向 | 决策 | 优先级 | 说明 |
|---|---|---|---|
| 语义嵌入 + BIRCH/HDBSCAN 事件聚类升级 | ADAPT | P1 | 提升跨平台事件召回率，有完整开源参考 |
| 事件生命周期/时间线追踪 | ADAPT | P1 | 服务舆情日历+事件中心+报告 |
| 多语言舆情 | MONITOR | P2 | 待海外需求明确 |
| 语义级去重 | RESEARCH_MORE | P2 | 现有 simhash 可先强化 |
| 引入重型 Agent 框架 | REJECT | - | 与现有轻量管线不符，成本>收益 |

## 六、双子星边界
- 本文件为 OSAI 研究侧成果，不修改 ZBC 生产代码
- 若 CTH-POMS 采纳事件聚类升级，由 Z-Brand-Core/Carter 按 Contract 施工
- 无密钥、无 Cookie、无生产数据入本文件

## 七、参考来源
- chronicle: https://github.com/dukeblue1994-glitch/chronicle/
- meridian: https://github.com/QuantaOverflow/meridian
- arXiv 2601.20680 (Online Density-Based Clustering for Real-Time Narrative Evolution Monitoring)
- moda.dev/blog/clustering (BIRCH→HDBSCAN 150M 实践)
- CSDN: BIRCH+HDBSCAN 两阶段无监督主题发现（2026-08-30）
