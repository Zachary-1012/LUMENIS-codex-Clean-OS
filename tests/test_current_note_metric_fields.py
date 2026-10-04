"""Current metric field semantics through the existing note repository API."""
import importlib
import sqlite3

import pytest


_METRICS = ("likes", "comments", "collects", "shares")


@pytest.fixture
def note_db(tmp_path, monkeypatch):
    path = tmp_path / "current_metric_fields.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv("ZBC_METRIC_SNAPSHOT", "1")
    import database

    module = importlib.reload(database)
    module.DB_PATH = str(path)
    module.init_db()
    return module, path


def _read_metrics(path, note_id):
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT likes, comments, collects, shares FROM notes WHERE note_id=?",
            (note_id,),
        ).fetchone()
    return tuple(row)


def _read_history(path, note_id):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT likes, comments, collects, shares FROM metric_snapshots "
            "WHERE entity_type='note' AND entity_key=? ORDER BY id",
            (note_id,),
        ).fetchall()


def test_all_four_metrics_transition_known_unknown_zero_and_keep_history(note_db):
    database, path = note_db
    values = dict(zip(_METRICS, (11, 12, 13, 14)))
    database.insert_note({"note_id": "metric-transition", "title": "first", **values})
    updated = dict(zip(_METRICS, (21, 22, 23, 24)))
    database.insert_note({"note_id": "metric-transition", "title": "measured", **updated})
    original_history = _read_history(path, "metric-transition")
    assert original_history == [(21, 22, 23, 24)]

    database.insert_note({
        "note_id": "metric-transition", "title": "currently unknown",
        **dict.fromkeys(_METRICS, None),
    })
    assert _read_metrics(path, "metric-transition") == (None, None, None, None)
    assert _read_history(path, "metric-transition") == original_history

    database.insert_note({
        "note_id": "metric-transition", "title": "measured zero",
        **dict.fromkeys(_METRICS, 0),
    })
    assert _read_metrics(path, "metric-transition") == (0, 0, 0, 0)
    assert _read_history(path, "metric-transition") == [
        (21, 22, 23, 24), (0, 0, 0, 0),
    ]


def test_omitted_metrics_retain_current_values_while_explicit_empty_is_unknown(note_db):
    database, path = note_db
    database.insert_note({
        "note_id": "metric-omission", "title": "seed",
        "likes": 7, "comments": 8, "collects": 9, "shares": 10,
    })
    database.insert_note({"note_id": "metric-omission", "title": "partial metadata"})
    assert _read_metrics(path, "metric-omission") == (7, 8, 9, 10)

    database.insert_note({"note_id": "metric-omission", "title": "one unknown", "comments": ""})
    assert _read_metrics(path, "metric-omission") == (7, None, 9, 10)


def test_caller_transaction_rolls_back_explicit_unknown_current_metrics(note_db):
    database, path = note_db
    database.insert_note({
        "note_id": "metric-rollback", "title": "observed",
        "likes": 31, "comments": 32, "collects": 33, "shares": 34,
    })
    database.insert_note({
        "note_id": "metric-rollback", "title": "refreshed",
        "likes": 41, "comments": 42, "collects": 43, "shares": 44,
    })
    history_before = _read_history(path, "metric-rollback")

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN IMMEDIATE")
        row_id, inserted = database.insert_note({
            "note_id": "metric-rollback", "title": "uncommitted unknown",
            **dict.fromkeys(_METRICS, None),
        }, connection=connection)
        assert row_id > 0 and inserted is False
        assert connection.in_transaction is True
        current = connection.execute(
            "SELECT likes, comments, collects, shares FROM notes WHERE note_id=?",
            ("metric-rollback",),
        ).fetchone()
        assert tuple(current) == (None, None, None, None)
        history_in_transaction = connection.execute(
            "SELECT likes, comments, collects, shares FROM metric_snapshots "
            "WHERE entity_type='note' AND entity_key=? ORDER BY id",
            ("metric-rollback",),
        ).fetchall()
        assert [tuple(row) for row in history_in_transaction] == history_before
        connection.rollback()
    finally:
        connection.close()

    assert _read_metrics(path, "metric-rollback") == (41, 42, 43, 44)
    assert _read_history(path, "metric-rollback") == history_before
