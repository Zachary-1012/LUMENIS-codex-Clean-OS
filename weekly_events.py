import json,re,sqlite3
from datetime import datetime,timedelta

def natural_week(now=None):
    now=now or datetime.now(); start=(now-timedelta(days=now.weekday())).date(); end=start+timedelta(days=6)
    return start.isoformat(),end.isoformat()

def urgency(event):
    s=(event.get('risk_level') or '').lower(); score=float(event.get('risk_score') or 0)
    return '紧急' if s=='high' or score>=70 or any(k in (event.get('title','')+event.get('summary','')) for k in ['安全','受伤','歧视','暴力','食品','媒体曝光','报警','起诉']) else '一般'

def extract_event_fields(event, notes):
    text=' '.join([(n.get('title') or '')+' '+(n.get('content') or '') for n in notes[:20]])
    def pick(labels):
        for lab in labels:
            m=re.search(rf'{re.escape(lab)}[：: ]([^\n，。；;]{2,80})',text)
            if m:return m.group(1).strip()
        return ''
    return {'category':pick(['事件类别','类型']) or (event.get('keywords') or ['舆情事件'])[0],
            'location':pick(['地点','位置']) or '', 'person':pick(['人物','涉事']) or '',
            'process':event.get('summary') or text[:220], 'user_demand':pick(['诉求','要求','希望']) or '',
            'screenshot':next((n.get('cover') for n in notes if n.get('cover')),'')}

def weekly_payload(conn,start,end):
    events=[]
    rows=conn.execute("SELECT * FROM events WHERE COALESCE(first_seen,'')<=? AND COALESCE(last_seen,first_seen,'')>=? ORDER BY risk_score DESC,mention_count DESC",(end+' 23:59:59',start+' 00:00:00')).fetchall()
    for r in rows:
        e=dict(r); notes=[dict(x) for x in conn.execute("SELECT * FROM notes WHERE is_taikoo_verified=1 AND publish_date BETWEEN ? AND ? AND (title LIKE ? OR content LIKE ?) ORDER BY likes+comments+collects+shares DESC LIMIT 20",(start,end,'%'+(e.get('title') or '')[:20]+'%','%'+(e.get('title') or '')[:20]+'%')).fetchall()]
        e.update(extract_event_fields(e,notes)); e['urgency']=urgency(e); events.append(e)
    return {'period_start':start,'period_end':end,'urgent':[e for e in events if e['urgency']=='紧急'],'general':[e for e in events if e['urgency']=='一般'],'events':events}
