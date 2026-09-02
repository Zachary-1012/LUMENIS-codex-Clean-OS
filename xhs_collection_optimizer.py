# -*- coding: utf-8 -*-
"""
XHS Collection Compliance Optimizer
小红书采集合规优化模块
【功能】
1. 按 note_type 三级分类采集（topic话题/opinion舆情/event事件）
2. 香港 RedNote 每天登录保活机制
3. 采集结果按分类存储和展示
【原则】合规采集，不破解不绕风控，失败真实记录，不伪装0条
"""
import os
import re
import json
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

# ============ 配置 ============
DB_PATH = os.environ.get('ZBC_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'monitor.db'))
LOGIN_KEEPALIVE_FILE = os.environ.get('XHS_LOGIN_KEEPALIVE_FILE',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'xhs_login_keepalive.json'))

# note_type 分类规则
NOTE_TYPE_RULES = {
    'topic': {
        'keywords': ['活动', '探店', '打卡', '优惠', '促销', '折扣', '满减', '买一送一',
                     '开业', '周年', '庆典', '节日', '圣诞', '元旦', '春节', '五一', '国庆',
                     '展览', '快闪', '市集', '嘉年华', '派对', '演出', '音乐会'],
        'description': '话题活动类笔记',
    },
    'opinion': {
        'keywords': ['投诉', '差评', '吐槽', '失望', '垃圾', '难吃', '贵', '服务差', '态度差',
                     '好评', '推荐', '喜欢', '不错', '体验', '感受', '评价', '测评', '对比',
                     '避雷', '避坑', '踩雷', '种草', '拔草', '值得', '不值得'],
        'description': '舆情评价类笔记',
    },
    'event': {
        'keywords': ['事件', '事故', '纠纷', '维权', '曝光', '爆料', '丑闻', '危机', '公关',
                     '回应', '声明', '道歉', '整改', '处罚', '罚款', '调查', '起诉', '法律',
                     '闭店', '撤店', '关店', '倒闭', '跑路', '爆雷', '翻车'],
        'description': '事件类笔记',
    },
}

# 默认分类
DEFAULT_NOTE_TYPE = 'opinion'


# ============ 1. note_type 分类器 ============
class NoteTypeClassifier:
    """笔记分类器：根据标题和内容自动分类为 topic/opinion/event。"""

    def __init__(self):
        self.rules = NOTE_TYPE_RULES

    def classify(self, title: str = '', content: str = '', keywords: List[str] = None) -> Tuple[str, Dict[str, int]]:
        """
        分类笔记。
        返回: (note_type, scores)
        """
        text = f"{title or ''} {content or ''}"
        if keywords:
            text += ' ' + ' '.join(keywords)

        scores = {}
        for note_type, rule in self.rules.items():
            score = 0
            for kw in rule['keywords']:
                if kw in text:
                    score += 1
            scores[note_type] = score

        # 选择得分最高的分类
        max_score = max(scores.values()) if scores else 0
        if max_score == 0:
            return DEFAULT_NOTE_TYPE, scores

        # 找到得分最高的分类（如果有并列，优先 event > topic > opinion）
        for note_type in ['event', 'topic', 'opinion']:
            if scores.get(note_type, 0) == max_score:
                return note_type, scores

        return DEFAULT_NOTE_TYPE, scores

    def classify_and_save(self, note_id: int, title: str = '', content: str = '',
                          keywords: List[str] = None, db_path: str = DB_PATH) -> str:
        """分类并保存到数据库。"""
        note_type, scores = self.classify(title, content, keywords)
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            # 检查 note_type 列是否存在
            c.execute("PRAGMA table_info(notes)")
            columns = [col[1] for col in c.fetchall()]
            if 'note_type' in columns:
                c.execute("UPDATE notes SET note_type = ? WHERE id = ?", (note_type, note_id))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f'[NoteTypeClassifier] 保存失败: {e}')
        return note_type


# 全局分类器
_classifier = NoteTypeClassifier()


def classify_note(title: str = '', content: str = '', keywords: List[str] = None) -> str:
    """便捷函数：分类笔记。"""
    return _classifier.classify(title, content, keywords)[0]


# ============ 2. 香港 RedNote 登录保活 ============
class RedNoteLoginKeepalive:
    """香港 RedNote 每天登录保活机制。"""

    def __init__(self, keepalive_file: str = LOGIN_KEEPALIVE_FILE):
        self.keepalive_file = keepalive_file
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.keepalive_file), exist_ok=True)

    def _load(self) -> Dict:
        if os.path.exists(self.keepalive_file):
            try:
                with open(self.keepalive_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            'last_login_at': None,
            'last_check_at': None,
            'login_status': 'unknown',
            'platform': 'rednote_hk',
            'history': [],
        }

    def _save(self, data: Dict):
        with open(self.keepalive_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def should_login_today(self) -> bool:
        """判断今天是否需要登录（每天一次）。"""
        data = self._load()
        last_login = data.get('last_login_at')
        if not last_login:
            return True
        try:
            last_date = datetime.fromisoformat(last_login).date()
            today = datetime.now().date()
            return last_date < today
        except Exception:
            return True

    def check_login_status(self, cdp_url: str = 'http://127.0.0.1:9223') -> Dict[str, Any]:
        """
        检查香港 RedNote 登录状态（通过 CDP 浏览器）。
        返回: {status, is_logged_in, checked_at, error}
        """
        result = {
            'status': 'unknown',
            'is_logged_in': False,
            'checked_at': datetime.now().isoformat(),
            'error': None,
        }
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(cdp_url, timeout=15000)
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                page = ctx.new_page()
                page.goto('https://www.xiaohongshu.com', wait_until='domcontentloaded', timeout=30000)
                # 检查是否有登录按钮（未登录状态）
                time.sleep(2)
                login_btn = page.query_selector('text=登录')
                result['is_logged_in'] = login_btn is None
                result['status'] = 'logged_in' if result['is_logged_in'] else 'not_logged_in'
                page.close()
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'check_failed'

        # 记录检查结果
        data = self._load()
        data['last_check_at'] = result['checked_at']
        data['login_status'] = result['status']
        data['history'].append(result)
        data['history'] = data['history'][-50:]  # 只保留最近50条
        self._save(data)
        return result

    def mark_login_success(self):
        """标记登录成功（用户扫码登录后调用）。"""
        data = self._load()
        data['last_login_at'] = datetime.now().isoformat()
        data['login_status'] = 'logged_in'
        data['history'].append({
            'status': 'login_success',
            'is_logged_in': True,
            'checked_at': datetime.now().isoformat(),
            'error': None,
        })
        self._save(data)

    def get_status(self) -> Dict[str, Any]:
        """获取保活状态。"""
        data = self._load()
        return {
            'platform': data.get('platform', 'rednote_hk'),
            'last_login_at': data.get('last_login_at'),
            'last_check_at': data.get('last_check_at'),
            'login_status': data.get('login_status', 'unknown'),
            'should_login_today': self.should_login_today(),
            'history_count': len(data.get('history', [])),
        }


# 全局保活实例
_keepalive = RedNoteLoginKeepalive()


def check_rednote_login(cdp_url: str = 'http://127.0.0.1:9223') -> Dict:
    """便捷函数：检查香港 RedNote 登录状态。"""
    return _keepalive.check_login_status(cdp_url)


def get_rednote_keepalive_status() -> Dict:
    """便捷函数：获取香港 RedNote 保活状态。"""
    return _keepalive.get_status()


# ============ 3. 采集合规优化 ============
class XHSCollectionOptimizer:
    """小红书采集合规优化：按分类采集、真人频率、动态冷却。"""

    def __init__(self):
        self.classifier = NoteTypeClassifier()
        self.keepalive = RedNoteLoginKeepalive()

    def get_collection_config(self, note_type: str = 'all') -> Dict[str, Any]:
        """
        根据分类获取采集配置。
        topic: 话题端不停止监测和收录
        opinion: 舆情笔记端开放
        event: 事件笔记端推进（按最新测试的真人频率数据）
        """
        configs = {
            'topic': {
                'enabled': True,
                'description': '话题活动端：不停止监测和收录',
                'max_scroll': 5,
                'max_details': 15,
                'interval_min': 20,  # 最小间隔20分钟
                'human_frequency': 'normal',
            },
            'opinion': {
                'enabled': True,
                'description': '舆情笔记端：开放采集',
                'max_scroll': 4,
                'max_details': 12,
                'interval_min': 30,
                'human_frequency': 'normal',
            },
            'event': {
                'enabled': True,
                'description': '事件笔记端：按真人频率数据监测，系统正式运行',
                'max_scroll': 3,
                'max_details': 8,
                'interval_min': 45,
                'human_frequency': 'conservative',
            },
            'all': {
                'enabled': True,
                'description': '全分类采集',
                'max_scroll': 4,
                'max_details': 10,
                'interval_min': 30,
                'human_frequency': 'normal',
            },
        }
        return configs.get(note_type, configs['all'])

    def should_collect(self, note_type: str, last_collect_at: str = None) -> Tuple[bool, str]:
        """
        判断是否应该采集（基于分类和间隔）。
        返回: (should_collect, reason)
        """
        config = self.get_collection_config(note_type)
        if not config['enabled']:
            return False, f'{note_type} 采集已禁用'

        if last_collect_at:
            try:
                last_time = datetime.fromisoformat(last_collect_at)
                elapsed = (datetime.now() - last_time).total_seconds() / 60
                if elapsed < config['interval_min']:
                    return False, f'距上次采集仅 {elapsed:.0f} 分钟，需间隔 {config["interval_min"]} 分钟'
            except Exception:
                pass

        return True, '可以采集'

    def get_human_sleep_range(self, human_frequency: str = 'normal') -> Tuple[float, float]:
        """获取真人睡眠间隔范围（秒）。"""
        ranges = {
            'conservative': (3.0, 6.0),  # 保守：慢一点
            'normal': (1.5, 3.5),         # 正常
            'fast': (0.8, 2.0),           # 快速（不推荐）
        }
        return ranges.get(human_frequency, ranges['normal'])


# 全局优化器
_optimizer = XHSCollectionOptimizer()


def get_collection_config(note_type: str = 'all') -> Dict:
    """便捷函数：获取采集配置。"""
    return _optimizer.get_collection_config(note_type)


# ============ 主入口（测试用） ============
if __name__ == '__main__':
    print('=== XHS 采集合规优化模块 ===')

    # 测试分类器
    print('\n1. 笔记分类测试:')
    test_cases = [
        ('广州太古汇十五周年活动探店', '今天去了太古汇十五周年活动，好多优惠'),
        ('吐槽太古汇某餐厅服务态度差', '等了一个小时才上菜，服务员态度还很差'),
        ('太古汇某品牌闭店事件', '突然宣布闭店，消费者维权中'),
    ]
    for title, content in test_cases:
        note_type = classify_note(title, content)
        print(f'   [{note_type}] {title}')

    # 测试采集配置
    print('\n2. 采集配置:')
    for nt in ['topic', 'opinion', 'event']:
        config = get_collection_config(nt)
        print(f'   {nt}: enabled={config["enabled"]}, interval={config["interval_min"]}min, {config["description"]}')

    # 测试保活状态
    print('\n3. RedNote 保活状态:')
    status = get_rednote_keepalive_status()
    print(f'   状态: {status["login_status"]}')
    print(f'   上次登录: {status["last_login_at"]}')
    print(f'   今天需要登录: {status["should_login_today"]}')

    print('\n模块加载完成！')
