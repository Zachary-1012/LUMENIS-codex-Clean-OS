#!/usr/bin/env python3
"""Migration: Create intelligence_assets table for Unified Intelligence Library.
Idempotent - safe to run multiple times.
Does NOT modify or drop any existing tables.
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'monitor.db')

def upgrade():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intelligence_assets (
            asset_id TEXT PRIMARY KEY,
            title TEXT,
            sub_library TEXT,
            source_origin TEXT,
            source_path TEXT,
            library_path TEXT,
            product TEXT,
            domain TEXT,
            evidence_level TEXT,
            knowledge_status TEXT,
            tags TEXT,
            summary TEXT,
            landing_status TEXT,
            admission_status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    cursor.execute("SELECT COUNT(*) FROM intelligence_assets")
    print(f"intelligence_assets table ready. Current records: {cursor.fetchone()[0]}")
    conn.close()

if __name__ == '__main__':
    upgrade()
