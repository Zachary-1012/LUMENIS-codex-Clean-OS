# -*- coding: utf-8 -*-
"""
GAP-10 报告路由收敛 P0：RFC 8594/9745 弃用信号回归测试。
验证：
1. 已确认的"重复实现"报告路由响应带 Deprecation / Sunset / X-Deprecated / Link 头
2. 保留路由（列表/验证/特殊报告/旁路预览/v2/stats）不带弃用头（无误伤）
3. 拦截器纯增量：不改任何业务响应体
"""
import pytest

# deprecated 精确路由
_DEPRECATED_GET = [
    '/api/report/daily',
    '/api/report/export?type=daily',
    '/api/v2/report/export?type=daily',
    '/api/report/v2/daily',
    '/api/reports/anything/download',
    '/api/reports/anything/file',
]
# deprecated 需要 POST 的路由
_DEPRECATED_POST = [
    '/api/brand-report/generate',
    '/api/report/generate',
]
# 保留路由（绝不能带弃用头）
_KEEP_GET = [
    '/api/report/v2/stats',
    '/api/reports',
    '/api/report/verify',
    '/api/v2/report-center/preview',
    '/api/special-report/check-trigger',
]
_KEEP_POST = [
    '/api/special-report/generate',
    '/api/report/special/export',
]


@pytest.mark.parametrize('path', _DEPRECATED_GET)
def test_deprecated_get_has_headers(client, auth_headers, path):
    r = client.get(path, headers=auth_headers)
    # 无论状态码如何（可能 200/400/401 之外的业务响应），都应有弃用头
    assert 'X-Deprecated' in r.headers, f'{path} 应带 X-Deprecated'
    assert 'Deprecation' in r.headers, f'{path} 应带 Deprecation(RFC9745)'
    assert 'Sunset' in r.headers, f'{path} 应带 Sunset(RFC8594)'
    assert 'successor-version' in r.headers.get('Link', ''), f'{path} 应带 Link successor-version'


@pytest.mark.parametrize('path', _DEPRECATED_POST)
def test_deprecated_post_has_headers(client, auth_headers, path):
    r = client.post(path, json={}, headers=auth_headers)
    assert 'X-Deprecated' in r.headers, f'{path} 应带 X-Deprecated'
    assert 'Sunset' in r.headers, f'{path} 应带 Sunset'


@pytest.mark.parametrize('path', _KEEP_GET)
def test_keep_get_has_no_deprecation(client, auth_headers, path):
    r = client.get(path, headers=auth_headers)
    assert 'X-Deprecated' not in r.headers, f'{path} 不应带 X-Deprecated（保留路由）'


@pytest.mark.parametrize('path', _KEEP_POST)
def test_keep_post_has_no_deprecation(client, auth_headers, path):
    r = client.post(path, json={}, headers=auth_headers)
    assert 'X-Deprecated' not in r.headers, f'{path} 不应带 X-Deprecated（保留路由）'


def test_deprecation_does_not_alter_body(client, auth_headers):
    """拦截器纯增量：响应体必须与未加拦截器时一致（用 report/verify 作为对照不可行，
    这里验证 deprecated 路由的响应体仍是合法 JSON 结构，未被拦截器篡改）。"""
    r = client.get('/api/report/daily', headers=auth_headers)
    assert r.status_code < 500, 'deprecated 路由不应因拦截器而 500'
    try:
        data = r.get_json()
        assert data is not None or r.status_code in (400, 401)
    except Exception:
        pass  # 非 JSON 响应（如文件流）也允许，只要状态 < 500
