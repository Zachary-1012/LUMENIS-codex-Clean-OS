# -*- coding: utf-8 -*-
"""GAP-02 红线函数级直接单测（不经过 HTTP/集成层，直接断言核心纯函数口径）。

覆盖：
- subject_rules.subject_hit：正向主体词命中、跨城同名【排除词一票否决】、混合文本排除优先、
  多字段/列表/大小写；
- subject_rules.subject_hit_note / canonical_text；
- subject_rules._subject_sql_and_values：正向 OR + AND NOT 排除、占位符与参数一一对应、
  alias 前缀、词表↔LIKE 数量自洽；
- risk_engine.build_daily_report：入口稳定委托（不真正连库）。

这些是广州太古汇主体口径的最小硬证据，防止后续重构弱化/改写主体规则。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.redline


@pytest.fixture(scope='module')
def sr():
    import subject_rules as m
    return m


# ---------- subject_hit 正向命中 ----------
def test_positive_basic_hit(sr):
    assert sr.subject_hit(title='广州太古汇今日客流') is True
    assert sr.subject_hit(title='太古汇') is True
    assert sr.subject_hit(body='LV太古汇上新快闪') is True
    assert sr.subject_hit(title='dior太古汇限定', body='') is True  # 大小写不敏感


def test_hit_across_fields_and_list(sr):
    # 正向词落在 body 而非 title 仍命中
    assert sr.subject_hit(title='无关标题', body='广州太古汇会员日') is True
    # matched_keywords 传列表也能判定（_text 负责摊平）
    assert sr.subject_hit(matched_keywords=['太古汇', '商场']) is True


def test_negative_no_hit(sr):
    assert sr.subject_hit(title='今天天气真好') is False
    assert sr.subject_hit(title='', body='', content='') is False


# ---------- 排除词：跨城同名一票否决（红线核心）----------
@pytest.mark.parametrize('text', [
    '上海太古汇新店开业',
    '兴业太古汇打卡',
    '北京三里屯太古汇',
    '成都远洋太古汇',
    '深圳太古汇客流',
    '香港太古汇',
    '太古城地铁站',
])
def test_other_city_same_name_excluded(sr, text):
    assert sr.subject_hit(title=text) is False, f'跨城同名必须排除: {text}'


def test_mixed_text_exclude_wins_over_positive(sr):
    # 同时出现广州主体词与异地同名：排除词一票否决，防止把外地舆情计入太古汇
    mixed = '广州太古汇与上海太古汇同步活动'
    assert sr.subject_hit(title=mixed) is False


def test_exclude_only_triggers_when_present(sr):
    # 仅正向、无任何排除词时必须稳定命中，避免排除规则误伤
    assert sr.subject_hit(title='太古汇商场周年庆') is True


# ---------- note dict / canonical ----------
def test_subject_hit_note_dict(sr):
    assert sr.subject_hit_note({'title': '广州太古汇', 'body': 'x'}) is True
    assert sr.subject_hit_note({'title': '成都太古汇', 'body': ''}) is False
    # 缺字段不报错
    assert sr.subject_hit_note({}) is False


def test_canonical_text_concat(sr):
    out = sr.canonical_text({'title': 'A', 'body': 'B', 'content': 'C',
                             'source_keyword': '', 'matched_keywords': ''})
    assert out.startswith('A B C')


# ---------- _subject_sql_and_values 结构自洽 ----------
def test_sql_positive_and_not_exclude(sr):
    sql, values = sr._subject_sql_and_values()
    assert ' OR ' in sql
    assert 'AND NOT' in sql
    # 结构 = (正向 OR...) AND NOT (排除 OR...)
    assert sql.strip().startswith('(')
    # 占位符数量与参数数量严格一致（防 SQL/参数错位）
    assert sql.count('?') == len(values)
    n_fields = len(sr.SUBJECT_FIELDS)
    expect = (len(sr.SUBJECT_WORDS) + len(sr.SUBJECT_EXCLUDE_WORDS)) * n_fields
    assert sql.count('LIKE') == expect == len(values)
    # 所有参数都是小写包裹的 %词%
    for v in values:
        assert v.startswith('%') and v.endswith('%')
        assert v == v.lower()


def test_sql_alias_prefix(sr):
    sql_alias, _ = sr._subject_sql_and_values('n')
    # 带 alias 时每个列都带 n. 前缀
    assert 'n.title' in sql_alias and 'n.body' in sql_alias
    sql_plain, _ = sr._subject_sql_and_values('')
    assert 'n.' not in sql_plain


def test_sql_alias_keeps_placeholder_count(sr):
    sql_a, val_a = sr._subject_sql_and_values('n')
    sql_b, val_b = sr._subject_sql_and_values()
    assert sql_a.count('?') == sql_b.count('?') == len(val_a) == len(val_b)


def test_subject_sql_alias_backward_compatible(sr):
    # 历史别名 subject_sql_and_values 必须仍指向同一实现
    assert sr.subject_sql_and_values is sr._subject_sql_and_values


# ---------- 日报入口稳定性（不连库，仅验证委托契约不被改坏）----------
def test_build_daily_report_entry_stable():
    import risk_engine
    import daily_report
    assert callable(risk_engine.build_daily_report)
    assert callable(daily_report.generate_daily_digest)
