"""
系统检查脚本
检查系统运行状态、数据库、配置等
版本: v5.8.0
"""

import sqlite3
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'monitor.db')


def check_system():
    """检查系统状态"""
    print("=" * 60)
    print("广州太古汇舆情监测系统 - 系统检查")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 1. 检查项目文件
    print("【1. 项目文件检查】")
    required_files = [
        'app.py', 'database.py', 'models.py', 'collector.py',
        'ai_analyzer.py', 'intelligence.py', 'risk_engine.py',
        'report_engine.py', 'daily_report.py', 'requirements.txt',
        '.env.example', 'test_system.py', 'README.md'
    ]

    for file in required_files:
        path = os.path.join(PROJECT_ROOT, file)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✅ {file} ({size/1024:.1f} KB)")
        else:
            print(f"  ❌ {file} (不存在)")

    print()

    # 2. 检查目录
    print("【2. 目录检查】")
    required_dirs = ['static', 'templates', 'deployment', 'collector_v2', 'scripts', 'data']
    for dir_name in required_dirs:
        path = os.path.join(PROJECT_ROOT, dir_name)
        if os.path.exists(path):
            file_count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
            print(f"  ✅ {dir_name}/ ({file_count}个文件)")
        else:
            print(f"  ❌ {dir_name}/ (不存在)")

    print()

    # 3. 检查数据库
    print("【3. 数据库检查】")
    if os.path.exists(DB_PATH):
        db_size = os.path.getsize(DB_PATH)
        print(f"  ✅ 数据库文件存在 ({db_size/1024/1024:.2f} MB)")

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # 检查表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [r[0] for r in cursor.fetchall()]
            print(f"  ✅ 数据表数量: {len(tables)}")

            # 检查关键表
            key_tables = ['notes', 'events', 'comments', 'daily_reports', 'collection_counters', 'system_config']
            for table in key_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"     - {table}: {count}条记录")
                else:
                    print(f"     - {table}: ❌ 不存在")

            # 检查notes表字段
            cursor.execute("PRAGMA table_info(notes)")
            note_cols = [r[1] for r in cursor.fetchall()]
            v580_fields = ['negative_confirmed', 'publish_datetime', 'captured_at',
                           'data_quality_status', 'data_quality_score']
            missing_fields = [f for f in v580_fields if f not in note_cols]
            if missing_fields:
                print(f"  ⚠️  notes表缺少v5.8.0字段: {', '.join(missing_fields)}")
            else:
                print(f"  ✅ notes表包含所有v5.8.0字段")

            conn.close()
        except Exception as e:
            print(f"  ❌ 数据库读取失败: {e}")
    else:
        print(f"  ❌ 数据库文件不存在: {DB_PATH}")

    print()

    # 4. 检查v5.8.0新增文件
    print("【4. v5.8.0新增功能检查】")
    v580_files = [
        'static/js/zachary_robot.js',
        'static/js/ui_interactions_v5.8.0.js',
        'weekly_events.py',
        'browser_discovery.py',
        'network_adaptive.py',
        'ai_gateway_v570.py',
    ]

    for file in v580_files:
        path = os.path.join(PROJECT_ROOT, file)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✅ {file} ({size/1024:.1f} KB)")
        else:
            print(f"  ⚠️  {file} (不存在)")

    print()

    # 5. 检查配置文件
    print("【5. 配置文件检查】")
    config_files = [
        'events_config.json', 'brand_directory.json', 'brand_websites.json',
        'case_library.json', 'function_map.json', 'system_config.json'
    ]

    for file in config_files:
        path = os.path.join(PROJECT_ROOT, file)
        if os.path.exists(path):
            print(f"  ✅ {file}")
        else:
            print(f"  ⚠️  {file} (不存在)")

    print()

    # 6. 检查.env
    print("【6. 环境配置检查】")
    env_path = os.path.join(PROJECT_ROOT, '.env')
    env_example_path = os.path.join(PROJECT_ROOT, '.env.example')

    if os.path.exists(env_path):
        print(f"  ✅ .env 文件存在")
    else:
        print(f"  ⚠️  .env 文件不存在（请从.env.example复制并配置）")

    if os.path.exists(env_example_path):
        print(f"  ✅ .env.example 模板存在")
    else:
        print(f"  ❌ .env.example 模板不存在")

    print()
    print("=" * 60)
    print("系统检查完成")
    print("=" * 60)


if __name__ == '__main__':
    check_system()
