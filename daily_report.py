"""
广州太古汇舆情监测系统 v5.3.2 - 智能日报模块
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
import re
from datetime import datetime, timedelta

import database as db
import ai_analyzer
import intelligence
import canonical_metrics as cm


# ============== 风险指数计算 ==============

def calculate_risk_index(notes, events, period_days=1):
    """
    风险指数 0-100
    综合维度：
    1. 负面内容占比（30%）
    2. 高风险内容数量（25%）
    3. 传播互动规模（20%）
    4. 事件持续时间（15%）
    5. 多来源交叉验证（10%）
    """
    if not notes:
        return 0.0

    total = len(notes)
    _sc = cm.sentiment_count(notes)
    _rc = cm.risk_count(notes)
    negative = _sc['negative']
    high_risk = _rc['high']      # Canonical FN-RISK-COUNT：high 不含 critical
    critical_risk = _rc['critical']  # 方案甲：critical 独立更高桶，风险指数中权重高于 high（Phase 6 审计修复）
    medium_risk = _rc['medium']
    total_engagement = sum(int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0) * 2
                           for n in notes)

    # 1. 负面占比得分 (0-30)
    # MET-NEG-RATIO：分母为 known(pos+neu+neg)，不含 unknown；分母为 0 返回 None（不可算）。
    # 不可算时该维度得 0 分并显式标记，绝不把 unknown 当 negative 或 0 混入比率（Phase 6 审计修复）。
    _nr = cm.neg_ratio(_sc)
    neg_ratio = _nr if _nr is not None else 0.0
    neg_score = min(30, neg_ratio * 60)  # 50%负面即满分

    # 2. 高风险数量得分 (0-25)
    # 单日高风险>=5条即满分；critical 权重为 high 的 2 倍（独立更高桶，不得被弱化）
    high_score = min(25, high_risk * 5 + critical_risk * 10 + medium_risk * 1.5)

    # 3. 传播互动得分 (0-20)
    # 负面内容的互动量权重更高
    neg_engagement = sum(int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0) * 2
                         for n in notes if n.get('sentiment') == 'negative')
    eng_score = min(20, neg_engagement / 50)  # 负面互动1000即满分

    # 4. 事件持续时间得分 (0-15)
    event_duration_score = 0
    if events:
        active_events = [e for e in events if e.get('status') == 'active']
        for e in active_events[:3]:
            first = e.get('first_seen', '')
            last = e.get('last_seen', '')
            if first and last:
                try:
                    d1 = datetime.strptime(first[:10], '%Y-%m-%d')
                    d2 = datetime.strptime(last[:10], '%Y-%m-%d')
                    days = (d2 - d1).days + 1
                    event_duration_score += min(5, days * 0.5)
                except Exception:
                    pass
    event_duration_score = min(15, event_duration_score)

    # 5. 多来源得分 (0-10)
    multi_source_score = 0
    if events:
        multi_source = sum(1 for e in events if (e.get('source_count') or 0) >= 2)
        multi_source_score = min(10, multi_source * 3)

    risk_index = round(neg_score + high_score + eng_score + event_duration_score + multi_source_score, 1)
    return min(100.0, max(0.0, risk_index))


def calculate_brand_health_score(notes, risk_index):
    """
    品牌健康度 0-100
    越高越健康
    维度：正面占比、风险水平、互动质量、官方声量
    """
    if not notes:
        return 50.0  # 无数据时中性

    total = len(notes)
    _scb = cm.sentiment_count(notes)
    positive = _scb['positive']
    negative = _scb['negative']
    official = sum(1 for n in notes if n.get('is_official') == 1)

    # 1. 正面占比 (0-40)
    pos_ratio = positive / total if total > 0 else 0
    pos_score = pos_ratio * 40

    # 2. 风险反向得分 (0-30)
    # risk_index 0 -> 30分, risk_index 100 -> 0分
    risk_score = max(0, 30 - risk_index * 0.3)

    # 3. 互动质量 (0-20)
    # 正面内容互动占比
    pos_engagement = sum(int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0)
                         for n in notes if n.get('sentiment') == 'positive')
    total_engagement = sum(int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0)
                           for n in notes)
    eng_quality = (pos_engagement / total_engagement * 20) if total_engagement > 0 else 10

    # 4. 官方声量 (0-10)
    official_score = min(10, official * 2)

    health = round(pos_score + risk_score + eng_quality + official_score, 1)
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


def generate_today_summary(date_str=None):
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

    # 今日所有通过主体过滤的笔记
    today_notes = db.get_notes_by_date_range(date_str, date_str)

    # 今日有效舆情（通过AI过滤层accepted的）
    effective_notes = [n for n in today_notes if n.get('ai_filter_status') == 'accepted']
    # 如果还没有跑过AI过滤，全部视为待处理
    if not effective_notes and today_notes:
        effective_notes = today_notes

    total_found = len(today_notes)
    effective_count = len(effective_notes)

    _sce = cm.sentiment_count(effective_notes)
    _rce = cm.risk_count(effective_notes)
    positive = _sce['positive']
    neutral = _sce['neutral']
    risk = _rce['high'] + _rce['medium']   # 风险数=中+高(口径不变;critical独立不计入)

    # 今日事件
    events = db.get_events(20)
    today_events = [e for e in events if (e.get('last_seen') or '')[:10] >= date_str
                    or (e.get('first_seen') or '')[:10] <= date_str <= (e.get('last_seen') or '')[:10]]

    risk_index = calculate_risk_index(effective_notes, today_events)
    brand_health = calculate_brand_health_score(effective_notes, risk_index)

    return {
        'date': date_str,
        'total_found': total_found,
        'effective_count': effective_count,
        'positive_count': positive,
        'neutral_count': neutral,
        'risk_count': risk,
        'risk_index': risk_index,
        'brand_health_score': brand_health,
        'events_count': len(today_events),
        'collection_health': _collection_health(date_str),
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
    risk_level = event.get('risk_level', 'low')
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
    if intelligence.ai_enabled() and event_notes:
        ai_result = _ai_summarize_event(event, event_notes)
        if ai_result:
            ai_summary = ai_result.get('summary', '')
            recommended_action = ai_result.get('recommended_action', '')

    # 规则引擎兜底
    if not ai_summary:
        risk_label = {'high': '高风险', 'medium': '中风险', 'low': '低风险'}.get(risk_level, '低风险')
        ai_summary = (f'该事件共涉及{mention_count}条提及，{sentiment_trend}。'
                     f'{propagation}。目前信息主要来自用户分享，事实仍需进一步核实。')

    if not recommended_action:
        if risk_level == 'high':
            recommended_action = '建议24小时内核查事实，准备官方回应口径，持续监测传播趋势。'
        elif risk_level == 'medium':
            recommended_action = '建议关注事件发展，收集更多用户反馈，必要时主动沟通改善。'
        else:
            recommended_action = '持续观察即可，暂不需要主动介入。'

    return {
        'event_id': event.get('id'),
        'event_title': event_title[:50],
        'risk_level': risk_level,
        'risk_score': event.get('risk_score', 0),
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

    system = '''你是广州太古汇舆情事件分析专家。把同一事件的多条用户提及凝练成管理层可执行的摘要。

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

    # 洞察1：情感格局
    pos = sum(1 for n in notes if n.get('sentiment') == 'positive')
    neg = sum(1 for n in notes if n.get('sentiment') == 'negative')
    pos_pct = round(pos / total * 100, 1) if total > 0 else 0
    neg_pct = round(neg / total * 100, 1) if total > 0 else 0

    if neg_pct > 30:
        insights.append({
            'insight': f'今日负面占比{neg_pct}%，高于警戒线（30%），需重点关注负面内容的扩散趋势。',
            'type': 'risk',
            'metric': f'负面{neg}条 / 正面{pos}条'
        })
    elif pos_pct > 60:
        insights.append({
            'insight': f'今日正面占比{pos_pct}%，品牌口碑整体健康，可关注正向内容的传播放大机会。',
            'type': 'opportunity',
            'metric': f'正面{pos}条 / 负面{neg}条'
        })
    else:
        insights.append({
            'insight': f'今日正负声量接近（正面{pos_pct}% / 负面{neg_pct}%），舆情处于中性观察状态。',
            'type': 'neutral',
            'metric': f'正面{pos}条 / 负面{neg}条'
        })

    # 洞察2：风险事件
    high_events = [e for e in events if e.get('risk_level') == 'high']
    if high_events:
        insights.append({
            'insight': f'存在{len(high_events)}个高风险事件，最高风险分{max(e.get("risk_score", 0) for e in high_events)}，建议优先处置。',
            'type': 'risk',
            'metric': f'高风险事件{len(high_events)}个'
        })

    # 洞察3：热门话题
    topics = db.get_hot_topics(5)
    if topics:
        top_topic = topics[0]
        insights.append({
            'insight': f'今日最热话题为「{top_topic["topic"]}」（{top_topic["count"]}条），'
                      f'情感倾向{top_topic.get("sentiment", "neutral")}，是当前用户讨论焦点。',
            'type': 'trend',
            'metric': f'{top_topic["count"]}条提及'
        })

    # 洞察4：传播力
    total_eng = sum(int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0) for n in notes)
    if total_eng > 1000:
        hot_note = max(notes, key=lambda x: int(x.get('likes', 0) or 0) + int(x.get('comments', 0) or 0))
        insights.append({
            'insight': f'今日总互动量{total_eng}，最热内容「{(hot_note.get("title", "") or "无标题")[:20]}」'
                      f'互动{int(hot_note.get("likes", 0) or 0) + int(hot_note.get("comments", 0) or 0)}，建议关注其传播走向。',
            'type': 'trend',
            'metric': f'总互动{total_eng}'
        })

    # 洞察5：AI过滤效果
    filter_stats = db.get_filter_stats()
    if filter_stats.get('pending', 0) > 100:
        insights.append({
            'insight': f'有{filter_stats["pending"]}条笔记待AI二次过滤，建议运行过滤任务以提升数据质量。',
            'type': 'system',
            'metric': f'待过滤{filter_stats["pending"]}条'
        })

    return insights[:5]


def generate_action_items(insights, events, summary):
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

    # 负面占比高 -> 客服行动
    if summary.get('risk_count', 0) > 5:
        actions.append({
            'priority': '高',
            'action': f'今日有{summary["risk_count"]}条风险内容，建议客服团队逐一查看负面笔记，主动联系用户解决问题。',
            'owner': '客服团队',
            'deadline': '48小时内',
        })

    # 正向机会 -> 营销行动
    if summary.get('positive_count', 0) > summary.get('risk_count', 0) * 2:
        actions.append({
            'priority': '中',
            'action': '今日正面声量占优，建议营销团队筛选优质UGC内容，考虑转发或二次传播放大正向口碑。',
            'owner': '营销/社媒团队',
            'deadline': '本周内',
        })

    # 数据质量 -> 系统行动
    filter_stats = db.get_filter_stats()
    if filter_stats.get('pending', 0) > 50:
        actions.append({
            'priority': '中',
            'action': f'运行AI二次过滤任务，清理{filter_stats["pending"]}条待处理笔记中的重复和垃圾内容。',
            'owner': '系统运维',
            'deadline': '今日内',
        })

    if not actions:
        actions.append({
            'priority': '常规',
            'action': '今日舆情整体平稳，按常规节奏监测即可，无需特殊干预。',
            'owner': '舆情团队',
            'deadline': '持续',
        })

    return actions[:5]


# ============== 管理层摘要 ==============

def generate_executive_summary(summary, insights, actions):
    """
    生成一句话管理层摘要
    适合放在日报最顶部，30秒读完
    """
    risk_index = summary.get('risk_index', 0)
    health = summary.get('brand_health_score', 50)
    effective = summary.get('effective_count', 0)
    risk_count = summary.get('risk_count', 0)
    coll = summary.get('collection_health') or {}

    # 数据完整性保护：采集被拦截/失败时，绝不能据空数据下“无舆情/风险低”结论
    if coll.get('complete') is False and effective == 0:
        return ('⚠️ 数据采集异常：本周期小红书采集受到平台安全限制或网络异常'
                f'（{coll.get("state")}），本周期数据不完整，因此不对“无新增舆情/风险较低”作结论；'
                '请恢复采集后再评估。')

    if risk_index >= 60:
        risk_desc = '风险偏高'
    elif risk_index >= 30:
        risk_desc = '风险中等'
    else:
        risk_desc = '风险较低'

    if health >= 70:
        health_desc = '品牌健康度良好'
    elif health >= 50:
        health_desc = '品牌健康度一般'
    else:
        health_desc = '品牌健康度需关注'

    top_action = actions[0]['action'][:40] if actions else '按常规节奏监测'

    return (f'今日监测到{effective}条有效舆情，{risk_desc}（风险指数{risk_index}），'
            f'{health_desc}（{health}分）。{risk_count}条内容需关注。'
            f'首要行动：{top_action}…')


# ============== 完整日报生成 ==============

def generate_daily_digest(date_str=None):
    """
    生成完整的每日摘要（v5.3.2增强版日报）
    保存到 daily_digest 表，并返回完整数据
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    # 1. 今日摘要
    summary = generate_today_summary(date_str)

    # 2. 今日有效笔记
    notes = db.get_notes_by_date_range(date_str, date_str)
    effective_notes = [n for n in notes if n.get('ai_filter_status') == 'accepted']
    if not effective_notes and notes:
        effective_notes = notes

    # 3. 今日事件
    events = db.get_events(20)
    today_events = [e for e in events if (e.get('last_seen') or '')[:10] >= date_str
                    or (e.get('first_seen') or '')[:10] <= date_str <= (e.get('last_seen') or '')[:10]]

    # 4. AI事件总结（取Top 5事件）
    event_insights = []
    for e in sorted(today_events, key=lambda x: x.get('risk_score', 0), reverse=True)[:5]:
        insight = generate_event_insight(e, effective_notes)
        event_insights.append(insight)
        # 保存事件洞察
        if e.get('id'):
            db.save_event_insight(e['id'], insight)

    # 5. 关键洞察
    insights = generate_key_insights(effective_notes, today_events, summary)

    # 6. 行动建议
    actions = generate_action_items(insights, today_events, summary)

    # 7. 管理层摘要
    executive = generate_executive_summary(summary, insights, actions)

    # 8. AI总结（如果AI可用）
    ai_summary = ''
    if intelligence.ai_enabled() and effective_notes:
        ai_summary = _ai_generate_daily_summary(summary, insights, event_insights)

    if not ai_summary:
        ai_summary = executive

    # 9. P1-E 智谱增强：管理层洞察 + 趋势预警 + 风险预警
    executive_insight = _ai_generate_executive_insight(summary, insights, event_insights)
    trend_alerts = _generate_trend_alerts(summary)
    risk_alerts = _generate_risk_alerts(event_insights)

    # 组装完整数据
    digest = {
        'digest_date': date_str,
        'total_found': summary['total_found'],
        'effective_count': summary['effective_count'],
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
    }

    # 保存到数据库
    db.save_daily_digest(digest)

    return digest


def _ai_generate_daily_summary(summary, insights, events):
    """AI生成日报总结。"""
    system = '''你是广州太古汇舆情日报撰写专家。基于数据生成一段150字以内的日报总结。

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
    system = '你是广州太古汇品牌公关总监。基于今日舆情数据，给出管理层一句话洞察。\n\n输出严格JSON：\n{\n  "executive_insight": "不超过80字，高层视角的核心结论，要有具体数据支撑",\n  "priority": "high|medium|low",\n  "focus_area": "需要管理层关注的具体领域",\n  "key_metric": "最关键的一个数据指标"\n}\n\n要求：必须有具体数据，不能说"整体平稳"这种空话；priority=high时必须说明为什么紧急；focus_area要具体到业务领域。'
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
    # 规则兜底
    neg_pct = round(summary.get('negative_count',0) / max(summary.get('effective_count',1),1) * 100, 1)
    high_risk = sum(1 for e in events if e.get('risk_level') == 'high')
    priority = 'high' if (neg_pct > 30 or high_risk >= 2) else ('medium' if (neg_pct > 15 or high_risk >= 1) else 'low')
    return {
        'executive_insight': f"今日有效舆情{summary.get('effective_count',0)}条，负面占比{neg_pct}%，高风险事件{high_risk}起，品牌健康分{summary.get('brand_health_score','N/A')}。",
        'priority': priority,
        'focus_area': '综合舆情',
        'key_metric': f"负面占比{neg_pct}%",
        'provider': 'rule_fallback'
    }


def _generate_trend_alerts(summary):
    """P1-E(2026-09-02): 规则引擎生成趋势预警（不依赖AI，实时计算）。"""
    alerts = []
    effective = summary.get('effective_count', 0)
    if effective == 0:
        return [{'type': 'data_gap', 'severity': 'high', 'message': '今日无有效舆情数据，建议检查采集任务是否正常运行', 'metric': 'effective_count=0'}]

    neg = summary.get('negative_count', 0)
    neg_pct = round(neg / effective * 100, 1)
    risk = summary.get('risk_count', 0)
    risk_index = summary.get('risk_index', 0)
    health = summary.get('brand_health_score', 100)

    if neg_pct > 40:
        alerts.append({'type': 'negative_surge', 'severity': 'high', 'message': f'负面占比{neg_pct}%，超过40%警戒线，需立即关注负面舆情来源', 'metric': f'negative_pct={neg_pct}%'})
    elif neg_pct > 25:
        alerts.append({'type': 'negative_elevated', 'severity': 'medium', 'message': f'负面占比{neg_pct}%，处于偏高区间，建议跟踪负面话题演化', 'metric': f'negative_pct={neg_pct}%'})

    if risk >= 3:
        alerts.append({'type': 'high_risk_cluster', 'severity': 'high', 'message': f'今日高风险事件{risk}起，达到集群预警阈值，建议启动应急响应流程', 'metric': f'risk_count={risk}'})
    elif risk >= 1:
        alerts.append({'type': 'high_risk_present', 'severity': 'medium', 'message': f'今日高风险事件{risk}起，需持续跟踪处置进展', 'metric': f'risk_count={risk}'})

    if risk_index >= 70:
        alerts.append({'type': 'risk_index_critical', 'severity': 'high', 'message': f'风险指数{risk_index}，处于危急区间，建议管理层立即介入', 'metric': f'risk_index={risk_index}'})
    elif risk_index >= 50:
        alerts.append({'type': 'risk_index_elevated', 'severity': 'medium', 'message': f'风险指数{risk_index}，处于偏高区间，建议加强监控频次', 'metric': f'risk_index={risk_index}'})

    if health < 60:
        alerts.append({'type': 'brand_health_critical', 'severity': 'high', 'message': f'品牌健康分{health}，低于60分警戒线，品牌声誉面临较大压力', 'metric': f'brand_health={health}'})
    elif health < 75:
        alerts.append({'type': 'brand_health_declining', 'severity': 'medium', 'message': f'品牌健康分{health}，处于下行区间，建议关注品牌声誉修复', 'metric': f'brand_health={health}'})

    if effective < 5:
        alerts.append({'type': 'low_volume', 'severity': 'low', 'message': f'今日有效舆情仅{effective}条，数据量偏低，可能影响分析准确性', 'metric': f'effective_count={effective}'})

    return alerts if alerts else [{'type': 'stable', 'severity': 'low', 'message': '今日舆情整体平稳，各项指标处于正常区间', 'metric': 'all_normal'}]


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
            'risk_score': e.get('risk_score', 0),
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
            'risk_score': e.get('risk_score', 0),
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

def format_daily_report_5sections(digest: dict, date_str: str = None) -> dict:
    """P1-D: 将日报数据格式化为5板块标准结构。

    Args:
        digest: generate_daily_digest() 返回的完整日报数据
        date_str: 日期字符串

    Returns:
        {section1_overview, section2_data, section3_negative_top3,
         section4_actions, section5_special_trigger, report_date}
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    summary = digest.get('summary', {}) if isinstance(digest.get('summary'), dict) else {}
    # 如果 digest 没有嵌套 summary，直接从 digest 取字段
    if not summary:
        summary = digest

    effective = summary.get('effective_count', digest.get('effective_count', None))
    negative = summary.get('negative_count', digest.get('risk_count', None))
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
        y_summary = generate_today_summary(yesterday)
        y_eff = y_summary.get('effective_count', 0)
        if y_eff > 0 and effective is not None:
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
    try:
        notes = db.get_notes_by_date_range(date_str, date_str)
        neg_notes = [n for n in notes if (n.get('sentiment') or '').lower() in ('negative', 'risk')]
        # 按互动量排序
        for n in neg_notes:
            engage = int(n.get('likes', 0) or 0) + int(n.get('comments', 0) or 0) * 3
            n['_engage'] = engage
        neg_notes.sort(key=lambda x: x.get('_engage', 0), reverse=True)
        for n in neg_notes[:3]:
            negative_top3.append({
                "业态": n.get('category', n.get('industry', '—')),
                "笔记摘要": (n.get('title') or n.get('content', '—'))[:50],
                "互动": n.get('_engage', 0),
                "状态": n.get('ai_filter_status', n.get('status', '—')),
            })
    except Exception:
        pass

    if not negative_top3:
        negative_top3 = [{"业态": "—", "笔记摘要": "今日无负面内容", "互动": "—", "状态": "—"}]

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
            "sentiment": "negative" if negative and negative > 0 else "neutral",
            "title": core_topic,
            "content": " ".join([n.get('笔记摘要', '') for n in negative_top3]),
            "negative_count_24h": negative if negative else 0,
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
    parser = argparse.ArgumentParser(description='广州太古汇舆情监测系统 - 智能日报')
    parser.add_argument('--date', type=str, help='指定日期 YYYY-MM-DD，默认今天')
    parser.add_argument('--summary', action='store_true', help='仅生成今日摘要')
    parser.add_argument('--full', action='store_true', help='生成完整日报')
    args = parser.parse_args()

    if args.summary:
        result = generate_today_summary(args.date)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.full:
        result = generate_daily_digest(args.date)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
