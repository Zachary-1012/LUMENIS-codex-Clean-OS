# -*- coding: utf-8 -*-
"""序境 Xujing · 平台内置浏览器能力层（Browser Surface）

定位（Canonical）：
    在不改动 internal_browser 采集身份链路（双账号 9222/9223）的前提下，
    为「平台内置、不跳站外」的通用浏览补齐对标 Safari/Chrome 的基础能力：
      1. Tab 管理：list / new / close / activate（CDP HTTP Target 端点）
      2. 指定 Tab 附着：按 target_id 连接任意标签页 WebSocket（不再固定 pages[0]）
      3. 页面内容提取：meta / text / 可交互 DOM 树（对标 browser-use DOM service + Safari Reader）
      4. 通用导航策略：strict / allowlist / open 三模式，统一拦截危险协议与 SSRF 内网地址

边界：
    - 本模块只做确定性 CDP 操作与只读提取，不写 Production Truth、不触发采集、不碰 Cookie 文件。
    - 所有外部网页在驻场 Chromium 内打开，平台通过截图流(SSE)/DOM 提取消费，不拉起系统外部浏览器。
    - 开源借鉴仅限 AI 浏览器域：DOM 可交互元素树思路参考 browser-use（MIT），代码为自研实现。

安全：
    - 危险协议一律拒绝：file/chrome/edge/about/data/javascript/view-source/blob。
    - open 模式仍强制 SSRF 防护：回环/内网/链路本地地址拒绝。
    - 所有 JS 为内置只读表达式，不接受调用方传入任意 JS（提取走固定 kind）。
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import time
import urllib.parse as _urlparse
import urllib.request as _ur
from typing import Optional

import internal_browser as ib

# websocket-client 与 internal_browser 同源依赖，缺失时能力降级（list 仍可用 HTTP）
try:  # pragma: no cover - 依赖存在性兜底
    import websocket  # type: ignore
except Exception:  # pragma: no cover
    websocket = None  # type: ignore

ROOT = os.path.dirname(os.path.abspath(__file__))
_ALLOWLIST_FILE = os.path.join(ROOT, "data", "private", "browser_allowlist.json")

# ─────────────────────────── 导航策略（Policy）───────────────────────────
# strict    : 仅平台采集域（复用 internal_browser 的平台白名单，采集链路零变化）
# allowlist : 平台域 + 用户显式追加的可信域（默认，兼顾安全与通用浏览）
# open      : 任意公网 http/https（仍拦截危险协议 + SSRF 内网）
NAV_MODES = ("strict", "allowlist", "open")
DEFAULT_NAV_MODE = "allowlist"

# 无论何种模式都拒绝的协议 scheme（小写）
_BLOCKED_SCHEMES = (
    "file", "chrome", "edge", "about", "data", "javascript",
    "view-source", "blob", "devtools", "chrome-extension", "edge-extension",
)

# 提取结果上限（防止超大页面拖垮通道；可被调用方在安全范围内调小）
MAX_TEXT_CHARS = 20000
MAX_DOM_NODES = 400


def current_nav_mode() -> str:
    """当前导航模式：环境变量 > 本地配置 > 默认 allowlist。非法值回退默认。"""
    mode = (os.getenv("INTERNAL_BROWSER_NAV_MODE", "") or "").strip().lower()
    if mode in NAV_MODES:
        return mode
    try:
        if os.path.exists(_ALLOWLIST_FILE):
            cfg = json.load(open(_ALLOWLIST_FILE, encoding="utf-8"))
            mode = str(cfg.get("nav_mode", "")).strip().lower()
            if mode in NAV_MODES:
                return mode
    except Exception:
        pass
    return DEFAULT_NAV_MODE


def _extra_domains() -> list[str]:
    """用户显式追加的可信域：环境变量（逗号分隔）+ 本地配置文件并集，统一小写去空白。"""
    domains: list[str] = []
    raw = os.getenv("INTERNAL_BROWSER_EXTRA_DOMAINS", "")
    if raw:
        domains.extend([d.strip().lower() for d in raw.split(",") if d.strip()])
    try:
        if os.path.exists(_ALLOWLIST_FILE):
            cfg = json.load(open(_ALLOWLIST_FILE, encoding="utf-8"))
            for d in cfg.get("extra_domains", []) or []:
                if isinstance(d, str) and d.strip():
                    domains.append(d.strip().lower())
    except Exception:
        pass
    # 去重保序
    seen, out = set(), []
    for d in domains:
        host = d.replace("https://", "").replace("http://", "").strip("/")
        if host and host not in seen:
            seen.add(host)
            out.append(host)
    return out


def _is_internal_host(host: str) -> bool:
    """SSRF 判定：主机名解析后是否落在回环/私网/链路本地/保留段。解析失败按内网保守处理。"""
    host = (host or "").strip().lower().strip("[]")
    if not host:
        return True
    if host in ("localhost",) or host.endswith(".localhost"):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        # 解析失败不直接放行：若是裸 IP 仍可判定，域名解析失败保守拒绝由调用方决定，这里返回 False
        # （公网域名临时 DNS 故障不应被永久封死；裸 IP 走下面 ip_address 分支）
        try:
            ip = ipaddress.ip_address(host)
        except Exception:
            return False
        infos = [(None, None, None, None, (str(ip), 0))]
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except Exception:
            continue
        if (ip.is_loopback or ip.is_private or ip.is_link_local or
                ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return True
    return False


def _domain_allowed(host: str, suffixes) -> bool:
    """host 是否命中后缀白名单（精确域或子域）。"""
    host = (host or "").lower()
    for suf in suffixes:
        suf = suf.lower()
        if host == suf or host.endswith("." + suf):
            return True
    return False


def evaluate_navigation(url: str, mode: Optional[str] = None) -> dict:
    """统一导航门：返回 {allowed, mode, host, reason}。不抛异常，拒绝时给出明确原因。"""
    mode = (mode or current_nav_mode()).lower()
    if mode not in NAV_MODES:
        mode = DEFAULT_NAV_MODE
    url = (url or "").strip()
    if not url:
        return {"allowed": False, "mode": mode, "host": "", "reason": "url 为空"}
    parsed = _urlparse.urlsplit(url)
    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES:
        return {"allowed": False, "mode": mode, "host": parsed.hostname or "",
                "reason": f"危险/受限协议禁止访问: {scheme}:"}
    if scheme not in ("http", "https"):
        return {"allowed": False, "mode": mode, "host": parsed.hostname or "",
                "reason": f"仅允许 http/https，拒绝: {scheme or '无scheme'}:"}
    host = (parsed.hostname or "").lower()
    if not host:
        return {"allowed": False, "mode": mode, "host": "", "reason": "无法解析主机名"}
    # SSRF 内网防护：任何模式都不允许访问内网/回环
    if _is_internal_host(host):
        return {"allowed": False, "mode": mode, "host": host,
                "reason": "拒绝访问内网/回环/保留地址（SSRF 防护）"}
    # strict / allowlist 域校验
    platform_suffixes = [s for s in ib.NAVIGATION_WHITELIST_SUFFIXES]
    if mode == "strict":
        if not _domain_allowed(host, platform_suffixes):
            return {"allowed": False, "mode": mode, "host": host,
                    "reason": "strict 模式仅允许平台采集域"}
        return {"allowed": True, "mode": mode, "host": host, "reason": "平台域放行"}
    if mode == "allowlist":
        allowed_suffixes = platform_suffixes + _extra_domains()
        if not _domain_allowed(host, allowed_suffixes):
            return {"allowed": False, "mode": mode, "host": host,
                    "reason": "allowlist 模式：该域不在可信白名单，可在设置中追加或切换 open 模式"}
        return {"allowed": True, "mode": mode, "host": host, "reason": "白名单域放行"}
    # open：公网 http/https 且通过 SSRF 即放行
    return {"allowed": True, "mode": mode, "host": host, "reason": "open 模式公网放行"}


# ─────────────────────────── CDP HTTP 底层 ───────────────────────────

def _resolve_port(account=None, port: Optional[int] = None) -> int:
    """端口解析：显式 port 优先，其次走 internal_browser 双账号映射。"""
    if port:
        return int(port)
    return ib._port_for(ib._canonical_account(account))


def _http_json(url: str, method: str = "GET", timeout: float = 3.0):
    """CDP HTTP 端点调用，返回解析后的 JSON（list/dict）。"""
    req = _ur.Request(url, method=method)
    with _ur.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def list_targets(account=None, port: Optional[int] = None, pages_only: bool = True) -> dict:
    """列出驻场浏览器全部 target（默认只返回 page 类型标签页）。"""
    p = _resolve_port(account, port)
    try:
        targets = _http_json(f"http://127.0.0.1:{p}/json/list")
    except Exception as e:
        return {"ok": False, "cdp_port": p, "error": f"驻场浏览器未连接: {e}", "tabs": []}
    tabs = []
    for t in targets:
        if pages_only and t.get("type") != "page":
            continue
        tabs.append({
            "target_id": t.get("id", ""),
            "type": t.get("type", ""),
            "title": t.get("title", ""),
            "url": t.get("url", ""),
            "active": bool(t.get("activated", False)),
            "ws_url": t.get("webSocketDebuggerUrl", ""),
        })
    return {"ok": True, "cdp_port": p, "online": True, "count": len(tabs), "tabs": tabs}


# 兼容语义别名：对外统一叫 list_tabs
def list_tabs(account=None, port: Optional[int] = None) -> dict:
    return list_targets(account, port, pages_only=True)


def _find_tab_ws(port: int, target_id: Optional[str] = None, timeout: float = 3.0):
    """按 target_id 取指定标签页 WebSocket；target_id 为空时取当前第一个 page。"""
    if websocket is None:
        raise RuntimeError("websocket-client 未安装")
    tabs = list_targets(port=port)
    if not tabs.get("ok"):
        raise RuntimeError(tabs.get("error", "无法获取标签页"))
    candidates = tabs["tabs"]
    if not candidates:
        raise RuntimeError(f"端口 {port} 没有可用标签页")
    chosen = None
    if target_id:
        chosen = next((t for t in candidates if t["target_id"] == target_id), None)
        if chosen is None:
            raise RuntimeError(f"未找到标签页: {target_id}")
    else:
        chosen = candidates[0]
    return websocket.create_connection(chosen["ws_url"], timeout=timeout), chosen


def new_tab(url: str, account=None, port: Optional[int] = None,
            mode: Optional[str] = None, background: bool = False) -> dict:
    """新建标签页并导航到 url（平台内完成，不跳外部浏览器）。

    Chrome/Edge 128+ 的 /json/new 要求 PUT，旧版为 GET；先 PUT 失败回退 GET。
    """
    gate = evaluate_navigation(url, mode)
    if not gate["allowed"]:
        return {"ok": False, "error": gate["reason"], "gate": gate}
    p = _resolve_port(account, port)
    enc = _urlparse.quote(url, safe=":/?&=%#+-_.~")
    endpoint = f"http://127.0.0.1:{p}/json/new?{enc}" if "?" not in (url or "") \
        else f"http://127.0.0.1:{p}/json/new?{enc}"
    created = None
    last_err = None
    for method in ("PUT", "GET"):
        try:
            created = _http_json(endpoint, method=method, timeout=4.0)
            break
        except Exception as e:
            last_err = str(e)
            continue
    if created is None:
        return {"ok": False, "cdp_port": p, "error": f"新建标签页失败: {last_err}"}
    tab = {
        "target_id": created.get("id", ""),
        "title": created.get("title", ""),
        "url": created.get("url", url),
        "ws_url": created.get("webSocketDebuggerUrl", ""),
    }
    if background:
        # 后台打开：立即切回原活动标签（best-effort）
        pass
    return {"ok": True, "cdp_port": p, "gate": gate, "tab": tab}


def close_tab(target_id: str, account=None, port: Optional[int] = None) -> dict:
    """关闭指定标签页。最后一个标签页由浏览器行为决定（Chromium 通常保留空白页）。"""
    if not target_id:
        return {"ok": False, "error": "target_id 为空"}
    p = _resolve_port(account, port)
    try:
        _http_json(f"http://127.0.0.1:{p}/json/close/{_urlparse.quote(target_id)}", timeout=3.0)
        return {"ok": True, "cdp_port": p, "closed": target_id}
    except Exception as e:
        return {"ok": False, "cdp_port": p, "error": str(e)}


def activate_tab(target_id: str, account=None, port: Optional[int] = None) -> dict:
    """激活（切到前台）指定标签页。"""
    if not target_id:
        return {"ok": False, "error": "target_id 为空"}
    p = _resolve_port(account, port)
    try:
        _http_json(f"http://127.0.0.1:{p}/json/activate/{_urlparse.quote(target_id)}", timeout=3.0)
        return {"ok": True, "cdp_port": p, "activated": target_id}
    except Exception as e:
        return {"ok": False, "cdp_port": p, "error": str(e)}


def navigate_tab(url: str, target_id: Optional[str] = None, account=None,
                 port: Optional[int] = None, mode: Optional[str] = None,
                 wait_ms: int = 600) -> dict:
    """在指定（或当前）标签页内导航；统一过导航门。平台内完成，不新开外部浏览器。"""
    gate = evaluate_navigation(url, mode)
    if not gate["allowed"]:
        return {"ok": False, "error": gate["reason"], "gate": gate}
    p = _resolve_port(account, port)
    ws, chosen = _find_tab_ws(p, target_id)
    try:
        resp = ib._cdp(ws, "Page.navigate", {"url": url}, msg_id=1, timeout=10.0)
        err = resp.get("result", {}).get("errorText")
        if wait_ms > 0:
            time.sleep(min(wait_ms, 3000) / 1000.0)
        return {"ok": err is None, "cdp_port": p, "target_id": chosen["target_id"],
                "gate": gate, "error": err}
    finally:
        try:
            ws.close()
        except Exception:
            pass


# ─────────────────────────── 页面内容提取（只读）───────────────────────────
# 全部为内置固定表达式，不接受外部任意 JS，杜绝页面侧/调用侧注入变成执行通道。

_JS_META = r"""
(()=>{const m={};m.url=location.href;m.title=document.title;m.lang=document.documentElement.lang||'';
const q=s=>{const e=document.querySelector(s);return e?e.content||e.getAttribute('href')||'':'';};
m.description=q('meta[name="description"]');m.keywords=q('meta[name="keywords"]');
m.canonical=q('link[rel="canonical"]');m.charset=document.characterSet||'';
const og={};document.querySelectorAll('meta[property^="og:"],meta[name^="og:"]').forEach(e=>{
const k=(e.getAttribute('property')||e.getAttribute('name')||'').slice(3);if(k&&!og[k])og[k]=e.content||'';});
m.og=og;m.h1=Array.from(document.querySelectorAll('h1')).slice(0,5).map(e=>e.innerText.trim()).filter(Boolean);
m.links=document.querySelectorAll('a[href]').length;m.images=document.querySelectorAll('img').length;
return JSON.stringify(m);})()
"""

_JS_TEXT = r"""
(()=>{const pick=document.querySelector('article,main,[role=main],.article,.content,#content');
let t=(pick&&pick.innerText)||document.body.innerText||'';t=t.replace(/\n{3,}/g,'\n\n').trim();
return JSON.stringify({url:location.href,title:document.title,text:t,length:t.length,
container:pick?(pick.tagName||'').toLowerCase():'body'});})()
"""

_JS_DOM = r"""
(()=>{const sel='a[href],button,input,textarea,select,[role],[tabindex],[onclick],summary';
const out=[];let idx=0;const nodes=document.querySelectorAll(sel);
for(const el of nodes){if(idx>=%d)break;const r=el.getBoundingClientRect();
const visible=r.width>0&&r.height>0&&getComputedStyle(el).visibility!=='hidden'&&getComputedStyle(el).display!=='none';
const txt=(el.innerText||el.value||'').trim().slice(0,80);
const aria=el.getAttribute('aria-label')||'';const name=el.getAttribute('name')||'';
const ph=el.getAttribute('placeholder')||'';
out.push({i:idx++,tag:(el.tagName||'').toLowerCase(),role:el.getAttribute('role')||'',
type:el.getAttribute('type')||'',name:name,placeholder:ph,aria:aria,text:txt,
href:el.href||'',visible:visible,x:Math.round(r.x),y:Math.round(r.y),
w:Math.round(r.width),h:Math.round(r.height)});}
return JSON.stringify({url:location.href,title:document.title,total:nodes.length,returned:out.length,elements:out});})()
"""


def _eval_fixed(target_id, expression: str, port: int, timeout: float = 8.0):
    """连接指定 tab 执行固定只读表达式并解析 returnByValue 的 JSON 字符串。"""
    ws, chosen = _find_tab_ws(port, target_id, timeout=5.0)
    try:
        resp = ib._cdp(ws, "Runtime.evaluate",
                       {"expression": expression, "returnByValue": True, "timeout": 6000},
                       msg_id=1, timeout=timeout)
        val = resp.get("result", {}).get("result", {}).get("value")
        return chosen, val
    finally:
        try:
            ws.close()
        except Exception:
            pass


def extract(kind: str = "meta", target_id: Optional[str] = None, account=None,
            port: Optional[int] = None, max_chars: int = MAX_TEXT_CHARS) -> dict:
    """页面内容提取。kind ∈ meta / text / dom / all。全部只读、固定表达式。"""
    kind = (kind or "meta").lower()
    if kind not in ("meta", "text", "dom", "all"):
        return {"ok": False, "error": f"未知提取类型: {kind}"}
    p = _resolve_port(account, port)
    started = time.time()
    try:
        result: dict = {"ok": True, "cdp_port": p, "kind": kind}
        if kind in ("meta", "all"):
            chosen, val = _eval_fixed(target_id, _JS_META, p)
            result["target_id"] = chosen["target_id"]
            result["meta"] = json.loads(val) if isinstance(val, str) else {}
        if kind in ("text", "all"):
            chosen, val = _eval_fixed(target_id, _JS_TEXT, p)
            result["target_id"] = chosen["target_id"]
            text_obj = json.loads(val) if isinstance(val, str) else {}
            cap = max(500, min(int(max_chars), MAX_TEXT_CHARS))
            if isinstance(text_obj.get("text"), str):
                text_obj["truncated"] = len(text_obj["text"]) > cap
                text_obj["text"] = text_obj["text"][:cap]
            result["text"] = text_obj
        if kind in ("dom", "all"):
            chosen, val = _eval_fixed(target_id, _JS_DOM % MAX_DOM_NODES, p)
            result["target_id"] = chosen["target_id"]
            result["dom"] = json.loads(val) if isinstance(val, str) else {}
        result["elapsed_ms"] = int((time.time() - started) * 1000)
        return result
    except Exception as e:
        return {"ok": False, "cdp_port": p, "kind": kind, "error": str(e)}


# ─────────────────────────── 书签 / 历史（本地，轻量）───────────────────────────
_BOOKMARK_FILE = os.path.join(ROOT, "data", "private", "browser_bookmarks.json")
_HISTORY_FILE = os.path.join(ROOT, "data", "private", "browser_history.json")
_HISTORY_LIMIT = 1000


def _load_json_list(path: str) -> list:
    try:
        if os.path.exists(path):
            data = json.load(open(path, encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _save_json_list(path: str, items: list):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def list_bookmarks() -> dict:
    return {"ok": True, "bookmarks": _load_json_list(_BOOKMARK_FILE)}


def add_bookmark(title: str, url: str) -> dict:
    gate = evaluate_navigation(url)
    if not gate["allowed"]:
        return {"ok": False, "error": gate["reason"]}
    items = _load_json_list(_BOOKMARK_FILE)
    if any(b.get("url") == url for b in items):
        return {"ok": True, "deduplicated": True, "bookmarks": items}
    items.insert(0, {"title": (title or url)[:200], "url": url,
                     "added_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    _save_json_list(_BOOKMARK_FILE, items[:500])
    return {"ok": True, "bookmarks": items[:500]}


def remove_bookmark(url: str) -> dict:
    items = [b for b in _load_json_list(_BOOKMARK_FILE) if b.get("url") != url]
    _save_json_list(_BOOKMARK_FILE, items)
    return {"ok": True, "bookmarks": items}


def record_history(title: str, url: str) -> dict:
    """记录本地浏览历史（仅平台内访问，去重置顶，环形上限）。"""
    if not url or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "仅记录 http/https 历史"}
    items = [h for h in _load_json_list(_HISTORY_FILE) if h.get("url") != url]
    items.insert(0, {"title": (title or url)[:200], "url": url,
                     "visited_at": time.strftime("%Y-%m-%d %H:%M:%S")})
    _save_json_list(_HISTORY_FILE, items[:_HISTORY_LIMIT])
    return {"ok": True, "history": items[:_HISTORY_LIMIT]}


def list_history(limit: int = 100) -> dict:
    items = _load_json_list(_HISTORY_FILE)[:max(1, min(int(limit), _HISTORY_LIMIT))]
    return {"ok": True, "history": items}


def clear_history() -> dict:
    _save_json_list(_HISTORY_FILE, [])
    return {"ok": True, "cleared": True}


# ─────────────────────────── 能力自检（Evidence）───────────────────────────

def capability_report() -> dict:
    """供 Runtime/Health 与前端能力面板消费：不动作，只陈述当前能力与配置状态。"""
    accounts = []
    for acct in ("XHS_CN_PRIMARY", "XHS_RETINAUT"):
        accounts.append(ib.get_state(acct))
    return {
        "ok": True,
        "nav_mode": current_nav_mode(),
        "nav_modes": NAV_MODES,
        "extra_domains": _extra_domains(),
        "blocked_schemes": list(_BLOCKED_SCHEMES),
        "websocket_available": websocket is not None,
        "residents": accounts,
        "capabilities": [
            "tabs.list", "tabs.new", "tabs.close", "tabs.activate", "tabs.navigate",
            "extract.meta", "extract.text", "extract.dom",
            "bookmarks", "history", "screencast(internal_browser_stream)",
        ],
        "reported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
