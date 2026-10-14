import sqlite3

from flask import Flask

import swire_group as sg


def _database(path):
    connection = sqlite3.connect(path)
    connection.execute(
        """CREATE TABLE swire_projects (
            project_key TEXT PRIMARY KEY, name TEXT, city TEXT, line TEXT, opened TEXT,
            intro TEXT, sort INTEGER DEFAULT 0, kind TEXT DEFAULT 'brand',
            keywords TEXT DEFAULT '', is_active INTEGER DEFAULT 1,
            collect_status TEXT DEFAULT 'idle', created_at TEXT DEFAULT '', updated_at TEXT DEFAULT ''
        )"""
    )
    connection.commit()
    connection.close()


def test_brand_collection_requires_system_task_and_preserves_library_records(tmp_path, monkeypatch):
    database = tmp_path / 'swire-isolated.sqlite3'
    _database(database)
    monkeypatch.setattr(sg, '_conn', lambda: sqlite3.connect(database, timeout=30))
    monkeypatch.setattr(sg, 'init_swire', lambda: None)

    app = Flask(__name__)
    sg.register_swire_group(app)
    client = app.test_client()

    saved = client.post('/api/swire/brand-save', json={
        'name': 'Synthetic brand', 'keywords': 'synthetic query',
    })
    assert saved.status_code == 200
    payload = saved.get_json()
    assert payload['collection']['status'] == 'UNAVAILABLE'
    assert payload['collection']['code'] == 'COLLECTION_TASK_CONTEXT_REQUIRED'
    key = payload['brand']['project_key']
    assert payload['brand']['collect_status'] == 'unavailable'

    retriggered = client.post('/api/swire/brand-collect', json={'project_key': key})
    assert retriggered.status_code == 409
    assert retriggered.get_json()['code'] == 'COLLECTION_TASK_CONTEXT_REQUIRED'

    connection = sqlite3.connect(database)
    stored = connection.execute(
        'SELECT collect_status FROM swire_projects WHERE project_key=?', (key,)
    ).fetchone()
    tables = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    connection.close()
    assert stored == ('unavailable',)
    assert 'swire_notes' not in tables


def test_reactivated_brand_does_not_reuse_previous_collection_success(tmp_path, monkeypatch):
    database = tmp_path / 'swire-reactivation.sqlite3'
    _database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO swire_projects(project_key,name,is_active,collect_status) VALUES(?,?,0,'ready')",
                           ('existing', 'Synthetic brand'))
    monkeypatch.setattr(sg, '_conn', lambda: sqlite3.connect(database, timeout=30))
    monkeypatch.setattr(sg, 'init_swire', lambda: None)
    app = Flask(__name__)
    sg.register_swire_group(app)
    payload = app.test_client().post('/api/swire/brand-save', json={
        'name': 'Synthetic brand', 'keywords': 'changed query',
    }).get_json()
    assert payload['action'] == 'reactivated'
    assert payload['brand']['collect_status'] == 'unavailable'
    assert payload['collection']['code'] == 'COLLECTION_TASK_CONTEXT_REQUIRED'
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT project_key,keywords,collect_status FROM swire_projects').fetchall() == [
            ('existing', 'changed query', 'unavailable')]
