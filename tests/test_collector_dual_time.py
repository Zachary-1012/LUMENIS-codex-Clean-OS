# -*- coding: utf-8 -*-
"""P0-C 采集链时间模型黄金样例：_norm_cdp_note 必须双时间分离（智谱采集链审查加固）。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = pytest.mark.redline


def _make_collector():
    import collector
    return collector


def test_norm_cdp_note_dual_time():
    """采集层必须同时落 publish_date(平台) + captured_at(本机采集时刻)，来源不同绝不顶替。"""
    c = _make_collector()
    n = c._norm_cdp_note({
        'note_id': 'abc123', 'detail_publish_time': '2026-09-01 10:30:00',
        'detail_title': '广州太古汇探店', 'content': '正文', 'likes': 5, 'comments': 1,
    })
    assert n['publish_date'] == '2026-09-01', 'publish_date 应来自平台发布时间'
    assert n['captured_at'], 'captured_at 必须存在（采集层显式落盘）'
    # 双时间真实分离：captured_at 是当前采集时刻，不可能等于 2026-09-01 的历史发布时间
    assert n['captured_at'][:10] != '2026-09-01', 'captured_at 不应等于历史 publish_date（混淆即失败）'
    assert n['captured_at'][:10] >= '2026-01-01', 'captured_at 应为真实采集日期'


def test_norm_cdp_note_publish_time_missing():
    """平台发布时间缺失时 publish_date 为空，但 captured_at 仍必须存在。"""
    c = _make_collector()
    n = c._norm_cdp_note({'note_id': 'x', 'detail_title': 't'})
    assert n['publish_date'] == ''
    assert n['captured_at'], 'captured_at 即使发布时间缺失也必须存在'


def test_norm_cdp_note_preserves_platform_fields():
    """核心字段透传不被破坏。"""
    c = _make_collector()
    n = c._norm_cdp_note({
        'note_id': 'n1', 'detail_title': '标题', 'desc': '描述',
        'detail_author': '作者', 'likes': '12', 'comments': '3', 'shares': '1',
        'source_channel_override': 'x',
    })
    assert n['title'] == '标题'
    assert n['content'] == '描述'
    assert n['author_nickname'] == '作者'
    assert n['likes'] == 12
    assert n['comments'] == 3
