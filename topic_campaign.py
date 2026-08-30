"""v5.7.3 活动专题监测能力（适配广州太古汇 v5.7.0 系统）。

适配要点：
1. 固定时间点调度（中频率：9/11/13/15/17/19点，错峰5-10分），与主舆情采集时间点完全不重叠
2. 独立 daemon 调度线程，不依赖已禁用的主 scheduler_loop
3. 独立采集配额：不占用主舆情每日12次配额，专题自己计数（每日上限8次，含手动）
4. 单次采集最长50分钟，充分滚动加载，保证数据完整
5. 复用 _collect_lock 互斥，主采集运行时专题自动让行
6. 7个话题完整覆盖（含 #拾光五境、#广州太古汇15周年促销）
7. 独立4张表，不污染主舆情库，不修改主体过滤逻辑
8. 活动窗口（2026-08-28 ~ 2026-10-07）外自动停止
9. 绝不伪造数据：采集失败记录错误快照，浏览量/讨论量采不到就存0并标注状态
"""
import os, json, threading, subprocess, time, csv, io, sys, random
from datetime import datetime
from flask import jsonify, request, send_from_directory, Response

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
MODULE_VERSION = '5.7.3-adapted-v2'
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

def _save_notes(conn, campaign_key, topic, notes):
    now = _now()
    new = 0
    for n in notes or []:
        nid = str(n.get('note_id') or n.get('id') or '').strip()
        if not nid:
            continue
        cur = conn.execute(
            "SELECT id FROM topic_campaign_notes WHERE campaign_key=? AND topic=? AND note_id=?",
            (campaign_key, topic, nid)
        ).fetchone()
        vals = (
            n.get('title', ''),
            n.get('content', n.get('desc', '')),
            n.get('author', n.get('nickname', '')),
            n.get('publish_datetime', n.get('publish_time', '')),
            int(n.get('likes', n.get('liked_count', 0)) or 0),
            int(n.get('comments', n.get('comment_count', 0)) or 0),
            int(n.get('collects', n.get('collected_count', 0)) or 0),
            int(n.get('shares', n.get('share_count', 0)) or 0),
            n.get('note_url', n.get('url', '')) or '',
            now,
            json.dumps(n, ensure_ascii=False)[:100000]
        )
        if cur:
            conn.execute(
                """UPDATE topic_campaign_notes SET title=?,content=?,author=?,publish_datetime=?,likes=?,comments=?,collects=?,shares=?,note_url=?,last_seen_at=?,raw_json=? WHERE id=?""",
                vals + (cur['id'],)
            )
        else:
            # INSERT 含 first_seen_at/last_seen_at 两个时间列，新笔记两者都取 now；
            # vals = [title..note_url 共9项, last_seen_at(now), raw_json]，故在 note_url 后补一个 now 作为 first_seen_at
            conn.execute(
                """INSERT INTO topic_campaign_notes(campaign_key,topic,note_id,title,content,author,publish_datetime,likes,comments,collects,shares,note_url,first_seen_at,last_seen_at,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (campaign_key, topic, nid) + vals[:9] + (now, now) + vals[10:]
            )
            new += 1
    return new

def _run_collector(topic):
    """调用 Node.js 采集脚本获取话题数据（独立配额，单次最长50分钟）。

    优先使用 CDP 连接已登录浏览器；若未配置 CDP 则使用持久化 profile 启动 Playwright。
    绝不伪造数据：采集失败返回错误信息，由调用方记录错误快照。
    """
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xhs_campaign_monitor.js')
    if not os.path.exists(script):
        return {'ok': False, 'error': f'采集脚本不存在: {script}', 'topic': topic}

    # 默认连 9222 已登录采集浏览器（app 主进程自身未必注入该 env，这里补缺省，避免误走 headless 未登录 profile）；
    # 仍可用 XHS_CDP_URL 环境变量覆盖
    cdp = (os.getenv('XHS_CDP_URL', '') or 'http://127.0.0.1:9222').strip()
    profile_dir = os.getenv('XHS_PROFILE_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'taikoo_browser_profile'))

    # 中频率充分采集：滚动6次，单次最长50分钟
    cmd = ['node', script, '--topic', topic, '--max-scroll', str(CAMPAIGN_MAX_SCROLL)]
    if cdp:
        cmd.extend(['--cdp', cdp])
    elif os.path.isdir(profile_dir):
        cmd.extend(['--profile', profile_dir])

    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=CAMPAIGN_COLLECT_TIMEOUT
        )
        out = (p.stdout or '').strip()
        idx = out.find('{')
        data = json.loads(out[idx:]) if idx >= 0 else {}
        if p.returncode != 0:
            if data.get('risk_status'):
                # node 风控退出码（3=NEED_VERIFY / 4=IP_RISK）：结构化状态已在 stdout，保留 risk_status，不用整段输出覆盖
                data['ok'] = False
                data.setdefault('topic', topic)
            else:
                data.update(ok=False, error=(p.stderr or out)[-1500:])
        return data
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': f'专题采集超时（{CAMPAIGN_COLLECT_TIMEOUT}秒）', 'topic': topic}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'topic': topic}

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
    except Exception:
        pass

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
    except Exception:
        pass

def _probe_xhs_health_via_cdp():
    """连 9222 已登录浏览器做一次轻量健康探活：访问 explore，判断是否仍被重定向到 captcha/登录页。
    返回 (healthy:bool, detail:str)。绝不绕过验证——只有真实会话正常才判定健康。"""
    page = None
    try:
        try:
            from cdp_helper import reset_cdp_targets
            from urllib.parse import urlparse
            _u = (os.getenv('XHS_CDP_URL', '') or 'http://127.0.0.1:9222')
            try: reset_cdp_targets(urlparse(_u).port or 9222, timeout=6)
            except Exception: pass
        except Exception:
            _u = os.getenv('XHS_CDP_URL', '') or 'http://127.0.0.1:9222'
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(_u, timeout=15000)
            ctx = browser.contexts[0]
            page = ctx.new_page()
            page.goto('https://www.xiaohongshu.com/explore', wait_until='domcontentloaded', timeout=15000)
            page.wait_for_timeout(2500)
            u = page.url() or ''
            body = ''
            try: body = page.evaluate("() => document.body ? document.body.innerText.slice(0,600) : ''") or ''
            except Exception: pass
            try: page.goto('about:blank', timeout=4000)
            except Exception: pass
            try: browser.close()
            except Exception: pass
        bad_url = ('captcha' in u) or ('/website-login' in u) or ('/login' in u)
        bad_txt = any(k in body for k in ('扫码验证', '安全验证', '拖动滑块', '完成验证', '人机验证', '验证码'))
        if bad_url or bad_txt:
            return False, '仍停留在登录/安全验证页，请在已登录浏览器完成扫码验证后再检测'
        return True, '会话正常（explore 未跳验证页）'
    except Exception as e:
        try:
            if page: page.goto('about:blank', timeout=3000)
        except Exception: pass
        return False, f'健康探活失败：{str(e)[:120]}'

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

def run_campaign(campaign_key=CAMPAIGN_KEY):
    """执行一次专题采集（所有话题）。

    独立配额：不占用主舆情每日12次采集配额，专题自己计数（每日上限8次）。
    与主采集互斥：主采集运行时自动让行。
    绝不伪造数据：采集失败记录错误快照，浏览量/讨论量采不到就存0并标注状态。
    """
    global _last_run
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
        return {'ok': True, 'campaign_key': campaign_key, 'captured_at': _now(), 'results': results}
    finally:
        if _app_lock is not None:
            try:
                _app_lock.release()
            except Exception:
                pass
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
                # 遍历所有启用且在各自监测窗口内的任务（十五周年为内置任务之一）
                _dbx = _db()
                with _dbx.get_db() as _cn:
                    _keys = [r['campaign_key'] for r in _cn.execute(
                        "SELECT campaign_key FROM topic_campaigns WHERE COALESCE(status,'active')='active'").fetchall()]
                _ran = False
                for _ck in _keys:
                    if not _campaign_in_window(_ck):
                        continue
                    _r = run_campaign(_ck)
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
        # 人工在已登录浏览器完成扫码/验证后调用：先做真实健康探活，通过才解除熔断（不绕过任何平台验证）
        healthy, detail = _probe_xhs_health_via_cdp()
        if healthy:
            clear_campaign_circuit()
            return jsonify({'ok': True, 'recovered': True, 'message': '健康检查通过，已解除熔断，可恢复采集', 'detail': detail})
        return jsonify({'ok': False, 'recovered': False, 'message': '尚未通过健康检查，保持熔断', 'detail': detail}), 423

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
