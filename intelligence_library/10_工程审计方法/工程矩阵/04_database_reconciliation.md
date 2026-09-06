# 04 — 数据库对账 (Database Reconciliation)

> Only ZBC has a relational database (SQLite). SICI uses localStorage, DCC uses JSON files, AIDRH uses JSONL records.  
> Verification: PASS (schema extracted from database.py + models.py + migrations)

## 1. Database Overview

| Property | Value |
|---|---|
| Engine | SQLite 3 |
| Default Path | data/monitor.db |
| Env Override | ZBC_DB_PATH |
| Tables in CREATE TABLE (database.py) | 15 |
| Tables in MODEL_REGISTRY (models.py) | 22 |
| Discrepancy | 7 tables in models.py not in CREATE TABLE |
| Migration Files | 2 (009_global_bil_staging.sql, 010_notes_subject_content_type.sql) |
| Migration Framework | Custom (database_migrations.py, no Alembic) |

## 2. Table-by-Table Reconciliation

### 2.1 Tables in BOTH database.py CREATE TABLE and models.py (15)

| Table | Model Class | Key Columns | Index | Constraints | Status |
|---|---|---|---|---|---|
| notes | Note | note_id UNIQUE, title, content, sentiment, risk_level, 70+ fields | note_id UNIQUE | NOT NULL on note_id | ACTIVE |
| events | Event | event_key, title, risk_level, status | — | — | ACTIVE |
| comments | Comment | note_id, comment_id, content, sentiment | — | — | ACTIVE |
| note_comments | NoteComment | comment_id, note_id, content, raw_json | — | — | ACTIVE |
| daily_reports | DailyReport | report_date, report_type, metrics | — | — | ACTIVE |
| daily_digest | DailyDigest | digest_date, metrics | — | — | ACTIVE |
| collection_logs | CollectionLog | keyword, notes_count, status, error_msg | — | — | ACTIVE |
| collector_quality_log | CollectorQualityLog | note_id, status, score, reason | — | — | ACTIVE |
| ai_filter_log | AIFilterLog | note_id, filter_stage, filter_result, confidence | — | — | ACTIVE |
| event_insights | EventInsight | event_id, ai_summary, risk_assessment | — | — | ACTIVE |
| event_mentions | EventMention | event_id, source_type, source_id, match_score | — | — | ACTIVE |
| note_review_history | NoteReviewHistory | note_id, old/new relevance/sentiment/risk | — | — | ACTIVE |
| feedback_keywords | FeedbackKeyword | keyword PK, source, score, enabled | keyword PK | — | ACTIVE |
| web_mentions | WebMention | source_id, source_platform, url, sentiment, risk | — | — | ACTIVE |
| web_runs | WebRun | adapter, query, started_at, fetched, accepted, rejected | — | — | ACTIVE |

### 2.2 Tables ONLY in models.py (NOT in database.py CREATE TABLE) — 7 tables

| Table | Model Class | Expected Columns | Creation Mechanism | Risk |
|---|---|---|---|---|
| weekly_events | WeeklyEvent | week_key, event_title, event_type, urgency, status | Likely ALTER TABLE or dynamic creation | NOT_VERIFIED — may not exist in production DB |
| web_topics | WebTopic | topic, source, sentiment, mention_count | Likely dynamic | NOT_VERIFIED |
| web_events | WebEvent | title, description, source, url, risk_level | Likely dynamic | NOT_VERIFIED |
| brand_industry_monitor | BrandIndustryMonitor | brand_name, industry, mention_count, sentiment | Likely dynamic | NOT_VERIFIED |
| collection_counters | CollectionCounter | date PK, daily_count, manual_count, auto_count | Likely dynamic | NOT_VERIFIED |
| system_config | SystemConfig | config_key, config_value, description | Likely dynamic | NOT_VERIFIED |
| web_sources | WebSource | source_key, source_name, adapter, enabled, last_run_at | Likely dynamic | NOT_VERIFIED |

**CONFLICT**: models.py registers 22 tables but database.py only creates 15. The 7 missing tables may be created via:
- database_migrations.py (not fully audited for CREATE TABLE statements)
- Dynamic CREATE TABLE IF NOT EXISTS in application code
- Legacy tables no longer created but still in model registry

**Status**: CONFLICT — requires Human Gate to verify actual production DB schema vs model registry.

## 3. Migration Files

### 3.1 migrations/009_global_bil_staging.sql (8307 bytes)
- Purpose: Global BIL (Brand Intelligence Layer) staging tables
- SHA: `3264938a8b1d2a11214270424b50a7fac6b55f29`
- Content: NOT_VERIFIED — file not fully read, size indicates multiple table definitions

### 3.2 migrations/010_notes_subject_content_type.sql (857 bytes)
- Purpose: Add subject content type to notes table
- SHA: `506bcf4ebd3b34034c895dc9bae532a6587a8d04`
- Likely: ALTER TABLE notes ADD COLUMN subject_content_type

### 3.3 Migration Risk Assessment
| Risk Factor | Assessment |
|---|---|
| Migration tooling | Custom Python (database_migrations.py), no standard framework (Alembic) |
| Migration tracking | No migration tracking table identified |
| Idempotency | Uses CREATE TABLE IF NOT EXISTS (safe) |
| Rollback | No down migrations defined |
| Ordering | Numeric prefix (009, 010) but gaps suggest earlier migrations were inline |

## 4. Sensitive Fields Assessment

| Table | Sensitive Columns | Type | Retention | Encryption |
|---|---|---|---|---|
| notes | author_id, author_nickname, author_avatar | PII | Permanent (no TTL) | None (plaintext SQLite) |
| comments | author_id, author_nickname | PII | Permanent | None |
| note_comments | author_id, author_nickname, raw_json | PII + raw data | Permanent | None |
| collection_logs | keyword, error_msg | May contain auth errors | Permanent | None |
| system_config | config_value | May contain API keys | Permanent | NOT_VERIFIED |
| feedback_keywords | keyword | Business data | Permanent | None |

**Security Finding**: No encryption at rest for SQLite database. No PII retention policy. No field-level encryption for potential credentials in system_config.

## 5. Database Dependencies (Read/Write Callers)

| Table | Primary Writer | Primary Readers | Dependencies |
|---|---|---|---|
| notes | collector.py, xhs_cdp_collector.py, collector_automation.py | app.py, ai_analyzer.py, daily_report.py, event_graph.py, export_report.py | Core table, 20+ dependents |
| events | event_graph.py, intelligence.py | app.py, daily_report.py, brand_report_generator.py | High dependency |
| comments | collector.py, xhs_cdp_collector.py | app.py, ai_analyzer.py | Medium |
| daily_reports | daily_report.py | app.py, export_report.py, wechat_notifier.py | Medium |
| collection_logs | collector.py, collector_automation.py | app.py, monitoring.py | Low |
| ai_filter_log | ai_filter.py | app.py, monitoring.py | Low |
| web_mentions | web_monitor.py, web_topic_discovery.py | app.py, intelligence.py | Medium |
| system_config | settings_module.py, config.py | All modules via config | Critical |
| feedback_keywords | data_feedback_loop.py | subject_classifier.py, collector.py | Medium |

## 6. Non-SQLite Persistence (Other Repos)

### SICI-Core
- **Mechanism**: localStorage (browser) via js/storage.js
- **Data**: Zachary AI state, capability registry cache, effective rules cache
- **No server-side database**

### DCC
- **Mechanism**: JSON files (data/baseline.json, data/rules/*.json, protocols/registry.json)
- **Runtime state**: In-memory (server.js), no persistence for tasks/snapshots/learning cases
- **Finding**: Learning store and shadow learning state is IN-MEMORY ONLY — lost on server restart

### AIDRH
- **Mechanism**: JSONL (data/research/records.jsonl — append-only ledger), JSON registries
- **Research records**: R-2026-0001 ~ R-2026-0008 (8 lines, append-only)
- **Capability registry**: data/learning/capability_registry.json (referenced in CAPABILITY-REGISTRY.md)

## 7. Database Reconciliation Summary

| Check | Status | Notes |
|---|---|---|
| Table count match (schema vs model) | FAIL | 15 vs 22, 7 tables discrepancy |
| Migration tracking | NOT_VERIFIED | No migration tracking table found |
| Sensitive field encryption | FAIL | No encryption at rest |
| PII retention policy | FAIL | No TTL/retention defined |
| Backup strategy | NOT_VERIFIED | No backup scripts identified in repo |
| Recovery procedure | NOT_VERIFIED | auto_recovery.py exists but DB recovery not confirmed |
| Cross-repo DB sharing | PASS | No cross-repo direct DB access (correct isolation) |
| ZBC evidence adapter (SICI) | PASS | Read-only, no direct DB access (via API contract) |

**Overall Database Gate**: BLOCKED — schema/model mismatch requires resolution before consolidation.