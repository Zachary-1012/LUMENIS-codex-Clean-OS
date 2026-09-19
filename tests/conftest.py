"""
pytest配置文件 - 广州太古汇舆情监测系统
"""
import os
import sys
import atexit
import shutil
import tempfile
import pytest
import sqlite3 as _sqlite3_guard
import traceback as _traceback_guard
from urllib.parse import unquote as _uri_unquote

# 添加项目根目录到Python路径
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

# P0-C 测试数据库总隔离：在任何测试模块被收集/import 前，把本机候选库复制到
# OS 临时目录，并让所有 Canonical DB 入口只指向该副本。这样既保留真实 schema/fixture
# 基线，也不会因“全局空库”制造假失败，更不会让普通测试写回仓库或生产候选数据库。
_PYTEST_DB_ROOT = tempfile.mkdtemp(prefix="lumenis-pytest-")
_PYTEST_DB_PATH = os.path.join(_PYTEST_DB_ROOT, "monitor-test-copy.db")
_LOCAL_CANDIDATE_DB = os.path.join(_REPO_ROOT, "data", "monitor.db")
_EXPLICIT_TEST_SEED_DB = os.environ.get("LUMENIS_TEST_SEED_DB", "").strip()


def _dotenv_path(name: str, dotenv_path: str) -> str:
    """Read one non-secret path setting without loading the whole .env file."""
    try:
        with open(dotenv_path, encoding="utf-8") as _f:
            for _raw in _f:
                _line = _raw.strip()
                if not _line or _line.startswith("#") or not _line.startswith(name + "="):
                    continue
                _value = _line.split("=", 1)[1].strip().strip('"').strip("'")
                return os.path.expandvars(_value)
    except OSError:
        pass
    return ""


def _existing_seed(*candidates: str) -> str:
    """Choose the first existing read-only seed, preserving CI fallback behavior."""
    for _candidate in candidates:
        if _candidate and os.path.isfile(_candidate):
            return os.path.abspath(_candidate)
    return _LOCAL_CANDIDATE_DB


# The production launcher keeps the canonical runtime DB outside the checkout.
# Prefer that path only as a read-only seed; every test still receives its own
# OS-temp copy and the sqlite guard is installed before any test executes.
_ENV_TEST_SEED_DB = os.environ.get("ZBC_DB_PATH", "").strip()
_DOTENV_TEST_SEED_DB = _dotenv_path("ZBC_DB_PATH", os.path.join(_REPO_ROOT, ".env"))
_TEST_SEED_DB = _existing_seed(
    _EXPLICIT_TEST_SEED_DB,
    _ENV_TEST_SEED_DB,
    _DOTENV_TEST_SEED_DB,
    _LOCAL_CANDIDATE_DB,
)
if os.path.isfile(_TEST_SEED_DB):
    # The source is read-only test input. SQLite backup gives a consistent
    # snapshot when the production DB is live/WAL-enabled; all tests operate on
    # the temporary destination only.
    try:
        _src = _sqlite3_guard.connect(
            f"file:{_TEST_SEED_DB}?mode=ro", uri=True, timeout=10
        )
        _dst = _sqlite3_guard.connect(_PYTEST_DB_PATH, timeout=10)
        try:
            _src.backup(_dst)
        finally:
            _src.close()
            _dst.close()
    except Exception:
        # CI may provide a non-SQLite placeholder; preserve the existing
        # behavior so the test process can report the actual fixture failure.
        shutil.copy2(_TEST_SEED_DB, _PYTEST_DB_PATH)
else:
    # CI/新机器允许从空文件开始；具体迁移测试必须自行初始化 schema，不能回退生产路径。
    open(_PYTEST_DB_PATH, "ab").close()
for _db_key in (
    "ZBC_DB_PATH",
    "ZBC_EVIDENCE_DB_PATH",
    "ZBC_RUNTIME_GUARDIAN_DB",
    "ZBC_TOKEN_DB_PATH",
):
    os.environ[_db_key] = _PYTEST_DB_PATH

# Hard Gate: tests may never open the repository-default SQLite database. This
# catches legacy literal paths even when application code swallows the exception.
_REAL_SQLITE_CONNECT = _sqlite3_guard.connect
_REPOSITORY_DEFAULT_DB = os.path.normcase(os.path.abspath(_LOCAL_CANDIDATE_DB))
_REPOSITORY_DB_VIOLATIONS = []


def _connection_target(database):
    raw = os.fspath(database) if isinstance(database, os.PathLike) else str(database)
    if raw == ":memory:":
        return None
    if raw.startswith("file:"):
        raw = _uri_unquote(raw[5:].split("?", 1)[0])
        if raw.startswith("/") and len(raw) > 2 and raw[2] == ":":
            raw = raw[1:]
    return os.path.normcase(os.path.abspath(raw))


def _guarded_sqlite_connect(database, *args, **kwargs):
    target = _connection_target(database)
    if target == _REPOSITORY_DEFAULT_DB:
        _REPOSITORY_DB_VIOLATIONS.append("".join(_traceback_guard.format_stack(limit=8)))
        raise RuntimeError(
            "[P0-C TEST DB GATE] repository data/monitor.db is forbidden; "
            "use ZBC_DB_PATH or tmp_path"
        )
    return _REAL_SQLITE_CONNECT(database, *args, **kwargs)


_sqlite3_guard.connect = _guarded_sqlite_connect


@pytest.fixture(autouse=True)
def _assert_no_repository_db_connection():
    before = len(_REPOSITORY_DB_VIOLATIONS)
    yield
    assert len(_REPOSITORY_DB_VIOLATIONS) == before, (
        "test attempted repository data/monitor.db connection:\n" +
        "\n---\n".join(_REPOSITORY_DB_VIOLATIONS[before:before + 3])
    )


def _cleanup_pytest_db_root():
    shutil.rmtree(_PYTEST_DB_ROOT, ignore_errors=True)


atexit.register(_cleanup_pytest_db_root)

# 排除纯脚本式 test_ 文件（模块级顶层 sys.exit 会在 pytest 收集/import 期杀掉整个进程，
# 表现为全量跑到某百分比静默退出、无 F、stderr 为空）。文件无 def test_，设计为
# `python tests/xxx.py` 独立运行；仅排除出 pytest 收集，文件保留不删。清单经 AST 全量扫描核对。
collect_ignore = [
    "test_agent_combined_shardB.py",  # L78,132 top-level exit
    "test_guard_wiring.py",           # L47 top-level exit
    "test_health_center.py",          # L77 top-level exit
    "test_scheduling.py",             # L183 top-level exit
    "test_security_scan.py",          # L61 top-level exit
    "test_t2_resilience.py",          # L184,186 top-level exit
    "test_title_fallback.py",         # L36 top-level exit
    "test_version_api.py",            # L25 top-level exit
]

# 测试配置
TEST_CONFIG = {
    'test_db': 'data/test_monitor.db',
    'test_port': 8201,
    'test_host': '127.0.0.1',
    'auth_user': 'Zachary',
    'auth_pass': 'Zachary01',
}

# 测试鉴权隔离（P1-9 权限审计修复）：
# app.py 在 import 时经 _load_dotenv 读取 .env，但只填充「环境变量中不存在」的 key。
# 因此在 import app 之前强制注入测试专用凭证，使测试自洽、可重复、不依赖 .env 真实密码，
# 也避免真实生产凭证被测试日志/断言回显。dev_exec_guard 等鉴权用例据此拿到一致凭证。
os.environ['TAIKOO_AUTH_USER'] = TEST_CONFIG['auth_user']
os.environ['TAIKOO_AUTH_PASSWORD'] = TEST_CONFIG['auth_pass']

# 测试默认离线：禁止任何真实云端 AI 网络（智谱/ARK/千问）。漏 mock 的用例若走到云端，
# intelligence._call_cloud 会立即抛 ConnectionError 并按生产降级链走 rule 兜底，
# 而不是在 ssl.read 上长等待（90s*3）冻结整个测试进程。需要真实云端的测试须显式
# monkeypatch.delenv('ZBC_TEST_OFFLINE', raising=False) 并自行负责网络与耗时。
os.environ.setdefault('ZBC_TEST_OFFLINE', '1')

# conftest 由 pytest 在 collect tests/ 下任何测试模块【之前】导入，此处记录的是尚未被
# 测试模块级 os.environ 污染的会话干净基线（如 ZBC_DB_PATH）。某些隔离测试
# （test_workspace_keys 等）在模块顶层把 ZBC_DB_PATH 指向临时空库，collect 期即全局生效、
# 字母序最后的还会覆盖前者，导致后续实时读 environ 的生产代码（api_dual_domain._get_db_path）
# 连到无表临时库返回 500。用此基线在每个"不自行设置该变量"的用例运行前还原。
_ENV_SESSION_BASELINE = {'ZBC_DB_PATH': os.environ.get('ZBC_DB_PATH')}
# 完整会话环境基线：任何用例（含其函数体内 os.environ 裸设）结束后，非自理模块一律回到此基线，
# 杜绝 AI_PROVIDER/API_KEY/OLLAMA_BASE_URL/ZBC_* 等泄漏给后续用例、importlib.reload(app) 与子进程。
_ENV_CANONICAL = dict(os.environ)
_MODULE_SETS_ENV_CACHE = {}

def _module_self_sets_env(mod, key='ZBC_DB_PATH'):
    """测试模块自身源码是否会【写/删/setdefault】该环境变量（顶层语句或 module/function
    fixture 内都算"自理"）。自理模块（如 ic_contracts_p2 用 module fixture 强制临时库、
    workspace_keys 顶层指定隔离库）的设置必须保留，护栏不得干预；只有源码完全不写该变量
    的受害模块（如 api_dual_domain 只 get 读取），才在 setup 恢复会话基线、清除 collect 期
    其它模块顶层遗留的全局污染。"""
    if mod is None:
        return False
    ident = getattr(mod, '__file__', None)
    if ident is None:
        return False
    _ck = (ident, key)
    if _ck in _MODULE_SETS_ENV_CACHE:
        return _MODULE_SETS_ENV_CACHE[_ck]
    import re as _re
    # 任意缩进位置：os.environ["KEY"]=（赋值，排除==）、.update(、.setdefault(、.pop("KEY"
    _pat = _re.compile(
        r"os\.environ\s*(?:\[\s*['\"]" + _re.escape(key) + r"['\"]\s*\]\s*=(?!=)"
        r"|\.update\s*\(|\.setdefault\s*\(|\.pop\s*\(\s*['\"]" + _re.escape(key) + r")"
    )
    sets = False
    try:
        with open(ident, encoding='utf-8', errors='replace') as _fh:
            sets = any(_pat.search(_ln) for _ln in _fh)
    except OSError:
        sets = False
    _MODULE_SETS_ENV_CACHE[_ck] = sets
    return sets

def _restore_env_baseline(key='ZBC_DB_PATH'):
    _bv = _ENV_SESSION_BASELINE.get(key)
    if _bv is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = _bv

@pytest.fixture(autouse=True)
def _env_full_restore(request):
    """全环境键隔离：进入用例前快照，用例结束后对所有变化键三向还原。
    - 当前模块源码自理该键（顶层/函数内会写它，如隔离测试指定临时库）：还原到进入用例时的值，
      保证同模块后续用例仍可见其模块级设置；
    - 其余模块（受害方）：一律回到会话基线 _ENV_CANONICAL（基线没有则删除），
      使 importlib.reload(app) 与 subprocess 子进程继承到的是干净环境而非前置用例泄漏。
    PYTEST_CURRENT_TEST 由 pytest 自身管理，不干预。"""
    _enter_env = dict(os.environ)
    _mod = getattr(request, 'module', None)
    yield
    _all_keys = set(os.environ) | set(_enter_env) | set(_ENV_CANONICAL)
    for _k in _all_keys:
        if _k == 'PYTEST_CURRENT_TEST':
            continue
        try:
            if _module_self_sets_env(_mod, _k):
                _ev = _enter_env.get(_k)
                if _ev is None:
                    os.environ.pop(_k, None)
                else:
                    os.environ[_k] = _ev
            else:
                _cv = _ENV_CANONICAL.get(_k)
                if _cv is None:
                    os.environ.pop(_k, None)
                else:
                    os.environ[_k] = _cv
        except Exception:
            pass

@pytest.fixture(scope='session')
def app():
    """创建Flask应用实例"""
    from app import app
    app.config['TESTING'] = True
    return app

@pytest.fixture(scope='session')
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture(scope='session')
def auth_headers():
    """认证请求头"""
    import base64
    auth = base64.b64encode(f"{TEST_CONFIG['auth_user']}:{TEST_CONFIG['auth_pass']}".encode()).decode()
    return {'Authorization': f'Basic {auth}'}

@pytest.fixture(scope='function')
def db():
    """数据库连接"""
    import database as db_module
    conn = db_module.get_connection()
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def _global_state_isolation(request):
    """每个用例前后把已知模块级"可变全局状态"重置到干净基线，保证完整套件任意顺序隔离。

    关键教训：必须重置对象的【内部状态】(dict.clear / breaker.reset / logger.setLevel)，
    仅"保存-恢复对象引用"无法清除用例对该对象内部做的修改（早期版本把 _PROVIDER_BREAKERS
    大小写写错成 _provider_breakers，getattr 恒为 None，provider 熔断状态从未被重置，
    导致 zhipu breaker 被前置用例打到 OPEN 后泄漏、route_with_fallback 跳过 zhipu）。
    """
    import logging as _logging

    # --- logging 全局状态快照（level/disable/handlers/disabled/propagate 全维度）---
    _root_logger = _logging.getLogger()
    _saved_root_level = _root_logger.level
    _saved_disable = _logging.root.manager.disable
    _saved_root_handlers = list(_root_logger.handlers)
    _saved_logger_state = {}
    for _n, _lg in list(_logging.Logger.manager.loggerDict.items()):
        if isinstance(_lg, _logging.Logger):
            _saved_logger_state[_n] = (_lg.level, _lg.disabled, _lg.propagate,
                                       list(_lg.handlers))
    # os.environ 中易被测试裸设且不还原的变量（多个测试模块级 os.environ['ZBC_DB_PATH']=...
    # 会污染整个 pytest 进程，导致延迟 import 的模块 DB_PATH 指向别人的临时库）
    _ENV_LEAK_KEYS = ('ZBC_DB_PATH',)
    _saved_env = {k: os.environ.get(k) for k in _ENV_LEAK_KEYS if k in os.environ}
    # 当前用例模块自身是否在顶层设置 ZBC_DB_PATH（隔离测试需要自己的临时库，予以保留；
    # 其余模块用例运行前一律恢复会话基线，清除 collect 期其它模块遗留的全局污染）
    _self_sets_env = _module_self_sets_env(getattr(request, 'module', None))

    def _reset_global_state():
        # ai_channel：清空每-provider 熔断器（get 时按 CLOSED 重建）+ 复位全局 breaker
        try:
            import ai_channel
            _pb = getattr(ai_channel, '_PROVIDER_BREAKERS', None)
            if isinstance(_pb, dict):
                _pb.clear()
            _gb = getattr(ai_channel, 'breaker', None)
            if _gb is not None and hasattr(_gb, 'reset'):
                _gb.reset()
        except Exception:
            pass
        # kos_metrics：重新加载平台规则到基线
        try:
            import kos_metrics
            if hasattr(kos_metrics, 'reload_platform_rules'):
                kos_metrics.reload_platform_rules()
        except Exception:
            pass
        # kos_attribution：重载归因配置到默认基线（不能 .clear() 成空 dict，
        # 否则 load_attribution_config 误判缓存有效返回 {}，触发 KeyError: attribution_weights）
        try:
            import kos_attribution
            if hasattr(kos_attribution, 'reload_attribution_config'):
                kos_attribution.reload_attribution_config()
            else:
                kos_attribution._attr_config_cache = None
        except Exception:
            pass

    _reset_global_state()
    # 当前模块不自行顶层设置 ZBC_DB_PATH 时，清除 collect 期其它隔离测试遗留的全局污染，
    # 让实时读 environ 的生产代码（如 api_dual_domain）连回会话基线库而非别人的临时空库
    if not _self_sets_env:
        _restore_env_baseline()
    yield
    _reset_global_state()

    # --- 恢复 logging 全维度：level/disable/disabled/propagate/handlers ---
    # 关键：alembic env.py 的 fileConfig（disable_existing_loggers）等会禁用业务 logger、
    # 清空 root handlers（摘掉 pytest caplog），必须逐维度还原，否则后续用例 caplog 失效。
    try:
        _logging.disable(_saved_disable)
        _root_logger.setLevel(_saved_root_level)
        # root handlers：移除用例期间新增的，补回用例期间被移除的
        for _h in list(_root_logger.handlers):
            if _h not in _saved_root_handlers:
                _root_logger.removeHandler(_h)
        for _h in _saved_root_handlers:
            if _h not in _root_logger.handlers:
                _root_logger.addHandler(_h)
        for _name, (_lvl, _dis, _prop, _hdlrs) in _saved_logger_state.items():
            _lg = _logging.getLogger(_name)
            _lg.setLevel(_lvl)
            _lg.disabled = _dis
            _lg.propagate = _prop
            for _h in list(_lg.handlers):
                if _h not in _hdlrs:
                    _lg.removeHandler(_h)
            for _h in _hdlrs:
                if _h not in _lg.handlers:
                    _lg.addHandler(_h)
    except Exception:
        pass

    # --- 恢复 os.environ，杜绝 ZBC_DB_PATH 跨用例/跨模块污染 ---
    # 自身顶层设置的隔离模块：恢复其进入用例时的值（保持模块内临时库一致）；
    # 其余模块：一律回到会话干净基线（未设置则 pop），不把任何临时库泄漏给后续模块。
    try:
        if _self_sets_env:
            for _k, _v in _saved_env.items():
                if _v is None:
                    os.environ.pop(_k, None)
                else:
                    os.environ[_k] = _v
            for _k in _ENV_LEAK_KEYS:
                if _k not in _saved_env:
                    os.environ.pop(_k, None)
        else:
            for _k in _ENV_LEAK_KEYS:
                _restore_env_baseline(_k)
    except Exception:
        pass


# ==== 线程泄漏诊断探针（阶段1测试隔离）：记录每个用例后新增且未退出的后台 daemon 线程 ====
import threading as _threading
import re as _re_leak
_LEAK_BG_RE = _re_leak.compile(
    r'(ai-channel|reaper|heartbeat|watchdog|scheduler|monitor|collector-|feedback|'
    r'recovery|memory|lifecycle|campaign|proxy-health|screencast|worker)', _re_leak.I)
THREAD_LEAK_REPORT = []


@pytest.fixture(autouse=True)
def _thread_leak_guard(request):
    before = {t.ident: t.name for t in _threading.enumerate()}
    yield
    leaked = [(t.name) for t in _threading.enumerate()
              if t.ident not in before and t.daemon and _LEAK_BG_RE.search(t.name or '')]
    if leaked:
        THREAD_LEAK_REPORT.append((request.node.nodeid, sorted(set(leaked))))
        try:
            import json as _json
            with open(os.path.join(os.environ.get("TEMP", "/tmp"), "zbc_thread_leak.jsonl"), "a", encoding="utf-8") as _lf:
                _lf.write(_json.dumps({"test": request.node.nodeid, "threads": sorted(set(leaked))}, ensure_ascii=False) + "\n")
        except Exception:
            pass


def pytest_sessionfinish(session, exitstatus):
    # 汇总：线程名 -> 首次泄漏它的用例（去重）
    by_name = {}
    for nodeid, names in THREAD_LEAK_REPORT:
        for nm in names:
            by_name.setdefault(nm, []).append(nodeid)
    lines = ["\n==== THREAD LEAK REPORT (background daemon threads left alive after test) ===="]
    if not by_name:
        lines.append("NO background-thread leak detected.")
    for nm, nodes in sorted(by_name.items()):
        lines.append(f"[{nm}] leaked by {len(nodes)} test(s); e.g. {nodes[:3]}")
    lines.append("==== END THREAD LEAK REPORT ====")
    line = "\n".join(lines)
    print(line)
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(line)

# ==== 出网守卫（阶段1测试隔离）：默认禁止真实公网连接 ====
# 漏 mock 的云端 AI/外部请求在 TCP connect 阶段立即失败（->生产降级 rule 兜底），
# 不在 ssl.read 上长等待(90s*3)冻结整个测试进程；放行回环/内网（本地 8201 online、CDP 9222）。
# 测试在 urllib/requests 层 mock 时根本到不了 socket，故不影响任何上层 mock。
# 确需真实公网的用例设环境变量 ZBC_ALLOW_NETWORK=1 显式放行。
import socket as _socket_guard
import ipaddress as _ipaddress_guard

def _peer_is_public(host):
    if host is None:
        return False
    h = str(host).strip('[]').lower()
    if h in ('localhost', '0.0.0.0', '::', ''):
        return False
    try:
        ip = _ipaddress_guard.ip_address(h)
        return not (ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified)
    except ValueError:
        return True  # 域名直连按公网处理（create_connection 正常会先解析成 IP）

@pytest.fixture(autouse=True)
def _block_real_outbound(monkeypatch):
    if os.environ.get('ZBC_ALLOW_NETWORK') == '1':
        yield
        return
    _real_create_connection = _socket_guard.create_connection
    _RealSocket = _socket_guard.socket

    def _guarded_create_connection(address, *a, **k):
        host = address[0] if isinstance(address, tuple) else address
        if _peer_is_public(host):
            raise ConnectionRefusedError(
                '[test-offline] 真实公网连接被测试守卫阻断，请 mock 网络层: %s' % (host,))
        return _real_create_connection(address, *a, **k)

    class _GuardedSocket(_RealSocket):
        def connect(self, address):
            host = address[0] if isinstance(address, tuple) else address
            if _peer_is_public(host):
                raise ConnectionRefusedError(
                    '[test-offline] 真实公网连接被测试守卫阻断，请 mock: %s' % (host,))
            return _RealSocket.connect(self, address)

        def connect_ex(self, address):
            host = address[0] if isinstance(address, tuple) else address
            if _peer_is_public(host):
                raise ConnectionRefusedError(
                    '[test-offline] 真实公网连接被测试守卫阻断，请 mock: %s' % (host,))
            return _RealSocket.connect_ex(self, address)

    monkeypatch.setattr(_socket_guard, 'create_connection', _guarded_create_connection)
    monkeypatch.setattr(_socket_guard, 'socket', _GuardedSocket)
    yield

# ==== 出网守卫结束 ====

# ==== 线程泄漏探针结束 ====

def pytest_ignore_collect(collection_path, config):
    """GAP-01 统一测试入口：纯脚本式 test_ 文件（全文无 def test_）默认不收集，
    避免 import 期执行真实平台/网络副作用或顶层 sys.exit 打断收集；
    仍可用 `python tests/xxx.py` 手动运行。含 def test_ 的规范用例正常收集。"""
    import re as _re, os as _os
    pp = str(collection_path)
    if _os.path.basename(pp).startswith("test_") and pp.endswith(".py"):
        try:
            txt = open(pp, encoding="utf-8", errors="replace").read()
        except OSError:
            return False
        if not _re.search(r"^\s*def test_", txt, _re.M):
            return True
    return False


@pytest.fixture(scope='session', autouse=True)
def _permission_gate_testing_default():
    """测试环境默认开启 PermissionGate 旁路（业务 API 写操作不被写门拦截），
    权限专项测试模块用 module 级 fixture 覆盖为严格模式。生产默认严格（deny-by-default）。"""
    from lumenis.system.security import set_testing_bypass
    set_testing_bypass(True)
    yield
    set_testing_bypass(False)
