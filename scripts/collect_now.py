"""
立即采集脚本
触发一次小红书舆情采集
版本: v5.8.0
"""

import sys
import os
import json
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def collect_now(keyword='广州太古汇', max_scroll=5, max_details=20):
    """立即执行采集"""
    print("=" * 60)
    print("广州太古汇舆情监测系统 - 立即采集")
    print(f"采集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"关键词: {keyword}")
    print("=" * 60)
    print()

    # 检查采集次数
    try:
        import sqlite3
        db_path = os.path.join(PROJECT_ROOT, 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT daily_count, manual_count, auto_count FROM collection_counters WHERE date = ?", (today,))
        row = cursor.fetchone()

        if row:
            daily_count, manual_count, auto_count = row
            print(f"今日采集次数: 总{daily_count}/手动{manual_count}/自动{auto_count}")

            if manual_count >= 3:
                print("⚠️ 今日手动采集次数已用完（3次），请等待明天或使用自动采集")
                conn.close()
                return False
        else:
            print("今日首次采集")

        conn.close()
    except Exception as e:
        print(f"⚠️ 检查采集次数失败: {e}")

    print()
    print("开始采集...")
    print()

    # 尝试使用collector_v2
    try:
        from collector_v2.xhs.live_engine import XHSLiveEngine
        engine = XHSLiveEngine()
        result = engine.collect(
            keyword=keyword,
            max_scroll=max_scroll,
            max_details=max_details
        )
        print(f"采集完成: {result}")
        return True
    except ImportError:
        print("⚠️ collector_v2不可用，尝试使用collector.py")
    except Exception as e:
        print(f"⚠️ collector_v2采集失败: {e}")

    # 尝试使用collector.py
    try:
        from collector import collect_all
        result = collect_all(keyword=keyword)
        print(f"采集完成: {result}")
        return True
    except ImportError:
        print("❌ collector.py不可用")
    except Exception as e:
        print(f"❌ 采集失败: {e}")

    print()
    print("⚠️ 采集模块不可用，请检查系统配置")
    return False


if __name__ == '__main__':
    keyword = sys.argv[1] if len(sys.argv) > 1 else '广州太古汇'
    max_scroll = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    max_details = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    success = collect_now(keyword, max_scroll, max_details)
    sys.exit(0 if success else 1)
