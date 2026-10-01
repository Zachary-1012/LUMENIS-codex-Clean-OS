from __future__ import annotations

import hashlib
import sqlite3

import pytest


TABLE = "lumenis_subject_registry"


def _seed_v14_registry(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """CREATE TABLE schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_by TEXT DEFAULT 'system'
            )"""
        )
        conn.execute(
            "INSERT INTO schema_version(version, description) VALUES (14, 'v14 fixture')"
        )
        # Model the note columns required by v18; v14 includes these scope fields.
        conn.execute(
            """CREATE TABLE notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id TEXT UNIQUE NOT NULL,
                url TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                domain_id TEXT,
                product_id TEXT,
                subject_id TEXT,
                brand_focus_id TEXT,
                scope_status TEXT NOT NULL DEFAULT 'UNASSIGNED',
                scope_evidence_ref TEXT
            )"""
        )
        # Keep the injected-failure test isolated to the v14→v15 migration.
        conn.execute("CREATE TABLE canonical_data (canonical_id TEXT PRIMARY KEY)")
        conn.execute("CREATE TABLE zbc_canonical_data (canonical_id TEXT PRIMARY KEY)")
        conn.execute(
            f"""CREATE TABLE {TABLE} (
                subject_id TEXT PRIMARY KEY,
                domain_id TEXT NOT NULL,
                subject_type TEXT NOT NULL,
                name_en TEXT NOT NULL,
                name_zh TEXT NOT NULL,
                name_en_norm TEXT NOT NULL,
                name_zh_norm TEXT NOT NULL,
                industry TEXT NOT NULL DEFAULT '',
                keywords_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'configured',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(domain_id, subject_type, name_en_norm, name_zh_norm)
            )"""
        )
        conn.execute(
            f"CREATE INDEX idx_{TABLE}_domain ON {TABLE}(domain_id, status)"
        )
        conn.executemany(
            f"""INSERT INTO {TABLE} (
                subject_id, domain_id, subject_type, name_en, name_zh,
                name_en_norm, name_zh_norm, industry, keywords_json, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', 'configured', ?, ?)""",
            [
                (
                    "SUBJ-LEGACY-BMP-1", "BMP", "brand", "North Star Brand",
                    "北辰品牌", "north star brand", "北辰品牌", "beauty",
                    "2026-09-01T01:02:03", "2026-09-02T01:02:03",
                ),
                (
                    "SUBJ-LEGACY-BMP-2", "BMP", "brand", "Harbor Light",
                    "港湾之光", "harbor light", "港湾之光", "food",
                    "2026-09-03T01:02:03", "2026-09-04T01:02:03",
                ),
                (
                    "SUBJ-LEGACY-CTH", "CTH", "company", "North Star Operations",
                    "北辰运营", "north star operations", "北辰运营", "retail",
                    "2026-09-05T01:02:03", "2026-09-06T01:02:03",
                ),
            ],
        )
        conn.commit()


def _registry_state(path):
    with sqlite3.connect(path) as conn:
        schema = conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        rows = conn.execute(f"SELECT * FROM {TABLE} ORDER BY subject_id").fetchall()
        versions = conn.execute(
            "SELECT version FROM schema_version ORDER BY id"
        ).fetchall()
    return schema, rows, versions


def _expected_brand_id(subject_type, name_en_norm, name_zh_norm):
    digest = hashlib.sha256(
        f"BMP|{subject_type}|{name_en_norm}|{name_zh_norm}".encode("utf-8")
    ).hexdigest()[:24]
    return f"BRAND-{digest}"


def _bind_migration_database(monkeypatch, db_path):
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))


def test_v14_upgrade_is_deterministic_compatible_and_reusable(tmp_path, monkeypatch):
    from flask import Flask

    import account.authorization as authorization
    import lumenis.auth.service as auth_service
    import subject_registry
    from lumenis.shared.database import migrations

    db_path = tmp_path / "subject-registry-v14.sqlite3"
    _seed_v14_registry(db_path)
    _bind_migration_database(monkeypatch, db_path)

    assert migrations.CURRENT_VERSION >= 15
    assert migrations.migrate(target_version=15) is True

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE})")}
        assert "brand_focus_id" in columns
        rows = {
            row[0]: row
            for row in conn.execute(
                f"SELECT subject_id, brand_focus_id, domain_id, subject_type, "
                f"name_en, name_zh, name_en_norm, name_zh_norm, industry, "
                f"created_at, updated_at FROM {TABLE} ORDER BY subject_id"
            )
        }
        version = conn.execute(
            "SELECT MAX(version) FROM schema_version WHERE typeof(version)='integer'"
        ).fetchone()[0]
        assert version == 15

        bmp_one = rows["SUBJ-LEGACY-BMP-1"]
        bmp_two = rows["SUBJ-LEGACY-BMP-2"]
        cth = rows["SUBJ-LEGACY-CTH"]
        expected_one = _expected_brand_id("brand", "north star brand", "北辰品牌")
        expected_two = _expected_brand_id("brand", "harbor light", "港湾之光")
        assert bmp_one[1] == expected_one
        assert bmp_two[1] == expected_two
        assert bmp_one[1] != bmp_two[1]
        assert bmp_one[2:8] == (
            "BMP", "brand", "North Star Brand", "北辰品牌",
            "north star brand", "北辰品牌",
        )
        assert bmp_one[8:] == ("beauty", "2026-09-01T01:02:03", "2026-09-02T01:02:03")
        assert cth[1] is None

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                f"UPDATE {TABLE} SET brand_focus_id=? WHERE subject_id=?",
                (bmp_one[1], "SUBJ-LEGACY-BMP-2"),
            )

    before_repeat = _registry_state(db_path)
    with sqlite3.connect(db_path) as conn:
        subject_registry.ensure_schema(conn)
        conn.commit()
    assert _registry_state(db_path) == before_repeat

    new_bmp, created = subject_registry.add_subject({
        "domain_id": "BMP",
        "subject_type": "brand",
        "name_en": "New Harbor Brand",
        "name_zh": "新港品牌",
        "industry": "retail",
    })
    assert created is True
    assert new_bmp["brand_focus_id"] == _expected_brand_id(
        "brand", "new harbor brand", "新港品牌"
    )
    assert any(
        row["subject_id"] == new_bmp["subject_id"]
        and row["brand_focus_id"] == new_bmp["brand_focus_id"]
        for row in subject_registry.list_subjects("BMP")
    )

    new_cth, cth_created = subject_registry.add_subject({
        "domain_id": "CTH",
        "subject_type": "company",
        "name_en": "New Commerce Group",
        "name_zh": "新商业集团",
    })
    assert cth_created is True
    assert new_cth["brand_focus_id"] is None

    monkeypatch.setattr(auth_service, "get_current_user", lambda: {"id": 91})
    monkeypatch.setattr(
        authorization,
        "check_dual_domain_permission",
        lambda user_id, product_id, module, action: (
            user_id == 91 and product_id == "ZBMP" and module == "subject_registry"
            and action == "read"
        ),
    )
    app = Flask(__name__)
    app.register_blueprint(subject_registry.subject_registry_bp)
    response = app.test_client().get("/api/settings/subjects?domain_id=BMP")
    assert response.status_code == 200
    body = response.get_json()
    assert body["domains"][0]["id"] == "BMP"
    exposed = {row["subject_id"]: row["brand_focus_id"] for row in body["subjects"]}
    assert exposed["SUBJ-LEGACY-BMP-1"] == expected_one
    assert exposed[new_bmp["subject_id"]] == new_bmp["brand_focus_id"]

    before_later_upgrade = _registry_state(db_path)[1]
    assert migrations.migrate() is True
    after_later_upgrade = _registry_state(db_path)
    assert after_later_upgrade[1] == before_later_upgrade
    assert after_later_upgrade[2][-1][0] == migrations.CURRENT_VERSION
    assert migrations.migrate() is True
    assert _registry_state(db_path) == after_later_upgrade


def test_v14_registry_read_and_write_require_migration_without_schema_rewrite(
    tmp_path, monkeypatch
):
    from flask import Flask

    import account.authorization as authorization
    import lumenis.auth.service as auth_service
    import subject_registry

    db_path = tmp_path / "subject-registry-v14-unavailable.sqlite3"
    _seed_v14_registry(db_path)
    _bind_migration_database(monkeypatch, db_path)
    before = _registry_state(db_path)

    with pytest.raises(subject_registry.SubjectRegistryUnavailableError):
        subject_registry.list_subjects("BMP")
    with pytest.raises(subject_registry.SubjectRegistryUnavailableError):
        subject_registry.add_subject({
            "domain_id": "BMP",
            "subject_type": "brand",
            "name_en": "Must Wait",
            "name_zh": "等待迁移",
        })
    assert _registry_state(db_path) == before

    monkeypatch.setattr(auth_service, "get_current_user", lambda: {"id": 91})
    monkeypatch.setattr(
        authorization,
        "check_dual_domain_permission",
        lambda user_id, product_id, module, action: user_id == 91 and product_id == "ZBMP",
    )
    app = Flask(__name__)
    app.register_blueprint(subject_registry.subject_registry_bp)
    response = app.test_client().get("/api/settings/subjects?domain_id=BMP")
    assert response.status_code == 503
    assert response.get_json()["code"] == "SUBJECT_REGISTRY_UNAVAILABLE"
    assert _registry_state(db_path) == before


def test_v14_to_v15_failure_rolls_back_registry_ddl_data_and_version(
    tmp_path, monkeypatch
):
    import subject_registry
    from lumenis.shared.database import migrations

    db_path = tmp_path / "subject-registry-v14-rollback.sqlite3"
    _seed_v14_registry(db_path)
    _bind_migration_database(monkeypatch, db_path)
    before = _registry_state(db_path)
    original_ensure_schema = subject_registry.ensure_schema

    def fail_after_brand_focus_ddl(conn):
        original_ensure_schema(conn)
        raise RuntimeError("injected v15 failure after DDL and backfill")

    monkeypatch.setattr(subject_registry, "ensure_schema", fail_after_brand_focus_ddl)

    assert migrations.migrate() is False
    assert _registry_state(db_path) == before
    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE})")}
        assert "brand_focus_id" not in columns
        assert conn.execute(
            "SELECT COUNT(*) FROM schema_version WHERE version=15"
        ).fetchone()[0] == 0
