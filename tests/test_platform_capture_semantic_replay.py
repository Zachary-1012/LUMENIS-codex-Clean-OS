"""Synthetic native-store regression: capture lineage is not observation freshness."""
import json
import sqlite3
import threading

import pytest

from lumenis.shared.database.platform_content import _CONTENT_FIELDS, _persist_native_records
from lumenis.system.collector.adapters.platform_naming import map_raw_to_normalized


@pytest.fixture
def native_store():
    with sqlite3.connect(":memory:") as connection:
        connection.execute(
            "CREATE TABLE platform_contents (platform TEXT, platform_content_id TEXT, "
            + ", ".join(_CONTENT_FIELDS)
            + ", raw_data TEXT, first_collected_at TEXT, last_collected_at TEXT, "
            "collected_at TEXT, UNIQUE(platform, platform_content_id))"
        )
        connection.execute(
            "CREATE TABLE metric_snapshots (id INTEGER PRIMARY KEY, entity_type TEXT, "
            "entity_key TEXT, likes, comments, collects, shares, raw_json TEXT, "
            "source TEXT, collector_version TEXT, snapshot_at TEXT)"
        )
        yield connection


def _write(connection, record, evidence_id=1, now="2026-10-17T00:00:00+00:00"):
    content = map_raw_to_normalized(record, "xiaohongshu")
    _persist_native_records(
        [record], [content], expected_ids=["synthetic-note"], platform="xiaohongshu",
        evidence_id=evidence_id, product="CTH", domain="cth", subject="synthetic",
        brand=None, now=now, connection=connection,
    )


def _state(connection):
    row = connection.execute(
        "SELECT first_collected_at, last_collected_at, collected_at, raw_data "
        "FROM platform_contents"
    ).fetchone()
    return row[:3], json.loads(row[3])


BASE = {"note_id": "synthetic-note", "title": "Synthetic title", "content": "Synthetic body", "likes": 7}


@pytest.mark.parametrize("metadata", [
    {"captured_at": "2026-10-18T00:00:00+00:00"},
    {"collected_at": "2026-10-18T00:00:00+00:00"},
    {"last_collected_at": "2026-10-18T00:00:00+00:00"},
    {},
])
@pytest.mark.parametrize("evidence_id", [1, 2])
def test_metadata_only_replay_retains_observation_time_and_current_lineage(native_store, metadata, evidence_id):
    _write(native_store, BASE)
    before, original_raw = _state(native_store)
    original_metrics = native_store.execute("SELECT * FROM metric_snapshots").fetchall()
    _write(native_store, {**BASE, **metadata}, evidence_id=evidence_id, now="2026-10-18T00:00:00+00:00")
    after, current_raw = _state(native_store)
    assert after == before
    assert current_raw == {**BASE, **metadata, "_lumenis_evidence_id": evidence_id}
    assert original_raw["_lumenis_evidence_id"] == 1
    assert native_store.execute("SELECT * FROM metric_snapshots").fetchall() == original_metrics


@pytest.mark.parametrize("change", [
    {"title": "Changed title"}, {"likes": 8}, {"likes": None}, {"likes": 0},
    {"source_extension": {"business_value": "new native source dimension"}},
])
def test_business_change_refreshes_time_including_native_only_fields(native_store, change):
    _write(native_store, BASE)
    before, _ = _state(native_store)
    _write(native_store, {**BASE, **change}, evidence_id=2, now="2026-10-18T00:00:00+00:00")
    after, current_raw = _state(native_store)
    assert after == (before[0], "2026-10-18T00:00:00+00:00", "2026-10-18T00:00:00+00:00")
    assert current_raw == {**BASE, **change, "_lumenis_evidence_id": 2}


def test_normalized_business_correction_refreshes_even_with_same_raw(native_store):
    _write(native_store, BASE)
    before, _ = _state(native_store)
    native_store.execute("UPDATE platform_contents SET title='Old normalized value'")
    _write(native_store, BASE, now="2026-10-18T00:00:00+00:00")
    after, _ = _state(native_store)
    assert after == (before[0], "2026-10-18T00:00:00+00:00", "2026-10-18T00:00:00+00:00")
    assert native_store.execute("SELECT title FROM platform_contents").fetchone()[0] == BASE["title"]


def test_native_json_type_change_is_business_change(native_store):
    _write(native_store,{**BASE,'native_flag':1},now='2026-10-17T00:00:00+00:00')
    before,_=_state(native_store)
    _write(native_store,{**BASE,'native_flag':True},evidence_id=2,now='2026-10-18T00:00:00+00:00')
    after,raw=_state(native_store)
    assert type(raw['native_flag']) is bool
    assert after==(before[0],'2026-10-18T00:00:00+00:00','2026-10-18T00:00:00+00:00')

@pytest.mark.parametrize("begin", [None, "BEGIN", "BEGIN IMMEDIATE"])
@pytest.mark.parametrize("journal_mode", ["DELETE", "WAL"])
def test_two_connection_semantic_compare_and_write_are_serialized(tmp_path, begin, journal_mode):
    path=tmp_path/'race.sqlite';con=sqlite3.connect(path)
    assert con.execute(f'PRAGMA journal_mode={journal_mode}').fetchone()[0].upper() == journal_mode
    con.execute('CREATE TABLE platform_contents (platform TEXT, platform_content_id TEXT,'+', '.join(_CONTENT_FIELDS)+',raw_data TEXT,first_collected_at TEXT,last_collected_at TEXT,collected_at TEXT,UNIQUE(platform,platform_content_id))')
    con.execute('CREATE TABLE metric_snapshots(id INTEGER PRIMARY KEY,entity_type TEXT,entity_key TEXT,likes,comments,collects,shares,raw_json TEXT,source TEXT,collector_version TEXT,snapshot_at TEXT)')
    _write(con,{**BASE,'native_value':'old'});con.commit();con.close()
    read_started=threading.Event();writer_started=threading.Event();writer_done=threading.Event();errors=[];trace=[]
    def writer():
        try:
            assert read_started.wait(2)
            b=sqlite3.connect(path,timeout=3);writer_started.set()
            _write(b,{**BASE,'native_value':'new'},evidence_id=2,now='2026-10-19T00:00:00+00:00')
            b.commit();b.close();writer_done.set()
        except Exception as exc:errors.append(exc);writer_done.set()
    thread=threading.Thread(target=writer);thread.start()
    class ReadCursor(sqlite3.Cursor):
        def execute(self,sql,*args,**kwargs):
            self.is_native_read=sql.startswith('SELECT raw_data FROM platform_contents')
            return super().execute(sql,*args,**kwargs)
        def fetchone(self):
            row=super().fetchone()
            if self.is_native_read:
                read_started.set();assert writer_started.wait(2);writer_done.wait(.2)
            return row
    class ReadHook(sqlite3.Connection):
        def execute(self,sql,*args,**kwargs):
            return self.cursor(factory=ReadCursor).execute(sql,*args,**kwargs)
    a=sqlite3.connect(path,timeout=3,factory=ReadHook)
    a.set_trace_callback(trace.append)
    if begin is not None:
        a.execute(begin)
    _write(a,{**BASE,'native_value':'old','captured_at':'new transport'},evidence_id=3,now='2026-10-18T00:00:00+00:00')
    a.commit();a.close();thread.join(4)
    assert not thread.is_alive() and not errors,errors
    with sqlite3.connect(path) as check:
        stamps,raw=_state(check)
        assert raw['native_value']=='new',(stamps,raw,trace)
        assert stamps[1:]==('2026-10-19T00:00:00+00:00',)*2


def test_change_detection_is_json_type_sensitive(native_store):
    from lumenis.shared.database.platform_content import platform_records_changed
    _write(native_store, {**BASE, "native_flag": 1})
    assert platform_records_changed(
        [{**BASE, "native_flag": True}], platform="xiaohongshu", connection=native_store,
    ) is True


@pytest.mark.parametrize("begin", ["BEGIN", "BEGIN IMMEDIATE"])
def test_native_write_keeps_caller_transaction_and_rollback(native_store, begin):
    _write(native_store, BASE)
    native_store.commit()
    before = _state(native_store)
    native_store.execute(begin)
    _write(native_store, {**BASE, "native_flag": True}, evidence_id=2,
           now="2026-10-18T00:00:00+00:00")
    assert native_store.in_transaction
    native_store.rollback()
    assert _state(native_store) == before
