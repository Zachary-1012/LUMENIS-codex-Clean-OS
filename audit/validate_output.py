import json, os
md_path = r'D:\Taikoo-monitor-new\audit\db_empty_tables_classification.md'
json_path = r'D:\Taikoo-monitor-new\audit\db_empty_tables_classification.json'
with open(json_path, encoding='utf-8') as f:
    d = json.load(f)
print(f'JSON valid: {len(d["tables"])} tables')
print(f'Classification: {d["classification_summary"]}')
print(f'MD: {os.path.getsize(md_path)} bytes')
print(f'JSON: {os.path.getsize(json_path)} bytes')
# Verify all 25 tables present
names = [t['name'] for t in d['tables']]
expected = ['ai_filter_log','alert_records','app_evidence_records','auth_recovery_tasks','brand_knowledge','case_deep_analysis','collection_logs','collector_quality_log','event_graph_events','event_graph_relations','event_insights','event_mentions','events','feedback_keywords','note_comments','note_review_history','podcast_ai_runs','podcast_entities','professional_accounts','professional_metrics','swire_notes','token_stat','topic_campaign_notes','v4_audit_logs','v4_login_attempts']
missing = set(expected) - set(names)
print(f'Missing tables: {missing if missing else "none"}')
# Verify all have producer and consumer recorded
for t in d['tables']:
    p = len(t['producers'])
    c = len(t['consumers'])
    print(f'  {t["name"]}: classification={t["classification"]}, producers={p}, consumers={c}')
