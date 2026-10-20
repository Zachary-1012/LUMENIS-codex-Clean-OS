"""
ZBC Phase 15 - Historical Data Governance Tests
=================================================
测试历史数据导入规范：Hash -> Dedup -> Provenance -> Timestamp -> Source -> Product -> Subject

所有测试使用临时内存数据库，绝不修改生产数据库 data/monitor.db。
"""
import os
import sys
import sqlite3
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import historical_data_importer as hdi


@pytest.fixture
def temp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id TEXT, title TEXT, content TEXT, body TEXT, url TEXT,
            source_platform TEXT, publish_date TEXT, publish_datetime TEXT,
            captured_at TEXT, collected_at TEXT, last_seen_at TEXT,
            is_taikoo_verified INTEGER DEFAULT 0, verify_reason TEXT,
            content_hash TEXT, provenance TEXT, product_id TEXT, rule_version TEXT,
            subject_type TEXT, content_type TEXT, status TEXT,
            source_keyword TEXT, matched_keywords TEXT,
            likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
            collects INTEGER DEFAULT 0, shares INTEGER DEFAULT 0,
            sentiment TEXT, risk_level TEXT, risk_score INTEGER DEFAULT 0,
            summary TEXT, topics TEXT, author_id TEXT, author_nickname TEXT,
            author_avatar TEXT, note_type TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE canonical_data (
            canonical_id TEXT PRIMARY KEY, product_id TEXT, content_hash TEXT,
            provenance TEXT, rule_version TEXT, source_platform TEXT,
            source_type TEXT, title TEXT, content TEXT,
            publish_datetime TEXT, captured_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE rule_version_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT NOT NULL UNIQUE,
            rule_type TEXT NOT NULL DEFAULT 'subject', description TEXT DEFAULT '',
            subject_words_count INTEGER DEFAULT 0, exclude_words_count INTEGER DEFAULT 0,
            subject_words_hash TEXT DEFAULT '', exclude_words_hash TEXT DEFAULT '',
            applied_at TEXT DEFAULT '', applied_by TEXT DEFAULT 'system',
            is_active INTEGER DEFAULT 0, changelog TEXT DEFAULT '{}'
        )
    """)
    conn.execute("""
        CREATE TABLE historical_import_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, import_batch_id TEXT NOT NULL,
            source_table TEXT NOT NULL, source_id TEXT NOT NULL,
            target_table TEXT NOT NULL, target_id TEXT DEFAULT '',
            content_hash TEXT DEFAULT '', rule_version TEXT DEFAULT '',
            product_id TEXT DEFAULT 'CTH', subject_hit INTEGER DEFAULT 0,
            subject_reason TEXT DEFAULT '', publish_datetime TEXT DEFAULT '',
            captured_at TEXT DEFAULT '', source_platform TEXT DEFAULT '',
            import_status TEXT DEFAULT 'imported', dedup_hit INTEGER DEFAULT 0,
            dedup_of TEXT DEFAULT '', imported_at TEXT DEFAULT '',
            imported_by TEXT DEFAULT 'historical_importer', notes TEXT DEFAULT ''
        )
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def sample_record():
    return {
        "note_id": "hist_xhs_20260815_001",
        "title": "广州太古汇七夕活动实拍",
        "content": "今天去了广州太古汇，七夕布置很美，LV专柜人很多",
        "body": "今天去了广州太古汇，七夕布置很美，LV专柜人很多",
        "url": "https://xhslink.com/hist001",
        "source_platform": "xhs",
        "publish_datetime": "2026-08-15 14:30:00",
        "captured_at": "2026-08-16 09:00:00",
        "author_nickname": "时尚探店博主",
        "author_id": "user_001",
        "likes": 150, "comments": 23, "collects": 45, "shares": 12,
        "sentiment": "positive", "risk_level": "low",
        "source_table": "historical_backup_202608",
    }


@pytest.fixture
def non_subject_record():
    return {
        "note_id": "hist_xhs_20260815_002",
        "title": "上海兴业太古汇探店",
        "content": "上海太古汇今天有活动",
        "body": "上海太古汇今天有活动",
        "url": "https://xhslink.com/hist002",
        "source_platform": "xhs",
        "publish_datetime": "2026-08-15 10:00:00",
        "captured_at": "2026-08-16 09:00:00",
        "source_table": "historical_backup_202608",
    }


class TestHashDedup:
    def test_same_content_same_hash(self):
        h1 = hdi.compute_content_hash("A", "B", "C")
        h2 = hdi.compute_content_hash("A", "B", "C")
        assert h1 == h2 and len(h1) == 16

    def test_different_content_different_hash(self):
        assert hdi.compute_content_hash("广州", "太古汇") != hdi.compute_content_hash("上海", "太古汇")

    def test_hash_ignores_url(self):
        h1 = hdi.compute_content_hash("t", "c https://x.com/abc  extra")
        h2 = hdi.compute_content_hash("t", "c extra")
        assert h1 == h2

    def test_dedup_by_hash(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1")
        temp_db.commit()
        dup = dict(sample_record, note_id="dup_id")
        r = hdi.import_historical_note(dup, conn=temp_db, batch_id="b1")
        assert r["status"] == hdi.IMPORT_STATUS_DEDUP_SKIPPED
        assert r["dedup_type"] == "content_hash"

    def test_dedup_by_note_id(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1")
        temp_db.commit()
        dup = dict(sample_record, title="不同标题", content="不同内容")
        r = hdi.import_historical_note(dup, conn=temp_db, batch_id="b1")
        assert r["status"] == hdi.IMPORT_STATUS_DEDUP_SKIPPED
        assert r["dedup_type"] == "note_id"

    def test_no_false_dedup(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1")
        temp_db.commit()
        other = {"note_id": "other_001", "title": "另一条", "content": "完全不同",
                 "url": "https://x.com/o", "source_platform": "xhs",
                 "publish_datetime": "2026-08-16", "captured_at": "2026-08-17"}
        r = hdi.import_historical_note(other, conn=temp_db, batch_id="b1")
        assert r["status"] == hdi.IMPORT_STATUS_INSERTED


class TestProvenance:
    def test_provenance_format(self):
        assert hdi.build_provenance("notes", "abc") == "notes:abc"

    def test_provenance_recorded(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1")
        row = temp_db.execute(
            "SELECT provenance, source_platform, publish_datetime, captured_at FROM notes WHERE note_id=?",
            (sample_record["note_id"],)).fetchone()
        assert row["provenance"] == "historical_backup_202608:hist_xhs_20260815_001"
        assert row["source_platform"] == "xiaohongshu"
        assert row["publish_datetime"] == "2026-08-15 14:30:00"
        assert row["captured_at"] == "2026-08-16 09:00:00"


class TestTimestamp:
    def test_publish_capture_separated(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1")
        row = temp_db.execute(
            "SELECT publish_datetime, captured_at FROM notes WHERE note_id=?",
            (sample_record["note_id"],)).fetchone()
        assert row["publish_datetime"] != row["captured_at"]
        assert row["publish_datetime"] == "2026-08-15 14:30:00"

    def test_missing_publish_not_replaced(self):
        ts = hdi.validate_timestamps(publish_datetime="", captured_at="2026-09-01 10:00:00")
        assert ts["publish_datetime"] == ""
        assert len(ts["warnings"]) > 0


class TestSourcePlatform:
    def test_normalization(self):
        assert hdi.normalize_platform("xhs") == "xiaohongshu"
        assert hdi.normalize_platform("weibo") == "weibo"
        assert hdi.normalize_platform("b站") == "bilibili"
        assert hdi.normalize_platform("") == "unknown"


class TestCTHNamespace:
    def test_default_cth(self):
        assert hdi.DEFAULT_PRODUCT_ID == "CTH"
        assert hdi.resolve_product_id("") == "CTH"

    def test_cth_recorded(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1", product_id="CTH")
        row = temp_db.execute("SELECT product_id FROM notes WHERE note_id=?",
                              (sample_record["note_id"],)).fetchone()
        assert row["product_id"] == "CTH"

    def test_zbc_isolated(self, temp_db, sample_record):
        cth = dict(sample_record, note_id="cth_001")
        zbc = dict(sample_record, note_id="zbc_001", title="ZBC数据", content="ZBC内容")
        hdi.import_historical_note(cth, conn=temp_db, batch_id="b1", product_id="CTH")
        hdi.import_historical_note(zbc, conn=temp_db, batch_id="b2", product_id="ZBC")
        rows = temp_db.execute("SELECT product_id, COUNT(*) as cnt FROM notes GROUP BY product_id").fetchall()
        counts = {r["product_id"]: r["cnt"] for r in rows}
        assert counts.get("CTH") == 1
        assert counts.get("ZBC") == 1


class TestSubjectFilter:
    def test_cth_hit(self):
        r = hdi.apply_subject_filter(title="广州太古汇探店", content="太古汇LV")
        assert r["subject_hit"] is True

    def test_exclude_veto(self):
        r = hdi.apply_subject_filter(title="上海太古汇", content="上海兴业太古汇")
        assert r["subject_hit"] is False
        assert "排除词" in r["subject_reason"]

    def test_subject_recorded(self, temp_db, sample_record, non_subject_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1")
        hdi.import_historical_note(non_subject_record, conn=temp_db, batch_id="b1")
        cth = temp_db.execute("SELECT is_taikoo_verified FROM notes WHERE note_id='hist_xhs_20260815_001'").fetchone()
        sh = temp_db.execute("SELECT is_taikoo_verified FROM notes WHERE note_id='hist_xhs_20260815_002'").fetchone()
        assert cth["is_taikoo_verified"] == 1
        assert sh["is_taikoo_verified"] == 0


class TestRuleVersion:
    def test_register(self, temp_db):
        rid = hdi.register_rule_version(temp_db, "v1.0", "test", subject_words=["太古汇"], exclude_words=["上海"])
        assert rid > 0
        row = temp_db.execute("SELECT * FROM rule_version_registry WHERE version='v1.0'").fetchone()
        assert row["subject_words_count"] == 1
        assert row["is_active"] == 1

    def test_new_deactivates_old(self, temp_db):
        hdi.register_rule_version(temp_db, "v1.0")
        hdi.register_rule_version(temp_db, "v2.0")
        rows = temp_db.execute("SELECT version, is_active FROM rule_version_registry ORDER BY id").fetchall()
        assert rows[0]["is_active"] == 0
        assert rows[1]["is_active"] == 1

    def test_recorded_on_import(self, temp_db, sample_record):
        hdi.register_rule_version(temp_db, "rv-test")
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1", rule_version="rv-test")
        row = temp_db.execute("SELECT rule_version FROM notes WHERE note_id=?",
                              (sample_record["note_id"],)).fetchone()
        assert row["rule_version"] == "rv-test"

    def test_baseline_idempotent(self, temp_db):
        v1 = hdi.ensure_baseline_rule_version(temp_db)
        v2 = hdi.ensure_baseline_rule_version(temp_db)
        assert v1 == v2
        cnt = temp_db.execute("SELECT COUNT(*) as c FROM rule_version_registry WHERE version=?",
                              (hdi.HISTORICAL_RULE_VERSION,)).fetchone()["c"]
        assert cnt == 1


class TestHistoricalProtection:
    def test_never_updates_existing(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1")
        original = temp_db.execute("SELECT title FROM notes WHERE note_id=?",
                                   (sample_record["note_id"],)).fetchone()["title"]
        modified = dict(sample_record, title="被篡改")
        r = hdi.import_historical_note(modified, conn=temp_db, batch_id="b2")
        assert r["status"] == hdi.IMPORT_STATUS_DEDUP_SKIPPED
        current = temp_db.execute("SELECT title FROM notes WHERE note_id=?",
                                  (sample_record["note_id"],)).fetchone()["title"]
        assert current == original
        assert current != "被篡改"

    def test_keeps_original_rule_version(self, temp_db, sample_record):
        hdi.register_rule_version(temp_db, "v1.0")
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="b1", rule_version="v1.0")
        hdi.register_rule_version(temp_db, "v2.0")
        row = temp_db.execute("SELECT rule_version FROM notes WHERE note_id=?",
                              (sample_record["note_id"],)).fetchone()
        assert row["rule_version"] == "v1.0"

    def test_import_log_auditable(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="audit1")
        log = temp_db.execute("SELECT * FROM historical_import_log WHERE import_batch_id='audit1'").fetchone()
        assert log is not None
        assert log["source_table"] == "historical_backup_202608"
        assert log["import_status"] == "inserted"
        assert log["product_id"] == "CTH"
        assert log["content_hash"] != ""

    def test_dedup_logged(self, temp_db, sample_record):
        hdi.import_historical_note(sample_record, conn=temp_db, batch_id="dl1")
        dup = dict(sample_record, note_id="dup_x")
        hdi.import_historical_note(dup, conn=temp_db, batch_id="dl1")
        rows = temp_db.execute(
            "SELECT import_status, dedup_hit FROM historical_import_log WHERE import_batch_id='dl1' ORDER BY id").fetchall()
        assert rows[0]["import_status"] == "inserted"
        assert rows[1]["import_status"] == "dedup_skipped"
        assert rows[1]["dedup_hit"] == 1


class TestImportTruthfulPersistence:
    def test_missing_metrics_and_analysis_remain_null(self, temp_db):
        record = {
            "note_id": "missing-metrics-001",
            "title": "广州太古汇日常记录",
            "content": "临时合成导入记录",
        }

        result = hdi.import_historical_note(record, conn=temp_db, batch_id="missing-values")

        assert result["status"] == hdi.IMPORT_STATUS_INSERTED
        row = temp_db.execute(
            """SELECT likes, comments, collects, shares, sentiment, risk_level, risk_score
               FROM notes WHERE note_id=?""",
            (record["note_id"],),
        ).fetchone()
        assert tuple(row) == (None, None, None, None, None, None, None)

    def test_explicit_zero_neutral_and_low_values_are_preserved(self, temp_db):
        record = {
            "note_id": "explicit-values-001",
            "title": "广州太古汇日常记录",
            "content": "临时合成导入记录",
            "likes": 0,
            "comments": 0,
            "collects": 0,
            "shares": 0,
            "sentiment": "neutral",
            "risk_level": "low",
            "risk_score": 0,
        }

        result = hdi.import_historical_note(record, conn=temp_db, batch_id="explicit-values")

        assert result["status"] == hdi.IMPORT_STATUS_INSERTED
        row = temp_db.execute(
            """SELECT likes, comments, collects, shares, sentiment, risk_level, risk_score
               FROM notes WHERE note_id=?""",
            (record["note_id"],),
        ).fetchone()
        assert tuple(row) == (0, 0, 0, 0, "neutral", "low", 0)

    def test_log_failure_rolls_back_importer_owned_transaction(self, temp_db):
        temp_db.execute(
            """CREATE TRIGGER reject_historical_log BEFORE INSERT ON historical_import_log
               BEGIN SELECT RAISE(ABORT, 'isolated log write failure'); END"""
        )
        record = {
            "note_id": "partial-write-001",
            "title": "广州太古汇日常记录",
            "content": "临时合成导入记录",
        }

        result = hdi.import_historical_note(record, conn=temp_db, batch_id="partial-write")

        assert result["status"] == hdi.IMPORT_STATUS_ERROR
        assert result["persistence_state"] == "ROLLED_BACK"
        assert not temp_db.in_transaction
        assert result["inserted_id"] is None
        assert result["log_id"] is None
        assert temp_db.execute(
            "SELECT COUNT(*) FROM notes WHERE note_id=?", (record["note_id"],)
        ).fetchone()[0] == 0
        assert temp_db.execute(
            "SELECT COUNT(*) FROM historical_import_log WHERE import_batch_id='partial-write'"
        ).fetchone()[0] == 0

    def test_failure_preserves_a_transaction_owned_by_caller(self, temp_db):
        temp_db.execute("BEGIN")
        temp_db.execute(
            """CREATE TRIGGER reject_historical_log BEFORE INSERT ON historical_import_log
               BEGIN SELECT RAISE(ABORT, 'isolated log write failure'); END"""
        )
        result = hdi.import_historical_note({
            "note_id": "caller-owned-failed-001",
            "title": "广州太古汇临时记录", "content": "isolated synthetic row",
        }, conn=temp_db, batch_id="caller-owned-failed")

        assert result["status"] == hdi.IMPORT_STATUS_ERROR
        assert result["persistence_state"] == "ROLLED_BACK_TO_SAVEPOINT"
        assert temp_db.in_transaction
        assert temp_db.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
        temp_db.rollback()

    def test_missing_note_id_reports_not_written(self, temp_db):
        result = hdi.import_historical_note({"title": "no id"}, conn=temp_db)

        assert result["status"] == hdi.IMPORT_STATUS_ERROR
        assert result["persistence_state"] == "NOT_WRITTEN"
        assert not temp_db.in_transaction

    @pytest.mark.parametrize(
        "failed_record",
        [
            {"note_id": "bad-metric", "likes": "not-a-number"},
            {"note_id": "abort-trigger"},
        ],
        ids=["nonnumeric-metric", "sqlite-abort-trigger"],
    )
    def test_first_isolated_failure_does_not_stop_later_valid_batch_rows(
            self, temp_db, tmp_path, monkeypatch, failed_record):
        db_path = tmp_path / "isolated-first-failure.sqlite"
        temp_db.execute(
            """CREATE TRIGGER abort_selected_note BEFORE INSERT ON notes
               WHEN NEW.note_id='abort-trigger'
               BEGIN SELECT RAISE(ABORT, 'synthetic isolated row failure'); END"""
        )
        temp_db.commit()
        disk_conn = sqlite3.connect(db_path)
        temp_db.backup(disk_conn)
        disk_conn.close()

        def open_fixture_database(path=None):
            conn = sqlite3.connect(path or db_path)
            conn.row_factory = sqlite3.Row
            return conn

        monkeypatch.setattr(hdi, "_get_connection", open_fixture_database)
        failed_record = {
            **failed_record,
            "title": "广州太古汇失败样例",
            "content": "synthetic isolated failure",
        }
        valid_record = {
            "note_id": "later-valid-row",
            "title": "广州太古汇后续有效记录",
            "content": "synthetic valid row",
        }

        stats = hdi.import_historical_batch(
            [failed_record, valid_record], db_path=str(db_path), rule_version="fixture-rule"
        )

        check = sqlite3.connect(db_path)
        try:
            assert check.execute(
                "SELECT COUNT(*) FROM notes WHERE note_id=?",
                (failed_record["note_id"],),
            ).fetchone()[0] == 0
            assert check.execute(
                "SELECT COUNT(*) FROM notes WHERE note_id='later-valid-row'"
            ).fetchone()[0] == 1
        finally:
            check.close()

        assert stats["inserted"] == 1
        assert stats["errors"] == 1
        assert [detail["status"] for detail in stats["details"]] == [
            hdi.IMPORT_STATUS_ERROR, hdi.IMPORT_STATUS_INSERTED,
        ]
        assert [detail["persistence_state"] for detail in stats["details"]] == [
            "ROLLED_BACK", "COMMITTED",
        ]

    def test_batch_wide_sqlite_rollback_stops_and_reclassifies_pending_rows(
            self, temp_db, tmp_path, monkeypatch):
        db_path = tmp_path / "batch-rollback.sqlite"
        temp_db.execute(
            """CREATE TRIGGER rollback_selected_note BEFORE INSERT ON notes
               WHEN NEW.note_id='rollback-trigger'
               BEGIN SELECT RAISE(ROLLBACK, 'synthetic whole-transaction rollback'); END"""
        )
        temp_db.commit()
        disk_conn = sqlite3.connect(db_path)
        temp_db.backup(disk_conn)
        disk_conn.close()

        def open_fixture_database(path=None):
            conn = sqlite3.connect(path or db_path)
            conn.row_factory = sqlite3.Row
            return conn

        monkeypatch.setattr(hdi, "_get_connection", open_fixture_database)
        records = [
            {"note_id": "batch-first", "title": "广州太古汇首条", "content": "synthetic first"},
            {"note_id": "rollback-trigger", "title": "广州太古汇触发", "content": "synthetic rollback"},
            None,
        ]

        stats = hdi.import_historical_batch(records, db_path=str(db_path), rule_version="fixture-rule")

        check = sqlite3.connect(db_path)
        try:
            assert check.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
            assert check.execute(
                "SELECT COUNT(*) FROM historical_import_log WHERE import_batch_id=?",
                (stats["batch_id"],),
            ).fetchone()[0] == 0
        finally:
            check.close()
        assert stats["inserted"] == 0
        assert stats["errors"] == 3
        assert [row["persistence_state"] for row in stats["details"]] == [
            "ROLLED_BACK", "ROLLED_BACK", "NOT_WRITTEN",
        ]
        assert stats["details"][2]["note_id"] == ""
        assert "not processed" in stats["details"][2]["warnings"][0]

    def test_caller_connection_remains_uncommitted_and_rollbackable(self, temp_db):
        record = {
            "note_id": "caller-transaction-001",
            "title": "广州太古汇日常记录",
            "content": "临时合成导入记录",
        }

        result = hdi.import_historical_note(record, conn=temp_db, batch_id="caller-transaction")

        assert result["status"] == hdi.IMPORT_STATUS_INSERTED
        assert result["persistence_state"] == "PENDING_CALLER_COMMIT"
        assert temp_db.in_transaction
        assert temp_db.execute(
            "SELECT COUNT(*) FROM notes WHERE note_id=?", (record["note_id"],)
        ).fetchone()[0] == 1
        assert temp_db.execute(
            "SELECT COUNT(*) FROM historical_import_log WHERE import_batch_id='caller-transaction'"
        ).fetchone()[0] == 1

        temp_db.rollback()

        assert temp_db.execute(
            "SELECT COUNT(*) FROM notes WHERE note_id=?", (record["note_id"],)
        ).fetchone()[0] == 0
        assert temp_db.execute(
            "SELECT COUNT(*) FROM historical_import_log WHERE import_batch_id='caller-transaction'"
        ).fetchone()[0] == 0

    def test_batch_owner_commits_and_marks_import_results(self, temp_db, tmp_path, monkeypatch):
        db_path = tmp_path / "batch-owner.sqlite"
        disk_conn = sqlite3.connect(db_path)
        temp_db.backup(disk_conn)
        disk_conn.close()

        def open_fixture_database(path=None):
            conn = sqlite3.connect(path or db_path)
            conn.row_factory = sqlite3.Row
            return conn

        monkeypatch.setattr(hdi, "_get_connection", open_fixture_database)
        record = {
            "note_id": "batch-owner-001",
            "title": "广州太古汇日常记录",
            "content": "临时合成导入记录",
        }

        stats = hdi.import_historical_batch(
            [record], db_path=str(db_path), rule_version="fixture-rule"
        )

        check = sqlite3.connect(db_path)
        try:
            assert check.execute(
                "SELECT COUNT(*) FROM notes WHERE note_id=?", (record["note_id"],)
            ).fetchone()[0] == 1
            assert check.execute(
                "SELECT COUNT(*) FROM historical_import_log WHERE import_batch_id=?",
                (stats["batch_id"],),
            ).fetchone()[0] == 1
        finally:
            check.close()
        assert stats["inserted"] == 1
        assert stats["details"][0]["persistence_state"] == "COMMITTED"


class TestSilentOverwriteRisk:
    def test_reprocess_has_audit_trail(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reprocess.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "UPDATE notes" in content
        assert "note_review_history" in content

    def test_reprocess_has_backup(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reprocess.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "backup" in content.lower()

    def test_populate_uses_insert_ignore(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "populate_empty_tables.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "INSERT OR IGNORE" in content
        assert "UPDATE " not in content

    def test_populate_checks_existing(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "populate_empty_tables.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "SELECT COUNT(*)" in content
        assert "已有数据，跳过" in content

    def test_safe_identifier(self):
        """验证 _safe_identifier 拒绝非法SQL标识符。"""
        import historical_data_importer as hdi
        assert hdi._safe_identifier("notes") == "notes"
        assert hdi._safe_identifier("web_mentions") == "web_mentions"
        with pytest.raises(ValueError):
            hdi._safe_identifier("notes; DROP TABLE users;--")
        with pytest.raises(ValueError):
            hdi._safe_identifier("col name")
        with pytest.raises(ValueError):
            hdi._safe_identifier("")
