import sqlite3, json, os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'monitor.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

tables = ['ai_filter_log','alert_records','app_evidence_records','auth_recovery_tasks',
          'brand_knowledge','case_deep_analysis','collection_logs','collector_quality_log',
          'event_graph_events','event_graph_relations','event_insights','event_mentions',
          'events','feedback_keywords','note_comments','note_review_history',
          'podcast_ai_runs','podcast_entities','professional_accounts','professional_metrics',
          'swire_notes','token_stat','topic_campaign_notes','v4_audit_logs','v4_login_attempts']

result = {}
for t in tables:
    cur.execute(f'PRAGMA table_info("{t}")')
    cols = cur.fetchall()
    cur.execute(f'PRAGMA index_list("{t}")')
    idxs = cur.fetchall()
    idx_detail = []
    for idx in idxs:
        idx_name = idx[1]
        cur.execute(f'PRAGMA index_info("{idx_name}")')
        idx_cols = cur.fetchall()
        idx_detail.append({'name': idx_name, 'unique': idx[2], 'columns': [c[2] for c in idx_cols]})
    cur.execute(f'PRAGMA foreign_key_list("{t}")')
    fks = cur.fetchall()
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    cnt = cur.fetchone()[0]
    cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}'")
    create_sql = cur.fetchone()
    result[t] = {
        'columns': [{'cid':c[0],'name':c[1],'type':c[2],'notnull':c[3],'default':c[4],'pk':c[5]} for c in cols],
        'indexes': idx_detail,
        'foreign_keys': [{'id':f[0],'seq':f[1],'table':f[2],'from':f[3],'to':f[4]} for f in fks],
        'row_count': cnt,
        'create_sql': create_sql[0] if create_sql else None
    }
conn.close()

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'table_schemas.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"Saved {len(result)} table schemas to {out_path}")
