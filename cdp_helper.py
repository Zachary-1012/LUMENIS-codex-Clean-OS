"""
CDP浏览器管理辅助函数
在采集前自动检查并启动带CDP调试端口的受控 Chromium 浏览器
"""
import os
import sys
import subprocess
import time
import socket
import logging
import ntpath

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CDP_PORT = 9222
DEFAULT_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
DEFAULT_PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edge-cdp-newaccount")

# ============================================================
# 多浏览器内核支持（Chrome / Edge 同为 Chromium，CDP 协议通用）
#   · Windows 无可用 Safari（Apple 2012 年已停 Windows 版），仅在 macOS 预留；
#   · Firefox 未走 Chromium CDP，暂作预留，不默认启用。
# 每个浏览器使用独立持久 Profile 与独立调试端口，指纹/登录态互不串扰。
# ============================================================
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BROWSER_REGISTRY = {
    "edge": {
        "exe_candidates": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "where_name": "msedge",
        "process_name": "msedge.exe",
        "default_profile": os.path.join(_BASE_DIR, "edge-cdp-newaccount"),
    },
    "chrome": {
        "exe_candidates": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ],
        "where_name": "chrome",
        "process_name": "chrome.exe",
        "default_profile": os.path.join(_BASE_DIR, "chrome-cdp-profile"),
    },
    "firefox": {
        "exe_candidates": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ],
        "where_name": "firefox",
        "process_name": "firefox.exe",
        "default_profile": os.path.join(_BASE_DIR, "firefox-cdp-profile"),
    },
}
# Windows 平台无法落地的内核（仅记录原因，不在此伪装为可用）
UNSUPPORTED_ON_WINDOWS = {
    "safari": "Apple 已于 2012 年停止 Windows 版 Safari；Safari 自动化仅支持 macOS（safaridriver/AppleScript），当前系统不可用，仅预留接口。",
}


def is_cdp_port_open(port=DEFAULT_CDP_PORT):
    """检查CDP端口是否已监听"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result == 0
    except Exception:
        return False


def is_cdp_profile_running(port, profile_dir):
    """Return true only when a local Chromium command line binds this port to this profile."""
    try:
        import psutil
        expected_profile = os.path.normcase(os.path.abspath(os.path.normpath(profile_dir)))
        expected_port = f"--remote-debugging-port={int(port)}".casefold()
        expected_bind_arg = "--remote-debugging-address=127.0.0.1"
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                name = str(proc.info.get("name") or "").casefold()
                if name not in {"msedge.exe", "chrome.exe"}:
                    continue
                args = [str(arg).strip().strip('"') for arg in (proc.info.get("cmdline") or [])]
                normalized_args = [arg.casefold() for arg in args]
                has_port = expected_port in normalized_args
                if not has_port:
                    for index, arg in enumerate(normalized_args[:-1]):
                        if arg == "--remote-debugging-port" and normalized_args[index + 1] == str(int(port)):
                            has_port = True
                            break
                has_profile = any(
                    arg.startswith("--user-data-dir=")
                    and os.path.normcase(os.path.abspath(os.path.normpath(arg.split("=", 1)[1])))
                    == expected_profile
                    for arg in args
                )
                has_loopback_bind = expected_bind_arg in normalized_args
                if has_port and has_profile and has_loopback_bind:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError, ValueError):
                continue
    except Exception:
        return False
    return False


def find_edge_path():
    """查找Edge浏览器路径"""
    for path in DEFAULT_EDGE_PATHS:
        if os.path.exists(path):
            return path
    # 尝试通过where命令查找
    try:
        result = subprocess.run(["where", "msedge"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass
    return None


def find_browser_path(browser="edge"):
    """按内核名查找可执行文件路径；未知内核或未安装返回 None。"""
    browser = (browser or "edge").lower()
    if browser in UNSUPPORTED_ON_WINDOWS:
        logger.warning(UNSUPPORTED_ON_WINDOWS[browser])
        return None
    conf = BROWSER_REGISTRY.get(browser)
    if not conf:
        logger.warning("未知浏览器内核: %s（支持 edge/chrome）", browser)
        return None
    for path in conf["exe_candidates"]:
        if path and os.path.exists(path):
            return path
    try:  # where 命令兜底
        result = subprocess.run(["where", conf["where_name"]], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass
    return None


def find_chrome_path():
    """查找 Chrome 浏览器路径。"""
    return find_browser_path("chrome")


def _https_associated_executable():
    """Read the Windows HTTPS handler through the supported shell association API."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        query = ctypes.WinDLL("Shlwapi").AssocQueryStringW
        query.argtypes = (
            wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR,
            wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
        )
        query.restype = ctypes.c_long
        buffer = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(buffer))
        # ASSOCSTR_EXECUTABLE=2; "https" asks Windows for the current handler.
        if query(0, 2, "https", None, buffer, ctypes.byref(length)) != 0:
            return None
        return buffer.value or None
    except (AttributeError, OSError, ValueError):
        return None


def system_default_cdp_browser():
    """Return the installed Chrome/Edge HTTPS handler, or None without fallback."""
    executable = _https_associated_executable()
    name = ntpath.basename(executable or "").casefold()
    browser = {"chrome.exe": "chrome", "msedge.exe": "edge"}.get(name)
    return browser if browser and find_browser_path(browser) else None


def default_profile_for(browser="edge"):
    """返回某内核的默认持久 Profile 目录。"""
    conf = BROWSER_REGISTRY.get((browser or "edge").lower())
    return conf["default_profile"] if conf else DEFAULT_PROFILE_DIR


def start_cdp_browser(port=DEFAULT_CDP_PORT, profile_dir=None, headless=False,
                      proxy_server=None, launch_url="https://www.xiaohongshu.com",
                      anti_automation=True, browser="edge", direct_connection=False,
                      loopback_only=False):
    """
    启动带 CDP 调试端口的指定 Chromium 浏览器。
    
    Args:
        port: CDP调试端口
        profile_dir: 用户数据目录
        headless: 是否无头模式
    
    Returns:
        dict: {success: bool, message: str, port: int, pid: int}
    """
    if is_cdp_port_open(port):
        return {"success": True, "message": f"CDP端口 {port} 已在使用", "port": port, "pid": None}
    
    browser = (browser or "edge").lower()
    if browser in UNSUPPORTED_ON_WINDOWS:
        return {"success": False, "message": UNSUPPORTED_ON_WINDOWS[browser], "port": port, "pid": None}
    edge_path = find_browser_path(browser)
    if not edge_path:
        return {"success": False, "message": f"未找到 {browser} 浏览器，请安装或改用其他内核", "port": port, "pid": None}
    
    if profile_dir is None:
        profile_dir = default_profile_for(browser)
    
    os.makedirs(profile_dir, exist_ok=True)
    
    args = [
        edge_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--disable-extensions",
        "--disable-default-apps",
        "--disable-sync",
        "--password-store=basic",
        "--disable-features=Translate,MediaRouter,OptimizationHints,InterestFeedContentSuggestions",
        # Chromium 111+ / 新版 Edge 要求显式允许 CDP WebSocket 的 Origin，
        # 否则 Playwright connect_over_cdp 会在 ws 握手阶段挂起直至 Timeout（话题端口曾因此全 0）。
        "--remote-allow-origins=*",
    ]
    if loopback_only:
        args.append("--remote-debugging-address=127.0.0.1")
    
    if anti_automation:
        args.append("--disable-blink-features=AutomationControlled")
    if proxy_server:
        args.append(f"--proxy-server=http://{proxy_server}")
    if direct_connection:
        # 大陆主采集强制直连：不跟随系统代理，代理核心未连/切节点时国内站仍可稳定加载；
        # 海外身份(香港 rednote)不传此开关，继承系统/海外代理链路。
        args.append("--no-proxy-server")
    if headless:
        args.append("--headless=new")
    
    # 打开小红书页面
    args.append(launch_url)
    
    try:
        # Windows 下让 Edge 真正脱离启动它的父进程独立运行：
        # CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS，并把三个标准句柄重定向到
        # DEVNULL、close_fds=True，避免父 python（采集脚本/任务线程）退出时把
        # CDP Edge 一起带走（此前现象：启动脚本一结束，9222 立即 ECONNREFUSED）。
        detached_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        if sys.platform == 'win32':
            detached_flags |= getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
        proc = subprocess.Popen(
            args,
            creationflags=detached_flags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 解除父子生命周期绑定：父进程不再等待该子进程
        try:
            proc._active = False
        except Exception:
            pass
        logger.info("已启动独立 %s 浏览器 (PID: %s), CDP端口: %s", browser, proc.pid, port)
        
        # 等待CDP端口就绪
        for i in range(15):
            time.sleep(1)
            if is_cdp_port_open(port):
                return {"success": True, "message": f"{browser} 浏览器已启动，CDP端口 {port} 就绪", "port": port, "pid": proc.pid}
        
        return {"success": False, "message": f"{browser} 浏览器已启动但CDP端口 {port} 未就绪，请检查浏览器状态", "port": port, "pid": proc.pid}
    
    except Exception as e:
        logger.error("启动 %s 浏览器失败: %s", browser, e)
        return {"success": False, "message": f"启动 {browser} 浏览器失败: {str(e)}", "port": port, "pid": None}


def ensure_cdp_browser(port=DEFAULT_CDP_PORT, profile_dir=None, auto_start=True, **launch_kwargs):
    """
    确保CDP浏览器可用，如果未启动则自动启动
    
    Args:
        port: CDP调试端口
        profile_dir: 用户数据目录
        auto_start: 是否自动启动
    
    Returns:
        dict: {available: bool, message: str, port: int, auto_started: bool}
    """
    if is_cdp_port_open(port):
        return {"available": True, "message": f"CDP端口 {port} 可用", "port": port, "auto_started": False}
    
    if not auto_start:
        return {"available": False, "message": f"CDP端口 {port} 未启动，请先运行 scripts/start_production.ps1（生产会启动 9223 香港采集 + 9224 通用浏览）", "port": port, "auto_started": False}
    
    logger.info(f"CDP端口 {port} 未启动，正在自动启动Edge浏览器...")
    result = start_cdp_browser(port, profile_dir, **launch_kwargs)
    
    return {
        "available": result["success"],
        "message": result["message"],
        "port": port,
        "auto_started": result["success"],
    }


def reset_cdp_targets(port=DEFAULT_CDP_PORT, timeout=6):
    """连接前用纯 HTTP CDP 接口复位活动 target（不走 WebSocket，不受挂起影响）。

    根因：Playwright connect_over_cdp 会 attach 现有 page；若浏览器停在小红书等"重页面"
    （持续 XHR / 长连接 / 复杂 JS）或残留 service worker，attach 阶段的 CDP 初始化会挂起直至超时
    （话题端口曾因此 connectOverCDP 30s 超时、数据全 0）。
    做法：新开 about:blank 保底，再关闭所有重 page 与 service_worker / shared_worker，
    使后续 connect_over_cdp 秒连（实测复位后 0.15s）。专用采集 profile，关闭其采集页安全
    （登录态保存在 profile 内，不依赖某个页面常开）。best-effort，任何异常都不阻断主流程，返回关闭数。
    """
    import urllib.request
    import json as _json
    base = f"http://127.0.0.1:{port}"

    def _http(path, method="GET"):
        req = urllib.request.Request(base + path, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore")

    closed = 0
    try:
        try:
            targets = _json.loads(_http("/json/list"))
        except Exception:
            return 0
        heavy = [t for t in targets
                 if not (t.get("type") == "page" and "about:blank" in (t.get("url") or ""))]
        if not heavy:
            return 0
        # 先开一个空白页保底（新版 Chromium 需 PUT，旧版用 GET 兜底）
        try:
            _http("/json/new?about:blank", "PUT")
        except Exception:
            try:
                _http("/json/new?about:blank", "GET")
            except Exception:
                pass
        time.sleep(0.6)
        try:
            targets = _json.loads(_http("/json/list"))
        except Exception:
            targets = heavy
        for t in targets:
            if t.get("type") == "page" and "about:blank" in (t.get("url") or ""):
                continue
            tid = t.get("id")
            if not tid:
                continue
            try:
                _http(f"/json/close/{tid}")
                closed += 1
            except Exception:
                pass
        time.sleep(0.4)
    except Exception:
        return closed
    return closed


def get_cdp_status(port=DEFAULT_CDP_PORT):
    """获取CDP浏览器状态"""
    return {
        "port": port,
        "available": is_cdp_port_open(port),
        "edge_path": find_edge_path(),
        "profile_dir": DEFAULT_PROFILE_DIR,
    }


def stop_cdp_browser(port=DEFAULT_CDP_PORT):
    """
    关闭CDP浏览器（通过CDP协议优雅关闭，或强制终止进程）
    
    Args:
        port: CDP调试端口
    
    Returns:
        dict: {success: bool, message: str}
    """
    try:
        # 方法1：通过CDP协议优雅关闭
        import urllib.request
        import json
        
        try:
            # 获取浏览器版本信息（验证CDP可用）
            req = urllib.request.Request(f'http://127.0.0.1:{port}/json/version')
            with urllib.request.urlopen(req, timeout=5) as response:
                version_info = json.loads(response.read().decode())
                logger.info(f"CDP浏览器版本: {version_info.get('Browser', 'unknown')}")
        except Exception:
            pass
        
        # 方法2：查找并终止Edge进程
        import psutil
        
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and any(n in proc.info['name'].lower() for n in ('msedge', 'chrome')):
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if f'--remote-debugging-port={port}' in cmdline:
                        logger.info(f"终止CDP浏览器进程: PID={proc.info['pid']}")
                        proc.terminate()
                        killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 等待进程终止
        if killed_count > 0:
            import time
            time.sleep(2)
            
            # 强制终止残留进程
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and any(n in proc.info['name'].lower() for n in ('msedge', 'chrome')):
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if f'--remote-debugging-port={port}' in cmdline:
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        
        # 验证端口已释放
        import time
        for _ in range(5):
            if not is_cdp_port_open(port):
                break
            time.sleep(1)
        
        return {
            "success": True,
            "message": f"CDP浏览器已关闭（终止{killed_count}个进程）",
            "killed_count": killed_count
        }
        
    except ImportError:
        # psutil未安装，使用taskkill
        try:
            import subprocess
            result = subprocess.run(
                ['taskkill', '/F', '/IM', 'msedge.exe', '/FI', f'WINDOWTITLE eq *{port}*'],
                capture_output=True, text=True, timeout=10
            )
            return {"success": True, "message": "已尝试终止Edge浏览器进程"}
        except Exception as e:
            return {"success": False, "message": f"关闭失败: {str(e)}"}
    
    except Exception as e:
        logger.error(f"关闭CDP浏览器失败: {e}")
        return {"success": False, "message": f"关闭失败: {str(e)}"}


class CDPBrowserContext:
    """
    CDP浏览器上下文管理器：自动启动→使用→自动关闭
    
    用法：
        with CDPBrowserContext(port=9222) as browser:
            if browser['available']:
                # 执行采集任务
                do_collect()
        # 退出with块后浏览器自动关闭
    
    参考GitHub实际应用：
    - albertofwb/douyin-publisher: chrome_utils.py
    """
    
    def __init__(self, port=DEFAULT_CDP_PORT, profile_dir=None, auto_start=True, auto_close=True):
        self.port = port
        self.profile_dir = profile_dir
        self.auto_start = auto_start
        self.auto_close = auto_close
        self.browser_info = None
        self.was_running = False
    
    def __enter__(self):
        """进入上下文：检查或启动CDP浏览器"""
        # 检查是否已经在运行
        self.was_running = is_cdp_port_open(self.port)
        
        if self.was_running:
            logger.info(f"CDP浏览器已在运行（端口{self.port}），复用现有实例")
            self.browser_info = {
                "available": True,
                "message": "复用现有CDP浏览器实例",
                "port": self.port,
                "auto_started": False,
                "was_running": True
            }
        elif self.auto_start:
            logger.info(f"CDP浏览器未运行，自动启动（端口{self.port}）...")
            result = ensure_cdp_browser(self.port, self.profile_dir, auto_start=True)
            self.browser_info = {
                **result,
                "was_running": False
            }
        else:
            self.browser_info = {
                "available": False,
                "message": "CDP浏览器未启动且auto_start=False",
                "port": self.port,
                "auto_started": False,
                "was_running": False
            }
        
        return self.browser_info
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文：自动关闭CDP浏览器（如果是自动启动的）"""
        if self.auto_close and not self.was_running and self.browser_info and self.browser_info.get('available'):
            logger.info(f"自动关闭CDP浏览器（端口{self.port}）...")
            result = stop_cdp_browser(self.port)
            if result.get('success'):
                logger.info(f"CDP浏览器已自动关闭: {result.get('message')}")
            else:
                logger.warning(f"CDP浏览器关闭失败: {result.get('message')}")
        
        # 不抑制异常
        return False


def auto_collect_with_cdp(collect_func, port=DEFAULT_CDP_PORT, profile_dir=None, *args, **kwargs):
    """
    自动化采集：自动启动CDP→执行采集→自动关闭
    
    Args:
        collect_func: 采集函数，接收browser_info作为第一个参数
        port: CDP端口
        profile_dir: 浏览器配置目录
        *args, **kwargs: 传递给采集函数的其他参数
    
    Returns:
        采集函数的返回值
    
    用法：
        def my_collect(browser_info, keyword):
            # 执行采集
            return results
        
        results = auto_collect_with_cdp(my_collect, keyword="广州太古汇")
    """
    with CDPBrowserContext(port=port, profile_dir=profile_dir, auto_start=True, auto_close=True) as browser_info:
        if not browser_info.get('available'):
            logger.error(f"CDP浏览器不可用: {browser_info.get('message')}")
            return {"success": False, "error": browser_info.get('message'), "data": None}
        
        try:
            result = collect_func(browser_info, *args, **kwargs)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"采集任务失败: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e), "data": None}


if __name__ == "__main__":
    # 测试
    print("CDP状态:", get_cdp_status())
    print("确保CDP可用:", ensure_cdp_browser(auto_start=True))
    
    # 测试上下文管理器
    print("\n测试上下文管理器...")
    with CDPBrowserContext(port=9222, auto_start=True, auto_close=True) as browser:
        print(f"浏览器状态: {browser}")
        if browser['available']:
            print("执行采集任务...")
            import time
            time.sleep(3)
            print("采集任务完成")
    
    print("上下文管理器测试完成，浏览器应已自动关闭")

