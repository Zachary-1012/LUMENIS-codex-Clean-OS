import json
from urllib.parse import urlsplit

from lumenis.system.ai_gateway import core


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


def test_local_structured_chat_uses_completion_and_reports_response_usage(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    responses = {
        '/api/show': {'capabilities': ['completion', 'tools']},
        '/api/chat': {
            'model': 'qwen3.5:4b-response',
            'done': True,
            'done_reason': 'stop',
            'message': {'role': 'assistant', 'content': '{"answer":"local"}'},
            'prompt_eval_count': 13,
            'eval_count': 5,
        },
    }
    calls = _mock_ollama(monkeypatch, responses)
    monkeypatch.setattr(
        core.urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('cloud path used')),
    )

    text, provider, meta = core.local_structured_chat(
        'system instruction', 'user request',
        response_schema={'type': 'object'}, model='qwen3.5:4b-requested', max_tokens=9999,
    )

    assert (text, provider) == ('{"answer":"local"}', 'ollama')
    assert meta == {
        'provider': 'ollama',
        'model': 'qwen3.5:4b-response',
        'requested_model': 'qwen3.5:4b-requested',
        'prompt_tokens': 13,
        'completion_tokens': 5,
        'total_tokens': 18,
        'status': 'ok',
    }
    assert [urlsplit(call[0].full_url).path for call in calls] == ['/api/show', '/api/chat']
    assert calls[0][2] == {'model': 'qwen3.5:4b-requested'}
    request, timeout, payload = calls[1]
    assert payload['model'] == 'qwen3.5:4b-requested'
    assert payload['format'] == {'type': 'object'}
    assert payload['messages'] == [
        {'role': 'system', 'content': 'system instruction'},
        {'role': 'user', 'content': 'user request'},
    ]
    assert 'images' not in payload['messages'][1]
    assert payload['options'] == {'temperature': 0, 'num_predict': 2048, 'num_ctx': 8192}
    assert payload['stream'] is False
    assert payload['think'] is False
    assert timeout == 120
    assert not any(key.lower() == 'authorization' for key in request.headers)
    assert core._get_call_meta()['model'] == 'qwen3.5:4b-response'
    assert core._get_call_meta()['total_tokens'] == 18


def test_local_structured_chat_defaults_to_qwen35_and_rejects_missing_completion(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    calls = _mock_ollama(monkeypatch, {
        '/api/show': {'capabilities': ['vision', 'tools']},
    })

    text, provider, meta = core.local_structured_chat('', 'request', response_schema={'type': 'object'})

    assert text is None
    assert provider == 'ollama_completion_unsupported'
    assert meta['requested_model'] == 'qwen3.5:4b'
    assert meta['model'] is None
    assert meta['status'] == 'ollama_completion_unsupported'
    assert len(calls) == 1
    assert calls[0][2] == {'model': 'qwen3.5:4b'}


def test_local_structured_chat_preserves_incomplete_response_metadata(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    _mock_ollama(monkeypatch, {
        '/api/show': {'capabilities': ['completion']},
        '/api/chat': {
            'model': 'qwen3.5:4b-actual',
            'done': False,
            'done_reason': 'length',
            'message': {'role': 'assistant', 'content': '{"partial":'},
            'prompt_eval_count': 7,
            'eval_count': 2000,
        },
    })

    text, provider, meta = core.local_structured_chat('', 'request', response_schema={'type': 'object'})

    assert text is None
    assert provider == 'ollama_incomplete'
    assert meta['model'] == 'qwen3.5:4b-actual'
    assert meta['prompt_tokens'] == 7
    assert meta['completion_tokens'] == 2000
    assert meta['total_tokens'] == 2007
    assert meta['status'] == 'ollama_incomplete'


def test_local_structured_chat_rejects_non_loopback_without_transport(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'https://ollama.example/v1')

    def forbid_network(*_args, **_kwargs):
        raise AssertionError('non-loopback endpoint was contacted')

    monkeypatch.setattr(core.urllib.request, 'build_opener', forbid_network)
    text, provider, meta = core.local_structured_chat('', 'request', response_schema={'type': 'object'})

    assert text is None
    assert provider == 'ollama_unavailable'
    assert meta['status'] == 'ollama_unavailable'
    assert meta['model'] is None


def test_report_text_timeout_is_bounded_without_changing_default(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    calls = _mock_ollama(monkeypatch, {'/api/show': {'capabilities': []}})
    core.local_structured_chat('', 'request', response_schema={'type': 'object'}, timeout_seconds=9999)
    core.local_structured_chat('', 'request', response_schema={'type': 'object'})
    assert [call[1] for call in calls] == [180, 120]
