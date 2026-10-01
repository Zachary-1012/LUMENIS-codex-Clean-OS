import json
import sys
from urllib.parse import urlsplit

import pytest

from lumenis.system.ai_gateway import core


def _enable_mock_provider(monkeypatch, name):
    from lumenis.system.ai_gateway import providers
    monkeypatch.setattr(
        providers, 'RETIRED_PROVIDERS', providers.RETIRED_PROVIDERS - {name},
    )
    monkeypatch.setitem(providers.PROVIDER_REGISTRY[name], 'status', providers.ACTIVE)


class _Response:
    def __init__(self, body, url):
        self._body = json.dumps(body).encode('utf-8')
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._body

    def geturl(self):
        return self._url


def _mock_ollama(monkeypatch, responses):
    _enable_mock_provider(monkeypatch, 'ollama')
    calls = []

    class _Opener:
        def open(self, request, timeout):
            body = json.loads(request.data.decode('utf-8'))
            calls.append((request, timeout, body))
            response = responses[urlsplit(request.full_url).path]
            if isinstance(response, Exception):
                raise response
            return _Response(response, request.full_url)

    def build_opener(*handlers):
        assert len(handlers) == 2
        assert isinstance(handlers[0], core.urllib.request.ProxyHandler)
        assert handlers[0].proxies == {}
        assert isinstance(handlers[1], core._LocalOnlyRedirectHandler)
        return _Opener()

    monkeypatch.setattr(core.urllib.request, 'build_opener', build_opener)
    return calls


def _vision_responses(content='a local result'):
    return {
        '/api/show': {'capabilities': ['completion', 'vision', 'tools', 'thinking']},
        '/api/chat': {
            'done': True,
            'done_reason': 'stop',
            'message': {'role': 'assistant', 'content': content},
            'prompt_eval_count': 11,
            'eval_count': 7,
        },
    }


def test_local_only_checks_capability_and_sends_image_to_ollama(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    monkeypatch.setenv('OLLAMA_TIMEOUT_SECONDS', '999')
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-only-key')
    calls = _mock_ollama(monkeypatch, _vision_responses())

    def forbid_cloud(*_args, **_kwargs):
        raise AssertionError('local_only attempted a cloud request')

    monkeypatch.setattr(core.urllib.request, 'urlopen', forbid_cloud)
    image = 'aGVsbG8taW1hZ2UtYnl0ZXM='
    result = core.vision_chat(
        'system instruction', 'describe this', image,
        model='qwen3.5:4b', max_tokens=9999, local_only=True, response_schema={'type': 'object'},
    )

    assert result == ('a local result', 'ollama')
    assert [urlsplit(call[0].full_url).path for call in calls] == ['/api/show', '/api/chat']
    assert calls[0][2] == {'model': 'qwen3.5:4b:local'}
    request, timeout, payload = calls[1]
    handler = core._LocalOnlyRedirectHandler()
    assert handler.redirect_request(request, None, 302, 'Found', {}, 'https://example.invalid/') is None
    assert payload['model'] == 'qwen3.5:4b:local'
    assert payload['format'] == {'type': 'object'}
    assert payload['options']['num_ctx'] == 8192
    assert payload['messages'] == [
        {'role': 'system', 'content': 'system instruction'},
        {'role': 'user', 'content': 'describe this', 'images': [image]},
    ]
    assert payload['think'] is False
    assert payload['stream'] is False
    assert payload['options']['num_predict'] == 2048
    assert timeout == 120
    assert not any(key.lower() == 'authorization' for key in request.headers)


def test_auto_provider_prefers_local_vision(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    monkeypatch.setenv('OLLAMA_VISION_MODEL', 'qwen3.5:4b')
    calls = _mock_ollama(monkeypatch, _vision_responses())

    def forbid_cloud(*_args, **_kwargs):
        raise AssertionError('auto used cloud despite a working local vision model')

    monkeypatch.setattr(core.urllib.request, 'urlopen', forbid_cloud)
    assert core.vision_chat('', 'inspect', 'cGl4ZWw=') == ('a local result', 'ollama')
    assert calls[-1][2]['model'] == 'qwen3.5:4b:local'


def test_ollama_reports_missing_vision_capability_without_chat_or_cloud(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    calls = _mock_ollama(monkeypatch, {
        '/api/show': {'capabilities': ['completion', 'tools']},
    })
    monkeypatch.setattr(
        core.urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('cloud fallback called')),
    )

    assert core.vision_chat('', 'inspect', 'cGl4ZWw=') == (None, 'ollama_vision_unsupported')
    assert len(calls) == 1
    assert urlsplit(calls[0][0].full_url).path == '/api/show'


def test_local_only_rejects_non_loopback_ollama_url(monkeypatch):
    _enable_mock_provider(monkeypatch, 'ollama')
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'https://ollama.example/v1')
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-only-key')

    def forbid_network(*_args, **_kwargs):
        raise AssertionError('non-loopback endpoint or cloud was contacted')

    monkeypatch.setattr(core.urllib.request, 'build_opener', forbid_network)
    monkeypatch.setattr(core.urllib.request, 'urlopen', forbid_network)
    assert core.vision_chat('', 'inspect', 'cGl4ZWw=', local_only=True) == (None, 'ollama_unavailable')


def test_local_only_refuses_remote_ollama_before_sending_image(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    calls = _mock_ollama(monkeypatch, {
        '/api/show': {'capabilities': ['vision'], 'remote_model': 'hosted-vision-model'},
    })
    monkeypatch.setattr(
        core.urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('cloud fallback called')),
    )

    result = core.vision_chat(
        'private system text', 'private image prompt', 'private-image-data', local_only=True,
    )

    assert result == (None, 'ollama_remote')
    assert [urlsplit(call[0].full_url).path for call in calls] == ['/api/show']
    assert calls[0][2] == {'model': 'qwen3.5:4b:local'}


def test_empty_local_response_is_not_reported_as_success(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'false')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    _mock_ollama(monkeypatch, _vision_responses(content='  '))
    monkeypatch.setattr(
        core.urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('cloud fallback called')),
    )

    assert core.vision_chat('', 'inspect', 'cGl4ZWw=') == (None, 'ollama_empty')


def test_local_only_reports_ollama_exception_without_cloud_fallback(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    calls = _mock_ollama(monkeypatch, {'/api/show': RuntimeError('local service unavailable')})
    monkeypatch.setattr(
        core.urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('cloud fallback called')),
    )

    assert core.vision_chat('', 'inspect', 'cGl4ZWw=', local_only=True) == (None, 'ollama_error')
    assert len(calls) == 1


def test_cloud_disabled_blocks_legacy_zhipu_vision(monkeypatch):
    _enable_mock_provider(monkeypatch, 'zhipu')
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'false')
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-only-key')

    def forbid_network(*_args, **_kwargs):
        raise AssertionError('cloud-disabled vision attempted a network request')

    monkeypatch.setattr(core.urllib.request, 'urlopen', forbid_network)
    monkeypatch.setattr(core.urllib.request, 'build_opener', forbid_network)
    assert core.vision_chat('', 'inspect', 'cGl4ZWw=') == (None, 'cloud_disabled')


def test_mocked_explicit_zhipu_vision_keeps_compatibility_adapter(monkeypatch):
    _enable_mock_provider(monkeypatch, 'zhipu')
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-only-key')
    monkeypatch.setenv('ZHIPU_BASE_URL', 'https://zhipu.invalid/v4')
    monkeypatch.setitem(sys.modules, 'ai_resource_packs', type('Packs', (), {
        'check_quota': staticmethod(lambda *_args: {'allowed': True}),
        'record_usage': staticmethod(lambda *_args, **_kwargs: None),
    }))
    requests = []

    def cloud_response(request, timeout):
        requests.append((request, timeout))
        return _Response({
            'choices': [{'message': {'content': 'legacy cloud result'}}],
            'usage': {'total_tokens': 9},
        }, request.full_url)

    monkeypatch.setattr(core.urllib.request, 'urlopen', cloud_response)
    result = core.vision_chat('', 'inspect', 'cGl4ZWw=')

    assert result == ('legacy cloud result', 'glm-4.6v')
    assert len(requests) == 1
    request, timeout = requests[0]
    assert request.full_url == 'https://zhipu.invalid/v4/chat/completions'
    assert timeout == 90


@pytest.mark.parametrize(
    ('provider', 'cloud_allowed'),
    [('auto', 'false'), ('ollama', 'true')],
)
def test_text_chat_unavailable_auto_or_local_never_enters_cloud_chain(
    monkeypatch, provider, cloud_allowed,
):
    monkeypatch.setenv('AI_PROVIDER', provider)
    monkeypatch.setenv('ALLOW_CLOUD_AI', cloud_allowed)
    monkeypatch.setattr(core, '_provider_config', lambda: None)
    calls = []
    monkeypatch.setattr(
        core.ai_channel, 'route_with_fallback',
        lambda *_args, **_kwargs: calls.append('cloud'),
    )

    assert core._chat('system', 'user') == (None, 'provider_disabled')
    assert calls == []
    assert core._get_call_meta()['provider'] == 'provider_disabled'


@pytest.mark.parametrize(
    ('provider', 'cloud_allowed'),
    [('zhipu', 'true')],
)
def test_text_chat_preserves_explicit_cloud_opt_in_route(
    monkeypatch, provider, cloud_allowed,
):
    _enable_mock_provider(monkeypatch, 'zhipu')
    monkeypatch.setenv('AI_PROVIDER', provider)
    monkeypatch.setenv('ALLOW_CLOUD_AI', cloud_allowed)
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-only-key')
    monkeypatch.setenv('ARK_API_KEY', '')
    monkeypatch.setenv('DASHSCOPE_API_KEY', '')
    monkeypatch.setattr(core, '_provider_config', lambda: None)
    routes = []

    def route(_call_provider, providers):
        routes.append(tuple(providers))
        return 'cloud response', 'zhipu'

    monkeypatch.setattr(core.ai_channel, 'route_with_fallback', route)
    assert core._chat('system', 'user') == ('cloud response', 'zhipu')
    assert routes == [('zhipu',)]


@pytest.mark.parametrize(('provider', 'local_only'), [('auto', False), ('zhipu', False), ('ollama', False), ('zhipu', True)])
def test_retired_vision_routes_return_disabled_without_network(monkeypatch, provider, local_only):
    monkeypatch.setenv('AI_PROVIDER', provider)
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('ZHIPU_API_KEY', 'test-only-placeholder-never-sent')

    def forbid_network(*_args, **_kwargs):
        raise AssertionError('disabled provider attempted network or inference')

    monkeypatch.setattr(core.urllib.request, 'build_opener', forbid_network)
    monkeypatch.setattr(core.urllib.request, 'urlopen', forbid_network)

    assert core.vision_chat('', 'inspect', 'cGl4ZWw=', local_only=local_only) == (
        None, 'provider_disabled',
    )
