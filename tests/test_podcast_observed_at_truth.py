"""Real original Repository/SQLite readback; only disposable paths are used."""
import ast
import importlib
import os
from pathlib import Path

import pytest


@pytest.fixture
def store(tmp_path, monkeypatch):
    db = tmp_path / 'podcast-time.sqlite3'
    monkeypatch.setenv('ZBC_DB_PATH', str(db))
    import podcast_store
    from lumenis.shared.database import DatabaseRepository
    module = importlib.reload(podcast_store)
    repository = DatabaseRepository(str(db))
    monkeypatch.setattr(module, 'get_repository', lambda: repository)
    monkeypatch.setattr(module, '_now', lambda: '2026-10-18T00:00:00+00:00')
    return module


@pytest.mark.parametrize('missing', [None, ''])
def test_missing_observation_is_null_not_write_time(store, missing):
    entity = store.upsert_entity('episode', title='Unknown observation', observed_at=missing)
    row = store.get_entity(entity)
    assert row['observed_at'] is None
    assert row['created_at'] == '2026-10-18T00:00:00+00:00'
    assert row['updated_at'] == '2026-10-18T00:00:00+00:00'


@pytest.mark.parametrize('stamp', ['2020-02-03T04:05:06Z', '2020-02-03T12:05:06+08:00'])
def test_known_observation_is_preserved_exactly(store, stamp):
    entity = store.upsert_entity('episode', observed_at=stamp)
    assert store.get_entity(entity)['observed_at'] == stamp


def test_publication_and_storage_time_do_not_supply_observation(store):
    entity = store.upsert_entity('episode', published_at='2019-01-02T03:04:05Z')
    row = store.get_entity(entity)
    assert row['observed_at'] is None
    assert row['published_at'] == '2019-01-02T03:04:05Z'
    assert row['created_at'] == '2026-10-18T00:00:00+00:00'


def test_update_missing_observation_stays_unknown_and_does_not_duplicate(store):
    store.upsert_entity('episode', entity_id='same', observed_at='2020-01-01T00:00:00Z')
    store.upsert_entity('episode', entity_id='same', title='new input', observed_at=None)
    row = store.get_entity('same')
    assert row['observed_at'] is None
    assert row['title'] == 'new input'
    assert len(store.list_entities(entity_type='episode')) == 1


def test_reopen_preserves_unknown_in_original_sqlite(store):
    entity = store.upsert_entity('episode', title='Retained unknown')
    # Original Repository creates/closes a fresh SQLite connection on every read.
    assert store.list_entities(entity_type='episode')[0]['observed_at'] is None
    assert store.get_entity(entity)['observed_at'] is None
    with store.get_repository().connection() as connection:
        assert connection.execute('SELECT observed_at IS NULL FROM podcast_entities WHERE entity_id=?', (entity,)).fetchone()[0] == 1


def test_entity_http_routes_remain_blocked_in_source():
    import podcast_store
    source = Path(podcast_store.__file__).with_name('podcast_routes.py').read_text()
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name in ('api_get_entity', 'api_create_entity'):
        function = functions[name]
        assert len(function.body) == 1
        assert isinstance(function.body[0], ast.Return)
        assert isinstance(function.body[0].value, ast.Call)
        assert function.body[0].value.func.id == '_entity_scope_unavailable'
    assert any(isinstance(node, ast.Constant) and node.value == 503 for node in ast.walk(functions['_entity_scope_unavailable']))


@pytest.mark.parametrize('method,path', [('get','/api/podcast/overview'), ('get','/api/podcast/entities'), ('get','/api/podcast/entity'), ('post','/api/podcast/entity')])
def test_entity_http_routes_return_503_without_touching_store(method, path, monkeypatch):
    from flask import Flask
    import podcast_routes
    monkeypatch.setattr(podcast_routes, '_store', lambda: pytest.fail('Blocked entity route must not enter the store'))
    app = Flask(__name__)
    app.register_blueprint(podcast_routes.podcast_bp)
    response = getattr(app.test_client(), method)(path, json={'entity_type':'episode','observed_at':None})
    assert response.status_code == 503
    assert response.json['code'] == 'PODCAST_ENTITY_SCOPE_UNAVAILABLE'
    assert response.json['status'] == 'blocked'
