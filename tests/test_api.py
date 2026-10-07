"""
API测试 - 广州太古汇舆情监测系统
"""
import os
import sys
import pytest
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def auth_headers():
    """认证请求头"""
    auth = base64.b64encode(b"Zachary:Zachary01").decode()
    return {'Authorization': f'Basic {auth}'}

class TestDashboardAPI:
    """仪表盘API测试"""

    def test_dashboard_all(self, client, auth_headers):
        """测试仪表盘汇总API"""
        response = client.get('/api/dashboard/all', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert 'overview' in data
        assert 'stats' in data

    def test_stats_api(self, client, auth_headers):
        """统计接口必须具备明确的业务域选择；Basic Auth 不代表业务范围。"""
        response = client.get('/api/stats', headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['code'] == 'DOMAIN_SELECTION_REQUIRED'

    def test_overview_api(self, client, auth_headers):
        """概览接口不从历史主体或进程默认值推断业务域。"""
        response = client.get('/api/overview', headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['code'] == 'DOMAIN_SELECTION_REQUIRED'

class TestNotesAPI:
    """笔记API测试"""

    def test_notes_list(self, client, auth_headers):
        """笔记列表不能把认证身份误当作已选择的业务域。"""
        response = client.get('/api/notes?page=1&per_page=10', headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['code'] == 'DOMAIN_SELECTION_REQUIRED'

    def test_notes_detail(self, client, auth_headers):
        """精确详情查询也需要显式业务域，不能继承隐式广州主体。"""
        response = client.get('/api/notes/known-note-id', headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['code'] == 'DOMAIN_SELECTION_REQUIRED'

class TestEventsAPI:
    """事件API测试"""

    def test_events_list(self, client, auth_headers):
        """事件查询也不能从认证身份推断业务域。"""
        response = client.get('/api/events', headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data['ok'] is False
        assert data['code'] == 'DOMAIN_SELECTION_REQUIRED'

class TestAIAPI:
    """AI API测试"""

    def test_ai_status(self, client, auth_headers):
        """测试AI状态API"""
        response = client.get('/api/ai/status', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

    def test_ark_status(self, client, auth_headers):
        """测试豆包AI状态API"""
        response = client.get('/api/ark/status', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'ok' in data

class TestSystemAPI:
    """系统API测试"""

    def test_system_health(self, client, auth_headers, monkeypatch):
        """测试系统健康检查API及默认禁用的历史发现配置。"""
        monkeypatch.delenv('TAIKOO_WEB_DISCOVERY', raising=False)
        response = client.get('/api/system/health', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['health']['web_discovery_enabled'] is False
        assert data['health']['ai']['provider'] == 'owned'
        assert data['health']['ai']['fallback_allowed'] is False

    def test_system_status(self, client, auth_headers, monkeypatch):
        """SYSTEM 状态保留采集历史，但业务统计留在明确范围的接口。"""
        monkeypatch.delenv('TAIKOO_WEB_DISCOVERY', raising=False)
        response = client.get('/api/status', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['collector'] == 'SYSTEM Collector / source-specific adapters'
        assert data['data_source'] == 'Source → Evidence → Canonical'
        assert data['ai_provider'] == 'owned'
        assert data['ai_fallback_allowed'] is False
        assert data['last_collection_semantics'] == 'historical_observation_not_current_readiness'
        assert data['web_discovery_enabled'] is False
        assert data['total_notes'] is None
        assert data['verified_notes'] is None
        assert data['business_metrics_state'] == 'SCOPE_REQUIRED'

class TestAuthAPI:
    """认证API测试"""

    def test_without_auth(self, client):
        """测试无认证访问"""
        response = client.get('/api/dashboard/all')
        assert response.status_code == 401

    def test_with_wrong_auth(self, client):
        """测试错误认证"""
        auth = base64.b64encode(b"wrong:wrong").decode()
        headers = {'Authorization': f'Basic {auth}'}
        response = client.get('/api/dashboard/all', headers=headers)
        assert response.status_code == 401
