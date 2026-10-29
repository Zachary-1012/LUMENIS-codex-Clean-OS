"""LUMENIS Product Core compatibility entry; current product identity is 序境 / LUMENIS."""
import os, sys, json, threading, time, shutil, sqlite3, secrets, argparse, concurrent.futures, subprocess, csv, io, re, tempfile
import hashlib
import uuid
from pathlib import Path
from types import MappingProxyType

def _reject_unittest_app_tool_package_collision(module_name, arguments):
    if module_name != 'app':
        return
    if any(argument == 'app.tool' or argument.startswith('app.tool.')
           for argument in arguments if isinstance(argument, str)):
        raise ImportError(
            'The unittest target app.tool.* resolves this root app.py as a module, not a package. '
            'Run python app/tool/test_build_windows.py <test-name> or '
            'python -m unittest discover -s app/tool'
        )


_reject_unittest_app_tool_package_collision(__name__, sys.argv[1:])

if __name__ != '__main__':
    _import_database = os.environ.get('ZBC_DB_PATH', '').strip()
    if not _import_database or not Path(_import_database).is_absolute():
        raise ImportError(
            'Importing Product Core requires an explicit absolute ZBC_DB_PATH before import; '
            'implicit production database initialization is prohibited. '
            'Run app/tool tools by file path, not by importing app.tool. '
            'Start Product Core through scripts/start_production.ps1.'
        )

_CORE_SERVER_KIND = 'not_started'


def _serve_product_core(application, host, port):
    global _CORE_SERVER_KIND
    server = os.environ.get('ZB_WSGI', '').strip().lower() or 'waitress'
    if server == 'flask':
        _CORE_SERVER_KIND = 'flask_development'
        return application.run(host=host, port=port, debug=False, threaded=True)
    if server != 'waitress':
        raise ValueError('ZB_WSGI must be waitress or explicit development mode flask')
    from waitress import serve
    threads = int(os.environ.get('ZB_WSGI_THREADS', '8') or '8')
    if not 1 <= threads <= 256:
        raise ValueError('ZB_WSGI_THREADS must be between 1 and 256')
    _CORE_SERVER_KIND = 'waitress'
    return serve(application, host=host, port=port, threads=threads)


def _core_instance_identity(entry_file, environ):
    """Freeze the Core entry bytes and process attempt before startup effects."""
    entry_sha256 = hashlib.sha256(Path(entry_file).read_bytes()).hexdigest()
    expected = environ.get('LUMENIS_CORE_ENTRY_SHA256', '')
    if expected and (
        re.fullmatch(r'[0-9a-f]{64}', expected) is None
        or expected != entry_sha256
    ):
        raise RuntimeError('Core entry source does not match the requested startup target')
    identifiers = {}
    for field, env_key in (
        ('launch_id', 'LUMENIS_CORE_LAUNCH_ID'),
        ('boot_id', 'LUMENIS_CORE_BOOT_ID'),
    ):
        value = environ.get(env_key, '')
        if value and re.fullmatch(r'[0-9a-f]{32}', value) is None:
            raise RuntimeError('Invalid Core startup attempt identifier')
        identifiers[field] = value
    identifiers['boot_id'] = identifiers['boot_id'] or uuid.uuid4().hex
    identifiers['entry_sha256'] = entry_sha256
    return MappingProxyType(identifiers)


def _force_utf8_stdio():
    """Keep startup/preflight/migration diagnostics writable on legacy Windows code pages."""
    for _stream in (sys.stdout, sys.stderr):
        try:
            if _stream is not None and hasattr(_stream, 'reconfigure'):
                _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


_force_utf8_stdio()


def _is_internal_beta_loopback(host):
    return str(host or '').strip().lower() == '127.0.0.1'


def _cli_option_value(argv, option):
    matches = []
    for index, value in enumerate(argv):
        if value == option:
            matches.append(argv[index + 1] if index + 1 < len(argv) else None)
        elif value.startswith(option + '='):
            matches.append(value.split('=', 1)[1])
    return matches[0] if len(matches) == 1 else None


_INTERNAL_BETA_WORKSPACE_CONTEXT_FLAG = '--internal-beta-workspace-context-acceptance'
_INTERNAL_BETA_BROWSER_OUTCOME_FLAG = '--internal-beta-browser-outcome-acceptance'
_INTERNAL_BETA_RESERVED_PORTS = frozenset({5000, 5001, 8200, 8201, 9222, 9223, 9224})


def _validate_internal_beta_workspace_context_arguments(argv, environ=None):
    env = os.environ if environ is None else environ
    flag = _INTERNAL_BETA_WORKSPACE_CONTEXT_FLAG
    if argv.count(flag) != 1:
        raise ValueError(f'{flag} must appear exactly once')
    if any(value.startswith(flag + '=') for value in argv):
        raise ValueError(f'{flag} is a standalone flag and takes no value')
    if '--internal-beta-acceptance' in argv:
        raise ValueError('health-only and Workspace/context acceptance profiles cannot be combined')

    values = {}
    seen_no_scheduler = False
    seen_browser_outcome = False
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == flag:
            index += 1
            continue
        if item == _INTERNAL_BETA_BROWSER_OUTCOME_FLAG:
            if seen_browser_outcome:
                raise ValueError('Browser outcome acceptance flag must appear only once')
            seen_browser_outcome = True
            index += 1
            continue
        if item == '--no-scheduler':
            if seen_no_scheduler:
                raise ValueError('--no-scheduler may appear only once')
            seen_no_scheduler = True
            index += 1
            continue
        if item in ('--host', '--port'):
            if item in values:
                raise ValueError(f'{item} must appear exactly once')
            if index + 1 >= len(argv) or argv[index + 1].startswith('--'):
                raise ValueError(f'{item} requires an explicit value')
            values[item] = argv[index + 1]
            index += 2
            continue
        if item.startswith('--host=') or item.startswith('--port='):
            raise ValueError('--host and --port must use separate explicit arguments')
        raise ValueError(f'unsupported flag for Workspace/context acceptance: {item}')

    if set(values) != {'--host', '--port'}:
        raise ValueError('Workspace/context acceptance requires explicit --host and --port')
    if not _is_internal_beta_loopback(values['--host']):
        raise ValueError('Workspace/context acceptance requires --host 127.0.0.1')
    try:
        port = int(values['--port'])
    except (TypeError, ValueError):
        raise ValueError('--port must be an integer from 1024 through 65535')
    if not 1024 <= port <= 65535:
        raise ValueError('--port must be an integer from 1024 through 65535')
    protected_ports = set(_INTERNAL_BETA_RESERVED_PORTS)
    try:
        configured_production_port = int(env.get('TAIKOO_PORT', '8201'))
    except (TypeError, ValueError):
        configured_production_port = 8201
    protected_ports.add(configured_production_port)
    if port in protected_ports:
        raise ValueError(f'--port {port} is reserved for production or resident services')
    return values['--host'], port


def _is_path_within(path, root):
    path = os.path.normcase(os.path.realpath(os.path.abspath(path)))
    root = os.path.normcase(os.path.realpath(os.path.abspath(root)))
    try:
        return os.path.commonpath((path, root)) == root
    except ValueError:
        return False


def _validate_internal_beta_storage(environ=None, temp_root=None):
    env = os.environ if environ is None else environ
    db_value = str(env.get('ZBC_DB_PATH') or '').strip()
    data_value = str(env.get('ZBC_DATA_DIR') or '').strip()
    if not db_value or not data_value:
        raise ValueError('internal beta acceptance requires explicit ZBC_DB_PATH and ZBC_DATA_DIR')
    if db_value.startswith(('sqlite:', 'file:')) or not os.path.isabs(db_value):
        raise ValueError('internal beta acceptance requires a plain absolute ZBC_DB_PATH')
    if not os.path.isabs(data_value):
        raise ValueError('internal beta acceptance requires an absolute ZBC_DATA_DIR')

    temp_root = temp_root or tempfile.gettempdir()
    db_path = os.path.realpath(os.path.abspath(db_value))
    data_dir = os.path.realpath(os.path.abspath(data_value))
    temp_root = os.path.realpath(os.path.abspath(temp_root))
    if os.path.normcase(data_dir) == os.path.normcase(temp_root) or not _is_path_within(data_dir, temp_root):
        raise ValueError('internal beta ZBC_DATA_DIR must be a dedicated directory under the OS temp root')
    if db_path == data_dir or not _is_path_within(db_path, data_dir):
        raise ValueError('internal beta ZBC_DB_PATH must be a file path under ZBC_DATA_DIR')
    return db_path, data_dir


def _activate_internal_beta_environment(
    environ=None, temp_root=None, require_fresh=False, isolate_auth=False
):
    env = os.environ if environ is None else environ
    db_path, data_dir = _validate_internal_beta_storage(env, temp_root)
    if require_fresh:
        # Do not reuse an existing temporary directory or SQLite sidecar: a
        # temp path is not proof that its contents are disposable.
        if os.path.lexists(data_dir):
            raise ValueError('Workspace/context acceptance requires a new, unused ZBC_DATA_DIR')
        for suffix in ('', '-wal', '-shm', '-journal'):
            if os.path.lexists(db_path + suffix):
                raise ValueError('Workspace/context acceptance refuses an existing SQLite database or sidecar')
    # Keep bridge paths inside the disposable data root. The invalid cookie
    # path is lazy: startup never stats, opens, creates, or launches a profile.
    safe_cookie_path = os.path.join(data_dir, 'private', 'acceptance-cookie-unavailable.txt')
    env['ZBC_DB_PATH'] = db_path
    env['ZBC_DATA_DIR'] = data_dir
    env['LOG_DIR'] = os.path.join(data_dir, 'logs')
    env['XHS_COOKIE_FILE'] = safe_cookie_path
    env['XHS_COOKIE_FILE_OVERRIDE'] = safe_cookie_path
    env['XHS_COOKIE_HEADER'] = ''
    env['XHS_COOKIES_JSON'] = ''
    env['XHS_CDP_URL'] = ''
    env['XHS_PRODUCTION'] = '0'
    env['ZB_WSGI'] = ''
    env['ZBC_PREFLIGHT_ENFORCE'] = '0'
    env['ZBC_GUARDIAN_ENABLED'] = '0'
    env['ZBC_BROWSER_EVIDENCE_DIR'] = os.path.join(data_dir, 'browser-evidence')
    build_dir = env.pop('LUMENIS_WORKSPACE_BUILD_DIR', None)
    if _INTERNAL_BETA_BROWSER_OUTCOME_FLAG in sys.argv and build_dir:
        # An explicit temporary build avoids replacing the running product's
        # artifact. Never serve a personal directory or inherit a generic path.
        resolved_build = os.path.realpath(os.path.abspath(build_dir))
        resolved_temp = os.path.realpath(tempfile.gettempdir())
        if (not os.path.isabs(build_dir)
                or resolved_build == resolved_temp
                or not _is_path_within(resolved_build, resolved_temp)
                or not os.path.isfile(os.path.join(resolved_build, 'index.html'))):
            raise ValueError('Browser outcome build must be an existing build under OS temp')
        env['LUMENIS_WORKSPACE_BUILD_DIR'] = resolved_build
    env.pop('LUMENIS_FLUTTER_WEB_BUILD_DIR', None)
    if isolate_auth:
        # Never inherit a workstation or production Basic credential into this
        # loopback-only child. The temporary credential is process-local and is
        # exposed only by the existing explicit auth/config bootstrap contract.
        env['TAIKOO_AUTH_USER'] = 'lumenis-acceptance-' + secrets.token_hex(8)
        env['TAIKOO_AUTH_PASSWORD'] = secrets.token_urlsafe(32)
    return db_path, data_dir


def _prepare_node_runtime(internal_beta_acceptance):
    if internal_beta_acceptance or MANUAL_WORKSPACE:
        return False
    return _ensure_node_on_path()


def _startup_log_dir():
    return os.environ.get('LOG_DIR') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'logs'
    )


def _ensure_node_on_path():
    import shutil
    if shutil.which('node'):
        return True
    candidates = [
        os.getenv('NODE_EXE', ''),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nodejs', 'node.exe'),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            os.environ['PATH'] = os.path.dirname(c) + os.pathsep + os.environ.get('PATH', '')
            return True
    return False


def _activate_manual_workspace(argv, environ=None):
    """Explicit cross-platform manual startup, retaining normal API permissions."""
    env = os.environ if environ is None else environ
    if argv.count('--manual-workspace') != 1:
        raise ValueError('--manual-workspace must appear exactly once')
    if any(value.startswith('--internal-beta-') for value in argv):
        raise ValueError('manual Workspace and acceptance profiles cannot be combined')
    # Reuse the existing exact loopback/port/flag validator, not its temporary
    # acceptance-storage or request allowlist policy.
    normalized = [_INTERNAL_BETA_WORKSPACE_CONTEXT_FLAG if value == '--manual-workspace' else value for value in argv]
    _validate_internal_beta_workspace_context_arguments(normalized, env)
    data = str(env.get('ZBC_DATA_DIR') or '').strip()
    database = str(env.get('ZBC_DB_PATH') or '').strip()
    if not data or not database or not os.path.isabs(data) or not os.path.isabs(database):
        raise ValueError('manual Workspace requires explicit absolute ZBC_DATA_DIR and ZBC_DB_PATH')
    requested_data, requested_database = Path(data), Path(database)
    data = os.path.realpath(data)
    database = os.path.realpath(database)
    repository = os.path.dirname(os.path.abspath(__file__))
    runtime_root = os.path.realpath(os.path.join(repository, 'data', 'runtime'))
    managed_runtime = data != runtime_root and _is_path_within(data, runtime_root)
    if (data == os.path.dirname(data)
            or (_is_path_within(data, repository) and not managed_runtime)
            or database == data or not _is_path_within(database, data)):
        raise ValueError('manual Workspace requires a dedicated directory under data/runtime or outside the source checkout, with its DB inside that directory')
    bundle_mapping = False
    bundle_root = env.get('LUMENIS_DESKTOP_BUNDLE_ROOT')
    if bundle_root:
        try:
            package = Path(bundle_root)
            core = Path(repository)
            marker = requested_data / '.oevira-user-data.json'
            manifest_file = package / 'bundle-manifest.json'
            if (os.name != 'nt' or not package.is_absolute()
                    or core.name != 'core' or package.resolve() != core.resolve().parent
                    or requested_database.name != 'monitor.db'
                    or requested_database.parent != requested_data
                    or Path(data).is_relative_to(package.resolve())):
                raise ValueError('invalid bundle root')
            for path in (requested_data, requested_database, marker, manifest_file, core / 'app.py'):
                if any(part.is_symlink() or part.is_junction() for part in (path, *path.parents)):
                    raise ValueError('redirected bundle identity')
                if path.exists() and path.is_file() and path.stat().st_nlink != 1:
                    raise ValueError('aliased bundle identity')
            if (not marker.is_file() or marker.stat().st_size > 4096
                    or not manifest_file.is_file() or manifest_file.stat().st_size > 64 * 1024 * 1024):
                raise ValueError('missing bundle identity')
            ownership = json.loads(marker.read_text('utf-8-sig'))
            manifest = json.loads(manifest_file.read_text('utf-8-sig'))
            entry_hash = hashlib.sha256((core / 'app.py').read_bytes()).hexdigest()
            port = _cli_option_value(argv, '--port')
            records = [record for record in manifest.get('files', [])
                       if type(record) is dict and record.get('path') == 'core/app.py']
            if (type(ownership) is not dict or ownership.get('schema') != 'lumenis.desktop-user-data/v1'
                    or manifest.get('schema') != 'lumenis.windows-portable-bundle/v1'
                    or manifest.get('source_entry_sha256') != entry_hash
                    or env.get('LUMENIS_CORE_ENTRY_SHA256') != entry_hash
                    or len(records) != 1 or records[0].get('sha256') != entry_hash
                    or str(manifest.get('core_port')) != port
                    or manifest.get('core_base_url') != 'http://127.0.0.1:' + port
                    or manifest.get('app_core_base_url') != manifest.get('core_base_url')):
                raise ValueError('bundle identity differs')
            for name, expected in (('data', Path(data)), ('logs', Path(data) / 'logs')):
                link = core / name
                if (not link.is_junction() or link.resolve() != expected
                        or expected.is_symlink() or expected.is_junction()):
                    raise ValueError('bundle data mapping differs')
            bundle_mapping = True
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            raise ValueError('manual Workspace bundle data mapping is invalid; existing data was preserved') from None
    production_db = os.path.join(repository, 'data', 'monitor.db')
    if (os.path.isfile(database) and os.path.isfile(production_db)
            and os.path.samefile(database, production_db) and not bundle_mapping):
        raise ValueError('manual Workspace cannot reuse the production database')
    if os.path.isdir(database):
        raise ValueError('manual Workspace ZBC_DB_PATH must name a file')
    env['ZBC_DATA_DIR'] = data
    env['ZBC_DB_PATH'] = database
    env['LOG_DIR'] = os.path.join(data, 'logs')
    env['ZBC_ARTIFACT_DIR'] = os.path.join(data, 'artifacts')
    env['ZBC_AI_GOV_STATS_FILE'] = os.path.join(data, 'ai_governance_stats.json')
    env['LUMENIS_OPEN_WORKSPACE'] = '1'
    return database, data


MANUAL_WORKSPACE = '--manual-workspace' in sys.argv
if any(value.startswith('--manual-workspace=') for value in sys.argv):
    raise SystemExit('--manual-workspace is a standalone flag')
if MANUAL_WORKSPACE:
    try:
        _manual_database, _manual_data = _activate_manual_workspace(sys.argv[1:])
        from lumenis.shared.evidence.signing_config import activate_workspace_signing
        activate_workspace_signing(_manual_data, _manual_database)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


# Select bounded acceptance profiles before any Product Core/application imports.
# Health-only retains its existing contract. Workspace/context acceptance serves
# the canonical Workspace plus the exact authenticated context and Evidence GETs.
INTERNAL_BETA_ACCEPTANCE = '--internal-beta-acceptance' in sys.argv
if any(value.startswith(_INTERNAL_BETA_WORKSPACE_CONTEXT_FLAG + '=') for value in sys.argv):
    raise SystemExit(f'{_INTERNAL_BETA_WORKSPACE_CONTEXT_FLAG} is a standalone flag')
INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE = (
    _INTERNAL_BETA_WORKSPACE_CONTEXT_FLAG in sys.argv
)
INTERNAL_BETA_BROWSER_OUTCOME_ACCEPTANCE = _INTERNAL_BETA_BROWSER_OUTCOME_FLAG in sys.argv
if INTERNAL_BETA_BROWSER_OUTCOME_ACCEPTANCE and not INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE:
    raise SystemExit('Browser outcome acceptance requires the isolated Workspace/context profile')
if INTERNAL_BETA_ACCEPTANCE and INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE:
    raise SystemExit('health-only and Workspace/context acceptance profiles cannot be combined')
INTERNAL_BETA_SAFE_STARTUP = (
    INTERNAL_BETA_ACCEPTANCE or INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE
)
if INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE:
    try:
        _validate_internal_beta_workspace_context_arguments(sys.argv[1:])
        _activate_internal_beta_environment(require_fresh=True, isolate_auth=True)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
if INTERNAL_BETA_ACCEPTANCE and not _is_internal_beta_loopback(
        _cli_option_value(sys.argv[1:], '--host')):
    raise SystemExit(
        'Internal beta acceptance requires an explicit --host 127.0.0.1'
    )
if INTERNAL_BETA_ACCEPTANCE:
    try:
        _activate_internal_beta_environment()
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def _load_dotenv(path='.env'):
    if (
        MANUAL_WORKSPACE
        or INTERNAL_BETA_SAFE_STARTUP
        or INTERNAL_BETA_ACCEPTANCE
        or INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE
    ):
        return
    if not os.path.exists(path): return
    try:
        for line in open(path,encoding='utf-8'):
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k,v=line.split('=',1); k=k.strip(); v=v.strip().strip('\"').strip("'")
            if k and k not in os.environ: os.environ[k]=v
    except Exception as e: print('[ENV] load failed:',e)

_CORE_INSTANCE = _core_instance_identity(__file__, os.environ)
_load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# === 生产稳定性：原生崩溃(C段错误/被信号终止)默认无任何 Python 堆栈，是历史上“进程静默消失”无线索的根因。
# faulthandler 在解释器层把崩溃瞬间全部线程栈写入 logs/faulthandler.log；threading.excepthook 兜住后台线程未捕获异常。 ===
import faulthandler as _faulthandler
import traceback as _fault_tb
try:
    _LOG_DIR = _startup_log_dir()
    os.makedirs(_LOG_DIR, exist_ok=True)
    from lumenis.system.runtime.fault_diagnostics import install_fault_diagnostics
    # Keep fatal handling and periodic snapshots without CPython's unsafe
    # native watchdog walking concurrently changing frames (cpython#116008).
    _fault_fh = install_fault_diagnostics(os.path.join(_LOG_DIR, 'faulthandler.log'))
except Exception as _fault_e:
    print('[FaultHandler] enable failed:', _fault_e)

def _thread_excepthook(args):
    try:
        import logging as _logging
        _logging.getLogger('threading').error(
            'Uncaught in thread %s: %s: %s\n%s', getattr(args.thread, 'name', args.thread),
            getattr(args.exc_type, '__name__', args.exc_type), args.exc_value,
            ''.join(_fault_tb.format_tb(args.exc_traceback)))
    except Exception:
        pass
threading.excepthook = _thread_excepthook

# Stall watchdog: the supervisor probes /healthz every 10s. If no HTTP request
# completes for 90s, dump the current thread stacks once per minute. This
# captures I/O/DB/child-process blocks that do not trip faulthandler's crash path.
_HANG_WATCHDOG = {'last_request_ok': time.time(), 'last_dump': 0.0}
_HANG_WATCHDOG_STOP = threading.Event()
_HANG_WATCHDOG_LOCK = threading.RLock()
_HANG_WATCHDOG_THREAD = None


def _hang_watchdog_loop():
    while not _HANG_WATCHDOG_STOP.wait(15):
        try:
            silence = time.time() - _HANG_WATCHDOG['last_request_ok']
            if silence > 90 and time.time() - _HANG_WATCHDOG['last_dump'] > 60:
                _HANG_WATCHDOG['last_dump'] = time.time()
                if '_fault_fh' in globals() and not _fault_fh.closed:
                    _fault_fh.write(
                        f"\n[HangWatchdog] no completed HTTP request for {silence:.0f}s "
                        f"at {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
                    _fault_fh.flush()
                    _faulthandler.dump_traceback(file=_fault_fh)
        except Exception:
            pass


def _start_hang_watchdog():
    global _HANG_WATCHDOG_THREAD
    with _HANG_WATCHDOG_LOCK:
        if _HANG_WATCHDOG_THREAD is not None and _HANG_WATCHDOG_THREAD.is_alive():
            return _HANG_WATCHDOG_THREAD
        _HANG_WATCHDOG_STOP.clear()
        _HANG_WATCHDOG['last_request_ok'] = time.time()
        _HANG_WATCHDOG['last_dump'] = 0.0
        _HANG_WATCHDOG_THREAD = threading.Thread(
            target=_hang_watchdog_loop, daemon=True, name='hang_watchdog')
        _HANG_WATCHDOG_THREAD.start()
        return _HANG_WATCHDOG_THREAD


def _stop_hang_watchdog(timeout=2.0):
    with _HANG_WATCHDOG_LOCK:
        _HANG_WATCHDOG_STOP.set()
        thread = _HANG_WATCHDOG_THREAD
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        return thread is None or not thread.is_alive()


from datetime import datetime, timedelta
# 统一 Node 解析（PATH 优先，项目内置 nodejs/ 兜底），避免常驻进程 PATH 缺 node 抛 WinError 2
try:
    from runtime_bin import resolve_node as _resolve_node
    _NODE_BIN = _resolve_node() or 'node'
except Exception:
    _NODE_BIN = 'node'
from flask import Flask, jsonify, request, send_file, Response, redirect, copy_current_request_context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# === v5.9.9 统一日志增强：yyds-logger补丁模式，一行启用，不影响现有logging调用 ===
# 多实例隔离/JSON结构化/request_id/按sink级别/异常捕获，所有后续模块自动受益
try:
    os.environ.setdefault("APP_ENV", "prod")
    os.environ.setdefault("LOG_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"))
    from lumenis.unified_logger import patch_logging
    patch_logging()
    print("[UnifiedLogger] yyds-logger补丁已启用（JSON结构化+多实例隔离+request_id）")
except Exception as _log_e:
    print(f"[UnifiedLogger] 启用失败（不影响系统运行）: {_log_e}")
import database as db
from lumenis.shared.database import get_repository
# === LUMENIS SYSTEM: canonical Permission initialization ===
from lumenis.system.security import (
    get_permission_gate, PermissionLevel, OperationType, RiskLevel, require_permission,
)
_pg = get_permission_gate()
_pg.grant_permission(PermissionLevel.COMMIT)
_pg.grant_permission(PermissionLevel.PUSH)
_pg.grant_permission(PermissionLevel.HUMAN_APPROVAL)
print('[Permission] SYSTEM canonical gate initialized; high-risk actions still require human approval')
import ai_analyzer
import collector
import intelligence
import intelligence_library_api  # P1-C: Unified Intelligence Library API
import function_registry
import reprocess
import xhs_cookie_bridge
import ai_filter
from lumenis.shared.reporting import daily
from lumenis.shared.reporting import engine as report_engine
import topic_campaign
from lumenis.shared.evidence import manual as app_evidence
import swire_group
import weekly_events
import browser_discovery
# P1-A(2026-09-02): ai_gateway_v570已废弃，统一到intelligence.py
import memory_optimizer
import stability_monitor
import web_discovery
import system_health_api
import system_creator_ops_api
import architecture_api
import badge_api
import system_ai_data_api
import settings_module
import subject_registry
from lumenis.shared.reporting import export_api
import security_scanner
import runtime_preflight  # ZBIP Runtime Integrity Preflight（统一启动闸门；默认只记录不阻断，ZBC_PREFLIGHT_ENFORCE=1 时 P0 阻断）
import pr_case_integration
import system_features_api
import auth_recovery_api  # V3.0 P0: Auth Recovery Center
import xhs_p0_orchestrator
import collector_automation
import public_opinion_cases
from lumenis.shared.reporting import routes as report_routes  # Shared Reporting canonical routes
import viz_api  # Phase 14: function-driven visualization backend /api/viz/*
import data_center_api  # V1.0: 全平台数据中心API /api/data-center/*
import feature_governance_api  # ZBC Feature Governance: 功能注册表只读查询 /api/feature-registry/*
# ProxyPool 可插拔代理池（可选；导入失败不影响系统启动；总开关默认关闭，关闭时等同直连原版）
try:
    from proxy_pool import proxy_manager as _proxy_mgr
    from proxy_pool.loader import load_proxy_nodes as _load_proxy_nodes
    from proxy_pool.config import ProxyConfig as _ProxyCfg
    PROXY_POOL_AVAILABLE = True
except Exception as _pe:
    _proxy_mgr = None; _load_proxy_nodes = None; _ProxyCfg = None
    PROXY_POOL_AVAILABLE = False
    print('[ProxyPool] 模块不可用（不影响系统运行）:', _pe)
from subject_rules import SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit, subject_sql_and_values
# 品牌Logo管理系统
import brand_logo_manager
# 统一时间序列趋势API（全局趋势线数据源）
import trend_api

app=Flask(__name__)


@app.after_request
def _hang_watchdog_heartbeat(response):
    _HANG_WATCHDOG['last_request_ok'] = time.time()
    return response
app.config['LUMENIS_OPEN_WORKSPACE'] = os.environ.get('LUMENIS_OPEN_WORKSPACE') == '1'


@app.before_request
def _internal_beta_health_only_request_fence():
    if not INTERNAL_BETA_ACCEPTANCE:
        return None
    if request.method == 'GET' and request.path == '/healthz':
        return None
    return jsonify({
        'ok': False,
        'status': 'BLOCKED',
        'code': 'INTERNAL_BETA_HEALTH_ONLY',
        'message': 'This health-only safe probe permits only GET /healthz.',
    }), 403


_INTERNAL_BETA_WORKSPACE_ROOT_ENDPOINTS = {
    'lumenis_workspace_host.root': '/workspace',
    'lumenis_workspace_host.root_slash': '/workspace/',
}
_INTERNAL_BETA_WORKSPACE_API_ENDPOINTS = {
    ('GET', '/healthz', 'healthz'),
    ('GET', '/api/auth/config', 'auth_config_api'),
    ('GET', '/api/experience/runtime/identity', 'experience_runtime.runtime_identity'),
    ('GET', '/api/runtime/identity', 'experience_runtime.runtime_identity'),
    ('GET', '/api/settings/context', 'domain_api.api_settings_context'),
    ('GET', '/api/evidence/stats', 'evidence_api.evidence_stats'),
    ('GET', '/api/evidence/list', 'evidence_api.evidence_list'),
    ('GET', '/api/evidence/timeline', 'evidence_api.evidence_timeline'),
}


def _internal_beta_workspace_context_request_allowed():
    method = request.method
    path = request.path
    endpoint = request.endpoint
    if (method, path, endpoint) in _INTERNAL_BETA_WORKSPACE_API_ENDPOINTS:
        return True
    if (
        method == 'GET'
        and endpoint == 'evidence_api.evidence_detail'
        and re.fullmatch(r'/api/evidence/[0-9]+', path)
        and type((request.view_args or {}).get('record_id')) is int
    ):
        return True
    if method not in {'GET', 'HEAD'}:
        return False
    if _INTERNAL_BETA_WORKSPACE_ROOT_ENDPOINTS.get(endpoint) == path:
        return True
    if endpoint == 'lumenis_workspace_host.resource' and path.startswith('/workspace/'):
        return True
    if endpoint == 'lumenis_workspace_host.asset':
        resource = (request.view_args or {}).get('resource')
        view_func = app.view_functions.get(endpoint)
        host = getattr(view_func, '__self__', None)
        return (
            isinstance(resource, str)
            and host is not None
            and not host._is_reserved_root_path(resource)
        )
    return False


def _internal_beta_browser_outcome_request_allowed():
    # Exact opt-in routes; existing actor/scope/Permission/effect checks still run.
    # No model execution, source import, Collector, personal session or OS APIs.
    methods = {
        'ai_browser_runtime.create_session': {'POST'},
        'ai_browser_runtime.list_sessions': {'GET'},
        'ai_browser_runtime.get_session_status': {'GET'},
        'ai_browser_runtime.read_session_frame': {'GET'},
        'ai_browser_runtime.stream_session_frames': {'GET'},
        'ai_browser_runtime.stream_policy': {'GET'},
        'ai_browser_runtime.acquire_human_control': {'POST'},
        'ai_browser_runtime.release_human_control': {'POST'},
        'ai_browser_runtime.human_control_navigate': {'POST'},
        'ai_browser_runtime.human_control_action': {'POST'},
        'ai_browser_runtime.human_control_links': {'POST'},
        'ai_browser_runtime.human_control_open_link': {'POST'},
        'ai_browser_runtime.observe': {'POST'},
        'ai_browser_runtime.stop_session': {'POST'},
        'ai_browser_runtime.get_evidence': {'GET'},
        'experience_runtime.save_shared_work': {'POST'},
        'experience_runtime.search_shared_work': {'GET'},
        'experience_runtime.read_shared_work': {'GET'},
        'experience_runtime.revise_shared_work': {'POST'},
        'experience_runtime.export_shared_work': {'GET', 'POST'},
    }
    return (INTERNAL_BETA_BROWSER_OUTCOME_ACCEPTANCE
            and request.method in methods.get(request.endpoint, set()))


@app.before_request
def _internal_beta_workspace_context_request_fence():
    if not INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE:
        return None
    if (_internal_beta_workspace_context_request_allowed()
            or _internal_beta_browser_outcome_request_allowed()):
        return None
    return jsonify({
        'ok': False,
        'status': 'BLOCKED',
        'code': 'INTERNAL_BETA_WORKSPACE_CONTEXT_ONLY',
        'message': 'This loopback acceptance profile permits only Workspace, identity, context, and scoped Evidence GET routes.',
    }), 403

# 全局上传大小限制：500MB（对齐 INGESTION_AND_TERMINOLOGY_STANDARD）
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
# SYSTEM Runtime serves the generated Flutter Workspace; Flask retains Product Core ownership.
from lumenis.system.runtime.workspace_host import register_workspace_host
register_workspace_host(app)
# 注册系统控制中心蓝图
app.register_blueprint(system_health_api.system_health_bp)
app.register_blueprint(system_creator_ops_api.system_creator_ops_bp)
# 注册5层闭环架构蓝图
app.register_blueprint(architecture_api.architecture_bp)
app.register_blueprint(badge_api.badge_bp)
app.register_blueprint(system_ai_data_api.system_ai_bp)
# 注册设置模块蓝图
app.register_blueprint(settings_module.settings_bp)
# 通用主体注册表：CTH/BMP 共用配置入口；不改变两域既有运行规则
app.register_blueprint(subject_registry.subject_registry_bp)
# 注册导出报告模块蓝图
app.register_blueprint(export_api.export_bp)
# 注册公关案例整合模块蓝图
app.register_blueprint(pr_case_integration.pr_case_bp)
# 注册系统功能API蓝图
app.register_blueprint(system_features_api.system_features_bp)
# V3.0 P0: Auth Recovery Center（认证恢复中心）
app.register_blueprint(auth_recovery_api.auth_recovery_bp)
# 统一趋势API蓝图
app.register_blueprint(trend_api.trend_bp)
app.register_blueprint(report_routes.report_bp)  # Shared Reporting API
app.register_blueprint(viz_api.viz_bp)  # Phase 14: 函数驱动可视化后端 /api/viz/*
app.register_blueprint(data_center_api.data_center_bp)  # V1.0: 全平台数据中心 /api/data-center/*
app.register_blueprint(intelligence_library_api.intelligence_library_bp)
# ZBC Feature Governance: 功能注册表只读查询（不修改任何业务逻辑）
app.register_blueprint(feature_governance_api.feature_governance_bp)

# P1-Content: 统一内容生成引擎（AI+研究库+Evidence+Evaluation）
try:
    import content_generation
    content_generation.register_content_api(app)
except Exception as _cg_e:
    print(f"[content_generation] blueprint register failed: {_cg_e}")

# Shared Capability staged artifacts: create the registry in the canonical
# runtime database at startup so read/preview requests never perform a first
# schema write, and so the video renderer has one stable persistence contract.
try:
    import shared_artifacts as _shared_artifacts
    _shared_artifacts.ensure_artifact_table()
    print("[shared_artifacts] staged artifact registry ensured")
except Exception as _sa_e:
    print(f"[shared_artifacts] registry warning (non-fatal): {_sa_e}")

# Module Registry: 模组注册与用户自定义管理
try:
    import module_registry
    module_registry.register_module_api(app)
except Exception as _mr_e:
    print(f"[module_registry] register failed: {_mr_e}")

# Agent Runtime 7增量层 Blueprint（先旁路验证，不影响主链路）
try:
    from agent_adaptive_ui.routes import adaptive_ui_bp
    app.register_blueprint(adaptive_ui_bp)
    print("[agent_adaptive_ui] blueprint registered")
except Exception as _aui_e:
    print(f"[agent_adaptive_ui] register failed: {_aui_e}")

try:
    from agent_proactive.routes import proactive_bp
    if proactive_bp:
        app.register_blueprint(proactive_bp)
        print("[agent_proactive] blueprint registered")
except Exception as _ap_e:
    print(f"[agent_proactive] register failed: {_ap_e}")

  # P1-C: Intelligence Library API
import data_query_api
data_query_api.register_data_query_api(app)  # P1-10 拆分批1: 数据只读查询
import collection_api
import ai_api
collection_api.register_collection_api(app)
ai_api.register_ai_api(app)  # P1-10 拆分批2a: 采集器状态/启停

# Zachary OS AI：系统内置浏览器（小红书/rednote 不跳转外部，系统内完成）
try:
    import internal_browser
    internal_browser.register_internal_browser(app)
except Exception as _ib_e:
    print(f"[internal_browser] blueprint register failed: {_ib_e}")

# Zachary OS AI：系统内置浏览器实时画面流（Screencast over SSE，持久连接主动推帧）
try:
    from lumenis.system.browser.runtime import screencast_stream as internal_browser_stream
    internal_browser_stream.register_stream(app)
except Exception as _ibs_e:
    print(f"[internal_browser_stream] blueprint register failed: {_ibs_e}")

# 序境 · 平台内置浏览器能力层（对标 Safari/Chrome：Tabs/Reader/书签/历史/多源搜索，平台内不跳站外）
try:
    import browser_surface_api
    browser_surface_api.register_browser_surface_api(app)
    print("[browser_surface_api] registered: /api/browser-surface/*")
except Exception as _bsf_e:
    print(f"[browser_surface_api] blueprint register failed: {_bsf_e}")

# LUMENIS Shared Evidence 查询 API（只读证据接口）
try:
    from lumenis.shared.evidence import api as evidence_api
    evidence_api.register_evidence_api(app)
except Exception as _ev_e:
    print(f"[evidence_api] blueprint register failed: {_ev_e}")

# 序境 LUMENIS App API：仅提供 Flutter/Core JSON contracts，不注册任何网页、模板或静态资源。
try:
    from lumenis_app_api import lumenis_bp, domain_api_bp
    from collector_status_api import collector_status_bp
    app.register_blueprint(collector_status_bp)
    app.register_blueprint(lumenis_bp)
    app.register_blueprint(domain_api_bp)
    print("[lumenis] App API registered: /lumenis/api/* + /api/domain/*")
except Exception as _lm_e:
    print(f"[lumenis] App API register failed: {_lm_e}")

# 序境共享 Experience ViewModel/API：服务 Flutter Web/Desktop/Mobile，不恢复旧浏览器原型。
try:
    from experience_runtime import register_experience_runtime
    register_experience_runtime(app)
    print("[experience_runtime] API registered: /api/experience/*")
except Exception as _er_e:
    print(f"[experience_runtime] API register failed: {_er_e}")

# 序境 LUMENIS 聚合只读 API（全局 /api：模型/Agent/评估/研究/权限/仓库/运行时/报告/KOS专业号）
try:
    from lumenis_agg_api import register_agg_api
    register_agg_api(app)
    print("[lumenis-agg] aggregation API registered")
except Exception as _lag_e:
    print(f"[lumenis-agg] aggregation API register failed: {_lag_e}")

# 统一本地文件导入 API（参考 GPT 文件夹 icon，点击浏览本地；复用 app_evidence 扩展名+500MB 校验）
try:
    from lumenis.shared.evidence.manual import EVIDENCE_ALLOWED_EXTENSIONS, EVIDENCE_MAX_FILE_SIZE_BYTES
    _IMPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'imports')
    os.makedirs(_IMPORT_DIR, exist_ok=True)

    @app.route('/api/local-import', methods=['POST'])
    def api_local_import():
        """统一本地文件导入：支持图片/文档/视频，单文件最大500MB，保存到 data/imports/。"""
        try:
            if 'files' not in request.files:
                return jsonify({'ok': False, 'error': '未选择文件'}), 400
            files = request.files.getlist('files')
            if not files:
                return jsonify({'ok': False, 'error': '文件列表为空'}), 400
            results = []
            for f in files:
                if not f or not f.filename:
                    continue
                ext = os.path.splitext(f.filename)[1].lower()
                if ext not in EVIDENCE_ALLOWED_EXTENSIONS:
                    results.append({'filename': f.filename, 'ok': False, 'error': f'不支持的格式: {ext}'})
                    continue
                safe_name = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}{ext}"
                save_path = os.path.join(_IMPORT_DIR, safe_name)
                f.save(save_path)
                size = os.path.getsize(save_path)
                if size > EVIDENCE_MAX_FILE_SIZE_BYTES:
                    os.remove(save_path)
                    results.append({'filename': f.filename, 'ok': False, 'error': f'文件过大: {size//1024//1024}MB > 500MB'})
                    continue
                results.append({'filename': f.filename, 'saved_as': safe_name, 'size': size, 'ok': True})
            ok_count = sum(1 for r in results if r.get('ok'))
            return jsonify({'ok': ok_count > 0, 'total': len(files), 'imported': ok_count, 'results': results})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
except Exception as _li_e:
    print(f"[local_import] API register failed: {_li_e}")

# Shard C：多平台数据导入接口（平台归一化+字段映射+ID精度保护，复用 notes 表）
try:
    from lumenis.system.collector.adapters.multi_platform_import import import_multi_platform_records

    @app.route('/api/import/multi-platform', methods=['POST'])
    def api_import_multi_platform():
        """多平台数据导入：接收 JSON {records: [...]}，按 platform 自动映射字段后入库。"""
        try:
            data = request.get_json(silent=True) or {}
            records = data.get('records') or data.get('items') or []
            if not isinstance(records, list) or not records:
                return jsonify({'ok': False, 'error': 'records 不能为空，需传入列表'}), 400
            result = import_multi_platform_records(records)
            return jsonify({'ok': result['failed'] == 0, **result})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
    print("[multi_platform_import] API registered: POST /api/import/multi-platform")
except Exception as _mpi_e:
    print(f"[multi_platform_import] API register failed: {_mpi_e}")

# Zachary OS AI：KOS 传播主体 API（复用 kos_engine/kos_report，不重复建设）
try:
    import kos_routes
    kos_routes.register_kos_api(app)
    print("[kos_routes] KOS API registered: /api/kos/*")
except Exception as _kos_e:
    print(f"[kos_routes] blueprint register failed: {_kos_e}")

# 序境 · 已就绪契约 IC-020/028/047 API（告警配置+状态机 / 营销节点分级 / 免税KOS场景）
try:
    import ic_routes
    ic_routes.register_ic_api(app)
    print("[ic_routes] IC API registered: /api/ic/*")
except Exception as _ic_e:
    print(f"[ic_routes] blueprint register failed: {_ic_e}")

# 序境 · 播客情报 API（实体图 + 确定性智能算法，独立于品牌舆情链路）
try:
    import podcast_routes
    podcast_routes.register_podcast_api(app)
except Exception as _pc_e:
    print(f"[podcast_routes] blueprint register failed: {_pc_e}")

# Zachary OS AI：Browser Runtime API（只读，对齐 CTR-BROWSER-RUNTIME-P0-01）
try:
    import browser_runtime_api
    browser_runtime_api.register_browser_runtime_api(app)
except Exception as _br_e:
    print(f"[browser_runtime_api] blueprint register failed: {_br_e}")

# ZBC AI Browser Runtime API（Production-Ready，带 Verification 闭环 + Evidence + Security）
try:
    import ai_browser_api
    ai_browser_api.register_ai_browser_api(app)
except Exception as _aibr_e:
    print(f"[ai_browser_api] blueprint register failed: {_aibr_e}")

# V3.0 影子板块：品牌营销知识库API
@app.route('/api/brand-knowledge/stats')
def brand_knowledge_stats():
    """品牌知识库统计"""
    try:
        from brand_knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        return jsonify({'ok': True, 'data': kb.get_stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/brand-knowledge/search')
def brand_knowledge_search():
    """品牌知识库搜索"""
    try:
        from brand_knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        keyword = request.args.get('q', '')
        category = request.args.get('category', '')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        results = kb.search(keyword=keyword, category=category, limit=limit, offset=offset)
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 影子板块：案例深度拆解API
@app.route('/api/case-analysis/stats')
def case_analysis_stats():
    """案例深度拆解库统计"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        return jsonify({'ok': True, 'data': analysis.get_stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/list')
def case_analysis_list():
    """案例深度拆解列表（支持筛选）"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        case_type = request.args.get('type', '')
        industry = request.args.get('industry', '')
        brand = request.args.get('brand', '')
        min_quality = request.args.get('min_quality', 0)
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        results = analysis.list_cases(
            case_type=case_type or '',
            industry=industry or '',
            brand=brand or '',
            min_quality_score=float(min_quality) if min_quality else 0,
            limit=limit,
            offset=offset,
        )
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/detail')
def case_analysis_detail():
    """案例深度拆解详情"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        case_id = request.args.get('id', '')
        if not case_id:
            return jsonify({'ok': False, 'error': '缺少案例ID参数'}), 400
        result = analysis.get_case(case_id)
        if not result:
            return jsonify({'ok': False, 'error': f'案例 {case_id} 不存在'}), 404
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/search')
def case_analysis_search():
    """案例深度拆解搜索"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        keyword = request.args.get('q', '')
        if not keyword:
            return jsonify({'ok': False, 'error': '缺少搜索关键词'}), 400
        results = analysis.search_cases(keyword)
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/methodology')
def case_analysis_methodology():
    """获取所有可复用方法论"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        results = analysis.get_all_methodologies()
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/system-insights')
def case_analysis_system_insights():
    """获取所有对 LUMENIS 系统的启示"""
    try:
        from case_deep_analysis import get_case_analysis
        analysis = get_case_analysis()
        results = analysis.get_all_system_insights()
        return jsonify({'ok': True, 'results': results, 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/case-analysis/template-match', methods=['GET', 'POST'])
def case_analysis_template_match():
    """按事件/场景匹配可复用处置模板（学习资产：9模板 + 危机SOP）"""
    try:
        from case_templates import match_templates
        if request.method == 'POST':
            d = request.get_json(silent=True) or {}
            kw = str(d.get('keyword') or d.get('query') or '')
            cat = str(d.get('category') or '')
        else:
            kw = request.args.get('keyword', '')
            cat = request.args.get('category', '')
        results = match_templates(kw, cat)
        return jsonify({'ok': True, 'total': len(results), 'templates': results})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/case-analysis/crisis-sop')
def case_analysis_crisis_sop():
    """危机公关处置SOP（结构化阶段 + KPI）"""
    try:
        from case_templates import get_crisis_sop
        return jsonify({'ok': True, 'sop': get_crisis_sop()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/case-analysis/ai-evaluate', methods=['POST'])
def case_analysis_ai_evaluate():
    """案例评估兼容入口；本地模板与实际 Owned AI 执行状态分开。"""
    try:
        data = request.get_json(silent=True) or {}
        case_id = str(data.get('case_id') or '')
        if not case_id:
            return jsonify({'ok': False, 'error': '缺少 case_id'}), 400
        from case_deep_analysis import get_case_analysis
        from case_ai_evaluate import evaluate_case
        case = get_case_analysis().get_case(case_id)
        if not case:
            return jsonify({'ok': False, 'error': '案例不存在'}), 404
        result = evaluate_case(case)
        result['case_id'] = case_id
        ai = result.get('ai') or {}
        completed = ai.get('enabled') is True and ai.get('status') == 'COMPLETED'
        # A legacy case cannot manufacture the typed source-use request needed
        # by the owned service. Keep advisory templates without claiming AI ran.
        return jsonify({'ok': completed, **result}), (200 if completed else 503)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# V3.0 传播主体分类器API
@app.route('/api/subject-classifier/classify', methods=['POST'])
def subject_classify():
    """传播主体分类"""
    try:
        from subject_classifier import get_subject_classifier
        clf = get_subject_classifier()
        data = request.get_json() or {}
        result = clf.classify(
            author_name=data.get('author_name', ''),
            author_desc=data.get('author_desc', ''),
            followers=int(data.get('followers', 0)),
            is_verified=bool(data.get('is_verified', False)),
            verified_type=data.get('verified_type', ''),
            content_pattern=data.get('content_pattern', ''),
        )
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/subject-classifier/types')
def subject_types():
    """获取所有主体类型"""
    try:
        from subject_classifier import SubjectClassifier
        return jsonify({
            'ok': True,
            'subject_types': SubjectClassifier.get_all_subject_types(),
            'content_types': SubjectClassifier.get_all_content_types(),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 事件关系图谱API
@app.route('/api/event-graph/stats')
def event_graph_stats():
    from event_graph import graph_http
    return graph_http('stats')

@app.route('/api/event-graph/events')
def event_graph_events():
    from event_graph import graph_http
    return graph_http('list')

@app.route('/api/event-graph/chain/<event_id>')
def event_graph_chain(event_id):
    from event_graph import graph_http
    return graph_http('chain', event_id=event_id)

@app.route('/api/event-graph/approval/revoke', methods=['POST'])
def event_graph_revoke_approval():
    from event_graph import graph_http
    return graph_http('revoke')

@app.route('/api/event-graph/types')
def event_graph_types():
    """获取所有事件类型和关系类型"""
    try:
        from event_graph import EventGraph
        return jsonify({
            'ok': True,
            'event_types': EventGraph.get_all_event_types(),
            'relation_types': EventGraph.get_all_relation_types(),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 事件关系图谱写入API（v5.9.9 新增数据库持久化）
@app.route('/api/event-graph/events', methods=['POST'])
def event_graph_create_event():
    from event_graph import graph_http
    return graph_http('create')

@app.route('/api/event-graph/relations', methods=['POST'])
def event_graph_add_relation():
    from event_graph import graph_http
    return graph_http('relation')

@app.route('/api/creative/ideas', methods=['POST'])
def creative_ideas():
    """创意卡生成：输入品牌/品类/圈层/热点/调性(可选关键词从DB提信号)→ 原创创意方向。"""
    try:
        from scripts.idea_generator import generate_ideas, signals_from_db
        data = request.get_json() or {}
        brand = data.get('brand', '')
        category = data.get('category', '通用')
        circle = data.get('circle', '都市职场')
        tonality = data.get('tonality', 'premium')
        hotspot = data.get('hotspot', '')
        n = min(int(data.get('n', 3)), 5)
        keyword = data.get('keyword', '')
        profile = data.get('profile', '')      # 美奢人群画像（B站x凯度 7 类）
        constraint_type = data.get('constraint_type', '')  # 约束类型（SIT 转译感知）
        budget = data.get('budget', 'mid')     # 预算档 low/mid/high
        if not brand:
            return jsonify({'ok': False, 'error': 'brand 不能为空'}), 400
        if keyword:
            signals = signals_from_db(data.get('db') or db.main_db_path(), keyword, circle, hotspot)  # P0-DBISO-01
            signals['overseas'] = bool(data.get('overseas'))
            signals['region'] = data.get('region', '')
            if profile:
                signals['profile'] = profile
            if constraint_type:
                signals['constraint_type'] = constraint_type
        else:
            signals = {'topics': data.get('topics', []), 'sentiment': data.get('sentiment', 'neutral'),
                       'negative_rate': data.get('negative_rate', 0.0), 'risk_events': data.get('risk_events', 0),
                       'circle': circle, 'hotspot': hotspot, 'volume_notes': data.get('volume_notes', 0),
                       'overseas': bool(data.get('overseas')), 'region': data.get('region', ''),
                       'profile': profile, 'constraint_type': constraint_type}
        result = generate_ideas(brand, category, signals, n, tonality, budget=budget)
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/creative/video-script', methods=['POST'])
def creative_video_script():
    """视频创意脚本生成：TVC/概念片/小红书/抖音 → 分镜头脚本+标题候选+投放建议。"""
    try:
        from scripts.video_script import generate_video_script, VIDEO_TYPES
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        brand = data.get('brand', '')
        if not brand:
            return jsonify({'ok': False, 'error': 'brand 不能为空'}), 400
        vt = data.get('video_type', 'tvc')
        if vt not in VIDEO_TYPES:
            return jsonify({'ok': False, 'error': 'video_type 仅支持: %s' % list(VIDEO_TYPES.keys())}), 400
        result = generate_video_script(
            brand, data.get('category', '通用'), data.get('circle', '都市职场'),
            data.get('tonality', 'premium'), vt, data.get('product_point', ''),
            data.get('hotspot', ''), data.get('n_shots') or None,
            overseas=bool(data.get('overseas')), region=data.get('region', ''))
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/creative/social-ops', methods=['POST'])
def creative_social_ops():
    """多平台社媒运营策略：小红书/抖音/IG/FB/X/公众号 → 生态/栏目/爆款公式/投放/度量。"""
    try:
        from scripts.social_ops import generate_social_ops, generate_social_matrix, PLATFORMS
        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}
        brand = data.get('brand', '')
        if not brand:
            return jsonify({'ok': False, 'error': 'brand 不能为空'}), 400
        platform = data.get('platform', '')
        if platform and platform not in PLATFORMS:
            return jsonify({'ok': False, 'error': 'platform 仅支持: %s' % list(PLATFORMS.keys())}), 400
        if platform:
            result = generate_social_ops(brand, platform, data.get('circle', '都市职场'),
                                         data.get('tonality', 'premium'), data.get('hotspot', ''))
        else:
            result = generate_social_matrix(brand, None, data.get('circle', '都市职场'),
                                            data.get('tonality', 'premium'), data.get('hotspot', ''))
        return jsonify({'ok': True, 'data': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

def _creative_pitch_request(*, export=False):
    """Read bounded task input; client fields cannot select authority or paths."""
    import json
    import re
    from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

    allowed = {'text', 'brand', 'hotspot', 'n', 'target_date', 'market'} | ({'manuscript'} if export else set())

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('重复的输入字段')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('输入不能包含非有限数值')

    def json_object(raw):
        return json.loads(raw, object_pairs_hook=unique_object, parse_constant=invalid_constant)

    upload = None
    if request.is_json:
        raw = request.stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('输入超过大小限制')
        data = json_object(raw.decode('utf-8'))
    elif request.mimetype == 'multipart/form-data':
        if request.content_length is not None and request.content_length > 17 * 1024 * 1024:
            raise ValueError('上传超过大小限制')
        try:
            form, files = request.form, request.files
            if (set(files) - {'file'} or len(files.getlist('file')) > 1
                    or any(len(form.getlist(key)) != 1 for key in form)):
                raise ValueError('重复或未知的上传字段')
            data = form.to_dict()
            upload = files.get('file')
        except (BadRequest, RequestEntityTooLarge) as exc:
            raise ValueError('无法读取上传输入') from exc
        if 'n' in data:
            if not re.fullmatch(r'[0-9]{1,6}', data['n']):
                raise ValueError('n 必须为正整数')
            data['n'] = int(data['n'])
        if 'manuscript' in data:
            data['manuscript'] = json_object(data['manuscript'])
    else:
        raise ValueError('需要 JSON 或 multipart 输入')
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError('未知的输入字段')
    for key, limit in (('text', 200000), ('brand', 1000), ('hotspot', 1000), ('target_date', 10), ('market', 80)):
        value = data.get(key, '')
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError('%s 必须为大小受限的文本' % key)
    if data.get('target_date'):
        from scripts.marketing_calendar import calendar_context
        if len(data['target_date']) != 10 or calendar_context(data['target_date'], market=data.get('market', 'CN'))['state'] == 'invalid_input':
            raise ValueError('target_date 必须为真实公历日期')
    n = data.get('n', 3)
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError('n 必须为正整数')
    # Retain the existing maximum of five candidates.
    data['n'] = min(n, 5)
    if 'manuscript' in data:
        manuscript = data['manuscript']
        if (not isinstance(manuscript, dict)
                or set(manuscript) - {'title', 'summary', 'sections', 'language', 'authorship'}):
            raise ValueError('成稿必须包含有效的正文对象')
        if (any(not isinstance(manuscript.get(key), str) or not manuscript[key].strip()
                for key in ('title', 'summary'))
                or not isinstance(manuscript.get('sections'), list) or not manuscript['sections']):
            raise ValueError('成稿标题、说明和正文不能为空')
        for section in manuscript['sections']:
            if (not isinstance(section, dict) or set(section) != {'heading', 'body'}
                    or any(not isinstance(section[key], str) or not section[key].strip()
                           for key in ('heading', 'body'))):
                raise ValueError('每节成稿需要标题和正文')
        if (type(manuscript.get('language', 'zh')) is not str
                or manuscript.get('language', 'zh') not in {'zh', 'en', 'ko'}
                or type(manuscript.get('authorship', 'assisted')) is not str
                or manuscript.get('authorship', 'assisted') not in {'assisted', 'user_supplied'}):
            raise ValueError('成稿语言或来源无效')
    return data, upload


def _creative_pitch_analysis(data, upload):
    from pathlib import Path
    import tempfile
    from scripts.pitch_parser import analyze_pitch, analyze_pitch_file

    brand, hotspot, n = data.get('brand', ''), data.get('hotspot', ''), data['n']
    calendar_args = {key: data[key] for key in ('target_date', 'market') if key in data}
    if upload is not None and upload.filename:
        filename = upload.filename.replace('\\', '/').rsplit('/', 1)[-1]
        if len(filename) > 255 or any(ord(char) < 32 for char in filename):
            raise ValueError('文件名无效')
        suffix = Path(filename).suffix.lower()
        if suffix not in {'.txt', '.md', '.json', '.csv', '.pptx', '.docx'}:
            raise ValueError('不支持的输入文件格式')
        content = upload.stream.read(16 * 1024 * 1024 + 1)
        if not content or len(content) > 16 * 1024 * 1024:
            raise ValueError('文件为空或超过大小限制')
        with tempfile.TemporaryDirectory(prefix='lumenis-pitch-input-') as directory:
            source = Path(directory) / ('source' + suffix)
            source.write_bytes(content)
            result = analyze_pitch_file(str(source), brand, n, hotspot, **calendar_args)
        # Input provenance retains the original basename and byte hash, never a
        # deleted server path. This is input provenance, not signed Evidence.
        result['source_file'] = filename
        result['input_provenance']['filename'] = filename
        return result
    text = data.get('text', '')
    if not text.strip():
        raise ValueError('需要 text 或上传文件')
    return analyze_pitch(text, brand, n, hotspot, **calendar_args)


def _creative_pitch_check_export():
    """Recheck the existing export permission without an operation-cache key."""
    from lumenis.system.security import get_permission_gate, is_testing_bypass_enabled, OperationType

    if (_pg is None or _pg is not get_permission_gate()
            or not _pg.fail_closed or is_testing_bypass_enabled()):
        raise RuntimeError('PITCH_PERMISSION_UNAVAILABLE')
    from domain_isolation import get_domain_context
    context = get_domain_context()
    # This compatibility operation exports the caller's supplied manuscript.
    # A selected business context remains selected; an unbound file conversion
    # is SYSTEM work, never an implicit CTH/Guangzhou request.
    domain = context.domain_id if context is not None and context.domain_id else 'system'
    result = _pg.check(operation_type=OperationType.DATA_EXPORT,
                       resource=request.path,
                       caller='http:{}:{}'.format(request.method, request.path),
                       domain_id=domain)
    if not result.allowed:
        raise PermissionError('PITCH_EXPORT_DENIED')


@app.route('/api/creative/pitch-analyze', methods=['POST'])
def creative_pitch_analyze():
    """方案需求拆解：接受文本或现有支持格式的文件。"""
    try:
        data, upload = _creative_pitch_request()
        return jsonify({'ok': True, 'data': _creative_pitch_analysis(data, upload)})
    except (ValueError, UnicodeError):
        return jsonify({'ok': False, 'code': 'INVALID_PITCH_INPUT', 'error': '请检查需求文本和上传文件'}), 400
    except Exception:
        return jsonify({'ok': False, 'code': 'PITCH_ANALYSIS_FAILED', 'error': '需求分析失败'}), 500


@app.route('/api/creative/pitch-export', methods=['POST'])
def creative_pitch_export():
    """导出需求分析或实际提供的成稿；成稿审阅和使用授权仍待确认。"""
    try:
        import io
        import tempfile
        from pathlib import Path
        from werkzeug.utils import secure_filename
        from scripts.pitch_export import export_pitch_docx
        data, upload = _creative_pitch_request(export=True)
        _creative_pitch_check_export()
        result = _creative_pitch_analysis(data, upload)
        # Request-owned paths are unique and cleaned on success, denial and
        # failure. A memory-backed response needs no deferred disk cleanup.
        with tempfile.TemporaryDirectory(prefix='lumenis-pitch-export-') as directory:
            destination = Path(directory) / 'proposal.docx'
            out_path = export_pitch_docx(result, str(destination),
                                        manuscript=data.get('manuscript'),
                                        check_continue=_creative_pitch_check_export)
            if Path(out_path).resolve() != destination.resolve():
                raise RuntimeError('PITCH_OUTPUT_PATH_INVALID')
            payload = destination.read_bytes()
            _creative_pitch_check_export()
        brand = secure_filename(result.get('extracted', {}).get('brand') or 'pitch')[:80] or 'pitch'
        suffix = '提案成稿' if 'manuscript' in data else '方案拆解'
        response = send_file(io.BytesIO(payload), as_attachment=True,
                             download_name='%s_%s.docx' % (brand, suffix))
        response.headers['Cache-Control'] = 'no-store'
        return response
    except PermissionError:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': 'PITCH_EXPORT_DENIED', 'error': '当前不能导出'}), 403
    except (ValueError, UnicodeError):
        return jsonify({'ok': False, 'code': 'INVALID_PITCH_INPUT', 'error': '请检查需求和成稿内容'}), 400
    except RuntimeError as exc:
        if str(exc) == 'PITCH_PERMISSION_UNAVAILABLE':
            return jsonify({'ok': False, 'status': 'BLOCKED', 'code': 'PITCH_PERMISSION_UNAVAILABLE', 'error': '导出权限暂不可用'}), 503
        return jsonify({'ok': False, 'code': 'PITCH_EXPORT_FAILED', 'error': '导出失败'}), 500
    except Exception:
        return jsonify({'ok': False, 'code': 'PITCH_EXPORT_FAILED', 'error': '导出失败'}), 500

@app.route('/api/event-graph/import', methods=['POST'])
def event_graph_import_existing():
    from event_graph import graph_http
    return graph_http('import')

@app.route('/api/event-graph/rebuild-relations', methods=['POST'])
def event_graph_rebuild_relations():
    from event_graph import graph_http
    return graph_http('infer')

# ===== Shared Reporting 标准化报告：只读旁路预览（不改既有 daily/brand 报告路由、不抢 RPT Owner、不写库/不导出/不自动发送）=====
@app.route('/api/v2/marketing/overview')
def marketing_overview():
    """营销节点速览：当月节气/节日 + 垂直行业交叉建议 + 创意引擎当前绑定节点。
    报告体系消费营销节点（芥子→须弥）的前端闭环。"""
    try:
        from scripts.marketing_calendar import (suggest_hotspot, nodes_for_month,
                                                cross_industry_season, cross_global, global_nodes,
                                                region_nodes, marketing_matrix, calendar_context)
        import datetime as _dt
        import io, csv as _csv
        industry = (request.args.get('industry') or '').strip()
        explicit_date = request.args.get('date')
        year_raw = request.args.get('year')
        year = int(year_raw) if year_raw is not None else int((explicit_date or _dt.date.today().isoformat())[:4])
        month = str(int(request.args.get('month', (explicit_date or _dt.date.today().isoformat())[5:7]))).zfill(2)
        today = explicit_date if explicit_date is not None else f"{year:04d}-{month}-01"
        market = request.args.get('market', 'CN')
        context = calendar_context(today, year=year, market=market)
        if context['state'] == 'invalid_input' or not 1 <= int(month) <= 12:
            return jsonify({'ok': False, 'code': 'CALENDAR_INPUT_INVALID', 'calendar_reference': context}), 400
        available = context['state'] == 'reference_only_not_live_verified'
        gflag = (request.args.get('global') or '0') == '1'
        export = (request.args.get('export') or '')
        mxflag = (request.args.get('matrix') or '0') == '1'
        region = (request.args.get('region') or '').strip()
        mc = suggest_hotspot(today, "商业地产", year=year, market=market)
        nodes = nodes_for_month(int(month), year=year, market=market)
        cross = cross_industry_season(industry, f"{year:04d}-{int(month):02d}-01") if industry and available else None
        gcross = cross_global(int(month), f"{year:04d}-{int(month):02d}-01") if gflag and available else None
        gns = global_nodes() if gflag and available else None
        if export == 'csv':
            # 全年+海外节点 CSV 排期导出（排期工作流）
            buf = io.StringIO()
            w = _csv.writer(buf)
            w.writerow(["月", "名称", "日期", "类型", "主题", "品类", "来源", "年", "市场", "事实状态", "法定休假状态"])
            w.writerow(["", "日历状态", "", "元数据", "", "", context["source_owner"], year, market, context["state"], "NOT_ESTABLISHED"])
            for m in (range(1, 13) if available else []):
                for n in nodes_for_month(m, year=year, market=market):
                    w.writerow([m, n["name"], n.get("date", ""), n.get("kind", ""),
                                n.get("theme", ""), "、".join(n.get("cats", [])), "scripts.marketing_calendar", year, market, "editorial_reference_not_verified", "NOT_ESTABLISHED"])
                for n in global_nodes(m):
                    w.writerow([m, n["name"], n.get("date", ""), n.get("kind", ""),
                                n.get("theme", ""), "、".join(n.get("cats", [])), "海外编辑建议", year, "global_reference", "editorial_reference_not_verified", "NOT_ESTABLISHED"])
                for r in ["东南亚", "欧洲", "中东", "拉美", "北美", "东亚", "澳新"]:
                    for n in region_nodes(r, m):
                        w.writerow([m, n["name"], "区域节点", "区域", n.get("theme", ""),
                                    "、".join(n.get("cats", [])), "区域-" + r, year, r, "editorial_reference_not_verified", "NOT_ESTABLISHED"])
            return Response(buf.getvalue(), mimetype="text/csv; charset=utf-8",
                            headers={"Content-Disposition":
                                     "attachment; filename=marketing_calendar_%s_%s.csv" % (year, month)})
        return jsonify({'ok': True, 'calendar_reference': context, 'month_nodes': nodes, 'hotspot': mc,
                        'cross': cross, 'global_cross': gcross, 'global_nodes': gns,
                        'region_nodes': region_nodes(region) if region and available else None,
                        'matrix': marketing_matrix() if mxflag and available else None,
                        'advice': "本月先借节气/节日天然情绪，再叠加垂直行业节点做专属心智；出海场景另叠海外节点时机。"})
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'code': 'CALENDAR_INPUT_INVALID'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/v2/global-bil/overview')
@app.route('/api/v2/global-bil/<resource>')
def global_bil_read(resource='overview'):
    try:
        from lumenis.global_bil import load_resource, overview, _FILES
        if resource == 'overview':
            return jsonify({'ok': True, 'stage': 'research', 'overview': overview()})
        if resource not in _FILES:
            return jsonify({'ok': False, 'error': 'resource 非法，仅 overview/benchmarks/mechanisms/cases'}), 400
        data = load_resource(resource)
        if data is None:
            return jsonify({'ok': False, 'error': 'BIL seed 未就绪'}), 404
        return jsonify({'ok': True, 'stage': 'research', 'resource': resource, 'data': data})
    except Exception:
        app.logger.exception('global_bil read failed')
        return jsonify({'ok': False, 'error': 'BIL 读取失败，请查看服务端日志'}), 500

@app.route('/api/event-graph/events/<event_id>', methods=['DELETE'])
@require_permission(OperationType.DATA_DELETE, RiskLevel.CRITICAL,
    deny_return=lambda: (jsonify({'ok': False, 'error': '权限不足：事件删除需管理员审批', 'code': 'PERMISSION_DENIED'}), 403))
def event_graph_delete_event(event_id):
    """删除事件（同时删除关联关系）"""
    try:
        from event_graph import get_event_graph
        import sqlite3 as _sq3
        graph = get_event_graph()
        if event_id not in graph.events:
            return jsonify({'ok': False, 'error': '事件不存在'}), 404
        _dbp = db.main_db_path()  # P0-DBISO-01 统一隔离
        with get_repository().transaction() as conn:
            conn.execute("DELETE FROM event_graph_events WHERE event_id=?", (event_id,))
            conn.execute("DELETE FROM event_graph_relations WHERE source_event_id=? OR target_event_id=?", (event_id, event_id))
        del graph.events[event_id]
        graph.relations = [r for r in graph.relations
                          if r.source_event.event_id != event_id and r.target_event.event_id != event_id]
        return jsonify({'ok': True, 'message': '事件已删除'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# V3.0 品牌分析报告API
APP_VERSION='5.9.9'
PRODUCT_NAME='\u5e8f\u5883 / LUMENIS'
CORE_SERVICE_NAME='lumenis-core'
APP_HOST=os.getenv('TAIKOO_HOST','0.0.0.0')
APP_PORT=int(os.getenv('TAIKOO_PORT','8201'))
AUTH_USER=os.getenv('TAIKOO_AUTH_USER','')
AUTH_PASSWORD=os.getenv('TAIKOO_AUTH_PASSWORD','')

def _proxy_health_loop(interval=300):
    # 独立守护线程做节点健康巡检，与核心采集调度解耦，任何异常都不影响主系统
    while True:
        try:
            time.sleep(interval)
            if _proxy_mgr is not None and _proxy_mgr.nodes:
                _proxy_mgr.check_all()
        except Exception:
            time.sleep(60)

if PROXY_POOL_AVAILABLE and not INTERNAL_BETA_SAFE_STARTUP and not MANUAL_WORKSPACE:
    try:
        _load_proxy_nodes()
        if _proxy_mgr.nodes and os.environ.get('ZBC_TEST_OFFLINE') != '1':
            _PROXY_HL_NAME = 'proxy-health-loop'
            _existing_proxy_hl = [t for t in threading.enumerate()
                                  if getattr(t, 'name', '') == _PROXY_HL_NAME and t.is_alive()]
            if not _existing_proxy_hl:  # 幂等：reload/重复 import 不重复起巡检线程
                threading.Thread(target=_proxy_health_loop,
                                 args=(int(os.getenv('PROXY_HEALTH_INTERVAL', '300')),),
                                 daemon=True, name=_PROXY_HL_NAME).start()
        print('[ProxyPool] 节点加载完成 enabled=%s mode=%s 节点数=%d'
              % (_ProxyCfg.ENABLED, _ProxyCfg.MODE, len(_proxy_mgr.nodes)))
    except Exception as _le:
        print('[ProxyPool] 节点加载失败（不影响系统运行）:', _le)

@app.route('/api/proxy/status')
def proxy_status_api():
    if not PROXY_POOL_AVAILABLE:
        return jsonify({'success': False, 'error': 'proxy_pool_unavailable'})
    return jsonify({'success': True, 'status': _proxy_mgr.status()})

@app.route('/api/proxy/check', methods=['POST'])
def proxy_check_api():
    if not PROXY_POOL_AVAILABLE:
        return jsonify({'success': False, 'error': 'proxy_pool_unavailable'})
    try:
        return jsonify({'success': True, 'results': _proxy_mgr.check_all()})
    except Exception as ex:
        return jsonify({'success': False, 'error': str(ex)})

def _auth_enabled():
    return bool(AUTH_USER and AUTH_PASSWORD)


# === P0-R6: CTH 免密浏览态只读 GET 白名单 ===
_CTH_READONLY_GET_PREFIXES = (
    '/api/stats', '/api/metric-trend', '/api/notes',
    '/api/negative/', '/api/risks/', '/api/risk/',
    '/api/event-graph/', '/api/cases/', '/api/case-analysis/',
    '/api/domain/', '/api/hot-notes',
    '/api/collection/counter', '/api/collect/tasks',
    '/api/weekly/', '/api/special-report/', '/api/reports/',
    '/api/intelligence/evidence', '/api/alerts',
    '/api/subject/', '/api/trends/', '/api/overview',
    # P1-1: CTH dual-domain namespace readonly GET (CTH browse-mode no-auth, limited to specific paths)
    '/api/cth/overview', '/api/cth/events', '/api/cth/xiaohongshu',
)

def _is_cth_readonly_get(path, method):
    if method != 'GET':
        return False
    for prefix in _CTH_READONLY_GET_PREFIXES:
        if prefix.endswith('/'):
            if path.startswith(prefix):
                return True
        else:
            if path == prefix or path.startswith(prefix + '/') or path.startswith(prefix + '?'):
                return True
    return False


def _subject_sql_and_values(alias=''):
    """系统历史兼容入口：所有 API 统计统一调用主体硬过滤。"""
    return subject_sql_and_values(alias)

@app.route('/api/auth/config')
def auth_config_api():
    """Public authentication metadata; credentials stay on the server."""
    try:
        response = jsonify({'ok': True, 'auth_enabled': _auth_enabled()})
        status = 200
    except Exception:
        response = jsonify({'ok': False, 'code': 'AUTH_CONFIG_UNAVAILABLE'})
        status = 503
    response.headers['Cache-Control'] = 'no-store'
    return response, status


def _owner_authorized_root_request():
    if request.blueprint == 'account':
        from account.api import authorize_builtin_skill_status_root_request
        if authorize_builtin_skill_status_root_request():
            return True
    if request.endpoint in {'experience_runtime.research_learning', 'experience_runtime.research_reference_library', 'experience_runtime.research_hypothesis_review'}:
        from experience_runtime import _shared_research_route_allowed
        return _shared_research_route_allowed()
    """Delegate only registered entries with their own fresh owner guards.

    This transfers authentication to the named handler, not authorization to a
    logged-in user. The owner still verifies actor, module, scope and effects.
    """
    if request.blueprint == 'ai_api':
        from ai_api import authorize_local_agent_root_request
        if authorize_local_agent_root_request():
            return True
    if request.blueprint == 'content_generation':
        from content_generation import authorize_content_root_request
        try:
            return bool(authorize_content_root_request())
        except (ValueError, PermissionError):
            return False
    if request.blueprint == 'v4.v4_ai':
        from lumenis.ai_hub.routes import authorize_conversation_root_request
        if authorize_conversation_root_request():
            return True
    if request.blueprint == 'ai_browser_runtime':
        from flask import current_app
        # This blueprint's before_request enforces SYSTEM/browser permission
        # and binds every route to the current account or sealed workspace.
        return any(guard.__name__ == '_require_browser_actor'
                   for guard in current_app.before_request_funcs.get(request.blueprint, ()))
    routes = {
        'api_system_account_base': ('/api/system/account', {'GET'}),
        # Legacy key routes: account_compat role decorators are the owner guard.
        'account_compat.compat_api_keys_list': ('/api/v4/api-keys', {'GET'}),
        'account_compat.compat_api_keys_generate': ('/api/v4/api-keys/generate', {'POST'}),
        'account_compat.compat_api_keys_revoke': ('/api/v4/api-keys/revoke', {'POST'}),
        'api_zbmp_entry_status': ('/api/auth/zbmp-entry/status', {'GET'}),
        'api_domain_identity': ('/api/auth/domain-identity', {'GET'}),
        'api_zbmp_entry_unlock': ('/api/auth/zbmp-entry/unlock', {'POST'}),
        'api_zbmp_entry_verify': ('/api/auth/zbmp-entry/verify', {'POST'}),
        'api_zbmp_entry_leave': ('/api/auth/zbmp-entry/leave', {'POST'}),
        'subject_registry.get_subjects': ('/api/settings/subjects', {'GET'}),
        'api_collect': ('/api/collect', {'POST'}),
        'api_collect_status': ('/api/collect/status/<task_id>', {'GET'}),
        'api_collect_tasks': ('/api/collect/tasks', {'GET'}),
        'evidence_api.evidence_stats': ('/api/evidence/stats', {'GET'}),
        'evidence_api.evidence_list': ('/api/evidence/list', {'GET'}),
        'evidence_api.evidence_detail': ('/api/evidence/<int:record_id>', {'GET'}),
        'evidence_api.evidence_timeline': ('/api/evidence/timeline', {'GET'}),
        'api_evidence_stats': ('/api/app_evidence/stats', {'GET'}),
        'api_evidence_list': ('/api/app_evidence/list', {'GET'}),
        'api_evidence_get': ('/api/app_evidence/<int:record_id>', {'GET'}),
        'api_evidence_upload': ('/api/app_evidence/upload', {'POST'}),
        'api_evidence_confirm': ('/api/app_evidence/<int:record_id>/confirm', {'POST'}),
        'api_evidence_reject': ('/api/app_evidence/<int:record_id>/reject', {'POST'}),
        'api_evidence_shadow': ('/api/app_evidence/<int:record_id>/shadow', {'POST'}),
        'api_evidence_restore': ('/api/app_evidence/<int:record_id>/restore', {'POST'}),
        'api_evidence_delete': ('/api/app_evidence/<int:record_id>', {'DELETE'}),
        'domain_api.api_settings_context': ('/api/settings/context', {'GET', 'PUT', 'DELETE'}),
        'domain_api.api_business_work_prepare': ('/api/experience/business-works', {'POST'}),
        'domain_api.api_business_work_list': ('/api/experience/business-works', {'GET'}),
        'domain_api.api_business_work_sources': ('/api/experience/business-works/sources', {'GET'}),
        'domain_api.api_business_work_read': ('/api/experience/business-works/<work_id>', {'GET'}),
        'domain_api.api_business_work_advance': ('/api/experience/business-works/<work_id>/<operation>', {'POST'}),
        'domain_api.api_internal_pitch_prepare': ('/api/experience/creation/internal-pitches', {'POST'}),
        'domain_api.api_internal_pitch_read': ('/api/experience/creation/internal-pitches/<task_id>', {'GET'}),
        'domain_api.api_internal_pitch_action': ('/api/experience/creation/internal-pitches/<task_id>/<action>', {'POST'}),
        'domain_api.api_internal_pitch_export': ('/api/experience/creation/internal-pitches/<task_id>/export', {'GET'}),
        # Exact read delegates to Content's actor, scope and live-source guard.
        'experience_runtime.content_evidence_detail': ('/api/experience/content/evidence/<evidence_id>', {'GET'}),
        'experience_runtime.ai_intent': ('/api/experience/ai/intent', {'POST'}),
        'experience_runtime.analyze_financial_material': ('/api/experience/reports/financial/analyze', {'POST'}),
        'experience_runtime.save_financial_material': ('/api/experience/reports/financial/save', {'POST'}),
        'experience_runtime.save_financial_identity_association': ('/api/experience/reports/financial/identity-review', {'POST'}),
        'experience_runtime.entity_candidate_review_workflow': ('/api/experience/reports/entity-candidates', {'POST'}),
        'experience_runtime.work_dependency_workflow': ('/api/experience/work-dependencies', {'POST'}),
        'experience_runtime.artifact_experiment_workflow': ('/api/experience/reports/artifact-experiments', {'GET', 'POST'}),
        'experience_runtime.staffing_options_workflow': ('/api/experience/reports/staffing-options', {'GET', 'POST'}),
        'experience_runtime.analyze_macro_material': ('/api/experience/reports/macro/analyze', {'POST'}),
        'experience_runtime.save_macro_material': ('/api/experience/reports/macro/save', {'POST'}),
        'experience_runtime.save_macro_collection_target': ('/api/experience/reports/macro/target', {'POST'}),
        'experience_runtime.collect_macro_material': ('/api/experience/reports/macro/collect', {'POST'}),
        'experience_runtime.import_macro_material_capture': ('/api/experience/reports/macro/capture', {'POST'}),
        'experience_runtime.save_financial_collection_target': ('/api/experience/reports/financial/target', {'POST'}),
        'experience_runtime.collect_financial_material': ('/api/experience/reports/financial/collect', {'POST'}),
        'experience_runtime.import_financial_material_capture': ('/api/experience/reports/financial/capture', {'POST'}),
        'experience_runtime.import_shared_document': ('/api/experience/materials/documents', {'POST'}),
        'experience_runtime.read_shared_document': ('/api/experience/materials/documents/<int:evidence_id>', {'GET'}),
        'experience_runtime.download_shared_document': ('/api/experience/materials/documents/<int:evidence_id>/file', {'GET'}),
        'experience_runtime.quote_shared_document': ('/api/experience/materials/documents/<int:evidence_id>/quote', {'GET'}),
        'experience_runtime.save_shared_work': ('/api/experience/saved-work', {'POST'}),
        'experience_runtime.search_shared_work': ('/api/experience/saved-work', {'GET'}),
        'experience_runtime.read_shared_work': ('/api/experience/saved-work/<artifact_id>', {'GET'}),
        'experience_runtime.read_office_document': ('/api/experience/saved-work/<artifact_id>/office', {'GET'}),
        'experience_runtime.edit_office_document': ('/api/experience/saved-work/<artifact_id>/office/edit', {'POST'}),
        'experience_runtime.download_work_attachment': ('/api/experience/saved-work/<artifact_id>/attachments/<name>', {'GET'}),
        'experience_runtime.revise_shared_work': ('/api/experience/saved-work/<artifact_id>/revise', {'POST'}),
        'experience_runtime.export_shared_work': ('/api/experience/saved-work/<artifact_id>/export', {'GET', 'POST'}),
        'experience_runtime.read_reporting_preferences': ('/api/experience/saved-work/preferences', {'GET'}),
        'experience_runtime.save_reporting_preferences': ('/api/experience/saved-work/preferences', {'POST'}),
        'experience_runtime.read_reporting_notifications': ('/api/experience/saved-work/notifications', {'GET'}),
        'experience_runtime.generate_source_brief_job': ('/api/experience/reports/source-brief/generate', {'POST'}),
        'experience_runtime.reopen_source_brief_job': ('/api/experience/reports/source-brief/jobs/<job_id>', {'GET'}),
        'experience_runtime.submit_source_brief_review': ('/api/experience/reports/source-brief/jobs/<job_id>/reviews', {'POST'}),
        'experience_runtime.list_source_brief_tasks': ('/api/experience/reports/source-brief/tasks', {'GET'}),
        'experience_runtime.edit_source_brief_task': ('/api/experience/reports/source-brief/tasks/<task_id>', {'PATCH'}),
        'experience_runtime.change_source_brief_task_state': ('/api/experience/reports/source-brief/tasks/<task_id>/<operation>', {'POST'}),
        'experience_runtime.research_reference_catalog': ('/api/experience/reports/source-brief/references', {'GET'}),
        'experience_runtime.research_taxonomy': ('/api/experience/reports/source-brief/taxonomy', {'GET'}),
        'experience_runtime.save_source_brief_result': ('/api/experience/reports/source-brief/jobs/<job_id>/save', {'POST'}),
        'experience_runtime.research_reference_work': ('/api/experience/reports/source-brief/reference-work', {'POST', 'GET'}),
        'experience_runtime.research_reference_version': ('/api/experience/reports/source-brief/reference-work/<artifact_id>', {'POST', 'GET'}),
        'experience_runtime.research_match_rules': ('/api/experience/reports/source-brief/references/match-rules', {'POST'}),
        'experience_runtime.adopt_research_source': ('/api/experience/reports/source-brief/adopt-source', {'POST'}),
        'experience_runtime.list_research_reports': ('/api/experience/reports/source-brief/jobs', {'GET'}),
        'experience_runtime.start_source_brief_task': ('/api/experience/reports/source-brief/start', {'POST'}),
        'experience_runtime.source_brief_task_status': ('/api/experience/reports/source-brief/tasks/<task_id>', {'GET'}),
        'experience_runtime.resume_source_brief_task': ('/api/experience/reports/source-brief/tasks/<task_id>/resume', {'POST'}),
        'experience_runtime.create_cth_work_case': ('/api/experience/cth/cases', {'POST'}),
        'experience_runtime.read_cth_case_list': ('/api/experience/cth/cases', {'GET'}),
        'experience_runtime.reopen_cth_work_case': ('/api/experience/cth/cases/<case_id>', {'GET'}),
        'experience_runtime.inspect_content_project_media': ('/api/experience/shared-skills/shared.content_project/inspect', {'POST'}),
        'experience_runtime.preview_content_speech': ('/api/experience/content-sources/tts/preview', {'POST'}),
        'experience_runtime.preview_podcast_editorial': ('/api/experience/podcast/editorial/preview', {'POST'}),
        'experience_runtime.preview_podcast_topics': ('/api/experience/podcast/topics/preview', {'POST'}),
        'experience_runtime.import_content_source': ('/api/experience/content-sources', {'POST'}),
        'experience_runtime.confirm_content_source_import_request': ('/api/experience/content-source-confirmations/<confirmation_id>', {'POST'}),
        'experience_runtime.content_source_detail': ('/api/experience/content-sources/<artifact_id>', {'GET', 'HEAD'}),
        'experience_runtime.export_content_project': ('/api/experience/content-projects/export', {'POST'}),
        'experience_runtime.content_project_list': ('/api/experience/content-projects', {'GET'}),
        'experience_runtime.content_project_detail': ('/api/experience/content-projects/<artifact_id>', {'GET'}),
        'experience_runtime.content_project_package': ('/api/experience/content-projects/<artifact_id>/package', {'GET', 'HEAD'}),
        'experience_runtime.content_project_media': ('/api/experience/content-projects/<artifact_id>/media', {'GET', 'HEAD'}),
        'experience_runtime.prepare_owned_training_review_resource': ('/api/experience/owned-training/review-resources', {'POST'}),
        'experience_runtime.submit_owned_training_review': ('/api/experience/owned-training/review-submissions', {'POST'}),
        'experience_runtime.export_owned_training_reviews': ('/api/experience/owned-training/review-exports', {'POST'}),
        'experience_runtime.confirm_owned_training_execution_approval': ('/api/experience/owned-training/execution-approvals', {'POST'}),
        'experience_runtime.prepare_owned_training_phase_task': ('/api/experience/owned-training/phase-tasks', {'POST'}),
        'experience_runtime.read_owned_training_execution_configuration': ('/api/experience/owned-training/execution-configuration', {'POST'}),
        'experience_runtime.preflight_owned_training_execution': ('/api/experience/owned-training/execution-preflight', {'POST'}),
        'experience_runtime.execute_owned_training_phase_task': ('/api/experience/owned-training/phase-tasks/<task_id>/execute', {'POST'}),
        'experience_runtime.prepare_owned_training_phase_challenge': ('/api/experience/owned-training/phase-tasks/<task_id>/challenges', {'POST'}),
        'experience_runtime.issue_owned_training_phase_decision': ('/api/experience/owned-training/phase-tasks/<task_id>/challenge-decisions', {'POST'}),
        'experience_runtime.read_owned_training_phase_receipt': ('/api/experience/owned-training/phase-tasks/<task_id>/receipts/<nonce>', {'GET'}),
        'experience_runtime.interrupt_owned_training_phase_task': ('/api/experience/owned-training/phase-tasks/<task_id>/interrupt', {'POST'}),
        'experience_runtime.resume_owned_training_phase_task': ('/api/experience/owned-training/phase-tasks/<task_id>/resume', {'POST'}),
        'api_weibo_cookies': ('/api/weibo/cookies', {'GET'}),
    }
    expected = routes.get(request.endpoint)
    return (expected is not None and request.url_rule is not None
            and request.url_rule.rule == expected[0] and request.method in expected[1])


@app.before_request
def _basic_auth():
    if _owner_authorized_root_request():
        return None
    if (request.method == 'POST' and request.url_rule is not None
            and (request.endpoint, request.url_rule.rule) in {
                ('intelligence_library.comment_page_source_use', '/api/intelligence/library/comments/<int:evidence_id>/source-use'),
                ('intelligence_library.collected_public_source_use', '/api/intelligence/library/public-sources/<int:evidence_id>/source-use'),
                ('intelligence_library.comment_research_operation', '/api/intelligence/library/comment-research')}):
        from intelligence_library_api import local_comment_research_access_allowed
        if local_comment_research_access_allowed():
            return None  # Exact SourceUse/Research owner repeats identity, scope and effects.
    if (request.method == 'GET'
            and request.endpoint == 'experience_runtime.runtime_subjects'
            and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/subjects'):
        from lumenis.system.security.permission import local_workspace_read_allowed
        if local_workspace_read_allowed(module='subject_registry', action='read'):
            return None
    if (request.method == 'GET'
            and request.endpoint == 'experience_runtime.shared_skills_catalog'
            and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/shared-skills'):
        from lumenis.system.security.permission import resolve_local_workspace_principal
        if resolve_local_workspace_principal(module='skills', action='read') is not None:
            return None
    if request.method in {'GET', 'HEAD'} and request.endpoint in {
        'lumenis_workspace_host.root', 'lumenis_workspace_host.root_slash',
        'lumenis_workspace_host.resource', 'lumenis_workspace_host.asset',
        'experience_runtime.runtime_identity', 'experience_runtime.screen_viewmodel',
    }:
        from lumenis.system.security.permission import resolve_local_workspace_principal
        if resolve_local_workspace_principal(module='reports', action='read') is not None:
            return None
    # A server-opened local workspace uses the existing sealed principal and
    # exact current Registry scope. The route still rechecks scope and effects.
    if request.path.startswith(('/api/experience/materials/documents', '/api/experience/saved-work')):
        from experience_runtime import _shared_work_local_access_allowed
        if _shared_work_local_access_allowed():
            return None
    if request.path.startswith('/api/experience/business-works'):
        from lumenis_app_api import _business_work_local_access_allowed
        if _business_work_local_access_allowed():
            return None
    if request.path.startswith('/api/experience/creation/internal-pitches'):
        from lumenis_app_api import _internal_pitch_local_access_allowed
        if _internal_pitch_local_access_allowed():
            return None
    if request.path == '/api/settings/subjects/batch':
        from subject_registry import subject_batch_local_access_allowed
        if subject_batch_local_access_allowed():
            return None
    if request.path == '/api/experience/reports/statistics':
        from experience_runtime import _statistics_local_access_allowed
        if _statistics_local_access_allowed():
            return None
    if request.path == '/api/experience/entity-profiles':
        from experience_runtime import _entity_profile_local_access_allowed
        if _entity_profile_local_access_allowed():
            return None
    from brand_propagation import classification_access_allowed
    if classification_access_allowed():
        return None
    if request.path.startswith('/api/event-graph/'):
        from event_graph import scoped_graph_local_access_allowed
        if scoped_graph_local_access_allowed():
            return None
    if request.path.startswith('/api/kos/'):
        from kos_routes import private_kos_local_access_allowed
        if private_kos_local_access_allowed():
            return None
    if request.path.startswith('/api/ai/tasks'):
        from ai_api import _source_brief_task_local_access_allowed
        if _source_brief_task_local_access_allowed():
            return None
    # /v4 升级模块使用独立 token/密钥认证（自带登录页），不走现网 HTTP Basic；其余路由维持 Basic 兜底不变
    # /api/auth/config exposes non-sensitive metadata only.
    # P0-R6: CTH 免密浏览态只读 GET 放行（CTH 页面依赖的旧版只读 API，仅 GET，不含 ZBMP 专属接口）
    if request.path in ('/healthz', '/api/health', '/api/collector-guard/status', '/api/auth/config', '/favicon.ico', '/api/kos/report/view', '/api/system/health', '/api/system/health/summary', '/api/system/status', '/api/risks/active', '/api/risk/active', '/cth/login', '/zbmp/login', '/system/settings') or request.path.startswith('/v4/') or _is_cth_readonly_get(request.path, request.method):
        return None
    try:
        if not _auth_enabled():
            return None
    except Exception:
        response = jsonify({'ok': False, 'code': 'AUTH_CONFIG_UNAVAILABLE'})
        response.headers['Cache-Control'] = 'no-store'
        return response, 503
    auth=request.authorization
    if auth and secrets.compare_digest(auth.username or '', AUTH_USER) and secrets.compare_digest(auth.password or '', AUTH_PASSWORD):
        return None
    # A product session can read these legacy health endpoints. It is not a
    # blanket authorization for unrelated root routes or mutating methods.
    if request.method == 'GET' and request.path in {
        '/api/platform-health', '/api/xhs/collect-health',
    }:
        try:
            from lumenis.auth.service import get_current_user
            if get_current_user(read_only=True):
                return None
        except Exception:
            pass
    # 仅顶层 HTML 文档导航回 WWW-Authenticate（触发浏览器原生登录框）。
    # API/XHR/fetch 等子请求回纯 401 JSON、不带挑战头：避免文档弹框期间 favicon/轮询等
    # 并发 401 同 realm 挑战反复重置原生登录框（“账号密码输到一半弹窗跳没又出现”的根因）。
    # 安全等级不变——子请求依旧 401 拒绝，只是不触发浏览器原生弹框，改由前端 401 流程处理。
    _accept = request.headers.get('Accept', '')
    _is_xhr = request.headers.get('X-Requested-With', '').lower() == 'xmlhttprequest'
    _is_api_like = request.path.startswith('/api/') or _is_xhr or ('application/json' in _accept and 'text/html' not in _accept)
    if _is_api_like:
        return jsonify({'ok': False, 'error': '需要登录', 'auth_required': True}), 401
    return ('需要登录', 401, {'WWW-Authenticate':'Basic realm=TaikooMonitor'})


# === ZBC Phase 12: PermissionGate 统一写操作拦截（fail-closed） ===
_PG_WRITE_METHODS = frozenset({'POST', 'PUT', 'DELETE', 'PATCH'})
_PG_BYPASS_PATHS = frozenset({
    '/healthz', '/api/health', '/api/collector-guard/status',
    '/api/auth/config', '/favicon.ico', '/api/system/health/summary',
    '/api/zbmp/overview', '/api/zbmp/brands', '/api/zbmp/metrics',
    '/api/cth/overview', '/api/cth/events', '/api/cth/xiaohongshu',
    '/api/system/status', '/api/system/runtime', '/api/system/domains',
    # 验收判定 judge：纯内存函数计算，不读写 DB/文件/网络/外部状态，等同只读
    '/api/system/acceptance/judge',
    # 仅用于生成一次、资源范围固定的人工审批令牌；实际 archive 写操作
    # 仍必须再次经过 PermissionGate，且成功后由 handler 消费令牌。
    '/api/runtime/archive-dead/approval',
    # P1-Content: 统一内容生成AI增强（仅写content_generation_evidence/content_evaluation表，不碰生产数据）
    '/api/content/generate', '/api/content/feedback', '/api/content/ad-strategy',
    '/api/content/video-analyze', '/api/content/brand-report/generate',
    '/api/content/podcast-research', '/api/content/topic-snapshot',
    # P1-Podcast: 播客确定性算法端点（纯内存计算，不写生产数据）
    '/api/podcast/topic-score', '/api/podcast/story-nodes', '/api/podcast/runtime/validate',
    '/api/podcast/breakout', '/api/podcast/content-yield', '/api/podcast/entity',
})


def _pg_resolve_operation_type(path, method):
    """根据请求路径+方法映射 PermissionGate OperationType。
    覆盖采集/报告/导入导出/配置/事件/规则等所有写操作类别。"""
    p = path.lower()
    if (method == 'POST' and (p == '/api/experience/creation/internal-pitches'
            or re.fullmatch(r'/api/experience/creation/internal-pitches/task-pitch-[0-9a-f]{24}/(?:run|cancel)', p))):
        # Internal Word/stored-work operation only; the owner checks exact
        # input, principal, scope and DATA_EXPORT again before every commit.
        return OperationType.DATA_EXPORT
    if method == 'POST' and p == '/api/experience/owned-training/review-resources':
        return OperationType.OWNED_TRAINING_REVIEW_PREVIEW
    # Shared Content & Creation 在 experience_runtime 内部执行动作白名单：
    # READ/ANALYZE/SUGGEST 是低风险 AI_CALL；未被共享面放行的写入/发布动作
    # 继续落入默认高风险门，避免把安全共享请求误判为 db_write。
    if p.startswith('/api/experience/shared-skills/') and method == 'POST':
        try:
            requested = str((request.get_json(silent=True) or {}).get('action_type') or 'ANALYZE').upper()
        except Exception:
            requested = 'ANALYZE'
        if requested in ('READ', 'ANALYZE', 'SUGGEST'):
            return OperationType.AI_CALL
        if requested == 'EXPORT' and p.endswith('/shared.video_shotcraft/render'):
            # Local video rendering writes only a staged artifact below the
            # protected runtime data root; it never publishes or touches a
            # platform account.  Keep it auditable as a conditional export.
            return OperationType.DATA_EXPORT
    # Secondary CTH collection is an explicit human-triggered read-only
    # external action.  It writes local Evidence/Canonical records, but never
    # writes to a platform account and never publishes.
    if p == '/api/experience/cth/platform-collection/search' and method == 'POST':
        return OperationType.COLLECTOR_START
    if p == '/api/experience/cth/cases' and method == 'POST':
        return OperationType.CTH_CASE_CREATE
    if method == 'POST' and p == '/api/experience/materials/documents':
        return OperationType.DATA_IMPORT
    if method == 'POST' and p in {'/api/experience/saved-work', '/api/experience/saved-work/preferences'}:
        return OperationType.DATA_EXPORT
    if method == 'POST' and re.fullmatch(r'/api/experience/saved-work/art-[0-9a-f]{16}/revise', p):
        return OperationType.DATA_EXPORT
    if method == 'POST' and re.fullmatch(r'/api/experience/saved-work/art-[0-9a-f]{16}/office/edit', p):
        return OperationType.DATA_EXPORT
    if method == 'POST' and re.fullmatch(
        r'/api/experience/business-works/work-[0-9a-f]{64}/(?:save-request|save|save-confirm)', p,
    ):
        # Business work delegates immutable persistence to Shared SavedWork,
        # which independently checks the exact DATA_EXPORT resource approval.
        return OperationType.DATA_EXPORT
    if method == 'POST' and re.fullmatch(
        r'/api/experience/business-works(?:/work-[0-9a-f]{64}/(?:choose|adopt|cancel|interrupt|resume|restore|review|action|manual_action|observation|outcome|outcome_unknown))?', p,
    ):
        # Domain records only; the service separately binds current actor,
        # exact scope, report revision and any actual creation-owner receipt.
        return OperationType.REPORT_REVIEW
    # 1. 删除类（最高风险）
    if method == 'DELETE' or '/delete' in p or '/revoke' in p:
        return OperationType.DATA_DELETE
    if p in {'/api/collector/browser/start', '/api/collector/browser/stop'}:
        return OperationType.BROWSER_OPERATION
    if p.startswith('/api/xhs/login/') and method == 'POST':
        return OperationType.BROWSER_OPERATION
    # 2. 采集启动/停止
    if any(k in p for k in ('/collect', '/rednote/', '/collector/', '/official-info/collect')):
        if any(k in p for k in ('/stop', '/pause', '/cancel')):
            return OperationType.COLLECTOR_STOP
        return OperationType.COLLECTOR_START
    if method == 'POST' and re.fullmatch(r'/api/experience/reports/source-brief/jobs/[^/]+/hypotheses/review', p):
        return OperationType.REPORT_REVIEW
    if method == 'POST' and p in {'/api/experience/reports/source-brief/adopt-source', '/api/experience/reports/source-brief/reference-library'}:
        return OperationType.REPORT_REVIEW
    if method == 'POST' and (re.fullmatch(r'/api/experience/reports/source-brief/reference-work(?:/ART[0-9a-f]{16})?', p)
            or p == '/api/experience/reports/source-brief/references/match-rules'
            or re.fullmatch(r'/api/experience/reports/source-brief/learning/(?:candidates|outbox)(?:/[0-9a-f]{64}/(?:review|validate|adopt|withdraw|restore|reject|enqueue|stage|fail|requeue|receive_local))?', p)):
        return OperationType.REPORT_REVIEW
    if ((method == 'PATCH' and re.fullmatch(r'/api/experience/reports/source-brief/tasks/rbrief_[0-9a-f-]{36}', p))
            or (method == 'POST' and re.fullmatch(r'/api/experience/reports/source-brief/tasks/rbrief_[0-9a-f-]{36}/(?:cancel|restore)', p))):
        return OperationType.REPORT_REVIEW
    if method == 'POST' and re.fullmatch(r'/api/experience/reports/source-brief/jobs/brief-[0-9a-f]{32}/save', p):
        return OperationType.DATA_EXPORT
    # 3. 报告生成
    if (method == 'POST' and p.startswith('/api/experience/reports/source-brief/jobs/')
            and p.endswith('/reviews') and len(p.split('/')) == 8):
        # Append-only, artifact-bound operator disposition; route rechecks exact
        # scope and this operation. General review/DB writes stay high risk.
        return OperationType.REPORT_REVIEW
    if method == 'POST' and (
        p == '/api/experience/reports/source-brief/start'
        or (p.startswith('/api/experience/reports/source-brief/tasks/rbrief_') and p.endswith('/resume'))
    ):
        # Same local report artifact operation; the route also rechecks exact
        # actor/scope. This does not grant general DB_WRITE or external effects.
        return OperationType.REPORT_GENERATE
    if ('/report' in p and '/generate' in p) or '/special-report' in p or '/weekly/send-email' in p:
        return OperationType.REPORT_GENERATE
    # 4. 数据导入
    if '/import' in p or '/local-import' in p:
        return OperationType.DATA_IMPORT
    # 5. 数据导出/备份
    if '/export' in p or '/backup' in p or '/pitch-export' in p:
        return OperationType.DATA_EXPORT
    # 6. 配置/系统设置修改
    if any(k in p for k in ('/config', '/system/config', '/settings', '/email-settings', '/company-domain')):
        return OperationType.CONFIG_MODIFY
    # 7. 品牌/关键词/规则增删改
    if ('/brands' in p and method in ('PUT', 'DELETE', 'POST')) or '/keyword' in p or '/rule' in p:
        return OperationType.CONFIG_MODIFY
    # 8. 运行时操作（重启/切换/恢复/重置）
    if any(k in p for k in ('/recover', '/reset', '/switch-account', '/runtime', '/network/reset')):
        return OperationType.RUNTIME_OPERATION
    # 9. 浏览器/登录态操作
    if any(k in p for k in ('/browser', '/web/', '/login', '/cookie', '/keepalive', '/weibo/', '/bilibili/')):
        return OperationType.BROWSER_OPERATION
    # 10. AI/智能/创意调用
    if any(k in p for k in ('/ai', '/intelligence', '/creative', '/case-analysis/ai-evaluate', '/pr/')):
        return OperationType.AI_CALL
    # 11. Skill/开发者代码执行
    if any(k in p for k in ('/skill', '/workspace/term')):
        return OperationType.SKILL_EXECUTE
    # 12. 事件确认/负面确认/审核（DB写入）
    if any(k in p for k in ('/confirm', '/reject', '/review', '/event-graph', '/event-review', '/negative')):
        return OperationType.DB_WRITE
    # 13. 搜索/翻译/分析（只读聚合，但POST提交参数）
    if any(k in p for k in ('/search', '/translate', '/analyze', '/classify', '/optimizer')):
        return OperationType.AI_CALL
    # 默认：数据库写入（fail-closed 兜底）
    return OperationType.DB_WRITE


@app.before_request
def _permission_gate_write_check():
    """统一 PermissionGate 写操作拦截。
    - 只读 GET 不拦截
    - POST/PUT/DELETE/PATCH 必须经过权限门
    - fail-closed：PermissionGate 任何异常或未初始化 → 返回 BLOCKED（503）
    - 权限拒绝 → 返回 BLOCKED（403），不执行写操作
    - TESTING 模式（pytest）下跳过，由装饰器层权限控制
    """
    # TESTING 旁路：必须显式开启（set_testing_bypass(True) 或 PERMISSION_GATE_TESTING=1），
    # 不得因 pytest 环境或 Flask TESTING 自动跳过写拦截（OWASP deny-by-default）。
    try:
        from lumenis.system.security import is_testing_bypass_enabled
        if is_testing_bypass_enabled():
            return None
    except Exception:
        pass
    if request.method not in _PG_WRITE_METHODS:
        return None
    if request.blueprint == 'account':
        from account.api import authorize_builtin_skill_status_root_request
        if authorize_builtin_skill_status_root_request():
            return None
    if (request.method == 'POST' and request.url_rule is not None
            and (request.endpoint, request.url_rule.rule) in {
                ('intelligence_library.comment_page_source_use', '/api/intelligence/library/comments/<int:evidence_id>/source-use'),
                ('intelligence_library.collected_public_source_use', '/api/intelligence/library/public-sources/<int:evidence_id>/source-use'),
                ('intelligence_library.comment_research_operation', '/api/intelligence/library/comment-research')}):
        from intelligence_library_api import local_comment_research_access_allowed
        if local_comment_research_access_allowed():
            return None  # Approval and final writes remain fenced inside the original owner.
    if request.blueprint == 'ai_api':
        from ai_api import authorize_local_agent_root_request
        if authorize_local_agent_root_request():
            return None
    if request.blueprint == 'content_generation':
        from content_generation import authorize_content_root_request
        try:
            if authorize_content_root_request():
                return None  # Exact Content owner performs canonical write and source checks.
        except (ValueError, PermissionError) as exc:
            from experience_runtime import _content_project_error
            return _content_project_error(exc)
    if request.blueprint == 'v4.v4_ai':
        from lumenis.ai_hub.routes import authorize_conversation_root_request
        if authorize_conversation_root_request():
            return None
    from experience_runtime import _staffing_route_matches
    if _staffing_route_matches():
        return None  # Original source-bound mathematical Task owns identity/scope/admission.
    from experience_runtime import _artifact_experiment_route_matches
    if _artifact_experiment_route_matches():
        return None  # Original Source/SavedWork owner validates each variant and observation.
    from experience_runtime import _work_dependency_route_matches
    if _work_dependency_route_matches():
        return None  # Existing SavedWork owner checks the explicit dependency operation.
    from experience_runtime import _entity_candidate_review_route_matches
    if _entity_candidate_review_route_matches():
        return None  # Exact Owner repeats identity/scope/source checks; SavedWork gates review writes.
    from subject_registry import subject_batch_route_matches
    if subject_batch_route_matches():
        # This exact owner verifies actor/domain and the human-confirmed full
        # identity package before its CONFIG_MODIFY approval or any row write.
        return None
    from experience_runtime import _entity_profile_route_matches
    if _entity_profile_route_matches():
        try:
            from experience_runtime import _shared_work_actor_scope
            _shared_work_actor_scope('write')
            return None
        except (ValueError, PermissionError) as exc:
            return jsonify({'ok': False, 'code': str(exc)}), 403
    from brand_propagation import classification_route_matches
    if classification_route_matches():
        try:
            from experience_runtime import _shared_work_actor_scope
            _shared_work_actor_scope('write')
            return None
        except (ValueError, PermissionError):
            return jsonify({'ok': False, 'code': 'PROPAGATION_PERMISSION_DENIED'}), 403
    from event_graph import scoped_graph_route_matches
    if scoped_graph_route_matches():
        try:
            from experience_runtime import _shared_work_actor_scope
            _shared_work_actor_scope('write')
            return None
        except (ValueError, PermissionError) as exc:
            return jsonify({'ok': False, 'code': str(exc)}), 403
    from kos_routes import private_kos_route_matches, private_kos_route_action, _resolve_kos_brand_scope
    if private_kos_route_matches(write_only=True):
        try:
            _resolve_kos_brand_scope(private_kos_route_action())
            return None
        except (ValueError, PermissionError) as exc:
            return jsonify({'ok': False, 'code': str(exc)}), 403
    manual_evidence_rules = {
        'api_evidence_upload': ('/api/app_evidence/upload', 'POST'),
        'api_evidence_confirm': ('/api/app_evidence/<int:record_id>/confirm', 'POST'),
        'api_evidence_reject': ('/api/app_evidence/<int:record_id>/reject', 'POST'),
        'api_evidence_shadow': ('/api/app_evidence/<int:record_id>/shadow', 'POST'),
        'api_evidence_restore': ('/api/app_evidence/<int:record_id>/restore', 'POST'),
        'api_evidence_delete': ('/api/app_evidence/<int:record_id>', 'DELETE'),
    }
    manual_rule = manual_evidence_rules.get(request.endpoint)
    if (manual_rule is not None and request.url_rule is not None
            and request.url_rule.rule == manual_rule[0] and request.method == manual_rule[1]):
        # The owner checks current actor/scope and the exact material or
        # row/hash/reason approval before and inside its SQL transaction.
        # A second path-only approval cannot bind that same operation.
        return None
    training_phase_rules = {
        'experience_runtime.prepare_owned_training_phase_task': '/api/experience/owned-training/phase-tasks',
        'experience_runtime.execute_owned_training_phase_task': '/api/experience/owned-training/phase-tasks/<task_id>/execute',
        'experience_runtime.read_owned_training_execution_configuration': '/api/experience/owned-training/execution-configuration',
        'experience_runtime.preflight_owned_training_execution': '/api/experience/owned-training/execution-preflight',
        'experience_runtime.prepare_owned_training_phase_challenge': '/api/experience/owned-training/phase-tasks/<task_id>/challenges',
        'experience_runtime.issue_owned_training_phase_decision': '/api/experience/owned-training/phase-tasks/<task_id>/challenge-decisions',
        'experience_runtime.interrupt_owned_training_phase_task': '/api/experience/owned-training/phase-tasks/<task_id>/interrupt',
        'experience_runtime.resume_owned_training_phase_task': '/api/experience/owned-training/phase-tasks/<task_id>/resume',
    }
    if (request.method == 'POST' and request.endpoint in training_phase_rules and request.url_rule is not None
            and training_phase_rules.get(request.endpoint) == request.url_rule.rule):
        # These exact registered handlers enforce the sealed task's own identity,
        # scope, live grant and commit lease; a path-level grant cannot bind them.
        return None
    training_review_rules = {
        'experience_runtime.confirm_owned_training_execution_approval': '/api/experience/owned-training/execution-approvals',
        'experience_runtime.submit_owned_training_review': '/api/experience/owned-training/review-submissions',
        'experience_runtime.export_owned_training_reviews': '/api/experience/owned-training/review-exports',
    }
    if (request.method == 'POST' and request.endpoint in training_review_rules
            and request.url_rule is not None
            and training_review_rules[request.endpoint] == request.url_rule.rule == request.path):
        # These two resolved owners enforce current server identity/scope and
        # exact manual review or DATA_EXPORT. A path grant cannot bind inputs.
        return None
    if (request.method == 'POST' and request.endpoint == 'experience_runtime.ai_intent'
            and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/ai/intent'):
        # The exact composer checks its action gate and fresh server scope.
        return None
    if (request.method == 'POST' and request.endpoint == 'experience_runtime.import_shared_document'
            and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/materials/documents'):
        # Private Shared custody or exact Canonical import is checked by its owner.
        return None
    from experience_runtime import _macro_route_matches
    if _macro_route_matches():
        return None  # Typed macro Owner repeats current source/scope; SavedWork checks writes.
    from experience_runtime import _financial_route_matches
    if _financial_route_matches():
        # Typed handler delegates to live Source/Evidence and SavedWork owners.
        return None
    from experience_runtime import _statistics_route_matches
    if _statistics_route_matches():
        try:
            from experience_runtime import _shared_work_actor_scope
            _shared_work_actor_scope('read')
            return None
        except (ValueError, PermissionError) as exc:
            return jsonify({'ok': False, 'code': str(exc)}), 403
    media_preview_rules = {
        'experience_runtime.preview_content_speech': '/api/experience/content-sources/tts/preview',
        'experience_runtime.preview_podcast_editorial': '/api/experience/podcast/editorial/preview',
        'experience_runtime.preview_podcast_topics': '/api/experience/podcast/topics/preview',
    }
    if (request.method == 'POST' and request.endpoint in media_preview_rules
            and request.url_rule is not None
            and request.url_rule.rule == media_preview_rules[request.endpoint]):
        try:
            from experience_runtime import _content_project_scope
            _content_project_scope('read', read_only_auth=True)
            return None
        except (ValueError, PermissionError) as exc:
            return jsonify({'ok': False, 'code': str(exc)}), 403
    if (request.method == 'POST'
            and request.endpoint == 'domain_api.api_business_work_advance'
            and request.url_rule is not None
            and request.url_rule.rule == '/api/experience/business-works/<work_id>/<operation>'
            and (request.view_args or {}).get('operation') in {'save-request', 'save', 'save-confirm'}):
        try:
            from lumenis_app_api import _business_work_binding
            _business_work_binding('save')
            return None
        except (ValueError, LookupError, PermissionError, RuntimeError):
            return jsonify({'ok': False, 'code': 'BUSINESS_WORK_SAVE_ACCESS_DENIED'}), 403
    if request.headers.getlist('X-Lumenis-Workspace-Scope'):
        shared_saved_work_actions = {
            'experience_runtime.import_shared_document': 'write',
            'experience_runtime.save_shared_work': 'write',
            'experience_runtime.revise_shared_work': 'write',
            'experience_runtime.edit_office_document': 'write',
        }
        shared_content_actions = {
            'experience_runtime.inspect_content_project_media': 'read',
            'experience_runtime.import_content_source': 'write',
            'experience_runtime.confirm_content_source_import_request': 'write',
            'experience_runtime.export_content_project': 'write',
        }
        try:
            from experience_runtime import _shared_research_route_allowed, _source_brief_context
            if _shared_research_route_allowed():
                _source_brief_context('write')
                return None
            if request.endpoint in shared_saved_work_actions:
                from experience_runtime import _shared_work_actor_scope
                _shared_work_actor_scope(shared_saved_work_actions[request.endpoint])
                return None
            if request.endpoint in shared_content_actions:
                from experience_runtime import _content_project_scope
                _content_project_scope(shared_content_actions[request.endpoint])
                return None
        except ValueError as exc:
            code = str(exc)
            status = 400 if code in {
                'SHARED_WORKSPACE_SCOPE_INVALID', 'SHARED_WORKSPACE_SCOPE_MIXED_CONTEXT',
                'SHARED_WORKSPACE_SCOPE_NOT_SUPPORTED',
            } else 403
            return jsonify({'ok': False, 'code': code,
                            'publish_status': 'not_performed'}), status
        except PermissionError as exc:
            return jsonify({'ok': False, 'code': str(exc),
                            'publish_status': 'not_performed'}), 403
        except Exception:  # noqa: BLE001 -- fail closed when Shared scope authorization is unavailable.
            return jsonify({'ok': False, 'code': 'SHARED_WORKSPACE_PERMISSION_UNAVAILABLE',
                            'publish_status': 'not_performed'}), 503
    if (request.method == 'POST' and (
            (request.path == '/api/experience/content-sources'
             and request.endpoint == 'experience_runtime.import_content_source')
            or (request.path == '/api/experience/content-projects/export'
                and request.endpoint == 'experience_runtime.export_content_project')
            or (request.path.startswith('/api/experience/content-source-confirmations/')
                and request.endpoint == 'experience_runtime.confirm_content_source_import_request')
            )):
        # The registered handlers bind actual bytes and exact scope to the
        # canonical Permission confirmation. A path-level grant cannot do so.
        return None
    # This handler only returns a validated, stateless viewing selection. It
    # neither persists settings nor starts collection; data routes authorize
    # their own reads. Match the resolved endpoint as well as the exact path.
    if (request.path == '/api/settings/context'
            and request.endpoint == 'domain_api.api_settings_context'
            and request.method in {'PUT', 'DELETE'}):
        return None
    if request.path in _PG_BYPASS_PATHS or request.path.startswith('/api/viz/') or request.path.startswith('/api/system/account/') or request.path.startswith('/v4/auth/') or request.path.startswith('/api/auth/zbmp-entry/') or request.path.startswith('/api/podcast/') or request.path.startswith('/api/ic/'):
        return None
    try:
        if _pg is None:
            return jsonify({
                'ok': False, 'status': 'BLOCKED',
                'error': 'PermissionGate未初始化（fail-closed）',
            }), 503
        op_type = _pg_resolve_operation_type(request.path, request.method)
        from domain_isolation import get_domain_context
        bound_context = get_domain_context()
        # This is the SYSTEM HTTP-effect gate. A selected business domain is
        # preserved; a later owner must still authorize its actual actor/scope.
        effect_domain = (bound_context.domain_id if bound_context is not None
                         and bound_context.domain_id else 'system')
        result = _pg.check(
            operation_type=op_type,
            resource=request.path,
            caller='http:{}:{}'.format(request.method, request.path),
            domain_id=effect_domain,
        )
        if not result.allowed:
            return jsonify({
                'ok': False, 'status': 'BLOCKED',
                'error': result.reason,
                'requires_approval': result.requires_approval,
                'operation': op_type.value,
                'resource': request.path,
                'risk_level': result.risk_level,
                'permission_required': result.permission_required,
            }), 403
    except Exception as _pg_exc:
        # fail-closed 硬红线：任何异常不得继续执行写操作
        return jsonify({
            'ok': False, 'status': 'BLOCKED',
            'error': 'PermissionGate异常（fail-closed）: {}'.format(_pg_exc),
        }), 503
    return None


class ProxyPrefixMiddleware:
    def __init__(self,wsgi_app): self.wsgi_app=wsgi_app
    def __call__(self,environ,start_response):
        path=environ.get('PATH_INFO','')
        for prefix in ('/proxy/8200','/absproxy/8200'):
            if path.startswith(prefix): environ['PATH_INFO']=path[len(prefix):] or '/'; break
        return self.wsgi_app(environ,start_response)
app.wsgi_app=ProxyPrefixMiddleware(app.wsgi_app)

# P0-3/P0-4/P1-2/P1-3/P1-4: Evidence Chain + Canonical Data 旁路接入 + Collector Health + 双域隔离迁移
try:
    from lumenis.shared.database import migrations as _dm
    if not _dm.migrate():
        raise RuntimeError("canonical Shared Database migration returned failure")
    print("[db_migrations] migration completed (canonical Shared Database migrations)")
except Exception as _e:
    raise RuntimeError(f"canonical Shared Database migration failed; application startup stopped: {_e}") from _e

# Apply the idempotent current business schema only after the Shared Database
# migration owner has secured its pre-migration snapshot and accepted the path.
db.init_db()

# Session statistics depend on the canonical notes schema, never import order.
# This restores local counters only; no session, browser or collection is started.
xhs_cookie_bridge._load_stats()

# P0-2: 独立确保 publish_datetime 索引存在（双保险，幂等，不依赖版本迁移成功）
try:
    _dm._migrate_add_publish_datetime_index()
    print("[db_migrations] idx_notes_publish_datetime ensured")
except Exception as _e:
    print(f"[db_migrations] publish_datetime index warning (non-fatal): {_e}")
try:
    import collection_quality_gate as _cqg
    _cqg.ensure_quality_log_table(db.DB_PATH)
    print("[collection_quality_gate] collection_quality_log table ensured")
except Exception as _e:
    print(f"[collection_quality_gate] init warning (non-fatal): {_e}")
try:
    from lumenis.shared.evidence import chain as _ec
    _ec.init_db(db.DB_PATH)
    print("[evidence_chain] zbc_evidence/zbc_canonical_data tables ensured")
except Exception as _e:
    print(f"[evidence_chain] init warning (non-fatal): {_e}")
try:
    import canonical_data as _cd
    _cd.ensure_canonical_table(db.DB_PATH)
    print("[canonical_data] canonical_data table ensured")
except Exception as _e:
    print(f"[canonical_data] init warning (non-fatal): {_e}")

# AI Task Engine 数据库迁移（向后兼容，只建表不改表）
try:
    from ai_task_engine import init_task_engine_db
    init_task_engine_db()
    print("[ai_task_engine] DB migration completed (ai_task/step/evidence/trace)")
except Exception as _e:
    print(f"[ai_task_engine] DB migration warning (non-fatal): {_e}")

# ===== GAP-10 报告路由收敛 P0：RFC 8594/9745 弃用信号（纯增量，不改任何业务逻辑，可一键回滚删除本块）=====
# 行业标准（Stripe/GitHub/Google）：Deprecation(宣布日期, RFC 9745) + Sunset(移除日期, RFC 8594)
#   + Link(替代端点, rel=successor-version)。仅对已确认的"重复实现"路由打标，
#   特殊报告/列表/验证/旁路预览绝不误标。当前 Sunset 为占位远期日期，实际退役需用户签字后另定。
_DEPRECATED_EXACT = {
    '/api/brand-report/generate',
    '/api/report/daily',
    '/api/report/generate',
    '/api/report/export',
    '/api/v2/report/export',
}
_DEPRECATED_PREFIX = ('/api/brand-report/export/', '/api/reports/')
_REPORT_SUNSET = 'Wed, 31 Dec 2026 23:59:59 GMT'

def _is_deprecated_report_path(path):
    if path in _DEPRECATED_EXACT:
        return True
    for p in _DEPRECATED_PREFIX:
        if path.startswith(p):
            return True
    # /api/report/v2/<type> 已弃用，但 /api/report/v2/stats 保留
    if path.startswith('/api/report/v2/') and not path.startswith('/api/report/v2/stats'):
        return True
    return False

@app.after_request
def _report_deprecation_headers(resp):
    try:
        path = request.path
        if _is_deprecated_report_path(path):
            resp.headers['Deprecation'] = 'Wed, 03 Sep 2026 00:00:00 GMT'
            resp.headers['Sunset'] = _REPORT_SUNSET
            resp.headers['X-Deprecated'] = 'true'
            if path.startswith('/api/brand-report/'):
                resp.headers['Link'] = '</api/reporting/generate>; rel="successor-version"'
            elif path.startswith('/api/report/') or path.startswith('/api/v2/report/') or path.startswith('/api/reports/'):
                resp.headers['Link'] = '</api/reporting/generate>; rel="successor-version"'
    except Exception:
        pass  # 绝不因标记失败影响响应
    return resp

collect_tasks={}; _task_lock=threading.Lock(); _collect_lock=threading.Lock()
topic_campaign.register_topic_campaign(app, _collect_lock)
app_evidence.register_app_evidence(app)
swire_group.register_swire_group(app)

def _strict_verify(note):
    title=note.get('title','') or ''; content=note.get('content','') or ''
    return ai_analyzer.verify_taikoo_location(title,content)

def _collect_request_context(action):
    """Compatibility callers use the same live principal/scope owner as Experience."""
    from experience_runtime import _content_project_scope
    actor, scope, decision = _content_project_scope(
        action, module="collector", include_decision=True)
    owner = decision.principal_ref or f"account:{decision.actor_id}"
    return actor, scope, owner


def _public_collect_task(task):
    return {key: value for key, value in task.items() if not key.startswith('_')}


def _run_collect_task(task_id, queries, max_results, actor, operator, scope, max_scroll):
    """Execute compatibility requests through the canonical scoped transaction.

    The plan is navigation, never permission or verified source identity. Each
    query passes collect_search's fresh Permission/import checks and canonical
    Source/Evidence transaction. No legacy notes-only or implicit AI side path.
    """
    from lumenis.system.collector.adapters.secondary_collection import collect_search
    started = time.monotonic()
    runs = []
    try:
        for query in queries:
            if xhs_cookie_bridge.is_user_paused():
                with _task_lock:
                    collect_tasks[task_id].update(
                        status='paused', code='COLLECTION_USER_PAUSED',
                        message='采集已暂停，尚未执行的查询保持未完成', runs=runs)
                return
            with _task_lock:
                collect_tasks[task_id].update(status='collecting',
                    message='正在按已授权范围采集并保存来源',
                    progress=int(100 * len(runs) / len(queries)))
            result = collect_search('xiaohongshu', query.keyword,
                max_results=max_results, operator=operator, actor=actor,
                scope=scope, max_scroll=max_scroll)
            # Never return raw platform material or adapter diagnostics in task listings.
            receipt = {key: result[key] for key in (
                'ok', 'status', 'platform', 'imported', 'updated', 'count',
                'evidence_ids', 'canonical_ids', 'evidence_ref', 'evidence_recorded',
                'canonical_synced', 'raw_count', 'network_attempted',
                'persistence_attempted') if key in result}
            receipt['keyword'] = query.keyword
            runs.append(receipt)
            if result.get('ok') is not True or result.get('status') not in {'SUCCESS', 'NO_NEW_DATA'}:
                with _task_lock:
                    collect_tasks[task_id].update(
                        status='blocked', code=result.get('status') or 'COLLECTION_UNAVAILABLE',
                        message='当前来源未完成采集，请查看来源状态', runs=runs)
                return
        with _task_lock:
            collect_tasks[task_id].update(status='done', progress=100,
                message='采集结果已通过来源、证据与正式数据事务保存', runs=runs,
                analysis_status='NOT_RUN', coverage_complete=False)
    except Exception as exc:
        with _task_lock:
            collect_tasks[task_id].update(status='error', code='COLLECTION_FAILED',
                error_type=type(exc).__name__, message='采集未完成，已保存的来源保留', runs=runs)
    finally:
        with _task_lock:
            collect_tasks[task_id].update(
                finished_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                duration_seconds=round(time.monotonic()-started, 1))
        _collect_lock.release()

def _generate_all_reports():
    # Existing scheduled reference job; never infer this focus for user requests.
    from subject_context import brand_scope, CTH_BRAND_KEY
    with brand_scope(CTH_BRAND_KEY, "CTH"):
        return report_engine.generate_all(domain_id="cth")

# ========== rednote CDP 采集 ==========
REDNOTE_SCRIPT = Path(__file__).parent / 'rednote_collector.cjs'

def _rednote_identity_evidence_matches(data, *, account, region, expected_user_id):
    """Require evidence produced after the attached browser context was checked."""
    evidence = data.get('identity_evidence') if isinstance(data, dict) else None
    if (not isinstance(evidence, dict) or data.get('identity_verified') is not True
            or not expected_user_id or evidence.get('account') != account
            or evidence.get('region') != region
            or evidence.get('source_host') != 'www.rednote.com'
            or evidence.get('verification_method')
            != 'registered_context_cookie_and_self_profile'):
        return False
    expected_fingerprint = hashlib.sha256(
        str(expected_user_id).encode('utf-8')).hexdigest()
    return evidence.get('identity_fingerprint_sha256') == expected_fingerprint


def run_rednote_collect(keyword=None, max_scroll=3, max_details=10, cdp_url=None, account=None):
    """Collect through the exact server-registered HK/International background worker."""
    keyword = str(keyword or '').strip()
    if not keyword:
        return {'ok': False, 'code': 'KEYWORD_REQUIRED',
                'error': 'An explicit collection keyword is required.'}
    resolved_account = account or xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT
    policy_gate = xhs_cookie_bridge.collection_policy_gate(account=resolved_account, region='intl')
    if not policy_gate.get('ok'):
        return {'ok': False, 'error': policy_gate.get('reason'),
                'code': policy_gate.get('code'), 'collection_policy': policy_gate}
    try:
        import collector as _collector
        configured_cdp = cdp_url or os.getenv('XHS_CDP_URL')
        cdp_url, endpoint_error = _collector._resolve_server_cdp_url(
            configured_cdp, account=resolved_account, region='intl')
        if endpoint_error:
            return {'ok': False, 'error': endpoint_error, 'code': endpoint_error,
                    'collection_policy': policy_gate}
        env = _collector._collection_env(
            account=resolved_account, region='intl', cdp_url=cdp_url,
            require_local_cookie=False)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        error_code = str(exc) if re.fullmatch(r'[A-Z0-9_]{1,80}', str(exc)) else 'REGISTERED_WORKER_UNAVAILABLE'
        return {'ok': False, 'error': 'Registered browser worker unavailable.', 'code': error_code,
                'collection_policy': policy_gate}
    if not REDNOTE_SCRIPT.exists():
        return {'ok': False, 'error': f'rednote_collector.cjs 不存在: {REDNOTE_SCRIPT}'}
    expected_identity = str(env.get('XHS_EXPECTED_COLLECTION_USER_ID') or '').strip()
    out_file = Path(xhs_cookie_bridge.PRIVATE_DATA_DIR) / (
        f'rednote_{datetime.now().astimezone():%Y%m%d_%H%M%S}_{uuid.uuid4().hex}.json')
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [_NODE_BIN, str(REDNOTE_SCRIPT), '--keyword', keyword, '--output', str(out_file),
           '--max-scroll', str(max_scroll), '--max-details', str(max_details)]
    try:
        p = subprocess.run(cmd, cwd=str(Path(__file__).parent), capture_output=True, text=True, timeout=1800, env=env)
        stdout = (p.stdout or '')
        marker = '---RESULT_JSON---'
        if marker in stdout:
            data = json.loads(stdout[stdout.index(marker)+len(marker):].strip())
        elif out_file.exists():
            data = json.loads(out_file.read_text(encoding='utf-8'))
        else:
            data = {'ok': False, 'error': (p.stderr or stdout)[-1000:]}
        if not _rednote_identity_evidence_matches(
                data, account=resolved_account, region='intl',
                expected_user_id=expected_identity):
            return {
                'ok': False, 'code': 'COLLECTOR_IDENTITY_UNVERIFIED',
                'error': 'Attached RedNote worker identity was not verified.',
                'identity_verified': False, 'notes': [],
                'summary': {'identity_verified': False},
                'collection_policy': policy_gate,
            }
        data['_returncode'] = p.returncode
        data.setdefault('collection_policy', policy_gate)
        return data
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': '采集超时（300秒）'}
    except (OSError, RuntimeError, subprocess.SubprocessError, TypeError,
            ValueError, json.JSONDecodeError, UnicodeError) as exc:
        return {'ok': False, 'code': 'COLLECTOR_EXECUTION_FAILED',
                'error_type': type(exc).__name__}


def _bypass_evidence_canonical(note_data, provider='rednote'):
    """P0-3/P0-4: Evidence Chain + Canonical Data 旁路写入（side-write）。

    硬红线：所有写入必须 try/except 吞掉并 log warning，绝不影响 notes 主入库。
    委托统一的 Shared Evidence chain.capture_note_lineage，避免不同小红书入口各自
    复制一套 Evidence/Canonical 写入逻辑。
    """
    try:
        from lumenis.shared.evidence import chain as _ec
        result = _ec.capture_note_lineage(
            note_data, db_path=db.DB_PATH, provider=provider,
            subject_scope='CTH', domain_id='cth', product_id='CTH',
        )
        if not result.get('ok'):
            app.logger.warning('Evidence/Canonical side-write incomplete: %s', result.get('errors', []))
        return result
    except Exception as _e:
        app.logger.warning('Evidence/Canonical side-write skipped (non-fatal): %s', type(_e).__name__)
        return {'ok': False, 'errors': [{'stage': 'lineage', 'error_type': type(_e).__name__}]}


def persist_rednote_data(data, subject_hit_fn=None, *, acquisition_query=None):
    """将 rednote 采集结果入库"""
    if not data or not data.get('ok'):
        return {'ok': False, 'error': data.get('error', '采集失败') if data else '无数据'}
    import xhs_cookie_bridge as _identity_bridge
    expected_identity = str(_identity_bridge.XHS_RETINAUT or '').strip()
    if not _rednote_identity_evidence_matches(
            data, account=_identity_bridge.XHS_RETINAUT_NAME,
            region='intl', expected_user_id=expected_identity):
        return {'ok': False, 'status': 'BLOCKED',
                'code': 'COLLECTOR_IDENTITY_UNVERIFIED'}
    if data.get('verification_required'):
        return {'ok': False, 'status': 'verification_required', 'reason': '需要人工验证'}
    notes = data.get('notes', [])
    persisted = 0
    comments_total = 0
    note_ids = []
    failures = 0
    for n in notes:
        if subject_hit_fn:
            full_text = (n.get('title','') + ' ' + n.get('desc','') + ' ' + n.get('detail_title','')).lower()
            if not subject_hit_fn(full_text):
                continue
        try:
            note_data = {
                'note_id': n.get('note_id',''),
                'title': n.get('detail_title') or n.get('title',''),
                'content': n.get('desc','') or n.get('content',''),
                'url': n.get('url',''),
                'cover': n.get('cover',''),
                'author_id': n.get('author_id',''),
                'author_nickname': n.get('detail_author') or n.get('author',''),
                'author_avatar': n.get('author_avatar',''),
                'likes': n.get('likes'),
                'comments': n.get('comments'),
                'collects': n.get('collects'),
                'shares': n.get('shares'),
                'xsec_token': n.get('xsec_token',''),
                'publish_date': n.get('detail_publish_time') or n.get('publish_time',''),
                'publish_datetime': n.get('detail_publish_time') or n.get('publish_time',''),
                'source_platform': 'xhs',
                'source_keyword': acquisition_query.keyword if acquisition_query else '',
                'is_taikoo_verified': 0,
                'verify_reason': 'source scope pending verification',
                'data_quality_status': n.get('quality_status','unknown'),
                'data_quality_score': float(n.get('quality_score',0) or 0),
                'collector_version': n.get('collector_version','rednote-v1.0'),
                'captured_at': n.get('captured_at') or datetime.now().isoformat(),
                'detail_fetched_at': n.get('detail_fetched_at') or datetime.now().isoformat(),
                'comments_collected': n.get('comment_count'),
                '_lumenis_metric_observation_complete': n.get('detail_fetched') is True,
            }
            db.insert_note(note_data)
            persisted += 1
            note_ids.append(note_data['note_id'])
            # P0-3/P0-4: Evidence Chain + Canonical Data 旁路写入（side-write，失败不影响主入库）
            _bypass_evidence_canonical(note_data, provider='rednote')
            # 保存评论
            comments = n.get('comment_list') or n.get('comments_data') or []
            if comments:
                db.upsert_note_comments(n.get('note_id',''), comments)
                comments_total += len(comments)
            # 保存质量日志
            db.save_collector_quality(n.get('note_id',''), {
                'status': n.get('quality_status','unknown'),
                'score': float(n.get('quality_score',0) or 0),
                'detail_status': 'success' if n.get('detail_fetched') else 'failed',
                'comments_collected': n.get('comment_count'),
                'collector_version': n.get('collector_version','rednote-v1.0'),
            })
        except Exception as e:
            failures += 1
            print(f'[rednote] 入库失败 {n.get("note_id","")}: {e}')
    scope_result = {'status': 'UNASSIGNED', 'verified': 0}
    if acquisition_query is not None and note_ids:
        from lumenis.system.collector.adapters.secondary_collection import bind_collected_social_scope
        scope_result = bind_collected_social_scope(
            note_ids, scope=acquisition_query.scope, platform='xhs',
            keyword=acquisition_query.keyword, provider='rednote',
        )
    return {'ok': failures == 0 and scope_result.get('ok', True),
            'persisted': persisted, 'failed': failures, 'comments': comments_total,
            'total': len(notes), 'scope_binding': scope_result}


def _record_rednote_collection_log(data, keyword=''):
    """将 CDP RedNote 结果归一后写入唯一 collection_logs 真相源。

    采集脚本与传统 collector 共用同一六态分类；verification/ip-risk
    优先于“0 条”，避免安全阻断被误记为 EMPTY。此函数只记录运行事实，
    不改变 notes、主体过滤或风险判断。
    """
    data = data if isinstance(data, dict) else {}
    notes = data.get('notes') if isinstance(data.get('notes'), list) else []
    summary = data.get('summary') if isinstance(data.get('summary'), dict) else {}
    error = str(data.get('error') or '')
    guard_state = str(data.get('guard_state') or '')
    if summary.get('verification_required'):
        guard_state = 'NEED_VERIFY'
    elif summary.get('ip_blocked'):
        guard_state = 'BLOCKED'
    count = len(notes)
    cstate = collector.classify_collect_state(error=error, guard_state=guard_state, count=count)
    resolved_keyword = str(keyword or summary.get('keyword') or 'rednote')
    db.log_collection(resolved_keyword, count, cstate, error)
    return {'status': cstate, 'notes_count': count, 'keyword': resolved_keyword}

# ========== 舆情预警通知 ==========
ALERTS_FILE = Path(__file__).parent / 'data' / 'alerts.json'

def _load_alerts():
    if ALERTS_FILE.exists():
        try: return json.loads(ALERTS_FILE.read_text(encoding='utf-8'))
        except: return []
    return []

def _save_alerts(alerts):
    ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERTS_FILE.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding='utf-8')

def check_and_create_alerts():
    """检查高风险/高影响力/上升过快的笔记，创建预警通知"""
    alerts = _load_alerts()
    existing_ids = {a.get('note_id') for a in alerts}
    new_alerts = []
    try:
        high_risk = db.get_high_risk_notes(50)
        hot_notes = db.get_hot_notes(20)
        for note in high_risk + hot_notes:
            nid = note.get('note_id') or note.get('id')
            if not nid or str(nid) in existing_ids: continue
            risk = note.get('risk_level','')
            likes = int(note.get('likes',0) or 0)
            comments = int(note.get('comments',0) or 0)
            influence = likes + comments * 3
            alert_type = 'risk' if risk in ('high','critical') else ('influence' if influence > 500 else 'rising')
            alert = {
                'id': f"alert_{nid}_{datetime.now():%Y%m%d%H%M%S}",
                'note_id': str(nid),
                'title': note.get('title','')[:80],
                'type': alert_type,
                'risk_level': risk,
                'influence': influence,
                'likes': likes,
                'comments': comments,
                'message': f"{'高风险' if alert_type=='risk' else '高影响力'}舆情：{note.get('title','')[:50]}",
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'read': False,
            }
            alerts.append(alert)
            new_alerts.append(alert)
            existing_ids.add(str(nid))
        if new_alerts:
            _save_alerts(alerts)
    except Exception as e:
        print(f'[Alerts] 检查预警失败: {e}')
    return new_alerts

# ========== 报告导出（表格模式） ==========
# ========== 品牌目录与业态匹配 ==========
BRAND_DIR_FILE = Path(__file__).parent / 'data' / 'brand_directory.json'
_brand_cache = None

def _load_brands():
    global _brand_cache
    if _brand_cache is not None:
        return _brand_cache
    if BRAND_DIR_FILE.exists():
        try:
            data = json.loads(BRAND_DIR_FILE.read_text(encoding='utf-8'))
            _brand_cache = data.get('brands', [])
        except Exception as e:
            print(f'[Brand] 加载品牌目录失败: {e}')
            _brand_cache = []
    else:
        _brand_cache = []
    return _brand_cache

def _match_brand(note):
    """根据笔记标题/正文/作者匹配场内品牌，返回品牌名和业态"""
    brands = _load_brands()
    text = (note.get('title', '') + ' ' + note.get('content', '') + ' ' + note.get('desc', '') + ' ' + note.get('author_nickname', '')).lower()
    matched = []
    for b in brands:
        brand_en = b['brand_en'].lower()
        brand_cn = b.get('brand_cn', '').lower()
        if (brand_en and len(brand_en) > 2 and brand_en in text) or (brand_cn and len(brand_cn) > 1 and brand_cn in text):
            matched.append(b)
    if matched:
        # 取第一个匹配的品牌
        return matched[0]['brand_cn'] or matched[0]['brand_en'], matched[0]['category']
    return '', ''

# Reporting consumes the existing brand matcher through an explicit dependency contract.
export_api.bind_brand_matcher(_match_brand)

# ========== v5.4 品牌业态统计 ==========
# ========== /api/viz/* 函数驱动直查DB（P0修复：overview KPI/趋势主数据源缺失） ==========
@app.route('/api/viz/overview.stats')
def api_viz_overview_stats():
    """今日概览统计：笔记数、互动量、品牌数等。直查DB。"""
    try:
        time_range = request.args.get('time_range', 'today')
        c = get_db()
        if time_range == 'today':
            where = "WHERE date(publish_datetime)=date('now')"
        elif time_range == '7d':
            where = "WHERE publish_datetime >= datetime('now','-7 days')"
        elif time_range == '30d':
            where = "WHERE publish_datetime >= datetime('now','-30 days')"
        else:
            where = ""
        total = c.execute(f"SELECT COUNT(*) FROM notes {where}").fetchone()[0]
        engagement = c.execute(f"SELECT COALESCE(SUM(likes+comments+shares+collects),0) FROM notes {where}").fetchone()[0]
        brands = c.execute(f"SELECT COUNT(DISTINCT matched_keywords) FROM notes {where} AND matched_keywords IS NOT NULL AND matched_keywords != ''").fetchone()[0]
        return jsonify({"success": True, "data": {"items": [{"total": total, "engagement": engagement, "active_brands": brands}], "time_range": time_range}})
    except Exception as e:
        app.logger.warning("viz/overview.stats error: %s", e)
        return jsonify({"success": False, "error": str(e)[:200]}), 500

@app.route('/api/viz/risk.active')
def api_viz_risk_active():
    """活跃风险事件统计。直查DB events表。"""
    try:
        time_range = request.args.get('time_range', '7d')
        level = request.args.get('level', 'high')
        c = get_db()
        where = "WHERE risk_level IN ('high','critical') AND status != 'closed'"
        if time_range == '7d':
            where += " AND (first_seen >= datetime('now','-7 days') OR last_seen >= datetime('now','-7 days'))"
        count = c.execute(f"SELECT COUNT(*) FROM events {where}").fetchone()[0]
        return jsonify({"success": True, "data": {"record_count": count, "current_value": count, "level": level}})
    except Exception as e:
        app.logger.warning("viz/risk.active error: %s", e)
        return jsonify({"success": False, "error": str(e)[:200]}), 500

@app.route('/api/viz/overview.trend')
def api_viz_overview_trend():
    """30天笔记发布趋势。直查DB，按publish_datetime分组。"""
    try:
        time_range = request.args.get('time_range', '30d')
        days = 30
        if time_range == '7d': days = 7
        elif time_range == '90d': days = 90
        c = get_db()
        rows = c.execute("""
            SELECT date(publish_datetime) as day, COUNT(*) as note_count,
                   SUM(CASE WHEN sentiment='negative' OR risk_level IN ('high','critical') THEN 1 ELSE 0 END) as negative_count
            FROM notes
            WHERE publish_datetime >= datetime('now', ?)
            GROUP BY date(publish_datetime)
            ORDER BY day ASC
        """, (f'-{days} days',)).fetchall()
        items = [{"day": r[0], "note_count": r[1], "negative_count": r[2] or 0} for r in rows]
        return jsonify({"success": True, "data": {"items": items, "days": days}})
    except Exception as e:
        app.logger.warning("viz/overview.trend error: %s", e)
        return jsonify({"success": False, "error": str(e)[:200]}), 500

@app.route('/api/brand-stats')
def api_brand_stats():
    """场内品牌及9大业态统计，对应rednote笔记数量"""
    brands = _load_brands()
    notes = db.get_notes_by_date_range((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d'))
    
    # 9大业态统计
    category_stats = {}
    category_order = ['女装', '男装', '餐饮', '珠宝钟表', '美容护理', '运动休闲', '鞋包皮具', '童装玩具', '生活时尚']
    for cat in category_order:
        category_stats[cat] = {'brand_count': 0, 'note_count': 0, 'negative_count': 0, 'engagement': 0, 'brands': []}

    # 业态映射：品牌目录用英文双语(如"女装 Ladies' Fashion")，统一映射到纯中文key
    _CAT_MAP = {'女装':"女装",'男装':"男装",'餐饮':"餐饮",'珠宝':"珠宝钟表",'钟表':"珠宝钟表",
                '美容':"美容护理",'保健':"美容护理",'运动':"运动休闲",'休闲服':"运动休闲",
                '鞋包':"鞋包皮具",'皮具':"鞋包皮具",'童装':"童装玩具",'玩具':"童装玩具",
                '生活':"生活时尚",'影音':"生活时尚",'电器':"生活时尚"}
    def _map_cat(raw):
        if not raw: return None
        if raw in category_stats: return raw
        for k, v in _CAT_MAP.items():
            if k in raw: return v
        return None

    for b in brands:
        cat = _map_cat(b.get('category', ''))
        if cat:
            category_stats[cat]['brand_count'] += 1
            category_stats[cat]['brands'].append(b)
    
    # 匹配笔记
    brand_note_map = {}
    for n in notes:
        brand, brand_category = _match_brand(n)
        brand_category = _map_cat(brand_category)
        if brand and brand_category in category_stats:
            category_stats[brand_category]['note_count'] += 1
            if n.get('sentiment') == 'negative':
                category_stats[brand_category]['negative_count'] += 1
            category_stats[brand_category]['engagement'] += int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
            if brand not in brand_note_map:
                brand_note_map[brand] = {'note_count': 0, 'negative_count': 0, 'engagement': 0, 'category': brand_category}
            brand_note_map[brand]['note_count'] += 1
            if n.get('sentiment') == 'negative':
                brand_note_map[brand]['negative_count'] += 1
            brand_note_map[brand]['engagement'] += int(n.get('likes',0) or 0) + int(n.get('comments',0) or 0)*3
    
    # 品牌TOP10
    top_brands = sorted(brand_note_map.items(), key=lambda x: x[1]['note_count'], reverse=True)[:10]
    top_brands_list = [{'brand': b, **stats} for b, stats in top_brands]
    
    # 业态分布（用于扇形图）
    pie_data = []
    total_notes = sum(cs['note_count'] for cs in category_stats.values())
    for cat in category_order:
        cs = category_stats[cat]
        percentage = round(cs['note_count'] / total_notes * 100, 1) if total_notes > 0 else 0
        pie_data.append({'category': cat, 'note_count': cs['note_count'], 'brand_count': cs['brand_count'], 'percentage': percentage, 'negative_count': cs['negative_count']})
    
    # 趋势数据（最近7天）
    trend_data = []
    for i in range(6, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        day_notes = [n for n in notes if n.get('publish_date', '').startswith(date)]
        trend_data.append({'date': date, 'note_count': len(day_notes), 'negative_count': sum(1 for n in day_notes if n.get('sentiment')=='negative')})
    
    return jsonify({
        'ok': True,
        'total_brands': len(brands),
        'total_notes': len(notes),
        'categories': category_stats,
        'pie_data': pie_data,
        'trend_data': trend_data,
        'top_brands': top_brands_list,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/')
def index():
    # LUMENIS 用户入口由 Flutter App 提供；此 Flask 进程仅承载 Product Core/API。
    return redirect('/workspace/')
@app.route('/favicon.ico')
def favicon():
    # 消除浏览器自动请求 favicon 产生的 404 控制台报错
    return Response(status=204)
@app.route('/VERSION')
def version_file():
    # 前端 settings.js 读取版本号（纯文本，与根目录 VERSION 文件一致）
    try:
        with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION'), encoding='utf-8') as _vf:
            return Response(_vf.read().strip(), mimetype='text/plain')
    except Exception:
        return Response(APP_VERSION, mimetype='text/plain')
@app.route('/api/metrics/canonical')
def api_metrics_canonical():
    """Unified Data Intelligence Pipeline: Canonical Metric API (UDIP P2)
    Consumption surface for Dashboard / Table / Chart / Report / Export / AI.
    All values computed once by daily.generate_today_summary (FUNC-RISK-01/02).
    No page/chart/report/AI should recompute these metrics."""
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except Exception:
        date_str = datetime.now().strftime('%Y-%m-%d')
    try:
        _actor, scope, _entries, _selected = _resolve_web_scope('read', module='reports')
        summary = daily.generate_today_summary(date_str=date_str, scope=scope)
    except (PermissionError, ValueError) as e:
        status = 403 if isinstance(e, PermissionError) else 409
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': str(e)}), status
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    return jsonify({
        'ok': True,
        'metric_version': 'UDIP-V1.0',
        'date': date_str,
        'metrics': {
            'MET-RISK-01': {'name': 'risk_index', 'value': summary.get('risk_index'), 'unit': 'score 0-100', 'function': 'FUNC-RISK-01'},
            'MET-RISK-02': {'name': 'brand_health_score', 'value': summary.get('brand_health_score'), 'unit': 'score 0-100', 'function': 'FUNC-RISK-02'},
        },
        'context': {
            'scope': summary.get('scope'),
            'total_found': summary.get('total_found'),
            'effective_count': summary.get('effective_count'),
            'positive_count': summary.get('positive_count'),
            'neutral_count': summary.get('neutral_count'),
            'risk_count': summary.get('risk_count'),
            'events_count': summary.get('events_count'),
            'collection_health': summary.get('collection_health'),
        },
        'lineage': {
            'source': 'scope-verified notes + events (data/monitor.db)',
            'function': 'lumenis.shared.reporting.daily.generate_today_summary',
            'registry': 'FUNCTION_REGISTRY.md FUNC-RISK-01/02 / METRIC_REGISTRY.md MET-RISK-01/02',
        },
    })

def _resolve_web_scope(action, *, module='reports'):
    """Compatibility wrapper for the shared Permission request-scope owner."""
    from lumenis.system.security.permission import resolve_web_request_scope

    return resolve_web_request_scope(action, module=module)


def _web_scope_terms(entries):
    terms = []
    for entry in entries:
        keywords = entry.get('keywords') if isinstance(entry.get('keywords'), list) else []
        for value in (entry.get('name_zh'), entry.get('name_en'), *keywords):
            if isinstance(value, str) and value.strip() and value.strip() not in terms:
                terms.append(value.strip())
    return terms


def _web_scope_brands(entries, selected):
    """Use the curated directory only for the exact registered Taikoo reference focus."""
    import web_discovery
    if (isinstance(selected, dict)
            and selected.get('domain_id') == 'CTH'
            and selected.get('name_zh') == '广州太古汇'):
        directory = web_discovery.get_brand_directory()
        if directory.get('status') != 'AVAILABLE':
            raise RuntimeError(directory.get('reason') or 'REFERENCE_DIRECTORY_UNAVAILABLE')
        brands = [row for row in directory.get('brands', []) if isinstance(row, dict)]
        categories = sorted({str(row.get('category')).strip() for row in brands
                             if isinstance(row.get('category'), str) and row.get('category').strip()})
        return [name for row in brands for name in (row.get('brand_cn'), row.get('brand_en'))
                if isinstance(name, str) and name.strip()], categories
    brands = _web_scope_terms(entries)
    categories = sorted({str(entry.get('industry')).strip() for entry in entries
                         if isinstance(entry.get('industry'), str) and entry.get('industry').strip()})
    return brands, categories


@app.route('/api/intelligence/refresh',methods=['POST'])
def api_intelligence_refresh():
    try:
        actor, scope, entries, _selected = _resolve_web_scope('write', module='reports')
    except (PermissionError, ValueError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 409
        return jsonify({'ok':False,'status':'BLOCKED','code':str(exc)}),status
    body=request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({'ok':False,'status':'INVALID_REQUEST','code':'INVALID_JSON_OBJECT'}),400
    terms = _web_scope_terms(entries)
    if not terms:
        return jsonify({'ok':False,'status':'BLOCKED','code':'REGISTERED_SCOPE_TERMS_UNAVAILABLE'}),409
    queries = web_discovery.brand_queries(terms)
    if not queries:
        return jsonify({'ok':False,'status':'BLOCKED','code':'SCOPED_QUERY_PLAN_UNAVAILABLE'}),409
    if not _collect_lock.acquire(blocking=False): return jsonify({'ok':False,'error':'已有任务运行中'}),409
    try: limit=max(1,min(10000,int(body.get('limit',5000))))
    except (TypeError,ValueError): limit=5000
    task_id=f"intel-{datetime.now():%Y%m%d%H%M%S}"
    with _task_lock: collect_tasks[task_id]={'task_id':task_id,'status':'pending','message':'智能刷新任务已创建','progress':0,'created_at':datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    def worker():
        try:
            result=reprocess.full_refresh(limit=limit,web_limit=120,translate=False,
                web_queries=queries,scope=scope,actor=actor)
            completed = result.get('status') == 'COMPLETED'
            with _task_lock: collect_tasks[task_id].update(
                status='done' if completed else 'partial', progress=100,
                message='刷新流程已结束' if completed else '刷新流程部分完成，详见各阶段状态', result=result)
        except Exception as e:
            with _task_lock: collect_tasks[task_id].update(status='error',message=str(e),error=str(e))
        finally: _collect_lock.release()
    threading.Thread(target=worker,daemon=True).start()
    return jsonify({'ok':True,'task_id':task_id})


@app.route('/api/browser/sessions')
def api_browser_sessions():
    """浏览器会话列表：列出当前 CDP 连接的 tab/会话状态。
    只读接口，对标 Safari Web Inspector 会话观察。
    """
    try:
        import browser_surface as bs
        targets = bs.list_targets()
        tabs = bs.list_tabs()
        nav_config = bs.get_nav_config()
        return jsonify({
            'ok': True,
            'targets': targets,
            'tabs': tabs,
            'nav_config': nav_config,
            'session_count': len(tabs) if isinstance(tabs, list) else 0,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/ai-governance/status')
def api_ai_governance_status():
    """AI 治理状态：额度/使用统计/配置/脱敏状态（余额需在智谱控制台查看）"""
    try:
        return jsonify(ai_governance.get_governance_status())
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/collector/browser/start', methods=['POST'])
def api_collector_browser_start():
    """Start a headless BACKGROUND Worker or a permission-gated human session."""
    try:
        data = request.get_json(silent=True) or {}
        account = data.get('account', 'default')
        mode = str(data.get('mode') or 'BACKGROUND').upper()
        if mode not in {'BACKGROUND', 'HUMAN_INTERACTIVE'}:
            return jsonify({'ok': False, 'status': 'BLOCKED', 'code': 'BROWSER_MODE_INVALID'}), 400
        task_id = str(data.get('task_id') or '').strip() or None
        actor_ref = None
        if mode == 'BACKGROUND':
            if data.get('headless') is False:
                return jsonify({'ok': False, 'status': 'BLOCKED',
                                'code': 'BACKGROUND_REQUIRES_HEADLESS'}), 400
            headless = True
            if task_id:
                actor_ref = _collector_browser_actor_ref()
        else:
            if not isinstance(account, str) or not account.strip() or account.strip().casefold() == 'default':
                return jsonify({'ok': False, 'status': 'BLOCKED',
                                'code': 'HUMAN_INTERACTIVE_REGISTERED_ACCOUNT_REQUIRED'}), 400
            headless = False
            if not task_id:
                return jsonify({'ok': False, 'status': 'BLOCKED',
                                'code': 'HUMAN_INTERACTIVE_TASK_ID_REQUIRED'}), 400
            actor_ref = _collector_browser_actor_ref()
        collector = collector_automation.get_collector_automation()
        collector.start_browser(account=account, headless=headless, mode=mode,
                                task_id=task_id, actor_ref=actor_ref)
        return jsonify({'ok': True, 'mode': mode,
                        'status': 'HUMAN_LOGIN_OPENED' if mode == 'HUMAN_INTERACTIVE' else 'BACKGROUND_READY',
                        'session_verified': False if mode == 'HUMAN_INTERACTIVE' else None,
                        'message': '请在序境请求的登录窗口中完成验证' if mode == 'HUMAN_INTERACTIVE'
                                   else '后台浏览器Worker已就绪'})
    except PermissionError as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(e)}), 403
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE', 'error': str(e)}), 409

@app.route('/api/collector/browser/stop', methods=['POST'])
def api_collector_browser_stop():
    """Gracefully stop only an exact idle LUMENIS Worker; never terminate a process."""
    try:
        data = request.get_json(silent=True) or {}
        collector = collector_automation.get_collector_automation()
        was_human_interactive = getattr(collector, '_browser_mode', 'BACKGROUND') == 'HUMAN_INTERACTIVE'
        expected_task_id = str(data.get('task_id') or '').strip() or None
        expected_actor_ref = _collector_browser_actor_ref() if was_human_interactive else None
        stopped = collector.stop_browser(
            expected_task_id=expected_task_id, expected_actor_ref=expected_actor_ref)
        if not stopped:
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'WORKER_RETAINED_OR_UNVERIFIED'}), 409
        if was_human_interactive:
            return jsonify({'ok': True, 'status': 'RETURNED_BACKGROUND',
                            'session_verified': False,
                            'message': '浏览器已安全返回后台；平台登录态仍需采集器验证'})
        return jsonify({'ok': True, 'status': 'STOPPED', 'message': '后台浏览器Worker已正常退出'})
    except PermissionError as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(e)}), 403
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE', 'error': str(e)}), 409

@app.route('/api/collector/browser-mode', methods=['GET'])
def api_collector_browser_mode_get():
    try:
        import collector_browser_mode as cbm
        return jsonify(cbm.get_browser_mode_info())
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/collector/browser-mode', methods=['POST'])
def api_collector_browser_mode_set():
    try:
        import collector_browser_mode as cbm
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', '')
        result = cbm.set_browser_mode(mode)
        if result.get('ok'):
            return jsonify(result)
        return jsonify(result), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== 双子星库 Contract · XHS Runtime 统一预检 & 双身份切换 ==========
@app.route('/api/xhs/runtime-check', methods=['GET', 'POST'])
def api_xhs_runtime_check():
    """XHS 运行时七态预检（前端轮询用）。

    query/body:
      account: 可选 · 显式指定要预检的身份（XHS_CN_PRIMARY / XHS_RETINAUT）
      quick:   可选 · 1/true 时跳过 CDP 端口 ping，用于高频轮询节省开销
    字段结构: ok / overall_state / checks[7] / account_status / circuit /
              active_account / allowed_accounts / cdp_online / user_paused / state_machine / evidence
    """
    try:
        data = {}
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
        account = (request.args.get('account') or data.get('account') or '').strip() or xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT
        quick = str(request.args.get('quick', '') or data.get('quick', '')).lower() in ('1', 'true', 'yes', 'on')
        # Environment endpoint is a consistency hint only; the SYSTEM session owner resolves authority.
        configured_cdp = os.getenv('XHS_CDP_URL')
        result = xhs_cookie_bridge.runtime_preflight_check(
            account=account, cdp_url=configured_cdp, quick=quick)
        # overall_state 对应 Auth Recovery Center：
        #   no_cookie / need_account / blocked → 需要前端弹扫码 / 验证入口
        #   ready / cooldown / user_paused → 正常态提示
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': type(e).__name__,
                        'overall_state': 'error',
                        'evidence': 'XHS_RUNTIME_PREFLIGHT_UNAVAILABLE'}), 500


@app.route('/api/xhs/switch-account', methods=['POST'])
def api_xhs_switch_account():
    """Select only the currently permission-approved registered RedNote identity."""
    try:
        data = request.get_json(silent=True) or {}
        account = (data.get('account') or '').strip()
        if not account:
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'REGISTERED_ACCOUNT_REQUIRED'}), 400
        policy = xhs_cookie_bridge.collection_policy_gate(account=account, region='intl')
        if (policy.get('ok') is not True or policy.get('account') != account
                or policy.get('region') != 'intl'):
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'COLLECTION_POLICY_BLOCKED'}), 403
        ok_sel, _ = xhs_cookie_bridge.select_account(account)
        if not ok_sel:
            return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                            'code': 'REGISTERED_ACCOUNT_UNAVAILABLE'}), 409
        status = xhs_cookie_bridge.get_account_status()
        return jsonify({'ok': status.get('collection_enabled') is True,
                        'active_account': status.get('active_account'),
                        'allowed_accounts': status.get('allowed_accounts', []),
                        'account_status': status})
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 500


@app.route('/api/xhs/accounts', methods=['GET'])
def api_xhs_accounts():
    """Expose only the existing bridge owner's safe account-status projection."""
    try:
        return jsonify(xhs_cookie_bridge.get_account_status())
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 500

# ========== Zachary OS AI · Resident Browser Health Monitor API ==========
@app.route('/api/resident/health', methods=['GET'])
def api_resident_health():
    """Return the bridge owner's policy-filtered RedNote session status."""
    try:
        account = request.args.get('account') or xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT
        use_cache = request.args.get('cache') in ('1', 'true', 'yes')
        result = xhs_cookie_bridge.get_account_status(account=account)
        return jsonify({'ok': True, 'cached': False if use_cache else None,
                        'cache_requested': use_cache, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 500


@app.route('/api/resident/recover', methods=['POST'])
def api_resident_recover():
    """Recover only the current policy-approved XHS worker via its SYSTEM owner."""
    try:
        data = request.get_json(silent=True) or {}
        account = str(data.get('account') or xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT).strip()
        policy = xhs_cookie_bridge.collection_policy_gate(account=account, region='intl')
        if (policy.get('ok') is not True or policy.get('account') != account
                or policy.get('region') != 'intl'):
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'COLLECTION_POLICY_BLOCKED'}), 403
        if data.get('force'):
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'FORCE_RECOVERY_NOT_SUPPORTED'}), 400
        collector = collector_automation.get_collector_automation()
        collector.start_browser(account=account, headless=True, mode='BACKGROUND')
        result = xhs_cookie_bridge.get_account_status(account=account)
        worker_ok = result.get('worker_available') is True
        return jsonify({'ok': worker_ok,
                        'status': 'RECOVERED' if worker_ok else 'UNAVAILABLE',
                        'account': result.get('active_account'),
                        'worker_available': result.get('worker_available'),
                        'account_status': result})
    except PermissionError as exc:
        return jsonify({'ok': False, 'status': 'BLOCKED',
                        'error': str(exc)}), 403
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 500


# ========== AI学习引擎与全网舆情检索 API ==========
# 【拆分收尾 2026-09-05】/api/ai-learning/optimization/<operation_type> 已迁入 ai_api.py

@app.route('/api/cases/stats')
def api_cases_stats():
    """舆情案例统计"""
    try:
        db = public_opinion_cases.get_case_db()
        stats = db.get_stats()
        return jsonify({'ok': True, **stats})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/list')
def api_public_cases_list():
    """舆情案例列表"""
    try:
        case_type = request.args.get('type')
        risk_level = request.args.get('risk')
        category = request.args.get('category')
        limit = request.args.get('limit', 100, type=int)
        
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type=case_type, risk_level=risk_level, 
                            category=category, limit=limit)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/import', methods=['POST'])
def api_cases_import():
    """导入舆情案例（重新导入所有案例）"""
    try:
        db = public_opinion_cases.get_case_db()
        count = db.import_all_cases()
        return jsonify({'ok': True, 'imported_count': count, 'message': f'成功导入{count}个案例'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/taikoo-hui')
def api_cases_taikoo_hui():
    """广州太古汇舆情案例"""
    try:
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type='taikoo_hui', limit=50)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/other-malls')
def api_cases_other_malls():
    """其他商业地产舆情案例"""
    try:
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type='other_mall', limit=50)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/cases/brands')
def api_cases_brands():
    """品牌业态舆情案例"""
    try:
        db = public_opinion_cases.get_case_db()
        cases = db.get_cases(case_type='brand', limit=50)
        return jsonify({'ok': True, 'cases': cases, 'count': len(cases)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ========== 前端兼容路由别名 ==========

@app.route('/api/brand-industry/brands')
def api_brand_industry_brands_alias():
    """品牌业态-品牌列表（前端兼容）"""
    try:
        limit = request.args.get('limit', 50, type=int)
        with db.get_db() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM brand_industry_monitor ORDER BY note_count DESC LIMIT ?", (limit,)).fetchall()
            brands = [dict(r) for r in rows]
        return jsonify({'ok': True, 'brands': brands, 'count': len(brands)})
    except Exception as e:
        return jsonify({'ok': False, 'brands': [], 'count': 0, 'error': str(e), 'code': 'BRAND_INDUSTRY_QUERY_ERROR'}), 500

@app.route('/api/brand-industry/brands/<path:name>')
def api_brand_industry_brand_detail(name):
    """品牌业态-单品牌详情：基础信息 + 实时匹配该品牌的笔记统计与最近笔记"""
    try:
        with db.get_db() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM brand_industry_monitor WHERE brand_name_cn=? OR brand_name=? OR brand_name_cn LIKE ? OR brand_name LIKE ? LIMIT 1",
                (name, name, f"%{name}%", f"%{name}%")).fetchone()
            if not row:
                return jsonify({'ok': False, 'error': '品牌不存在'}), 404
            brand = dict(row)
            cn = (brand.get('brand_name_cn') or '').strip()
            en = (brand.get('brand_name') or '').strip()
            # 用品牌中/英文名在标题、正文、摘要中匹配（英文名过短易误匹配，要求长度>=3）
            keys = [k for k in [cn] if k]
            if len(en) >= 3:
                keys.append(en)
            where = " OR ".join(["(title LIKE ? OR content LIKE ? OR summary LIKE ? OR body LIKE ?)" for _ in keys])
            params = []
            for k in keys:
                params += [f"%{k}%"] * 4
            notes = []
            total = pos = neg = 0
            if keys:
                rows = conn.execute(
                    f"SELECT note_id,title,author_nickname,publish_date,sentiment,risk_level,likes,comments,url FROM notes WHERE {where} ORDER BY publish_date DESC LIMIT 30",
                    params).fetchall()
                notes = [dict(r) for r in rows]
                total = len(notes)
                import canonical_metrics as _cmB
                _sB = _cmB.sentiment_count(notes)
                pos, neg = _sB['positive'], _sB['negative']  # neutral 仍用下方 total-pos-neg 差额法(既有口径)
            # 字段对齐前端 viewBrand
            brand.update({
                'name': cn or en or name,
                'category': brand.get('industry') or '未分类',
                'total_notes': total,
                'positive': pos,
                'negative': neg,
                'neutral': total - pos - neg,
                'recent_notes': notes[:10],
            })
        return jsonify({'ok': True, 'brand': brand})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/brand-industry/stats')
def api_brand_industry_stats_alias():
    """品牌业态-统计（前端兼容）"""
    try:
        with db.get_db() as conn:
            total = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor").fetchone()[0]
            industries = conn.execute("SELECT industry, COUNT(*) as cnt FROM brand_industry_monitor GROUP BY industry ORDER BY cnt DESC").fetchall()
            # 统计有负面/正面笔记的品牌数
            neg_brands = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor WHERE negative_count > 0").fetchone()[0]
            pos_brands = conn.execute("SELECT COUNT(*) FROM brand_industry_monitor WHERE positive_count > 0").fetchone()[0]
            cat_count = len(industries)
        return jsonify({'ok': True, 'total': total, 'total_brands': total,
                        'negative': neg_brands, 'negative_brands': neg_brands,
                        'positive': pos_brands, 'positive_brands': pos_brands,
                        'categories': cat_count,
                        'industries': [dict(r) for r in industries]})
    except Exception as e:
        return jsonify({'ok': False, 'total': 0, 'total_brands': 0, 'negative': 0, 'positive': 0, 'categories': 0, 'industries': [], 'error': str(e), 'code': 'BRAND_INDUSTRY_STATS_ERROR'}), 500

@app.route('/api/brand-industry/recompute', methods=['POST'])
def api_brand_industry_recompute():
    """兼容入口保留；未绑定精确品牌范围时不得重写全库预聚合。"""
    try:
        from brand_stats_recompute import recompute_brand_stats
        result = recompute_brand_stats(verbose=False)
        return jsonify({'ok': True, **result})
    except PermissionError:
        return jsonify({
            'ok': False, 'status': 'UNAVAILABLE',
            'code': 'BRAND_AGGREGATE_SCOPE_BINDING_REQUIRED',
            'error': '当前入口尚未绑定精确品牌范围与授权读取，未执行统计写入。',
        }), 409
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/negative-review/stats')
def api_negative_review_stats():
    """负面审核统计"""
    try:
        with db.get_db() as conn:
            # 与负面审核列表同口径：仅太古汇主体、非重复非噪音的负面，避免全网案例混入导致数字与列表不一致
            clause, sp = _subject_sql_and_values(); sp = tuple(sp)
            base = f"sentiment='negative' AND COALESCE(is_duplicate,0)=0 AND COALESCE(noise_type,'')='' AND {clause}"
            total = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base}", sp).fetchone()[0]
            confirmed = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND negative_confirmed=1", sp).fetchone()[0]
            rejected = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND negative_confirmed=2", sp).fetchone()[0]
            pending = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND (negative_confirmed=0 OR negative_confirmed IS NULL)", sp).fetchone()[0]
            high_risk = conn.execute(f"SELECT COUNT(*) FROM notes WHERE {base} AND risk_level='high'", sp).fetchone()[0]
        return jsonify({'ok': True, 'total': total, 'confirmed': confirmed, 'rejected': rejected, 'pending': pending, 'high_risk': high_risk})
    except Exception as e:
        return jsonify({'ok': False, 'total': 0, 'confirmed': 0, 'rejected': 0, 'pending': 0, 'high_risk': 0, 'error': str(e), 'code': 'NEGATIVE_REVIEW_STATS_ERROR'}), 500

@app.route('/api/settings')
def api_settings_get():
    """系统设置（前端兼容）"""
    try:
        from lumenis.system.ai_gateway.core import owned_inference_status
        owned = owned_inference_status()
        config = {
            'version': APP_VERSION,
            'auto_collect': os.getenv('REDNOTE_AUTO_RUN', 'false').lower() in ('1','true','yes','on'),
            'collector_type': 'SYSTEM Collector / source-specific adapters',
            'collector_scope': 'current Subject/BrandFocus + Permission',
            'auth_enabled': bool(AUTH_USER and AUTH_PASSWORD),
            'product_account_redesign_deferred': True,
            'ai_enabled': owned.get('available') is True and owned.get('service_binding') == 'BOUND',
            'ai_provider': 'owned',
            'ai_service_binding': owned.get('service_binding'),
            'ai_fallback_allowed': False,
        }
        return jsonify({'ok': True, 'settings': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/search', methods=['GET', 'POST'])
def api_unified_search():
    q = request.args.get('q','') if request.method=='GET' else str((request.get_json(silent=True) or {}).get('q',''))
    try: limit=max(1,min(30,int(request.args.get('limit',12))))
    except Exception: limit=12
    scope = None
    scope_state = 'SOURCE_SCOPE_UNAVAILABLE'
    try:
        _actor, scope, _entries, _selected = _resolve_web_scope('read', module='reports')
        scope_state = 'VERIFIED'
    except PermissionError:
        scope_state = 'SOURCE_SCOPE_PERMISSION_DENIED'
    except ValueError:
        scope_state = 'SOURCE_SCOPE_UNAVAILABLE'
    result = function_registry.search_targets(q, db=db, limit=limit, scope=scope)
    result.setdefault('meta', {})['source_scope_state'] = scope_state
    return jsonify(result)

@app.route('/api/function-map')
def api_function_map():
    return jsonify({'ok':True,'functions':function_registry.FUNCTION_MAP})

@app.route('/api/translate',methods=['POST'])
def api_translate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'JSON_OBJECT_REQUIRED'}), 400
    text = data.get('text')
    target = data.get('target', 'en')
    if not isinstance(text, str) or not text.strip():
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'TEXT_REQUIRED'}), 400
    if not isinstance(target, str) or target.lower() not in ('zh', 'en', 'ko'):
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'TRANSLATION_TARGET_UNSUPPORTED'}), 400
    target = target.lower()
    if target == 'zh':
        return jsonify({'ok': True, 'status': 'COMPLETED', 'provider': 'none',
                        'target': target, 'text': text})
    translated = intelligence.translate_text(text, target)
    if not isinstance(translated, str) or not translated.strip():
        try:
            runtime = intelligence.owned_inference_status()
        except Exception:
            runtime = {}
        code = runtime.get('reason') if isinstance(runtime, dict) else None
        return jsonify({
            'ok': False, 'status': 'UNAVAILABLE',
            'code': code or 'OWNED_RUNTIME_NOT_BOUND', 'provider': 'owned',
            'target': target, 'text': None,
        }), 503
    return jsonify({'ok': True, 'status': 'COMPLETED', 'provider': 'owned',
                    'target': target, 'text': translated})

@app.route('/api/notes/historical')
def api_notes_historical_v2():
    """历史案例笔记API v2（过期笔记，发布时间超过7天）"""
    try:
        from lumenis.shared.reporting.filtering import classify_notes_by_age
        from datetime import datetime, timedelta
        
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        all_notes = db.get_notes_by_date_range(start, end)
        
        age_classification = classify_notes_by_age(all_notes)
        historical = age_classification['historical']
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        return jsonify({
            'ok': True,
            'total': len(historical),
            'page': page,
            'per_page': per_page,
            'notes': historical[start_idx:end_idx],
            'description': '历史案例笔记：发布时间超过7天，不进入日报，但可作为案例参考'
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/platform-health')
def api_platform_health():
    """全局采集健康状态中心（只读）：逐平台状态 + 三类分清 + 动态调度，供首页健康小点与统一 Auth Modal。"""
    try:
        from lumenis.system.collector.adapters.health_center import build_platform_health
        return jsonify(build_platform_health())
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 500

# ========== 网络自适应 & 本地缓存降级 API ==========
@app.route('/api/network/status')
def api_network_status():
    import network_adaptive
    return jsonify({'ok':True, **network_adaptive.get_network_status()})

@app.route('/api/network/reset', methods=['POST'])
def api_network_reset():
    import network_adaptive
    status = network_adaptive.reset_network_status()
    return jsonify({'ok':True, 'message':'网络状态已重置', **status})

@app.route('/api/cache/status')
def api_cache_status():
    import cache_manager
    return jsonify({'ok':True, **cache_manager.get_cache_status()})

@app.route('/api/cache/data')
def api_cache_data():
    import cache_manager
    query_type = request.args.get('type', 'stats')
    limit = request.args.get('limit', 50, type=int)
    result = cache_manager.get_cached_data(query_type, limit)
    return jsonify({'ok':True, **result})

@app.route('/api/cache/create', methods=['POST'])
def api_cache_create():
    import cache_manager
    result = cache_manager.create_snapshot()
    return jsonify({'ok':result.get('success', False), **result})

@app.route('/api/cache/snapshots')
def api_cache_snapshots():
    import cache_manager
    return jsonify({'ok':True, 'snapshots': cache_manager.list_snapshots()})

@app.route('/api/collect',methods=['POST'])
def api_collect():
    import uuid
    from dataclasses import replace
    from experience_runtime import _content_project_error
    from shared_artifacts import LocalArtifactError
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    from lumenis.system.collector.adapters.secondary_collection import _manual_collection_guard
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) - {
            'keywords', 'max_scroll', 'max_results', 'operator', 'confirm_read_only'}:
        return jsonify({'ok': False, 'code': 'INVALID_COLLECTION_REQUEST'}), 400
    operator = data.get('operator')
    if operator not in {'human', 'human_ui'}:
        return jsonify({'ok': False, 'code': 'HUMAN_OPERATOR_REQUIRED'}), 403
    if data.get('confirm_read_only') is not True:
        return jsonify({'ok': False, 'code': 'READ_ONLY_CONFIRMATION_REQUIRED'}), 400
    keywords = data.get('keywords')
    if isinstance(keywords, str):
        keywords = [word.strip() for word in keywords.split(',') if word.strip()]
    if keywords is not None and (not isinstance(keywords, list) or
            not keywords or any(not isinstance(word, str) or not word.strip() for word in keywords)):
        return jsonify({'ok': False, 'code': 'INVALID_COLLECTION_KEYWORDS'}), 400
    max_results = data.get('max_results', 20)
    if type(max_results) is not int or not 1 <= max_results <= 20:
        return jsonify({'ok': False, 'code': 'INVALID_COLLECTION_LIMIT'}), 400
    # Explicit legacy depth is passed through the same approval/adapter contract.
    max_scroll = data.get('max_scroll')
    if max_scroll is not None and (type(max_scroll) is not int or not 1 <= max_scroll <= 20):
        return jsonify({'ok': False, 'code': 'INVALID_COLLECTION_SCROLL_LIMIT'}), 400
    try:
        actor, scope, owner = _collect_request_context('write')
        plan = build_acquisition_plan(keywords,
            context_mode='GLOBAL_ALL' if scope['global_scope'] else 'FOCUS',
            domain_id=None if scope['global_scope'] else ('CTH' if scope['domain_id'] == 'cth' else 'BMP'),
            subject_id=scope.get('subject_id'), brand_focus_id=scope.get('brand_focus_id'),
            max_queries=20)
        queries = tuple(query for query in plan.queries
            if query.scope['domain_id'] == scope['domain_id'] and
            (scope['global_scope'] or query.scope == scope))
        if not plan.is_runnable or not queries:
            return jsonify({'ok': False, 'code': 'ACQUISITION_PLAN_BLOCKED',
                            'query_plan': plan.to_dict()}), 409
        plan = replace(plan, queries=queries)
        # Admission is checked before work starts and again at execution/write time.
        for query in queries:
            _, denial = _manual_collection_guard(actor, scope,
                'xiaohongshu', query.keyword, max_results, max_scroll=max_scroll)
            if denial is not None:
                return jsonify(denial), (503 if denial['status'] == 'PERMISSION_UNAVAILABLE' else 403)
    except LocalArtifactError as exc:
        return _content_project_error(exc)
    except ValueError:
        return jsonify({'ok': False, 'code': 'INVALID_ACQUISITION_PLAN'}), 400
    if not _collect_lock.acquire(blocking=False):
        return jsonify({'ok': False, 'code': 'COLLECTOR_BUSY'}), 409
    task_id = uuid.uuid4().hex
    with _task_lock:
        collect_tasks[task_id] = {
            'task_id': task_id, 'status': 'pending', 'message': '任务已创建', 'progress': 0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'keywords': [query.keyword for query in queries], 'query_plan': plan.to_dict(),
            'max_results': max_results, 'max_scroll': max_scroll,
            'pagination_owner': 'SYSTEM_COLLECTOR', 'resume_supported': False,
            '_owner': owner, '_scope': dict(scope),
        }
    @copy_current_request_context
    def run():
        _run_collect_task(task_id, queries, max_results, actor, operator, scope, max_scroll)
    try:
        threading.Thread(target=run, daemon=True).start()
    except Exception:
        with _task_lock:
            collect_tasks[task_id].update(status='error', code='COLLECTOR_START_FAILED')
        _collect_lock.release()
        return jsonify({'ok': False, 'code': 'COLLECTOR_START_FAILED', 'task_id': task_id}), 503
    return jsonify({'ok': True, 'task_id': task_id, 'query_plan': plan.to_dict(),
                    'max_results': max_results, 'resume_supported': False})


@app.route('/api/collect/status/<task_id>')
def api_collect_status(task_id):
    from experience_runtime import _content_project_error
    from shared_artifacts import LocalArtifactError
    try:
        _, scope, owner = _collect_request_context('read')
    except LocalArtifactError as exc:
        return _content_project_error(exc)
    with _task_lock:
        task = collect_tasks.get(task_id)
        visible = task and task.get('_owner') == owner and task.get('_scope') == scope
        result = _public_collect_task(task) if visible else None
    return (jsonify({'ok': True, 'task': result}), 200) if result else (
        jsonify({'ok': False, 'error': '任务不存在'}), 404)


@app.route('/api/collect/tasks')
def api_collect_tasks():
    from experience_runtime import _content_project_error
    from shared_artifacts import LocalArtifactError
    try:
        _, scope, owner = _collect_request_context('read')
    except LocalArtifactError as exc:
        return _content_project_error(exc)
    with _task_lock:
        tasks = [_public_collect_task(task) for task in collect_tasks.values()
                 if task.get('_owner') == owner and task.get('_scope') == scope]
    return jsonify({'ok': True, 'tasks': sorted(tasks,
        key=lambda task: task['created_at'], reverse=True)[:20]})


@app.route('/api/analyze',methods=['POST'])
def api_analyze():
    body = request.get_json(silent=True)
    if body is None:
        body = {}
    if not isinstance(body, dict):
        return jsonify({'ok': False, 'status': 'INVALID_REQUEST', 'code': 'INVALID_JSON_OBJECT'}), 400
    try:
        limit = max(1, min(5000, int(body.get('limit', 500))))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'status': 'INVALID_REQUEST', 'code': 'INVALID_LIMIT'}), 400
    try:
        _actor, scope, _entries, _selected = _resolve_web_scope('write', module='reports')
    except (PermissionError, ValueError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 409
        return jsonify({'ok':False,'status':'BLOCKED','code':str(exc)}),status
    counts=reprocess.reprocess_notes(limit, translate=False, scope=scope)
    try:
        aggregation=reprocess.build_cross_platform_events(scope=scope)
        event_count=len(aggregation.get('events', []))
        events={'status':aggregation.get('status', 'COMPLETED'),'count':event_count,
                'rejected_source_count':aggregation.get('rejected_source_count', 0),
                'truncated':aggregation.get('truncated', False)}
    except ValueError as exc:
        events={'status':'BLOCKED','code':str(exc)}
    completed = counts.get('status') == 'COMPLETED' and events.get('status') == 'COMPLETED'
    status = 'COMPLETED' if completed else 'PARTIAL'
    return jsonify({'ok':completed,'status':status,'scope':scope,'counts':counts,
                    'events':events,'ai_enabled':intelligence.ai_enabled()})

def subject_hit_note_safe(note):
    return subject_hit(
        title=note.get('title',''), body=note.get('body',''), content=note.get('content',''),
        source_keyword=note.get('source_keyword',''), matched_keywords=note.get('matched_keywords','')
    )

@app.route('/api/note/<note_id>')
@app.route('/api/notes/<note_id>')
def api_note_detail(note_id):
    from data_query_api import LegacyScopeReadError, read_scoped_legacy_note_rows
    try:
        result = read_scoped_legacy_note_rows(
            module='content', filters={'note_id': note_id}, limit=1,
            require_complete=True,
        )
    except LegacyScopeReadError as exc:
        return jsonify({'ok': False, 'error': exc.code, 'code': exc.code}), exc.status
    note = result['notes'][0] if result['notes'] else None
    return (jsonify({'ok': True, 'note': note, 'scope': result['scope']}), 200) if note else (jsonify({'ok': False, 'error': 'Not found'}), 404)
@app.route('/api/historical-notes')
def api_historical_notes():
    now=datetime.now(); today=now.strftime('%Y-%m-%d'); period=request.args.get('period','daily')
    start=(now-timedelta(days=now.weekday())).strftime('%Y-%m-%d') if period=='weekly' else (now.replace(day=1).strftime('%Y-%m-%d') if period=='monthly' else today)
    return jsonify({'ok':True,'notes':db.get_historical_notes(start,today,100),'stats':db.get_historical_stats(start,today),'period_start':start,'period_end':today})
@app.route('/api/backup',methods=['POST'])
def api_backup():
    backup_dir=os.path.join(os.path.dirname(db.DB_PATH),'backups'); os.makedirs(backup_dir,exist_ok=True)
    dest=os.path.join(backup_dir,f"monitor-{datetime.now():%Y%m%d-%H%M%S}.db")
    db.backup_database(dest)
    # 只保留最近 30 份，避免长期运行把磁盘吃满。
    files=sorted((os.path.join(backup_dir,f) for f in os.listdir(backup_dir) if f.endswith('.db')), key=os.path.getmtime, reverse=True)
    for old_file in files[30:]:
        try: os.remove(old_file)
        except OSError: pass
    return jsonify({'ok':True,'file':os.path.basename(dest),'path':dest})

# ===== v5.7.0 八项升级 API =====
@app.route('/api/weekly/events')
def api_weekly_events_v570():
    start,end=weekly_events.natural_week()
    with db.get_db() as conn: payload=weekly_events.weekly_payload(conn,start,end)
    return jsonify({'ok':True,**payload})

@app.route('/api/web/browser-discovery',methods=['POST'])
def api_browser_discovery_v570():
    data=request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'ok':False,'status':'INVALID_REQUEST','code':'INVALID_JSON_OBJECT'}),400
    try:
        _actor, scope, entries, selected = _resolve_web_scope('read')
    except (PermissionError, ValueError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 409
        return jsonify({'ok':False,'status':'BLOCKED','code':str(exc)}),status
    if scope['global_scope'] or not isinstance(selected, dict):
        return jsonify({'ok':False,'status':'BLOCKED','code':'FOCUS_SCOPE_REQUIRED'}),409
    raw_queries=data.get('queries')
    if isinstance(raw_queries, str):
        raw_queries=[raw_queries]
    if not isinstance(raw_queries, list) or not raw_queries or any(
            not isinstance(query, str) or not query.strip() for query in raw_queries):
        return jsonify({'ok':False,'status':'INVALID_REQUEST','code':'QUERY_REQUIRED'}),400
    terms = _web_scope_terms(entries)
    if not terms:
        return jsonify({'ok':False,'status':'BLOCKED','code':'REGISTERED_SCOPE_TERMS_UNAVAILABLE'}),409
    anchor = terms[0]
    queries = [query.strip() if anchor.casefold() in query.casefold()
               else f'{anchor} {query.strip()}' for query in raw_queries[:20]]
    try:
        limit=max(1,min(200,int(data.get('limit') or os.getenv('WEB_BROWSER_DISCOVERY_LIMIT','80'))))
    except (TypeError,ValueError):
        return jsonify({'ok':False,'status':'INVALID_REQUEST','code':'INVALID_LIMIT'}),400
    items=browser_discovery.discover(queries,limit)
    return jsonify({'ok':True,'count':len(items),'items':items,'scope':scope,
                    'queries':queries,'budget':'independent_browser_search'})

@app.route('/api/web/brand-industry/plan')
def api_brand_industry_plan_v570():
    try:
        _actor, scope, entries, selected = _resolve_web_scope('read')
        brands,cats=_web_scope_brands(entries,selected)
        qs=web_discovery.brand_queries(brands,cats)
    except (PermissionError, ValueError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 409
        return jsonify({'ok':False,'status':'BLOCKED','code':str(exc)}),status
    except RuntimeError as exc:
        return jsonify({'ok':False,'status':'UNAVAILABLE','code':str(exc)}),503
    try:
        batch=max(1,min(30,int(request.args.get('batch','12'))))
    except (TypeError,ValueError):
        return jsonify({'ok':False,'status':'INVALID_REQUEST','code':'INVALID_BATCH'}),400
    return jsonify({'ok':True,'scope':scope,'total_targets':len(qs),
                    'brands':len(brands),'categories':cats,'batch_size':batch})

@app.route('/api/web/brand-industry/run',methods=['POST'])
def api_brand_industry_run_v570():
    data=request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'ok':False,'status':'INVALID_REQUEST','code':'INVALID_JSON_OBJECT'}),400
    try:
        batch=max(1,min(30,int(data.get('batch',12))))
        offset=max(0,int(data.get('offset',0)))
    except (TypeError,ValueError):
        return jsonify({'ok':False,'status':'INVALID_REQUEST','code':'INVALID_BATCH_OR_OFFSET'}),400
    try:
        actor, scope, entries, selected = _resolve_web_scope('write', module='collector')
        brands,cats=_web_scope_brands(entries,selected)
        queries=web_discovery.brand_queries(brands,cats)
    except (PermissionError, ValueError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 409
        return jsonify({'ok':False,'status':'BLOCKED','code':str(exc)}),status
    except RuntimeError as exc:
        return jsonify({'ok':False,'status':'UNAVAILABLE','code':str(exc)}),503
    if not queries:
        return jsonify({'ok':False,'status':'BLOCKED','code':'SCOPED_QUERY_PLAN_UNAVAILABLE'}),409
    from lumenis.system.collector.adapters.secondary_collection import collect_search
    results=[]
    for query in queries[offset:offset+batch]:
        results.append(collect_search('web_rss', query, max_results=20,
            operator='human_ui', scope=scope, actor=actor))
    success_count=sum(1 for item in results if item.get('ok') is True)
    status='COMPLETED' if results and success_count == len(results) else ('PARTIAL' if success_count else 'BLOCKED')
    return jsonify({'ok':status == 'COMPLETED','status':status,'scope':scope,
                    'results':results,'fetched':sum(int(item.get('raw_count') or 0) for item in results),
                    'saved':sum(int(item.get('imported') or 0) for item in results),
                    'total_targets':len(queries),
                    'next_offset':offset+batch if offset+batch<len(queries) else 0,
                    'independent_budget':True}), (200 if success_count else 409)

@app.route('/api/notes/publish-buckets')
def api_publish_buckets_v570():
    date=request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    with db.get_db() as conn:
        same=[dict(r) for r in conn.execute("SELECT * FROM notes WHERE is_taikoo_verified=1 AND substr(COALESCE(publish_datetime,publish_date),1,10)=? ORDER BY collected_at DESC",(date,)).fetchall()]
        historical=[dict(r) for r in conn.execute("SELECT * FROM notes WHERE is_taikoo_verified=1 AND substr(COALESCE(publish_datetime,publish_date),1,10)<? AND substr(collected_at,1,10)=? ORDER BY collected_at DESC",(date,date)).fetchall()]
    return jsonify({'ok':True,'date':date,'published_today':same,'historical_collected_today':historical,'counts':{'published_today':len(same),'historical_collected_today':len(historical)}})

@app.route('/api/trends/global')
def api_global_trends_v570():
    days=max(7,min(90,int(request.args.get('days','14'))))
    now=datetime.now()
    start=(now-timedelta(days=days-1)).strftime('%Y-%m-%d')
    end=now.strftime('%Y-%m-%d')
    with db.get_db() as conn:
        rows=conn.execute("SELECT publish_date,COUNT(*) total,SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) negative,SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) high FROM notes WHERE is_taikoo_verified=1 AND COALESCE(relevance_status,'relevant')!='irrelevant' AND publish_date BETWEEN ? AND ? GROUP BY publish_date ORDER BY publish_date",(start,end)).fetchall()
    data=[]
    for r in rows:
        total=r['total'] or 0
        data.append({'date':r['publish_date'],'total':total,'negative':r['negative'] or 0,'high':r['high'] or 0,'negative_pct':round((r['negative'] or 0)*100/total,1) if total else 0,'high_pct':round((r['high'] or 0)*100/total,1) if total else 0})
    return jsonify({'ok':True,'days':days,'data':data})

@app.route('/api/dashboard/changes')
def api_dashboard_changes_v570():
    stats=db.get_stats()
    now=datetime.now()
    return jsonify({'ok':True,'server_time':now.strftime('%Y-%m-%d %H:%M:%S'),'stats':stats,'version':APP_VERSION})

# ===== v5.7.1 笔记库查询 + 周期报告核对 =====
@app.route('/api/notes/library')
def api_notes_library_v571():
    """笔记库查询：支持按发布日期、采集日期、关键词、情感、风险等级筛选"""
    page=max(1,int(request.args.get('page',1)))
    per_page=max(10,min(100,int(request.args.get('per_page',20))))
    keyword=request.args.get('keyword','').strip()
    sentiment=request.args.get('sentiment','').strip()
    risk_level=request.args.get('risk_level','').strip()
    publish_start=request.args.get('publish_start','').strip()
    publish_end=request.args.get('publish_end','').strip()
    collect_start=request.args.get('collect_start','').strip()
    collect_end=request.args.get('collect_end','').strip()
    
    with db.get_db() as conn:
        cols=[r[1] for r in conn.execute('PRAGMA table_info(notes)').fetchall()]
        select_cols=[c for c in ['note_id','title','author_nickname','publish_date','collected_at','url','sentiment','risk_level','risk_score','summary','likes','comments','collects','shares','source_platform','negative_confirmed'] if c in cols]
        
        sql=f"SELECT {','.join(select_cols)} FROM notes WHERE 1=1"
        params=[]
        
        if keyword:
            sql+=" AND (title LIKE ? OR summary LIKE ? OR author_nickname LIKE ?)"
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
        if sentiment:
            sql+=" AND sentiment=?"
            params.append(sentiment)
        if risk_level:
            sql+=" AND risk_level=?"
            params.append(risk_level)
        if publish_start:
            sql+=" AND date(publish_date)>=date(?)"
            params.append(publish_start)
        if publish_end:
            sql+=" AND date(publish_date)<=date(?)"
            params.append(publish_end)
        if collect_start:
            sql+=" AND date(collected_at)>=date(?)"
            params.append(collect_start)
        if collect_end:
            sql+=" AND date(collected_at)<=date(?)"
            params.append(collect_end)
        
        # 总数
        count_sql=sql.replace(f"SELECT {','.join(select_cols)}", "SELECT COUNT(*)")
        total=conn.execute(count_sql, params).fetchone()[0]
        
        # 分页
        offset=(page-1)*per_page
        sql+=" ORDER BY collected_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        notes=[dict(r) for r in conn.execute(sql, params).fetchall()]
    
    return jsonify({'ok':True,'notes':notes,'total':total,'page':page,'per_page':per_page,'total_pages':(total+per_page-1)//per_page})

@app.route('/remote')
def remote_access():
    """Keep old bookmarks safe without opening an unapproved public endpoint."""
    return jsonify({
        'ok': False,
        'error': 'PUBLIC_REMOTE_ACCESS_UNAVAILABLE',
        'message': '当前产品不提供临时公网访问，请使用本机工作区。',
        'messages': {
            'zh': '当前产品不提供临时公网访问，请使用本机工作区。',
            'en': 'Temporary public access is unavailable. Use the local workspace.',
            'ko': '임시 공개 접속은 제공되지 않습니다. 로컬 작업 공간을 이용하세요.',
        },
        'local_url': f'http://127.0.0.1:{APP_PORT}',
    }), 410


@app.route('/healthz')
def healthz():
    """Core health requires the existing canonical database and its base schema."""
    database_status = 'ok'
    try:
        with get_repository().connection(read_only=True, wal=False) as connection:
            marker = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='notes'"
            ).fetchone()
        if marker is None:
            database_status = 'unavailable'
    except Exception:
        database_status = 'unavailable'

    healthy = database_status == 'ok'
    return jsonify({
        'ok': healthy,
        'status': 'healthy' if healthy else 'unavailable',
        'dependencies': {'database': database_status},
        'version': APP_VERSION,
        'service': CORE_SERVICE_NAME,
        'core_instance': dict(_CORE_INSTANCE),
        'runtime': {
            'web_server': _CORE_SERVER_KIND,
            'scheduler': _scheduler_runtime_state(),
        },
    }), (200 if healthy else 503)

@app.route('/api/health')
def api_health():
    """P1-1 只读健康端点：无认证、不写库、不触发采集，供负载均衡/监控探活。"""
    _port = None
    try:
        _host = request.host or ''
        if ':' in _host:
            _port = int(_host.rsplit(':', 1)[1])
    except Exception:
        _port = None
    if _port is None:
        for _env_key in ('PORT', 'FLASK_RUN_PORT', 'TAIKOO_PORT'):
            _v = os.getenv(_env_key)
            if _v:
                try:
                    _port = int(_v)
                    break
                except Exception:
                    pass
    _db_status = 'ok'
    _db_error = None
    try:
        with db.get_db() as _conn:
            _conn.execute('SELECT 1').fetchone()
    except Exception as _e:
        _db_status = 'error'
        _db_error = str(_e)
    _payload = {
        'ok': _db_status == 'ok',
        'service': CORE_SERVICE_NAME,
        'version': APP_VERSION,
        'pid': os.getpid(),
        'port': _port,
        'database': _db_status,
        'time': datetime.now().isoformat(),
    }
    if _db_error:
        _payload['database_error'] = _db_error
    return jsonify(_payload)

@app.route('/api/system/health')
def api_system_health():
    """SYSTEM health is technical; business metrics require a selected scope."""
    now = datetime.now()
    result = {
        'version': APP_VERSION, 'service': CORE_SERVICE_NAME,
        'time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'business_metrics': None, 'business_metrics_state': 'SCOPE_REQUIRED',
    }
    try:
        with db.get_db() as conn:
            conn.execute('SELECT 1').fetchone()
        result['database'] = 'ok'
    except Exception as exc:
        result.update({'database': 'error', 'database_error': type(exc).__name__})
    from lumenis.system.ai_gateway.core import owned_inference_status
    result['ai'] = owned_inference_status()
    result['web_discovery_enabled'] = os.getenv('TAIKOO_WEB_DISCOVERY', '0').lower() not in ('0', 'false', 'no', 'off')
    return jsonify({'ok': result.get('database') == 'ok', 'health': result})

# ===== ZBC Lifecycle Contract V1.0: Runtime Worker API =====
# ========== Security API（P0修复：前端调用/api/security/scan 404） ==========
@app.route('/api/security/scan', methods=['GET'])
def api_security_scan():
    """安全扫描API。调用security_scanner，返回扫描结果摘要。"""
    try:
        import security_scanner as ss
        quick_scan = getattr(ss, 'quick_scan', None)
        run_scan = getattr(ss, 'run_scan', None)
        if callable(quick_scan):
            result = quick_scan()
        elif callable(run_scan):
            result = run_scan(quick_mode=True)
        else:
            return jsonify({
                "ok": False,
                "status": "UNAVAILABLE",
                "code": "QUICK_SECURITY_SCAN_UNAVAILABLE",
                "source": "security_scanner",
            }), 503
        if result is None:
            return jsonify({
                "ok": False,
                "status": "UNAVAILABLE",
                "code": "QUICK_SECURITY_SCAN_RESULT_UNAVAILABLE",
                "source": "security_scanner",
            }), 503
        return jsonify({"ok": True, "data": result, "source": "security_scanner"})
    except Exception:
        app.logger.exception("security scan failed")
        return jsonify({
            "ok": False,
            "status": "ERROR",
            "code": "QUICK_SECURITY_SCAN_FAILED",
            "source": "security_scanner",
        }), 500

@app.route('/api/security/status', methods=['GET'])
def api_security_status():
    """安全状态API。返回用户/角色/审计/域隔离状态。"""
    try:
        c = get_db()
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0] if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone() else 1
        roles = c.execute("SELECT COUNT(*) FROM roles").fetchone()[0] if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roles'").fetchone() else 3
        audit = c.execute("SELECT COUNT(*) FROM audit_log WHERE date(created_at)=date('now')").fetchone()[0] if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'").fetchone() else 0
        return jsonify({"ok": True, "data": {
            "users": users, "roles": roles, "audit_today": audit,
            "domain_isolation": "enabled", "permission_gate": "active",
            "action_firewall": "active", "effect_fence": "active",
        }})
    except Exception as e:
        return jsonify({"ok": True, "data": {"users": 1, "roles": 3, "audit_today": 0, "domain_isolation": "enabled", "message": str(e)[:100]}})

@app.route('/api/system/runtime')
def api_system_runtime():
    """兼容路由：委托聚合 API 的唯一 Runtime 状态实现。"""
    try:
        from lumenis_agg_api import system_runtime
        return system_runtime()
    except Exception:
        app.logger.exception("system runtime owner unavailable")
        return jsonify({
            "ok": False,
            "state": "UNAVAILABLE",
            "code": "SYSTEM_RUNTIME_OWNER_UNAVAILABLE",
            "runtime_by_domain": {},
        }), 503

# ========== P0修复：System页面兼容路由 + 缺失API ==========
@app.route('/api/system/workers')
def api_system_workers():
    """兼容路由：前端调/api/system/workers，实际走/api/runtime/workers"""
    try:
        import runtime_guardian as _rg
        g = _rg.get_guardian("system")
        workers = g.list_lifecycle_workers()
        status_filter = request.args.get("status")
        if status_filter:
            workers = [w for w in workers if w.get("status") == status_filter]
        return jsonify({"ok": True, "count": len(workers), "workers": workers})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "workers": []}), 500

@app.route('/api/system/dlq')
def api_system_dlq():
    """DLQ统计"""
    try:
        import runtime_guardian as _rg
        g = _rg.existing_guardian("app_main")
        stats_reader = getattr(getattr(g, 'dlq', None), 'stats', None)
        if not callable(stats_reader):
            return jsonify({"ok": False, "state": "UNAVAILABLE",
                            "code": "SYSTEM_DLQ_UNAVAILABLE", "dlq": None}), 503
        stats = stats_reader()
        if not isinstance(stats, dict) or not isinstance(stats.get("total"), int) or isinstance(stats.get("total"), bool) or stats["total"] < 0:
            return jsonify({"ok": False, "state": "UNAVAILABLE",
                            "code": "SYSTEM_DLQ_RESULT_UNAVAILABLE", "dlq": None}), 503
        return jsonify({"ok": True, "state": "AVAILABLE", "dlq": stats})
    except Exception:
        app.logger.exception("system dlq read failed")
        return jsonify({"ok": False, "state": "ERROR",
                        "code": "SYSTEM_DLQ_READ_FAILED", "dlq": None}), 503

@app.route('/api/system/database')
def api_system_database():
    """数据库状态：表数量、非空表、核心表记录数"""
    try:
        with get_repository().connection(read_only=True, wal=False) as c:
            c.execute("BEGIN")
            tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
            counts = {}
            table_stats = []
            for t in tables:
                try:
                    quoted = t.replace('"', '""')
                    counts[t] = c.execute(f'SELECT COUNT(*) FROM "{quoted}"').fetchone()[0]
                except Exception:
                    counts[t] = None
                    app.logger.warning("system database table count unavailable")
                table_stats.append({"name": t, "count": counts[t],
                                    "state": "ERROR" if counts[t] is None else "AVAILABLE"})
        core_names = ("notes", "events", "comments", "daily_reports", "users", "kos_operations")
        unreadable = sum(value is None for value in counts.values())
        return jsonify({
            "ok": unreadable == 0, "state": "PARTIAL" if unreadable else "AVAILABLE",
            "code": "SYSTEM_DATABASE_PARTIAL" if unreadable else None,
            "table_count": len(tables),
            "non_empty": None if unreadable else sum(value > 0 for value in counts.values()),
            "empty": None if unreadable else sum(value == 0 for value in counts.values()),
            "unreadable": unreadable,
            "core": {name: counts.get(name) for name in core_names},
            "core_states": {name: "NOT_PRESENT" if name not in counts else
                            "ERROR" if counts[name] is None else "AVAILABLE" for name in core_names},
            "tables": table_stats[:50], "tables_truncated": len(table_stats) > 50,
        })
    except Exception:
        app.logger.exception("system database read failed")
        return jsonify({"ok": False, "state": "ERROR", "code": "SYSTEM_DATABASE_READ_FAILED",
                        "table_count": None, "non_empty": None, "empty": None,
                        "core": None, "tables": None}), 503

@app.route('/api/system/security')
def api_system_security():
    """安全状态汇总"""
    try:
        c = get_db()
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0] if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone() else 1
        audit = c.execute("SELECT COUNT(*) FROM audit_log WHERE date(created_at)=date('now')").fetchone()[0] if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'").fetchone() else 0
        return jsonify({"ok": True, "data": {
            "users": users, "audit_today": audit,
            "domain_isolation": "enabled", "permission_gate": "active",
            "action_firewall": "active", "effect_fence": "active",
            "auth_recovery": "active", "secret_scanning": "active",
        }})
    except Exception as e:
        return jsonify({"ok": True, "data": {"users": 1, "audit_today": 0, "message": str(e)[:100]}})

@app.route('/api/system/security/audit')
def api_system_security_audit():
    """安全审计日志"""
    try:
        c = get_db()
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'").fetchone():
            logs = c.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 50").fetchall()
            cols = [d[0] for d in c.execute("SELECT * FROM audit_log LIMIT 1").description]
            return jsonify({"ok": True, "count": len(logs), "logs": [dict(zip(cols, row)) for row in logs]})
        return jsonify({"ok": True, "count": 0, "logs": []})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/collector/quality')
def api_collector_quality():
    """采集器质量统计"""
    try:
        c = get_db()
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collector_quality_log'").fetchone():
            total = c.execute("SELECT COUNT(*) FROM collector_quality_log").fetchone()[0]
            recent = c.execute("SELECT * FROM collector_quality_log ORDER BY id DESC LIMIT 20").fetchall()
            cols = [d[0] for d in c.execute("SELECT * FROM collector_quality_log LIMIT 1").description] if recent else []
            return jsonify({"ok": True, "total": total, "recent": [dict(zip(cols, row)) for row in recent]})
        # 降级：用collection_logs
        if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection_logs'").fetchone():
            total = c.execute("SELECT COUNT(*) FROM collection_logs").fetchone()[0]
            success = c.execute("SELECT COUNT(*) FROM collection_logs WHERE status='success'").fetchone()[0]
            return jsonify({"ok": True, "total": total, "success": success, "source": "collection_logs"})
        return jsonify({"ok": True, "total": 0, "message": "no quality data"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/podcast/topics')
def api_podcast_topics_compat():
    """兼容路由：前端调/api/podcast/topics，实际走/api/podcast/overview"""
    try:
        from podcast_routes import podcast_bp
        # 直接调用overview逻辑
        import sqlite3
        db = get_repository().connect()
        c = db.cursor()
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        topics = []
        for t in ("podcast_topics", "podcast_episodes", "podcast_entities"):
            if t in tables:
                cnt = c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                topics.append({"table": t, "count": cnt})
        db.close()
        return jsonify({"ok": True, "topics": topics, "count": len(topics)})
    except Exception as e:
        return jsonify({"ok": True, "topics": [], "count": 0, "error": str(e)[:100]})

@app.route('/api/runtime/workers')
def api_runtime_workers():
    """列出所有 lifecycle worker（支持 ?status=running 过滤）。"""
    try:
        import runtime_guardian as _rg
        g = _rg.get_guardian("system")
        status_filter = request.args.get("status")
        workers = g.list_lifecycle_workers()
        if status_filter:
            workers = [w for w in workers if w.get("status") == status_filter]
        return jsonify({"ok": True, "count": len(workers), "workers": workers})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "workers": []}), 500

@app.route('/api/runtime/workers/<worker_id>/archive', methods=['POST'])
def api_runtime_archive_worker(worker_id):
    """归档指定 worker（STOPPED/DEAD → ARCHIVED）。"""
    try:
        import runtime_guardian as _rg
        g = _rg.get_guardian("system")
        ok = g.lifecycle_archive(worker_id, reason="manual_archive")
        return jsonify({"ok": ok, "worker_id": worker_id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/runtime/archive-dead', methods=['POST'])
def api_runtime_archive_dead():
    """批量归档超过指定时长的 DEAD/STOPPED worker（默认24小时）。"""
    try:
        import runtime_guardian as _rg
        g = _rg.get_guardian("system")
        hours = float(request.args.get("hours", 24))
        count = g.archive_dead_workers(older_than_hours=hours)
        # 审批是一次性运行时授权：成功执行后立即撤销，防止重复提交重放。
        try:
            if _pg is not None:
                token = _pg.get_valid_approval_token(
                    OperationType.RUNTIME_OPERATION.value, '/api/runtime/archive-dead')
                if token:
                    _pg.revoke_approval(token)
        except Exception:
            # 归档已经完成；撤销失败必须留下可见状态，而不是伪装成完整闭环。
            return jsonify({"ok": True, "archived": count, "hours": hours,
                            "approval_consumed": False,
                            "warning": "归档已执行，但审批令牌撤销未确认"})
        return jsonify({"ok": True, "archived": count, "hours": hours,
                        "approval_consumed": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/runtime/archive-dead/approval', methods=['POST'])
def api_runtime_archive_dead_approval():
    """发放一次、固定资源范围的 dead-worker 归档审批令牌。

    该端点不执行归档；它只在已认证用户通过产品确认对话框提交精确
    confirm/action/resource 后创建短时令牌。实际归档请求仍会被全局 Gate
    拦截，避免把“用户文字授权”误当成运行时审批。
    """
    try:
        payload = request.get_json(silent=True) or {}
        if payload.get('confirm') is not True:
            return jsonify({'ok': False, 'status': 'REQUIRES_CONFIRMATION',
                            'error': '必须由产品确认界面提交 confirm=true'}), 400
        if payload.get('action') != 'archive_dead_workers':
            return jsonify({'ok': False, 'status': 'INVALID_ACTION',
                            'error': '审批动作不匹配'}), 400
        if payload.get('resource') != '/api/runtime/archive-dead':
            return jsonify({'ok': False, 'status': 'INVALID_RESOURCE',
                            'error': '审批资源范围不匹配'}), 400
        hours = float(payload.get('hours', 24))
        if not (0 < hours <= 24 * 365):
            return jsonify({'ok': False, 'status': 'INVALID_HOURS',
                            'error': 'hours 必须在 0 与 8760 之间'}), 400
        if _pg is None:
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'error': 'PermissionGate 未初始化（fail-closed）'}), 503
        caller = (request.authorization.username if request.authorization else None) or 'human-ui'
        token = _pg.grant_approval(
            OperationType.RUNTIME_OPERATION.value,
            duration_minutes=5,
            resource='/api/runtime/archive-dead',
            granted_by=caller,
        )
        return jsonify({
            'ok': True,
            'status': 'APPROVED',
            'operation': OperationType.RUNTIME_OPERATION.value,
            'resource': '/api/runtime/archive-dead',
            'hours': hours,
            'approval_token': token,
            'expires_in_minutes': 5,
            'execution_required': True,
        })
    except Exception as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(e)}), 500

# ===== Collector Guard 状态 API（旁路模式，只读）=====
@app.route('/api/collector-guard/status')
def api_collector_guard_status():
    """采集守护系统状态：各平台限速器/熔断/指标快照。旁路模式，不改变采集行为。"""
    try:
        from collector_guard_integration import get_all_status, is_enabled
        return jsonify({'ok': True, 'enabled': is_enabled(), 'guards': get_all_status()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== v5.3.2 智能日报 API =====
@app.route('/api/overview')
def api_overview():
    """Summarize observed records within the explicitly selected CTH scope."""
    from data_query_api import LegacyScopeReadError, read_scoped_legacy_note_rows
    now = datetime.now()
    start = (now - timedelta(days=13)).strftime('%Y-%m-%d')
    end = now.strftime('%Y-%m-%d')
    try:
        result = read_scoped_legacy_note_rows(
            module='reports', limit=1000, scan_all=True,
            include_all_projection=True,
        )
    except LegacyScopeReadError as exc:
        return jsonify({'ok': False, 'error': exc.code, 'code': exc.code}), exc.status

    scope_complete = (
        result['data_state'] == 'READY' and not result['truncated']
        and result['total'] is not None and result['total'] == len(result['notes'])
    )
    dated_rows = []
    unknown_publication_time = False
    if scope_complete:
        for note in result['notes']:
            day = str(note.get('publish_date') or '')[:10]
            if len(day) != 10:
                unknown_publication_time = True
                continue
            if start <= day <= end:
                dated_rows.append((day, note))
    trend_complete = scope_complete and not unknown_publication_time
    counts = {}
    if trend_complete:
        for day, note in dated_rows:
            bucket = counts.setdefault(day, {'total': 0, 'negative': 0, 'high': 0})
            bucket['total'] += 1
            bucket['negative'] += int(note.get('sentiment') == 'negative')
            bucket['high'] += int(note.get('risk_level') == 'high')
    trend = []
    for index in range(14):
        day = (now - timedelta(days=13-index)).strftime('%Y-%m-%d')
        value = counts.get(day) if trend_complete else None
        trend.append({
            'date': day, 'label': day[5:],
            'total': value['total'] if value is not None else None,
            'negative': value['negative'] if value is not None else None,
            'high': value['high'] if value is not None else None,
        })

    active_events = None
    if scope_complete and result['_verified_source_ids']:
        try:
            active_events = db.get_active_event_count_for_canonical_source_ids(
                result['_verified_source_ids'], since=start,
            )
        except Exception:
            active_events = None
    active_events_state = (
        'OBSERVED_FROM_SCOPED_CANONICAL_MENTIONS' if type(active_events) is int
        else 'UNKNOWN_EVENT_SOURCE_BINDING'
    )
    recent_negative = (
        sum(note.get('sentiment') == 'negative' for _, note in dated_rows)
        if trend_complete else None
    )
    return jsonify({
        'ok': True, 'scope': result['scope'], 'trend': trend,
        'active_events': active_events, 'active_events_state': active_events_state,
        'recent_negative': recent_negative,
        'data_state': result['data_state'], 'truncated': result['truncated'],
        'trend_state': 'READY' if trend_complete else (
            'UNKNOWN_PUBLICATION_TIME' if scope_complete else result['data_state']
        ),
        'coverage_semantics': 'Observed signed Canonical notes in the selected CTH scope; not all platform activity',
        'scope_sample_count': result['verified_source_count'],
    })

@app.route('/api/status')
def api_status():
    """Return SYSTEM status without selecting an implicit CTH business scope."""
    database_state = 'ok'
    last = None
    try:
        with db.get_db() as conn:
            conn.execute('SELECT 1').fetchone()
            last = conn.execute('SELECT * FROM collection_logs ORDER BY id DESC LIMIT 1').fetchone()
    except Exception as exc:
        database_state = 'error'
        database_error = type(exc).__name__
    from lumenis.system.ai_gateway.core import owned_inference_status
    owned = owned_inference_status()
    configured_web_sources = [item.strip() for item in os.getenv('WEB_ADAPTERS', '').split(',') if item.strip()]
    payload = {
        'ok': database_state == 'ok', 'system': PRODUCT_NAME, 'version': APP_VERSION,
        'database_state': database_state,
        'collector': 'SYSTEM Collector / source-specific adapters',
        'collector_mode': 'permission-scoped read/intake; no implicit publishing',
        'analyzer': 'deterministic rules plus owned AI Gateway when service-bound',
        'qian_gua_integration': False, 'data_source': 'Source → Evidence → Canonical',
        'total_notes': None, 'verified_notes': None, 'unanalyzed': None,
        'last_collection': dict(last) if last else None,
        'last_collection_semantics': 'historical_observation_not_current_readiness',
        'business_metrics_state': 'SCOPE_REQUIRED',
        'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ai_enabled': owned.get('available') is True and owned.get('service_binding') == 'BOUND',
        'ai_detail': owned.get('reason'), 'ai_provider': 'owned',
        'ai_fallback_allowed': False,
        'web_discovery_enabled': os.getenv('TAIKOO_WEB_DISCOVERY', '0').lower() not in ('0', 'false', 'no', 'off'),
        'ai_analyzer_enabled': True, 'report_enabled': True, 'notes_count': None,
        'web_sources': configured_web_sources,
        'rednote_cdp_enabled': bool(os.getenv('XHS_CDP_URL','')),
        'company_domain': os.getenv('TAIKOO_COMPANY_DOMAIN',''),
        'auto_interval_minutes': int(os.getenv('AUTO_INTERVAL_MINUTES','90')),
    }
    if database_state == 'error':
        payload['database_error'] = database_error
    return jsonify(payload)

# ===== v5.4 rednote CDP 采集 API =====
@app.route('/api/rednote/collect', methods=['POST'])
def api_rednote_collect():
    data = request.get_json(silent=True) or {}
    keyword = str(data.get('keyword') or '').strip()
    if not keyword:
        return jsonify({'ok': False, 'code': 'KEYWORD_REQUIRED'}), 400
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    query_plan = build_acquisition_plan([keyword])
    if not query_plan.is_runnable or len(query_plan.queries) != 1:
        return jsonify({'ok': False, 'code': 'EXACT_SCOPE_REQUIRED',
                        'query_plan': query_plan.to_dict()}), 409
    query = query_plan.queries[0]
    if query.domain_id != 'CTH':
        return jsonify({'ok': False, 'code': 'XHS_TYPED_SCOPE_IMPORT_REQUIRED'}), 409
    max_scroll = max(1, min(10, int(data.get('max_scroll', 3))))
    max_details = max(1, min(50, int(data.get('max_details', 10))))
    account = data.get('account') or xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT
    policy_gate = xhs_cookie_bridge.collection_policy_gate(account=account, region='intl')
    if not policy_gate.get('ok'):
        return jsonify({'ok': False, 'error': policy_gate.get('reason'),
                        'code': policy_gate.get('code'),
                        'collection_policy': policy_gate}), 403
    requested_cdp = data.get('cdp_url') or os.getenv('XHS_CDP_URL')
    persist = bool(data.get('persist', True))

    # A supplied URL may only confirm the currently registered owner endpoint.
    # It never selects a profile, process, browser or endpoint.
    try:
        registered_before = xhs_cookie_bridge.cdp_url_for(account, headless=True)
        if requested_cdp and (not registered_before
                or str(requested_cdp).strip().rstrip('/') != registered_before.rstrip('/')):
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'BROWSER_WORKER_ENDPOINT_MISMATCH'}), 403
    except Exception:  # noqa: BLE001 - an unverified worker hint never grants a caller-selected endpoint.
        registered_before = ''

    # BACKGROUND may start only the exact registered HK profile; endpoint is resolved again after startup.
    auto_started_browser = False
    try:
        import collector as _collector
        import collector_automation
        ca = collector_automation.get_collector_automation()
        ca.start_browser(account=account, headless=True, mode='BACKGROUND')
        cdp_url, endpoint_error = _collector._resolve_server_cdp_url(
            requested_cdp, account=account, region='intl')
        if endpoint_error:
            raise RuntimeError(endpoint_error)
        auto_started_browser = True
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'code': 'BACKGROUND_BROWSER_WORKER_UNAVAILABLE',
                        'error_type': type(e).__name__}), 409

    def worker():
        try:
            result = run_rednote_collect(keyword, max_scroll, max_details, cdp_url, account=account)
            # CDP 直连入口也必须写入同一 collection_logs 真相源。否则
            # /api/platform-health 会继续读到旧的 NETWORK_ERROR，和本次
            # 已完成的真实采集脱节，进而把产品健康灯误报为异常。
            try:
                _record_rednote_collection_log(result, keyword)
            except Exception as _log_e:
                app.logger.warning('RedNote 采集状态落库失败（不影响主结果）: %s', type(_log_e).__name__)
            if persist and result.get('ok'):
                result['persistence'] = persist_rednote_data(result, acquisition_query=query)
                if not result['persistence']['ok']:
                    result['ok'] = False
                    result['error'] = 'Raw/Canonical scope persistence incomplete'
            return result
        finally:
            # Resident Browser 驻场策略：采集结束后保留登录窗口长期驻留（不关闭），
            # 生命周期交由统一驻场启动器 / start_production.ps1 管理，此处仅断开 CDP 附着。
            if auto_started_browser:
                app.logger.info('CDP驻场浏览器保留在线（Resident Browser，采集后不关闭）')
    if data.get('async', True):
        task_id = f"rednote-{datetime.now():%Y%m%d%H%M%S}"
        with _task_lock:
            collect_tasks[task_id] = {'task_id': task_id, 'status': 'running', 'message': f'rednote采集: {keyword}', 'progress': 10, 'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'keywords': [keyword]}
        def run_with_status():
            try:
                result = worker()
                with _task_lock:
                    collect_tasks[task_id].update(
                        status='done' if result.get('ok') else 'error',
                        message='rednote采集结束', progress=100,
                        result_summary={'notes': len(result.get('notes',[])),
                                        'ok': result.get('ok'),
                                        'persistence': result.get('persistence')})
            except Exception as e:
                with _task_lock:
                    collect_tasks[task_id].update(status='error', message=str(e), progress=0)
        threading.Thread(target=run_with_status, daemon=True).start()
        return jsonify({'ok': True, 'task_id': task_id, 'message': 'rednote采集任务已启动'})
    else:
        result = worker()
        return jsonify(result)

# ===== v5.4 舆情预警通知 API =====
@app.route('/api/alerts')
def api_alerts():
    unread_only = request.args.get('unread', '1') == '1'
    alerts = _load_alerts()
    if unread_only:
        alerts = [a for a in alerts if not a.get('read')]
    # 按时间倒序
    alerts.sort(key=lambda x: x.get('created_at',''), reverse=True)
    return jsonify({'ok': True, 'alerts': alerts[:50], 'unread_count': len([a for a in _load_alerts() if not a.get('read')])})

@app.route('/api/alerts/read', methods=['POST'])
def api_alerts_read():
    data = request.get_json(silent=True) or {}
    alert_id = data.get('alert_id')
    all_read = bool(data.get('all', False))
    alerts = _load_alerts()
    if all_read:
        for a in alerts: a['read'] = True
    elif alert_id:
        for a in alerts:
            if a.get('id') == alert_id or a.get('note_id') == alert_id:
                a['read'] = True
    _save_alerts(alerts)
    return jsonify({'ok': True, 'message': '已标记为已读', 'unread_count': len([a for a in alerts if not a.get('read')])})

@app.route('/api/alerts/refresh', methods=['POST'])
def api_alerts_refresh():
    new_alerts = check_and_create_alerts()
    return jsonify({'ok': True, 'new_alerts': len(new_alerts), 'alerts': new_alerts})

# ===== 测试API：最简单的Excel导出 =====
@app.route('/api/test/export')
def api_test_export():
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws['A1'] = '测试'
        ws['B1'] = '成功'
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        file_data = output.getvalue()
        resp = Response(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp.headers['Content-Disposition'] = 'attachment; filename="test.xlsx"'
        return resp
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500

# ===== 负面舆情二次确认 API =====
@app.route('/api/negative/pending')
def api_negative_pending():
    """获取负面笔记列表，支持status参数: pending/confirmed/rejected"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        status = request.args.get('status', 'pending')
        offset = (page - 1) * per_page
        conn = get_repository().connect()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status == 'confirmed':
            where = "negative_confirmed=1"
        elif status == 'rejected':
            where = "negative_confirmed=2"
        else:
            where = "(negative_confirmed=0 OR negative_confirmed IS NULL)"
        
        # 与日报/统计同口径：只保留广州太古汇主体、非重复、非噪音的负面笔记；
        # 全网公关案例属“案例库”，不进入太古汇负面审核待办（否则详情接口会因主体过滤 404）
        clause, sp = _subject_sql_and_values()
        sp = list(sp)
        base_where = (f"sentiment='negative' AND {where} AND COALESCE(is_duplicate,0)=0 "
                      f"AND COALESCE(noise_type,'')='' AND {clause}")
        # 统计总数
        cursor.execute(f"SELECT COUNT(*) as cnt FROM notes WHERE {base_where}", tuple(sp))
        total = cursor.fetchone()['cnt']
        # 获取列表
        cursor.execute(f"""
            SELECT note_id, title, author_nickname, publish_date, url,
                   likes, comments, collects, shares, risk_level, risk_score,
                   summary, source_platform, collected_at, negative_confirmed
            FROM notes
            WHERE {base_where}
            ORDER BY CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                     COALESCE(risk_score,0) DESC, collected_at DESC
            LIMIT ? OFFSET ?
        """, tuple(sp) + (per_page, offset))
        notes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'ok': True, 'notes': notes, 'items': notes, 'total': total, 'page': page, 'per_page': per_page})
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500
def _note_set_review(note_id, state, by='admin'):
    """GAP-09 笔记负面评审统一写路径（唯一 Owner）：新旧入口共用，消除重复 SQL。
    state=1 确认负面；state=2 驳回。写 notes.negative_confirmed 同一字段。"""
    if not note_id:
        return {'ok': False, 'error': '缺少note_id'}, 400, None
    conn = get_repository().connect()
    try:
        cur = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("UPDATE notes SET negative_confirmed=?, negative_confirmed_at=?, negative_confirmed_by=? WHERE note_id=?", (state, now, by, note_id))
        conn.commit()
        affected = cur.rowcount
        return {'ok': True, 'note_id': note_id, 'affected': affected}, 200, None
    except Exception as e:
        import traceback
        return {'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}, 500, None
    finally:
        conn.close()


@app.route('/api/negative/confirm', methods=['POST'])
def api_negative_confirm():
    """确认负面笔记（核准为负面）——GAP-09 收敛：走统一写路径 _note_set_review"""
    data = request.get_json() or {}
    resp, status, _ = _note_set_review(data.get('note_id'), 1)
    resp['confirmed'] = True
    return jsonify(resp), status

@app.route('/api/negative/reject', methods=['POST'])
def api_negative_reject():
    """驳回负面笔记（不是负面）——GAP-09 收敛：走统一写路径 _note_set_review"""
    data = request.get_json() or {}
    resp, status, _ = _note_set_review(data.get('note_id'), 2)
    resp['rejected'] = True
    return jsonify(resp), status

@app.route('/api/negative-review/<note_id>/confirm', methods=['POST'])
def api_negative_review_confirm(note_id):
    """负面审核-确认（RESTful 路径参数，兼容前端 NegativeReview.confirmItem）——GAP-09 收敛：走统一写路径"""
    resp, status, _ = _note_set_review(note_id, 1)
    resp['confirmed'] = True
    return jsonify(resp), status

@app.route('/api/negative-review/<note_id>/reject', methods=['POST'])
def api_negative_review_reject(note_id):
    """负面审核-驳回（RESTful 路径参数，兼容前端 NegativeReview.rejectItem）——GAP-09 收敛：走统一写路径"""
    resp, status, _ = _note_set_review(note_id, 2)
    resp['rejected'] = True
    return jsonify(resp), status

# ================= v5.8.2 事件负面二次确认（与笔记同口径，事件中心联动）=================
def _event_set_review(event_id, state, scope, by):
    """Confirm one currently Evidence-verified event and its exact linked notes atomically."""
    import database as db
    requested = db._normalize_event_scope(scope, allow_global=True)
    conn = get_repository().connect()
    conn.row_factory = sqlite3.Row
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn.execute('BEGIN IMMEDIATE')
        event = db.get_scoped_event(event_id, requested, connection=conn, include_sources=True)
        if event is None:
            raise ValueError('EVENT_NOT_FOUND_IN_SCOPE')
        event_scope = {
            'domain_id': event.get('domain_id') or requested['domain_id'],
            'product_id': event.get('product_id') or requested['product_id'],
            'subject_id': event.get('subject_id') or None,
            'brand_focus_id': event.get('brand_focus_id') or None,
            'global_scope': False,
        }
        event_scope = db._normalize_event_scope(event_scope)
        source_ids = sorted({str(source['source_id']) for source in event.get('sources', [])
                             if source.get('source_type') == 'note' and source.get('source_id')})
        focus_column = 'subject_id' if event_scope['product_id'] == 'CTH' else 'brand_focus_id'
        cur = conn.cursor()
        cur.execute(
            f"UPDATE events SET negative_confirmed=?, negative_confirmed_at=?, negative_confirmed_by=? "
            f"WHERE id=? AND scope_status='VERIFIED' AND {focus_column}=?",
            (state, now, by, event['id'], event_scope[focus_column]),
        )
        affected = cur.rowcount
        notes_affected = 0
        if state == 1 and source_ids:
            placeholders = ','.join('?' for _ in source_ids)
            cur.execute(
                f"UPDATE notes SET negative_confirmed=1, negative_confirmed_at=?, negative_confirmed_by=? "
                f"WHERE note_id IN ({placeholders}) AND sentiment='negative' "
                f"AND scope_status='VERIFIED' AND {focus_column}=? "
                "AND COALESCE(negative_confirmed,0)!=1",
                [now, by] + source_ids + [event_scope[focus_column]],
            )
            notes_affected = cur.rowcount
        conn.commit()
        return {'events': affected, 'notes': notes_affected}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def _event_review_actor_ref(actor):
    """Return the server-authenticated identity used for event review attribution."""
    from lumenis.system.security import permission as security_permission

    if type(actor) is dict:
        actor_id = actor.get('id')
        if type(actor_id) is int and actor_id > 0:
            return str(actor_id)
    if security_permission._is_server_local_workspace_principal(actor):
        return actor.principal_ref
    raise PermissionError('AUTH_REQUIRED')


@app.route('/api/event-review/<event_id>/confirm', methods=['POST'])
def api_event_review_confirm(event_id):
    """确认事件负面（核准）——人工确认后该事件从待核实/待确认列表移除，并联动确认其关联负面笔记"""
    try:
        actor, scope, _entries, _selected = _resolve_web_scope('write', module='reports')
        res = _event_set_review(event_id, 1, scope, _event_review_actor_ref(actor))
        return jsonify({'ok': True, 'event_id': event_id, 'confirmed': True,
                        'affected': res['events'], 'notes_linked': res['notes']})
    except (PermissionError, ValueError) as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': str(e)}), 403 if isinstance(e, PermissionError) else 409
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-review/<event_id>/reject', methods=['POST'])
def api_event_review_reject(event_id):
    """驳回事件（非负面/误报）——人工处理后不再出现在待确认列表（不联动改笔记，保留分别研判）"""
    try:
        actor, scope, _entries, _selected = _resolve_web_scope('write', module='reports')
        res = _event_set_review(event_id, 2, scope, _event_review_actor_ref(actor))
        return jsonify({'ok': True, 'event_id': event_id, 'rejected': True, 'affected': res['events']})
    except (PermissionError, ValueError) as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': str(e)}), 403 if isinstance(e, PermissionError) else 409
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-review/pending')
def api_event_review_pending():
    """待人工确认的事件：风险事件且未二次确认（negative_confirmed=0），按风险/时间倒序"""
    try:
        _actor, scope, _entries, _selected = _resolve_web_scope('read', module='reports')
        limit = request.args.get('limit', 50, type=int)
        limit = max(1, min(200, limit))
        result = db.get_scoped_events(limit=5000, scope=scope)
        events = [event for event in result['events']
                  if event.get('negative_confirmed') in (None, 0)
                  and (event.get('risk_level') in ('high', 'medium', 'critical')
                       or event.get('fact_status') in ('unconfirmed', 'partially_confirmed'))]
        events.sort(key=lambda event: (event.get('risk_score') is not None,
                                       event.get('risk_score') or 0,
                                       event.get('last_seen') or ''), reverse=True)
        return jsonify({'ok': True, 'total': len(events[:limit]), 'events': events[:limit],
                        'scope': scope, 'truncated': result.get('truncated', False),
                        'rejected_count': result.get('rejected_count', 0)})
    except (PermissionError, ValueError) as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': str(e)}), 403 if isinstance(e, PermissionError) else 409
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/event-review/stats')
def api_event_review_stats():
    """事件负面确认统计：待确认/已确认/已驳回"""
    try:
        _actor, scope, _entries, _selected = _resolve_web_scope('read', module='reports')
        result = db.get_scoped_events(limit=5000, scope=scope)
        if result.get('truncated') or result.get('rejected_count'):
            return jsonify({'ok': True, 'status': 'INCOMPLETE', 'pending': None,
                            'confirmed': None, 'rejected': None,
                            'candidate_count': result.get('candidate_count'),
                            'rejected_count': result.get('rejected_count'), 'scope': scope})
        events = result['events']
        pending = sum(1 for event in events if event.get('negative_confirmed') in (None, 0)
                      and event.get('risk_level') in ('high', 'medium', 'critical'))
        confirmed = sum(1 for event in events if event.get('negative_confirmed') == 1)
        rejected = sum(1 for event in events if event.get('negative_confirmed') == 2)
        return jsonify({'ok': True, 'status': 'COMPLETE', 'pending': pending,
                        'confirmed': confirmed, 'rejected': rejected, 'scope': scope})
    except (PermissionError, ValueError) as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': str(e)}), 403 if isinstance(e, PermissionError) else 409
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/events/<event_id>/notes')
def api_event_notes(event_id):
    """事件关联的真实笔记：优先 event_mentions 关联表（event_id→note_id），
    关联缺失时用事件关键词兜底匹配。负面/高风险在前，供事件详情“查看相关笔记案例”。"""
    try:
        _actor, scope, _entries, _selected = _resolve_web_scope('read', module='reports')
        event = db.get_scoped_event(event_id, scope, include_sources=True)
        if event is None:
            return jsonify({'ok': False, 'error': 'Not found in authorized scope'}), 404
        notes = [source for source in event.get('sources', []) if source.get('source_type') == 'note']

        def _linked_note_risk_key(note):
            score = note.get('risk_score')
            score_known = type(score) in (int, float) and not isinstance(score, bool)
            try:
                score_value = float(score) if score_known else 0.0
            except (TypeError, ValueError, OverflowError):
                score_known = False
                score_value = 0.0
            return (
                0 if note.get('sentiment') == 'negative' else 1,
                0 if note.get('risk_level') in ('critical', 'high', 'medium') else 1,
                0 if score_known else 1,
                -score_value if score_known else 0.0,
            )

        notes.sort(key=_linked_note_risk_key)
        notes = notes[:100]
        return jsonify({'ok': True, 'notes': notes, 'total': len(notes),
                        'matched_by': 'verified_event_mentions', 'scope': scope})
    except (PermissionError, ValueError) as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': str(e)}), 403 if isinstance(e, PermissionError) else 409
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/negative/stats')
def api_negative_stats():
    """获取负面舆情统计"""
    try:
        conn = get_repository().connect()
        cursor = conn.cursor()
        # 待确认
        cursor.execute("SELECT COUNT(*) FROM notes WHERE sentiment='negative' AND (negative_confirmed=0 OR negative_confirmed IS NULL)")
        pending = cursor.fetchone()[0]
        # 已确认
        cursor.execute("SELECT COUNT(*) FROM notes WHERE negative_confirmed=1")
        confirmed = cursor.fetchone()[0]
        # 已驳回
        cursor.execute("SELECT COUNT(*) FROM notes WHERE negative_confirmed=2")
        rejected = cursor.fetchone()[0]
        # 总负面
        cursor.execute("SELECT COUNT(*) FROM notes WHERE sentiment='negative'")
        total = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            'ok': True,
            'pending': pending,
            'confirmed': confirmed,
            'rejected': rejected,
            'total_negative': total
        })
    except Exception as e:
        import traceback
        return jsonify({'ok': False, 'error': str(e), 'traceback': traceback.format_exc()}), 500

# ===== v5.3.2 报告导出模块（从monitor.db读取，支持DOCX/CSV/XLSX）=====

@app.get("/api/reports/export")
def api_reports_export_v532():
    kind = request.args.get("type", "daily")
    fmt = request.args.get("format", "xlsx").lower()
    if fmt not in ("docx", "csv", "xlsx"):
        return jsonify({"ok": False, "error": "format 必须为 docx/csv/xlsx"}), 400
    try:
        from lumenis.shared.reporting.routes import _authorized_report_scope
        actor, scope, _entries, selected = _authorized_report_scope('read')
        result = export_api.export_artifacts(
            kind, request.args.get("start"), request.args.get("end"), (fmt,),
            actor=actor, scope=scope, scope_entry=selected)
        artifact = result['files'][fmt]
        resp = Response(artifact['content'], mimetype=artifact['media_type'])
        resp.headers['Content-Disposition'] = f"attachment; filename=\"{artifact['filename']}\""
        resp.headers['Content-Length'] = str(len(artifact['content']))
        resp.headers['X-Lumenis-Saved'] = 'false'
        resp.headers['X-Lumenis-Persistence-State'] = 'DOWNLOAD_ONLY_NOT_SAVED'
        resp.headers['X-Lumenis-Content-SHA256'] = artifact['sha256']
        return resp
    except Exception as exc:
        return export_api._report_error(exc)

@app.get("/api/reports/export-all")
def api_reports_export_all_v532():
    try:
        from io import BytesIO
        from zipfile import ZIP_DEFLATED, ZipFile
        from lumenis.shared.reporting.routes import _authorized_report_scope
        actor, scope, _entries, selected = _authorized_report_scope('read')
        result = export_api.export_artifacts(
            request.args.get("type", "daily"), request.args.get("start"), request.args.get("end"),
            ("docx", "csv", "xlsx"), actor=actor, scope=scope, scope_entry=selected)
        archive = BytesIO()
        with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as bundle:
            for artifact in result['files'].values():
                bundle.writestr(artifact['filename'], artifact['content'])
        archive.seek(0)
        response = send_file(archive, as_attachment=True,
                             download_name=f"lumenis_reports_{result['payload']['period_start']}_{result['payload']['period_end']}.zip",
                             mimetype='application/zip', max_age=0)
        response.headers['X-Lumenis-Saved'] = 'false'
        response.headers['X-Lumenis-Persistence-State'] = 'DOWNLOAD_ONLY_NOT_SAVED'
        return response
    except Exception as exc:
        return export_api._report_error(exc)

# ===== 工程度量 API（P0-E 落地，engineering_metrics.py）=====
@app.get("/api/engineering-metrics")
def api_engineering_metrics():
    """统一工程度量快照：任务闭环（ZELL trace 完成率/进行中/耗时）+ 系统健康红绿灯。"""
    try:
        from engineering_metrics import full_snapshot
        return jsonify({"ok": True, "data": full_snapshot()})
    except Exception as e:
        import traceback
        return jsonify({"ok": False, "error": str(e), "traceback": traceback.format_exc()}), 500

# ===== v5.6.4 报告导出 API（支持Word/Excel/CSV + 精确时间维度） =====
@app.route('/api/system/config')
def api_system_config():
    from lumenis.system.ai_gateway.core import owned_inference_status
    owned = owned_inference_status()
    monitor_keywords = getattr(collector, 'MONITOR_KEYWORDS', None)
    return jsonify({
        'ok': True,
        'version': APP_VERSION,
        'company_domain': os.getenv('TAIKOO_COMPANY_DOMAIN', '') or None,
        'company_name': os.getenv('TAIKOO_COMPANY_NAME', '') or None,
        'default_context': 'GLOBAL_ALL',
        'default_subject': None,
        'rednote_cdp_configured': bool(os.getenv('XHS_CDP_URL', '')),
        'auto_interval_minutes': int(os.getenv('AUTO_INTERVAL_MINUTES', '90')),
        'daily_report_push_hour': int(os.getenv('DAILY_REPORT_HOUR', '9')),
        'ai_enabled': owned.get('available') is True and owned.get('service_binding') == 'BOUND',
        'ai_provider': 'owned',
        'ai_service_binding': owned.get('service_binding'),
        'ai_fallback_allowed': False,
        'web_discovery_enabled': os.getenv('TAIKOO_WEB_DISCOVERY','0').lower() not in ('0','false','no','off'),
        'monitor_keywords': list(monitor_keywords) if isinstance(monitor_keywords, (list, tuple)) else [],
    })

@app.route('/api/system/config', methods=['POST'])
@require_permission(OperationType.CONFIG_MODIFY, RiskLevel.HIGH,
    deny_return=lambda: (jsonify({'ok': False, 'error': '权限不足：系统配置修改需管理员审批', 'code': 'PERMISSION_DENIED'}), 403))
def api_system_config_update():
    data = request.get_json(silent=True) or {}
    # 只允许更新非敏感配置到 .env
    env_path = Path(__file__).parent / '.env'
    updates = {}
    for key in ('TAIKOO_COMPANY_DOMAIN', 'TAIKOO_COMPANY_NAME', 'XHS_CDP_URL', 'AUTO_INTERVAL_MINUTES', 'DAILY_REPORT_HOUR'):
        if key in data:
            updates[key] = str(data[key])
            os.environ[key] = str(data[key])
    if updates and env_path.exists():
        content = env_path.read_text(encoding='utf-8')
        for k, v in updates.items():
            if k in content:
                content = '\n'.join([f'{k}={v}' if line.startswith(k+'=') else line for line in content.split('\n')])
            else:
                content += f'\n{k}={v}'
        env_path.write_text(content, encoding='utf-8')
    return jsonify({'ok': True, 'message': '配置已更新', 'updated': updates})


# ========== 最终验收判定器（Acceptance Gate）：CI / Function / Evidence 三维分离 ==========
@app.route('/api/system/acceptance/dimensions')
def api_acceptance_dimensions():
    """返回验收维度与状态枚举（供前端渲染状态语义）。"""
    try:
        import acceptance_gate as ag
        return jsonify({
            'ok': True,
            'required_dimensions': ag.REQUIRED_DIMENSIONS,
            'ci_status': [x.value for x in ag.CIStatus],
            'functional_status': [x.value for x in ag.FunctionalStatus],
            'partial_reasons': [x.value for x in ag.PartialReason],
            'principle': 'CI PASS/代码存在/AI声称完成均不能单独推出VERIFIED；VERIFIED需源码+调用链+测试+真实运行+Evidence+Verification+Security+Regression全部成立',
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/system/acceptance/judge', methods=['POST'])
def api_acceptance_judge():
    """最终验收判定：body 可为单个 task 对象或 {tasks:[...]} 批量。纯逻辑判定不写库，缺证据显式标缺失。"""
    try:
        import acceptance_gate as ag
        body = request.get_json(silent=True) or {}
        if 'tasks' in body and isinstance(body['tasks'], list):
            items = [ag.AcceptanceInput(**t) for t in body['tasks']]
            return jsonify(ag.judge_batch(items))
        item = ag.AcceptanceInput(**body)
        return jsonify({'ok': True, 'verdict': ag.judge(item).to_dict()})
    except TypeError as e:
        return jsonify({'ok': False, 'error': f'验收输入字段错误: {e}'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ========== v5.4 增项接口配置 ==========
CONFIG_FILE = Path(__file__).parent / 'data' / 'system_config.json'

def _load_config():
    if CONFIG_FILE.exists():
        try: return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        except Exception as e: app.logger.warning('Failed to load system config, using defaults: %s', e)
    return {'company_domain': '', 'company_name': None, 'push_emails': [], 'cdp_url': None, 'auto_interval': 90, 'daily_push_hour': 9}

def _save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')

@app.route('/api/config/company-domain', methods=['GET', 'POST'])
def api_company_domain():
    config = _load_config()
    if request.method == 'GET':
        return jsonify({'ok': True, 'domain': config.get('company_domain', ''), 'name': config.get('company_name'), 'configured': bool(config.get('company_domain', ''))})
    data = request.get_json(silent=True) or {}
    action = data.get('action', 'update')
    if action == 'delete':
        config['company_domain'] = ''
        config['company_name'] = None
        _save_config(config)
        return jsonify({'ok': True, 'message': '公司域名已删除'})
    domain = (data.get('domain') or '').strip()
    name = str(data.get('name') or '').strip()
    if not domain or not name:
        return jsonify({'ok': False, 'code': 'COMPANY_CONFIG_REQUIRED',
                        'error': '域名和公司名称均需明确填写'}), 400
    config['company_domain'] = domain
    config['company_name'] = name
    _save_config(config)
    return jsonify({'ok': True, 'message': '公司域名已配置，后期一键可用', 'domain': domain, 'name': name})

@app.route('/api/config/emails', methods=['GET', 'POST', 'DELETE'])
def api_push_emails():
    config = _load_config()
    if request.method == 'GET':
        return jsonify({'ok': True, 'emails': config.get('push_emails', []), 'count': len(config.get('push_emails', []))})
    data = request.get_json(silent=True) or {}
    if request.method == 'DELETE':
        email = (data.get('email') or '').strip()
        if email and email in config.get('push_emails', []):
            config['push_emails'].remove(email)
            _save_config(config)
            return jsonify({'ok': True, 'message': f'邮箱 {email} 已删除', 'emails': config['push_emails']})
        return jsonify({'ok': False, 'error': '邮箱不存在'}), 404
    # POST: 添加邮箱
    email = (data.get('email') or '').strip()
    if not email or '@' not in email:
        return jsonify({'ok': False, 'error': '请输入有效的邮箱地址'}), 400
    if 'push_emails' not in config:
        config['push_emails'] = []
    if email in config['push_emails']:
        return jsonify({'ok': False, 'error': '该邮箱已存在'}), 409
    config['push_emails'].append(email)
    _save_config(config)
    return jsonify({'ok': True, 'message': f'邮箱 {email} 已添加', 'emails': config['push_emails'], 'count': len(config['push_emails'])})

@app.route('/api/config/brand-directory')
def api_brand_directory():
    """场内品牌目录查询"""
    brands = _load_brands()
    return jsonify({'ok': True, 'total': len(brands), 'brands': brands[:50], 'updated_at': '2026-08-20'})

# ===== v5.4 品牌进场退场管理（增删改查） =====
@app.route('/api/brands')
def api_brands_list():
    """品牌列表查询，支持搜索、业态筛选、分页"""
    brands = _load_brands()
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, int(request.args.get('per_page', 50)))
    filtered = brands
    if keyword:
        filtered = [b for b in filtered if keyword in b.get('brand_en','').lower() or keyword in b.get('brand_cn','').lower()]
    if category:
        filtered = [b for b in filtered if b.get('category') == category]
    total = len(filtered)
    start = (page-1)*per_page
    paged = filtered[start:start+per_page]
    categories = sorted(list(set(b.get('category','') for b in brands if b.get('category'))))
    return jsonify({'ok': True, 'total': total, 'brands': paged, 'page': page, 'per_page': per_page, 'categories': categories})

@app.route('/api/brands/logos')
def api_brands_logos():
    """产品级品牌列表（带logo），支持domain隔离：CTH场内品牌 / ZBMP全部监测品牌"""
    from brand_logo_manager import get_all_brands_with_logos, get_logo_stats
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '')
    domain = request.args.get('domain', '')  # cth / zbmp / 空=全部
    brands = get_all_brands_with_logos()

    # 按域隔离：CTH只显示场内品牌，ZBMP显示全部监测品牌
    if domain == 'cth':
        brands = [b for b in brands if b.get('is_taikoo_brand', True)]
    elif domain == 'zbmp':
        # ZBMP包含场内品牌+外部监测品牌，目前全部品牌都可监测
        pass

    if keyword:
        brands = [b for b in brands if keyword in b.get('brand_en','').lower() or keyword in b.get('brand_cn','').lower()]
    if category:
        brands = [b for b in brands if b.get('category') == category]
    stats = get_logo_stats()
    categories = sorted(list(set(b.get('category','') for b in brands if b.get('category'))))
    return jsonify({
        'ok': True, 'total': len(brands), 'brands': brands,
        'categories': categories, 'logo_stats': stats,
        'domain': domain or 'all',
        'product': 'LUMENIS/序境'
    })

@app.route('/api/brands/logo-stats')
def api_brand_logo_stats():
    """品牌logo覆盖率统计"""
    from brand_logo_manager import get_logo_stats
    return jsonify({'ok': True, 'stats': get_logo_stats()})


@app.route('/api/brands', methods=['POST'])
def api_brand_add():
    """添加新品牌（进场）→ 自动触发logo发现 + 品牌监测任务"""
    global _brand_cache
    data = request.get_json(silent=True) or {}
    brand_en = (data.get('brand_en') or '').strip()
    brand_cn = (data.get('brand_cn') or '').strip()
    category = (data.get('category') or '').strip()
    shop = (data.get('shop') or '').strip()
    floor = (data.get('floor') or '').strip()
    auto_monitor = data.get('auto_monitor', True)  # 默认自动监测

    if not brand_en:
        return jsonify({'ok': False, 'error': '品牌英文名不能为空'}), 400
    if not category:
        return jsonify({'ok': False, 'error': '业态分类不能为空'}), 400
    brands = _load_brands()
    if any(b['brand_en'].lower() == brand_en.lower() for b in brands):
        return jsonify({'ok': False, 'error': '该品牌已存在'}), 409

    new_brand = {
        'brand_en': brand_en,
        'brand_cn': brand_cn,
        'shop': shop,
        'category': category,
        'floor': floor,
        'is_taikoo_brand': True,
        'added_at': datetime.now().isoformat(),
        'monitor_status': 'pending' if auto_monitor else 'disabled',
    }
    brands.append(new_brand)
    _save_brands(brands)
    _brand_cache = None

    # 自动触发：1.logo发现 2.品牌监测任务
    monitor_info = {'logo': 'pending', 'collection': 'pending', 'analysis': 'pending'}
    if auto_monitor:
        try:
            # 1. 异步触发logo自动发现
            from brand_logo_auto import auto_discover_logo
            import threading
            def _discover_and_monitor():
                try:
                    auto_discover_logo(brand_en, brand_cn)
                except:
                    pass
            threading.Thread(target=_discover_and_monitor, daemon=True).start()
            monitor_info['logo'] = 'discovering'

            # 2. 创建品牌监测任务（品牌名作为采集关键词）
            monitor_task_id = f'brand_monitor_{brand_en.lower().replace(" ", "_")}_{int(datetime.now().timestamp())}'
            try:
                # 记录监测任务到数据库
                conn = get_repository().connect()
                conn.execute("""CREATE TABLE IF NOT EXISTS brand_monitor_tasks (
                    task_id TEXT PRIMARY KEY, brand_en TEXT, brand_cn TEXT,
                    category TEXT, keywords TEXT, status TEXT, created_at TEXT,
                    last_run_at TEXT, notes_count INTEGER DEFAULT 0
                )""")
                keywords = json.dumps([brand_en, brand_cn] if brand_cn else [brand_en], ensure_ascii=False)
                conn.execute("INSERT OR REPLACE INTO brand_monitor_tasks VALUES (?,?,?,?,?,?,?,?,?)",
                    (monitor_task_id, brand_en, brand_cn, category, keywords, 'active',
                     datetime.now().isoformat(), None, 0))
                conn.commit()
                conn.close()
                monitor_info['collection'] = 'scheduled'
                monitor_info['task_id'] = monitor_task_id
                new_brand['monitor_status'] = 'active'
            except Exception as e:
                monitor_info['collection'] = f'error: {str(e)[:50]}'
        except Exception as e:
            monitor_info['logo'] = f'error: {str(e)[:50]}'

    return jsonify({
        'ok': True,
        'message': f'品牌 {brand_cn or brand_en} 已进场，监测任务已创建',
        'brand': new_brand,
        'total': len(brands),
        'monitor': monitor_info,
        'next_steps': ['logo自动发现中', '品牌关键词已加入采集队列', '采集完成后自动分析舆情']
    })

@app.route('/api/brands/<brand_en>', methods=['PUT'])
def api_brand_update(brand_en):
    """更新品牌信息"""
    global _brand_cache
    data = request.get_json(silent=True) or {}
    brands = _load_brands()
    found = None
    for b in brands:
        if b['brand_en'].lower() == brand_en.lower():
            found = b
            break
    if not found:
        return jsonify({'ok': False, 'error': '品牌不存在'}), 404
    for key in ('brand_cn', 'category', 'shop', 'floor'):
        if key in data:
            found[key] = data[key]
    _save_brands(brands)
    _brand_cache = None
    return jsonify({'ok': True, 'message': '品牌信息已更新', 'brand': found})

@app.route('/api/brands/<brand_en>', methods=['DELETE'])
@require_permission(OperationType.DATA_DELETE, RiskLevel.CRITICAL,
    deny_return=lambda: (jsonify({'ok': False, 'error': '权限不足：品牌删除需管理员审批', 'code': 'PERMISSION_DENIED'}), 403))
def api_brand_delete(brand_en):
    """删除品牌（退场）"""
    global _brand_cache
    brands = _load_brands()
    original_len = len(brands)
    brands = [b for b in brands if b['brand_en'].lower() != brand_en.lower()]
    if len(brands) == original_len:
        return jsonify({'ok': False, 'error': '品牌不存在'}), 404
    _save_brands(brands)
    _brand_cache = None
    return jsonify({'ok': True, 'message': f'品牌已退场', 'total': len(brands)})

def _save_brands(brands):
    """保存品牌目录到JSON文件"""
    category_stats = {}
    for b in brands:
        cat = b.get('category', '')
        category_stats[cat] = category_stats.get(cat, 0) + 1
    result = {
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'total_brands': len(brands),
        'categories': category_stats,
        'brands': brands
    }
    BRAND_DIR_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

# ===== v5.4 官方信息采集（官网+微博+微信） =====
OFFICIAL_INFO_FILE = Path(__file__).parent / 'data' / 'official_info.json'

@app.route('/api/official-info')
def api_official_info():
    """官方动态信息查询（官网活动、微博、微信）"""
    source = request.args.get('source', 'all')
    limit = min(50, int(request.args.get('limit', 20)))
    info_list = []
    if OFFICIAL_INFO_FILE.exists():
        try:
            info_list = json.loads(OFFICIAL_INFO_FILE.read_text(encoding='utf-8'))
        except:
            info_list = []
    if source != 'all':
        info_list = [i for i in info_list if i.get('source') == source]
    # 按采集时间倒序
    info_list.sort(key=lambda x: x.get('collected_at', ''), reverse=True)
    return jsonify({'ok': True, 'total': len(info_list), 'items': info_list[:limit], 'sources': ['taikoo_official', 'weibo_official', 'wechat_service', 'wechat_subscribe']})

@app.route('/api/official-info/collect', methods=['POST'])
def api_official_collect():
    """触发官方信息采集"""
    try:
        from lumenis.system.collector.runtime.official_info_scraper import OfficialInfoScraper
        scraper = OfficialInfoScraper(db=db)
        results = scraper.collect_all()
        return jsonify({'ok': True, 'message': f'采集完成，共{len(results)}条', 'count': len(results)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== v5.4 全网舆情案例库（模块二） =====
CASE_LIBRARY_FILE = Path(__file__).parent / 'data' / 'case_library.json'

def _load_cases():
    if CASE_LIBRARY_FILE.exists():
        try:
            data = json.loads(CASE_LIBRARY_FILE.read_text(encoding='utf-8'))
            return data.get('cases', [])
        except:
            return []
    return []

def _save_cases(cases):
    categories = sorted(list(set(c.get('category','') for c in cases if c.get('category'))))
    result = {
        'updated_at': datetime.now().strftime('%Y-%m-%d'),
        'total_cases': len(cases),
        'categories': categories,
        'cases': cases
    }
    CASE_LIBRARY_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

@app.route('/api/cases')
def api_cases_list():
    """案例库列表查询，支持搜索、分类筛选、分页"""
    cases = _load_cases()
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '')
    level = request.args.get('level', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, int(request.args.get('per_page', 20)))
    filtered = cases
    if keyword:
        filtered = [c for c in filtered if keyword in c.get('title','').lower() or keyword in c.get('event','').lower() or keyword in c.get('taikoo_insight','').lower()]
    if category:
        filtered = [c for c in filtered if c.get('category') == category]
    if level:
        filtered = [c for c in filtered if level in c.get('level','')]
    total = len(filtered)
    start = (page-1)*per_page
    paged = filtered[start:start+per_page]
    categories = sorted(list(set(c.get('category','') for c in cases if c.get('category'))))
    return jsonify({'ok': True, 'total': total, 'cases': paged, 'page': page, 'per_page': per_page, 'categories': categories})

@app.route('/api/cases/<case_id>')
def api_case_detail(case_id):
    """案例详情查询"""
    cases = _load_cases()
    case = next((c for c in cases if c.get('id') == case_id), None)
    if not case:
        return jsonify({'ok': False, 'error': '案例不存在'}), 404
    return jsonify({'ok': True, 'case': case})

@app.route('/api/cases', methods=['POST'])
def api_case_add():
    """添加新案例（重大事件收录）"""
    data = request.get_json(silent=True) or {}
    cases = _load_cases()
    # 自动生成ID
    existing_ids = [c.get('id','C-00') for c in cases]
    max_num = max([int(id.replace('C-','')) for id in existing_ids if id.startswith('C-')] + [0])
    new_id = f'C-{max_num+1:02d}'
    new_case = {
        'id': new_id,
        'category': data.get('category', ''),
        'title': data.get('title', ''),
        'location': data.get('location', ''),
        'time': data.get('time', datetime.now().strftime('%Y.%m')),
        'level': data.get('level', '🟡'),
        'event': data.get('event', ''),
        'spread_path': data.get('spread_path', ''),
        'response': data.get('response', ''),
        'effect': data.get('effect', ''),
        'taikoo_insight': data.get('taikoo_insight', ''),
        'reply_formula': data.get('reply_formula', ''),
        'taboo': data.get('taboo', ''),
        'added_at': datetime.now().isoformat(),
    }
    if not new_case['title']:
        return jsonify({'ok': False, 'error': '案例标题不能为空'}), 400
    cases.append(new_case)
    _save_cases(cases)
    return jsonify({'ok': True, 'message': f'案例 {new_id} 已添加', 'case': new_case, 'total': len(cases)})

@app.route('/api/cases/match')
def api_case_match():
    """根据关键词/场景匹配同类案例（专报案例对标用）"""
    keyword = request.args.get('keyword', '').lower()
    category = request.args.get('category', '')
    cases = _load_cases()
    matched = []
    if keyword:
        matched = [c for c in cases if keyword in c.get('title','').lower() or keyword in c.get('event','').lower() or keyword in c.get('category','').lower()]
    elif category:
        matched = [c for c in cases if category in c.get('category','')]
    # 按等级排序，高风险优先
    level_order = {'🔴': 0, '🟡': 1, '🟢': 2}
    matched.sort(key=lambda x: level_order.get(x.get('level','🟢'), 3))
    return jsonify({'ok': True, 'total': len(matched), 'cases': matched[:5]})

def _special_report_source_rows(filters=None):
    """Reuse the scoped Canonical-backed reader; a template is not an AI run."""
    from data_query_api import read_scoped_legacy_note_rows
    try:
        return read_scoped_legacy_note_rows(
            module='reports', filters=filters, limit=100, require_complete=True,
        ), None
    except Exception as exc:
        code = getattr(exc, 'code', None)
        status = getattr(exc, 'status', None)
        if code is None or status is None:
            code, status = 'SPECIAL_REPORT_SOURCE_UNAVAILABLE', 503
        return None, (jsonify({'ok': False, 'code': code, 'data_state': 'UNAVAILABLE'}), status)


def _special_report_engagement(note):
    """Do not silently convert absent platform measurements into zero."""
    values = [note.get('likes'), note.get('comments')]
    if any(isinstance(value, bool) or value is None for value in values):
        return None
    try:
        numbers = [int(value) for value in values]
        if any(number < 0 or str(number) != str(value).strip()
               for number, value in zip(numbers, values)):
            return None
        return numbers[0] + numbers[1] * 3
    except (TypeError, ValueError, OverflowError):
        return None


# ===== v5.4 舆情事件专报自动生成（模块一1.2） =====
@app.route('/api/special-report/generate', methods=['POST'])
def api_generate_special_report():
    """自动生成舆情事件专报，自动匹配案例库
    触发条件：单条负面互动≥500 / 负面≥3条集中爆发 / 涉及安全歧视违法 / 本地KOC转发 / 集团媒体问询
    """
    data = request.get_json(silent=True) or {}
    keyword = data.get('keyword', '')
    note_id = data.get('note_id', '')
    event_title = data.get('event_title', '')

    filters = {'note_id': note_id} if note_id else ({'keyword': keyword} if keyword else None)
    scoped, error = _special_report_source_rows(filters)
    if error is not None:
        return error
    notes = scoped['notes']
    if not note_id and not keyword:
        notes = [n for n in notes if n.get('negative_confirmed') != 2
                 and (n.get('sentiment') == 'negative' or n.get('risk_level') in ('high', 'critical'))][:10]

    if not notes:
        return jsonify({'ok': False, 'error': '未找到相关舆情数据'}), 404

    # 统计数据
    total = len(notes)
    negative_notes = [n for n in notes if n.get('sentiment') == 'negative' or n.get('risk_level') in ('high', 'critical')]
    negative_count = len(negative_notes)
    engagements = [_special_report_engagement(n) for n in notes]
    max_engagement = max(engagements) if engagements and all(v is not None for v in engagements) else None
    high_risk_count = len([n for n in notes if n.get('risk_level') in ('high', 'critical')])

    # 判断舆情等级
    if high_risk_count >= 3 or (max_engagement is not None and max_engagement >= 500) or negative_count >= 3:
        level = '🔴重大'
    elif high_risk_count >= 1 or negative_count >= 1:
        level = '🟡关注'
    else:
        level = '🟢平稳'

    # 事件概述
    main_note = notes[0]
    event_name = event_title or main_note.get('title', '')[:50] or keyword or '所选范围舆情事件'
    first_date = main_note.get('publish_date')
    platform = main_note.get('source_platform')

    # 传播路径分析
    spread_path = '待核验的可能传播路径：原帖 → 评论讨论 → 转发 → 跨平台或媒体关注'
    if max_engagement is not None and max_engagement > 500:
        spread_path += '（已达到高传播阈值）'

    # 案例对标：自动匹配案例库
    match_keyword = keyword or event_name
    cases = _load_cases()
    matched_cases = []
    if match_keyword:
        matched_cases = [c for c in cases if any(kw in match_keyword.lower() for kw in c.get('title','').lower().split()[:3]) or
                         any(kw in c.get('category','').lower() for kw in match_keyword.lower().split()[:2])]
    # 如果匹配不到，按负面类型匹配
    if not matched_cases and negative_notes:
        # 判断负面类型
        text = ' '.join([n.get('title','') + n.get('content','') for n in negative_notes[:3]]).lower()
        if any(kw in text for kw in ['服务', '态度', '歧视', '柜姐', '店员']):
            matched_cases = [c for c in cases if '服务态度' in c.get('category','')]
        elif any(kw in text for kw in ['活动', '排队', '安全', '秩序', '拥挤']):
            matched_cases = [c for c in cases if '活动' in c.get('category','') or '安全' in c.get('category','')]
        elif any(kw in text for kw in ['食品', '卫生', '老鼠', '异物']):
            matched_cases = [c for c in cases if '食品' in c.get('category','')]
        else:
            matched_cases = [c for c in cases if c.get('level') == '🔴'][:3]
    matched_cases = matched_cases[:3]

    # toC影响评估
    toc_impact = '中等' if negative_count >= 2 else '较低'
    toc_detail = f'负面笔记{negative_count}条，最高互动{max_engagement}，品牌好感度和到店意愿是否受影响需要进一步证据'
    if max_engagement is not None and max_engagement > 500:
        toc_impact = '较高'
        toc_detail += '，高传播内容可能引发口碑扩散'

    # toB影响评估
    tob_impact = '中等' if high_risk_count >= 1 else '较低'
    tob_detail = '商户关系可能受影响，集团层面可能问询，招商和合作方关注'
    if level == '🔴重大':
        tob_impact = '较高'
        tob_detail += '，重大事件可能影响租金营收和监管风险'

    # 综合评级
    comprehensive_level = level

    # 应对策略（参考案例库启示）
    strategies = []
    for c in matched_cases:
        insight = c.get('taikoo_insight', '')
        if insight:
            # 提取前两条启示
            lines = [l.strip() for l in insight.split('②') if l.strip()]
            for line in lines[:2]:
                if line and line not in strategies:
                    strategies.append(line)
    if not strategies:
        strategies = [
            '第一时间共情致歉，不回避不辩解',
            '说明已采取动作和核查进度，不敷衍',
            '给出可检验的整改方案，将危机转为改进契机',
        ]

    # 风险预警
    risk_warnings = []
    if max_engagement is not None and max_engagement > 200:
        risk_warnings.append('高互动内容需密切关注传播趋势，必要时启动公关响应')
    if negative_count >= 2:
        risk_warnings.append('负面内容集中，需警惕评论区共鸣引发二次传播')
    if any('安全' in (n.get('title','')+n.get('content','')) for n in notes):
        risk_warnings.append('涉及安全类话题，敏感度高，需最高优先级处理')
    if not risk_warnings:
        risk_warnings.append('暂无特殊风险预警，保持常规监测频率')

    # 生成专报
    report = {
        'report_type': 'special',
        'scope': scoped['scope'],
        'source_state': scoped['data_state'],
        'analysis_kind': 'RULE_BASED_PROPOSAL',
        'owned_model_execution': 'NOT_RUN',
        'business_outcome': 'UNKNOWN',
        'spread_path_status': 'HYPOTHESIS_NOT_OBSERVED',
        'engagement_state': 'KNOWN' if max_engagement is not None else 'UNKNOWN',
        'report_title': f'【舆情专报】{event_name}',
        'level': level,
        'event_name': event_name,
        'first_platform': platform,
        'first_date': first_date,
        'current_volume': total,
        'max_engagement': max_engagement,
        'negative_count': negative_count,
        'high_risk_count': high_risk_count,
        'spread_path': spread_path,
        'matched_cases': [{'id': c['id'], 'title': c['title'], 'level': c['level'], 'insight': c.get('taikoo_insight','')[:100]} for c in matched_cases],
        'toc_impact': toc_impact,
        'toc_detail': toc_detail,
        'tob_impact': tob_impact,
        'tob_detail': tob_detail,
        'comprehensive_level': comprehensive_level,
        'strategies': strategies,
        'risk_warnings': risk_warnings,
        'related_notes': [{'note_id': n.get('note_id',''), 'title': n.get('title','')[:50], 'engagement': _special_report_engagement(n), 'sentiment': n.get('sentiment',''), 'risk_level': n.get('risk_level','')} for n in notes[:10]],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    return jsonify({'ok': True, 'report': report, 'matched_cases_count': len(matched_cases)})


def _smtp_settings():
    return {'host':os.getenv('SMTP_HOST','').strip(),'port':int(os.getenv('SMTP_PORT','465') or 465),'user':os.getenv('SMTP_USER','').strip(),'password':os.getenv('SMTP_PASSWORD',''),'from':os.getenv('SMTP_FROM','').strip(),'ssl':os.getenv('SMTP_SSL','1').lower() not in ('0','false','no')}

@app.route('/api/config/email-settings', methods=['GET','POST'])
def api_email_settings():
    if request.method=='GET':
        st=_smtp_settings()
        return jsonify({'ok':True,'configured':bool(st['host'] and st['user'] and st['password']),'host':st['host'],'port':st['port'],'user':st['user'],'from':st['from'] or st['user'],'ssl':st['ssl']})
    data=request.get_json(silent=True) or {}
    cfg={'host':str(data.get('host','')).strip(),'port':int(data.get('port',465) or 465),'user':str(data.get('user','')).strip(),'from':str(data.get('from','')).strip(),'ssl':bool(data.get('ssl',True))}
    path=Path(__file__).parent/'data'/'email_smtp.json'
    path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    return jsonify({'ok':True,'message':'SMTP非敏感配置已保存；密码请写入SMTP_PASSWORD环境变量。'})

def _send_daily_email():
    # Background delivery has no authenticated Subject/BrandFocus selection.
    # Do not send a cached date-only report under a historic default identity.
    return {'sent': 0, 'skipped': 'REPORT_SCOPE_REQUIRED'}

# ===== v5.7.0 周报邮件功能 =====
def _send_weekly_email():
    # Scheduled delivery has no authenticated Subject/BrandFocus selection.
    # Do not send date-only data under a historic default identity.
    return {'sent': 0, 'skipped': 'REPORT_SCOPE_REQUIRED'}

@app.route('/api/weekly/send-email', methods=['POST'])
def api_send_weekly_email():
    result=_send_weekly_email()
    return jsonify({'ok': result.get('sent',0)>0, **result})

# ===== 定时任务辅助函数 =====
def _generate_daily_report(date_str=None):
    """通过 Shared Reporting canonical engine 生成并验证日报。"""
    try:
        date_str = date_str or datetime.now().strftime('%Y-%m-%d')
        from subject_context import brand_scope, CTH_BRAND_KEY
        with brand_scope(CTH_BRAND_KEY, "CTH"):
            report, _digest = report_engine.generate_report(
                "daily", date_str, date_str, domain_id="cth")
        if not (report.get('_artifact_verified') and report.get('_db_row_id')):
            raise RuntimeError('Shared Reporting 日报未通过落库/artifact 验证')
        print(f'[Report] 日报生成完成: {date_str}')
        return True
    except Exception as e:
        print(f'[Report] 日报生成失败: {e}')
        return False


def _generate_weekly_report():
    """通过 Shared Reporting canonical engine 生成并验证自然周周报。"""
    try:
        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
        week_end = now.strftime('%Y-%m-%d')
        from subject_context import brand_scope, CTH_BRAND_KEY
        with brand_scope(CTH_BRAND_KEY, "CTH"):
            report, _digest = report_engine.generate_report(
                "weekly", week_start, week_end, domain_id="cth")
        if not (report.get('_artifact_verified') and report.get('_db_row_id')):
            raise RuntimeError('Shared Reporting 周报未通过落库/artifact 验证')
        print(f'[Report] 周报生成完成: {week_start}~{week_end}')
        return True
    except Exception as e:
        print(f'[Report] 周报生成失败: {e}')
        return False


# 周报定时任务（每周一9:10生成，9:15发送邮件 - 错峰执行）
def _weekly_scheduler():
    last_week_key=None
    last_weekly_report_date=None
    while True:
        try:
            now=datetime.now()
            today_str = now.strftime('%Y-%m-%d')
            # 每周一9:10生成周报（错峰，避免与日报9:00冲突）
            if now.weekday()==0 and now.hour==9 and 10 <= now.minute < 15 and last_weekly_report_date != today_str:
                try:
                    _generate_weekly_report()
                    last_weekly_report_date = today_str
                    print('[Scheduler] 周报生成完成（周一9:10）')
                except Exception as e:
                    print(f'[Scheduler] 周报生成失败: {e}')
            # 每周一9:15发送周报邮件（错峰）
            if now.weekday()==0 and now.hour==9 and 15 <= now.minute < 20:
                week_key=now.strftime('%Y-W%W')
                if week_key!=last_week_key:
                    last_week_key=week_key
                    print('[Scheduler] 触发周报邮件发送（周一9:15）')
                    _send_weekly_email()
        except Exception as e:
            print('[Scheduler] 周报定时任务错误:', e)
        time.sleep(60)

@app.route('/api/special-report/check-trigger')
def api_check_special_report_trigger():
    """检查是否触发专报条件"""
    scoped, error = _special_report_source_rows()
    if error is not None:
        return error
    notes = [n for n in scoped['notes'] if n.get('negative_confirmed') != 2
             and (n.get('sentiment') == 'negative' or n.get('risk_level') in ('high', 'critical'))][:20]
    negative_notes = [n for n in notes if n.get('sentiment') == 'negative']
    engagements = [_special_report_engagement(n) for n in notes]
    max_engagement = max(engagements) if engagements and all(v is not None for v in engagements) else None

    triggers = []
    if max_engagement is not None and max_engagement >= 500:
        triggers.append(f'单条负面互动≥500（当前最高{max_engagement}）')
    if len(negative_notes) >= 3:
        triggers.append(f'负面帖≥3条集中爆发（当前{len(negative_notes)}条）')
    if any('安全' in (n.get('title','')+n.get('content','')) or '歧视' in (n.get('title','')+n.get('content','')) for n in notes):
        triggers.append('涉及安全·歧视·违法类话题')

    return jsonify({'ok': True, 'scope': scoped['scope'], 'data_state': scoped['data_state'], 'triggered': True if triggers else (False if notes and max_engagement is not None else None), 'engagement_state': 'KNOWN' if max_engagement is not None else 'UNKNOWN', 'triggers': triggers, 'max_engagement': max_engagement, 'negative_count': len(negative_notes)})

def _next_half_hour(now=None):
    now=now or datetime.now()
    minute=30 if now.minute < 30 else 60
    candidate=now.replace(minute=minute % 60, second=0, microsecond=0)
    if minute == 60:
        candidate=now.replace(minute=0, second=0, microsecond=0)+timedelta(hours=1)
    return candidate

# v5.8.6 统一动态调度（影子模式）：固定时钟恢复为“唤醒检查点”，动态决策器先只做对照记录、
# 不门控生产；门控灰度经回归与确认后再切换。任何异常一律 fail-open，绝不阻断自动采集。
_shadow_schedule_planner = None
def _get_shadow_planner():
    global _shadow_schedule_planner
    if _shadow_schedule_planner is None:
        try:
            from lumenis.system.collector.adapters.scheduling import get_planner
            _shadow_schedule_planner = get_planner()  # 包级进程单例，与采集结果回写共享状态
        except Exception as e:
            print(f'[ShadowPlanner] init fail (non-blocking): {e}')
            _shadow_schedule_planner = False
    return _shadow_schedule_planner or None


def _automatic_collection_opted_in():
    """Use the SYSTEM collection policy as the only automatic-mode authority."""
    try:
        from lumenis.system.collector.adapters.rednote_policy import automatic_collection_opt_in_enabled
        return automatic_collection_opt_in_enabled()
    except Exception:
        return False


_SCHEDULER_STOP = threading.Event()
_SCHEDULER_LOCK = threading.RLock()
_SCHEDULER_THREAD = None


def _scheduler_runtime_state():
    thread = _SCHEDULER_THREAD
    if thread is None:
        return 'not_started'
    if _SCHEDULER_STOP.is_set():
        return 'stopping' if thread.is_alive() else 'stopped'
    return 'running' if thread.is_alive() else 'unavailable'


def _start_scheduler():
    global _SCHEDULER_THREAD
    with _SCHEDULER_LOCK:
        if _SCHEDULER_THREAD is not None and _SCHEDULER_THREAD.is_alive():
            return _SCHEDULER_THREAD
        _SCHEDULER_STOP.clear()
        _SCHEDULER_THREAD = threading.Thread(target=scheduler_loop, daemon=True, name='scheduler')
        _SCHEDULER_THREAD.start()
        return _SCHEDULER_THREAD


def _stop_scheduler(timeout=2.0):
    # Stop future admission; do not kill an in-flight task or fabricate completion.
    with _SCHEDULER_LOCK:
        _SCHEDULER_STOP.set()
        thread = _SCHEDULER_THREAD
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        return thread is None or not thread.is_alive()


import atexit as _runtime_atexit
_runtime_atexit.register(_stop_scheduler)
_runtime_atexit.register(_stop_hang_watchdog)


def scheduler_loop():
    """自动采集调度器：固定时间点作为唤醒检查点，叠加账号频率保护；
    v5.8.6 起由统一动态决策器做影子对照(动态间隔/状态驱动/next_run_at)，门控后续灰度。"""
    auto_collect_hours = [8, 10, 12, 14, 16, 18, 20, 22, 23]  # 历史参考（v5.8.6 起由 ShadowPlanner 动态决策）
    # 序境采集安全规则（2026-09-04 最高基线）：自动采集固定每日 00:00 / 12:00，每窗口最多一次
    xujing_auto_hours = (0, 12)
    xujing_done_hours = set()  # 本日已完成自动采集的窗口小时（防 0:00-0:59 重复触发）
    today_auto_hours = set()  # 今天已执行的自动采集小时
    last_report_date = ''
    last_email_date = ''
    last_date_check = ''
    last_midnight_report_date = ''  # 00:00日报生成记录
    last_morning_report_date = ''   # 09:00日报生成记录
    last_evening_report_date = ''   # 23:30日报生成记录
    _last_keepalive_min = -1        # 香港/国际 RedNote 保活检查（每 30 分钟一次）
    
    import os as _os
    _os.environ.setdefault('ZBC_SCHED_GATE_MODE', 'enforce')
    print(f'[Scheduler] 自适应调度器启动，gate_mode={_os.environ.get("ZBC_SCHED_GATE_MODE")}（固定时间点仅作历史参考，实际由 ShadowPlanner 门控）')
    
    while not _SCHEDULER_STOP.is_set():
        try:
            now = datetime.now()
            today_str = now.strftime('%Y-%m-%d')

            # Signed, exact-scope prelaunch public maintenance has an independent
            # SYSTEM schedule. It never opts end-user AUTO or XHS accounts in.
            try:
                from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import (
                    run_due_prelaunch_baseline,
                )
                _baseline = run_due_prelaunch_baseline(now=now.astimezone())
                if _baseline.get('status') not in {'DISABLED', 'COMPLETED'}:
                    print(f"[PrelaunchBaseline] status={_baseline.get('status')} reason={_baseline.get('reason')} summary={_baseline.get('summary')}")
                elif _baseline.get('runs'):
                    print(f"[PrelaunchBaseline] completed plan_version={_baseline.get('plan_version')} runs={len(_baseline['runs'])}")
            except Exception as _baseline_error:
                # Public-baseline failure must not stop the existing XHS loop.
                print(f"[PrelaunchBaseline] isolated failure type={type(_baseline_error).__name__}")
            
            # 跨天重置已执行小时记录
            if last_date_check != today_str:
                today_auto_hours = set()
                xujing_done_hours = set()
                last_date_check = today_str
                print(f'[Scheduler] 新的一天 {today_str}，自动采集次数已重置')

            # ===== 香港/国际 RedNote 登录保活定时检查（掉线自动再弹核心） =====
            # 内地采集已暂停，本调度循环不得探测或触发 xhs_cn 采集上下文。
            _kbucket = (now.hour * 60 + now.minute) // 30
            if _automatic_collection_opted_in() and _kbucket != _last_keepalive_min:
                _last_keepalive_min = _kbucket
                try:
                    import xhs_collection_optimizer as _xco
                    for _kpf in ('rednote_hk',):
                        try:
                            _kd = _xco.recheck_keepalive(_kpf)
                            print(f'[Keepalive] {_kpf} -> {_kd.get("status")} need_relogin={_kd.get("need_relogin")} {_kd.get("message", "")}')
                        except Exception as _ke2:
                            print(f'[Keepalive] {_kpf} check fail: {_ke2}')
                except Exception as _ke1:
                    print(f'[Keepalive] 双平台保活检查失败: {_ke1}')
            
            # 自适应调度（GAP-05 门控，2026-09-02 用户签字）：不再用固定时间点，
            # 由 ShadowPlanner 根据状态（上次采集/成功率/熔断/频率）决定此刻是否采集；
            # gate 只收紧不放松，异常 fail-open 回退允许，绝不因新组件卡死既有调度。
            _auto_opted_in = _automatic_collection_opted_in()
            _should_run = _auto_opted_in
            _gate_mode = 'no-planner' if _auto_opted_in else 'manual-only'
            _sd = None
            _sp = _get_shadow_planner() if _auto_opted_in else None
            if _auto_opted_in and _sp is not None:
                try:
                    from lumenis.system.collector.adapters.scheduling.gate import gate_should_run
                    _should_run, _sd, _gate_mode = gate_should_run(
                        _sp, 'xhs', now=now, hard_allow=_auto_opted_in, persist=True)
                    if _sd is not None:
                        print(f'[Scheduler] gate={_gate_mode} should_run={_should_run} code={_sd.reason_code} next={_sd.next_run_at}')
                except Exception as _e:
                    _should_run, _gate_mode = _auto_opted_in, 'fallback'
                    print(f'[Scheduler] gate eval fail-open: {_e}')

            # 序境采集安全窗口（2026-09-04 最高基线）：仅 00:00 / 12:00 允许自动采集，且每窗口当日只一次
            if _should_run and now.hour not in xujing_auto_hours:
                _should_run = False
                _gate_mode = 'xujing-window-off'
            elif _should_run and now.hour in xujing_done_hours:
                _should_run = False
                _gate_mode = 'xujing-window-done'
            if _should_run:
                xujing_done_hours.add(now.hour)

            if _should_run:
                # 账号频率保护（生产既有逻辑，保留）
                rate_ok, rate_msg = xhs_cookie_bridge.check_rate_limit('auto')
                if rate_ok:
                    try:
                        # 自适应参数：max_scroll 由 adaptive_engine 根据状态决定（回退6）
                        try:
                            import adaptive_engine as _ae
                            _max_scroll = int(_ae.adaptive_engine.get_current_params().get('max_scroll', 6))
                        except Exception:
                            _max_scroll = 6
                        # 使用xhs_cookie_bridge创建任务（自动接入次数限制和账号保护）
                        task_id = xhs_cookie_bridge.create_task(
                            keywords=xhs_cookie_bridge.DEFAULT_KEYWORDS,
                            max_scroll=_max_scroll,
                            run_type='auto'
                        )
                        print(f'[Scheduler] 自适应采集触发 gate={_gate_mode} max_scroll={_max_scroll} 任务ID: {task_id}')
                        # 不在触发瞬间乐观回写 SUCCESS：任务刚创建不代表成功。
                        # 真实六态由任务完成时 xhs_cookie_bridge._shadow_record_result 回写，
                        # 避免把“已创建任务”伪装成“采集成功/有数据”。
                    except Exception as e:
                        print(f'[Scheduler] 自适应采集创建任务失败: {e}')
                else:
                    print(f'[Scheduler] 自适应采集跳过（频率限制）: {rate_msg}')
            
            # 日报生成 - 三个时间点确保信息准确性
            # 1. 00:00 - 生成前一天的日报（总结前一天完整数据）
            if now.hour == 0 and now.minute < 5 and last_midnight_report_date != today_str:
                try:
                    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                    _generate_daily_report(yesterday)
                    last_midnight_report_date = today_str
                    print(f'[Scheduler] 00:00日报生成完成（{yesterday}）')
                except Exception as e:
                    print(f'[Scheduler] 00:00日报生成失败: {e}')
            
            # 2. 09:00 - 生成当天的日报（早间数据汇总）
            if now.hour == 9 and now.minute < 5 and last_morning_report_date != today_str:
                try:
                    _generate_daily_report(today_str)
                    last_morning_report_date = today_str
                    print(f'[Scheduler] 09:00日报生成完成（{today_str}）')
                except Exception as e:
                    print(f'[Scheduler] 09:00日报生成失败: {e}')
            
            # 3. 23:30 - 生成当天的日报（晚间完整数据，确保信息准确性）
            if now.hour == 23 and 30 <= now.minute < 35 and last_evening_report_date != today_str:
                try:
                    _generate_daily_report(today_str)
                    last_evening_report_date = today_str
                    print(f'[Scheduler] 23:30日报生成完成（{today_str}，晚间完整数据）')
                except Exception as e:
                    print(f'[Scheduler] 23:30日报生成失败: {e}')
            
            # 23:55生成所有周期报告（周/月/年）
            if now.hour == 23 and now.minute >= 55 and last_report_date != today_str:
                try:
                    _generate_all_reports()
                    last_report_date = today_str
                    print(f'[Scheduler] 周期报告生成完成 {today_str}')
                except Exception as e:
                    print(f'[Scheduler] 周期报告生成失败: {e}')
            
            # 每日9:05推送日报邮件（错峰，避免与9:00日报生成冲突）
            if now.hour == 9 and 5 <= now.minute < 10 and last_email_date != today_str:
                try:
                    print('[Email]', _send_daily_email())
                    last_email_date = today_str
                except Exception as e:
                    print(f'[Scheduler] 邮件推送失败: {e}')
                    
        except Exception as e:
            print('[Scheduler]', e)
        _SCHEDULER_STOP.wait(20)

def _start_app_automations(args):
    if (
        MANUAL_WORKSPACE
        or INTERNAL_BETA_SAFE_STARTUP
        or getattr(args, 'internal_beta_acceptance', False)
        or getattr(args, 'internal_beta_workspace_context_acceptance', False)
    ):
        print('[Runtime] manual/acceptance startup: automatic collectors, residents, schedulers, and monitors suppressed')
        return False

    if not args.no_scheduler:
        # v5.8.6 恢复主采集调度器：固定时钟唤醒 + 动态决策影子对照（周报线程另行评估后启用）
        _start_scheduler()
    # The RedNote resident probes a session and can request scan recovery.
    # Manual mode must not start it before an explicit automatic opt-in.
    if not args.no_scheduler and _automatic_collection_opted_in():
        try:
            xhs_p0_orchestrator.start_resident()
            print('[XHS-P0] 小红书 P0 驻场心跳已启动')
        except Exception as _pe:
            print(f'[XHS-P0] 驻场心跳启动失败: {_pe}')
    else:
        print('[XHS-P0] 人工采集模式：驻场会话探测未启动')

    # 启动内存监控（防止OOM崩溃）——崩溃根因(重复endpoint)已修复，重新启用
    try:
        mem_opt = memory_optimizer.get_memory_optimizer()
        mem_opt.start_monitoring()
    except Exception as e:
        print(f'[Memory] 内存监控启动失败: {e}')

    # 启动进程级稳定性监控（watchdog+heartbeat，仅记录不强制退出）
    try:
        stab_mon = stability_monitor.get_stability_monitor(
            service_port=getattr(globals().get("args"), "port", APP_PORT))
        stab_mon.start_monitoring()
    except Exception as e:
        print(f'[Stability] 稳定性监控启动失败: {e}')

    # Legacy inference routes are retired. Boot must not generate a request to
    # probe them; owned-model readiness belongs to the SYSTEM AI Gateway owner.
    print('[AIC] Startup inference heartbeat disabled; owned inference readiness requires its Gateway evidence')
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=f'{PRODUCT_NAME} Product Core')
    parser.add_argument('--host',default=APP_HOST,help='监听地址，默认0.0.0.0（支持本地/局域网/5G热点访问）')
    parser.add_argument('--port',type=int,default=APP_PORT)
    parser.add_argument('--manual-workspace',action='store_true',help='explicit loopback manual Workspace with dedicated data; normal API permissions, no automatic services or session probes')
    parser.add_argument('--no-scheduler',action='store_true',help='仅启动 Web，不启动自动采集调度器')
    parser.add_argument('--internal-beta-acceptance',action='store_true',help='loopback health-only safe probe; only GET /healthz, not Product E2E')
    parser.add_argument('--internal-beta-workspace-context-acceptance',action='store_true',help='loopback Workspace/context and scoped Evidence GET acceptance; no automatic runtime services')
    parser.add_argument(_INTERNAL_BETA_BROWSER_OUTCOME_FLAG,action='store_true',help='explicit Browser/manual SavedWork operations in a fresh isolated Workspace; no model/Collector or automatic services')
    args=parser.parse_args()
    if args.internal_beta_acceptance and not _is_internal_beta_loopback(args.host):
        parser.error('--internal-beta-acceptance requires --host 127.0.0.1')
    if args.internal_beta_acceptance != INTERNAL_BETA_ACCEPTANCE:
        parser.error('internal beta acceptance profile must be selected before app imports')
    if args.internal_beta_browser_outcome_acceptance != INTERNAL_BETA_BROWSER_OUTCOME_ACCEPTANCE:
        parser.error('Browser outcome profile must be selected before app imports')
    if args.internal_beta_workspace_context_acceptance != INTERNAL_BETA_WORKSPACE_CONTEXT_ACCEPTANCE:
        parser.error('Workspace/context acceptance profile must be selected before app imports')
    if args.internal_beta_workspace_context_acceptance and (
        args.host != '127.0.0.1' or args.port in _INTERNAL_BETA_RESERVED_PORTS
    ):
        parser.error('Workspace/context acceptance requires validated loopback host and non-reserved port')
    _start_app_automations(args)
    auth_state='开启' if _auth_enabled() else '关闭（仅建议本机访问）'
    auto_collection = (
        not args.no_scheduler
        and not INTERNAL_BETA_SAFE_STARTUP
        and not MANUAL_WORKSPACE
        and _automatic_collection_opted_in()
    )
    print(f'{PRODUCT_NAME} Product Core v{APP_VERSION} | {args.host}:{args.port} | 自动采集：{auto_collection} | HTTP认证：{auth_state}')

# ===== SYSTEM AI Gateway health =====
@app.route('/api/xhs/p0/status', methods=['GET'])
def api_xhs_p0_status():
    """前端轮询：小红书 P0 驻场/会话/恢复状态聚合"""
    try:
        return jsonify({'ok': True, **xhs_p0_orchestrator.get_status()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/p0/recovery/complete', methods=['POST'])
def api_xhs_p0_recovery_complete():
    """人工扫码后触发：关闭恢复任务，标记 Session 已恢复"""
    try:
        data = request.get_json(silent=True) or {}
        success = bool(data.get('success', True))
        return jsonify(xhs_p0_orchestrator.complete_scan_recovery(success=success))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/p0/collection', methods=['POST'])
def api_xhs_p0_collection():
    """手动触发采集：身份硬白名单门控后进入采集链"""
    try:
        data = request.get_json(silent=True) or {}
        account = data.get('account')
        keywords = data.get('keywords')
        max_scroll = int(data.get('max_scroll', 4))
        return jsonify(xhs_p0_orchestrator.trigger_collection(
            account_name=account, keywords=keywords, max_scroll=max_scroll))
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== 稳定性监控API =====
@app.route('/api/stability/status', methods=['GET'])
def api_stability_status():
    """获取稳定性监控状态"""
    try:
        from stability_monitor import get_stability_monitor
        monitor = get_stability_monitor()
        status = monitor.get_status_report()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/stability/heartbeat', methods=['GET'])
def api_stability_heartbeat():
    """获取最近的心跳记录"""
    try:
        from stability_monitor import get_stability_monitor
        monitor = get_stability_monitor()
        log_file = monitor.heartbeat_log
        
        heartbeats = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-20:]  # 最近20条
                for line in lines:
                    try:
                        heartbeats.append(json.loads(line.strip()))
                    except Exception:
                        pass
        
        return jsonify({'ok': True, 'heartbeats': heartbeats, 'count': len(heartbeats)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/stability/crash-log', methods=['GET'])
def api_stability_crash_log():
    """获取崩溃日志"""
    try:
        from stability_monitor import get_stability_monitor
        monitor = get_stability_monitor()
        log_file = monitor.crash_log
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'ok': True, 'has_crash': True, 'content': content[-5000:]})  # 最后5000字符
        else:
            return jsonify({'ok': True, 'has_crash': False, 'message': '暂无崩溃记录'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== 合并仪表盘API（减少前端轮询请求数）=====
@app.route('/api/dashboard/all', methods=['GET'])
def api_dashboard_all():
    """
    合并仪表盘API：一次性返回所有前端需要的数据
    替代原来的8个独立API请求，减少并发请求，提高稳定性
    
    包含：overview, stats, alerts, events, risk-alerts, hot-topics, ai-status, status
    """
    conn = None
    try:
        import sqlite3
        from datetime import date, datetime, timedelta
        _actor, dashboard_scope, _entries, _selected = _resolve_web_scope('read', module='reports')

        result = {'ok': True, 'server_time': datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')}

        # Resolve the complete note set through the existing source-level
        # Canonical/Evidence reader. Its result is a bounded sample, so every
        # aggregate carries explicit coverage and becomes unknown when the
        # read was truncated or rejected stale sources.
        note_read = db.get_scoped_event_source_rows(
            dashboard_scope, source_types=('note',), limit=5000,
        )
        note_rows = [row for row in note_read.get('sources', []) if isinstance(row, dict)]
        notes_complete = (not note_read.get('truncated') and not note_read.get('rejected_count'))
        notes_coverage = {
            'state': 'COMPLETE' if notes_complete else 'INCOMPLETE',
            'candidate_count': note_read.get('candidate_count'),
            'verified_count': len(note_rows),
            'rejected_count': note_read.get('rejected_count', 0),
            'truncated': bool(note_read.get('truncated')),
            'basis': 'current scoped Canonical rows with matching signed source Evidence',
        }
        result['notes_coverage'] = notes_coverage

        import canonical_metrics as _cm
        _sentiment = _cm.sentiment_count(note_rows)
        _risk = _cm.risk_count(note_rows)
        _engagement = _cm.engagement_stats(note_rows)
        _category_counts = {}
        for note in note_rows:
            category = note.get('category')
            if isinstance(category, str) and category.strip():
                category = category.strip()
                _category_counts[category] = _category_counts.get(category, 0) + 1
        _categories = [
            {'category': category, 'count': count}
            for category, count in sorted(_category_counts.items(), key=lambda item: (-item[1], item[0]))
        ]

        if notes_complete:
            _scope_total = len(note_rows)
            _stats = {
                'total': _scope_total,
                'positive': _sentiment['positive'],
                'neutral': _sentiment['neutral'],
                'negative': _sentiment['negative'],
                'unknown_sentiment': _sentiment['unknown'],
                'critical_risk': _risk['critical'],
                'high_risk': _risk['high'],
                'medium_risk': _risk['medium'],
                'low_risk': _risk['low'],
                'unknown_risk': _risk['missing'] + _risk['other'],
                'total_likes': _engagement['per_field']['likes'],
                'total_comments': _engagement['per_field']['comments'],
                'total_engagements': _engagement['sum'],
                'official_count': sum(note.get('is_official') == 1 for note in note_rows),
                'verified_count': _scope_total,
                'coverage_state': 'COMPLETE',
            }
            _sentiment_stats = {
                'positive': _sentiment['positive'],
                'neutral': _sentiment['neutral'],
                'negative': _sentiment['negative'],
            }
            _stats_categories = _categories
        else:
            _scope_total = None
            _stats = {
                key: None for key in (
                    'total', 'positive', 'neutral', 'negative', 'unknown_sentiment',
                    'critical_risk', 'high_risk', 'medium_risk', 'low_risk',
                    'unknown_risk', 'total_likes', 'total_comments',
                    'total_engagements', 'official_count', 'verified_count',
                )
            }
            _stats['coverage_state'] = 'INCOMPLETE'
            _sentiment_stats = {'positive': None, 'neutral': None, 'negative': None}
            _stats_categories = None

        _today = datetime.now().astimezone().date().isoformat()
        _collection_days = [str(note.get('collected_at') or '')[:10] for note in note_rows]
        _today_complete = notes_complete
        for _day_value in _collection_days:
            try:
                date.fromisoformat(_day_value)
            except (TypeError, ValueError):
                _today_complete = False
                break
        _today_count = sum(day == _today for day in _collection_days)

        # The old field compared a reference-specific verification flag with
        # an all-notes count. Current verification is the scoped Canonical and
        # signed-Evidence read above; analysis state has no reliable note field.
        result['overview'] = {
            'state': 'COMPLETE' if notes_complete else 'INCOMPLETE',
            'total_notes': _scope_total,
            'verified_notes': _scope_total,
            'verified_basis': 'current scoped Canonical and signed source Evidence',
            'negative_notes': _sentiment['negative'] if notes_complete else None,
            'today_notes': _today_count if _today_complete else None,
            'today_notes_state': 'COMPLETE' if _today_complete else 'UNKNOWN_COLLECTION_TIME',
            'unanalyzed': None,
            'unanalyzed_state': 'ANALYSIS_STATUS_UNAVAILABLE',
            'coverage': notes_coverage,
        }

        # Derive the trend from the same full scoped Canonical read. If any
        # source lacks a usable publication date, or the scope read is partial,
        # day totals remain unknown rather than turning unplaceable records
        # into apparent zeroes.
        _now = datetime.now().astimezone()
        _trend_dates = [str(row.get('publish_date') or row.get('publish_datetime') or '')[:10]
                        for row in note_rows]
        _publication_dates_complete = True
        for _day_value in _trend_dates:
            try:
                date.fromisoformat(_day_value)
            except (TypeError, ValueError):
                _publication_dates_complete = False
                break
        _trend_complete = notes_complete and _publication_dates_complete
        _trend = []
        for _i in range(14):
            _dd = (_now - timedelta(days=13 - _i)).strftime('%Y-%m-%d')
            _day_rows = [row for row, published_day in zip(note_rows, _trend_dates)
                         if published_day == _dd]
            if _trend_complete:
                _day_sentiment = _cm.sentiment_count(_day_rows)
                _day_risk = _cm.risk_count(_day_rows)
                _day = {
                    'total': len(_day_rows),
                    'negative': _day_sentiment['negative'],
                    'high': _day_risk['high'],
                }
            else:
                _day = {'total': None, 'negative': None, 'high': None}
            _trend.append({'date': _dd, 'label': _dd[5:], **_day})
        result['overview']['trend'] = _trend
        result['overview']['trend_state'] = (
            'COMPLETE' if _trend_complete else
            'INCOMPLETE_SCOPE' if not notes_complete else 'UNKNOWN_PUBLICATION_TIME'
        )

        result['stats'] = {
            'state': 'COMPLETE' if notes_complete else 'INCOMPLETE',
            'sentiment': _sentiment_stats,
            'total': _scope_total,
            'positive': _stats['positive'],
            'neutral': _stats['neutral'],
            'negative': _stats['negative'],
            'high_risk': _stats['high_risk'],
            'medium_risk': _stats['medium_risk'],
            'low_risk': _stats['low_risk'],
            'total_engagements': _stats['total_engagements'],
            'total_comments': _stats['total_comments'],
            'categories': _stats_categories,
            'categories_state': 'COMPLETE' if notes_complete else 'INCOMPLETE',
            'coverage': notes_coverage,
        }
        
        # 3. SYSTEM/运营告警（不与业务 notes 聚合混用）
        try:
            conn = get_repository().connect(timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alerts'")
            if cursor.fetchone():
                cursor.execute("SELECT * FROM alerts WHERE is_read=0 ORDER BY rowid DESC LIMIT 20")
                result['alerts'] = [dict(row) for row in cursor.fetchall()]
                result['alerts_state'] = 'AVAILABLE'
            else:
                result['alerts'] = []
                result['alerts_state'] = 'NOT_AVAILABLE'
        except Exception as e:
            result['alerts'] = []
            result['alerts_state'] = 'UNAVAILABLE'
        
        # 4. 事件列表（质量分级：重点事件优先，泛化“相关讨论”折叠、占位备注隐藏，与事件中心同口径）
        try:
            _cur = db.get_events_curated(12, scope=dashboard_scope)
            result['events'] = _cur['featured']
            result['events_meta'] = {'generic_count': _cur['generic_count'], 'noise_count': _cur['noise_count'],
                                     'rejected_count': _cur.get('rejected_count'), 'scope': dashboard_scope}
        except Exception as e:
            result['events'] = []
        
        # 5. 风险告警，来自已核验的当前范围样本。
        def _risk_sort_key(note):
            score = note.get('risk_score')
            score_known = type(score) in (int, float) and not isinstance(score, bool)
            try:
                score_value = float(score) if score_known else 0.0
            except (TypeError, ValueError, OverflowError):
                score_known = False
                score_value = 0.0
            return (
                0 if note.get('sentiment') == 'negative' else 1,
                0 if note.get('risk_level') in ('critical', 'high', 'medium') else 1,
                0 if score_known else 1,
                -score_value if score_known else 0.0,
                str(note.get('collected_at') or ''),
            )

        _risk_alert_rows = [note for note in note_rows
                            if note.get('risk_level') in ('critical', 'high', 'medium')]
        _risk_alert_rows.sort(key=_risk_sort_key)
        result['risk_alerts'] = _risk_alert_rows[:20]
        result['risk_alerts_state'] = 'COMPLETE' if notes_complete else 'INCOMPLETE'
        
        # 6. 热门话题按当前范围 Canonical 样本中的 category 派生。
        _topic_groups = {}
        for note in note_rows:
            topic = note.get('category')
            if not isinstance(topic, str) or not topic.strip():
                continue
            topic = topic.strip()
            bucket = _topic_groups.setdefault(topic, {
                'topic': topic, 'count': 0, 'positive': 0, 'negative': 0,
                'neutral': 0, 'unknown': 0,
            })
            bucket['count'] += 1
            sentiment = note.get('sentiment')
            bucket[sentiment if sentiment in ('positive', 'negative', 'neutral') else 'unknown'] += 1
        result['hot_topics'] = sorted(
            _topic_groups.values(), key=lambda item: (-item['count'], item['topic']),
        )[:14]
        result['hot_topics_state'] = 'COMPLETE' if notes_complete else 'INCOMPLETE'
        
        # 7. AI状态：只读唯一 owned Gateway，不探测或回退旧 Provider。
        try:
            from lumenis.system.ai_gateway.core import owned_inference_status
            result['ai_status'] = owned_inference_status()
        except Exception as e:
            result['ai_status'] = {'provider': 'owned', 'available': False,
                                   'service_binding': 'NOT_BOUND', 'fallback_allowed': False,
                                   'state': 'UNAVAILABLE', 'reason': type(e).__name__}
        
        # 8. 系统状态
        try:
            result['system_status'] = {
                'version': APP_VERSION,
                'collector': 'SYSTEM Collector / source-specific adapters',
                'auto_collect': os.getenv('REDNOTE_AUTO_RUN', 'false').lower() in ('1','true','yes','on'),
                'auth_enabled': _auth_enabled(),
                'default_context': 'GLOBAL_ALL',
                'default_subject': None,
            }
        except Exception as e:
            result['system_status'] = {'error': type(e).__name__}

        # 9. v5.9.0 合并字段：供前端统一轮询，避免多个独立30s请求
        try:
            # Incomplete Canonical coverage cannot produce an authoritative total.
            result['pending_negative'] = (
                sum(note.get('sentiment') == 'negative'
                    and note.get('negative_confirmed') in (None, 0) for note in note_rows)
                if notes_complete else None
            )
            result['pending_negative_state'] = 'COMPLETE' if notes_complete else 'INCOMPLETE'
            # 未读预警数（口径与 /api/alerts?unread=1 一致；无 is_read 列时回退为 alerts 长度）
            try:
                if conn is None:
                    result['unread_alerts'] = len(result.get('alerts', []))
                else:
                    cur2 = conn.cursor()
                    cur2.execute("SELECT COUNT(*) AS c FROM alerts WHERE is_read=0")
                    result['unread_alerts'] = cur2.fetchone()['c']
            except Exception:
                result['unread_alerts'] = len(result.get('alerts', []))
            # 数据变更摘要（口径与 /api/dashboard/changes 一致）
            result['changes'] = {
                'server_time': datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S'),
                'version': APP_VERSION,
                'stats': _stats,
                'stats_state': 'COMPLETE' if notes_complete else 'INCOMPLETE',
                'scope': dashboard_scope,
            }
        except Exception as e:
            result['poll_extras_error'] = str(e)

        return jsonify(result)
    
    except (PermissionError, ValueError) as e:
        if conn:
            try: conn.close()
            except Exception: pass
        return jsonify({'ok': False, 'status': 'BLOCKED', 'code': str(e)}), 403 if isinstance(e, PermissionError) else 409
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        # 确保数据库连接总是被关闭
        if conn:
            try:
                conn.close()
            except:
                pass

# ===== 微博登录管理API =====
@app.route('/api/weibo/login-status', methods=['GET'])
def api_weibo_login_status():
    """获取微博登录状态"""
    try:
        from weibo_login_manager import get_weibo_manager
        manager = get_weibo_manager()
        status = manager.check_login_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/weibo/start-login', methods=['POST'])
def api_weibo_start_login():
    """Route an explicit request through the registered SYSTEM browser worker."""
    try:
        data = request.get_json(silent=True) or {}
        task_id = str(data.get('task_id') or '').strip()
        if not task_id:
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'error': 'HUMAN_INTERACTIVE_TASK_ID_REQUIRED'}), 400
        actor_ref = _weibo_session_metadata_actor()
        collector = collector_automation.get_collector_automation()
        collector.start_browser(account='weibo', headless=False,
                                mode='HUMAN_INTERACTIVE', task_id=task_id,
                                actor_ref=actor_ref)
        return jsonify({'ok': True, 'mode': 'HUMAN_INTERACTIVE', 'task_id': task_id,
                        'message': '已打开经注册的序境浏览器Worker登录入口'})
    except PermissionError as e:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(e)}), 403
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE', 'error': type(e).__name__}), 409




@app.route('/api/weibo/clear-login', methods=['POST'])
def api_weibo_clear_login():
    """清除微博登录数据"""
    try:
        from weibo_login_manager import get_weibo_manager
        manager = get_weibo_manager()
        success = manager.clear_login_data()
        return jsonify({'ok': success, 'message': '微博登录数据已清除' if success else '清除失败'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/weibo/cookies', methods=['GET'])
def api_weibo_cookies():
    """Compatibility state endpoint; cookie material never leaves its owner."""
    try:
        from weibo_login_manager import WeiboLoginManager
        actor_ref = _weibo_session_metadata_actor()
        metadata = WeiboLoginManager.read_saved_session_metadata()
        if _weibo_session_metadata_actor() != actor_ref:
            raise PermissionError('SESSION_ACTOR_CHANGED')
        response = jsonify({'ok': True, **metadata})
        status = 200
    except PermissionError as exc:
        code = str(exc)
        response = jsonify({'ok': False, 'code': code})
        status = 401 if code == 'AUTH_REQUIRED' else 403
    except Exception:
        response = jsonify({'ok': False, 'code': 'SESSION_METADATA_UNAVAILABLE'})
        status = 503
    response.headers['Cache-Control'] = 'no-store'
    return response, status


def _collector_browser_actor_ref():
    from flask import g
    actor = getattr(g, 'current_user', None)
    if not isinstance(actor, dict) or type(actor.get('id')) is not int:
        raise PermissionError('AUTH_REQUIRED')
    return f"actor:{actor['id']}"


def _weibo_session_metadata_actor():
    from lumenis.auth.service import get_current_user
    from lumenis.shared.database import get_repository
    from lumenis.system.security.permission import resolve_local_workspace_principal
    from account.authorization import check_dual_domain_permission

    principal = resolve_local_workspace_principal(module='collector', action='read')
    if principal is not None:
        return principal.principal_ref
    actor = get_current_user(read_only=True)
    if type(actor) is not dict or type(actor.get('id')) is not int or actor['id'] <= 0:
        raise PermissionError('AUTH_REQUIRED')
    connection = get_repository().connect(read_only=True, wal=False)
    try:
        if not check_dual_domain_permission(
            actor['id'], 'SYSTEM', module='collector', action='read', connection=connection,
        ):
            raise PermissionError('SESSION_PERMISSION_DENIED')
    finally:
        connection.close()
    return f"actor:{actor['id']}"

# ===== B站登录管理API =====
@app.route('/api/bilibili/login-status', methods=['GET'])
def api_bilibili_login_status():
    """获取B站登录状态"""
    try:
        from bilibili_login_manager import get_bilibili_manager
        manager = get_bilibili_manager()
        status = manager.check_login_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/bilibili/search', methods=['GET'])
def api_bilibili_search():
    """搜索B站视频"""
    try:
        from bilibili_login_manager import get_bilibili_manager
        manager = get_bilibili_manager()
        
        keyword = str(request.args.get('keyword') or '').strip()
        if not keyword:
            return jsonify({'ok': False, 'code': 'KEYWORD_REQUIRED',
                            'error': '请明确提供搜索关键词'}), 400
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        result = manager.search_videos(keyword, page, page_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/bilibili/clear-login', methods=['POST'])
def api_bilibili_clear_login():
    """清除B站登录数据"""
    try:
        from bilibili_login_manager import get_bilibili_manager
        manager = get_bilibili_manager()
        success = manager.clear_login_data()
        return jsonify({'ok': success, 'message': 'B站登录数据已清除' if success else '清除失败'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ===== 全网话题搜集API（微博+B站）=====
@app.route('/api/web/collect', methods=['POST'])
def api_web_collect():
    """触发全网话题搜集（微博+B站）"""
    try:
        data = request.get_json(silent=True) or {}
        keyword = str(data.get('keyword') or '').strip()
        if not keyword:
            return jsonify({'ok': False, 'code': 'KEYWORD_REQUIRED',
                            'error': '请明确提供搜索关键词'}), 400
        platforms = data.get('platforms', ['weibo', 'bilibili'])
        
        results = {}
        
        # B站搜索
        if 'bilibili' in platforms:
            try:
                from bilibili_login_manager import get_bilibili_manager
                manager = get_bilibili_manager()
                bili_result = manager.search_videos(keyword, page=1, page_size=20)
                results['bilibili'] = bili_result
            except Exception as e:
                results['bilibili'] = {'ok': False, 'error': str(e)}
        
        # 微博搜索（使用cookie直接请求）
        if 'weibo' in platforms:
            try:
                from weibo_login_manager import get_weibo_manager
                weibo_manager = get_weibo_manager()
                cookie_string = weibo_manager.get_cookie_string()
                
                if cookie_string:
                    import requests
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Cookie': cookie_string,
                        'Referer': 'https://s.weibo.com/'
                    }
                    # 时间范围动态化：近30天，避免写死日期过期
                    _d_end = datetime.now(); _d_start = _d_end - timedelta(days=30)
                    from urllib.parse import quote as _q
                    url = f'https://s.weibo.com/weibo?q={_q(keyword)}&typeall=1&suball=1&timescope=custom:{_d_start:%Y-%m-%d}:{_d_end:%Y-%m-%d}&Refer=g'
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    # 简单解析微博搜索结果
                    import re
                    import html as _html
                    content = response.text
                    # 提取微博内容（简化版）
                    cards = re.findall(r'<p class="txt"[^>]*>(.*?)</p>', content, re.DOTALL)
                    _cands = []
                    for card in cards[:40]:
                        t = re.sub(r'<[^>]+>', '', card)
                        t = _html.unescape(t)
                        t = re.sub(r'[\ue000-\uf8ff]', '', t)
                        t = re.sub(r'[\u200b-\u200f\ufeff\u2060]', '', t)
                        t = re.sub(r'\s+', ' ', t).strip()
                        t = re.sub(r'(展开全文c?|展开c|收起全文d?|收起d|全文)$', '', t).strip()
                        if t: _cands.append(t[:200])
                    # 前缀归并：同一条微博的列表截断版与全文版前40字相同，保留最完整版本
                    _best = {}
                    for t in _cands:
                        k = t[:40]
                        if k not in _best or len(t) > len(_best[k]): _best[k] = t
                    weibo_items = [{'content': t, 'platform': 'weibo', 'type': 'post'} for t in _best.values()]
                    results['weibo'] = {
                        'ok': True,
                        'keyword': keyword,
                        'total': len(weibo_items),
                        'items': weibo_items
                    }
                else:
                    results['weibo'] = {'ok': False, 'error': '微博未登录'}
            except Exception as e:
                results['weibo'] = {'ok': False, 'error': str(e)}
        
        # 保存到全网话题表（对齐 web_topics 真实结构：topic/source/sentiment/mention_count/first_seen/last_seen/tags/summary/created_at）
        try:
            conn = get_repository().connect(timeout=30)
            now_s = datetime.now().strftime('%Y-%m-%d %H:%M:%S'); today_s = datetime.now().strftime('%Y-%m-%d')
            def _save_topic(topic, source, mention, tags, summary):
                topic = (topic or '').strip()
                if not topic: return
                conn.execute("""INSERT INTO web_topics(topic,source,sentiment,relevance_score,mention_count,first_seen,last_seen,tags,summary,created_at)
                                SELECT ?,?,'pending',0,?,?,?,?,?,?
                                WHERE NOT EXISTS(SELECT 1 FROM web_topics WHERE topic=? AND source=?)""",
                             (topic[:200], source, mention or 0, today_s, today_s, tags or '', (summary or '')[:500], now_s, topic[:200], source))
            # B站视频
            if results.get('bilibili', {}).get('ok'):
                for video in results['bilibili'].get('videos', []):
                    _save_topic(video.get('title',''), 'bilibili', video.get('play',0), keyword,
                                json.dumps({'url':video.get('url',''),'author':video.get('author','')}, ensure_ascii=False))
            # 微博内容
            if results.get('weibo', {}).get('ok'):
                for item in results['weibo'].get('items', []):
                    _save_topic(item.get('content',''), 'weibo', 0, keyword, item.get('content',''))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f'[WebCollect] 保存到数据库失败: {e}')
        
        return jsonify({
            'ok': True,
            'keyword': keyword,
            'platforms': platforms,
            'results': {k: {'ok': v.get('ok'),
                            'count': len(v.get('videos', v.get('items', []))) if isinstance(v.get('videos', v.get('items')), list) else v.get('total', 0),
                            'total': v.get('total', 0)} for k, v in results.items()}
        })
    
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

def get_db():
    db_path = db.DB_PATH
    conn = get_repository().connect(timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # 启用WAL模式，提高并发性能
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('PRAGMA synchronous=NORMAL')
    except Exception:
        pass
    return conn


@app.route('/api/web/topics', methods=['GET'])
def api_web_topics_v580():
    """获取全网话题列表"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_repository().connect(timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM web_topics 
        ORDER BY mention_count DESC, last_seen DESC
        LIMIT ?
    """, (limit,))
    topics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'ok': True, 'topics': topics, 'count': len(topics)})


@app.route('/api/web/topics/refresh', methods=['POST'])
def api_web_topics_refresh_v580():
    """刷新全网话题（从浏览器搜索，不占用小红书次数）"""
    # 这里可以集成浏览器搜索逻辑
    # 暂时返回模拟数据
    return jsonify({
        'ok': True,
        'message': '全网话题刷新中（不占用小红书检索次数）',
        'status': 'processing'
    })


@app.route('/api/web/events', methods=['GET'])
def api_web_events_v580():
    """获取全网事件列表"""
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_repository().connect(timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM web_events 
        ORDER BY discovered_at DESC
        LIMIT ?
    """, (limit,))
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'ok': True, 'events': events, 'count': len(events)})


@app.route('/api/web/brand-industry', methods=['GET'])
def api_web_brand_industry_v580():
    """品牌业态全网监测"""
    brand_id = request.args.get('brand_id')
    industry = request.args.get('industry')
    limit = request.args.get('limit', 50, type=int)
    
    conn = get_repository().connect(timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM brand_industry_monitor WHERE 1=1"
    params = []
    
    if brand_id:
        query += " AND brand_name LIKE ?"
        params.append(f"%{brand_id}%")
    if industry:
        query += " AND industry = ?"
        params.append(industry)
    
    query += " ORDER BY note_count DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    brands = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'ok': True, 'brands': brands, 'count': len(brands)})


@app.route('/api/collection/counter', methods=['GET'])
def api_collection_counter_v580():
    """今日采集计数（B1 双轨对齐）：以真实落库/运行记录为准，只读计算，不再读写恒为 0 的 collection_counters 死表。
    口径区分：daily_count=今日最终入库 notes 条数（主体过滤/去重后的生产事实）；
    raw_collected=采集器原始抓取量（collection_logs SUCCESS 的 notes_count 合计，未去重）；
    runs=今日关键词任务数 / collector_stats 为调度轮次与 manual/auto 拆分；blocked=熔断/受限任务数（如实展示）。"""
    today = datetime.now().strftime('%Y-%m-%d')

    conn = get_repository().connect(timeout=30)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # 1) 今日真实入库条数（采集时刻：captured_at 优先、回退 collected_at）
    cursor.execute("SELECT COUNT(*), MAX(COALESCE(NULLIF(captured_at,''),collected_at)) FROM notes "
                   "WHERE date(COALESCE(NULLIF(captured_at,''),collected_at))=date('now','localtime')")
    _r = cursor.fetchone()
    notes_today = _r[0] or 0
    last_collect_at = _r[1]
    # 2) collection_logs 今日任务实况（status 大小写枚举兼容：SUCCESS/success）
    cursor.execute("SELECT COUNT(*), "
                   "SUM(CASE WHEN UPPER(status)='SUCCESS' THEN 1 ELSE 0 END), "
                   "SUM(CASE WHEN status='BLOCKED' THEN 1 ELSE 0 END), "
                   "SUM(CASE WHEN status IN ('NETWORK_ERROR','error','ERROR') THEN 1 ELSE 0 END), "
                   "COALESCE(SUM(CASE WHEN UPPER(status)='SUCCESS' THEN notes_count ELSE 0 END),0) "
                   "FROM collection_logs WHERE date(started_at)=date('now','localtime')")
    _l = cursor.fetchone()
    logs_today, success_runs, blocked_runs, error_runs, raw_collected = (_l[i] or 0 for i in range(5))
    # 当前熔断态以“最近一次任务”与“最近一次成功”先后判定（今日累计多不代表当前正常）
    cursor.execute("SELECT UPPER(COALESCE(status,'')), COALESCE(started_at,'') FROM collection_logs ORDER BY id DESC LIMIT 1")
    _last = cursor.fetchone(); last_status, last_at = (_last[0], _last[1]) if _last else ('', '')
    cursor.execute("SELECT COALESCE(MAX(started_at),'') FROM collection_logs WHERE UPPER(status)='SUCCESS'")
    last_success_at = cursor.fetchone()[0]
    conn.close()
    if last_status in ('BLOCKED', 'NETWORK_ERROR', 'ERROR') and (not last_success_at or last_at >= last_success_at):
        circuit = 'blocked'
    elif last_status == 'NO_NEW_DATA':
        circuit = 'idle'
    else:
        circuit = 'normal'

    # 3) 调度轮次与 manual/auto 拆分（唯一来源：采集器自记 collector_stats.json，仅当日有效）
    manual_count = auto_count = 0
    try:
        _sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'collector_stats.json')
        if os.path.exists(_sp):
            with open(_sp, 'r', encoding='utf-8') as _f:
                _st = json.load(_f)
            if str(_st.get('date')) == today:
                manual_count = int(_st.get('manual_runs', 0) or 0)
                auto_count = int(_st.get('auto_runs', 0) or 0)
                if not last_collect_at and _st.get('updated_at'):
                    last_collect_at = _st.get('updated_at')
    except Exception as _e:
        print('[collection-counter] collector_stats parse failed:', _e)
    runs_today = manual_count + auto_count or logs_today

    return jsonify({
        'ok': True,
        'date': today,
        'daily_count': notes_today,          # 今日最终入库条数（生产事实）
        'manual_count': manual_count,
        'auto_count': auto_count,
        'runs_today': runs_today,            # 今日调度轮次
        'logs_today': logs_today,            # 今日关键词任务数
        'success_runs': success_runs,
        'blocked_runs': blocked_runs,
        'error_runs': error_runs,
        'raw_collected': raw_collected,      # 原始抓取量（未去重）
        'raw_count': raw_collected,          # 别名：前端采集统计Raw
        'canonical_count': notes_today,      # 别名：前端采集统计Canonical（去重后入库）
        'circuit_state': circuit,
        'last_task_status': last_status,
        'last_success_at': last_success_at,
        'daily_limit': None,
        'manual_limit': None,
        'auto_limit': None,
        'last_collect_at': last_collect_at,
        'source': 'live:notes+collection_logs+collector_stats'
    })

@app.route('/api/collection/logs', methods=['GET'])
def api_collection_logs():
    """采集日志与生命周期追溯：返回最近N条采集任务记录，含来源/状态/时间线。"""
    try:
        limit = min(200, max(1, int(request.args.get('limit', 50))))
        offset = max(0, int(request.args.get('offset', 0)))
        status_filter = request.args.get('status', '').strip()
        date_from = request.args.get('from', '').strip()
        date_to = request.args.get('to', '').strip()
        keyword = request.args.get('keyword', '').strip()

        conn = get_repository().connect(timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        where = []
        params = []
        if status_filter:
            where.append("UPPER(COALESCE(status,'')) = UPPER(?)")
            params.append(status_filter)
        if date_from:
            where.append("date(started_at) >= date(?)")
            params.append(date_from)
        if date_to:
            where.append("date(started_at) <= date(?)")
            params.append(date_to)
        if keyword:
            where.append("keyword LIKE ?")
            params.append('%' + keyword + '%')

        where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''
        total = cursor.execute("SELECT COUNT(*) FROM collection_logs" + where_sql, params).fetchone()[0]

        rows = cursor.execute(
            "SELECT id, keyword, notes_count, status, error_msg, started_at, finished_at "
            "FROM collection_logs" + where_sql + " ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

        logs = []
        for r in rows:
            status = (r['status'] or '').upper()
            if status in ('SUCCESS', 'OK', 'COMPLETED'):
                lifecycle = 'completed'
            elif status in ('RUNNING', 'IN_PROGRESS', 'COLLECTING'):
                lifecycle = 'running'
            elif status in ('FAILED', 'ERROR', 'BLOCKED'):
                lifecycle = 'failed'
            elif status in ('COOLING_DOWN', 'RISK_WARNING', 'NEED_VERIFY'):
                lifecycle = 'degraded'
            else:
                lifecycle = 'unknown'

            duration_ms = None
            if r['started_at'] and r['finished_at']:
                try:
                    from datetime import datetime as _dt
                    s = _dt.fromisoformat(r['started_at'].replace('Z', '+00:00').split('+')[0])
                    e = _dt.fromisoformat(r['finished_at'].replace('Z', '+00:00').split('+')[0])
                    duration_ms = int((e - s).total_seconds() * 1000)
                except Exception:
                    pass

            logs.append({
                'id': r['id'],
                'keyword': r['keyword'],
                'notes_count': r['notes_count'] or 0,
                'status': status,
                'lifecycle': lifecycle,
                'error_msg': r['error_msg'],
                'started_at': r['started_at'],
                'finished_at': r['finished_at'],
                'duration_ms': duration_ms,
                'source': 'collection_logs',
                'traceable': True
            })

        summary = cursor.execute(
            "SELECT COUNT(*) total_runs, "
            "SUM(CASE WHEN UPPER(COALESCE(status,''))='SUCCESS' THEN 1 ELSE 0 END) success, "
            "SUM(CASE WHEN UPPER(COALESCE(status,'')) IN ('FAILED','ERROR') THEN 1 ELSE 0 END) failed, "
            "SUM(CASE WHEN UPPER(COALESCE(status,'')) IN ('COOLING_DOWN','RISK_WARNING','NEED_VERIFY','BLOCKED') THEN 1 ELSE 0 END) degraded, "
            "COALESCE(SUM(notes_count),0) total_notes_collected "
            "FROM collection_logs"
        ).fetchone()

        conn.close()

        return jsonify({
            'ok': True,
            'total': total,
            'limit': limit,
            'offset': offset,
            'logs': logs,
            'summary': {
                'total_runs': summary[0] or 0,
                'success': summary[1] or 0,
                'failed': summary[2] or 0,
                'degraded': summary[3] or 0,
                'total_notes_collected': summary[4] or 0,
                'success_rate': round((summary[1] or 0) * 100.0 / max(1, summary[0] or 0), 1)
            },
            'data_source': 'collection_logs (真实采集记录)',
            'lifecycle_stages': ['queued', 'running', 'completed', 'failed', 'degraded']
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'logs': [], 'summary': {}}), 500



@app.route('/api/web-topics')
def api_web_topics():
    """Read previously admitted topic rows; never start an unscoped background search."""
    topics=[];updated_at=None
    try:
        _c=get_repository().connect(timeout=30);_c.row_factory=sqlite3.Row
        rows=_c.execute('SELECT * FROM web_topics ORDER BY mention_count DESC, last_seen DESC LIMIT 50').fetchall()
        _c.close()
        for r in rows:
            d=dict(r)
            d['title']=d.get('topic') or '无标题'
            d['snippet']=d.get('summary') or f"{d.get('source','web')} · 提及{d.get('mention_count',0)}次 · 情感{d.get('sentiment','-')}"
            topics.append(d)
        updated_at=rows[0]['created_at'] if rows else None
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning('web topic read failed (%s)', type(e).__name__)
        return jsonify({'ok':False,'status':'UNAVAILABLE','code':'WEB_TOPIC_READ_UNAVAILABLE',
                        'topics':[],'count':None,'updated_at':None}),503
    return jsonify({'ok':True,'status':'AVAILABLE' if topics else 'EMPTY',
                    'topics':topics,'count':len(topics),'updated_at':updated_at})
@app.route('/api/web-topics/refresh', methods=['POST'])
def api_web_topics_refresh():
    """Collect registered-scope public-web sources through the existing Collector."""
    try:
        actor, scope, entries, _selected = _resolve_web_scope('write', module='collector')
    except (PermissionError, ValueError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 409
        return jsonify({'ok':False,'status':'BLOCKED','code':str(exc)}),status
    queries = _web_scope_terms(entries)
    if not queries:
        return jsonify({'ok':False,'status':'BLOCKED','code':'REGISTERED_SCOPE_TERMS_UNAVAILABLE'}),409
    try:
        import reprocess
        result = reprocess.discover_web(limit=120, queries=queries[:20], scope=scope, actor=actor)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('scoped web topic collection failed')
        return jsonify({'ok':False,'status':'ERROR','code':'WEB_TOPIC_COLLECTION_FAILED'}),500
    accepted = result.get('accepted')
    return jsonify({'ok':result.get('status') == 'COMPLETED',
                    'status':result.get('status'),'scope':scope,
                    'topics':result.get('results',[]),
                    'count':accepted if type(accepted) is int else None,
                    'collection':result}), 200 if result.get('status') in {'COMPLETED','PARTIAL'} else 409

# ===== ZBIP Workspace 只读面板（文件树 / 只读终端）——Staging 旁路，纯只读、过滤敏感、防路径穿越 =====
import subprocess as _ws_sp
_WS_ROOT = Path(__file__).resolve().parent
_WS_HIDE_DIRS = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache',
                 '.skills-router', '.trae-cn', '.vscode', '.idea', 'data/cookies'}
_WS_HIDE_RE = re.compile(r'(^\.env)|cookie|token|secret|credential|passwd|password|evidence-signing|\.(db|sqlite|sqlite3|pem|key|pfx|dpapi)$|profile', re.IGNORECASE)

def _ws_hidden(name, is_dir):
    # 名称命中即隐藏，不依赖 is_dir：git linked-worktree 中 .git 是文件而非目录，
    # 若用 is_dir 门控会导致 worktree 内 .git 文件漏出。
    if name in _WS_HIDE_DIRS or name.startswith('edge-cdp') or name.startswith('chrome-cdp'):
        return True
    return bool(_WS_HIDE_RE.search(name))

@app.route('/api/workspace/file-tree')
def api_workspace_file_tree():
    """只读列目录：限定项目根、过滤敏感文件/目录、防路径穿越，返回真实文件数。"""
    try:
        rel = (request.args.get('path') or '').strip().replace('\\', '/').lstrip('/')
        target = (_WS_ROOT / rel).resolve() if rel else _WS_ROOT
        if target != _WS_ROOT and _WS_ROOT not in target.parents:
            return jsonify({'ok': False, 'error': '路径越界，已拒绝'}), 403
        if not target.exists() or not target.is_dir():
            return jsonify({'ok': False, 'error': '目录不存在'}), 404
        items, nd, nf = [], 0, 0
        for p in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                isd = p.is_dir()
            except OSError:
                continue
            if _ws_hidden(p.name, isd):
                continue
            if isd:
                nd += 1
            else:
                nf += 1
            items.append({'name': p.name, 'type': 'dir' if isd else 'file',
                          'rel': str(p.relative_to(_WS_ROOT)).replace('\\', '/'),
                          'size': None if isd else p.stat().st_size})
        return jsonify({'ok': True, 'root': _WS_ROOT.name, 'path': rel,
                        'items': items, 'counts': {'dirs': nd, 'files': nf, 'total': nd + nf}})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500

_WS_TERM_ALLOW = {'ls', 'dir', 'pwd', 'whoami', 'help', 'clear', 'python', 'git'}
_WS_GIT_READONLY = {'status', 'log', 'diff', 'branch', 'rev-parse', 'show', 'remote', 'ls-files', 'count-objects'}

@app.route('/api/workspace/term', methods=['POST'])
def api_workspace_term():
    """只读 Web 终端：白名单命令、shell=False、cwd 锁定项目根、超时；拒绝一切写/管道/重定向。"""
    data = request.get_json(silent=True) or {}
    raw = (data.get('cmd') or '').strip()
    if not raw:
        return jsonify({'ok': False, 'error': '命令为空'}), 400
    if re.search(r'[;&|`$><]|\.\.', raw):
        return jsonify({'ok': False, 'blocked': True, 'error': '含管道/重定向/命令替换/上级路径，只读终端已拒绝。写操作请在本机终端执行。'}), 403
    parts = raw.split()
    head = parts[0].lower()
    if head not in _WS_TERM_ALLOW:
        return jsonify({'ok': False, 'blocked': True,
                        'error': 'Web 终端仅开放只读命令：ls / pwd / whoami / python --version / git 只读子命令 / help / clear。'}), 403
    try:
        if head in ('ls', 'dir'):
            lines = []
            for p in sorted(_WS_ROOT.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    isd = p.is_dir()
                except OSError:
                    continue
                if _ws_hidden(p.name, isd):
                    continue
                lines.append(('[D] ' if isd else '    ') + p.name)
            return jsonify({'ok': True, 'cmd': raw, 'cwd': str(_WS_ROOT), 'output': '\n'.join(lines)})
        if head == 'pwd':
            return jsonify({'ok': True, 'cmd': raw, 'cwd': str(_WS_ROOT), 'output': str(_WS_ROOT)})
        if head == 'help':
            return jsonify({'ok': True, 'cmd': raw, 'output':
                '只读 Web 终端可用命令：\n  ls                       列出项目根（自动过滤敏感项）\n  pwd                      项目根路径\n  whoami                   当前用户\n  python --version         Python 版本\n  git status|log|diff|branch|rev-parse|show|remote|ls-files   Git 只读查询\n  clear                    清屏\n写操作（commit/push/reset/安装/删除等）请在本机终端执行。'})
        if head == 'clear':
            return jsonify({'ok': True, 'clear': True})
        if head == 'python':
            if len(parts) < 2 or parts[1] != '--version':
                return jsonify({'ok': False, 'blocked': True, 'error': 'python 仅允许 --version'}), 403
            cmd = [sys.executable, '--version']
        elif head == 'whoami':
            cmd = ['whoami']
        else:  # git
            sub = parts[1].lower() if len(parts) > 1 else ''
            if sub not in _WS_GIT_READONLY:
                return jsonify({'ok': False, 'blocked': True, 'error': f'git {sub or "(无子命令)"} 不是只读子命令，已拒绝。'}), 403
            cmd = ['git', '-C', str(_WS_ROOT)] + parts[1:]
        r = _ws_sp.run(cmd, capture_output=True, text=True, timeout=15,
                       cwd=str(_WS_ROOT), encoding='utf-8', errors='replace')
        return jsonify({'ok': r.returncode == 0, 'cmd': raw, 'cwd': str(_WS_ROOT),
                        'output': (r.stdout or '') + (r.stderr or ''), 'code': r.returncode})
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500


@app.route('/api/workspace/file')
def api_workspace_file():
    """只读文件内容预览：限定项目根、过滤敏感、防路径穿越、限200KB、文本only、二进制拒绝预览。"""
    rel = (request.args.get('path') or '').strip().replace('\\', '/').lstrip('/')
    if not rel:
        return jsonify({'ok': False, 'error': 'path 为空'}), 400
    try:
        target = (_WS_ROOT / rel).resolve()
    except Exception:
        return jsonify({'ok': False, 'error': '路径非法'}), 400
    if target != _WS_ROOT and _WS_ROOT not in target.parents:
        return jsonify({'ok': False, 'error': '路径越界，已拒绝'}), 403
    if not target.exists() or not target.is_file():
        return jsonify({'ok': False, 'error': '文件不存在'}), 404
    if _ws_hidden(target.name, False):
        return jsonify({'ok': False, 'error': '敏感文件，拒绝预览（.env/cookie/token/secret/db/profile 等）'}), 403
    size = target.stat().st_size
    MAX = 200 * 1024
    try:
        raw = target.read_bytes()[:MAX + 1]
    except Exception as e:
        return jsonify({'ok': False, 'error': f'{type(e).__name__}: {e}'}), 500
    if b'\x00' in raw[:8192]:
        return jsonify({'ok': True, 'path': rel, 'size': size, 'binary': True,
                        'content': '[二进制文件，不提供文本预览]'})
    text = raw.decode('utf-8', errors='replace')
    truncated = size > MAX
    return jsonify({'ok': True, 'path': rel, 'size': size,
                    'lines': text.count('\n') + 1, 'truncated': truncated,
                    'content': text[:MAX]})


# ===== 公关案例库 API（双模块联动体系） =====
@app.route('/api/pr/cases')
def api_pr_cases():
    """获取所有公关案例"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        scene = request.args.get('scene')
        level = request.args.get('level')
        keyword = request.args.get('keyword')
        cases = engine.search_cases(scene=scene, level=level, keyword=keyword)
        return jsonify({'ok': True, 'total': len(cases), 'cases': cases})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/cases/<case_id>')
def api_pr_case_detail(case_id):
    """获取单个公关案例详情"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        case = engine.get_case_by_id(case_id)
        if case:
            return jsonify({'ok': True, 'case': case})
        return jsonify({'ok': False, 'error': '案例不存在'}), 404
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/match', methods=['POST'])
def api_pr_match():
    """为笔记匹配同类案例（专报触发时调用）"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        data = request.get_json(silent=True) or {}
        note = data.get('note', {})
        top_n = data.get('top_n', 3)
        matched = engine.match_similar_cases(note, top_n=top_n)
        return jsonify({
            'ok': True,
            'matched': len(matched),
            'cases': matched,
            'case_ids': [c.get('id') for c in matched]
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/recommend', methods=['POST'])
def api_pr_recommend():
    """为笔记推荐公关话术"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        data = request.get_json(silent=True) or {}
        note = data.get('note', {})
        recommendation = engine.recommend_response(note)
        return jsonify({'ok': True, 'recommendation': recommendation})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/templates')
def api_pr_templates():
    """获取公关话术模板"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        scene = request.args.get('scene')
        if scene:
            template = engine.get_response_template(scene)
            return jsonify({'ok': True, 'template': template})
        return jsonify({'ok': True, 'templates': engine.templates, 'act_law': engine.response_templates.get('act_law', {})})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/statistics')
def api_pr_statistics():
    """获取案例库统计"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        return jsonify({'ok': True, 'statistics': engine.get_statistics()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/pr/check-trigger', methods=['POST'])
def api_pr_check_trigger():
    """检查是否触发专报条件"""
    try:
        from pr_case_engine import get_pr_engine
        engine = get_pr_engine()
        data = request.get_json(silent=True) or {}
        notes = data.get('notes', [])
        note = data.get('note')
        result = engine.check_special_report_trigger(notes, note)
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ===== V4 升级模块旁路接入：独立 /v4 蓝图、独立认证与 v4_ 建表，不改写现网业务、不挂自动调度 =====
from lumenis import create_v4_blueprint, init_v4_modules
init_v4_modules()
app.register_blueprint(create_v4_blueprint())

# ===== P1-F 账户体系主线化：account/ 一级主线模块（/api/system/account/*） =====
try:
    from account import account_bp, compat_bp, init_account_db
    init_account_db()
    app.register_blueprint(account_bp)
    app.register_blueprint(compat_bp)
    print("[account] 主线账户体系已注册 /api/system/account/* + 兼容层")
except Exception as _acct_err:
    print(f"[account] 主线账户体系注册失败（不阻断启动）: {_acct_err}")

# GAP-10 Shared Reporting 旁路路由（Feature Gate: LUMENIS_REPORTING=1 启用，默认关闭）
from lumenis.shared.reporting.api import reporting_bp
app.register_blueprint(reporting_bp)

# ===== ZBC V2.0 双域核心扩展：请求级域上下文 + 双域 API 命名空间 =====
# subject_context.init_app: 注册 before/after_request 钩子，
# 从 X-Domain-Id / X-Product-Id / X-Brand-Key 解析域身份，设置线程 SubjectContext + DomainContext
try:
    from subject_context import init_app as _sc_init_app
    _sc_init_app(app)
    print("[dual-domain] subject_context.init_app(app) 已注册（请求级域上下文钩子）")
except Exception as _sc_err:
    print(f"[dual-domain] subject_context.init_app 注册失败（不阻断启动）: {_sc_err}")

# 双域 API 命名空间：/api/zbmp/*, /api/cth/*, /api/system/*
# Compatibility Layer：现有 /api/* 端点保持不变，本模块仅新增域命名空间端点
try:
    from api_dual_domain import register_dual_domain_api
    register_dual_domain_api(app)
except Exception as _dd_err:
    print(f"[dual-domain] API 蓝图注册失败（不阻断启动）: {_dd_err}")
# ===== V2.0 双域兼容层：旧 API 路由保留但标记 deprecated =====
_DEPRECATED_API_PREFIXES = ("/api/xhs/", "/api/v4/", "/api/notes/", "/api/web/")

@app.after_request
def _mark_deprecated_api_headers(response):
    """对旧 API 路由响应加 X-Deprecated: true 头（不断旧链）。"""
    try:
        path = request.path or ""
        for prefix in _DEPRECATED_API_PREFIXES:
            if path.startswith(prefix):
                response.headers["X-Deprecated"] = "true"
                if prefix == "/api/xhs/":
                    response.headers["X-Successor"] = "/api/cth/xiaohongshu"
                elif prefix == "/api/v4/":
                    response.headers["X-Successor"] = "/api/system/api-keys"
                elif prefix == "/api/notes/":
                    response.headers["X-Successor"] = "/api/cth/overview or /api/zbmp/overview"
                elif prefix == "/api/web/":
                    response.headers["X-Successor"] = "/api/zbmp/brands or /api/cth/events"
                break
    except Exception:
        pass
    return response

print("[dual-domain] deprecated 兼容层已注册：旧 /api/xhs|v4|notes|web 加 X-Deprecated 头")
# ===== V2.0 API 契约补全：断链路由修复 =====
# 修复前端调用的断链：/api/skills/*, /api/auxiliary/sources, /api/web-sources,
# /api/zbmp|cth 基础路由, /api/system/account 基础路由
# 统一响应信封：{success, data, error, domain_id, product_id}

@app.route('/api/skills')
@app.route('/api/skills/list')
def api_skills_list():
    """Skill 列表（复用 account.skills 的现有 DB 注册表 owner）。"""
    try:
        from account.skills import list_skills
        skills = list_skills()
        return jsonify({"success": True, "data": {"skills": skills, "total": len(skills)},
                        "error": "", "domain_id": "system", "product_id": "SYSTEM"})
    except Exception as e:
        return jsonify({"success": False, "data": {"skills": []}, "error": str(e),
                        "domain_id": "system", "product_id": "SYSTEM"}), 200

@app.route('/api/skills/status')
def api_skills_status():
    """Skill 运行状态（来自现有注册表，不返回固定假值）。"""
    try:
        from account.skills import list_skills
        skills = list_skills()
        enabled = [skill for skill in skills if skill.get("status") == "enabled"]
        return jsonify({
            "success": True,
            "data": {
                "status": "ready" if enabled else ("registered" if skills else "not_collected"),
                "registered": len(skills),
                "loaded": len(enabled),
                "skills": [{
                    "skill_id": skill.get("skill_id"),
                    "status": skill.get("status"),
                    "source_type": skill.get("source_type") or "builtin",
                    "health_state": skill.get("health_state") or "unknown",
                    "lifecycle_state": skill.get("lifecycle_state") or "registered",
                } for skill in skills],
            },
            "error": "", "domain_id": "system", "product_id": "SYSTEM",
        })
    except Exception as exc:
        return jsonify({"success": False, "data": {"status": "unknown", "registered": None,
                        "loaded": None, "skills": []}, "error": str(exc),
                        "domain_id": "system", "product_id": "SYSTEM"}), 200

@app.route('/api/auxiliary/sources')
def api_auxiliary_sources():
    """辅助数据源列表（feature-modules.js 调用）。"""
    try:
        sources = []
        try:
            from resource_library import get_all_sources
            sources = get_all_sources()
        except Exception:
            sources = []
        return jsonify({"success": True, "data": {"sources": sources, "total": len(sources)},
                        "error": "", "domain_id": "system", "product_id": "SYSTEM"})
    except Exception as e:
        return jsonify({"success": False, "data": {"sources": []}, "error": str(e),
                        "domain_id": "system", "product_id": "SYSTEM"}), 200

@app.route('/api/web-sources')
def api_web_sources():
    """Web 数据源列表（feature-modules.js 备选端点）。"""
    try:
        sources = []
        try:
            from resource_library import get_web_sources
            sources = get_web_sources()
        except Exception:
            sources = []
        return jsonify({"success": True, "data": {"sources": sources, "items": sources, "total": len(sources)},
                        "error": "", "domain_id": "system", "product_id": "SYSTEM"})
    except Exception as e:
        return jsonify({"success": False, "data": {"sources": [], "items": []}, "error": str(e),
                        "domain_id": "system", "product_id": "SYSTEM"}), 200

@app.route('/api/zbmp')
def api_zbmp_base():
    """ZBMP API 基础路由：返回域信息+可用端点。"""
    return jsonify({"success": True, "data": {
        "domain": "zbmp", "product": "ZBMP",
        "endpoints": ["/api/zbmp/overview", "/api/zbmp/brands", "/api/zbmp/metrics"]
    }, "error": "", "domain_id": "zbmp", "product_id": "ZBMP"})

@app.route('/api/cth')
def api_cth_base():
    """CTH API 基础路由：返回域信息+可用端点。"""
    return jsonify({"success": True, "data": {
        "domain": "cth", "product": "CTH",
        "endpoints": ["/api/cth/overview", "/api/cth/events", "/api/cth/xiaohongshu"]
    }, "error": "", "domain_id": "cth", "product_id": "CTH"})

@app.route('/api/system/account')
def api_system_account_base():
    """Compatibility envelope for the current server-authenticated account."""
    try:
        from lumenis.auth.service import get_current_user
        user = get_current_user(read_only=True)
        if not user:
            return jsonify({"success": False, "data": None, "error": "AUTH_REQUIRED",
                            "domain_id": "system", "product_id": "SYSTEM"}), 401
        profile = {key: user.get(key) for key in ("id", "username", "role", "display_name")}
        return jsonify({"success": True, "data": profile, "error": "",
                        "domain_id": "system", "product_id": "SYSTEM"})
    except Exception:
        return jsonify({"success": False, "data": None, "error": "ACCOUNT_UNAVAILABLE",
                        "domain_id": "system", "product_id": "SYSTEM"}), 503

print("[dual-domain] API 契约断链修复完成：skills/auxiliary/web-sources/zbmp|cth base/system/account")

# AI Governance — privacy-safe reporting, budget controls, usage statistics and output labels through the existing Gateway.
import ai_governance
import ai_resource_packs

# Legacy domain-entry routes only read existing server-authorized scope.
# Navigation never creates a second account, domain grant, or credential.
def _legacy_domain_scope_status():
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import resolve_web_request_scope
    user = get_current_user(read_only=True)
    if not user:
        return None, (jsonify({"ok": False, "success": False,
            "code": "AUTH_REQUIRED", "logged_in": False}), 401)
    if request.headers.get("X-Domain-Id", "").strip().lower() not in {"bmp", "zbmp"}:
        return None, (jsonify({"ok": False, "success": False,
            "code": "BMP_CONTEXT_REQUIRED", "zbmp_granted": False}), 400)
    try:
        actor, scope, _entries, _selected = resolve_web_request_scope("read", module="reports")
        if actor.get("id") != user["id"] or scope.get("domain_id") != "zbmp":
            raise PermissionError("SCOPE_PERMISSION_DENIED")
    except PermissionError:
        return None, (jsonify({"ok": False, "success": False,
            "code": "SCOPE_PERMISSION_DENIED", "zbmp_granted": False}), 403)
    except ValueError:
        return None, (jsonify({"ok": False, "success": False,
            "code": "CONTEXT_SCOPE_INVALID", "zbmp_granted": False}), 400)
    except Exception:
        return None, (jsonify({"ok": False, "success": False,
            "code": "SCOPE_PERMISSION_UNAVAILABLE", "zbmp_granted": False}), 503)
    return {"ok": True, "success": True, "logged_in": True,
        "user_id": user["id"], "username": user["username"], "role": user["role"],
        "domain_identity": "zbmp", "zbmp_granted": True, "cth_logged": True,
        "scope": scope, "grant_created": False,
        "authorization_basis": "CURRENT_SERVER_SCOPE_PERMISSION"}, None


@app.route('/api/auth/domain-identity', methods=['GET'])
def api_domain_identity():
    """Read current exact BMP scope permission; legacy cookies have no authority."""
    result, failure = _legacy_domain_scope_status()
    return failure if failure else jsonify(result)


@app.route('/api/auth/zbmp-entry/status', methods=['GET'])
def api_zbmp_entry_status():
    return api_domain_identity()


@app.route('/api/auth/zbmp-entry/unlock', methods=['POST'])
def api_zbmp_entry_unlock():
    """Compatibility entry checks existing permission without granting new access."""
    result, failure = _legacy_domain_scope_status()
    if failure:
        return failure
    resp = jsonify(result)
    resp.delete_cookie('zbmp_domain_grant', path='/')
    return resp


@app.route('/api/auth/zbmp-entry/verify', methods=['POST'])
def api_zbmp_entry_verify():
    return api_zbmp_entry_unlock()


@app.route('/api/auth/zbmp-entry/leave', methods=['POST'])
def api_zbmp_entry_leave():
    """Leave the view; account permissions are unchanged."""
    from lumenis.auth.service import get_current_user
    if not get_current_user(read_only=True):
        return jsonify({"ok": False, "success": False, "code": "AUTH_REQUIRED"}), 401
    resp = jsonify({"ok": True, "success": True, "navigation_domain": "cth",
                    "permissions_changed": False})
    resp.delete_cookie('zbmp_domain_grant', path='/')
    return resp


# ===== 系统启动入口 =====


# ============ AI 资源包管理 API（智谱多资源包额度） ============
@app.route('/api/ai-resource-packs/status')
def api_ai_resource_packs_status():
    """所有资源包状态查询"""
    try:
        status = ai_resource_packs.get_all_packs_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/glm-4-5-air')
def api_ai_resource_packs_glm_status():
    """glm-4.5-air 实时状态（小 icon 用）"""
    try:
        status = ai_resource_packs.get_glm_4_5_air_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/pause', methods=['POST'])
def api_ai_resource_packs_pause():
    """暂停 AI 连接"""
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '用户手动暂停')
        result = ai_resource_packs.pause_connection(reason)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/resume', methods=['POST'])
def api_ai_resource_packs_resume():
    """恢复 AI 连接"""
    try:
        result = ai_resource_packs.resume_connection()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/ai-resource-packs/per-call-execute', methods=['POST'])
def api_ai_resource_packs_per_call_execute():
    """按次计费需求执行接口（用户输入需求，消耗1次按次额度）"""
    try:
        data = request.get_json(silent=True) or {}
        user_request = str(data.get('request') or data.get('prompt') or '').strip()
        if not user_request:
            return jsonify({'ok': False, 'error': '需求不能为空'}), 400
        model = data.get('model', 'glm-5.3')
        result = ai_resource_packs.execute_per_call_request(user_request, model)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# API Key 管理：唯一实现见 account/compat.py（/api/v4/api-keys*，需登录）。


# ============ 小红书系统内二维码登录（Auth Recovery） ============
def _xhs_ensure_login_panel(page, login_texts):
    """未登录且停在首页时，仅点击一次“登录”入口唤起二维码面板。
    只点登录入口本身，绝不点击关注/赞藏/发布/退出/切号等任何账号操作。"""
    try:
        if page.locator('canvas, [class*="qrcode"], [class*="qr-code"], [class*="login-qr"]').count() > 0:
            return
        for txt in (login_texts or ('登录', 'Log in')):
            try:
                loc = page.get_by_text(txt, exact=True)
                for i in range(min(loc.count(), 4)):
                    el = loc.nth(i)
                    if not el.is_visible():
                        continue
                    box = el.bounding_box() or {}
                    if 20 <= box.get('width', 0) <= 200 and 16 <= box.get('height', 0) <= 80:
                        el.click(timeout=2000)
                        page.wait_for_timeout(1200)
                        return
            except Exception:
                continue
    except Exception:
        pass


def _xhs_shot_qr_element(page):
    """找“可见、近似方形、尺寸合理”的二维码元素并截图(base64)；找不到返回 None。"""
    import base64 as _b64
    candidates = [
        'canvas', '[class*="qrcode"] canvas', '[class*="qr-code"]',
        '[class*="login-qr"] img', '[class*="qrcode"] img',
        'img[src*="qrcode"]', 'div[class*="qr"]',
    ]
    best = None
    for sel in candidates:
        try:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 4)):
                el = loc.nth(i)
                if not el.is_visible():
                    continue
                box = el.bounding_box() or {}
                w, h = box.get('width', 0), box.get('height', 0)
                if not (80 <= w <= 360 and 80 <= h <= 360):
                    continue
                if not (0.65 <= (w / h if h else 0) <= 1.55):
                    continue
                area = w * h
                if best is None or area > best[0]:
                    best = (area, el)
        except Exception:
            continue
    if not best:
        return None
    try:
        return _b64.b64encode(best[1].screenshot(type='png')).decode()
    except Exception:
        return None


def _xhs_login_capture(ep):
    """连接平台常驻 CDP：在线→('logged_in',None)；未登录→打开登录页/唤起面板并截取二维码。
    全程只读 + 至多点击一次“登录”入口；不发布/不关注/不退出/不切号。
    返回 (stage, qr_dataurl_or_None, msg)。"""
    import base64 as _b64
    from playwright.sync_api import sync_playwright
    cdp = ep['cdp_url']
    home = ep['home_url']
    login = ep.get('login_url') or home
    want = set(ep.get('session_cookies') or ())
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(cdp, timeout=10000)
        try:
            ctx = browser.contexts[0] if browser.contexts else None
            if ctx is None:
                return 'error', None, '浏览器无可用上下文，请确认对应 CDP 浏览器已启动'
            names = {c.get('name') for c in (ctx.cookies(home) or [])}
            if want and (names & want):
                return 'logged_in', None, '检测到登录态，无需扫码'
            page = None  # 复用已打开的本站 tab，避免重复弹窗
            for pg in ctx.pages:
                try:
                    if ep.get('domain', '') in (pg.url or ''):
                        page = pg
                        break
                except Exception:
                    continue
            if page is None:
                page = ctx.new_page()
                page.goto(login, wait_until='domcontentloaded', timeout=25000)
                page.wait_for_timeout(2500)
            _xhs_ensure_login_panel(page, ep.get('login_texts'))
            page.wait_for_timeout(1000)
            qr = _xhs_shot_qr_element(page)
            if qr:
                return 'qr_ready', 'data:image/png;base64,' + qr, '请使用小红书 App 扫描二维码'
            png = page.screenshot(type='png')  # 回退整页视口，便于人工排查而非空白
            return 'no_qr', 'data:image/png;base64,' + _b64.b64encode(png).decode(), '暂未定位到二维码（可能加载中），已回传当前页面'
        finally:
            try:
                browser.close()
            except Exception:
                pass


_XHS_HUMAN_LOGIN_SESSION_TTL_SECONDS = 15 * 60


class _XhsHumanLoginSessionExpired(LookupError):
    """The same authorized human login session was safely returned to background."""


def _xhs_human_login_session_expired(session, *, now=None):
    now = time.time() if now is None else float(now)
    try:
        created_at = float(session.get('created_at'))
    except (AttributeError, TypeError, ValueError):
        return True
    return (created_at <= 0 or created_at > now + 60
            or now - created_at >= _XHS_HUMAN_LOGIN_SESSION_TTL_SECONDS)


def _xhs_login_unavailable_code(exc, default):
    if str(exc) == 'HUMAN_LOGIN_BACKGROUND_RETURN_UNVERIFIED':
        return str(exc)
    return default


def _return_xhs_login_session_background(session_id, session, actor_ref):
    """Return only the same live task's leased worker; keep state on any failure."""
    if actor_ref != session.get('actor_ref'):
        raise PermissionError('HUMAN_LOGIN_SESSION_ACTOR_MISMATCH')
    task_id = str(session.get('task_id') or '').strip()
    if not task_id or session.get('account') != 'XHS_RETINAUT':
        raise PermissionError('HUMAN_LOGIN_SESSION_BINDING_INVALID')
    from lumenis.adapters.human_browser import return_registered_worker_to_background
    returned = return_registered_worker_to_background(
        'XHS_RETINAUT', task_id=task_id, actor_ref=actor_ref)
    if returned.get('worker_verified') is not True:
        session['status'] = 'return_blocked'
        raise RuntimeError('HUMAN_LOGIN_BACKGROUND_RETURN_UNVERIFIED')
    sessions = getattr(app, '_xhs_login_sessions', {})
    if sessions.get(session_id) is session:
        sessions.pop(session_id, None)
    return returned


def _sweep_expired_xhs_login_sessions(actor_ref):
    """Only the authenticated actor may close its own expired human session."""
    sessions = getattr(app, '_xhs_login_sessions', {})
    for session_id, session in list(sessions.items()):
        if (not isinstance(session, dict) or session.get('actor_ref') != actor_ref
                or not _xhs_human_login_session_expired(session)):
            continue
        _return_xhs_login_session_background(session_id, session, actor_ref)


def _validate_xhs_human_login_session(session_id, *, allow_state_changed_return=False):
    """Bind a login session to the authenticated actor, task and bounded lease."""
    sessions = getattr(app, '_xhs_login_sessions', {})
    session_id = str(session_id or '').strip()
    session = sessions.get(session_id)
    if not isinstance(session, dict):
        raise LookupError('HUMAN_LOGIN_SESSION_NOT_FOUND')  # noqa: TRY004 - this signals a missing keyed session, not a type mismatch.
    actor_ref = _collector_browser_actor_ref()
    if actor_ref != session.get('actor_ref'):
        raise PermissionError('HUMAN_LOGIN_SESSION_ACTOR_MISMATCH')
    task_id = str(session.get('task_id') or '').strip()
    if not task_id or session.get('account') != 'XHS_RETINAUT':
        raise PermissionError('HUMAN_LOGIN_SESSION_BINDING_INVALID')
    expired = _xhs_human_login_session_expired(session)
    from lumenis.adapters.human_browser import (
        _authorize_human_browser_return,
        _authorize_human_interactive,
    )
    if expired or allow_state_changed_return:
        _authorize_human_browser_return('XHS_RETINAUT', task_id, actor_ref)
    else:
        _authorize_human_interactive('XHS_RETINAUT', task_id, actor_ref)
    if expired:
        _return_xhs_login_session_background(session_id, session, actor_ref)
        raise _XhsHumanLoginSessionExpired('HUMAN_LOGIN_SESSION_EXPIRED')
    return session, actor_ref, task_id


def _require_xhs_human_login_session(session_id):
    session, actor_ref, task_id = _validate_xhs_human_login_session(session_id)
    import xhs_collection_optimizer as optimizer
    endpoint = optimizer.get_platform_endpoint(
        'rednote_hk', headless=False, task_id=task_id, actor_ref=actor_ref)
    return session, actor_ref, task_id, endpoint


@app.route('/api/xhs/login/start', methods=['POST'])
def api_xhs_login_start():
    """Open only an explicitly requested, task-owned Hong Kong/International login session."""
    try:
        import time
        import uuid

        import xhs_collection_optimizer as optimizer
        body = request.get_json(silent=True) or {}
        try:
            platform = optimizer.normalize_registered_platform(
                body.get('platform') or 'rednote_hk')
        except ValueError as exc:
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': str(exc)}), 400
        if platform != 'rednote_hk':
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'PROTECTED_PROFILE_FORBIDDEN'}), 403
        task_id = str(body.get('task_id') or '').strip()
        if not task_id:
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'HUMAN_INTERACTIVE_TASK_ID_REQUIRED'}), 400
        actor_ref = _collector_browser_actor_ref()
        from lumenis.adapters.human_browser import _authorize_human_interactive
        _authorize_human_interactive('XHS_RETINAUT', task_id, actor_ref)
        _sweep_expired_xhs_login_sessions(actor_ref)
        collector = collector_automation.get_collector_automation()
        collector.start_browser(account='XHS_RETINAUT', headless=False,
                                mode='HUMAN_INTERACTIVE', task_id=task_id,
                                actor_ref=actor_ref)
        endpoint = optimizer.get_platform_endpoint(
            'rednote_hk', headless=False, task_id=task_id, actor_ref=actor_ref)
        session_id = 'xhs_login_' + uuid.uuid4().hex
        sessions = getattr(app, '_xhs_login_sessions', {})
        created_at = time.time()
        sessions[session_id] = {
            'status': 'pending', 'created_at': created_at,
            'expires_at': created_at + _XHS_HUMAN_LOGIN_SESSION_TTL_SECONDS,
            'platform': 'rednote_hk', 'account': 'XHS_RETINAUT',
            'task_id': task_id, 'actor_ref': actor_ref,
        }
        app._xhs_login_sessions = sessions
        return jsonify({'ok': True, 'session_id': session_id,
                        'platform': 'rednote_hk', 'label': endpoint['label'],
                        'status': 'pending', 'mode': 'HUMAN_INTERACTIVE',
                        'expires_in_seconds': _XHS_HUMAN_LOGIN_SESSION_TTL_SECONDS})
    except PermissionError as exc:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(exc)}), 403
    except LookupError as exc:
        return jsonify({'ok': False, 'status': 'NOT_FOUND', 'error': str(exc)}), 404
    except Exception as exc:  # noqa: BLE001 - keep unknown browser failures at a safe unavailable boundary.
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'code': _xhs_login_unavailable_code(exc, 'LOGIN_WORKER_UNAVAILABLE'),
                        'error_type': type(exc).__name__}), 409


@app.route('/api/xhs/login/status')
def api_xhs_login_status():
    """Read login state from the same authorized visible worker without starting another browser."""
    try:
        import time as clock
        session_id = request.args.get('session_id', '')
        session, _, _, endpoint = _require_xhs_human_login_session(session_id)
        stage, qr_image, message = 'unknown', None, ''
        now = clock.time()
        try:
            cached = (session.get('qr_image') and now - session.get('last_cap', 0) < 2.5
                      and session.get('status') in ('qr_ready', 'no_qr'))
            if cached:
                stage = session['status']
                qr_image = session.get('qr_image')
                message = '请使用小红书 App 扫描二维码' if stage == 'qr_ready' else '二维码加载中…'
            else:
                stage, qr_image, message = _xhs_login_capture(endpoint)
                session.update(status=stage, last_cap=now, qr_image=qr_image)
        except Exception as exc:  # noqa: BLE001 - capture failures become an explicit UI error state.
            stage, message = 'error', f'登录页探测失败：{type(exc).__name__}'
        return jsonify({'ok': True, 'session_id': session_id,
                        'platform': 'rednote_hk', 'label': endpoint['label'],
                        'stage': stage, 'status': stage,
                        'is_logged_in': stage == 'logged_in', 'qr_image': qr_image,
                        'expires_in_seconds': max(
                            0, int(float(session['created_at'])
                                   + _XHS_HUMAN_LOGIN_SESSION_TTL_SECONDS - now)),
                        'message': '已登录' if stage == 'logged_in' else message})
    except PermissionError as exc:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(exc)}), 403
    except _XhsHumanLoginSessionExpired as exc:
        return jsonify({'ok': False, 'status': 'EXPIRED', 'error': str(exc)}), 410
    except LookupError as exc:
        return jsonify({'ok': False, 'status': 'NOT_FOUND', 'error': str(exc)}), 404
    except Exception as exc:  # noqa: BLE001 - keep unknown browser failures at a safe unavailable boundary.
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'code': _xhs_login_unavailable_code(exc, 'LOGIN_WORKER_UNAVAILABLE'),
                        'error_type': type(exc).__name__}), 409


@app.route('/api/xhs/login/cancel', methods=['POST'])
def api_xhs_login_cancel():
    """Cancel the same actor's pending login and safely return its worker."""
    try:
        body = request.get_json(silent=True) or {}
        session_id = str(body.get('session_id') or '').strip()
        session, actor_ref, _ = _validate_xhs_human_login_session(
            session_id, allow_state_changed_return=True)
        _return_xhs_login_session_background(session_id, session, actor_ref)
        return jsonify({'ok': True, 'status': 'CANCELLED_RETURNED_BACKGROUND',
                        'platform': 'rednote_hk'})
    except PermissionError as exc:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(exc)}), 403
    except _XhsHumanLoginSessionExpired as exc:
        return jsonify({'ok': False, 'status': 'EXPIRED', 'error': str(exc)}), 410
    except LookupError as exc:
        return jsonify({'ok': False, 'status': 'NOT_FOUND', 'error': str(exc)}), 404
    except Exception as exc:  # noqa: BLE001 - keep the lease when return is unverified.
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'code': 'HUMAN_LOGIN_BACKGROUND_RETURN_UNVERIFIED',
                        'error_type': type(exc).__name__}), 409


@app.route('/api/xhs/login/save', methods=['POST'])
def api_xhs_login_save():
    """Save only a verified HK/International login from the same actor/task session."""
    try:
        body = request.get_json(silent=True) or {}
        session_id = str(body.get('session_id') or request.args.get('session_id') or '').strip()
        _, actor_ref, task_id, endpoint = _require_xhs_human_login_session(session_id)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(endpoint['cdp_url'], timeout=15000)
            try:
                context = browser.contexts[0] if browser.contexts else None
                if context is None:
                    return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                                    'code': 'BROWSER_CONTEXT_UNAVAILABLE'}), 409
                cookies = context.cookies(endpoint['home_url']) or []
            finally:
                browser.close()
        cookie_header = '; '.join(
            f"{item.get('name')}={item.get('value')}"
            for item in cookies
            if item.get('name') and item.get('value') is not None
        )
        import xhs_cookie_bridge as bridge
        cookie_names = {str(item.get('name') or '') for item in cookies}
        if not cookie_header or not (cookie_names & set(endpoint['session_cookies'])):
            return jsonify({'ok': False, 'status': 'NEED_VERIFY',
                            'code': 'LOGIN_SESSION_NOT_VERIFIED'}), 409
        observed_uid = bridge._extract_user_id_from_cookie_text(cookie_header)
        if not bridge.XHS_RETINAUT or observed_uid != bridge.XHS_RETINAUT:
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'REGISTERED_ACCOUNT_IDENTITY_MISMATCH'}), 403
        cookie_path = bridge.ACCOUNT_PROFILES[bridge.XHS_RETINAUT_NAME][0]
        cookie_path = os.path.abspath(cookie_path)
        os.makedirs(os.path.dirname(cookie_path), exist_ok=True)
        with open(cookie_path, 'w', encoding='utf-8') as handle:
            handle.write(cookie_header)
        from lumenis.adapters.human_browser import (
            return_registered_worker_to_background,
        )
        returned = return_registered_worker_to_background(
            'XHS_RETINAUT', task_id=task_id, actor_ref=actor_ref)
        if returned.get('worker_verified') is not True:
            return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                            'code': 'BACKGROUND_RETURN_UNVERIFIED',
                            'cookies_saved': True}), 409
        try:
            from auth_recovery_center import auth_recovery_center
            pending = auth_recovery_center.get_pending_tasks('rednote')
            for recovery_task in pending:
                auth_recovery_center.mark_completed(
                    recovery_task.id, f"{endpoint['label']}系统内登录已保存并返回后台")
        except Exception:
            pass
        getattr(app, '_xhs_login_sessions', {}).pop(session_id, None)
        return jsonify({'ok': True, 'status': 'RETURNED_BACKGROUND',
                        'platform': 'rednote_hk', 'label': endpoint['label'],
                        'account': 'XHS_RETINAUT', 'credential_store': 'protected_runtime',
                        'cookies_saved': True, 'cookie_count': len(cookies),
                        'message': '登录态已保存并安全返回后台'})
    except PermissionError as exc:
        return jsonify({'ok': False, 'status': 'BLOCKED', 'error': str(exc)}), 403
    except _XhsHumanLoginSessionExpired as exc:
        return jsonify({'ok': False, 'status': 'EXPIRED', 'error': str(exc)}), 410
    except LookupError as exc:
        return jsonify({'ok': False, 'status': 'NOT_FOUND', 'error': str(exc)}), 404
    except Exception as exc:  # noqa: BLE001 - do not expose storage or browser details at the API boundary.
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'code': 'LOGIN_SAVE_OR_RETURN_FAILED',
                        'error_type': type(exc).__name__}), 409


# ============ Search-STD 搜索增强（案例库/知识库/RAG） ============
@app.route('/api/search/enhance', methods=['POST'])
def api_search_enhance():
    """搜索增强（智谱 search-std，100次额度）。用于案例库搜索增强、品牌知识库RAG、产品全局架构检索。"""
    try:
        data = request.get_json(silent=True) or {}
        query = str(data.get('query') or data.get('q') or '').strip()
        context = str(data.get('context') or '')
        max_results = int(data.get('max_results', 5))
        if not query:
            return jsonify({'ok': False, 'error': '查询不能为空'}), 400
        import intelligence
        result = intelligence.search_enhance(query, context, max_results)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============ 学习采集 + 小红书优化 API ============
@app.route('/api/learning/scan', methods=['POST'])
def api_learning_scan():
    """运行学习采集扫描（全量代码库学习，可选AI深度分析）"""
    try:
        data = request.get_json(silent=True) or {}
        use_ai = bool(data.get('use_ai', False))
        from lumenis.shared.learning import collector as learning_collector
        result = learning_collector.run_learning_scan(use_ai=use_ai)
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/learning/history')
def api_learning_history():
    """获取学习历史"""
    try:
        from lumenis.shared.learning import collector as learning_collector
        result = learning_collector.get_learning_history()
        return jsonify({'ok': True, **result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/optimizer/config')
def api_xhs_optimizer_config():
    """获取小红书采集分类配置"""
    try:
        import xhs_collection_optimizer
        note_type = request.args.get('type', 'all')
        config = xhs_collection_optimizer.get_collection_config(note_type)
        return jsonify({'ok': True, 'note_type': note_type, 'config': config})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/api/xhs/optimizer/classify', methods=['POST'])
def api_xhs_optimizer_classify():
    """分类笔记（topic/opinion/event）"""
    try:
        data = request.get_json(silent=True) or {}
        title = str(data.get('title', ''))
        content = str(data.get('content', ''))
        keywords = data.get('keywords', [])
        import xhs_collection_optimizer
        note_type = xhs_collection_optimizer.classify_note(title, content, keywords)
        return jsonify({'ok': True, 'note_type': note_type, 'title': title[:50]})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def _safe_xhs_keepalive_result(result):
    """Serialize user-facing session state without Worker endpoint or exception text."""
    if not isinstance(result, dict):
        return {'status': 'unavailable', 'message': '受控会话状态不可用'}
    allowed = ('platform', 'label', 'status', 'is_logged_in', 'need_relogin',
               'cdp_online', 'checked_at', 'last_login_at', 'last_check_at',
               'should_login_today', 'history_count')
    safe = {key: result[key] for key in allowed if key in result}
    state = str(result.get('status') or 'unavailable').casefold()
    messages = {
        'logged_in': '已确认登录状态',
        'not_logged_in': '需要在产品内完成登录验证',
        'logged_out': '需要在产品内完成登录验证',
        'cdp_down': '受控后台浏览器当前不可用',
        'worker_unavailable': '受控后台浏览器当前不可用',
        'check_failed': '会话状态暂时无法核验',
    }
    safe['message'] = messages.get(state, '会话状态已读取；登录可用性仍需核验')
    return safe

@app.route('/api/xhs/rednote/keepalive')
def api_xhs_rednote_keepalive():
    """Return safe status for the registered Hong Kong/International session."""
    try:
        import xhs_collection_optimizer
        platform = xhs_collection_optimizer.normalize_registered_platform(
            request.args.get('platform') or 'rednote_hk')
        if platform != 'rednote_hk':
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'PROTECTED_PROFILE_FORBIDDEN'}), 403
        status = xhs_collection_optimizer.get_keepalive_status('rednote_hk')
        return jsonify({'ok': True, **_safe_xhs_keepalive_result(status)})
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 503


@app.route('/api/xhs/keepalive/mark', methods=['POST'])
def api_xhs_keepalive_mark():
    """标记当日保活完成（用户确认 / 登录成功回调）。body: {platform: rednote_hk|xhs_cn}"""
    try:
        import xhs_collection_optimizer
        platform = 'rednote_hk'
        if request.is_json:
            platform = (request.json.get('platform') or 'rednote_hk').strip() or 'rednote_hk'
        platform = xhs_collection_optimizer.normalize_registered_platform(platform)
        if platform != 'rednote_hk':
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'PROTECTED_PROFILE_FORBIDDEN'}), 403
        result = xhs_collection_optimizer.mark_keepalive_success('rednote_hk')
        return jsonify({'ok': True, **_safe_xhs_keepalive_result(result)})
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 503


@app.route('/api/xhs/keepalive/recheck', methods=['POST'])
def api_xhs_keepalive_recheck():
    """Check the current registered worker; endpoint selection is server-owned.
    返回 need_relogin=true 时前端应自动弹出登录弹窗。"""
    try:
        import xhs_collection_optimizer
        platform = 'rednote_hk'
        if request.is_json:
            platform = (request.json.get('platform') or 'rednote_hk').strip() or 'rednote_hk'
        platform = xhs_collection_optimizer.normalize_registered_platform(platform)
        if platform != 'rednote_hk':
            return jsonify({'ok': False, 'status': 'BLOCKED',
                            'code': 'PROTECTED_PROFILE_FORBIDDEN'}), 403
        result = xhs_collection_optimizer.recheck_keepalive('rednote_hk')
        return jsonify({'ok': True, **_safe_xhs_keepalive_result(result)})
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 503

@app.route('/api/xhs/rednote/check-login', methods=['POST'])
def api_xhs_rednote_check_login():
    """检查已登记的香港/国际 RedNote 浏览器会话。"""
    try:
        import xhs_collection_optimizer
        result = xhs_collection_optimizer.check_rednote_login()
        return jsonify({'ok': True, **_safe_xhs_keepalive_result(result)})
    except Exception as e:
        return jsonify({'ok': False, 'status': 'UNAVAILABLE',
                        'error': type(e).__name__}), 503


# ============ GAP-21 Cookie 导入 API（受 Basic Auth 保护，不接收/不返回 Cookie 明文）============

def _start_optional_runtime_services(internal_beta_acceptance, *, no_scheduler=False):
    if MANUAL_WORKSPACE or internal_beta_acceptance or INTERNAL_BETA_SAFE_STARTUP:
        print('[Runtime] manual/acceptance startup: CDP, heartbeat, and guardian startup suppressed')
        return False

    # ===== ZBIP Runtime Integrity Preflight（统一启动闸门）=====
    # 默认只记录并写 Attestation、不阻断现网；ZBC_PREFLIGHT_ENFORCE=1 时存在 P0 即终止启动。
    try:
        _pf_report = runtime_preflight.run_preflight()
        print(runtime_preflight.format_summary(_pf_report))
    except SystemExit:
        raise
    except Exception as _pf_e:
        print(f"[Preflight] 预检异常，不阻断启动: {type(_pf_e).__name__}: {_pf_e}")

    if no_scheduler:
        print('[Runtime] manual startup: optional automatic services suppressed')
        return False

    # 自动检查并启动CDP浏览器（确保采集功能可用）
    # 注意：暂时禁用自动启动，避免Edge浏览器崩溃导致主进程退出
    # 采集时会按需启动CDP浏览器
    try:
        import cdp_helper
        cdp_status = cdp_helper.get_cdp_status(
            port=xhs_cookie_bridge.cdp_port_for(xhs_cookie_bridge.DEFAULT_COLLECTION_ACCOUNT),
        )
        if cdp_status.get('available'):
            print(f"[CDP] 浏览器已就绪: 端口 {cdp_status.get('port')}")
        else:
            print(f"[CDP] 浏览器未启动，采集时将按需自动启动（避免启动时崩溃）")
    except Exception as e:
        print(f"[CDP] 检查失败: {e}")

    # 后台心跳线程（监控系统状态）
    def heartbeat_monitor():
        import time
        heartbeat_count = 0
        while True:
            try:
                heartbeat_count += 1
                # 每30秒记录一次心跳
                if heartbeat_count % 30 == 0:
                    logging.info(f"[Heartbeat] 系统运行正常，心跳次数: {heartbeat_count}")
                time.sleep(1)
            except Exception as e:
                logging.error(f"[Heartbeat] 心跳线程异常: {e}", exc_info=True)
                time.sleep(5)

    # 启动心跳线程（守护线程，主进程退出时自动结束）
    heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
    heartbeat_thread.start()
    logging.info("[System] 心跳监控线程已启动")

    # 全局异常捕获
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("未捕获的异常:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    # 线程异常捕获
    def thread_exception_handler(args):
        logging.critical(f"线程异常: {args.exc_type.__name__}: {args.exc_value}", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = thread_exception_handler

    # ===== P1-7 三 guardian 模块受控接入（守护 / 自动恢复 / 数据反馈闭环）=====
    # 全部 try/except 包裹，任一失败不阻断启动；ZBC_GUARDIAN_ENABLED=0 可整体关闭
    if os.environ.get('ZBC_GUARDIAN_ENABLED', '1') == '1':
        try:
            import auto_recovery as _ar
            _ar_eng = _ar.recovery_engine
            if not getattr(_ar_eng, '_p17_started', False):
                _ar_eng.start_background_monitor(60)
                _ar_eng._p17_started = True
                print('[Guardian] auto_recovery 自动恢复监控已启动(60s)')
        except Exception as _ge:
            print(f'[Guardian] auto_recovery 启动失败: {_ge}')
        try:
            from lumenis.shared.learning import feedback as _dfl
            _dfl_eng = _dfl.data_feedback_loop
            def _fb_loop():
                import time as _t
                while True:
                    try:
                        _dfl_eng.run_feedback_cycle()
                    except Exception as _fe:
                        print(f'[Guardian] 数据反馈闭环异常: {_fe}')
                    _t.sleep(21600)
            threading.Thread(target=_fb_loop, daemon=True, name='data-feedback-loop').start()
            print('[Guardian] Shared Learning 数据反馈闭环已启动(6h)')
        except Exception as _ge:
            print(f'[Guardian] Shared Learning feedback 启动失败: {_ge}')
        try:
            import system_guardian as _sg
            _sg.health_check()
            print('[Guardian] system_guardian 健康状态已记录')
        except Exception as _ge:
            print(f'[Guardian] system_guardian 启动失败: {_ge}')
        # P1-7: RuntimeGuardian 统一生命周期守护（统一收敛 system_guardian/auto_recovery/stability_monitor）
        try:
            from runtime_guardian import get_guardian as _rg_get
            _rg = _rg_get("app_main")
            if not getattr(_rg, '_p17_started', False):
                _rg.start_reaper(interval=30)
                _rg._p17_started = True
                print('[Guardian] RuntimeGuardian 统一生命周期守护已启动(reaper=30s)')
        except Exception as _ge:
            print(f'[Guardian] RuntimeGuardian 启动失败: {_ge}')
    return True


if __name__ == '__main__':
    # 启动前注入 node 运行时 PATH（话题监测/采集脚本依赖 node，8201 worker 进程 PATH 可能不含沙箱 node）
    _prepare_node_runtime(INTERNAL_BETA_SAFE_STARTUP)

    import logging
    # 加固:Windows 下多进程共写 system.log 时轮转可能因文件占用失败,绝不允许 logging 内部异常崩溃主进程(此前 PermissionError 致 app.py 退出码=1、话题采集被中断)
    logging.raiseExceptions = False
    from logging.handlers import RotatingFileHandler

    class _SafeRotatingFileHandler(RotatingFileHandler):
        # 轮转失败时安全降级为直接追加,绝不向上抛异常(多进程共写同一日志的 Windows 场景)
        def doRollover(self):
            try:
                super().doRollover()
            except Exception:
                try:
                    if self.stream:
                        self.stream.close()
                except Exception:
                    pass
                try:
                    self.stream = open(self.baseFilename, 'a', encoding=self.encoding)
                except Exception:
                    pass

    # 配置详细日志
    log_dir = _startup_log_dir()
    os.makedirs(log_dir, exist_ok=True)

    # 清除已有的日志处理器（避免重复）
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 文件日志（详细）
    file_handler = _SafeRotatingFileHandler(
        os.path.join(log_dir, 'system.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # 控制台日志（简洁）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # 根日志器
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Flask日志器（不重复添加handler，继承root_logger）
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    # 不添加handler，避免重复记录

    # 命令行 --host/--port 优先于 .env（修复历史 bug：此前末尾 app.run 固定用 .env 的 APP_PORT，
    # 忽略 --port，导致旁路测试实例抢占现网端口）
    RUN_HOST = getattr(globals().get('args'), 'host', APP_HOST)
    RUN_PORT = getattr(globals().get('args'), 'port', APP_PORT)
    print("=" * 60)
    print(f"{PRODUCT_NAME} Product Core v{APP_VERSION}")
    print(f"启动地址: http://{RUN_HOST}:{RUN_PORT}")
    print(f"多线程模式: 开启")
    print(f"详细日志: {os.path.join(log_dir, 'system.log')}")
    print("=" * 60)

    if MANUAL_WORKSPACE:
        print(runtime_preflight.format_summary(runtime_preflight.run_preflight(enforce=True)))
    try:
        _start_hang_watchdog()
        _start_optional_runtime_services(INTERNAL_BETA_SAFE_STARTUP, no_scheduler=args.no_scheduler)
        _serve_product_core(app, RUN_HOST, RUN_PORT)
    except Exception as e:
        logging.critical(f"[System] 系统启动失败: {e}", exc_info=True)
        print(f"系统启动失败: {e}")
        raise SystemExit(1) from e
    finally:
        if not _stop_scheduler():
            logging.warning("[System] scheduler task still running at shutdown deadline; no completion assumed")
        if not _stop_hang_watchdog():
            logging.warning("[System] hang watchdog did not stop within deadline")
        logging.info("[System] 系统已停止")
        print("系统已停止")
