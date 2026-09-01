# -*- coding: utf-8 -*-
"""GAP-06 传播主体/内容双维度落库测试（临时隔离库，不碰生产 data/monitor.db）。

覆盖：
- enrich_note_types 纯函数：媒体/官方识别、异常兜底空串、永不抛；
- init_db 幂等加 subject_type/content_type 两列、重复执行不报错；
- insert_note 新笔记落两列；
- get_notes/get_note_count 双维度白名单筛选，非法枚举被忽略；
- 双维度为纯增量：不加筛选时结果与既有口径一致，subject_hit 红线不受影响。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    import database as db
    db_file = str(tmp_path / 'dual_dim.db')
    monkeypatch.setattr(db, 'DB_PATH', db_file)
    db.init_db()
    db.init_db()  # 幂等：第二次不得因列已存在而报错
    return db


# ---------- 纯函数 ----------
def test_enrich_media_identified():
    from subject_classifier import enrich_note_types
    st, ct = enrich_note_types(author_name='羊城晚报', verified_type='媒体')
    assert st == 'media'
    assert ct  # 非空内容类型


def test_enrich_never_raises_on_bad_input():
    from subject_classifier import enrich_note_types
    # 传入异常类型也必须兜底，绝不向采集链抛异常
    st, ct = enrich_note_types(author_name=None, followers='not-a-number')
    assert isinstance(st, str) and isinstance(ct, str)


# ---------- 迁移幂等 ----------
def test_columns_added_idempotent(temp_db):
    import sqlite3
    conn = sqlite3.connect(temp_db.DB_PATH)
    cols = {r[1] for r in conn.execute('PRAGMA table_info(notes)')}
    conn.close()
    assert {'subject_type', 'content_type'} <= cols


def _note(nid, author='普通小红薯', **kw):
    # is_taikoo_verified=1 以满足既有 _verified_base 主体基线（与双维度无关的既有读取前提）
    base = {'note_id': nid, 'title': '广州太古汇逛街', 'content': '广州太古汇人很多',
            'author_nickname': author, 'followers': 100, 'publish_date': '2026-08-31',
            'is_taikoo_verified': 1}
    base.update(kw)
    return base


# ---------- 落库 ----------
def test_insert_note_persists_dual_dimension(temp_db):
    temp_db.insert_note(_note('n1', author='广州太古汇官方账号'))
    rows = temp_db.get_notes({}, 10, 0)
    hit = [r for r in rows if r['note_id'] == 'n1'][0]
    assert 'subject_type' in hit and 'content_type' in hit
    # 官方账号应被识别为 official（非空）
    assert hit['subject_type'] == 'official'


def test_dual_dimension_is_additive_not_breaking_subject(temp_db):
    # 主体红线：广州太古汇命中、跨城同名排除，双维度不改变该口径
    from subject_rules import subject_hit
    assert subject_hit(title='广州太古汇活动') is True
    assert subject_hit(title='上海太古汇活动') is False
    # 未加双维度筛选时，笔记正常可查
    temp_db.insert_note(_note('n2'))
    assert temp_db.get_note_count({}) >= 1


# ---------- 白名单筛选 ----------
def test_filter_whitelist_and_reject_illegal(temp_db):
    # 直接构造两列不同取值
    temp_db.insert_note(_note('a', author='广州太古汇官方账号'))
    with temp_db.get_db() as conn:
        conn.execute("UPDATE notes SET subject_type='media', content_type='ugc' WHERE note_id='a'")
        conn.execute("INSERT INTO notes(note_id,title,content,subject_type,content_type,status,is_taikoo_verified,relevance_status) "
                     "VALUES('b','广州太古汇','x','kol','commercial','active',1,'relevant')")
        conn.commit()
    media = temp_db.get_notes({'subject_type': 'media'}, 10, 0)
    assert all(r['note_id'] == 'a' for r in media) and len(media) == 1
    comm = temp_db.get_notes({'content_type': 'commercial'}, 10, 0)
    assert [r['note_id'] for r in comm] == ['b']
    # 非法枚举被忽略：不应拼进 SQL，也不应报错（退化为不按该维过滤之外的其它条件）
    illegal = temp_db.get_notes({'subject_type': "media'; DROP TABLE notes;--"}, 10, 0)
    # 表仍在、数据未丢
    assert temp_db.get_note_count({}) == 2
    assert len(illegal) == 2


# ---------- 媒体优先级与冲突解决（GAP 媒体匹配优先级） ----------
def test_media_plus_official_resolves_to_media():
    """羊城晚报官方账号：同时匹配媒体(晚报)+官方(官方)，必须判为媒体而非官方"""
    from subject_classifier import get_subject_classifier
    clf = get_subject_classifier()
    r = clf.classify(author_name='羊城晚报官方账号')
    assert r['subject_type'] == 'media'
    assert r['confidence'] >= 0.9


def test_media_keywords_cover_urban_daily():
    """南方都市报：扩充媒体关键词后应识别为媒体（此前漏判为普通用户）"""
    from subject_classifier import get_subject_classifier
    clf = get_subject_classifier()
    r = clf.classify(author_name='南方都市报')
    assert r['subject_type'] == 'media'


def test_institution_plus_official_resolves_to_institution():
    """XX协会官方：同时匹配机构+官方，必须判为机构"""
    from subject_classifier import get_subject_classifier
    clf = get_subject_classifier()
    r = clf.classify(author_name='XX协会官方')
    assert r['subject_type'] == 'institution'


def test_strong_media_high_confidence():
    """传统媒体关键词(日报/晚报/电视台/新闻等)置信度>=0.9"""
    from subject_classifier import get_subject_classifier
    clf = get_subject_classifier()
    for name in ['央视新闻', '澎湃新闻', '广州日报']:
        r = clf.classify(author_name=name)
        assert r['subject_type'] == 'media', f'{name} 应判为媒体'
        assert r['confidence'] >= 0.9, f'{name} 置信度应>=0.9'
