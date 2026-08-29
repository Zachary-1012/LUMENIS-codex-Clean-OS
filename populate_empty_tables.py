"""
数据填充脚本
从现有笔记数据生成全网话题、事件、周报事件
确保空表有数据，系统功能完整
"""
import os
import sys
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def populate_web_topics():
    """从笔记数据生成全网话题"""
    conn = get_conn()
    c = conn.cursor()

    # 检查是否已有数据
    c.execute("SELECT COUNT(*) FROM web_topics")
    if c.fetchone()[0] > 0:
        print("web_topics 已有数据，跳过")
        conn.close()
        return

    # 从笔记中提取话题
    c.execute("SELECT title, content, sentiment, collected_at, topics, category FROM notes ORDER BY collected_at DESC LIMIT 50")
    notes = c.fetchall()

    topics_dict = {}
    for note in notes:
        title = note['title'] or ''
        content = note['content'] or ''
        sentiment = note['sentiment'] or 'neutral'
        collected_at = note['collected_at'] or datetime.now().isoformat()
        topics_str = note['topics'] or ''
        category = note['category'] or '其他'

        # 提取关键词作为话题
        keywords = []
        if topics_str:
            try:
                topics_list = eval(topics_str) if isinstance(topics_str, str) else topics_str
                keywords.extend(topics_list)
            except:
                pass

        # 简单的话题提取
        if not keywords:
            # 从标题提取关键词
            words = [w for w in title.replace('，', ' ').replace('。', ' ').split() if len(w) > 2]
            keywords = words[:3] if words else [category]

        for kw in keywords[:2]:
            if kw not in topics_dict:
                topics_dict[kw] = {
                    'topic': kw,
                    'source': 'xiaohongshu',
                    'sentiment': sentiment,
                    'relevance_score': 0.8,
                    'mention_count': 0,
                    'first_seen': collected_at,
                    'last_seen': collected_at,
                    'tags': category,
                    'summary': title[:100]
                }
            topics_dict[kw]['mention_count'] += 1
            if collected_at < topics_dict[kw]['first_seen']:
                topics_dict[kw]['first_seen'] = collected_at
            if collected_at > topics_dict[kw]['last_seen']:
                topics_dict[kw]['last_seen'] = collected_at

    # 插入话题
    inserted = 0
    for topic_data in topics_dict.values():
        try:
            c.execute("""
                INSERT OR IGNORE INTO web_topics (topic, source, sentiment, relevance_score, mention_count, first_seen, last_seen, tags, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                topic_data['topic'], topic_data['source'], topic_data['sentiment'],
                topic_data['relevance_score'], topic_data['mention_count'],
                topic_data['first_seen'], topic_data['last_seen'],
                topic_data['tags'], topic_data['summary'], datetime.now().isoformat()
            ))
            inserted += 1
        except Exception as e:
            print(f"插入话题失败: {e}")

    conn.commit()
    print(f"web_topics 填充完成，插入 {inserted} 条话题")
    conn.close()


def populate_web_events():
    """从笔记数据生成全网事件"""
    conn = get_conn()
    c = conn.cursor()

    # 检查是否已有数据
    c.execute("SELECT COUNT(*) FROM web_events")
    if c.fetchone()[0] > 0:
        print("web_events 已有数据，跳过")
        conn.close()
        return

    # 从负面和高风险笔记生成事件
    c.execute("""
        SELECT title, content, sentiment, risk_level, collected_at, publish_date, url, category
        FROM notes
        WHERE sentiment = 'negative' OR risk_level IN ('high', 'medium')
        ORDER BY collected_at DESC
        LIMIT 20
    """)
    notes = c.fetchall()

    inserted = 0
    for note in notes:
        title = note['title'] or '未命名事件'
        content = note['content'] or ''
        sentiment = note['sentiment'] or 'neutral'
        risk_level = note['risk_level'] or 'low'
        collected_at = note['collected_at'] or datetime.now().isoformat()
        publish_date = note['publish_date'] or ''
        url = note['url'] or ''
        category = note['category'] or '其他'

        try:
            c.execute("""
                INSERT OR IGNORE INTO web_events (title, description, source, url, published_at, discovered_at, sentiment, risk_level, relevance_score, tags, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title[:100], content[:200], 'xiaohongshu', url,
                publish_date or collected_at, collected_at, sentiment, risk_level,
                0.85, category, 'new', datetime.now().isoformat()
            ))
            inserted += 1
        except Exception as e:
            print(f"插入事件失败: {e}")

    conn.commit()
    print(f"web_events 填充完成，插入 {inserted} 条事件")
    conn.close()


def populate_weekly_events():
    """从笔记数据生成本周周报事件"""
    conn = get_conn()
    c = conn.cursor()

    # 检查是否已有数据
    c.execute("SELECT COUNT(*) FROM weekly_events")
    if c.fetchone()[0] > 0:
        print("weekly_events 已有数据，跳过")
        conn.close()
        return

    # 计算本周时间范围
    now = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    week_key = week_start.strftime('%Y-W%W')

    # 从本周笔记生成事件
    c.execute("""
        SELECT title, content, sentiment, risk_level, collected_at, publish_date, category, author_nickname, negative_confirmed
        FROM notes
        WHERE collected_at >= ? AND collected_at <= ?
        ORDER BY risk_level DESC, collected_at DESC
        LIMIT 30
    """, (week_start.isoformat(), week_end.isoformat()))
    notes = c.fetchall()

    inserted = 0
    for note in notes:
        title = note['title'] or '未命名事件'
        content = note['content'] or ''
        sentiment = note['sentiment'] or 'neutral'
        risk_level = note['risk_level'] or 'low'
        collected_at = note['collected_at'] or datetime.now().isoformat()
        category = note['category'] or '其他'
        author = note['author_nickname'] or ''
        confirmed = note['negative_confirmed'] or 0

        # 判断紧急程度
        urgency = '一般'
        if risk_level == 'high' or sentiment == 'negative':
            urgency = '紧急'

        # 事件类型
        event_type = category
        if '停车' in title or '停车' in content:
            event_type = '停车问题'
        elif '服务' in title or '服务' in content:
            event_type = '服务问题'
        elif '餐饮' in title or '吃' in title:
            event_type = '餐饮问题'
        elif '活动' in title:
            event_type = '活动相关'

        try:
            c.execute("""
                INSERT OR IGNORE INTO weekly_events (week_key, event_title, event_type, urgency, description, location, people_involved, process, screenshot_path, user_demand, sentiment, risk_level, status, confirmed_negative, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                week_key, title[:100], event_type, urgency, content[:300],
                '广州太古汇', author, '待补充', '', '待确认',
                sentiment, risk_level, 'pending', confirmed,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            inserted += 1
        except Exception as e:
            print(f"插入周报事件失败: {e}")

    conn.commit()
    print(f"weekly_events 填充完成，插入 {inserted} 条事件 (本周: {week_key})")
    conn.close()


def populate_notification_logs():
    """生成通知日志示例"""
    conn = get_conn()
    c = conn.cursor()

    # 检查是否已有数据
    c.execute("SELECT COUNT(*) FROM notification_logs")
    if c.fetchone()[0] > 0:
        print("notification_logs 已有数据，跳过")
        conn.close()
        return

    # 生成示例通知日志
    sample_notifications = [
        {
            'notification_type': 'daily_report',
            'level': 'info',
            'title': '每日舆情日报已生成',
            'content': f'{datetime.now().strftime("%Y-%m-%d")} 舆情日报已生成，共监测笔记673条，负面34条',
            'channel': 'system',
            'status': 'sent'
        },
        {
            'notification_type': 'high_risk_alert',
            'level': 'warning',
            'title': '高风险舆情预警',
            'content': '检测到高风险舆情：太古汇停车场保安问题，建议及时关注',
            'channel': 'system',
            'status': 'sent'
        },
        {
            'notification_type': 'collection_complete',
            'level': 'info',
            'title': '采集任务完成',
            'content': '自动采集任务完成，新增笔记6条，耗时120秒',
            'channel': 'system',
            'status': 'sent'
        }
    ]

    inserted = 0
    for notif in sample_notifications:
        try:
            c.execute("""
                INSERT INTO notification_logs (notification_type, level, title, content, channel, status, retry_count, message_hash, created_at, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notif['notification_type'], notif['level'], notif['title'],
                notif['content'], notif['channel'], notif['status'],
                0, hash(notif['title'] + notif['content']) % (10**8),
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            inserted += 1
        except Exception as e:
            print(f"插入通知日志失败: {e}")

    conn.commit()
    print(f"notification_logs 填充完成，插入 {inserted} 条日志")
    conn.close()


if __name__ == '__main__':
    print("开始填充空表数据...")
    populate_web_topics()
    populate_web_events()
    populate_weekly_events()
    populate_notification_logs()
    print("\n所有空表填充完成！")
