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
    auth = base64.b64encode(b"Zachary:ID082610").decode()
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
        """测试统计API"""
        response = client.get('/api/stats', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

    def test_overview_api(self, client, auth_headers):
        """测试概览API"""
        response = client.get('/api/overview', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

class TestNotesAPI:
    """笔记API测试"""

    def test_notes_list(self, client, auth_headers):
        """测试笔记列表API"""
        response = client.get('/api/notes?page=1&per_page=10', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert 'notes' in data

    def test_notes_detail(self, client, auth_headers):
        """测试笔记详情API"""
        # 先获取一个笔记ID
        response = client.get('/api/notes?page=1&per_page=1', headers=auth_headers)
        data = response.get_json()
        if data.get('notes') and len(data['notes']) > 0:
            note_id = data['notes'][0]['note_id']
            response = client.get(f'/api/notes/{note_id}', headers=auth_headers)
            assert response.status_code == 200

class TestEventsAPI:
    """事件API测试"""

    def test_events_list(self, client, auth_headers):
        """测试事件列表API"""
        response = client.get('/api/events', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

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

    def test_system_health(self, client, auth_headers):
        """测试系统健康检查API"""
        response = client.get('/api/system/health', headers=auth_headers)
        assert response.status_code == 200

    def test_system_status(self, client, auth_headers):
        """测试系统状态API"""
        response = client.get('/api/status', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

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
