# -*- coding: utf-8 -*-
"""execute_per_call_request 的 model 透传回归：默认走智谱旗舰 glm-5.3，且 model 真正传给网关。"""
import sys, os
sys.path.insert(0, r'D:\Taikoo-monitor-new')

def test_per_call_default_model_is_flag():
    import ai_resource_packs
    import inspect
    sig = inspect.signature(ai_resource_packs.execute_per_call_request)
    assert sig.parameters['model'].default == 'glm-5.3', '默认模型应为智谱最强可用 glm-5.3'

def test_per_call_passes_model_to_chat(monkeypatch):
    import ai_resource_packs
    captured = {}
    def fake_chat(system, user, temperature, max_tokens, model):
        captured['model'] = model
        return 'ok', 'zhipu'
    monkeypatch.setattr('ai_resource_packs.check_quota', lambda *a, **k: {'allowed': True})
    monkeypatch.setattr('ai_resource_packs.record_usage', lambda *a, **k: None)
    monkeypatch.setattr('ai_resource_packs._get_pack_usage', lambda p: {'remaining': 10})
    import types
    fake_int = types.ModuleType('intelligence')
    fake_int._chat = fake_chat
    # execute_per_call_request 函数体内 import intelligence，注入 sys.modules
    monkeypatch.setitem(sys.modules, 'intelligence', fake_int)
    ai_resource_packs.execute_per_call_request('测试需求', model='glm-5.3')
    assert captured['model'] == 'glm-5.3'

def test_intelligence_chat_model_override(monkeypatch):
    import intelligence
    def fake_provider_config():
        return ('zhipu', 'glm-4.5-air', 'https://open.bigmodel.cn/api/paas/v4')
    monkeypatch.setattr(intelligence, '_provider_config', fake_provider_config)
    payload = {}
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return b'{"choices":[{"message":{"content":"hi"}}]}'
    def fake_urlopen(req, timeout=None):
        import json
        d = json.loads(req.data.decode('utf-8'))
        payload['model'] = d['model']
        payload['thinking'] = d.get('thinking')
        return FakeResp()
    monkeypatch.setattr(intelligence.urllib.request, 'urlopen', fake_urlopen)
    import types
    monkeypatch.setattr(intelligence.urllib.request, 'build_opener',
                        lambda *a, **k: types.SimpleNamespace(open=fake_urlopen))
    res, prov = intelligence._chat('s', 'u', model='glm-5.2')
    assert payload.get('model') == 'glm-5.2'
    assert payload.get('thinking') == {'type': 'disabled'}


def test_intelligence_chat_glm53_no_thinking(monkeypatch):
    """glm-5.3 始终思考：不得传 thinking（否则 400），且 content 空时回退 reasoning_content。"""
    import intelligence
    monkeypatch.setattr(intelligence, '_provider_config',
                        lambda: ('zhipu', 'glm-4.5-air', 'https://open.bigmodel.cn/api/paas/v4'))
    sent = {}
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return ('{"choices":[{"message":{"content":"","reasoning_content":"思考..."}}]}').encode('utf-8')
    def fake_urlopen(req, timeout=None):
        import json
        sent['has_thinking'] = 'thinking' in json.loads(req.data.decode('utf-8'))
        return FakeResp()
    import types
    monkeypatch.setattr(intelligence.urllib.request, 'urlopen', fake_urlopen)
    monkeypatch.setattr(intelligence.urllib.request, 'build_opener',
                        lambda *a, **k: types.SimpleNamespace(open=fake_urlopen))
    res, prov = intelligence._chat('s', 'u', model='glm-5.3')
    assert sent['has_thinking'] is False, 'glm-5.3 不应传 thinking'
    assert res == '思考...', 'content 空时应回退 reasoning_content'
