# -*- coding: utf-8 -*-
"""Learning Memory 单元测试 — 真实操作临时DB，不 mock。"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lumenis.shared.learning.memory import (
    LearningMemory, LearningType, LifecycleStage, SampleType,
)


class TestLearningMemory:
    def test_list_feedback_keywords(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        keywords = lm.list_feedback_keywords()
        assert len(keywords) >= 2
        kw_names = [k["keyword"] for k in keywords]
        assert "排队" in kw_names
        assert "服务态度" in kw_names

    def test_get_feedback_keyword(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        kw = lm.get_feedback_keyword("排队")
        assert kw is not None
        assert kw["score"] == 0.9
        assert kw["used_count"] == 5

    def test_record_learning(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_learning(
            learning_type=LearningType.FEEDBACK,
            content={"text": "测试反馈"},
            source="user",
            confidence=0.8,
        )
        assert rec is not None
        assert rec.value["learning_type"] == "feedback"
        assert rec.value["confidence"] == 0.8
        assert rec.value["lifecycle_stage"] == "raw"

    def test_record_feedback(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_feedback("这个分析不准确", context={"task": "test"})
        assert rec is not None
        assert rec.value["content"]["feedback_text"] == "这个分析不准确"
        assert rec.value["source"] == "user"

    def test_record_correction(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_correction(
            original_output="负面",
            corrected_output="中性",
            context={"note_id": "n1"},
        )
        assert rec is not None
        assert rec.value["content"]["original_output"] == "负面"
        assert rec.value["content"]["corrected_output"] == "中性"

    def test_positive_negative_samples(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        lm.add_positive_sample({"text": "good output"})
        lm.add_negative_sample({"text": "bad output"})
        assert lm.get_positive_samples() == []
        assert lm.get_negative_samples() == []

        records = lm.query({"learning_type": "correction"}, limit=10)
        assert len(records) == 2
        for record in records:
            assert lm.promote_record(record.record_id, LifecycleStage.REVIEWED)
            assert lm.promote_record(record.record_id, LifecycleStage.VALIDATED)
            assert lm.promote_record(record.record_id, LifecycleStage.PROMOTED)
        assert [s["sample_type"] for s in lm.get_positive_samples()] == ["positive"]
        assert [s["sample_type"] for s in lm.get_negative_samples()] == ["negative"]

    def test_query_keeps_legacy_override_and_shares_ttl_clock(self, monkeypatch):
        from datetime import datetime, timedelta, timezone
        import agent_memory.base as memory_base
        from agent_memory.base import MemoryRecord

        lm = LearningMemory(enabled=True)
        now = datetime.now(timezone.utc)
        expired_at = (now - timedelta(seconds=1)).isoformat()
        valid_at = (now - timedelta(seconds=10)).isoformat()
        for index in range(51):
            record = MemoryRecord(
                layer="learning", key=f"expired-{index}", value={"ordinal": index},
                timestamp=expired_at, ttl_seconds=0.1,
            )
            lm._in_memory[record.key] = record
        valid = MemoryRecord(
            layer="learning", key="valid-older", value={"source": "valid"},
            timestamp=valid_at, ttl_seconds=60,
        )
        lm._in_memory[valid.key] = valid

        clock_reads = []
        query_time = now.timestamp()
        monkeypatch.setattr(memory_base.time, "time",
                            lambda: clock_reads.append(query_time) or query_time)

        assert [record.key for record in lm.query(limit=1)] == ["valid-older"]
        assert clock_reads == [query_time]

    def test_samples_follow_persisted_lifecycle_across_restart(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_correction(
            original_output="draft",
            corrected_output="reviewed result",
            sample_type=SampleType.POSITIVE,
        )
        assert rec is not None
        assert lm.get_positive_samples() == []

        assert lm.promote_record(rec.record_id, LifecycleStage.REVIEWED)
        assert lm.promote_record(rec.record_id, LifecycleStage.VALIDATED)
        assert lm.promote_record(rec.record_id, LifecycleStage.PROMOTED)
        assert lm.get_positive_samples()[0]["corrected"] == "reviewed result"

        restarted = LearningMemory(db_path=seeded_db, enabled=True)
        promoted = restarted.get_positive_samples()
        assert len(promoted) == 1
        assert promoted[0]["learning_record_id"] == rec.record_id
        assert promoted[0]["lifecycle_stage"] == "promoted"

        assert restarted.promote_record(rec.record_id, LifecycleStage.ARCHIVED)
        assert lm.get_positive_samples() == []  # 旧实例缓存也不能覆盖持久化归档状态。
        after_archive = LearningMemory(db_path=seeded_db, enabled=True)
        assert after_archive.get_positive_samples() == []

    def test_configured_db_read_failure_cannot_revive_archived_learning(self, seeded_db, monkeypatch):
        import sqlite3
        import lumenis.shared.learning.memory as memory_module

        stale = LearningMemory(db_path=seeded_db, enabled=True)
        sample = stale.record_correction(
            original_output="draft",
            corrected_output="promoted sample",
            sample_type=SampleType.POSITIVE,
        )
        rule = stale.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={"suggestion_text": "promoted rule"},
        )
        assert sample is not None and rule is not None
        for record_id in (sample.record_id, rule.record_id):
            assert stale.promote_record(record_id, LifecycleStage.REVIEWED)
            assert stale.promote_record(record_id, LifecycleStage.VALIDATED)
            assert stale.promote_record(record_id, LifecycleStage.PROMOTED)
        assert stale.get_positive_samples()
        assert stale.get_promoted_rules()

        # A second owner archives both persisted records while `stale` retains
        # PROMOTED cache entries from before the archive.
        archive_owner = LearningMemory(db_path=seeded_db, enabled=True)
        assert archive_owner.promote_record(sample.record_id, LifecycleStage.ARCHIVED)
        assert archive_owner.promote_record(rule.record_id, LifecycleStage.ARCHIVED)

        def locked_connection(_db_path):
            raise sqlite3.OperationalError("database is locked")

        monkeypatch.setattr(memory_module, "get_db_connection", locked_connection)
        assert stale.get_positive_samples() == []
        assert stale.get_promoted_rules() == []
        # The stale PROMOTED value must not make an idempotent promotion appear
        # successful when the configured lifecycle owner cannot be read.
        assert stale.promote_record(sample.record_id, LifecycleStage.PROMOTED) is False

    def test_configured_db_missing_record_cannot_promote_cached_record(self, seeded_db):
        import sqlite3

        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_correction(
            original_output="draft",
            corrected_output="uncertain sample",
            sample_type=SampleType.POSITIVE,
        )
        assert rec is not None
        conn = sqlite3.connect(seeded_db)
        conn.execute(
            "DELETE FROM agent_learning_records WHERE record_id=?",
            (rec.record_id,),
        )
        conn.commit()
        conn.close()

        assert lm.promote_record(rec.record_id, LifecycleStage.REVIEWED) is False
        assert rec.value["lifecycle_stage"] == LifecycleStage.RAW.value
        assert lm.get_positive_samples() == []

    def test_explicit_memory_only_learning_lifecycle(self):
        lm = LearningMemory(enabled=True)
        sample = lm.record_correction(
            original_output="draft",
            corrected_output="memory-only promoted sample",
            sample_type=SampleType.POSITIVE,
        )
        rule = lm.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={"suggestion_text": "memory-only promoted rule"},
        )
        for record in (sample, rule):
            assert record is not None
            assert lm.promote_record(record.record_id, LifecycleStage.REVIEWED)
            assert lm.promote_record(record.record_id, LifecycleStage.VALIDATED)
            assert lm.promote_record(record.record_id, LifecycleStage.PROMOTED)

        assert lm.get_positive_samples()[0]["corrected"] == "memory-only promoted sample"
        assert lm.get_promoted_rules()[0]["content"]["suggestion_text"] == "memory-only promoted rule"

    def test_promote_record(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={"rule": "test"},
            confidence=0.6,
        )
        assert lm.promote_record(rec.record_id, LifecycleStage.REVIEWED) is True
        retrieved = lm.retrieve(rec.key)
        assert retrieved.value["lifecycle_stage"] == "reviewed"

    def test_promote_record_not_found(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        assert lm.promote_record("nonexistent", LifecycleStage.REVIEWED) is False

    def test_get_promoted_rules(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={"rule": "promoted rule"},
        )
        assert lm.promote_record(rec.record_id, LifecycleStage.REVIEWED) is True
        assert lm.promote_record(rec.record_id, LifecycleStage.VALIDATED) is True
        assert lm.promote_record(rec.record_id, LifecycleStage.PROMOTED) is True
        promoted = lm.get_promoted_rules()
        assert len(promoted) >= 1

    def test_promote_record_persists_across_restart(self, seeded_db):
        import sqlite3
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        rec = lm.record_learning(
            learning_type=LearningType.RULE_SUGGESTION,
            content={"rule": "restart-safe"},
        )
        assert lm.promote_record(rec.record_id, LifecycleStage.REVIEWED) is True

        # 新实例没有旧内存记录，仍必须能从 SQLite 继续治理生命周期。
        restarted = LearningMemory(db_path=seeded_db, enabled=True)
        assert restarted.promote_record(rec.record_id, LifecycleStage.VALIDATED) is True

        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT lifecycle_stage FROM agent_learning_records WHERE record_id=?",
            (rec.record_id,),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["lifecycle_stage"] == "validated"

    def test_persist_to_agent_learning_records(self, seeded_db):
        import sqlite3
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        lm.record_learning(
            learning_type=LearningType.FEEDBACK,
            content={"text": "persist test"},
        )
        conn = sqlite3.connect(seeded_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM agent_learning_records WHERE learning_type='feedback'"
        ).fetchone()
        conn.close()
        assert row is not None
        assert "persist test" in row["content_json"]

    def test_disabled(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=False)
        assert lm.list_feedback_keywords() == []
        assert lm.record_feedback("test") is None

    def test_stats(self, seeded_db):
        lm = LearningMemory(db_path=seeded_db, enabled=True)
        s = lm.stats()
        assert s["feedback_keywords_total"] >= 2
        assert s["positive_samples"] == 0
        assert s["negative_samples"] == 0


def test_full_learning_json_survives_and_failed_commit_is_not_success(seeded_db):
    import json
    import sqlite3
    from lumenis.shared.learning.memory import LearningMemory, LearningType
    owner = LearningMemory(db_path=seeded_db, enabled=True)
    content = {'text': '中文完整资料' * 2000}
    record = owner.record_learning(LearningType.FEEDBACK, content)
    assert record is not None
    with sqlite3.connect(seeded_db) as conn:
        stored = conn.execute('SELECT content_json FROM agent_learning_records WHERE record_id=?', (record.record_id,)).fetchone()[0]
        assert json.loads(stored) == content
        conn.execute("CREATE TRIGGER break_learning_insert BEFORE INSERT ON agent_learning_records BEGIN SELECT RAISE(ABORT,'fault'); END")
    assert owner.record_learning(LearningType.FEEDBACK, {'text': 'must not succeed'}) is None
    assert all(rec.value['content'] != {'text': 'must not succeed'} for rec in owner._in_memory.values())


def test_oversized_learning_is_explicit_not_truncated(seeded_db):
    import pytest
    from lumenis.shared.learning.memory import LearningMemory, LearningType
    owner = LearningMemory(db_path=seeded_db, enabled=True)
    with pytest.raises(ValueError, match='LEARNING_CONTENT_TOO_LARGE'):
        owner.record_learning(LearningType.FEEDBACK, {'text': 'x' * (8 * 1024 * 1024)})
    assert owner._in_memory == {}
