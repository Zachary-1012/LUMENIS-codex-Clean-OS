# -*- coding: utf-8 -*-
"""[Moved 2026-10-13 from repo-root internal_browser_stream.py; single owner lumenis/system/browser/runtime]
Zachary OS AI · Internal Browser —— 实时画面流（Screencast over SSE）

与 internal_browser.py 的「一次截图一条短连接」不同，本模块为每个驻场账号维护
一条持久 CDP WebSocket，用 Page.startScreencast 让浏览器**主动推帧**（云浏览器/
Browserless live view 的标准做法），再通过 SSE 把最新帧推给前端，帧率与流畅度
远高于轮询截图。

设计要点：
  - 引用计数：第一个观看者连上才 startScreencast，最后一个断开即 stop 并关连接，
    无人观看时不编码、不耗 CPU。
  - 单后台守护线程收帧，收到 Page.screencastFrame 立即 Ack（不 Ack 浏览器会停推），
    只缓存「最新一帧」，SSE 生成器按节奏取，慢客户端丢旧帧不堆积。
  - ws 断线有限重连（最多 3 次），状态通过 state 暴露给前端状态点。
  - 纯标准库 + 已有 websocket-client，不引入 flask-sock/gevent。
"""
from __future__ import annotations
import base64
import json
import threading
import time
from typing import Optional

try:
    import websocket
except Exception:  # pragma: no cover
    websocket = None

import internal_browser as ib


class ScreencastSession:
    """单个驻场账号的持久 screencast 会话（后台线程收帧）。"""

    def __init__(self, account: str, max_width: int = 1280, quality: int = 55):
        self.account = ib._canonical_account(account)
        self.port = ib._port_for(self.account)
        self.max_width = max_width
        self.quality = quality
        self._lock = threading.Lock()
        self._latest: dict = {}          # {seq, data, ts, dw, dh}
        self._seq = 0
        self._ws = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.viewers = 0                 # 引用计数
        self.online = False
        self.last_error = ""
        self.fps = 0.0
        self._frame_times: list = []

    # ---------- 生命周期 ----------
    def acquire(self):
        """观看者 +1，必要时启动后台收帧。"""
        self.viewers += 1
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, name=f"screencast-{self.account}", daemon=True)
            self._thread.start()

    def release(self):
        """观看者 -1，归零则停止。"""
        self.viewers = max(0, self.viewers - 1)
        if self.viewers == 0:
            self.stop()

    def stop(self):
        self._running = False
        try:
            if self._ws:
                self._safe_cdp("Page.stopScreencast", {}, msg_id=9001, timeout=2.0)
        except Exception:
            pass
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
        self._ws = None

    # ---------- 帧读取 ----------
    def get_latest(self, after_seq: int) -> Optional[dict]:
        with self._lock:
            if self._latest.get("seq", 0) > after_seq:
                return dict(self._latest)
        return None

    def state(self) -> dict:
        with self._lock:
            seq = self._latest.get("seq", 0)
        return {
            "account": self.account, "port": self.port, "online": self.online,
            "viewers": self.viewers, "seq": seq, "fps": round(self.fps, 1),
            "error": self.last_error,
        }

    # ---------- 内部 ----------
    def _connect_ws(self):
        pages = ib._get_page_targets(self.port, timeout=2.0)
        if not pages:
            raise RuntimeError(f"端口 {self.port} 无可用页面 target")
        # 优先选平台主页 target
        pick = pages[0]
        for t in pages:
            if any(d in (t.get("url", "")) for d in ("xiaohongshu.com", "rednote.com")):
                pick = t
                break
        ws = websocket.create_connection(pick["webSocketDebuggerUrl"], timeout=4.0)
        self._safe_send(ws, {"id": 1, "method": "Page.enable"})
        self._drain_until_id(ws, 1, timeout=3.0)
        self._safe_send(ws, {"id": 2, "method": "Page.startScreencast", "params": {
            "format": "jpeg", "quality": self.quality,
            "maxWidth": self.max_width, "maxHeight": 900, "everyNthFrame": 1,
        }})
        self._drain_until_id(ws, 2, timeout=3.0)
        return ws

    @staticmethod
    def _safe_send(ws, obj: dict):
        ws.send(json.dumps(obj))

    def _safe_cdp(self, method: str, params: dict, msg_id: int, timeout: float):
        if not self._ws:
            return
        self._safe_send(self._ws, {"id": msg_id, "method": method, "params": params or {}})
        self._drain_until_id(self._ws, msg_id, timeout=timeout)

    @staticmethod
    def _drain_until_id(ws, target_id: int, timeout: float):
        deadline = time.time() + timeout
        ws.settimeout(0.5)
        while time.time() < deadline:
            try:
                raw = ws.recv()
            except Exception:
                continue
            try:
                m = json.loads(raw)
            except Exception:
                continue
            if m.get("id") == target_id:
                return m
        return None

    def _loop(self):
        retries = 0
        while self._running and self.viewers > 0 and retries <= 3:
            try:
                self._ws = self._connect_ws()
                self.online = True
                self.last_error = ""
                retries = 0
                self._pump()
            except Exception as e:
                self.online = False
                self.last_error = str(e)[:160]
                retries += 1
                time.sleep(min(1.5 * retries, 4.0))
            finally:
                try:
                    if self._ws:
                        self._ws.close()
                except Exception:
                    pass
                self._ws = None
        self._running = False
        self.online = False

    def _pump(self):
        """持续接收 screencast 帧并 Ack。"""
        ws = self._ws
        ws.settimeout(1.0)
        ack_id = 5000
        while self._running and self.viewers > 0:
            try:
                raw = ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                raise RuntimeError(f"ws 接收中断: {e}")
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            method = msg.get("method", "")
            if method == "Page.screencastFrame":
                p = msg.get("params", {})
                meta = p.get("metadata", {})
                sid = meta.get("sessionId")
                data = p.get("data", "")
                if data:
                    now = time.time()
                    self._frame_times.append(now)
                    self._frame_times = [t for t in self._frame_times if now - t <= 2.0]
                    if len(self._frame_times) >= 2:
                        self.fps = (len(self._frame_times) - 1) / (self._frame_times[-1] - self._frame_times[0] + 1e-6)
                    with self._lock:
                        self._seq += 1
                        self._latest = {
                            "seq": self._seq, "data": data, "ts": now,
                            "dw": meta.get("deviceWidth", 0), "dh": meta.get("deviceHeight", 0),
                        }
                # 必须 Ack，否则浏览器停止推帧
                ack_id += 1
                try:
                    self._safe_send(ws, {"id": ack_id, "method": "Page.screencastFrameAck",
                                         "params": {"sessionId": sid}})
                except Exception:
                    pass


class ScreencastManager:
    """按账号复用 session。"""
    def __init__(self):
        self._sessions: dict[str, ScreencastSession] = {}
        self._g = threading.Lock()

    def get(self, account: str) -> ScreencastSession:
        acct = ib._canonical_account(account)
        with self._g:
            s = self._sessions.get(acct)
            if s is None:
                s = ScreencastSession(acct)
                self._sessions[acct] = s
            return s

    def all_state(self) -> list:
        with self._g:
            return [s.state() for s in self._sessions.values() if s.viewers > 0 or s.online]


MANAGER = ScreencastManager()


def register_stream(app):
    """注册 SSE 实时流与状态路由。"""
    from flask import Blueprint, Response, request, jsonify, stream_with_context

    bp = Blueprint("internal_browser_stream", __name__)

    @bp.route("/api/internal-browser/stream")
    def api_stream():
        account = request.args.get("account", "")
        quality = int(request.args.get("quality", "55"))
        session = MANAGER.get(account)
        session.quality = quality
        session.acquire()

        @stream_with_context
        def gen():
            last_seq = 0
            # 初始握手：告诉客户端流已建立 + 当前状态
            yield "retry: 3000\n"
            idle_ticks = 0
            try:
                while True:
                    frame = session.get_latest(last_seq)
                    if frame:
                        last_seq = frame["seq"]
                        idle_ticks = 0
                        payload = json.dumps({
                            "t": "frame", "seq": frame["seq"], "data": frame["data"],
                            "dw": frame["dw"], "dh": frame["dh"],
                            "fps": round(session.fps, 1), "online": session.online,
                        }, ensure_ascii=False)
                        # SSE 单帧；data 较大，确保一帧一条消息
                        yield f"data: {payload}\n\n"
                    else:
                        idle_ticks += 1
                        # 每 ~3s 推一次状态/心跳，前端据此显示连接状态点
                        if idle_ticks % 20 == 0:
                            yield f"data: {json.dumps({'t':'state','online':session.online,'fps':round(session.fps,1),'error':session.last_error}, ensure_ascii=False)}\n\n"
                        time.sleep(0.06)   # 最高约 16fps，本地回环足够流畅
            except GeneratorExit:
                pass
            finally:
                session.release()

        resp = Response(gen(), mimetype="text/event-stream")
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        resp.headers["Connection"] = "keep-alive"
        return resp

    @bp.route("/api/internal-browser/stream-state")
    def api_stream_state():
        return jsonify({"ok": True, "sessions": MANAGER.all_state()})

    app.register_blueprint(bp)
    return bp
