"""
pytest配置文件 - 广州太古汇舆情监测系统
"""
import os
import sys
import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 排除纯脚本式 test_ 文件（模块级 sys.exit 会在收集期杀掉 pytest 进程）
# 这些文件无 def test_，设计为 `python tests/xxx.py` 独立运行，不纳入 pytest 收集
collect_ignore = [
    "test_agent_combined_shardB.py",
    "test_guard_wiring.py",
    "test_security_scan.py",
    "test_t2_resilience.py",
    "test_title_fallback.py",
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
    """Reset known global-state modules before every test for full-suite isolation.

    Some modules (ai_channel, kos_metrics, kos_attribution) hold module-level
    mutable state that earlier tests may mutate and not restore.  This fixture
    guarantees a clean slate regardless of test ordering.
    """
    import importlib
    # --- ai_channel ---
    try:
        import ai_channel
        _saved_aicb = getattr(ai_channel, 'CircuitBreaker', None)
        _saved_aibr = getattr(ai_channel, 'breaker', None)
        _saved_aipb = getattr(ai_channel, '_provider_breakers', None)
    except Exception:
        _saved_aicb = _saved_aibr = _saved_aipb = None
    # --- kos_metrics ---
    try:
        import kos_metrics
        _saved_kmpr = getattr(kos_metrics, 'PLATFORM_RULES', None)
    except Exception:
        _saved_kmpr = None
    # --- kos_attribution ---
    try:
        import kos_attribution
        _saved_kacache = getattr(kos_attribution, '_attr_config_cache', None)
    except Exception:
        _saved_kacache = None
    yield
    # Restore
    try:
        import ai_channel
        if _saved_aicb is not None:
            ai_channel.CircuitBreaker = _saved_aicb
        if _saved_aibr is not None:
            ai_channel.breaker = _saved_aibr
        if _saved_aipb is not None:
            ai_channel._provider_breakers = _saved_aipb
    except Exception:
        pass
    try:
        import kos_metrics
        if _saved_kmpr is not None:
            kos_metrics.PLATFORM_RULES = _saved_kmpr
    except Exception:
        pass
    try:
        import kos_attribution
        if _saved_kacache is not None:
            kos_attribution._attr_config_cache = _saved_kacache
    except Exception:
        pass


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
