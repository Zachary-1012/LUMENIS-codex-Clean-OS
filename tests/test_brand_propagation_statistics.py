import json
import sqlite3

from brand_propagation import BrandPropagationEngine, PropagationEventCategory


def _engine(tmp_path):
    path = tmp_path / 'brand-propagation.sqlite'
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute('''CREATE TABLE brand_propagation_events (
        event_id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,
        entity_type TEXT DEFAULT '',entity_ids TEXT DEFAULT '[]',content_type TEXT DEFAULT '',
        platform TEXT DEFAULT '',sentiment TEXT DEFAULT 'unknown',heat_score REAL DEFAULT 0,
        mention_count INTEGER DEFAULT 0,engagement_total INTEGER DEFAULT 0,
        start_time TEXT DEFAULT '',end_time TEXT DEFAULT '',summary TEXT DEFAULT '',
        key_contents TEXT DEFAULT '[]',metadata TEXT DEFAULT '{}',created_at TEXT DEFAULT '')''')
    connection.commit()
    connection.close()
    engine = object.__new__(BrandPropagationEngine)

    def get_conn():
        get_conn.calls += 1
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    get_conn.calls = 0
    engine._get_conn = get_conn
    return engine, get_conn


def _insert(get_conn, event_id, sentiment, platform, *, heat=None):
    metadata = {}
    stored_heat = 0 if heat is None else heat
    if heat is not None:
        metadata['metric_observations'] = {
            'basis': 'EXPLICIT_CALLER_INPUT', 'values': {'heat_score': heat},
        }
    conn = get_conn()
    conn.execute('''INSERT INTO brand_propagation_events
        (event_id,title,category,platform,sentiment,heat_score,metadata,created_at)
        VALUES(?,?,?,?,?,?,?,?)''',
        (event_id, event_id, PropagationEventCategory.BRAND_EVENT.value,
         platform, sentiment, stored_heat, json.dumps(metadata), event_id))
    conn.commit()
    conn.close()


def test_dashboard_uses_full_filter_for_counts_and_keeps_unproven_metrics_unknown(tmp_path):
    engine, get_conn = _engine(tmp_path)
    _insert(get_conn, 'one', 'positive', 'x', heat=0)
    _insert(get_conn, 'two', 'neutral', 'x')
    _insert(get_conn, 'three', 'negative', 'y')
    _insert(get_conn, 'four', 'legacy-label', 'y')

    get_conn.calls = 0
    dashboard = engine.get_dashboard(PropagationEventCategory.BRAND_EVENT.value, top_n=2)

    assert get_conn.calls == 1
    assert dashboard.total_events == 4
    assert dashboard.positive_count == 1
    assert dashboard.neutral_count == 1
    assert dashboard.negative_count == 1
    assert dashboard.unknown_sentiment_count == 1
    assert dashboard.platform_distribution == {'x': 2, 'y': 2}
    assert dashboard.avg_heat is None
    assert dashboard.heat_observed_count == 1
    assert dashboard.heat_unknown_count == 3
    assert dashboard.metric_freshness == 'UNKNOWN'
    assert dashboard.metric_completeness == 'UNKNOWN'
    assert dashboard.source_verification == 'NOT_ESTABLISHED'
    assert all(event.heat_score is None for event in dashboard.top_events if event.event_id != 'one')


def test_dashboard_preserves_real_zero_and_computes_heat_only_for_complete_filter(tmp_path):
    engine, get_conn = _engine(tmp_path)
    _insert(get_conn, 'zero', 'positive', 'x', heat=0)
    _insert(get_conn, 'ten', 'neutral', 'x', heat=10)

    dashboard = engine.get_dashboard(PropagationEventCategory.BRAND_EVENT.value)

    assert dashboard.avg_heat == 5
    assert dashboard.heat_observed_count == 2
    assert dashboard.heat_unknown_count == 0
    values = {event.event_id: event.heat_score for event in dashboard.top_events}
    assert values == {'zero': 0.0, 'ten': 10.0}
