import json
from urllib.parse import urlsplit

import pytest

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
            path = urlsplit(request.full_url).path
            payload = json.loads(request.data.decode('utf-8'))
            calls.append((path, request, timeout, payload))
            response = responses[path]
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


def _responses(embeddings=None, **response_fields):
    response = {
        'model': 'bge-m3:latest',
        'embeddings': embeddings if embeddings is not None else [[0.1, 0.2], [0.3, 0.4]],
        'prompt_eval_count': 8,
        'total_duration': 900,
    }
    response.update(response_fields)
    return {'/api/show': {'capabilities': ['embedding']}, '/api/embed': response}


def test_local_embeddings_uses_loopback_api_and_reports_real_metadata(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    monkeypatch.delenv('OLLAMA_EMBEDDING_MODEL', raising=False)
    calls = _mock_ollama(monkeypatch, _responses())
    monkeypatch.setattr(
        core.urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('cloud path used')),
    )

    vectors, status, meta = core.local_embeddings(['first item', 'second item'])

    assert (vectors, status) == ([[0.1, 0.2], [0.3, 0.4]], 'ollama')
    assert meta == {
        'provider': 'ollama', 'model': 'bge-m3:latest', 'requested_model': 'bge-m3:latest',
        'prompt_tokens': 8, 'duration_ns': 900, 'status': 'ok',
    }
    assert [call[0] for call in calls] == ['/api/show', '/api/embed']
    assert calls[0][3] == {'model': 'bge-m3:latest'}
    assert calls[1][3] == {
        'model': 'bge-m3:latest', 'input': ['first item', 'second item'], 'truncate': False,
    }
    assert [call[2] for call in calls] == [60, 60]
    assert not any(key.lower() == 'authorization' for key in calls[1][1].headers)


def test_local_embeddings_accepts_only_latest_model_alias(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    calls = _mock_ollama(monkeypatch, _responses())

    vectors, status, meta = core.local_embeddings(['one', 'two'], model='bge-m3')

    assert status == 'ollama'
    assert len(vectors) == 2
    assert meta['requested_model'] == 'bge-m3'
    assert meta['model'] == 'bge-m3:latest'
    assert calls[1][3]['model'] == 'bge-m3'


def test_local_embeddings_rejects_unsupported_capability_before_embed(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    calls = _mock_ollama(monkeypatch, {'/api/show': {'capabilities': ['completion']}})

    vectors, status, meta = core.local_embeddings(['one'])

    assert vectors is None
    assert status == 'ollama_embedding_unsupported'
    assert meta['status'] == status
    assert [call[0] for call in calls] == ['/api/show']


def test_local_embeddings_rejects_non_loopback_before_network(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'https://ollama.example/v1')

    def forbid_network(*_args, **_kwargs):
        raise AssertionError('non-loopback endpoint was contacted')

    monkeypatch.setattr(core.urllib.request, 'build_opener', forbid_network)
    vectors, status, meta = core.local_embeddings(['one'])

    assert vectors is None
    assert status == 'ollama_unavailable'
    assert meta['model'] is None


@pytest.mark.parametrize('texts', [None, [], [''], ['   '], ['x' * 1601], ('one',), [1], ['x'] * 102])
def test_local_embeddings_rejects_invalid_text_input_before_network(monkeypatch, texts):
    def forbid_network(*_args, **_kwargs):
        raise AssertionError('invalid input reached transport')

    monkeypatch.setattr(core.urllib.request, 'build_opener', forbid_network)
    vectors, status, meta = core.local_embeddings(texts)

    assert vectors is None
    assert status == 'ollama_invalid_input'
    assert meta['status'] == status


@pytest.mark.parametrize('model', ['', 7])
def test_local_embeddings_rejects_invalid_model_before_network(monkeypatch, model):
    def forbid_network(*_args, **_kwargs):
        raise AssertionError('invalid model reached transport')

    monkeypatch.setattr(core.urllib.request, 'build_opener', forbid_network)
    vectors, status, _meta = core.local_embeddings(['one'], model=model)

    assert vectors is None
    assert status == 'ollama_invalid_input'


@pytest.mark.parametrize('embeddings', [
    [[1.0, 2.0]],
    [[], [1.0, 2.0]],
    [[1.0, 2.0], [3.0]],
    [[True, 2.0], [3.0, 4.0]],
    [[float('nan'), 2.0], [3.0, 4.0]],
    [[float('inf'), 2.0], [3.0, 4.0]],
    [[1e308] * 5, [3.0, 4.0]],
    [[0, 0], [3.0, 4.0]],
])
def test_local_embeddings_rejects_partial_or_invalid_vectors(monkeypatch, embeddings):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    _mock_ollama(monkeypatch, _responses(embeddings=embeddings))

    vectors, status, meta = core.local_embeddings(['one', 'two'])

    assert vectors is None
    assert status == 'ollama_invalid_embeddings'
    assert meta['model'] == 'bge-m3:latest'
    assert meta['prompt_tokens'] == 8
    assert meta['duration_ns'] == 900


def test_local_embeddings_rejects_model_identity_mismatch(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    responses = _responses(model='other-model:latest')
    _mock_ollama(monkeypatch, responses)

    vectors, status, meta = core.local_embeddings(['one', 'two'])

    assert vectors is None
    assert status == 'ollama_model_mismatch'
    assert meta['model'] == 'other-model:latest'


def test_local_embeddings_keeps_missing_usage_metadata_unknown(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    responses = _responses()
    responses['/api/embed'].pop('prompt_eval_count')
    responses['/api/embed'].pop('total_duration')
    _mock_ollama(monkeypatch, responses)

    vectors, status, meta = core.local_embeddings(['one', 'two'])

    assert vectors is not None
    assert status == 'ollama'
    assert meta['prompt_tokens'] is None
    assert meta['duration_ns'] is None


def test_local_embeddings_api_failure_does_not_fall_back_to_cloud(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'zhipu')
    monkeypatch.setenv('ALLOW_CLOUD_AI', 'true')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    calls = _mock_ollama(monkeypatch, {
        '/api/show': {'capabilities': ['embedding']},
        '/api/embed': RuntimeError('local API failed'),
    })
    monkeypatch.setattr(
        core.urllib.request, 'urlopen',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('cloud fallback used')),
    )

    vectors, status, meta = core.local_embeddings(['one'])

    assert vectors is None
    assert status == 'ollama_error'
    assert meta['status'] == status
    assert [call[0] for call in calls] == ['/api/show', '/api/embed']
