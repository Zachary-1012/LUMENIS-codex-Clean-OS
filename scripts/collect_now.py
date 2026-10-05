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

    # Read collection limits through the Shared Database owner. If policy state
    # cannot be read, fail closed instead of bypassing the manual quota.
    try:
        import database as db

        today = datetime.now().strftime('%Y-%m-%d')
        with db.get_db() as conn:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='collection_counters'"
            ).fetchone()
            if not table:
                print("❌ 采集限额状态不可用，已阻止请求")
                return False
            row = conn.execute(
                "SELECT daily_count, manual_count, auto_count FROM collection_counters WHERE date = ?",
                (today,),
            ).fetchone()

        if row:
            daily_count, manual_count, auto_count = row
            print(f"今日采集次数: 总{daily_count}/手动{manual_count}/自动{auto_count}")

            if manual_count >= 3:
                print("⚠️ 今日手动采集次数已用完（3次），请等待明天或使用自动采集")
                return False
        else:
            print("今日首次采集")
    except Exception as e:
        print(f"❌ 采集限额状态不可用，已阻止请求: {type(e).__name__}")
        return False

    print()
    print("开始采集...")
    print()

    # 通过 SYSTEM Collector 的当前 XHS runtime 采集并按现行 Subject 规则入库。
    try:
        from lumenis.system.collector.runtime.xhs.live_engine import run_live, persist_live
        from subject_rules import subject_hit_text

        result = run_live(
            keyword,
            max_scroll=max_scroll,
            max_details=max_details,
        )
        stats = persist_live(result, subject_hit_text)
        print(f"采集结果: {result}")
        print(f"入库结果: {stats}")
        return bool(stats.get("ok"))
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
