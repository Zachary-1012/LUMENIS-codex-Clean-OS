"""
LUMENIS SYSTEM Collector - Guangzhou reference-subject RedNote compatibility module
使用 rednote-cli 浏览器实例 + 自定义 Playwright 搜索脚本
采集小红书广州太古汇相关笔记
"""
import subprocess
import json
import os
import re
import sys
import time
import ipaddress
import hashlib
from datetime import datetime
from urllib.parse import urlsplit
from uuid import uuid4

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
    from lumenis.system.collector.adapters import rednote_policy as _rednote_policy
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

_XHS_RAW_CHECKPOINT_SUBDIR = os.path.join('collector_raw', 'xhs')
_XHS_SOURCE_HOST = 'www.rednote.com'
_XHS_MAX_WORKER_CHUNK_SECONDS = 300.0


def _xhs_raw_checkpoint_root(*, create=False):
    """Resolve the existing private data root used for immutable XHS raw chunks."""
    from xhs_cookie_bridge import PRIVATE_DATA_DIR

    private_root = os.path.realpath(os.path.abspath(PRIVATE_DATA_DIR))
    raw_root = os.path.realpath(os.path.join(private_root, _XHS_RAW_CHECKPOINT_SUBDIR))
    try:
        if os.path.normcase(os.path.commonpath((private_root, raw_root))) != os.path.normcase(private_root):
            raise ValueError('XHS_CHECKPOINT_ROOT_INVALID')
    except (OSError, ValueError):
        raise ValueError('XHS_CHECKPOINT_ROOT_INVALID')
    if create:
        os.makedirs(raw_root, exist_ok=True)
        raw_root = os.path.realpath(raw_root)
        try:
            if os.path.normcase(os.path.commonpath((private_root, raw_root))) != os.path.normcase(private_root):
                raise ValueError('XHS_CHECKPOINT_ROOT_INVALID')
        except (OSError, ValueError):
            raise ValueError('XHS_CHECKPOINT_ROOT_INVALID')
    return raw_root


def validate_xhs_raw_checkpoint_path(path, *, must_exist=False, must_be_new=False):
    """Accept only JSON raw checkpoints within the canonical XHS private directory."""
    if not isinstance(path, str) or not path or not os.path.isabs(path):
        raise ValueError('XHS_CHECKPOINT_PATH_INVALID')
    root = _xhs_raw_checkpoint_root(create=False)
    candidate = os.path.realpath(os.path.abspath(path))
    try:
        if os.path.normcase(os.path.commonpath((root, candidate))) != os.path.normcase(root):
            raise ValueError('XHS_CHECKPOINT_PATH_INVALID')
    except (OSError, ValueError):
        raise ValueError('XHS_CHECKPOINT_PATH_INVALID')
    if os.path.splitext(candidate)[1].lower() != '.json':
        raise ValueError('XHS_CHECKPOINT_PATH_INVALID')
    if must_exist and not os.path.isfile(candidate):
        raise ValueError('XHS_CHECKPOINT_MISSING')
    if must_be_new and os.path.exists(candidate):
        raise ValueError('XHS_CHECKPOINT_PATH_REUSED')
    return candidate


def new_xhs_raw_checkpoint_path(acquisition_fingerprint, keyword):
    """Allocate one unique private raw artifact for an exact purpose/query chunk."""
    if (not isinstance(acquisition_fingerprint, str)
            or re.fullmatch(r'[0-9a-f]{64}', acquisition_fingerprint) is None
            or not isinstance(keyword, str) or not keyword):
        raise ValueError('XHS_CHECKPOINT_BINDING_INVALID')
    task_token = hashlib.sha256(
        (acquisition_fingerprint + '\0' + keyword).encode('utf-8')
    ).hexdigest()[:24]
    root = _xhs_raw_checkpoint_root(create=True)
    return os.path.join(root, f'{task_token}_{uuid4().hex}.json')


def inspect_xhs_raw_checkpoint(path):
    """Read only safe continuation metadata and a digest from one private raw chunk."""
    resolved = validate_xhs_raw_checkpoint_path(path, must_exist=True)
    try:
        with open(resolved, 'rb') as source:
            payload = source.read()
        data = json.loads(payload.decode('utf-8'))
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ValueError('XHS_CHECKPOINT_INVALID')
    if not isinstance(data, dict):
        raise ValueError('XHS_CHECKPOINT_INVALID')
    detail_media_mode = data.get('detail_media_mode', 'legacy')
    if detail_media_mode not in {'legacy', 'cover_only'}:
        raise ValueError('XHS_CHECKPOINT_MEDIA_MODE_INVALID')
    checkpoint = data.get('checkpoint')
    summary = data.get('summary')
    if not isinstance(checkpoint, dict) or not isinstance(summary, dict):
        raise ValueError('XHS_CHECKPOINT_INVALID')
    pending = summary.get('pending_note_ids', [])
    if (not isinstance(pending, list)
            or any(not isinstance(note_id, str)
                   or re.fullmatch(r'[0-9a-fA-F]{24}', note_id) is None
                   for note_id in pending)):
        raise ValueError('XHS_CHECKPOINT_INVALID')
    fingerprint = checkpoint.get('verified_identity_fingerprint')
    if (not isinstance(fingerprint, str)
            or re.fullmatch(r'[0-9a-f]{64}', fingerprint) is None):
        raise ValueError('XHS_CHECKPOINT_IDENTITY_UNVERIFIED')
    run_id = checkpoint.get('run_id')
    if not isinstance(run_id, str) or not run_id:
        raise ValueError('XHS_CHECKPOINT_INVALID')
    partial = bool(data.get('partial'))
    complete = checkpoint.get('complete') is True
    terminal_error = bool(data.get('error'))
    continuation_required = bool(partial or pending)
    return {
        'raw_path': resolved,
        'raw_sha256': hashlib.sha256(payload).hexdigest(),
        'keyword': data.get('keyword'),
        'task_binding': data.get('acquisition_fingerprint'),
        'source_host': checkpoint.get('source_host'),
        'identity_verified': data.get('identity_verified') is True,
        'identity_fingerprint': fingerprint,
        'run_id': run_id,
        'complete': complete,
        'partial': partial,
        'detail_media_mode': detail_media_mode,
        'terminal_error': terminal_error,
        'pending_note_ids': list(pending),
        'pagination_exhausted': False,
        'continuation_required': continuation_required,
        'captured_at': checkpoint.get('written_at'),
    }


def verify_xhs_raw_checkpoint_reference(descriptor, *, acquisition_fingerprint, keyword):
    """Verify exact task, query, identity and immutable raw-file hash before resume."""
    if not isinstance(descriptor, dict):
        raise ValueError('XHS_CHECKPOINT_REFERENCE_INVALID')
    if (descriptor.get('task_binding') != acquisition_fingerprint
            or descriptor.get('keyword') != keyword
            or descriptor.get('source_host') != _XHS_SOURCE_HOST):
        raise ValueError('XHS_CHECKPOINT_BINDING_MISMATCH')
    snapshot = inspect_xhs_raw_checkpoint(descriptor.get('raw_path'))
    for name in ('task_binding', 'keyword', 'source_host', 'identity_fingerprint',
                 'raw_sha256', 'run_id', 'complete', 'pending_note_ids',
                 'terminal_error', 'pagination_exhausted', 'continuation_required', 'captured_at'):
        if snapshot.get(name) != descriptor.get(name):
            raise ValueError('XHS_CHECKPOINT_REFERENCE_MISMATCH')
    if snapshot.get('identity_verified') is not True:
        raise ValueError('XHS_CHECKPOINT_IDENTITY_UNVERIFIED')
    return snapshot

# Legacy default keywords are deliberately non-authoritative.
# Runtime collection scope is resolved from the canonical Subject/BrandFocus registry.
MONITOR_KEYWORDS = None

def _check_profile_lock(profile_dir):
    """Check only the registered HK/intl profile and never remove lock files."""
    if not isinstance(profile_dir, (str, os.PathLike)) or not str(profile_dir).strip():
        raise ValueError('XHS_PROFILE_DIR_REQUIRED')
    from xhs_cookie_bridge import ACCOUNT_PROFILES, XHS_RETINAUT_NAME
    binding = ACCOUNT_PROFILES.get(XHS_RETINAUT_NAME)
    if not isinstance(binding, (tuple, list)) or len(binding) != 2 or not binding[1]:
        raise PermissionError('XHS_REGISTERED_PROFILE_UNAVAILABLE')
    lock_dir = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(profile_dir))))
    registered_dir = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(binding[1]))))
    if os.path.normcase(lock_dir) != os.path.normcase(registered_dir):
        raise PermissionError('XHS_REGISTERED_PROFILE_BINDING_MISMATCH')
    return any(os.path.exists(os.path.join(lock_dir, f)) for f in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'))

# CDP 真人通道（9223 香港/国际 RedNote；仅复用已登录的本机驻场实例）
CDP_URL = os.getenv('XHS_CDP_URL', '').strip()
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
    """Inject the server-owned account vault and remote worker URL, never shell-local credentials."""
    env = os.environ.copy()
    env.pop('XHS_COOKIE_FILE', None)
    env.pop('XHS_EXPECTED_COLLECTION_USER_ID', None)
    env.pop('XHS_PROFILE_DIR', None)
    env.pop('XHS_COOKIE_HEADER', None)
    env.pop('XHS_COOKIES_JSON', None)
    env.pop('XHS_CDP_URL', None)
    selected_region = region or 'intl'
    env['XHS_COLLECTION_REGION'] = selected_region
    env['XHS_COLLECTION_HOST'] = 'www.rednote.com'
    if cdp_url:
        env['XHS_CDP_URL'] = cdp_url
    from xhs_cookie_bridge import (
        ACCOUNT_PROFILES,
        DEFAULT_COLLECTION_ACCOUNT,
        PRIVATE_DATA_DIR,
        XHS_RETINAUT,
        XHS_RETINAUT_NAME,
        _extract_user_id_from_cookie_text,
    )
    selected = account or DEFAULT_COLLECTION_ACCOUNT
    profile = ACCOUNT_PROFILES.get(selected)
    if (selected != XHS_RETINAUT_NAME or selected_region != 'intl' or not XHS_RETINAUT
            or not isinstance(profile, (tuple, list)) or len(profile) != 2
            or not profile[0] or not profile[1]):
        raise PermissionError('POLICY_BLOCKED: approved HK identity/profile unavailable')
    cookie_file = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(profile[0]))))
    profile_dir = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(profile[1]))))
    expected_cookie = os.path.realpath(os.path.join(PRIVATE_DATA_DIR, 'xhs_cookie_retinaut.txt'))
    expected_profile = os.path.realpath(os.path.join(PRIVATE_DATA_DIR, 'profiles', 'xhs-retinaut'))
    if (os.path.normcase(cookie_file) != os.path.normcase(expected_cookie)
            or os.path.normcase(profile_dir) != os.path.normcase(expected_profile)):
        raise PermissionError('XHS_REGISTERED_PROFILE_BINDING_MISMATCH')
    if not os.path.isfile(cookie_file):
        raise PermissionError('XHS_REGISTERED_COOKIE_UNAVAILABLE')
    with open(cookie_file, encoding='utf-8', errors='replace') as cookie_stream:
        if _extract_user_id_from_cookie_text(cookie_stream.read()) != XHS_RETINAUT:
            raise PermissionError('XHS_REGISTERED_COOKIE_IDENTITY_MISMATCH')
    env['XHS_COOKIE_FILE'] = cookie_file
    env['XHS_PROFILE_DIR'] = profile_dir
    env['XHS_COLLECTION_ACCOUNT'] = selected
    env['XHS_EXPECTED_COLLECTION_USER_ID'] = XHS_RETINAUT
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    return env


def xhs_expected_identity_fingerprint(account=None, region='intl'):
    """Return a comparison-only hash for the registered XHS identity, never its value."""
    gate = _collection_policy_gate(region=region or 'intl', account=account)
    if not gate.get('ok'):
        raise ValueError('XHS_COLLECTION_POLICY_BLOCKED')
    selected_account = gate.get('account') or account
    try:
        env = _collection_env(account=selected_account, region=gate.get('region') or region or 'intl')
    except Exception as exc:
        raise ValueError('XHS_APPROVED_IDENTITY_UNAVAILABLE') from exc
    expected = str(env.get('XHS_EXPECTED_COLLECTION_USER_ID') or '').strip()
    if not expected:
        raise ValueError('XHS_APPROVED_IDENTITY_UNAVAILABLE')
    return hashlib.sha256(expected.encode('utf-8')).hexdigest()


def _approved_local_profile_contract(account=None, region=None):
    """Return the existing approved HK identity only for its registered profile."""
    if account != 'XHS_RETINAUT' or region != 'intl':
        return None
    try:
        from xhs_cookie_bridge import (
            ACCOUNT_CDP_PORTS, ACCOUNT_PROFILES, DEFAULT_COLLECTION_ACCOUNT,
            PRIVATE_DATA_DIR, XHS_RETINAUT,
        )
        profile = ACCOUNT_PROFILES.get(account)
        expected_profile = os.path.normcase(os.path.abspath(os.path.join(
            PRIVATE_DATA_DIR, 'profiles', 'xhs-retinaut')))
        if (account != DEFAULT_COLLECTION_ACCOUNT or not XHS_RETINAUT
                or ACCOUNT_CDP_PORTS.get(account) != 9223
                or not isinstance(profile, tuple) or len(profile) != 2
                or not profile[0] or not profile[1]
                or os.path.normcase(os.path.abspath(profile[1])) != expected_profile):
            return None
        return XHS_RETINAUT
    except Exception:
        return None


def _resolve_server_cdp_url(cdp_url=None, *, account=None, region=None):
    """Resolve a configured remote worker or the one approved HK loopback worker."""
    candidate = str(cdp_url or os.getenv('XHS_CDP_URL') or CDP_URL or '').strip()
    if not candidate:
        # The approved local worker may be discovered only through its fixed,
        # loopback-only endpoint.  This is a read-only health probe; it never
        # reads cookies or touches the browser profile.
        if _approved_local_profile_contract(account, region):
            import urllib.request
            try:
                with urllib.request.urlopen(
                        'http://127.0.0.1:9223/json/version', timeout=1.5) as response:
                    if getattr(response, 'status', 200) == 200:
                        return 'http://127.0.0.1:9223', ''
            except Exception:
                pass
        return '', 'COLLECTOR_ENDPOINT_NOT_CONFIGURED'
    try:
        parsed = urlsplit(candidate)
        hostname = (parsed.hostname or '').strip('[]').lower()
        if parsed.scheme not in {'http', 'https'} or not hostname:
            return '', 'COLLECTOR_ENDPOINT_INVALID'
        if parsed.username or parsed.password or parsed.fragment:
            return '', 'COLLECTOR_ENDPOINT_INVALID'
        if parsed.port == 9222:
            return '', 'POLICY_BLOCKED'
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            ip = None
        is_loopback = hostname in {'localhost', 'localhost.localdomain'} or bool(
            ip and (ip.is_loopback or ip.is_unspecified)
        )
        if is_loopback:
            expected_user_id = _approved_local_profile_contract(account, region)
            if (hostname != '127.0.0.1' or parsed.scheme != 'http'
                    or parsed.port != 9223 or parsed.path not in {'', '/'}
                    or parsed.query or not expected_user_id):
                return '', 'LOCAL_COLLECTOR_ENDPOINT_FORBIDDEN'
            return 'http://127.0.0.1:9223', ''
        if parsed.path not in {'', '/'}:
            return '', 'COLLECTOR_ENDPOINT_INVALID'
        return candidate.rstrip('/'), ''
    except Exception:
        return '', 'COLLECTOR_ENDPOINT_INVALID'


def _get_xhs_guard():
    """懒加载小红书采集保护层（CollectorGuard），避免无条件 import 影响其它通道。"""
    global _XHS_GUARD
    if _XHS_GUARD is None:
        from lumenis.system.collector.guard.guard import CollectorGuard
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
            from lumenis.system.collector.guard.risk_engine import RiskEngine
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
            from lumenis.system.collector.guard.state import CollectState
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
    from lumenis.system.collector.guard.schedule_adapter import schedule_state, should_stop_schedule
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


def _cdp_online(timeout=2.0, cdp_url=None, *, account=None, region=None):
    """Probe a configured remote browser worker; never assume a local browser."""
    import urllib.request
    _url, endpoint_error = _resolve_server_cdp_url(
        cdp_url, account=account, region=region)
    if endpoint_error:
        return False

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


def _ensure_cdp_online(timeout=30, cdp_url=None):
    """Compatibility name; production never launches a developer-local browser."""
    return _cdp_online(timeout=min(float(timeout), 5.0), cdp_url=cdp_url)


def _norm_cdp_note(rec):
    """把 rednote_collector.cjs 的详情记录映射为 collector/insert_note 标准字段。"""
    pub = rec.get('detail_publish_time') or rec.get('publish_time') or rec.get('publish_datetime') or ''
    if 'time_source_observations' in rec and rec.get('publication_time_source') not in {'detail', 'card'}:
        pub = ''
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
        if v is None or isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v if v >= 0 else None
        if isinstance(v, float):
            return int(v) if v >= 0 and v.is_integer() else None
        if isinstance(v, str) and v.strip().isascii() and v.strip().isdigit():
            return int(v.strip())
        return None
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
        'publish_time': pub,
        'detail_publish_time': pub,
        'time_raw': rec.get('time_raw', ''),
        'time_source_observations': rec.get('time_source_observations', []),
        'publication_time_source': rec.get('publication_time_source', 'legacy_not_classified'),
        # 双时间铁律：publish_date 来自平台发布时间；captured_at 是本机采集时刻，来源不同。
        # 显式落采集时刻，不依赖下游 insert_note 的隐式兜底（智谱采集链审查 P0-C 加固）。
        'captured_at': rec.get('collected_at') or rec.get('captured_at') or datetime.now().astimezone().isoformat(),
        'xsec_token': rec.get('xsec_token', ''),
        'source_channel': 'cdp_edge_9223',
        'quality_status': rec.get('quality_status', ''),
        'subject_hit_cdp': rec.get('subject_hit'),
        'comment_list': rec.get('comment_list', []),
        'comment_count': rec.get('comment_count'),
        'is_video': rec.get('is_video'),
        'image_count': rec.get('image_count'),
        'image_list': rec.get('image_list', []),
        'video_list': rec.get('video_list', []),
        'tag_list': rec.get('tag_list', []),
        'author_url': rec.get('author_url', ''),
        'detail_fetched': rec.get('detail_fetched'),
        'human_view': rec.get('human_view', {}),
        'detail_media_mode': rec.get('detail_media_mode', 'legacy'),
        'native_metrics_raw': rec.get('native_metrics_raw', {}),
        'source_note_ids': rec.get('source_note_ids'),
        'source_page_url': rec.get('source_page_url'),
        'detail_identity_verified': rec.get('detail_identity_verified'),
        'unassigned_detail_observation': rec.get('unassigned_detail_observation'),
        'collector_version': rec.get('collector_version', ''),
    }


def _search_via_cdp(keyword, max_scroll, output_path, max_details=10, cdp_url=None, region=None, account=None,
                    resume_path=None, time_budget=None, worker_chunk_seconds=300,
                    acquisition_fingerprint=None, detail_media_mode='legacy'):
    """Use the configured server browser worker with the existing XHS collector."""
    import math
    if not isinstance(detail_media_mode, str) or detail_media_mode not in {'legacy', 'cover_only'}:
        return {'keyword': keyword, 'notes': [], 'total': 0,
                'error': 'INVALID_DETAIL_MEDIA_MODE', 'channel': 'cdp'}
    if isinstance(worker_chunk_seconds, bool):
        return {'keyword': keyword, 'notes': [], 'total': 0,
                'error': 'INVALID_WORKER_CHUNK_SECONDS', 'channel': 'cdp'}
    try:
        worker_chunk_seconds = float(worker_chunk_seconds)
    except (ValueError, TypeError, OverflowError):
        return {'keyword': keyword, 'notes': [], 'total': 0,
                'error': 'INVALID_WORKER_CHUNK_SECONDS', 'channel': 'cdp'}
    if (not math.isfinite(worker_chunk_seconds) or worker_chunk_seconds <= 0
            or worker_chunk_seconds > _XHS_MAX_WORKER_CHUNK_SECONDS):
        return {'keyword': keyword, 'notes': [], 'total': 0,
                'error': 'INVALID_WORKER_CHUNK_SECONDS', 'channel': 'cdp'}
    if (acquisition_fingerprint is not None
            and (not isinstance(acquisition_fingerprint, str)
                 or re.fullmatch(r'[0-9a-f]{64}', acquisition_fingerprint) is None)):
        return {'keyword': keyword, 'notes': [], 'total': 0,
                'error': 'INVALID_ACQUISITION_FINGERPRINT', 'channel': 'cdp'}
    if time_budget is not None:
        if isinstance(time_budget, bool):
            return {'keyword': keyword, 'notes': [], 'total': 0, 'error': 'INVALID_TIME_BUDGET', 'channel': 'cdp'}
        try:
            time_budget = float(time_budget)
        except (ValueError, TypeError, OverflowError):
            return {'keyword': keyword, 'notes': [], 'total': 0, 'error': 'INVALID_TIME_BUDGET', 'channel': 'cdp'}
        if not math.isfinite(time_budget) or time_budget <= 0:
            return {'keyword': keyword, 'notes': [], 'total': 0, 'error': 'INVALID_TIME_BUDGET', 'channel': 'cdp'}
    if acquisition_fingerprint is not None:
        try:
            output_path = validate_xhs_raw_checkpoint_path(output_path, must_be_new=True)
            if resume_path:
                resume_path = validate_xhs_raw_checkpoint_path(resume_path, must_exist=True)
                if os.path.normcase(resume_path) == os.path.normcase(output_path):
                    raise ValueError('XHS_CHECKPOINT_PATH_REUSED')
        except (OSError, ValueError):
            return {'keyword': keyword, 'notes': [], 'total': 0,
                    'error': 'XHS_CHECKPOINT_PATH_INVALID', 'channel': 'cdp'}
    _cdp, endpoint_error = _resolve_server_cdp_url(
        cdp_url, account=account, region=region or 'intl')
    if endpoint_error:
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': endpoint_error, 'channel': 'cdp'}
    env = _collection_env(account=account, region=region or 'intl', cdp_url=_cdp)
    from uuid import uuid4
    run_id = uuid4().hex
    py = sys.executable or 'python'
    cmd = [py, CDP_SCRIPT, '--keyword', keyword, '--output', output_path,
           '--max-scroll', str(max_scroll), '--max-details', str(max_details), '--cdp-url', _cdp,
           '--run-id', run_id, '--worker-chunk-seconds', str(worker_chunk_seconds),
           '--detail-media-mode', detail_media_mode]
    if time_budget is not None:
        cmd.extend(['--time-budget', str(time_budget)])
    if acquisition_fingerprint is not None:
        cmd.extend(['--acquisition-fingerprint', acquisition_fingerprint])
    if resume_path:
        cmd.extend(['--resume-from', str(resume_path)])
    invocation_budget = min(worker_chunk_seconds, time_budget) if time_budget is not None else worker_chunk_seconds
    try:
        p = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, encoding='utf-8',
                           timeout=invocation_budget + 60, env=env)
    except subprocess.TimeoutExpired:
        # Recover only this invocation's atomically-written, identity-verified checkpoint.
        try:
            with open(output_path, encoding='utf-8') as source:
                data = json.load(source)
            checkpoint = data.get('checkpoint') or {}
            expected_identity = str(env.get('XHS_EXPECTED_COLLECTION_USER_ID') or '').strip()
            expected_identity_fingerprint = hashlib.sha256(
                expected_identity.encode('utf-8')).hexdigest() if expected_identity else ''
            if (checkpoint.get('run_id') != run_id or data.get('keyword') != keyword
                    or checkpoint.get('source_host') != 'www.rednote.com'
                    or data.get('identity_verified') is not True
                    or not expected_identity_fingerprint
                    or checkpoint.get('verified_identity_fingerprint') != expected_identity_fingerprint
                    or data.get('acquisition_fingerprint') != acquisition_fingerprint
                    or checkpoint.get('acquisition_fingerprint') != acquisition_fingerprint
                    or not isinstance(data.get('notes'), list)
                    or not all(isinstance(note, dict) for note in data['notes'])
                    or not isinstance(data.get('summary'), dict)):
                raise ValueError('checkpoint belongs to another acquisition')
        except (OSError, ValueError, TypeError, AttributeError):
            return {'keyword': keyword, 'total': 0, 'notes': [], 'ok': False,
                    'error': 'CDP_TIMEOUT_NO_CHECKPOINT', 'channel': 'cdp',
                    'summary': {'timed_out': True, 'checkpoint_recovered': False}}
        data.setdefault('summary', {}).update({'timed_out': True, 'checkpoint_recovered': True})
        if checkpoint.get('complete') is not True:
            data['ok'] = False
            data['partial'] = True
            data['error'] = 'CDP_TIMEOUT_PARTIAL'
        else:
            data['summary']['timed_out_after_complete_checkpoint'] = True
    else:
        out = p.stdout or ''
        marker = '---RESULT_JSON---'
        raw = out.split(marker, 1)[1].strip() if marker in out else (out[out.find('{'):] if out.find('{') >= 0 else '')
        if not raw:
            return {'keyword': keyword, 'total': 0, 'notes': [], 'ok': False,
                    'error': ((p.stderr or out) or f'CDP exit {p.returncode}')[-800:], 'channel': 'cdp'}
        try:
            data = json.loads(raw)
        except Exception as e:
            return {'keyword': keyword, 'total': 0, 'notes': [], 'ok': False,
                    'error': f'CDP结果解析失败: {e}', 'channel': 'cdp'}
    summ = data.get('summary', {}) or {}
    notes = [_norm_cdp_note(r) for r in data.get('notes', []) if r.get('note_id')]
    if summ.get('ip_blocked'):
        err = 'IP_RISK_OR_300012'
    elif summ.get('session_expired'):
        err = 'SESSION_EXPIRED'
    elif summ.get('verification_required'):
        err = 'NEED_VERIFY'
    elif data.get('error'):
        err = data['error']
    elif not notes and not data.get('ok'):
        err = 'CDP_EMPTY_OR_LOAD_FAILED'
    else:
        err = ''
    return {'keyword': keyword, 'total': len(notes), 'notes': notes, 'error': err,
            'channel': 'cdp', 'summary': summ, 'ok': bool(data.get('ok')),
            'partial': bool(data.get('partial')), 'checkpoint': data.get('checkpoint', {}),
            'detail_media_mode': data.get('detail_media_mode', 'legacy'),
            'identity_verified': data.get('identity_verified') is True,
            'search_diagnostics': data.get('search_diagnostics', {})}


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
                        region=None, cdp_port=None, kos_only=False, account=None, resume_path=None,
                        time_budget=None, worker_chunk_seconds=300, acquisition_fingerprint=None,
                        detail_media_mode='legacy'):
    """多通道搜索 RedNote：仅走香港/国际账号与 9223 入口。
    返回 dict: {keyword,total,notes,error,channel,region}。风控态显式返回，不当作普通0条。
    region: 当前生产值为 'intl'；'cn' 明确返回策略阻断，不触发任何下游进程。
    """
    if not isinstance(detail_media_mode, str) or detail_media_mode not in {'legacy', 'cover_only'}:
        return {'keyword': keyword, 'total': 0, 'notes': [],
                'error': 'INVALID_DETAIL_MEDIA_MODE', 'channel': 'policy'}
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
    if (acquisition_fingerprint is not None
            and (not isinstance(acquisition_fingerprint, str)
                 or re.fullmatch(r'[0-9a-f]{64}', acquisition_fingerprint) is None)):
        return {'keyword': keyword, 'total': 0, 'notes': [],
                'error': 'INVALID_ACQUISITION_FINGERPRINT', 'channel': 'policy',
                'region': 'intl'}
    region = 'intl'
    cdp_port = 9223  # legacy policy identity only; it is not a host-local endpoint
    selected_account = policy_gate.get('account') or account
    cdp_url, endpoint_error = _resolve_server_cdp_url(
        account=selected_account, region='intl')
    if endpoint_error:
        return {
            'keyword': keyword, 'total': 0, 'notes': [], 'error': endpoint_error,
            'channel': 'worker', 'region': region, 'policy': policy_gate,
        }
    if output_path is None:
        # 采集原始产物属于运行数据，不得回写唯一源码目录；沿用账号桥的
        # 受保护数据根目录，保证直接调用与 API/调度器使用同一落盘边界。
        try:
            from xhs_cookie_bridge import PRIVATE_DATA_DIR as _private_data_dir
        except Exception as exc:
            return {
                'keyword': keyword, 'total': 0, 'notes': [],
                'error': f'运行数据目录不可用，拒绝写入源码目录: {exc}',
                'channel': 'policy', 'region': region,
                'policy': {'ok': False, 'code': 'runtime_data_dir_unavailable'},
            }
        if acquisition_fingerprint is not None:
            try:
                output_path = new_xhs_raw_checkpoint_path(acquisition_fingerprint, keyword)
            except (OSError, ValueError):
                return {'keyword': keyword, 'total': 0, 'notes': [],
                        'error': 'XHS_CHECKPOINT_PATH_INVALID', 'channel': 'policy',
                        'region': region}
        else:
            output_path = os.path.join(_private_data_dir, f'search_{uuid4().hex}.json')
    if acquisition_fingerprint is not None:
        try:
            output_path = validate_xhs_raw_checkpoint_path(output_path, must_be_new=True)
            if resume_path:
                resume_path = validate_xhs_raw_checkpoint_path(resume_path, must_exist=True)
                if os.path.normcase(resume_path) == os.path.normcase(output_path):
                    raise ValueError('XHS_CHECKPOINT_PATH_REUSED')
        except (OSError, ValueError):
            return {'keyword': keyword, 'total': 0, 'notes': [],
                    'error': 'XHS_CHECKPOINT_PATH_INVALID', 'channel': 'policy',
                    'region': region}
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 选择器只返回当前允许的香港/国际入口；不再轮换或回落到大陆。
    if _REDNOTE_POLICY_AVAILABLE:
        sel = _rednote_policy.select_region(kos_only=kos_only, force_region='intl')
        region = sel['region']; cdp_port = sel['cdp_port']
    if not os.path.exists(CDP_SCRIPT):
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': 'COLLECTOR_SCRIPT_UNAVAILABLE',
                'channel': 'worker', 'region': region}
    if not _cdp_online(cdp_url=cdp_url, account=selected_account, region='intl'):
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': 'COLLECTOR_ENDPOINT_UNAVAILABLE',
                'channel': 'worker', 'region': region}
    result = _search_via_cdp(keyword, max_scroll, output_path, max_details=max_details,
                             cdp_url=cdp_url, region=region, account=selected_account,
                             resume_path=resume_path, time_budget=time_budget,
                             worker_chunk_seconds=worker_chunk_seconds,
                             acquisition_fingerprint=acquisition_fingerprint,
                             detail_media_mode=detail_media_mode)
    result['region'] = region
    result['channel'] = 'authorized_browser_worker'
    return result


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
                kind="public_opinion", auto_trigger=False, account=None, *,
                business_requests=None, continuation=None, max_queries=32,
                max_details=0):
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

    # Resolve the canonical acquisition plan before touching Guard/browser/network.
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    query_plan = build_acquisition_plan(keywords, business_requests=business_requests,
                                       continuation=continuation, max_queries=max_queries)
    if not query_plan.is_runnable:
        return [], [{
            'keyword': '',
            'count': 0,
            'error': 'ACQUISITION_PLAN_BLOCKED',
            'plan_reason_code': query_plan.reason_code,
            'query_plan': query_plan.to_dict(),
        }]

    # 清洗噪声词 + 去重保序 + 限量（避免英文网页发现的 the/silver 类噪声拖慢采集、徒增风控暴露）
    seen_kw, clean_kw = set(), []
    for k in query_plan.keywords:
        k = (k or '').strip()
        if not k or _is_noise_keyword(k) or k.lower() in seen_kw:
            continue
        seen_kw.add(k.lower()); clean_kw.append(k)
    keywords = clean_kw
    if any(query.business_context and query.business_context.get('platform') not in
           {'xhs', 'xiaohongshu', 'rednote', '小红书'} for query in query_plan.queries):
        return [], [{'keyword': '', 'count': 0, 'error': 'USE_PLATFORM_COLLECTION_ENTRY',
                     'query_plan': query_plan.to_dict()}]

    all_notes = {}
    collection_results = []
    core_set = {query.keyword for query in query_plan.queries if query.priority == 0}

    for idx, kw in enumerate(keywords):
        # 首个显式词与主体监测词为核心，深采；其余为扩展反馈词，浅采（提速、降负载、降风控）
        is_core = (idx == 0) or (kw in core_set)
        kw_details = max_details
        kw_scroll = max_scroll
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
        matching_queries = [query.to_dict() for query in query_plan.queries if query.keyword == kw]
        collection_results.append({'keyword': kw, 'count': count, 'error': error,
                                   'tier': 'core' if is_core else 'expand',
                                   'planned_queries': matching_queries,
                                   'scope_role': 'QUERY_INTENT_NOT_VERIFIED_SOURCE_BINDING'})
        print(f"[Collector]   -> {count} 条 {'(错误: '+error+')' if error else ''}")

        # P1-A 动态调度间隔（生产接线）：关键词间按 RiskEngine 六态动态降频/恢复。
        # base × interval_multiplier（NORMAL=1x / ADAPTIVE=1.8x / COOLDOWN=4x / FROZEN=5x），
        # 服务基线 §9/§10「动态熔断联动」：降频不停止，资源恢复后自动回升。
        try:
            import time as _sched_time
            from lumenis.system.collector.guard.schedule_adapter import schedule_sleep_seconds
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
    if collection_results:
        attempted = {item.get('keyword') for item in collection_results}
        pending = [query.to_dict() for query in query_plan.queries if query.keyword not in attempted]
        collection_results[-1]['query_plan'] = query_plan.to_dict()
        collection_results[-1]['pending_queries'] = pending
        collection_results[-1]['next_cursor'] = query_plan.next_cursor
        collection_results[-1]['continuation_required'] = bool(pending or query_plan.next_cursor)
        collection_results[-1]['coverage_complete'] = False
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
    if gs in {'SESSION_EXPIRED', 'AUTH_REQUIRED'}:
        return 'AUTH_REQUIRED'
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
