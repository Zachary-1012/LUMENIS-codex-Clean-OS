# -*- coding: utf-8 -*-
"""Zachary OS AI · Internal Browser（系统内置浏览器）

Contract：OSAI 研究侧 → ZBC 生产侧。
目标：小红书/rednote 操作不跳转外部浏览器，全部在系统内部完成。

架构：
  前端视图（截图流 + 控制层）
    ↓ HTTP API（本模块 Blueprint）
  CDP 命令层（Page.captureScreenshot / Page.navigate / Input.* / Runtime.evaluate）
    ↓ WebSocket
  驻场浏览器实例（9223 香港生产采集；9222 仅保留诊断兼容）

安全：
  - 导航域名白名单（xiaohongshu.com / rednote.com），防 SSRF
  - 只读 cookie 数量，不回传 cookie 值
  - 生产默认身份为 XHS_RETINAUT；XHS_CN_PRIMARY 仅允许显式诊断调用
"""
from __future__ import annotations
import base64
import json
import time
import urllib.request as ur
from typing import Any, Optional

try:
    import websocket  # .venv 环境提供（websocket-client）
except Exception:  # pragma: no cover
    websocket = None

# 复用双身份端口/首页映射
try:
    import xhs_cookie_bridge as bridge
except Exception:  # pragma: no cover
    bridge = None

# 导航域名白名单（防 SSRF：内置浏览器只允许平台域）
NAVIGATION_WHITELIST_SUFFIXES = (
    "xiaohongshu.com", "www.xiaohongshu.com",
    "rednote.com", "www.rednote.com",
)

# 账号显示名
ACCOUNT_LABELS = {
    "XHS_CN_PRIMARY": "大陆主号",
    "XHS_RETINAUT": "香港 Retinaut",
}


# ─────────────────────────── CDP 底层 ───────────────────────────

def _canonical_account(account: Optional[str]) -> str:
    if bridge:
        return bridge._canonical_account_name(account)
    return account or "XHS_RETINAUT"


def _port_for(account: Optional[str]) -> int:
    if bridge:
        return bridge.cdp_port_for(account)
    return 9223


def _home_for(account: Optional[str]) -> str:
    if bridge:
        return bridge.home_url_for(account)
    return "https://www.rednote.com"


def _get_page_targets(port: int, timeout: float = 2.0) -> list[dict]:
    """通过 CDP HTTP /json/list 获取 page targets。"""
    with ur.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=timeout) as r:
        targets = json.loads(r.read().decode("utf-8", "replace"))
    return [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]


def _open_page_ws(port: int, timeout: float = 5.0):
    """打开第一个 page target 的 WebSocket。返回 ws 或 None。"""
    if websocket is None:
        raise RuntimeError("websocket-client 未安装，内置浏览器需要 .venv 环境")
    pages = _get_page_targets(port)
    if not pages:
        raise RuntimeError(f"端口 {port} 没有可用的页面 target（驻场浏览器可能未启动）")
    return websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=timeout)


def _cdp(ws, method: str, params: dict = None, msg_id: int = 1, timeout: float = 8.0) -> dict:
    """发送一条 CDP 命令并等待对应 id 的响应（跳过事件通知）。"""
    ws.settimeout(timeout)
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = ws.recv()
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            return msg
    raise TimeoutError(f"CDP 命令超时: {method}")


# ─────────────────────────── 浏览器操作 ───────────────────────────

def get_state(account: Optional[str] = None) -> dict:
    """获取账号对应驻场浏览器的页面状态（URL/title/端口/在线）。"""
    acct = _canonical_account(account)
    port = _port_for(acct)
    state = {
        "account": acct,
        "label": ACCOUNT_LABELS.get(acct, acct),
        "cdp_port": port,
        "home_url": _home_for(acct),
        "online": False,
        "url": "",
        "title": "",
        "page_count": 0,
    }
    try:
        pages = _get_page_targets(port)
        state["online"] = len(pages) > 0
        state["page_count"] = len(pages)
        if pages:
            state["url"] = pages[0].get("url", "")
            state["title"] = pages[0].get("title", "")
    except Exception as e:
        state["error"] = str(e)
    return state


def capture_screenshot(account: Optional[str] = None, quality: int = 70,
                       viewport_width: int = 0) -> dict:
    """截图，返回 base64 JPEG（前端用 data:image/jpeg;base64 显示）。"""
    acct = _canonical_account(account)
    port = _port_for(acct)
    ws = _open_page_ws(port)
    try:
        params = {"format": "jpeg", "quality": int(quality)}
        resp = _cdp(ws, "Page.captureScreenshot", params, msg_id=1)
        data = resp.get("result", {}).get("data", "")
        # 顺带取 URL/title
        state_resp = _cdp(ws, "Runtime.evaluate",
                          {"expression": "JSON.stringify({url:location.href,title:document.title})",
                           "returnByValue": True}, msg_id=2)
        meta = {}
        try:
            val = state_resp["result"]["result"].get("value", "{}")
            meta = json.loads(val)
        except Exception:
            pass
        return {
            "ok": bool(data),
            "account": acct,
            "image_base64": data,
            "url": meta.get("url", ""),
            "title": meta.get("title", ""),
            "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    finally:
        try:
            ws.close()
        except Exception:
            pass


def navigate(account: Optional[str], url: str) -> dict:
    """页面导航（域名白名单校验）。"""
    acct = _canonical_account(account)
    url = (url or "").strip()
    if not url:
        return {"ok": False, "error": "url 不能为空"}
    # 相对路径/搜索页允许；完整 URL 校验白名单
    if url.startswith("http://") or url.startswith("https://"):
        low = url.lower()
        if not any(suf in low for suf in NAVIGATION_WHITELIST_SUFFIXES):
            return {"ok": False, "error": f"内置浏览器只允许平台域名，拒绝导航: {url}"}
    port = _port_for(acct)
    ws = _open_page_ws(port)
    try:
        resp = _cdp(ws, "Page.navigate", {"url": url}, msg_id=1)
        err = resp.get("result", {}).get("errorText")
        return {"ok": err is None, "account": acct, "url": url, "error": err}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def evaluate(account: Optional[str], expression: str) -> dict:
    """执行只读 JS 表达式（returnByValue）。限制长度，防滥用。"""
    if not expression or len(expression) > 2000:
        return {"ok": False, "error": "expression 为空或超长(>2000)"}
    acct = _canonical_account(account)
    port = _port_for(acct)
    ws = _open_page_ws(port)
    try:
        resp = _cdp(ws, "Runtime.evaluate",
                    {"expression": expression, "returnByValue": True, "timeout": 5000}, msg_id=1)
        result = resp.get("result", {}).get("result", {})
        return {"ok": True, "account": acct, "value": result.get("value"),
                "type": result.get("type")}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def click_at(account: Optional[str], x: float, y: float, button: str = "left") -> dict:
    """坐标点击（鼠标按下+抬起）。"""
    acct = _canonical_account(account)
    port = _port_for(acct)
    ws = _open_page_ws(port)
    try:
        common = {"x": float(x), "y": float(y), "button": button, "clickCount": 1}
        _cdp(ws, "Input.dispatchMouseEvent", {**common, "type": "mousePressed"}, msg_id=1)
        _cdp(ws, "Input.dispatchMouseEvent", {**common, "type": "mouseReleased"}, msg_id=2)
        return {"ok": True, "account": acct, "x": x, "y": y}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def type_text(account: Optional[str], text: str) -> dict:
    """在当前聚焦元素输入文本（Input.insertText，不记录按键）。"""
    if not text or len(text) > 500:
        return {"ok": False, "error": "text 为空或超长(>500)"}
    acct = _canonical_account(account)
    port = _port_for(acct)
    ws = _open_page_ws(port)
    try:
        _cdp(ws, "Input.insertText", {"text": text}, msg_id=1)
        return {"ok": True, "account": acct, "length": len(text)}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def scroll_page(account: Optional[str], delta_y: float = 400) -> dict:
    """页面滚动（通过 JS window.scrollBy，兼容性最好）。"""
    acct = _canonical_account(account)
    port = _port_for(acct)
    ws = _open_page_ws(port)
    try:
        expr = f"window.scrollBy({{top:{int(delta_y)},behavior:'smooth'}}); window.scrollY"
        resp = _cdp(ws, "Runtime.evaluate",
                    {"expression": expr, "returnByValue": True}, msg_id=1)
        scroll_y = resp.get("result", {}).get("result", {}).get("value")
        return {"ok": True, "account": acct, "scroll_y": scroll_y}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def history_action(account: Optional[str], action: str = "reload") -> dict:
    """导航历史：back / forward / reload / home。"""
    acct = _canonical_account(account)
    port = _port_for(acct)
    ws = _open_page_ws(port)
    try:
        if action == "back":
            _cdp(ws, "Page.navigate", {"url": "javascript:history.back()"}, msg_id=1)
        elif action == "forward":
            _cdp(ws, "Page.navigate", {"url": "javascript:history.forward()"}, msg_id=1)
        elif action == "home":
            _cdp(ws, "Page.navigate", {"url": _home_for(acct)}, msg_id=1)
        else:  # reload
            _cdp(ws, "Page.reload", {"ignoreCache": False}, msg_id=1)
        return {"ok": True, "account": acct, "action": action}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def list_accounts() -> list[dict]:
    """列出双账号内置浏览器状态。"""
    accounts = ["XHS_CN_PRIMARY", "XHS_RETINAUT"]
    return [get_state(a) for a in accounts]


# ─────────────────────────── 执行恢复回路（Page Agent/browser-use 可借鉴点落地）───
# 对照：失败→重新定位→重试→降级；受采集安全 Gate（手动≤30min）约束；trace 供 Evidence 可追溯

def find_element(account, selector):
    """通过 JS 定位元素并返回可视坐标；找不到返回 {ok:False}。selector 限定简单 CSS（防注入）。"""
    import re as _re
    if not selector or len(selector) > 200:
        return {"ok": False, "error": "selector 为空或超长"}
    if not _re.fullmatch(r"[A-Za-z0-9_#.\[\]='\": -]+", selector):
        return {"ok": False, "error": "selector 含非法字符"}
    expr = ("(()=>{const el=document.querySelector(%r);if(!el)return JSON.stringify({found:false});"
            "const r=el.getBoundingClientRect();return JSON.stringify({found:true,x:r.x+r.width/2,"
            "y:r.y+r.height/2,visible:!!(r.width&&r.height)});})()" % selector)
    try:
        val = evaluate(account, expr).get("value")
        data = json.loads(val) if isinstance(val, str) else {}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if not data.get("found") or not data.get("visible"):
        return {"ok": False, "error": "元素未找到或不可见"}
    return {"ok": True, "x": float(data["x"]), "y": float(data["y"])}


def click_selector(account, selector, retry=2, retry_delay=1.0):
    """定位→点击，带失败重试（重新定位→重试→报告），对齐恢复回路。"""
    acct = _canonical_account(account)
    trace = []
    for attempt in range(retry + 1):
        t0 = time.time()
        loc = find_element(acct, selector)
        if loc.get("ok"):
            try:
                click_at(acct, loc["x"], loc["y"])
                trace.append({"action": "click_selector", "selector": selector, "ok": True,
                              "attempt": attempt + 1, "elapsed_ms": int((time.time() - t0) * 1000)})
                return {"ok": True, "account": acct, "trace": trace}
            except Exception as e:
                trace.append({"action": "click_selector", "selector": selector, "ok": False,
                              "attempt": attempt + 1, "error": str(e)})
        else:
            trace.append({"action": "click_selector", "selector": selector, "ok": False,
                          "attempt": attempt + 1, "error": loc.get("error", "定位失败")})
        if attempt < retry:
            time.sleep(retry_delay)
    return {"ok": False, "account": acct, "trace": trace, "error": trace[-1].get("error", "重试后仍失败")}


def type_into(account, selector, text, retry=2, retry_delay=1.0):
    """定位→聚焦→输入，带失败重试。"""
    acct = _canonical_account(account)
    trace = []
    for attempt in range(retry + 1):
        t0 = time.time()
        loc = find_element(acct, selector)
        if loc.get("ok"):
            try:
                click_at(acct, loc["x"], loc["y"])
                time.sleep(0.2)
                type_text(acct, text)
                trace.append({"action": "type_into", "selector": selector, "ok": True,
                              "attempt": attempt + 1, "elapsed_ms": int((time.time() - t0) * 1000)})
                return {"ok": True, "account": acct, "trace": trace}
            except Exception as e:
                trace.append({"action": "type_into", "selector": selector, "ok": False,
                              "attempt": attempt + 1, "error": str(e)})
        else:
            trace.append({"action": "type_into", "selector": selector, "ok": False,
                          "attempt": attempt + 1, "error": loc.get("error", "定位失败")})
        if attempt < retry:
            time.sleep(retry_delay)
    return {"ok": False, "account": acct, "trace": trace, "error": trace[-1].get("error", "重试后仍失败")}


def browser_task(account, steps, max_steps=10, total_timeout=60.0):
    """按步骤顺序执行浏览器任务，带 trace + 预算（步骤上限/总超时），失败重试后继续。
    steps: [{"action": "navigate|click|type|scroll|wait|eval", ...}, ...]
    返回全 trace，供 Evidence 可追溯；默认预算远小于采集安全 Gate 上限。
    """
    acct = _canonical_account(account)
    t0 = time.time()
    trace = []
    executed = 0
    for idx, step in enumerate(steps):
        if executed >= max_steps:
            trace.append({"idx": idx, "action": step.get("action"), "ok": False,
                          "skipped": True, "reason": "步骤预算超限"})
            break
        if time.time() - t0 > total_timeout:
            trace.append({"idx": idx, "action": step.get("action"), "ok": False,
                          "skipped": True, "reason": "总超时"})
            break
        action = step.get("action")
        st = time.time()
        try:
            if action == "navigate":
                r = navigate(acct, step.get("url", ""))
            elif action == "click":
                r = click_selector(acct, step.get("selector"), retry=step.get("retry", 2))
            elif action == "type":
                r = type_into(acct, step.get("selector"), step.get("text", ""),
                              retry=step.get("retry", 2))
            elif action == "scroll":
                r = scroll_page(acct, float(step.get("delta_y", 400)))
            elif action == "wait":
                time.sleep(float(step.get("seconds", 1)))
                r = {"ok": True}
            elif action == "eval":
                r = evaluate(acct, step.get("expression", ""))
            else:
                r = {"ok": False, "error": "未知 action: %s" % action}
        except Exception as e:
            r = {"ok": False, "error": str(e)}
        executed += 1
        trace.append({"idx": idx, "action": action, "ok": bool(r.get("ok")),
                      "elapsed_ms": int((time.time() - st) * 1000),
                      "detail": r.get("error") or r.get("url") or r.get("length")
                                or r.get("scroll_y") or ""})
    ok_steps = sum(1 for t in trace if t.get("ok"))
    skipped = sum(1 for t in trace if t.get("skipped"))
    return {"ok": ok_steps + skipped == len(trace) and len(trace) > 0,
            "account": acct, "executed": executed, "ok_steps": ok_steps,
            "total_ms": int((time.time() - t0) * 1000), "trace": trace}


# ─────────────────────────── Flask Blueprint ───────────────────────────

def register_internal_browser(app):
    """在 Flask app 上注册内置浏览器 API 蓝图。"""
    from flask import Blueprint, jsonify, request

    bp = Blueprint("internal_browser", __name__)

    @bp.route("/api/internal-browser/accounts", methods=["GET"])
    def api_accounts():
        return jsonify({"ok": True, "accounts": list_accounts()})

    @bp.route("/api/internal-browser/state", methods=["GET"])
    def api_state():
        account = request.args.get("account", "")
        return jsonify({"ok": True, "state": get_state(account)})

    @bp.route("/api/internal-browser/screenshot", methods=["GET"])
    def api_screenshot():
        account = request.args.get("account", "")
        quality = int(request.args.get("quality", "70"))
        try:
            result = capture_screenshot(account, quality=quality)
            return jsonify(result)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 502

    @bp.route("/api/internal-browser/navigate", methods=["POST"])
    def api_navigate():
        """P1-D: 导航到URL，经过 browser_surface.evaluate_navigation 门禁。
        strict 模式外部域名返回 need_confirmation，前端确认后带 confirmed=true 重试。"""
        data = request.get_json(force=True, silent=True) or {}
        url = data.get("url", "")
        confirmed = bool(data.get("confirmed", False))
        account = data.get("account", "")
        try:
            port = _port_for(_canonical_account(account))
        except Exception:
            port = 9223
        try:
            import internal_browser_adapter as adapter
            result = adapter.navigate(url, port=port, confirmed=confirmed)
            status_code = 403 if result.get("status") == "blocked" else 200
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({"ok": False, "status": "error", "error": str(e)}), 500

    @bp.route("/api/internal-browser/tabs", methods=["GET"])
    def api_tabs():
        """P1-D: 当前Tab列表（指定端口，默认香港生产端口9223）。"""
        port = int(request.args.get("port", "9223"))
        try:
            import internal_browser_adapter as adapter
            return jsonify(adapter.list_tabs(port=port))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e), "tabs": []}), 500

    @bp.route("/api/internal-browser/refresh", methods=["POST"])
    def api_refresh():
        """P1-D: 刷新当前Tab（CDP Page.reload）。"""
        data = request.get_json(force=True, silent=True) or {}
        port = int(data.get("port", 9223))
        target_id = data.get("target_id", "")
        try:
            import internal_browser_adapter as adapter
            return jsonify(adapter.refresh(port=port, target_id=target_id or None))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/internal-browser/switch-tab", methods=["POST"])
    def api_switch_tab():
        """P1-D: 切换（激活）指定Tab。"""
        data = request.get_json(force=True, silent=True) or {}
        port = int(data.get("port", 9223))
        target_id = data.get("target_id", "")
        if not target_id:
            return jsonify({"ok": False, "error": "target_id 为空"}), 400
        try:
            import internal_browser_adapter as adapter
            return jsonify(adapter.switch_tab(port=port, target_id=target_id))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @bp.route("/api/internal-browser/evaluate", methods=["POST"])
    def api_evaluate():
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(evaluate(data.get("account"), data.get("expression", "")))

    @bp.route("/api/internal-browser/click", methods=["POST"])
    def api_click():
        data = request.get_json(force=True, silent=True) or {}
        try:
            return jsonify(click_at(data.get("account"),
                                    float(data.get("x", 0)), float(data.get("y", 0))))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400

    @bp.route("/api/internal-browser/type", methods=["POST"])
    def api_type():
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(type_text(data.get("account"), data.get("text", "")))

    @bp.route("/api/internal-browser/scroll", methods=["POST"])
    def api_scroll():
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(scroll_page(data.get("account"), float(data.get("delta_y", 400))))

    @bp.route("/api/internal-browser/history", methods=["POST"])
    def api_history():
        data = request.get_json(force=True, silent=True) or {}
        action = data.get("action", "reload")
        if action not in ("back", "forward", "reload", "home"):
            return jsonify({"ok": False, "error": f"未知 action: {action}"}), 400
        return jsonify(history_action(data.get("account"), action))

    @bp.route("/api/internal-browser/find", methods=["POST"])
    def api_find():
        data = request.get_json(force=True, silent=True) or {}
        return jsonify(find_element(data.get("account"), data.get("selector", "")))

    @bp.route("/api/internal-browser/click-selector", methods=["POST"])
    def api_click_selector():
        data = request.get_json(force=True, silent=True) or {}
        try:
            return jsonify(click_selector(data.get("account"), data.get("selector", ""),
                                          retry=int(data.get("retry", 2))))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400

    @bp.route("/api/internal-browser/type-into", methods=["POST"])
    def api_type_into():
        data = request.get_json(force=True, silent=True) or {}
        try:
            return jsonify(type_into(data.get("account"), data.get("selector", ""),
                                     data.get("text", ""), retry=int(data.get("retry", 2))))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400

    @bp.route("/api/internal-browser/task", methods=["POST"])
    def api_task():
        data = request.get_json(force=True, silent=True) or {}
        steps = data.get("steps") or []
        if not isinstance(steps, list) or len(steps) > 20:
            return jsonify({"ok": False, "error": "steps 必须为非空数组且≤20"}), 400
        try:
            return jsonify(browser_task(data.get("account"), steps,
                                        max_steps=int(data.get("max_steps", 10)),
                                        total_timeout=float(data.get("total_timeout", 60))))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400



    app.register_blueprint(bp)
    return bp
