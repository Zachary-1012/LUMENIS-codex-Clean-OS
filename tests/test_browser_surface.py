# -*- coding: utf-8 -*-
"""序境 · 平台内置浏览器能力层（browser_surface / browser_discovery）离线单元测试。

不依赖在线驻场浏览器、不发起真实网络请求：
- 导航策略门：危险协议 / SSRF 内网段 / strict / allowlist / open
- 多源搜索：mock HTML 解析器与编排去重
- 书签 / 历史：tmp_path 隔离，不污染生产 data/private
- API 层：最小 Flask app + test_client
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import browser_surface as bs
import browser_discovery as bd


# ─────────────────────────── 导航策略门 ───────────────────────────

@pytest.mark.parametrize("url", [
    "file:///C:/Windows/win.ini",
    "chrome://settings",
    "edge://flags",
    "about:blank",
    "javascript:alert(1)",
    "data:text/html,<script>",
    "view-source:https://example.com",
    "blob:https://example.com/abcd",
])
def test_blocked_schemes_any_mode(url):
    # 任何模式下危险协议都必须被拦截
    for mode in ("strict", "allowlist", "open"):
        r = bs.evaluate_navigation(url, mode=mode)
        assert r["allowed"] is False, f"{mode} 应拦截 {url}"


@pytest.mark.parametrize("ip", [
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://172.16.4.4/",
    "http://169.254.1.1/",
    "http://0.0.0.0/",
])
def test_ssrf_internal_blocked(ip):
    r = bs.evaluate_navigation(ip, mode="open")  # 即使 open 也拦截私网
    assert r["allowed"] is False
    assert "SSRF" in r["reason"] or "内网" in r["reason"]


@pytest.mark.parametrize("ip", [
    "http://127.0.0.1/",
    "http://localhost/",
    "http://[::1]/",
])
def test_platform_internal_host_allowed(ip):
    """P1-D: 平台内部主机(127.0.0.1/localhost/::1)直接放行，其他私网仍SSRF拦截。"""
    r = bs.evaluate_navigation(ip, mode="open")
    assert r["allowed"] is True
    assert r["status"] == "allowed"


def test_strict_only_platform():
    r = bs.evaluate_navigation("https://www.xiaohongshu.com/explore", mode="strict")
    assert r["allowed"] is True
    r2 = bs.evaluate_navigation("https://www.zhihu.com/", mode="strict")
    assert r2["allowed"] is True


def test_strict_allows_approved_platform_and_research_domains(monkeypatch):
    """平台可在序境内置浏览器打开；这不等于启用对应采集器。"""
    monkeypatch.setattr(bs, "_is_internal_host", lambda _host: False)
    for domain in bs.BROWSER_PLATFORM_DOMAINS:
        result = bs.evaluate_navigation(f"https://www.{domain}/", mode="strict")
        assert result["allowed"] is True, domain


def test_allowlist_extra_domains(monkeypatch):
    monkeypatch.setenv("INTERNAL_BROWSER_EXTRA_DOMAINS", "zhihu.com, bing.com")
    # open 模式会触发 DNS，这里只测 allowlist 的域名匹配（在 SSRF 之前先判公网域，
    # zhihu/bing 是公网域名；为避免测试依赖网络，mock 掉内网判定）
    monkeypatch.setattr(bs, "_is_internal_host", lambda h: False)
    monkeypatch.setattr(bs, "current_nav_mode", lambda: "allowlist")
    assert "zhihu.com" in bs._extra_domains()
    r = bs.evaluate_navigation("https://www.zhihu.com/question/1")
    assert r["allowed"] is True
    r2 = bs.evaluate_navigation("https://www.example.com/")
    assert r2["allowed"] is False  # 未追加的域仍被拦


def test_open_public_passes(monkeypatch):
    monkeypatch.setattr(bs, "_is_internal_host", lambda h: False)
    r = bs.evaluate_navigation("https://any-public-site.example/page")
    # 默认 allowlist 会拦未知域；显式 open 放行公网
    r_open = bs.evaluate_navigation("https://any-public-site.example/page", mode="open")
    assert r_open["allowed"] is True
    assert r["mode"] == "strict"  # P1-D: 默认 strict


def test_empty_and_bad_url():
    assert bs.evaluate_navigation("")["allowed"] is False
    assert bs.evaluate_navigation("ftp://example.com/x", mode="open")["allowed"] is False


def test_domain_suffix_match():
    assert bs._domain_allowed("www.xiaohongshu.com", ["xiaohongshu.com"])
    assert bs._domain_allowed("xiaohongshu.com", ["xiaohongshu.com"])
    assert not bs._domain_allowed("evil-xiaohongshu.com", ["xiaohongshu.com"])


# ─────────────────────────── 多源搜索解析 ───────────────────────────

def test_bing_parser_offline(monkeypatch):
    html = ('<li class="b_algo"><h2><a href="https://a.com/1">标题 A</a></h2><p>摘要 A</p></li>'
            '<li class="b_algo"><h2><a href="https://a.com/2"><b>标题</b> B</a></h2></li>')
    monkeypatch.setattr(bd, "_get", lambda u, timeout=15: html)
    r = bd._search_bing("q", 10)
    assert len(r) == 2
    assert r[0]["engine"] == "bing"
    assert r[0]["domain"] == "a.com"
    assert r[0]["source_adapter"] == "bing_html"


def test_ddg_redirect_decode():
    assert bd._decode_ddg_redirect("//duckduckgo.com/l/?uddg=https%3A%2F%2Fx.org%2Fp&rut=1") \
        == "https://x.org/p"
    assert bd._decode_ddg_redirect("https://x.org/direct") == "https://x.org/direct"


def test_ddg_parser_block_split(monkeypatch):
    html = ('<div class="result"><a class="result__a" href="//ddg.io/l/?uddg=https%3A%2F%2Fc.com%2F1">'
            'C 标题</a><a class="result__snippet">C 摘要</a></div>')
    monkeypatch.setattr(bd, "_get", lambda u, timeout=15: html)
    r = bd._search_duckduckgo("q", 10)
    assert len(r) == 1
    assert r[0]["url"] == "https://c.com/1"


def test_search_engine_filter_and_dedup(monkeypatch):
    html = '<li class="b_algo"><h2><a href="https://a.com/1">A</a></h2></li>'
    monkeypatch.setattr(bd, "_get", lambda u, timeout=15: html)
    only_bing = bd.search("q", engines="bing")
    assert all(x["engine"] == "bing" for x in only_bing)
    assert bd.search("q", engines=["nonexistent"]) == []


def test_discover_backward_compatible_signature(monkeypatch):
    # 旧调用 discover(queries, limit) 必须仍可用
    html = '<li class="b_algo"><h2><a href="https://a.com/1">A</a></h2></li>'
    monkeypatch.setattr(bd, "_get", lambda u, timeout=15: html)
    out = bd.discover(["k1", "k2"], 10, engines=["bing"])
    assert isinstance(out, list)


# ─────────────────────────── 书签 / 历史（tmp 隔离）───────────────────────────

@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "_BOOKMARK_FILE", str(tmp_path / "bm.json"))
    monkeypatch.setattr(bs, "_HISTORY_FILE", str(tmp_path / "hist.json"))
    return tmp_path


def test_bookmark_add_dedup_remove(isolated_store, monkeypatch):
    monkeypatch.setattr(bs, "evaluate_navigation",
                        lambda u, m=None: {"allowed": True, "reason": "test", "mode": "allowlist"})
    r = bs.add_bookmark("页", "https://www.xiaohongshu.com/a")
    assert r["ok"] and len(r["bookmarks"]) == 1
    r2 = bs.add_bookmark("页", "https://www.xiaohongshu.com/a")  # 同 URL 去重
    assert r2.get("deduplicated") and len(r2["bookmarks"]) == 1
    r3 = bs.remove_bookmark("https://www.xiaohongshu.com/a")
    assert len(r3["bookmarks"]) == 0


def test_bookmark_rejects_blocked(isolated_store):
    r = bs.add_bookmark("x", "file:///C:/x")
    assert r["ok"] is False


def test_history_ring_limit(isolated_store, monkeypatch):
    for i in range(5):
        bs.record_history(f"t{i}", f"https://www.xiaohongshu.com/p{i}")
    r = bs.list_history()
    assert len(r["history"]) == 5
    # 同 URL 重访置顶多一条
    bs.record_history("t0-new", "https://www.xiaohongshu.com/p0")
    r2 = bs.list_history()
    assert len(r2["history"]) == 5 and r2["history"][0]["title"] == "t0-new"
    bs.clear_history()
    assert bs.list_history()["history"] == []


def test_history_rejects_non_http(isolated_store):
    assert bs.record_history("x", "javascript:alert(1)")["ok"] is False


# ─────────────────────────── API 层（最小 Flask，离线）───────────────────────────

@pytest.fixture
def client():
    from flask import Flask
    import browser_surface_api
    app = Flask(__name__)
    browser_surface_api.register_browser_surface_api(app)
    return app.test_client()


def test_api_capabilities_and_policy(client):
    r = client.get("/api/browser-surface/capabilities")
    assert r.status_code == 200 and r.get_json()["ok"]
    p = client.get("/api/browser-surface/policy?url=file:///C:/x").get_json()
    assert p["evaluation"]["allowed"] is False


def test_browser_surface_api_defaults_to_product_browser(monkeypatch, client):
    """未指定端口的产品浏览器 API 必须走独立通用实例 9224。"""
    seen = {}
    monkeypatch.setattr(bs, "_verified_general_browser", lambda *args: True)

    def fake_list_tabs(account=None, port=None):
        seen.update(account=account, port=port)
        return {"ok": True, "cdp_port": port, "tabs": [], "count": 0}

    monkeypatch.setattr(bs, "list_tabs", fake_list_tabs)
    response = client.get("/api/browser-surface/tabs")
    assert response.status_code == 200
    assert seen["port"] == bs.GENERAL_CDP_PORT == 9224


def test_browser_surface_history_endpoint_rejects_unknown_action(client):
    response = client.post("/api/browser-surface/tab/history", json={"action": "javascript"})
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_api_search_requires_query(client):
    assert client.get("/api/browser-surface/search?q=").status_code == 400


def test_api_tab_new_validates_url(client):
    r = client.post("/api/browser-surface/tab/new", json={"url": ""})
    assert r.status_code == 400


def test_api_bookmark_roundtrip(client, tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "_BOOKMARK_FILE", str(tmp_path / "b.json"))
    r = client.get("/api/browser-surface/bookmarks")
    assert r.status_code == 200 and r.get_json()["bookmarks"] == []


# ─────────────────────────── 增量能力：导航配置 / 通用实例 / 页内查找 / 下载 ─────────────

def test_nav_config_roundtrip(tmp_path, monkeypatch):
    cfg_file = str(tmp_path / "nav.json")
    monkeypatch.setattr(bs, "_ALLOWLIST_FILE", cfg_file)
    monkeypatch.delenv("INTERNAL_BROWSER_NAV_MODE", raising=False)
    monkeypatch.delenv("INTERNAL_BROWSER_EXTRA_DOMAINS", raising=False)
    # 默认 P1-D: strict
    g = bs.get_nav_config()
    assert g["ok"] and g["nav_mode"] == "strict" and g["nav_mode_source"] == "default"
    # 写 open 模式 + 追加域
    r = bs.set_nav_config(mode="open", extra_domains=["Example.com", "bing.com"])
    assert r["ok"] and r["nav_mode"] == "open"
    assert "example.com" in r["extra_domains"] and "bing.com" in r["extra_domains"]
    # 再追加去重
    r2 = bs.set_nav_config(extra_domains=["example.com", "zhihu.com"], append=True)
    assert r2["extra_domains"].count("example.com") == 1
    assert "zhihu.com" in r2["extra_domains"]
    # 非法模式拒绝
    bad = bs.set_nav_config(mode="uber")
    assert bad["ok"] is False


def test_nav_config_invalid_mode_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "_ALLOWLIST_FILE", str(tmp_path / "n.json"))
    assert bs.set_nav_config(mode="hack")["ok"] is False


def test_general_browser_online_requires_verified_owned_session(monkeypatch):
    monkeypatch.setattr(bs, "_verified_general_browser", lambda: False)
    assert bs.general_browser_online() is False
    monkeypatch.setattr(bs, "_verified_general_browser", lambda: True)
    assert bs.general_browser_online() is True


def test_find_in_page_offline_graceful(monkeypatch):
    # Use the verified product browser endpoint; the retired 9222 port stays blocked.
    monkeypatch.setattr(bs, "_verified_general_browser", lambda *args: True)
    monkeypatch.setattr(bs, "_find_tab_ws", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    r = bs.find_in_page("test", port=bs.GENERAL_CDP_PORT)
    assert r["ok"] is False and "offline" in r["error"]


def test_stop_find_offline_graceful(monkeypatch):
    monkeypatch.setattr(bs, "_verified_general_browser", lambda *args: True)
    monkeypatch.setattr(bs, "_find_tab_ws", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    r = bs.stop_find_in_page(port=bs.GENERAL_CDP_PORT)
    assert r["ok"] is False


def test_set_download_behavior_offline(monkeypatch):
    monkeypatch.setattr(bs, "_verified_general_browser", lambda *args: True)
    monkeypatch.setattr(bs, "_find_tab_ws", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    r = bs.set_download_behavior(enabled=True, port=bs.GENERAL_CDP_PORT)
    assert r["ok"] is False


def test_list_downloads_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "_DOWNLOAD_DIR", str(tmp_path / "dl"))
    r = bs.list_downloads()
    assert r["ok"] and r["files"] == []


def test_api_nav_config_endpoint(client, tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "_ALLOWLIST_FILE", str(tmp_path / "n.json"))
    monkeypatch.delenv("INTERNAL_BROWSER_NAV_MODE", raising=False)
    monkeypatch.delenv("INTERNAL_BROWSER_EXTRA_DOMAINS", raising=False)
    g = client.get("/api/browser-surface/nav-config").get_json()
    assert g["ok"] and g["nav_mode"] == "strict"  # P1-D: 默认 strict
    p = client.post("/api/browser-surface/nav-config", json={"mode": "open"}).get_json()
    assert p["ok"] and p["nav_mode"] == "open"
    bad = client.post("/api/browser-surface/nav-config", json={})
    assert bad.status_code == 400


def test_api_general_status(client):
    r = client.get("/api/browser-surface/general-browser/status").get_json()
    assert r["ok"] and r["port"] == 9224 and "online" in r
    assert "profile" not in r


def test_general_browser_uses_supported_system_default_without_edge_fallback(monkeypatch):
    import cdp_helper

    monkeypatch.setattr(cdp_helper, "find_browser_path", lambda name: f"/{name}" if name in {"chrome", "edge"} else None)
    monkeypatch.setattr(cdp_helper, "_https_associated_executable", lambda: r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    assert cdp_helper.system_default_cdp_browser() == "chrome"
    monkeypatch.setattr(cdp_helper, "_https_associated_executable", lambda: r"C:\Program Files\Mozilla Firefox\firefox.exe")
    assert cdp_helper.system_default_cdp_browser() is None


def test_general_browser_launch_is_headless_isolated_and_reuses_only_its_session(tmp_path, monkeypatch):
    import cdp_helper

    monkeypatch.setattr(bs, "GENERAL_PROFILE_BASE", str(tmp_path / "general"))
    monkeypatch.setattr(cdp_helper, "system_default_cdp_browser", lambda: "chrome")
    online = {"value": False}
    monkeypatch.setattr(cdp_helper, "is_cdp_port_open", lambda _port: online["value"])
    version = {"Browser": "HeadlessChrome/140.0", "webSocketDebuggerUrl": "ws://127.0.0.1:9224/devtools/browser/owned"}
    monkeypatch.setattr(bs, "_http_json", lambda *_args, **_kwargs: version)
    launched = {}

    def start(**kwargs):
        launched.update(kwargs)
        online["value"] = True
        return {"success": True, "pid": 321}

    monkeypatch.setattr(cdp_helper, "start_cdp_browser", start)
    assert bs.ensure_general_browser(force=True)["code"] == "FORCED_BROWSER_RESTART_UNAVAILABLE"
    assert launched == {}
    first = bs.ensure_general_browser()
    assert first["ok"] and first["browser"] == "chrome"
    assert launched["headless"] is True and launched["loopback_only"] is True
    assert launched["direct_connection"] is False
    assert launched["launch_url"] == "about:blank"
    assert launched["profile_dir"] == str(tmp_path / "general-chrome")
    assert bs._resolve_port() == bs.GENERAL_CDP_PORT
    assert bs._resolve_port(port=bs.GENERAL_CDP_PORT) == bs.GENERAL_CDP_PORT
    assert bs.ensure_general_browser()["action"] == "already_online"
    version["webSocketDebuggerUrl"] = "ws://127.0.0.1:9224/devtools/browser/other"
    assert bs.general_browser_online() is False
    assert bs.ensure_general_browser()["code"] == "UNVERIFIED_BROWSER_SESSION"
    with pytest.raises(PermissionError, match="not LUMENIS-owned"):
        bs._resolve_port(port=bs.GENERAL_CDP_PORT)


def test_browser_surface_api_rejects_unverified_product_session(monkeypatch, client):
    monkeypatch.setattr(bs, "_verified_general_browser", lambda *args: False)
    response = client.get("/api/browser-surface/tabs")
    assert response.status_code == 403
    assert response.get_json()["code"] == "BROWSER_SESSION_BLOCKED"


def test_api_find_requires_query(client):
    r = client.post("/api/browser-surface/find", json={"query": ""})
    assert r.status_code == 400
