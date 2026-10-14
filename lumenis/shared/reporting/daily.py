"""
LUMENIS scoped daily reporting module
================================================
从"看到数据"升级为"输出决策信息"

核心能力：
1. 今日舆情摘要：今日发现、有效关联、正向/中性/风险分布
2. AI事件总结：事件聚类、风险等级、AI总结、处置建议
3. 管理层摘要：一句话决策信息
4. 关键洞察：数据背后的趋势信号
5. 行动建议：可执行的下一步动作
6. 风险指数：综合情绪强度、传播量、互动规模、事件持续时间
7. 品牌健康度：0-100分，综合正面占比、风险水平、互动质量

设计原则：
- 无AI Key也能跑（规则引擎兜底）
- 所有结论可追溯到原始数据
- 不把单一用户指控写成已证实事实
"""
import json
import math
import os
import re
from datetime import date, datetime, timedelta

import ai_analyzer
import canonical_metrics as cm
import database as db
import intelligence


def _ai_allowed_for_report():
    """Return whether report generation may invoke an external/local model."""
    return os.environ.get('ZBC_TEST_OFFLINE', '').strip() != '1'


def _effective_relevance_notes(notes, *, source_complete):
    """Return only admitted relevant rows when every observed row is classified."""
    recognized = {'relevant', 'accepted', 'irrelevant', 'rejected'}
    values = [str(note.get('relevance_status') or '').strip().lower()
              if isinstance(note, dict) else '' for note in notes]
    known = sum(value in recognized for value in values)
    complete = source_complete and known == len(notes)
    effective = ([note for note, value in zip(notes, values)
                  if value in {'relevant', 'accepted'}] if complete else [])
    return effective, known, complete


# ============== 风险指数计算 ==============

def calculate_risk_index(notes, events, period_days=1):
    """Calculate the composite risk index only when every input dimension is known."""
    if not notes or events is None or not isinstance(events, (list, tuple)):
        return None

    sentiment = cm.sentiment_count(notes)
    risks = cm.risk_count(notes)
    if sentiment["known"] == 0 or sentiment["known"] != sentiment["total"]:
        return None
    if risks["missing"] or risks["other"] or risks["total"] != len(notes):
        return None

    engagement = cm.engagement_stats(notes, keys=("likes", "comments"))
    if engagement["quality"]["state"] != "COMPLETE":
        return None

    duration_score = 0.0
    duration_samples = 0
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("status"), str) or not event["status"].strip():
            return None
        if cm.engagement_count(event.get("source_count")) is None:
            return None
        if event["status"] != "active":
            continue
        first, last = event.get("first_seen"), event.get("last_seen")
        if not isinstance(first, str) or not isinstance(last, str) or not first or not last:
            return None
        try:
            first_day = datetime.strptime(first[:10], "%Y-%m-%d")
            last_day = datetime.strptime(last[:10], "%Y-%m-%d")
        except ValueError:
            return None
        if last_day < first_day:
            return None
        if duration_samples < 3:
            duration_score += min(5, ((last_day - first_day).days + 1) * 0.5)
        duration_samples += 1

    negative_ratio = cm.neg_ratio(sentiment)
    if negative_ratio is None:
        return None

    negative_engagement = sum(
        int(note["likes"]) + int(note["comments"]) * 2
        for note in notes if note.get("sentiment") == "negative"
    )
    negative_score = min(30, negative_ratio * 60)
    risk_count_score = min(25, risks["high"] * 5 + risks["critical"] * 10 + risks["medium"] * 1.5)
    engagement_score = min(20, negative_engagement / 50)
    duration_score = min(15, duration_score)
    multisource_count = sum(1 for event in events if int(event["source_count"]) >= 2)
    multisource_score = min(10, multisource_count * 3)
    score = round(negative_score + risk_count_score + engagement_score + duration_score + multisource_score, 1)
    return min(100.0, max(0.0, score))

def calculate_brand_health_score(notes, risk_index):
    """Calculate the health score only from complete, measured dimensions."""
    if not notes or type(risk_index) not in (int, float) or not math.isfinite(risk_index):
        return None

    sentiments = cm.sentiment_count(notes)
    if sentiments["known"] == 0 or sentiments["known"] != sentiments["total"]:
        return None
    positive_ratio = cm.pos_ratio(sentiments)
    if positive_ratio is None:
        return None
    risks = cm.risk_count(notes)
    if risks['missing'] or risks['other'] or risks['total'] != len(notes):
        return None

    engagement = cm.engagement_stats(notes, keys=("likes", "comments"))
    if engagement["quality"]["state"] != "COMPLETE":
        return None
    official_values = [note.get("is_official") for note in notes if isinstance(note, dict)]
    if len(official_values) != len(notes) or any(value not in (0, 1, False, True) for value in official_values):
        return None

    positive_engagement = sum(
        int(note["likes"]) + int(note["comments"])
        for note in notes if note.get("sentiment") == "positive"
    )
    total_engagement = sum(int(note["likes"]) + int(note["comments"]) for note in notes)
    engagement_ratio = cm.safe_ratio(positive_engagement, total_engagement)
    if engagement_ratio is None:
        return None
    engagement_quality = engagement_ratio * 20
    positive_score = positive_ratio * 40
    risk_score = max(0.0, 30.0 - float(risk_index) * 0.3)
    official_score = min(10, sum(1 for value in official_values if value in (1, True)) * 2)
    health = round(positive_score + risk_score + engagement_quality + official_score, 1)
    return min(100.0, max(0.0, health))


# ============== 今日舆情摘要 ==============

def _collection_health(date_str=None):
    """采集完整性保护：判断当日采集链路是否真的成功过。
    返回 {'complete': True/False/None, 'state':..., 'detail':...}
    complete=False 时，报告不得写“今日无舆情”结论。"""
    date_str = date_str or datetime.now().strftime('%Y-%m-%d')
    # 1) 熔断状态
    try:
        import xhs_cookie_bridge as xb
        circ = xb.get_circuit_state()
        if circ.get('open'):
            return {'complete': False, 'state': circ.get('state'), 'detail': '采集熔断中：' + str(circ.get('detail', ''))}
    except Exception:
        pass
    # 2) 当日 collection_logs 各状态
    try:
        rows = db.query_all(
            "SELECT status FROM collection_logs WHERE date(finished_at)=? ", (date_str,)) if hasattr(db, 'query_all') else None
        if rows is None:
            with db.get_db() as conn:
                rows = [r[0] for r in conn.execute(
                    "SELECT status FROM collection_logs WHERE date(finished_at)=date(?)", (date_str,)).fetchall()]
        states = [r if isinstance(r, str) else (r.get('status') if isinstance(r, dict) else None) for r in rows]
        states = [s for s in states if s]
        if not states:
            return {'complete': None, 'state': 'NO_RUN', 'detail': '当日尚无采集记录'}
        ok = sum(1 for s in states if s in ('SUCCESS', 'EMPTY'))
        bad = sum(1 for s in states if s in ('BLOCKED', 'AUTH_FAILED', 'CAPTCHA', 'NETWORK_ERROR'))
        if ok == 0 and bad > 0:
            return {'complete': False, 'state': 'ALL_FAILED', 'detail': f'当日 {bad} 次采集均未成功（被拦截/网络异常）'}
        return {'complete': True, 'state': 'OK', 'detail': f'当日成功 {ok} 批'}
    except Exception as e:
        return {'complete': None, 'state': 'UNKNOWN', 'detail': str(e)[:80]}


def generate_today_summary(date_str=None, *, scope=None):
    """
    生成今日舆情摘要
    返回结构化数据：
    {
        'date': '2026-08-26',
        'total_found': 56,      # 今日发现（原始采集）
        'effective_count': 23,   # 有效关联（通过AI过滤层）
        'positive_count': 14,    # 正向
        'neutral_count': 6,      # 中性
        'risk_count': 3,         # 风险（中+高风险）
        'risk_index': 72.5,      # 风险指数
        'brand_health_score': 68.0,  # 品牌健康度
    }
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    try:
        parsed_date = date.fromisoformat(str(date_str))
        if parsed_date.isoformat() != str(date_str):
            raise ValueError('REPORT_DATE_INVALID')
        exact = db._normalize_event_scope(scope, allow_global=True)
    except (TypeError, ValueError) as exc:
        raise ValueError('REPORT_SCOPE_OR_DATE_INVALID') from exc

    # Consume only source rows whose current scope Evidence and Canonical
    # projection agree. Classification and arithmetic remain useful without AI.
    source_read = db.get_scoped_event_source_rows(
        exact, source_types=('note', 'web_mention'), date_start=date_str, date_end=date_str, limit=5000,
    )
    today_notes = source_read['sources']
    source_complete = not source_read['truncated'] and not source_read['rejected_count']
    effective_notes, known_relevance, relevance_complete = _effective_relevance_notes(
        today_notes, source_complete=source_complete)
    effective_count = len(effective_notes) if relevance_complete else None
    total_found = len(today_notes) if source_complete else None

    _sce = cm.sentiment_count(effective_notes)
    _rce = cm.risk_count(effective_notes)
    positive = _sce['positive'] if relevance_complete and _sce['known'] else None
    neutral = _sce['neutral'] if relevance_complete and _sce['known'] else None
    risk = (_rce['high'] + _rce['medium']
            if relevance_complete and _rce['total'] and not _rce['missing'] and not _rce['other'] else None)

    # 今日事件
    events_read = db.get_scoped_events(500, scope=exact, date_start=date_str, date_end=date_str)
    today_events = events_read['events']
    events_complete = not events_read['truncated'] and not events_read['rejected_count']

    risk_index = calculate_risk_index(effective_notes, today_events) if relevance_complete and events_complete else None
    brand_health = calculate_brand_health_score(effective_notes, risk_index) if relevance_complete and events_complete else None

    return {
        'date': date_str,
        'total_found': total_found,
        'effective_count': effective_count,
        'relevance_coverage': {'known': known_relevance if source_complete else None,
                               'total': len(today_notes) if source_complete else None,
                               'unknown': len(today_notes) - known_relevance if source_complete else None,
                               'observed': len(today_notes)},
        'positive_count': positive,
        'neutral_count': neutral,
        'negative_count': _sce['negative'] if relevance_complete and _sce['known'] else None,
        'sentiment_coverage': {'known': _sce['known'] if relevance_complete else None,
                              'total': len(effective_notes) if relevance_complete else None,
                              'unknown': _sce['unknown'] if relevance_complete else None},
        'risk_coverage': {'known': _rce['total'] - _rce['missing'] - _rce['other'] if relevance_complete else None,
                          'total': _rce['total'] if relevance_complete else None,
                          'missing': _rce['missing'] if relevance_complete else None,
                          'other': _rce['other'] if relevance_complete else None,
                          'observed': _rce['total'] if relevance_complete else None},
        'risk_count': risk,
        'risk_index': risk_index,
        'brand_health_score': brand_health,
        'events_count': len(today_events) if events_complete else None,
        'collection_health': {**_collection_health(date_str), 'scope': 'system-global'},
        'scope': exact,
        'source_state': source_read['state'],
        'source_coverage': {'complete': source_complete,
                            'observed': len(today_notes),
                            'candidates': source_read['candidate_count'],
                            'rejected': source_read['rejected_count'],
                            'truncated': source_read['truncated'],
                            'source_types': ['note', 'web_mention']},
        'event_coverage': {'complete': events_complete,
                           'observed': len(today_events),
                           'candidates': events_read['candidate_count'],
                           'rejected': events_read['rejected_count'],
                           'truncated': events_read['truncated']},
        'source_rejected_count': source_read['rejected_count'],
        'source_truncated': source_read['truncated'],
        'event_rejected_count': events_read['rejected_count'],
        'event_truncated': events_read['truncated'],
    }


# ============== AI事件总结 ==============

def generate_event_insight(event, notes):
    """
    为单个事件生成AI总结
    返回：
    {
        'event_title': '消费者反馈停车体验',
        'risk_level': 'medium',
        'ai_summary': '近期部分消费者讨论停车收费及停车指引问题...',
        'recommended_action': '优化停车指引展示，加强客服解释统一口径。',
        'sentiment_trend': '负面为主，有扩散趋势',
        'propagation_analysis': '主要在小红书传播，互动量中等',
        'key_voices': [...],
    }
    """
    event_title = event.get('title', '未命名事件')
    risk_level = event.get('risk_level') or 'unknown'
    mention_count = event.get('mention_count', 0)
    source_count = event.get('source_count', 1)

    # 关联笔记
    event_notes = [n for n in notes if any(
        kw in (n.get('title', '') + n.get('content', ''))
        for kw in (event.get('keywords') or [])[:5]
    )][:10]

    if not event_notes:
        event_notes = [n for n in notes if n.get('risk_level') == risk_level][:5]

    # 情感趋势
    neg_count = sum(1 for n in event_notes if n.get('sentiment') == 'negative')
    pos_count = sum(1 for n in event_notes if n.get('sentiment') == 'positive')
    if neg_count > pos_count * 2:
        sentiment_trend = '负面为主，需关注扩散'
    elif neg_count > pos_count:
        sentiment_trend = '偏负面，持续观察'
    elif pos_count > neg_count:
        sentiment_trend = '偏正面，口碑良好'
    else:
        sentiment_trend = '正负交织，观点分化'

    # 传播分析
    total_eng = sum(int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0) for n in event_notes)
    if total_eng > 500:
        propagation = '传播热度较高，互动活跃'
    elif total_eng > 100:
        propagation = '有一定传播量，互动中等'
    else:
        propagation = '传播量有限，尚未形成大规模讨论'

    if source_count >= 2:
        propagation += '，多平台交叉出现'

    # 关键声音
    key_voices = []
    for n in sorted(event_notes, key=lambda x: int(x.get('likes', 0) or 0) + int(x.get('comments', 0) or 0), reverse=True)[:3]:
        key_voices.append({
            'author': n.get('author_nickname', '匿名'),
            'title': (n.get('title', '') or '无标题')[:40],
            'engagement': int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0),
            'sentiment': n.get('sentiment', 'neutral'),
            'url': n.get('url', ''),
        })

    # AI深度总结（如果AI可用）
    ai_summary = ''
    recommended_action = ''
    if _ai_allowed_for_report() and intelligence.ai_enabled() and event_notes:
        ai_result = _ai_summarize_event(event, event_notes)
        if ai_result:
            ai_summary = ai_result.get('summary', '')
            recommended_action = ai_result.get('recommended_action', '')

    # 规则引擎兜底
    if not ai_summary:
        risk_label = {'high': '高风险', 'medium': '中风险', 'low': '低风险'}.get(risk_level, '风险等级未知')
        ai_summary = (f'该事件共涉及{mention_count}条提及，{sentiment_trend}。'
                     f'{propagation}。目前信息主要来自用户分享，事实仍需进一步核实。')

    if not recommended_action:
        if risk_level == 'high':
            recommended_action = '建议24小时内核查事实，准备官方回应口径，持续监测传播趋势。'
        elif risk_level == 'medium':
            recommended_action = '建议关注事件发展，收集更多用户反馈，必要时主动沟通改善。'
        elif risk_level == 'low':
            recommended_action = '持续观察即可，暂不需要主动介入。'
        else:
            recommended_action = '风险等级尚未核实，请先补充或核验风险数据。'

    return {
        'event_id': event.get('id'),
        'event_title': event_title[:50],
        'risk_level': risk_level,
        'risk_score': event.get('risk_score'),
        'mention_count': mention_count,
        'source_count': source_count,
        'ai_summary': ai_summary[:200],
        'recommended_action': recommended_action[:150],
        'sentiment_trend': sentiment_trend,
        'propagation_analysis': propagation,
        'key_voices': key_voices,
        'first_seen': event.get('first_seen', ''),
        'last_seen': event.get('last_seen', ''),
        'fact_status': event.get('fact_status', 'unconfirmed'),
    }


def _ai_summarize_event(event, notes):
    """AI事件深度总结。"""
    sample = [{'title': n.get('title', ''), 'summary': n.get('summary', ''),
               'sentiment': n.get('sentiment', 'neutral'), 'engagement': int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0)}
              for n in notes[:10]]

    system = '''你是当前已授权业务范围的舆情事件分析助手。把同一事件的多条用户提及凝练成管理层可执行的摘要，不得猜测主体身份。

输出严格JSON：
{
  "summary": "不超过100字，客观描述事件现状，不把单一用户指控写成事实",
  "recommended_action": "不超过80字，给出具体可执行的建议动作",
  "fact_status": "confirmed|partially_confirmed|unconfirmed"
}

注意：
- 只有多个独立来源交叉验证才能写confirmed
- 单一用户体验分享必须保持unconfirmed
- 建议要具体，不要说"加强管理"这种空话
'''
    user = json.dumps({'event': event.get('title', ''), 'mentions': sample}, ensure_ascii=False)

    raw, provider, _ = intelligence.chat(system, user, level='low', use_cache=True,
                                         temperature=0.0, max_tokens=600, pack_id='glm_4_5_air')
    data = intelligence._json_from_text(raw)
    if data:
        data['provider'] = provider
        return data
    return None


# ============== 关键洞察 & 行动建议 ==============

def generate_key_insights(notes, events, summary):
    """
    生成3-5条关键洞察
    每条洞察：数据信号 + 趋势判断 + 业务含义
    """
    insights = []
    total = len(notes)

    if total == 0:
        return [{'insight': '今日暂无有效舆情数据，建议检查采集任务是否正常运行。', 'type': 'system'}]

    # 洞察1：只在样本情感分类完整时计算占比，不能把未知类别当作零。
    sentiment = cm.sentiment_count(notes)
    if sentiment['known'] == total and sentiment['known'] > 0:
        pos = sentiment['positive']
        neg = sentiment['negative']
        denominator = sentiment['known']
        pos_pct = round(pos / denominator * 100, 1)
        neg_pct = round(neg / denominator * 100, 1)

        if neg_pct > 30:
            insights.append({
                'insight': f'今日负面占比{neg_pct}%，高于警戒线（30%），需重点关注负面内容的扩散趋势。',
                'type': 'risk',
                'metric': f'负面{neg}条 / 正面{pos}条（已分类{denominator}/{total}条）'
            })
        elif pos_pct > 60:
            insights.append({
                'insight': f'今日正面占比{pos_pct}%，品牌口碑整体健康，可关注正向内容的传播放大机会。',
                'type': 'opportunity',
                'metric': f'正面{pos}条 / 负面{neg}条（已分类{denominator}/{total}条）'
            })
        else:
            insights.append({
                'insight': f'今日正面占比{pos_pct}%，负面占比{neg_pct}%；情感分类完整，可据此观察声量结构。',
                'type': 'neutral',
                'metric': f'正面{pos}条 / 负面{neg}条（已分类{denominator}/{total}条）'
            })
    else:
        insights.append({
            'insight': '情感分类覆盖不足，暂不能计算正负面比例或判断声量结构。',
            'type': 'data_gap',
            'metric': f'已分类{sentiment["known"]}/{total}条；未知{sentiment["unknown"]}条'
        })

    # 洞察2：风险事件
    high_events = [e for e in events if e.get('risk_level') == 'high']
    if high_events:
        measured_scores = [e['risk_score'] for e in high_events if e.get('risk_score') is not None]
        score_summary = f'最高风险分{max(measured_scores)}' if measured_scores else '风险分未取得'
        insights.append({
            'insight': f'已识别{len(high_events)}个高风险事件，{score_summary}，建议优先处置。',
            'type': 'risk',
            'metric': f'高风险事件{len(high_events)}个'
        })

    # Derive topics only from the already scope-verified report input. The old
    # homepage helper silently read its legacy reference Subject and cannot be
    # used for a generic CTH/BMP/GLOBAL report.
    topic_counts = {}
    for note in notes:
        raw_topics = note.get('topics')
        if isinstance(raw_topics, str):
            try:
                parsed_topics = json.loads(raw_topics)
            except (TypeError, ValueError):
                parsed_topics = [item.strip() for item in raw_topics.split(',')]
        else:
            parsed_topics = raw_topics
        if not isinstance(parsed_topics, (list, tuple)):
            continue
        for topic in {item.strip() for item in parsed_topics
                      if isinstance(item, str) and item.strip()}:
            bucket = topic_counts.setdefault(topic, {'topic': topic, 'count': 0,
                                                      'positive': 0, 'neutral': 0,
                                                      'negative': 0, 'unknown': 0})
            bucket['count'] += 1
            sentiment_value = str(note.get('sentiment') or 'unknown').strip().lower()
            bucket[sentiment_value if sentiment_value in {'positive', 'neutral', 'negative'} else 'unknown'] += 1
    topics = []
    for bucket in topic_counts.values():
        known = {key: bucket[key] for key in ('positive', 'neutral', 'negative')}
        bucket['sentiment'] = max(known, key=known.get) if sum(known.values()) else 'unknown'
        topics.append(bucket)
    topics.sort(key=lambda item: (item['count'], item[item['sentiment']]), reverse=True)
    topics = topics[:5]
    if topics:
        top_topic = topics[0]
        insights.append({
            'insight': f'当前已核验记录中提及较多的话题为「{top_topic["topic"]}」（{top_topic["count"]}条），'
                      f'已分类样本情感倾向{top_topic.get("sentiment", "unknown")}。',
            'type': 'trend',
            'metric': f'{top_topic["count"]}条提及'
        })

    # 洞察4：传播力
    engagement = cm.engagement_stats(notes, keys=('likes', 'comments'))
    total_eng = engagement['sum']
    if total_eng is not None and total_eng > 1000:
        hot_note = max(notes, key=lambda x: int(x['likes']) + int(x['comments']))
        insights.append({
            'insight': f'今日总互动量{total_eng}，最热内容「{(hot_note.get("title", "") or "无标题")[:20]}」'
                      f'互动{int(hot_note["likes"]) + int(hot_note["comments"])}，建议关注其传播走向。',
            'type': 'trend',
            'metric': f'总互动{total_eng}'
        })

    # Pending counts are limited to the same verified rows as the report.
    pending_filter_count = sum(
        1 for note in notes
        if str(note.get('ai_filter_status') or '').strip().lower() == 'pending'
    )
    if pending_filter_count > 100:
        insights.append({
            'insight': f'当前范围有{pending_filter_count}条记录待筛选复核。',
            'type': 'system',
            'metric': f'待复核{pending_filter_count}条'
        })

    return insights[:5]


def _measured_negative_percentage(summary):
    """Return a negative percentage only when its classified denominator is complete."""
    coverage = summary.get('sentiment_coverage') or {}
    negative = summary.get('negative_count')
    known = coverage.get('known')
    total = coverage.get('total')
    if (type(negative) is not int or type(known) is not int or type(total) is not int
            or known <= 0 or known != total or negative < 0 or negative > known):
        return None
    return round(negative / known * 100, 1)


def _rule_executive_insight(summary, events):
    """Build a deterministic summary without turning unclassified data into zero."""
    negative_pct = _measured_negative_percentage(summary)
    high_risk = sum(1 for event in events if event.get('risk_level') == 'high')
    health = summary.get('brand_health_score')
    risk_count = summary.get('risk_count')
    if negative_pct is None:
        priority = 'high' if high_risk >= 2 else 'medium' if high_risk else 'unknown'
        executive = ('情感分类覆盖不足，暂不能计算负面占比或判定总体风险；'
                     f'已识别高风险事件{high_risk}起，品牌健康度为{health if health is not None else "—"}。')
        key_metric = '负面占比—'
    elif risk_count is None:
        priority = 'high' if negative_pct > 30 or high_risk >= 2 else 'medium' if negative_pct > 15 or high_risk else 'unknown'
        executive = (f'已分类样本负面占比{negative_pct}%；风险等级覆盖不足，暂不能判断总体风险。'
                     f'已识别高风险事件{high_risk}起，品牌健康度为{health if health is not None else "—"}。')
        key_metric = f'负面占比{negative_pct}%（完整分类样本）'
    else:
        priority = 'high' if negative_pct > 30 or high_risk >= 2 else 'medium' if negative_pct > 15 or high_risk else 'low'
        executive = (f'今日有效舆情{summary.get("effective_count", 0)}条，负面占比{negative_pct}%，'
                     f'已识别高风险事件{high_risk}起，品牌健康度为{health if health is not None else "—"}。')
        key_metric = f'负面占比{negative_pct}%'
    return {
        'executive_insight': executive,
        'priority': priority,
        'focus_area': '综合舆情' if negative_pct is not None else '数据质量核验',
        'key_metric': key_metric,
        'provider': 'rule_fallback',
    }


def generate_action_items(insights, events, summary, notes=None):
    """
    基于洞察生成行动建议清单
    每条：优先级 + 具体动作 + 负责方向 + 时限
    """
    actions = []

    # 高风险事件 -> 紧急行动
    high_events = [e for e in events if e.get('risk_level') == 'high']
    for e in high_events[:2]:
        actions.append({
            'priority': '紧急',
            'action': f'核查事件「{e.get("title", "未命名")[:20]}」的事实真相，收集更多独立来源验证。',
            'owner': '舆情/客服团队',
            'deadline': '24小时内',
            'event_id': e.get('id')
        })

    # 中风险事件 -> 关注行动
    med_events = [e for e in events if e.get('risk_level') == 'medium']
    if med_events:
        actions.append({
            'priority': '高',
            'action': f'持续关注{len(med_events)}个中风险事件发展，准备应对预案，必要时主动沟通。',
            'owner': '舆情/运营团队',
            'deadline': '本周内',
        })

    # 风险和情感缺失时不将 None 与数字比较，也不推断其为零。
    risk_count = summary.get('risk_count')
    positive_count = summary.get('positive_count')
    if risk_count is None:
        actions.append({
            'priority': '待核实',
            'action': '风险等级覆盖不足，暂不能统计风险内容；请先核验缺失风险数据。',
            'owner': '数据分析团队',
            'deadline': '本周期内',
        })
    elif risk_count > 5:
        actions.append({
            'priority': '高',
            'action': f'今日有{risk_count}条风险内容，建议客服团队逐一查看负面笔记，主动联系用户解决问题。',
            'owner': '客服团队',
            'deadline': '48小时内',
        })

    # 正向机会 -> 营销行动
    if positive_count is not None and risk_count is not None and positive_count > risk_count * 2:
        actions.append({
            'priority': '中',
            'action': '今日正面声量占优，建议营销团队筛选优质UGC内容，考虑转发或二次传播放大正向口碑。',
            'owner': '营销/社媒团队',
            'deadline': '本周内',
        })

    # Data quality actions use the exact scope-verified rows used by the report.
    pending_filter_count = sum(
        1 for note in (notes or [])
        if str(note.get('ai_filter_status') or '').strip().lower() == 'pending'
    )
    if pending_filter_count > 50:
        actions.append({
            'priority': '中',
            'action': f'复核当前范围内{pending_filter_count}条待筛选记录，保留未知状态并按现有规则处理。',
            'owner': '数据分析团队',
            'deadline': '今日内',
        })

    if not actions:
        sentiment_coverage = summary.get('sentiment_coverage') or {}
        risk_coverage = summary.get('risk_coverage') or {}
        metrics_complete = (
            summary.get('positive_count') is not None
            and summary.get('negative_count') is not None
            and summary.get('risk_count') is not None
            and sentiment_coverage.get('known') == sentiment_coverage.get('total')
            and risk_coverage.get('known') == risk_coverage.get('total')
        )
        actions.append({
            'priority': '常规' if metrics_complete else '待补数据',
            'action': ('今日已知指标未触发预警阈值，可按常规节奏监测。'
                       if metrics_complete else '当前指标覆盖不足，不能判定整体平稳；请补充缺失分类或风险数据。'),
            'owner': '舆情团队' if metrics_complete else '数据分析团队',
            'deadline': '持续',
        })

    return actions[:5]


# ============== 管理层摘要 ==============

def generate_executive_summary(summary, insights, actions):
    """Summarize only measured metrics; unavailable scores stay visibly unknown."""
    risk_index = summary.get('risk_index')
    health = summary.get('brand_health_score')
    effective = summary.get('effective_count', 0)
    risk_count = summary.get('risk_count')
    coll = summary.get('collection_health') or {}

    if coll.get('complete') is False and effective == 0:
        return ('⚠️ 数据采集异常：本周期数据不完整，因此不对“无新增舆情/风险较低”作结论；'
                '请恢复采集后再评估。')

    if risk_index is None:
        risk_desc, risk_display = '风险数据不足，暂不能计算风险指数', '—'
    else:
        risk_desc = '风险偏高' if risk_index >= 60 else '风险中等' if risk_index >= 30 else '风险较低'
        risk_display = risk_index

    if health is None:
        health_desc, health_display = '品牌健康度数据不足', '—'
    else:
        health_desc = '品牌健康度良好' if health >= 70 else '品牌健康度一般' if health >= 50 else '品牌健康度需关注'
        health_display = health

    risk_count_display = '—' if risk_count is None else risk_count
    top_action = actions[0]['action'][:40] if actions else '按常规节奏监测'
    return (f'今日监测到{effective}条有效舆情，{risk_desc}（风险指数{risk_display}），'
            f'{health_desc}（{health_display}分）。{risk_count_display}条内容需关注。'
            f'首要行动：{top_action}…')

# ============== 完整日报生成 ==============

def generate_daily_digest(date_str=None, *, scope=None):
    """
    Generate a complete deterministic daily digest for an authorized scope.

    The legacy date-only digest table cannot preserve focus and version lineage;
    this function returns an unsaved result for the existing SavedWork flow.
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    exact = db._normalize_event_scope(scope, allow_global=True)
    # 1. 今日摘要。No implicit Subject and no AI gate for deterministic results.
    summary = generate_today_summary(date_str, scope=exact)

    # 2. Only current scope-verified source records.
    note_read = db.get_scoped_event_source_rows(
        exact, source_types=('note', 'web_mention'), date_start=date_str, date_end=date_str, limit=5000,
    )
    source_complete = not note_read['truncated'] and not note_read['rejected_count']
    effective_notes, _known_relevance, relevance_complete = _effective_relevance_notes(
        note_read['sources'], source_complete=source_complete)

    # 3. Events are read only after each event/source Evidence and Canonical
    # reference has been rechecked by the existing database owner.
    event_read = db.get_scoped_events(
        500, scope=exact, date_start=date_str, date_end=date_str, include_sources=True,
    )
    today_events = event_read['events']

    event_complete = not event_read['truncated'] and not event_read['rejected_count']
    coverage_complete = source_complete and relevance_complete and event_complete

    # Incomplete capped reads remain useful as an explicitly observed sample,
    # but cannot drive whole-scope insight, alert, or AI claims.
    if coverage_complete:
        event_insights = []
        for e in sorted(today_events, key=lambda x: (x.get('risk_score') is not None, x.get('risk_score') or 0), reverse=True)[:5]:
            linked_ids = {(str(source.get('source_type')), str(source.get('source_id')))
                          for source in e.get('sources', [])}
            linked_notes = [note for note in effective_notes
                            if (str(note.get('source_type') or 'note'),
                                str(note.get('source_id') or note.get('note_id'))) in linked_ids]
            event_insights.append(generate_event_insight(e, linked_notes))
        insights = generate_key_insights(effective_notes, today_events, summary)
        actions = generate_action_items(insights, today_events, summary, effective_notes)
        executive = generate_executive_summary(summary, insights, actions)
        ai_summary = ''
        if _ai_allowed_for_report() and intelligence.ai_enabled() and effective_notes:
            ai_summary = _ai_generate_daily_summary(summary, insights, event_insights)
        if not ai_summary:
            ai_summary = executive
        executive_insight = _ai_generate_executive_insight(summary, insights, event_insights)
        trend_alerts = _generate_trend_alerts(summary)
        risk_alerts = _generate_risk_alerts(event_insights)
    else:
        event_insights = []
        insights = []
        actions = [{'priority': '待核验', 'action': '当前来源、相关性或事件覆盖未达到完整条件，样本仅供查看，暂不生成全范围分析与行动建议。',
                    'owner': '数据分析团队', 'deadline': '本周期内'}]
        executive = '当前来源、相关性或事件覆盖不完整；已隐藏全范围指标与结论，请先完成范围核验。'
        ai_summary = executive
        executive_insight = {'executive_insight': executive, 'priority': 'unknown',
                             'focus_area': '数据覆盖核验', 'provider': 'rule_fallback'}
        trend_alerts = []
        risk_alerts = []

    # 组装完整数据
    digest = {
        'digest_date': date_str,
        'scope': exact,
        'total_found': summary['total_found'],
        'effective_count': summary['effective_count'],
        'relevance_coverage': summary.get('relevance_coverage'),
        'positive_count': summary['positive_count'],
        'neutral_count': summary['neutral_count'],
        'risk_count': summary['risk_count'],
        'risk_index': summary['risk_index'],
        'brand_health_score': summary['brand_health_score'],
        'ai_summary': ai_summary,
        'executive_summary': executive,
        'executive_insight': executive_insight,
        'trend_alerts': trend_alerts,
        'risk_alerts': risk_alerts,
        'key_insights': insights,
        'action_items': actions,
        'top_events': event_insights,
        'coverage': {'complete': coverage_complete,
                     'sources': summary.get('source_coverage'),
                     'events': summary.get('event_coverage')},
        'saved': False,
        'persistence_state': 'NOT_SAVED_USE_SAVEDWORK',
        'persistence_reason': '请通过现有 SavedWork 工作流保存、修订和重开本报告。',
    }

    return digest


def _ai_generate_daily_summary(summary, insights, events):
    """AI生成日报总结。"""
    # Hermetic/离线测试必须保持有界：报告的事实摘要与规则预警仍然运行，
    # 但不触发本地 Ollama 或云端模型请求。生产环境不设置该门禁时，
    # 继续沿用现有 AI 增强路径，失败后由调用方使用规则结果。
    if os.environ.get('ZBC_TEST_OFFLINE', '').strip() == '1':
        return ''
    system = '''你是当前已授权业务范围的舆情日报撰写助手。基于数据生成一段150字以内的日报总结，不得猜测主体身份。

要求：
1. 客观陈述数据，不夸大不缩小
2. 指出最需要关注的1-2个点
3. 语气专业、简洁，适合管理层阅读
4. 不要说套话，要有具体信息
5. 直接输出总结文本，不要JSON
'''
    user = json.dumps({
        'summary': summary,
        'top_insights': insights[:3],
        'top_events': [{'title': e['event_title'], 'risk': e['risk_level'], 'summary': e['ai_summary'][:60]} for e in events[:3]]
    }, ensure_ascii=False)

    raw, provider, _ = intelligence.chat(system, user, level='medium', temperature=0.3, max_tokens=400, pack_id='glm_4_5_air')
    if raw:
        return raw.strip()[:200]
    return ''


# ============== P1-E 智谱增强：管理层洞察 + 趋势预警 + 风险预警 ==============

def _ai_generate_executive_insight(summary, insights, events):
    """P1-E(2026-09-02): AI生成管理层一句话洞察（高层视角核心结论）。
    智谱驱动，输出严格JSON：executive_insight + priority + focus_area
    """
    rule_result = _rule_executive_insight(summary, events)
    # Do not ask a model to invent a denominator or fill unavailable values.
    if (not _ai_allowed_for_report() or _measured_negative_percentage(summary) is None
            or summary.get('risk_count') is None):
        return rule_result
    system = ('基于提供的今日舆情数据，给出管理层一句话洞察。字段为 null 或覆盖不足时必须明确说明未知，'
              '不得补成0、推断缺失分母或把未知说成平稳。\n\n输出严格JSON：\n{\n'
              '  "executive_insight": "不超过80字，高层视角的核心结论",\n'
              '  "priority": "high|medium|low|unknown",\n'
              '  "focus_area": "需要管理层关注的具体领域",\n'
              '  "key_metric": "最关键的一个数据指标"\n}\n\n'
              '依据具体数据；缺少支持时，明确指出待核实的数据。')
    user = json.dumps({
        'summary': {k: summary[k] for k in ['total_found','effective_count','positive_count','neutral_count','negative_count','risk_count','risk_index','brand_health_score'] if k in summary},
        'top_insights': insights[:3],
        'top_events': [{'title': e.get('event_title',''), 'risk': e.get('risk_level',''), 'mentions': e.get('mention_count',0)} for e in events[:3]]
    }, ensure_ascii=False)

    raw, provider, _ = intelligence.chat(system, user, level='medium', temperature=0.2, max_tokens=500, pack_id='glm_4_5_air')
    data = intelligence._json_from_text(raw)
    if data:
        data['provider'] = provider
        return data
    return rule_result


def _generate_trend_alerts(summary):
    """Generate threshold alerts only for measured values."""
    alerts = []
    effective = summary.get('effective_count')
    if not effective:
        return [{'type': 'data_gap', 'severity': 'high',
                 'message': '今日无有效舆情数据，无法计算风险和健康指标；请检查采集与分类状态',
                 'metric': 'effective_count=0'}]

    coverage = summary.get('sentiment_coverage') or {}
    negative = summary.get('negative_count')
    if negative is not None and coverage.get('known', 0) > 0 and coverage.get('known') == coverage.get('total'):
        neg_pct = round(negative / coverage['known'] * 100, 1)
        if neg_pct > 40:
            alerts.append({'type': 'negative_surge', 'severity': 'high', 'message': f'负面占比{neg_pct}%，超过40%警戒线，需立即关注负面舆情来源', 'metric': f'negative_pct={neg_pct}%'})
        elif neg_pct > 25:
            alerts.append({'type': 'negative_elevated', 'severity': 'medium', 'message': f'负面占比{neg_pct}%，处于偏高区间，建议跟踪负面话题演化', 'metric': f'negative_pct={neg_pct}%'})
    else:
        alerts.append({'type': 'sentiment_data_gap', 'severity': 'medium',
                       'message': '情感分类覆盖不足，暂不判断负面比例', 'metric': 'negative_pct=—'})

    risk = summary.get('risk_count')
    if risk is None:
        alerts.append({'type': 'risk_data_gap', 'severity': 'medium',
                       'message': '风险等级存在缺失，暂不判断风险事件数量', 'metric': 'risk_count=—'})
    elif risk >= 3:
        alerts.append({'type': 'high_risk_cluster', 'severity': 'high', 'message': f'今日高风险事件{risk}起，达到集群预警阈值，建议启动应急响应流程', 'metric': f'risk_count={risk}'})
    elif risk >= 1:
        alerts.append({'type': 'high_risk_present', 'severity': 'medium', 'message': f'今日高风险事件{risk}起，需持续跟踪处置进展', 'metric': f'risk_count={risk}'})

    risk_index = summary.get('risk_index')
    health = summary.get('brand_health_score')
    if risk_index is None:
        alerts.append({'type': 'risk_index_data_gap', 'severity': 'medium',
                       'message': '风险指标输入不完整，暂不能计算风险指数', 'metric': 'risk_index=—'})
    elif risk_index >= 70:
        alerts.append({'type': 'risk_index_critical', 'severity': 'high', 'message': f'风险指数{risk_index}，处于危急区间，建议管理层立即介入', 'metric': f'risk_index={risk_index}'})
    elif risk_index >= 50:
        alerts.append({'type': 'risk_index_elevated', 'severity': 'medium', 'message': f'风险指数{risk_index}，处于偏高区间，建议加强监控频次', 'metric': f'risk_index={risk_index}'})

    if health is None:
        alerts.append({'type': 'brand_health_data_gap', 'severity': 'medium',
                       'message': '品牌健康指标输入不完整，暂不能计算品牌健康度', 'metric': 'brand_health=—'})
    elif health < 60:
        alerts.append({'type': 'brand_health_critical', 'severity': 'high', 'message': f'品牌健康分{health}，低于60分警戒线，品牌声誉面临较大压力', 'metric': f'brand_health={health}'})
    elif health < 75:
        alerts.append({'type': 'brand_health_declining', 'severity': 'medium', 'message': f'品牌健康分{health}，处于下行区间，建议关注品牌声誉修复', 'metric': f'brand_health={health}'})

    if effective < 5:
        alerts.append({'type': 'low_volume', 'severity': 'low', 'message': f'今日有效舆情仅{effective}条，数据量偏低，可能影响分析准确性', 'metric': f'effective_count={effective}'})
    if not alerts:
        alerts.append({'type': 'stable', 'severity': 'low', 'message': '已计算指标未触发预警阈值', 'metric': 'measured_metrics_within_thresholds'})
    return alerts

def _generate_risk_alerts(events):
    """P1-E(2026-09-02): 规则引擎生成风险事件预警（不依赖AI，基于事件风险等级）。"""
    high_risk = [e for e in events if e.get('risk_level') == 'high']
    medium_risk = [e for e in events if e.get('risk_level') == 'medium']

    alerts = []
    for e in high_risk[:5]:
        alerts.append({
            'event_id': e.get('id'),
            'title': e.get('event_title', '未知事件'),
            'risk_level': 'high',
            'risk_score': e.get('risk_score'),
            'mention_count': e.get('mention_count', 0),
            'ai_summary': (e.get('ai_summary') or '')[:100],
            'recommended_action': '立即启动应急响应，2小时内完成初步评估并上报管理层',
            'urgency': 'immediate'
        })

    for e in medium_risk[:3]:
        alerts.append({
            'event_id': e.get('id'),
            'title': e.get('event_title', '未知事件'),
            'risk_level': 'medium',
            'risk_score': e.get('risk_score'),
            'mention_count': e.get('mention_count', 0),
            'ai_summary': (e.get('ai_summary') or '')[:100],
            'recommended_action': '24小时内完成评估，制定处置方案并跟踪进展',
            'urgency': 'within_24h'
        })

    return alerts




# ============================================================
# P1-D: 日报5板块标准格式 + 专报触发条件标注
# ============================================================
# 5个标准板块：
#   1. 一句话概览（今日监测X条/负面X条/最高互动X/核心话题/等级）
#   2. 数据速览（总提及/负面/负面占比/最高互动/环比±%）
#   3. 负面TOP3（业态-笔记摘要-互动-状态）
#   4. 今日动作（已处理/待跟进(责任人·时限)/预警）
#   5. 专报触发条件标注（满足任一即升级）
# 数据缺失显式 null/—，不用0填充

def format_daily_report_5sections(digest: dict, date_str: str = None, *, scope=None) -> dict:
    """P1-D: 将日报数据格式化为5板块标准结构。

    Args:
        digest: generate_daily_digest() 返回的完整日报数据
        date_str: 日期字符串

    Returns:
        {section1_overview, section2_data, section3_negative_top3,
         section4_actions, section5_special_trigger, report_date}
    """
    exact_scope = db._normalize_event_scope(scope, allow_global=True)
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    summary = digest.get('summary', {}) if isinstance(digest.get('summary'), dict) else {}
    # 如果 digest 没有嵌套 summary，直接从 digest 取字段
    if not summary:
        summary = digest

    effective = summary.get('effective_count', digest.get('effective_count', None))
    negative = summary.get('negative_count', digest.get('negative_count'))
    risk_count = summary.get('risk_count', digest.get('risk_count', None))
    risk_index = summary.get('risk_index', digest.get('risk_index', None))
    health = summary.get('brand_health_score', digest.get('brand_health_score', None))

    # 等级判定
    if risk_index is not None:
        if risk_index >= 60:
            level = "🔴"
        elif risk_index >= 30:
            level = "🟡"
        else:
            level = "🟢"
    else:
        level = "—"

    # ===== 板块1: 一句话概览 =====
    core_topic = "—"
    top_events = digest.get('top_events', []) or []
    if top_events:
        core_topic = (top_events[0].get('event_title') or '—')[:30]

    overview_parts = []
    overview_parts.append(f"今日监测{effective if effective is not None else '—'}条")
    overview_parts.append(f"负面{negative if negative is not None else '—'}条")
    overview_parts.append(f"最高互动{summary.get('max_engagement', '—')}")
    overview_parts.append(f"核心话题{core_topic}")
    overview_parts.append(f"等级{level}")
    section1 = "，".join(overview_parts)

    # ===== 板块2: 数据速览 =====
    total_found = summary.get('total_found', digest.get('total_found', None))
    neg_pct = None
    if effective and negative is not None and effective > 0:
        neg_pct = round(negative / effective * 100, 1)

    # 环比（简化：与昨日对比，数据缺失时为—）
    chain_change = "—"
    try:
        yesterday = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        y_summary = generate_today_summary(yesterday, scope=exact_scope)
        y_eff = y_summary.get('effective_count')
        if y_eff is not None and y_eff > 0 and effective is not None:
            pct = round((effective - y_eff) / y_eff * 100, 1)
            chain_change = f"{'+' if pct >= 0 else ''}{pct}%"
    except Exception:
        pass

    section2 = {
        "总提及": total_found if total_found is not None else "—",
        "负面": negative if negative is not None else "—",
        "负面占比": f"{neg_pct}%" if neg_pct is not None else "—",
        "最高互动": summary.get('max_engagement', '—'),
        "环比": chain_change,
    }

    # ===== 板块3: 负面TOP3 =====
    negative_top3 = []
    source_state = 'UNAVAILABLE'
    try:
        note_read = db.get_scoped_event_source_rows(
            exact_scope, source_types=('note', 'web_mention'), date_start=date_str, date_end=date_str, limit=5000)
        notes = note_read['sources']
        source_state = note_read.get('state')
        if note_read.get('truncated') or note_read.get('rejected_count'):
            source_state = 'INCOMPLETE'
            notes = []
        neg_notes = [n for n in notes if (n.get('sentiment') or '').lower() in ('negative', 'risk')]
        # Missing interaction values stay unknown; only complete measured pairs
        # participate in the ranking.
        for n in neg_notes:
            likes, comments = n.get('likes'), n.get('comments')
            try:
                n['_engage'] = int(likes) + int(comments) * 3 if likes is not None and comments is not None else None
            except (TypeError, ValueError):
                n['_engage'] = None
        neg_notes.sort(key=lambda x: (x.get('_engage') is not None, x.get('_engage') or 0), reverse=True)
        for n in neg_notes[:3]:
            negative_top3.append({
                "业态": n.get('category', n.get('industry', '—')),
                "笔记摘要": (n.get('title') or n.get('content', '—'))[:50],
                "互动": n.get('_engage') if n.get('_engage') is not None else '—',
                "状态": n.get('ai_filter_status', n.get('status', '—')),
            })
    except (PermissionError, ValueError):
        raise
    except Exception:
        raise ValueError('REPORT_SOURCE_READ_UNAVAILABLE') from None

    if not negative_top3:
        message = ('当前范围暂无已核验来源' if source_state == 'EMPTY'
                   else '当前范围未发现已核验负面内容' if source_state == 'AVAILABLE'
                   else '来源状态不可用')
        negative_top3 = [{"业态": "—", "笔记摘要": message, "互动": "—", "状态": source_state}]

    section3 = negative_top3

    # ===== 板块4: 今日动作 =====
    actions = digest.get('action_items', []) or []
    processed = []
    pending = []
    warnings = []
    for a in actions:
        priority = (a.get('priority') or '').lower()
        if priority in ('已处理', 'done', 'completed'):
            processed.append(a.get('action', ''))
        elif priority in ('预警', 'warning', 'alert', 'high'):
            warnings.append(a.get('action', ''))
        else:
            pending.append({
                "action": a.get('action', ''),
                "owner": a.get('owner', '舆情团队'),
                "deadline": a.get('deadline', '今日内'),
            })

    section4 = {
        "已处理": processed if processed else ["—"],
        "待跟进": pending if pending else [{"action": "无待跟进事项", "owner": "—", "deadline": "—"}],
        "预警": warnings if warnings else ["—"],
    }

    # ===== 板块5: 专报触发条件标注 =====
    # 调用 risk_engine.check_special_report_trigger 检测
    trigger_status = {"triggered": False, "reasons": [], "conditions": []}
    try:
        import risk_engine
        # 构建 event 字典用于触发检测
        max_engage = 0
        for n in negative_top3:
            if isinstance(n.get('互动'), int):
                max_engage = max(max_engage, n['互动'])
        event = {
            "engagement": max_engage,
            "sentiment": (None if negative is None
                          else "negative" if negative > 0 else "neutral"),
            "title": core_topic,
            "content": " ".join([n.get('笔记摘要', '') for n in negative_top3]),
            "negative_count_24h": negative,
        }
        triggered, reasons = risk_engine.check_special_report_trigger(event)
        trigger_status = {
            "triggered": triggered,
            "reasons": reasons,
            "conditions": [
                "单条负面互动≥500",
                "负面帖≥3条集中爆发(24h)",
                "涉及安全·歧视·违法",
                "本地KOC转发",
                "集团或媒体问询",
            ],
        }
    except Exception as e:
        trigger_status["error"] = str(e)

    section5 = trigger_status

    return {
        "report_date": date_str,
        "section1_overview": section1,
        "section2_data": section2,
        "section3_negative_top3": section3,
        "section4_actions": section4,
        "section5_special_trigger": section5,
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='LUMENIS scoped daily reporting')
    parser.add_argument('--date', type=str, help='指定日期 YYYY-MM-DD，默认今天')
    parser.add_argument('--summary', action='store_true', help='仅生成今日摘要')
    parser.add_argument('--full', action='store_true', help='生成完整日报')
    parser.add_argument('--domain', choices=('cth', 'zbmp'), help='显式业务域')
    parser.add_argument('--subject-id', help='CTH 已登记主体 ID；与 --brand-focus-id 互斥')
    parser.add_argument('--brand-focus-id', help='BMP 已登记品牌焦点 ID；与 --subject-id 互斥')
    parser.add_argument('--global-all', action='store_true', help='显式选择该业务域的 GLOBAL / ALL 范围')
    args = parser.parse_args()

    if not args.domain:
        parser.error('--domain is required; no report Subject is selected implicitly')
    if args.subject_id and args.brand_focus_id:
        parser.error('--subject-id and --brand-focus-id are mutually exclusive')
    expected_focus = args.subject_id if args.domain == 'cth' else args.brand_focus_id
    unexpected_focus = args.brand_focus_id if args.domain == 'cth' else args.subject_id
    if unexpected_focus or (not args.global_all and not expected_focus):
        parser.error('provide the matching registered focus ID, or select --global-all')
    scope = {'domain_id': args.domain,
             'subject_id': args.subject_id,
             'brand_focus_id': args.brand_focus_id,
             'global_scope': args.global_all}

    if args.summary:
        result = generate_today_summary(args.date, scope=scope)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.full:
        result = generate_daily_digest(args.date, scope=scope)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
