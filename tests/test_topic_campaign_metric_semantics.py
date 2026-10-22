import json
import sqlite3
from contextlib import nullcontext
from datetime import datetime, timedelta

from flask import Flask

import topic_campaign as campaign


class _MemoryDB:
    def __init__(self):
        self.connection = sqlite3.connect(':memory:')
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(campaign.SCHEMA)
        for column in (
            'media_json TEXT DEFAULT "[]"', 'comments_json TEXT DEFAULT "[]"',
            'sentiment TEXT DEFAULT "unknown"', 'content_type TEXT DEFAULT ""',
            'subject_hit INTEGER DEFAULT 0', 'risk_level TEXT DEFAULT "unknown"',
            'evidence_quality TEXT DEFAULT "unknown"', 'detail_captured_at TEXT DEFAULT ""',
        ):
            self.connection.execute('ALTER TABLE topic_campaign_notes ADD COLUMN ' + column)

    def get_db(self):
        return nullcontext(self.connection)


def _insert_note(conn, *, topic, note_id, first_seen, last_seen, raw_json, sentiment='unknown'):
    conn.execute(
        """INSERT INTO topic_campaign_notes
        (campaign_key,topic,note_id,first_seen_at,last_seen_at,raw_json,likes,comments,collects,shares,
         sentiment,content_type,media_json,comments_json)
        VALUES('metric-test',?,?,?,?,?,0,0,0,0,?,'UGC','[]','[]')""",
        (topic, note_id, first_seen, last_seen, json.dumps(raw_json), sentiment),
    )


def _client(monkeypatch, db):
    monkeypatch.setattr(campaign, '_db', lambda: db)
    monkeypatch.setattr(campaign, 'init_campaign', lambda: None)
    monkeypatch.setattr(campaign, 'start_scheduler', lambda: False)
    app = Flask('topic-campaign-metrics-test')
    campaign.register_topic_campaign(app)
    return app.test_client()


def test_snapshot_view_ignores_legacy_zero_but_keeps_explicit_raw_zero():
    projected = campaign._snapshot_view({
        'browse_count': 0, 'discussion_count': 0, 'note_count': 0,
        'new_note_count': 0, 'engagement_count': 0, 'raw_json': '{"note_count":0}',
    })

    assert projected['browse_count'] is None
    assert projected['discussion_count'] is None
    assert projected['note_count'] == 0
    assert projected['new_note_count'] is None
    assert projected['engagement_count'] is None
    assert projected['metric_freshness'] == 'UNKNOWN'
    assert projected['metric_completeness'] == 'UNKNOWN'
    assert projected['source_verification'] == 'NOT_ESTABLISHED'


def test_note_projection_keeps_explicit_zero_and_hides_ambiguous_columns():
    projected = campaign._note_view({
        'likes': 0, 'comments': 0, 'collects': 0, 'shares': 0,
        'raw_json': '{"likes":0}', 'media_json': '[]', 'comments_json': '[]',
    })

    assert projected['likes'] == 0
    assert projected['comments'] is None
    assert projected['comments_detail'] == []
    assert projected['collects'] is None
    assert projected['shares'] is None


def test_latest_note_view_preserves_last_explicit_observation_with_unknown_freshness():
    rows = [
        {'id': 1, 'topic': 'A', 'note_id': 'same', 'last_seen_at': '2026-10-20 10:00:00',
         'raw_json': '{"likes":0}', 'media_json': '[]', 'comments_json': '[]'},
        {'id': 2, 'topic': 'B', 'note_id': 'same', 'last_seen_at': '2026-10-21 10:00:00',
         'raw_json': '{}', 'media_json': '[]', 'comments_json': '[]'},
    ]

    projected = campaign._latest_note_views(rows)[0]

    assert projected['likes'] == 0
    assert projected['metric_observation_saved_at']['likes'].startswith('2026-10-20T10:00:00')
    assert projected['metric_freshness'] == 'UNKNOWN'
    assert projected['metric_completeness'] == 'UNKNOWN'


def test_stats_preserve_real_unique_count_and_never_call_snapshots_runs(monkeypatch):
    db = _MemoryDB()
    conn = db.connection
    now = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
    older = (datetime.now().astimezone() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    _insert_note(conn, topic='A', note_id='shared', first_seen=now, last_seen=now,
                 raw_json={'likes': 0, 'sentiment': 'positive'}, sentiment='positive')
    _insert_note(conn, topic='B', note_id='shared', first_seen=now, last_seen=now,
                 raw_json={'likes': 1}, sentiment='negative')
    _insert_note(conn, topic='A', note_id='old', first_seen=older, last_seen=older,
                 raw_json={}, sentiment='unknown')
    conn.execute("INSERT INTO topic_campaign_snapshots(campaign_key,topic,captured_at,status,raw_json) VALUES('metric-test','A',?,'success','{}')", (now,))
    conn.execute("INSERT INTO topic_campaign_snapshots(campaign_key,topic,captured_at,status,raw_json) VALUES('metric-test','A',?,'error','{}')", (now,))
    conn.commit()

    client = _client(monkeypatch, db)
    stats = client.get('/api/topic-campaign/stats?campaign_key=metric-test').get_json()
    assert stats['total']['unique_notes'] == 2
    assert stats['total']['new_notes_24h'] == 1
    assert stats['total']['runs'] is None
    assert stats['total']['snapshot_count'] == 2
    assert stats['total']['successful_topic_snapshots'] == 1
    assert stats['sentiment_dist'] == [{'count': 2, 'name': 'unknown'}]
    assert stats['metric_freshness'] == 'UNKNOWN'
    assert stats['source_verification'] == 'NOT_ESTABLISHED'


def test_note_routes_expose_conflicting_latest_metrics_as_unknown(monkeypatch):
    db = _MemoryDB()
    conn = db.connection
    now = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
    _insert_note(conn, topic='A', note_id='same', first_seen=now, last_seen=now,
                 raw_json={'likes': 3, 'comments': 0}, sentiment='positive')
    _insert_note(conn, topic='B', note_id='same', first_seen=now, last_seen=now,
                 raw_json={'likes': 4}, sentiment='negative')
    conn.commit()

    client = _client(monkeypatch, db)
    notes = client.get('/api/topic-campaign/notes?campaign_key=metric-test').get_json()['notes']
    assert len(notes) == 1
    assert notes[0]['topics'] == ['A', 'B']
    assert notes[0]['likes'] is None
    assert notes[0]['comments'] == 0
    assert notes[0]['metric_conflicts'] == ['likes']
    assert notes[0]['metric_freshness'] == 'UNKNOWN'


def test_invalid_first_seen_makes_new_24h_unknown_not_zero(monkeypatch):
    db = _MemoryDB()
    _insert_note(db.connection, topic='A', note_id='bad-time', first_seen='not-a-date',
                 last_seen='not-a-date', raw_json={})
    db.connection.commit()

    client = _client(monkeypatch, db)
    stats = client.get('/api/topic-campaign/stats?campaign_key=metric-test').get_json()
    assert stats['total']['unique_notes'] == 1
    assert stats['total']['new_notes_24h'] is None


def test_snapshot_ingestion_keeps_missing_unknown_and_explicit_zero():
    db = _MemoryDB()
    conn = db.connection
    campaign._insert_snapshot(conn, 'metric-test', 'missing', {})
    campaign._insert_snapshot(conn, 'metric-test', 'zero', {
        'browse_count': 0, 'discussion_count': '0', 'note_count': 0,
        'new_note_count': 0, 'engagement_count': 0,
    })
    campaign._insert_snapshot(conn, 'metric-test', 'invalid', {
        'browse_count': True, 'discussion_count': -1, 'note_count': 1.5,
    })
    rows = {row['topic']: row for row in conn.execute(
        'SELECT * FROM topic_campaign_snapshots ORDER BY id'
    ).fetchall()}

    missing = campaign._snapshot_view(rows['missing'])
    assert all(missing[key] is None for key in campaign._SNAPSHOT_METRICS)
    assert all(rows['missing'][key] is None for key in campaign._SNAPSHOT_METRICS)

    explicit_zero = campaign._snapshot_view(rows['zero'])
    assert all(explicit_zero[key] == 0 for key in campaign._SNAPSHOT_METRICS)
    assert all(rows['zero'][key] == 0 for key in campaign._SNAPSHOT_METRICS)

    invalid = campaign._snapshot_view(rows['invalid'])
    assert all(invalid[key] is None for key in campaign._SNAPSHOT_METRICS)
    assert all(rows['invalid'][key] is None for key in campaign._SNAPSHOT_METRICS)


def test_note_ingestion_keeps_missing_unknown_and_counts_campaign_unique_notes(monkeypatch):
    import subject_rules

    db = _MemoryDB()
    conn = db.connection
    monkeypatch.setattr(subject_rules, 'subject_hit', lambda _text: False)
    monkeypatch.setattr(campaign, '_classify_note', lambda _note, _hit: ('UGC', 'unknown', 'unknown', 'search_only'))
    note = {'note_id': 'same', 'title': 'A'}

    assert campaign._save_notes(conn, 'metric-test', 'topic-a', [note]) == 1
    first_seen = conn.execute(
        'SELECT first_seen_at FROM topic_campaign_notes WHERE campaign_key=? AND topic=?',
        ('metric-test', 'topic-a'),
    ).fetchone()['first_seen_at']
    assert campaign._save_notes(conn, 'metric-test', 'topic-b', [note]) == 0

    rows = conn.execute(
        'SELECT * FROM topic_campaign_notes WHERE campaign_key=? ORDER BY topic',
        ('metric-test',),
    ).fetchall()
    assert len(rows) == 2
    assert {row['first_seen_at'] for row in rows} == {first_seen}
    assert all(row[key] is None for row in rows for key in ('likes', 'comments', 'collects', 'shares'))


def test_observed_count_rejects_boolean_negative_fractional_and_overflow_values():
    for value in (True, -1, 1.5, str(1 << 63), 'NaN'):
        assert campaign._observed_count(value) is None
    assert campaign._observed_count(0) == 0
    assert campaign._observed_count('17') == 17
