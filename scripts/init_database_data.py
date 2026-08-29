"""
数据库数据补齐脚本 - 广州太古汇舆情监测系统 v5.8.0
为web_topics, web_events, weekly_events等空表添加示例数据
"""
import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'monitor.db')

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_web_topics():
    """初始化全网话题数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查表是否为空
    cursor.execute("SELECT COUNT(*) FROM web_topics")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"web_topics表已有 {count} 条数据，跳过初始化")
        conn.close()
        return
    
    # 示例话题数据
    topics = [
        {
            'topic': '广州太古汇奢侈品购物体验',
            'platform': 'xiaohongshu',
            'mention_count': 156,
            'sentiment': 'positive',
            'trend': 'up',
            'first_seen': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '奢侈品,购物,体验,太古汇',
        },
        {
            'topic': '太古汇停车场排队问题',
            'platform': 'xiaohongshu',
            'mention_count': 89,
            'sentiment': 'negative',
            'trend': 'up',
            'first_seen': (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '停车场,排队,拥堵,太古汇',
        },
        {
            'topic': '广州太古汇美食推荐',
            'platform': 'xiaohongshu',
            'mention_count': 234,
            'sentiment': 'positive',
            'trend': 'stable',
            'first_seen': (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '美食,推荐,餐厅,太古汇',
        },
        {
            'topic': '太古汇服务态度投诉',
            'platform': 'weibo',
            'mention_count': 45,
            'sentiment': 'negative',
            'trend': 'down',
            'first_seen': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '服务,态度,投诉,太古汇',
        },
        {
            'topic': '广州太古汇圣诞节活动',
            'platform': 'xiaohongshu',
            'mention_count': 312,
            'sentiment': 'positive',
            'trend': 'up',
            'first_seen': (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '圣诞节,活动,装饰,太古汇',
        },
        {
            'topic': '太古汇品牌入驻动态',
            'platform': 'weibo',
            'mention_count': 67,
            'sentiment': 'neutral',
            'trend': 'stable',
            'first_seen': (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '品牌,入驻,新店,太古汇',
        },
        {
            'topic': '广州太古汇探店攻略',
            'platform': 'xiaohongshu',
            'mention_count': 178,
            'sentiment': 'positive',
            'trend': 'stable',
            'first_seen': (datetime.now() - timedelta(days=50)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '探店,攻略,购物,太古汇',
        },
        {
            'topic': '太古汇空调温度问题',
            'platform': 'xiaohongshu',
            'mention_count': 34,
            'sentiment': 'negative',
            'trend': 'down',
            'first_seen': (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': '空调,温度,冷,太古汇',
        },
    ]
    
    # 插入数据
    for topic in topics:
        cursor.execute("""
            INSERT INTO web_topics (topic, platform, mention_count, sentiment, trend, first_seen, last_seen, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            topic['topic'], topic['platform'], topic['mention_count'],
            topic['sentiment'], topic['trend'], topic['first_seen'],
            topic['last_seen'], topic['keywords']
        ))
    
    conn.commit()
    print(f"✅ web_topics表已初始化，添加 {len(topics)} 条数据")
    conn.close()

def init_web_events():
    """初始化全网事件数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查表是否为空
    cursor.execute("SELECT COUNT(*) FROM web_events")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"web_events表已有 {count} 条数据，跳过初始化")
        conn.close()
        return
    
    # 示例事件数据
    events = [
        {
            'title': '太古汇停车场高峰期严重拥堵事件',
            'summary': '周末高峰期太古汇停车场入口排队超过1小时，多位消费者在社交媒体投诉',
            'platform': 'xiaohongshu',
            'risk_level': 'medium',
            'mention_count': 56,
            'first_seen': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'ongoing',
            'keywords': '停车场,拥堵,排队,投诉',
        },
        {
            'title': '某奢侈品品牌专柜服务态度引发争议',
            'summary': '消费者反映某品牌专柜导购服务态度冷漠，引发网络讨论',
            'platform': 'weibo',
            'risk_level': 'high',
            'mention_count': 123,
            'first_seen': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'ongoing',
            'keywords': '服务,态度,奢侈品,争议',
        },
        {
            'title': '太古汇圣诞节装饰亮相获好评',
            'summary': '太古汇2026圣诞节装饰正式亮相，精美设计获得消费者广泛好评',
            'platform': 'xiaohongshu',
            'risk_level': 'low',
            'mention_count': 245,
            'first_seen': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'ongoing',
            'keywords': '圣诞节,装饰,好评,活动',
        },
        {
            'title': '网红餐厅入驻太古汇引发排队热潮',
            'summary': '知名网红餐厅正式入驻太古汇，开业首日排队超过3小时',
            'platform': 'xiaohongshu',
            'risk_level': 'low',
            'mention_count': 89,
            'first_seen': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
            'last_seen': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'resolved',
            'keywords': '网红,餐厅,排队,入驻',
        },
    ]
    
    # 插入数据
    for event in events:
        cursor.execute("""
            INSERT INTO web_events (title, summary, platform, risk_level, mention_count, first_seen, last_seen, status, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event['title'], event['summary'], event['platform'],
            event['risk_level'], event['mention_count'], event['first_seen'],
            event['last_seen'], event['status'], event['keywords']
        ))
    
    conn.commit()
    print(f"✅ web_events表已初始化，添加 {len(events)} 条数据")
    conn.close()

def init_weekly_events():
    """初始化周报事件数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查表是否为空
    cursor.execute("SELECT COUNT(*) FROM weekly_events")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"weekly_events表已有 {count} 条数据，跳过初始化")
        conn.close()
        return
    
    # 计算本周起止日期
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # 示例周报事件数据
    events = [
        {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'title': '停车场拥堵问题持续发酵',
            'category': 'service',
            'urgency': 'high',
            'summary': '本周停车场拥堵相关讨论持续增加，建议优化高峰期车流管理',
            'mention_count': 89,
            'sentiment': 'negative',
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
        {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'title': '圣诞节活动预热效果良好',
            'category': 'marketing',
            'urgency': 'low',
            'summary': '圣诞节装饰和活动预热获得积极反馈，建议持续推进活动宣传',
            'mention_count': 156,
            'sentiment': 'positive',
            'status': 'confirmed',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
        {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'title': '品牌服务质量需关注',
            'category': 'service',
            'urgency': 'medium',
            'summary': '本周收到多起品牌服务质量投诉，建议加强导购培训',
            'mention_count': 34,
            'sentiment': 'negative',
            'status': 'pending',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        },
    ]
    
    # 插入数据
    for event in events:
        cursor.execute("""
            INSERT INTO weekly_events (week_start, week_end, title, category, urgency, summary, mention_count, sentiment, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event['week_start'], event['week_end'], event['title'],
            event['category'], event['urgency'], event['summary'],
            event['mention_count'], event['sentiment'], event['status'],
            event['created_at']
        ))
    
    conn.commit()
    print(f"✅ weekly_events表已初始化，添加 {len(events)} 条数据")
    conn.close()

def init_notification_logs():
    """初始化通知日志数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查表是否为空
    cursor.execute("SELECT COUNT(*) FROM notification_logs")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"notification_logs表已有 {count} 条数据，跳过初始化")
        conn.close()
        return
    
    # 示例通知日志
    logs = [
        {
            'type': 'daily_report',
            'title': '每日舆情报告已生成',
            'content': f'{datetime.now().strftime("%Y-%m-%d")} 舆情报告已生成，共收录156条笔记',
            'status': 'sent',
            'channel': 'system',
            'created_at': datetime.now().strftime('%Y-%m-%d 09:00:00'),
        },
        {
            'type': 'high_risk_alert',
            'title': '高风险舆情预警',
            'content': '检测到高风险舆情：某品牌服务态度争议，建议及时处理',
            'status': 'sent',
            'channel': 'system',
            'created_at': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
        },
        {
            'type': 'collection_complete',
            'title': '采集任务完成',
            'content': '自动采集任务完成，新增23条笔记',
            'status': 'sent',
            'channel': 'system',
            'created_at': (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S'),
        },
    ]
    
    # 插入数据
    for log in logs:
        cursor.execute("""
            INSERT INTO notification_logs (type, title, content, status, channel, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            log['type'], log['title'], log['content'],
            log['status'], log['channel'], log['created_at']
        ))
    
    conn.commit()
    print(f"✅ notification_logs表已初始化，添加 {len(logs)} 条数据")
    conn.close()

def init_brand_industry_monitor():
    """初始化品牌业态监测数据"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查表是否为空
    cursor.execute("SELECT COUNT(*) FROM brand_industry_monitor")
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"brand_industry_monitor表已有 {count} 条数据，跳过初始化")
        conn.close()
        return
    
    # 示例品牌数据
    brands = [
        {'name': 'Louis Vuitton', 'category': '奢侈品', 'floor': 'L1', 'total_notes': 45, 'positive': 38, 'negative': 4, 'neutral': 3},
        {'name': 'Gucci', 'category': '奢侈品', 'floor': 'L1', 'total_notes': 38, 'positive': 30, 'negative': 5, 'neutral': 3},
        {'name': 'Apple', 'category': '数码', 'floor': 'L2', 'total_notes': 67, 'positive': 55, 'negative': 8, 'neutral': 4},
        {'name': '星巴克', 'category': '餐饮', 'floor': 'L1', 'total_notes': 89, 'positive': 72, 'negative': 10, 'neutral': 7},
        {'name': '喜茶', 'category': '餐饮', 'floor': 'L2', 'total_notes': 56, 'positive': 45, 'negative': 6, 'neutral': 5},
        {'name': '优衣库', 'category': '服饰', 'floor': 'L3', 'total_notes': 34, 'positive': 28, 'negative': 3, 'neutral': 3},
        {'name': 'MUJI', 'category': '生活方式', 'floor': 'L2', 'total_notes': 28, 'positive': 24, 'negative': 2, 'neutral': 2},
        {'name': 'Nike', 'category': '运动', 'floor': 'L3', 'total_notes': 42, 'positive': 35, 'negative': 4, 'neutral': 3},
    ]
    
    # 插入数据
    for brand in brands:
        cursor.execute("""
            INSERT INTO brand_industry_monitor (brand_name, category, floor, total_notes, positive_count, negative_count, neutral_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            brand['name'], brand['category'], brand['floor'],
            brand['total_notes'], brand['positive'], brand['negative'],
            brand['neutral'], datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
    
    conn.commit()
    print(f"✅ brand_industry_monitor表已初始化，添加 {len(brands)} 条数据")
    conn.close()

def main():
    """主函数"""
    print("=" * 60)
    print("数据库数据补齐脚本 - 广州太古汇舆情监测系统 v5.8.0")
    print("=" * 60)
    print()
    
    # 检查数据库文件
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    print(f"数据库路径: {DB_PATH}")
    print()
    
    # 初始化各表
    init_web_topics()
    init_web_events()
    init_weekly_events()
    init_notification_logs()
    init_brand_industry_monitor()
    
    print()
    print("=" * 60)
    print("✅ 数据库数据补齐完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
