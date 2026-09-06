# ZBC/LUMENIS 新增资产八类验收报告 (New Asset Acceptance Report)

> 生成时间: 2026-09-07 00:36:52
> 检查器: scripts/audit_tools/new_asset_acceptance_check.py

## 1. 验收总览

| # | 资产类别 | 状态 | 回归测试数 | 备注 |
|---|----------|------|-----------|------|
| 1 | 963笔记 subject 重判 | PASS | 5 |  |
| 2 | 711智能资产 (intelligence_assets) | PASS | 5 |  |
| 3 | 双域账户 TOTP (v4_totp_secrets) | PASS | 3 |  |
| 4 | 八平台 Cookie (cookie_vault) | WARN | 2 | 检测到 10 处代码可能打印 cookie 内容 |
| 5 | 微信 Adapter (wechat_notifier/sogou_wechat) | PASS | 2 | .env 中未检测到微信相关凭证（可能未配置，运行时应为 BLOCKED） |
| 6 | KOS 配置化 (kos_attribution/kos_metrics) | PASS | 9 |  |
| 7 | 报告 artifact_hash (report_artifact) | PASS | 12 |  |
| 8 | OSAI EvidenceChain | PASS | 7 |  |

**汇总**: PASS=7, WARN=1, FAIL=0, 回归测试总数=45

## 2. 963笔记 subject 重判

**状态**: PASS

### 数据一致性检查

```json
{
  "total_notes": 963,
  "null_or_empty_subject_type": 0,
  "distribution": {
    "CTH": 645,
    "unknown": 312,
    "normal_user": 6
  }
}
```

### 来源追溯链

subject_type 由 subject_classifier.py / subject_rules.py 规则判定，rule_version 可追溯；重判脚本可重跑

### 可撤回机制

UPDATE notes SET subject_type=NULL 可回滚；重判为幂等操作，原始数据不删除

### 回归测试

相关测试文件数: 5

## 3. 711智能资产 (intelligence_assets)

**状态**: PASS

### 数据一致性检查

```json
{
  "total_assets": 711,
  "missing_source_origin": 0,
  "missing_evidence_level": 0,
  "missing_knowledge_status": 0,
  "missing_admission_status": 0,
  "knowledge_status_distribution": {
    "CONCEPT": 29,
    "FACT": 108,
    "PENDING": 374,
    "RECOMMENDATION": 4,
    "VERIFIED": 196
  },
  "admission_status_distribution": {
    "CANDIDATE": 711
  },
  "pending_concept_count": 403
}
```

### 来源追溯链

每条资产携带 source_origin/source_path/library_path，evidence_level 标记证据等级(E2/E3/E4)，knowledge_status 五态流转

### 可撤回机制

DELETE FROM intelligence_assets WHERE asset_id=? 可单条撤回；admission_status=CANDIDATE 表示未准入生产，PENDING/CONCEPT 不被生产引用

### 回归测试

相关测试文件数: 5

## 4. 双域账户 TOTP (v4_totp_secrets)

**状态**: PASS

### 数据一致性检查

```json
{
  "total_secrets": 1,
  "enabled_count": 1,
  "avg_secret_length": 72.0,
  "potential_plaintext_seeds": 0,
  "active_sessions": 68
}
```

### 来源追溯链

TOTP 种子由用户启用时生成，关联 user_id；last_used_at 追踪使用时间，created_at 追踪启用时间

### 可撤回机制

DELETE FROM v4_totp_secrets WHERE user_id=? 可关闭 TOTP；session 8h 过期由 v4_sessions 表控制

### 回归测试

相关测试文件数: 3

## 5. 八平台 Cookie (cookie_vault)

**状态**: WARN

### 数据一致性检查

```json
{
  "storage": "file",
  "cookie_files_count": 10,
  "cookie_files": [
    "data\\bilibili_cookies.json",
    "data\\instagram_cookies.json",
    "data\\weibo_cookies.json",
    "data\\xhs_cookies.json",
    "data\\zhihu_cookies.json",
    "data\\backups\\cookie_test_pollution_20260903\\xhs_cookies.json",
    "data\\backups\\cookie_test_pollution_20260903\\xhs_cookies.source.json",
    "data\\private\\xhs_cookie_header.txt",
    "data\\private\\xhs_cookie_retinaut.txt",
    "data\\backups\\cookie_test_pollution_20260903\\xhs_cookie_string.txt"
  ],
  "cookie_print_in_code": 10,
  "gitignore_excludes_cookies": true
}
```

### 来源追溯链

Cookie 由用户手动扫码登录后通过 xhs_cookie_bridge / import_cookies 写入；状态字段 ACTIVE/EXPIRED/BLOCKED 追踪生命周期

### 可撤回机制

删除 cookie 文件/记录即可撤回；Cookie 失效后自动标记 EXPIRED，不影响其他平台

### 回归测试

相关测试文件数: 2

### 备注

- 检测到 10 处代码可能打印 cookie 内容

## 6. 微信 Adapter (wechat_notifier/sogou_wechat)

**状态**: PASS

### 数据一致性检查

```json
{
  "wechat_notifier_exists": true,
  "sogou_wechat_exists": true,
  "env_has_wechat_credentials": false,
  "blocked_on_missing_credentials": true
}
```

### 来源追溯链

微信通知通过 wechat_notifier.py 发送，搜狗微信搜索通过 sogou_wechat adapter；凭证从 .env 读取，不硬编码

### 可撤回机制

移除 .env 中 WECHAT_* 配置即停用；Adapter 为可插拔设计，不影响其他平台

### 回归测试

相关测试文件数: 2

### 备注

- .env 中未检测到微信相关凭证（可能未配置，运行时应为 BLOCKED）

## 7. KOS 配置化 (kos_attribution/kos_metrics)

**状态**: PASS

### 数据一致性检查

```json
{
  "kos_tables": [
    "kos_profiles",
    "kos_executions",
    "kos_operations",
    "kos_paid_plans",
    "kos_rewards"
  ],
  "table_row_counts": {
    "kos_profiles": 1,
    "kos_executions": 481,
    "kos_operations": 230,
    "kos_paid_plans": 92,
    "kos_rewards": 46
  },
  "kos_module_files": 12,
  "files_with_hardcoded_weights": 0,
  "files_reading_config": 7
}
```

### 来源追溯链

KOS 归属由 kos_attribution.py 规则判定，权重从 config/system_config.json 读取；G1-G3 分组已修复，执行记录在 kos_executions 表

### 可撤回机制

修改 config 权重即可回滚配置；kos_executions 记录每次执行，可追溯历史归因结果

### 回归测试

相关测试文件数: 9

## 8. 报告 artifact_hash (report_artifact)

**状态**: PASS

### 数据一致性检查

```json
{
  "daily_reports_count": 30,
  "has_hash_field": true,
  "columns": [
    "id",
    "report_type",
    "report_date",
    "period_start",
    "period_end",
    "total_notes",
    "positive_count",
    "neutral_count",
    "negative_count",
    "high_risk_count",
    "medium_risk_count",
    "low_risk_count",
    "total_likes",
    "total_comments",
    "total_engagements",
    "top_topics",
    "hot_notes",
    "risk_alerts",
    "key_events",
    "event_summary",
    "sentiment_analysis",
    "summary",
    "generated_at",
    "executive_summary",
    "ai_summary",
    "key_insights",
    "action_items",
    "risk_index",
    "brand_health_score",
    "report_id",
    "artifact_hash",
    "generator_version",
    "data_version",
    "source_snapshot"
  ],
  "report_artifact_module": {
    "exists": true,
    "has_compute_hash": true,
    "has_verify": true,
    "has_historical_marker": true
  }
}
```

### 来源追溯链

artifact_hash = SHA-256(报告核心数据)，排除 hash 自身与 meta 注入键，保证可复算；G4 已修复，新报告 hash 非空，历史报告标记 historical

### 可撤回机制

hash 为只读校验字段，不修改报告内容；verify_report_hash 可随时复算比对

### 回归测试

相关测试文件数: 12

## 9. OSAI EvidenceChain

**状态**: PASS

### 数据一致性检查

```json
{
  "osai_direct_write_violations": 0,
  "evidence_contract_exists": false,
  "evidence_chain_uses_contract": false,
  "contract_files_count": 11
}
```

### 来源追溯链

OSAI EvidenceChain 通过 contract/artifact 与 ZBC 交换数据，不直接写 ZBC 生产 DB；边界检查 B3 持续验证

### 可撤回机制

OSAI 写入为独立表(zbc_evidence/zbc_canonical_data)，不修改现有生产表(notes/events/daily_reports)，可独立清理

### 回归测试

相关测试文件数: 7

---

## 验收标准

- **PASS**: 数据一致性通过，来源可追溯，有可撤回机制，有回归测试
- **WARN**: 基本通过但有需关注项（如缺失字段、潜在风险）
- **FAIL**: 未通过验收，需修复

*本文件由验收检查脚本自动生成，请勿手动编辑。*