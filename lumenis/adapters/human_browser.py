# -*- coding: utf-8 -*-
"""
共享拟人浏览层（Human Browser Layer）
=================================================
定位：面向小红书 / 抖音 / Google 等“强反爬、需真人浏览”的采集源，
提供统一的、基于已注册 CDP Worker 的拟人化浏览器操作底座。

设计原则（结合 GitHub 反检测开源实践 niespodd/browser-fingerprinting、
nodriver、SeleniumBase 等的共识）：
  1. BACKGROUND 只连接经端口、Profile、内核和 headless 参数核验的无头 Worker；
     只有带真实 Collector task 和 Permission 的 HUMAN_INTERACTIVE 请求才可切换到可见模式；
  2. JS 层 stealth 注入仅作纵深防御（掩盖 navigator.webdriver 等显性泄漏），
     不把它当作唯一手段；
  3. 行为拟人：贝塞尔鼠标轨迹、人类打字节奏、变速/偶发回滚的滚动、
     高斯随机停顿，替代固定 sleep 与机械滚轮；
  4. 六态严格分离：SUCCESS / EMPTY / BLOCKED / CAPTCHA / AUTH_FAILED /
     NETWORK_ERROR，绝不把被拦或加载失败伪装成“0 条成功”；
  5. CDP 模式只关闭自己新建的标签页，绝不 browser.close()；受控模式切换
     只通过现有 SYSTEM Worker 的身份核验和 graceful Browser.close 完成。

线程模型：playwright sync_api 需在工作线程内独立创建实例，HumanBrowser
作为上下文管理器在单次采集任务内创建与释放。
"""
import hashlib
import ipaddress
import json
import logging
import os
import random
import re
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlsplit

logger = logging.getLogger(__name__)


class NativePageWindowError(ValueError):
    """A saved position cannot safely identify the observed native page."""


def validate_native_page_window_cursor(cursor):
    """Validate adapter page offsets before making a browser read.

    These fields describe a position *inside* a platform page. They never
    replace its native cursor or grant permission to read that page.
    """
    if cursor is None:
        return
    if not isinstance(cursor, dict):
        raise NativePageWindowError('NATIVE_CURSOR_WINDOW_INVALID')
    has_offset = 'item_offset' in cursor
    has_digest = 'page_sha256' in cursor
    if has_offset != has_digest:
        raise NativePageWindowError('NATIVE_CURSOR_WINDOW_INVALID')
    if has_offset and (type(cursor['item_offset']) is not int
            or not 0 <= cursor['item_offset'] <= 1_000_000
            or not isinstance(cursor['page_sha256'], str)
            or re.fullmatch(r'[0-9a-f]{64}', cursor['page_sha256']) is None):
        raise NativePageWindowError('NATIVE_CURSOR_WINDOW_INVALID')


def native_page_window(rows, *, limit, cursor=None, identities):
    """Return a bounded window without dropping an already observed remainder.

    The digest binds the ordered native identities, rather than changing view
    or like counts. An insertion, removal or reorder requires a fresh read;
    silently applying an old offset would skip or misattribute source data.
    """
    validate_native_page_window_cursor(cursor)
    if not isinstance(rows, list) or len(identities) != len(rows):
        raise NativePageWindowError('NATIVE_PAGE_IDENTITIES_INVALID')
    if type(limit) is not int or limit < 1:
        raise NativePageWindowError('NATIVE_PAGE_LIMIT_INVALID')
    digest = hashlib.sha256(json.dumps(
        identities, ensure_ascii=False, separators=(',', ':'), allow_nan=False
    ).encode('utf-8')).hexdigest()
    start = (cursor or {}).get('item_offset', 0)
    if 'page_sha256' in (cursor or {}) and (
            cursor['page_sha256'] != digest or start >= len(rows)):
        raise NativePageWindowError('NATIVE_CURSOR_PAGE_CHANGED')
    end = min(start + limit, len(rows))
    complete = end == len(rows)
    return {
        'rows': rows[start:end], 'page_complete': complete,
        'next_window': None if complete else {'item_offset': end, 'page_sha256': digest},
        'window_start': start, 'window_end': end, 'observed_native_rows': len(rows),
        'page_sha256': digest, 'page_identity_basis': 'ORDERED_NATIVE_IDENTITIES',
    }


class NativeReadCapture:
    """Observe completed reads from the current registered browser page.

    This never constructs/replays a signed request or exports a session. Only
    explicitly named native resource/pagination variables leave the transient
    request; headers, cookies, CSRF fields and signed URLs are not retained.
    Continuation is driven by the platform's own visible read controls.
    """

    def __init__(self, *, hosts, paths, request_keys=(), max_pages=64, object_decoder=None):
        self.hosts = frozenset(hosts)
        self.paths = tuple(paths)
        self.request_keys = frozenset(request_keys)
        self.max_pages = max_pages
        self.pages = []
        self.page = None
        self.object_decoder = object_decoder or self._objects

    def attach(self, page):
        self.page = page
        page.on("requestfinished", self._finished)
        return self

    def close(self):
        if self.page is not None:
            try:
                self.page.remove_listener("requestfinished", self._finished)
            except Exception:
                pass
        self.page = None

    @staticmethod
    def _objects(text):
        text = text.lstrip()
        if text.startswith("for (;;);"):
            text = text[len("for (;;);"):].lstrip()
        decoder = json.JSONDecoder()
        values = []
        offset = 0
        while offset < len(text):
            while offset < len(text) and text[offset].isspace():
                offset += 1
            if offset == len(text):
                break
            try:
                value, offset = decoder.raw_decode(text, offset)
            except (ValueError, TypeError):
                break
            if isinstance(value, (dict, list)):
                values.append(value)
        return values

    def _finished(self, request):
        try:
            parsed = urlsplit(request.url)
            if (parsed.scheme != "https" or parsed.hostname not in self.hosts
                    or parsed.username is not None or parsed.password is not None
                    or request.resource_type not in {"xhr", "fetch"}
                    or request.method not in {"GET", "POST"}
                    or not any(path in parsed.path for path in self.paths)
                    or len(self.pages) >= self.max_pages):
                return
            # Read only the configured keys, never retain the original request.
            fields = {key: values[-1] for key, values in parse_qs(parsed.query).items()
                      if key in self.request_keys and values}
            query = parse_qs(parsed.query)
            variables = query.get("variables", [None])[-1]
            post = request.post_data if request.method == "POST" else None
            if isinstance(post, str) and len(post) <= 2_000_000:
                try:
                    decoded = json.loads(post)
                except ValueError:
                    decoded = {key: values[-1] for key, values in parse_qs(post).items()
                               if values}
                if isinstance(decoded, dict):
                    variables = decoded.get("variables", variables)
                    fields.update({key: value for key, value in decoded.items()
                                   if key in self.request_keys})
            if isinstance(variables, str):
                try:
                    variables = json.loads(variables)
                except ValueError:
                    variables = None
            if isinstance(variables, dict):
                fields.update({key: value for key, value in variables.items()
                               if key in self.request_keys})
            fields = {key: value for key, value in fields.items()
                      if value is None or type(value) in {int, bool}
                      or isinstance(value, str) and len(value) <= 4096
                      and not any(ord(c) < 32 for c in value)}
            response = request.response()
            if response is None:
                return
            status = response.status
            retry = response.header_value("retry-after")
            retry_seconds = None
            if isinstance(retry, str) and retry.isascii() and retry.isdigit():
                retry_seconds = min(int(retry), 86400)
            elif retry:
                try:
                    from datetime import datetime, timezone
                    from email.utils import parsedate_to_datetime
                    deadline = parsedate_to_datetime(retry)
                    retry_seconds = min(86400, max(0, int((deadline - datetime.now(timezone.utc)).total_seconds())))
                except (ValueError, TypeError, OverflowError):
                    pass
            failure = ({401: "AUTH_REQUIRED", 403: "ACCESS_BLOCKED",
                        404: "CONTENT_UNAVAILABLE", 412: "ACCESS_BLOCKED",
                        429: "RATE_LIMITED"}.get(status)
                       if not 200 <= status < 300 else None)
            if not 200 <= status < 300 and failure is None:
                failure = "PROVIDER_UNAVAILABLE"
            body = response.text()
            objects = self.object_decoder(body) if len(body) <= 8_000_000 else []
            if not objects and failure is None:
                failure = "NATIVE_RESPONSE_NOT_JSON"
            self.pages.append({"path": parsed.path, "request": fields,
                               "http_status": status, "retry_after_seconds": retry_seconds,
                               "failure_class": failure, "objects": objects})
        except Exception:
            # No exception text: browser exceptions can contain a signed URL.
            return

    def failure(self):
        return next((page for page in self.pages if page["failure_class"]), None)

    def seek(self, page, select, advance, *, max_steps=12, wait_ms=650):
        """Reach an observed native page using only the supplied read control."""
        checked = 0
        for step in range(max_steps + 1):
            for observation in self.pages[checked:]:
                if observation["failure_class"]:
                    return None
                selected = select(observation)
                if selected is not None:
                    selected.setdefault("observed_prior_native_responses", checked)
                    return selected
                checked += 1
            if step == max_steps or self.failure() is not None:
                break
            if advance(step) is False:
                break
            page.wait_for_timeout(wait_ms)
        return None


def native_read_scroll(page, *, reply_id=None, reply_attribute=None):
    """One bounded official comment/list read action; never a social write."""
    if reply_id and reply_attribute:
        if not re.fullmatch(r"[A-Za-z0-9_:-]{1,200}", str(reply_id)):
            return False
        anchor = page.locator(f'[{reply_attribute}="{reply_id}"]').first
        if anchor.count():
            button = anchor.get_by_text(re.compile(
                r"^(?:View|Show|See|Load|查看|展开|显示|載入|查看全部).{0,28}(?:repl(?:y|ies)|回复|回覆)", re.I)).first
            if button.count() and button.is_visible():
                button.click(timeout=3000)
                return True
    # A comment panel may be a nested scrolling container. Move the pointer
    # over an observed comment list before wheeling so it receives the event.
    for selector in ('[role="dialog"] [role="list"]', '[data-e2e="comment-list"]',
                     '[data-e2e="comment-list-container"]', '[role="feed"]', 'article'):
        target = page.locator(selector).first
        if target.count() and target.is_visible():
            target.hover(timeout=3000)
            break
    page.mouse.wheel(0, 750)
    return True


def native_json_nodes(value):
    """Walk provider JSON in source order; each adapter verifies its own IDs."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from native_json_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from native_json_nodes(child)


def native_page_json(page, *, max_bytes=8_000_000):
    """Read inert native SSR JSON, without evaluating page scripts or storage."""
    used = 0
    for body in page.locator('script[type="application/json"]').all_text_contents():
        used += len(body)
        if used > max_bytes:
            break
        try:
            value = json.loads(body)
        except (ValueError, TypeError):
            continue
        if isinstance(value, (dict, list)):
            yield value

_LEGACY_IPV4_LITERAL = re.compile(
    r"(?:0[xX][0-9a-fA-F]+|[0-9]+)(?:\.(?:0[xX][0-9a-fA-F]+|[0-9]+)){0,3}\Z"
)


def _is_local_browser_host(host: str | None) -> bool:
    """Recognize canonical and legacy loopback aliases without doing DNS."""
    normalized = str(host or "").strip().lower().rstrip(".")
    if not normalized:
        return False
    if (normalized in {"localhost", "localhost.localdomain"}
            or normalized.endswith(".localhost")):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        if not _LEGACY_IPV4_LITERAL.fullmatch(normalized):
            return False
        try:
            address = ipaddress.ip_address(socket.inet_aton(normalized))
        except OSError:
            # An invalid numeric address is treated as local and then fails the
            # registered-profile check, instead of reaching an unowned endpoint.
            return True
    mapped = getattr(address, "ipv4_mapped", None)
    return bool(
        address.is_loopback
        or address.is_unspecified
        or (mapped and (mapped.is_loopback or mapped.is_unspecified))
    )


def _parse_browser_endpoint(endpoint: str):
    """Parse a credential-free HTTP(S) endpoint without resolving its host."""
    try:
        parsed = urlsplit(str(endpoint or "").strip())
        port = parsed.port
    except ValueError:
        return None
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.netloc.endswith(":")):
        return None
    if port is not None and not 1 <= port <= 65535:
        return None
    return parsed, port or (443 if parsed.scheme == "https" else 80)


# ============================================================
# 六态定义（对齐系统采集状态机，禁止与“0 条”混淆）
# ============================================================
class PageState:
    SUCCESS = "SUCCESS"              # 正常取到内容（是否有数据由选择器另行判断）
    EMPTY = "EMPTY"                  # 正常加载但确无结果
    BLOCKED = "BLOCKED"              # IP/风控拦截（如小红书 300012、Google knitsail）
    CAPTCHA = "CAPTCHA"              # 人机/滑块/图形验证码
    AUTH_FAILED = "AUTH_FAILED"      # 登录态失效，需重新登录/扫码
    NETWORK_ERROR = "NETWORK_ERROR"  # 网络中断、加载失败、about:blank


# 各状态的通用文本特征（小写匹配）；平台特有特征可在 detect_state 追加
_STATE_MARKERS = {
    PageState.BLOCKED: [
        "300012", "ip存在风险", "安全限制", "访问过于频繁", "unusual traffic",
        "如果您无法访问", "knitsail", "请求过于频繁", "系统检测到异常",
    ],
    PageState.CAPTCHA: [
        "图形验证码", "拖动滑块", "完成安全验证", "点击验证", "人机验证",
        "我不是机器人", "captcha", "nc_icon", "安全验证", "请通过验证", "滑块验证",
    ],
    PageState.AUTH_FAILED: [
        "请先登录", "扫码登录", "登录后查看", "登录后即可", "website-login",
        "请登录", "登录小红书", "登录抖音", "验证码登录", "密码登录", "sign in to continue",
    ],
    PageState.NETWORK_ERROR: [
        "无法访问此网站", "加载失败", "err_", "连接超时", "网页可能暂时无法连接",
        "dns_probe", "网络错误", "请检查网络",
    ],
}

# 纵深防御：掩盖最显性的自动化指纹（真实 Edge + CDP 下多数本就不存在）
_STEALTH_INIT_JS = r"""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
if (!window.chrome) { window.chrome = { runtime: {} }; }
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
  window.navigator.permissions.query = (p) => (
    p && p.name === 'notifications'
      ? Promise.resolve({state: Notification.permission})
      : originalQuery(p)
  );
}
"""


def is_cdp_open(host: str = "127.0.0.1", port: int | None = None,
                timeout: float = 1.0) -> bool:
    """Check an explicitly owner-resolved CDP port; never assume a legacy port."""
    if port is None:
        return False
    try:
        port = int(port)
    except (TypeError, ValueError):
        return False
    if not 1 <= port <= 65535:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


def is_cdp_url_open(cdp_url: str, timeout: float = 1.0) -> bool:
    """Check only TCP reachability for an explicitly configured worker URL."""
    endpoint = _parse_browser_endpoint(cdp_url)
    if endpoint is None:
        return False
    parsed, port = endpoint
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except Exception:
        return False


def readonly_worker_spec(platform: str, private_data_dir=None) -> dict:
    """Resolve isolated worker parameters from the existing platform catalog."""
    from lumenis.system.collector.adapters.config import get_platform_capabilities

    from .cookie_vault import registered_session_data_dir

    binding = get_platform_capabilities(platform).get("readonly_worker")
    if not isinstance(binding, dict):
        raise RuntimeError("READONLY_WORKER_NOT_REGISTERED")
    root = (Path(private_data_dir) if private_data_dir is not None
            else registered_session_data_dir() / "private")
    profiles = (root / "profiles").resolve()
    profile = (profiles / binding["profile"]).resolve()
    if profile.parent != profiles or binding["port"] in {9222, 9223, 9224}:
        raise RuntimeError("READONLY_WORKER_BOUNDARY_INVALID")
    return {"account": binding["account"], "port": binding["port"],
            "profile": str(profile), "env_prefix": binding["env_prefix"],
            "home": "about:blank", "direct": False}


def _normalized_profile(path) -> str:
    return os.path.normcase(os.path.abspath(os.path.normpath(str(path or "")))).rstrip("\\/")


def registered_browser_worker_spec(identity: str, *, port: int | None = None,
                                   profile: str | None = None) -> dict:
    """Resolve one exact platform account or one exact registered local worker."""
    from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES

    candidate = str(identity or "").strip()
    candidate_folded = candidate.casefold()
    matches = []
    for platform, config in PLATFORM_CAPABILITIES.items():
        binding = config.get("readonly_worker") if isinstance(config, dict) else None
        if not isinstance(binding, dict):
            continue
        spec = readonly_worker_spec(platform)
        if (candidate_folded in {platform.casefold(), str(binding.get("account", "")).casefold()}
                or (port is not None and int(port) == int(spec["port"])
                    and (profile is None or _normalized_profile(profile) == _normalized_profile(spec["profile"])) )):
            matches.append({**spec, "platform": platform})

    # XHS resolves through its existing HK/International SYSTEM session owner;
    # the identity registry carries no fixed CDP port.
    if candidate_folded in {"xhs_retinaut", "xiaohongshu", "xhs"}:
        try:
            import cdp_helper
            import xhs_cookie_bridge as bridge
            account = bridge.XHS_RETINAUT_NAME
            binding = bridge.ACCOUNT_PROFILES[account]
            xhs_profile = binding.get("profile") if isinstance(binding, dict) else binding[1]
            if not os.path.isabs(xhs_profile):
                xhs_profile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", xhs_profile)
            xhs_profile = os.path.realpath(os.path.abspath(os.path.expanduser(xhs_profile)))
            registered = cdp_helper._registered_xhs_binding(account)
            if (not registered or _normalized_profile(xhs_profile)
                    != _normalized_profile(registered["profile"])):
                raise RuntimeError("XHS_REGISTERED_PROFILE_UNAVAILABLE")
            worker = cdp_helper.resolve_registered_xhs_worker(account=account)
            xhs_port = int(worker["port"]) if worker.get("available") else 0
            identity_matches = candidate_folded in {account.casefold(), "xiaohongshu", "xhs"}
            owner_matches = (port is not None and int(port) != 0
                             and worker.get("available") and int(port) == xhs_port
                             and (profile is None or _normalized_profile(profile) == _normalized_profile(xhs_profile)))
            if ((identity_matches and candidate_folded != "default") or owner_matches):
                if port is not None and int(port) not in {0, xhs_port}:
                    raise RuntimeError("BROWSER_WORKER_PORT_MISMATCH")
                matches.append({"platform": "xiaohongshu", "account": account,
                                "port": xhs_port, "profile": xhs_profile,
                                "env_prefix": "XHS", "home": "about:blank",
                                "direct": False, "browser": "edge"})
        except (KeyError, AttributeError, TypeError, ValueError):
            pass

    unique = {(item["platform"], int(item["port"]), _normalized_profile(item["profile"])): item
              for item in matches}
    if len(unique) != 1:
        raise RuntimeError("BROWSER_PLATFORM_OR_WORKER_BINDING_UNAVAILABLE")
    spec = next(iter(unique.values()))
    if port is not None and int(port) not in ({0, int(spec["port"])}
            if spec["platform"] == "xiaohongshu" else {int(spec["port"])}):
        raise RuntimeError("BROWSER_WORKER_PORT_MISMATCH")
    if profile is not None and _normalized_profile(profile) != _normalized_profile(spec["profile"]):
        raise RuntimeError("BROWSER_WORKER_PROFILE_MISMATCH")
    if int(spec["port"]) == 9222:
        raise RuntimeError("PROTECTED_PROFILE_FORBIDDEN")
    return spec


def _task_result_for_platform(task: dict, platform: str) -> tuple[str, dict] | None:
    from lumenis.system.collector.adapters.config import resolve_platform_config_key

    requested = resolve_platform_config_key(platform)
    results = task.get("per_platform") if isinstance(task, dict) else None
    if not isinstance(results, dict):
        return None
    for key, result in results.items():
        try:
            if resolve_platform_config_key(str(key)) == requested and isinstance(result, dict):
                return str(key).casefold(), result
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _authorize_human_interactive(identity: str, task_id: str,
                                 actor_ref: Optional[str] = None) -> str:
    """Require a completed manual Collector task for the exact registered platform."""
    task_id = str(task_id or "").strip()
    if not task_id:
        raise PermissionError("HUMAN_INTERACTIVE_TASK_ID_REQUIRED")
    actor_ref = str(actor_ref or "").strip()
    if not actor_ref:
        raise PermissionError("HUMAN_INTERACTIVE_AUTHENTICATED_ACTOR_REQUIRED")
    spec = registered_browser_worker_spec(identity)
    platform = spec["platform"]
    try:
        from lumenis.adapters import collector_service
        task = collector_service.get_task(task_id)
        task_owner = collector_service.get_task_owner(task_id)
    except Exception:
        task, task_owner = None, None
    if task_owner != actor_ref:
        raise PermissionError("HUMAN_INTERACTIVE_TASK_ACTOR_MISMATCH")
    match = _task_result_for_platform(task, platform) if isinstance(task, dict) else None
    task_platform, result = match if match else ("", None)
    allowed_states = {"AUTH_REQUIRED", "CAPTCHA", "NEED_VERIFY"}
    if (not isinstance(task, dict) or task.get("manual") is not True
            or task.get("status") != "finished" or not isinstance(result, dict)
            or str(result.get("state") or "").upper() not in allowed_states):
        raise PermissionError("HUMAN_INTERACTIVE_COLLECTOR_TASK_UNVERIFIED")
    from lumenis.system.security import OperationType, get_permission_gate
    decision = get_permission_gate().check(
        operation_type=OperationType.BROWSER_OPERATION,
        resource=f"collector.browser.login:{task_platform}:{task_id}",
        caller="lumenis.adapters.human_browser.HUMAN_INTERACTIVE",
        domain_id="system",
    )
    if not decision.allowed:
        raise PermissionError("HUMAN_INTERACTIVE_PERMISSION_DENIED")
    return task_platform


def _authorize_human_browser_return(identity: str, task_id: str,
                                    actor_ref: str | None = None) -> str:
    """Authorize only returning the same actor's already-leased worker.

    The NEED_VERIFY gate remains mandatory for opening HUMAN_INTERACTIVE mode.
    Return is cleanup of an existing lease, so it is bound by the in-memory
    task owner, exact platform lease, and the same browser-operation Permission.
    """
    task_id = str(task_id or "").strip()
    actor_ref = str(actor_ref or "").strip()
    if not task_id:
        raise PermissionError("HUMAN_INTERACTIVE_TASK_ID_REQUIRED")
    if not actor_ref:
        raise PermissionError("HUMAN_INTERACTIVE_AUTHENTICATED_ACTOR_REQUIRED")
    spec = registered_browser_worker_spec(identity)
    platform = spec["platform"]
    from lumenis.adapters import collector_service
    try:
        task = collector_service.get_task(task_id)
        task_owner = collector_service.get_task_owner(task_id)
    except Exception:  # noqa: BLE001 - fail closed when task ownership cannot be read.
        task, task_owner = None, None
    if task_owner != actor_ref:
        raise PermissionError("HUMAN_INTERACTIVE_TASK_ACTOR_MISMATCH")
    match = _task_result_for_platform(task, platform) if isinstance(task, dict) else None
    task_platform = match[0] if match else ""
    if (not isinstance(task, dict) or task.get("manual") is not True
            or not task_platform
            or not collector_service.human_browser_return_lease_owned(
                task_id, task_platform)):
        raise PermissionError("HUMAN_INTERACTIVE_BROWSER_LEASE_REQUIRED")
    from lumenis.system.security import OperationType, get_permission_gate
    decision = get_permission_gate().check(
        operation_type=OperationType.BROWSER_OPERATION,
        resource=f"collector.browser.login:{task_platform}:{task_id}",
        caller="lumenis.adapters.human_browser.HUMAN_INTERACTIVE_RETURN",
        domain_id="system",
    )
    if not decision.allowed:
        raise PermissionError("HUMAN_INTERACTIVE_PERMISSION_DENIED")
    return task_platform


def _require_human_browser_lease(task_id: str, platform: str) -> None:
    """Require the existing Collector service to hold this task's browser lane."""
    from lumenis.adapters import collector_service
    if not collector_service.human_browser_lease_owned(task_id, platform):
        raise PermissionError("HUMAN_INTERACTIVE_BROWSER_LEASE_REQUIRED")


def _worker_mode_state(spec: dict, *, headless: bool):
    import cdp_helper
    if spec.get("platform") == "xiaohongshu":
        state = cdp_helper.resolve_registered_xhs_worker(headless=headless)
        if (not state.get("available")
                or _normalized_profile(spec.get("profile"))
                != _normalized_profile(state.get("profile"))
                or (int(spec.get("port") or 0) not in {0, int(state.get("port") or 0)})):
            return None
        return state["browser"]
    if not spec.get("port"):
        return None
    port, profile = int(spec["port"]), spec["profile"]
    browser = cdp_helper.registered_cdp_browser_for_port(
        port, profile, headless=headless)
    if browser and cdp_helper.is_cdp_profile_running(
            port, profile, headless=headless, loopback_only=True, browser=browser):
        return browser
    return None


def _launch_registered_worker(spec: dict, *, mode: str, browser: str | None = None,
                              task_id: str | None = None,
                              actor_ref: str | None = None) -> dict:
    from scripts.start_resident_browsers import _launch_readonly_worker
    launch_spec = dict(spec)
    if spec.get("platform") == "xiaohongshu":
        # XHS endpoints are assigned by Chromium for each process lifetime. A
        # previously registered port is evidence for the worker being closed,
        # not a reusable endpoint for its replacement.
        launch_spec["port"] = 0
    result = _launch_readonly_worker(
        launch_spec, mode=mode, browser=browser or spec.get("browser"),
        task_id=task_id, platform=spec["account"], actor_ref=actor_ref)
    headless = mode == "BACKGROUND"
    import cdp_helper
    if spec.get("platform") == "xiaohongshu":
        state = cdp_helper.resolve_registered_xhs_worker(
            account=spec["account"], headless=headless)
        exact = (state.get("available") is True
                 and _normalized_profile(spec.get("profile"))
                 == _normalized_profile(state.get("profile"))
                 and state.get("browser") == (browser or spec.get("browser"))
                 and state.get("headless") is headless
                 and state.get("loopback_only") is True
                 and int(state.get("port") or 0) not in {0, 9222, 9223, 9224, 9225,
                                                         9226, 9227, 9228}
                 and str(state.get("endpoint") or "")
                 == f"http://127.0.0.1:{int(state.get('port') or 0)}"
                 and int(state.get("pid") or 0) > 0)
        reported_port = int(result.get("port") or 0)
        reported_pid = int(result.get("pid") or 0)
        reported_endpoint = str(result.get("endpoint") or "")
        launch_matches = (reported_port == int(state.get("port") or 0)
                          and reported_pid == int(state.get("pid") or 0)
                          and reported_endpoint == str(state.get("endpoint") or "")
                          and result.get("account") == state.get("account")
                          and _normalized_profile(result.get("profile"))
                          == _normalized_profile(state.get("profile")))
        online = result.get("online") is True and exact and launch_matches
        return {"online": online, "browser": state.get("browser") if exact else browser,
                "action": result.get("action") or "worker_unavailable",
                "code": result.get("error_code") or result.get("code"),
                "port": state.get("port") if online else None,
                "endpoint": state.get("endpoint") if online else None,
                "pid": state.get("pid") if online else None,
                "profile": state.get("profile") if online else None,
                "account": state.get("account") if online else spec.get("account")}
    online = result.get("online") is True and bool(_worker_mode_state(spec, headless=headless))
    return {"online": online, "browser": result.get("browser") or browser,
            "action": result.get("action") or "worker_unavailable"}


def _switch_registered_worker_mode(spec: dict, *, target_mode: str,
                                   task_id: str | None = None,
                                   actor_ref: str | None = None) -> dict:
    """Switch one verified isolated worker gracefully while its task lease is held."""
    target_mode = str(target_mode or "BACKGROUND").upper()
    if target_mode not in {"BACKGROUND", "HUMAN_INTERACTIVE"}:
        raise RuntimeError("BROWSER_MODE_INVALID")
    if target_mode == "HUMAN_INTERACTIVE":
        task_platform = _authorize_human_interactive(
            spec["account"], task_id or "", actor_ref)
        _require_human_browser_lease(task_id or "", task_platform)
    target_headless = target_mode == "BACKGROUND"
    import cdp_helper
    if spec.get("platform") == "xiaohongshu":
        current = cdp_helper.resolve_registered_xhs_worker()
        if current.get("available"):
            desired = current.get("headless") is target_headless
            if desired:
                return {"online": True, "browser": "edge", "action": "already_online",
                        "port": current["port"]}
            if current.get("browser") != "edge":
                raise RuntimeError("READONLY_WORKER_KERNEL_UNVERIFIED")
            closed = cdp_helper.close_cdp_browser(
                int(current["port"]), current["profile"],
                headless=not target_headless, browser="edge")
            if closed.get("success") is not True:
                raise RuntimeError("READONLY_WORKER_GRACEFUL_CLOSE_UNCONFIRMED")
        else:
            if current.get("code") != "XHS_REGISTERED_WORKER_UNAVAILABLE":
                raise RuntimeError(str(current.get("code") or "XHS_WORKER_OWNER_UNVERIFIED"))
        result = _launch_registered_worker(
            spec, mode=target_mode, browser="edge", task_id=task_id,
            actor_ref=actor_ref)
        if not result["online"]:
            raise RuntimeError(result.get("code") or "READONLY_WORKER_MODE_START_UNVERIFIED")
        if (not result.get("port") or not result.get("endpoint")
                or not result.get("pid")
                or _normalized_profile(spec.get("profile"))
                != _normalized_profile(result.get("profile"))
                or result.get("account") != spec.get("account")):
            raise RuntimeError("READONLY_WORKER_NEW_ENDPOINT_UNVERIFIED")
        return {"online": True, "browser": "edge", "action": result["action"],
                "port": result["port"], "endpoint": result["endpoint"],
                "pid": result["pid"], "profile": result["profile"],
                "account": result["account"]}

    port, profile = int(spec["port"]), spec["profile"]
    desired = _worker_mode_state(spec, headless=target_headless)
    opposite = _worker_mode_state(spec, headless=not target_headless)
    if cdp_helper.is_cdp_port_open(port):
        if desired:
            if target_mode == "HUMAN_INTERACTIVE":
                raise RuntimeError("HUMAN_INTERACTIVE_WORKER_OWNER_UNVERIFIED")
            return {"online": True, "browser": desired, "action": "already_online"}
        if not opposite:
            raise RuntimeError("READONLY_WORKER_PORT_IN_USE_UNVERIFIED")
        closed = cdp_helper.close_cdp_browser(
            port, profile, headless=not target_headless, browser=opposite)
        if closed.get("success") is not True or cdp_helper.is_cdp_port_open(port):
            raise RuntimeError("READONLY_WORKER_GRACEFUL_CLOSE_UNCONFIRMED")
        selected_browser = opposite
    else:
        selected_browser = None

    result = _launch_registered_worker(
        spec, mode=target_mode, browser=selected_browser, task_id=task_id,
        actor_ref=actor_ref)
    if not result["online"]:
        raise RuntimeError("READONLY_WORKER_MODE_START_UNVERIFIED")
    return {"online": True, "browser": result["browser"], "action": result["action"]}


def return_registered_worker_to_background(platform: str, *, task_id: str,
                                           actor_ref: Optional[str] = None) -> dict:
    """Restore the same human task's isolated worker to verified headless mode."""
    spec = registered_browser_worker_spec(platform)
    task_platform = _authorize_human_browser_return(
        spec["account"], task_id, actor_ref)
    from lumenis.adapters import collector_service
    if not collector_service.begin_background_browser_return(task_id, task_platform):
        raise PermissionError("HUMAN_INTERACTIVE_TASK_OR_WORKER_NOT_OWNED")
    try:
        _worker_endpoint(spec)
        with collector_service.platform_activity_lock(task_platform) as acquired:
            if acquired is not True:
                raise RuntimeError("COLLECTOR_MAINTENANCE_ATTEMPT_ACTIVE")
            worker = _switch_registered_worker_mode(
                spec, target_mode="BACKGROUND", task_id=task_id,
                actor_ref=actor_ref)
        if not collector_service.update_human_browser_state(
                task_id, task_platform, "RETURNED_BACKGROUND", release_lease=True):
            raise RuntimeError("HUMAN_INTERACTIVE_TASK_STATE_UPDATE_FAILED")
        return {"platform": spec["platform"], "account": spec["account"],
                "task_id": task_id, "mode": "BACKGROUND",
                "status": "RETURNED_BACKGROUND", "worker_verified": worker["online"],
                "session_state": "NEED_VERIFY"}
    except Exception:
        collector_service.update_human_browser_state(
            task_id, task_platform, "BLOCKED", release_lease=False)
        raise


def _worker_endpoint(spec: dict) -> str:
    if spec["platform"] == "xiaohongshu":
        import cdp_helper
        state = cdp_helper.resolve_registered_xhs_worker(account=spec["account"])
        if (not state.get("available")
                or _normalized_profile(state.get("profile"))
                != _normalized_profile(spec.get("profile"))
                or (int(spec.get("port") or 0) not in {0, int(state.get("port") or 0)})):
            raise RuntimeError("XHS_REGISTERED_BROWSER_SESSION_UNAVAILABLE")
        expected = str(state.get("endpoint") or "")
        configured = os.getenv("XHS_CDP_URL", "").strip()
        if configured and configured.rstrip("/") != expected:
            raise RuntimeError("XHS_INTERACTIVE_WORKER_ENDPOINT_MISMATCH")
        return expected
    expected = f"http://127.0.0.1:{int(spec['port'])}"
    prefix = spec["env_prefix"]
    configured = os.getenv(prefix + "_CDP_URL", "").strip()
    enabled = os.getenv(prefix + "_LOCAL_WORKER_ENABLED", "").strip().lower()
    account = os.getenv(prefix + "_LOCAL_WORKER_ACCOUNT", "").strip().upper()
    if (configured != expected or enabled not in {"1", "true", "yes"}
            or account != spec["account"]):
        raise RuntimeError("READONLY_WORKER_NOT_CONFIGURED")
    return expected


def ensure_registered_browser_worker_background(platform: str) -> dict:
    """Ensure the exact registered worker is headless; never replace a visible/unknown owner."""
    spec = registered_browser_worker_spec(platform)
    import cdp_helper
    if spec.get("platform") == "xiaohongshu":
        result = cdp_helper.ensure_registered_xhs_worker(headless=True)
        state = cdp_helper.resolve_registered_xhs_worker(headless=True)
        online = result.get("success") is True and state.get("available") is True
        return {"status": ("ALREADY_RUNNING" if result.get("reused") else "RECOVERED")
                if online else "UNAVAILABLE", "worker_verified": online,
                "reason": None if online else result.get("code") or state.get("code"),
                "platform": spec["platform"], "account": spec["account"],
                "port": state.get("port") if online else None}
    _worker_endpoint(spec)
    current = _worker_mode_state(spec, headless=True)
    if current:
        return {"status": "ALREADY_RUNNING", "worker_verified": True,
                "platform": spec["platform"], "account": spec["account"]}
    if cdp_helper.is_cdp_port_open(spec["port"]):
        return {"status": "BLOCKED", "worker_verified": False,
                "reason": "READONLY_WORKER_PORT_IN_USE_UNVERIFIED",
                "platform": spec["platform"], "account": spec["account"]}
    try:
        worker = _launch_registered_worker(spec, mode="BACKGROUND")
    except Exception:
        return {"status": "UNAVAILABLE", "worker_verified": False,
                "reason": "READONLY_WORKER_BACKGROUND_START_FAILED",
                "platform": spec["platform"], "account": spec["account"]}
    return {"status": "RECOVERED" if worker["online"] else "UNAVAILABLE",
            "worker_verified": worker["online"],
            "reason": None if worker["online"] else "READONLY_WORKER_IDENTITY_UNVERIFIED",
            "platform": spec["platform"], "account": spec["account"]}


def configured_readonly_worker_url(platform: str, *, mode: str = "BACKGROUND",
                                   task_id: Optional[str] = None,
                                   actor_ref: Optional[str] = None) -> str:
    """Resolve the exact registered local profile and requested browser mode."""
    import cdp_helper

    mode = str(mode or "BACKGROUND").upper()
    if mode not in {"BACKGROUND", "HUMAN_INTERACTIVE"}:
        raise RuntimeError("BROWSER_MODE_INVALID")
    if mode == "HUMAN_INTERACTIVE":
        task_platform = _authorize_human_interactive(platform, task_id or "", actor_ref)
        _require_human_browser_lease(task_id or "", task_platform)
    spec = registered_browser_worker_spec(platform)
    if spec.get("platform") == "xiaohongshu":
        return _worker_endpoint(spec)
    spec = readonly_worker_spec(platform)
    prefix = spec["env_prefix"]
    expected_url = f"http://127.0.0.1:{spec['port']}"
    configured = os.getenv(prefix + "_CDP_URL", "").strip()
    enabled = os.getenv(prefix + "_LOCAL_WORKER_ENABLED", "").strip().lower()
    account = os.getenv(prefix + "_LOCAL_WORKER_ACCOUNT", "").strip().upper()
    if (configured != expected_url or enabled not in {"1", "true", "yes"}
            or account != spec["account"]):
        raise RuntimeError("READONLY_WORKER_NOT_CONFIGURED")
    expected_headless = mode == "BACKGROUND"
    if not cdp_helper.registered_cdp_browser_for_port(
            spec["port"], spec["profile"], headless=expected_headless):
        raise RuntimeError("READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE")
    return expected_url

def open_readonly_worker_login(platform: str, *, task_id: str,
                               actor_ref: Optional[str] = None) -> dict:
    """Switch one registered worker to visible mode for an authorized task."""
    login_urls = {
        "instagram": "https://www.instagram.com/accounts/login/",
        "facebook": "https://www.facebook.com/login/",
        "douyin": "https://www.douyin.com/",
        "x": "https://x.com/i/flow/login",
        "xiaohongshu": "https://www.rednote.com/",
    }
    spec = registered_browser_worker_spec(platform)
    platform = spec["platform"]
    if platform not in login_urls:
        raise ValueError("no approved readonly login entry")
    task_platform = _authorize_human_interactive(spec["account"], task_id, actor_ref)
    from lumenis.adapters import collector_service
    if not collector_service.begin_human_browser(task_id, task_platform):
        raise PermissionError("HUMAN_INTERACTIVE_TASK_OR_WORKER_BUSY")
    transition_started = False
    try:
        if not collector_service.human_browser_lease_owned(task_id, task_platform):
            raise RuntimeError("COLLECTOR_BROWSER_LANE_NOT_RESERVED")
        with collector_service.platform_activity_lock(task_platform) as acquired:
            if acquired is not True:
                raise RuntimeError("COLLECTOR_MAINTENANCE_ATTEMPT_ACTIVE")
            initial_human_worker = bool(_worker_mode_state(spec, headless=False))
            initial_headless_worker = bool(_worker_mode_state(spec, headless=True))
            import cdp_helper
            if initial_human_worker:
                raise RuntimeError("HUMAN_INTERACTIVE_WORKER_OWNER_UNVERIFIED")
            if (cdp_helper.is_cdp_port_open(spec["port"])
                    and not initial_headless_worker):
                raise RuntimeError("READONLY_WORKER_PORT_IN_USE_UNVERIFIED")
            if spec.get("platform") == "xiaohongshu":
                if initial_headless_worker:
                    _worker_endpoint(spec)
                else:
                    current = cdp_helper.resolve_registered_xhs_worker(
                        account=spec["account"])
                    if (current.get("available")
                            or current.get("code") != "XHS_REGISTERED_WORKER_UNAVAILABLE"):
                        raise RuntimeError(
                            current.get("code") or "HUMAN_INTERACTIVE_WORKER_OWNER_UNVERIFIED")
            else:
                _worker_endpoint(spec)
            transition_started = True
            worker = _switch_registered_worker_mode(
                spec, target_mode="HUMAN_INTERACTIVE", task_id=task_id,
                actor_ref=actor_ref)
            if not worker["online"]:
                raise RuntimeError("READONLY_WORKER_HUMAN_MODE_UNAVAILABLE")
            if spec.get("platform") == "xiaohongshu":
                human_spec = registered_browser_worker_spec(
                    spec["account"], profile=spec["profile"])
                state = cdp_helper.resolve_registered_xhs_worker(
                    account=spec["account"], headless=False,
                    port=worker.get("port"))
                if (not state.get("available")
                        or int(state.get("pid") or 0) != int(worker.get("pid") or 0)
                        or int(state.get("port") or 0) != int(worker.get("port") or 0)
                        or _normalized_profile(state.get("profile"))
                        != _normalized_profile(spec.get("profile"))
                        or state.get("endpoint") != worker.get("endpoint")
                        or human_spec.get("port") != state.get("port")):
                    raise RuntimeError("HUMAN_INTERACTIVE_NEW_WORKER_IDENTITY_UNVERIFIED")
                if (_authorize_human_interactive(spec["account"], task_id, actor_ref)
                        != task_platform):
                    raise PermissionError("HUMAN_INTERACTIVE_TASK_SCOPE_CHANGED")
                _require_human_browser_lease(task_id, task_platform)
                endpoint = _worker_endpoint(human_spec)
                if endpoint != state.get("endpoint"):
                    raise RuntimeError("HUMAN_INTERACTIVE_ENDPOINT_CHANGED")
            else:
                endpoint = _worker_endpoint(spec)
            from urllib.parse import urlsplit

            from playwright.sync_api import sync_playwright
            target_host = (urlsplit(login_urls[platform]).hostname or "").lower()
            opened = False
            with sync_playwright() as runtime:
                browser = runtime.chromium.connect_over_cdp(endpoint, timeout=10000)
                if not browser.contexts:
                    raise RuntimeError("registered human worker context unavailable")
                context = browser.contexts[0]
                page = next((item for item in context.pages
                             if (urlsplit(item.url).hostname or "").lower() == target_host), None)
                if page is None:
                    page = context.new_page()
                    page.goto(login_urls[platform], wait_until="domcontentloaded", timeout=40000)
                    opened = True
                page.bring_to_front()
        if not collector_service.update_human_browser_state(
                task_id, task_platform, "ACTIVE", release_lease=False):
            raise RuntimeError("HUMAN_INTERACTIVE_TASK_STATE_UPDATE_FAILED")
    except Exception:
        # If a visible worker was started but login UI setup failed, return it to
        # BACKGROUND. A failed graceful return keeps the lane leased and blocked.
        try:
            if transition_started and not _worker_mode_state(spec, headless=True):
                with collector_service.platform_activity_lock(task_platform) as acquired:
                    if acquired is not True:
                        raise RuntimeError("COLLECTOR_MAINTENANCE_ATTEMPT_ACTIVE")
                    _switch_registered_worker_mode(
                        spec, target_mode="BACKGROUND", task_id=task_id,
                        actor_ref=actor_ref)
            collector_service.update_human_browser_state(
                task_id, task_platform, "BLOCKED", release_lease=True)
        except Exception:
            collector_service.update_human_browser_state(
                task_id, task_platform, "BLOCKED", release_lease=False)
        raise
    return {"platform": platform, "account": spec["account"],
            "task_id": str(task_id), "mode": "HUMAN_INTERACTIVE",
            "status": "HUMAN_LOGIN_OPENED" if opened else "HUMAN_LOGIN_REUSED",
            "login_url": login_urls[platform], "worker_verified": worker["online"],
            "session_verified": False}

def recover_registered_readonly_worker(platform: str, *, mode: str = "BACKGROUND") -> dict:
    """Recover only a registered headless worker; never open UI during recovery."""
    if str(mode or "BACKGROUND").upper() != "BACKGROUND":
        return {"status": "BLOCKED", "worker_verified": False,
                "reason": "AUTOMATIC_HUMAN_INTERACTIVE_FORBIDDEN",
                "session_verified": False}
    try:
        configured_readonly_worker_url(platform, mode="BACKGROUND")
        return {"status": "ALREADY_RUNNING", "worker_verified": True,
                "session_verified": False}
    except RuntimeError as exc:
        code = str(exc)
        unavailable_codes = {
            "READONLY_WORKER_PROFILE_OR_MODE_UNAVAILABLE",
            "READONLY_WORKER_PROFILE_MODE_OR_KERNEL_UNAVAILABLE",
        }
        if code not in unavailable_codes:
            allowed = {"READONLY_WORKER_NOT_REGISTERED", "READONLY_WORKER_NOT_CONFIGURED",
                       "READONLY_WORKER_BOUNDARY_INVALID"}
            return {"status": "UNAVAILABLE", "worker_verified": False,
                    "reason": code if code in allowed else "READONLY_WORKER_CONFIGURATION_ERROR",
                    "session_verified": False}
        spec = readonly_worker_spec(platform)
        import cdp_helper
        if cdp_helper.is_cdp_port_open(spec["port"]):
            return {"status": "BLOCKED", "worker_verified": False,
                    "reason": "READONLY_WORKER_PORT_IN_USE_UNVERIFIED",
                    "session_verified": False}
    from scripts.start_resident_browsers import _launch_readonly_worker
    try:
        result = _launch_readonly_worker(readonly_worker_spec(platform), mode="BACKGROUND")
        online = result.get("online") is True
        action = result.get("action")
        return {"status": "RECOVERED" if online else "UNAVAILABLE",
                "worker_verified": online, "session_verified": False,
                "reason": (None if online else "READONLY_WORKER_IDENTITY_UNVERIFIED"
                           if action == "port_in_use_unverified" else "READONLY_WORKER_START_FAILED"),
                "recovery_action": action if action in {"started", "already_online", "port_in_use_unverified"}
                                   else "FAILED"}
    except Exception:
        return {"status": "UNAVAILABLE", "worker_verified": False,
                "reason": "READONLY_WORKER_START_FAILED", "session_verified": False}


def readonly_worker_health(platform: str) -> dict:
    """Expose connectivity separately from a real platform login or result."""
    try:
        endpoint = configured_readonly_worker_url(platform)
    except (KeyError, RuntimeError):
        return {"status": "NOT_CONFIGURED", "ready": False,
                "metadata": {"provider": "authorized_browser_worker",
                             "healthcheck_scope": "configuration_only",
                             "worker_binding_registered": False,
                             "login_and_collection_verified": False}}
    online = is_cdp_url_open(endpoint)
    return {"status": "NEED_VERIFY" if online else "PROVIDER_UNAVAILABLE", "ready": False,
            "metadata": {"provider": "authorized_browser_worker",
                         "healthcheck_scope": "worker_connectivity",
                         "worker_binding_registered": True, "endpoint_configured": True,
                         "session_state": "worker_reachable_unverified" if online else "worker_unavailable",
                         "login_and_collection_verified": False}}


@dataclass
class HumanConfig:
    """拟人节奏参数（毫秒/秒级，贴近真人分布）。"""
    type_min_ms: int = 70           # 单键最小间隔
    type_max_ms: int = 240          # 单键最大间隔
    typo_prob: float = 0.03         # 误触后回删重打的概率
    scroll_min_px: int = 120        # 单次滚动最小距离
    scroll_max_px: int = 520        # 单次滚动最大距离
    scroll_back_prob: float = 0.10  # 小幅回滚概率
    move_duration_s: tuple[float, float] = (0.4, 0.9)
    settle_s: tuple[float, float] = (0.1, 0.4)   # 鼠标到位后、点击前停顿
    pause_s: tuple[float, float] = (0.6, 1.6)    # 动作间普通停顿


class HumanBrowser:
    """连接已注册 CDP Worker；后台无头，人工可见模式必须有已验证任务与权限。"""

    def __init__(self, cdp_url: Optional[str] = None,
                 config: Optional[HumanConfig] = None,
                 auto_ensure: bool = True, *,
                 port: int | None = None, profile_dir: str | None = None,
                 proxy_server: Optional[str] = None,
                 launch_url: str = "about:blank",
                 browser: Optional[str] = None, mode: str = "BACKGROUND",
                 task_id: Optional[str] = None,
                 actor_ref: Optional[str] = None):
        self._explicit_cdp_url = bool(cdp_url)
        self.mode = str(mode or "BACKGROUND").upper()
        if self.mode not in {"BACKGROUND", "HUMAN_INTERACTIVE"}:
            raise ValueError("BROWSER_MODE_INVALID")
        if not cdp_url and port is None:
            raise ValueError("BROWSER_WORKER_ENDPOINT_REQUIRED")
        self.port = int(port) if port is not None else None
        self.cdp_url = str(cdp_url or (f"http://127.0.0.1:{self.port}" if self.port else ""))
        self.profile_dir = profile_dir
        self.proxy_server = proxy_server
        self.launch_url = launch_url
        self.browser = str(browser).lower() if browser else (None if cdp_url else "edge")
        self.cfg = config or HumanConfig()
        self.auto_ensure = auto_ensure
        self.task_id = str(task_id or "").strip()
        self.actor_ref = str(actor_ref or "").strip()
        if self.mode == "HUMAN_INTERACTIVE":
            if self.port == 0 and not self._explicit_cdp_url:
                self.platform = "xiaohongshu"
                self.human_task_platform = _authorize_human_interactive(
                    "XHS_RETINAUT", self.task_id, self.actor_ref)
                _require_human_browser_lease(self.task_id, self.human_task_platform)
                self.browser = "edge"
                self._pw = None
                self._browser = None
                self._context = None
                self._owned_pages = []
                return
            endpoint = _parse_browser_endpoint(self.cdp_url)
            if endpoint is None or not _is_local_browser_host(endpoint[0].hostname):
                raise PermissionError("HUMAN_INTERACTIVE_WORKER_IDENTITY_UNAVAILABLE")
            _, self.port = endpoint
            if self.port in {9222, 9223}:
                raise PermissionError("REGISTERED_WORKER_ENDPOINT_REQUIRED")
            import cdp_helper
            profile = self.profile_dir or cdp_helper.registered_cdp_profile_for_port(
                self.port, browser=self.browser)
            if not profile:
                raise PermissionError("HUMAN_INTERACTIVE_WORKER_IDENTITY_UNAVAILABLE")
            worker = registered_browser_worker_spec(
                "", port=self.port, profile=profile)
            self.profile_dir = worker["profile"]
            self.platform = worker["platform"]
            self.human_task_platform = _authorize_human_interactive(
                worker["account"], self.task_id, self.actor_ref)
            _require_human_browser_lease(self.task_id, self.human_task_platform)
        elif self.port in {9222, 9223}:
            raise ValueError("REGISTERED_WORKER_ENDPOINT_REQUIRED")
        self._pw = None
        self._browser = None
        self._context = None
        self._owned_pages: list = []

    def connect(self):
        """Attach only to the registered profile and exact requested browser mode."""
        if self.port == 0 and not self.cdp_url:
            import cdp_helper
            headless = self.mode == "BACKGROUND"
            binding = cdp_helper._registered_xhs_binding()
            if not binding:
                raise RuntimeError("XHS_REGISTERED_IDENTITY_UNAVAILABLE")
            if self.profile_dir and _normalized_profile(self.profile_dir) != _normalized_profile(binding["profile"]):
                raise PermissionError("XHS_REGISTERED_PROFILE_BINDING_MISMATCH")
            self.profile_dir = binding["profile"]
            worker = cdp_helper.resolve_registered_xhs_worker(headless=headless)
            if not worker.get("available") and self.auto_ensure:
                self._ensure_browser()
                worker = cdp_helper.resolve_registered_xhs_worker(headless=headless)
            if not worker.get("available"):
                raise RuntimeError(str(worker.get("code") or "XHS_REGISTERED_WORKER_UNAVAILABLE"))
            self.port = int(worker["port"])
            self.cdp_url = str(worker["endpoint"])
            self.browser = "edge"
        endpoint = _parse_browser_endpoint(self.cdp_url)
        if endpoint is None:
            raise RuntimeError("configured browser worker endpoint is invalid")
        parsed, endpoint_port = endpoint
        local = _is_local_browser_host(parsed.hostname)
        if local:
            self.port = endpoint_port
            if self.port == 9222:
                raise RuntimeError("PROTECTED_PROFILE_FORBIDDEN")
            if self.port == 9223:
                raise RuntimeError("REGISTERED_WORKER_ENDPOINT_REQUIRED")
            import cdp_helper
            expected_headless = self.mode == "BACKGROUND"
            if not self.profile_dir:
                self.profile_dir = cdp_helper.registered_cdp_profile_for_port(
                    self.port, browser=self.browser)
            if not self.profile_dir:
                raise RuntimeError("BROWSER_PROFILE_OWNER_UNAVAILABLE")
            if self.browser is None:
                self.browser = cdp_helper.registered_cdp_browser_for_port(
                    self.port, self.profile_dir, headless=expected_headless)
                if not self.browser:
                    raise RuntimeError("BROWSER_WORKER_KERNEL_OR_IDENTITY_UNVERIFIED")
            exact = cdp_helper.is_cdp_profile_running(
                self.port, self.profile_dir, headless=expected_headless,
                loopback_only=True, browser=self.browser)
            if not exact and self.mode == "HUMAN_INTERACTIVE":
                _require_human_browser_lease(self.task_id, self.human_task_platform)
                raise RuntimeError("HUMAN_INTERACTIVE_WORKER_NOT_PREPARED")
            if not exact and self.auto_ensure and not self._explicit_cdp_url:
                self._ensure_browser()
                exact = cdp_helper.is_cdp_profile_running(
                    self.port, self.profile_dir, headless=expected_headless,
                    loopback_only=True, browser=self.browser)
            if not exact:
                raise RuntimeError("BROWSER_WORKER_PROFILE_OR_MODE_UNAVAILABLE")
        elif self.auto_ensure:
            raise RuntimeError("REMOTE_BROWSER_CANNOT_BE_STARTED_BY_LOCAL_WORKER")
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(self.cdp_url)
        if not self._browser.contexts:
            raise RuntimeError("CDP 浏览器没有可用的浏览器上下文")
        self._context = self._browser.contexts[0]
        logger.info("HumanBrowser 已连接 %s，既有标签页 %d 个，mode=%s",
                    self.cdp_url, len(self._context.pages), self.mode)
        return self

    def _ensure_browser(self):
        """Start only the registered isolated profile in the selected mode."""
        if self.mode == "HUMAN_INTERACTIVE":
            _require_human_browser_lease(self.task_id, self.human_task_platform)
        try:
            import cdp_helper
            kwargs = {"port": self.port, "profile_dir": self.profile_dir,
                      "auto_start": True, "headless": self.mode == "BACKGROUND",
                      "loopback_only": True, "launch_url": self.launch_url,
                      "browser": self.browser, "task_id": self.task_id,
                      "actor_ref": self.actor_ref}
            if self.proxy_server:
                kwargs["proxy_server"] = self.proxy_server
            info = cdp_helper.ensure_cdp_browser(**kwargs)
            if info.get("available") is not True:
                raise RuntimeError(f"BROWSER_WORKER_UNAVAILABLE: {info.get('message')}")
            time.sleep(0.5)
        except ImportError as e:
            raise RuntimeError("cdp_helper 不可用，无法启动CDP浏览器") from e

    def new_page(self, stealth: bool = True):
        """新建一个干净标签页并注入反检测脚本；返回 page。"""
        page = self._context.new_page()
        if stealth:
            page.add_init_script(_STEALTH_INIT_JS)
        self._owned_pages.append(page)
        return page

    def close(self):
        """只关闭本层创建的标签页与 CDP 连接，绝不动用户的 Edge。"""
        for page in self._owned_pages:
            try:
                if page and not page.is_closed():
                    page.close()
            except Exception:
                pass
        self._owned_pages.clear()
        try:
            if self._browser:
                self._browser.close()  # CDP 下仅断开连接，不关 Edge
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # ---------- 拟人原语 ----------
    @staticmethod
    def pause(a: float, b: float):
        """均匀随机停顿。"""
        time.sleep(random.uniform(a, b))

    @staticmethod
    def gauss_pause(mean: float = 1.0, sigma: float = 0.3, floor: float = 0.2):
        """高斯停顿，模拟真人动作间隔的自然抖动。"""
        time.sleep(max(floor, random.gauss(mean, sigma)))

    @staticmethod
    def _bezier_path(start: tuple[float, float], end: tuple[float, float],
                     steps: int = 24) -> list[tuple[float, float]]:
        """生成带两个随机控制点的三次贝塞尔鼠标轨迹。"""
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        cp1 = (sx + dx * random.uniform(0.2, 0.45) + random.uniform(-30, 30),
               sy + dy * random.uniform(0.2, 0.45) + random.uniform(-30, 30))
        cp2 = (sx + dx * random.uniform(0.55, 0.8) + random.uniform(-30, 30),
               sy + dy * random.uniform(0.55, 0.8) + random.uniform(-30, 30))

        def b(t, p0, p1, p2, p3):
            mt = 1 - t
            return (mt ** 3 * p0 + 3 * mt ** 2 * t * p1 + 3 * mt * t ** 2 * p2 + t ** 3 * p3)

        return [(b(i / steps, sx, cp1[0], cp2[0], ex),
                 b(i / steps, sy, cp1[1], cp2[1], ey)) for i in range(steps + 1)]

    def human_move_and_click(self, page, locator, *, click: bool = True):
        """沿贝塞尔轨迹把鼠标移入元素随机内点，停顿后再真实点击。"""
        locator.scroll_into_view_if_needed(timeout=8000)
        box = locator.bounding_box()
        if not box:
            raise RuntimeError("目标元素无布局位置，无法移动点击")
        tx = box["x"] + box["width"] * random.uniform(0.25, 0.75)
        ty = box["y"] + box["height"] * random.uniform(0.25, 0.75)
        mx = page.mouse
        path = self._bezier_path((random.uniform(0, 400), random.uniform(0, 300)),
                                 (tx, ty))
        dur = random.uniform(*self.cfg.move_duration_s)
        per = dur / len(path)
        for x, y in path:
            mx.move(x, y)
            time.sleep(per)
        self.pause(*self.cfg.settle_s)
        if click:
            mx.down()
            self.pause(0.04, 0.12)
            mx.up()

    def human_type(self, page, locator, text: str, *, clear_first: bool = True):
        """逐字符拟人输入，偶发误触→停顿→退格→重打。"""
        locator.click()
        if clear_first:
            page.keyboard.press("Control+A")
            self.pause(0.08, 0.2)
        for ch in text:
            if random.random() < self.cfg.typo_prob:
                wrong = "z" if ch != "z" else "x"
                page.keyboard.type(wrong)
                self.pause(0.15, 0.4)
                page.keyboard.press("Backspace")
                self.pause(0.1, 0.3)
            page.keyboard.type(ch, delay=random.randint(self.cfg.type_min_ms, self.cfg.type_max_ms))
            if random.random() < 0.05:
                self.gauss_pause(0.5, 0.2)  # 思考式短暂停顿

    def human_scroll(self, page, *, total_px: int = 1600, rounds: Optional[int] = None):
        """变速、偶发小幅回滚地向下滚动，替代固定 mouse.wheel(0,2000)。"""
        scrolled = 0
        rounds = rounds or max(2, total_px // 300)
        for _ in range(rounds):
            if random.random() < self.cfg.scroll_back_prob:
                page.mouse.wheel(0, -random.randint(60, 180))  # 偶尔回看
            else:
                step = random.randint(self.cfg.scroll_min_px, self.cfg.scroll_max_px)
                page.mouse.wheel(0, step)
                scrolled += step
            self.pause(0.3, 0.9)
            if scrolled >= total_px and rounds <= 2:
                break
        return scrolled

    # ---------- 六态识别 ----------
    @staticmethod
    def detect_state(page, *, extra_markers: Optional[dict] = None,
                     success_selector: Optional[str] = None) -> str:
        """依据 URL / 正文 / 结果选择器判定页面六态。

        success_selector 命中即 SUCCESS；未命中且页面正常则 EMPTY；
        命中各风控/登录/网络特征返回对应状态。调用方据此决定熔断或恢复。
        """
        try:
            url_value = page.url
            url = str((url_value() if callable(url_value) else url_value) or "").lower()
        except Exception:
            url = ""
        if url.startswith("about:blank"):
            return PageState.NETWORK_ERROR
        try:
            body = page.locator("body").inner_text(timeout=3000).lower()
        except Exception:
            body = ""

        markers = {k: list(v) for k, v in _STATE_MARKERS.items()}
        if extra_markers:
            for state, words in extra_markers.items():
                markers.setdefault(state, []).extend(w.lower() for w in words)

        # 风控/验证/登录/网络优先级高于空结果判定
        for state in (PageState.BLOCKED, PageState.CAPTCHA,
                      PageState.AUTH_FAILED, PageState.NETWORK_ERROR):
            if any(w.lower() in body or w.lower() in url for w in markers.get(state, [])):
                return state

        if success_selector:
            try:
                if page.locator(success_selector).count() > 0:
                    return PageState.SUCCESS
            except Exception:
                pass
            return PageState.EMPTY if body else PageState.NETWORK_ERROR
        return PageState.SUCCESS if body else PageState.EMPTY
