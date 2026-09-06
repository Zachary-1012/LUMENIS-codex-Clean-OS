# -*- coding: utf-8 -*-
"""Podcast API smoke test — Flask test client, 不启动真实服务。"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 app（app.py 末尾有 __main__ 守卫，import 不会启动服务器）
from app import app
from permission_gate import get_permission_gate, PermissionLevel

# 测试环境授予 COMMIT + 全局审批令牌，绕过高风险操作人工审批（仅 smoke test）
_gate = get_permission_gate()
_gate.grant_permission(PermissionLevel.COMMIT)
_gate.grant_approval("*", duration_minutes=60, granted_by="smoke_test")

import base64
client = app.test_client()
# Basic Auth: Zachary / Zachary01
_auth = base64.b64encode(b'Zachary:Zachary01').decode()
_headers = {'Authorization': 'Basic ' + _auth}
results = []

def check(name, method, path, body=None, expect=200):
    try:
        if method == 'GET':
            r = client.get(path, headers=_headers)
        else:
            r = client.post(path, data=json.dumps(body or {}), content_type='application/json', headers=_headers)
        ok = r.status_code == expect
        try:
            data = r.get_json()
        except Exception:
            data = r.data[:200]
        results.append((name, method, path, r.status_code, ok, data))
        status = 'PASS' if ok else 'FAIL'
        print(f'[{status}] {method} {path} -> {r.status_code} (expect {expect})')
        if not ok:
            print(f'       body: {str(data)[:300]}')
        return ok
    except Exception as e:
        results.append((name, method, path, 'ERROR', False, str(e)))
        print(f'[ERROR] {method} {path}: {e}')
        return False

print('=' * 60)
print('Podcast API Smoke Test')
print('=' * 60)

# 1. overview
check('overview', 'GET', '/api/podcast/overview')

# 2. entities
check('entities', 'GET', '/api/podcast/entities?limit=10')

# 3. entity GET (可能 404，用一个不存在的 id，期望 404 也算 API 可达)
check('entity_not_found', 'GET', '/api/podcast/entity?entity_id=nonexistent_test', expect=404)

# 4. topic-score
check('topic_score', 'POST', '/api/podcast/topic-score', {
    'signals': {
        'demand': 0.8, 'timeliness': 0.7, 'novelty': 0.6,
        'human_relevance': 0.9, 'guest_fit': 0.7, 'evidence': 0.8,
        'content_yield': 0.6, 'distribution': 0.5, 'risk': 0.2, 'cost': 0.3
    }
})

# 5. story-nodes
check('story_nodes', 'POST', '/api/podcast/story-nodes', {
    'segments': [
        {'segment_id': 's0', 'start_ms': 0, 'end_ms': 60000, 'node_type': 'story', 'text': 'test', 'confidence': 0.8},
        {'segment_id': 's1', 'start_ms': 60000, 'end_ms': 120000, 'node_type': 'conflict', 'text': 'test2', 'confidence': 0.9}
    ]
})

# 6. runtime/validate (valid)
check('runtime_valid', 'POST', '/api/podcast/runtime/validate', {
    'segments': [
        {'segment_id': 'r0', 'start_ms': 0, 'end_ms': 60000, 'kind': 'opening'},
        {'segment_id': 'r1', 'start_ms': 60000, 'end_ms': 120000, 'kind': 'story'}
    ]
})

# 7. runtime/validate (invalid overlapping -> 400)
check('runtime_invalid', 'POST', '/api/podcast/runtime/validate', {
    'segments': [
        {'segment_id': 'r0', 'start_ms': 0, 'end_ms': 100000, 'kind': 'story'},
        {'segment_id': 'r1', 'start_ms': 50000, 'end_ms': 150000, 'kind': 'conflict'}
    ]
}, expect=400)

# 8. breakout
check('breakout', 'POST', '/api/podcast/breakout', {'current': 5000, 'baseline': 2000})

# 9. content-yield
check('content_yield', 'POST', '/api/podcast/content-yield', {
    'story_count': 3, 'insight_count': 2, 'emotion_peak_count': 1,
    'quote_count': 2, 'evidence_count': 1
})

print('=' * 60)
passed = sum(1 for r in results if r[4])
total = len(results)
print(f'Result: {passed}/{total} passed')
print('=' * 60)

# 打印关键返回结构
print('\n--- Key response structures ---')
for name, method, path, code, ok, data in results:
    if ok and isinstance(data, dict):
        keys = list(data.keys())
        print(f'{name}: keys={keys}')
        if 'data' in data and isinstance(data['data'], dict):
            print(f'  data keys: {list(data["data"].keys())}')

sys.exit(0 if passed == total else 1)
