"""
pytest配置文件 - 广州太古汇舆情监测系统
"""
import os
import sys
import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
def _global_state_isolation():
    """每个用例前后把已知模块级"可变全局状态"重置到干净基线，保证完整套件任意顺序隔离。

    关键教训：必须重置对象的【内部状态】(dict.clear / breaker.reset / logger.setLevel)，
    仅"保存-恢复对象引用"无法清除用例对该对象内部做的修改（早期版本把 _PROVIDER_BREAKERS
    大小写写错成 _provider_breakers，getattr 恒为 None，provider 熔断状态从未被重置，
    导致 zhipu breaker 被前置用例打到 OPEN 后泄漏、route_with_fallback 跳过 zhipu）。
    """
    import logging as _logging

    # --- logging 全局状态快照（level/disable 是值类型，保存-恢复有效）---
    _root_logger = _logging.getLogger()
    _saved_root_level = _root_logger.level
    _saved_disable = _logging.root.manager.disable
    _saved_logger_levels = {
        n: lg.level for n, lg in _logging.Logger.manager.loggerDict.items()
        if isinstance(lg, _logging.Logger)
    }
    # os.environ 中易被测试裸设且不还原的变量（多个测试模块级 os.environ['ZBC_DB_PATH']=...
    # 会污染整个 pytest 进程，导致延迟 import 的模块 DB_PATH 指向别人的临时库）
    _ENV_LEAK_KEYS = ('ZBC_DB_PATH',)
    _saved_env = {k: os.environ.get(k) for k in _ENV_LEAK_KEYS if k in os.environ}

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
    yield
    _reset_global_state()

    # --- 恢复 logging：解除任何全局抑制、还原 root 与各具名 logger 级别 ---
    try:
        _logging.disable(_saved_disable)
        _root_logger.setLevel(_saved_root_level)
        for _name, _lvl in _saved_logger_levels.items():
            _logging.getLogger(_name).setLevel(_lvl)
    except Exception:
        pass

    # --- 恢复 os.environ 易泄漏变量，杜绝 ZBC_DB_PATH 跨用例污染 ---
    try:
        for _k, _v in _saved_env.items():
            if _v is None:
                os.environ.pop(_k, None)
            else:
                os.environ[_k] = _v
        for _k in _ENV_LEAK_KEYS:
            if _k not in _saved_env:
                os.environ.pop(_k, None)
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
    from permission_gate import set_testing_bypass
    set_testing_bypass(True)
    yield
    set_testing_bypass(False)
