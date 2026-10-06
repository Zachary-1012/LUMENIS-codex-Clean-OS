"""
LUMENIS CTH reference-subject compatibility filter
============================================
数据流转：原始数据 → 主体过滤 → AI二次判断 → 有效舆情库 → 事件分析 → 日报

核心能力：
1. AI二次判断：对通过主体过滤的笔记进行相关性二次校验
2. 去重检测：自动识别重复/搬运内容
3. 垃圾内容清理：识别营销号、广告、无意义内容
4. 内容质量评分：0-1分，低质量内容降级
5. 规则引擎兜底：无AI Key时使用可审计的本地规则

不可动摇的红线：
- 主体过滤（SUBJECT_WORDS / subject_hit()）永远是第一道关
- AI过滤层只做二次判断，不放宽主体口径
- 所有AI判断必须可追溯、可审计、可人工修正
"""
import re
import json
import hashlib
import os
from datetime import datetime

import database as db
import ai_analyzer
import intelligence

# ZBC Phase 7: module status markers
MODULE_STATUS = 'ACTIVE'
AI_ROLE = 'SECONDARY_REVIEW_ONLY'
SUBJECT_FILTER_FIRST = True  # subject filtering is the first gate, AI only does secondary review

# ============== 垃圾/营销内容特征词 ==============
SPAM_KEYWORDS = {
    '加微信', '加v', '私聊', '私信我', '联系方式', '代购', '代拍',
    '刷单', '兼职', '日结', '赚钱', '副业', '引流', '涨粉',
    '点击链接', '扫码', '二维码', '福利群', '粉丝群', '优惠券',
    '全网最低', '最低价', '亏本', '清仓大甩卖', '限时秒杀',
    '复制打开', '淘宝', '拼多多', '1688', '闲鱼',
}

MARKETING_PATTERNS = [
    r'[vV信微信][:：]?\s*[a-zA-Z0-9_-]{5,}',
    r'手机号[:：]?\s*1[3-9]\d{9}',
    r'QQ[:：]?\s*\d{5,}',
    r'https?://[^\s]+(?:taobao|pinduoduo|jd\.com|1688)',
]

LOW_QUALITY_PATTERNS = [
    r'^[^\u4e00-\u9fff]{0,5}$',  # 几乎没有中文内容
    r'^(哈哈|呵呵|嗯|啊|哦|。。。|\.\.\.)+$',  # 无意义语气词
    r'^[emoji\s]+$',  # 只有表情
]

# ============== 内容质量评估 ==============

def assess_content_quality(title, content, likes=0, comments=0):
    """
    内容质量评分 0-1
    维度：内容长度、信息密度、互动量、是否含垃圾特征
    """
    text = f"{title} {content}".strip()
    score = 0.5  # 基础分

    # 1. 内容长度维度
    char_count = len(text)
    if char_count < 10:
        score -= 0.3
    elif char_count < 30:
        score -= 0.1
    elif 50 <= char_count <= 500:
        score += 0.15  # 适中长度加分
    elif char_count > 1000:
        score += 0.05  # 长内容略加分

    # 2. 信息密度（中文占比）
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    chinese_ratio = chinese_chars / max(char_count, 1)
    if chinese_ratio < 0.2:
        score -= 0.2
    elif chinese_ratio > 0.5:
        score += 0.1

    # 3. 互动量维度
    engagement = int(likes or 0) + int(comments or 0) * 2
    if engagement >= 100:
        score += 0.15
    elif engagement >= 20:
        score += 0.08
    elif engagement == 0 and char_count < 50:
        score -= 0.1  # 零互动+短内容降分

    # 4. 垃圾特征降分
    spam_hits = sum(1 for kw in SPAM_KEYWORDS if kw in text)
    if spam_hits >= 2:
        score -= 0.4
    elif spam_hits == 1:
        score -= 0.15

    for pattern in MARKETING_PATTERNS:
        if re.search(pattern, text):
            score -= 0.3
            break

    # 5. 低质量模式
    for pattern in LOW_QUALITY_PATTERNS:
        if re.match(pattern, text):
            score -= 0.3
            break

    return max(0.0, min(1.0, round(score, 3)))


def detect_noise_type(title, content):
    """
    检测噪声类型
    返回: (noise_type, reason)
    noise_type: spam / marketing / duplicate / low_quality / irrelevant / ''
    """
    text = f"{title} {content}".strip()

    # 1. 营销/广告
    for pattern in MARKETING_PATTERNS:
        if re.search(pattern, text):
            return 'marketing', '检测到联系方式/推广链接'

    spam_hits = [kw for kw in SPAM_KEYWORDS if kw in text]
    if len(spam_hits) >= 2:
        return 'spam', f'检测到垃圾营销关键词：{"、".join(spam_hits[:3])}'

    # 2. 低质量内容
    char_count = len(text)
    if char_count < 10:
        return 'low_quality', '内容过短，信息不足'

    for pattern in LOW_QUALITY_PATTERNS:
        if re.match(pattern, text):
            return 'low_quality', '无实质内容'

    # 3. 虽然通过主体过滤但主题偏离
    # （主体过滤只看关键词，AI二次判断看语义）
    taikoo_context_words = ['太古汇', '广州太古汇', '天河太古汇', '石牌桥', '天河路383']
    has_taikoo_direct = any(w in text for w in taikoo_context_words)
    if not has_taikoo_direct and char_count < 100:
        # 只有品牌名没有太古汇上下文，且内容短，可能偏离
        return 'irrelevant', '缺少广州太古汇上下文语境'

    return '', ''


def ai_secondary_review(note):
    """
    AI二次判断：对通过主体过滤的笔记进行深度相关性校验
    返回: {
        'status': 'accepted' | 'rejected' | 'pending',
        'reason': str,
        'noise_type': str,
        'confidence': float,
        'quality_score': float,
        'is_duplicate': bool,
        'duplicate_of': str,
        'ai_insight': str,
        'provider': str
    }
    """
    title = note.get('title', '') or ''
    content = note.get('content', '') or ''
    likes = int(note.get('likes', 0) or 0)
    comments = int(note.get('comments', 0) or 0)

    # 1. 先做规则层快速判断
    quality_score = assess_content_quality(title, content, likes, comments)
    noise_type, noise_reason = detect_noise_type(title, content)

    # 规则层直接拒绝：明确的营销/垃圾内容
    if noise_type in ('spam', 'marketing'):
        return {
            'status': 'rejected',
            'reason': noise_reason,
            'noise_type': noise_type,
            'confidence': 0.9,
            'quality_score': quality_score,
            'is_duplicate': False,
            'duplicate_of': '',
            'ai_insight': '',
            'provider': 'rule'
        }

    # 2. 去重检测（规则层）
    duplicates = db.find_duplicate_notes(note, similarity_threshold=0.75)
    if duplicates:
        return {
            'status': 'rejected',
            'reason': f'与笔记 {duplicates[0]["note_id"]} 内容高度重复（相似度{duplicates[0]["similarity"]}）',
            'noise_type': 'duplicate',
            'confidence': 0.85,
            'quality_score': quality_score,
            'is_duplicate': True,
            'duplicate_of': duplicates[0]['note_id'],
            'ai_insight': '',
            'provider': 'rule'
        }

    # 3. 低质量内容降级（不直接拒绝，标记为低质量）
    if quality_score < 0.25:
        return {
            'status': 'rejected',
            'reason': f'内容质量过低（{quality_score}），{noise_reason or "信息密度不足"}',
            'noise_type': noise_type or 'low_quality',
            'confidence': 0.7,
            'quality_score': quality_score,
            'is_duplicate': False,
            'duplicate_of': '',
            'ai_insight': '',
            'provider': 'rule'
        }

    # 4. AI深度判断（如果AI可用）。测试/离线门禁下不触发任何本地或云端
    # 推理请求：报告生成必须保持有界，规则结果仍然可审计且不改变事实。
    # 生产运行不设置 ZBC_TEST_OFFLINE 时，仍按现有本地优先 AI 路径执行。
    if os.environ.get('ZBC_TEST_OFFLINE', '').strip() != '1' and intelligence.ai_enabled():
        ai_result = _ai_deep_review(note, quality_score)
        if ai_result:
            return ai_result

    # 5. 规则层兜底：通过主体过滤 + 质量合格 = 接受
    return {
        'status': 'accepted',
        'reason': '通过主体过滤与质量校验',
        'noise_type': '',
        'confidence': 0.6,
        'quality_score': quality_score,
        'is_duplicate': False,
        'duplicate_of': '',
        'ai_insight': _generate_rule_insight(note),
        'provider': 'rule'
    }


def _ai_deep_review(note, quality_score):
    """AI深度二次判断（仅在AI可用时调用）。"""
    title = note.get('title', '') or ''
    content = note.get('content', '') or ''

    system = '''你是广州太古汇舆情监测系统的AI二次审核员。
你的任务：对已经通过"广州太古汇"关键词主体过滤的笔记，做深度语义相关性判断。

判断标准：
1. accepted：内容确实在讨论广州太古汇（体验、活动、店铺、服务、事件等）
2. rejected：虽然出现了关键词，但实际主题不是广州太古汇（如：只是提到地名、广告引流、无关讨论、重复搬运）

输出严格JSON：
{"status":"accepted|rejected","reason":"不超过50字","confidence":0-1,"insight":"不超过80字的舆情洞察"}

注意：
- 单一用户的投诉/体验分享，如果确实发生在广州太古汇，应该accepted
- 营销广告、代购引流、无意义内容，应该rejected
- 不要因为内容负面就rejected，负面真实体验也是有效舆情
'''
    user = f'标题：{title}\n正文：{content[:3000]}\n内容质量分：{quality_score}'

    raw, provider, _ = intelligence.chat(system, user, level='low', use_cache=True,
                                        temperature=0.0, max_tokens=500, pack_id='glm_4_5_air')
    data = intelligence._json_from_text(raw)
    if not data:
        return None

    status = data.get('status', 'accepted')
    if status not in ('accepted', 'rejected'):
        status = 'accepted'

    return {
        'status': status,
        'reason': data.get('reason', 'AI二次判断')[:80],
        'noise_type': 'irrelevant' if status == 'rejected' else '',
        'confidence': max(0, min(1, float(data.get('confidence', 0.7)))),
        'quality_score': quality_score,
        'is_duplicate': False,
        'duplicate_of': '',
        'ai_insight': data.get('insight', '')[:120],
        'provider': provider
    }


def _generate_rule_insight(note):
    """规则引擎生成的简短舆情洞察。"""
    title = note.get('title', '') or ''
    content = note.get('content', '') or ''
    sentiment = note.get('sentiment', 'neutral')
    topics = note.get('topics', []) or []

    topic_str = '、'.join([t for t in topics if t and t != '其他'][:2])
    if not topic_str:
        topic_str = '一般讨论'

    sentiment_label = {'positive': '正向体验', 'negative': '负面反馈', 'neutral': '中性信息'}.get(sentiment, '中性信息')
    return f'{sentiment_label}｜{topic_str}｜规则引擎初步归类，建议结合原文核实'


def run_filter_batch(limit=500):
    """
    批量运行AI过滤层
    返回统计结果
    """
    notes = db.get_pending_filter_notes(limit)
    if not notes:
        return {'processed': 0, 'accepted': 0, 'rejected': 0, 'message': '没有待过滤的笔记'}

    stats = {'processed': 0, 'accepted': 0, 'rejected': 0, 'errors': 0}

    for note in notes:
        try:
            result = ai_secondary_review(note)
            db.update_note_ai_filter(
                note_id=note['note_id'],
                filter_result=result['status'],
                reason=result['reason'],
                noise_type=result['noise_type'],
                confidence=result['confidence'],
                provider=result['provider'],
                quality_score=result['quality_score'],
                is_duplicate=1 if result['is_duplicate'] else 0,
                duplicate_of=result['duplicate_of'],
                ai_insight=result['ai_insight']
            )
            stats['processed'] += 1
            if result['status'] == 'accepted':
                stats['accepted'] += 1
            else:
                stats['rejected'] += 1
        except Exception as e:
            stats['errors'] += 1
            print(f'[AIFilter] 处理笔记 {note.get("note_id")} 失败: {e}')

    return stats


def cleanup_rejected_notes(dry_run=True):
    """
    清理被AI过滤层拒绝的笔记（软删除：标记为inactive，不物理删除）
    dry_run=True时只统计不执行
    """
    with db.get_db() as conn:
        count = conn.execute("""SELECT COUNT(*) c FROM notes
            WHERE is_taikoo_verified=1 AND ai_filter_status='rejected' AND status='active'""").fetchone()['c']
        if not dry_run and count > 0:
            conn.execute("""UPDATE notes SET status='filtered_out'
                WHERE is_taikoo_verified=1 AND ai_filter_status='rejected' AND status='active'""")
    return {'count': count, 'dry_run': dry_run, 'action': '标记为filtered_out（软删除）'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='广州太古汇舆情监测系统 - AI过滤层')
    parser.add_argument('--run', action='store_true', help='运行批量过滤')
    parser.add_argument('--limit', type=int, default=500, help='批量处理数量')
    parser.add_argument('--stats', action='store_true', help='查看过滤统计')
    parser.add_argument('--cleanup', action='store_true', help='清理被拒绝的笔记')
    parser.add_argument('--execute', action='store_true', help='实际执行清理（默认dry run）')
    args = parser.parse_args()

    if args.stats:
        print(json.dumps(db.get_filter_stats(), ensure_ascii=False, indent=2))
    elif args.run:
        result = run_filter_batch(args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.cleanup:
        result = cleanup_rejected_notes(dry_run=not args.execute)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
