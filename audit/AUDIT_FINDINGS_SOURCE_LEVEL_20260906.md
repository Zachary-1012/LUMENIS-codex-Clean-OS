# 源码级实际审计发现 2026-09-06（线上审计规范×本地源码实测）

> 方法：grep/读文件实测，非文档印象。基线本地 lumenis-dual-domain-v3 @1085104，线上审计规范来自两份docx(HEAD 0dca073)。

## VERIFIED（已符合）
1. KOS平台规则配置化：config/kos_platform_rules.json v1.0.0(2026-09-06)，小红书 engagement_weights(likes1.0/comments2.0/collects1.5/shares2.0)+influence公式系数全配置；kos_metrics.py:31/33/131 从配置加载，失败回退内置默认。
2. 采集调度门：app.py:3732/3796 自动采集固定00:00/12:00每窗口当日一次；platform_adapters/scheduling/policy.py:5/30/31 auto_slots=("00:00","12:00")默认关闭UI隐藏。
3. TopicCampaign独立配额：topic_campaign.py:84 CAMPAIGN_COLLECT_HOURS=[9,11,13,15,17,19]；:761独立daemon线程不依赖主scheduler；:642/768独立配额每日上限8次含手动、不占主舆情配额；错峰5分。合规。
4. PermissionGate接入：50文件463处匹配(app.py/security_boundary/permission_gate/ad_intelligence/account/lumenis_agg_api/tests等)。
5. 报告口径：report_engine.py:7/8 声明report_id/artifact_hash/generator_version/data_version；:282 generator_version="dual-domain-v2.0"；双域报告类型CTH6类/ZBMP6类。

## P1 缺口（实际发现，需修补）
G1. kos_attribution.py 未读平台配置(违反R14权重配置化)：
   - :78 demand_score=min(100, total_comments/500.0*100) 硬编码阈值500
   - :162 time_weight=0.5+(i/(len-1))*1.0 硬编码
   - :165 interactions直接求和，未按likes/comments/collects/shares平台权重
   修补：attribution改读config/kos_platform_rules.json的engagement_weights；demand阈值/time_weight系数移入配置；配置缺失显式告警+回退与配置一致的默认。
G2. ai_call_logger.py 审计字段缺项(线上要求14项)：
   现有：provider/model/prompt_version/input_hash/input_text/output/confidence/task_id/trace_id/timestamp/human_correction/latency_ms/token_usage/failure_reason/created_at
   缺：target_type/target_id/model_version/system_result/final_result/accepted(ai_run_id可用id)
   修补：ALTER TABLE ai_call_logs 向后兼容加列(DEFAULT空)，log_call()参数补可选字段，不破坏历史数据与现有调用；新调用逐步填充。
G3. kos_metrics配置回退静默：配置缺失/损坏时回退内置默认但需显式WARNING日志+状态标记，禁止静默用默认导致口径漂移。
G4. 报告artifact_hash真实落库确认：report_engine声明artifact_hash但需核实在daily_report.py/report_api.py生成时是否真实计算hash并写入daily_reports表；若仅声明未计算则补sha256(内容+数据快照)落库。

## 待续审（下一批）
- Legacy收敛入口：safety_boundary/system_guardian/compliance_gate/根risk_engine/web_monitor_v570 新代码是否都走新入口
- 风险口径：RISK_LEVELS 5档/SENTIMENT 4档在各报告与API是否一致，unknown是否被当负面
- 双时间分离：publish_datetime vs captured_at 在迁移后963笔记是否100%分离(团队进行中)
- 前后端契约：前端fetch与Flask路由对账(团队进行中)
