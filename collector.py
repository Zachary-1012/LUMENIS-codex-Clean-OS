"""
广州太古汇舆情监测系统 - RedNote 采集模块
使用 rednote-cli 浏览器实例 + 自定义 Playwright 搜索脚本
采集小红书广州太古汇相关笔记
"""
import subprocess
import json
import os
import re
import sys
import time
from datetime import datetime

# Runtime Guardian 旁路接入（ZBC-PHASE2-RUNTIME-GUARDIAN Shard B）
try:
    import runtime_guardian as _runtime_guardian
    _RG_AVAILABLE = True
except Exception:
    _runtime_guardian = None
    _RG_AVAILABLE = False

# RedNote 采集策略 SoT 旁路接入（阶段5 集中策略）：香港/国际主链 + 内地暂停
# 这是生产采集入口的硬门禁；策略模块缺失时必须拒绝，不得 fail-open。
try:
    from platform_adapters import rednote_policy as _rednote_policy
    _REDNOTE_POLICY_AVAILABLE = True
except Exception:
    _rednote_policy = None
    _REDNOTE_POLICY_AVAILABLE = False

# 统一 Node 解析（PATH 优先，项目内置 nodejs/ 兜底），避免常驻进程 PATH 缺 node 抛 WinError 2
try:
    from runtime_bin import resolve_node as _resolve_node
    _NODE_BIN = _resolve_node() or 'node'
except Exception:
    _NODE_BIN = 'node'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
def _resolve_search_script():
    # xhs_search_v2.js 为首选；若该文件缺失（历史上曾丢失导致 0 条），回退到参数/输出契约一致的
    # 现存 xhs_search.js（独立持久化 Chromium 通道），保证主采集链不因单文件缺失而整体空跑。
    for _name in ('xhs_search_v2.js', 'xhs_search.js'):
        _p = os.path.join(SCRIPT_DIR, _name)
        if os.path.exists(_p):
            return _p
    return os.path.join(SCRIPT_DIR, 'xhs_search_v2.js')  # 保留原名以便错误可定位
SEARCH_SCRIPT = _resolve_search_script()
INSTANCE_NAME = 'taikoo'

# 监测关键词组
MONITOR_KEYWORDS = [
    '广州太古汇',
    '太古汇 投诉',
    '太古汇 避雷',
    '太古汇 活动',
    '太古汇 新店',
    '太古汇 方所',
    '太古汇 停车',
]

def _check_profile_lock():
    """检查持久化 Chromium profile 是否可能被其他进程占用。

    旧版会直接删除 SingletonLock/SingletonCookie/SingletonSocket。
    这在 Windows 上尤其危险：如果另一个 Chromium 实例正在使用 profile，
    强删锁文件可能导致 profile 损坏或两个浏览器同时写入。现在只做检测，
    真正的锁冲突交给 Playwright 返回错误。
    """
    lock_dir = os.path.expanduser('~/.skills-router/rednote/instances/taikoo')
    return any(os.path.exists(os.path.join(lock_dir, f)) for f in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'))

# CDP 真人通道（9223 香港/国际 RedNote；仅复用已登录的本机驻场实例）
CDP_URL = os.getenv('XHS_CDP_URL', 'http://127.0.0.1:9223')
CDP_SCRIPT = os.path.join(SCRIPT_DIR, 'xhs_cdp_collector.py')  # Python Playwright CDP 真人通道
CDP_NODE_FALLBACK = os.path.join(SCRIPT_DIR, 'rednote_collector.cjs')  # 备用 node 通道
# 明确风控态：这些不是“0条舆情”，上层必须据此熔断/转 AUTH&VERIFY，不得当成正常空结果
_CDP_RISK_STATES = ('IP_RISK_OR_300012', 'NEED_VERIFY')


_XHS_GUARD = None
_XHS_RISK = None


def _collection_policy_gate(region=None, account=None):
    """返回生产采集门禁结果；策略不可用时按安全边界拒绝。"""
    if not _REDNOTE_POLICY_AVAILABLE:
        return {
            'ok': False, 'code': 'policy_unavailable',
            'reason': 'RedNote生产策略模块不可用，拒绝进入采集主链',
        }
    try:
        from xhs_cookie_bridge import DEFAULT_COLLECTION_ACCOUNT
        return _rednote_policy.collection_gate(
            account=account or DEFAULT_COLLECTION_ACCOUNT,
            region=region or 'intl',
        )
    except Exception as exc:
        return {
            'ok': False, 'code': 'policy_error',
            'reason': f'RedNote生产策略判定失败，拒绝进入采集主链: {exc}',
        }


def _collection_env(account=None, region='intl', cdp_url=None):
    """为下游适配器注入同一账号/区域契约，不包含 Cookie 内容。"""
    env = os.environ.copy()
    env['XHS_COLLECTION_REGION'] = region or 'intl'
    env['XHS_COLLECTION_HOST'] = 'www.rednote.com' if env['XHS_COLLECTION_REGION'] == 'intl' else 'www.xiaohongshu.com'
    if cdp_url:
        env['XHS_CDP_URL'] = cdp_url
    try:
        from xhs_cookie_bridge import ACCOUNT_PROFILES, DEFAULT_COLLECTION_ACCOUNT
        selected = account or DEFAULT_COLLECTION_ACCOUNT
        profile = ACCOUNT_PROFILES.get(selected)
        if profile and profile[0]:
            env['XHS_COOKIE_FILE'] = str(profile[0])
    except Exception:
        pass
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    return env


def _get_xhs_guard():
    """懒加载小红书采集保护层（CollectorGuard），避免无条件 import 影响其它通道。"""
    global _XHS_GUARD
    if _XHS_GUARD is None:
        from collector_guard.guard import CollectorGuard
        enabled = os.getenv('TAIKOO_COLLECTOR_GUARD', '1').lower() not in ('0', 'false', 'no', 'off')
        base = float(os.getenv('XHS_GUARD_BASE_INTERVAL', '6'))
        _XHS_GUARD = CollectorGuard('xiaohongshu', enabled=enabled, base_interval=base)
    return _XHS_GUARD


def _get_xhs_risk_engine():
    """懒加载连续风险评分引擎（P1-4 接入）。

    与 CollectorGuard 的离散七态互补：RiskEngine 给出 0-100 连续风险分并随
    成功/健康响应衰减、随时间回落，当风险档位进入 COOLDOWN/CIRCUIT_OPEN 时
    触发熔断，避免单一信号漏判导致无限重试。
    默认开启（TAIKOO_RISK_ENGINE=0/false 关闭，关闭时行为与原链路完全一致）。
    """
    global _XHS_RISK
    if _XHS_RISK is None:
        enabled = os.getenv('TAIKOO_RISK_ENGINE', '1').lower() not in ('0', 'false', 'no', 'off')
        if enabled:
            from collector_guard.risk_engine import RiskEngine
            # T-P0A-1: 熔断/冷却状态跨进程重启持久化（data/collector_* 已 gitignore，不入库）
            _risk_state = os.path.join('data', 'collector_guard', 'xhs_risk_state.json')
            _XHS_RISK = RiskEngine(state_file=_risk_state)
        else:
            _XHS_RISK = False
    return _XHS_RISK or None


# 采集结果六态 -> RiskEngine 风险因子（BLOCKED/CAPTCHA/AUTH 为硬信号，NETWORK 累加；
# SUCCESS/EMPTY 属正常响应，不加分；EMPTY 与真实无内容一致，交给 guard 节流）
_RISK_FACTOR_BY_STATE = {
    'BLOCKED': 'security_page',
    'CAPTCHA': 'security_page',
    'AUTH_REQUIRED': 'login_error',
    'NETWORK_ERROR': 'http_error',
}


def _feed_risk_engine(risk, *, error, guard_state, count, kw, is_core, results):
    """把单次关键词采集结果喂给 RiskEngine（P1-4 接入）。

    返回 True 表示风险引擎判定熔断，调用方应停止后续关键词请求。
    risk 为 None（Feature Flag 关闭）时恒返回 False，不改变原链路行为。
    """
    if risk is None:
        return False
    state = classify_collect_state(error=error, guard_state=guard_state, count=count)
    factor = _RISK_FACTOR_BY_STATE.get(state)
    if factor:
        score, band, st = risk.record_failure(factor)
    elif state == 'EMPTY':
        # EMPTY 不衰减风险分：无法区分"真无内容"与"软风控空响应"，保持当前风险分不变
        # （智谱采集链审查 P0-C 加固：避免空结果被视为成功而提前解除熔断）
        score, band, st = risk.score, risk._last_band, risk.lifecycle_state()
    else:
        score, band, st = risk.record_success()
    snap = risk.snapshot()
    if snap['should_stop_request']:
        # RiskEngine熔断联动guard.limiter.force_pause（P0-C加固：避免两套熔断系统脱节）
        try:
            from collector_guard.state import CollectState
            _guard = _get_xhs_guard()
            if _guard and hasattr(_guard, 'limiter'):
                _guard.limiter.force_pause(CollectState.PAUSED, cooldown_seconds=max(300, risk.reset_timeout))
        except Exception as _link_err:
            print(f"[Collector]   RiskEngine联动limiter失败(忽略): {_link_err}")
        results.append({
            'keyword': kw, 'count': count,
            'error': error or '', 'guard_state': guard_state or '',
            'risk_score': snap['risk_score'], 'risk_band': snap['band'],
            'tier': 'core' if is_core else 'expand',
        })
        print(f"[Collector]   !! 风险引擎熔断({snap['band']}, score={snap['risk_score']})，停止后续关键词请求")
        return True
    # P1-A：ResourceGuard 资源/效率层联动——消费 lifecycle_action(六态) -> 四态 -> 调度停止
    from collector_guard.schedule_adapter import schedule_state, should_stop_schedule
    if should_stop_schedule(snap.get('lifecycle_action')):
        results.append({
            'keyword': kw, 'count': count,
            'error': error or '', 'guard_state': guard_state or '',
            'risk_score': snap.get('risk_score'), 'risk_band': snap.get('band'),
            'schedule_state': schedule_state(snap.get('lifecycle_action')),
            'tier': 'core' if is_core else 'expand',
        })
        print(f"[Collector]   !! 资源/效率守卫({snap.get('lifecycle_action')})，停止后续关键词请求")
        return True
    return False


def _cdp_online(timeout=2.0, cdp_url=None):
    """探测 CDP 是否在线（默认9223香港/国际；不启动浏览器，只探测）。"""
    import urllib.request
    _url = (cdp_url or CDP_URL)

    def _probe():
        with urllib.request.urlopen(_url + '/json/version', timeout=timeout) as r:
            return getattr(r, 'status', 200) == 200

    # P1-2 tenacity 可选增强：CDP 探测偶发瞬断（瞬时抖动）时指数退避重试，
    # 避免把「瞬时抖动」误判为「浏览器掉线」而触发不必要的浏览器拉起。
    # 纯本机 CDP HTTP 探测，零风控风险；仅网络层，不碰平台风控决策。
    try:
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        import urllib.error
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, min=0.2, max=1.2),
               retry=retry_if_exception_type((urllib.error.URLError, OSError, TimeoutError)),
               reraise=True)
        def _probe_retry():
            return _probe()
        try:
            return bool(_probe_retry())
        except Exception:
            return False
    except ImportError:
        # tenacity 未安装（可选依赖）：回落原生单次探测，保持「无重依赖全链可跑」
        try:
            return bool(_probe())
        except Exception:
            return False


def _ensure_cdp_online(timeout=30):
    """香港/国际真人通道掉线时尝试拉起持久 Edge；拉起失败返回 False，由上层走兜底。"""
    import time as _time
    if _cdp_online():
        return True
    try:
        from collector_automation import CollectorAutomation
        ctrl = CollectorAutomation(base_dir=SCRIPT_DIR)
        print('[Collector] 9223 不在线，尝试自动拉起香港/国际真人采集浏览器 ...')
        ctrl.start_browser(account='default', headless=False)  # 内部已等待 CDP 就绪
        for _ in range(timeout):
            if _cdp_online():
                print('[Collector] 9223 已自动拉起并就绪')
                return True
            _time.sleep(1)
    except Exception as e:
        print('[Collector] 自动拉起 9223 失败:', e)
    return _cdp_online()


def _norm_cdp_note(rec):
    """把 rednote_collector.cjs 的详情记录映射为 collector/insert_note 标准字段。"""
    pub = rec.get('detail_publish_time') or rec.get('publish_time') or rec.get('publish_datetime') or ''
    m = re.match(r'(\d{4}-\d{2}-\d{2})', str(pub))
    publish_date = m.group(1) if m else ''
    _title = rec.get('detail_title') or rec.get('title') or ''
    _desc = rec.get('desc') or rec.get('content') or ''
    if not _title and _desc:
        # 详情标题偶发缺失：用正文首个非空行兜底（截断 40 字），保证入库标题不留空
        for _line in str(_desc).splitlines():
            _line = _line.strip(' \t\r\n　')
            if _line:
                _title = _line[:40]
                break
    def _int(v):
        try: return int(v or 0)
        except Exception: return 0
    return {
        'note_id': rec.get('note_id', ''),
        'title': _title,
        'content': _desc,
        'url': rec.get('url', ''),
        'cover': rec.get('cover', ''),
        'author_id': rec.get('author_id', ''),
        'author_nickname': rec.get('detail_author') or rec.get('author') or rec.get('author_nickname') or '',
        'likes': _int(rec.get('likes')),
        'comments': _int(rec.get('comments')),
        'collects': _int(rec.get('collects')),
        'shares': _int(rec.get('shares')),
        'publish_date': publish_date,
        # 双时间铁律：publish_date 来自平台发布时间；captured_at 是本机采集时刻，来源不同。
        # 显式落采集时刻，不依赖下游 insert_note 的隐式兜底（智谱采集链审查 P0-C 加固）。
        'captured_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'xsec_token': rec.get('xsec_token', ''),
        'source_channel': 'cdp_edge_9223',
        'quality_status': rec.get('quality_status', ''),
        'subject_hit_cdp': rec.get('subject_hit'),
        'comment_list': rec.get('comment_list', []),
    }


def _search_via_cdp(keyword, max_scroll, output_path, max_details=10, cdp_url=None, region=None, account=None):
    """走已登录 Edge 的 rednote_collector.cjs，返回与独立通道一致的 dict 结构。
    cdp_url: 9223=香港/国际intl；region/account 仅用于统一通道标记和 Cookie 路径。"""
    _cdp = cdp_url or CDP_URL
    env = _collection_env(account=account, region=region or 'intl', cdp_url=_cdp)
    py = sys.executable or 'python'
    cmd = [py, CDP_SCRIPT, '--keyword', keyword, '--output', output_path,
           '--max-scroll', str(max_scroll), '--max-details', str(max_details), '--cdp-url', _cdp]
    p = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding='utf-8', timeout=300, env=env)
    out = p.stdout or ''
    marker = '---RESULT_JSON---'
    raw = out.split(marker, 1)[1].strip() if marker in out else (out[out.find('{'):] if out.find('{') >= 0 else '')
    if not raw:
        return {'keyword': keyword, 'total': 0, 'notes': [],
                'error': ((p.stderr or out) or f'CDP exit {p.returncode}')[-800:], 'channel': 'cdp'}
    try:
        data = json.loads(raw)
    except Exception as e:
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': f'CDP结果解析失败: {e}', 'channel': 'cdp'}
    summ = data.get('summary', {}) or {}
    notes = [_norm_cdp_note(r) for r in data.get('notes', []) if r.get('note_id')]
    if summ.get('ip_blocked'):
        err = 'IP_RISK_OR_300012'
    elif summ.get('verification_required'):
        err = 'NEED_VERIFY'
    elif not notes and not data.get('ok'):
        err = 'CDP_EMPTY_OR_LOAD_FAILED'
    else:
        err = ''
    return {'keyword': keyword, 'total': len(notes), 'notes': notes, 'error': err,
            'channel': 'cdp', 'summary': summ, 'ok': bool(data.get('ok'))}


def _search_standalone(keyword, max_scroll, output_path, account=None, region='intl', cdp_url=None):
    """回退通道：独立持久化 Chromium（xhs_search.js）。无 CDP 时使用，headless 易被风控，仅作兜底。"""
    if not os.path.exists(SEARCH_SCRIPT):
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': f'搜索脚本缺失: {SEARCH_SCRIPT}', 'channel': 'standalone'}
    cmd = [_NODE_BIN, SEARCH_SCRIPT, '--keyword', keyword, '--output', output_path, '--max-scroll', str(max_scroll)]
    try:
        env = _collection_env(account=account, region=region, cdp_url=cdp_url)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or '').strip()
            return {'keyword': keyword, 'total': 0, 'notes': [], 'error': err[-800:] or f'Node exited with code {result.returncode}', 'channel': 'standalone'}
        stdout = result.stdout.strip()
        idx = stdout.find('{')
        if idx >= 0:
            data = json.loads(stdout[idx:]); data['channel'] = 'standalone'; return data
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': 'No JSON output', 'channel': 'standalone'}
    except subprocess.TimeoutExpired:
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': 'Timeout', 'channel': 'standalone'}
    except Exception as e:
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': str(e), 'channel': 'standalone'}


# 英文停用词/噪声（多来自 GDELT 等英文网页发现），对广州太古汇主体无意义，采集前剔除
_KEYWORD_STOPWORDS = {
    'the', 'a', 'an', 'of', 'and', 'or', 'to', 'in', 'on', 'at', 'for', 'is', 'are',
    'was', 'were', 'be', 'been', 'with', 'by', 'from', 'as', 'it', 'this', 'that',
    'these', 'those', 'you', 'your', 'we', 'they', 'he', 'she', 'his', 'her', 'their',
    'what', 'which', 'who', 'whom', 'how', 'why', 'when', 'where', 'can', 'could',
    'will', 'would', 'should', 'may', 'might', 'must', 'shall', 'about', 'into', 'over',
    'after', 'before', 'more', 'most', 'some', 'any', 'all', 'not', 'no', 'yes', 'news',
}


def _is_noise_keyword(k):
    k = (k or '').strip()
    if len(k) < 2:
        return True
    if re.fullmatch(r'[\d\W_]+', k):  # 纯数字/符号
        return True
    if k.lower() in _KEYWORD_STOPWORDS:
        return True
    return False


def search_xiaohongshu(keyword, max_scroll=4, output_path=None, max_details=10,
                        region=None, cdp_port=None, kos_only=False, account=None):
    """多通道搜索 RedNote：仅走香港/国际账号与 9223 入口。
    返回 dict: {keyword,total,notes,error,channel,region}。风控态显式返回，不当作普通0条。
    region: 当前生产值为 'intl'；'cn' 明确返回策略阻断，不触发任何下游进程。
    """
    policy_gate = _collection_policy_gate(region=region or 'intl', account=account)
    if not policy_gate.get('ok'):
        return {
            'keyword': keyword, 'total': 0, 'notes': [],
            'error': policy_gate.get('code', 'POLICY_BLOCKED'),
            'blocked_reason': policy_gate.get('reason', 'RedNote生产采集被策略阻断'),
            'channel': 'policy', 'region': region or 'intl',
            'policy': policy_gate,
        }
    if cdp_port is not None and int(cdp_port) != 9223:
        gate = dict(policy_gate)
        gate.update({'ok': False, 'code': 'cdp_port_not_allowed',
                     'reason': '当前生产采集仅允许香港/国际驻场端口9223'})
        return {
            'keyword': keyword, 'total': 0, 'notes': [],
            'error': gate['code'], 'blocked_reason': gate['reason'],
            'channel': 'policy', 'region': 'intl', 'cdp_port': cdp_port,
            'policy': gate,
        }
    region = 'intl'
    cdp_port = 9223
    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, 'data', f'search_{int(datetime.now().timestamp())}.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 选择器只返回当前允许的香港/国际入口；不再轮换或回落到大陆。
    if _REDNOTE_POLICY_AVAILABLE:
        sel = _rednote_policy.select_region(kos_only=kos_only, force_region='intl')
        region = sel['region']; cdp_port = sel['cdp_port']
    cdp_url = f'http://127.0.0.1:{cdp_port}'

    # Phase4: 浏览器模式门控 - external_standalone 时跳过CDP，直接走独立Chromium兜底
    _browser_mode = 'internal_cdp'
    try:
        import collector_browser_mode as _cbm
        _browser_mode = _cbm.get_browser_mode()
    except Exception:
        pass
    if _browser_mode == 'external_standalone':
        print('[Collector] 浏览器模式=external_standalone，使用香港/国际策略上下文的独立通道')
        return _search_standalone(keyword, max_scroll, output_path, account=account,
                                   region=region, cdp_url=cdp_url)

    # 主路径：CDP 真人通道
    try:
        if os.path.exists(CDP_SCRIPT) and _cdp_online(cdp_url=cdp_url):
            res = _search_via_cdp(keyword, max_scroll, output_path, max_details=max_details,
                                  cdp_url=cdp_url, region=region, account=account)
            res['region'] = region; res['cdp_port'] = cdp_port
            if res.get('notes') or res.get('error') in _CDP_RISK_STATES:
                return res  # 真出数 / 明确风控态都直接返回
            # CDP 非风控空结果，落兜底通道再试一次
            fb = _search_standalone(keyword, max_scroll, output_path, account=account,
                                    region=region, cdp_url=cdp_url)
            fb['cdp_first_empty'] = res.get('error', '')
            return fb
    except Exception as e:
        print('[Collector] CDP 主路径异常，回退独立通道:', e)
    return _search_standalone(keyword, max_scroll, output_path, account=account,
                              region=region, cdp_url=cdp_url)


def _collect_one_keyword(guard, kw, kw_scroll, kw_details, account=None):
    """单个关键词采集（封装 CollectorGuard.run），返回 (gr, result_dict)。
    独立函数便于 Runtime Guardian execute_with_retry 包装重试。"""
    gr = guard.run(
        lambda kw=kw, ss=kw_scroll, dd=kw_details, acc=account: search_xiaohongshu(
            kw, max_scroll=ss, max_details=dd, account=acc, region='intl', cdp_port=9223),
        kw,
    )
    result = gr.raw if isinstance(gr.raw, dict) else {
        'keyword': kw, 'total': len(gr.notes), 'notes': gr.notes,
        'error': '', 'channel': 'guard',
    }
    return gr, result


def collect_all(keywords=None, max_scroll=4, guardian=None, worker_id=None, run_id=None,
                kind="public_opinion", auto_trigger=False, account=None):
    """
    批量采集所有关键词
    返回去重后的笔记列表

    Runtime Guardian 旁路参数（均为可选，不传时行为与原链路完全一致）：
      guardian:   RuntimeGuardian 实例，传入后启用逐关键词心跳/检查点/重试+DLQ
      worker_id:  已注册的 worker ID
      run_id:     本次采集运行 ID（用于 checkpoint 关联）

    RedNote 策略门控参数（阶段5 集中策略 SoT）：
      kind:        采集类型 topic/public_opinion/event（三端开关白名单制）
      auto_trigger: True=调度器自动触发（额外校验 auto_run_enabled），False=手动触发
    """
    # RedNote 统一门控：香港/国际账号 + 三端能力白名单 + 自动运行总闸。
    policy_gate = _collection_policy_gate(region='intl', account=account)
    if not policy_gate.get('ok'):
        print(f"[Collector][PolicyGate] BLOCKED: {policy_gate.get('reason')}")
        return [], [{'keyword': '', 'count': 0, 'error': policy_gate.get('code', 'POLICY_BLOCKED'),
                     'policy': policy_gate}]
    _pol = _rednote_policy.effective_policy()
    _gate_reason = None
    if not _pol.can_run_kind(kind):
        _gate_reason = f"kind={kind} 未在策略白名单内（topic/public_opinion开，event关）"
    elif auto_trigger and not _pol.auto_run_enabled:
        _gate_reason = "auto_run_enabled=False（自动调度需显式 REDNOTE_AUTO_RUN=true 授权）"
    if _gate_reason:
        print(f"[Collector][PolicyGate] BLOCKED: {_gate_reason}")
        return [], [{'keyword': '', 'count': 0, 'error': 'KIND_POLICY_BLOCKED',
                     'policy': policy_gate, 'detail': _gate_reason}]
    print(f"[Collector][PolicyGate] PASS: kind={kind} auto_trigger={auto_trigger} "
          f"region=intl account={policy_gate.get('account')} "
          f"cadence_status={_pol.human_cadence.get('status')}")

    if keywords is None:
        keywords = MONITOR_KEYWORDS

    # 清洗噪声词 + 去重保序 + 限量（避免英文网页发现的 the/silver 类噪声拖慢采集、徒增风控暴露）
    seen_kw, clean_kw = set(), []
    for k in keywords:
        k = (k or '').strip()
        if not k or _is_noise_keyword(k) or k.lower() in seen_kw:
            continue
        seen_kw.add(k.lower()); clean_kw.append(k)
    keywords = clean_kw[:12]

    all_notes = {}
    collection_results = []
    core_set = set(MONITOR_KEYWORDS or [])

    for idx, kw in enumerate(keywords):
        # 首个显式词与主体监测词为核心，深采；其余为扩展反馈词，浅采（提速、降负载、降风控）
        is_core = (idx == 0) or (kw in core_set)
        kw_details = 10 if is_core else 3
        kw_scroll = max_scroll if is_core else min(max_scroll, 2)
        print(f"[Collector] 搜索: {kw} ({'核心' if is_core else '扩展'}浅采)" if not is_core else f"[Collector] 搜索: {kw}")
        guard = _get_xhs_guard()
        # Runtime Guardian: 逐关键词心跳
        if guardian and worker_id:
            try:
                guardian.heartbeat(worker_id)
            except Exception:
                pass
        # Runtime Guardian: 受保护执行（重试+指数退避+熔断+DLQ），旁路模式
        if guardian and worker_id and _RG_AVAILABLE:
            try:
                gr, result = guardian.execute_with_retry(
                    worker_id, _collect_one_keyword, guard, kw, kw_scroll, kw_details,
                    account or policy_gate.get('account'),
                    task_type='xhs_keyword_search',
                    payload={'keyword': kw, 'max_scroll': kw_scroll, 'max_details': kw_details},
                    run_id=run_id or f'collect_{int(time.time())}',
                )
            except RuntimeError as _rg_err:
                # 重试耗尽进入 DLQ：跳过本关键词，继续后续关键词（不阻塞主链路）
                print(f"[Collector]   !! 关键词 '{kw}' 重试耗尽进入DLQ，跳过: {_rg_err}")
                collection_results.append({
                    'keyword': kw, 'count': 0, 'error': f'DLQ: {_rg_err}',
                    'guard_state': '', 'tier': 'core' if is_core else 'expand',
                })
                continue
        else:
            gr, result = _collect_one_keyword(guard, kw, kw_scroll, kw_details,
                                              account or policy_gate.get('account'))
        if gr.should_stop:
            collection_results.append({'keyword': kw, 'count': result.get('total', 0),
                                       'error': result.get('error', '') or gr.reason,
                                       'guard_state': gr.state, 'tier': 'core' if is_core else 'expand'})
            print(f"[Collector]   !! 受控暂停/熔断({gr.to_dict().get('state_label')})，停止后续关键词请求：{gr.detail}")
            break
        count = result.get('total', 0)
        error = result.get('error', '')
        # ── RiskEngine 连续风险分接入（P1-4）：与 guard 七态互补，硬信号/累积风险触发熔断 ──
        if _feed_risk_engine(_get_xhs_risk_engine(), error=error, guard_state=getattr(gr, 'state', ''),
                             count=count, kw=kw, is_core=is_core, results=collection_results):
            break
        collection_results.append({'keyword': kw, 'count': count, 'error': error, 'tier': 'core' if is_core else 'expand'})
        print(f"[Collector]   -> {count} 条 {'(错误: '+error+')' if error else ''}")

        # P1-A 动态调度间隔（生产接线）：关键词间按 RiskEngine 六态动态降频/恢复。
        # base × interval_multiplier（NORMAL=1x / ADAPTIVE=1.8x / COOLDOWN=4x / FROZEN=5x），
        # 服务基线 §9/§10「动态熔断联动」：降频不停止，资源恢复后自动回升。
        try:
            import time as _sched_time
            from collector_guard.schedule_adapter import schedule_sleep_seconds
            _life = _get_xhs_risk_engine().snapshot().get('lifecycle_action')
            base = float(os.getenv('XHS_GUARD_BASE_INTERVAL', '6'))
            _interval = schedule_sleep_seconds(_life, base_interval=base)
            if _interval > 0.5:
                print(f"[Collector]   调度间隔 {_interval:.1f}s (lifecycle={_life})")
                _sched_time.sleep(_interval)
        except Exception as _sched_err:
            print(f"[Collector]   调度间隔计算失败(忽略): {_sched_err}")


        for note in result.get('notes', []):
            nid = note.get('note_id')
            if nid and nid not in all_notes:
                # 主体硬过滤（P0-C加固）：CDP详情采集已判定subject_hit=False的记录，collector层入库前直接排除
                # 不依赖下游insert层过滤，避免漏过滤路径污染正式KOS/舆情池
                # subject_hit_cdp为None（standalone通道未判定）时不排除，保持向后兼容
                _subj_hit = note.get('subject_hit_cdp')
                if _subj_hit is False:
                    continue
                # 标记来源关键词
                note['source_keyword'] = kw
                all_notes[nid] = note

        # Runtime Guardian: 逐关键词检查点（异常中断后可从 checkpoint 恢复而非从头开始）
        if guardian and worker_id and _RG_AVAILABLE:
            try:
                guardian.save_checkpoint(
                    run_id=run_id or 'collect_all', worker_id=worker_id,
                    position=f'keyword_idx={idx} keyword={kw} notes={len(all_notes)}',
                    metadata={
                        'keyword_idx': idx, 'keyword': kw,
                        'notes_so_far': len(all_notes), 'is_core': is_core,
                    },
                )
            except Exception:
                pass

    notes_list = list(all_notes.values())
    print(f"[Collector] 去重后共 {len(notes_list)} 条笔记")
    return notes_list, collection_results


def import_from_file(filepath):
    """从已有的搜索结果 JSON 文件导入数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('notes', [])


def classify_collect_state(error='', guard_state='', count=0):
    """把单次关键词采集结果归一化为标准六态（与全局健康中心 / Auth Recovery 对齐）。
    返回 SUCCESS / EMPTY / AUTH_REQUIRED / CAPTCHA / BLOCKED / NETWORK_ERROR。
    只做识别与归类，不绕过任何平台安全机制；空结果(EMPTY)与风控严格区分。"""
    err = error or ''
    gs = (guard_state or '').upper()
    el = err.lower()
    # 1) guard 硬状态优先：即使 error 为空，熔断/暂停/需验证/登录失效也绝不能被当成 EMPTY
    if gs in ('COOLDOWN', 'PAUSED', 'CIRCUIT_OPEN'):
        return 'BLOCKED'
    if gs == 'AUTH_REQUIRED':
        return 'AUTH_REQUIRED'
    if gs == 'NEED_VERIFY':
        return 'CAPTCHA'
    # 2) 无错误信号：有内容=SUCCESS，确无内容=EMPTY（EMPTY 不是风控）
    if not err:
        return 'SUCCESS' if count and count > 0 else 'EMPTY'
    # 3) 依据错误文本细分
    if 'IP_RISK' in err or '300012' in err:
        return 'BLOCKED'
    if 'NEED_VERIFY' in err.upper() or 'captcha' in el or '验证' in err:
        return 'CAPTCHA'
    if 'login' in el or 'auth' in el or 'session' in el or '登录' in err:
        return 'AUTH_REQUIRED'
    return 'NETWORK_ERROR'
