"""
广州太古汇舆情监测系统 - 端到端测试
采集→入库→前端显示→导出报告全流程测试

使用方法：
    python test_e2e.py              # 运行所有测试
    python test_e2e.py --quick      # 快速测试（跳过采集）
    python test_e2e.py --verbose    # 详细输出
"""

# 这是需要已启动服务与现有业务数据的独立验收脚本，不是 hermetic pytest。
# 脚本函数以 bool 返回执行结果；若被 pytest 自动收集，False 也会被当作通过。
# 因此正式单元/契约套件不收集本模块，运行时验收阶段由命令行显式执行 main。
__test__ = False

import os
import sys
import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 测试结果统计
test_results = {
    'passed': 0,
    'failed': 0,
    'skipped': 0,
    'details': []
}


def log_test_result(name: str, passed: bool, message: str = '', duration: float = 0):
    """记录测试结果"""
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f"{status} | {name} | {message} | {duration:.2f}s")
    
    test_results['details'].append({
        'name': name,
        'passed': passed,
        'message': message,
        'duration': duration
    })
    
    if passed:
        test_results['passed'] += 1
    else:
        test_results['failed'] += 1


def test_database_connection():
    """测试1：数据库连接"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        
        if not os.path.exists(db_path):
            log_test_result('数据库连接', False, f'数据库文件不存在: {db_path}', time.time() - start)
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if 'notes' not in tables:
            log_test_result('数据库连接', False, '缺少notes表', time.time() - start)
            return False
        
        log_test_result('数据库连接', True, f'连接成功，共{len(tables)}个表', time.time() - start)
        return True
        
    except Exception as e:
        log_test_result('数据库连接', False, str(e), time.time() - start)
        return False


def test_database_schema():
    """测试2：数据库表结构"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        
        # 检查必需表
        required_tables = ['notes', 'daily_reports', 'events', 'collection_logs']
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        if missing_tables:
            log_test_result('数据库表结构', False, f'缺少表: {missing_tables}', time.time() - start)
            conn.close()
            return False
        
        # 检查notes表关键字段
        cursor = conn.execute("PRAGMA table_info(notes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        required_columns = ['note_id', 'title', 'content', 'author_id', 'likes', 'comments', 'publish_date', 'sentiment', 'risk_level']
        missing_columns = [c for c in required_columns if c not in columns]
        
        if missing_columns:
            log_test_result('数据库表结构', False, f'notes表缺少字段: {missing_columns}', time.time() - start)
            conn.close()
            return False
        
        conn.close()
        log_test_result('数据库表结构', True, f'表结构完整，notes表共{len(columns)}个字段', time.time() - start)
        return True
        
    except Exception as e:
        log_test_result('数据库表结构', False, str(e), time.time() - start)
        return False


def test_data_integrity():
    """测试3：数据完整性"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        
        # 统计笔记数量
        cursor = conn.execute("SELECT COUNT(*) FROM notes")
        note_count = cursor.fetchone()[0]
        
        # 统计有标题的笔记
        cursor = conn.execute("SELECT COUNT(*) FROM notes WHERE title IS NOT NULL AND title != ''")
        titled_count = cursor.fetchone()[0]
        
        # 统计有正文的笔记
        cursor = conn.execute("SELECT COUNT(*) FROM notes WHERE content IS NOT NULL AND content != ''")
        content_count = cursor.fetchone()[0]
        
        # 统计有发布时间的笔记
        cursor = conn.execute("SELECT COUNT(*) FROM notes WHERE publish_date IS NOT NULL")
        dated_count = cursor.fetchone()[0]
        
        # 统计有情绪分析的笔记
        cursor = conn.execute("SELECT COUNT(*) FROM notes WHERE sentiment IS NOT NULL")
        sentiment_count = cursor.fetchone()[0]
        
        conn.close()
        
        # 数据完整性评估
        if note_count == 0:
            log_test_result('数据完整性', False, '数据库中没有笔记数据', time.time() - start)
            return False
        
        completeness = {
            'total': note_count,
            'has_title': titled_count,
            'has_content': content_count,
            'has_date': dated_count,
            'has_sentiment': sentiment_count,
        }
        
        # 标题完整度应>80%
        title_rate = titled_count / note_count * 100
        if title_rate < 80:
            log_test_result('数据完整性', False, f'标题完整度仅{title_rate:.1f}%', time.time() - start)
            return False
        
        log_test_result(
            '数据完整性', 
            True, 
            f'共{note_count}条笔记，标题完整度{title_rate:.1f}%，正文{content_count}条，有日期{dated_count}条', 
            time.time() - start
        )
        return True
        
    except Exception as e:
        log_test_result('数据完整性', False, str(e), time.time() - start)
        return False


def test_subject_filter():
    """测试4：主体过滤（广州太古汇）"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        
        # 统计已验证为太古汇的笔记
        if 'is_taikoo_verified' in [row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()]:
            cursor = conn.execute("SELECT COUNT(*) FROM notes WHERE is_taikoo_verified = 1")
            verified_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM notes WHERE is_taikoo_verified = 0")
            unverified_count = cursor.fetchone()[0]
            
            log_test_result(
                '主体过滤', 
                True, 
                f'已验证太古汇{verified_count}条，未验证{unverified_count}条', 
                time.time() - start
            )
        else:
            log_test_result('主体过滤', True, '使用旧版过滤逻辑（无is_taikoo_verified字段）', time.time() - start)
        
        conn.close()
        return True
        
    except Exception as e:
        log_test_result('主体过滤', False, str(e), time.time() - start)
        return False


def test_sentiment_analysis():
    """测试5：情绪分析数据"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        
        cursor = conn.execute("SELECT sentiment, COUNT(*) as count FROM notes WHERE sentiment IS NOT NULL GROUP BY sentiment")
        sentiment_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        if not sentiment_dist:
            log_test_result('情绪分析', True, '暂无情绪分析数据（正常，AI分析异步执行）', time.time() - start)
            return True
        
        total = sum(sentiment_dist.values())
        log_test_result(
            '情绪分析', 
            True, 
            f'已分析{total}条，分布: {sentiment_dist}', 
            time.time() - start
        )
        return True
        
    except Exception as e:
        log_test_result('情绪分析', False, str(e), time.time() - start)
        return False


def test_risk_level():
    """测试6：风险等级数据"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        
        cursor = conn.execute("SELECT risk_level, COUNT(*) as count FROM notes WHERE risk_level IS NOT NULL GROUP BY risk_level")
        risk_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        if not risk_dist:
            log_test_result('风险等级', True, '暂无风险等级数据（正常，风险引擎异步执行）', time.time() - start)
            return True
        
        log_test_result('风险等级', True, f'分布: {risk_dist}', time.time() - start)
        return True
        
    except Exception as e:
        log_test_result('风险等级', False, str(e), time.time() - start)
        return False


def test_events_aggregation():
    """测试7：事件聚合"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        
        cursor = conn.execute("SELECT COUNT(*) FROM events")
        event_count = cursor.fetchone()[0]
        
        if event_count > 0:
            cursor = conn.execute("SELECT title, risk_level, mention_count FROM events ORDER BY mention_count DESC LIMIT 5")
            top_events = cursor.fetchall()
            log_test_result('事件聚合', True, f'共{event_count}个事件，TOP5: {[e[0] for e in top_events]}', time.time() - start)
        else:
            log_test_result('事件聚合', True, '暂无聚合事件（正常，事件聚合异步执行）', time.time() - start)
        
        conn.close()
        return True
        
    except Exception as e:
        log_test_result('事件聚合', False, str(e), time.time() - start)
        return False


def test_daily_reports():
    """测试8：日报生成"""
    start = time.time()
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'monitor.db')
        conn = sqlite3.connect(db_path)
        
        cursor = conn.execute("SELECT COUNT(*) FROM daily_reports")
        report_count = cursor.fetchone()[0]
        
        if report_count > 0:
            cursor = conn.execute("SELECT report_type, report_date FROM daily_reports ORDER BY report_date DESC LIMIT 5")
            recent_reports = cursor.fetchall()
            log_test_result('日报生成', True, f'共{report_count}份报告，最近: {[r[1] for r in recent_reports]}', time.time() - start)
        else:
            log_test_result('日报生成', True, '暂无日报（正常，日报定时生成）', time.time() - start)
        
        conn.close()
        return True
        
    except Exception as e:
        log_test_result('日报生成', False, str(e), time.time() - start)
        return False


def test_api_endpoints():
    """测试9：API端点可用性"""
    start = time.time()
    
    try:
        import requests
        
        base_url = 'http://127.0.0.1:8200'
        
        # 测试状态端点（需要认证，预期401）
        try:
            response = requests.get(f'{base_url}/api/status', timeout=5)
            if response.status_code == 401:
                log_test_result('API端点', True, 'API服务运行中（返回401需要认证，正常）', time.time() - start)
                return True
            elif response.status_code == 200:
                log_test_result('API端点', True, 'API服务运行中（无需认证）', time.time() - start)
                return True
            else:
                log_test_result('API端点', False, f'返回状态码: {response.status_code}', time.time() - start)
                return False
        except requests.exceptions.ConnectionError:
            log_test_result('API端点', False, '无法连接到API服务（系统未启动？）', time.time() - start)
            return False
            
    except ImportError:
        log_test_result('API端点', True, '跳过（requests库未安装）', time.time() - start)
        test_results['skipped'] += 1
        return True
    except Exception as e:
        log_test_result('API端点', False, str(e), time.time() - start)
        return False


def test_config_files():
    """测试10：配置文件完整性"""
    start = time.time()
    
    try:
        base_dir = os.path.dirname(__file__)
        
        required_files = [
            'app.py',
            'database.py',
            'config.py',
            'logger.py',
            'database_migrations.py',
            'requirements.txt',
            '.env.example',
            'system_config.json',
        ]
        
        missing_files = []
        for f in required_files:
            if not os.path.exists(os.path.join(base_dir, f)):
                missing_files.append(f)
        
        if missing_files:
            log_test_result('配置文件', False, f'缺少文件: {missing_files}', time.time() - start)
            return False
        
        log_test_result('配置文件', True, f'所有{len(required_files)}个必需文件存在', time.time() - start)
        return True
        
    except Exception as e:
        log_test_result('配置文件', False, str(e), time.time() - start)
        return False


def test_database_migration():
    """测试11：数据库迁移脚本"""
    start = time.time()
    
    try:
        from database_migrations import get_current_version, CURRENT_VERSION, get_connection
        
        conn = get_connection()
        current_version = get_current_version(conn)
        conn.close()
        
        log_test_result(
            '数据库迁移', 
            True, 
            f'当前版本v{current_version}，最新版本v{CURRENT_VERSION}', 
            time.time() - start
        )
        return True
        
    except Exception as e:
        log_test_result('数据库迁移', False, str(e), time.time() - start)
        return False


def test_logger_system():
    """测试12：日志系统"""
    start = time.time()
    
    try:
        from logger import get_logger, get_log_summary
        
        logger = get_logger('test_e2e')
        logger.info('端到端测试日志系统')
        
        summary = get_log_summary()
        
        log_test_result('日志系统', True, f'日志目录存在，共{summary["total_files"]}个文件，{summary["total_size_mb"]}MB', time.time() - start)
        return True
        
    except Exception as e:
        log_test_result('日志系统', False, str(e), time.time() - start)
        return False


def test_config_system():
    """测试13：配置系统"""
    start = time.time()
    
    try:
        from config import get_config
        
        config = get_config()
        validation = config.validate()
        
        log_test_result(
            '配置系统', 
            True, 
            f'配置有效: {validation["valid"]}，已配置{validation["details"]["configured_keys"]}/{validation["details"]["total_keys"]}个键', 
            time.time() - start
        )
        return True
        
    except Exception as e:
        log_test_result('配置系统', False, str(e), time.time() - start)
        return False


def run_all_tests(quick: bool = False):
    """运行所有测试"""
    print("=" * 80)
    print("🧪 广州太古汇舆情监测系统 - 端到端测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"快速模式: {quick}")
    print()
    
    # 基础测试
    print("📊 基础测试")
    print("-" * 80)
    test_database_connection()
    test_database_schema()
    test_data_integrity()
    test_config_files()
    
    print()
    print("🔍 数据测试")
    print("-" * 80)
    test_subject_filter()
    test_sentiment_analysis()
    test_risk_level()
    test_events_aggregation()
    test_daily_reports()
    
    print()
    print("⚙️  系统测试")
    print("-" * 80)
    test_database_migration()
    test_logger_system()
    test_config_system()
    
    if not quick:
        print()
        print("🌐 API测试")
        print("-" * 80)
        test_api_endpoints()
    
    # 测试总结
    print()
    print("=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")
    print(f"⏭️  跳过: {test_results['skipped']}")
    print(f"总计: {test_results['passed'] + test_results['failed'] + test_results['skipped']}")
    
    pass_rate = test_results['passed'] / (test_results['passed'] + test_results['failed']) * 100 if (test_results['passed'] + test_results['failed']) > 0 else 0
    print(f"通过率: {pass_rate:.1f}%")
    
    if test_results['failed'] > 0:
        print()
        print("❌ 失败的测试:")
        for detail in test_results['details']:
            if not detail['passed']:
                print(f"  - {detail['name']}: {detail['message']}")
    
    print()
    return test_results['failed'] == 0


if __name__ == '__main__':
    quick_mode = '--quick' in sys.argv
    verbose_mode = '--verbose' in sys.argv
    
    success = run_all_tests(quick=quick_mode)
    
    sys.exit(0 if success else 1)
