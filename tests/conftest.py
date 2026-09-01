"""
pytest配置文件 - 广州太古汇舆情监测系统
"""
import os
import sys
import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试配置
TEST_CONFIG = {
    'test_db': 'data/test_monitor.db',
    'test_port': 8201,
    'test_host': '127.0.0.1',
    'auth_user': 'Zachary',
    'auth_pass': 'ID082610',
}

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
