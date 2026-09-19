"""
导出报告模板模块 v1.0
功能：
1. 严格按照太古汇汇报模板导出Word/Excel
2. 日报/周报/月报/年报
3. 按发布日期筛选（日报只含当日/前一日发布）
4. 周期报告负面必须二次确认
5. 事件分析（起因/经过/影响）
6. 点击下载到本地
"""

import os
import sys
import json
import sqlite3
from lumenis.shared.database import get_repository, main_db_path
import csv
import io
from pathlib import Path
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, send_file, send_from_directory
import database as db

# Shared Reporting owns export behavior; repo root remains the data/runtime anchor.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

export_bp = Blueprint('export', __name__)

# 数据库/导出路径保持原生产位置，不因模块迁移改变数据归属。
DB_PATH = main_db_path()
EXPORT_DIR = str(PROJECT_ROOT / 'data' / 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

# Artifact 真实性校验是 Shared Reporting 的强制依赖，不允许静默跳过。
from lumenis.shared.reporting import artifact as ra


def get_db():
    """获取数据库连接"""
    conn = get_repository().connect(timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _i(v, default=0):
    """安全转整数，None/空/异常都回落到 default"""
    try:
        return int(v) if v not in (None, '') else default
    except (TypeError, ValueError):
        return default

SENT_CN = {'positive': '正面', 'negative': '负面', 'neutral': '中性'}
RISK_CN = {'high': '高风险', 'medium': '中风险', 'low': '低风险'}

def note_type_cn(t):
    return '视频' if t == 'video' else '图文'

def engagement(n):
    """互动量 = 点赞+评论+收藏+分享"""
    return _i(n.get('likes')) + _i(n.get('comments')) + _i(n.get('collects')) + _i(n.get('shares'))


def get_date_range(period, date_str=None):
    """获取日期范围"""
    if date_str:
        try:
            base_date = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            base_date = datetime.now()
    else:
        base_date = datetime.now()

    if period == 'daily':
        start = base_date.replace(hour=0, minute=0, second=0)
        end = base_date.replace(hour=23, minute=59, second=59)
    elif period == 'weekly':
        # 自然周：周一到周日
        start = (base_date - timedelta(days=base_date.weekday())).replace(hour=0, minute=0, second=0)
        end = (start + timedelta(days=6)).replace(hour=23, minute=59, second=59)
    elif period == 'monthly':
        # 自然月：1号到月底
        start = base_date.replace(day=1, hour=0, minute=0, second=0)
        if base_date.month == 12:
            end = base_date.replace(year=base_date.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            end = base_date.replace(month=base_date.month + 1, day=1) - timedelta(seconds=1)
    elif period == 'yearly':
        # 自然年：1.1到12.31
        start = base_date.replace(month=1, day=1, hour=0, minute=0, second=0)
        end = base_date.replace(month=12, day=31, hour=23, minute=59, second=59)
    else:
        start = base_date.replace(hour=0, minute=0, second=0)
        end = base_date.replace(hour=23, minute=59, second=59)

    return start, end


def filter_notes_by_period(period, date_str=None, require_negative_confirmed=False, start_date=None, end_date=None):
    """按周期筛选笔记；显式传入 start_date/end_date(YYYY-MM-DD) 时优先使用该范围"""
    start, end = get_date_range(period, date_str)
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            pass
    conn = get_db()
    c = conn.cursor()

    # 基础查询（ZBC Phase 9: 强制主体过滤，与 database._verified_base 同口径）
    try:
        from subject_rules import subject_sql_and_values
        _clause, _sp = subject_sql_and_values()
        query = f"SELECT * FROM notes WHERE is_taikoo_verified=1 AND COALESCE(relevance_status,'relevant')!='irrelevant' AND {_clause}"
        params = list(_sp)
    except Exception:
        # subject_rules 不可用时退化为 verified 过滤（仍比全表扫描安全）
        query = "SELECT * FROM notes WHERE is_taikoo_verified=1 AND COALESCE(relevance_status,'relevant')!='irrelevant'"
        params = []

    # 显式自定义范围 或 非日报周期：按发布日期落在区间
    if start_date or end_date or period != 'daily':
        query += " AND (publish_date >= ? AND publish_date <= ?)"
        params.extend([start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')])
    else:
        # 日报：只包含当日或前一日发布的笔记
        day_before = start - timedelta(days=1)
        query += " AND (publish_date >= ? OR publish_date IS NULL)"
        params.append(day_before.strftime('%Y-%m-%d'))

    # 负面笔记必须二次确认（周期报告）
    if require_negative_confirmed and period != 'daily':
        query += " AND (sentiment != 'negative' OR negative_confirmed = 1)"

    query += " ORDER BY collected_at DESC"

    c.execute(query, params)
    notes = [dict(row) for row in c.fetchall()]
    conn.close()

    return notes, start, end


def generate_report_data(period, date_str=None, start_date=None, end_date=None):
    """生成报告数据"""
    # 报告全量呈现负面（含待二次确认），不因“未人工确认”而隐藏造成“0负面”假正常；
    # negative_confirmed 状态随笔记带出，可在前端/导出中标注“待确认”。
    notes, start, end = filter_notes_by_period(period, date_str, require_negative_confirmed=False,
                                               start_date=start_date, end_date=end_date)

    # 只保留“有效舆情笔记”：剔除重复与噪音（irrelevant/low_quality/marketing/duplicate）
    # 报告的统计、事件、明细、Top 统一基于有效舆情笔记，避免重复/噪音虚高
    raw_total = len(notes)
    def _is_valid_yuqing(n):
        try:
            if int(n.get('is_duplicate') or 0) == 1:
                return False
        except (TypeError, ValueError):
            pass
        if (n.get('noise_type') or '').strip():
            return False
        return True
    notes = [n for n in notes if _is_valid_yuqing(n)]
    filtered_noise = raw_total - len(notes)

    # 统计
    total = len(notes)
    # [Canonical P0] 情感/风险分桶统一走 canonical_metrics（方案甲 high 不含 critical）
    from canonical_metrics import sentiment_count as _sc_fn, risk_count as _rc_fn
    _sc = _sc_fn(notes); _rc = _rc_fn(notes)
    positive, negative, neutral = _sc['positive'], _sc['negative'], _sc['neutral']

    # 高风险
    high_risk = _rc['high']

    # 品牌分布
    brand_dist = {}
    for n in notes:
        brand = n.get('category') or n.get('event_hint') or '未分类'
        brand_dist[brand] = brand_dist.get(brand, 0) + 1

    # 事件分类
    event_dist = {}
    for n in notes:
        event = n.get('event_hint') or n.get('category') or '未分类'
        event_dist[event] = event_dist.get(event, 0) + 1

    # 互动量 / 体裁 / 待确认负面 / 日均
    total_likes = sum(_i(n.get('likes')) for n in notes)
    total_comments = sum(_i(n.get('comments')) for n in notes)
    total_collects = sum(_i(n.get('collects')) for n in notes)
    total_shares = sum(_i(n.get('shares')) for n in notes)
    total_engagement = total_likes + total_comments + total_collects + total_shares
    video_cnt = sum(1 for n in notes if n.get('note_type') == 'video')
    text_cnt = total - video_cnt
    pending_neg = sum(1 for n in notes if n.get('sentiment') == 'negative' and n.get('negative_confirmed') in (0, None))
    days = max(1, (end.date() - start.date()).days + 1)
    # 重点笔记：负面优先（按风险+互动），负面不足时再以高互动其他笔记补足，保证报告聚焦风险
    _neg = sorted([n for n in notes if n.get('sentiment') == 'negative'],
                  key=lambda n: ({'high': 0, 'medium': 1, 'low': 2}.get(n.get('risk_level'), 3), -engagement(n)))
    _other = sorted([n for n in notes if n.get('sentiment') != 'negative'], key=engagement, reverse=True)
    top_notes = (_neg + _other)[:8]
    top_notes_negative_cnt = len(_neg[:8])

    # 周期内舆情事件（与系统事件中心同口径：events 表与周期时间重叠 + 主体过滤）
    period_events = []
    try:
        from subject_rules import subject_hit
        conn = get_db(); ce = conn.cursor()
        ev_rows = ce.execute(
            "SELECT * FROM events WHERE substr(COALESCE(NULLIF(event_date,''),first_seen),1,10) BETWEEN ? AND ? "
            "ORDER BY CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "
            "COALESCE(mention_count,0) DESC, COALESCE(event_date,first_seen,'') DESC LIMIT 30",
            (start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))).fetchall()
        conn.close()
        for r in ev_rows:
            d = dict(r)
            if subject_hit(d.get('title', ''), d.get('summary', ''), d.get('summary', ''), '', []):
                period_events.append(d)
    except Exception as _e:
        print("[Export] 周期事件读取跳过:", _e, flush=True)

    # 事件凝练：中高风险 / 提及≥2 / 非“相关讨论”模板标题才展开；单篇泛化低关注事件折叠计数
    def _is_generic_title(t):
        return (t or '').strip().endswith('相关讨论')
    featured_events, minor_event_cnt = [], 0
    for ev in period_events:
        try:
            mc = int(ev.get('mention_count') or 0)
        except (TypeError, ValueError):
            mc = 0
        rl = ev.get('risk_level')
        if rl in ('high', 'medium') or mc >= 2 or not _is_generic_title(ev.get('title')):
            featured_events.append(ev)
        else:
            minor_event_cnt += 1
    period_events = featured_events[:12]  # 报告最多展开12起，保持凝练

    # 一句话核心结论
    if total == 0:
        conclusion = '本周期未监测到有效舆情笔记。'
    else:
        _lv = '总体平稳' if negative == 0 else ('存在需重点关注负面' if high_risk == 0 else '出现高风险舆情，需立即关注')
        _ev_txt = f"重点舆情事件 {len(period_events)} 起"
        if minor_event_cnt:
            _ev_txt += f"（另有 {minor_event_cnt} 起单篇低关注讨论已归档）"
        conclusion = (f"本周期共收录有效舆情笔记 {total} 篇（已剔除重复/噪音 {filtered_noise} 篇），"
                      f"正面 {positive}、中性 {neutral}、负面 {negative}，高风险 {high_risk}；"
                      f"{_ev_txt}，互动总量 {total_engagement}，{_lv}。")

    return {
        'period': period,
        'date_range': f"{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}",
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'high_risk': high_risk,
            'pending_neg': pending_neg,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_collects': total_collects,
            'total_shares': total_shares,
            'total_engagement': total_engagement,
            'video_cnt': video_cnt,
            'text_cnt': text_cnt,
            'daily_avg': round(total / days, 1),
            'positive_rate': round(positive / total * 100, 1) if total > 0 else 0,
            'negative_rate': round(negative / total * 100, 1) if total > 0 else 0
        },
        'brand_distribution': dict(sorted(brand_dist.items(), key=lambda x: x[1], reverse=True)[:10]),
        'event_distribution': dict(sorted(event_dist.items(), key=lambda x: x[1], reverse=True)[:10]),
        'period_events': period_events,          # 周期内重点舆情事件（凝练后，与事件中心同口径）
        'period_events_minor': minor_event_cnt,  # 被折叠的单篇低关注事件数
        'raw_total': raw_total,                  # 周期内原始条数
        'filtered_noise': filtered_noise,        # 被剔除的重复/噪音条数
        'conclusion': conclusion,                # 一句话核心结论
        'top_engagement_notes': top_notes,
        'top_notes_negative_cnt': top_notes_negative_cnt,  # 重点笔记中负面条数（负面优先）
        'notes': notes[:100],  # 有效舆情笔记，最多100条
        'negative_notes': [n for n in notes if n.get('sentiment') == 'negative'][:50]
    }




_brand_matcher = None


def bind_brand_matcher(matcher):
    """Bind the existing brand matcher without duplicating brand-directory truth."""
    global _brand_matcher
    _brand_matcher = matcher


def _match_brand(note):
    if _brand_matcher is None:
        return '', ''
    return _brand_matcher(note)


def _classify_category(note):
    """太古汇核心业态分类：零售品牌、餐饮、商场服务、活动/展览、环境/设施、安全/突发事件"""
    brand, brand_category = _match_brand(note)
    if brand_category == '餐饮':
        return '餐饮'
    if brand_category in ('女装', '男装', '鞋包皮具', '珠宝钟表', '运动休闲', '童装玩具', '生活时尚', '美容护理'):
        return '零售品牌'
    # 关键词匹配
    text = (note.get('title', '') + ' ' + note.get('content', '') + ' ' + note.get('desc', '')).lower()
    if any(k in text for k in ['停车', '会员', '积分', '客服', '服务台', '投诉', '服务态度']):
        return '商场服务'
    if any(k in text for k in ['活动', '展览', '快闪', '排队', '规则', '奖品', '现场', '十五周年', '周年庆']):
        return '活动/展览'
    if any(k in text for k in ['卫生', '空调', '母婴室', '导视', '厕所', '洗手间', '环境', '设施']):
        return '环境/设施'
    if any(k in text for k in ['安全', '突发', '事故', '受伤', '盗窃', '纠纷', '打架']):
        return '安全/突发事件'
    return '其他'

def _calc_alert_level(stats, notes):
    """判断舆情等级：🔴重大 / 🟡关注 / 🟢平稳"""
    negative = stats.get('negative', 0)
    high_risk = stats.get('high_risk', 0)
    total = stats.get('total', len(notes))
    if total == 0:
        return '🟢平稳', '本期无监测数据'
    neg_ratio = negative / total if total > 0 else 0
    if high_risk >= 3 or neg_ratio >= 0.3:
        return '🔴重大', f'负面占比{neg_ratio*100:.0f}%，高风险{high_risk}条，需立即响应'
    if high_risk >= 1 or neg_ratio >= 0.15:
        return '🟡关注', f'负面占比{neg_ratio*100:.0f}%，高风险{high_risk}条，需持续关注'
    return '🟢平稳', f'负面占比{neg_ratio*100:.0f}%，整体舆情平稳'

def _generate_core_conclusion(stats, notes, category_stats):
    """生成1句话核心结论"""
    total = stats.get('total', len(notes))
    negative = stats.get('negative', 0)
    max_engagement = max([int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3 for n in notes], default=0)
    # 找最高负面业态
    top_category = max(category_stats.items(), key=lambda x: x[1].get('negative',0), default=(None, {}))
    top_cat_name = top_category[0] if top_category[0] else '综合'
    top_cat_neg = top_category[1].get('negative', 0) if top_category[1] else 0
    # 判断是否扩散
    spreading = '已出现扩散' if max_engagement > 500 else '暂无扩散'
    return f'本期共监测小红书舆情{total}条，负面{negative}条，主要集中在【{top_cat_name}】，最高互动{max_engagement}，{spreading}。'

# ========== 报告导出（太古汇舆情汇报模板） ==========
def export_report_to_csv(report_type='daily', date_str=None, start_date=None, end_date=None):
    """按太古汇舆情汇报模板导出CSV；显式 start/end 优先，保持所有导出入口同一周期 Truth。"""
    now = datetime.now()
    date_str = date_str or now.strftime('%Y-%m-%d')
    range_start, range_end = get_date_range(report_type, date_str)
    if start_date:
        range_start = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
    if end_date:
        range_end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    start = range_start.strftime('%Y-%m-%d')
    end = range_end.strftime('%Y-%m-%d')
    period_label = start.replace("-", ".") if start == end else f'{start.replace("-",".")} – {end.replace("-",".")}'

    notes = db.get_notes_by_date_range(start, end)
    stats = db.get_stats_by_date_range(start, end)

    # 环比统一按当前实际周期长度向前平移，避免不同入口用不同“上一周期”定义。
    try:
        current_start = datetime.strptime(start, '%Y-%m-%d')
        current_end = datetime.strptime(end, '%Y-%m-%d')
        span_days = max(1, (current_end - current_start).days + 1)
        prev_end_dt = current_start - timedelta(days=1)
        prev_start_dt = prev_end_dt - timedelta(days=span_days - 1)
        prev_start = prev_start_dt.strftime('%Y-%m-%d')
        prev_end = prev_end_dt.strftime('%Y-%m-%d')
        prev_notes = db.get_notes_by_date_range(prev_start, prev_end)
        prev_stats = db.get_stats_by_date_range(prev_start, prev_end)
    except Exception:
        prev_stats = {'total': 0, 'negative': 0, 'positive': 0, 'high_risk': 0, 'total_engagement': 0}

    # 分业态统计
    category_stats = {}
    category_order = ['零售品牌', '餐饮', '商场服务', '活动/展览', '环境/设施', '安全/突发事件', '其他']
    for n in notes:
        cat = _classify_category(n)
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'negative': 0, 'positive': 0, 'engagement': 0, 'topics': [], 'brands': []}
        category_stats[cat]['total'] += 1
        sent = n.get('sentiment', '')
        if sent == 'negative': category_stats[cat]['negative'] += 1
        elif sent == 'positive': category_stats[cat]['positive'] += 1
        category_stats[cat]['engagement'] += int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
        brand, _ = _match_brand(n)
        if brand and brand not in category_stats[cat]['brands']:
            category_stats[cat]['brands'].append(brand)

    # 舆情等级
    alert_level, alert_desc = _calc_alert_level(stats, notes)
    # 核心结论
    core_conclusion = _generate_core_conclusion(stats, notes, category_stats)

    output = io.StringIO()
    # 写入BOM以便Excel正确识别中文
    output.write('\ufeff')
    writer = csv.writer(output)

    # ===== 表头 =====
    report_title = '舆情日报' if report_type == 'daily' else ('舆情专报' if report_type in ('weekly',) else f'舆情{report_type}报')
    writer.writerow([f'【{report_title}】'])
    writer.writerow([f'汇报周期：{period_label}'])
    writer.writerow(['汇报人：舆情监测系统'])
    writer.writerow([f'舆情等级：{alert_level} — {alert_desc}'])
    writer.writerow([])

    # ===== 1. 核心结论 =====
    writer.writerow(['1. 核心结论（1句话）'])
    writer.writerow([core_conclusion])
    writer.writerow([])

    # ===== 2. 数据概览 =====
    writer.writerow(['2. 数据概览'])
    writer.writerow(['指标', '本期', '环比'])
    cur_total = stats.get('total', len(notes))
    prev_total = prev_stats.get('total', 0)
    cur_neg = stats.get('negative', 0)
    prev_neg = prev_stats.get('negative', 0)
    cur_pos = stats.get('positive', 0)
    max_eng = max([int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3 for n in notes], default=0)
    def pct_change(cur, prev):
        if prev == 0: return '—' if cur == 0 else '+∞'
        change = (cur - prev) / prev * 100
        return f'{"+" if change >= 0 else ""}{change:.1f}%'
    writer.writerow(['总提及量', cur_total, pct_change(cur_total, prev_total)])
    writer.writerow(['负面量', cur_neg, pct_change(cur_neg, prev_neg)])
    neg_ratio = f'{(cur_neg/cur_total*100):.1f}%' if cur_total > 0 else '0%'
    prev_neg_ratio = f'{(prev_neg/prev_total*100):.1f}%' if prev_total > 0 else '0%'
    writer.writerow(['负面占比', neg_ratio, f'{"+" if float(neg_ratio.strip("%")) >= float(prev_neg_ratio.strip("%")) else ""}{float(neg_ratio.strip("%"))-float(prev_neg_ratio.strip("%")):.1f}pp'])
    writer.writerow(['最高单条互动', max_eng, '—'])
    writer.writerow([])

    # ===== 3. 分业态舆情分布 =====
    writer.writerow(['3. 分业态舆情分布（太古汇核心维度）'])
    writer.writerow(['业态/模块', '提及量', '负面量', '主要话题/品牌', '等级'])
    for cat in category_order:
        if cat not in category_stats: continue
        cs = category_stats[cat]
        neg = cs['negative']
        total = cs['total']
        if neg >= 3 or (total > 0 and neg/total >= 0.3):
            level = '🔴'
        elif neg >= 1 or (total > 0 and neg/total >= 0.15):
            level = '🟡'
        else:
            level = '🟢'
        topics = '、'.join(cs['brands'][:3]) if cs['brands'] else '—'
        writer.writerow([cat, total, neg, topics, level])
    writer.writerow([])

    # ===== 4. 重点负面帖清单 =====
    writer.writerow(['4. 重点负面帖清单'])
    writer.writerow(['序号', '业态', '笔记标题', '发布时间', '互动量', '核心诉求', '处理状态'])
    negative_notes = [n for n in notes if n.get('sentiment') == 'negative' or n.get('risk_level') in ('high', 'critical')]
    negative_notes.sort(key=lambda x: int(x.get('likes',0) or 0) + int(x.get('comments',0) or 0)*3, reverse=True)
    for i, n in enumerate(negative_notes[:15], 1):
        cat = _classify_category(n)
        engagement = int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
        # 核心诉求（从内容提取前30字）
        content = n.get('content', '') or n.get('desc', '') or n.get('summary', '') or ''
        core_demand = content[:40] + '...' if len(content) > 40 else content
        writer.writerow([i, cat, n.get('title', '')[:50], n.get('publish_date', ''), engagement, core_demand, '待处理'])
    if not negative_notes:
        writer.writerow(['—', '—', '本期无重点负面帖', '—', '—', '—', '—'])
    writer.writerow([])

    # ===== 5. 舆情归因 =====
    writer.writerow(['5. 舆情归因'])
    # 高发业态
    if category_stats:
        top_cat = max(category_stats.items(), key=lambda x: x[1]['negative'])
        total_neg = sum(cs['negative'] for cs in category_stats.values())
        high_cat_ratio = f'{(top_cat[1]["negative"]/total_neg*100):.0f}%' if total_neg > 0 else '0%'
        writer.writerow([f'高发业态：{top_cat[0]}（占负面{high_cat_ratio}）'])
    else:
        writer.writerow(['高发业态：—'])
    # 触发类型
    trigger_types = []
    for n in negative_notes[:10]:
        text = (n.get('title','') + ' ' + n.get('content','') + ' ' + n.get('desc','')).lower()
        if any(k in text for k in ['服务态度', '店员', '客服', '态度差']): trigger_types.append('服务态度')
        elif any(k in text for k in ['活动', '规则', '排队', '奖品']): trigger_types.append('活动规则')
        elif any(k in text for k in ['空调', '卫生', '设施', '厕所', '母婴室']): trigger_types.append('硬件设施')
        elif any(k in text for k in ['品牌', '专柜', '缺货', '价格']): trigger_types.append('品牌商户')
        elif any(k in text for k in ['价格', '贵', '涨价']): trigger_types.append('价格争议')
    trigger_str = ' / '.join(list(dict.fromkeys(trigger_types))[:4]) if trigger_types else '综合'
    writer.writerow([f'触发类型：{trigger_str}'])
    writer.writerow(['传播路径：素人发帖 → 评论区共鸣 → KOC/本地号转发'])
    writer.writerow([])

    # ===== 6. 应对动作 & 下一步 =====
    writer.writerow(['6. 应对动作 & 下一步'])
    writer.writerow(['已执行：系统自动采集、分类、风险标记，高风险内容已推送预警'])
    writer.writerow(['待执行：重点负面帖人工复核与回复（责任部门：公关部/运营部/对接人/截止时间：24小时内）'])
    # 风险预警
    risk_warnings = []
    if any('十五周年' in (n.get('title','')+n.get('content','')) for n in notes):
        risk_warnings.append('广州太古汇15周年庆活动期间，预计客流激增，需提前准备停车/排队话术，提高危机敏感意识')
    if category_stats.get('活动/展览', {}).get('negative', 0) > 0:
        risk_warnings.append('活动/展览类负面上升，建议现场增派人手疏导，优化活动规则说明')
    if max_eng > 500:
        risk_warnings.append('出现高互动内容，需密切关注传播趋势，必要时启动公关响应')
    if not risk_warnings:
        risk_warnings.append('暂无特殊风险预警，保持常规监测频率')
    writer.writerow([f'风险预警：{"；".join(risk_warnings)}'])
    writer.writerow([])
    writer.writerow([f'报告生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow(['数据来源：小红书/rednote 真实采集 · 太古汇场内品牌目录（2026.08.20更新）'])

    filename = f'太古汇{report_title}_{date_str}.csv'
    return output.getvalue(), filename

def export_artifacts(kind='daily', start=None, end=None, formats=('docx', 'csv', 'xlsx')):
    """唯一文件导出 facade：所有 DOCX/CSV/XLSX artifact 统一由 Shared Reporting export_api 生成与校验。"""
    allowed = {'docx', 'csv', 'xlsx'}
    requested = tuple(dict.fromkeys(str(x).lower() for x in formats))
    unknown = [x for x in requested if x not in allowed]
    if unknown:
        raise ValueError(f"不支持的导出格式: {unknown}")

    date_str = end or start
    files = {}
    if 'xlsx' in requested:
        path = _export_excel(kind, date_str, start, end)
        if not isinstance(path, str) or not path.lower().endswith('.xlsx'):
            raise RuntimeError(f"XLSX 导出未返回有效文件路径: {path}")
        files['xlsx'] = path

    if 'docx' in requested:
        path = _export_word(kind, date_str, start, end)
        if not isinstance(path, str) or not path.lower().endswith('.docx'):
            raise RuntimeError(f"DOCX 导出未返回有效文件路径: {path}")
        files['docx'] = path

    if 'csv' in requested:
        csv_content, filename = export_report_to_csv(kind, date_str, start, end)
        path = os.path.join(EXPORT_DIR, filename)
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(csv_content)
        files['csv'] = path

    verified = {}
    for fmt, path in files.items():
        vr = ra.verify_artifact_file(path)
        verified[fmt] = {
            'exists': vr['exists'], 'size': vr['size'], 'hash': vr['hash'], 'valid': vr['valid']
        }
        if not vr['valid']:
            raise RuntimeError(f"导出 artifact 校验失败 [{fmt}]: {vr['reason']}")

    resolved_start, resolved_end = get_date_range(kind, date_str)
    if start:
        resolved_start = datetime.strptime(start, '%Y-%m-%d')
    if end:
        resolved_end = datetime.strptime(end, '%Y-%m-%d')
    return {
        'files': files,
        'artifact_verified': verified,
        'payload': {
            'report_type': kind,
            'period_start': resolved_start.strftime('%Y-%m-%d'),
            'period_end': resolved_end.strftime('%Y-%m-%d'),
        },
    }


# ============================================
# API接口
# ============================================

@export_bp.route('/api/export/preview')
def export_preview():
    """预览报告数据"""
    try:
        period = request.args.get('period', 'daily')
        date_str = request.args.get('date')

        report_data = generate_report_data(period, date_str)
        return jsonify({'ok': True, 'data': report_data})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@export_bp.route('/api/export/excel')
def export_excel():
    r = _export_excel(request.args.get('period', 'daily'), request.args.get('date'),
                      request.args.get('start'), request.args.get('end'))
    return r if not isinstance(r, str) else send_file(r, as_attachment=True, download_name=os.path.basename(r))


def _export_excel(period, date_str=None, start_date=None, end_date=None):
    """生成并返回 Excel 报告（内部复用，统一入口也调用）"""
    try:
        report_data = generate_report_data(period, date_str, start_date, end_date)

        # 生成Excel文件
        filename = f"太古汇舆情_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(EXPORT_DIR, filename)

        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            wb = openpyxl.Workbook()

            # Sheet1: 概览
            ws1 = wb.active
            ws1.title = "报告概览"

            # 标题
            ws1['A1'] = "广州太古汇舆情监测报告"
            ws1['A1'].font = Font(size=16, bold=True)
            ws1.merge_cells('A1:F1')

            ws1['A2'] = f"报告周期：{report_data['date_range']}"
            ws1['A2'].font = Font(size=11)
            ws1.merge_cells('A2:F2')

            ws1['A3'] = f"生成时间：{report_data['generated_at']}"
            ws1['A3'].font = Font(size=11, color='666666')
            ws1.merge_cells('A3:F3')

            ws1['A4'] = f"核心结论：{report_data.get('conclusion','')}"
            ws1['A4'].font = Font(size=11, bold=True, color='1A73E8')
            ws1.merge_cells('A4:F4')

            # 统计数据
            ws1['A5'] = "数据统计"
            ws1['A5'].font = Font(size=13, bold=True)

            s = report_data['summary']
            stats = [
                ['有效舆情笔记', s['total']],
                ['原始收录 / 剔除噪音', f"{report_data.get('raw_total', s['total'])} / {report_data.get('filtered_noise', 0)}"],
                ['聚合舆情事件', len(report_data.get('period_events') or [])],
                ['日均笔记', s.get('daily_avg', 0)],
                ['正面舆情', s['positive']],
                ['负面舆情', s['negative']],
                ['中性舆情', s['neutral']],
                ['高风险内容', s['high_risk']],
                ['待确认负面', s.get('pending_neg', 0)],
                ['图文 / 视频', f"{s.get('text_cnt', 0)} / {s.get('video_cnt', 0)}"],
                ['正面占比', f"{s['positive_rate']}%"],
                ['负面占比', f"{s['negative_rate']}%"],
                ['互动总量', s.get('total_engagement', 0)],
                ['点赞 / 评论', f"{s.get('total_likes', 0)} / {s.get('total_comments', 0)}"],
                ['收藏 / 分享', f"{s.get('total_collects', 0)} / {s.get('total_shares', 0)}"],
            ]

            for i, (label, value) in enumerate(stats, 6):
                ws1[f'A{i}'] = label
                ws1[f'B{i}'] = value
                ws1[f'A{i}'].font = Font(bold=True)

            # Sheet2: 笔记明细（运营数据表：体裁/曝光/互动等；小红书专业号后台才有的列保留—）
            ws2 = wb.create_sheet("笔记明细")
            headers = ['序号', '笔记标题', '首次发布时间', '体裁', '曝光', '观看量', '封面点击率',
                       '点赞', '评论', '收藏', '分享', '互动', '涨粉', '情绪', '风险等级']
            for col, header in enumerate(headers, 1):
                cell = ws2.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color='E8F0FE', end_color='E8F0FE', fill_type='solid')

            sum_like = sum_cmt = sum_col = sum_shr = sum_eng = 0
            for i, note in enumerate(report_data['notes'], 2):
                lk, cm, cl, sh = _i(note.get('likes')), _i(note.get('comments')), _i(note.get('collects')), _i(note.get('shares'))
                eng = lk + cm + cl + sh
                sum_like += lk; sum_cmt += cm; sum_col += cl; sum_shr += sh; sum_eng += eng
                pub = note.get('publish_datetime') or note.get('publish_date') or ''
                row_vals = [i - 1, (note.get('title', '') or '')[:100], pub, note_type_cn(note.get('note_type')),
                            '—', '—', '—', lk, cm, cl, sh, eng, '—',
                            SENT_CN.get(note.get('sentiment'), note.get('sentiment') or ''),
                            RISK_CN.get(note.get('risk_level'), note.get('risk_level') or '')]
                for col, val in enumerate(row_vals, 1):
                    ws2.cell(row=i, column=col, value=val)
            # 合计行
            tr = len(report_data['notes']) + 2
            tc = ws2.cell(row=tr, column=2, value='合计'); tc.font = Font(bold=True)
            for col, val in [(8, sum_like), (9, sum_cmt), (10, sum_col), (11, sum_shr), (12, sum_eng)]:
                ws2.cell(row=tr, column=col, value=val).font = Font(bold=True)
            for col, w in enumerate([6, 42, 20, 8, 8, 8, 10, 7, 7, 7, 7, 8, 8, 8, 10], 1):
                ws2.column_dimensions[chr(64 + col)].width = w

            # Sheet3: 舆情事件分析（与系统事件中心同口径；无事件写“无”，不凑空表）
            ws3 = wb.create_sheet("舆情事件")
            ev_list = report_data.get('period_events') or []
            ev_headers = ['序号', '事件标题', '风险等级', '提及量', '首次出现', '最近出现', '事件概述', '风险研判', '建议动作']
            for col, header in enumerate(ev_headers, 1):
                cell = ws3.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color='E8F0FE', end_color='E8F0FE', fill_type='solid')
            if ev_list:
                for i, ev in enumerate(ev_list, 2):
                    ws3.cell(row=i, column=1, value=i - 1)
                    ws3.cell(row=i, column=2, value=(ev.get('title', '') or '')[:120])
                    ws3.cell(row=i, column=3, value=RISK_CN.get(ev.get('risk_level'), ev.get('risk_level') or ''))
                    ws3.cell(row=i, column=4, value=ev.get('mention_count', 0))
                    ws3.cell(row=i, column=5, value=ev.get('first_seen', ''))
                    ws3.cell(row=i, column=6, value=ev.get('last_seen', ''))
                    ws3.cell(row=i, column=7, value=(ev.get('summary', '') or '')[:500])
                    ws3.cell(row=i, column=8, value=(ev.get('risk_reason', '') or '')[:300])
                    ws3.cell(row=i, column=9, value=(ev.get('recommended_action', '') or '')[:300])
                if report_data.get('period_events_minor'):
                    ws3.cell(row=len(ev_list) + 2, column=1,
                             value=f"另有 {report_data['period_events_minor']} 起单篇低关注泛化讨论已归档，不单独展开")
            else:
                ws3.cell(row=2, column=1, value='本期无显著聚合舆情事件')
            for col, w in enumerate([6, 34, 10, 8, 12, 12, 50, 36, 36], 1):
                ws3.column_dimensions[chr(64 + col)].width = w

            wb.save(filepath)
            print(f"[Export] Excel报告已生成: {filename}", flush=True)
            # ZBC Phase 9: 保存后验证文件真实存在且非空
            if ra:
                _v = ra.verify_artifact_file(filepath)
                if not _v['valid']:
                    raise RuntimeError(f"Excel artifact 校验失败: {_v['reason']}")

        except ImportError:
            # 如果没有openpyxl，生成CSV
            import csv
            filepath = filepath.replace('.xlsx', '.csv')
            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['广州太古汇舆情监测报告'])
                writer.writerow([f"报告周期：{report_data['date_range']}"])
                writer.writerow([])
                writer.writerow(['序号', '标题', '作者', '情绪', '风险等级', '品牌', '发布时间'])
                for i, note in enumerate(report_data['notes'], 1):
                    writer.writerow([i, note.get('title', ''), note.get('author_nickname', ''),
                                   note.get('sentiment', ''), note.get('risk_level', ''),
                                   note.get('category', ''), note.get('publish_date', '')])

        return filepath

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@export_bp.route('/api/export/word')
def export_word():
    r = _export_word(request.args.get('period', 'daily'), request.args.get('date'),
                     request.args.get('start'), request.args.get('end'))
    return r if not isinstance(r, str) else send_file(r, as_attachment=True, download_name=os.path.basename(r))


def _export_word(period, date_str=None, start_date=None, end_date=None):
    """生成并返回 Word 报告（内部复用，统一入口也调用）"""
    try:
        report_data = generate_report_data(period, date_str, start_date, end_date)

        filename = f"太古汇舆情_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        filepath = os.path.join(EXPORT_DIR, filename)

        try:
            from docx import Document
            from docx.shared import Pt, Inches, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = Document()

            # 标题
            title = doc.add_heading('广州太古汇舆情监测报告', level=0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER

            # 报告信息
            info = doc.add_paragraph()
            info.add_run(f"报告周期：{report_data['date_range']}\n").bold = True
            info.add_run(f"生成时间：{report_data['generated_at']}\n")
            info.add_run(f"数据来源：小红书舆情监测系统")

            doc.add_paragraph()

            # 一、核心结论
            doc.add_heading('一、核心结论', level=1)
            pcon = doc.add_paragraph()
            pcon.add_run(report_data.get('conclusion', '')).font.size = Pt(11)
            if report_data.get('filtered_noise', 0):
                note_p = doc.add_paragraph(f"注：已自动剔除重复/低质/无关笔记 {report_data['filtered_noise']} 篇，报告仅呈现有效舆情笔记。")
                note_p.runs[0].font.size = Pt(9)
                note_p.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)

            doc.add_paragraph()

            # 二、数据概览
            doc.add_heading('二、数据概览', level=1)

            summary = report_data['summary']
            overview_table = doc.add_table(rows=6, cols=4)
            overview_table.style = 'Table Grid'

            cells = overview_table.rows[0].cells
            cells[0].text = '监测总数'
            cells[1].text = str(summary['total'])
            cells[2].text = '日均笔记'
            cells[3].text = str(summary.get('daily_avg', 0))

            cells = overview_table.rows[1].cells
            cells[0].text = '正面舆情'
            cells[1].text = f"{summary['positive']} ({summary['positive_rate']}%)"
            cells[2].text = '负面舆情'
            cells[3].text = f"{summary['negative']} ({summary['negative_rate']}%)"

            cells = overview_table.rows[2].cells
            cells[0].text = '中性舆情'
            cells[1].text = str(summary['neutral'])
            cells[2].text = '高风险内容'
            cells[3].text = str(summary['high_risk'])

            cells = overview_table.rows[3].cells
            cells[0].text = '图文 / 视频'
            cells[1].text = f"{summary.get('text_cnt', 0)} / {summary.get('video_cnt', 0)}"
            cells[2].text = '待确认负面'
            cells[3].text = str(summary.get('pending_neg', 0))

            cells = overview_table.rows[4].cells
            cells[0].text = '互动总量'
            cells[1].text = str(summary.get('total_engagement', 0))
            cells[2].text = '点赞 / 评论'
            cells[3].text = f"{summary.get('total_likes', 0)} / {summary.get('total_comments', 0)}"

            cells = overview_table.rows[5].cells
            cells[0].text = '收藏 / 分享'
            cells[1].text = f"{summary.get('total_collects', 0)} / {summary.get('total_shares', 0)}"
            cells[2].text = ''
            cells[3].text = ''

            # 高互动笔记 Top（最具传播力内容）
            top_notes = report_data.get('top_engagement_notes') or []
            if top_notes:
                doc.add_paragraph()
                doc.add_heading('高互动传播亮点 Top' + str(len(top_notes)), level=2)
                ttable = doc.add_table(rows=1, cols=5)
                ttable.style = 'Table Grid'
                for i, h in enumerate(['排名', '笔记标题', '体裁', '互动量', '情绪/风险']):
                    ttable.rows[0].cells[i].text = h
                for rank, n in enumerate(top_notes, 1):
                    r = ttable.add_row()
                    r.cells[0].text = str(rank)
                    r.cells[1].text = (n.get('title', '') or '')[:40]
                    r.cells[2].text = note_type_cn(n.get('note_type'))
                    r.cells[3].text = str(engagement(n))
                    r.cells[4].text = f"{SENT_CN.get(n.get('sentiment'), '')}/{RISK_CN.get(n.get('risk_level'), '')}"

            doc.add_paragraph()

            # 内容分类分布（概览子表）
            doc.add_heading('内容分类分布', level=2)
            if report_data['brand_distribution']:
                brand_table = doc.add_table(rows=1, cols=3)
                brand_table.style = 'Table Grid'
                brand_table.rows[0].cells[0].text = '内容分类'
                brand_table.rows[0].cells[1].text = '笔记数'
                brand_table.rows[0].cells[2].text = '占比'
                _tot = summary['total'] or 1
                for brand, count in report_data['brand_distribution'].items():
                    row = brand_table.add_row()
                    row.cells[0].text = str(brand)
                    row.cells[1].text = str(count)
                    row.cells[2].text = f"{round(count / _tot * 100, 1)}%"

            doc.add_paragraph()

            # 三、舆情事件分析（与系统事件中心同口径；无事件则写“无”，不凑空表）
            doc.add_paragraph()
            doc.add_heading('三、舆情事件分析', level=1)
            period_events = report_data.get('period_events') or []
            if period_events:
                ev_risk_cn = {'high': '【高风险】', 'medium': '【中风险】', 'low': '【低风险】'}
                for idx, ev in enumerate(period_events, 1):
                    tag = ev_risk_cn.get(ev.get('risk_level'), '【未评级】')
                    doc.add_heading(
                        f"{idx}. {ev.get('title','未命名事件')}  {tag} 提及{ev.get('mention_count',0)} "
                        f"（{ev.get('first_seen','')} 至 {ev.get('last_seen','')}）", level=2)
                    if ev.get('summary'):
                        doc.add_paragraph(f"事件概述：{ev['summary']}")
                    if ev.get('risk_reason'):
                        doc.add_paragraph(f"风险研判：{ev['risk_reason']}")
                    if ev.get('impact'):
                        doc.add_paragraph(f"影响评估：{ev['impact']}")
                    if ev.get('recommended_action'):
                        doc.add_paragraph(f"建议动作：{ev['recommended_action']}")
                if report_data.get('period_events_minor'):
                    mp = doc.add_paragraph(f"另有 {report_data['period_events_minor']} 起单篇、低关注度的泛化讨论已归档入库，不单独展开。")
                    mp.runs[0].font.size = Pt(9)
                    mp.runs[0].font.color.rgb = RGBColor(0x88, 0x88, 0x88)
            else:
                doc.add_paragraph('本期无显著聚合舆情事件。')

            doc.add_paragraph()

            # 四、舆情笔记明细（有效舆情笔记；互动 = 点赞+评论+收藏+分享）
            doc.add_heading('四、舆情笔记明细（有效）', level=1)
            np = doc.add_paragraph()
            np.add_run('仅列与广州太古汇相关的有效舆情笔记（已剔除重复/噪音）；曝光、观看量、封面点击率、涨粉为小红书专业号后台数据，本系统不采集，统一记为「—」，完整字段见 Excel；互动量 = 点赞+评论+收藏+分享。').font.size = Pt(9)
            if report_data['notes']:
                cols = ['序号', '笔记标题', '首次发布时间', '体裁', '点赞', '评论', '收藏', '分享', '互动', '情绪', '风险']
                all_table = doc.add_table(rows=1, cols=len(cols))
                all_table.style = 'Table Grid'
                for i, h in enumerate(cols):
                    all_table.rows[0].cells[i].text = h
                SL = SC = MS = MH = ME = 0
                for i, note in enumerate(report_data['notes'][:60], 1):
                    lk, cm, cl, sh = _i(note.get('likes')), _i(note.get('comments')), _i(note.get('collects')), _i(note.get('shares'))
                    eng = lk + cm + cl + sh
                    SL += lk; SC += cm; MS += cl; MH += sh; ME += eng
                    vals = [str(i), (note.get('title', '') or '')[:46],
                            note.get('publish_datetime') or note.get('publish_date') or '',
                            note_type_cn(note.get('note_type')), str(lk), str(cm), str(cl), str(sh), str(eng),
                            SENT_CN.get(note.get('sentiment'), note.get('sentiment') or ''),
                            RISK_CN.get(note.get('risk_level'), note.get('risk_level') or '')]
                    row = all_table.add_row()
                    for j, v in enumerate(vals):
                        row.cells[j].text = v
                # 合计行
                trow = all_table.add_row()
                tvals = ['', '合计', '', '', str(SL), str(SC), str(MS), str(MH), str(ME), '', '']
                for j, v in enumerate(tvals):
                    trow.cells[j].text = v
                    for para in trow.cells[j].paragraphs:
                        for run in para.runs:
                            run.bold = True
            else:
                doc.add_paragraph('本期无有效舆情笔记。')

            # 页脚
            doc.add_paragraph()
            footer = doc.add_paragraph()
            footer.add_run('—— 本报告由广州太古汇舆情监测系统自动生成 ——').italic = True
            footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

            doc.save(filepath)
            print(f"[Export] Word报告已生成: {filename}", flush=True)
            # ZBC Phase 9: 保存后验证文件真实存在且非空
            if ra:
                _v = ra.verify_artifact_file(filepath)
                if not _v['valid']:
                    raise RuntimeError(f"Word artifact 校验失败: {_v['reason']}")

        except ImportError:
            # 如果没有python-docx，生成TXT
            filepath = filepath.replace('.docx', '.txt')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("广州太古汇舆情监测报告\n")
                f.write(f"报告周期：{report_data['date_range']}\n")
                f.write(f"生成时间：{report_data['generated_at']}\n\n")
                f.write("一、数据概览\n")
                f.write(f"监测总数：{summary['total']}\n")
                f.write(f"正面：{summary['positive']} ({summary['positive_rate']}%)\n")
                f.write(f"负面：{summary['negative']} ({summary['negative_rate']}%)\n")
                f.write(f"中性：{summary['neutral']}\n\n")
                f.write("二、负面舆情清单\n")
                for i, note in enumerate(report_data['negative_notes'][:20], 1):
                    f.write(f"{i}. {note.get('title', '')} - {note.get('author_nickname', '')}\n")

        return filepath

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@export_bp.route('/api/export/list')
def export_list():
    """获取已导出的报告列表"""
    try:
        files = []
        if os.path.exists(EXPORT_DIR):
            for f in os.listdir(EXPORT_DIR):
                filepath = os.path.join(EXPORT_DIR, f)
                if os.path.isfile(filepath):
                    files.append({
                        'name': f,
                        'size': round(os.path.getsize(filepath) / 1024, 1),
                        'created_at': datetime.fromtimestamp(os.path.getctime(filepath)).strftime('%Y-%m-%d %H:%M:%S')
                    })
        files.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({'ok': True, 'files': files[:50]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def _send_build(r):
    """内部构建结果：字符串路径则发送文件，否则透传错误 Response"""
    return r if not isinstance(r, str) else send_file(r, as_attachment=True, download_name=os.path.basename(r))


@export_bp.route('/api/export/report')
def export_unified():
    """统一导出入口，兼容前端 exportReportWithVerify(type, format)
    type=daily/weekly/monthly/yearly（等价 period）；format=xlsx/excel 或 docx/word
    """
    period = request.args.get('type') or request.args.get('period') or 'daily'
    fmt = (request.args.get('format') or 'xlsx').lower()
    date_str = request.args.get('date')
    s, e = request.args.get('start'), request.args.get('end')
    if period == 'annual':
        period = 'yearly'
    if fmt in ('docx', 'word'):
        return _send_build(_export_word(period, date_str, s, e))
    return _send_build(_export_excel(period, date_str, s, e))


@export_bp.route('/api/export/generate', methods=['POST', 'GET'])
def export_generate():
    """报告中心-生成报告：落盘并返回下载链接（前端 result.download_url 契约）"""
    try:
        period = request.values.get('type') or request.values.get('period') or 'daily'
        fmt = (request.values.get('format') or 'xlsx').lower()
        date_str = request.values.get('date')
        s, e = request.values.get('start'), request.values.get('end')
        if period == 'annual':
            period = 'yearly'
        r = _export_word(period, date_str, s, e) if fmt in ('docx', 'word') else _export_excel(period, date_str, s, e)
        if not isinstance(r, str):
            return r  # 内部错误 Response
        # ZBC Phase 9: 返回前验证文件真实存在且非空，禁止假成功
        if ra:
            _v = ra.verify_artifact_file(r)
            if not _v['valid']:
                return jsonify({'ok': False, 'error': f'导出文件校验失败: {_v["reason"]}', 'filepath': r}), 500
        from urllib.parse import quote
        name = os.path.basename(r)
        return jsonify({'ok': True, 'name': name, 'download_url': f'/api/export/file/{quote(name)}',
                        'size': _v['size'] if ra else os.path.getsize(r),
                        'artifact_hash': _v['hash'] if ra else ''})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@export_bp.route('/api/export/file/<path:filename>')
def export_file(filename):
    """下载已生成的导出文件（basename 防路径穿越）"""
    safe = os.path.basename(filename)
    fpath = os.path.join(EXPORT_DIR, safe)
    if not os.path.isfile(fpath):
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    return send_from_directory(EXPORT_DIR, safe, as_attachment=True)


print("[Export] 导出报告模板模块已加载", flush=True)