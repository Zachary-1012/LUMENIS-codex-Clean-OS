"""GAP-07 事件三类四关系：关系推断器测试（临时隔离库，不碰生产）。

原则验证：
- 三类事件 / 四类关系字典完整；
- parallel：时间相近(<=36h)且主题相关；derive：先后且强主题延续(>=2 共享)；follow：先后弱相关；
- 无主题重叠绝不连边（不伪造）；trigger 强因果不自动生成；
- 通用词（太古/古汇等）已停用，不因“都是太古汇事件”而全相连；
- 重算幂等、且只清理 [auto] 关系，手工 trigger 保留。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def graph(tmp_path, monkeypatch):
    import event_graph as eg
    from lumenis.shared.database import DatabaseRepository
    repository = DatabaseRepository(str(tmp_path / 'eg.db'))
    monkeypatch.setattr(eg, 'get_repository', lambda: repository)
    eg.init_db()
    g = eg.EventGraph(auto_load=False)
    return g


def _mk(graph, etype, title, t):
    return graph.create_event(etype, title, event_time=t, source='test')


def test_dictionaries_complete():
    from event_graph import EVENT_TYPES, RELATION_TYPES
    assert set(EVENT_TYPES) == {'marketing_event', 'propagation_event', 'public_opinion_event'}
    assert set(RELATION_TYPES) == {'trigger', 'derive', 'follow', 'parallel'}


@pytest.mark.parametrize('confidence', [0.0, None, 0.9])
def test_relation_confidence_survives_save_and_reopen(graph, confidence):
    import event_graph as eg

    source = _mk(graph, 'marketing_event', 'First source event', '2026-08-01 09:00:00')
    target = _mk(graph, 'propagation_event', 'Later source event', '2026-08-02 09:00:00')
    relation = graph.add_relation(source.event_id, target.event_id, 'follow',
                                  evidence='manual: unverified temporal hypothesis',
                                  confidence=confidence, persist=True)
    assert relation.confidence == confidence
    with eg._get_db() as connection:
        row = connection.execute('SELECT confidence FROM event_graph_relations').fetchone()
        assert row['confidence'] == confidence

    reopened = eg.EventGraph()
    assert len(reopened.relations) == 1
    assert reopened.relations[0].confidence == confidence
    assert reopened.relations[0].to_dict()['confidence'] == confidence


def test_derive_parallel_and_no_fabrication(graph):
    e1 = _mk(graph, 'marketing_event', '方所闭店公告', '2026-08-01 09:00:00')
    e2 = _mk(graph, 'propagation_event', '方所闭店后续讨论', '2026-08-03 09:00:00')  # 48h>并行窗
    e3 = _mk(graph, 'public_opinion_event', 'OLE投诉处理', '2026-08-01 10:00:00')
    e4 = _mk(graph, 'propagation_event', 'OLE投诉排队', '2026-08-01 12:00:00')
    e5 = _mk(graph, 'propagation_event', '美食节开业', '2026-08-05 09:00:00')
    res = graph.infer_and_link_relations(persist=False)
    pairs = {(r.source_event.event_id, r.target_event.event_id): r.relation_type
             for r in graph.relations}
    assert pairs.get((e1.event_id, e2.event_id)) == 'derive'      # 先后 + 强主题延续
    assert pairs.get((e3.event_id, e4.event_id)) == 'parallel'    # 同日 2h
    # e5 与其它事件无主题重叠 -> 不产生任何边
    assert all(e5.event_id not in k for k in pairs)
    # 绝不自动生成 trigger
    assert all(t != 'trigger' for t in pairs.values())
    assert res['added'] == 2
    assert res['by_type']['derive'] == 1 and res['by_type']['parallel'] == 1
    assert res['no_evidence_pairs'] >= 1


def test_follow_weak_temporal(graph):
    _mk(graph, 'propagation_event', '周年庆活动启动', '2026-08-01 09:00:00')
    _mk(graph, 'propagation_event', '周年庆客流回顾', '2026-08-06 09:00:00')  # 5 天后、弱相关
    graph.infer_and_link_relations(persist=False)
    types = [r.relation_type for r in graph.relations]
    assert 'follow' in types and 'derive' not in types


def test_stopwords_prevent_full_mesh(graph):
    # 仅共享通用词“太古汇”，停用后主题重叠为空 -> 不连边
    _mk(graph, 'propagation_event', '太古汇巡检', '2026-08-01 09:00:00')
    _mk(graph, 'propagation_event', '太古汇保洁', '2026-08-03 09:00:00')
    res = graph.infer_and_link_relations(persist=False)
    assert graph.relations == []
    assert res['added'] == 0


def test_rebuild_idempotent_and_keeps_manual(graph, persist=True):
    _mk(graph, 'propagation_event', '方所闭店公告', '2026-08-01 09:00:00')
    _mk(graph, 'propagation_event', '方所闭店后续', '2026-08-02 09:00:00')
    r1 = graph.infer_and_link_relations(persist=True)
    # 手工 trigger（无 [auto] 前缀）
    evs = list(graph.events.values())
    graph.add_relation(evs[0].event_id, evs[1].event_id, 'trigger',
                       evidence='manual: 运营确认直接触发', confidence=0.9, persist=True)
    r2 = graph.infer_and_link_relations(persist=True)  # 重算
    rel_types = sorted(r.relation_type for r in graph.relations)
    assert 'trigger' in rel_types            # 手工关系保留
    assert r1['added'] >= 1 and r2['added'] == r1['added']  # 自动边数量稳定（幂等）
    auto = [r for r in graph.relations if r.evidence.startswith('[auto]')]
    assert len(auto) == r2['added']
