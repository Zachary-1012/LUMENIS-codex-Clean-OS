"""
采集器自动化模块 - 广州太古汇舆情监测系统 v5.8.0
实现自动启动→采集→自动关闭的完整流程
"""
import os
import sys
import time
import json
import subprocess
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 配置日志
logger = logging.getLogger(__name__)

class CollectorAutomation:
    """采集器自动化控制器"""
    
    def __init__(self, base_dir=None):
        # 本文件就在项目根目录，只上溯一级；此前多上溯一级误指向 D:\，导致 cjs/profile/data 路径全部错位
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.logs_dir = os.path.join(self.base_dir, 'logs')
        self.cdp_port = 9222
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
    
    def start_browser(self, account='default', headless=False):
        """启动Edge浏览器（CDP模式）"""
        if not self.edge_path:
            raise RuntimeError("未找到Edge浏览器，请先安装Microsoft Edge")
        
        # 检查浏览器是否已经在运行
        if self._is_browser_running():
            logger.info("浏览器已在运行，无需重复启动")
            return True
        
        profile_dir = self._get_cdp_profile_dir(account)
        
        # 构建启动参数
        args = [
            self.edge_path,
            f'--remote-debugging-port={self.cdp_port}',
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
            # 国内主采集强制直连：不跟随系统代理(v2rayN 10808)，代理核心未连/切节点时国内站也能采；
            # 海外平台(Google/Instagram)走 9223 独立代理 profile，互不影响。
            '--no-proxy-server',
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

            logger.info(f"Edge浏览器已启动，PID: {process.pid} (profile={os.path.basename(profile_dir)})")
            
            # 等待CDP端口就绪
            if self._wait_for_cdp_ready(timeout=30):
                logger.info("CDP调试端口已就绪")
                return True
            else:
                logger.warning("CDP调试端口未就绪，但浏览器已启动")
                return True
                
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            raise
    
    def _is_browser_running(self):
        """检查浏览器是否在运行"""
        try:
            import urllib.request
            response = urllib.request.urlopen(f'http://127.0.0.1:{self.cdp_port}/json/version', timeout=3)
            return response.status == 200
        except Exception:
            return False
    
    def _wait_for_cdp_ready(self, timeout=30):
        """等待CDP端口就绪"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_browser_running():
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
    
    def start_collection(self, keywords=None, mode='standard', account='default', force=False):
        """启动采集任务。force=True 跳过 1 小时冷却（测试期使用）。

        双子星库 Contract 门控：采集前调用 xhs_cookie_bridge.runtime_preflight_check()。
        - account 传 'default' 时：等价于无显式 account，runtime_preflight 会激活默认 XHS_CN_PRIMARY。
        - account ∈ {XHS_CN_PRIMARY_NAME, XHS_RETINAUT_NAME}：按 Contract 白名单切换；不在白名单直接拒绝。
        - 任何预检失败（熔断/无Cookie/白名单/冷却/暂停）→ 如实返回错误，绝不静默启动空跑。
        """
        with self._lock:
            if self.is_running:
                logger.warning("采集任务已在运行中")
                return {'ok': False, 'error': '采集任务已在运行中'}

            # ── 双子星库 Contract 预检（在所有调度逻辑之前，fail-fast）──
            pre_ok, pre_msg, pre_detail = True, '', {}
            try:
                import xhs_cookie_bridge as _xcb
                # 归一化：'default' 传 None → runtime_preflight 使用默认 XHS_CN_PRIMARY_NAME
                _account_for_check = None if account in (None, '', 'default') else account
                # force=True 预检仍跑（保留真实报告），但只在严重 P0 阻断（身份/白名单/熔断）时才拦截
                preflight = _xcb.runtime_preflight_check(account=_account_for_check,
                                                          cdp_url=os.getenv('XHS_CDP_URL', f'http://127.0.0.1:{self.cdp_port}'),
                                                          quick=False)
                pre_detail = {'overall_state': preflight.get('overall_state'),
                              'evidence': preflight.get('evidence'),
                              'active_account': preflight.get('active_account'),
                              'checks_fail_count': sum(1 for c in preflight.get('checks', []) if c.get('status') == 'fail')}
                if not preflight.get('ok'):
                    ov = str(preflight.get('overall_state', ''))
                    # force=True 允许旁路 cooldown / rate_limit（用于测试 & 紧急）；但 P0 严重项仍然阻断
                    p0_blocker = ov in ('need_account', 'no_cookie', 'not_in_whitelist', 'blocked', 'user_paused')
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
            
            config = mode_config.get(mode, mode_config['standard'])
            
            self.current_task = {
                'id': f'collect_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'keywords': keywords,
                'mode': mode,
                'account': account,
                'trigger_type': trigger_type,
                'config': config,
                'status': 'starting',
                'start_time': datetime.now().isoformat(),
                'progress': 0,
                'new_notes': 0,
                'errors': [],
            }
            
            self.is_running = True
            
            # 在后台线程中执行采集
            thread = threading.Thread(target=self._run_collection, args=(self.current_task,), daemon=True)
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
        try:
            task['status'] = 'starting_browser'
            logger.info(f"任务 {task['id']}: 启动浏览器...")
            
            # 启动浏览器
            self.start_browser(account=task['account'])
            time.sleep(3)
            
            task['status'] = 'collecting'
            logger.info(f"任务 {task['id']}: 开始采集...")
            
            # 执行采集（调用现有的采集模块）
            new_notes = self._execute_collection(task)
            task['new_notes'] = new_notes
            task['progress'] = 100
            
            task['status'] = 'completed'
            task['end_time'] = datetime.now().isoformat()
            logger.info(f"任务 {task['id']}: 采集完成，新增 {new_notes} 条笔记")
            
        except Exception as e:
            task['status'] = 'failed'
            task['errors'].append(str(e))
            task['end_time'] = datetime.now().isoformat()
            logger.error(f"任务 {task['id']}: 采集失败: {e}", exc_info=True)
        finally:
            # 自动关闭浏览器
            logger.info(f"任务 {task['id']}: 自动关闭浏览器...")
            try:
                self.stop_browser()
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")
            
            # 保存历史记录
            self._save_history(task)
            # 记录本次结束时间，作为 1 小时冷却起点
            self._last_finish_at[task.get('trigger_type', 'auto')] = datetime.now()
            self.is_running = False
            self.current_task = None
    
    def _execute_collection(self, task):
        """执行实际的采集逻辑（必须真实入库，不再静默 sleep 模拟空跑）"""
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
                    result = xhs_cookie_bridge.sync(keywords=task['keywords'], max_scroll=max_scroll)
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

    def _warmup_cdp(self):
        """采集前让 CDP 浏览器先进入小红书域（建连 + 带验证 cookie），
        避免从 about:blank 冷启动、在慢网络/热点下 goto 搜索页 45s 超时。"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                b = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{self.cdp_port}', timeout=15000)
                ctx = b.contexts[0]
                pg = next((x for x in ctx.pages if 'xiaohongshu.com' in x.url), None)
                if pg is None:
                    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                try:
                    pg.goto('https://www.xiaohongshu.com/explore', wait_until='commit', timeout=60000)
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
        env = os.environ.copy()
        env['XHS_CDP_URL'] = f'http://127.0.0.1:{self.cdp_port}'
        max_details = 6
        total_new = 0; blocked_any = False; loadfail_any = False; attempted = 0
        self._warmup_cdp()
        for kw in (task.get('keywords') or []):
            attempted += 1
            out = os.path.join(self.data_dir, f'rednote_cdp_{datetime.now():%Y%m%d_%H%M%S}_{abs(hash(kw))%10000}.json')
            cmd = ['node', cjs, '--keyword', str(kw), '--output', out,
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
                        'publish_date': n.get('detail_publish_time') or n.get('publish_time', ''),
                        'source_platform': 'xiaohongshu-cdp',
                        'is_taikoo_verified': 1, 'verify_reason': 'CDP采集主体命中',
                        'data_quality_status': n.get('quality_status', 'complete'),
                        'data_quality_score': float(n.get('quality_score', 0) or 0),
                        'collector_version': n.get('collector_version', 'rednote-v1.0-cdp'),
                        'captured_at': datetime.now().isoformat(),
                        'detail_fetched_at': datetime.now().isoformat(),
                        'comments_collected': int(n.get('comment_count', 0) or 0),
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
            'current_task': self.current_task,
            'browser_running': self._is_browser_running(),
            'cdp_port': self.cdp_port,
            'edge_path': self.edge_path,
            'history_count': len(self.task_history),
            'today_count': len([t for t in self.task_history if t.get('start_time', '').startswith(datetime.now().strftime('%Y-%m-%d'))]),
        }
    
    def stop_collection(self):
        """停止当前采集任务"""
        with self._lock:
            if not self.is_running:
                return {'ok': False, 'error': '没有正在运行的采集任务'}
            
            if self.current_task:
                self.current_task['status'] = 'stopping'
                logger.info(f"正在停止采集任务: {self.current_task['id']}")
            
            # 停止浏览器会导致采集任务中断
            try:
                self.stop_browser()
            except Exception as e:
                logger.error(f"停止浏览器失败: {e}")
            
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
