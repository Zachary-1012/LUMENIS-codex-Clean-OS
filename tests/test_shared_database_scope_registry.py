"""Exact registry membership resolves in an isolated, migrated v18 database."""
from __future__ import annotations

import sqlite3

import pytest


def test_scope_resolves_exact_cth_and_bmp_keys_in_v18_database(tmp_path, monkeypatch):
    from lumenis.shared.database import migrations
    from lumenis.shared.database.scope import (
        SCOPE_STATUS_UNVERIFIED,
        ScopeValidationError,
        normalize_product_domain,
        resolve_scope,
    )
    from lumenis.shared.database.business_schema import apply_business_schema
    from canonical_data import ensure_canonical_table
    from lumenis.shared.evidence.store import (
        ensure_evidence_schema,
    )
    import subject_registry

    path = tmp_path / "scope-registry-v18.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setattr(migrations, "DB_PATH", str(path))
    monkeypatch.setattr(migrations, "BACKUP_DIR", str(tmp_path / "backups"))
    # Build the Shared Database and Evidence owner schemas in this isolated DB,
    # then invoke the actual v18 schema migration. The canonical Evidence owner
    # supplies nullable domain/product columns required by v18.
    with sqlite3.connect(path) as conn:
        apply_business_schema(conn)
        conn.execute("ALTER TABLE notes ADD COLUMN domain_id TEXT DEFAULT 'cth'")
        conn.execute("ALTER TABLE notes ADD COLUMN product_id TEXT DEFAULT 'CTH'")
        ensure_canonical_table(connection=conn)
        migrations.migration_13_to_14(conn)
        subject_registry.ensure_schema(conn)
        ensure_evidence_schema(conn)
        migrations.init_version_table(conn)
        migrations.set_version(conn, 17, migrations.MIGRATION_HISTORY[17])
        migrations.migration_17_to_18(conn)
        migrations.set_version(conn, 18, migrations.MIGRATION_HISTORY[18])
        assert conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='lumenis_entity_relation_assertions'"
        ).fetchone()

    with sqlite3.connect(path) as conn:
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        assert version == 18
        conn.executemany(
            """INSERT INTO lumenis_subject_registry
               (subject_id, brand_focus_id, domain_id, subject_type, name_en,
                name_zh, name_en_norm, name_zh_norm, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'now', 'now')""",
            [
                ("SUBJ-CTH", None, "CTH", "company", "Venue", "商场", "venue", "商场"),
                ("SUBJ-BMP", "BRAND-1", "BMP", "brand", "Brand", "品牌", "brand", "品牌"),
            ],
        )
        assert normalize_product_domain("CTH", "cth") == ("CTH", "cth")
        assert normalize_product_domain("BMP", "zbmp") == ("ZBMP", "zbmp")
        cth = resolve_scope(
            conn, product_id="CTH", domain_id="cth", subject_id="SUBJ-CTH",
            requested_status="UNVERIFIED",
        )
        bmp = resolve_scope(
            conn, product_id="ZBMP", domain_id="zbmp", brand_focus_id="BRAND-1",
            requested_status="UNVERIFIED",
        )
        assert (cth.subject_id, cth.brand_focus_id, cth.status) == (
            "SUBJ-CTH", None, SCOPE_STATUS_UNVERIFIED,
        )
        assert (bmp.subject_id, bmp.brand_focus_id, bmp.status) == (
            None, "BRAND-1", SCOPE_STATUS_UNVERIFIED,
        )
        with pytest.raises(ScopeValidationError, match="not present"):
            resolve_scope(conn, product_id="CTH", subject_id="SUBJ-MISSING")
        with pytest.raises(ScopeValidationError, match="cannot carry subject_id"):
            resolve_scope(conn, product_id="ZBMP", subject_id="SUBJ-CTH")
        with pytest.raises(ScopeValidationError, match="cannot promote"):
            resolve_scope(
                conn, product_id="CTH", subject_id="SUBJ-CTH",
                requested_status="VERIFIED",
            )
