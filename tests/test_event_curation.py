# -*- coding: utf-8 -*-
"""事件中心质量分级与事件-笔记联动的单元测试（不依赖网络，直接读库/纯函数）。
运行：.venv\\Scripts\\python.exe tests\\test_event_curation.py
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import classify_event_quality, _event_title_is_noise, get_events_curated

FAILS = []
def check(name, cond):
    print(('PASS' if cond else 'FAIL'), '-', name)
    if not cond: FAILS.append(name)

# 1) 噪音/占位标题识别
check("'无明确事件' 判为噪音", _event_title_is_noise('无明确事件'))
check("'其他' 判为噪音", _event_title_is_noise('其他'))
check("'需补充原文正文后再研判' 判为噪音", _event_title_is_noise('需补充原文正文后再研判'))
check("'品牌招聘信息，非商场本体舆情' 判为噪音", _event_title_is_noise('品牌招聘信息，非商场本体舆情'))
check("真实负面标题不是噪音", not _event_title_is_noise('广州太古汇OLE员工态度投诉'))

# 2) 三级质量分类
check("单篇中性'相关讨论'→generic",
      classify_event_quality({'title': '广州太古汇｜用户互动相关讨论', 'mention_count': 1, 'risk_level': 'low'}) == 'generic')
check("中风险'相关讨论'仍→featured（安全优先不折叠风险）",
      classify_event_quality({'title': '广州太古汇｜服务投诉相关讨论', 'mention_count': 1, 'risk_level': 'medium'}) == 'featured')
check("具体负面事件→featured",
      classify_event_quality({'title': '停车场保安封路投诉待核实', 'mention_count': 1, 'risk_level': 'high'}) == 'featured')
check("多篇'相关讨论'→featured（持续升温）",
      classify_event_quality({'title': '广州太古汇｜停车/保安相关讨论', 'mention_count': 5, 'risk_level': 'low'}) == 'featured')
check("占位标题→noise",
      classify_event_quality({'title': '无事件', 'mention_count': 1, 'risk_level': 'low'}) == 'noise')

# 3) get_events_curated 返回结构完整且重点事件不含噪音
cur = get_events_curated(50)
check("curated 返回 featured/generic_count/noise_count/total 四字段",
      all(k in cur for k in ('featured', 'generic_count', 'noise_count', 'total')))
check("重点事件列表中不出现噪音标题",
      all(not _event_title_is_noise(e.get('title', '')) for e in cur['featured']))
check("重点事件按风险排序（high 在 medium 前）",
      [e.get('risk_level') for e in cur['featured']].count('high') == 0 or
      cur['featured'][0].get('risk_level') == 'high')

print('\n重点事件 %d，泛化折叠 %d，噪音隐藏 %d' % (len(cur['featured']), cur['generic_count'], cur['noise_count']))
print('\n结果:', '全部通过 ✅' if not FAILS else ('%d 项失败: %s' % (len(FAILS), FAILS)))
sys.exit(1 if FAILS else 0)
