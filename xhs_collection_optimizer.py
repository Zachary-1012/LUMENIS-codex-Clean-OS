# -*- coding: utf-8 -*-
"""
XHS Collection Compliance Optimizer
小红书采集合规优化模块
【功能】
1. 按 note_type 三级分类采集（topic话题/opinion舆情/event事件）
2. 香港 RedNote + 国内小红书 双平台每天登录保活机制（对等）
3. 采集结果按分类存储和展示
【原则】合规采集，不破解不绕风控，失败真实记录，不伪装0条

【硬红线 · 广州太古汇官方账号只读保护（用户 2026-09-03 明令）】
- 无论页面登录的是哪个账号（含广州太古汇官方账号），本模块及一切自动采集/保活/内置浏览器自动流程，
  对账号一律【只读】：只允许 打开页面(goto)、读取 cookie/会话、读取公开内容、探测登录态。
- 严禁任何写操作/交互动作作用于账号：关注/取关、点赞、收藏、评论、私信、发布、转发、
  改资料/设置、退出登录、切换账号、点击任何社交动作按钮（follow/like/collect/comment/publish/logout 等）。
- 登录仅由用户本人在系统内浏览器手动扫码完成；自动流程不得替用户点击任何账号操作。
- 采集“展开评论/滚动浏览”属只读，允许；“发表评论/点赞”属写操作，永久禁止。
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

# ============ 双平台登录保活统一配置（香港 RedNote / 国内小红书）============
_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
KEEPALIVE_PLATFORMS = {
    'rednote_hk': {
        'label': '香港 RedNote',
        'cdp_url': os.environ.get('XHS_HK_CDP_URL', 'http://127.0.0.1:9223'),
        'domain': 'rednote.com',
        'login_url': 'https://www.rednote.com/login',
        'home_url': 'https://www.rednote.com',
        # 登录态 cookie 候选名（国际站 web_session / webBuild 不同版本可能不同，任一命中即视为已登录）
        'session_cookies': ('web_session', 'web_session_v2', 'access-token'),
        # 未登录时页面可见的登录入口文案（中文/英文，cookie 判断失败时回退）
        'login_texts': ('登录', '登 录', 'Log in', 'Sign in', 'Login'),
        'file': LOGIN_KEEPALIVE_FILE,
    },
    'xhs_cn': {
        'label': '国内小红书',
        'cdp_url': os.environ.get('XHS_CN_CDP_URL', 'http://127.0.0.1:9222'),
        'domain': 'xiaohongshu.com',
        'login_url': 'https://www.xiaohongshu.com',
        'home_url': 'https://www.xiaohongshu.com',
        'session_cookies': ('web_session', 'web_session_v2'),
        'login_texts': ('登录', '登 录', 'Log in', 'Sign in'),
        'file': os.path.join(_DATA_DIR, 'data', 'xhs_cn_login_keepalive.json'),
    },
}

# 平台名归一化：前端/历史调用存在两套命名（登录用 xhs/rednote，保活用 xhs_cn/rednote_hk），
# 统一收敛到 KEEPALIVE_PLATFORMS 的两个标准 key，杜绝大陆被错标到香港。
_PLATFORM_ALIASES = {
    'xhs_cn': 'xhs_cn', 'xhs': 'xhs_cn', 'cn': 'xhs_cn', 'china': 'xhs_cn',
    'domestic': 'xhs_cn', 'mainland': 'xhs_cn', '国内': 'xhs_cn', '大陆': 'xhs_cn',
    '国内小红书': 'xhs_cn', '大陆小红书': 'xhs_cn', 'xhs-cn': 'xhs_cn',
    'rednote_hk': 'rednote_hk', 'rednote': 'rednote_hk', 'hk': 'rednote_hk',
    'hongkong': 'rednote_hk', '香港': 'rednote_hk', '香港rednote': 'rednote_hk',
    'rednote-hk': 'rednote_hk', 'retinaut': 'rednote_hk', 'xhs_retinaut': 'rednote_hk',
}


def normalize_platform(platform: str = 'rednote_hk') -> str:
    """把任意平台别名归一化为 'xhs_cn' / 'rednote_hk'；无法识别回退 rednote_hk（向后兼容）。"""
    if not platform:
        return 'rednote_hk'
    key = str(platform).strip().lower().replace(' ', '')
    return _PLATFORM_ALIASES.get(key, 'rednote_hk' if key not in ('xhs_cn',) else 'xhs_cn')

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
    """小红书 / 香港 RedNote 每日登录保活机制（双平台统一）。

    platform 支持：
      - rednote_hk: 香港 RedNote（CDP 9223 / rednote.com）
      - xhs_cn:     国内小红书（CDP 9222 / xiaohongshu.com）
    核心能力：
      - 当日保活标记（last_login_at，每天一次，避免重复弹登录）
      - 会话掉线自动检测（recheck_and_decide：CDP 掉线/登出 → need_relogin，前端自动再弹）
    """

    def __init__(self, keepalive_file: str = None, platform: str = 'rednote_hk'):
        # 平台配置：任意别名统一归一化到 rednote_hk / xhs_cn，两个平台完全对等
        self.platform = normalize_platform(platform)
        _cfg = KEEPALIVE_PLATFORMS[self.platform]
        self.cdp_url = _cfg['cdp_url']
        self.domain = _cfg['domain']
        self.label = _cfg['label']
        self.login_url = _cfg.get('login_url', _cfg['home_url'])
        self.home_url = _cfg.get('home_url', f'https://{_cfg["domain"]}')
        self.session_cookies = tuple(_cfg.get('session_cookies', ('web_session',)))
        self.login_texts = tuple(_cfg.get('login_texts', ('登录', 'Log in')))
        if keepalive_file is None:
            keepalive_file = _cfg['file']
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

    def check_login_status(self, cdp_url: str = None) -> Dict[str, Any]:
        """
        检查当前平台登录状态（通过对应 CDP 浏览器，大陆 9222 / 香港 9223 各自独立）。
        判定优先级：会话 cookie（web_session 等，跨语言最可靠）→ 页面是否存在登录入口文案。
        返回: {status, is_logged_in, checked_at, error}
        """
        cdp_url = cdp_url or self.cdp_url
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
                # 1) cookie 优先：按本平台域名取 cookie，命中会话 cookie 即已登录
                try:
                    cookies = ctx.cookies(self.home_url)
                    names = {c.get('name') for c in (cookies or [])}
                    if names & set(self.session_cookies):
                        result['is_logged_in'] = True
                except Exception:
                    cookies = None
                # 2) cookie 未命中时回退到页面登录入口探测（打开本平台首页）
                if not result['is_logged_in']:
                    page = ctx.new_page()
                    page.goto(self.home_url, wait_until='domcontentloaded', timeout=30000)
                    time.sleep(2)
                    login_present = False
                    for txt in self.login_texts:
                        try:
                            if page.query_selector(f'text={txt}'):
                                login_present = True
                                break
                        except Exception:
                            continue
                    result['is_logged_in'] = not login_present
                    page.close()
                browser.close()
                result['status'] = 'logged_in' if result['is_logged_in'] else 'not_logged_in'
        except Exception as e:
            result['error'] = str(e)
            result['status'] = 'check_failed'

        # 记录检查结果
        data = self._load()
        data['last_check_at'] = result['checked_at']
        data['login_status'] = result['status']
        data['platform'] = self.platform
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

    def _mark_login_reset(self, reason: str = ''):
        """会话掉线时重置当日保活标记（使 should_login_today 重新为 True，前端可再次弹登录）。"""
        data = self._load()
        data['last_login_at'] = None
        data['login_status'] = 'logged_out'
        data['history'].append({
            'status': 'login_reset',
            'is_logged_in': False,
            'checked_at': datetime.now().isoformat(),
            'error': reason or '会话掉线，当日保活标记已重置',
        })
        data['history'] = data['history'][-50:]
        self._save(data)

    def recheck_and_decide(self, cdp_url: str = None) -> Dict[str, Any]:
        """检查 CDP 会话并给出保活决策（掉线自动再弹的核心）。

        决策逻辑：
          - CDP 端口不可达/无法连接 → status=cdp_down, need_relogin=False（浏览器都没在线，弹窗无意义，等 CDP 恢复）
          - CDP 可达但已登出/会话失效 → status=logged_out, need_relogin=True + 重置当日标记（前端自动弹登录）
          - CDP 可达且已登录 → 若当日未标记则自动标记当日完成；status=logged_in, need_relogin=False
        返回: {status, is_logged_in, need_relogin, cdp_online, checked_at, error, message}
        """
        cdp_url = cdp_url or self.cdp_url
        result = {
            'platform': self.platform,
            'label': self.label,
            'domain': self.domain,
            'cdp_url': cdp_url,
            'status': 'unknown',
            'is_logged_in': False,
            'need_relogin': False,
            'cdp_online': False,
            'checked_at': datetime.now().isoformat(),
            'error': None,
            'message': '',
        }
        # 1) CDP 可达性检查
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(cdp_url, timeout=8000)
                result['cdp_online'] = True
                browser.close()
        except Exception as e:
            result['status'] = 'cdp_down'
            result['cdp_online'] = False
            result['need_relogin'] = False
            result['error'] = str(e)[:120]
            result['message'] = f'[{self.label}] 浏览器未在线（CDP {cdp_url}），无法检查会话'
            # 记录检查（仅记录，不重置当日标记：CDP 掉线不等于账号登出）
            try:
                data = self._load()
                data['last_check_at'] = result['checked_at']
                data['login_status'] = 'cdp_down'
                data['history'].append(result)
                data['history'] = data['history'][-50:]
                self._save(data)
            except Exception:
                pass
            return result

        # 2) 会话登录态检查
        chk = self.check_login_status(cdp_url)
        result['checked_at'] = chk.get('checked_at', result['checked_at'])
        result['error'] = chk.get('error')
        if chk.get('is_logged_in'):
            result['status'] = 'logged_in'
            result['is_logged_in'] = True
            result['need_relogin'] = False
            # 已登录 → 若当日未标记则自动标记当日完成（保活达成，避免重复弹登录）
            if self.should_login_today():
                self.mark_login_success()
            result['message'] = f'[{self.label}] 会话已在线，当日保活已确认'
        else:
            result['status'] = 'logged_out'
            result['is_logged_in'] = False
            result['need_relogin'] = True
            # 已登出 → 重置当日标记，前端将自动弹出登录
            self._mark_login_reset(reason=f'[{self.label}] 会话已掉线，需要重新扫码登录')
            result['message'] = f'[{self.label}] 会话已掉线，请重新扫码登录'
        return result

    def get_status(self) -> Dict[str, Any]:
        """获取保活状态。platform 以实例身份为权威（不读历史文件残留，避免旧数据把大陆错标成香港）。"""
        data = self._load()
        return {
            'platform': self.platform,
            'label': self.label,
            'domain': self.domain,
            'cdp_url': self.cdp_url,
            'last_login_at': data.get('last_login_at'),
            'last_check_at': data.get('last_check_at'),
            'login_status': data.get('login_status', 'unknown'),
            'should_login_today': self.should_login_today(),
            'history_count': len(data.get('history', [])),
        }


# 全局保活实例（双平台）
_keepalive = RedNoteLoginKeepalive(platform='rednote_hk')
_keepalive_cn = RedNoteLoginKeepalive(platform='xhs_cn')


def _get_keepalive(platform: str = 'rednote_hk'):
    """按平台取保活实例（任意别名归一化后分派，大陆/香港对等）。"""
    return _keepalive_cn if normalize_platform(platform) == 'xhs_cn' else _keepalive


def check_rednote_login(cdp_url: str = 'http://127.0.0.1:9223') -> Dict:
    """便捷函数：检查香港 RedNote 登录状态。"""
    return _keepalive.check_login_status(cdp_url)


def get_rednote_keepalive_status() -> Dict:
    """便捷函数：获取香港 RedNote 保活状态（兼容旧调用）。"""
    return _keepalive.get_status()


def get_keepalive_status(platform: str = 'rednote_hk') -> Dict:
    """按平台获取保活状态。platform: rednote_hk / xhs_cn。"""
    return _get_keepalive(platform).get_status()


def check_keepalive_login(platform: str = 'rednote_hk', cdp_url: str = None) -> Dict:
    """按平台检查登录状态。"""
    inst = _get_keepalive(platform)
    return inst.check_login_status(cdp_url or inst.cdp_url)


def mark_keepalive_success(platform: str = 'rednote_hk') -> Dict:
    """按平台标记当日保活完成（用户确认 / 登录成功回调调用）。"""
    inst = _get_keepalive(platform)
    inst.mark_login_success()
    return {'ok': True, 'platform': platform, **inst.get_status()}


def recheck_keepalive(platform: str = 'rednote_hk', cdp_url: str = None) -> Dict:
    """按平台执行保活检查并给出决策（掉线自动再弹核心）。"""
    inst = _get_keepalive(platform)
    return inst.recheck_and_decide(cdp_url or inst.cdp_url)


def get_platform_endpoint(platform: str = 'xhs_cn') -> Dict[str, Any]:
    """供登录路由统一解析平台端点：返回标准 key + cdp_url + domain + 各 URL + 会话 cookie 名 + label。
    兼容登录侧命名 xhs/rednote 与保活侧命名 xhs_cn/rednote_hk。"""
    key = normalize_platform(platform)
    cfg = KEEPALIVE_PLATFORMS[key]
    return {
        'key': key,
        'label': cfg['label'],
        'cdp_url': cfg['cdp_url'],
        'domain': cfg['domain'],
        'login_url': cfg.get('login_url', cfg.get('home_url')),
        'home_url': cfg.get('home_url', f'https://{cfg["domain"]}'),
        'session_cookies': tuple(cfg.get('session_cookies', ('web_session',))),
    }


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
