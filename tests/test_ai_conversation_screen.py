"""AI03 adapter contract; persistent Owner/HTTP checks live in its own suite."""
import pytest
from flask import Flask

import experience_screens as screens
from lumenis.ai_hub import conversations


def test_shared_conversation_projection_without_focus(monkeypatch):
    actor = object()
    called = []
    monkeypatch.setattr(conversations, 'current_actor', lambda action: actor)
    monkeypatch.setattr(conversations, 'list_conversations', lambda actual, **kw: {
        'conversations': [{'conversation_id': 'conv_1', 'title': 'Research'}],
        'has_more': False, 'next_offset': None})
    def read(actual, identifier):
        assert actual is actor
        called.append(identifier)
        return {'conversation_id': identifier, 'turns': [
            {'role': 'user', 'origin_kind': 'user', 'content': {'text': 'Question'}}]}
    monkeypatch.setattr(conversations, 'read_conversation', read)
    with Flask(__name__).test_request_context('/?conversation_id=conv_1'):
        value = screens._build_ai03()
    assert called == ['conv_1']
    assert value['data']['selected_conversation']['turns'][0]['role'] == 'user'
    assert value['truth']['scope'] == 'actor-owned-shared-workspace'


def test_no_implicit_conversation_read(monkeypatch):
    monkeypatch.setattr(conversations, 'current_actor', lambda action: {'id': 4})
    monkeypatch.setattr(conversations, 'list_conversations', lambda *a, **kw: {
        'conversations': [], 'has_more': False, 'next_offset': None})
    monkeypatch.setattr(conversations, 'read_conversation', lambda *a, **kw: pytest.fail('implicit read'))
    with Flask(__name__).test_request_context('/'):
        assert screens._build_ai03()['data']['selected_conversation'] is None


@pytest.mark.parametrize('query', ['actor=7', 'conversation_id=a&conversation_id=b'])
def test_client_identity_and_duplicate_selectors_rejected(query):
    with Flask(__name__).test_request_context('/?' + query):
        with pytest.raises(ValueError, match='CONVERSATION_SCREEN_QUERY_INVALID'):
            screens._build_ai03()


def test_foreign_conversation_owner_denial_is_preserved(monkeypatch):
    monkeypatch.setattr(conversations, 'current_actor', lambda action: {'id': 4})
    monkeypatch.setattr(conversations, 'list_conversations', lambda *a, **kw: {'conversations': []})
    def deny(*args, **kw):
        raise PermissionError('CONVERSATION_ACCESS_DENIED')
    monkeypatch.setattr(conversations, 'read_conversation', deny)
    with Flask(__name__).test_request_context('/?conversation_id=foreign'):
        with pytest.raises(PermissionError):
            screens._build_ai03()
