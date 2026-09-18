# -*- coding: utf-8 -*-
import sys, io, os
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
os.chdir(_root)
from lumenis.shared.reporting import export_api as E
for period in ('daily','weekly','monthly','yearly'):
    try:
        r = E.generate_report_data(period)
        s = r['summary']; tops = r['top_engagement_notes']
        top_sent = [t.get('sentiment') for t in tops]
        print(f'[{period}] {r["date_range"]} 总{s["total"]} 正{s["positive"]} 中{s["neutral"]} 负{s["negative"]} 高风险{s["high_risk"]} 事件{len(r["period_events"])} 重点笔记负面数{r["top_notes_negative_cnt"]}/{len(tops)}')
        print('   结论:', r['conclusion'][:120])
        print('   重点笔记情感顺序:', top_sent)
    except Exception as ex:
        import traceback; print(f'[{period}] 异常:', ex); traceback.print_exc()