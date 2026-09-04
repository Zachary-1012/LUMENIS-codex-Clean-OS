# -*- coding: utf-8 -*-
"""事件中心质量分级与事件-笔记联动的单元测试（不依赖网络，直接读库/纯函数）。
运行：.venv\\Scripts\\python.exe -m pytest tests\\test_event_curation.py
"""
import os, sys, io
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import classify_event_quality, _event_title_is_noise, get_events_curated


def test_event_title_is_noise():
    """噪音/占位标题识别。"""
    assert _event_title_is_noise('无明确事件')
    assert _event_title_is_noise('其他')
    assert _event_title_is_noise('需补充原文正文后再研判')
    assert _event_title_is_noise('品牌招聘信息，非商场本体舆情')
    assert not _event_title_is_noise('广州太古汇OLE员工态度投诉')


def test_classify_event_quality():
    """三级质量分类。"""
    # 单篇中性'相关讨论'→generic
    assert classify_event_quality({
        'title': '广州太古汇｜用户互动相关讨论',
        'mention_count': 1, 'risk_level': 'low'
    }) == 'generic'
    # 中风险'相关讨论'仍→featured（安全优先不折叠风险）
    assert classify_event_quality({
        'title': '广州太古汇｜服务投诉相关讨论',
        'mention_count': 1, 'risk_level': 'medium'
    }) == 'featured'
    # 具体负面事件→featured
    assert classify_event_quality({
        'title': '停车场保安封路投诉待核实',
        'mention_count': 1, 'risk_level': 'high'
    }) == 'featured'
    # 多篇'相关讨论'→featured（持续升温）
    assert classify_event_quality({
        'title': '广州太古汇｜停车/保安相关讨论',
        'mention_count': 5, 'risk_level': 'low'
    }) == 'featured'
    # 占位标题→noise
    assert classify_event_quality({
        'title': '无事件', 'mention_count': 1, 'risk_level': 'low'
    }) == 'noise'


def test_get_events_curated_structure():
    """get_events_curated 返回结构完整且重点事件不含噪音。"""
    cur = get_events_curated(50)
    # 四字段完整
    assert all(k in cur for k in ('featured', 'generic_count', 'noise_count', 'total'))
    # 重点事件列表中不出现噪音标题
    assert all(not _event_title_is_noise(e.get('title', '')) for e in cur['featured'])
    # 重点事件按风险排序（high 在 medium 前）
    featured = cur['featured']
    if featured:
        high_count = [e.get('risk_level') for e in featured].count('high')
        if high_count > 0:
            assert featured[0].get('risk_level') == 'high'


if __name__ == '__main__':
    test_event_title_is_noise()
    test_classify_event_quality()
    test_get_events_curated_structure()
    print('事件中心质量分级: 全部通过')
