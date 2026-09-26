"""
采集器自动化模块 - 广州太古汇舆情监测系统 v5.8.0
实现自动启动→采集→自动关闭的完整流程
"""
# 采集生产主链固定使用香港/国际账号；大陆身份只保留诊断能力，不进入采集。
try:
    from dual_account_rotation import select_account_for_collection, record_collection_result, get_rotation_status
    DUAL_ACCOUNT_ENABLED = True
except ImportError:
    DUAL_ACCOUNT_ENABLED = False

import os
import sys
import time
import json
import subprocess
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum


class CollectorLifecycleState(Enum):
    """采集器生命周期七态状态机（ZBC Track 2 审计要求）。

    禁止"进程活着但实际停止采集"：每次状态转换必须显式记录，
    DEGRADED 表示采集在跑但部分通道/关键词失败，不是假运行。
    """
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"
    RECOVERING = "recovering"

    @classmethod
    def can_transition(cls, from_state, to_state):
        """检查状态转换是否合法。_VALID_TRANSITIONS 定义在模块级避免被 Enum 收编。"""
        if not isinstance(from_state, cls):
            try:
                from_state = cls(str(from_state).lower())
            except ValueError:
                return False
        if not isinstance(to_state, cls):
            try:
                to_state = cls(str(to_state).lower())
            except ValueError:
                return False
        return to_state in _VALID_TRANSITIONS.get(from_state, set())


# 合法状态转换表（模块级，避免被 Enum 元类收编为成员）
_VALID_TRANSITIONS = {
    CollectorLifecycleState.STARTING: {
        CollectorLifecycleState.RUNNING, CollectorLifecycleState.DEGRADED,
        CollectorLifecycleState.FAILED, CollectorLifecycleState.STOPPING,
    },
    CollectorLifecycleState.RUNNING: {
        CollectorLifecycleState.DEGRADED, CollectorLifecycleState.FAILED,
        CollectorLifecycleState.STOPPING, CollectorLifecycleState.RECOVERING,
    },
    CollectorLifecycleState.DEGRADED: {
        CollectorLifecycleState.RUNNING, CollectorLifecycleState.FAILED,
        CollectorLifecycleState.STOPPING, CollectorLifecycleState.RECOVERING,
    },
    CollectorLifecycleState.FAILED: {
        CollectorLifecycleState.RECOVERING, CollectorLifecycleState.STOPPING,
        CollectorLifecycleState.STOPPED,
    },
    CollectorLifecycleState.STOPPING: {CollectorLifecycleState.STOPPED},
    CollectorLifecycleState.STOPPED: {CollectorLifecycleState.STARTING},
    CollectorLifecycleState.RECOVERING: {
        CollectorLifecycleState.RUNNING, CollectorLifecycleState.DEGRADED,
        CollectorLifecycleState.FAILED, CollectorLifecycleState.STOPPING,
    },
}


# Runtime Guardian 统一生命周期守护（ZBC-PHASE2-RUNTIME-GUARDIAN Shard B）
# 旁路接入：import 失败不阻断采集主链路
try:
    import runtime_guardian as _runtime_guardian
    _RG_AVAILABLE = True
except Exception as _rg_import_err:
    _runtime_guardian = None
    _RG_AVAILABLE = False
    logging.getLogger(__name__).warning('Runtime Guardian 不可用(旁路模式): %s', _rg_import_err)

# 统一 Node 解析（PATH 优先，项目内置 nodejs/ 兜底），避免常驻进程 PATH 缺 node 抛 WinError 2
try:
    from runtime_bin import resolve_node as _resolve_node
    _NODE_BIN = _resolve_node() or 'node'
except Exception:
    _NODE_BIN = 'node'

# 配置日志
logger = logging.getLogger(__name__)

class CollectorAutomation:
    """采集器自动化控制器"""
    
    def __init__(self, base_dir=None):
        # 本文件就在项目根目录，只上溯一级；此前多上溯一级误指向 D:\，导致 cjs/profile/data 路径全部错位
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.cdp_port = 9223
        self._task_cdp_port = 9223  # 当前任务实际驻场端口（香港/国际 RedNote）
        self.edge_path = self._find_edge_browser()
        self.is_running = False
        self.current_task = None
        self.task_history = []
        self._lock = threading.Lock()
        # 精确管理本采集器自己启动的浏览器实例（独立 user-data-dir），避免误杀用户日常 Edge
        self.browser_process = None
        self._cdp_profile_dir = None
        # 冷却控制：手动一键 20min/冷却1h、自动 30min/冷却1h；force=True 可跳过（测试期）
        self._last_finish_at = {}   # {'manual': ts, 'auto': ts}
        self.cooldown_seconds = 3600

        # ── Runtime Guardian 生命周期守护（旁路接入，不影响原链路）──
        self._guardian = None
        self._worker_id = None
        self._lease_owner = None
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None
        self._task_start_ts = None
        self._stop_event = threading.Event()  # 优雅关闭信号
        self._collection_thread = None  # 采集后台线程引用（stop 时可 join 等待）
        self._lifecycle_state = CollectorLifecycleState.STOPPED
        # 单次采集任务最大时长（秒），超时由心跳线程标记 worker FAILED；默认 40min
        self._max_task_duration = float(os.getenv('COLLECTOR_MAX_TASK_SECONDS', '2400'))

        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        # 加载历史记录
        self._load_history()
    
    def _find_edge_browser(self):
        """查找Edge浏览器路径"""
        possible_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 尝试通过where命令查找
        try:
            result = subprocess.run(['where', 'msedge'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0].strip()
        except Exception:
            pass
        
        return None
    
    def _get_cdp_profile_dir(self, account='default'):
        """获取CDP配置目录（双子星库 Contract 对齐：优先 xhs_cookie_bridge.ACCOUNT_PROFILES）。

        优先级：
          1) account ∈ 双子星库 Contract 白名单 → 用 ACCOUNT_PROFILES[account][1]（与 select_account 一致）
          2) 否则：兼容 legacy 映射（default/new/newaccount），保留历史行为，不破坏外部调用。
        """
        # ── 双子星库 Contract：优先读取 xhs_cookie_bridge 的身份定义（与 xhs_cookie_bridge.select_account 同源）──
        try:
            import xhs_cookie_bridge as _xcb
            if account in (None, '', 'default'):
                account = _xcb.DEFAULT_COLLECTION_ACCOUNT
            contract_profiles = getattr(_xcb, 'ACCOUNT_PROFILES', None) or {}
            if account in contract_profiles:
                # ACCOUNT_PROFILES[name] = (cookie_path, cdp_profile_dir)
                _, profile_dir = contract_profiles[account]
                if profile_dir:
                    # 允许 profile_dir 是相对路径（基于项目根目录）→ 拼接成绝对
                    if not os.path.isabs(profile_dir):
                        profile_dir = os.path.join(self.base_dir, profile_dir)
                    os.makedirs(profile_dir, exist_ok=True)
                    return profile_dir
        except Exception:
            pass  # 导入失败时降级 legacy，不阻塞
        # ── Legacy 兼容映射（保持向后不变）──
        profile_map = {
            'default': 'edge-cdp-profile',
            'new': 'edge-cdp-profile-new',
            'newaccount': 'edge-cdp-newaccount',
        }
        profile_name = profile_map.get(account, 'edge-cdp-profile')
        profile_dir = os.path.join(self.base_dir, profile_name)
        os.makedirs(profile_dir, exist_ok=True)
        return profile_dir
    
    def _port_for(self, account=None):
        """按逻辑身份解析驻场 CDP 端口（委托 xhs_cookie_bridge 单一事实源；异常回退默认 9223）。"""
        try:
            import xhs_cookie_bridge as _xcb
            _a = None if account in (None, '', 'default') else account
            return int(_xcb.cdp_port_for(_a))
        except Exception:
            return self.cdp_port

    def start_browser(self, account='default', headless=False):
        """启动Edge浏览器（CDP模式：按账号选独立驻场端口/profile；端口已在线则直接附着复用）"""
        if not self.edge_path:
            raise RuntimeError("未找到Edge浏览器，请先安装Microsoft Edge")
        
        # 检查浏览器是否已经在运行
        port = self._port_for(account)
        self._task_cdp_port = port
        if self._is_browser_running(port):
            logger.info(f"驻场浏览器已在线（port={port}），直接附着复用，不重复启动、不关闭驻场窗口")
            return True
        
        profile_dir = self._get_cdp_profile_dir(account)
        
        # 构建启动参数
        args = [
            self.edge_path,
            f'--remote-debugging-port={port}',
            f'--user-data-dir={profile_dir}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-popup-blocking',
            '--disable-extensions',
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--disable-background-networking',
            '--disable-component-update',
            '--remote-allow-origins=*',
            # 大陆 9222 强制直连（不跟随系统代理，保证国内站稳定）；香港 9223 继承系统/海外代理
            *(['--no-proxy-server'] if port == self.cdp_port else []),
            # 起始页固定 about:blank：避免默认 MSN 新标签页的 service-worker/worker target，
            # 那会让 Playwright connect_over_cdp 在枚举 target 时握手挂起（ws 已连却 30s 超时）。
            'about:blank',
        ]

        if headless:
            args.append('--headless=new')
        
        try:
            # 启动浏览器
            process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            # 记录句柄，关闭时只终止本采集器启动的独立实例，绝不 taskkill 全部 msedge
            self.browser_process = process
            self._cdp_profile_dir = profile_dir

            logger.info(f"Edge浏览器已启动，PID: {process.pid} (port={port}, profile={os.path.basename(profile_dir)})")
            
            # 等待CDP端口就绪
            if self._wait_for_cdp_ready(timeout=30, port=port):
                logger.info("CDP调试端口已就绪")
                return True
            else:
                logger.warning("CDP调试端口未就绪，但浏览器已启动")
                return True
                
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            raise
    
    def _is_browser_running(self, port=None):
        """检查浏览器是否在运行（可指定端口；默认用当前任务驻场端口）"""
        try:
            import urllib.request
            _p = port or self._task_cdp_port or self.cdp_port
            response = urllib.request.urlopen(f'http://127.0.0.1:{_p}/json/version', timeout=3)
            return response.status == 200
        except Exception:
            return False
    
    def _wait_for_cdp_ready(self, timeout=30, port=None):
        """等待CDP端口就绪"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_browser_running(port):
                return True
            time.sleep(1)
        return False
    
    def stop_browser(self):
        """关闭本采集器启动的浏览器实例（只关自己的独立 profile 进程树，不影响用户日常 Edge）"""
        killed = False
        try:
            proc = self.browser_process
            if proc is not None and proc.poll() is None:
                pid = proc.pid
                try:
                    if sys.platform == 'win32':
                        # /T 连同该实例派生的子进程一起结束；因使用独立 --user-data-dir，与用户日常 Edge 互不影响
                        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                                       capture_output=True, timeout=15)
                    else:
                        proc.terminate()
                        try:
                            proc.wait(timeout=8)
                        except Exception:
                            proc.kill()
                    killed = True
                    logger.info(f"已精确关闭采集浏览器进程树 PID={pid}")
                except Exception as e:
                    logger.warning(f"按PID关闭浏览器失败: {e}")
            # CDP 兜底探测：仅当仍可连接时记录，不做 /IM msedge 全量强杀（避免误关用户窗口）
            try:
                if self._is_browser_running():
                    logger.warning("CDP 端口仍可连接，但已无受控进程句柄；保留用户浏览器，不做全量 taskkill")
            except Exception:
                pass
            self.browser_process = None
            time.sleep(1)
            return True if (killed or proc is not None) else False

        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
            self.browser_process = None
            return False
    
    # ------------------------------------------------------------------
    # Runtime Guardian 生命周期守护方法（旁路接入）
    # ------------------------------------------------------------------
    def transition_state(self, new_state, reason=""):
        """显式状态转换：校验合法性并记录，禁止"进程活着但实际停止采集"。"""
        if not isinstance(new_state, CollectorLifecycleState):
            try:
                new_state = CollectorLifecycleState(str(new_state).lower())
            except ValueError:
                logger.warning('未知采集器状态: %s', new_state)
                return False
        old = self._lifecycle_state
        if not CollectorLifecycleState.can_transition(old, new_state):
            logger.warning('非法状态转换: %s -> %s (reason=%s)', old.value, new_state.value, reason)
            # 仍允许转换但记录警告（避免阻断主流程），但 STOPPING/STOPPED 是终态必须尊重
            if old in (CollectorLifecycleState.STOPPING, CollectorLifecycleState.STOPPED):
                return False
        self._lifecycle_state = new_state
        if self.current_task:
            self.current_task['lifecycle_state'] = new_state.value
            if reason:
                self.current_task['state_reason'] = reason
        logger.info('采集器状态转换: %s -> %s%s', old.value, new_state.value,
                    f' ({reason})' if reason else '')
        return True

    def _get_guardian(self):
        """懒加载 Runtime Guardian 单例；不可用时返回 None（旁路模式）。"""
        if not _RG_AVAILABLE:
            return None
        if self._guardian is None:
            try:
                self._guardian = _runtime_guardian.get_guardian('collector_automation')
            except Exception as _e:
                logger.warning('Runtime Guardian 初始化失败(旁路): %s', _e)
                self._guardian = None
        return self._guardian

    def _start_heartbeat(self, worker_id):
        """启动后台心跳线程：每 10s 发送心跳 + 续期租约 + 检测任务超时。"""
        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, args=(worker_id,),
            daemon=True, name='collector-heartbeat',
        )
        self._heartbeat_thread.start()
        logger.debug('心跳线程已启动 worker=%s', worker_id)

    def _heartbeat_loop(self, worker_id):
        """心跳主循环：每10s发送心跳+续期租约；每秒检测任务超时。"""
        _hb_interval = 10.0
        _tick = 0.0
        while not self._heartbeat_stop.is_set():
            try:
                g = self._get_guardian()
                if g:
                    # 每 _hb_interval 秒发送心跳+续期租约
                    if _tick <= 0:
                        g.heartbeat(worker_id)
                        if self.current_task:
                            self.current_task['last_heartbeat_at'] = datetime.now().isoformat()
                        if self._lease_owner:
                            g.renew_lease(worker_id, self._lease_owner, ttl_seconds=120)
                        _tick = _hb_interval
                    # 每秒检测任务超时：超过 _max_task_duration 标记 FAILED
                    if self._task_start_ts:
                        elapsed = time.time() - self._task_start_ts
                        if elapsed > self._max_task_duration:
                            logger.warning(
                                '采集任务超时 (%.0fs > %.0fs)，标记 worker FAILED',
                                elapsed, self._max_task_duration,
                            )
                            g.update_worker_status(
                                worker_id, _runtime_guardian.WorkerStatus.FAILED,
                                reason=f'task_timeout_{elapsed:.0f}s',
                            )
            except Exception as _hb_err:
                logger.debug('心跳循环异常(忽略): %s', _hb_err)
            # 1秒粒度睡眠，stop 时快速退出
            self._heartbeat_stop.wait(1.0)
            _tick -= 1.0

    def _stop_heartbeat(self):
        """停止心跳线程。"""
        self._heartbeat_stop.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        self._heartbeat_thread = None

    def _rg_cleanup(self, task):
        """采集结束时统一清理 Runtime Guardian 资源：停心跳、释放租约、更新 worker 状态。"""
        self._stop_heartbeat()
        wid = self._worker_id
        if wid:
            try:
                g = self._get_guardian()
                if g:
                    if self._lease_owner:
                        g.release_lease(wid, self._lease_owner)
                    final_status = (
                        _runtime_guardian.WorkerStatus.STOPPED
                        if task.get('status') == 'completed'
                        else _runtime_guardian.WorkerStatus.FAILED
                    )
                    g.update_worker_status(wid, final_status, reason=str(task.get('status', '')))
                    logger.info('Runtime Guardian: worker %s 已清理 status=%s', wid, final_status.value)
            except Exception as _clean_err:
                logger.warning('Runtime Guardian 清理失败(不影响主流程): %s', _clean_err)
        self._worker_id = None
        self._lease_owner = None
        self._task_start_ts = None

    def start_collection(self, keywords=None, mode='manual', account='default', force=False):
        """启动采集任务。force=True 跳过 1 小时冷却（测试期使用）。

        双子星库 Contract 门控：采集前调用 xhs_cookie_bridge.runtime_preflight_check()。
        - account 传 'default' 时：解析为香港/国际 XHS_RETINAUT。
        - account ∈ {XHS_CN_PRIMARY_NAME, XHS_RETINAUT_NAME}：按 Contract 白名单切换；不在白名单直接拒绝。
        - 任何预检失败（熔断/无Cookie/白名单/冷却/暂停）→ 如实返回错误，绝不静默启动空跑。
        """
        manual_modes = {'quick', 'manual'}
        auto_modes = {'standard', 'auto', 'deep'}
        if not isinstance(mode, str) or mode not in manual_modes | auto_modes:
            return {'ok': False, 'status': 'ERROR', 'code': 'INVALID_COLLECTION_MODE',
                    'error': 'Unsupported collection mode'}
        if mode in auto_modes:
            try:
                from lumenis.system.collector.adapters.rednote_policy import automatic_collection_opt_in_enabled
                auto_enabled = automatic_collection_opt_in_enabled()
            except Exception:
                auto_enabled = False
            if not auto_enabled:
                return {'ok': False, 'status': 'BLOCKED',
                        'code': 'AUTO_COLLECTION_OPT_IN_REQUIRED',
                        'error': 'Automatic collection requires explicit authorized scope, source and cadence'}

        with self._lock:
            if self.is_running:
                logger.warning("采集任务已在运行中")
                return {'ok': False, 'error': '采集任务已在运行中'}

            # ── 双子星库 Contract 预检（在所有调度逻辑之前，fail-fast）──
            pre_ok, pre_msg, pre_detail = True, '', {}
            try:
                import xhs_cookie_bridge as _xcb
                # 归一化：'default' 明确解析为当前唯一生产采集账号
                _account_for_check = account
                if _account_for_check in (None, '', 'default'):
                    _account_for_check = _xcb.DEFAULT_COLLECTION_ACCOUNT
                policy_gate = _xcb.collection_policy_gate(account=_account_for_check, region='intl')
                if not policy_gate.get('ok'):
                    pre_ok = False
                    pre_msg = f'[采集策略门禁] {policy_gate.get("reason", "当前账号/区域不允许生产采集")}'
                    pre_detail = {'overall_state': policy_gate.get('code'),
                                  'collection_policy': policy_gate}
                    return {'ok': False, 'error': pre_msg, 'preflight': pre_detail}
                # force=True 预检仍跑（保留真实报告），但只在严重 P0 阻断（身份/白名单/熔断）时才拦截
                # 生产采集固定使用香港/国际端口；不接受全局环境中的大陆端口覆盖。
                _configured_cdp = os.getenv('XHS_CDP_URL')
                if _configured_cdp and not _configured_cdp.rstrip('/').endswith(':9223'):
                    pre_ok = False
                    pre_msg = '[采集策略门禁] XHS_CDP_URL 不是香港/国际 9223，拒绝启动采集'
                    pre_detail = {'overall_state': 'cdp_port_not_allowed',
                                  'collection_policy': policy_gate}
                    return {'ok': False, 'error': pre_msg, 'preflight': pre_detail}
                _cdp_url = _configured_cdp or _xcb.cdp_url_for(_account_for_check)
                preflight = _xcb.runtime_preflight_check(account=_account_for_check,
                                                          cdp_url=_cdp_url,
                                                          quick=False)
                pre_detail = {'overall_state': preflight.get('overall_state'),
                              'evidence': preflight.get('evidence'),
                              'active_account': preflight.get('active_account'),
                              'checks_fail_count': sum(1 for c in preflight.get('checks', []) if c.get('status') == 'fail')}
                if not preflight.get('ok'):
                    ov = str(preflight.get('overall_state', ''))
                    # force=True 允许旁路 cooldown / rate_limit（用于测试 & 紧急）；但 P0 严重项仍然阻断
                    p0_blocker = ov in ('need_account', 'no_cookie', 'not_in_whitelist', 'blocked',
                                        'user_paused', 'account_paused', 'region_paused',
                                        'policy_unavailable', 'policy_error', 'cdp_port_not_allowed')
                    if p0_blocker or not force:
                        pre_ok = False
                        pre_msg = f'[采集预检未通过·状态={ov}] {preflight.get("evidence","")}'
            except Exception as _pe:
                # import 或预检异常视为失败（防止异常时静默启动）
                pre_ok = False
                pre_msg = f'[采集预检异常] {type(_pe).__name__}: {str(_pe)}'
                pre_detail = {'exception': pre_msg}
            if not pre_ok:
                logger.warning(pre_msg)
                return {'ok': False, 'error': pre_msg, 'preflight': pre_detail}

            # 配置采集参数
            if keywords is None:
                keywords = ['广州太古汇', '太古汇', '广州太古汇 舆情']
            
            # 采集参数（按用户设定：手动一键20min/冷却1h、自动定时30min/冷却1h，边采边入库）
            mode_config = {
                'quick':    {'duration': 1200, 'max_pages': 20, 'interval': 3},   # 手动一键更新 = 20 分钟
                'manual':   {'duration': 1200, 'max_pages': 20, 'interval': 3},
                'standard': {'duration': 1800, 'max_pages': 40, 'interval': 3},   # 自动定时 = 30 分钟
                'auto':     {'duration': 1800, 'max_pages': 40, 'interval': 3},
                'deep':     {'duration': 1800, 'max_pages': 60, 'interval': 5},
            }
            # 冷却校验：同一触发类型 1 小时内不重复（force=True 测试期可跳过）
            trigger_type = 'manual' if mode in ('quick', 'manual') else 'auto'
            if not force:
                last = self._last_finish_at.get(trigger_type)
                if last is not None:
                    elapsed = (datetime.now() - last).total_seconds()
                    if elapsed < self.cooldown_seconds:
                        wait_min = round((self.cooldown_seconds - elapsed) / 60)
                        return {'ok': False, 'error': f'采集冷却中，{trigger_type} 采集需间隔 1 小时，约还需 {wait_min} 分钟（测试期可 force 跳过）',
                                'cooldown_remain': int(self.cooldown_seconds - elapsed)}
            
            config = mode_config[mode]
            
            import uuid as _uuid_for_domain
            _task_id = f'collect_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            _trace_id = _uuid_for_domain.uuid4().hex[:16]
            # 双域核心：采集任务默认 CTH 域（广州太古汇生产采集），
            # 可通过环境变量 ZBC_COLLECTOR_DOMAIN 覆盖为 zbmp
            _collector_domain = os.environ.get('ZBC_COLLECTOR_DOMAIN', 'cth')
            _collector_product = 'CTH' if _collector_domain == 'cth' else 'ZBMP'
            self.current_task = {
                'id': _task_id,
                'task_id': _task_id,
                'trace_id': _trace_id,
                'domain_id': _collector_domain,
                'product_id': _collector_product,
                'collector_id': 'xhs_collector_automation',
                'source_id': 'xiaohongshu',
                'keywords': keywords,
                'mode': mode,
                'account': _account_for_check,
                'trigger_type': trigger_type,
                'config': config,
                'status': 'starting',
                'start_time': datetime.now().isoformat(),
                'started_at': datetime.now().isoformat(),
                'last_heartbeat_at': None,
                'last_success_at': None,
                'finished_at': None,
                'retry_count': 0,
                'progress': 0,
                'new_notes': 0,
                'errors': [],
            }
            
            self.is_running = True
            self._stop_event.clear()
            self.transition_state(CollectorLifecycleState.STARTING, reason='task_started')

            # ── Runtime Guardian: 注册 worker + 获取租约（旁路，失败不阻断）──
            try:
                g = self._get_guardian()
                if g:
                    self._worker_id = g.register_worker(
                        f'xhs_collector_{self.current_task["id"]}',
                        metadata={
                            'mode': mode, 'account': account, 'keywords': keywords,
                            'task_id': self.current_task.get('task_id'),
                            'trace_id': self.current_task.get('trace_id'),
                        },
                        domain_id=self.current_task.get('domain_id', 'cth'),
                        product_id=self.current_task.get('product_id', 'CTH'),
                    )
                    self._lease_owner = f'pid-{os.getpid()}'
                    lease = g.acquire_lease(self._worker_id, self._lease_owner, ttl_seconds=120)
                    g.heartbeat(self._worker_id, domain_id=self.current_task.get('domain_id', 'cth'))
                    self.current_task['worker_id'] = self._worker_id
                    logger.info('Runtime Guardian: worker %s 已注册并获取租约', self._worker_id)
            except Exception as _rg_err:
                logger.warning('Runtime Guardian 接入失败(不阻断采集): %s', _rg_err)
                self._worker_id = None
                self._lease_owner = None

            # 在后台线程中执行采集
            thread = threading.Thread(target=self._run_collection, args=(self.current_task,), daemon=True)
            self._collection_thread = thread
            thread.start()
            
            logger.info(f"采集任务已启动: {self.current_task['id']}")
            
            return {
                'ok': True,
                'task_id': self.current_task['id'],
                'status': 'started',
                'message': f'采集任务已启动，模式: {mode}',
            }
    
    def _run_collection(self, task):
        """执行采集任务（后台线程）"""
        # Runtime Guardian: 启动心跳 + 记录任务开始时间（超时检测基准）
        self._task_start_ts = time.time()
        if self._worker_id:
            self._start_heartbeat(self._worker_id)
        try:
            task['status'] = 'starting_browser'
            logger.info(f"任务 {task['id']}: 启动浏览器...")

            # 启动浏览器
            self.start_browser(account=task['account'])
            time.sleep(3)

            # 优雅关闭：启动浏览器后检查停止信号
            if self._stop_event.is_set():
                logger.info(f"任务 {task['id']}: 收到停止信号，取消采集")
                task['status'] = 'cancelled'
                task['finished_at'] = datetime.now().isoformat()
                self.transition_state(CollectorLifecycleState.STOPPING, reason='cancelled')
                self.transition_state(CollectorLifecycleState.STOPPED, reason='cancelled')
                return

            task['status'] = 'collecting'
            self.transition_state(CollectorLifecycleState.RUNNING, reason='collecting')
            logger.info(f"任务 {task['id']}: 开始采集...")
            
            # 执行采集（调用现有的采集模块）
            new_notes = self._execute_collection(task)
            task['new_notes'] = new_notes
            task['progress'] = 100
            
            task['status'] = 'completed'
            task['end_time'] = datetime.now().isoformat()
            task['finished_at'] = datetime.now().isoformat()
            task['last_success_at'] = datetime.now().isoformat()
            # 合法状态转换：RUNNING -> STOPPING -> STOPPED（禁止 RUNNING 直跳 STOPPED）
            self.transition_state(CollectorLifecycleState.STOPPING, reason='completed')
            self.transition_state(CollectorLifecycleState.STOPPED, reason='completed')
            logger.info(f"任务 {task['id']}: 采集完成，新增 {new_notes} 条笔记")
            # Runtime Guardian: 保存完成检查点（可恢复/可审计）
            try:
                g = self._get_guardian()
                if g and self._worker_id:
                    g.save_checkpoint(
                        run_id=task['id'], worker_id=self._worker_id,
                        position=f'completed notes={new_notes}',
                        state='completed',
                        metadata={'new_notes': new_notes, 'mode': task.get('mode')},
                    )
            except Exception as _cp_err:
                logger.warning('Checkpoint 保存失败(不影响主流程): %s', _cp_err)
            # Evidence：采集成功落证据（禁止只存状态不存证据）
            try:
                from lumenis.shared.evidence.store import record_collection_evidence
                _detail = task.get('collect_detail', {}) or {}
                _start = datetime.fromisoformat(task['start_time'])
                _dur = int((datetime.now() - _start).total_seconds() * 1000)
                record_collection_evidence(
                    account=task.get('account', '') or 'unknown',
                    platform='xhs',
                    notes_collected=int(_detail.get('raw_unique', new_notes) or 0),
                    notes_filtered=int(_detail.get('rejected', 0) or 0),
                    notes_inserted=int(_detail.get('inserted', new_notes) or 0),
                    notes_updated=int(_detail.get('updated', 0) or 0),
                    duration_ms=_dur,
                    result='PASS',
                    session_state='logged_in',
                    keywords=task.get('keywords', []),
                    started_at=task.get('start_time', ''),
                )
            except Exception as _ev_e:
                logger.error(f"任务 {task['id']}: Evidence 写入失败(不影响主流程): {_ev_e}")

            
        except Exception as e:
            task['status'] = 'failed'
            self.transition_state(CollectorLifecycleState.FAILED, reason=str(e)[:200])
            task['errors'].append(str(e))
            task['end_time'] = datetime.now().isoformat()
            task['finished_at'] = datetime.now().isoformat()
            logger.error(f"任务 {task['id']}: 采集失败: {e}", exc_info=True)
            # Evidence：采集失败必留证据链（异常类型+消息，禁止以0条充当结果）
            try:
                from lumenis.shared.evidence.store import record_collection_evidence
                _start = datetime.fromisoformat(task['start_time'])
                _dur = int((datetime.now() - _start).total_seconds() * 1000)
                _err_str = str(e)
                if any(k in _err_str for k in ['验证码', '人机验证', '风控', '安全拦截']):
                    _err_type = 'CAPTCHA'
                elif any(k in _err_str.upper() for k in ['AUTH', 'LOGIN', 'COOKIE']) or '登录' in _err_str:
                    _err_type = 'AUTH_FAILED'
                elif '网络' in _err_str or '超时' in _err_str or 'timeout' in _err_str.lower():
                    _err_type = 'NETWORK_ERROR'
                else:
                    _err_type = 'COLLECTION_ERROR'
                record_collection_evidence(
                    account=task.get('account', '') or 'unknown',
                    platform='xhs',
                    notes_collected=0, notes_filtered=0, notes_inserted=0, notes_updated=0,
                    duration_ms=_dur,
                    result='FAIL',
                    error_type=_err_type,
                    error_message=_err_str[:500],
                    session_state='unknown',
                    keywords=task.get('keywords', []),
                    started_at=task.get('start_time', ''),
                )
            except Exception as _ev_e:
                logger.error(f"任务 {task['id']}: Evidence 写入失败(不影响主流程): {_ev_e}")

        finally:
            # 自动关闭浏览器
            logger.info(f"任务 {task['id']}: 自动关闭浏览器...")
            try:
                self.stop_browser()
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")

            # Runtime Guardian: 统一清理（停心跳、释放租约、更新 worker 状态）
            self._rg_cleanup(task)

            # 保存历史记录
            self._save_history(task)
            # 记录本次结束时间，作为 1 小时冷却起点
            self._last_finish_at[task.get('trigger_type', 'auto')] = datetime.now()
            self.is_running = False
            self.current_task = None
    
    def _execute_collection(self, task):
        """执行实际的采集逻辑（必须真实入库，不再静默 sleep 模拟空跑）。

        重试策略：网络/超时类错误最多重试 2 次（指数退避 2s/4s）；
        风控/登录/验证码类错误不重试（立即上报，避免硬撞风控）。
        """
        max_retries = 2
        attempt = 0
        last_error = None
        while attempt <= max_retries:
            if self._stop_event.is_set():
                logger.info('采集被停止信号中断（attempt=%d）', attempt)
                raise RuntimeError('采集被用户停止信号中断')
            try:
                result = self._execute_collection_once(task)
                if attempt > 0:
                    logger.info('采集重试成功（attempt=%d）', attempt)
                return result
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                # 风控/登录/验证码类错误不重试（立即上报）
                is_risk_error = any(k in err_str for k in [
                    '验证码', '人机验证', '风控', '安全拦截', '安全验证',
                    '登录', 'auth', 'cookie', 'blocked', 'captcha',
                    '未找到可用的真实采集模块', '被用户停止信号中断',
                ])
                if is_risk_error or attempt >= max_retries:
                    logger.error('采集失败（不重试/已达最大重试次数 attempt=%d）: %s', attempt, e)
                    raise
                # 网络/超时类错误：指数退避后重试
                task['retry_count'] = attempt + 1
                backoff = 2 ** attempt  # 2s, 4s
                logger.warning('采集遇瞬时错误，%ds 后重试（attempt=%d/%d）: %s',
                               backoff, attempt + 1, max_retries, str(e)[:120])
                # 退避期间可被停止信号中断
                if self._stop_event.wait(timeout=backoff):
                    logger.info('退避期间收到停止信号，中断重试')
                    raise RuntimeError('采集被用户停止信号中断')
                attempt += 1
        # 理论上不会到达这里（循环内已 raise），兜底
        raise last_error or RuntimeError('采集执行失败（未知错误）')

    def _execute_collection_once(self, task):
        """单次采集执行（被 _execute_collection 的重试循环调用）。"""
        try:
            # 尝试导入并使用现有的采集模块
            sys.path.insert(0, self.base_dir)
            cfg = task['config']
            # 页数 → 搜索结果滚动次数（每次滚动约加载一批笔记）
            max_scroll = max(4, min(12, int(cfg.get('max_pages', 20)) // 4))

            # 1) 首选 xhs_cookie_bridge.sync：真实搜索→主体过滤→insert_note 入库→异步AI/事件聚合
            try:
                import xhs_cookie_bridge
                if hasattr(xhs_cookie_bridge, 'sync'):
                    if not xhs_cookie_bridge.cookie_configured():
                        raise RuntimeError('XHS Cookie 未配置：请在 data/private/xhs_cookie_header.txt 配置，或使用已登录的 CDP profile')
                    result = xhs_cookie_bridge.sync(
                        keywords=task['keywords'], max_scroll=max_scroll,
                        account=task.get('account') or xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT,
                    )
                    ins = int(result.get('inserted', 0)); upd = int(result.get('updated', 0))
                    task['collect_detail'] = {'inserted': ins, 'updated': upd,
                                             'rejected': result.get('rejected'), 'raw_unique': result.get('raw_unique')}
                    # 判断纯 HTTP 通道是否被风控（六态），被拦则自动切换到已启动的 CDP 真实浏览器，不把失败当 0 条
                    http_state = str(result.get('task_state', '') or '').upper()
                    state_counts = result.get('state_counts') or {}
                    risk_hit = http_state in ('BLOCKED', 'CAPTCHA', 'AUTH_FAILED', 'PARTIAL_BLOCKED') or \
                        any(str(k).upper() in ('BLOCKED', 'CAPTCHA') for k in state_counts)
                    if ins == 0 and risk_hit:
                        logger.warning(f'纯HTTP采集被风控(state={http_state},{state_counts})，自动切换 CDP 真实浏览器采集 ...')
                        task['collect_detail']['http_state'] = http_state
                        cdp_new, cdp_state = self._collect_via_cdp(task, max_scroll)
                        task['collect_detail']['cdp_inserted'] = cdp_new
                        logger.info(f'CDP 兜底采集：新增 {cdp_new} 条，状态 {cdp_state}')
                        if cdp_new > 0 or cdp_state == 'success':
                            return cdp_new
                        # HTTP 与 CDP 均未取到数据：按真实原因报错，绝不伪装成“本次 0 条”
                        if cdp_state == 'blocked':
                            raise RuntimeError(
                                '小红书安全拦截：纯HTTP与CDP浏览器均被风控/需人机验证，已暂停本次采集（不计为0条）。'
                                '请在采集浏览器完成一次人机验证后重试。')
                        raise RuntimeError(
                            f'小红书搜索页未加载成功（CDP状态={cdp_state}，多为当前网络过慢/临时风控），本次不计为0条；'
                            '建议切换更稳定网络或稍后重试，若持续出现请在采集浏览器完成一次人机验证。')
                    logger.info(f"真实采集完成：新增 {ins}、更新 {upd}、主体外拒绝 {result.get('rejected')}")
                    return ins
            except ImportError:
                pass

            # 2) 兜底：collector.run_collection
            try:
                import collector
                if hasattr(collector, 'run_collection'):
                    result = collector.run_collection(
                        keywords=task['keywords'],
                        duration=cfg['duration'],
                    )
                    return int(result.get('new_notes', result.get('inserted', 0)))
            except ImportError:
                pass

            # 没有真实采集模块时明确报错，而不是 sleep 假装采集（避免“看起来在跑、实际 0 条”）
            raise RuntimeError('未找到可用的真实采集模块（xhs_cookie_bridge.sync / collector.run_collection 均不可用），已拒绝空跑模拟')

        except Exception as e:
            logger.error(f"执行采集失败: {e}")
            raise

    def _warmup_cdp(self, account=None):
        """采集前让 CDP 浏览器先进入目标平台域（建连 + 带验证 cookie），
        避免从 about:blank 冷启动、在慢网络/热点下 goto 搜索页 45s 超时。"""
        try:
            import xhs_cookie_bridge as _xcb
            port = self._port_for(account)
            home = _xcb.home_url_for(account)
            host_key = 'rednote.com' if 'rednote' in home else 'xiaohongshu.com'
            warm_url = home + ('/explore' if host_key == 'xiaohongshu.com' else '')
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                b = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{port}', timeout=15000)
                ctx = b.contexts[0]
                pg = next((x for x in ctx.pages if host_key in x.url), None)
                if pg is None:
                    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                try:
                    pg.goto(warm_url, wait_until='commit', timeout=60000)
                    time.sleep(5)
                    logger.info(f'[CDP热身] 已进入小红书域 url={pg.url[:60]}')
                except Exception as e:
                    logger.warning(f'[CDP热身] 未完成(继续尝试采集): {str(e)[:80]}')
                b.close()
        except Exception as e:
            logger.warning(f'[CDP热身] 跳过: {str(e)[:80]}')

    def _collect_via_cdp(self, task, max_scroll):
        """纯 HTTP 通道被风控时的兜底：通过 _run_collection 已启动的 CDP 真实浏览器采集并真实入库。
        返回 (新增条数, 状态)；状态 ∈ success / blocked / failed。不绕过人机验证，被拦即如实上报。"""
        import database as db
        try:
            import subject_rules
            subj = getattr(subject_rules, 'subject_hit', None)
        except Exception:
            subj = None
        cjs = os.path.join(self.base_dir, 'rednote_collector.cjs')
        if not os.path.exists(cjs):
            raise RuntimeError(f'CDP 兜底采集缺少 rednote_collector.cjs: {cjs}')
        account = task.get('account')
        import xhs_cookie_bridge as _xcb
        policy_gate = _xcb.collection_policy_gate(account=account, region='intl')
        if not policy_gate.get('ok'):
            logger.warning('[CDP采集] 生产策略阻断: %s', policy_gate.get('reason'))
            return 0, 'blocked'
        port = self._port_for(account)
        env = os.environ.copy()
        env['XHS_CDP_URL'] = f'http://127.0.0.1:{port}'
        env['XHS_COLLECTION_REGION'] = 'intl'
        env['XHS_COLLECTION_HOST'] = 'www.rednote.com'
        profile = _xcb.ACCOUNT_PROFILES.get(account or _xcb.DEFAULT_COLLECTION_ACCOUNT)
        if profile and profile[0]:
            env['XHS_COOKIE_FILE'] = str(profile[0])
        max_details = 6
        total_new = 0; blocked_any = False; loadfail_any = False; attempted = 0
        self._warmup_cdp(account)
        for kw in (task.get('keywords') or []):
            attempted += 1
            out = os.path.join(_xcb.PRIVATE_DATA_DIR,
                               f'rednote_cdp_{datetime.now():%Y%m%d_%H%M%S}_{abs(hash(kw))%10000}.json')
            os.makedirs(os.path.dirname(out), exist_ok=True)
            cmd = [_NODE_BIN, cjs, '--keyword', str(kw), '--output', out,
                   '--max-scroll', str(max_scroll), '--max-details', str(max_details)]
            try:
                p = subprocess.run(cmd, cwd=self.base_dir, capture_output=True, text=True, timeout=900, env=env)
                data = None
                marker = '---RESULT_JSON---'
                if marker in (p.stdout or ''):
                    data = json.loads(p.stdout[p.stdout.index(marker) + len(marker):].strip())
                elif os.path.exists(out):
                    data = json.loads(Path(out).read_text(encoding='utf-8'))
                if not data:
                    loadfail_any = True
                    logger.warning(f'[CDP采集] {kw} 无结果: {(p.stderr or p.stdout or "")[-160:]}')
                    continue
                summ = data.get('summary', {}) or {}
                if data.get('verification_required') or data.get('ip_blocked') or \
                   summ.get('verification_required') or summ.get('ip_blocked'):
                    blocked_any = True
                    logger.warning(f'[CDP采集] {kw} 仍被风控/需人机验证')
                    continue
                # 搜索页加载失败（慢网络/临时风控，页面停在 about:blank）不计为成功 0 条
                if not data.get('ok', True) or data.get('load_failed'):
                    loadfail_any = True
                    logger.warning(f'[CDP采集] {kw} 搜索页加载失败: {str(data.get("error",""))[:100]}')
                    continue
                kw_new = 0
                for n in data.get('notes', []):
                    title = n.get('detail_title') or n.get('title', '')
                    body = n.get('desc', '') or n.get('content', '')
                    if subj and not subj(title, body, body, str(kw), []):
                        continue
                    note_data = {
                        'note_id': n.get('note_id', ''),
                        'title': title, 'content': body,
                        'url': n.get('url', ''), 'cover': n.get('cover', ''),
                        'author_id': n.get('author_id', ''),
                        'author_nickname': n.get('detail_author') or n.get('author', ''),
                        'author_avatar': n.get('author_avatar', ''),
                        'likes': int(n.get('likes', 0) or 0), 'comments': int(n.get('comments', 0) or 0),
                        'collects': int(n.get('collects', 0) or 0), 'shares': int(n.get('shares', 0) or 0),
                        'xsec_token': n.get('xsec_token', ''),
                        'publish_datetime': n.get('detail_publish_time') or n.get('publish_time', ''),
                        'source_platform': 'xiaohongshu-cdp',
                        'is_taikoo_verified': 1, 'verify_reason': 'CDP采集主体命中',
                        'data_quality_status': n.get('quality_status', 'complete'),
                        'data_quality_score': float(n.get('quality_score', 0) or 0),
                        'collector_version': n.get('collector_version', 'rednote-v1.0-cdp'),
                        'collected_at': datetime.now().isoformat(),
                        'detail_fetched_at': datetime.now().isoformat(),
                        'comments_collected': n.get('comment_count'),
                    }
                    try:
                        ins_ret = db.insert_note(note_data)
                        is_new = ins_ret[1] if isinstance(ins_ret, (list, tuple)) and len(ins_ret) > 1 else True
                        kw_new += int(bool(is_new)); total_new += int(bool(is_new))
                        cl = n.get('comment_list') or n.get('comments_data') or []
                        if cl:
                            db.upsert_note_comments(n.get('note_id', ''), cl)
                    except Exception as e:
                        logger.error(f'[CDP采集] 入库失败 {n.get("note_id","")}: {e}')
                logger.info(f'[CDP采集] {kw}: 发现{summ.get("discovered")} 详情{summ.get("detail_success")} 新增{kw_new}')
            except subprocess.TimeoutExpired:
                logger.error(f'[CDP采集] {kw} 超时')
            except Exception as e:
                logger.error(f'[CDP采集] {kw} 异常: {e}')
        if attempted == 0:
            return 0, 'failed'
        if blocked_any and total_new == 0:
            return 0, 'blocked'
        if loadfail_any and total_new == 0:
            return 0, 'load_failed'
        return total_new, 'success'

    def get_status(self):
        """获取采集器状态"""
        return {
            'is_running': self.is_running,
            'lifecycle_state': self._lifecycle_state.value,
            'stop_requested': self._stop_event.is_set(),
            'current_task': self.current_task,
            'browser_running': self._is_browser_running(),
            'cdp_port': self.cdp_port,
            'active_cdp_port': self._task_cdp_port,
            'edge_path': self.edge_path,
            'history_count': len(self.task_history),
            'today_count': len([t for t in self.task_history if t.get('start_time', '').startswith(datetime.now().strftime('%Y-%m-%d'))]),
        }
    
    def stop_collection(self):
        """优雅停止当前采集任务：设置 STOPPING 状态 + stop_event，等待线程退出（最多30s）。"""
        with self._lock:
            if not self.is_running:
                return {'ok': False, 'error': '没有正在运行的采集任务'}

            if self.current_task:
                self.current_task['status'] = 'stopping'
                logger.info(f"正在停止采集任务: {self.current_task['id']}")

            # 设置停止信号（采集线程可检测此信号实现优雅退出）
            self._stop_event.set()
            self.transition_state(CollectorLifecycleState.STOPPING, reason='user_stop')

            # 停止浏览器会导致采集任务中断
            try:
                self.stop_browser()
            except Exception as e:
                logger.error(f"停止浏览器失败: {e}")

        # 在锁外等待线程退出（避免死锁：_run_collection 的 finally 也会尝试获取 _lock）
        thread = self._collection_thread
        if thread and thread.is_alive():
            thread.join(timeout=30)
            if thread.is_alive():
                logger.warning('采集线程 30s 内未退出，标记为强制停止（线程仍在后台运行）')

        with self._lock:
            self.transition_state(CollectorLifecycleState.STOPPED, reason='stopped')
            self._collection_thread = None
            return {'ok': True, 'message': '采集任务已停止'}
    
    def _load_history(self):
        """加载历史记录"""
        history_file = os.path.join(self.data_dir, 'collector_history.json')
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.task_history = json.load(f)
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            self.task_history = []
    
    def _save_history(self, task):
        """保存历史记录"""
        history_file = os.path.join(self.data_dir, 'collector_history.json')
        try:
            # 只保留最近100条记录
            self.task_history.append(task)
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.task_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
    
    def get_history(self, limit=20):
        """获取历史记录"""
        return self.task_history[-limit:][::-1]  # 最新的在前


# 全局单例
_collector_automation = None

def get_collector_automation():
    """获取采集器自动化单例"""
    global _collector_automation
    if _collector_automation is None:
        _collector_automation = CollectorAutomation()
    return _collector_automation


# 测试
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    collector = get_collector_automation()
    print("采集器自动化模块已加载")
    print(f"Edge浏览器路径: {collector.edge_path}")
    print(f"CDP端口: {collector.cdp_port}")
    print(f"浏览器运行状态: {collector._is_browser_running()}")
    
    # 测试启动浏览器
    # collector.start_browser()
    # time.sleep(5)
    # collector.stop_browser()


# ===== 双账号轮换集成 =====
def _rotate_account_before_collection(kos_mode=False):
    """采集前选择账号（不规则轮换）。"""
    if not DUAL_ACCOUNT_ENABLED:
        return None, '双账号模块未启用'
    try:
        account, reason = select_account_for_collection(kos_mode=kos_mode)
        return account, reason
    except Exception as e:
        return None, f'账号轮换异常: {e}'

def _record_collection_result(account, success, risk=False):
    """记录采集结果用于账号轮换决策。"""
    if not DUAL_ACCOUNT_ENABLED or not account:
        return
    try:
        record_collection_result(account, success, risk)
    except:
        pass
