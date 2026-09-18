"""
collector_v2 接入补丁
将collector_v2模块化采集器接入现有app.py
不破坏现有系统，提供可选的新采集器入口
通过 USE_COLLECTOR_V2 配置切换

使用方法：
1. 将此文件放在项目根目录
2. 在app.py中添加：
   from collector_v2_integration import init_collector_v2, collect_with_v2
   init_collector_v2(app)
3. 设置环境变量 USE_COLLECTOR_V2=true 启用新采集器
"""
import os
import sys
import json
import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime
from functools import wraps

# 确保collector_v2可以导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from lumenis.system.collector.runtime.xhs.collector import XHSCollector
    from lumenis.system.collector.runtime.pipeline.normalize import NoteNormalizer
    from lumenis.system.collector.runtime.pipeline.deduplicate import SimHashDeduplicator
    from lumenis.system.collector.runtime.pipeline.spam_filter import SpamFilter
    from lumenis.system.collector.runtime.pipeline.subject_filter import SubjectFilter, filter_subject
    from lumenis.system.collector.runtime.pipeline.persist import NotePersister
    from lumenis.system.collector.runtime.scheduler.collector_job import Scheduler, CollectMode
    from subject_rules import subject_hit_text
    V2_AVAILABLE = True
except ImportError as e:
    V2_AVAILABLE = False
    V2_IMPORT_ERROR = str(e)


# 全局实例
_collector: Optional[XHSCollector] = None
_normalizer: Optional[NoteNormalizer] = None
_deduplicator: Optional[SimHashDeduplicator] = None
_spam_filter: Optional[SpamFilter] = None
_subject_filter: Optional[SubjectFilter] = None
_persister: Optional[NotePersister] = None
_scheduler: Optional[Scheduler] = None
_initialized = False


def is_v2_enabled() -> bool:
    """检查是否启用collector_v2"""
    if not V2_AVAILABLE:
        return False
    return os.environ.get('USE_COLLECTOR_V2', 'false').lower() == 'true'


def init_collector_v2(app=None, cookie: str = "", brand_directory_path: str = ""):
    """
    初始化collector_v2
    app: Flask应用实例（可选，用于注册路由）
    cookie: 小红书Cookie
    brand_directory_path: 品牌目录JSON路径
    """
    global _collector, _normalizer, _deduplicator, _spam_filter
    global _subject_filter, _persister, _scheduler, _initialized
    
    if not V2_AVAILABLE:
        print(f"[CollectorV2] 模块不可用: {V2_IMPORT_ERROR}")
        return False
    
    if _initialized:
        return True
    
    try:
        # 初始化各模块
        _collector = XHSCollector(cookie=cookie)
        _normalizer = NoteNormalizer()
        _deduplicator = SimHashDeduplicator(threshold=6)
        _spam_filter = SpamFilter()
        _subject_filter = SubjectFilter()
        
        # 加载品牌关键词
        if brand_directory_path and os.path.exists(brand_directory_path):
            _subject_filter.load_brands(brand_directory_path)
        
        _persister = NotePersister()
        _scheduler = Scheduler()
        
        _initialized = True
        print(f"[CollectorV2] 初始化成功，启用状态: {is_v2_enabled()}")
        
        # 如果提供了app，注册路由
        if app:
            _register_routes(app)
        
        return True
    except Exception as e:
        print(f"[CollectorV2] 初始化失败: {e}")
        return False


def _register_routes(app):
    """注册collector_v2相关路由"""
    
    @app.route('/api/collector-v2/status')
    def collector_v2_status():
        """获取collector_v2状态"""
        from flask import jsonify
        return jsonify({
            'available': V2_AVAILABLE,
            'enabled': is_v2_enabled(),
            'initialized': _initialized,
            'scheduler': _scheduler.get_status() if _scheduler else None,
            'dedup_size': _deduplicator.size if _deduplicator else 0,
        })
    
    @app.route('/api/collector-v2/collect', methods=['POST'])
    def collector_v2_collect():
        """使用collector_v2采集"""
        from flask import request, jsonify
        if not is_v2_enabled():
            return jsonify({'ok': False, 'error': 'collector_v2未启用，设置USE_COLLECTOR_V2=true启用'}), 400
        
        data = request.get_json() or {}
        keywords = data.get('keywords', ['广州太古汇'])
        max_scroll = data.get('max_scroll', 3)
        
        try:
            result = asyncio.run(collect_with_v2(keywords, max_scroll))
            return jsonify({'ok': True, 'result': result})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
    
    @app.route('/api/collector-v2/scheduler/status')
    def collector_v2_scheduler_status():
        """获取调度器状态"""
        from flask import jsonify
        if not _scheduler:
            return jsonify({'ok': False, 'error': '调度器未初始化'}), 400
        return jsonify({'ok': True, 'status': _scheduler.get_status()})


async def collect_with_v2(keywords: List[str], max_scroll: int = 3,
                           mode: CollectMode = CollectMode.NORMAL) -> Dict:
    """
    使用collector_v2完整流水线采集
    采集 → 标准化 → 水军过滤 → SimHash去重 → 主体过滤 → 持久化
    """
    if not _initialized:
        raise RuntimeError("collector_v2未初始化，请先调用init_collector_v2()")
    
    start_time = datetime.now()
    stats = {
        'keywords': keywords,
        'raw_collected': 0,
        'after_normalize': 0,
        'after_spam_filter': 0,
        'spam_removed': 0,
        'after_dedup': 0,
        'duplicates_removed': 0,
        'after_subject_filter': 0,
        'subject_excluded': 0,
        'inserted': 0,
        'updated': 0,
        'failed': 0,
        'duration_seconds': 0,
    }
    
    all_notes = []
    
    # 1. 采集
    for keyword in keywords:
        try:
            notes = await _collector.search(keyword, max_scroll=max_scroll)
            all_notes.extend([n.__dict__ for n in notes])
            stats['raw_collected'] += len(notes)
        except Exception as e:
            print(f"[CollectorV2] 关键词'{keyword}'采集失败: {e}")
    
    if not all_notes:
        stats['duration_seconds'] = (datetime.now() - start_time).total_seconds()
        return stats
    
    # 2. 标准化
    normalized = _normalizer.normalize_notes(all_notes)
    normalized = _normalizer.filter_valid(normalized)
    stats['after_normalize'] = len(normalized)
    
    # 3. 水军过滤
    valid_notes, spam_notes = _spam_filter.filter_notes(normalized)
    stats['after_spam_filter'] = len(valid_notes)
    stats['spam_removed'] = len(spam_notes)
    
    # 4. SimHash去重
    unique_notes = _deduplicator.batch_deduplicate(valid_notes)
    stats['after_dedup'] = len(unique_notes)
    stats['duplicates_removed'] = len(valid_notes) - len(unique_notes)
    
    # 5. 主体过滤（T3修复：统一委托 subject_rules 权威口径，消除独立词表口径分叉）
    related_notes = filter_subject(unique_notes, subject_hit_text)
    stats['after_subject_filter'] = len(related_notes)
    stats['subject_excluded'] = len(unique_notes) - len(related_notes)
    
    # 6. 持久化
    if related_notes:
        persist_result = _persister.batch_persist(related_notes)
        stats['inserted'] = persist_result.get('inserted', 0)
        stats['updated'] = persist_result.get('updated', 0)
        stats['failed'] = persist_result.get('failed', 0)
    
    # 7. 记录采集
    if _scheduler:
        _scheduler.record_collect(mode)
    
    stats['duration_seconds'] = round((datetime.now() - start_time).total_seconds(), 2)
    return stats


def update_cookie(cookie: str):
    """更新Cookie"""
    if _collector:
        _collector.update_cookie(cookie)
        print("[CollectorV2] Cookie已更新")


def get_v2_modules() -> Dict:
    """获取collector_v2各模块实例（用于外部调用）"""
    return {
        'collector': _collector,
        'normalizer': _normalizer,
        'deduplicator': _deduplicator,
        'spam_filter': _spam_filter,
        'subject_filter': _subject_filter,
        'persister': _persister,
        'scheduler': _scheduler,
        'available': V2_AVAILABLE,
        'enabled': is_v2_enabled(),
        'initialized': _initialized,
    }
