"""广州太古汇 v5.3.2：受控运行时 Cookie 小红书数据桥。

职责：
1. 使用受控运行时 Cookie/隔离 Playwright profile 搜索小红书；
2. 只把搜索结果标准化后交给现有 database.insert_note；
3. 继续调用现有 ai_analyzer / reprocess，保持 v5.3.1 业务链；
4. source_id 使用 note_id，xsec_token 原样存入 notes，保证真实详情链接可更新；
5. Cookie 只从本机读取，不进入源码、日志、JSON 数据快照。
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

import ai_analyzer
import cache_manager
import database as db
import network_adaptive

ROOT=os.path.dirname(os.path.abspath(__file__))


def _resolve_runtime_data_dir(root: str | None = None, environ=None) -> str:
    """Resolve the shared local data root used by the running production instance.

    Production keeps the SQLite database and credential assets outside the source
    checkout.  The bridge must follow the same path contract as the rest of the
    runtime instead of silently falling back to ``<repo>/data``.  ``ZBC_DATA_DIR``
    is authoritative; when it is not set, the parent of ``ZBC_DB_PATH`` is the
    existing local data root.  The repository ``data`` directory remains the
    development fallback for isolated tests and fresh checkouts.
    """
    env = os.environ if environ is None else environ
    base = os.path.abspath(root or os.path.dirname(os.path.abspath(__file__)))

    configured = str(env.get('ZBC_DATA_DIR') or '').strip()
    if configured:
        return os.path.abspath(configured)

    db_path = str(env.get('ZBC_DB_PATH') or '').strip()
    if db_path:
        # Accept the SQLite URL form used by Alembic as well as the plain
        # filesystem path used by the production launcher.
        if db_path.startswith('sqlite:///'):
            db_path = db_path[len('sqlite:///'):]
        elif db_path.startswith('file:'):
            db_path = db_path[len('file:'):].split('?', 1)[0]
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            return parent

    return os.path.join(base, 'data')


DATA_DIR = _resolve_runtime_data_dir()
PRIVATE_DATA_DIR = os.path.join(DATA_DIR, 'private')
# 统一 Node 解析（PATH 优先，项目内置 nodejs/ 兜底），避免常驻进程 PATH 缺 node 抛 WinError 2
try:
    from runtime_bin import resolve_node as _resolve_node
    _NODE_BIN=_resolve_node() or 'node'
except Exception:
    _NODE_BIN='node'
SEARCH_JS=os.path.join(ROOT,'xhs_cookie_search.js')
COOKIE_FILE=os.path.abspath(
    os.environ.get('XHS_COOKIE_FILE') or os.path.join(PRIVATE_DATA_DIR, 'xhs_cookie_header.txt')
)
STATS_FILE=os.path.join(DATA_DIR,'collector_stats.json')  # 采集计数持久化文件
# Legacy fallback keywords are non-authoritative. The canonical registry owns
# acquisition identity and query planning.
DEFAULT_KEYWORDS = None

# ========== 账号安全保护机制（双子星库 Contract：双身份硬白名单） ==========
# 逻辑身份常量（Contract 入口：Z-Brand Core 所有采集仅接受下面两个身份名）
XHS_CN_PRIMARY_NAME = "XHS_CN_PRIMARY"   # 主账号：日常采集/驻场
XHS_RETINAUT_NAME  = "XHS_RETINAUT"      # Retinaut 账号：备用身份/隔离采集
DEFAULT_COLLECTION_ACCOUNT = XHS_RETINAUT_NAME
# 物理 user_id 白名单（与逻辑身份一一绑定）
XHS_CN_PRIMARY = "61d58d560000000010005a8a"   # 现有主账号（100% 向后兼容原 ALLOWED_USER_ID）
XHS_RETINAUT  = "6a3cef27000000000e03b800"          # Retinaut 香港 rednote 账号真实 user_id（来自个人主页 URL，24位）
ALLOWED_USER_IDS = tuple(x for x in (XHS_CN_PRIMARY, XHS_RETINAUT) if x)
# 向后兼容别名：防止其它 import ALLOWED_USER_ID 的代码失效
ALLOWED_USER_ID = XHS_CN_PRIMARY  # LEGACY ALIAS（只读）
# 逻辑身份 → 物理配置（Cookie 文件 + CDP Profile 目录）
ACCOUNT_PROFILES = {
    XHS_CN_PRIMARY_NAME: (
        COOKIE_FILE,  # 原主 Cookie：data/private/xhs_cookie_header.txt
        os.path.join(PRIVATE_DATA_DIR, "profiles", "xhs-cn-primary"),
    ),
    XHS_RETINAUT_NAME: (
        os.path.join(PRIVATE_DATA_DIR, "xhs_cookie_retinaut.txt"),
        os.path.join(PRIVATE_DATA_DIR, "profiles", "xhs-retinaut"),
    ),
}

# ── 身份到受控浏览器会话解析；身份策略不再编码固定 CDP 端口。 ──
ACCOUNT_CDP_PORTS = {
    XHS_CN_PRIMARY_NAME: None,
    XHS_RETINAUT_NAME: None,
}
DEFAULT_CDP_PORT = 0

ACCOUNT_HOME_URLS = {
    XHS_CN_PRIMARY_NAME: 'https://www.xiaohongshu.com',
    XHS_RETINAUT_NAME: 'https://www.rednote.com',
}

def _canonical_account_name(account=None):
    """default/None/空 → 当前生产采集默认的香港/国际身份。"""
    if account in (None, '', 'default'):
        return _ACTIVE_ACCOUNT or XHS_RETINAUT_NAME
    return account

def cdp_port_for(account=None, *, headless=True):
    """Return the registered XHS worker port; collection defaults to BACKGROUND."""
    selected = _canonical_account_name(account)
    if selected != XHS_RETINAUT_NAME or not collection_policy_gate(
            account=selected, region="intl").get("ok"):
        return None
    try:
        import cdp_helper
        state = cdp_helper.resolve_registered_xhs_worker(
            account=selected, headless=headless)
        return int(state["port"]) if state.get("available") else None
    except Exception:  # noqa: BLE001 - owner lookup failure must not resolve to a legacy port.
        return None

def cdp_url_for(account=None, *, headless=True):
    """Resolve a registered endpoint; unattended collection defaults to BACKGROUND."""
    selected = _canonical_account_name(account)
    if selected != XHS_RETINAUT_NAME or not collection_policy_gate(
            account=selected, region="intl").get("ok"):
        return ""
    try:
        import cdp_helper
        state = cdp_helper.resolve_registered_xhs_worker(
            account=selected, headless=headless)
        return str(state.get("endpoint") or "") if state.get("available") else ""
    except Exception:  # noqa: BLE001 - owner lookup failure must not resolve to a legacy endpoint.
        return ""

def home_url_for(account=None):
    """逻辑身份 → 平台首页（驻场窗口起始页 / CDP 热身页）。"""
    return ACCOUNT_HOME_URLS.get(_canonical_account_name(account), ACCOUNT_HOME_URLS[XHS_RETINAUT_NAME])


def collection_policy_gate(account=None, region='intl'):
    """统一生产采集门禁；只判定，不读取 Cookie 内容、不连平台、不启动浏览器。"""
    from lumenis.system.collector.adapters import rednote_policy
    requested = account
    if requested in (None, '', 'default'):
        requested = rednote_policy.DEFAULT_COLLECTION_ACCOUNT
    return rednote_policy.collection_gate(account=requested, region=region)



_TAIKOO_MARKERS = ('广州太古汇', 'taikoo hui guangzhou', 'guangzhou taikoo hui')


def _verify_note_for_query(note, query):
    """Verify a note against the registered Subject that produced its keyword.

    Taikoo Hui keeps its location verifier; any other registered subject is
    verified by its own registered alias appearing in the note text.
    """
    title = note.get('title', '') or ''
    content = note.get('content', '') or ''
    keyword = str(getattr(query, 'keyword', '') or note.get('source_keyword') or '')
    if any(m in keyword.lower() for m in _TAIKOO_MARKERS):
        return ai_analyzer.verify_taikoo_location(title, content)
    if not keyword:
        return False, 'no registered subject for note'
    text = f"{title}\n{content}".lower()
    if keyword.lower() in text:
        return True, f'registered alias matched: {keyword}'
    return False, f'registered alias not in note: {keyword}'


def _canonical_query_scope(query):
    """Return only the scope admitted by the server-side acquisition plan."""
    raw_scope = getattr(query, 'scope', None)
    scope = dict(raw_scope) if isinstance(raw_scope, dict) else {}
    scope['product_id'] = str(getattr(query, 'product_id', '') or '').strip().upper()
    return scope


def _is_exact_analysis_scope(scope):
    if not isinstance(scope, dict) or scope.get('global_scope') is not False:
        return False
    domain = str(scope.get('domain_id') or '').strip().lower()
    product = str(scope.get('product_id') or '').strip().upper()
    subject_id = str(scope.get('subject_id') or '').strip()
    brand_focus_id = str(scope.get('brand_focus_id') or '').strip()
    return ((domain == 'cth' and product == 'CTH' and bool(subject_id) and not brand_focus_id)
            or (domain == 'zbmp' and product == 'ZBMP' and bool(brand_focus_id) and not subject_id))


def _scope_key(scope):
    if not _is_exact_analysis_scope(scope):
        return None
    return (str(scope['product_id']).upper(), str(scope['domain_id']).lower(),
            str(scope.get('subject_id') or ''), str(scope.get('brand_focus_id') or ''))


def _scoped_query_groups(queries):
    """Group admitted queries by exact business focus, never by query text."""
    groups = {}
    skipped = 0
    for query in queries or ():
        scope = _canonical_query_scope(query)
        key = _scope_key(scope)
        keyword = str(getattr(query, 'keyword', '') or '').strip()
        if key is None or not keyword:
            skipped += 1
            continue
        group = groups.setdefault(key, {'scope': scope, 'keywords': []})
        if keyword not in group['keywords']:
            group['keywords'].append(keyword)
    return groups, skipped


def _load_scoped_pending_analysis(query_plan, *, database_module=None, limit=20):
    """Read a bounded pending-analysis batch separately for each exact scope."""
    database_module = database_module or db
    groups, skipped = _scoped_query_groups(getattr(query_plan, 'queries', ()))
    per_scope_rows = []
    read_failures = []
    for key, group in groups.items():
        scope = group['scope']
        keywords = group['keywords']
        placeholders = ','.join('?' for _ in keywords)
        sql = (
            "SELECT * FROM notes WHERE is_taikoo_verified=1 AND scope_status='VERIFIED' "
            "AND product_id=? AND domain_id=? "
            "AND COALESCE(subject_id,'')=? AND COALESCE(brand_focus_id,'')=? "
            f"AND source_keyword IN ({placeholders}) "
            "AND (ai_analyzed_at='' OR ai_analyzed_at IS NULL) "
            "ORDER BY id DESC LIMIT ?"
        )
        params = (
            scope['product_id'], scope['domain_id'], scope.get('subject_id') or '',
            scope.get('brand_focus_id') or '', *keywords, max(1, int(limit)),
        )
        try:
            with database_module.get_db() as conn:
                rows = conn.execute(sql, params).fetchall()
        except Exception as exc:  # noqa: BLE001 - continue other exact scopes when one read fails.
            read_failures.append((key, type(exc).__name__))
            continue
        per_scope_rows.extend((key, scope, row) for row in rows)

    def _row_id(item):
        row = item[2]
        try:
            return int(row['id'])
        except (KeyError, TypeError, ValueError, IndexError):
            return -1

    # Keep the legacy total work bound while letting every scope compete for
    # the newest records instead of allowing the first scope to consume it all.
    per_scope_rows.sort(key=lambda item: (_row_id(item), item[0]), reverse=True)
    selected = per_scope_rows[:max(1, int(limit))]
    rows_by_scope = {}
    for key, scope, row in selected:
        rows_by_scope.setdefault(key, (scope, []))[1].append(row)
    return groups, rows_by_scope, skipped, read_failures


def _run_scoped_postprocess(rows_by_scope, scopes, reprocess_module, results):
    """Isolate analysis and event aggregation failures to their own scope."""
    for key, (scope, rows) in rows_by_scope.items():
        failures = 0
        for row in rows:
            try:
                reprocess_module.analyze_note_row(row, translate=False, scope=scope)
            except Exception as exc:  # noqa: BLE001 - isolate failures to this scope and continue others.
                failures += 1
                results.append({'stage': 'analysis', 'status': 'FAILED',
                                'scope': key, 'error_type': type(exc).__name__})
        if rows and not failures:
            results.append({'stage': 'analysis', 'status': 'COMPLETED',
                            'scope': key, 'processed': len(rows)})

    for key, scope in scopes.items():
        try:
            event_result = reprocess_module.build_cross_platform_events(limit=100, scope=scope)
            status = str(event_result.get('status') or '').upper() if isinstance(event_result, dict) else ''
            code = (event_result.get('code') or event_result.get('persistence_status')
                    or status) if isinstance(event_result, dict) else None
            if status in {'BLOCKED', 'FAILED'} or code in {
                    'BLOCKED', 'EVENT_SCOPE_EVIDENCE_REQUIRED', 'NOT_RUN_INCOMPLETE_SOURCE_READ'}:
                results.append({'stage': 'event_aggregation', 'status': 'BLOCKED',
                                'scope': key, 'code': code})
            elif status == 'COMPLETED':
                results.append({'stage': 'event_aggregation', 'status': 'COMPLETED',
                                'scope': key})
            else:
                results.append({'stage': 'event_aggregation', 'status': status or 'NOT_VERIFIED',
                                'scope': key, 'code': code})
        except Exception as exc:  # noqa: BLE001 - isolate failures to this scope and continue others.
            results.append({'stage': 'event_aggregation', 'status': 'FAILED',
                            'scope': key, 'error_type': type(exc).__name__})

_AUTO_PLAN_CURSOR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'private', 'xhs_auto_plan_cursor.json')


def _load_plan_cursor():
    try:
        with open(_AUTO_PLAN_CURSOR_FILE, 'r', encoding='utf-8') as f:
            value = json.load(f)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _save_plan_cursor(cursor):
    try:
        os.makedirs(os.path.dirname(_AUTO_PLAN_CURSOR_FILE), exist_ok=True)
        if cursor:
            with open(_AUTO_PLAN_CURSOR_FILE, 'w', encoding='utf-8') as f:
                json.dump(dict(cursor), f, ensure_ascii=False)
        elif os.path.exists(_AUTO_PLAN_CURSOR_FILE):
            os.remove(_AUTO_PLAN_CURSOR_FILE)
    except Exception:
        pass


def _resolve_registry_page(keywords=None):
    """Registry-wide plan that advances through every page across runs."""
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    if keywords is not None:
        return build_acquisition_plan(keywords)
    cursor = _load_plan_cursor()
    try:
        plan = build_acquisition_plan(None, continuation=cursor) if cursor else build_acquisition_plan(None)
    except Exception:
        plan = build_acquisition_plan(None)
    return plan

def _resolve_acquisition_plan(
    keywords=None, *, context_mode='GLOBAL_ALL', domain_id=None,
    subject_id=None, brand_focus_id=None,
):
    """Resolve canonical registry scope before identity/browser/network work."""
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    return build_acquisition_plan(
        keywords,
        context_mode=context_mode,
        domain_id=domain_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
    )

# 配置一致性断言：逻辑身份在 ACCOUNT_PROFILES 中存在 / 白名单数量匹配
assert XHS_CN_PRIMARY_NAME in ACCOUNT_PROFILES and XHS_RETINAUT_NAME in ACCOUNT_PROFILES, \
    "ACCOUNT_PROFILES 必须覆盖所有双身份逻辑名"
assert len(ALLOWED_USER_IDS) == (1 if XHS_RETINAUT is None else 2), \
    f"ALLOWED_USER_IDS 长度不匹配：XHS_RETINAUT 配置为 {XHS_RETINAUT!r}（None=暂不启用）"
# 运行时当前激活的身份（select_account 设置；None=默认 XHS_RETINAUT + 未 override）
_ACTIVE_ACCOUNT: str | None = None

# ── 每日次数上限：已改为“动态调度下的防失控兜底”，不再是固定配额 ──────────────
# 采集节奏由 platform_adapters.scheduling 的动态间隔主导（基准 3600s；NO_NEW_DATA
# ×1.5 指数延长至上限 6h；风控/网络退避、熔断、恢复试探），并由下方 COOLDOWN_MINUTES
# 做“任意两次运行至少间隔 60min”的账号安全硬地板。因此这里的每日次数只用于防止
# 死循环/失控刷量的高兜底，不再承担调度节奏：理论最快 1h 一次≈24 次/天，无新数据会
# 自动拉长，实际远少于此。提高日上限不会让单次间隔变密（仍受 60min 硬冷却约束），
# 只是允许采集持续全天、不再“午后用满固定次数即停摆到次日”。
MAX_DAILY_RUNS = 30  # 每日总次数兜底（=自动26 + 手动3 + 1 余量），仅防失控
MAX_MANUAL_RUNS = 3  # 每日手动触发（一键实时更新）最大次数（保持不变）
MAX_AUTO_RUNS = 26  # 每日自动采集兜底上限（动态间隔主导，基准1h理论≤24，留余量）
COOLDOWN_MINUTES = 60  # 连续运行后的冷却时间（分钟）- 账号安全硬地板，不随动态调度放宽
# ── 单轮内频率保护（所有采集路径在 sync 汇聚点统一遵循，降低单轮请求密度、防风控）──
KEYWORD_GAP_MIN_SEC = 12      # 同一轮相邻两次关键词搜索的最小拟人间隔下限（再叠加 _run_search 自身 delay）
KEYWORD_GAP_JITTER_SEC = 6    # 额外随机抖动上限，避免固定节奏被识别
EARLY_STOP_CONSECUTIVE = 3    # 一轮内连续这么多个关键词被拦截/网络失败即提前结束本轮，不再硬撞风控
NEW_ACCOUNT_GUARD_RUNS = 3  # 新账号前N次强制极轻量模式
# 采集时长配置（秒）
AUTO_COLLECT_DURATION = 1800  # 自动采集每次30分钟
MANUAL_COLLECT_DURATION = 1200  # 手动采集每次20分钟
NODE_PROCESS_TIMEOUT = 1800  # Node进程超时时间（秒）- 调整为30分钟，给足时间完成
# 固定钟点表：仅用于状态展示（get_account_status），生产调度已由 ShadowPlanner
# 动态间隔门控（app.py scheduler_loop），不再按此固定钟点触发；保留为历史参考。
AUTO_COLLECT_HOURS = [8, 10, 12, 14, 16, 18, 20, 22, 23]
_daily_runs = []  # 今日运行时间戳列表
_daily_manual_runs = 0  # 今日手动触发次数
_daily_auto_runs = 0  # 今日自动采集次数
_last_run_time = None  # 上次运行时间
_daily_run_history_state = 'UNKNOWN'  # task-start count is not inferred from note/keyword rows
_stats_loaded = False  # 是否已加载持久化统计
_stats_init_lock = threading.RLock()

_lock=threading.Lock()
_tasks={}

def _load_stats_from_db():
    """从数据库统计今天的采集次数（兜底恢复）"""
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time
    global _daily_run_history_state
    _daily_run_history_state = 'UNKNOWN'
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        with db.get_db() as conn:
            # 统计今天有多少个不同的采集批次（按collected_at的分钟级分组）
            cur = conn.execute("SELECT COUNT(DISTINCT strftime('%Y-%m-%d %H:%M', collected_at)) FROM notes WHERE date(collected_at)=date('now','localtime')")
            db_batch_count = cur.fetchone()[0] or 0
            # 获取最晚采集时间
            cur2 = conn.execute("SELECT MAX(collected_at) FROM notes WHERE date(collected_at)=date('now','localtime')")
            last_collect = cur2.fetchone()[0]
            if last_collect:
                try:
                    _last_run_time = datetime.strptime(last_collect, '%Y-%m-%d %H:%M:%S').timestamp()
                except Exception:
                    pass
        # 如果数据库有今天的采集记录，且内存计数为0，则从数据库恢复
        if db_batch_count > 0 and len(_daily_runs) == 0:
            # 估算：数据库批次数量作为今日运行次数（上限MAX_DAILY_RUNS）
            estimated_runs = min(db_batch_count, MAX_DAILY_RUNS)
            now = time.time()
            _daily_runs = [now - (estimated_runs - i) * 3600 for i in range(estimated_runs)]
            # 假设大部分是自动采集，手动占少数
            _daily_auto_runs = max(0, estimated_runs - 1)
            _daily_manual_runs = min(1, estimated_runs)
            print(f'[Stats] 从数据库恢复今日采集次数: {estimated_runs}次 (自动{_daily_auto_runs}/手动{_daily_manual_runs})')
    except Exception as e:
        print(f'[Stats] 从数据库恢复计数失败: {e}')

def _load_stats():
    """Initialize after schema bootstrap, or on the first explicit stats use."""
    with _stats_init_lock:
        return _load_stats_unlocked()


def _load_stats_unlocked():
    """从持久化文件加载统计数据（优先），失败则从数据库恢复"""
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time
    global _daily_run_history_state, _stats_loaded
    if _stats_loaded:
        return
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('date') == today:
                _daily_runs = data.get('daily_runs', [])
                _daily_manual_runs = data.get('manual_runs', 0)
                _daily_auto_runs = data.get('auto_runs', 0)
                _last_run_time = data.get('last_run_time')
                _daily_run_history_state = (
                    'OBSERVED_TASK_STARTS'
                    if data.get('daily_run_history_state') == 'OBSERVED_TASK_STARTS'
                    else 'UNKNOWN'
                )
                print(f'[Stats] 从文件恢复今日计数: 总{len(_daily_runs)}/手动{_daily_manual_runs}/自动{_daily_auto_runs}')
                _stats_loaded = True
                return
            try:
                stored_day = datetime.strptime(str(data.get('date') or ''), '%Y-%m-%d').date()
            except ValueError:
                stored_day = None
            if stored_day is not None and stored_day < datetime.now().date():
                # A previous-day snapshot cannot establish how many keyword
                # observations ran today. Start the task-start ledger at zero;
                # its entries are written only by record_run().
                _daily_runs = []
                _daily_manual_runs = 0
                _daily_auto_runs = 0
                # The previous-day file still carries the last actual start.
                # Keep that timestamp so a midnight rollover cannot bypass
                # the account cooldown.
                try:
                    previous_last_run = float(data.get('last_run_time'))
                    if previous_last_run > 0:
                        _last_run_time = previous_last_run
                except (TypeError, ValueError):
                    pass
                _daily_run_history_state = 'OBSERVED_TASK_STARTS'
                _stats_loaded = True
                _save_stats()
                return
        # 文件不存在或不是今天的数据，从数据库恢复
        _load_stats_from_db()
        _save_stats()
        _stats_loaded = True
    except Exception as e:
        print(f'[Stats] 加载统计失败: {e}')
        _load_stats_from_db()
        _stats_loaded = True

def _save_stats():
    """保存统计数据到持久化文件"""
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'daily_runs': _daily_runs[-50:],  # 只保留最近50条
            'manual_runs': _daily_manual_runs,
            'auto_runs': _daily_auto_runs,
            'daily_run_history_state': _daily_run_history_state,
            'last_run_time': _last_run_time,
            'updated_at': datetime.now().isoformat()
        }
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'[Stats] 保存统计失败: {e}')

# Importing a session owner must not query or create a database. Product Core
# initializes stats after its canonical schema lifecycle; standalone consumers
# initialize lazily below without starting collection or a browser.

def _effective_cookie_file() -> str:
    """返回当前生效的 Cookie 文件路径：优先 select_account() 设置的 override；否则默认 PRIMARY。"""
    override = os.environ.get('XHS_COOKIE_FILE_OVERRIDE', '').strip()
    if override:
        return override
    return COOKIE_FILE


def _extract_user_id_from_cookie_text(content: str):
    """从Cookie字符串（分号分隔）中提取 x-user-id-pro；提取不到返回 None。"""
    if not content:
        return None
    for part in content.split(';'):
        part = part.strip()
        if part.startswith('x-user-id-pro='):
            return part.split('=', 1)[1].strip()
    return None


def _get_current_user_id():
    """从当前生效 Cookie 文件中提取登录账号ID（兼容 override / env header / 默认路径）。"""
    try:
        cookie_file = _effective_cookie_file()
        # 1) 首选：Cookie 文件（支持 select_account override）
        if cookie_file and os.path.exists(cookie_file):
            content = open(cookie_file, encoding='utf-8', errors='replace').read()
            uid = _extract_user_id_from_cookie_text(content)
            if uid:
                return uid
        # 2) 其次：XHS_COOKIE_HEADER 环境变量（全局 HTTP Header Cookie）
        if os.getenv('XHS_COOKIE_HEADER'):
            uid = _extract_user_id_from_cookie_text(os.environ['XHS_COOKIE_HEADER'])
            if uid:
                return uid
        # 3) 兜底：XHS_COOKIES_JSON（老格式兼容）
        if os.getenv('XHS_COOKIES_JSON'):
            try:
                cj = json.loads(os.environ['XHS_COOKIES_JSON'])
                if isinstance(cj, list):
                    for c in cj:
                        if str(c.get('name', '')).lower() in ('x-user-id-pro', 'a1') and c.get('value'):
                            return str(c['value']).strip()
                elif isinstance(cj, dict):
                    for k, v in cj.items():
                        if 'x-user-id-pro' in str(k).lower() and v:
                            return str(v).strip()
            except Exception:
                pass
    except Exception:
        pass
    return None

def verify_account():
    """Verify only the policy-approved registered international account.

    Never fall back to ambient Cookie environment variables: they are not an
    identity grant and may belong to a protected personal browser session.
    """
    active = _canonical_account_name(_ACTIVE_ACCOUNT or DEFAULT_COLLECTION_ACCOUNT)
    try:
        policy = collection_policy_gate(account=active, region="intl")
    except Exception:  # noqa: BLE001 - unavailable policy is a denial, never an identity grant.
        return False, "POLICY_UNAVAILABLE"
    if (policy.get("ok") is not True or policy.get("account") != active
            or policy.get("region") != "intl" or active != DEFAULT_COLLECTION_ACCOUNT
            or active != XHS_RETINAUT_NAME or not XHS_RETINAUT
            or XHS_RETINAUT not in ALLOWED_USER_IDS):
        return False, "POLICY_BLOCKED"
    binding = ACCOUNT_PROFILES.get(active)
    if not isinstance(binding, (tuple, list)) or len(binding) != 2 or not binding[0] or not binding[1]:
        return False, "REGISTERED_IDENTITY_UNAVAILABLE"
    cookie_path = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(binding[0]))))
    profile_path = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(binding[1]))))
    expected_cookie = os.path.realpath(os.path.join(PRIVATE_DATA_DIR, "xhs_cookie_retinaut.txt"))
    expected_profile = os.path.realpath(os.path.join(PRIVATE_DATA_DIR, "profiles", "xhs-retinaut"))
    if (os.path.normcase(cookie_path) != os.path.normcase(expected_cookie)
            or os.path.normcase(profile_path) != os.path.normcase(expected_profile)):
        return False, "REGISTERED_IDENTITY_BINDING_MISMATCH"
    try:
        with open(cookie_path, encoding="utf-8", errors="replace") as cookie_stream:
            current_id = _extract_user_id_from_cookie_text(cookie_stream.read())
    except OSError:
        return False, "REGISTERED_SESSION_UNAVAILABLE"
    if current_id != XHS_RETINAUT:
        return False, "REGISTERED_IDENTITY_MISMATCH"
    return True, "REGISTERED_IDENTITY_VERIFIED"

def check_rate_limit(run_type='manual'):
    """检查频率限制，返回(是否允许, 提示信息)
    run_type: 'manual'（一键实时更新）或 'auto'（定时自动采集）
    """
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time
    _load_stats()
    now = time.time()
    today = datetime.now().strftime('%Y-%m-%d')
    # 清理非今日的记录
    _daily_runs = [t for t in _daily_runs if datetime.fromtimestamp(t).strftime('%Y-%m-%d') == today]
    # 检查每日总次数
    if len(_daily_runs) >= MAX_DAILY_RUNS:
        return False, f"今日已运行{len(_daily_runs)}次，达到每日上限({MAX_DAILY_RUNS}次)，请明天再试"
    # 检查手动次数
    if run_type == 'manual' and _daily_manual_runs >= MAX_MANUAL_RUNS:
        return False, f"今日手动触发已达{MAX_MANUAL_RUNS}次上限，剩余{MAX_AUTO_RUNS}次为定时自动采集"
    # 检查自动次数
    if run_type == 'auto' and _daily_auto_runs >= MAX_AUTO_RUNS:
        return False, f"今日自动采集已达{MAX_AUTO_RUNS}次上限"
    # 检查冷却时间
    if _last_run_time and (now - _last_run_time) < COOLDOWN_MINUTES * 60:
        wait_min = int((COOLDOWN_MINUTES * 60 - (now - _last_run_time)) / 60) + 1
        return False, f"距离上次运行不足{COOLDOWN_MINUTES}分钟，请等待{wait_min}分钟后再试（保护账号）"
    return True, "频率检查通过"

def record_run(run_type='manual'):
    """记录一次运行
    run_type: 'manual'（一键实时更新）或 'auto'（定时自动采集）
    """
    global _daily_runs, _daily_manual_runs, _daily_auto_runs, _last_run_time
    global _daily_run_history_state
    _load_stats()
    now = time.time()
    _daily_runs.append(now)
    _last_run_time = now
    _daily_run_history_state = 'OBSERVED_TASK_STARTS'
    if run_type == 'manual':
        _daily_manual_runs += 1
    else:
        _daily_auto_runs += 1
    # 持久化保存
    _save_stats()

def get_account_status(account=None):
    """Return safe status for the currently policy-approved XHS session.

    Policy is checked before account bindings. The response omits Cookie values,
    user IDs, local paths, CDP endpoints, and identities outside the current policy.
    Cookie presence is metadata only; authentication is verified by collection preflight.
    """
    active_account = _canonical_account_name(
        account or _ACTIVE_ACCOUNT or DEFAULT_COLLECTION_ACCOUNT)
    try:
        policy = collection_policy_gate(account=active_account, region="intl")
    except Exception:  # noqa: BLE001 - unavailable policy keeps all account capabilities unavailable.
        policy = {"ok": False, "code": "policy_unavailable"}
    policy_ok = (policy.get("ok") is True
                 and policy.get("account") == active_account
                 and policy.get("region") == "intl"
                 and active_account == DEFAULT_COLLECTION_ACCOUNT
                 and active_account == XHS_RETINAUT_NAME
                 and bool(XHS_RETINAUT)
                 and XHS_RETINAUT in ALLOWED_USER_IDS)

    binding_valid = False
    cookie_ready = False
    worker_available = False
    if policy_ok:
        try:
            binding = ACCOUNT_PROFILES.get(active_account)
            if isinstance(binding, (tuple, list)) and len(binding) == 2 and binding[0] and binding[1]:
                cookie_path = os.path.realpath(os.path.abspath(
                    os.path.expanduser(os.fspath(binding[0]))))
                profile_path = os.path.realpath(os.path.abspath(
                    os.path.expanduser(os.fspath(binding[1]))))
                expected_cookie = os.path.realpath(os.path.join(
                    PRIVATE_DATA_DIR, "xhs_cookie_retinaut.txt"))
                expected_profile = os.path.realpath(os.path.join(
                    PRIVATE_DATA_DIR, "profiles", "xhs-retinaut"))
                if (os.path.normcase(cookie_path) == os.path.normcase(expected_cookie)
                        and os.path.normcase(profile_path) == os.path.normcase(expected_profile)):
                    try:
                        cookie_ready = os.path.isfile(cookie_path) and os.path.getsize(cookie_path) > 0
                    except OSError:
                        cookie_ready = False
                    import cdp_helper
                    registered = cdp_helper._registered_xhs_binding(active_account)
                    binding_valid = bool(registered and
                        os.path.normcase(os.path.realpath(registered["profile"]))
                        == os.path.normcase(expected_profile))
                    if binding_valid:
                        worker = cdp_helper.resolve_registered_xhs_worker(
                            account=active_account, headless=True)
                        worker_available = worker.get("available") is True
        except Exception:  # noqa: BLE001 - incomplete profile/worker proof fails closed.
            binding_valid = False
            worker_available = False

    _load_stats()
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    today_runs = len([
        t for t in _daily_runs
        if datetime.fromtimestamp(t, tz=timezone.utc).astimezone().strftime("%Y-%m-%d") == today
    ])
    cooldown_remaining = 0
    if _last_run_time:
        elapsed = time.time() - _last_run_time
        if elapsed < COOLDOWN_MINUTES * 60:
            cooldown_remaining = int((COOLDOWN_MINUTES * 60 - elapsed) / 60) + 1
    visible_account = active_account if policy_ok and binding_valid else None
    account_row = ({
        "account": visible_account,
        "active": True,
        "cookie_ready": cookie_ready,
        "user_id_match": None,
        "diagnostic_ready": None,
        "can_use": None,
        "collection_enabled": bool(policy_ok and binding_valid),
        "session_state": "NOT_VERIFIED",
        "cdp_online": worker_available,
    } if visible_account else None)
    safe_policy = {
        "ok": bool(policy_ok),
        "code": "allowed" if policy_ok else str(policy.get("code") or "unavailable"),
        "region": "intl" if policy_ok else None,
        "policy_version": policy.get("policy_version") if policy_ok else None,
    }
    return {
        "ok": True,
        "active_account": visible_account,
        "accounts": [account_row] if account_row else [],
        "allowed_accounts": [visible_account] if visible_account else [],
        "today_runs": today_runs,
        "today_manual_runs": _daily_manual_runs,
        "today_auto_runs": _daily_auto_runs,
        "max_daily_runs": MAX_DAILY_RUNS,
        "max_manual_runs": MAX_MANUAL_RUNS,
        "max_auto_runs": MAX_AUTO_RUNS,
        "auto_collect_hours": AUTO_COLLECT_HOURS,
        "cooldown_minutes": COOLDOWN_MINUTES,
        "cooldown_remaining_minutes": cooldown_remaining,
        "new_account_guard_runs": NEW_ACCOUNT_GUARD_RUNS,
        "cookie_configured": cookie_ready if policy_ok and binding_valid else None,
        "worker_available": worker_available if policy_ok and binding_valid else None,
        "collection_enabled": bool(policy_ok and binding_valid),
        "collection_policy": safe_policy,
        "status": ("configured" if policy_ok and binding_valid and cookie_ready
                   else "unavailable" if not policy_ok or not binding_valid
                   else "not_verified"),
    }
def cookie_configured():
    """当前身份的 Cookie 是否齐备（支持 select_account override 生效路径）。"""
    if os.getenv('XHS_COOKIE_HEADER') or os.getenv('XHS_COOKIES_JSON'):
        return True
    cookie_file = _effective_cookie_file()
    return bool(cookie_file and os.path.exists(cookie_file) and
                open(cookie_file, encoding='utf-8', errors='replace').read().strip())


def _check_cdp_online(cdp_url: str, timeout: float = 2.5) -> bool:
    """轻量 CDP 健康探活：只 ping /json/version 不做动作。返回 True=浏览器已常驻连接就绪。"""
    try:
        import urllib.request as _ur
        if not cdp_url:
            return False
        if not cdp_url.startswith('http'):
            cdp_url = 'http://' + cdp_url
        with _ur.urlopen(cdp_url.rstrip('/') + '/json/version', timeout=timeout) as _r:
            return _r.status == 200
    except Exception:
        return False


def runtime_preflight_check(account: str | None = None,
                            cdp_url: str | None = None,
                            quick: bool = False) -> dict:
    """Check only the currently policy-approved registered XHS session.

    This compatibility response is safe for the product UI: it never returns
    Cookie values, user IDs, local paths, CDP URLs/ports, or raw process details.
    """
    from xhs_runtime_state import (
        AuthState,
        PlatformState,
        SessionState,
        XhsRuntimeState,
    )

    state = XhsRuntimeState()
    checks: list = []
    def _add(cid, name, level, st, detail, **kw):
        checks.append({"id": cid, "name": name, "level": level, "status": st, "detail": detail, **kw})
    def _safe_policy(policy):
        return {"ok": policy.get("ok") is True,
                "code": str(policy.get("code") or "unavailable"),
                "region": "intl" if policy.get("ok") is True else None,
                "policy_version": policy.get("policy_version") if policy.get("ok") is True else None}
    def _safe_circuit(circuit):
        return {"open": bool(circuit.get("open")),
                "state": str(circuit.get("state") or "UNKNOWN"),
                "resume_at": circuit.get("resume_at")}
    def _safe_pause(pause):
        return {"paused": bool(pause), "at": pause.get("at") if isinstance(pause, dict) else None}

    account_used = str(account or DEFAULT_COLLECTION_ACCOUNT).strip().upper()
    try:
        policy_gate = collection_policy_gate(account=account_used, region="intl")
    except Exception:  # noqa: BLE001 - unavailable policy prevents collection-result use.
        policy_gate = {"ok": False, "code": "policy_unavailable"}
    safe_policy = _safe_policy(policy_gate)
    account_status = get_account_status(account=account_used)
    circ = _safe_circuit(get_circuit_state())
    paused = _safe_pause(is_user_paused())
    public_account = (account_used if policy_gate.get("ok") is True
                      and policy_gate.get("account") == account_used
                      and policy_gate.get("region") == "intl"
                      and account_status.get("collection_enabled") else None)

    if not public_account:
        _add("A0_POLICY", "RedNote collection policy", "P0", "fail", "Collection is unavailable under the current account policy.")
        state.auth = AuthState.REQUIRED
        return {"ok": False, "overall_state": safe_policy["code"], "checks": checks,
                "account_status": account_status, "circuit": circ, "active_account": None,
                "allowed_accounts": [], "cdp_online": False, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "POLICY_BLOCKED"}

    try:
        import cdp_helper
        registered = cdp_helper._registered_xhs_binding(public_account)
    except Exception:  # noqa: BLE001 - no verified registered binding means unavailable.
        registered = None
    if not registered:
        _add("A1_ACCOUNT", "Registered collection identity", "P0", "fail", "The approved registered identity or browser profile is unavailable.")
        return {"ok": False, "overall_state": "identity_unavailable", "checks": checks,
                "account_status": account_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": False, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "REGISTERED_IDENTITY_UNAVAILABLE"}

    ok_sel, _ = select_account(public_account)
    if not ok_sel:
        _add("A1_ACCOUNT", "Registered collection identity", "P0", "fail", "The approved collection identity is not configured.")
        return {"ok": False, "overall_state": "need_account", "checks": checks,
                "account_status": account_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": False, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "REGISTERED_IDENTITY_UNAVAILABLE"}
    _add("A1_ACCOUNT", "Registered collection identity", "P0", "pass", "The policy-approved registered collection identity is selected.")

    registered_cdp_url = cdp_url_for(public_account, headless=True)
    configured_endpoints = [str(value or "").strip().rstrip("/")
                            for value in (cdp_url, os.getenv("XHS_CDP_URL"))]
    endpoint_mismatch = any(value and value != registered_cdp_url
                            for value in configured_endpoints)
    cdp_probe_url = "" if endpoint_mismatch else registered_cdp_url

    if not cookie_configured():
        state.auth = AuthState.REQUIRED
        state.session = SessionState.NO_COOKIE
        _add("A2_COOKIE", "Registered session configuration", "P0", "fail", "The approved session is not configured.")
        return {"ok": False, "overall_state": "no_cookie", "checks": checks,
                "account_status": account_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": False, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "REGISTERED_SESSION_UNAVAILABLE"}
    _add("A2_COOKIE", "Registered session configuration", "P0", "pass", "The approved session configuration is present.")
    state.session = SessionState.COOKIE_PRESENT

    ok_uid, _ = verify_account()
    if not ok_uid:
        state.auth = AuthState.EXPIRED
        _add("A3_IDENTITY", "Registered identity verification", "P0", "fail", "The registered session identity could not be verified.")
        return {"ok": False, "overall_state": "identity_unverified", "checks": checks,
                "account_status": account_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": False, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "REGISTERED_IDENTITY_UNVERIFIED"}
    _add("A3_IDENTITY", "Registered identity verification", "P0", "pass", "The registered session identity matches its approved binding.")
    state.auth = AuthState.VALID

    cdp_online = False
    if not quick:
        cdp_online = _check_cdp_online(cdp_probe_url)
        if cdp_online:
            state.session = SessionState.BROWSER_CONNECTED
            _add("A4_BROWSER", "Registered background browser", "P1", "pass", "The registered background browser is reachable.")
        else:
            _add("A4_BROWSER", "Registered background browser", "P1", "warn",
                 "The registered background browser is unavailable or its endpoint hint does not match.")
            state.platform = PlatformState.UNREACHABLE
    else:
        _add("A4_BROWSER", "Registered background browser", "P1", "skip", "Quick status skipped the browser reachability check.")

    circ = _safe_circuit(get_circuit_state())
    if circ.get("open"):
        state.circuit = "OPEN"
        _add("A5_CIRCUIT", "Collection circuit", "P0", "fail", "Collection is paused by the current circuit state.")
        return {"ok": False, "overall_state": "blocked", "checks": checks,
                "account_status": account_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": cdp_online, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "COLLECTION_CIRCUIT_OPEN"}
    _add("A5_CIRCUIT", "Collection circuit", "P0", "pass", "The collection circuit is closed.")
    state.platform = PlatformState.REACHABLE

    pause_state = is_user_paused()
    paused = _safe_pause(pause_state)
    if paused["paused"]:
        _add("A6_PAUSE", "User pause", "P0", "fail", "Collection is paused by the user.")
        return {"ok": False, "overall_state": "user_paused", "checks": checks,
                "account_status": account_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": cdp_online, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "USER_PAUSED"}
    _add("A6_PAUSE", "User pause", "P0", "pass", "Collection is not paused by the user.")

    acc_status = get_account_status(account=public_account)
    cooldown = acc_status.get("cooldown_remaining_minutes", 0)
    if cooldown and cooldown > 0:
        _add("A7_RATE", "Collection pacing", "P1", "warn", f"Collection is cooling down for about {cooldown} more minutes.")
        return {"ok": False, "overall_state": "cooldown", "checks": checks,
                "account_status": acc_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": cdp_online, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "COLLECTION_COOLDOWN"}
    if acc_status.get("today_runs", 0) >= acc_status.get("max_daily_runs", 12):
        _add("A7_RATE", "Collection pacing", "P1", "fail", "The daily collection limit has been reached.")
        return {"ok": False, "overall_state": "rate_limit", "checks": checks,
                "account_status": acc_status, "circuit": circ, "active_account": public_account,
                "allowed_accounts": [public_account], "cdp_online": cdp_online, "user_paused": paused,
                "collection_policy": safe_policy, "evidence": "DAILY_COLLECTION_LIMIT_REACHED"}
    _add("A7_RATE", "Collection pacing", "P0", "pass", "Collection pacing limits permit a new attempt.")
    state.session = SessionState.REAL_SESSION_VALID if cdp_online else SessionState.COOKIE_PRESENT
    return {"ok": True, "overall_state": "ready", "checks": checks,
            "account_status": acc_status, "circuit": circ, "active_account": public_account,
            "allowed_accounts": [public_account], "collection_policy": safe_policy,
            "cdp_online": cdp_online, "user_paused": paused,
            "state_machine": {"auth": state.auth.value, "session": state.session.value,
                             "platform": state.platform.value,
                             "circuit": (state.circuit.value if hasattr(state.circuit, "value") else str(state.circuit))},
            "evidence": "PRECHECK_READY"}

def _run_search(keyword,max_scroll=6):
    service_python = sys.executable
    if not isinstance(service_python, str) or not service_python or not os.path.isabs(service_python):
        raise RuntimeError('LUMENIS_SERVICE_PYTHON_INVALID')
    # 网络自适应：使用当前自适应设置
    adaptive = network_adaptive.get_adaptive_settings()
    effective_scroll = min(max_scroll, adaptive.get('current_scroll_limit', 6))
    delay = adaptive.get('current_delay_seconds', 2)
    
    os.makedirs(PRIVATE_DATA_DIR, exist_ok=True)
    out=os.path.join(PRIVATE_DATA_DIR,f'xhs_{int(time.time()*1000)}.json')
    env=os.environ.copy()
    env['LUMENIS_SERVICE_PYTHON'] = service_python
    # Resolve the approved identity and profile through the existing Python owners.
    # The child environment carries consistency data; it is not an authorization grant.
    selected = _ACTIVE_ACCOUNT or DEFAULT_COLLECTION_ACCOUNT
    policy = collection_policy_gate(account=selected, region='intl')
    binding = ACCOUNT_PROFILES.get(selected)
    if (selected != XHS_RETINAUT_NAME or not policy.get('ok')
            or not isinstance(binding, (tuple, list)) or len(binding) != 2
            or not binding[0] or not binding[1] or not XHS_RETINAUT):
        raise PermissionError('XHS_APPROVED_HK_INTL_IDENTITY_UNAVAILABLE')
    cookie_file = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(binding[0]))))
    expected_cookie_file = os.path.realpath(os.path.join(PRIVATE_DATA_DIR, 'xhs_cookie_retinaut.txt'))
    profile_dir = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(binding[1]))))
    expected_profile_dir = os.path.realpath(os.path.join(PRIVATE_DATA_DIR, 'profiles', 'xhs-retinaut'))
    if (os.path.normcase(cookie_file) != os.path.normcase(expected_cookie_file)
            or os.path.normcase(profile_dir) != os.path.normcase(expected_profile_dir)):
        raise PermissionError('XHS_REGISTERED_PROFILE_BINDING_MISMATCH')
    # A registered SYSTEM worker is a required caller precondition. Resolve it
    # before reading the approved cookie file or starting the legacy JS bridge;
    # the child repeats PID/profile/kernel/endpoint verification before connect.
    cdp_endpoint = cdp_url_for(account=selected, headless=True)
    if not cdp_endpoint:
        raise RuntimeError('XHS_REGISTERED_BROWSER_SESSION_UNAVAILABLE')
    # Check the exact registered Cookie file; a fallback environment header must
    # not authorize a child process whose registered Cookie has another identity.
    try:
        with open(cookie_file, encoding='utf-8', errors='replace') as cookie_stream:
            registered_user_id = _extract_user_id_from_cookie_text(cookie_stream.read())
    except OSError as exc:
        raise PermissionError('XHS_REGISTERED_COOKIE_UNAVAILABLE') from exc
    if registered_user_id != XHS_RETINAUT:
        raise PermissionError('XHS_REGISTERED_COOKIE_IDENTITY_MISMATCH')
    env['XHS_COLLECTION_ACCOUNT'] = XHS_RETINAUT_NAME
    env['XHS_EXPECTED_COLLECTION_USER_ID'] = XHS_RETINAUT
    env['XHS_COOKIE_FILE'] = cookie_file
    env['XHS_PROFILE_DIR'] = profile_dir
    env['XHS_COLLECTION_HOST'] = 'www.rednote.com'
    env['XHS_COLLECTION_REGION'] = 'intl'
    env.pop('XHS_COOKIE_HEADER', None)
    env.pop('XHS_COOKIES_JSON', None)
    # Search reuses the server-resolved HK/intl worker. The child validates the
    # same registered identity again and never starts a replacement browser.
    env['XHS_CDP_URL'] = cdp_endpoint
    cmd=[_NODE_BIN,SEARCH_JS,'--keyword',keyword,'--output',out,'--max-scroll',str(effective_scroll)]
    try:
        # 使用Popen+轮询，避免Flask线程中subprocess阻塞
        stdout_file = out + '.stdout'
        stderr_file = out + '.stderr'
        with open(stdout_file, 'w', encoding='utf-8') as fout, open(stderr_file, 'w', encoding='utf-8') as ferr:
            p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=fout, stderr=ferr)
        # 轮询等待完成，最多30分钟（给足时间完成采集，不要因为担心时间长而简短过去）
        waited = 0
        while p.poll() is None and waited < NODE_PROCESS_TIMEOUT:
            time.sleep(5)
            waited += 5
            # 每30秒输出一次进度（通过任务状态反馈）
            if waited % 30 == 0:
                print(f"[xhs-bridge] 关键词 '{keyword}' 采集中... 已等待 {waited}秒", flush=True)
        if p.poll() is None:
            p.kill()
            return {'keyword':keyword,'total':0,'notes':[],'state':'NETWORK_ERROR','error':f'Node进程超时（{NODE_PROCESS_TIMEOUT}秒）','risk_detected':False}
        if p.returncode != 0:
            error_msg = ''
            parsed = None
            # Node 崩溃时也可能已写出结构化结果（main catch 会落 NETWORK_ERROR）
            try:
                if os.path.exists(out):
                    with open(out, encoding='utf-8') as f: parsed = json.load(f)
            except Exception:
                parsed = None
            try:
                with open(stderr_file, encoding='utf-8') as f:
                    error_msg = f.read()[-1000:]
            except Exception:
                pass
            # 风控检测
            risk = network_adaptive.detect_risk(error_msg=error_msg)
            if risk['is_risk']:
                network_adaptive.report_collection_result(False, risk_info=risk)
            if parsed:
                parsed.setdefault('error', error_msg); return parsed
            return {'keyword':keyword,'total':0,'notes':[],'state':'NETWORK_ERROR','error':error_msg,'risk_detected':risk['is_risk']}
        with open(out,encoding='utf-8') as f:
            result = json.load(f)
        # 六态兜底：若旧版结果无 state，则按 blocked_reason/数量推导
        if not result.get('state'):
            _br = result.get('blocked_reason','')
            if _br == 'LOGIN_REQUIRED': result['state']='AUTH_FAILED'
            elif _br: result['state']='BLOCKED'
            elif result.get('api_calls',0)>0 and result.get('total',0)==0: result['state']='EMPTY'
            elif result.get('total',0)>0: result['state']='SUCCESS'
            else: result['state']='NETWORK_ERROR'
        # js 已基于 URL 重定向 / error_code / 验证码精确判定 state；
        # bridge 不再用“结果正文词频”覆盖成功态——搜“投诉/避雷”时正文本就含风险词，宽泛匹配会误杀成功采集
        if result.get('state') in (None, '', 'NETWORK_ERROR'):
            risk = network_adaptive.detect_risk(response_text=json.dumps(result, ensure_ascii=False))
            if risk['is_risk']:
                result['state']='BLOCKED'; result['blocked_reason']=risk.get('type','RISK')
        if result.get('state') in ('BLOCKED','AUTH_FAILED','CAPTCHA'):
            network_adaptive.report_collection_result(False, risk_info={'type':result.get('blocked_reason') or result['state'],'is_risk':True})
        return result
    finally:
        try: os.remove(out)
        except OSError: pass
        try: os.remove(out + '.stdout')
        except OSError: pass
        try: os.remove(out + '.stderr')
        except OSError: pass
        # 自适应延迟
        time.sleep(delay)

# ========== 六态状态机：采集日志落库 + 自动熔断 ==========
CIRCUIT_FILE=os.path.join(PRIVATE_DATA_DIR,'xhs_circuit.json')
# 用户级“手动暂停采集”开关（区别于风控熔断：由用户主动设置，手动/自动一律不发起平台请求，直到用户主动恢复）
USER_PAUSE_FILE=os.path.join(PRIVATE_DATA_DIR,'xhs_user_paused.json')

def is_user_paused():
    """返回用户暂停信息 dict；未暂停返回 None。"""
    try:
        if not os.path.exists(USER_PAUSE_FILE): return None
        d=json.load(open(USER_PAUSE_FILE,encoding='utf-8'))
        return d if d.get('paused') else None
    except Exception:
        return None

def set_user_paused(reason='用户手动暂停'):
    try:
        os.makedirs(os.path.dirname(USER_PAUSE_FILE),exist_ok=True)
        with open(USER_PAUSE_FILE,'w',encoding='utf-8') as f:
            json.dump({'paused':True,'reason':reason,'at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')},f,ensure_ascii=False)
        return True
    except Exception:
        return False

def resume_user_paused():
    try:
        if os.path.exists(USER_PAUSE_FILE): os.remove(USER_PAUSE_FILE)
        return True
    except OSError:
        return False
STATE_LABEL={'SUCCESS':'正常','EMPTY':'正常但无数据','BLOCKED':'IP风控拦截','AUTH_FAILED':'登录态失效',
             'CAPTCHA':'需要人机验证','NETWORK_ERROR':'网络异常','PARTIAL_BLOCKED':'部分关键词被拦截'}

def _write_collection_log(keyword,notes_count,state,error_msg=''):
    """每个关键词一条采集日志，state 为六态，绝不把 BLOCKED 写成成功 0 条"""
    try:
        with db.get_db() as conn:
            conn.execute("INSERT INTO collection_logs(keyword,notes_count,status,error_msg,started_at,finished_at) VALUES(?,?,?,?,?,?)",
                         (keyword,notes_count if state in ('SUCCESS','EMPTY') else None,state,error_msg,
                          datetime.now().strftime('%Y-%m-%d %H:%M:%S'),datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
    except Exception as e:
        print('[xhs-bridge] collection_logs写入失败:',e,flush=True)

def _trip_circuit(state,detail,cool_minutes=60):
    """熔断：BLOCKED/AUTH/CAPTCHA 时写入暂停时间，自动调度在此之前跳过（手动/测试模式可强制）"""
    try:
        import json as _json
        until=time.time()+cool_minutes*60
        cur={'state':state,'detail':detail,'tripped_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             'resume_at':datetime.fromtimestamp(until).strftime('%Y-%m-%d %H:%M:%S'),'resume_ts':until}
        with open(CIRCUIT_FILE,'w',encoding='utf-8') as f: _json.dump(cur,f,ensure_ascii=False)
    except Exception:
        pass

def get_circuit_state():
    """供调度器/报告/前端读取当前熔断状态"""
    try:
        if not os.path.exists(CIRCUIT_FILE): return {'open':False,'state':'SUCCESS'}
        d=json.load(open(CIRCUIT_FILE,encoding='utf-8'))
        if d.get('resume_ts',0) <= time.time(): return {'open':False,'state':'SUCCESS'}
        d['open']=True; return d
    except Exception:
        return {'open':False,'state':'SUCCESS'}

def clear_circuit():
    try:
        if os.path.exists(CIRCUIT_FILE): os.remove(CIRCUIT_FILE)
    except OSError: pass


def _adaptive_cool_minutes():
    # 熔断冷却时长随 adaptive_engine 策略动态递增（越失败冻结越久），异常回退60分钟
    try:
        import adaptive_engine as _ae
        return {'normal': 60, 'cautious': 90, 'conservative': 180, 'suspended': 360}.get(
            _ae.adaptive_engine.get_current_strategy(), 60)
    except Exception:
        return 60

def risk_gating_enabled():
    """风控闸门总开关 COLLECTION_RISK_GATING：研发期默认 off（不限速/不熔断/不冷却），闭环前设 on。"""
    return os.environ.get('COLLECTION_RISK_GATING','off').strip().lower() in ('1','on','true','yes')

def is_test_mode():
    """XHS_TEST_MODE=1 或风控闸门关闭（研发期默认）时跳过冷却/新账号保护/熔断拦截"""
    return (os.environ.get('XHS_TEST_MODE','').strip() in ('1','true','TRUE','yes')
            or not risk_gating_enabled())

def select_account(account_name: str):
    """双子星库 Contract：选择小红书采集身份（硬白名单 ACCOUNT_PROFILES）。

    成功 → 设置模块级 _ACTIVE_ACCOUNT + 环境变量 XHS_COOKIE_FILE_OVERRIDE；
    失败 → 返回 (False, 详细错误信息)，绝不静默降级到其他身份。

    Args:
        account_name: 逻辑身份名，必须 ∈ ACCOUNT_PROFILES.keys()

    Returns:
        (ok: bool, message: str)
    """
    global _ACTIVE_ACCOUNT
    if not account_name:
        return False, "身份名为空，必须显式指定双子星库 Contract 白名单身份之一"
    if account_name not in ACCOUNT_PROFILES:
        return False, (f"身份 [{account_name}] 不在双子星库 Contract 硬白名单中。"
                       f"允许身份: {list(ACCOUNT_PROFILES.keys())}")
    cookie_path, cdp_profile_dir = ACCOUNT_PROFILES[account_name]
    # RETINAUT 等未配置身份（XHS_RETINAUT is None 或 cookie 文件不存在）给出友好错误
    if cookie_path is None:
        return False, (f"身份 [{account_name}] Cookie 路径尚未配置（XHS_RETINAUT 等身份需提供真实 user_id + cookie 文件）。"
                       f"当前激活: {list(ACCOUNT_PROFILES.keys())}，请先补齐 data/private/ 下对应 cookie 文件。")
    if not os.path.isfile(cookie_path):
        return False, (f"身份 [{account_name}] 对应 Cookie 文件不存在: {cookie_path}。"
                       f"请先合法导入对应身份 Cookie 到该路径后重试。")
    if not ACCOUNT_PROFILES[account_name][1] or not os.path.isdir(ACCOUNT_PROFILES[account_name][1]):
        # CDP profile 目录缺失仅警告，不阻塞（cookie_bridge 模式可能不走 CDP；Playwright 模式会再报错）
        pass
    # 写入生效 Contract：环境变量 override 优先级最高，所有下游 _effective_cookie_file() 读到一致身份
    os.environ['XHS_COOKIE_FILE_OVERRIDE'] = str(cookie_path)
    _ACTIVE_ACCOUNT = account_name
    return True, (f"身份切换成功: {account_name} | cookie={os.path.basename(cookie_path)} "
                  f"| cdp_profile={os.path.basename(cdp_profile_dir) if cdp_profile_dir else 'N/A'}")

def _record_note_lineage(note_data, provider="xhs_cookie_bridge"):
    """写 Evidence/Canonical 旁路；任何异常都不能覆盖或回滚 notes 主记录。"""
    try:
        from lumenis.shared.evidence import capture_note_lineage

        result = capture_note_lineage(
            note_data,
            db_path=db.DB_PATH,
            provider=provider,
            subject_scope="CTH",
            domain_id="cth",
            product_id="CTH",
        )
        if not result.get("ok"):
            error_types = ",".join(item.get("error_type", "unknown") for item in result.get("errors", []))
            print(f"[xhs-bridge][lineage] side-write incomplete: {error_types or 'unknown'}", flush=True)
        return result
    except Exception as exc:
        print(f"[xhs-bridge][lineage] side-write skipped (non-fatal): {type(exc).__name__}", flush=True)
        return {"ok": False, "errors": [{"stage": "lineage", "error_type": type(exc).__name__}]}


def sync(keywords=None, max_scroll=6, account=None):
    query_plan = _resolve_acquisition_plan(keywords)
    query_plan_payload = query_plan.to_dict()
    if not query_plan.is_runnable:
        return {
            'ok': False, 'task_state': 'BLOCKED', 'state_counts': {},
            'keywords': [], 'raw_unique': 0, 'verified': 0,
            'rejected': 0, 'inserted': 0, 'updated': 0, 'analyzed': 0, 'events': 0,
            'results': [{'stage': 'acquisition_plan', 'status': 'blocked',
                         'code': 'ACQUISITION_PLAN_BLOCKED',
                         'message': query_plan.reason or query_plan.reason_code}],
            'query_plan': query_plan_payload,
            'network_status': network_adaptive.get_network_status(),
            'cache_status': cache_manager.get_cache_status(),
            'blocked': query_plan.reason or query_plan.reason_code,
            'active_account': None, 'active_user_id': None,
            'allowed_accounts': [],
            'finished_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    # Typed persistence: the XHS writer persists CTH scope only. Non-CTH (BMP)
    # queries are deferred (reported, not dropped silently) instead of blocking
    # every CTH target in the same plan.
    deferred_queries = [q for q in query_plan.queries if q.domain_id != 'CTH']
    if deferred_queries:
        import dataclasses as _dc
        _cth = tuple(q for q in query_plan.queries if q.domain_id == 'CTH')
        query_plan = _dc.replace(query_plan, queries=_cth)
        if not _cth and keywords is None:
            # Page held only deferred BMP targets: collect the CTH registry page instead of idling.
            import subject_registry as _sr
            from lumenis.system.collector.acquisition_plan import (
                build_acquisition_plan as _bap,
            )
            query_plan = _bap(None, registry_loader=lambda: _sr.list_subjects('CTH'))
        query_plan_payload = dict(query_plan_payload or {})
        query_plan_payload['deferred_non_cth'] = [
            {'keyword': q.keyword, 'domain_id': q.domain_id,
             'reason': 'XHS_TYPED_SCOPE_IMPORT_REQUIRED'} for q in deferred_queries]
    plan_domains = {query.domain_id for query in query_plan.queries}
    if not plan_domains or any(domain != 'CTH' for domain in plan_domains):
        return {
            'ok': False, 'task_state': 'BLOCKED', 'state_counts': {},
            'keywords': list(query_plan.keywords), 'raw_unique': 0,
            'verified': 0, 'rejected': 0, 'inserted': 0, 'updated': 0,
            'analyzed': 0, 'events': 0,
            'results': [{'stage': 'scope_persistence', 'status': 'blocked',
                         'code': 'XHS_TYPED_SCOPE_IMPORT_REQUIRED',
                         'message': 'XHS legacy writer cannot persist non-CTH scope safely'}],
            'query_plan': query_plan_payload,
            'network_status': network_adaptive.get_network_status(),
            'cache_status': cache_manager.get_cache_status(),
            'blocked': 'XHS_TYPED_SCOPE_IMPORT_REQUIRED',
            'active_account': None, 'active_user_id': None,
            'allowed_accounts': [],
            'finished_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    resolved_account = account or DEFAULT_COLLECTION_ACCOUNT
    policy_gate = collection_policy_gate(account=resolved_account, region='intl')
    if not policy_gate.get('ok'):
        requested_keywords = list(dict.fromkeys(query_plan.keywords))
        return {
            'ok': False, 'task_state': 'POLICY_BLOCKED', 'state_counts': {},
            'keywords': requested_keywords, 'raw_unique': 0, 'verified': 0,
            'rejected': 0, 'inserted': 0, 'updated': 0, 'analyzed': 0, 'events': 0,
            'results': [{'stage': 'collection_policy', 'status': 'blocked',
                         'code': policy_gate.get('code'), 'message': policy_gate.get('reason')}],
            'network_status': network_adaptive.get_network_status(),
            'cache_status': cache_manager.get_cache_status(),
            'blocked': policy_gate.get('reason'), 'collection_policy': policy_gate,
            'active_account': resolved_account, 'active_user_id': None,
            'allowed_accounts': [],
            'finished_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    ok_sel, msg_sel = select_account(resolved_account)
    if not ok_sel:
        raise RuntimeError(f"[XHS生产身份门控] {msg_sel}")
    # ── 统一采集前置门：自动 create_task / collector_automation / p0_orchestrator 三条生产路径
    #     最终都汇聚到本函数，在此一处收口，确保“用户暂停”对所有采集一视同仁、零平台请求（测试模式旁路）──
    if not is_test_mode():
        _p = is_user_paused()
        if _p:
            _msg = f"采集已由用户暂停（{_p.get('reason','')}），本轮不发起任何平台请求"
            return {'ok':True,'task_state':'USER_PAUSED','state_counts':{},
                    'keywords':list(dict.fromkeys(keywords or DEFAULT_KEYWORDS)),
                    'raw_unique':0,'verified':0,'rejected':0,'inserted':0,'updated':0,'analyzed':0,'events':0,
                    'results':[{'stage':'user_paused','message':_msg}],
                    'network_status':network_adaptive.get_network_status(),
                    'cache_status':cache_manager.get_cache_status(),'blocked':_msg,
                    'active_account':resolved_account,'active_user_id':None,
                    'allowed_accounts': [resolved_account] if policy_gate.get('ok') is True else [],
                    'collection_policy':policy_gate,
                    'finished_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    if not cookie_configured():
        raise RuntimeError(f'未配置本机香港/国际 XHS Cookie。请在 {ACCOUNT_PROFILES[resolved_account][0]} 导入合法登录态。')
    keywords=list(dict.fromkeys(query_plan.keywords))[:32]
    raw={}; results=[]; blocked={}; state_counts={}
    _consec_bad=0  # 连续被拦截/失败计数（成功或空结果清零），达到阈值即提前结束本轮保护账号
    for _ki, kw in enumerate(keywords):
        r=_run_search(kw,max_scroll)
        st=r.get('state') or ('SUCCESS' if r.get('total',0)>0 else 'NETWORK_ERROR')
        state_counts[st]=state_counts.get(st,0)+1
        results.append({'keyword':kw,'fetched':r.get('total',0),'state':st,'error':r.get('error',''),'blocked':r.get('blocked_reason','')})
        _write_collection_log(kw, r.get('total',0), st, (r.get('blocked_reason') or r.get('error_code') or r.get('error') or '')[:200])
        br=r.get('blocked_reason')
        if br: blocked[br]=blocked.get(br,0)+1
        # 连续拦截/网络失败早停：已在被风控时继续打只会加重，立即结束本轮（半数熔断仍在下方统一判定）
        if st in ('SUCCESS','EMPTY'):
            _consec_bad=0
        else:
            _consec_bad+=1
            if _consec_bad>=EARLY_STOP_CONSECUTIVE and not is_test_mode():
                results.append({'stage':'early_stop','reason':f'连续{_consec_bad}个关键词被拦截/失败，提前结束本轮以保护账号'})
                break
        # 仅在真正成功/空结果态收集笔记；被拦截态 notes 必为空，双保险防止把故障当数据
        if st in ('SUCCESS','EMPTY'):
            for n in r.get('notes',[]):
                nid=str(n.get('note_id') or '').strip()
                if nid:
                    n['source_keyword']=kw; raw.setdefault(nid,n)
        # 词间最小拟人间隔（末词不等）：复用 network_adaptive 延迟并设下限 + 随机抖动，避免固定节奏/过密
        if _ki < len(keywords)-1 and not is_test_mode():
            _gap=max(KEYWORD_GAP_MIN_SEC, int(network_adaptive.get_adaptive_settings().get('current_delay_seconds',2)))
            time.sleep(_gap+random.randint(0,KEYWORD_GAP_JITTER_SEC))
    # 若多数关键词被风控/登录墙拦截，上报网络自适应并在结果中明确标注（不再伪装成“0 条新笔记”）
    blocked_summary = ''
    if blocked:
        top_block=max(blocked,key=blocked.get)
        label={'IP_RISK_OR_CAPTCHA':'IP存在风险/出现验证码，已被小红书安全拦截','LOGIN_REQUIRED':'登录态失效，需要重新登录','EMPTY_NO_API':'未收到搜索接口响应（可能被风控）'}.get(top_block,top_block)
        blocked_summary=f'{label}（{sum(blocked.values())}/{len(keywords)} 个关键词被拦截）'
        try:
            network_adaptive.report_collection_result(False, risk_info={'type':top_block,'is_risk':True})
        except Exception:
            pass
        results.append({'stage':'blocked','reason':top_block,'detail':blocked_summary})
        if top_block=='LOGIN_REQUIRED' and not is_test_mode():
            # PO rule 2026-10-13 #1: in-product login popup, then resume this task.
            try:
                from lumenis.adapters import auth_recovery as _ar
                _rec = _ar.request_recovery('xiaohongshu', 'LOGIN_REQUIRED', blocked_summary)
                if isinstance(_rec, dict) and _rec.get('success'):
                    # Resume re-enters the guarded task path (admission, rate limit, policy).
                    _ar.register_resume('xiaohongshu', lambda _k=list(keywords), _s=max_scroll, _a=account: create_task(keywords=_k, max_scroll=_s, run_type='manual', account=_a))
                    results.append({'stage':'auth_recovery','status':'LOGIN_POPUP_REQUESTED','resume':'queued'})
                else:
                    results.append({'stage':'auth_recovery','status':'RECOVERY_UNAVAILABLE','error':(_rec or {}).get('error') if isinstance(_rec, dict) else None})
            except Exception as _exc:
                results.append({'stage':'auth_recovery','status':'FAILED','error':type(_exc).__name__})
    inserted=updated=rejected=0
    queries_by_keyword = {}
    for query in query_plan.queries:
        scope = _canonical_query_scope(query)
        key = _scope_key(scope)
        if key is not None:
            queries_by_keyword.setdefault(query.keyword, {})[key] = query
    persisted_by_keyword_scope = {}
    for n in raw.values():
        keyword = n.get('source_keyword')
        matching = queries_by_keyword.get(keyword, {})
        if len(matching) != 1:
            ok = False
            reason = 'SCOPE_AMBIGUOUS' if matching else 'SCOPE_REQUIRED'
            query = None
        else:
            scope_key, query = next(iter(matching.items()))
            ok,reason=_verify_note_for_query(n, query)
        n['is_taikoo_verified']=1 if ok else 0; n['verify_reason']=reason; n['source_platform']='xhs'
        if not ok: rejected+=1; continue
        n['captured_at']=str(n.get('captured_at') or n.get('collected_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        _,new=db.insert_note(n); inserted+=int(new); updated+=int(not new)
        _record_note_lineage(n, provider='xhs_cookie_bridge')
        persisted_by_keyword_scope.setdefault((keyword, scope_key), []).append(n['note_id'])
    scope_bindings = []
    from lumenis.system.collector.adapters.secondary_collection import bind_collected_social_scope
    binding_groups = {}
    for query in query_plan.queries:
        scope = _canonical_query_scope(query)
        key = _scope_key(scope)
        if key is not None:
            binding_groups.setdefault((query.keyword, key), (query, scope))
    for (keyword, key), (query, scope) in binding_groups.items():
        ids = persisted_by_keyword_scope.get((keyword, key), [])
        if ids:
            try:
                binding = bind_collected_social_scope(
                    ids, scope=scope, platform='xhs', keyword=query.keyword,
                    provider='xhs_cookie_bridge',
                )
            except Exception as exc:
                binding = {'ok': False, 'status': 'SCOPE_BINDING_FAILED',
                           'error_type': type(exc).__name__}
            scope_bindings.append(binding)
    analyzed=0
    events=[]
    try:
        import reprocess
        query_groups, rows_by_scope, skipped_scopes, read_failures = _load_scoped_pending_analysis(query_plan)
        scopes = {key: group['scope'] for key, group in query_groups.items()}
        analyzed = sum(len(rows) for _, rows in rows_by_scope.values())
        if skipped_scopes:
            results.append({'stage': 'analysis', 'status': 'NOT_RUN',
                            'code': 'SCOPE_REQUIRED', 'queries': skipped_scopes})
        for key, error_type in read_failures:
            results.append({'stage': 'analysis', 'status': 'FAILED',
                            'scope': key, 'code': 'SCOPED_READ_FAILED',
                            'error_type': error_type})

        if scopes:
            def _async_analyze_and_events():
                _run_scoped_postprocess(rows_by_scope, scopes, reprocess, results)

            threading.Thread(target=_async_analyze_and_events, daemon=True,
                             name='ai-analysis-events').start()
            results.append({'stage': 'ai_analysis', 'status': 'async_started',
                            'analyzed': analyzed, 'scope_count': len(scopes)})
        else:
            results.append({'stage': 'ai_analysis', 'status': 'NOT_RUN',
                            'code': 'SCOPE_REQUIRED'})
    except Exception as e:
        results.append({'stage':'post_process','error':str(e)})
    
    # 网络自适应：报告采集结果
    total_new = inserted + updated
    if total_new > 0:
        network_adaptive.report_collection_result(True, notes_count=total_new)
        # 成功采集后创建缓存快照
        try:
            cache_result = cache_manager.create_snapshot()
            results.append({'stage':'cache_snapshot','success':cache_result.get('success',False)})
        except Exception as e:
            results.append({'stage':'cache_snapshot','error':str(e)})
    else:
        network_adaptive.report_collection_result(False, notes_count=0)
    
    # 获取当前网络状态
    net_status = network_adaptive.get_network_status()

    # ===== 任务级六态汇总（关键：被拦截不等于“0 条正常”）=====
    n=len(keywords)
    n_ok=state_counts.get('SUCCESS',0); n_empty=state_counts.get('EMPTY',0)
    n_block=state_counts.get('BLOCKED',0)+state_counts.get('CAPTCHA',0)+state_counts.get('AUTH_FAILED',0)
    n_neterr=state_counts.get('NETWORK_ERROR',0)
    if n_ok==n: task_state='SUCCESS'
    elif (n_ok+n_empty)==n and n_ok==0: task_state='EMPTY'
    elif n_ok>0 and (n_block+n_neterr)>0: task_state='PARTIAL_BLOCKED'
    elif n_block==n: task_state='BLOCKED'
    elif (n_block+n_neterr)==n: task_state='NETWORK_ERROR'
    elif n_ok==0 and n_empty>0: task_state='EMPTY'
    else: task_state='PARTIAL_BLOCKED'
    # 半数以上关键词被拦截/失败：熔断自动调度（测试模式不熔断，便于端到端验证）
    if not is_test_mode() and (n_block+n_neterr) >= max(1, n//2):
        top=blocked_summary or task_state
        _trip_circuit(task_state, top, cool_minutes=_adaptive_cool_minutes())
    elif task_state=='SUCCESS':
        clear_circuit()

    return {
        'ok':all(item.get('ok') for item in scope_bindings),
        'task_state':task_state,
        'state_counts':state_counts,
        'keywords':keywords,
        'raw_unique':len(raw),
        'verified':len(raw)-rejected,
        'rejected':rejected,
        'inserted':inserted,
        'updated':updated,
        'analyzed':analyzed,
        'events':len(events),
        'results':results,
        'network_status': net_status,
        'cache_status': cache_manager.get_cache_status(),
        'blocked': blocked_summary,
        # ── 双子星库 Contract 身份证据链（写入所有 sync 返回，方便追溯哪条数据由哪个身份采集）──
        'active_account': resolved_account,
        'active_user_id': None,
        'allowed_accounts': [],
        'collection_policy': policy_gate,
        'query_plan': query_plan_payload,
        'scope_bindings': scope_bindings,
        'finished_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def _shadow_record_result(task_state, items_found, blocked='', run_type='auto'):
    """v5.8.6 动态调度影子闭环：把本次真实采集状态回写统一规划器。
    仅演进影子状态/写审计，不门控、不影响采集，任何异常 fail-open；AI 不参与此决策。"""
    try:
        from lumenis.system.collector.adapters.scheduling import get_planner
        _map = {'EMPTY': 'NO_NEW_DATA', 'PARTIAL_BLOCKED': 'RISK_WARNING', 'SUCCESS': 'SUCCESS'}
        raw = _map.get(task_state, task_state)
        planner = get_planner()
        planner.record_result('xhs', raw, now=datetime.now(),
                              items_found=int(items_found or 0),
                              error_code=str(blocked or '')[:120],
                              trigger_source=f'xhs-{run_type}')
    except Exception as e:
        print('[xhs-bridge] shadow record skipped:', e, flush=True)


def create_task(keywords=None,max_scroll=6,run_type='manual',account=None):
    """创建采集任务
    run_type: 'manual'（一键实时更新）或 'auto'（定时自动采集）
    """
    if run_type not in ('manual', 'auto'):
        raise ValueError("run_type must be 'manual' or 'auto'")

    # Resolve registry-owned scope before account/profile/rate-limit work.
    query_plan = (_resolve_registry_page(keywords) if run_type == 'auto'
                  else _resolve_acquisition_plan(keywords))
    if not query_plan.is_runnable:
        raise RuntimeError(
            f"采集计划未就绪：{query_plan.reason_code or query_plan.reason or 'ACQUISITION_PLAN_BLOCKED'}"
        )
    keywords = list(dict.fromkeys(query_plan.keywords))[:32]
    query_plan_payload = query_plan.to_dict()

    if run_type == 'auto':
        try:
            from lumenis.system.collector.adapters import rednote_policy
            auto_opted_in = rednote_policy.automatic_collection_opt_in_enabled()
        except Exception as exc:
            raise RuntimeError('Automatic collection is blocked because SYSTEM policy is unavailable') from exc
        if not auto_opted_in:
            raise RuntimeError(
                'Automatic collection is blocked until REDNOTE_AUTO_RUN, '
                'REDNOTE_AUTO_SCOPE, REDNOTE_AUTO_SOURCE, and '
                'REDNOTE_AUTO_CADENCE_MINUTES explicitly match the authorized schedule'
            )
    resolved_account = account or DEFAULT_COLLECTION_ACCOUNT
    policy_gate = collection_policy_gate(account=resolved_account, region='intl')
    if not policy_gate.get('ok'):
        raise RuntimeError(f"采集策略门禁：{policy_gate.get('reason', '当前账号/区域不允许生产采集')}")
    ok_sel, msg_sel = select_account(resolved_account)
    if not ok_sel:
        raise RuntimeError(f'[XHS生产身份门控] {msg_sel}')
    # 用户主动暂停期间，手动/自动一律不发起平台请求（测试模式旁路），保护账号，直到用户显式恢复
    _paused = is_user_paused()
    if _paused and not is_test_mode():
        raise RuntimeError(f"小红书采集已手动暂停（{_paused.get('reason','')}，{_paused.get('at','')}）。请恢复后再采集。")
    # 账号白名单验证
    account_ok, account_msg = verify_account()
    if not account_ok:
        raise RuntimeError(f'账号验证失败：{account_msg}')
    # 频率限制检查（区分手动/自动）；测试模式旁路，便于端到端连续验证
    if not is_test_mode():
        rate_ok, rate_msg = check_rate_limit(run_type)
        if not rate_ok:
            raise RuntimeError(f'频率限制：{rate_msg}')
    # 自动任务在熔断期直接跳过（手动/测试模式可强制，用于恢复健康检查）
    circ=get_circuit_state()
    if run_type=='auto' and circ.get('open') and not is_test_mode():
        raise RuntimeError(f'采集熔断中（{circ.get("state")}），自动任务暂停至 {circ.get("resume_at")}')
    # 新账号保护：前N次强制极轻量模式（测试模式旁路）
    today = datetime.now().strftime('%Y-%m-%d')
    today_runs = len([t for t in _daily_runs if datetime.fromtimestamp(t).strftime('%Y-%m-%d') == today])
    if today_runs < NEW_ACCOUNT_GUARD_RUNS and not is_test_mode():
        max_scroll = min(max_scroll, 2)
        guard_msg = f'（新账号保护：第{today_runs+1}/{NEW_ACCOUNT_GUARD_RUNS}次，强制极轻量模式max_scroll={max_scroll}）'
    else:
        guard_msg = '（测试模式：已旁路冷却/新账号保护）' if is_test_mode() else ''
    type_label = '手动触发' if run_type == 'manual' else '自动采集'
    if not _lock.acquire(blocking=False): raise RuntimeError('已有小红书 Cookie 同步任务运行中')
    if run_type == 'auto':
        _save_plan_cursor(getattr(query_plan, 'next_cursor', None))  # advance only after admission
    task_id=f"xhs-{datetime.now():%Y%m%d%H%M%S}-{int(time.time()*1000)%1000:03d}"
    _tasks[task_id]={
        'task_id':task_id,'status':'running','progress':5,'run_type':run_type,
        'account':resolved_account,'collection_policy':policy_gate,
        'query_plan':query_plan_payload,
        'message':f'[{type_label}]正在按 Registry 采集计划检索 RedNote…{guard_msg}',
        'created_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    def worker():
        _w_start=time.time()
        try:
            record_run(run_type)  # 记录运行（区分手动/自动）
            _tasks[task_id].update(progress=20,message=f'[{type_label}]按采集计划搜索已授权关键词…{guard_msg}')
            result=sync(keywords,max_scroll,account=resolved_account)
            ts=result.get('task_state','SUCCESS')
            if ts=='USER_PAUSED':
                # 用户主动暂停：不回写 planner/adaptive（非网络成败、不触发退避），直接收尾且零请求
                _tasks[task_id].update(status='done',progress=100,message='采集处于用户暂停态，本轮未发起任何请求',result=result,finished_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                return
            if ts in ('BLOCKED','PARTIAL_BLOCKED','NETWORK_ERROR','AUTH_FAILED','CAPTCHA'):
                done_msg=f'[{type_label}]采集未完成（{STATE_LABEL.get(ts,ts)}）：{result.get("blocked") or "多数关键词未取得响应"}。本次不计为0条，自动任务已按策略熔断/降频'
            elif ts=='EMPTY':
                done_msg=f'[{type_label}]采集成功但本批无新笔记（接口正常）'
            else:
                done_msg=f'[{type_label}]小红书同步完成（新增{result.get("inserted",0)}、更新{result.get("updated",0)}）'
            if result.get('blocked') and ts=='SUCCESS':
                done_msg=f'[{type_label}]未采集到新笔记：{result["blocked"]}（已自动降频，建议切换网络或稍后重试）'
            _tasks[task_id].update(status='done',progress=100,message=done_msg,result=result,finished_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            # v5.8.6 真实结果回写动态调度影子（不门控、不影响采集）
            try:
                _shadow_record_result(ts, result.get('inserted',0)+result.get('updated',0),
                                      result.get('blocked') or '', run_type)
            except Exception as _be:
                print('[xhs-bridge] shadow feedback non-blocking:', _be, flush=True)
            # adaptive_engine 结果回写：滑动窗口成功率自动调整策略/参数
            try:
                import adaptive_engine as _ae
                _ae.adaptive_engine.report_collection_result(
                    success=(ts == 'SUCCESS'),
                    notes_count=int(result.get('inserted',0))+int(result.get('updated',0)),
                    duration=round(time.time()-_w_start, 1),
                    error=result.get('blocked') or (None if ts=='SUCCESS' else ts))
            except Exception as _ae_e:
                print('[xhs-bridge] adaptive feedback non-blocking:', _ae_e, flush=True)
        except Exception as e:
            _tasks[task_id].update(status='error',progress=100,message=str(e),error=str(e))
            # D2 动态调度闭环补齐：sync 未兜住的异常也要回写统一规划器（归一 NETWORK_ERROR 走退避），
            # 否则 planner 的 last_run/动态间隔不更新，enforce 门控可能在异常后仍按原间隔高频重试。
            # 与成功/受控失败路径(905-910)一致，fail-open，AI 不参与此决策。
            try:
                _shadow_record_result('NETWORK_ERROR', 0, str(e), run_type)
            except Exception:
                pass
            try:
                import adaptive_engine as _ae
                _ae.adaptive_engine.report_collection_result(
                    success=False, notes_count=0,
                    duration=round(time.time()-_w_start, 1), error=str(e))
            except Exception:
                pass
        finally: _lock.release()
    threading.Thread(target=worker,daemon=True,name='xhs-cookie-sync').start()
    return task_id

def get_task(task_id): return _tasks.get(task_id)
