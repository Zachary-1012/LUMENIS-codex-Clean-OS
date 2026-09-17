"""Z-Brand-Core 小红书 P0 生产编排层（双子星库 Contract 落地）。

职责边界（用户指令·职责钉死）：
  Zachary-OS-AI  = 研究 / 学习（本模块不承载研究逻辑）
  Z-Brand-Core   = 开发 / 执行 / 生产（本模块 = 采集链生产执行编排）

P0 目标流程（硬编码在 run_once / trigger_collection）：
  系统启动 → 小红书 Runtime 检查 → Session 有效 → 直接驻场
        │                     └ Session 失效 → 系统内部弹出扫码(二维码)
        │                                      → 人工扫码一次
        │                                      → 验证成功
        │                                      → 长期驻场
  有采集任务 → 调用指定身份(硬白名单) → 采集 → 入库
            → Z-Brand-Core 主体过滤 → 舆情 / 事件 / 风险

依赖（全部为本仓既有真实模块，不新增未验证依赖）：
  xhs_cookie_bridge  : select_account / verify_account / runtime_preflight_check /
                       ACCOUNT_PROFILES / ALLOWED_USER_IDS / XHS_CN_PRIMARY_NAME / XHS_RETINAUT_NAME
  runtime_preflight  : run_preflight（启动预检）
  auth_recovery_center : recovery_center 服务层（create_task / mark_in_progress /
                       mark_completed / mark_failed）——不依赖 HTTP 请求上下文，可后台线程调用

生产采集身份门禁（RedNote HK-only Contract）：
  XHS_RETINAUT    = 香港/国际生产采集身份
  XHS_CN_PRIMARY  = 保留为诊断/历史凭证映射，但不得进入生产采集任务。
  除香港/国际身份外，任何身份无法进入采集任务。

本模块是"编排 + 状态聚合"，不复制任何采集实现（防止两套 Core）。
"""
from __future__ import annotations

import os
import threading
import time
import logging
from datetime import datetime, timedelta

import xhs_cookie_bridge as bridge
import runtime_preflight

# ============ 常量（生产采集 Contract 硬白名单） ============
# 只引用 bridge 的生产默认身份；ACCOUNT_PROFILES 仍保留历史/诊断映射。
ALLOWED_IDENTITY_NAMES: tuple[str, ...] = (
    bridge.DEFAULT_COLLECTION_ACCOUNT,
)

# 心跳周期（秒）与失效判定阈值（连续失败次数）
HEARTBEAT_INTERVAL = 30.0          # 心跳探活间隔
SESSION_FAIL_THRESHOLD = 3          # 连续失败达此值 → 判定 Session 失效 → 触发扫码恢复
COOLDOWN_AFTER_RECOVERY = 300.0     # 扫码恢复成功后的冷却（秒），避免立即再次触发
SCAN_WAIT_TIMEOUT = 900.0           # 扫码等待超时（秒）= 15 分钟，超时恢复任务标记失败

_logger = logging.getLogger("xhs_p0_orchestrator")


# ============ 运行时状态（模块级，供 /api/xhs/p0/status 聚合） ============
class _P0State:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.session_ok: bool | None = None      # None=尚未探测
        self.heartbeat_last: float | None = None  # 最近一次心跳时间戳
        self.heartbeat_fails = 0                  # 连续失败计数
        self.resident_until: float | None = None  # 驻场有效截止（epoch）
        self.recovery_task_id: int | None = None  # 当前恢复任务（auth_recovery_api 任务 id）
        self.recovery_started: float | None = None
        self.last_error: str = ""
        self.collections = 0                      # 本次驻场已完成采集次数
        self.last_collection_at: float | None = None

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "session_ok": self.session_ok,
                "heartbeat_last": self.heartbeat_last,
                "heartbeat_fails": self.heartbeat_fails,
                "resident_until": self.resident_until,
                "resident_active": bool(self.resident_until and time.time() < self.resident_until),
                "recovery_task_id": self.recovery_task_id,
                "recovery_active": bool(self.recovery_task_id),
                "last_error": self.last_error,
                "collections": self.collections,
                "last_collection_at": self.last_collection_at,
            }


_STATE = _P0State()
_THREAD: threading.Thread | None = None


# ============ 内部工具 ============
def _identity_allowed(account_name: str) -> bool:
    """身份硬白名单门控：仅允许双子星库 Contract 白名单身份进入采集。"""
    if not account_name:
        return False
    return account_name in ALLOWED_IDENTITY_NAMES and account_name in bridge.ACCOUNT_PROFILES


def _session_healthy() -> bool:
    """一次性健康探测：preflight 通过 + cookie 已配置 + CDP 在线 + 账号校验通过。

    复用 bridge 既有实现（runtime_preflight_check 内部已包含 cookie_configured /
    _check_cdp_online / verify_account 等），不重写采集探活逻辑。
    """
    try:
        pre = bridge.runtime_preflight_check(account=None)
        return bool(pre.get("ok"))
    except Exception as e:  # noqa: BLE001
        _logger.warning("session health probe failed: %s", e)
        return False


def _mark_session_lost(reason: str) -> None:
    with _STATE.lock:
        _STATE.session_ok = False
        _STATE.heartbeat_fails += 1
        _STATE.last_error = reason
    _logger.warning("XHS session lost: %s (fails=%d)",
                    reason, _STATE.heartbeat_fails)


# ============ 扫码恢复（系统内部弹出扫码 → 人工扫码一次） ============
def trigger_scan_recovery() -> dict:
    """Session 失效后由心跳自动调用，或由前端手动触发。

    流程：auth_recovery_api 建任务(二维码生成在 auth_recovery 前端) → start_task
          → 等待人工扫码 → 前端 POST /api/xhs/p0/recovery/complete 关闭本恢复。
    返回：统一状态字典。
    """
    with _STATE.lock:
        if _STATE.recovery_task_id:
            return {"ok": False, "recovery_active": True,
                    "msg": "恢复流程已在进行中，请勿重复触发"}
        _STATE.session_ok = False
        _STATE.recovery_started = time.time()

    try:
        # 直接调用服务层（不依赖 HTTP 请求上下文），避免后台线程调 Flask 视图函数报错
        from auth_recovery_center import recovery_center
        task = recovery_center.create_task(
            platform="xhs",
            issue_type="session_invalid",
            title="小红书 Session 失效，请扫码恢复",
            description="系统检测到小红书 Session 失效，已自动弹出扫码。请使用白名单账号扫码一次完成验证。",
            recovery_url="",
        )
        task_id = task.id if hasattr(task, "id") else getattr(task, "task_id", None)
        if not task_id:
            return {"ok": False, "msg": f"扫码恢复任务创建失败: {task}"}
        # 标记为进行中（等价 auth_recovery_api.start_task）
        recovery_center.mark_in_progress(int(task_id))
        with _STATE.lock:
            _STATE.recovery_task_id = int(task_id)
            _STATE.last_error = "Session 失效，已弹出扫码恢复"
        return {"ok": True, "task_id": int(task_id),
                "msg": "已弹出扫码，请使用白名单账号扫码一次"}
    except Exception as e:  # noqa: BLE001
        with _STATE.lock:
            _STATE.last_error = f"扫码恢复触发异常: {e}"
        _logger.exception("trigger_scan_recovery failed")
        return {"ok": False, "msg": f"扫码恢复触发异常: {e}"}


def complete_scan_recovery(success: bool = True) -> dict:
    """人工扫码后由前端调用（POST /api/xhs/p0/recovery/complete）。

    success=True：关闭恢复任务 → 进入驻场冷却 → 下次心跳重新探测。
    success=False：任务标记失败，保留错误信息。
    """
    with _STATE.lock:
        task_id = _STATE.recovery_task_id
        _STATE.recovery_task_id = None
    if task_id:
        try:
            from auth_recovery_center import recovery_center
            if success:
                recovery_center.mark_completed(int(task_id))
            else:
                recovery_center.mark_failed(int(task_id), error_message="扫码未完成")
        except Exception as e:  # noqa: BLE001
            _logger.warning("finalize recovery task %s failed: %s", task_id, e)
    with _STATE.lock:
        _STATE.heartbeat_fails = 0
        if success:
            _STATE.session_ok = True
            _STATE.resident_until = time.time() + COOLDOWN_AFTER_RECOVERY
            _STATE.last_error = ""
        else:
            _STATE.session_ok = False
            _STATE.resident_until = None  # 驻场不再有效，回到需扫码状态
            _STATE.last_error = "扫码恢复未完成，Session 仍未恢复"
    return {"ok": True, "success": success}


# ============ 采集任务入口（身份白名单 + 复用既有 sync） ============
def trigger_collection(account_name: str | None = None,
                       keywords=None, max_scroll: int = 4) -> dict:
    """有采集任务 → 调用指定身份(硬白名单) → 采集 → 入库 → 主体过滤。

    三层门控（严格优先）：
      1. identity 白名单：account_name ∈ {XHS_CN_PRIMARY, XHS_RETINAUT}
      2. select_account：切换身份（bridge 内部含 cookie 文件存在性校验）
      3. runtime_preflight_check：Session 健康预检
    之后调用 bridge.sync（内部完成采集 → database.insert_note → 主体过滤）。
    """
    # 门控 1：身份硬白名单 + 当前生产边界（仅香港/国际账号）
    account = account_name or bridge.DEFAULT_COLLECTION_ACCOUNT
    if not _identity_allowed(account):
        policy_gate = bridge.collection_policy_gate(account=account, region='intl')
        return {"ok": False,
                "account": account,
                "code": policy_gate.get("code", "account_paused"),
                "collection_policy": policy_gate,
                "msg": f"身份 [{account}] 不在双子星库 Contract 硬白名单中。"
                       f"允许身份: {list(ALLOWED_IDENTITY_NAMES)}"}
    policy_gate = bridge.collection_policy_gate(account=account, region='intl')
    if not policy_gate.get('ok'):
        return {"ok": False, "account": account,
                "code": policy_gate.get('code'),
                "collection_policy": policy_gate,
                "msg": f"[生产采集边界] {policy_gate.get('reason', '当前账号暂不可采集')}"}

    # 门控 2：身份切换
    ok_sel, msg_sel = bridge.select_account(account)
    if not ok_sel:
        return {"ok": False, "msg": f"[身份门控] {msg_sel}"}

    # 门控 3：Session 健康预检（返回 dict，非元组）
    pre = bridge.runtime_preflight_check(account=account)
    ok_pre = bool(pre.get("ok"))
    msg_pre = str(pre.get("evidence") or pre.get("overall_state") or "预检未通过")
    if not ok_pre:
        _mark_session_lost(msg_pre)
        # 用户主动暂停不触发扫码（尊重用户暂停开关，守 AGENTS §7）
        if pre.get("overall_state") == "user_paused":
            return {"ok": False, "msg": f"[Session门控] {msg_pre}（用户已手动暂停）"}
        trigger_scan_recovery()
        return {"ok": False, "msg": f"[Session门控] {msg_pre} → 已触发扫码恢复"}

    # 采集 → 入库（bridge.sync 内部：采集 → database.insert_note → 主体过滤 → 落库）
    try:
        result = bridge.sync(keywords=keywords, max_scroll=max_scroll, account=account)
        with _STATE.lock:
            _STATE.session_ok = True
            _STATE.heartbeat_fails = 0
            _STATE.collections += 1
            _STATE.last_collection_at = time.time()
        return {"ok": True, "account": account,
                "collection_policy": policy_gate, "result": result}
    except Exception as e:  # noqa: BLE001
        _mark_session_lost(f"采集异常: {e}")
        return {"ok": False, "msg": f"采集执行异常: {e}"}


# ============ 长期驻场心跳线程 ============
def _resident_loop() -> None:
    """长期驻场心跳：周期探活 → 连续失败达阈值 → 系统内弹扫码。

    线程化、daemon，随 app 进程生命周期运行。不发外部通知、不破解风控。
    """
    while True:
        try:
            # 用户手动暂停时：心跳只记录状态，不判 Session 失效、不触发扫码（守 AGENTS §7）
            try:
                from xhs_cookie_bridge import is_user_paused
                if is_user_paused():
                    with _STATE.lock:
                        _STATE.session_ok = False
                        _STATE.heartbeat_fails = 0
                        _STATE.heartbeat_last = time.time()
                        _STATE.last_error = "用户手动暂停采集（不触发扫码恢复）"
                    time.sleep(HEARTBEAT_INTERVAL)
                    continue
            except Exception:
                pass  # 暂停状态不可用时继续常规探活

            healthy = _session_healthy()
            if healthy:
                with _STATE.lock:
                    _STATE.session_ok = True
                    _STATE.heartbeat_fails = 0
                    _STATE.heartbeat_last = time.time()
                    _STATE.last_error = ""
            else:
                _mark_session_lost("心跳探活失败")
                # 连续失败达阈值 → 触发扫码恢复（若尚未在恢复中）
                if (_STATE.heartbeat_fails >= SESSION_FAIL_THRESHOLD
                        and not _STATE.recovery_task_id):
                    trigger_scan_recovery()
        except Exception as e:  # noqa: BLE001
            _logger.exception("resident heartbeat error: %s", e)
        time.sleep(HEARTBEAT_INTERVAL)


def get_status() -> dict:
    """前端轮询状态聚合（GET /api/xhs/p0/status）。"""
    snap = _STATE.snapshot()
    snap["allowed_identities"] = list(ALLOWED_IDENTITY_NAMES)
    snap["heartbeat_interval"] = HEARTBEAT_INTERVAL
    snap["fail_threshold"] = SESSION_FAIL_THRESHOLD
    # 用户手动暂停是主动状态，与 Session 失效区分（守 AGENTS §7）
    try:
        from xhs_cookie_bridge import is_user_paused
        paused = is_user_paused()
        snap["user_paused"] = bool(paused)
    except Exception:
        snap["user_paused"] = False
    # 驻场模式描述（供前端展示）
    now = time.time()
    in_cooldown = bool(snap["resident_until"] and now < snap["resident_until"])
    # 心跳新鲜度：最近一次成功心跳在 2 个周期内视为驻场存活
    hb_fresh = bool(snap["heartbeat_last"] and (now - snap["heartbeat_last"]) < HEARTBEAT_INTERVAL * 2)
    if snap["user_paused"]:
        snap["resident_mode"] = "USER_PAUSED"
    elif in_cooldown or (snap["session_ok"] is True and hb_fresh):
        # Session 有效且心跳存活 → 直接驻场（P0：有效即驻场，无需扫码）
        snap["resident_mode"] = "RESIDENT_ACTIVE"
    elif snap["session_ok"] is False:
        snap["resident_mode"] = "NEED_SCAN_RECOVERY"
    elif snap["session_ok"] is None:
        snap["resident_mode"] = "PROBING"
    else:
        snap["resident_mode"] = "IDLE"
    return snap


def start_resident() -> None:
    """启动长期驻场心跳线程（幂等）。app 启动时调用一次。"""
    global _THREAD
    with _STATE.lock:
        if _THREAD is not None and _THREAD.is_alive():
            return
        _THREAD = threading.Thread(target=_resident_loop, daemon=True,
                                   name="xhs-p0-resident")
        _THREAD.start()
    _logger.info("XHS P0 resident heartbeat started (interval=%.0fs, threshold=%d)",
                 HEARTBEAT_INTERVAL, SESSION_FAIL_THRESHOLD)


# ============ 自检（python xhs_p0_orchestrator.py --selfcheck） ============
def _selfcheck() -> None:
    print("== XHS P0 Orchestrator selfcheck ==")
    print(f"allowed identities: {ALLOWED_IDENTITY_NAMES}")
    print(f"ACCOUNT_PROFILES keys: {list(bridge.ACCOUNT_PROFILES.keys())}")
    print(f"allow XHS_CN_PRIMARY -> {_identity_allowed(bridge.XHS_CN_PRIMARY_NAME)}")
    print(f"allow XHS_RETINAUT  -> {_identity_allowed(bridge.XHS_RETINAUT_NAME)}")
    print(f"allow evil_identity -> {_identity_allowed('evil_identity')}")
    # 白名单拒绝测试：非白名单身份必须被拒
    assert not _identity_allowed("evil_identity"), "FAIL: evil identity must be rejected"
    assert not _identity_allowed(bridge.XHS_CN_PRIMARY_NAME), "FAIL: mainland identity must be paused"
    assert _identity_allowed(bridge.XHS_RETINAUT_NAME), "FAIL: HK identity must be allowed"
    print("whitelist gate: PASS")
    print("selfcheck OK")


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        print("XHS P0 Orchestrator — 由 app.py 启动时调用 start_resident()")
        print("自检: python xhs_p0_orchestrator.py --selfcheck")
