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
    """重判数据质量原则"""

    def test_no_data_deletion(self):
        """重判只更新字段，不删除数据（通过生产库验证总数）。"""
        db_path = os.environ['ZBC_DB_PATH']
        if not os.path.exists(db_path):
            pytest.skip("生产库不存在")
        conn = sqlite3.connect(db_path)
        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        conn.close()
        # 重判只更新字段不删数据；采集使 notes 只增不减，故总数不得低于建测基线 963（不写死等值）
        assert total >= 963, f"重判不应删除数据，notes 总数 {total} 低于建测基线 963"

    def test_no_empty_subject_type(self):
        """重判后不应有空/NULL subject_type。"""
        db_path = os.environ['ZBC_DB_PATH']
        if not os.path.exists(db_path):
            pytest.skip("生产库不存在")
        conn = sqlite3.connect(db_path)
        empty = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE subject_type IS NULL OR subject_type = ''"
        ).fetchone()[0]
        conn.close()
        assert empty == 0, f"仍有 {empty} 条空/NULL subject_type"

    def test_unknown_is_explicit(self):
        """不相关笔记 subject_type 应为 'unknown'，不是'未知'或空。"""
        db_path = os.environ['ZBC_DB_PATH']
        if not os.path.exists(db_path):
            pytest.skip("生产库不存在")
        conn = sqlite3.connect(db_path)
        # 不应有"未知"这种静默填充
        bad = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE subject_type = '未知'"
        ).fetchone()[0]
        conn.close()
        assert bad == 0, "存在'未知'静默填充，违反显式标记原则"

    def test_cth_notes_hit_subject(self):
        """CTH 分类的笔记应确实命中主体。"""
        db_path = os.environ['ZBC_DB_PATH']
        if not os.path.exists(db_path):
            pytest.skip("生产库不存在")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cth_notes = conn.execute(
            "SELECT title, body, content, source_keyword, matched_keywords FROM notes WHERE subject_type = 'CTH' LIMIT 20"
        ).fetchall()
        conn.close()
        assert len(cth_notes) > 0
        for n in cth_notes:
            assert subject_hit(
                title=n['title'], body=n['body'], content=n['content'],
                source_keyword=n['source_keyword'], matched_keywords=n['matched_keywords']
            ) is True, f"CTH 笔记未命中主体: {n['title']}"

    def test_unknown_notes_dont_hit_subject(self):
        """unknown 分类的笔记应确实不命中主体。"""
        db_path = os.environ['ZBC_DB_PATH']
        if not os.path.exists(db_path):
            pytest.skip("生产库不存在")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        unknown_notes = conn.execute(
            "SELECT title, body, content, source_keyword, matched_keywords FROM notes WHERE subject_type = 'unknown' LIMIT 20"
        ).fetchall()
        conn.close()
        assert len(unknown_notes) > 0
        for n in unknown_notes:
            assert subject_hit(
                title=n['title'], body=n['body'], content=n['content'],
                source_keyword=n['source_keyword'], matched_keywords=n['matched_keywords']
            ) is False, f"unknown 笔记实际命中主体: {n['title']}"


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
