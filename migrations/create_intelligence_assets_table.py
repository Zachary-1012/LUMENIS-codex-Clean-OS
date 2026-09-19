#!/usr/bin/env python3
"""Controlled additive schema operation for the intelligence asset catalog.

Use the canonical Shared Database connection owner. An explicit path is useful
for isolated verification; the default resolves the configured production DB.
The operation is idempotent and does not modify or drop existing tables.
"""
from typing import Optional

from lumenis.shared.database import connect_sqlite


def upgrade(db_path: Optional[str] = None):
    conn = connect_sqlite(db_path)
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
