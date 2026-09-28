# -*- coding: utf-8 -*-
"""播客模块单元测试：确定性智能算法 + 统一实体图存储。

覆盖：
- topic_scoring：十维加权打分可复现、分级 now/soon/watch/later
- breakout：normal/breakout/viral 阈值与零基线保护
- episode_runtime：RuntimeSegment 时间合法性、validate_segments
- podcast_store：临时 DB 的 upsert/list/get/stats 闭环（不碰生产库）

AI 不参与上述任何判定，结果必须确定可复现。
"""
import os
import sys
import tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTEL = os.path.join(ROOT, "podcast", "intelligence")
for p in (ROOT, INTEL):
    if p not in sys.path:
        sys.path.insert(0, p)

from topic_scoring import TopicSignals, score_topic, classify_topic  # noqa: E402
from breakout import classify_breakout  # noqa: E402
from episode_runtime import RuntimeSegment, SegmentKind, validate_segments  # noqa: E402


# ---------- 选题打分 ----------

def test_topic_score_full_marks_is_90():
    # 八个正向维度权重和为 0.90，risk/cost 为 0 时满分即 90（确定性权重，可审计）
    sig = TopicSignals(
        demand=1.0, timeliness=1.0, novelty=1.0, human_relevance=1.0,
        guest_fit=1.0, evidence=1.0, content_yield=1.0, distribution=1.0,
        risk=0.0, cost=0.0,
    )
    assert round(score_topic(sig), 1) == 90.0


def test_topic_score_zero_is_minimum():
    # 无正向、风险与成本拉满：positive=0，penalty 被 clamp 到 0
    sig = TopicSignals(
        demand=0, timeliness=0, novelty=0, human_relevance=0, guest_fit=0,
        evidence=0, content_yield=0, distribution=0, risk=1.0, cost=1.0,
    )
    assert score_topic(sig) == 0.0


def test_topic_score_deterministic():
    sig = TopicSignals(
        demand=0.7, timeliness=0.6, novelty=0.5, evidence=0.8, human_relevance=0,
        guest_fit=0, content_yield=0, distribution=0, risk=0, cost=0,
    )
    assert score_topic(sig) == score_topic(sig) == 31.4


def test_classify_topic_buckets():
    # 真实分级：<35 rejected；timeliness>=0.85 now；>=75 soon；>=55 evergreen；else watch
    assert classify_topic(90, 1.0) == "now"
    assert classify_topic(80, 0.0) == "soon"
    assert classify_topic(60, 0.0) == "evergreen"
    assert classify_topic(40, 0.0) == "watch"
    assert classify_topic(10, 0.0) == "rejected"


# ---------- 破圈分类 ----------

def test_breakout_normal():
    assert classify_breakout(1000, 1000).value == "normal"


def test_breakout_viral():
    assert classify_breakout(50000, 10000).value == "viral"


def test_breakout_zero_baseline_safe():
    # 基线为 0 时不得除零，回落到 normal
    assert classify_breakout(999, 0).value == "normal"


# ---------- 运行时分段 ----------

def test_runtime_segment_rejects_bad_range():
    with pytest.raises(ValueError):
        RuntimeSegment("s1", 1000, 500, SegmentKind.STORY)


def test_runtime_segment_ok():
    seg = RuntimeSegment("s1", 0, 12000, SegmentKind.OPENING)
    assert seg.kind == SegmentKind.OPENING


def test_validate_segments_accepts_single_layer():
    segs = [
        RuntimeSegment("a", 0, 5000, SegmentKind.OPENING),
        RuntimeSegment("b", 5000, 12000, SegmentKind.STORY),
    ]
    assert validate_segments(segs) is None


# ---------- 存储层（临时 DB，隔离生产库） ----------

@pytest.fixture()
def store(tmp_path, monkeypatch):
    dbf = tmp_path / "podcast_test.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(dbf))
    import importlib
    import podcast_store
    importlib.reload(podcast_store)
    podcast_store.init_db()
    return podcast_store


def test_store_upsert_and_get(store):
    eid = store.upsert_entity("show", title="序境播客·测试", evidence_status="observed")
    assert eid
    got = store.get_entity(eid)
    assert got is not None
    assert got["title"] == "序境播客·测试"
    assert got["entity_type"] == "show"


def test_store_list_filter_and_stats(store):
    store.upsert_entity("show", entity_id="s-1", title="节目1")
    store.upsert_entity("episode", entity_id="e-1", title="单集1", parent_id="s-1")
    store.upsert_entity("episode", entity_id="e-2", title="单集2", parent_id="s-1")
    shows = store.list_entities(entity_type="show")
    eps = store.list_entities(entity_type="episode")
    assert len(shows) == 1 and len(eps) == 2
    children = store.list_entities(parent_id="s-1")
    assert len(children) == 2
    stats = store.get_stats()
    assert stats["total"] == 3
    assert stats["by_type"].get("show") == 1
    assert stats["by_type"].get("episode") == 2


def test_store_upsert_idempotent(store):
    # 同一 entity_id 重复写入应更新而非新增
    store.upsert_entity("topic", entity_id="t-1", title="旧标题")
    store.upsert_entity("topic", entity_id="t-1", title="新标题")
    rows = store.list_entities(entity_type="topic")
    assert len(rows) == 1
    assert rows[0]["title"] == "新标题"
