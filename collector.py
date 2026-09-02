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
from datetime import datetime

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

# CDP 真人通道（9222 有头、已登录、持久 Edge；用户认可“真实窗口登录一次长期复用”）
CDP_URL = os.getenv('XHS_CDP_URL', 'http://127.0.0.1:9222')
CDP_SCRIPT = os.path.join(SCRIPT_DIR, 'xhs_cdp_collector.py')  # Python Playwright CDP 真人通道
CDP_NODE_FALLBACK = os.path.join(SCRIPT_DIR, 'rednote_collector.cjs')  # 备用 node 通道
# 明确风控态：这些不是“0条舆情”，上层必须据此熔断/转 AUTH&VERIFY，不得当成正常空结果
_CDP_RISK_STATES = ('IP_RISK_OR_300012', 'NEED_VERIFY')


_XHS_GUARD = None
_XHS_RISK = None


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
    else:
        score, band, st = risk.record_success()
    snap = risk.snapshot()
    if snap['should_stop_request']:
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


def _cdp_online(timeout=2.0):
    """探测 9222 CDP 是否在线（不启动浏览器，只探测）。"""
    import urllib.request

    def _probe():
        with urllib.request.urlopen(CDP_URL + '/json/version', timeout=timeout) as r:
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
    """9222 真人通道掉线时自动拉起持久 Edge（无人值守自愈）；拉起失败返回 False，由上层走兜底。"""
    import time as _time
    if _cdp_online():
        return True
    try:
        from collector_automation import CollectorAutomation
        ctrl = CollectorAutomation(base_dir=SCRIPT_DIR)
        print('[Collector] 9222 不在线，尝试自动拉起真人采集浏览器 ...')
        ctrl.start_browser(account='default', headless=False)  # 内部已等待 CDP 就绪
        for _ in range(timeout):
            if _cdp_online():
                print('[Collector] 9222 已自动拉起并就绪')
                return True
            _time.sleep(1)
    except Exception as e:
        print('[Collector] 自动拉起 9222 失败:', e)
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
        'source_channel': 'cdp_edge_9222',
        'quality_status': rec.get('quality_status', ''),
        'subject_hit_cdp': rec.get('subject_hit'),
        'comment_list': rec.get('comment_list', []),
    }


def _search_via_cdp(keyword, max_scroll, output_path, max_details=10):
    """走 9222 已登录 Edge 的 rednote_collector.cjs，返回与独立通道一致的 dict 结构。"""
    env = os.environ.copy(); env['XHS_CDP_URL'] = CDP_URL
    env['PYTHONIOENCODING'] = 'utf-8'; env['PYTHONUTF8'] = '1'  # 子进程强制 UTF-8，避免 Windows cp936 捕获中文乱码
    py = sys.executable or 'python'
    cmd = [py, CDP_SCRIPT, '--keyword', keyword, '--output', output_path,
           '--max-scroll', str(max_scroll), '--max-details', str(max_details), '--cdp-url', CDP_URL]
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


def _search_standalone(keyword, max_scroll, output_path):
    """回退通道：独立持久化 Chromium（xhs_search.js）。无 CDP 时使用，headless 易被风控，仅作兜底。"""
    if not os.path.exists(SEARCH_SCRIPT):
        return {'keyword': keyword, 'total': 0, 'notes': [], 'error': f'搜索脚本缺失: {SEARCH_SCRIPT}', 'channel': 'standalone'}
    cmd = [_NODE_BIN, SEARCH_SCRIPT, '--keyword', keyword, '--output', output_path, '--max-scroll', str(max_scroll)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
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


def search_xiaohongshu(keyword, max_scroll=4, output_path=None, max_details=10):
    """多通道搜索小红书：9222 CDP 真人通道优先，独立 Chromium 兜底。
    返回 dict: {keyword,total,notes,error,channel}。风控态(IP风险/验证码)显式返回，不当作普通0条。
    max_details 控制 CDP 进入多少个详情页（核心词深采、扩展词浅采以提速降风控）。"""
    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, 'data', f'search_{int(datetime.now().timestamp())}.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 主路径：CDP 真人通道
    try:
        if os.path.exists(CDP_SCRIPT) and (_cdp_online() or _ensure_cdp_online()):
            res = _search_via_cdp(keyword, max_scroll, output_path, max_details=max_details)
            if res.get('notes') or res.get('error') in _CDP_RISK_STATES:
                return res  # 真出数 / 明确风控态都直接返回
            # CDP 非风控空结果，落兜底通道再试一次
            fb = _search_standalone(keyword, max_scroll, output_path)
            fb['cdp_first_empty'] = res.get('error', '')
            return fb
    except Exception as e:
        print('[Collector] CDP 主路径异常，回退独立通道:', e)
    return _search_standalone(keyword, max_scroll, output_path)


def collect_all(keywords=None, max_scroll=4):
    """
    批量采集所有关键词
    返回去重后的笔记列表
    """
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
        gr = guard.run(lambda kw=kw, ss=kw_scroll, dd=kw_details: search_xiaohongshu(kw, max_scroll=ss, max_details=dd), kw)
        result = gr.raw if isinstance(gr.raw, dict) else {'keyword': kw, 'total': len(gr.notes), 'notes': gr.notes, 'error': '', 'channel': 'guard'}
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

        for note in result.get('notes', []):
            nid = note.get('note_id')
            if nid and nid not in all_notes:
                # 标记来源关键词
                note['source_keyword'] = kw
                all_notes[nid] = note

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
