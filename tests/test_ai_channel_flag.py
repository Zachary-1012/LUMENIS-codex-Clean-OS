# -*- coding: utf-8 -*-
"""execute_per_call_request 的 model 透传回归：默认走智谱旗舰 glm-5.3，且 model 真正传给网关。"""
import sys, os
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    from lumenis.system.ai_gateway import core as ai_gateway
    monkeypatch.setattr(ai_gateway, '_chat', fake_chat)
    ai_resource_packs.execute_per_call_request('测试需求', model='glm-5.3')
    assert captured['model'] == 'glm-5.3'

def test_intelligence_chat_model_override(monkeypatch):
    from lumenis.system.ai_gateway import core as intelligence
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-key-not-real')
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
    """GLM-5.3 omits thinking, and reasoning alone is not a final answer."""
    from lumenis.system.ai_gateway import core as intelligence
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-key-not-real')
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
    monkeypatch.setattr(intelligence, '_detect_local', lambda: None)
    res, prov = intelligence._chat('s', 'u', model='glm-5.3')
    assert sent['has_thinking'] is False, 'glm-5.3 不应传 thinking'
    assert (res, prov) == (None, 'rule')


# ---------- P0B-2 智谱评审发现修复回归（2026-09-03）----------
def test_provider_config_glm_alias_no_keyerror(monkeypatch):
    """AI_PROVIDER=glm 时不得 KeyError（configs 无 'glm' 键，应映射到 zhipu）。智谱评审 P0B-2。"""
    from lumenis.system.ai_gateway import core as intelligence
    monkeypatch.setenv('AI_PROVIDER', 'glm')
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-key-abc')
    intelligence._CACHE['ts'] = 0  # 强制重算
    intelligence._CACHE['provider'] = None
    cfg = intelligence._provider_config()
    assert cfg is not None
    assert cfg[0] == 'zhipu', f'glm 别名应解析为 zhipu，实际 {cfg[0]}'


def test_provider_config_glm_without_key_returns_none(monkeypatch):
    """AI_PROVIDER=glm 且无 key 时返回 None（不崩溃、不降级异常）。"""
    from lumenis.system.ai_gateway import core as intelligence
    monkeypatch.setenv('AI_PROVIDER', 'glm')
    monkeypatch.delenv('ZHIPU_API_KEY', raising=False)
    intelligence._CACHE['ts'] = 0
    intelligence._CACHE['provider'] = None
    assert intelligence._provider_config() is None


def test_glm53_case_insensitive_no_thinking(monkeypatch):
    """GLM-5.3 returns final content even when it also includes reasoning."""
    from lumenis.system.ai_gateway import core as intelligence
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-key-not-real')
    monkeypatch.setattr(intelligence, '_provider_config',
                        lambda: ('zhipu', 'glm-4.5-air', 'https://open.bigmodel.cn/api/paas/v4'))
    sent = {}
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return ('{"choices":[{"message":{"content":"最终答案","reasoning_content":"思考"}}]}').encode('utf-8')
    def fake_urlopen(req, timeout=None):
        import json
        sent['has_thinking'] = 'thinking' in json.loads(req.data.decode('utf-8'))
        return FakeResp()
    import types
    monkeypatch.setattr(intelligence.urllib.request, 'urlopen', fake_urlopen)
    monkeypatch.setattr(intelligence.urllib.request, 'build_opener',
                        lambda *a, **k: types.SimpleNamespace(open=fake_urlopen))
    res, prov = intelligence._chat('s', 'u', model='GLM-5.3')
    assert sent['has_thinking'] is False, 'GLM-5.3 大写不应传 thinking'
    assert (res, prov) == ('最终答案', 'zhipu')


def test_glm53_flash_variant_no_thinking(monkeypatch):
    """glm-5.3-flash 变体也应视为始终思考，不传 thinking。"""
    from lumenis.system.ai_gateway import core as intelligence
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-key-not-real')
    monkeypatch.setattr(intelligence, '_provider_config',
                        lambda: ('zhipu', 'glm-4.5-air', 'https://open.bigmodel.cn/api/paas/v4'))
    sent = {}
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return ('{"choices":[{"message":{"content":"","reasoning_content":"思考"}}]}').encode('utf-8')
    def fake_urlopen(req, timeout=None):
        import json
        sent['has_thinking'] = 'thinking' in json.loads(req.data.decode('utf-8'))
        return FakeResp()
    import types
    monkeypatch.setattr(intelligence.urllib.request, 'urlopen', fake_urlopen)
    monkeypatch.setattr(intelligence.urllib.request, 'build_opener',
                        lambda *a, **k: types.SimpleNamespace(open=fake_urlopen))
    monkeypatch.setattr(intelligence, '_detect_local', lambda: None)
    res, prov = intelligence._chat('s', 'u', model='glm-5.3-flash')
    assert sent['has_thinking'] is False, 'glm-5.3-flash 不应传 thinking'
    assert (res, prov) == (None, 'rule')


# ---------- Search-STD 增强搜索修复回归（2026-09-03）----------
def test_search_enhance_default_model_is_web_search_pro(monkeypatch):
    """search_enhance 默认运行时使用智谱联网搜索 web-search-pro。
    签名 model=None 为动态路由（自 ZHIPU_SEARCH_MODEL 获取），无环境覆盖时回退官方联网搜索 web-search-pro。"""
    from lumenis.system.ai_gateway import core as intelligence
    import inspect
    sig = inspect.signature(intelligence.search_enhance)
    assert sig.parameters['model'].default is None, '签名默认应为 None（动态读 ZHIPU_SEARCH_MODEL）'
    monkeypatch.delenv('ZHIPU_SEARCH_MODEL', raising=False)
    assert intelligence._env('ZHIPU_SEARCH_MODEL', 'web-search-pro') == 'web-search-pro', '无覆盖时应回退智谱联网搜索 web-search-pro'

def test_search_enhance_parses_tool_calls(monkeypatch):
    """web-search-pro 返回 message.tool_calls[].search_result 时应正确解析为 results（真实联网搜索）。"""
    from lumenis.system.ai_gateway import core as intelligence
    import sys, types
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-key-abc')
    monkeypatch.setenv('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
    # mock ai_resource_packs 额度
    fake_arp = types.ModuleType('ai_resource_packs')
    fake_arp.check_quota = lambda *a, **k: {'allowed': True}
    fake_arp.record_usage = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, 'ai_resource_packs', fake_arp)
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return ('{"choices":[{"message":{"role":"tool","tool_calls":['
                    '{"type":"search_result","search_result":['
                    '{"title":"太古汇品牌专区","content":"广州天河核心地段总建筑面积406000平","refer":"ref_1","index":0}'
                    ']}]}}]}').encode('utf-8')
    sent = {}
    def fake_urlopen(req, timeout=None):
        import json
        sent['model'] = json.loads(req.data.decode('utf-8'))['model']
        return FakeResp()
    monkeypatch.setattr(intelligence.urllib.request, 'urlopen', fake_urlopen)
    monkeypatch.setattr(intelligence.urllib.request, 'build_opener',
                        lambda *a, **k: types.SimpleNamespace(open=fake_urlopen))
    res = intelligence.search_enhance('广州太古汇')
    assert sent['model'] == 'web-search-pro', f'应使用 web-search-pro，实际 {sent["model"]}'
    if not res.get('ok'):
        print('DEBUG res:', res)
    assert res['ok'] is True
    assert len(res['results']) == 1, f'应解析出 1 条结果，实际 {len(res.get("results", []))}'
    assert res['results'][0]['title'] == '太古汇品牌专区'
    assert res['results'][0]['content'].startswith('广州天河')
    assert res['model'] == 'web-search-pro'
