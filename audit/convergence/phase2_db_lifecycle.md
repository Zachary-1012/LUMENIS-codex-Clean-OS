# Phase 2: 数据库表生命周期分类审计报告

> 生成时间: 2026-09-07 13:44:56
> 数据库: `data/monitor.db` (SQLite, 只读模式)
> 仓库: `D:\Taikoo-monitor-new`
> 审计范围: 全部 128 张表 (用户口径129，实际查询128表+0视图，差异1张需后续核对)

## 0. 审计方法

1. **只读查询**: `sqlite3` 以 `mode=ro` 连接，查询 `sqlite_master` 获取全部表名，逐表 `SELECT COUNT(*)`
2. **源码引用扫描**: 遍历 1357 个 `.py` 文件 + 5354 个非 `.py` 文件，对每张表名做单词边界正则匹配
3. **引用分类**: 区分核心生产代码 / 适配器桩 / 账户系统 / 报告 / 脚本 / 迁移 / 测试 / 审计注册表 / 归档 / IDE垃圾
4. **写入逻辑验证**: 对空表检查是否存在 `INSERT INTO` 语句，判断功能是否已实现
5. **迁移脚本检查**: `migrations/` 目录含 2 个 SQL 迁移文件 + `database_migrations.py` 内嵌迁移

## 1. 分类汇总

| 分类 | 数量 | 占比 | 说明 |
|------|------|------|------|
| KEEP | 98 | 76.6% | 生产核心表，有代码引用+有数据或有明确业务用途 |
| MIGRATE | 27 | 21.1% | 有代码引用但schema需演进/合并，或功能未完成 |
| DEPRECATE | 3 | 2.3% | 被新表替代的遗留表，保留历史数据 |
| DELETE-CANDIDATE | 0 | 0.0% | 无代码引用、无数据、无业务用途 (本次审计未发现符合此严格标准的表) |
| **合计** | **128** | **100%** | |

### 按产品域分布

| 产品域 | 表数 |
|--------|------|
| 采集 | 49 |
| 系统 | 32 |
| 品牌 | 15 |
| AI | 11 |
| KOS | 8 |
| 事件 | 5 |
| 风险 | 2 |
| 报告 | 2 |
| 舆情 | 2 |
| 其他 | 2 |

## 2. 全表汇总 (按表名排序)

| 表名 | 行数 | 引用文件数 | 主要引用文件 | 产品域 | 分类 | 分类理由 |
|------|------|-----------|-------------|--------|------|----------|
| ai_call_logs | 542 | 42 | AI_PROVIDER_FAILOVER_POLICY_V1.0.md, ai_call_logger.py | AI | KEEP | AI调用日志，542行，ai_call_logger/ai_channel引用 |
| ai_filter_log | 864 | 80 | spec.md, tasks.md | AI | KEEP | AI过滤日志，864行，10个app引用，核心AI过滤链路 |
| ai_task | 970 | 6 | ai_task_engine.py, app.py | AI | KEEP | AI任务表，970行，ai_task_engine+app.py引用 |
| ai_task_evidence | 1354 | 5 | ai_task_engine.py | AI | KEEP | AI任务证据，1354行，ai_task_engine引用 |
| ai_task_step | 2234 | 5 | ai_task_engine.py | AI | KEEP | AI任务步骤，2234行，ai_task_engine引用 |
| ai_task_trace | 2800 | 5 | ai_task_engine.py | AI | KEEP | AI任务追踪，2800行，ai_task_engine引用 |
| alert_configs | 13 | 22 | alert_engine.py, ZBC_FEATURE_MAP_DUAL_DOMAIN_20260906.md | 风险 | KEEP | 预警配置，13行，alert_engine.py引用 |
| alert_records | 0 | 40 | alert_engine.py, badge_api.py | 风险 | KEEP | 预警记录，空表但alert_engine.py有INSERT逻辑，预警触发后写入 |
| app_evidence_records | 17 | 75 | scripts_inventory_feature_final_verify.py, _t10_db_audit.py | 系统 | KEEP | 应用证据记录，17行，app_evidence.py引用 |
| auth_recovery_tasks | 5 | 40 | auth_recovery_center.py, ZBC_PAGE_LEVEL_DESIGN_V1.1.md | 系统 | KEEP | Auth恢复任务，5行，全局Auth状态中心 |
| bilibili_comments | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | B站评论，空表，仅data_center_api.py+platform_naming.py引用，无bilibili.p... |
| bilibili_users | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | B站用户，空表，同上 |
| bilibili_videos | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | B站视频，空表，同上 |
| brand_industry_monitor | 198 | 42 | ARCHITECTURE.md, app.py | 品牌 | KEEP | 品牌业态监测，198行，app.py引用 |
| brand_knowledge | 0 | 56 | CHANGELOG.md, brand_knowledge_base.py | 品牌 | KEEP | 品牌知识库，空表但brand_knowledge_base.py有INSERT逻辑 |
| brand_propagation_entities | 0 | 9 | brand_propagation.py, gap_closure_audit.md | 品牌 | MIGRATE | 品牌传播实体，空表，仅brand_propagation.py引用，无INSERT，AGENTS.md 9.1传播主体规... |
| brand_propagation_events | 0 | 9 | brand_propagation.py, gap_closure_audit.md | 品牌 | MIGRATE | 品牌传播事件，空表，仅brand_propagation.py引用，无INSERT，AGENTS.md 9.3三类事件规... |
| brands | 0 | 117 | CANONICAL_REGISTRY.md, UNIFIED-DATA-INTELLIGENCE-PIPELINE-V1.0.md | 品牌 | KEEP | 多品牌核心表，空表但20个app引用，Z-Brand平台多品牌架构基础 |
| browser_evidence | 722 | 7 | ai_browser_runtime.py | 系统 | KEEP | 浏览器证据，722行，ai_browser_runtime引用 |
| canonical_data | 13 | 100 | feature_registry.md, osai_module_call_graph_shardB.json | 采集 | KEEP | 标准化数据，13行，14个app引用，双域核心 |
| case_deep_analysis | 0 | 106 | feature_registry.md, CHANGELOG.md | 品牌 | KEEP | 案例深度分析，空表但case_deep_analysis.py有INSERT逻辑 |
| channels_comments | 0 | 9 | data_center_api.py, channels.py | 采集 | KEEP | 频道评论，空表，platform_adapters/channels.py有实现 |
| channels_videos | 0 | 9 | data_center_api.py, channels.py | 采集 | KEEP | 频道视频，空表，platform_adapters/channels.py有实现 |
| collection_logs | 499 | 119 | tasks.md, ARCHITECTURE.md, health_center.py | 采集 | KEEP | 采集日志，499行，20个app引用，采集主链路 |
| collection_quality_log | 0 | 11 | app.py, collection_quality_gate.py | 采集 | KEEP | 采集质量门日志，空表但collection_quality_gate.py有INSERT逻辑，migration v11... |
| collection_runs | 0 | 7 | data_center_api.py | 采集 | MIGRATE | 采集运行，空表，仅data_center_api.py引用，无INSERT，可能被collection_logs替代，需... |
| collector_quality_log | 7 | 67 | ARCHITECTURE.md, check_logs.py | 采集 | KEEP | 采集器质量日志，7行，database.py定义+INSERT |
| content_analysis | 0 | 6 | data_center_api.py | AI | MIGRATE | 内容分析，空表，仅data_center_api.py引用，无INSERT，可能被content_evaluation替... |
| content_evaluation | 34 | 8 | app.py, content_generation.py | AI | KEEP | 内容评估，34行，app.py+content_generation引用 |
| content_generation_evidence | 34 | 8 | app.py, content_generation.py | AI | KEEP | 内容生成证据，34行，content_generation引用 |
| creators | 0 | 21 | KOS_ENTITY_OWNERSHIP_CONTRACT_v1.md, data_center_api.py | KOS | MIGRATE | 创作者表，空表，仅data_center_api.py+scripts引用，无INSERT，KOS主体可能已由kos_p... |
| daily_digest | 9 | 60 | ARCHITECTURE.md, daily_report.py | 报告 | KEEP | 每日摘要，9行，daily_report.py引用 |
| daily_reports | 30 | 120 | tasks.md, AGENTS.md, evidence_exporter.py | 报告 | KEEP | 日报，30行，21个app引用，报告核心 |
| douyin_comments | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | 抖音评论，空表，仅注册表引用，无adapter实现 |
| douyin_users | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | 抖音用户，空表，同上 |
| douyin_videos | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | 抖音视频，空表，同上 |
| evaluation_records | 0 | 28 | evaluation_recorder.py, evaluation_runner.py | AI | KEEP | 评估记录，空表但evaluation_recorder.py+evaluation_runner.py有完整逻辑 |
| event_graph_events | 0 | 60 | CHANGELOG.md, app.py | 事件 | KEEP | 事件图谱事件，空表但event_graph.py有INSERT逻辑 |
| event_graph_relations | 0 | 43 | CHANGELOG.md, DEV_LOG.md | 事件 | MIGRATE | 事件图谱关系，空表，event_graph.py有CREATE+DELETE但无INSERT，功能未完成，需补全写入逻辑 |
| event_insights | 17 | 59 | ARCHITECTURE.md, daily_report.py | 事件 | KEEP | 事件洞察，17行，事件分析 |
| event_mentions | 736 | 84 | E-001-E-009_close-out.md, self-review-checklist.md | 事件 | KEEP | 事件提及，736行，app.py引用，事件核心 |
| events | 461 | 403 | PROGRESS.md, scripts_e2e_loop_check.py, nav_config.py | 事件 | KEEP | 事件表，461行，60个app引用，事件中心核心 |
| feedback_keywords | 16 | 72 | _t10_db_audit.py, ARCHITECTURE.md | 舆情 | KEEP | 反馈关键词，16行，app.py引用 |
| github_issues | 0 | 9 | data_center_api.py, github.py | 采集 | KEEP | GitHub Issues，空表，platform_adapters/github.py有实现 |
| github_pull_requests | 0 | 9 | data_center_api.py, github.py | 采集 | KEEP | GitHub PR，空表，platform_adapters/github.py有实现 |
| github_releases | 0 | 9 | data_center_api.py, github.py | 采集 | KEEP | GitHub Release，空表，platform_adapters/github.py有实现 |
| github_repositories | 0 | 9 | data_center_api.py, github.py | 采集 | KEEP | GitHub仓库，空表，platform_adapters/github.py有实现 |
| historical_import_log | 0 | 22 | historical_data_importer.py, _table_info.json | 系统 | KEEP | 历史导入日志，空表但historical_data_importer.py有INSERT逻辑 |
| industry_stats | 8 | 13 | source_refs.json, 05_DATABASE_RECONCILIATION.md | 品牌 | KEEP | 行业统计，8行，schema_registry定义 |
| instagram_comments | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | Instagram评论，空表，仅注册表引用，无adapter实现 |
| instagram_media | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | Instagram媒体，空表，同上 |
| instagram_users | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | Instagram用户，空表，同上 |
| intelligence_assets | 711 | 25 | content_generation.py, INTELLIGENCE_LIBRARY_ARCHITECTURE_V1.0.md | 品牌 | KEEP | 情报资产，711行，intelligence_library_api引用 |
| kos_executions | 494 | 28 | DEV_LOG.md, ZBC_PAGE_LEVEL_DESIGN_V1.1.md | KOS | KEEP | KOS执行，494行，kos_execution.py引用 |
| kos_operations | 340 | 28 | function_registry.py, _table_info.json | KOS | KEEP | KOS运营，340行，kos_ops.py引用 |
| kos_paid_plans | 136 | 27 | ZBC_PAGE_LEVEL_DESIGN_V1.1.md, _table_info.json | KOS | KEEP | KOS付费计划，136行，kos_paid.py引用 |
| kos_profiles | 375 | 54 | DEV_LOG.md, kos_profile.yaml | KOS | KEEP | KOS画像，375行，12个app引用，kos_engine核心 |
| kos_rewards | 68 | 20 | _table_info.json, db_api_guardian_audit.md | KOS | KEEP | KOS奖励，68行，kos_paid.py引用 |
| linkedin_posts | 0 | 9 | data_center_api.py, linkedin.py | 采集 | KEEP | LinkedIn帖子，空表，platform_adapters/linkedin.py有实现 |
| linkedin_users | 0 | 9 | data_center_api.py, linkedin.py | 采集 | KEEP | LinkedIn用户，空表，platform_adapters/linkedin.py有实现 |
| metric_snapshots | 1087 | 55 | data_center_api.py, database.py | 系统 | KEEP | 指标快照，1087行，database.py+data_center_api引用 |
| note_comments | 141 | 92 | ARCHITECTURE.md, cache_manager.py | 采集 | KEEP | 笔记评论，141行，17个app引用，评论核心 |
| note_review_history | 8347 | 85 | tasks.md, ARCHITECTURE.md | 舆情 | KEEP | 笔记审核历史，8347行，审核链路核心 |
| notes | 1020 | 780 | _reanalyze.py, AGENTS.md, bilibili.py | 采集 | KEEP | 笔记表，1020行，171个app引用，系统最核心表 |
| notification_config | 0 | 22 | check_empty_tables.py, source_refs.json | 系统 | KEEP | 通知配置，空表但wechat_notifier.py有INSERT逻辑 |
| notification_logs | 3 | 25 | check_empty_tables.py, check_system.py | 系统 | KEEP | 通知日志，3行，通知系统 |
| platform_accounts | 0 | 6 | data_center_api.py | 采集 | MIGRATE | 平台账号通用表，空表，仅data_center_api.py引用，无INSERT，通用表与各平台adapter表职责重叠... |
| platform_comments | 0 | 6 | data_center_api.py | 采集 | MIGRATE | 平台评论通用表，空表，仅data_center_api.py引用，无INSERT，同上 |
| platform_contents | 0 | 8 | data_center_api.py, channels.py | 采集 | KEEP | 平台内容通用表，空表，platform_adapters/channels.py引用 |
| platform_evidence | 0 | 7 | data_center_api.py | 采集 | MIGRATE | 平台证据通用表，空表，仅data_center_api.py引用，无INSERT，同上 |
| platform_registry | 12 | 34 | data_center_api.py, ZBC_FEATURE_GAP_AUDIT_20260906.md | 系统 | KEEP | 平台注册表，12行，ad_intelligence+data_center引用 |
| podcast_ai_runs | 0 | 31 | ZBC_FEATURE_MAP_DUAL_DOMAIN_20260906.md, _table_info.json | 其他 | MIGRATE | 播客AI运行，空表，仅文档引用无.py实现代码，功能未启动，需评估是否实现或删除 |
| podcast_entities | 0 | 33 | ZBC_FEATURE_MAP_DUAL_DOMAIN_20260906.md, _table_info.json | 其他 | KEEP | 播客实体，空表但podcast_store.py有INSERT逻辑 |
| professional_accounts | 0 | 37 | function_registry.py, ZBC_PAGE_LEVEL_DESIGN_V1.1.md | KOS | KEEP | 专业账号，空表但kos_professional.py有INSERT逻辑 |
| professional_metrics | 0 | 35 | function_registry.py, ZBC_PAGE_LEVEL_DESIGN_V1.1.md | KOS | MIGRATE | 专业指标，空表，仅function_registry.py+文档引用，无INSERT，需补全实现或合并 |
| reddit_comments | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | Reddit评论，空表，platform_adapters/reddit.py有实现 |
| reddit_posts | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | Reddit帖子，空表，platform_adapters/reddit.py有实现 |
| reddit_subreddits | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | Reddit子版，空表，platform_adapters/reddit.py有实现 |
| rule_version_registry | 1 | 20 | historical_data_importer.py, _table_info.json | 系统 | KEEP | 规则版本注册，1行，规则管理 |
| runtime_guardian_checkpoints | 38 | 24 | evaluation_dimensions.py, function_registry.py | 系统 | KEEP | 运行时守护检查点，38行 |
| runtime_guardian_dlq | 0 | 28 | api_dual_domain.py, evidence_api.py | 系统 | KEEP | 死信队列，空表但evidence_store.py+runtime_guardian.py有INSERT逻辑，正常应为空 |
| runtime_guardian_workers | 1007 | 27 | api_dual_domain.py, function_registry.py | 系统 | KEEP | 运行时守护worker，1007行，function_registry引用 |
| schedule_decisions | 14408 | 40 | DEV_LOG.md, _table_info.json, planner.py | 系统 | KEEP | 调度决策，14408行，planner.py引用，调度核心 |
| schema_version | 4 | 66 | spec.md, tasks.md | 系统 | KEEP | Schema版本，4行，数据库迁移管理 |
| skill_executions | 18 | 3 | skill_execution_chain.py | 系统 | KEEP | 技能执行，18行，skill_execution_chain引用 |
| skills_registry | 12 | 10 | models.py | 系统 | KEEP | 技能注册表，12行，account/skills.py引用 |
| swire_events | 10 | 42 | learning_database.json, RESEARCH_2026-09-C-CONSTRAINT.md | 品牌 | KEEP | 太古汇事件，10行，report_engine引用 |
| swire_notes | 0 | 70 | PROJECT_STATUS.md, WORK_LOG_20260901.md | 品牌 | KEEP | 太古汇笔记，空表但swire_group.py有INSERT逻辑 |
| swire_projects | 8 | 30 | _table_info.json, db_api_guardian_audit.md | 品牌 | KEEP | 太古汇项目，8行，swire_group.py引用 |
| tiktok_comments | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | TikTok评论，空表，platform_adapters/tiktok.py有实现 |
| tiktok_users | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | TikTok用户，空表，platform_adapters/tiktok.py有实现 |
| tiktok_videos | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | TikTok视频，空表，platform_adapters/tiktok.py有实现 |
| token_stat | 0 | 47 | CHANGELOG.md, DEV_LOG.md | AI | MIGRATE | Token统计，空表，仅ark_llm.py引用，无INSERT，可能被ai_call_logs替代，需确认合并 |
| topic_campaign_notes | 79 | 84 | CHANGELOG.md, DEV_LOG.md | 品牌 | KEEP | 话题活动笔记，79行，活动监测 |
| topic_campaign_snapshots | 325 | 51 | DEV_LOG.md, function_registry.py | 品牌 | KEEP | 话题活动快照，325行，活动监测 |
| topic_campaign_topics | 7 | 36 | _table_info.json, db_api_guardian_audit.md | 品牌 | KEEP | 话题活动主题，7行，活动监测 |
| topic_campaigns | 1 | 38 | ZBC_PAGE_LEVEL_DESIGN_V1.1.md, _table_info.json | 品牌 | KEEP | 话题活动，1行，活动监测核心 |
| user_nav_config | 0 | 9 | models.py | 系统 | KEEP | 用户导航配置，空表但account/nav_config.py有INSERT逻辑 |
| v4_audit_logs | 57 | 52 | _t10_db_audit.py, security_verification_shardC.md, audit.py | 系统 | KEEP | 审计日志，57行，account/models.py引用 |
| v4_login_approvals | 0 | 9 | api.py | 系统 | KEEP | 登录审批，空表但account/api.py+models.py有完整逻辑 |
| v4_login_attempts | 39 | 49 | _t10_db_audit.py, security_verification_shardC.md, models.py | 系统 | KEEP | 登录尝试，39行，account/security.py引用 |
| v4_member_authorizations | 2 | 9 | authorization.py | 系统 | KEEP | 成员授权，2行，account/authorization引用 |
| v4_product_protection | 0 | 9 | models.py | 系统 | KEEP | 产品保护，空表但account/product_protection.py有INSERT逻辑 |
| v4_security_questions | 2 | 33 | api.py, VISUAL_REFRESH_AND_APPLEID_ACCOUNT_REQUIREMENT_V1.0.md, _table_info.json | 系统 | KEEP | 安全问题，2行，account/security引用 |
| v4_sessions | 110 | 43 | security_verification_shardC.md, api.py, CTH-POMS_LEARNING_LIBRARY.md | 系统 | KEEP | 会话，110行，account/service引用 |
| v4_totp_secrets | 2 | 10 | models.py | 系统 | KEEP | TOTP密钥，2行，account/totp引用 |
| v4_users | 9 | 51 | security_verification_shardC.md, DEV_LOG.md, api.py | 系统 | KEEP | 用户，9行，8个app引用，账户核心 |
| v4_verification_codes | 0 | 9 | models.py | 系统 | KEEP | 验证码，空表但account/verification.py有INSERT逻辑 |
| v4_workspace_grants | 70 | 28 | security_verification_shardC.md, models.py, _table_info.json | 系统 | KEEP | 工作区授权，70行，account/workspace_keys引用 |
| v4_workspace_keys | 352 | 32 | security_verification_shardC.md, models.py, app.py | 系统 | KEEP | 工作区密钥，352行，app.py+account引用 |
| web_mentions | 89 | 78 | ARCHITECTURE.md, api_dual_domain.py | 采集 | KEEP | 网页提及，89行，11个app引用，网页采集 |
| web_runs | 29 | 45 | ARCHITECTURE.md, phase8-six-maps-20260902.json | 采集 | KEEP | 网页采集运行，29行，database.py引用 |
| web_sources | 1 | 50 | ARCHITECTURE.md, app.py | 采集 | KEEP | 网页源，1行，app.py引用，网页采集配置 |
| x_posts | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | X帖子，空表，仅注册表引用，无adapter实现 |
| x_users | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | X用户，空表，同上 |
| xhs_note_comments | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | DEPRECATE | 遗留小红书评论表，空表，已被note_comments替代，仅注册表引用 |
| xhs_notes | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | DEPRECATE | 遗留小红书笔记表，空表，schema与notes不同(无id主键/列名不同)，已被notes表替代，仅注册表引用，保留用... |
| xhs_users | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | DEPRECATE | 遗留小红书用户表，空表，用户信息已嵌入notes表，仅注册表引用 |
| youtube_channels | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | YouTube频道，空表，platform_adapters/youtube.py有实现 |
| youtube_comments | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | YouTube评论，空表，platform_adapters/youtube.py有实现 |
| youtube_videos | 0 | 9 | data_center_api.py, platform_naming.py | 采集 | KEEP | YouTube视频，空表，platform_adapters/youtube.py有实现 |
| zbc_canonical_data | 4 | 23 | app.py, evidence_chain.py | 系统 | KEEP | ZBC标准化数据，4行，evidence_chain引用 |
| zbc_evidence | 6 | 35 | acceptance_evidence_chain.py, app.py | 系统 | KEEP | ZBC证据，6行，acceptance_evidence_chain引用 |
| zbc_lifecycle_tracking | 8 | 20 | evidence_chain.py, ZBC_FEATURE_MAP_DUAL_DOMAIN_20260906.md | 系统 | KEEP | ZBC生命周期追踪，8行，evidence_chain引用 |
| zhihu_answers | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | 知乎回答，空表，仅注册表引用，无adapter实现 |
| zhihu_articles | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | 知乎文章，空表，同上 |
| zhihu_comments | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | 知乎评论，空表，同上 |
| zhihu_questions | 0 | 8 | data_center_api.py, platform_naming.py | 采集 | MIGRATE | 知乎问题，空表，同上 |

## 3. KEEP 详细清单 (98 张)

### 3.1 有数据的生产核心表 (63张)

| 表名 | 行数 | 产品域 | 核心引用 |
|------|------|--------|----------|
| ai_call_logs | 542 | AI | AI_PROVIDER_FAILOVER_POLICY_V1.0.md, ai_call_logger.py |
| ai_filter_log | 864 | AI | spec.md, tasks.md |
| ai_task | 970 | AI | ai_task_engine.py, app.py |
| ai_task_evidence | 1354 | AI | ai_task_engine.py |
| ai_task_step | 2234 | AI | ai_task_engine.py |
| ai_task_trace | 2800 | AI | ai_task_engine.py |
| alert_configs | 13 | 风险 | alert_engine.py, ZBC_FEATURE_MAP_DUAL_DOMAIN_20260906.md |
| app_evidence_records | 17 | 系统 | scripts_inventory_feature_final_verify.py, _t10_db_audit.py |
| auth_recovery_tasks | 5 | 系统 | auth_recovery_center.py, ZBC_PAGE_LEVEL_DESIGN_V1.1.md |
| brand_industry_monitor | 198 | 品牌 | ARCHITECTURE.md, app.py |
| browser_evidence | 722 | 系统 | ai_browser_runtime.py |
| canonical_data | 13 | 采集 | feature_registry.md, osai_module_call_graph_shardB.json |
| collection_logs | 499 | 采集 | tasks.md, ARCHITECTURE.md |
| collector_quality_log | 7 | 采集 | ARCHITECTURE.md, check_logs.py |
| content_evaluation | 34 | AI | app.py, content_generation.py |
| content_generation_evidence | 34 | AI | app.py, content_generation.py |
| daily_digest | 9 | 报告 | ARCHITECTURE.md, daily_report.py |
| daily_reports | 30 | 报告 | tasks.md, AGENTS.md |
| event_insights | 17 | 事件 | ARCHITECTURE.md, daily_report.py |
| event_mentions | 736 | 事件 | E-001-E-009_close-out.md, self-review-checklist.md |
| events | 461 | 事件 | PROGRESS.md, scripts_e2e_loop_check.py |
| feedback_keywords | 16 | 舆情 | _t10_db_audit.py, ARCHITECTURE.md |
| industry_stats | 8 | 品牌 | source_refs.json, 05_DATABASE_RECONCILIATION.md |
| intelligence_assets | 711 | 品牌 | content_generation.py, INTELLIGENCE_LIBRARY_ARCHITECTURE_V1.0.md |
| kos_executions | 494 | KOS | DEV_LOG.md, ZBC_PAGE_LEVEL_DESIGN_V1.1.md |
| kos_operations | 340 | KOS | function_registry.py, _table_info.json |
| kos_paid_plans | 136 | KOS | ZBC_PAGE_LEVEL_DESIGN_V1.1.md, _table_info.json |
| kos_profiles | 375 | KOS | DEV_LOG.md, kos_profile.yaml |
| kos_rewards | 68 | KOS | _table_info.json, db_api_guardian_audit.md |
| metric_snapshots | 1087 | 系统 | data_center_api.py, database.py |
| note_comments | 141 | 采集 | ARCHITECTURE.md, cache_manager.py |
| note_review_history | 8347 | 舆情 | tasks.md, ARCHITECTURE.md |
| notes | 1020 | 采集 | _reanalyze.py, AGENTS.md |
| notification_logs | 3 | 系统 | check_empty_tables.py, check_system.py |
| platform_registry | 12 | 系统 | data_center_api.py, ZBC_FEATURE_GAP_AUDIT_20260906.md |
| rule_version_registry | 1 | 系统 | historical_data_importer.py, _table_info.json |
| runtime_guardian_checkpoints | 38 | 系统 | evaluation_dimensions.py, function_registry.py |
| runtime_guardian_workers | 1007 | 系统 | api_dual_domain.py, function_registry.py |
| schedule_decisions | 14408 | 系统 | DEV_LOG.md, _table_info.json |
| schema_version | 4 | 系统 | spec.md, tasks.md |
| skill_executions | 18 | 系统 | skill_execution_chain.py |
| skills_registry | 12 | 系统 |  |
| swire_events | 10 | 品牌 | learning_database.json, RESEARCH_2026-09-C-CONSTRAINT.md |
| swire_projects | 8 | 品牌 | _table_info.json, db_api_guardian_audit.md |
| topic_campaign_notes | 79 | 品牌 | CHANGELOG.md, DEV_LOG.md |
| topic_campaign_snapshots | 325 | 品牌 | DEV_LOG.md, function_registry.py |
| topic_campaign_topics | 7 | 品牌 | _table_info.json, db_api_guardian_audit.md |
| topic_campaigns | 1 | 品牌 | ZBC_PAGE_LEVEL_DESIGN_V1.1.md, _table_info.json |
| v4_audit_logs | 57 | 系统 | _t10_db_audit.py, security_verification_shardC.md |
| v4_login_attempts | 39 | 系统 | _t10_db_audit.py, security_verification_shardC.md |
| v4_member_authorizations | 2 | 系统 |  |
| v4_security_questions | 2 | 系统 | VISUAL_REFRESH_AND_APPLEID_ACCOUNT_REQUIREMENT_V1.0.md, _table_info.json |
| v4_sessions | 110 | 系统 | security_verification_shardC.md, CTH-POMS_LEARNING_LIBRARY.md |
| v4_totp_secrets | 2 | 系统 |  |
| v4_users | 9 | 系统 | security_verification_shardC.md, DEV_LOG.md |
| v4_workspace_grants | 70 | 系统 | security_verification_shardC.md, _table_info.json |
| v4_workspace_keys | 352 | 系统 | security_verification_shardC.md, app.py |
| web_mentions | 89 | 采集 | ARCHITECTURE.md, api_dual_domain.py |
| web_runs | 29 | 采集 | ARCHITECTURE.md, phase8-six-maps-20260902.json |
| web_sources | 1 | 采集 | ARCHITECTURE.md, app.py |
| zbc_canonical_data | 4 | 系统 | app.py, evidence_chain.py |
| zbc_evidence | 6 | 系统 | acceptance_evidence_chain.py, app.py |
| zbc_lifecycle_tracking | 8 | 系统 | evidence_chain.py, ZBC_FEATURE_MAP_DUAL_DOMAIN_20260906.md |

### 3.2 空表但有活跃写入逻辑 (17张)

| 表名 | 产品域 | 写入逻辑位置 | 说明 |
|------|--------|-------------|------|
| alert_records | 风险 | 空表但alert_engine.py有INSERT逻辑 | 预警记录，空表但alert_engine.py有INSERT逻辑，预警触发后写入 |
| brand_knowledge | 品牌 | 空表但brand_knowledge_base.py有INSERT逻辑 | 品牌知识库，空表但brand_knowledge_base.py有INSERT逻辑 |
| brands | 品牌 | 空表但20个app引用 | 多品牌核心表，空表但20个app引用，Z-Brand平台多品牌架构基础 |
| case_deep_analysis | 品牌 | 空表但case_deep_analysis.py有INSERT逻辑 | 案例深度分析，空表但case_deep_analysis.py有INSERT逻辑 |
| collection_quality_log | 采集 | 空表但collection_quality_gate.py有INSERT逻辑 | 采集质量门日志，空表但collection_quality_gate.py有INSERT逻辑，migration v11创建 |
| evaluation_records | AI | 空表但evaluation_recorder.py+evaluation_runner.py有完整逻辑 | 评估记录，空表但evaluation_recorder.py+evaluation_runner.py有完整逻辑 |
| event_graph_events | 事件 | 空表但event_graph.py有INSERT逻辑 | 事件图谱事件，空表但event_graph.py有INSERT逻辑 |
| historical_import_log | 系统 | 空表但historical_data_importer.py有INSERT逻辑 | 历史导入日志，空表但historical_data_importer.py有INSERT逻辑 |
| notification_config | 系统 | 空表但wechat_notifier.py有INSERT逻辑 | 通知配置，空表但wechat_notifier.py有INSERT逻辑 |
| podcast_entities | 其他 | 空表但podcast_store.py有INSERT逻辑 | 播客实体，空表但podcast_store.py有INSERT逻辑 |
| professional_accounts | KOS | 空表但kos_professional.py有INSERT逻辑 | 专业账号，空表但kos_professional.py有INSERT逻辑 |
| runtime_guardian_dlq | 系统 | 空表但evidence_store.py+runtime_guardian.py有INSERT逻辑 | 死信队列，空表但evidence_store.py+runtime_guardian.py有INSERT逻辑，正常应为空 |
| swire_notes | 品牌 | 空表但swire_group.py有INSERT逻辑 | 太古汇笔记，空表但swire_group.py有INSERT逻辑 |
| user_nav_config | 系统 | 空表但account/nav_config.py有INSERT逻辑 | 用户导航配置，空表但account/nav_config.py有INSERT逻辑 |
| v4_login_approvals | 系统 | 空表但account/api.py+models.py有完整逻辑 | 登录审批，空表但account/api.py+models.py有完整逻辑 |
| v4_product_protection | 系统 | 空表但account/product_protection.py有INSERT逻辑 | 产品保护，空表但account/product_protection.py有INSERT逻辑 |
| v4_verification_codes | 系统 | 空表但account/verification.py有INSERT逻辑 | 验证码，空表但account/verification.py有INSERT逻辑 |

### 3.3 未来平台适配器表 (18张)

| 表名 | 产品域 | Adapter实现 | 说明 |
|------|--------|------------|------|
| channels_comments | 采集 | channels.py | 频道评论，空表，platform_adapters/channels.py有实现 |
| channels_videos | 采集 | channels.py | 频道视频，空表，platform_adapters/channels.py有实现 |
| github_issues | 采集 | github.py | GitHub Issues，空表，platform_adapters/github.py有实现 |
| github_pull_requests | 采集 | github.py | GitHub PR，空表，platform_adapters/github.py有实现 |
| github_releases | 采集 | github.py | GitHub Release，空表，platform_adapters/github.py有实现 |
| github_repositories | 采集 | github.py | GitHub仓库，空表，platform_adapters/github.py有实现 |
| linkedin_posts | 采集 | linkedin.py | LinkedIn帖子，空表，platform_adapters/linkedin.py有实现 |
| linkedin_users | 采集 | linkedin.py | LinkedIn用户，空表，platform_adapters/linkedin.py有实现 |
| platform_contents | 采集 | channels.py | 平台内容通用表，空表，platform_adapters/channels.py引用 |
| reddit_comments | 采集 | platform_naming.py | Reddit评论，空表，platform_adapters/reddit.py有实现 |
| reddit_posts | 采集 | platform_naming.py | Reddit帖子，空表，platform_adapters/reddit.py有实现 |
| reddit_subreddits | 采集 | platform_naming.py | Reddit子版，空表，platform_adapters/reddit.py有实现 |
| tiktok_comments | 采集 | platform_naming.py | TikTok评论，空表，platform_adapters/tiktok.py有实现 |
| tiktok_users | 采集 | platform_naming.py | TikTok用户，空表，platform_adapters/tiktok.py有实现 |
| tiktok_videos | 采集 | platform_naming.py | TikTok视频，空表，platform_adapters/tiktok.py有实现 |
| youtube_channels | 采集 | platform_naming.py | YouTube频道，空表，platform_adapters/youtube.py有实现 |
| youtube_comments | 采集 | platform_naming.py | YouTube评论，空表，platform_adapters/youtube.py有实现 |
| youtube_videos | 采集 | platform_naming.py | YouTube视频，空表，platform_adapters/youtube.py有实现 |

## 4. MIGRATE 详细清单 (27 张)

### 4.1 功能未完成/需演进 (8张)

| 表名 | 产品域 | 行数 | 问题 | 建议 |
|------|--------|------|------|------|
| event_graph_relations | 事件 | 0 | 事件图谱关系，空表，event_graph.py有CREATE+DELETE但无INSERT，功能未完成，需补全写入逻辑 | 补全INSERT逻辑或确认合并 |
| brand_propagation_entities | 品牌 | 0 | 品牌传播实体，空表，仅brand_propagation.py引用，无INSERT，AGENTS.md 9.1传播主体规划中，需演进 | 补全INSERT逻辑或确认合并 |
| brand_propagation_events | 品牌 | 0 | 品牌传播事件，空表，仅brand_propagation.py引用，无INSERT，AGENTS.md 9.3三类事件规划中，需演进 | 补全INSERT逻辑或确认合并 |
| podcast_ai_runs | 其他 | 0 | 播客AI运行，空表，仅文档引用无.py实现代码，功能未启动，需评估是否实现或删除 | 补全INSERT逻辑或确认合并 |
| professional_metrics | KOS | 0 | 专业指标，空表，仅function_registry.py+文档引用，无INSERT，需补全实现或合并 | 补全INSERT逻辑或确认合并 |
| creators | KOS | 0 | 创作者表，空表，仅data_center_api.py+scripts引用，无INSERT，KOS主体可能已由kos_profiles覆盖，需确认合并 | 补全INSERT逻辑或确认合并 |
| token_stat | AI | 0 | Token统计，空表，仅ark_llm.py引用，无INSERT，可能被ai_call_logs替代，需确认合并 | 补全INSERT逻辑或确认合并 |

### 4.2 可能重复/需合并 (5张)

| 表名 | 可能被替代为 | 行数 | 建议 |
|------|-------------|------|------|
| collection_runs | collection_logs | 0 | 确认职责边界，合并或明确区分 |
| content_analysis | content_evaluation | 0 | 确认职责边界，合并或明确区分 |
| platform_accounts | 各平台adapter表/v4_workspace_keys | 0 | 确认职责边界，合并或明确区分 |
| platform_comments | 各平台adapter评论表 | 0 | 确认职责边界，合并或明确区分 |
| platform_evidence | browser_evidence/app_evidence_records | 0 | 确认职责边界，合并或明确区分 |

### 4.3 无Adapter实现的平台表 (15张)

| 平台 | 表数 | 表名 | 建议 |
|------|------|------|------|
| B站 | 3 | bilibili_comments, bilibili_users, bilibili_videos | 实现adapter或清理schema |
| 抖音 | 3 | douyin_comments, douyin_users, douyin_videos | 实现adapter或清理schema |
| Instagram | 3 | instagram_comments, instagram_media, instagram_users | 实现adapter或清理schema |
| X(Twitter) | 2 | x_posts, x_users | 实现adapter或清理schema |
| 知乎 | 4 | zhihu_answers, zhihu_articles, zhihu_comments, zhihu_questions | 实现adapter或清理schema |

## 5. DEPRECATE 详细清单 (3 张)

| 表名 | 行数 | 被替代为 | 说明 |
|------|------|---------|------|
| xhs_note_comments | 0 | note_comments | 遗留小红书评论表，空表，已被note_comments替代，仅注册表引用 |
| xhs_notes | 0 | notes | 遗留小红书笔记表，空表，schema与notes不同(无id主键/列名不同)，已被notes表替代，仅注册表引用，保留用于历史追溯 |
| xhs_users | 0 | notes(内嵌) | 遗留小红书用户表，空表，用户信息已嵌入notes表，仅注册表引用 |

> DEPRECATE 表保留历史数据，不执行删除。xhs_* 系列为早期小红书采集schema，列结构与当前 notes 表不同。

## 6. DELETE-CANDIDATE 详细清单 (0 张)

**本次审计未发现符合严格 DELETE-CANDIDATE 标准的表。**

所有 128 张表均至少在注册表/适配器代码中有引用。最接近删除候选的是 MIGRATE 分类中
无 adapter 实现的平台表（B站/抖音/Instagram/X/知乎共15张），但它们属于 AGENTS.md
第8节定义的多平台 Adapter 架构规划范围，建议先实现或确认放弃后再决定删除。

> **重要: DELETE-CANDIDATE 仅记录为删除候选，不执行删除。任何删除操作需用户明确授权。**

## 7. 关键发现

### 发现1: 表数量与用户口径差异 (128 vs 129)
- 实际查询 `sqlite_master` 得到 **128 张表 + 0 个视图**
- 用户口径为 129 表 (64非空+65空)，实际为 128 表 (63非空+65空)
- 差异1张可能来自历史计数包含已删除表或视图，需核对 `schema_version` 迁移记录

### 发现2: 空表占比50.8%，但多数有明确用途
- 65张空表中: 17张有活跃INSERT逻辑(功能就绪待数据), 18张为未来平台adapter, 26张需MIGRATE评估, 3张为DEPRECATE遗留
- 无任何表完全符合"无代码引用+无数据+无业务用途"的删除标准

### 发现3: 存在多组疑似重复表，需合并梳理
- `collection_runs` vs `collection_logs` (采集运行记录)
- `content_analysis` vs `content_evaluation` (内容分析/评估)
- `collector_quality_log` vs `collection_quality_log` (命名极易混淆，实际为不同用途)
- `platform_accounts/comments/evidence` 通用表 vs 各平台adapter专用表 (职责重叠)
- `token_stat` vs `ai_call_logs` (Token用量统计)

### 发现4: xhs_* 遗留表与 notes 表 schema 不兼容
- `xhs_notes` 无 `id` 主键，列名风格不同 (liked_count vs likes, collected_count vs collects)
- 已被 `notes` 表完全替代，仅在 `data_center_api.py` 和 `platform_naming.py` 注册表中残留
- 建议标记 DEPRECATE 后保留，待确认无历史数据依赖后可迁移删除

### 发现5: 多平台Adapter架构已规划但实现不均衡
- 已实现adapter: Reddit, TikTok, YouTube, LinkedIn, GitHub, Channels (6个平台)
- 仅有schema无adapter: B站, 抖音, Instagram, X, 知乎 (5个平台15张表)
- AGENTS.md第8节明确多平台Adapter为Core架构方向，建议优先实现或清理未实现平台

## 8. UNKNOWN / PARTIAL 标注

| 表名 | 状态 | 说明 |
|------|------|------|
| (全部128表) | PARTIAL | 表数量与用户口径129差1，需核对是否存在遗漏表或视图 |
| brands | PARTIAL | 20个引用但无INSERT/FROM/UPDATE，引用多为文档和架构描述，实际生产写入路径待确认 |
| podcast_ai_runs | PARTIAL | 仅在intelligence_library文档中引用，无.py实现代码，功能状态不明 |

## 9. 下一步建议

1. **核对表数量差异**: 检查 `schema_version` 表迁移历史，确认129 vs 128差异来源
2. **MIGRATE表专项评估**: 对27张MIGRATE表逐一确认是"补全实现"还是"合并删除"
3. **重复表合并**: 优先处理 `collection_runs`/`content_analysis`/`token_stat` 等疑似重复表
4. **DEPRECATE表清理计划**: xhs_* 三张表确认无依赖后制定删除迁移脚本
5. **未实现平台决策**: B站/抖音/Instagram/X/知乎 15张表，决定是实现adapter还是清理schema
