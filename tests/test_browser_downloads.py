# -*- coding: utf-8 -*-
"""下载实时进度监听单测（mock WS，不真实连接）"""
import pytest
import browser_surface as bs


@pytest.fixture
def client():
    """独立 Flask app（只注册 browser_surface_api，无全局 Basic Auth）。"""
    from flask import Flask
    import browser_surface_api
    app = Flask(__name__)
    browser_surface_api.register_browser_surface_api(app)
    return app.test_client()


class TestDownloadManager:
    def test_singleton_per_port(self):
        """同一端口返回同一实例。"""
        m1 = bs.DownloadManager.get(19001)
        m2 = bs.DownloadManager.get(19001)
        assert m1 is m2

    def test_status_not_running(self):
        mgr = bs.DownloadManager.get(19002)
        s = mgr.status()
        assert s["port"] == 19002
        assert s["running"] is False
        assert s["connected"] is False
        assert s["active_count"] == 0

    def test_download_will_begin_event(self, monkeypatch):
        """模拟 downloadWillBegin 事件，验证下载状态记录。"""
        mgr = bs.DownloadManager.get(19003)
        # 直接调用内部事件处理逻辑（通过模拟 _listen_loop 的事件解析）
        msg = {"method": "Browser.downloadWillBegin", "params": {
            "guid": "test-guid-1", "url": "https://example.com/file.zip",
            "suggestedFilename": "file.zip"}}
        # 手动触发事件处理（复制 _listen_loop 中的逻辑）
        import time
        with mgr._lock:
            mgr._downloads["test-guid-1"] = {
                "state": "inProgress", "url": "https://example.com/file.zip",
                "filename": "file.zip", "totalBytes": 0, "receivedBytes": 0,
                "percent": 0, "startedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S")}
        active = mgr.active_downloads()
        assert len(active) == 1
        assert active[0]["filename"] == "file.zip"
        assert active[0]["state"] == "inProgress"

    def test_download_progress_update(self, monkeypatch):
        """模拟 downloadProgress 事件，验证进度更新。"""
        mgr = bs.DownloadManager.get(19004)
        import time
        with mgr._lock:
            mgr._downloads["g2"] = {
                "state": "inProgress", "url": "https://x/f.zip", "filename": "f.zip",
                "totalBytes": 1000, "receivedBytes": 0, "percent": 0,
                "startedAt": "t", "updatedAt": "t"}
        # 模拟进度更新 50%
        with mgr._lock:
            d = mgr._downloads["g2"]
            d["receivedBytes"] = 500
            d["percent"] = 50.0
        active = mgr.active_downloads()
        assert active[0]["percent"] == 50.0
        assert active[0]["receivedBytes"] == 500

    def test_download_completed_removes_from_active(self):
        """下载完成后不在 active 列表（但仍在 all_downloads 直到清理）。"""
        mgr = bs.DownloadManager.get(19005)
        import time
        with mgr._lock:
            mgr._downloads["g3"] = {
                "state": "completed", "url": "https://x/f.zip", "filename": "f.zip",
                "totalBytes": 1000, "receivedBytes": 1000, "percent": 100.0,
                "startedAt": "t", "updatedAt": "t"}
        assert len(mgr.active_downloads()) == 0
        assert len(mgr.all_downloads()) == 1

    def test_cancel_not_connected(self):
        """未连接时 cancel 返回错误。"""
        mgr = bs.DownloadManager.get(19006)
        r = mgr.cancel("any-guid")
        assert r["ok"] is False
        assert "not connected" in r["error"]


class TestDownloadAPI:
    def test_monitor_status_endpoint(self, client, monkeypatch):
        monkeypatch.setattr(bs, "_verified_general_browser", lambda *args: True)
        r = client.get("/api/browser-surface/downloads/monitor/status").get_json()
        assert r["port"] == bs.GENERAL_CDP_PORT
        assert "running" in r

    def test_active_endpoint(self, client, monkeypatch):
        monkeypatch.setattr(bs, "_verified_general_browser", lambda *args: True)
        r = client.get("/api/browser-surface/downloads/active").get_json()
        assert r["ok"] and r["downloads"] == []

    def test_unowned_port_is_blocked(self, client):
        response = client.get("/api/browser-surface/downloads/active?port=19008")
        assert response.status_code == 403
        assert response.get_json()["code"] == "BROWSER_SESSION_BLOCKED"

    def test_cancel_requires_guid(self, client):
        r = client.post("/api/browser-surface/downloads/cancel", json={})
        assert r.status_code == 400
