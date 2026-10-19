"""Editable topic vault projections using the existing deterministic score owner."""
from datetime import date,timedelta
import hashlib,json,re
from .topic_scoring import TopicSignals,score_topic,classify_topic

def _date(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('PODCAST_TOPIC_DATE_INVALID')
    try:return date.fromisoformat(value)
    except ValueError as exc:raise ValueError('PODCAST_TOPIC_DATE_INVALID') from exc

def _text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 and c not in '\n\t' for c in value):raise ValueError('PODCAST_TOPIC_TEXT_INVALID')
    return value.strip()

def build_topic_preview(*,as_of,cards,source_bindings=None,citations=None):
    today=_date(as_of)
    if not isinstance(cards,list) or not 1<=len(cards)<=100:raise ValueError('PODCAST_TOPIC_CARDS_INVALID')
    bindings=source_bindings or {};items=[];ids=set()
    for item in cards:
        if not isinstance(item,dict) or not {'topic_id','title','planned_date'}<=set(item) or set(item)-{'topic_id','title','planned_date','signals','source_artifact_ids','notes'}:raise ValueError('PODCAST_TOPIC_CARD_INVALID')
        tid=_text(item['topic_id'],80);title=_text(item['title'],300);planned=_date(item['planned_date'])
        if tid in ids:raise ValueError('PODCAST_TOPIC_ID_DUPLICATE')
        ids.add(tid)
        values=item.get('signals',{})
        if not isinstance(values,dict) or set(values)-set(TopicSignals.__dataclass_fields__):raise ValueError('PODCAST_TOPIC_SIGNALS_INVALID')
        signals=TopicSignals(**values);score=score_topic(signals)
        refs=item.get('source_artifact_ids',[])
        if not isinstance(refs,list) or len(refs)>20 or any(not isinstance(v,str) or v not in bindings for v in refs) or len(set(refs))!=len(refs):raise ValueError('PODCAST_TOPIC_SOURCE_BINDING_REQUIRED')
        notes=item.get('notes','')
        if notes:notes=_text(notes,2000)
        if not isinstance(notes,str):raise ValueError('PODCAST_TOPIC_TEXT_INVALID')
        items.append({'topic_id':tid,'title':title,'planned_date':planned.isoformat(),'notes':notes,
          'signals':{k:getattr(signals,k) for k in TopicSignals.__dataclass_fields__},'score':score,
          'stage':classify_topic(score,signals.timeliness),'state':'scored' if score is not None else 'input_required',
          'missing_signals':[k for k in TopicSignals.__dataclass_fields__ if getattr(signals,k) is None],
          'signal_origin':'USER_ANNOTATION_NOT_LIVE_TREND','source_artifact_ids':refs,
          'source_state':'preview_read_verified_not_independent_fact_verification' if refs else 'original_user_draft_no_external_source',
          'heat':{'value':None,'state':'missing','display':'数据缺失'}})
    week=today-timedelta(days=today.weekday())
    projections={'day':[x['topic_id'] for x in items if x['planned_date']==as_of],
                 'week':[x['topic_id'] for x in items if week<=_date(x['planned_date'])<week+timedelta(days=7)],
                 'month':[x['topic_id'] for x in items if x['planned_date'][:7]==as_of[:7]]}
    from scripts import marketing_calendar
    from pathlib import Path
    calendar={'state':'reference_only_not_live_verified' if today.year==2026 else 'year_not_covered','year':2026,
        'source_owner':'scripts.marketing_calendar','source_sha256':hashlib.sha256(Path(marketing_calendar.__file__).read_bytes()).hexdigest(),
        'nodes':marketing_calendar.nodes_for_month(today.month) if today.year==2026 else [],'automatic_scheduling':False}
    payload={'as_of':as_of,'topic_cards':items,'vault_projections':projections,'calendar_reference':calendar,
             'source_preview_bindings':bindings,'source_binding_semantics':'verified_at_preview_reopen_required_for_current_use',
             'source_facts_verified':False,'automatic_selection':False}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    markdown=render_topic_markdown(payload)
    return {'state':'editable_draft','input_hash':digest,'external_fetch':False,'published':False,
      'saved_work_draft':{'title':'播客选题库 '+as_of,'kind':'podcast_episode','markdown':markdown,'payload':payload,'citations':citations or [],
       'contract':{'id':'lumenis.podcast-topic-vault','version':'1','required_payload_paths':['topic_cards','vault_projections','calendar_reference']}}}


def render_topic_markdown(payload):
    """Render the current topic-card fields without changing source or signal state."""
    markdown = '# 播客选题库\n\n信号由用户填写；缺失热度保留为空。日历是现有2026参考资料，未经实时核实。\n'
    for card in payload['topic_cards']:
        score = card.get('score')
        markdown += (f"\n## {card['title']}\n计划日期：{card.get('planned_date', 'UNKNOWN')}\n"
                     f"评分：{score if score is not None else '需补输入'}\n{card.get('notes', '')}\n")
    return markdown
