# -*- coding: utf-8 -*-
"""
统一登录态恢复中心（Auth Recovery Center）—— 配套7 · P0
=========================================================
抽象：Platform Account → Session/Cookie → Health Check → Auth State，
覆盖小红书 / 抖音 / 微博 / B站 / Instagram / Google，*新增平台只需在
RECOVERY_PROFILES 增一条配置，恢复框架本身不改*。

一、完整登录态状态机
  AUTH_VALID → EXPIRED → REQUIRED → QR_DISPLAYED → WAITING_SCAN
     → SCANNED → CONFIRMING → RECOVERED → HEALTH_CHECK → AUTH_VALID
  异常分支：QR_EXPIRED(自动刷新重取) / QR_FAILED(重取) /
           AUTH_FAILED(保持，可重试) / PLATFORM_BLOCKED(进冷却，不伪装成扫码可解)

二、三类问题严格分清（RecoveryKind，绝不互相冒充）
  A. AUTH    登录失效：弹二维码/登录页，走扫码恢复；
  B. VERIFY  人机验证(NEEDED/CAPTCHA)：提示到浏览器人工过验证，不是重新登录；
  C. BLOCKED IP风控/300012/熔断：只冷却降频，明确“扫码无法解决，不硬刚”。

三、不跳页：后端只负责“打开持久Profile官方登录页 + 截图二维码 + 探测恢复”，
弹窗始终停留在用户当前页面（含手机端），由前端全局 Modal 承载。

四、远程恢复：状态/截图均为普通 HTTP 接口，公网部署后手机打开同一地址即可看到
本恢复任务与二维码（公网地址由部署层注入，本模块不写死）。

安全边界：不绕过验证码/风控、不伪造登录；只用用户本人持久 Profile 打开官方登录页，
由用户本人扫码/验证；浏览器没启动时健康检查返回 UNKNOWN，绝不误判成“登录失效”。
"""
import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlsplit

from .risk_controller import (
    IP_RISK,
    NEED_VERIFY,
    risk_controller,
)

ROOT = Path(__file__).resolve().parents[2]

# ---------- 登录态状态机 ----------
AUTH_VALID = "AUTH_VALID"
EXPIRED = "EXPIRED"
REQUIRED = "REQUIRED"
QR_DISPLAYED = "QR_DISPLAYED"
WAITING_SCAN = "WAITING_SCAN"
SCANNED = "SCANNED"
CONFIRMING = "CONFIRMING"
RECOVERED = "RECOVERED"
HEALTH_CHECK = "HEALTH_CHECK"
QR_EXPIRED = "QR_EXPIRED"
QR_FAILED = "QR_FAILED"
AUTH_FAILED = "AUTH_FAILED"
PLATFORM_BLOCKED = "PLATFORM_BLOCKED"
UNKNOWN = "UNKNOWN"

STATE_CN = {
    AUTH_VALID: "登录有效", EXPIRED: "登录已失效", REQUIRED: "准备恢复",
    QR_DISPLAYED: "二维码已展示", WAITING_SCAN: "等待扫码/登录", SCANNED: "已扫码，待确认",
    CONFIRMING: "确认登录中", RECOVERED: "已恢复", HEALTH_CHECK: "恢复后健康检查",
    QR_EXPIRED: "二维码已过期，自动刷新", QR_FAILED: "取码失败，可重取",
    AUTH_FAILED: "尚未恢复", PLATFORM_BLOCKED: "平台风控冷却中", UNKNOWN: "未知（浏览器未启动）",
}

# ---------- 三类问题 ----------
KIND_AUTH = "AUTH"        # A 登录失效→弹码
KIND_VERIFY = "VERIFY"    # B 人机验证→人工过验证
KIND_BLOCKED = "BLOCKED"  # C IP/强风控→冷却，不可扫码解

# 各真人平台配置：新增平台只改这里（框架不动）。XHS 身份与端点由
# SYSTEM Collector 的现有策略/会话 owner 在每个入口重新解析。
RECOVERY_PROFILES = {
    "douyin": {
        "port": 9222, "profile": "edge-cdp-newaccount", "proxy_env": "",
        "login_url": "https://www.douyin.com/",
        "auth_cookies": ["sessionid", "sessionid_ss"],
        "qr_selectors": ["img[src*='qrcode']", "canvas", "[class*='qr'] img", "[class*='QRCode'] canvas"],
        "display": "抖音", "remote_hint": "用抖音App扫码登录",
    },
    "xiaohongshu": {
        "login_url": "https://www.rednote.com/",
        "auth_cookies": ["web_session", "a1"],
        "qr_selectors": ["img.qrcode", "[class*='qrcode'] img", "[class*='login'] canvas", "canvas"],
        "display": "小红书", "remote_hint": "在获准的香港/国际账号上完成登录（风控状态请走冷却）",
    },
    "instagram": {
        "port": 9223, "profile": "edge-cdp-proxy", "proxy_env": "GOOGLE_PROXY",
        "login_url": "https://www.instagram.com/accounts/login/",
        "auth_cookies": ["sessionid", "ds_user_id"],
        "qr_selectors": [],
        "display": "Instagram", "remote_hint": "Instagram 无网页扫码，请在弹出的浏览器登录",
    },
    "google": {
        "port": 9223, "profile": "edge-cdp-proxy", "proxy_env": "GOOGLE_PROXY",
        "login_url": "https://accounts.google.com/",
        "auth_cookies": ["SID", "SAPISID"],
        "qr_selectors": [],
        "display": "Google", "remote_hint": "请在弹出的浏览器登录Google账号",
    },
    "weibo": {
        "port": 9222, "profile": "edge-cdp-newaccount", "proxy_env": "",
        "login_url": "https://weibo.com/login.php",
        "auth_cookies": ["SUB"],
        "qr_selectors": ["[class*='qrcode'] img", "canvas"],
        "display": "微博", "remote_hint": "用微博App扫码登录",
    },
    "bilibili": {
        "port": 9222, "profile": "edge-cdp-newaccount", "proxy_env": "",
        "login_url": "https://passport.bilibili.com/login",
        "auth_cookies": ["SESSDATA"],
        "qr_selectors": ["[class*='qr'] img", "canvas"],
        "display": "B站", "remote_hint": "用哔哩哔哩App扫码登录",
    },
    "x": {
        "login_url": "https://x.com/i/flow/login",
        "auth_cookies": ["auth_token", "ct0"],
        "qr_selectors": [],
        "display": "X", "remote_hint": "Log in to X in the in-product browser login window",
    },
    "facebook": {
        "login_url": "https://www.facebook.com/login/",
        "auth_cookies": ["c_user", "xs"],
        "qr_selectors": [],
        "display": "Facebook", "remote_hint": "Log in to Facebook in the in-product browser login window",
    },
    "wechat_oa": {
        "login_url": "https://mp.weixin.qq.com/",
        "auth_cookies": ["slave_sid", "data_ticket"],
        "qr_selectors": [".login__type__container__scan__qrcode", "img[class*='qrcode']", "canvas"],
        "display": "微信公众号", "remote_hint": "Scan the QR code with WeChat in the in-product login window",
    },
}

# PO rule 2026-10-13 #1: non-XHS platforms bind to their registered background
# worker (headless; visible only as the in-product login popup).
_REGISTERED_WORKER_PLATFORMS = {"douyin", "instagram", "x", "facebook", "wechat_oa"}
_resume_queue: Dict[str, list] = {}


def register_resume(platform: str, resume_fn) -> None:
    """Queue the interrupted task; it runs once login + health check succeed."""
    if callable(resume_fn):
        with _lock:
            _resume_queue.setdefault(platform, []).append(resume_fn)


def _resume_pending(platform: str) -> list:
    with _lock:
        pending = _resume_queue.pop(platform, [])
    results = []
    for fn in pending:
        try:
            results.append({"ok": True, "result": fn()})
        except Exception as exc:  # resume failure is reported, never hidden
            results.append({"ok": False, "error": type(exc).__name__})
    if results:
        _set(platform, resumed=results)
    return results

WATCH_INTERVAL = 10       # 登录态探测周期（秒）
WATCH_TIMEOUT = 60 * 15   # 单个恢复任务最长守候15分钟
QR_REFRESH = 90           # 二维码超过该秒数自动重取（QR_EXPIRED）

_sessions: Dict[str, dict] = {}
_lock = threading.Lock()


def _proxy_for(cfg: dict) -> str:
    env = cfg.get("proxy_env")
    raw = os.environ.get(env or "", "") or os.environ.get("OPENAI_PROXY", "")
    if raw.startswith("http://"):
        raw = raw[7:]
    elif raw.startswith("https://"):
        raw = raw[8:]
    return raw.rstrip("/")


def _shot_path(prefix: str, platform: str) -> Path:
    """Use the current Registry lifecycle; refuse path aliases before IO."""
    import re
    from lumenis.shared.database.registry import get_registry
    if type(platform) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", platform) is None:
        raise ValueError("RECOVERY_PLATFORM_INVALID")
    root = get_registry().data_dir / "recovery"
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise ValueError("RECOVERY_PATH_INVALID")
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{prefix}_{platform}.png"
    if target.is_symlink() or target.resolve().parent != root.resolve():
        raise ValueError("RECOVERY_PATH_INVALID")
    return target


def _full_shot(platform: str) -> Path:
    return _shot_path("login", platform)


def _qr_shot(platform: str) -> Path:
    return _shot_path("qr", platform)


def classify_kind(platform: str, source_state: str = "", detail: str = "") -> str:
    """根据风险等级/六态/错误细节，推导 A/B/C 三类。"""
    text = f"{source_state} {detail}".lower()
    risk = {x["platform"]: x for x in risk_controller.snapshot()}.get(platform, {})
    level = risk.get("level", "")
    if level == IP_RISK or "300012" in text or source_state == "BLOCKED" \
            and ("ip" in text or "风控" in text or "熔断" in text):
        return KIND_BLOCKED
    if source_state == "CAPTCHA" or "captcha" in text or "滑块" in text or "人机" in text:
        return KIND_VERIFY
    if level == NEED_VERIFY or source_state in ("AUTH_REQUIRED", "AUTH_FAILED"):
        return KIND_AUTH
    # 无明确风险信号时，用户手动发起按登录失效处理
    return KIND_AUTH


# ---------- 浏览器探测（不启动浏览器时返回 UNKNOWN，绝不误判失效） ----------
_XHS_RECOVERY_PLATFORM = "xiaohongshu"
_XHS_RECOVERY_REGION = "intl"
_XHS_RECOVERY_HOST = "www.rednote.com"


def _resolve_recovery_profile(platform: str):
    """Resolve XHS identity and CDP endpoint through the existing Collector owner."""
    profile = RECOVERY_PROFILES.get(platform)
    if not profile:
        return None, "RECOVERY_PLATFORM_NOT_CONFIGURED"
    resolved = dict(profile)
    if platform in _REGISTERED_WORKER_PLATFORMS:
        try:
            from .human_browser import (
                readonly_worker_spec,
                registered_browser_worker_spec,
            )
            spec = registered_browser_worker_spec(platform)
            expected = readonly_worker_spec(platform)
            if (not isinstance(spec, dict)
                    or spec.get("platform") != platform
                    or spec.get("account") != expected.get("account")
                    or int(spec.get("port", 0)) != int(expected["port"])
                    or str(spec.get("profile") or "") != str(expected["profile"])):
                return None, "RECOVERY_WORKER_NOT_REGISTERED"
            resolved["port"] = int(spec["port"])
            resolved["profile"] = spec["profile"]
            resolved["cdp_url"] = f"http://127.0.0.1:{int(spec['port'])}"  # attach to the registered background worker; never launch a visible fallback
        except Exception:
            return None, "RECOVERY_WORKER_NOT_REGISTERED"
    if platform != _XHS_RECOVERY_PLATFORM and (
            resolved.get("port") == 9222
            or str(resolved.get("profile") or "").casefold() == "edge-cdp-newaccount"):
        return None, "PROTECTED_PROFILE_NOT_COLLECTION_ASSET"
    if platform != _XHS_RECOVERY_PLATFORM:
        return resolved, ""

    try:
        import collector

        policy_gate = getattr(collector, "_collection_policy_gate", None)
        endpoint_resolver = getattr(collector, "_resolve_server_cdp_url", None)
        if not callable(policy_gate) or not callable(endpoint_resolver):
            return None, "XHS_RECOVERY_POLICY_UNAVAILABLE"

        # The current owner selects and validates the approved default identity.
        identity = policy_gate(region=_XHS_RECOVERY_REGION)
        if not isinstance(identity, dict) or identity.get("ok") is not True:
            return None, "XHS_RECOVERY_POLICY_BLOCKED"
        account = identity.get("account")
        region = identity.get("region")
        host = str(identity.get("host") or "").strip().lower()
        if (not isinstance(account, str) or not account.strip()
                or region != _XHS_RECOVERY_REGION or host != _XHS_RECOVERY_HOST):
            return None, "XHS_RECOVERY_IDENTITY_REJECTED"

        endpoint, endpoint_error = endpoint_resolver(account=account, region=region)
        if endpoint_error or not isinstance(endpoint, str) or not endpoint.strip():
            if endpoint_error == "COLLECTOR_ENDPOINT_NOT_CONFIGURED":
                return None, "XHS_RECOVERY_ENDPOINT_NOT_CONFIGURED"
            if endpoint_error == "POLICY_BLOCKED":
                return None, "XHS_RECOVERY_POLICY_BLOCKED"
            return None, "XHS_RECOVERY_ENDPOINT_INVALID"
        try:
            endpoint_port = urlsplit(endpoint).port
        except ValueError:
            return None, "XHS_RECOVERY_ENDPOINT_INVALID"
        # Defense in depth for the forbidden legacy Mainland endpoint. The
        # canonical resolver remains responsible for all other endpoint policy.
        if endpoint_port == 9222:
            return None, "XHS_RECOVERY_POLICY_BLOCKED"

        resolved["region"] = region
        resolved["account"] = account
        resolved["cdp_url"] = endpoint
        return resolved, ""
    except Exception:
        return None, "XHS_RECOVERY_POLICY_UNAVAILABLE"


def _connect_hb(cfg: dict, auto_ensure: bool = True):
    from .human_browser import HumanBrowser
    if cfg.get("cdp_url"):
        # Use the owner-resolved browser context; never launch a local profile
        # as a fallback for XHS recovery.
        return HumanBrowser(
            cdp_url=cfg["cdp_url"], launch_url="about:blank", auto_ensure=False,
        )
    from .human_browser import is_cdp_open
    return HumanBrowser(
        port=cfg["port"], profile_dir=str(ROOT / cfg["profile"]),
        proxy_server=_proxy_for(cfg), launch_url="about:blank",
        auto_ensure=auto_ensure,
    )


def _read_auth_cookies(platform: str, launch: bool = False, cfg: Optional[dict] = None):
    """返回 (status, cookie_dict)。launch=False 时浏览器没开→UNKNOWN 不启动、不误判失效。"""
    if cfg is None:
        cfg, _error = _resolve_recovery_profile(platform)
    if not cfg:
        return UNKNOWN, {}
    if not launch:
        if cfg.get("cdp_url"):
            from .human_browser import is_cdp_url_open
            if not is_cdp_url_open(cfg["cdp_url"]):
                return UNKNOWN, {}
        else:
            from .human_browser import is_cdp_open
            if not is_cdp_open(port=cfg["port"]):
                return UNKNOWN, {}
    hb = _connect_hb(cfg, auto_ensure=launch)
    try:
        hb.connect()
        # context 级读 cookie，无需新开标签（不打扰用户正在用的窗口）
        jars = hb._context.cookies(cfg["login_url"])
        ck = {c.get("name"): (c.get("value") or "")[:8] for c in jars}
        have = [k for k in cfg["auth_cookies"] if k in ck and ck[k]]
        if have:
            return AUTH_VALID, ck
        # 浏览器开着但缺关键登录cookie → 失效
        return EXPIRED, ck
    except Exception:
        return UNKNOWN, {}
    finally:
        try:
            hb.close()
        except Exception:
            pass


def health_check(platform: str) -> dict:
    """主动健康检查（不改动风险状态）：AUTH_VALID / EXPIRED / UNKNOWN。"""
    cfg, error = _resolve_recovery_profile(platform)
    if not cfg:
        if platform not in RECOVERY_PROFILES:
            return {"success": False, "status": UNKNOWN, "error": "非真人浏览器平台，无需登录态检查"}
        return {"success": False, "platform": platform, "status": UNKNOWN, "error": error}
    if platform not in RECOVERY_PROFILES:
        return {"success": False, "status": UNKNOWN, "error": "非真人浏览器平台，无需登录态检查"}
    status, ck = _read_auth_cookies(platform, launch=False, cfg=cfg)
    return {"success": True, "platform": platform, "status": status,
            "status_cn": STATE_CN.get(status, status), "cookie_keys": sorted(ck.keys())}


def _set(platform, **kw):
    with _lock:
        s = _sessions.setdefault(platform, {"platform": platform})
        s.update(kw)
        s["updated_at"] = time.time()
        return dict(s)


def _get(platform) -> Optional[dict]:
    with _lock:
        s = _sessions.get(platform)
        return dict(s) if s else None


def _capture(page, platform: str, cfg: dict):
    """优先裁剪二维码元素，失败退化为整页截图。返回 (qr_path_or_empty, full_path)。"""
    full = _full_shot(platform)
    qr = _qr_shot(platform)
    try:
        page.screenshot(path=str(full), full_page=False)
    except Exception:
        pass
    qr_ok = False
    for sel in cfg.get("qr_selectors", []):
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                box = loc.bounding_box()
                if box and box["width"] >= 60 and box["height"] >= 60:
                    loc.screenshot(path=str(qr))
                    qr_ok = True
                    break
        except Exception:
            continue
    if not qr_ok and qr.exists():
        try:
            qr.unlink()
        except Exception:
            pass
    return (str(qr) if qr_ok else ""), str(full)


def _open_and_watch(platform: str, kind: str):
    cfg, _ = _resolve_recovery_profile(platform)
    if not cfg:
        _set(platform, state=AUTH_FAILED,
             message="当前获准身份或浏览器端点不可用，恢复已拒绝")
        return
    _set(platform, state=REQUIRED, kind=kind, account=cfg["display"],
         steps={"open": True, "scan": False, "done": False})
    hb = _connect_hb(cfg)
    page = None
    try:
        hb.connect()
        page = hb.new_page()
        # 登录页移交用户：移出自动关闭清单，hb.close() 只断连接、保留标签供扫码
        if page in hb._owned_pages:
            hb._owned_pages.remove(page)
        page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)
        hb.pause(1.6, 2.6)
        qr_path, full = _capture(page, platform, cfg)
        # 整页登录截图一定可展示；qr=True 表示额外裁出了二维码
        _set(platform, state=QR_DISPLAYED if Path(full).exists() else QR_FAILED,
             qr=bool(qr_path), shot_at=time.time(),
             steps={"open": True, "scan": False, "done": False})
        # 打开即检测：持久Profile若本就登录（cookie仍有效），直接恢复，不傻等扫码
        try:
            jars = page.context.cookies(cfg["login_url"])
            have = [c for c in jars if c.get("name") in cfg["auth_cookies"] and c.get("value")]
            if have:
                risk_controller.mark_recovered(platform)
                _set(platform, state=AUTH_VALID, recovered_at=time.time(),
                     message="检测到采集浏览器仍处于登录态，直接恢复，无需扫码",
                     steps={"open": True, "scan": True, "done": True})
                _resume_pending(platform)
                return
        except Exception:
            pass
        # 保留登录标签：只断开自动化连接，不关页面
    except Exception as e:
        browser_hint = "获准浏览器端点" if cfg.get("cdp_url") else f"{cfg['port']}浏览器"
        _set(platform, state=QR_FAILED,
             message=f"打开登录页失败：{e}（请检查{browser_hint}后重试）")
    finally:
        try:
            hb.close()
        except Exception:
            pass

    last_fp = {}
    deadline = time.time() + WATCH_TIMEOUT
    while time.time() < deadline:
        time.sleep(WATCH_INTERVAL)
        cur = _get(platform)
        if cur and cur.get("cancel"):
            _set(platform, state=AUTH_FAILED, message="已取消")
            return
        # 二维码过期自动刷新
        cur = _get(platform)
        if cur and cur.get("shot_at") and time.time() - cur["shot_at"] > QR_REFRESH \
                and cur.get("state") in (WAITING_SCAN, QR_DISPLAYED, QR_EXPIRED):
            _refresh_shot(platform, cfg)

        cfg, _ = _resolve_recovery_profile(platform)
        if not cfg:
            _set(platform, state=AUTH_FAILED,
                 message="当前获准身份或浏览器端点不可用，恢复已停止")
            return
        status, ck = _read_auth_cookies(platform, launch=False, cfg=cfg)
        fp = {k: ck.get(k) for k in cfg["auth_cookies"]}
        present = [k for k in cfg["auth_cookies"] if fp.get(k)]
        if status == AUTH_VALID and present:
            # 先出现部分会话变化 → SCANNED；齐全 → CONFIRMING → 复检 → RECOVERED
            if len(present) < len(cfg["auth_cookies"]):
                _set(platform, state=SCANNED, steps={"open": True, "scan": True, "done": False})
                continue
            _set(platform, state=CONFIRMING, steps={"open": True, "scan": True, "done": False})
            time.sleep(2)
            status2, _ = _read_auth_cookies(platform, launch=False)
            if status2 == AUTH_VALID:
                risk_controller.mark_recovered(platform)
                _set(platform, state=HEALTH_CHECK, steps={"open": True, "scan": True, "done": True})
                time.sleep(1)
                _set(platform, state=AUTH_VALID, recovered_at=time.time(),
                      message="登录态已恢复，自动解除暂停并续采",
                      steps={"open": True, "scan": True, "done": True})
                _resume_pending(platform)
                return
        elif present and not last_fp:
            _set(platform, state=SCANNED)
        else:
            if cur and cur.get("state") not in (SCANNED, CONFIRMING):
                _set(platform, state=WAITING_SCAN)
        last_fp = fp
    _set(platform, state=AUTH_FAILED, message="等待超时，可重新打开登录页")


def _refresh_shot(platform: str, cfg: dict):
    """二维码过期：重连当前登录标签重新截图。"""
    cfg, _ = _resolve_recovery_profile(platform)
    if not cfg:
        _set(platform, state=AUTH_FAILED,
             message="当前获准身份或浏览器端点不可用，恢复已停止")
        return
    _set(platform, state=QR_EXPIRED)
    hb = _connect_hb(cfg)
    try:
        hb.connect()
        pages = hb._context.pages if hb._context else []
        host = cfg["login_url"].split("/")[2]
        page = None
        for pg in pages:
            try:
                if host in (pg.url or ""):
                    page = pg
                    break
            except Exception:
                continue
        if page is None:
            page = hb.new_page()
            if page in hb._owned_pages:
                hb._owned_pages.remove(page)  # 同样移交保留
            page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)
            hb.pause(1.0, 1.8)
        qr_path, _ = _capture(page, platform, cfg)
        _set(platform, state=QR_DISPLAYED, qr=bool(qr_path), shot_at=time.time())
    except Exception:
        _set(platform, state=QR_FAILED)
    finally:
        try:
            hb.close()
        except Exception:
            pass


def _bridge_to_recovery_center(platform: str, source_state: str, detail: str, kind: str) -> None:
    """Phase4: 桥接 v4 内存态恢复会话 -> auth_recovery_center（DB表 auth_recovery_tasks）。
    前端全局 Modal 轮询 /api/auth-recovery/summary 读的是 center，不桥接则弹窗永远拿不到任务。
    最小增量：detect_and_create_task 幂等（同 platform+issue_type 已有 pending 则复用）。
    任何异常吞掉并 log，绝不阻塞 v4 主恢复链路。
    """
    try:
        from auth_recovery_center import AuthIssueType, recovery_center
        _disp = RECOVERY_PROFILES.get(platform, {}).get("display", platform)
        state_upper = (source_state or "").upper()
        if state_upper in ("AUTH_REQUIRED", "AUTH_FAILED", "SESSION_EXPIRED"):
            issue_type = AuthIssueType.COOKIE_EXPIRED.value
            title = _disp + "登录失效 - 需要扫码恢复"
        elif state_upper in ("CAPTCHA", "NEED_VERIFY"):
            issue_type = AuthIssueType.CAPTCHA.value
            title = _disp + "人机验证 - 需要人工通过"
        elif state_upper == "BLOCKED":
            issue_type = AuthIssueType.IP_RISK.value
            title = _disp + "IP风控熔断 - 冷却中"
        else:
            issue_type = AuthIssueType.SESSION_INVALID.value
            title = _disp + "采集认证异常 - 需要恢复"
        desc = detail or ("采集链路检测到 " + (source_state or "认证异常") + ", kind=" + kind + ", 请在系统内完成验证后恢复。")
        recovery_url = ""
        cfg = RECOVERY_PROFILES.get(platform, {})
        if cfg.get("login_url"):
            recovery_url = cfg["login_url"]
        recovery_center.detect_and_create_task(
            platform=platform, issue_type=issue_type, title=title,
            description=desc, recovery_url=recovery_url,
        )
    except Exception as _bridge_err:
        print("[AuthRecovery][Bridge] 桥接 auth_recovery_center 失败(不阻塞主链路):", _bridge_err)

def request_recovery(platform: str, source_state: str = "", detail: str = "") -> dict:
    """发起恢复（幂等）。BLOCKED 类不开浏览器、不伪装成扫码可解。"""
    cfg, config_error = _resolve_recovery_profile(platform)
    if not cfg:
        return {"success": False, "error": config_error}
    kind = classify_kind(platform, source_state, detail)
    existing = _get(platform)
    if existing and existing.get("state") in (REQUIRED, QR_DISPLAYED, WAITING_SCAN, SCANNED, CONFIRMING):
        _bridge_to_recovery_center(platform, source_state, detail, kind)
        return {"success": True, "session": existing, "reuse": True, "kind": kind}

    base = {"platform": platform, "display": cfg["display"], "kind": kind,
            "account": cfg["display"], "remote_hint": cfg.get("remote_hint", ""),
            "state": REQUIRED, "qr": False, "message": "", "started_at": time.time(),
            "cancel": False, "steps": {"open": False, "scan": False, "done": False}}
    with _lock:
        _sessions[platform] = dict(base)

    _bridge_to_recovery_center(platform, source_state, detail, kind)

    if kind == KIND_BLOCKED:
        # C类：只冷却，不开登录页、不轮询
        risk = {x["platform"]: x for x in risk_controller.snapshot()}.get(platform, {})
        _set(platform, state=PLATFORM_BLOCKED,
             cooldown_remain=risk.get("cooldown_remain", 0),
             message="IP/平台风控熔断中，扫码无法解决，系统已自动降频冷却，请勿硬刚")
        return {"success": True, "session": _get(platform), "reuse": False, "kind": kind}

    th = threading.Thread(target=_open_and_watch, args=(platform, kind), daemon=True,
                          name=f"auth-recovery-{platform}")
    th.start()
    return {"success": True, "session": _get(platform), "reuse": False, "kind": kind}


def check_recovery(platform: str) -> dict:
    """手动立即探测一次。"""
    cfg, config_error = _resolve_recovery_profile(platform)
    if not cfg:
        return {"success": False, "recovered": False, "status": UNKNOWN,
                "error": config_error}
    status, ck = _read_auth_cookies(platform, launch=True, cfg=cfg)
    recovered = status == AUTH_VALID
    if recovered:
        risk_controller.mark_recovered(platform)
        _set(platform, state=AUTH_VALID, recovered_at=time.time(),
             message="检测到登录态已恢复", steps={"open": True, "scan": True, "done": True})
        _resume_pending(platform)
    return {"success": True, "recovered": recovered, "status": status,
            "status_cn": STATE_CN.get(status, status)}


def cancel_recovery(platform: str):
    s = _get(platform)
    if s:
        _set(platform, cancel=True, state=AUTH_FAILED, message="用户取消")


def recovery_status() -> list:
    with _lock:
        out = [dict(s) for s in _sessions.values()]
    # 附带实时冷却秒数
    rmap = {x["platform"]: x for x in risk_controller.snapshot()}
    for s in out:
        r = rmap.get(s["platform"])
        s["risk"] = r
        if r:
            s["cooldown_remain"] = r.get("cooldown_remain", 0)
        s["state_cn"] = STATE_CN.get(s.get("state", ""), s.get("state", ""))
    return out


def recovery_platforms() -> list:
    """可恢复平台清单（前端据此知道哪些是真人平台及其账号/端口）。"""
    return [{"platform": k, "display": v["display"], "port": v.get("port"),
             "profile": v.get("profile"), "remote_hint": v.get("remote_hint", "")}
            for k, v in RECOVERY_PROFILES.items()]


def shot_paths(platform: str):
    """返回 (二维码路径或空, 整页路径或空)。"""
    qr, full = _qr_shot(platform), _full_shot(platform)
    return (str(qr) if qr.exists() else "", str(full) if full.exists() else "")
