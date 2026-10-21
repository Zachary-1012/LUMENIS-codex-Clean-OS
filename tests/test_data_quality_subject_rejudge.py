# -*- coding: utf-8 -*-
"""数据质量终验单测：subject 重判逻辑

验证：
1. subject_hit 逻辑正确（命中/排除/不命中）
2. 重判不删除数据
3. unknown 保持显式标记，不用"未知"静默填
4. None/空 → unknown 显式
"""
import os
import sqlite3
import tempfile

import pytest

from subject_rules import (
    subject_hit, subject_hit_note, subject_reason,
    SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, SUBJECT_FIELDS,
)


@pytest.fixture(autouse=True)
def explicit_reference_focus():
    from subject_context import brand_scope
    with brand_scope("guangzhou_taikoo_hui", product_id="CTH"):
        yield


class TestSubjectHitLogic:
    """主体判定逻辑"""

    def test_hit_taikoo_hui(self):
        """标题含'广州太古汇'应命中。"""
        assert subject_hit(title="广州太古汇探店") is True

    def test_hit_taikoo_short(self):
        """标题含'太古汇'应命中。"""
        assert subject_hit(title="太古汇停车场") is True

    def test_exclude_shanghai(self):
        """含'上海太古汇'应被排除词一票否决。"""
        assert subject_hit(title="上海太古汇开业") is False

    def test_exclude_chengdu(self):
        """含'成都太古汇'应被排除。"""
        assert subject_hit(title="成都太古汇活动") is False

    def test_no_hit(self):
        """不含主体词应不命中。"""
        assert subject_hit(title="今天天气真好") is False

    def test_hit_in_content(self):
        """content 字段含主体词也应命中。"""
        assert subject_hit(title="日常", content="去了太古汇逛街") is True

    def test_hit_in_body(self):
        """body 字段含主体词也应命中。"""
        assert subject_hit(title="日常", body="广州太古汇很好逛") is True

    def test_exclude_overrides_hit(self):
        """同时含主体词和排除词时，排除词优先。"""
        assert subject_hit(title="上海太古汇和广州太古汇哪个好") is False

    def test_none_fields(self):
        """None 字段不报错，按空处理。"""
        assert subject_hit(title=None, body=None, content=None) is False

    def test_subject_reason_hit(self):
        """命中时 reason 应包含'命中主体词'。"""
        reason = subject_reason({"title": "广州太古汇"})
        assert "命中主体词" in reason

    def test_subject_reason_exclude(self):
        """排除时 reason 应包含'主体排除词'。"""
        reason = subject_reason({"title": "上海太古汇"})
        assert "主体排除词" in reason

    def test_subject_reason_miss(self):
        """不命中时 reason 应包含'未命中'。"""
        reason = subject_reason({"title": "无关内容"})
        assert "未命中" in reason


class TestSubjectRejudgeDataQuality:
    """Current identity and relevance are separate; never inspect a production seed.

    The old 963-row/subject_type=CTH assertions described a historical dataset,
    not a repeatable operation. Exercise the current Database writer twice on
    synthetic rows and prove no loss, explicit unknown identity and independent
    subject relevance instead of restoring the retired conflation.
    """
    @pytest.fixture
    def rows(self, tmp_path, monkeypatch):
        import database
        from lumenis.shared.database import repository
        path = tmp_path / "subject-rejudge.sqlite3"
        repo = repository.DatabaseRepository(str(path))
        monkeypatch.setenv("ZBC_DB_PATH", str(path))
        monkeypatch.setattr(repository, "_default_repository", repo)
        database.init_db()
        inputs = [
            {"note_id": "focus", "title": "广州太古汇探店", "content": "太古汇LV"},
            {"note_id": "excluded", "title": "上海太古汇", "content": "上海兴业太古汇"},
            {"note_id": "unknown", "title": "天气", "content": "无身份来源"},
        ]
        for note in inputs:
            database.insert_note(note)
        before = repo.query_one("SELECT COUNT(*) FROM notes")[0]
        for note in inputs:
            database.insert_note(note)
        with repo.connection() as connection:
            result = [dict(r) for r in connection.execute("SELECT * FROM notes ORDER BY note_id")]
        return before, result

    def test_no_data_deletion(self, rows):
        before, after = rows
        assert before == len(after) == 3
        assert {r["note_id"] for r in after} == {"focus", "excluded", "unknown"}

    def test_no_empty_subject_type(self, rows):
        assert all(r["subject_type"] for r in rows[1])

    def test_unknown_is_explicit(self, rows):
        assert {r["subject_type"] for r in rows[1]} == {"unknown"}

    def test_cth_notes_hit_subject(self, rows):
        focused = next(r for r in rows[1] if r["note_id"] == "focus")
        assert subject_hit_note(focused) is True
        assert focused["subject_type"] == "unknown"  # A mention is not account identity.

    def test_unknown_notes_dont_hit_subject(self, rows):
        unrelated = [r for r in rows[1] if r["note_id"] != "focus"]
        assert len(unrelated) == 2
        assert all(not subject_hit_note(r) for r in unrelated)


class TestSubjectWordsProtected:
    """主体词表保护（P0 红线）"""

    def test_subject_words_non_empty(self):
        """SUBJECT_WORDS 不应为空。"""
        assert len(SUBJECT_WORDS) > 0

    def test_exclude_words_non_empty(self):
        """SUBJECT_EXCLUDE_WORDS 不应为空。"""
        assert len(SUBJECT_EXCLUDE_WORDS) > 0

    def test_guangzhou_taikoo_in_words(self):
        """'广州太古汇'应在主体词表中。"""
        assert "广州太古汇" in SUBJECT_WORDS

    def test_shanghai_in_exclude(self):
        """'上海太古汇'应在排除词表中。"""
        assert "上海太古汇" in SUBJECT_EXCLUDE_WORDS

    def test_subject_fields_complete(self):
        """SUBJECT_FIELDS 应包含五个业务字段。"""
        assert set(SUBJECT_FIELDS) == {"title", "body", "content", "source_keyword", "matched_keywords"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


def test_missing_identity_is_unknown_not_default_normal_user():
    from subject_classifier import SubjectClassifier
    result = SubjectClassifier().classify()
    assert result["subject_type"] == "unknown"
    assert result["identity_truth"] == "NOT_ESTABLISHED"
    assert result["identity_status"] == "INSUFFICIENT_EVIDENCE"
