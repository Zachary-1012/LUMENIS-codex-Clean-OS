"""
完整采集测试脚本 - 给足时间完成，不再中途终止
测试阶段不限制次数，只保证安全
"""
import sys
import os
import time
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xhs_cookie_bridge as bridge

print("=" * 60)
print("  广州太古汇舆情监测系统 - 完整采集测试")
print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print()

# 测试配置
test_keywords = ["广州太古汇", "太古汇 投诉"]
max_scroll = 3  # 测试阶段用3次滚动，保证有结果

print(f"测试关键词: {test_keywords}")
print(f"最大滚动次数: {max_scroll}")
print(f"Node进程超时: {bridge.NODE_PROCESS_TIMEOUT}秒 ({bridge.NODE_PROCESS_TIMEOUT/60:.1f}分钟)")
print()

# 采集前数据库统计
print("=== 采集前数据库统计 ===")
import sqlite3
conn = sqlite3.connect('data/monitor.db')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM notes")
before_count = c.fetchone()[0]
print(f"  笔记总数: {before_count}")
c.execute("SELECT MAX(collected_at) FROM notes")
print(f"  最新采集: {c.fetchone()[0]}")
conn.close()
print()

# 开始采集
print("=== 开始采集（给足时间完成，不再中途终止） ===")
start_time = time.time()

try:
    result = bridge.sync(keywords=test_keywords, max_scroll=max_scroll)
    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print("  采集完成！")
    print(f"  耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
    print("=" * 60)
    print()

    # 采集结果
    print("=== 采集结果 ===")
    print(f"  原始唯一笔记: {result.get('raw_unique', 0)}")
    print(f"  主体验证通过: {result.get('verified', 0)}")
    print(f"  主体验证拒绝: {result.get('rejected', 0)}")
    print(f"  新增笔记: {result.get('inserted', 0)}")
    print(f"  更新笔记: {result.get('updated', 0)}")
    print(f"  待AI分析: {result.get('analyzed', 0)}")
    print()

    # 各关键词结果
    print("=== 各关键词采集详情 ===")
    for r in result.get('results', []):
        if 'keyword' in r:
            print(f"  关键词: {r.get('keyword')}")
            print(f"    获取: {r.get('fetched', 0)}条")
            if r.get('error'):
                print(f"    错误: {str(r.get('error'))[:200]}")
            print()

    # 采集后数据库统计
    print("=== 采集后数据库统计 ===")
    conn = sqlite3.connect('data/monitor.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM notes")
    after_count = c.fetchone()[0]
    print(f"  笔记总数: {after_count}")
    print(f"  新增: {after_count - before_count}条")
    c.execute("SELECT MAX(collected_at) FROM notes")
    print(f"  最新采集: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM notes WHERE date(collected_at)=date('now','localtime')")
    print(f"  今日采集: {c.fetchone()[0]}条")
    conn.close()
    print()

    # 最新5条笔记
    print("=== 最新5条笔记 ===")
    conn = sqlite3.connect('data/monitor.db')
    c = conn.cursor()
    c.execute("SELECT note_id, title, collected_at, sentiment FROM notes ORDER BY collected_at DESC LIMIT 5")
    rows = c.fetchall()
    for r in rows:
        print(f"  [{r[2]}] {r[3]} | {str(r[1])[:50]}")
    conn.close()

except Exception as e:
    elapsed = time.time() - start_time
    print()
    print("=" * 60)
    print("  采集失败！")
    print(f"  耗时: {elapsed:.1f}秒")
    print(f"  错误: {e}")
    import traceback
    traceback.print_exc()
    print("=" * 60)

print()
print(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
