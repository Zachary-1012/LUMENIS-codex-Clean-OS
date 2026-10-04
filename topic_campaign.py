"""v5.7.3 活动专题监测能力（适配广州太古汇 v5.7.0 系统）。

适配要点：
1. 固定时间点调度（中频率：9/11/13/15/17/19点，错峰5-10分），与主舆情采集时间点完全不重叠
2. 独立 daemon 调度线程，不依赖已禁用的主 scheduler_loop
3. 独立采集配额：不占用主舆情每日12次配额，专题自己计数（每日上限8次，含手动）【2026-09-03 本人授权例外，见 00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md 的 retained TopicCampaign safety parameters】
4. 单次采集最长50分钟，充分滚动加载，保证数据完整
5. 复用 _collect_lock 互斥，主采集运行时专题自动让行
6. 7个话题完整覆盖（含 #拾光五境、#广州太古汇15周年促销）
7. 独立4张表，不污染主舆情库，不修改主体过滤逻辑
8. 活动窗口（2026-08-28 ~ 2026-10-07）外自动停止
9. 绝不伪造数据：采集失败记录错误快照，浏览量/讨论量采不到就存0并标注状态
"""
# 话题APP端采集adapter（小红书APP搜索话题，与Web端互补）
try:
    from lumenis.system.collector.adapters.xhs_app_topic import XHSAppTopicAdapter
    APP_TOPIC_ENABLED = True
except ImportError:
    APP_TOPIC_ENABLED = False
    XHSAppTopicAdapter = None

import os, json, threading, subprocess, time, csv, io, sys, random, logging
from datetime import datetime
from flask import jsonify, request, send_from_directory, Response

# V2.0 基线 P0-1：统一 XHS Runtime State 六态状态机
# AUTH / SESSION / PLATFORM / COLLECTOR / CIRCUIT / RECOVERY
try:
    from xhs_runtime_state import (
        XhsRuntimeState, state_from_probe, state_from_circuit,
        CircuitState, PlatformState, AuthState, CollectorState, RecoveryState,
    )
    _RUNTIME_STATE_AVAILABLE = True
except Exception as _e:
    _RUNTIME_STATE_AVAILABLE = False
    _RUNTIME_STATE_IMPORT_ERROR = str(_e)

# V3.0 P0-2 阶段1：统一动态调度影子模式接入
# 只做观察、记录、回写，不门控固定时钟，不改变任何生产采集行为
try:
    from lumenis.system.collector.adapters.scheduling import get_planner
    _SCHEDULER_AVAILABLE = True
except Exception as _e:
    _SCHEDULER_AVAILABLE = False
    _SCHEDULER_IMPORT_ERROR = str(_e)

# 统一 Node 运行时解析：优先 PATH，兜底项目内置 nodejs/，避免常驻进程 PATH 缺 node 抛 WinError 2
try:
    from runtime_bin import resolve_node as _resolve_node
except Exception:
    def _resolve_node():
        import shutil
        # 1. NODE_EXE 环境变量
        exe = os.getenv('NODE_EXE', '').strip()
        if exe and os.path.isfile(exe):
            return exe
        # 2. 项目 nodejs/ 目录
        proj_node = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodejs', 'node.exe')
        if os.path.isfile(proj_node):
            return proj_node
        # 3. PATH 中查找（app.py 启动时已注入沙箱 node）
        found = shutil.which('node')
        if found:
            return found
        return None

logger = logging.getLogger(__name__)
# ZBC Lifecycle Contract V1.0 (bypass-mode)
try:
    from lifecycle_mixin import LifecycleMixin as _LifecycleMixin
    _LIFECYCLE_AVAILABLE = True
except Exception:
    _LifecycleMixin = None
    _LIFECYCLE_AVAILABLE = False


def _node_bin():
    """返回可用 node 路径；解析不到时返回 None，由调用方产出结构化错误（不进 subprocess）。"""
    try:
        return _resolve_node() or None
    except Exception:
        return 'node'


def _canonical_campaign_identity(auto_trigger=False):
    """Resolve the only permitted RedNote campaign identity without side effects.

    This is a configuration/policy check only: it never connects to CDP, opens a
    profile, reads a Cookie, starts a process, or reads the business database.
    """
    account = 'XHS_RETINAUT'
    region = 'intl'
    try:
        from lumenis.system.collector.adapters import rednote_policy
        gate = rednote_policy.collection_gate(account=account, region=region)
        policy = rednote_policy.effective_policy()
    except Exception as exc:
        return {'ok': False, 'code': 'POLICY_UNAVAILABLE',
                'reason': f'RedNote policy unavailable; collection is blocked: {exc}'}

    if (gate.get('ok') is not True or gate.get('account') != account
            or gate.get('region') != region or gate.get('cdp_port') != 9223
            or gate.get('host') != 'www.rednote.com'):
        return {'ok': False, 'code': 'IDENTITY_BLOCKED',
                'reason': gate.get('reason') or 'Canonical policy did not allow the HK/international route',
                'policy': gate}
    if not policy.can_run_kind('topic'):
        return {'ok': False, 'code': 'TOPIC_COLLECTION_DISABLED',
                'reason': 'Canonical RedNote policy has disabled topic collection', 'policy': gate}
    if auto_trigger and not policy.auto_run_enabled:
        return {'ok': False, 'code': 'AUTO_RUN_DISABLED',
                'reason': 'Automatic RedNote collection requires REDNOTE_AUTO_RUN=true', 'policy': gate}

    endpoint = os.environ.get('XHS_CDP_URL') or ''
    if not endpoint:
        return {'ok': False, 'code': 'COLLECTOR_ENDPOINT_NOT_CONFIGURED',
                'reason': 'No explicit HK browser endpoint is configured', 'policy': gate}
    if endpoint != 'http://127.0.0.1:9223':
        return {'ok': False, 'code': 'COLLECTOR_ENDPOINT_INVALID',
                'reason': 'Only the explicit approved HK endpoint http://127.0.0.1:9223 is permitted',
                'policy': gate}

    return {'ok': True, 'account': account, 'region': region, 'cdp_port': 9223,
            'host': 'www.rednote.com', 'cdp_url': endpoint,
            'policy_version': gate.get('policy_version'), 'policy': gate}


def _legacy_campaign_route_status(auto_trigger=False):
    """Fail closed: the legacy campaign worker is Mainland-only and cannot be reused.

    The JavaScript worker and detail-backfill script still target the Mainland
    host and retain legacy browser/profile fallbacks. This owner is deliberately
    disabled until a bounded follow-up binds these callers to SYSTEM Collector.
    """
    identity = _canonical_campaign_identity(auto_trigger=auto_trigger)
    if not identity.get('ok'):
        return identity
    return {'ok': False, 'code': 'CANONICAL_COLLECTOR_BINDING_REQUIRED',
            'reason': 'Campaign collection is unavailable until this legacy caller is bound to the canonical SYSTEM Collector',
            'identity': identity}

# ========== 专题配置 ==========
DEFAULT_TOPICS = [
    '#广州太古汇十五周年',
    '#广州太古汇15周年',
    '#一方五境',
    '#广州太古汇',
    '#那年汇相遇',
    '#拾光五境',
    '#广州太古汇15周年促销',
]
START_DATE = '2026-08-28'
END_DATE = '2026-10-07'
MODULE_VERSION = '5.8.11-probe-fix'
CAMPAIGN_KEY = 'taikoo_15th'

# 中频率固定时间点调度（与主采集 8/10/12/14/16/18/20/22/23 完全错峰，间隔约2小时）
CAMPAIGN_COLLECT_HOURS = [9, 11, 13, 15, 17, 19]

# ========== 专题独立安全控制（不占用主采集配额） ==========
CAMPAIGN_MAX_DAILY_RUNS = 8       # 专题每日最大采集次数（含手动，保护账号）
CAMPAIGN_MIN_INTERVAL_MINUTES = 30 # 两次专题采集最小间隔（分钟）
CAMPAIGN_COLLECT_TIMEOUT = 3000     # 单次采集最长时间（秒）= 50分钟
CAMPAIGN_MAX_SCROLL = 6              # 每个话题最大滚动次数
CAMPAIGN_TOPIC_GAP_MIN = 12          # 同一轮内相邻话题的拟人随机冷却下限（秒），避免短时密集搜索被软降频
CAMPAIGN_TOPIC_GAP_MAX = 28          # 相邻话题冷却上限（秒）
CAMPAIGN_TOPIC_GAP_CAP = 90          # 连续空结果退避时的间隔封顶（秒）
CAMPAIGN_IP_RISK_COOLDOWN = 2700      # IP_RISK 熔断冷却（秒，45分钟）后自动半开；NEED_VERIFY 不自动恢复，须人工验证
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CAMPAIGN_CIRCUIT = os.path.join(_BASE_DIR, 'data', 'private', 'topic_campaign_circuit.json')
_today_campaign_runs = []            # 今日专题采集时间戳列表

# ========== 线程安全 ==========
_lock = threading.Lock()
_app_lock = None
_last_run = 0.0
_scheduler_running = False
_today_run_hours = set()
_today_date = ''

# ========== 数据库 Schema ==========
SCHEMA = """
CREATE TABLE IF NOT EXISTS topic_campaigns (
 id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_key TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
 status TEXT DEFAULT 'active', interval_minutes INTEGER DEFAULT 90,
 created_at TEXT DEFAULT (datetime('now','localtime')), updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS topic_campaign_topics (
 id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_key TEXT NOT NULL, topic TEXT NOT NULL,
 normalized_topic TEXT NOT NULL, enabled INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now','localtime')),
 UNIQUE(campaign_key, normalized_topic)
);
CREATE TABLE IF NOT EXISTS topic_campaign_snapshots (
 id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_key TEXT NOT NULL, topic TEXT NOT NULL,
 captured_at TEXT NOT NULL, browse_count INTEGER DEFAULT 0, discussion_count INTEGER DEFAULT 0,
 note_count INTEGER DEFAULT 0, new_note_count INTEGER DEFAULT 0, engagement_count INTEGER DEFAULT 0,
 status TEXT DEFAULT 'success', error TEXT DEFAULT '', raw_json TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS topic_campaign_notes (
 id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_key TEXT NOT NULL, topic TEXT NOT NULL,
 note_id TEXT NOT NULL, title TEXT DEFAULT '', content TEXT DEFAULT '', author TEXT DEFAULT '',
 publish_datetime TEXT DEFAULT '', likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
 collects INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, note_url TEXT DEFAULT '',
 first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, raw_json TEXT DEFAULT '{}',
 UNIQUE(campaign_key, topic, note_id)
);
CREATE INDEX IF NOT EXISTS idx_tcs_campaign_topic_time ON topic_campaign_snapshots(campaign_key, topic, captured_at);
CREATE INDEX IF NOT EXISTS idx_tcn_campaign_topic_time ON topic_campaign_notes(campaign_key, topic, last_seen_at);
"""

def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def _norm(t):
    return (t or '').strip().lstrip('#').strip().lower()

def _db():
    import database as db
    return db

def init_campaign():
    """初始化专题数据表和默认配置。"""
    db = _db()
    with db.get_db() as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO topic_campaigns(campaign_key,name,start_date,end_date,interval_minutes) VALUES(?,?,?,?,?)",
            (CAMPAIGN_KEY, '广州太古汇十五周年', START_DATE, END_DATE, 240)
        )
        for t in DEFAULT_TOPICS:
            conn.execute(
                "INSERT OR IGNORE INTO topic_campaign_topics(campaign_key,topic,normalized_topic) VALUES(?,?,?)",
                (CAMPAIGN_KEY, t, _norm(t))
            )

def _campaign_active():
    """检查当前日期是否在活动窗口内。"""
    d = datetime.now().strftime('%Y-%m-%d')
    return START_DATE <= d <= END_DATE

def _insert_snapshot(conn, campaign_key, topic, data, status='success', error=''):
    now = _now()
    conn.execute(
        """INSERT INTO topic_campaign_snapshots(campaign_key,topic,captured_at,browse_count,discussion_count,note_count,new_note_count,engagement_count,status,error,raw_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (campaign_key, topic, now,
         int(data.get('browse_count') or 0),
         int(data.get('discussion_count') or 0),
         int(data.get('note_count') or 0),
         int(data.get('new_note_count') or 0),
         int(data.get('engagement_count') or 0),
         status, error,
         json.dumps(data, ensure_ascii=False)[:200000])
    )

def _classify_note(n, subject_hit_flag):
    """V2.0 P0-6：基于规则的笔记分类（不依赖AI，可解释、可追溯）。

    返回 (content_type, sentiment, risk_level, evidence_quality)。
    主体口径由 subject_rules.py 决定，这里只做内容类型/情绪/风险的规则判断。
    """
    title = (n.get('title') or n.get('desc') or n.get('content') or '').lower()
    author = (n.get('author') or n.get('nickname') or '').lower()
    has_content = bool((n.get('content') or n.get('desc') or '').strip())
    has_media = bool(n.get('media') or n.get('images') or n.get('image_list'))
    has_comments_detail = bool(n.get('comments_detail') or n.get('comment_list'))

    if has_content and has_media and has_comments_detail:
        eq = 'full'
    elif has_content or has_media:
        eq = 'partial'
    else:
        eq = 'search_only'

    if any(k in author for k in ('太古汇', '官方', 'taikoo')):
        ct = '官方'
    elif any(k in title for k in ('推广', '广告', '赞助', '合作', '商单', '种草')):
        ct = '商业'
    elif any(k in title for k in ('投诉', '差评', '维权', '避雷', '垃圾', '坑', '失望', '退款')):
        ct = '投诉'
    elif any(k in title for k in ('测评', '对比', '评测', '横评')):
        ct = '测评'
    elif any(k in title for k in ('体验', '打卡', '探店', '逛', '一日游')):
        ct = '体验'
    elif any(k in title for k in ('活动', '促销', '优惠', '打折', '周年庆', '展览', '展')):
        ct = '活动内容'
    else:
        ct = 'UGC'

    # FUNC-CONTENT-02: 情感分析统一为单一真相源（canonical_data.unified_sentiment_analysis）
    try:
        from canonical_data import unified_sentiment_analysis
        st = unified_sentiment_analysis(title, n.get('content') or n.get('desc') or '')
        if isinstance(st, dict):
            st = st.get('sentiment', 'neutral')
    except Exception:
        st = 'neutral'

    if subject_hit_flag and ct == '投诉':
        rl = 'high'
    elif subject_hit_flag and st == 'negative':
        rl = 'medium'
    elif st == 'negative':
        rl = 'low'
    else:
        rl = 'none'

    return ct, st, rl, eq


def _save_notes(conn, campaign_key, topic, notes):
    """V2.0 P0-5/P0-6：保存话题笔记，集成主体过滤、分类、情绪、风险、证据质量。

    主体判断必须调用 subject_rules.subject_hit()，绝不重新实现第二套主体规则。
    新增字段：media_json, comments_json, subject_hit, content_type, sentiment, risk_level, evidence_quality, detail_captured_at。
    向后兼容：旧字段不变，新字段有默认值。
    """
    from subject_rules import subject_hit as _subject_hit

    now = _now()
    new = 0
    for n in notes or []:
        nid = str(n.get('note_id') or n.get('id') or '').strip()
        if not nid:
            continue
        subject_text = ' '.join([
            str(n.get('title', '')), str(n.get('content', n.get('desc', ''))),
            str(n.get('author', n.get('nickname', '')))
        ])
        s_hit = 1 if _subject_hit(subject_text) else 0
        ct, st, rl, eq = _classify_note(n, s_hit)

        media_json = json.dumps(n.get('media') or n.get('images') or n.get('image_list') or [], ensure_ascii=False)[:50000]
        comments_json = json.dumps(n.get('comments_detail') or n.get('comment_list') or [], ensure_ascii=False)[:50000]
        detail_captured = n.get('detail_captured_at', '') or (now if eq in ('full', 'partial') else '')

        cur = conn.execute(
            "SELECT id FROM topic_campaign_notes WHERE campaign_key=? AND topic=? AND note_id=?",
            (campaign_key, topic, nid)
        ).fetchone()
        if cur:
            conn.execute(
                """UPDATE topic_campaign_notes SET title=?,content=?,author=?,publish_datetime=?,likes=?,comments=?,collects=?,shares=?,note_url=?,last_seen_at=?,raw_json=?,media_json=?,comments_json=?,subject_hit=?,content_type=?,sentiment=?,risk_level=?,evidence_quality=?,detail_captured_at=? WHERE id=?""",
                (
                    n.get('title', ''), n.get('content', n.get('desc', '')),
                    n.get('author', n.get('nickname', '')),
                    n.get('publish_datetime', n.get('publish_time', '')),
                    int(n.get('likes', n.get('liked_count', 0)) or 0),
                    int(n.get('comments', n.get('comment_count', 0)) or 0),
                    int(n.get('collects', n.get('collected_count', 0)) or 0),
                    int(n.get('shares', n.get('share_count', 0)) or 0),
                    n.get('note_url', n.get('url', '')) or '',
                    now, json.dumps(n, ensure_ascii=False)[:100000],
                    media_json, comments_json, s_hit, ct, st, rl, eq, detail_captured,
                    cur['id'],
                )
            )
        else:
            conn.execute(
                """INSERT INTO topic_campaign_notes(campaign_key,topic,note_id,title,content,author,publish_datetime,likes,comments,collects,shares,note_url,first_seen_at,last_seen_at,raw_json,media_json,comments_json,subject_hit,content_type,sentiment,risk_level,evidence_quality,detail_captured_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    campaign_key, topic, nid,
                    n.get('title', ''), n.get('content', n.get('desc', '')),
                    n.get('author', n.get('nickname', '')),
                    n.get('publish_datetime', n.get('publish_time', '')),
                    int(n.get('likes', n.get('liked_count', 0)) or 0),
                    int(n.get('comments', n.get('comment_count', 0)) or 0),
                    int(n.get('collects', n.get('collected_count', 0)) or 0),
                    int(n.get('shares', n.get('share_count', 0)) or 0),
                    n.get('note_url', n.get('url', '')) or '',
                    now, now, json.dumps(n, ensure_ascii=False)[:100000],
                    media_json, comments_json, s_hit, ct, st, rl, eq, detail_captured,
                )
            )
            new += 1
    return new

def _run_collector(topic):
    """Fail closed until this legacy caller is bound to the SYSTEM Collector."""
    route = _legacy_campaign_route_status()
    return {'ok': False, 'error': route.get('reason', 'Campaign collection is blocked'),
            'status': route.get('code', 'COLLECTION_BLOCKED'), 'topic': topic}

# ========== 专题级风控熔断（NEED_VERIFY 须人工恢复，IP_RISK 定时冷却；绝不把验证页伪装成 0 条） ==========
def _trip_campaign_circuit(status, reason=''):
    """命中安全验证/IP 风控时落熔断文件，停止后续危险请求。"""
    try:
        os.makedirs(os.path.dirname(_CAMPAIGN_CIRCUIT), exist_ok=True)
        now = time.time()
        cooldown = CAMPAIGN_IP_RISK_COOLDOWN if status == 'IP_RISK' else 0
        obj = {
            'status': status, 'reason': reason, 'platform': 'xiaohongshu',
            'opened_at': _now(),
            'resume_at': datetime.fromtimestamp(now + cooldown).strftime('%Y-%m-%d %H:%M:%S') if cooldown else None,
        }
        with io.open(_CAMPAIGN_CIRCUIT, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.warning("Unhandled exception: %s", e)

def _campaign_circuit_state():
    """仍生效返回熔断 dict；NEED_VERIFY 人工清除前一直阻断，IP_RISK 到 resume_at 后半开放行；无熔断返回 None。"""
    try:
        if not os.path.exists(_CAMPAIGN_CIRCUIT):
            return None
        with io.open(_CAMPAIGN_CIRCUIT, 'r', encoding='utf-8') as f:
            obj = json.load(f)
        if obj.get('status') == 'NEED_VERIFY':
            return obj
        ra = obj.get('resume_at')
        if ra:
            try:
                if datetime.now() < datetime.strptime(ra, '%Y-%m-%d %H:%M:%S'):
                    return obj
            except Exception:
                return obj
        return None
    except Exception:
        return None

def clear_campaign_circuit():
    """人工完成验证/健康检查通过后调用，解除专题熔断。"""
    try:
        if os.path.exists(_CAMPAIGN_CIRCUIT):
            os.remove(_CAMPAIGN_CIRCUIT)
    except Exception as e: logger.warning("Unhandled exception: %s", e)

def _probe_xhs_health_via_cdp(test_search=False):
    """Fail closed until health probes use the canonical RedNote Collector owner."""
    route = _legacy_campaign_route_status()
    if route.get('code') == 'CANONICAL_COLLECTOR_BINDING_REQUIRED':
        return False, route['reason']
    return False, f"{route.get('code', 'COLLECTION_BLOCKED')}: {route.get('reason', 'RedNote collection is blocked')}"

# ========== V2.0 P0-1：统一 Runtime State 六态探活 ==========

def _probe_runtime_state():
    """Return an honest unavailable state without probing legacy identity paths."""
    route = _legacy_campaign_route_status()
    if not route.get('ok'):
        unavailable = route.get('code') == 'CANONICAL_COLLECTOR_BINDING_REQUIRED'
        return {
            'overall': 'unavailable' if unavailable else 'blocked',
            'healthy': False,
            'auth_state': 'unknown',
            'session_state': 'unknown',
            'platform_state': 'unknown',
            'collector_state': 'unavailable',
            'circuit_state': 'unknown',
            'recovery_state': 'blocked',
            'last_check': _now(),
            'detail': {'code': route.get('code'), 'reason': route.get('reason')},
        }
    if not _RUNTIME_STATE_AVAILABLE:
        return {
            'overall': 'unknown', 'healthy': False, 'auth_state': 'unknown',
            'session_state': 'unknown', 'platform_state': 'unknown',
            'collector_state': 'unavailable', 'circuit_state': 'unknown',
            'recovery_state': 'idle', 'last_check': _now(),
            'detail': {'runtime_state_unavailable': _RUNTIME_STATE_IMPORT_ERROR},
        }
    state = state_from_circuit(_CAMPAIGN_CIRCUIT)
    state.last_check = _now()
    state.detail['health_probe'] = 'unavailable until canonical Collector binding is implemented'
    return state

def _half_open_probe():
    """Fail closed until half-open recovery uses the canonical RedNote Collector."""
    route = _legacy_campaign_route_status()
    if route.get('code') == 'CANONICAL_COLLECTOR_BINDING_REQUIRED':
        return False, route['reason']
    return False, f"{route.get('code', 'COLLECTION_BLOCKED')}: {route.get('reason', 'RedNote collection is blocked')}"

# ========== 专题独立频率控制（不占用主舆情采集配额） ==========
def _clean_today_runs():
    """清理非今日的运行记录。"""
    global _today_campaign_runs
    today = datetime.now().strftime('%Y-%m-%d')
    _today_campaign_runs = [
        t for t in _today_campaign_runs
        if datetime.fromtimestamp(t).strftime('%Y-%m-%d') == today
    ]

def _check_campaign_rate_limit():
    """检查专题采集频率限制（独立配额，不碰主采集）。

    返回: (是否允许, 提示信息)
    限制：每日最多 CAMPAIGN_MAX_DAILY_RUNS 次，两次间隔至少 CAMPAIGN_MIN_INTERVAL_MINUTES 分钟
    """
    _clean_today_runs()
    now = time.time()
    # 每日次数限制
    if len(_today_campaign_runs) >= CAMPAIGN_MAX_DAILY_RUNS:
        return False, f'今日专题采集已达{len(_today_campaign_runs)}次上限（{CAMPAIGN_MAX_DAILY_RUNS}次/天），请明天再试'
    # 最小间隔限制
    if _today_campaign_runs:
        last = _today_campaign_runs[-1]
        elapsed = now - last
        if elapsed < CAMPAIGN_MIN_INTERVAL_MINUTES * 60:
            wait_min = int((CAMPAIGN_MIN_INTERVAL_MINUTES * 60 - elapsed) / 60) + 1
            return False, f'距离上次专题采集不足{CAMPAIGN_MIN_INTERVAL_MINUTES}分钟，请等待{wait_min}分钟（保护账号）'
    return True, '频率检查通过'

def _record_campaign_run():
    """记录一次专题采集运行。"""
    global _today_campaign_runs
    _today_campaign_runs.append(time.time())
    _clean_today_runs()

def get_campaign_rate_status():
    """获取专题采集配额状态。"""
    _clean_today_runs()
    now = time.time()
    last_run = _today_campaign_runs[-1] if _today_campaign_runs else None
    cooldown_remaining = 0
    if last_run:
        elapsed = now - last_run
        if elapsed < CAMPAIGN_MIN_INTERVAL_MINUTES * 60:
            cooldown_remaining = int((CAMPAIGN_MIN_INTERVAL_MINUTES * 60 - elapsed) / 60) + 1
    return {
        'today_runs': len(_today_campaign_runs),
        'max_daily_runs': CAMPAIGN_MAX_DAILY_RUNS,
        'remaining_today': max(0, CAMPAIGN_MAX_DAILY_RUNS - len(_today_campaign_runs)),
        'min_interval_minutes': CAMPAIGN_MIN_INTERVAL_MINUTES,
        'cooldown_remaining_minutes': cooldown_remaining,
        'collect_timeout_seconds': CAMPAIGN_COLLECT_TIMEOUT,
        'max_scroll': CAMPAIGN_MAX_SCROLL,
    }

def _campaign_in_window(campaign_key):
    """某监测任务当前是否在其自建时间窗内（按任务 start/end 判断；暂停则不放行）。"""
    if campaign_key == CAMPAIGN_KEY:
        return _campaign_active()
    try:
        db = _db()
        with db.get_db() as conn:
            row = conn.execute(
                'SELECT start_date,end_date,status FROM topic_campaigns WHERE campaign_key=?',
                (campaign_key,)).fetchone()
        if not row:
            return False
        if (row['status'] or 'active') == 'paused':
            return False
        today = datetime.now().strftime('%Y-%m-%d')
        s = (row['start_date'] or today)
        e = (row['end_date'] or '2999-12-31')
        return s <= today <= e
    except Exception:
        return True

def run_campaign(campaign_key=CAMPAIGN_KEY, auto_trigger=False):
    """执行一次专题采集（所有话题）。

    独立配额：不占用主舆情每日12次采集配额，专题自己计数（每日上限8次）。
    与主采集互斥：主采集运行时自动让行。
    绝不伪造数据：采集失败记录错误快照，浏览量/讨论量采不到就存0并标注状态。
    """
    global _last_run
    route = _legacy_campaign_route_status(auto_trigger=auto_trigger)
    if not route.get('ok'):
        return {'ok': False, 'blocked': route.get('code') != 'CANONICAL_COLLECTOR_BINDING_REQUIRED',
                'unavailable': route.get('code') == 'CANONICAL_COLLECTOR_BINDING_REQUIRED',
                'status': route.get('code', 'COLLECTION_BLOCKED'),
                'error': route.get('reason', 'Campaign collection is blocked')}
    if not _campaign_in_window(campaign_key):
        return {'ok': True, 'skipped': True, 'reason': 'outside task window or paused'}
    # 专题独立频率检查
    rate_ok, rate_msg = _check_campaign_rate_limit()
    if not rate_ok:
        return {'ok': False, 'rate_limited': True, 'message': rate_msg}
    _cb = _campaign_circuit_state()
    if _cb:
        return {'ok': False, 'circuit_open': True, 'risk_status': _cb.get('status'),
                'message': f"专题采集熔断中（{_cb.get('status')}）：{_cb.get('reason','')}；NEED_VERIFY 需人工验证后解除，IP_RISK 冷却结束自动半开"}
    if not _lock.acquire(False):
        return {'ok': False, 'busy': True, 'message': '专题采集正在运行'}
    # 与主采集互斥
    if _app_lock is not None and not _app_lock.acquire(False):
        _lock.release()
        return {'ok': False, 'busy': True, 'message': '主舆情采集正在运行，专题任务本轮让行'}
    try:
        init_campaign()
        db = _db()
        results = []
        with db.get_db() as conn:
            topics = [r['topic'] for r in conn.execute(
                "SELECT topic FROM topic_campaign_topics WHERE campaign_key=? AND enabled=1 ORDER BY id",
                (campaign_key,)
            ).fetchall()]
        empty_streak = 0  # 连续“成功但0笔记”计数：疑似平台软降频（不报错、结果暂空）时拉长下一话题间隔
        for idx, topic in enumerate(topics):
            if idx > 0:
                # 拟人随机冷却；连续空结果则指数退避（封顶），保护账号，不硬撞平台频率限制
                gap = random.uniform(CAMPAIGN_TOPIC_GAP_MIN, CAMPAIGN_TOPIC_GAP_MAX) * (2 ** min(empty_streak, 2))
                time.sleep(min(gap, CAMPAIGN_TOPIC_GAP_CAP))
            data = _run_collector(topic)
            if data.get('ok'):
                with db.get_db() as conn:
                    new = _save_notes(conn, campaign_key, topic, data.get('notes', []))
                    data['new_note_count'] = new
                    data['note_count'] = len(data.get('notes', [])) or int(data.get('note_count') or 0)
                    data['engagement_count'] = sum(
                        int((n.get('likes', n.get('liked_count', 0)) or 0))
                        + int((n.get('comments', n.get('comment_count', 0)) or 0))
                        + int((n.get('collects', n.get('collected_count', 0)) or 0))
                        + int((n.get('shares', n.get('share_count', 0)) or 0))
                        for n in data.get('notes', [])
                    )
                    _insert_snapshot(conn, campaign_key, topic, data)
            else:
                # 采集失败：记录真实状态快照，绝不伪造数据、绝不显示成 0 条
                _rs = data.get('risk_status', '')
                _snap_status = 'need_verify' if _rs == 'NEED_VERIFY' else ('blocked' if _rs in ('IP_RISK', 'BLOCKED') else 'error')
                with db.get_db() as conn:
                    _insert_snapshot(conn, campaign_key, topic, data, _snap_status, data.get('error', ''))
            results.append({
                'topic': topic,
                'ok': bool(data.get('ok')),
                'browse_count': data.get('browse_count', 0),
                'discussion_count': data.get('discussion_count', 0),
                'note_count': data.get('note_count', 0),
                'new_note_count': data.get('new_note_count', 0),
                'error': data.get('error', '')
            })
            # 成功出数清零；成功但 0 笔记累计（用于下一话题退避）；失败不累计（失败另有错误快照）
            if data.get('ok') and not data.get('note_count'):
                empty_streak += 1
            elif data.get('ok'):
                empty_streak = 0
            # 命中安全验证/IP 风控：落熔断并立即终止本轮后续话题（停止危险请求，不继续撞击平台）
            if (not data.get('ok')) and data.get('risk_status') in ('NEED_VERIFY', 'IP_RISK', 'BLOCKED'):
                _trip_campaign_circuit(data['risk_status'], data.get('error', ''))
                break
        _last_run = time.time()
        _record_campaign_run()  # 记录一次专题采集运行
        # P0-2 阶段1影子模式：采集完成后回写结果到统一Scheduler，不改变执行
        if _SCHEDULER_AVAILABLE:
            try:
                _planner = get_planner()
                _total_new = sum(int(r.get('new_note_count', 0) or 0) for r in results)
                _total_notes = sum(int(r.get('note_count', 0) or 0) for r in results)
                _has_risk = any((not r.get('ok')) and r.get('error') for r in results)
                _risk_status = ''
                for r in results:
                    if not r.get('ok'):
                        _err = str(r.get('error', ''))
                        if 'NEED_VERIFY' in _err or '验证' in _err:
                            _risk_status = 'NEED_VERIFY'
                            break
                        elif 'IP_RISK' in _err or 'BLOCKED' in _err or '风控' in _err:
                            _risk_status = 'IP_RISK_OR_300012'
                            break
                if _risk_status:
                    _canon = _planner.record_result('xhs', _risk_status, now=datetime.now(),
                                                     items_found=_total_new, xhs_code=_risk_status)
                    print(f'[Shadow][TopicCampaign] 回写风险状态: {_canon}, new_notes={_total_new}')
                elif _total_new > 0:
                    _canon = _planner.record_result('xhs', 'SUCCESS', now=datetime.now(),
                                                     items_found=_total_new)
                    print(f'[Shadow][TopicCampaign] 回写成功: {_canon}, new_notes={_total_new}')
                elif _total_notes > 0:
                    _canon = _planner.record_result('xhs', 'SUCCESS', now=datetime.now(),
                                                     items_found=0)
                    print(f'[Shadow][TopicCampaign] 回写无新数据(有历史): {_canon}')
                else:
                    _canon = _planner.record_result('xhs', 'NO_NEW_DATA', now=datetime.now(),
                                                     items_found=0)
                    print(f'[Shadow][TopicCampaign] 回写无新数据: {_canon}')
            except Exception as _re:
                print(f'[Shadow][TopicCampaign] Scheduler结果回写失败: {_re}')
        return {'ok': True, 'campaign_key': campaign_key, 'captured_at': _now(), 'results': results}
    finally:
        if _app_lock is not None:
            try:
                _app_lock.release()
            except Exception as e: logger.warning("Unhandled exception: %s", e)
        _lock.release()

# ========== 固定时间点调度器（独立线程，独立配额） ==========
def _campaign_scheduler_loop():
    """活动专题固定时间点调度器（中频率，独立配额）。

    时间点：9:00 / 11:00 / 13:00 / 15:00 / 17:00 / 19:00（与主采集完全错峰，间隔约2小时）
    执行窗口：整点后 5-10 分钟（与主系统错峰策略一致）
    独立 daemon 线程，不依赖主 scheduler_loop。
    独立配额：不占用主舆情采集次数，专题自己计数（每日上限8次，含手动）。
    """
    global _scheduler_running, _today_run_hours, _today_date
    _scheduler_running = True
    print(f'[TopicCampaign] 专题调度器启动（中频率独立配额），采集时间点: {CAMPAIGN_COLLECT_HOURS}（错峰5分执行）')

    while True:
        try:
            route = _legacy_campaign_route_status(auto_trigger=True)
            if not route.get('ok'):
                time.sleep(60)
                continue
            now = datetime.now()
            today_str = now.strftime('%Y-%m-%d')

            # 跨天重置
            if _today_date != today_str:
                _today_run_hours = set()
                _today_date = today_str
                print(f'[TopicCampaign] 新的一天 {today_str}，专题采集次数已重置')

            # 活动窗口外不执行
            if not _campaign_active():
                time.sleep(60)
                continue

            # 固定时间点 + 错峰5-10分
            if (now.hour in CAMPAIGN_COLLECT_HOURS
                    and now.hour not in _today_run_hours
                    and 5 <= now.minute < 10):
                print(f'[TopicCampaign] 触发话题监测调度 {now.hour}:05（错峰，独立配额）')
                # GAP-05 影子→门控三态：默认 shadow 不改变固定触发；canary/enforce 且 allow=False 时保守跳过本轮（只收紧、不弱化熔断）
                _gate_run = True
                if _SCHEDULER_AVAILABLE:
                    try:
                        from lumenis.system.collector.adapters.scheduling import gate_should_run
                        _gate_run, _gd, _gmode = gate_should_run(get_planner(), 'xhs', now=now)
                        if _gd is not None:
                            print(f'[Gate:{_gmode}][TopicCampaign] should_run={_gate_run}, allow={_gd.allow}, '
                                  f'reason={_gd.reason_code}, next_run_at={_gd.next_run_at}, risk={_gd.risk_status}')
                    except Exception as _se:
                        print(f'[Gate][TopicCampaign] 门控调用失败，按固定触发继续: {_se}')
                if not _gate_run:
                    print(f'[Gate][TopicCampaign] 本轮被动态调度门控保守跳过（冷却/风险窗），不触发采集；下轮再评估')
                    time.sleep(20)
                    continue
                # 遍历所有启用且在各自监测窗口内的任务（十五周年为内置任务之一）
                _dbx = _db()
                with _dbx.get_db() as _cn:
                    _keys = [r['campaign_key'] for r in _cn.execute(
                        "SELECT campaign_key FROM topic_campaigns WHERE COALESCE(status,'active')='active'").fetchall()]
                _ran = False
                for _ck in _keys:
                    if not _campaign_in_window(_ck):
                        continue
                    _r = run_campaign(_ck, auto_trigger=True)
                    if _r.get('busy'):
                        print(f'[TopicCampaign] 任务 {_ck} 让行（主采集中）')
                        continue
                    _ran = True
                    print(f'[TopicCampaign] 任务 {_ck} ' + ('跳过' if _r.get('skipped') else f"采集 {len(_r.get('results', []))} 话题"))
                if _ran:
                    _today_run_hours.add(now.hour)

        except Exception as e:
            print(f'[TopicCampaign] 调度器错误: {e}')

        time.sleep(20)

def start_scheduler():
    """启动专题调度器（幂等）。"""
    global _scheduler_running
    if os.environ.get('ZBC_TEST_OFFLINE') == '1':
        return False  # 测试隔离：不启动生产采集调度线程（避免测试期真实采集/解释器退出时崩溃）
    if os.environ.get('ZBC_ENV') == 'staging' or os.environ.get('XHS_PRODUCTION', '').lower() in ('false', '0', 'off'):
        print('[TopicCampaign] Staging/no-collect: campaign scheduler thread disabled')
        return False
    route = _legacy_campaign_route_status(auto_trigger=True)
    if not route.get('ok'):
        print(f"[TopicCampaign] Scheduler disabled: {route.get('code')} - {route.get('reason')}")
        return False
    if not _scheduler_running:
        t = threading.Thread(target=_campaign_scheduler_loop, daemon=True, name='topic-campaign-scheduler')
        t.start()
        return True
    return False

# ========== 查询辅助 ==========
def _latest(conn, campaign_key):
    rows = conn.execute(
        "SELECT * FROM topic_campaign_snapshots WHERE campaign_key=? AND id IN (SELECT MAX(id) FROM topic_campaign_snapshots WHERE campaign_key=? GROUP BY topic)",
        (campaign_key, campaign_key)
    ).fetchall()
    return [dict(r) for r in rows]

# ========== Flask 路由注册 ==========
def register_topic_campaign(app, collect_lock=None):
    """注册活动专题监测路由和调度器。

    Args:
        app: Flask 应用实例
        collect_lock: 主采集锁（threading.Lock），用于互斥
    """
    global _app_lock
    _app_lock = collect_lock
    init_campaign()

    # 启动独立调度线程（不依赖主 scheduler_loop）
    start_scheduler()

    @app.route('/topic-campaign')
    def topic_campaign_page():
        return send_from_directory(app.static_folder, 'topic_campaign.html')

    @app.route('/api/topic-campaign/status')
    def topic_status():
        ck = request.args.get('campaign_key', CAMPAIGN_KEY).strip()
        db = _db()
        with db.get_db() as conn:
            campaign_row = conn.execute(
                'SELECT * FROM topic_campaigns WHERE campaign_key=?', (ck,)
            ).fetchone()
            campaign = dict(campaign_row) if campaign_row else {}
            latest = _latest(conn, ck)
            total = conn.execute(
                'SELECT COUNT(*) c FROM topic_campaign_notes WHERE campaign_key=?', (ck,)
            ).fetchone()['c']
        # Report collection availability, not a stale circuit-derived healthy state.
        runtime_state = _probe_runtime_state()
        return jsonify({
            'ok': True,
            'module_version': MODULE_VERSION,
            'campaign': campaign,
            'latest': latest,
            'total_notes': total,
            'active_window': _campaign_active(),
            'scheduler_running': _scheduler_running,
            'collect_hours': CAMPAIGN_COLLECT_HOURS,
            'last_run_at': datetime.fromtimestamp(_last_run).strftime('%Y-%m-%d %H:%M:%S') if _last_run else '',
            'today_run_hours': sorted(list(_today_run_hours)),
            'rate_status': get_campaign_rate_status(),
            'circuit': _campaign_circuit_state(),
            'runtime_state': runtime_state,
        })

    @app.route('/api/topic-campaign/topics')
    def topic_list():
        ck = request.args.get('campaign_key', CAMPAIGN_KEY).strip()
        db = _db()
        with db.get_db() as conn:
            rows = conn.execute(
                'SELECT * FROM topic_campaign_topics WHERE campaign_key=? ORDER BY id', (ck,)
            ).fetchall()
        return jsonify({'ok': True, 'topics': [dict(r) for r in rows]})

    @app.route('/api/topic-campaign/run', methods=['POST'])
    def topic_run():
        route = _legacy_campaign_route_status()
        if not route.get('ok'):
            status_code = 423 if route.get('code') != 'CANONICAL_COLLECTOR_BINDING_REQUIRED' else 503
            return jsonify({'ok': False, 'blocked': status_code == 423,
                            'status': route.get('code'), 'error': route.get('reason')}), status_code
        d = request.get_json(silent=True) or {}
        ck = (d.get('campaign_key') or request.args.get('campaign_key') or CAMPAIGN_KEY).strip()
        if not _campaign_in_window(ck):
            return jsonify({'ok': False, 'error': '该任务不在监测时间窗内或已暂停（可在任务里调整起止日期）'}), 400
        _cb0 = _campaign_circuit_state()
        if _cb0:
            return jsonify({'ok': False, 'circuit_open': True, 'risk_status': _cb0.get('status'),
                            'error': f"专题采集熔断中（{_cb0.get('status')}）：{_cb0.get('reason','')}。NEED_VERIFY 请在已登录浏览器完成扫码验证后解除；IP_RISK 冷却结束自动半开。"}), 423
        if not _lock.acquire(False):
            return jsonify({'ok': False, 'busy': True, 'error': '上一轮专题采集仍在运行，请稍后'}), 429
        _lock.release()
        threading.Thread(target=run_campaign, args=(ck,), daemon=True, name='topic-campaign-manual').start()
        return jsonify({'ok': True, 'campaign_key': ck, 'message': '话题监测任务已启动，可在页面实时查看状态'})

    @app.route('/api/topic-campaign/recover', methods=['POST'])
    def topic_recover():
        route = _legacy_campaign_route_status()
        if not route.get('ok'):
            status_code = 423 if route.get('code') != 'CANONICAL_COLLECTOR_BINDING_REQUIRED' else 503
            return jsonify({'ok': False, 'recovered': False, 'blocked': status_code == 423,
                            'status': route.get('code'), 'error': route.get('reason'),
                            'runtime_state': _probe_runtime_state()}), status_code
        # V2.0 P0-2/P0-4：人工完成扫码/验证后调用，做完整探活（explore + 搜索测试），通过才解除熔断
        # 注意：不调用 _probe_runtime_state()，因为它在熔断 OPEN 时会跳过实时探活
        healthy, detail = _probe_xhs_health_via_cdp(test_search=True)
        # 构建六态返回
        if _RUNTIME_STATE_AVAILABLE:
            state = state_from_circuit(_CAMPAIGN_CIRCUIT)
            state.set_health_probe_result(healthy, {'health_detail': detail, 'search_test': True})
            sd = state.to_dict()
        else:
            cb = _campaign_circuit_state()
            sd = {
                'overall': 'healthy' if healthy else ('circuit_open' if cb else 'unhealthy'),
                'healthy': healthy,
                'auth_state': 'valid' if healthy else 'required',
                'session_state': 'real_session_valid' if healthy else 'browser_disconnected',
                'platform_state': 'reachable' if healthy else 'unreachable',
                'collector_state': 'idle',
                'circuit_state': 'open' if cb else 'closed',
                'recovery_state': 'idle',
                'last_check': _now(),
                'circuit': cb,
                'detail': {'health_detail': detail},
            }
        if healthy:
            clear_campaign_circuit()
            sd['recovered'] = True
            sd['message'] = 'explore + 搜索均正常，已解除熔断，可恢复采集和详情补抓'
            return jsonify({'ok': True, **sd})
        sd['recovered'] = False
        sd['message'] = detail or '尚未通过健康检查，保持熔断'
        return jsonify({'ok': False, **sd}), 423

    @app.route('/api/topic-campaign/runtime-state')
    def topic_runtime_state():
        """V2.0 P0-1：返回统一六态运行时状态（前端全局健康小点/Auth Modal 共用）。"""
        state = _probe_runtime_state()
        if isinstance(state, XhsRuntimeState) if _RUNTIME_STATE_AVAILABLE else False:
            return jsonify({'ok': True, **state.to_dict()})
        return jsonify({'ok': True, **state})

    @app.route('/api/topic-campaign/half-open-probe', methods=['POST'])
    def topic_half_open_probe():
        """V2.0 P0-3：IP_RISK 冷却结束后的半开探测（小流量单话题验证，成功才完全解除）。"""
        success, detail = _half_open_probe()
        state = _probe_runtime_state()
        if isinstance(state, XhsRuntimeState) if _RUNTIME_STATE_AVAILABLE else False:
            sd = state.to_dict()
        else:
            sd = state
        return jsonify({'ok': success, 'half_open_success': success, 'detail': detail, **sd})

    @app.route('/api/topic-campaign/note/<note_id>')
    def topic_note_detail(note_id):
        """V2.0 P0-7：获取单条笔记完整详情（正文/媒体/评论/主体/分类/情绪/风险），用于 Note Detail 下钻。"""
        ck = request.args.get('campaign_key', CAMPAIGN_KEY).strip()
        db = _db()
        with db.get_db() as conn:
            row = conn.execute(
                'SELECT * FROM topic_campaign_notes WHERE campaign_key=? AND note_id=?',
                (ck, note_id)
            ).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': '笔记不存在'}), 404
        d = dict(row)
        # 解析 media_json 和 comments_json
        try:
            d['media'] = json.loads(d.get('media_json') or '[]')
        except Exception:
            d['media'] = []
        try:
            d['comments'] = json.loads(d.get('comments_json') or '[]')
        except Exception:
            d['comments'] = []
        return jsonify({'ok': True, 'note': d})

    @app.route('/api/topic-campaign/backfill-detail', methods=['POST'])
    def topic_backfill_detail():
        """Return an honest unavailable state until detail collection has an HK owner."""
        route = _legacy_campaign_route_status()
        status_code = 423 if route.get('code') != 'CANONICAL_COLLECTOR_BINDING_REQUIRED' else 503
        return jsonify({'ok': False, 'blocked': status_code == 423,
                        'status': route.get('code'), 'error': route.get('reason')}), status_code

    @app.route('/api/topic-campaign/timeline')
    def topic_timeline():
        topic = request.args.get('topic', '').strip()
        ck = request.args.get('campaign_key', CAMPAIGN_KEY).strip()
        limit = min(1000, max(10, int(request.args.get('limit', 300))))
        db = _db()
        with db.get_db() as conn:
            q = 'SELECT * FROM topic_campaign_snapshots WHERE campaign_key=?'
            p = [ck]
            if topic:
                q += ' AND topic=?'
                p.append(topic)
            q += ' ORDER BY captured_at ASC LIMIT ?'
            p.append(limit)
            rows = [dict(r) for r in conn.execute(q, tuple(p)).fetchall()]
        return jsonify({'ok': True, 'snapshots': rows})

    @app.route('/api/topic-campaign/stats')
    def topic_stats():
        """V2.0 P0-8：话题聚合统计（Unique/New/Runs口径统一）。
        SQLite兼容版：使用CASE WHEN替代FILTER语法。
        """
        ck = request.args.get('campaign_key', CAMPAIGN_KEY).strip()
        db = _db()
        with db.get_db() as conn:
            # 按话题聚合（SQLite兼容语法）
            topic_stats = conn.execute("""
                SELECT
                    n.topic,
                    COUNT(DISTINCT n.note_id) AS unique_notes,
                    COUNT(DISTINCT CASE WHEN n.first_seen_at >= datetime('now','-24 hours') THEN n.note_id END) AS new_notes
                FROM topic_campaign_notes n
                WHERE n.campaign_key=?
                GROUP BY n.topic
                ORDER BY unique_notes DESC
            """, (ck,)).fetchall()

            # Runs次数（按话题统计快照数）
            runs_by_topic = dict(conn.execute("""
                SELECT topic, COUNT(*) AS runs FROM topic_campaign_snapshots
                WHERE campaign_key=? AND status='success' GROUP BY topic
            """, (ck,)).fetchall())

            # 全局汇总
            total = conn.execute("""
                SELECT
                    COUNT(DISTINCT note_id) AS total_unique,
                    COUNT(DISTINCT CASE WHEN first_seen_at >= datetime('now','-24 hours') THEN note_id END) AS total_new
                FROM topic_campaign_notes WHERE campaign_key=?
            """, (ck,)).fetchone()

            total_runs = conn.execute(
                "SELECT COUNT(*) FROM topic_campaign_snapshots WHERE campaign_key=? AND status='success'",
                (ck,)
            ).fetchone()[0]

        topics = []
        for ts in topic_stats:
            t = dict(ts)
            t['runs'] = runs_by_topic.get(t['topic'], 0)
            topics.append(t)

        return jsonify({
            'ok': True,
            'campaign_key': ck,
            'total': {
                'unique_notes': total['total_unique'] or 0,
                'new_notes_24h': total['total_new'] or 0,
                'runs': total_runs,
            },
            'by_topic': topics,
            'content_type_dist': [],
            'sentiment_dist': [],
            'note': '当前topic_campaign_notes表为精简结构，subject_hit/risk/evidence等字段待迁移补齐',
        })


    @app.route('/api/topic-campaign/notes')
    def topic_notes():
        topic = request.args.get('topic', '').strip()
        ck = request.args.get('campaign_key', CAMPAIGN_KEY).strip()
        limit = min(1000, max(10, int(request.args.get('limit', 200))))
        db = _db()
        with db.get_db() as conn:
            q = 'SELECT * FROM topic_campaign_notes WHERE campaign_key=?'
            p = [ck]
            if topic:
                q += ' AND topic=?'
                p.append(topic)
            q += ' ORDER BY last_seen_at DESC LIMIT ?'
            p.append(limit)
            rows = [dict(r) for r in conn.execute(q, tuple(p)).fetchall()]
        return jsonify({'ok': True, 'notes': rows})

    @app.route('/api/topic-campaign/export')
    def topic_export():
        topic = request.args.get('topic', '').strip()
        ck = request.args.get('campaign_key', CAMPAIGN_KEY).strip()
        db = _db()
        with db.get_db() as conn:
            q = ('SELECT topic,note_id,title,author,publish_datetime,likes,comments,collects,shares,note_url,first_seen_at,last_seen_at '
                 'FROM topic_campaign_notes WHERE campaign_key=?')
            p = [ck]
            if topic:
                q += ' AND topic=?'
                p.append(topic)
            q += ' ORDER BY publish_datetime DESC,last_seen_at DESC'
            rows = conn.execute(q, tuple(p)).fetchall()
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(['话题', '笔记ID', '标题', '作者', '发布日期', '点赞', '评论', '收藏', '分享', '笔记链接', '首次发现', '最近发现'])
        w.writerows([tuple(r) for r in rows])
        return Response(
            '\ufeff' + out.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=taikoo_15th_topic_notes.csv'}
        )

    # ===== 话题监测端口：多任务管理（v5.8.5 泛化，十五周年为内置任务之一）=====
    @app.route('/api/topic-campaign/campaigns')
    def tc_campaign_list():
        db = _db()
        with db.get_db() as conn:
            cams = [dict(r) for r in conn.execute('SELECT * FROM topic_campaigns ORDER BY id DESC').fetchall()]
            for cm in cams:
                ck = cm['campaign_key']
                cm['topic_count'] = conn.execute('SELECT COUNT(*) n FROM topic_campaign_topics WHERE campaign_key=? AND enabled=1', (ck,)).fetchone()['n']
                cm['note_count'] = conn.execute('SELECT COUNT(*) n FROM topic_campaign_notes WHERE campaign_key=?', (ck,)).fetchone()['n']
                cm['snapshot_count'] = conn.execute('SELECT COUNT(*) n FROM topic_campaign_snapshots WHERE campaign_key=?', (ck,)).fetchone()['n']
                agg = conn.execute("""SELECT COALESCE(SUM(note_count),0) notes,COALESCE(SUM(new_note_count),0) new,
                    COALESCE(SUM(engagement_count),0) eng,COALESCE(SUM(discussion_count),0) dis,MAX(captured_at) last
                    FROM topic_campaign_snapshots WHERE campaign_key=? AND status='success'""", (ck,)).fetchone()
                cm['agg'] = dict(agg) if agg else {}
                cm['in_window'] = _campaign_in_window(ck)
        return jsonify({'ok': True, 'campaigns': cams})

    @app.route('/api/topic-campaign/campaign-save', methods=['POST'])
    def tc_campaign_save():
        import re, hashlib
        d = request.get_json(silent=True) or {}
        name = (d.get('name') or '').strip()
        if not name:
            return jsonify({'ok': False, 'error': '任务名称不能为空'}), 400
        start = (d.get('start_date') or datetime.now().strftime('%Y-%m-%d')).strip()
        end = (d.get('end_date') or '2999-12-31').strip()
        try:
            interval = int(d.get('interval_minutes') or 240)
        except Exception:
            interval = 240
        topics = d.get('topics') or []
        if isinstance(topics, str):
            topics = re.split('[;\n,，；]', topics)
        topics = [str(t).strip() for t in topics if str(t).strip()]
        if not topics:
            topics = [name]
        ck = (d.get('campaign_key') or '').strip()
        db = _db()
        with db.get_db() as conn:
            if ck and conn.execute('SELECT 1 FROM topic_campaigns WHERE campaign_key=?', (ck,)).fetchone():
                conn.execute("""UPDATE topic_campaigns SET name=?,start_date=?,end_date=?,interval_minutes=?,
                    updated_at=datetime('now','localtime') WHERE campaign_key=?""", (name, start, end, interval, ck))
                action = 'updated'
            else:
                ck = ck or None
                if not ck:
                    slug = re.sub(r'[^a-zA-Z0-9]', '', name)
                    base = ('t_' + slug[:14]) if slug else ('topic_' + hashlib.md5(name.encode('utf-8')).hexdigest()[:8])
                    ck = base; i = 1
                    while conn.execute('SELECT 1 FROM topic_campaigns WHERE campaign_key=?', (ck,)).fetchone():
                        i += 1; ck = f'{base}_{i}'
                conn.execute("""INSERT INTO topic_campaigns(campaign_key,name,start_date,end_date,interval_minutes,status)
                    VALUES(?,?,?,?,?,'active')""", (ck, name, start, end, interval))
                action = 'created'
            conn.execute('DELETE FROM topic_campaign_topics WHERE campaign_key=?', (ck,))
            for t in topics:
                conn.execute('INSERT INTO topic_campaign_topics(campaign_key,topic,normalized_topic,enabled) VALUES(?,?,?,1)',
                             (ck, t, _norm(t)))
        return jsonify({'ok': True, 'action': action, 'campaign_key': ck, 'topic_count': len(topics)})

    @app.route('/api/topic-campaign/campaign-toggle', methods=['POST'])
    def tc_campaign_toggle():
        d = request.get_json(silent=True) or {}
        ck = (d.get('campaign_key') or '').strip()
        status = (d.get('status') or 'active').strip()
        if not ck:
            return jsonify({'ok': False, 'error': '缺少 campaign_key'}), 400
        db = _db()
        with db.get_db() as conn:
            conn.execute("UPDATE topic_campaigns SET status=?,updated_at=datetime('now','localtime') WHERE campaign_key=?",
                         (status, ck))
        return jsonify({'ok': True, 'campaign_key': ck, 'status': status})

    print('[TopicCampaign] 话题监测端口模块已注册（多任务 + 固定时间点调度，独立线程）')



# ===== 话题APP端采集集成 =====
def _app_topic_collect(topic_keyword, max_notes=20):
    """通过小红书APP端采集话题笔记（与Web端互补，APP端数据更全）。"""
    route = _legacy_campaign_route_status()
    if not route.get('ok'):
        return {'enabled': False, 'status': route.get('code'),
                'reason': route.get('reason', 'APP topic collection is blocked')}
    if not APP_TOPIC_ENABLED or XHSAppTopicAdapter is None:
        return {'enabled': False, 'reason': 'APP采集adapter未启用'}
    try:
        adapter = XHSAppTopicAdapter(cdp_port=route['identity']['cdp_port'])
        if not adapter.is_enabled():
            return {'enabled': False, 'reason': 'APP采集未启用（检查配置）'}
        result = adapter.search(topic_keyword, max_results=max_notes)
        return {'enabled': True, 'data': result, 'source': 'xhs_app'}
    except Exception as e:
        return {'enabled': False, 'reason': f'APP采集异常: {e}'}

def _merge_app_and_web_notes(web_notes, app_notes):
    """合并Web端和APP端采集的笔记（按note_id去重）。"""
    merged = {}
    for note in web_notes or []:
        nid = note.get('note_id') or note.get('id') or str(note)
        if nid:
            merged[nid] = {**note, '_source': 'web'}
    for note in app_notes or []:
        nid = note.get('note_id') or note.get('id') or str(note)
        if nid and nid not in merged:
            merged[nid] = {**note, '_source': 'xhs_app'}
    return list(merged.values())
