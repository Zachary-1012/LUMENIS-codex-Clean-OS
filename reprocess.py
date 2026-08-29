"""历史数据再处理与跨平台事件聚合。"""
import hashlib, json, re, os
from datetime import datetime
import database as db
import ai_analyzer
import intelligence
import web_monitor


def _event_key(title, hint, topics, event_date=''):
    """Create an auditable event cluster key using semantics + a short time window.

    A topic is not automatically an event: similar mentions are grouped only when
    their normalized incident signals fall inside the same 14-day window. This
    avoids turning a long-running category such as “服务投诉” into one endless event.
    """
    text=' '.join([str(hint or ''),str(title or ''), ' '.join(str(x) for x in (topics or []))])
    text=re.sub(r'20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?', '', text)
    text=re.sub(r'[“”"「」【】\[\]（）()]',' ',text)
    text=re.sub(r'\s+',' ',text).strip()
    keys=['停车','保安','服务','投诉','方所','闭店','撤场','开业','骚扰','安全','消防','餐饮','日料','售后','LV','Dior','Chanel','价格','厕所','扩容','调整','活动','购物','探店','设施']
    hits=[k for k in keys if k.lower() in text.lower()]
    topic='、'.join((topics or ['其他'])[:2])
    base=(topic+'|'+('、'.join(hits[:3]) if hits else re.sub(r'(广州太古汇|太古汇|天河太古汇|广州)','',text)[:12]))
    bucket='na'
    if event_date:
        try:
            from datetime import datetime as _dt
            ds=str(event_date)[:10]
            d=_dt.strptime(ds,'%Y-%m-%d').date()
            bucket=str(d.toordinal()//14)
        except Exception:
            bucket='na'
    base=base+'|'+bucket
    base=re.sub(r'[^\w\u4e00-\u9fff|、]+','',base.lower())[:80] or '其他|'+bucket
    return hashlib.sha1(base.encode('utf-8')).hexdigest()[:16]

def analyze_note_row(row, translate=False):
    note=db.note_to_dict(row)
    old_relevance=note.get('relevance_status','relevant'); old_sentiment=note.get('sentiment','neutral'); old_risk=note.get('risk_level','low')
    verified, reason=ai_analyzer.verify_taikoo_location(note.get('title',''),note.get('content',''))
    rule=ai_analyzer.analyze_note(note, provider='rule')
    rule['verified']=verified; rule['verify_reason']=reason
    review=intelligence.review_note(note, rule)
    # 主体硬过滤永远优先；品牌名但缺少地点不直接写成“相关”，保留为待复核。
    if not verified:
        with db.get_db() as conn:
            conn.execute("UPDATE notes SET is_taikoo_verified=0,verify_reason=?,relevance_status=?,verification_status=?,verification_confidence=?,ai_provider=?,ai_model=?,last_reviewed_at=datetime('now','localtime') WHERE note_id=?",
                (reason,'irrelevant',review.get('verification','rejected'),review.get('confidence',1.0),review.get('provider','rule'),intelligence.ai_status().get('model',''),note['note_id']))
            conn.execute("INSERT INTO note_review_history(note_id,old_relevance,new_relevance,old_sentiment,new_sentiment,old_risk,new_risk,reason,provider) VALUES (?,?,?,?,?,?,?,?,?)",
                (note['note_id'],old_relevance,'irrelevant',old_sentiment,old_sentiment,old_risk,old_risk,reason,review.get('provider','rule')))
        return 'rejected'
    merged={**rule, **{k:v for k,v in review.items() if k in ('sentiment','confidence','fact_basis','risk_reason','event_hint','topics')}}
    if review.get('sentiment') in ('positive','neutral','negative'): merged['sentiment']=review['sentiment']
    if review.get('summary'): merged['summary']=review['summary'][:160]
    db.update_note_analysis(note['note_id'], merged)
    review['relevance']='relevant'; review.setdefault('verification','review')
    if translate and intelligence.ai_enabled():
        text=review.get('summary') or rule.get('summary','')
        review['translations']={'en':intelligence.translate_text(text,'en'),'ko':intelligence.translate_text(text,'ko')}
    db.update_note_intelligence(note['note_id'], review)
    provider=review.get('provider','rule'); model=intelligence.ai_status().get('model','')
    with db.get_db() as conn:
        conn.execute("UPDATE notes SET relevance_score=?,content_quality=?,ai_model=?,last_reviewed_at=datetime('now','localtime') WHERE note_id=?",(float(review.get('confidence',.5)),max(.1,min(1.0,float(review.get('confidence',.5)))),model,note['note_id']))
        conn.execute("INSERT INTO note_review_history(note_id,old_relevance,new_relevance,old_sentiment,new_sentiment,old_risk,new_risk,reason,provider) VALUES (?,?,?,?,?,?,?,?,?)",
            (note['note_id'],old_relevance,'relevant',old_sentiment,merged.get('sentiment',old_sentiment),old_risk,merged.get('risk_level',old_risk),review.get('risk_reason') or reason,provider))
    return 'accepted'

def reprocess_notes(limit=5000, translate=False):
    with db.get_db() as conn:
        rows=conn.execute('SELECT * FROM notes ORDER BY id ASC LIMIT ?',(limit,)).fetchall()
    counts={'accepted':0,'rejected':0,'errors':0}
    for row in rows:
        try: counts[analyze_note_row(row,translate)] += 1
        except Exception as exc:
            counts['errors'] += 1; print('[Reprocess]',row['note_id'],exc)
    return counts


def discover_web(limit=120, translate=False):
    started=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    items=web_monitor.discover(limit)
    new=analyzed=0
    for item in items:
        if db.insert_web_mention(item): new += 1
        # 对公开网页也做同一套主体/情感/风险复核
        fake={'note_id':item.get('source_id','web'),'title':item.get('title',''),'content':item.get('content',''),'likes':0,'comments':0,'author_nickname':'','source_platform':item.get('source_platform','web')}
        verified, reason=ai_analyzer.verify_taikoo_location(fake['title'],fake['content'])
        rule=ai_analyzer.analyze_note(fake,provider='rule')
        rule['verified']=verified; rule['verify_reason']=reason
        review=intelligence.review_note(fake,rule)
        if not verified or review.get('relevance')=='irrelevant':
            review['relevance']='irrelevant'; review['verification']='rejected'
        else:
            review['relevance']='relevant'; analyzed += 1
        db.update_web_analysis(item.get('source_id') or item.get('url') or item.get('title'), {**review, **rule, 'provider':review.get('provider','rule')})
    for kw in web_monitor.feedback_keywords(items):
        db.upsert_feedback_keyword(kw, 1.0, 'web')
    feedback=web_monitor.feedback_keywords(items)
    try: db.log_web_run('multi-source','multi-query',started,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),len(items),analyzed,len(items)-analyzed,'')
    except Exception: pass
    return {'fetched':len(items),'new':new,'analyzed':analyzed,'feedback_keywords':feedback}


def build_cross_platform_events(limit=100):
    notes=db.get_notes({'verified':True},2000,0)
    web=db.get_web_mentions(500,True)
    groups={}
    for n in notes:
        hint=n.get('event_hint') or ''
        topics=n.get('topics') or ['其他']
        key=_event_key(hint,n.get('title',''),topics,n.get('publish_date') or n.get('collected_at') or '')
        groups.setdefault(key,[]).append({**n,'source_platform':'xiaohongshu'})
    for w in web:
        key=_event_key(w.get('event_hint',''),w.get('title',''),w.get('topics') or ['其他'],w.get('published_at') or w.get('fetched_at') or '')
        groups.setdefault(key,[]).append(w)
    made=[]
    for key,mentions in sorted(groups.items(),key=lambda kv:len(kv[1]),reverse=True)[:limit]:
        if len(mentions)<1: continue
        first=mentions[0]
        topic='、'.join((first.get('topics') or ['其他'])[:2])
        title=first.get('event_hint') or (f'广州太古汇｜{topic}相关讨论' if topic!='其他' else (first.get('title') or '未命名事件'))
        dates=[m.get('publish_date') or m.get('published_at') or m.get('collected_at') or m.get('fetched_at') or '' for m in mentions]
        neg=sum(1 for m in mentions if m.get('sentiment')=='negative')
        risk=max([int(m.get('risk_score',0) or 0) for m in mentions] or [0])
        risk_level='high' if risk>=60 or neg>=3 else ('medium' if risk>=30 or neg else 'low')
        event={'event_key':key,'title':title[:40],'first_seen':min(dates) if dates else '', 'last_seen':max(dates) if dates else '', 'mention_count':len(mentions), 'source_count':len(set(m.get('source_platform','unknown') for m in mentions)), 'risk_level':risk_level,'risk_score':risk,'keywords':list(dict.fromkeys([t for m in mentions for t in (m.get('topics') or [])]))[:8]}
        ai=intelligence.summarize_event(event,mentions)
        event.update(ai)
        if intelligence.ai_enabled():
            event['translations']={'en':intelligence.translate_text(ai.get('summary',''),'en'),'ko':intelligence.translate_text(ai.get('summary',''),'ko')}
        event_id=db.upsert_event(event)
        try: db.link_event_mentions(event_id, mentions)
        except Exception: pass
        made.append(event)
    return made


def full_refresh(limit=5000, web_limit=120, translate=False):
    backup=None
    try:
        backup_path=os.path.join(os.path.dirname(db.DB_PATH),'backups','pre-ai-refresh-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.db')
        backup=db.backup_database(backup_path)
    except Exception as e: print('[Refresh] backup failed:',e)
    notes=reprocess_notes(limit,translate)
    web=discover_web(web_limit,translate)
    events=build_cross_platform_events()
    return {'backup':backup,'notes':notes,'web':web,'events':len(events),'ai_enabled':intelligence.ai_enabled()}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--limit',type=int,default=5000)
    ap.add_argument('--web-limit',type=int,default=120)
    ap.add_argument('--translate',action='store_true')
    args=ap.parse_args()
    print(json.dumps(full_refresh(args.limit,args.web_limit,args.translate),ensure_ascii=False,indent=2))
