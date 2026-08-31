# ZBC-UPA-001 Phase 1 盘点总册

> **TASK ID**: ZBC-UPA-001  
> **阶段**: Phase 1 - INVENTORY（盘点阶段，禁止修改代码）  
> **基线**: commit 40073df (v5.8.9)  
> **生成时间**: 2026-08-31  
> **原则**: 先盘点不修改、先运行不猜测、先证据后修改

---

## 一、ARCHITECTURE-MAP（架构地图）

### 1.1 仓库基本信息

| 指标 | 数值 |
|------|------|
| 业务Python文件 | 400 个 |
| 业务JS文件 | 238 个（static/js 21个核心） |
| 业务CSS文件 | 26 个（static/css 21个核心） |
| HTML模板 | 56 个 |
| MD文档 | 1369 个 |
| 主入口 | app.py (250.9 KB) |
| 生产入口 | run_supervised.py (7.6 KB) |

### 1.2 根目录核心模块分层

#### 核心业务层 (Core)
| 模块 | 大小 | 职责 |
|------|------|------|
| app.py | 250.9 KB | Flask主应用，191个路由 |
| database.py | 60.5 KB | 数据库操作层 |
| models.py | 9.8 KB | 数据模型 |
| config.py | 10.6 KB | 配置管理 |
| risk_engine.py | 0.4 KB | 风险引擎（极简，可能是占位） |
| event_graph.py | 19.4 KB | 事件关系图谱 |
| subject_classifier.py | 14.5 KB | 传播主体分类器 |
| monitoring.py | 19.3 KB | 舆情监测核心 |
| collector.py | 15.1 KB | 采集器基础 |
| ai_analyzer.py | 33.6 KB | AI分析引擎 |

#### 采集层 (Collectors)
| 模块 | 大小 | 职责 |
|------|------|------|
| topic_campaign.py | 61.3 KB | 话题采集 campaign（固定时间调度，待收口到Dynamic Scheduler） |
| xhs_cdp_collector.py | 12.4 KB | 小红书CDP采集器 |
| xhs_cookie_bridge.py | 29.7 KB | 小红书Cookie桥接（7层账号安全防护） |
| cdp_helper.py | 19.3 KB | CDP辅助工具 |
| collector_automation.py | 26.7 KB | 采集自动化 |
| wechat_notifier.py | 36.8 KB | 微信通知 |

#### 系统管理层 (System)
| 模块 | 大小 | 职责 |
|------|------|------|
| system_health_api.py | 19.9 KB | 系统健康API |
| system_watchdog.py | 11.5 KB | 系统看门狗 |
| system_guardian.py | 7.1 KB | 系统守护 |
| auto_recovery.py | 16.8 KB | 自动恢复 |
| stability_monitor.py | 18.0 KB | 稳定性监控 |
| security_scanner.py | 14.2 KB | 安全扫描 |
| auth_recovery_center.py | 12.9 KB | 认证恢复中心 |

#### AI/知识层 (AI & Knowledge)
| 模块 | 大小 | 职责 |
|------|------|------|
| ai_learning_engine.py | 18.0 KB | AI学习引擎（影子板块） |
| ai_filter.py | 12.9 KB | AI过滤器 |
| ai_gateway_v570.py | 8.1 KB | AI网关v570 |
| ark_llm.py | 12.6 KB | 字节方舟LLM |
| brand_knowledge_base.py | 7.9 KB | 品牌知识库 |
| case_deep_analysis.py | 13.8 KB | 案例深度拆解 |
| brand_report_generator.py | 12.3 KB | 品牌报告生成器 |
| local_ai_client.py | 7.7 KB | 本地AI客户端 |

#### 报告/导出层 (Reports)
| 模块 | 大小 | 职责 |
|------|------|------|
| export_report.py | 35.5 KB | 报告导出 |
| daily_report.py | 25.9 KB | 日报生成 |
| public_opinion_cases.py | 24.6 KB | 舆情案例库 |
| pr_case_integration.py | 24.4 KB | 公关案例整合 |
| evaluation_system.py | 18.6 KB | 评估系统 |

### 1.3 子目录结构

| 目录 | 职责 |
|------|------|
| static/ | 前端静态资源（css/js/images） |
| templates/ | Jinja2 HTML模板 |
| tests/ | 测试文件（113个正式测试 + _archive归档） |
| docs/ | 文档（governance治理文档、reference参考） |
| scripts/ | 工具脚本 |
| platform_adapters/ | 平台适配器（XHS/Web等） |
| collector_v2/ | 采集器v2版本 |
| collector_guard/ | 采集守护 |
| config/ | 配置文件 |
| deployment/ | 部署相关 |
| docker/ | Docker配置 |
| staging/ | Staging环境 |
| report_export/ | 报告导出 |
| proxy_pool/ | 代理池 |
| tools/ | 工具 |
| v4_upgrade/ | v4升级相关 |

---

## 二、DEPENDENCY-MATRIX（依赖矩阵）

### 2.1 requirements.txt 全量清单（17个包）

| 包 | 版本要求 | 分类 | 实际引用 | 状态 |
|----|----------|------|----------|------|
| Flask | >=2.0.0 | CORE | app.py等 | ✅ 核心 |
| Werkzeug | >=2.0.0 | CORE | Flask依赖 | ✅ 核心 |
| pandas | >=1.3.0 | CORE | 1处引用 | ✅ 在用 |
| openpyxl | >=3.0.0 | OPTIONAL | Excel导出 | ✅ 在用 |
| xlsxwriter | >=3.0.0 | OPTIONAL | 0引用 | ⚠️ 移除候选 |
| python-docx | >=0.8.11 | OPTIONAL | Word导出 | ✅ 在用 |
| reportlab | >=3.6.0 | OPTIONAL | 3处引用 | ✅ 在用 |
| playwright | >=1.30.0 | BROWSER | 33处引用 | ✅ 主要浏览器 |
| selenium | >=4.0.0 | BROWSER | 0引用 | ⚠️ 移除候选 |
| psutil | >=5.9.0 | CORE | 6处引用 | ✅ 在用 |
| requests | >=2.28.0 | CORE | HTTP客户端 | ✅ 核心 |
| httpx | >=0.24.0 | OPTIONAL | 0引用 | ⚠️ 移除候选 |
| python-dotenv | >=0.21.0 | CORE | 环境变量 | ✅ 核心 |
| colorama | >=0.4.6 | OPTIONAL | 0引用 | ⚠️ 移除候选 |
| tqdm | >=4.64.0 | OPTIONAL | 0引用 | ⚠️ 移除候选 |

### 2.2 依赖分类汇总

| 分类 | 数量 | 包 |
|------|------|-----|
| **CORE（核心）** | 6 | Flask, Werkzeug, pandas, psutil, requests, python-dotenv |
| **OPTIONAL（可选）** | 4 | openpyxl, python-docx, reportlab, xlsxwriter |
| **BROWSER（浏览器）** | 2 | playwright, selenium |
| **UNUSED（0引用移除候选）** | 5 | selenium, httpx, xlsxwriter, colorama, tqdm |

### 2.3 移除候选说明

> **注意**: 本轮只登记，不删除。需在Staging环境验证后，经回归测试确认无影响，再执行删除。

| 包 | 移除理由 | 风险 |
|----|----------|------|
| selenium | 全项目0 import，Playwright 33处在用 | 低（需确认无动态import） |
| httpx | 0引用，requests已覆盖HTTP需求 | 低 |
| xlsxwriter | 0引用，openpyxl已覆盖Excel导出 | 低 |
| colorama | 0引用，Windows终端颜色非必需 | 极低 |
| tqdm | 0引用，进度条非生产必需 | 极低 |

---

## 三、MODULE-MATRIX（模块矩阵）

### 3.1 模块分类

| 分类 | 数量 | 说明 |
|------|------|------|
| **ACTIVE（活跃）** | ~60 | 核心业务、采集、AI、系统管理 |
| **STABLE（稳定）** | ~20 | 报告导出、工具类、配置 |
| **LEGACY（遗留）** | ~10 | 旧版本模块（v3/v4升级残留） |
| **DEPRECATED（已废弃）** | 1 | app_refactor_blueprint.py（16路由零注册） |
| **EXPERIMENTAL（实验）** | ~5 | AI影子板块、本地AI客户端 |
| **DUPLICATE（重复）** | 待确认 | 多套设计系统CSS、多版本采集器 |
| **UNUSED（无用）** | 待确认 | check_*.py一次性诊断脚本（约15个） |

### 3.2 已确认的死代码

| 模块 | 大小 | 问题 | 建议 |
|------|------|------|------|
| app_refactor_blueprint.py | 8.8 KB | 16个路由零注册，从未被app.py引用 | 标记DEPRECATED，回归后删除 |
| check_collection.py | 1.5 KB | 一次性诊断脚本 | 归档到tests/_archive |
| check_collection_detail.py | 2.1 KB | 一次性诊断脚本 | 归档 |
| check_db_dates.py | 1.9 KB | 一次性诊断脚本 | 归档 |
| check_empty_tables.py | 0.6 KB | 一次性诊断脚本 | 归档 |
| check_logs.py | 1.4 KB | 一次性诊断脚本 | 归档 |
| check_system.py | 1.2 KB | 一次性诊断脚本 | 归档 |
| check_warnings.py | 1.6 KB | 一次性诊断脚本 | 归档 |
| _reanalyze.py | 2.0 KB | 临时脚本 | 归档 |
| quick_check.py | 1.6 KB | 临时脚本 | 归档 |
| read_docx.py | 1.4 KB | 临时工具 | 归档 |

### 3.3 重复实现识别

| 功能 | 实现1 | 实现2 | 实现3 | 建议 |
|------|-------|-------|-------|------|
| 设计系统 | tokens.css+components.css+layout.css | design-v8.css | design-v9-gpt-codex.css | 三套并存，需收敛到zb-theme.css |
| 极简设计 | tokens-minimal.css+components-minimal.css+layout-minimal.css | - | - | 第四套，需整合 |
| 采集器 | collector.py | collector_v2/ | xhs_cdp_collector.py | 多版本，需明确主路径 |
| AI网关 | ai_analyzer.py | ai_gateway_v570.py | ark_llm.py | 多Provider，需统一AIProvider接口 |
| 系统监控 | system_watchdog.py | system_guardian.py | stability_monitor.py | 功能重叠，需合并 |

---

## 四、ROUTE-MATRIX（路由矩阵）

### 4.1 路由总览

| 指标 | 数值 |
|------|------|
| 总路由数 | 191 |
| API端点 | 187 |
| 页面路由 | 4（/、/favicon.ico、/healthz、/remote） |
| 架构 | SPA单页应用（前端JS客户端路由） |

### 4.2 API分组统计

| 分组 | 数量 | 说明 |
|------|------|------|
| /api/ai* | ~15 | AI分析、AI过滤、AI学习、AI网关、Ark LLM |
| /api/cases* | ~10 | 案例库、案例深度拆解 |
| /api/brand* | ~12 | 品牌业态、品牌知识库、品牌报告、品牌统计 |
| /api/alerts* | 3 | 风险预警 |
| /api/events* | ~5 | 事件中心、事件图谱 |
| /api/cache* | 4 | 缓存管理 |
| /api/bilibili* | 3 | B站采集 |
| /api/subject* | ~3 | 传播主体分类 |
| /api/backup* | 1 | 数据备份 |
| /api/monitor* | ~5 | 舆情监测 |
| /api/notes* | ~5 | 笔记管理 |
| /api/reports* | ~5 | 报告中心 |
| /api/system* | ~8 | 系统管理、健康检查 |
| /api/auth* | ~5 | 认证、恢复 |
| /api/app-evidence* | ~3 | App证据（影子模式） |
| /api/knowledge* | ~3 | 知识库 |
| /api/topic* | ~5 | 话题采集 |
| 其他 | ~50 | 杂项API |

### 4.3 关键API端点（示例）

```
/api/ai/analyze              - AI分析
/api/ai/chat                 - AI对话
/api/ai/providers            - AI Provider列表
/api/alerts                  - 风险预警列表
/api/alerts/refresh          - 刷新预警
/api/brand-report/generate   - 生成品牌报告
/api/case-analysis/list      - 案例拆解列表
/api/case-analysis/search    - 案例搜索
/api/brand-knowledge/search  - 知识库搜索
/api/event-graph/events      - 事件图谱事件
/api/subject-classifier/types - 主体分类器类型
/api/app-evidence/upload     - App证据上传（影子模式）
/api/system/health           - 系统健康
/healthz                     - 健康检查（生产用）
```

### 4.4 路由问题识别

| 问题 | 说明 | 建议 |
|------|------|------|
| 无版本前缀 | 所有API都是/api/xxx，无/v1/ | 未来新增API统一用/api/v1/，旧API保持兼容 |
| 重复路由 | /api/brands出现2次（GET/POST） | 正常，不同HTTP方法 |
| 未注册路由 | app_refactor_blueprint.py中16个路由零注册 | 死代码，删除 |
| 命名不统一 | 有的用kebab-case（/api/brand-report），有的用snake_case | 逐步统一为kebab-case |

---

## 五、DATABASE-MATRIX（数据库矩阵）

### 5.1 数据库总览

| 指标 | 数值 |
|------|------|
| 主数据库 | data/monitor.db (6.29 MB) |
| 表数量 | 51 张 |
| 索引数量 | 50 个 |
| Staging数据库 | staging/monitor.staging.db (6.3 MB) |
| 备份数据库 | data/backups/ + data/cache/ (约10个) |

### 5.2 核心业务表

| 表名 | 行数 | 列数 | 职责 |
|------|------|------|------|
| notes | 957 | 65 | 舆情笔记主表 |
| note_review_history | 8327 | 11 | 笔记审核历史 |
| events | 427 | 22 | 舆情事件 |
| collection_logs | 477 | 7 | 采集日志 |
| ai_filter_log | 827 | 9 | AI过滤日志 |
| topic_campaign_snapshots | 325 | 12 | 话题采集快照 |
| event_mentions | 562 | 6 | 事件提及关联 |
| note_comments | 141 | 11 | 笔记评论 |
| brand_industry_monitor | 198 | 12 | 品牌业态监测 |
| brand_knowledge | 103 | 11 | 品牌知识库 |
| daily_reports | 25 | 29 | 日报 |
| topic_campaign_notes | 120 | 24 | 话题采集笔记 |
| case_deep_analysis | 20 | 22 | 案例深度拆解 |
| event_graph_events | 16 | 12 | 事件图谱事件 |
| web_mentions | 79 | 24 | Web提及 |
| web_topics | 96 | 11 | Web话题 |
| weekly_events | 30 | 17 | 周度事件 |
| swire_events | 10 | 12 | 太古汇事件 |
| schedule_decisions | 51 | 22 | 调度决策 |
| v4_audit_logs | 33 | 9 | 审计日志 |
| v4_sessions | 27 | 7 | 用户会话 |
| v4_login_attempts | 26 | 5 | 登录尝试 |
| collector_quality_log | 7 | 9 | 采集质量日志 |
| comments | 2 | 14 | 评论（旧表，可能被note_comments替代） |
| app_evidence_records | 0 | 16 | App证据记录（新表，影子模式） |

### 5.3 系统/安全表

| 表名 | 行数 | 职责 |
|------|------|------|
| v4_users | 1 | 用户表 |
| v4_security_questions | 2 | 安全问题 |
| system_config | 10 | 系统配置 |
| schema_version | 7 | 数据库版本 |
| token_stat | 1 | Token使用统计 |
| collection_counters | 1 | 采集计数器 |
| notification_config | 0 | 通知配置 |
| notification_logs | 3 | 通知日志 |

### 5.4 数据库问题识别

| 问题 | 说明 | 建议 |
|------|------|------|
| 表命名不统一 | 有的用snake_case（note_review_history），有的用前缀（v4_users、swire_events） | 逐步统一，v4_前缀可去除 |
| 重复表 | comments (2行) vs note_comments (141行) | 确认comments是否为旧表，迁移后删除 |
| 空表 | app_evidence_records、notification_config、review_*等 | 新功能表，正常 |
| 无外键约束 | 所有表无外键，靠应用层维护关系 | 暂不修改，SQLite外键支持有限 |
| 备份过多 | data/backups/和data/cache/有约10个备份数据库 | 建立备份清理策略，保留最近5个 |

---

## 六、UI-MATRIX（UI矩阵）

### 6.1 CSS文件清单（static/css，21个核心文件，约460KB）

| 文件 | 大小 | 类型 | 状态 |
|------|------|------|------|
| style.css | 79.8 KB | 旧主样式 | ⚠️ 遗留，需收敛 |
| ui_modern.css | 36.1 KB | 旧现代UI | ⚠️ 遗留 |
| ui_dashboard.css | 31.7 KB | 旧仪表盘 | ⚠️ 遗留 |
| components.css | 31.6 KB | 设计系统v1组件 | 🔄 第一套 |
| zb-theme.css | 29.9 KB | 最终主题覆盖层 | ✅ 权威主题 |
| design-v9-gpt-codex.css | 29.7 KB | v9 GPT/Codex风格 | 🔄 第三套 |
| design-v8.css | 26.2 KB | v8设计 | ⚠️ 遗留 |
| layout-minimal.css | 26.1 KB | 极简布局 | 🔄 第四套 |
| apple-ui.css | 25.8 KB | 苹果风格 | ⚠️ 遗留 |
| layout.css | 22.8 KB | 设计系统v1布局 | 🔄 第一套 |
| components-minimal.css | 20.6 KB | 极简组件 | 🔄 第四套 |
| compat.css | 15.4 KB | 兼容性 | ✅ 保留 |
| tokens.css | 15.0 KB | 设计系统v1令牌 | 🔄 第一套 |
| ui_optimized.css | 13.7 KB | 优化UI | ⚠️ 遗留 |
| case_deep_analysis.css | 12.1 KB | 案例拆解页 | ✅ 页面专用 |
| architecture_dashboard.css | 11.3 KB | 架构仪表盘 | ✅ 页面专用 |
| v3_modules.css | 9.4 KB | v3模块 | ⚠️ 遗留 |
| mobile.css | 8.6 KB | 移动端 | ✅ 响应式 |
| tokens-minimal.css | 7.7 KB | 极简令牌 | 🔄 第四套 |
| zachary_robot.css | 6.7 KB | 3D机器人 | ⚠️ 待评估 |
| nomi_global_drag.css | 0.9 KB | 全局拖拽 | ✅ 保留 |

### 6.2 CSS加载顺序（index.html，17个CSS）

```
1. tokens.css?v=1.0.0              - 设计系统v1令牌
2. components.css?v=1.0.0          - 设计系统v1组件
3. layout.css?v=1.0.0              - 设计系统v1布局
4. style.css?v=8.0.0               - 旧主样式（最大，79.8KB）
5. nomi_global_drag.css?v=8.0.0    - 全局拖拽
6. architecture_dashboard.css?v=8.0.0 - 架构仪表盘
7. ui_optimized.css?v=8.0.0        - 优化UI
8. mobile.css?v=8.0.0              - 移动端
9. case_deep_analysis.css?v=8.0.0  - 案例拆解
10. v3_modules.css?v=8.0.0         - v3模块
11. design-v8.css?v=8.0.0          - v8设计
12. design-v9-gpt-codex.css?v=9.0.0 - v9 GPT/Codex
13. tokens-minimal.css?v=2.0.0      - 极简令牌
14. components-minimal.css?v=2.0.0  - 极简组件
15. layout-minimal.css?v=2.0.0      - 极简布局
16. zb-theme.css?v=5.9.9            - 最终主题覆盖层（最后加载，权威）
```

### 6.3 CSS层级污染分析

**问题：四套设计系统并存，严重层级污染**

| 套系 | 文件 | 大小 | 说明 |
|------|------|------|------|
| 第一套 | tokens.css + components.css + layout.css | 69.4 KB | 通用设计系统v1 |
| 第二套 | design-v8.css | 26.2 KB | v8设计 |
| 第三套 | design-v9-gpt-codex.css | 29.7 KB | v9 GPT/Codex风格 |
| 第四套 | tokens-minimal.css + components-minimal.css + layout-minimal.css | 54.4 KB | 极简侘寂风格 |
| 旧样式 | style.css + ui_modern.css + ui_dashboard.css + apple-ui.css + ui_optimized.css + v3_modules.css | 193.7 KB | 历史遗留 |
| 权威层 | zb-theme.css | 29.9 KB | 最终覆盖层 |

**总CSS体积：约460KB，其中约60%是重复/遗留样式**

### 6.4 JS文件清单（static/js，21个核心文件，约550KB）

| 文件 | 大小 | 职责 |
|------|------|------|
| app.js | 112.8 KB | 主应用JS（核心） |
| frontend_enhancement.js | 54.1 KB | 前端增强 |
| ui_interactions_v5.8.0.js | 39.6 KB | UI交互v5.8 |
| zachary_robot.js | 34.9 KB | 3D机器人 |
| system_controls.js | 29.7 KB | 系统控制 |
| zachary_robot_enhanced.js | 28.4 KB | 3D机器人增强 |
| architecture_dashboard.js | 24.6 KB | 架构仪表盘 |
| app_evidence.js | 20.9 KB | App证据（影子模式） |
| v3_modules.js | 19.7 KB | v3模块 |
| case_deep_analysis.js | 17.6 KB | 案例拆解 |
| system_features_ui.js | 17.1 KB | 系统功能UI |
| swire_group.js | 16.8 KB | 太古汇集团 |
| design-v9-interactions.js | 13.6 KB | v9交互（命令面板等） |
| zachary_system_knowledge.js | 12.3 KB | 系统知识 |
| pr_case_integration.js | 10.7 KB | 公关案例整合 |
| badge_manager.js | 8.7 KB | 徽章管理 |
| zachary_3d.js | 7.8 KB | 3D效果 |
| auxiliary_sources.js | 3.8 KB | 辅助来源 |
| nomi_global_drag.js | 3.7 KB | 全局拖拽 |
| zachary_png_face.js | 2.0 KB | PNG头像 |
| app.js.bak_20260827_201308 | 140.1 KB | 备份（应删除） |

### 6.5 UI问题汇总

| 问题 | 严重程度 | 说明 |
|------|----------|------|
| CSS层级污染 | 🔴 高 | 四套设计系统并存，17个CSS依次加载，互相覆盖 |
| JS体积过大 | 🟡 中 | 21个JS约550KB，app.js单文件112KB |
| 3D机器人装饰 | 🟡 中 | zachary_robot相关3个JS约66KB，CSS 6.7KB，用户要求极简 |
| 备份文件入库 | 🟡 中 | app.js.bak_140KB、style.css.bak_74KB应删除 |
| 响应式断点混乱 | 🟡 中 | 多套CSS各自定义断点，不统一 |
| 无设计令牌统一 | 🔴 高 | 颜色/间距/字体硬编码在各CSS中，无统一tokens |
| 右侧AI面板显示异常 | 🟡 中 | HTML存在但部分页面不显示，需排查 |
| 移动端适配不完整 | 🟡 中 | mobile.css存在但与主CSS冲突 |

---

## 七、CLEANUP-MATRIX（清理矩阵）

### 7.1 重复实现

| 类型 | 重复项 | 数量 | 建议 |
|------|--------|------|------|
| CSS设计系统 | 4套并存（v1/v8/v9/minimal） | 4套 | 收敛到zb-theme.css单一权威层 |
| 采集器 | collector.py / collector_v2/ / xhs_cdp_collector.py | 3套 | 明确主路径，旧版标记DEPRECATED |
| AI网关 | ai_analyzer.py / ai_gateway_v570.py / ark_llm.py | 3套 | 统一AIProvider接口 |
| 系统监控 | system_watchdog.py / system_guardian.py / stability_monitor.py | 3套 | 功能重叠，合并 |
| 评论表 | comments / note_comments | 2张 | 确认旧表，迁移后删除 |

### 7.2 无用代码

| 类型 | 数量 | 说明 |
|------|------|------|
| 一次性诊断脚本 | ~15个 | check_*.py、quick_check.py等 |
| 死代码模块 | 1个 | app_refactor_blueprint.py（16路由零注册） |
| 0引用依赖 | 5个 | selenium/httpx/xlsxwriter/colorama/tqdm |
| 备份文件 | 2个 | app.js.bak_140KB、style.css.bak_74KB |

### 7.3 临时文件

| 类型 | 位置 | 说明 |
|------|------|------|
| 抽帧图片 | _ref_frames/ | 视频分析抽帧，已归档移除 |
| 截图 | _shots/ | 测试截图，应加入.gitignore |
| 临时脚本 | _u/ | 不明目录，需确认 |
| 参考截图 | ref_gpt_*.jpg | 本次UI优化参考，用完删除 |

### 7.4 清理优先级

| 优先级 | 项目 | 风险 | 预计收益 |
|--------|------|------|----------|
| P0 | 删除备份文件（.bak） | 极低 | 减少214KB |
| P0 | 归档一次性诊断脚本 | 低 | 减少约20KB，清晰目录 |
| P1 | CSS设计系统收敛 | 中 | 减少约200KB，解决层级污染 |
| P1 | 删除0引用依赖 | 低 | 减少安装体积，需Staging验证 |
| P2 | 采集器版本统一 | 中 | 明确主路径，减少混淆 |
| P2 | AI网关统一 | 中 | 统一Provider接口 |
| P3 | 系统监控模块合并 | 中 | 减少功能重叠 |

---

## 八、敏感文件泄露审计

### 8.1 审计结果

| 检查项 | 结果 | 说明 |
|--------|------|------|
| .env文件被git跟踪 | ✅ 安全 | 只有.env.example被跟踪，.env和.env.txt未跟踪 |
| .db文件被git跟踪 | ✅ 安全 | 无.db文件被git跟踪 |
| 明文凭据（cookie/token） | ✅ 安全 | 代码中未发现硬编码的明文凭据 |
| browser profile被跟踪 | ✅ 安全 | chrome-cdp-profile/edge-cdp-profile等未被跟踪 |
| .gitignore覆盖 | ✅ 良好 | 136行，覆盖.env/.db/logs/node_modules等 |
| .trae-cn IDE数据 | ✅ 安全 | 6.7万行IDE数据未被跟踪，trae-jwt-token未提交 |

### 8.2 需关注的文件

| 文件 | 大小 | 状态 | 建议 |
|------|------|------|------|
| .env | - | 未跟踪 | 生产配置，保持未跟踪 |
| .env.txt | - | 未跟踪 | 文本版配置，确认是否必要 |
| data/monitor.db | 6.3MB | 未跟踪 | 主数据库，保持未跟踪 |
| staging/monitor.staging.db | 6.3MB | 未跟踪 | Staging数据库，保持未跟踪 |
| data/backups/*.db | ~10个 | 未跟踪 | 备份，建立清理策略 |

---

## 九、Phase 1 总结与下一步

### 9.1 盘点结论

1. **架构现状**: Flask + SQLite + Playwright/Selenium 单页应用架构，400个Python文件，191个API路由，51张数据库表
2. **主要问题**: CSS层级污染（四套设计系统并存）、重复实现（采集器/AI网关/系统监控）、0引用依赖（5个包）、死代码（1个模块+15个脚本）
3. **安全基线**: 良好，无.env/.db/明文凭据被git跟踪
4. **生产状态**: 8201生产运行中（v5.9.9），8200待切换

### 9.2 关键发现

| 发现 | 影响 | 建议阶段 |
|------|------|----------|
| CSS四套并存，460KB中60%重复 | 页面加载慢、样式互相覆盖 | Phase 3 Consolidation |
| app.py单文件250KB，191个路由 | 维护困难、测试复杂 | Phase 6 分层重构 |
| topic_campaign.py固定时间调度 | 与Dynamic Scheduler冲突 | Phase 3 调度收口 |
| 5个0引用依赖 | 安装体积大、安全面广 | Phase 3 依赖收敛 |
| 右侧AI面板显示异常 | 用户体验问题 | Phase 3 UI修复 |
| App Evidence表已建但0行 | 影子模式待接入 | Phase 8 Adapter |

### 9.3 下一步（Phase 2 - Staging Runtime）

> **等待用户确认后启动**

- 建立ZBC-STAGING-RUNTIME（独立端口8301 + 独立DB + XHS_PRODUCTION=false）
- 零安装轻量方案（无需Docker），当天可跑
- 不影响本地生产系统及临时公网

### 9.4 本次盘点产出文件

| 文件 | 说明 |
|------|------|
| docs/governance/UPA-PHASE1-TASK-LEDGER.md | 施工台账 |
| docs/governance/UPA-PHASE1-INVENTORY.md | 本盘点总册 |
| _scan_routes.py | 路由扫描脚本（临时，可删除） |
| _scan_db.py | 数据库扫描脚本（临时，可删除） |
| _scan_main_db.py | 主数据库扫描脚本（临时，可删除） |

---

**盘点完成。全程未修改业务代码，未碰运行中的8201/9222，未碰数据库和采集。**
