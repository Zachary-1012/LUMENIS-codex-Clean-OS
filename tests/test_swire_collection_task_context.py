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


def test_init_swire_creates_schema_without_default_seed_rows(tmp_path, monkeypatch):
    database = tmp_path / 'swire-empty-startup.sqlite3'
    monkeypatch.setattr(sg, '_conn', lambda: sqlite3.connect(database, timeout=30))
    monkeypatch.setattr(sg, '_inited', False)

    sg.init_swire()

    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        indexes = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )}
        assert {'swire_projects', 'swire_events', 'swire_notes'} <= tables
        assert {'idx_swe_proj', 'idx_swn_proj'} <= indexes
        for table in ('swire_projects', 'swire_events', 'swire_notes'):
            assert connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == 0


def test_reinitializing_swire_preserves_user_edits(tmp_path, monkeypatch):
    database = tmp_path / 'swire-edited-startup.sqlite3'
    monkeypatch.setattr(sg, '_conn', lambda: sqlite3.connect(database, timeout=30))
    monkeypatch.setattr(sg, '_inited', False)
    sg.init_swire()

    with sqlite3.connect(database) as connection:
        connection.execute(
            """INSERT OR REPLACE INTO swire_projects(
                project_key,name,city,line,opened,intro,sort,kind,keywords,is_active,
                collect_status,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ('guangzhou_thh', '用户编辑的项目名', '用户城市', '用户产品线', '用户年份',
             '用户简介', 71, 'brand', '用户关键词', 0, 'ready', 'created-by-user', 'edited-by-user'),
        )
        connection.execute(
            """INSERT OR REPLACE INTO swire_events(
                project_key,brand,event_type,title,summary,source,event_date,sentiment,tags,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            ('guangzhou_thh', '用户品牌', '用户类型', '广州太古汇开业，奠定华南高端商业标杆',
             '用户编辑的事件摘要', 'user-source', '2011-09-01', 'neutral', 'user-tags', 'created-by-user'),
        )
        projects_before = connection.execute(
            'SELECT * FROM swire_projects WHERE project_key=?', ('guangzhou_thh',)
        ).fetchone()
        events_before = connection.execute(
            'SELECT * FROM swire_events WHERE project_key=? AND title=? AND event_date=?',
            ('guangzhou_thh', '广州太古汇开业，奠定华南高端商业标杆', '2011-09-01'),
        ).fetchone()

    # Simulate a fresh process boot, which must run schema initialization again.
    monkeypatch.setattr(sg, '_inited', False)
    sg.init_swire()

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            'SELECT * FROM swire_projects WHERE project_key=?', ('guangzhou_thh',)
        ).fetchone() == projects_before
        assert connection.execute(
            'SELECT * FROM swire_events WHERE project_key=? AND title=? AND event_date=?',
            ('guangzhou_thh', '广州太古汇开业，奠定华南高端商业标杆', '2011-09-01'),
        ).fetchone() == events_before
