# -*- coding: utf-8 -*-
"""
ZBC LifecycleMixin — 统一生命周期接入 Mixin V1.0
===================================================
工单：ZBC-LIFECYCLE-CONTRACT-V1
权威实现：runtime_guardian.py

为所有长运行模块提供统一的生命周期管理接入，无需重复实现注册/心跳/检查点/清理逻辑。

用法：
    from lifecycle_mixin import LifecycleMixin

    class MyAIEngine(LifecycleMixin):
        def __init__(self):
            super().__init__(worker_name="my_ai_engine", domain_id="zbmp", product_id="ZBMP")

        def do_work(self):
            self.lifecycle_start()
            try:
                while not self._stop_requested:
                    self.lifecycle_heartbeat()
                    # ... do work ...
                    self.lifecycle_checkpoint(position="page=3")
            finally:
                self.lifecycle_stop()
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    import runtime_guardian as _rg
    _RG_AVAILABLE = True
except Exception as _e:
    _rg = None
    _RG_AVAILABLE = False


class LifecycleMixin:
    """
    统一生命周期 Mixin。所有长运行模块继承此 Mixin 即可获得：
    - worker 注册（create）
    - 租约获取/释放（start/stop）
    - 后台心跳线程（heartbeat）
    - 检查点保存（checkpoint）
    - 暂停/恢复（pause/resume）
    - 优雅停止（stop/cleanup）
    - 归档（archive）

    所有方法均为旁路模式：Runtime Guardian 不可用时不阻断主流程。
    """

    # 子类可覆盖
    LIFECYCLE_WORKER_NAME = "lifecycle_worker"
    LIFECYCLE_DOMAIN_ID = "system"
    LIFECYCLE_PRODUCT_ID = "SYSTEM"
    LIFECYCLE_HEARTBEAT_INTERVAL = 10.0  # 秒
    LIFECYCLE_LEASE_TTL = 60  # 秒

    def __init__(
        self,
        worker_name: Optional[str] = None,
        domain_id: Optional[str] = None,
        product_id: Optional[str] = None,
        heartbeat_interval: Optional[float] = None,
        lease_ttl: Optional[float] = None,
    ):
        self._lifecycle_worker_name = worker_name or self.LIFECYCLE_WORKER_NAME
        self._lifecycle_domain_id = domain_id or self.LIFECYCLE_DOMAIN_ID
        self._lifecycle_product_id = product_id or self.LIFECYCLE_PRODUCT_ID
        self._lifecycle_heartbeat_interval = heartbeat_interval or self.LIFECYCLE_HEARTBEAT_INTERVAL
        self._lifecycle_lease_ttl = lease_ttl or self.LIFECYCLE_LEASE_TTL

        self._lifecycle_worker_id: Optional[str] = None
        self._lifecycle_lease_owner: str = f"pid-{os.getpid()}"
        self._lifecycle_run_id: str = ""
        self._lifecycle_guardian = None
        self._lifecycle_heartbeat_thread: Optional[threading.Thread] = None
        self._lifecycle_heartbeat_stop = threading.Event()
        self._lifecycle_stop_requested = False
        self._lifecycle_paused = False

    # ------------------------------------------------------------------
    # Guardian 懒加载
    # ------------------------------------------------------------------
    def _get_lifecycle_guardian(self):
        if not _RG_AVAILABLE:
            return None
        if self._lifecycle_guardian is None:
            try:
                self._lifecycle_guardian = _rg.get_guardian(self._lifecycle_worker_name)
            except Exception:
                self._lifecycle_guardian = None
        return self._lifecycle_guardian

    # ------------------------------------------------------------------
    # 生命周期方法
    # ------------------------------------------------------------------
    def lifecycle_create(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """注册 worker，状态 CREATED。返回 worker_id 或 None（旁路失败）。"""
        g = self._get_lifecycle_guardian()
        if not g:
            return None
        try:
            self._lifecycle_worker_id = g.lifecycle_create(
                self._lifecycle_worker_name,
                metadata=metadata,
                domain_id=self._lifecycle_domain_id,
                product_id=self._lifecycle_product_id,
            )
            return self._lifecycle_worker_id
        except Exception:
            return None

    def lifecycle_start(self, run_id: str = "") -> bool:
        """启动：获取租约 + 启动心跳线程 + 状态 RUNNING。"""
        if not self._lifecycle_worker_id:
            self.lifecycle_create()
        if not self._lifecycle_worker_id:
            return False
        g = self._get_lifecycle_guardian()
        if not g:
            return False
        try:
            self._lifecycle_run_id = run_id or f"run_{int(time.time())}"
            self._lifecycle_stop_requested = False
            self._lifecycle_paused = False
            ok = g.lifecycle_start(
                self._lifecycle_worker_id,
                owner=self._lifecycle_lease_owner,
                lease_ttl=self._lifecycle_lease_ttl,
            )
            if ok:
                self._start_lifecycle_heartbeat()
            return ok
        except Exception:
            return False

    def lifecycle_heartbeat(self) -> bool:
        """发送一次心跳（通常由后台线程自动调用，也可手动调用）。"""
        if not self._lifecycle_worker_id:
            return False
        g = self._get_lifecycle_guardian()
        if not g:
            return False
        try:
            g.heartbeat(self._lifecycle_worker_id, domain_id=self._lifecycle_domain_id)
            # 续期租约
            g.renew_lease(
                self._lifecycle_worker_id,
                self._lifecycle_lease_owner,
                ttl_seconds=self._lifecycle_lease_ttl,
            )
            return True
        except Exception:
            return False

    def lifecycle_checkpoint(self, position: str = "", state: str = "active",
                             metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """保存检查点。返回 checkpoint_id 或 None。"""
        if not self._lifecycle_worker_id:
            return None
        g = self._get_lifecycle_guardian()
        if not g:
            return None
        try:
            return g.save_checkpoint(
                run_id=self._lifecycle_run_id or f"run_{int(time.time())}",
                worker_id=self._lifecycle_worker_id,
                position=position,
                state=state,
                metadata=metadata,
            )
        except Exception:
            return None

    def lifecycle_pause(self, reason: str = "paused") -> bool:
        """暂停：RUNNING → PAUSED。"""
        if not self._lifecycle_worker_id:
            return False
        g = self._get_lifecycle_guardian()
        if not g:
            return False
        try:
            self._lifecycle_paused = True
            return g.lifecycle_pause(self._lifecycle_worker_id, reason=reason)
        except Exception:
            return False

    def lifecycle_resume(self) -> bool:
        """恢复：PAUSED → RESUMING → RUNNING。"""
        if not self._lifecycle_worker_id:
            return False
        g = self._get_lifecycle_guardian()
        if not g:
            return False
        try:
            self._lifecycle_paused = False
            return g.lifecycle_resume(self._lifecycle_worker_id)
        except Exception:
            return False

    def lifecycle_stop(self, reason: str = "stopped") -> bool:
        """优雅停止：停止心跳 + 释放租约 + 状态 STOPPED。"""
        self._lifecycle_stop_requested = True
        self._stop_lifecycle_heartbeat()
        if not self._lifecycle_worker_id:
            return False
        g = self._get_lifecycle_guardian()
        if not g:
            return False
        try:
            return g.lifecycle_stop(self._lifecycle_worker_id, reason=reason)
        except Exception:
            return False

    def lifecycle_cleanup(self, reason: str = "cleanup") -> bool:
        """清理：释放租约 + 清理内存引用 + 状态 STOPPED。"""
        self._lifecycle_stop_requested = True
        self._stop_lifecycle_heartbeat()
        if not self._lifecycle_worker_id:
            return False
        g = self._get_lifecycle_guardian()
        if not g:
            return False
        try:
            ok = g.lifecycle_cleanup(self._lifecycle_worker_id, reason=reason)
            self._lifecycle_worker_id = None
            return ok
        except Exception:
            return False

    def lifecycle_archive(self, reason: str = "archived") -> bool:
        """归档：STOPPED/DEAD → ARCHIVED（终态）。"""
        if not self._lifecycle_worker_id:
            return False
        g = self._get_lifecycle_guardian()
        if not g:
            return False
        try:
            return g.lifecycle_archive(self._lifecycle_worker_id, reason=reason)
        except Exception:
            return False

    def lifecycle_execute_with_retry(
        self,
        func: Callable,
        *args,
        task_type: str = "",
        payload: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Any:
        """受保护的执行：重试 + 指数退避 + 熔断器 + DLQ。"""
        if not self._lifecycle_worker_id:
            self.lifecycle_create()
        if not self._lifecycle_worker_id:
            return func(*args, **kwargs)  # 旁路失败时直接执行
        g = self._get_lifecycle_guardian()
        if not g:
            return func(*args, **kwargs)
        return g.execute_with_retry(
            self._lifecycle_worker_id, func, *args,
            task_type=task_type, payload=payload,
            run_id=self._lifecycle_run_id, **kwargs,
        )

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------
    @property
    def lifecycle_worker_id(self) -> Optional[str]:
        return self._lifecycle_worker_id

    @property
    def lifecycle_status(self) -> str:
        if not self._lifecycle_worker_id:
            return "not_created"
        g = self._get_lifecycle_guardian()
        if not g:
            return "guardian_unavailable"
        worker = g.get_worker(self._lifecycle_worker_id)
        return worker.get("status", "unknown") if worker else "not_found"

    @property
    def is_lifecycle_running(self) -> bool:
        return self.lifecycle_status == "running" and not self._lifecycle_stop_requested

    @property
    def is_lifecycle_paused(self) -> bool:
        return self._lifecycle_paused

    # ------------------------------------------------------------------
    # 后台心跳线程
    # ------------------------------------------------------------------
    def _start_lifecycle_heartbeat(self) -> None:
        self._lifecycle_heartbeat_stop.clear()
        self._lifecycle_heartbeat_thread = threading.Thread(
            target=self._lifecycle_heartbeat_loop,
            daemon=True,
            name=f"lifecycle-hb-{self._lifecycle_worker_name}",
        )
        self._lifecycle_heartbeat_thread.start()

    def _lifecycle_heartbeat_loop(self) -> None:
        while not self._lifecycle_heartbeat_stop.is_set():
            try:
                if not self._lifecycle_paused:
                    self.lifecycle_heartbeat()
            except Exception:
                pass
            self._lifecycle_heartbeat_stop.wait(self._lifecycle_heartbeat_interval)

    def _stop_lifecycle_heartbeat(self) -> None:
        self._lifecycle_heartbeat_stop.set()
        if self._lifecycle_heartbeat_thread and self._lifecycle_heartbeat_thread.is_alive():
            self._lifecycle_heartbeat_thread.join(timeout=5)
        self._lifecycle_heartbeat_thread = None


# ---------------------------------------------------------------------------
# 函数级生命周期上下文管理器（供无类的函数模块使用）
# ---------------------------------------------------------------------------
from contextlib import contextmanager


@contextmanager
def lifecycle_task(worker_name: str, domain_id: str = "system",
                   product_id: str = "SYSTEM", run_id: str = "",
                   heartbeat_interval: float = 10.0):
    """
    函数级生命周期上下文管理器。

    用法：
        with lifecycle_task("report_generator", domain_id="cth", product_id="CTH") as lc:
            generate_report(...)
            lc.checkpoint(position="section=3")

    旁路模式：Runtime Guardian 不可用时不阻断原流程。
    """
    worker = LifecycleMixin(
        worker_name=worker_name,
        domain_id=domain_id,
        product_id=product_id,
        heartbeat_interval=heartbeat_interval,
    )
    wid = worker.lifecycle_create()
    started = worker.lifecycle_start(run_id=run_id) if wid else False
    try:
        yield worker
    except Exception:
        if started:
            try:
                worker.lifecycle_stop(reason="error")
            except Exception:
                pass
        raise
    else:
        if started:
            try:
                worker.lifecycle_stop(reason="completed")
            except Exception:
                pass
