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

for t in tables:
    cur.execute(f'PRAGMA table_info("{t}")')
    cols = cur.fetchall()
    cur.execute(f'PRAGMA index_list("{t}")')
    idxs = cur.fetchall()
    cur.execute(f'PRAGMA foreign_key_list("{t}")')
    fks = cur.fetchall()
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    cnt = cur.fetchone()[0]
    
    col_str = ', '.join([f"{c[1]} {c[2]}{' PK' if c[5] else ''}{' NOT NULL' if c[3] else ''}" for c in cols])
    idx_str = ', '.join([f"{i[1]}{'(UNIQUE)' if i[2] else ''}" for i in idxs]) if idxs else 'none'
    fk_str = ', '.join([f"{f[3]}->{f[2]}.{f[4]}" for f in fks]) if fks else 'none'
    
    print(f"=== {t} (rows={cnt}) ===")
    print(f"  cols: {col_str}")
    print(f"  indexes: {idx_str}")
    print(f"  FKs: {fk_str}")
    print()

conn.close()
