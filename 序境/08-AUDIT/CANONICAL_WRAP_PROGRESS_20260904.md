# Canonical 统一管线 WRAP 进度矩阵（2026-09-04 起）

口径基线（Q1 方案甲，永久）：high 只计 risk_level=='high'，critical 独立不并入；情感三值精确、其余 unknown；FN-ENGAGEMENT=likes+comments+collects+shares 等权四字段；业务加权/两字段/差额法属不同 Metric，保留不强换。

## 已 WRAP（统一到 canonical_metrics 唯一计算层）
| # | 文件 / 位置 | 收敛的指标 | 明确保留（不同口径，勿强换） | 验证 | 状态 | Commit |
|---|---|---|---|---|---|---|
| 01 | app.py `/api/dashboard/all` | 情感/风险/等权互动（6 SQL→1 趟） | 输出 JSON 键结构零变化 | 回归+test_client+生产HTTP+浏览器 | PRODUCTION-VERIFIED | ed41265 |
| 02 | daily_report.py 三处 | risk_index/health/摘要纯分桶 | comments×2 加权传播分、赞+评两字段、比率分母 total=len | oracle(50.5/64.0)+40 回归 | PRODUCTION-VERIFIED | 3d60a29 |
| 03 | report_center/report_generator `_calculate_stats` | 五计数；**消除 high+critical 分叉** | comments×2 加权、百分比分母、复用 daily_report | oracle+30 回归 | PRODUCTION-VERIFIED | 451644e |
| 04 | export_report.py `generate_report_data` | 情感三计数+high | pending_neg 复合、负面优先排序、比率分母 | oracle+真实周/月/年 summary | PRODUCTION-VERIFIED | dd1dd69 |
| 05 | intelligence.py `summarize_event` 兜底 | neg/high | analyze_sentiment AI 链路、sample 不动 | oracle+14 回归 | PRODUCTION-VERIFIED | 2aa5e0b |
| 06 | reprocess.py `aggregate_events`（红线内） | 仅 neg 计数 | risk_score 阈值→risk_level 规则一字不动 | 29 测试+event_curation 脚本 | PRODUCTION-VERIFIED | 5e48944 |
| 07 | report_export/report_engine.py `payload` | 六桶（6 次 cnt→一次） | cnt 通用兜底、二次确认、发布日期过滤 | 四周期六桶全等 | PRODUCTION-VERIFIED | 5e48944 |
| 08 | app.py 三处：`/api/report/v2`、品牌详情、`/api/report/daily` | 情感三桶+high | v2 的 negative_count 取二次确认集合、品牌 neutral=total-pos-neg 差额法、daily 的 high 在负面子集计 | 表达式等价+34 回归+生产三路由 HTTP(stats 正常) | PRODUCTION-VERIFIED | c195c05 |
| 09 | kos_attribution.py 两处 | 等权四字段聚合/per_field/单条（FN-ENGAGEMENT） | 时间衰减权重、reach_score、KOS 业务评分不动 | Top5 真实 KOS 等价(9895/6397/3343/10272/543)+70 KOS 测试 | PRODUCTION-VERIFIED(待重载) | 本次 |
| — | brand_stats_recompute.py | 巡检已先行 WRAP（含 Canonical==旧口径前置断言） | — | 复核一致 | 已完成（巡检） | 巡检 |

## 审计后判定 KEEP（不是漏做，是无需/不应改）
- **SQL CASE WHEN 趋势聚合**（app.py L2883/L3106/L4898/L4985，按 publish_date GROUP BY）：等值口径已与 Canonical 精确一致（='negative'、='high'，high 不含 critical）；改内存聚合反而降性能，KEEP。
- **风险关注列表筛选** `risk_level in ('high','critical')`（app.py L1555/L4175/L4178）：这是"待关注风险笔记集合"宁不漏，非 high 分桶计数，语义不同，KEEP。
- **根 report_engine.py**（112 行薄编排）：自身不计数，统计全部转发 daily_report（已 WRAP-02），自动继承，KEEP。
- **event-graph 图谱模块**（event_graph.py，app.py L413-799 多端点）：关系图谱（event_graph_events/relations 表），通过 source_event_id 关联 events 表，**不重复计算情感/风险/互动计数**，属语义网络非计数层 → KEEP
- app.py L1415 趋势点单值、L2625-2627 负面二次确认复合计数、L3603-3609 品类循环/fallback：结构特殊或复合业务，单点收益低，暂 KEEP（如需统一走 group_count 另开小批）。

## 待 WRAP
- [x] 族 C KOS：kos_attribution.py 两处 Python 等权聚合已 WRAP-09 接入 FN-ENGAGEMENT（per_field/单条）；其余 SQL 等权/专属加权审计判定 KEEP，见下：
  - kol_analysis.py L62 `SUM(likes+comments+collects+shares)`：**SQL 层等权四字段，与 FN-ENGAGEMENT 数学等价**；SQL 聚合性能最优，改内存聚合降性能 → KEEP
  - kos_metrics.py L93 `SUM(n.likes+n.comments+n.collects+n.shares) AS exposure`：SQL 层等权，语义为 viewership 曝光（漏斗）→ KEEP（口径一致，非重复）
  - kos_engine.py L119 加权 `eng=tl+tc*2+tcol*1.5+ts*2`：不同 Metric（KOS 加权互动）→ KEEP；total_likes 为独立字段（FN-LIKES 语义）不并入互动 → KEEP
- [x] 多端点 Reference Scan（2026-09-04 完成，见 CANONICAL_CAPABILITY_AUDIT_20260904.md）：/api/brand-stats（业态维度）、/api/brand-industry/stats（行业维度，REFSCAN 已修复实体 id 计数）、/api/negative-review/stats（负面审核口径）——三者**不同业务语义，非重复计算** → 判定不强行统一；/api/brand-stats 内联等权 engagement 两处符合 FN-ENGAGEMENT 语义，遍历内联非独立函数，按"不重写已正确代码"暂 KEEP
- [x] 三套报告实现口径差异 Reference Scan（结论见下）

## 三套报告实现口径 Reference Scan（2026-09-04 已执行）
| 实现 | 取数/口径 | 关系 |
|---|---|---|
| export_report.py `generate_report_data` | 自有 notes 过滤 + canonical（WRAP-04） | 独立实现，已接入 canonical 计数 |
| 根 report_engine.py | 薄编排，统计全部转发 daily_report（WRAP-02） | 自动继承 canonical |
| report_export.report_engine.py `payload` | 六桶一次 canonical（WRAP-07），保留二次确认/发布日期过滤 | 独立实现，已接入 canonical |
三套计数均消费 canonical；差异仅在**过滤条件**（严格日期/二次确认），属业务口径而非算法分叉 → 判定同源已收敛，不改数字。

## AI Capability Registry（2026-09-04 智谱 glm-5.3 聚类分析）
- **传输入口已收敛**：全仓 13 处业务 AI 调用统一走唯一权威 `intelligence._chat/chat`（ai_gateway_v570 已废弃统一、scripts/ai_gateway.py 仅测试脚本），无第二套 AI Gateway → 已收敛 ✓
- **智谱聚类结论（三大模式，各调用点业务语义独立、已工作正确 → KEEP，不强行重构）**：
  - Cluster A 问答/对话：app.py:1800 通用对话、app.py:2472 诺米 RAG(检索优先/不编造)、ai_hub:142 数据限定QA、ai_resource_packs:235 按次执行
  - Cluster B 分析/评分/分类：app.py:2876 舆情情感风险、ai_filter:254 质量过滤、kos_engine:386 KOS评分、ai_hub:179 模块分析
  - Cluster C 摘要/生成：daily_report 355/649/668、kos_engine:549 回复、learning_collector:373
- **Pattern 1 Grounded QA（唯一值得关注的共享模式）**：app.py:2472 与 ai_hub:142 共享"仅据给定数据/不编造/检索优先"约束，但各自含特有模板（诺米处置建议模板、ai_hub 模块 hint），收敛收益低、风险中 → 登记 KEEP
- **参数域**：temperature 0.0~0.4（确定性任务≤0.0 正确）、max_tokens 300~3000（按任务），无高风险不一致 → 归一不作为本轮动作
- **待办（非本轮）**：高频确定性调用（ai_filter/daily_report 摘要分析）可评估改走 `chat(use_cache=True, pack_id='glm_4_5_air')` 拿分级+缓存收益；per_call 已用尽，glm_4_5_air token 包充足（1191万 token）时再启
- **Evidence**：调用点清单与智谱分析见本轮 AI 调用点扫描脚本与 `STABLECHANNEL_ZHIPU_20260904.md`

## 已知测试隔离缺陷（登记，不掩盖）
- `test_ai_channel_flag.py` 与 `test_ai_gateway.py` 同进程共跑会失败：`config.py` 的 `load_dotenv(ENV_FILE, override=True)` 在测试共享进程强灌真实 .env 到 os.environ，破坏 flag 测试对"未配置 Key"场景的模拟。**既有缺陷，非本轮引入**；单跑各自全过。修法需动 config override 行为或给 flag 测试加 autouse 清 Key fixture（影响面较大），暂登记 Backlog，不强行改。

## Cross-Surface 一致性目标
同一(时间/维度/过滤/权限)：首页=表=图=日报/周报/报告=导出=AI 答询，数字必须一致；差异回溯 Function/Metric/Dataset，禁止改展示层凑齐。
