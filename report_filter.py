"""
报告筛选逻辑模块
优化内容：
1. 日报：只包含当日或前一日发布的笔记（按publish_date筛选）
2. 周报/月报/年报：负面笔记必须是二次确认的（negative_confirmed=1）
3. 过期笔记：标记为历史案例，不进入日报，但可在笔记库查看
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple


def get_report_period(report_type: str, now: datetime = None) -> Tuple[str, str]:
    """
    获取报告时间范围（按自然周期）
    Args:
        report_type: daily/weekly/monthly/yearly
        now: 当前时间
    Returns:
        (start_date, end_date) 格式: YYYY-MM-DD
    """
    now = now or datetime.now()
    
    if report_type == 'daily':
        # 日报：当日
        start = now.strftime('%Y-%m-%d')
        end = now.strftime('%Y-%m-%d')
    elif report_type == 'weekly':
        # 周报：自然周（周一到周日）
        weekday = now.weekday()  # 0=周一
        monday = now - timedelta(days=weekday)
        sunday = monday + timedelta(days=6)
        start = monday.strftime('%Y-%m-%d')
        end = sunday.strftime('%Y-%m-%d')
    elif report_type == 'monthly':
        # 月报：自然月（1号到月末）
        start = now.replace(day=1).strftime('%Y-%m-%d')
        if now.month == 12:
            next_month = now.replace(year=now.year+1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month+1, day=1)
        end = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')
    elif report_type == 'yearly':
        # 年报：自然年（1月1日到12月31日）
        start = now.replace(month=1, day=1).strftime('%Y-%m-%d')
        end = now.replace(month=12, day=31).strftime('%Y-%m-%d')
    else:
        start = now.strftime('%Y-%m-%d')
        end = now.strftime('%Y-%m-%d')
    
    return start, end


def filter_notes_for_daily_report(notes: List[Dict], include_yesterday: bool = True) -> List[Dict]:
    """
    筛选日报笔记：只包含当日或前一日发布的笔记
    Args:
        notes: 笔记列表
        include_yesterday: 是否包含前一日发布的笔记
    Returns:
        筛选后的笔记列表
    """
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    filtered = []
    for note in notes:
        publish_date = note.get('publish_date', '')
        if not publish_date:
            # 没有发布日期的笔记，按采集日期判断
            publish_date = (note.get('collected_at') or '')[:10]
        
        if publish_date == today:
            filtered.append(note)
        elif include_yesterday and publish_date == yesterday:
            filtered.append(note)
    
    return filtered


def filter_negative_for_period_report(notes: List[Dict], require_confirmed: bool = True) -> Tuple[List[Dict], List[Dict]]:
    """
    筛选周期报告（周报/月报/年报）的负面笔记
    Args:
        notes: 笔记列表
        require_confirmed: 是否要求负面笔记必须二次确认
    Returns:
        (all_notes, confirmed_negative_notes)
        - all_notes: 所有笔记（用于统计总提及量等）
        - confirmed_negative_notes: 二次确认的负面笔记（用于负面分析）
    """
    confirmed_negative = []
    
    for note in notes:
        sentiment = note.get('sentiment', '')
        negative_confirmed = note.get('negative_confirmed')
        
        if sentiment == 'negative':
            if require_confirmed:
                # 只包含二次确认的负面笔记
                if negative_confirmed == 1:
                    confirmed_negative.append(note)
            else:
                confirmed_negative.append(note)
    
    return notes, confirmed_negative


def classify_notes_by_age(notes: List[Dict]) -> Dict[str, List[Dict]]:
    """
    按发布时间分类笔记
    Args:
        notes: 笔记列表
    Returns:
        {
            'recent': 近2天发布的笔记,
            'weekly': 近7天发布的笔记,
            'monthly': 近30天发布的笔记,
            'historical': 30天前发布的历史案例笔记
        }
    """
    now = datetime.now()
    recent = []
    weekly = []
    monthly = []
    historical = []
    
    for note in notes:
        publish_date = note.get('publish_date', '')
        if not publish_date:
            publish_date = (note.get('collected_at') or '')[:10]
        
        try:
            pub_date = datetime.strptime(publish_date[:10], '%Y-%m-%d')
            days_ago = (now - pub_date).days
        except (ValueError, TypeError):
            days_ago = 999  # 无法解析日期的归为历史
        
        if days_ago <= 1:
            recent.append(note)
        elif days_ago <= 7:
            weekly.append(note)
        elif days_ago <= 30:
            monthly.append(note)
        else:
            historical.append(note)
    
    return {
        'recent': recent,
        'weekly': weekly,
        'monthly': monthly,
        'historical': historical
    }


def is_historical_note(note: Dict, threshold_days: int = 7) -> bool:
    """
    判断笔记是否为历史案例笔记（发布时间早于阈值）
    Args:
        note: 笔记数据
        threshold_days: 阈值天数（默认7天）
    Returns:
        True表示历史案例笔记
    """
    publish_date = note.get('publish_date', '')
    if not publish_date:
        publish_date = (note.get('collected_at') or '')[:10]
    
    try:
        pub_date = datetime.strptime(publish_date[:10], '%Y-%m-%d')
        days_ago = (datetime.now() - pub_date).days
        return days_ago > threshold_days
    except (ValueError, TypeError):
        return True  # 无法解析日期的归为历史


def get_daily_report_filter_stats(notes: List[Dict]) -> Dict:
    """
    获取日报筛选统计
    Args:
        notes: 所有采集到的笔记
    Returns:
        统计信息
    """
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    total = len(notes)
    today_published = sum(1 for n in notes if (n.get('publish_date') or '')[:10] == today)
    yesterday_published = sum(1 for n in notes if (n.get('publish_date') or '')[:10] == yesterday)
    historical = sum(1 for n in notes if is_historical_note(n, threshold_days=7))
    
    return {
        'total_collected': total,
        'today_published': today_published,
        'yesterday_published': yesterday_published,
        'historical_notes': historical,
        'daily_report_included': today_published + yesterday_published,
        'daily_report_excluded': total - today_published - yesterday_published
    }


if __name__ == '__main__':
    # 测试
    print("=== 报告筛选逻辑测试 ===")
    print(f"日报周期: {get_report_period('daily')}")
    print(f"周报周期: {get_report_period('weekly')}")
    print(f"月报周期: {get_report_period('monthly')}")
    print(f"年报周期: {get_report_period('yearly')}")
