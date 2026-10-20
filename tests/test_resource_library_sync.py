"""Isolated regression tests for legacy resource synchronization counts."""

import sqlite3

import resource_library


def _connect_to_temp_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn):
    conn.executescript(
        """
        CREATE TABLE resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_uid TEXT UNIQUE,
            resource_category TEXT,
            title TEXT,
            content TEXT,
            tags TEXT,
            source TEXT,
            url TEXT,
            provenance TEXT,
            pipeline_stage TEXT,
            evidence_id TEXT,
            normalized_at TEXT,
            dedup_hash TEXT UNIQUE,
            is_production_rule INTEGER,
            product_context TEXT,
            extra_json TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE brand_knowledge (
            id INTEGER PRIMARY KEY,
            resource_uid TEXT,
            title TEXT,
            content TEXT,
            tags TEXT,
            source TEXT,
            url TEXT,
            provenance TEXT,
            pipeline_stage TEXT,
            evidence_id TEXT,
            normalized_at TEXT,
            dedup_hash TEXT,
            content_hash TEXT,
            is_production_rule INTEGER,
            product_context TEXT,
            category TEXT,
            relevance_score REAL,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE case_deep_analysis (
            id INTEGER PRIMARY KEY,
            case_id TEXT,
            resource_uid TEXT,
            resource_category TEXT,
            pipeline_stage TEXT,
            provenance TEXT,
            evidence_id TEXT,
            normalized_at TEXT,
            dedup_hash TEXT,
            is_production_rule INTEGER,
            product_context TEXT,
            case_title TEXT,
            basic_info TEXT,
            challenge TEXT,
            strategy TEXT,
            big_idea TEXT,
            execution TEXT,
            results TEXT,
            success_factors TEXT,
            system_insights TEXT,
            case_type TEXT,
            industry TEXT,
            brand TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE brand_industry_monitor (
            id INTEGER PRIMARY KEY,
            resource_uid TEXT,
            resource_category TEXT,
            pipeline_stage TEXT,
            provenance TEXT,
            evidence_id TEXT,
            normalized_at TEXT,
            dedup_hash TEXT,
            is_production_rule INTEGER,
            product_context TEXT,
            brand_name TEXT,
            brand_name_cn TEXT,
            industry TEXT,
            floor TEXT,
            shop_number TEXT,
            risk_level TEXT,
            last_updated TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )


def _insert_existing_resource(conn, resource_uid, category):
    conn.execute(
        """INSERT INTO resources
        (resource_uid, resource_category, title, content, source, url, provenance,
         dedup_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            resource_uid,
            category,
            "Original title",
            "Original content",
            "original source",
            "https://original.invalid/source",
            '{"origin":"preserved"}',
            f"existing-hash-{resource_uid}",
            "2026-01-01",
            "2026-01-01",
        ),
    )


def _seed_legacy_rows(conn):
    conn.executemany(
        """INSERT INTO brand_knowledge
        (id, resource_uid, title, content, source, url, provenance, dedup_hash,
         created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (1, "new-brand", "New brand", "New body", "brand source", "https://new.invalid/b",
             '{"origin":"new"}', "new-brand-hash", "2026-02-01", "2026-02-02"),
            (2, "existing-brand", "Changed title", "Changed body", "changed source",
             "https://changed.invalid/b", '{"origin":"changed"}', "incoming-brand-hash",
             "2026-03-01", "2026-03-02"),
        ],
    )
    conn.executemany(
        """INSERT INTO case_deep_analysis
        (id, case_id, resource_uid, case_title, basic_info, challenge, strategy,
         big_idea, execution, results, success_factors, system_insights, brand,
         created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (1, "new-case-id", "new-case", "New case", "basic", "challenge", "strategy",
             "idea", "execution", "results", "success", "insights", "new brand",
             "2026-02-01", "2026-02-02"),
            (2, "existing-case-id", "existing-case", "Changed case", "changed basic", "challenge",
             "strategy", "idea", "execution", "results", "success", "insights", "changed brand",
             "2026-03-01", "2026-03-02"),
        ],
    )
    conn.executemany(
        """INSERT INTO brand_industry_monitor
        (id, resource_uid, brand_name, industry, floor, shop_number, risk_level,
         last_updated, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (1, "new-industry", "New brand", "retail", "1F", "101", "low",
             "2026-02-02", "2026-02-01", "2026-02-02"),
            (2, "existing-industry", "Changed brand", "changed", "2F", "202", "high",
             "2026-03-02", "2026-03-01", "2026-03-02"),
        ],
    )


def test_sync_counts_only_inserted_rows_and_preserves_existing_provenance(tmp_path, monkeypatch):
    db_path = tmp_path / "resource-sync.sqlite"
    conn = _connect_to_temp_db(db_path)
    _create_schema(conn)
    _insert_existing_resource(conn, "existing-brand", "brand_theory")
    _insert_existing_resource(conn, "existing-case", "case_study")
    _insert_existing_resource(conn, "existing-industry", "industry_monitor")
    _seed_legacy_rows(conn)
    conn.commit()
    conn.close()

    monkeypatch.setattr(resource_library, "_get_conn", lambda: _connect_to_temp_db(db_path))

    result = resource_library.sync_from_legacy_tables()

    assert result == {
        "brand_theory": 1,
        "case_study": 1,
        "industry_monitor": 1,
        "total": 3,
    }

    conn = _connect_to_temp_db(db_path)
    try:
        for resource_uid in ("existing-brand", "existing-case", "existing-industry"):
            row = conn.execute(
                "SELECT title, source, url, provenance FROM resources WHERE resource_uid = ?",
                (resource_uid,),
            ).fetchone()
            assert tuple(row) == (
                "Original title",
                "original source",
                "https://original.invalid/source",
                '{"origin":"preserved"}',
            )
    finally:
        conn.close()

    assert resource_library.sync_from_legacy_tables() == {
        "brand_theory": 0,
        "case_study": 0,
        "industry_monitor": 0,
        "total": 0,
    }
