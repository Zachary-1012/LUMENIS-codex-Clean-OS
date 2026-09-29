# -*- coding: utf-8 -*-
"""版本中心 · 自动保存守护线程

检测源码变化 → 自动成版本 → 自动推送 GitHub（间隔/开关由版本中心配置控制）。
- daemon 线程，主进程退出即结束，绝不阻塞系统；
- 任何异常只记录不抛出，版本能力永远是增强项，不拖垮主业务；
- 单例启动，避免 Flask debug reloader / 多入口重复拉起。
"""
import os
import threading
import time
from .git_manager import gm

_watcher_started = False
_watcher_lock = threading.Lock()


def _loop():
    g = gm()
    while True:
        try:
            # 每 60s 巡检一次是否到点，到点由 manager 内部按 interval 防抖
            time.sleep(60)
            if g.load_config().get("auto_commit") is True:
                g.auto_save_if_changed()
        except Exception as e:  # noqa: BLE001  版本守护永不影响主系统
            print(f"[version-watcher] 巡检异常(已忽略): {type(e).__name__}: {e}")
            time.sleep(60)


def start_version_watcher():
    """幂等启动自动版本守护线程。"""
    global _watcher_started
    with _watcher_lock:
        if _watcher_started:
            return False
        if os.environ.get('ZBC_TEST_OFFLINE') == '1':
            return False  # 测试隔离：不启动 git 自动提交守护（测试期严禁自动 commit 工作区）
        g = gm()
        if g.load_config().get("auto_commit") is not True:
            return False
        if not g.is_repo():
            return False
        t = threading.Thread(target=_loop, name="version-center-watcher", daemon=True)
        t.start()
        _watcher_started = True
        return True
