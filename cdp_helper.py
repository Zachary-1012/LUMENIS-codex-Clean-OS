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


def _normalized_profile_path(profile_dir):
    return os.path.normcase(os.path.abspath(os.path.normpath(str(profile_dir or "")))).rstrip("\\/")


def registered_cdp_profile_for_port(port, browser=None):
    """Resolve the existing SYSTEM owner for a reserved local browser port."""
    port = int(port)
    if port == 9222:  # Protected Mainland personal profile: never an automatic worker.
        return None
    try:
        if port == 9223:
            import xhs_cookie_bridge as bridge
            account = getattr(bridge, "XHS_RETINAUT_NAME", "XHS_RETINAUT")
            binding = bridge.ACCOUNT_PROFILES.get(account)
            profile = binding.get("profile") if isinstance(binding, dict) else binding[1]
            if not os.path.isabs(profile):
                profile = os.path.join(os.path.dirname(os.path.abspath(__file__)), profile)
            return os.path.abspath(profile)
        if port == 9224:
            import browser_surface
            selected = browser or system_default_cdp_browser()
            return (os.path.abspath(browser_surface._general_profile_dir(selected))
                    if selected in {"chrome", "edge"} else None)
        if port in {9225, 9226, 9227, 9228}:
            from pathlib import Path
            from lumenis.adapters.cookie_vault import _current_data_dir
            from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES
            profile_root = (Path(_current_data_dir()) / "private" / "profiles").resolve()
            for config in PLATFORM_CAPABILITIES.values():
                worker = config.get("readonly_worker") if isinstance(config, dict) else None
                if isinstance(worker, dict) and int(worker.get("port", -1)) == port:
                    return str((profile_root / worker["profile"]).resolve())
            return None
    except Exception:
        return None
    return None


def _profile_binding_allowed(port, profile_dir, browser=None):
    port = int(port)
    if port not in {9222, 9223, 9224, 9225, 9226, 9227, 9228}:
        return True
    if port == 9224 and browser is None:
        expected_profiles = [registered_cdp_profile_for_port(port, browser=name)
                            for name in ("chrome", "edge")]
        candidate = _normalized_profile_path(profile_dir)
        return any(expected and _normalized_profile_path(expected) == candidate
                   for expected in expected_profiles)
    expected = registered_cdp_profile_for_port(port, browser=browser)
    return bool(expected and _normalized_profile_path(expected) == _normalized_profile_path(profile_dir))


def _profile_processes(profile_dir):
    """Return exact profile owners and whether process inspection was incomplete."""
    try:
        import psutil
    except Exception:
        return [], True
    expected_profile = _normalized_profile_path(profile_dir)
    owners = []
    incomplete = False
    try:
        processes = psutil.process_iter(["pid", "name", "cmdline"])
        for proc in processes:
            try:
                name = str(proc.info.get("name") or "").casefold()
                if name not in {"msedge.exe", "chrome.exe"}:
                    continue
                args = [str(arg).strip().strip('"') for arg in (proc.info.get("cmdline") or [])]
                profile = None
                for index, arg in enumerate(args):
                    lower = arg.casefold()
                    if lower.startswith("--user-data-dir="):
                        profile = arg.split("=", 1)[1]
                        break
                    if lower == "--user-data-dir" and index + 1 < len(args):
                        profile = args[index + 1]
                        break
                if profile is None or _normalized_profile_path(profile) != expected_profile:
                    continue
                lowered = [arg.casefold() for arg in args]
                debug_port = None
                for index, arg in enumerate(lowered):
                    if arg.startswith("--remote-debugging-port="):
                        debug_port = arg.split("=", 1)[1]
                        break
                    if arg == "--remote-debugging-port" and index + 1 < len(lowered):
                        debug_port = lowered[index + 1]
                        break
                loopback = any(arg == "--remote-debugging-address=127.0.0.1"
                               for arg in lowered)
                headless = any(arg in {"--headless", "--headless=new"}
                               for arg in lowered)
                owners.append({"pid": int(proc.info.get("pid") or proc.pid), "name": name,
                               "port": int(debug_port) if debug_port and debug_port.isdigit() else None,
                               "headless": headless, "loopback": loopback})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError, ValueError):
                incomplete = True
    except Exception:
        return owners, True
    return owners, incomplete


def _cdp_listener_pids(port):
    """Return loopback listener PIDs for the exact port; fail closed if ambiguous."""
    try:
        import ipaddress
        import psutil
        listeners = [conn for conn in psutil.net_connections(kind="inet")
                     if conn.status == psutil.CONN_LISTEN and conn.laddr
                     and int(conn.laddr.port) == int(port)]
    except Exception:
        return set(), False
    if not listeners:
        return set(), False
    pids = set()
    for conn in listeners:
        try:
            address = ipaddress.ip_address(str(conn.laddr.ip))
            mapped = getattr(address, "ipv4_mapped", None)
            if not address.is_loopback and not (mapped and mapped.is_loopback):
                return set(), False
            if conn.pid is None:
                return set(), False
            pids.add(int(conn.pid))
        except (TypeError, ValueError, AttributeError):
            return set(), False
    return pids, bool(pids)


def _cdp_process_matches(pid, port, profile_dir, *, headless=None, browser=None):
    """Inspect the exact listener process instead of unrelated browser processes."""
    try:
        import psutil
        proc = psutil.Process(int(pid))
        name = str(proc.name() or "").casefold()
        args = [str(arg).strip().strip('"') for arg in proc.cmdline()]
    except Exception:
        return False
    known_browser_processes = {"msedge.exe", "chrome.exe"}
    if name not in known_browser_processes:
        return False
    expected_process = {"edge": "msedge.exe", "chrome": "chrome.exe"}.get(str(browser or "").lower())
    if expected_process and name != expected_process:
        return False
    profile = None
    debug_port = None
    for index, arg in enumerate(args):
        lowered = arg.casefold()
        if lowered.startswith("--user-data-dir="):
            profile = arg.split("=", 1)[1]
        elif lowered == "--user-data-dir" and index + 1 < len(args):
            profile = args[index + 1]
        if lowered.startswith("--remote-debugging-port="):
            debug_port = arg.split("=", 1)[1]
        elif lowered == "--remote-debugging-port" and index + 1 < len(args):
            debug_port = args[index + 1]
    lowered_args = [arg.casefold() for arg in args]
    is_headless = any(arg in {"--headless", "--headless=new"} for arg in lowered_args)
    loopback = "--remote-debugging-address=127.0.0.1" in lowered_args
    return bool(profile and _normalized_profile_path(profile) == _normalized_profile_path(profile_dir)
                and debug_port == str(int(port)) and loopback
                and (headless is None or is_headless is bool(headless)))


def is_cdp_profile_running(port, profile_dir, *, headless=None, loopback_only=True,
                           browser=None):
    """Verify the listening socket is owned by this exact profile/browser/mode worker."""
    if not profile_dir or not _profile_binding_allowed(port, profile_dir, browser=browser):
        return False
    listener_pids, verified_listener = _cdp_listener_pids(port)
    if not verified_listener or len(listener_pids) != 1:
        return False
    return all(_cdp_process_matches(
        pid, port, profile_dir, headless=headless, browser=browser)
        for pid in listener_pids)




def registered_cdp_browser_for_port(port, profile_dir=None, *, headless=None):
    """Resolve the engine only from an exact registered profile and CDP listener."""
    try:
        port = int(port)
        if port not in {9223, 9224, 9225, 9226, 9227, 9228}:
            return None
        if profile_dir:
            profiles = [profile_dir]
        elif port == 9224:
            profiles = [registered_cdp_profile_for_port(port, browser=name)
                        for name in ("chrome", "edge")]
        else:
            profile = registered_cdp_profile_for_port(port)
            profiles = [profile] if profile else []
        listener_pids, verified_listener = _cdp_listener_pids(port)
        if not verified_listener or len(listener_pids) != 1:
            return None
        pid = next(iter(listener_pids))
        import psutil
        process = psutil.Process(pid)
        created = process.create_time()
        process_name = str(process.name() or "").casefold()
        browser = {"chrome.exe": "chrome", "msedge.exe": "edge"}.get(process_name)
        if not browser:
            return None
        for profile in profiles:
            if not profile or not _profile_binding_allowed(port, profile):
                continue
            if not _profile_binding_allowed(port, profile, browser=browser):
                continue
            if not _cdp_process_matches(
                    pid, port, profile, headless=headless, browser=browser):
                continue
            if psutil.Process(pid).create_time() != created:
                return None
            current_pids, current_listener = _cdp_listener_pids(port)
            if not current_listener or current_pids != listener_pids:
                return None
            return browser
        return None
    except Exception:
        return None


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


def start_cdp_browser(port=DEFAULT_CDP_PORT, profile_dir=None, headless=True,
                      proxy_server=None, launch_url="https://www.xiaohongshu.com",
                      anti_automation=True, browser="edge", direct_connection=False,
                      loopback_only=True):
    """
    启动带 CDP 调试端口的指定 Chromium 浏览器。
    
    Args:
        port: CDP调试端口
        profile_dir: 用户数据目录
        headless: 是否无头模式
    
    Returns:
        dict: {success: bool, message: str, port: int, pid: int}
    """
    browser = (browser or "edge").lower()
    port = int(port)
    if port == 9222:
        return {"success": False, "code": "PROTECTED_PROFILE_FORBIDDEN",
                "message": "受保护的9222身份不能由自动浏览器路径启动或复用", "port": port, "pid": None}
    if browser in UNSUPPORTED_ON_WINDOWS:
        return {"success": False, "message": UNSUPPORTED_ON_WINDOWS[browser], "port": port, "pid": None}
    if profile_dir is None:
        profile_dir = default_profile_for(browser)
    if not _profile_binding_allowed(port, profile_dir, browser=browser):
        return {"success": False, "code": "PORT_PROFILE_BINDING_MISMATCH",
                "message": f"CDP端口 {port} 与请求的隔离Profile不匹配", "port": port, "pid": None}
    if _is_default_user_browser_profile(profile_dir):
        return {"success": False, "code": "USER_PROFILE_FORBIDDEN",
                "message": "自动浏览器不能接管用户日常Chrome/Edge Profile", "port": port, "pid": None}
    if not loopback_only:
        return {"success": False, "code": "NON_LOOPBACK_CDP_FORBIDDEN",
                "message": "SYSTEM浏览器Worker只允许绑定本机回环地址", "port": port, "pid": None}

    if is_cdp_port_open(port):
        if is_cdp_profile_running(port, profile_dir, headless=headless,
                                  loopback_only=True, browser=browser):
            listener_pids, verified_listener = _cdp_listener_pids(port)
            if not verified_listener or len(listener_pids) != 1:
                return {"success": False, "code": "PORT_IN_USE_UNVERIFIED",
                        "message": f"CDP端口 {port} 的监听进程不唯一或无法核实", "port": port, "pid": None}
            return {"success": True, "message": f"已复用端口 {port} 的精确Profile/模式Worker",
                    "port": port, "pid": next(iter(listener_pids)), "reused": True}
        return {"success": False, "code": "PORT_IN_USE_UNVERIFIED",
                "message": f"CDP端口 {port} 已被不同身份或浏览器模式占用", "port": port, "pid": None}
    owners, incomplete = _profile_processes(profile_dir)
    if incomplete:
        return {"success": False, "code": "PROFILE_OWNER_UNVERIFIED",
                "message": "无法核实隔离Profile进程归属，拒绝重复启动", "port": port, "pid": None}
    if owners:
        return {"success": False, "code": "PROFILE_IN_USE_UNVERIFIED",
                "message": f"Profile已被不同端口或模式的浏览器使用", "port": port, "pid": owners[0]["pid"]}
    edge_path = find_browser_path(browser)
    if not edge_path:
        return {"success": False, "message": f"未找到 {browser} 浏览器，请安装或改用其他内核", "port": port, "pid": None}

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
            if is_cdp_profile_running(
                    port, profile_dir, headless=headless, loopback_only=True, browser=browser):
                listener_pids, verified_listener = _cdp_listener_pids(port)
                if verified_listener and len(listener_pids) == 1:
                    return {"success": True, "message": f"{browser} Profile/模式已核实，CDP端口 {port} 就绪",
                            "port": port, "pid": next(iter(listener_pids)),
                            "reused": False}
            if is_cdp_port_open(port):
                return {"success": False, "code": "STARTED_WORKER_UNVERIFIED",
                        "message": f"CDP端口 {port} 可连接，但启动参数与Profile归属未核实",
                        "port": port, "pid": proc.pid}
        
        return {"success": False, "code": "CDP_START_TIMEOUT",
                "message": f"{browser} 浏览器CDP端口 {port} 未就绪", "port": port, "pid": proc.pid}
    
    except Exception as e:
        logger.error("启动 %s 浏览器失败: %s", browser, e)
        return {"success": False, "message": f"启动 {browser} 浏览器失败: {str(e)}", "port": port, "pid": None}


def ensure_cdp_browser(port=DEFAULT_CDP_PORT, profile_dir=None, auto_start=True,
                       headless=True, loopback_only=True, **launch_kwargs):
    """Reuse or start only the exact local profile and browser mode requested."""
    browser = (launch_kwargs.get("browser") or "edge").lower()
    selected_profile = profile_dir or default_profile_for(browser)
    if int(port) == 9222:
        return {"available": False, "code": "PROTECTED_PROFILE_FORBIDDEN",
                "message": "受保护的9222身份不能由自动浏览器路径启动或复用",
                "port": int(port), "auto_started": False}
    if not _profile_binding_allowed(port, selected_profile, browser=browser):
        return {"available": False, "code": "PORT_PROFILE_BINDING_MISMATCH",
                "message": f"CDP端口 {port} 与请求的隔离Profile不匹配",
                "port": int(port), "auto_started": False}
    if is_cdp_port_open(port):
        if is_cdp_profile_running(port, selected_profile, headless=headless,
                                  loopback_only=True, browser=browser):
            return {"available": True, "message": f"CDP端口 {port} 的Profile与模式已核实",
                    "port": int(port), "auto_started": False, "reused": True}
        return {"available": False, "code": "PORT_IN_USE_UNVERIFIED",
                "message": f"CDP端口 {port} 已被不同身份或浏览器模式占用",
                "port": int(port), "auto_started": False}
    if not auto_start:
        return {"available": False, "code": "BROWSER_WORKER_UNAVAILABLE",
                "message": f"精确的后台浏览器Worker端口 {port} 未启动",
                "port": int(port), "auto_started": False}

    result = start_cdp_browser(port, selected_profile, headless=headless,
                               loopback_only=loopback_only, **launch_kwargs)
    return {"available": result.get("success") is True,
            "message": result.get("message"), "code": result.get("code"),
            "port": int(port), "auto_started": result.get("success") is True,
            "pid": result.get("pid"), "reused": result.get("reused") is True}


def _is_default_user_browser_profile(profile_dir):
    """Reject Chrome/Edge's daily user-data roots before any launch or attach."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return False
    candidate = _normalized_profile_path(profile_dir)
    roots = (
        os.path.join(local_appdata, "Google", "Chrome", "User Data"),
        os.path.join(local_appdata, "Microsoft", "Edge", "User Data"),
    )
    for root in roots:
        normalized_root = _normalized_profile_path(root)
        try:
            if os.path.commonpath([candidate, normalized_root]) == normalized_root:
                return True
        except ValueError:
            continue
    return False


def close_cdp_browser(port, profile_dir, *, headless=True, browser=None, timeout=8):
    """Request graceful Browser.close only for an exact, verified LUMENIS worker."""
    if browser is None:
        browser = registered_cdp_browser_for_port(port, profile_dir, headless=headless)
    if not browser or not is_cdp_profile_running(
            port, profile_dir, headless=headless, loopback_only=True, browser=browser):
        return {"success": False, "code": "WORKER_IDENTITY_UNVERIFIED", "port": int(port)}
    try:
        import json
        import urllib.request
        from urllib.parse import urlsplit
        version_req = urllib.request.Request(f"http://127.0.0.1:{int(port)}/json/version")
        with urllib.request.urlopen(version_req, timeout=3) as response:
            version = json.loads(response.read().decode("utf-8"))
        endpoint = urlsplit(str(version.get("webSocketDebuggerUrl") or ""))
        if (endpoint.scheme != "ws" or endpoint.hostname not in {"127.0.0.1", "localhost", "::1"}
                or endpoint.port != int(port)):
            return {"success": False, "code": "WORKER_WEBSOCKET_UNVERIFIED", "port": int(port)}
        import websocket
        connection = websocket.create_connection(endpoint.geturl(), timeout=3)
        try:
            connection.send(json.dumps({"id": 1, "method": "Browser.close"}))
        finally:
            connection.close()
        deadline = time.time() + max(1, int(timeout))
        while time.time() < deadline:
            owners, incomplete = _profile_processes(profile_dir)
            if not incomplete and not is_cdp_port_open(port) and not owners:
                return {"success": True, "code": "WORKER_CLOSED_GRACEFULLY", "port": int(port)}
            time.sleep(0.2)
        return {"success": False, "code": "WORKER_CLOSE_NOT_CONFIRMED", "port": int(port)}
    except Exception:
        return {"success": False, "code": "WORKER_CLOSE_UNAVAILABLE", "port": int(port)}


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
    """Gracefully close only an exact registered headless worker; never kill by port alone."""
    try:
        port = int(port)
        browser = registered_cdp_browser_for_port(port, headless=True)
        profile = (registered_cdp_profile_for_port(port, browser=browser)
                   if browser else None)
        if not browser or not profile or not is_cdp_profile_running(
                port, profile, headless=True, loopback_only=True, browser=browser):
            return {"success": False, "code": "WORKER_IDENTITY_UNVERIFIED", "port": port}
        result = close_cdp_browser(port, profile, headless=True, browser=browser)
        return {"success": result.get("success") is True,
                "code": result.get("code", "WORKER_CLOSE_UNAVAILABLE"),
                "port": port}
    except Exception:
        logger.exception("Refused unsafe CDP browser stop")
        return {"success": False, "code": "WORKER_CLOSE_UNAVAILABLE", "port": port}





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
    
    def __init__(self, port=DEFAULT_CDP_PORT, profile_dir=None, auto_start=True,
                 auto_close=True, headless=True, browser=None):
        self.port = int(port)
        self.profile_dir = profile_dir
        self.auto_start = auto_start
        self.auto_close = auto_close
        self.headless = bool(headless)
        self.browser = browser
        self.browser_info = None
        self.was_running = False
        self.started_by_self = False

    def __enter__(self):
        """Attach or start only the exact registered BACKGROUND worker."""
        if not self.headless or self.port == 9222:
            self.browser_info = {"available": False, "code": "BACKGROUND_WORKER_CONFIGURATION_INVALID",
                                 "message": "Automatic CDP is limited to registered headless workers",
                                 "port": self.port, "auto_started": False}
            return self.browser_info
        port_open = is_cdp_port_open(self.port)
        if port_open:
            browser = registered_cdp_browser_for_port(
                self.port, self.profile_dir, headless=True)
            if not browser or (self.browser and self.browser != browser):
                self.browser_info = {"available": False, "code": "PORT_IN_USE_UNVERIFIED",
                                     "message": "CDP listener does not match the registered profile and mode",
                                     "port": self.port, "auto_started": False}
                return self.browser_info
        else:
            browser = self.browser or system_default_cdp_browser()
        profile = self.profile_dir or registered_cdp_profile_for_port(self.port, browser=browser)
        self.browser = browser
        self.profile_dir = profile
        if browser not in {"chrome", "edge"} or not profile:
            self.browser_info = {"available": False, "code": "BACKGROUND_WORKER_CONFIGURATION_INVALID",
                                 "message": "Automatic CDP is limited to registered headless workers",
                                 "port": self.port, "auto_started": False}
            return self.browser_info

        if port_open:
            if is_cdp_profile_running(self.port, profile, headless=True,
                                      loopback_only=True, browser=browser):
                self.was_running = True
                self.browser_info = {"available": True, "code": "WORKER_REUSED",
                                     "message": "Verified registered headless Worker reused",
                                     "port": self.port, "auto_started": False,
                                     "was_running": True}
            else:
                self.browser_info = {"available": False, "code": "PORT_IN_USE_UNVERIFIED",
                                     "message": "CDP port, profile or mode does not match",
                                     "port": self.port, "auto_started": False}
            return self.browser_info

        if not self.auto_start:
            self.browser_info = {"available": False, "code": "BROWSER_WORKER_UNAVAILABLE",
                                 "message": "Verified headless Worker is unavailable; automatic start is disabled",
                                 "port": self.port, "auto_started": False}
            return self.browser_info
        result = ensure_cdp_browser(
            self.port, profile, auto_start=True, headless=True, loopback_only=True,
            browser=browser)
        self.started_by_self = result.get("available") is True and result.get("auto_started") is True
        self.was_running = result.get("available") is True and not self.started_by_self
        self.browser_info = {**result, "was_running": self.was_running}
        return self.browser_info


    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close only a verified Worker this context started itself."""
        if self.auto_close and self.started_by_self and self.browser_info:
            result = close_cdp_browser(
                self.port, self.profile_dir, headless=True, browser=self.browser)
            if not result.get("success"):
                logger.warning("自动启动Worker未能确认优雅退出: %s", result.get("code"))
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

