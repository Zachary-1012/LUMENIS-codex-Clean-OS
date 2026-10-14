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
# No implicit worker is selected by a generic caller. XHS dynamic resolution is
# explicit (port=0) and remains bound to its existing registered identity.
DEFAULT_CDP_PORT = None
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
        if port is None:
            return False
        if int(port) == 0:
            return bool(resolve_registered_xhs_worker().get("available"))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            return result == 0
    except Exception:
        return False


def _normalized_profile_path(profile_dir):
    return os.path.normcase(os.path.realpath(os.path.abspath(
        os.path.normpath(str(profile_dir or ""))))).rstrip("\\/")


def _registered_xhs_binding(account=None):
    """Return only the existing approved HK/intl account and its exact profile."""
    try:
        import xhs_cookie_bridge as bridge
        account = str(account or bridge.DEFAULT_COLLECTION_ACCOUNT).strip().upper()
        if (account != bridge.XHS_RETINAUT_NAME
                or account != bridge.DEFAULT_COLLECTION_ACCOUNT
                or not bridge.XHS_RETINAUT
                or not bridge.collection_policy_gate(account=account, region="intl").get("ok")):
            return None
        entry = bridge.ACCOUNT_PROFILES.get(account)
        if not isinstance(entry, (tuple, list)) or len(entry) != 2 or not entry[1]:
            return None
        expected = os.path.realpath(os.path.join(
            bridge.PRIVATE_DATA_DIR, "profiles", "xhs-retinaut"))
        profile = os.path.realpath(os.path.abspath(os.path.expanduser(os.fspath(entry[1]))))
        if _normalized_profile_path(profile) != _normalized_profile_path(expected):
            return None
        if _is_default_user_browser_profile(profile):
            return None
        return {"account": account, "profile": profile, "browser": "edge"}
    except Exception:  # noqa: BLE001 - unavailable owner configuration must never select a fallback identity.
        return None


def _registered_edge_executable():
    """Find the installed Edge binary only from the existing SYSTEM registry."""
    conf = BROWSER_REGISTRY.get("edge") or {}
    for candidate in conf.get("exe_candidates", ()):
        if not candidate or not os.path.isfile(candidate):
            continue
        resolved = os.path.realpath(os.path.abspath(candidate))
        if ntpath.basename(resolved).casefold() == "msedge.exe":
            return resolved
    return None


def _switch_value(args, name):
    prefix = name.casefold() + "="
    lowered = [str(arg).strip().strip('"') for arg in (args or ())]
    for index, arg in enumerate(lowered):
        if arg.casefold().startswith(prefix):
            return arg.split("=", 1)[1]
        if arg.casefold() == name.casefold() and index + 1 < len(lowered):
            return lowered[index + 1]
    return None


def _read_devtools_active_port(profile_dir):
    """Read Chromium's ephemeral-port metadata from the registered profile only."""
    try:
        profile = os.path.realpath(profile_dir)
        active_file = os.path.realpath(os.path.join(profile, "DevToolsActivePort"))
        if os.path.commonpath([profile, active_file]) != profile:
            return None
        with open(active_file, "r", encoding="ascii") as handle:
            rows = handle.read(512).splitlines()
        if len(rows) < 2 or not rows[0].isdigit():
            return None
        port = int(rows[0])
        websocket_path = rows[1]
        if not (1 <= port <= 65535) or not websocket_path.startswith("/devtools/browser/"):
            return None
        if ".." in websocket_path or "\\" in websocket_path:
            return None
        return port
    except (OSError, UnicodeError, ValueError):
        return None


def _registered_xhs_profile_processes(binding):
    """Inspect exact-profile browser owners without reading Cookies or page data."""
    try:
        import psutil
    except ImportError:
        return [], True
    owners = []
    incomplete = False
    expected_profile = _normalized_profile_path(binding["profile"])
    expected_edge = _registered_edge_executable()
    try:
        processes = psutil.process_iter(["pid", "name", "cmdline"])
        for process in processes:
            try:
                name = str(process.info.get("name") or "").casefold()
                if name not in {"msedge.exe", "chrome.exe"}:
                    continue
                args = [str(arg).strip().strip('"')
                        for arg in (process.info.get("cmdline") or ())]
                # Chromium's renderer/utility/GPU children inherit --user-data-dir.
                # They are not independent browser owners or CDP workers. Keep
                # exact-profile main processes visible so an ambiguous or
                # non-CDP owner still fails closed below.
                if _switch_value(args, "--type"):
                    continue
                profile_arg = _switch_value(args, "--user-data-dir")
                if not profile_arg or _normalized_profile_path(profile_arg) != expected_profile:
                    continue
                pid = int(process.info.get("pid") or process.pid)
                exe = os.path.realpath(os.path.abspath(process.exe()))
                created = float(process.create_time())
                raw_port = _switch_value(args, "--remote-debugging-port")
                port = None
                if raw_port and raw_port.isdigit():
                    parsed_port = int(raw_port)
                    port = (_read_devtools_active_port(binding["profile"])
                            if parsed_port == 0 else parsed_port)
                lowered = [arg.casefold() for arg in args]
                owners.append({
                    "pid": pid,
                    "name": name,
                    "exe": exe,
                    "created": created,
                    "port": port,
                    "headless": any(arg in {"--headless", "--headless=new"}
                                     for arg in lowered),
                    "loopback": _switch_value(args, "--remote-debugging-address") == "127.0.0.1",
                    "trusted_kernel": bool(expected_edge and name == "msedge.exe"
                                           and _normalized_profile_path(exe)
                                           == _normalized_profile_path(expected_edge)),
                })
            except Exception:  # noqa: BLE001 - an unreadable process makes worker ownership ambiguous.
                # An inaccessible browser process can be using the registered profile.
                incomplete = True
    except Exception:  # noqa: BLE001 - any process-enumeration error leaves ownership unverified.
        return owners, True
    return owners, incomplete


def resolve_registered_xhs_worker(*, account=None, headless=None, port=None):
    """Resolve the active XHS worker from its registered HK profile and exact process."""
    binding = _registered_xhs_binding(account)
    if not binding:
        return {"available": False, "code": "XHS_REGISTERED_IDENTITY_UNAVAILABLE"}
    owners, incomplete = _registered_xhs_profile_processes(binding)
    if incomplete:
        return {"available": False, "code": "XHS_WORKER_OWNER_UNVERIFIED",
                "account": binding["account"]}
    if not owners:
        return {"available": False, "code": "XHS_REGISTERED_WORKER_UNAVAILABLE",
                "account": binding["account"], "profile": binding["profile"]}
    if len(owners) != 1:
        return {"available": False, "code": "XHS_WORKER_IDENTITY_AMBIGUOUS",
                "account": binding["account"]}
    owner = owners[0]
    if not owner["trusted_kernel"] or not owner["loopback"] or owner["port"] is None:
        return {"available": False, "code": "XHS_WORKER_IDENTITY_UNVERIFIED",
                "account": binding["account"], "pid": owner["pid"]}
    if owner["port"] in {9222, 9223, 9224, 9225, 9226, 9227, 9228}:
        return {"available": False, "code": "XHS_WORKER_RESERVED_ENDPOINT",
                "account": binding["account"], "pid": owner["pid"]}
    if port is not None and int(port) != owner["port"]:
        return {"available": False, "code": "XHS_WORKER_ENDPOINT_MISMATCH",
                "account": binding["account"]}
    if headless is not None and owner["headless"] is not bool(headless):
        return {"available": False, "code": "XHS_WORKER_MODE_MISMATCH",
                "account": binding["account"], "pid": owner["pid"]}
    listener_pids, listener_verified = _cdp_listener_pids(owner["port"])
    if not listener_verified or listener_pids != {owner["pid"]}:
        return {"available": False, "code": "XHS_WORKER_LISTENER_UNVERIFIED",
                "account": binding["account"], "pid": owner["pid"]}
    try:
        import psutil
        process = psutil.Process(owner["pid"])
        if float(process.create_time()) != owner["created"]:
            raise RuntimeError("PROCESS_IDENTITY_CHANGED")
        current_args = [str(arg).strip().strip('"') for arg in process.cmdline()]
        current_profile = _switch_value(current_args, "--user-data-dir")
        current_port = _switch_value(current_args, "--remote-debugging-port")
        if (not current_profile
                or _normalized_profile_path(current_profile) != _normalized_profile_path(binding["profile"])
                or current_port not in {str(owner["port"]), "0"}):
            raise RuntimeError("PROCESS_BINDING_CHANGED")
        current_pids, current_listener = _cdp_listener_pids(owner["port"])
        if not current_listener or current_pids != {owner["pid"]}:
            raise RuntimeError("LISTENER_BINDING_CHANGED")
    except Exception:  # noqa: BLE001 - any PID/profile/listener mismatch rejects the registered worker.
        return {"available": False, "code": "XHS_WORKER_IDENTITY_UNVERIFIED",
                "account": binding["account"]}
    return {"available": True, "account": binding["account"],
            "profile": binding["profile"], "browser": "edge", "port": owner["port"],
            "endpoint": f"http://127.0.0.1:{owner['port']}", "pid": owner["pid"],
            "headless": owner["headless"], "loopback_only": True}


def ensure_registered_xhs_worker(*, headless=True, launch_url="https://www.rednote.com",
                                 direct_connection=False, task_id=None, actor_ref=None):
    """Start/reuse only the exact registered Edge profile on an OS-assigned local port."""
    if headless is not True:
        _authorize_registered_xhs_human_worker(task_id=task_id, actor_ref=actor_ref)
    state = resolve_registered_xhs_worker(headless=headless)
    if state.get("available"):
        return {"success": True, "reused": True, **state}
    if state.get("code") not in {"XHS_REGISTERED_WORKER_UNAVAILABLE"}:
        return {"success": False, **state}
    binding = _registered_xhs_binding()
    if not binding:
        return {"success": False, "code": "XHS_REGISTERED_IDENTITY_UNAVAILABLE"}
    return start_cdp_browser(port=0, profile_dir=binding["profile"],
                             headless=headless, loopback_only=True,
                             launch_url=launch_url, browser="edge",
                             direct_connection=direct_connection,
                             task_id=task_id, actor_ref=actor_ref)


def _authorize_registered_xhs_human_worker(*, task_id=None, actor_ref=None):
    """Visible XHS workers require the current task actor and existing lease."""
    from lumenis.adapters.human_browser import _authorize_human_interactive
    task_platform = _authorize_human_interactive(
        "XHS_RETINAUT", task_id or "", actor_ref)
    from lumenis.adapters import collector_service
    if not collector_service.human_browser_lease_owned(task_id or "", task_platform):
        raise PermissionError("HUMAN_INTERACTIVE_BROWSER_LEASE_REQUIRED")
    return task_platform


def registered_cdp_profile_for_port(port, browser=None):
    """Resolve a protected/general port or one exact configured local worker."""
    port = int(port)
    if port in {9222, 9223}:  # Protected legacy/personal ports are never workers.
        return None
    if port == 0:
        binding = _registered_xhs_binding()
        return binding["profile"] if binding else None
    try:
        if port == 9224:
            import browser_surface
            selected = browser or system_default_cdp_browser()
            return (os.path.abspath(browser_surface._general_profile_dir(selected))
                    if selected in {"chrome", "edge"} else None)
        from lumenis.adapters.human_browser import readonly_worker_spec
        from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES

        rows = []
        for platform, config in PLATFORM_CAPABILITIES.items():
            worker = config.get("readonly_worker") if isinstance(config, dict) else None
            if not isinstance(worker, dict):
                continue
            try:
                worker_port = int(worker["port"])
            except (KeyError, TypeError, ValueError):
                worker_port = None
            rows.append({
                "platform": platform,
                "port": worker_port,
                "account": str(worker.get("account") or "").strip().casefold(),
                "profile": str(worker.get("profile") or "").strip(),
            })

        def profile_key(value):
            normalized = ntpath.normpath(str(value or "").strip().replace("/", "\\"))
            return ntpath.normcase(normalized).casefold()

        matches = [row for row in rows if row["port"] == port]
        if matches:
            if len(matches) != 1:
                return None
            row = matches[0]
            if (port < 1024 or port > 65535 or port in {9222, 9223, 9224}
                    or not row["account"] or not row["profile"]
                    or sum(item["port"] == port for item in rows) != 1
                    or sum(item["account"] == row["account"] for item in rows) != 1
                    or sum(profile_key(item["profile"]) == profile_key(row["profile"])
                           for item in rows) != 1):
                return None
            spec = readonly_worker_spec(row["platform"])
            if (int(spec["port"]) != port
                    or str(spec["account"]).strip().casefold() != row["account"]
                    or ntpath.basename(str(spec["profile"]).rstrip("\\/")).casefold()
                    != row["profile"].casefold()):
                return None
            return spec["profile"]

        # XHS is the only dynamic SYSTEM worker; unregistered static ports fail closed.
        xhs = resolve_registered_xhs_worker(port=port)
        if xhs.get("available"):
            return xhs["profile"]
    except Exception:
        return None
    return None


def _profile_binding_allowed(port, profile_dir, browser=None):
    port = int(port)
    xhs_binding = _registered_xhs_binding()
    if port == 0:
        return bool(xhs_binding and browser == "edge"
                    and _normalized_profile_path(xhs_binding["profile"])
                    == _normalized_profile_path(profile_dir))
    if xhs_binding and _normalized_profile_path(profile_dir) == _normalized_profile_path(
            xhs_binding["profile"]):
        if port in {9222, 9223, 9224, 9225, 9226, 9227, 9228} or browser not in {None, "edge"}:
            return False
        from lumenis.system.collector.adapters.config import PLATFORM_CAPABILITIES
        if any(isinstance(config, dict)
               and isinstance(config.get("readonly_worker"), dict)
               and int(config["readonly_worker"].get("port", -1)) == port
               for config in PLATFORM_CAPABILITIES.values()):
            return False
        state = resolve_registered_xhs_worker(port=port)
        return bool(state.get("available") and state.get("port") == port)
    if port in {9222, 9223}:
        return False
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
                port = int(debug_port) if debug_port and debug_port.isdigit() else None
                if port == 0:
                    port = _read_devtools_active_port(profile_dir)
                owners.append({"pid": int(proc.info.get("pid") or proc.pid), "name": name,
                               "port": port,
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
    effective_port = debug_port
    if debug_port == "0":
        effective_port = str(_read_devtools_active_port(profile_dir) or "")
    return bool(profile and _normalized_profile_path(profile) == _normalized_profile_path(profile_dir)
                and effective_port == str(int(port)) and loopback
                and (headless is None or is_headless is bool(headless)))


def is_cdp_profile_running(port, profile_dir, *, headless=None, loopback_only=True,
                           browser=None):
    """Verify the listening socket is owned by this exact profile/browser/mode worker."""
    if int(port) == 0:
        state = resolve_registered_xhs_worker(headless=headless)
        return bool(state.get("available") and profile_dir
                    and _normalized_profile_path(state["profile"])
                    == _normalized_profile_path(profile_dir)
                    and (browser is None or browser == state["browser"]))
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
        if port == 0:
            state = resolve_registered_xhs_worker(headless=headless)
            if (state.get("available") and (profile_dir is None
                    or _normalized_profile_path(profile_dir)
                    == _normalized_profile_path(state["profile"]))):
                return state["browser"]
            return None
        if port == 9224:
            if profile_dir:
                profiles = [profile_dir]
            else:
                profiles = [registered_cdp_profile_for_port(port, browser=name)
                            for name in ("chrome", "edge")]
        else:
            registered_profile = registered_cdp_profile_for_port(port)
            if (not registered_profile or (profile_dir and
                    _normalized_profile_path(profile_dir)
                    != _normalized_profile_path(registered_profile))):
                return None
            profiles = [registered_profile]
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
                      loopback_only=True, task_id=None, actor_ref=None):
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
    if port is None:
        return {"success": False, "code": "BROWSER_WORKER_ENDPOINT_REQUIRED",
                "message": "通用浏览器调用必须指定并核验已有注册端点", "port": None, "pid": None}
    port = int(port)
    if port == 9222:
        return {"success": False, "code": "PROTECTED_PROFILE_FORBIDDEN",
                "message": "受保护的9222身份不能由自动浏览器路径启动或复用", "port": port, "pid": None}
    if browser in UNSUPPORTED_ON_WINDOWS:
        return {"success": False, "message": UNSUPPORTED_ON_WINDOWS[browser], "port": port, "pid": None}
    if profile_dir is None:
        profile_dir = default_profile_for(browser)
    if port == 0:
        binding = _registered_xhs_binding()
        if (not binding or browser != "edge"
                or _normalized_profile_path(profile_dir) != _normalized_profile_path(binding["profile"])):
            return {"success": False, "code": "DYNAMIC_PORT_REQUIRES_REGISTERED_XHS_PROFILE",
                    "message": "动态 CDP 仅允许绑定已登记的香港/国际 RedNote Profile",
                    "port": 0, "pid": None}
        if headless is not True:
            _authorize_registered_xhs_human_worker(task_id=task_id, actor_ref=actor_ref)
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
    edge_path = (_registered_edge_executable() if port == 0 else find_browser_path(browser))
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
            if port == 0:
                state = resolve_registered_xhs_worker(headless=headless)
                if state.get("available"):
                    return {"success": True, "message": "已验证注册的动态 CDP Worker",
                            "port": state["port"], "pid": state["pid"], "reused": False,
                            "endpoint": state["endpoint"], "account": state["account"]}
                continue
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
                       headless=True, loopback_only=True, task_id=None,
                       actor_ref=None, **launch_kwargs):
    """Reuse or start only the exact local profile and browser mode requested."""
    browser = (launch_kwargs.get("browser") or "edge").lower()
    selected_profile = profile_dir or default_profile_for(browser)
    if port is None:
        return {"available": False, "code": "BROWSER_WORKER_ENDPOINT_REQUIRED",
                "port": None, "auto_started": False}
    if int(port) == 0:
        binding = _registered_xhs_binding()
        if (not binding or browser != "edge"
                or _normalized_profile_path(selected_profile)
                != _normalized_profile_path(binding["profile"])):
            return {"available": False, "code": "DYNAMIC_PORT_REQUIRES_REGISTERED_XHS_PROFILE",
                    "port": None, "auto_started": False}
        state = resolve_registered_xhs_worker(headless=headless)
        if state.get("available"):
            return {"available": True, "code": "WORKER_REUSED", "port": state["port"],
                    "endpoint": state["endpoint"], "pid": state["pid"],
                    "auto_started": False, "reused": True}
        if not auto_start:
            return {"available": False, "code": state.get("code") or "BROWSER_WORKER_UNAVAILABLE",
                    "port": None, "auto_started": False}
        if headless is not True:
            _authorize_registered_xhs_human_worker(task_id=task_id, actor_ref=actor_ref)
        result = start_cdp_browser(0, selected_profile, headless=headless,
                                   loopback_only=loopback_only, task_id=task_id,
                                   actor_ref=actor_ref, **launch_kwargs)
        return {"available": result.get("success") is True,
                "message": result.get("message"), "code": result.get("code"),
                "port": result.get("port"), "endpoint": result.get("endpoint"),
                "auto_started": result.get("success") is True,
                "pid": result.get("pid"), "reused": result.get("reused") is True}
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
    try:
        requested_port = int(port)
    except (TypeError, ValueError):
        return {"success": False, "code": "WORKER_ENDPOINT_INVALID", "port": None}
    if requested_port == 0:
        state = resolve_registered_xhs_worker(headless=headless)
        if (not state.get("available") or not profile_dir
                or _normalized_profile_path(profile_dir)
                != _normalized_profile_path(state.get("profile"))
                or (browser is not None and browser != state.get("browser"))):
            return {"success": False,
                    "code": state.get("code") or "WORKER_IDENTITY_UNVERIFIED",
                    "port": None}
        port = int(state["port"])
        profile_dir = state["profile"]
        browser = state["browser"]
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
    try:
        port = int(port)
    except (TypeError, ValueError):
        return 0
    if port == 0:
        state = resolve_registered_xhs_worker(headless=True)
        if not state.get("available"):
            return 0
        port = int(state["port"])
    elif port in {9222, 9223}:
        return 0
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
    if port is None:
        return {"port": None, "available": False, "endpoint": None,
                "browser": None, "profile_dir": None,
                "code": "BROWSER_WORKER_ENDPOINT_REQUIRED"}
    if int(port) == 0:
        state = resolve_registered_xhs_worker()
        return {"port": state.get("port"), "available": state.get("available") is True,
                "endpoint": state.get("endpoint"), "browser": state.get("browser"),
                "profile_dir": state.get("profile"), "code": state.get("code")}
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
        if port == 0:
            state = resolve_registered_xhs_worker(headless=True)
            if not state.get("available"):
                return {"success": False, "code": state.get("code") or "WORKER_IDENTITY_UNVERIFIED",
                        "port": None}
            port = int(state["port"])
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
        worker = resolve_registered_xhs_worker(headless=True)
        if worker['available']:
            with CDPBrowserContext(
                    port=worker['port'], profile_dir=worker['profile'],
                    headless=True, browser=worker['browser']) as browser:
                if browser['available']:
                    do_collect()
        # Context exits stop only a verified worker started by this context.
    
    参考GitHub实际应用：
    - albertofwb/douyin-publisher: chrome_utils.py
    """
    
    def __init__(self, port=DEFAULT_CDP_PORT, profile_dir=None, auto_start=True,
                 auto_close=True, headless=True, browser=None):
        self.port = int(port) if port is not None else None
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
        if self.port is None or not self.headless or self.port == 9222:
            self.browser_info = {"available": False, "code": "BACKGROUND_WORKER_CONFIGURATION_INVALID",
                                 "message": "Automatic CDP requires an explicit registered headless worker",
                                 "port": self.port, "auto_started": False}
            return self.browser_info
        if self.port == 0:
            binding = _registered_xhs_binding()
            if (not binding or (self.profile_dir is not None
                    and _normalized_profile_path(self.profile_dir)
                    != _normalized_profile_path(binding["profile"]))
                    or self.browser not in {None, "edge"}):
                self.browser_info = {"available": False,
                                     "code": "DYNAMIC_PORT_REQUIRES_REGISTERED_XHS_PROFILE",
                                     "port": None, "auto_started": False}
                return self.browser_info
            self.browser = "edge"
            self.profile_dir = binding["profile"]
            state = resolve_registered_xhs_worker(headless=True)
            if state.get("available"):
                self.port = int(state["port"])
                self.browser_info = {"available": True, "code": "WORKER_REUSED",
                                     "port": self.port, "endpoint": state["endpoint"],
                                     "pid": state["pid"], "auto_started": False,
                                     "was_running": True}
                self.was_running = True
                return self.browser_info
            if not self.auto_start:
                self.browser_info = {"available": False,
                                     "code": state.get("code") or "BROWSER_WORKER_UNAVAILABLE",
                                     "port": None, "auto_started": False}
                return self.browser_info
            result = start_cdp_browser(
                0, self.profile_dir, headless=True, loopback_only=True,
                browser="edge", launch_url="https://www.rednote.com")
            if result.get("success") is True and result.get("port"):
                self.port = int(result["port"])
                self.started_by_self = True
                self.browser_info = {**result, "available": True,
                                     "auto_started": True, "was_running": False}
                return self.browser_info
            self.browser_info = {**result, "available": False, "auto_started": False}
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
        
        results = auto_collect_with_cdp(my_collect, keyword="user-supplied topic")
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
    with CDPBrowserContext(port=0, auto_start=True, auto_close=True) as browser:
        print(f"浏览器状态: {browser}")
        if browser['available']:
            print("执行采集任务...")
            import time
            time.sleep(3)
            print("采集任务完成")
    
    print("上下文管理器测试完成，浏览器应已自动关闭")

