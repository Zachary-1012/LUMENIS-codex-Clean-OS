"""RedNote persistence keeps missing comment metrics distinct from zero."""

import ast
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _persist_function(db):
    source = (ROOT / "app.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(ROOT / "app.py"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "persist_rednote_data"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {
        "db": db,
        "datetime": datetime,
        "_bypass_evidence_canonical": lambda *args, **kwargs: None,
    }
    exec(compile(ast.fix_missing_locations(module), str(ROOT / "app.py"), "exec"), namespace)
    return namespace["persist_rednote_data"]


class _RecordingDatabase:
    def __init__(self):
        self.notes = []
        self.quality = []

    def insert_note(self, note):
        self.notes.append(dict(note))

    def save_collector_quality(self, note_id, quality):
        self.quality.append((note_id, dict(quality)))


def test_persist_rednote_passes_unknown_and_explicit_zero_without_coercion():
    db = _RecordingDatabase()
    persist = _persist_function(db)

    persist({
        "ok": True,
        "notes": [{
            "note_id": "detail-failed",
            "detail_fetched": False,
            "comments": None,
            "comment_count": None,
            "comments_collected": None,
        }],
    })
    unknown_note = db.notes[0]
    unknown_quality = db.quality[0][1]
    assert unknown_note["comments"] is None
    assert unknown_note["comments_collected"] is None
    assert unknown_quality["comments_collected"] is None

    persist({"ok": True, "notes": [{"note_id": "legacy-missing", "detail_fetched": False}]})
    missing_note = db.notes[1]
    missing_quality = db.quality[1][1]
    assert missing_note["comments"] is None
    assert missing_note["comments_collected"] is None
    assert missing_quality["comments_collected"] is None

    persist({
        "ok": True,
        "notes": [{
            "note_id": "observed-zero",
            "detail_fetched": True,
            "comments": 0,
            "comment_count": 0,
        }],
    })
    zero_note = db.notes[2]
    zero_quality = db.quality[2][1]
    assert zero_note["comments"] == 0
    assert zero_note["comments_collected"] == 0
    assert zero_quality["comments_collected"] == 0


def test_persist_rednote_nulls_preserve_existing_metrics_and_zero_updates(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "rednote-comments.sqlite3"))
    import database
    from lumenis.shared.database import DatabaseRepository

    db_path = tmp_path / "rednote-comments.sqlite3"
    repository = DatabaseRepository(str(db_path))
    monkeypatch.setattr(database, "get_repository", lambda: repository)
    monkeypatch.setattr(database, "DB_PATH", str(db_path))
    database.init_db()
    with repository.connection() as connection:
        fields = {row["name"]: row for row in connection.execute("PRAGMA table_info(notes)")}
    assert fields["comments"]["notnull"] == 0
    assert fields["comments_collected"]["notnull"] == 0

    database.insert_note({"note_id": "note-1", "comments": 12, "comments_collected": 7})
    persist = _persist_function(database)

    persist({
        "ok": True,
        "notes": [{
            "note_id": "note-1",
            "detail_fetched": False,
            "comments": None,
            "comment_count": None,
            "comments_collected": None,
        }, {
            "note_id": "unknown-new",
            "detail_fetched": False,
            "comments": None,
            "comment_count": None,
            "comments_collected": None,
        }],
    })
    with database.get_db() as connection:
        existing_row = connection.execute(
            "SELECT comments, comments_collected FROM notes WHERE note_id = ?",
            ("note-1",),
        ).fetchone()
        new_row = connection.execute(
            "SELECT comments, comments_collected FROM notes WHERE note_id = ?",
            ("unknown-new",),
        ).fetchone()
        unknown_quality = connection.execute(
            "SELECT comments_collected FROM collector_quality_log WHERE note_id = ? ORDER BY id DESC LIMIT 1",
            ("unknown-new",),
        ).fetchone()
    assert tuple(existing_row) == (12, 7)
    assert tuple(new_row) == (None, None)
    assert unknown_quality[0] is None

    persist({
        "ok": True,
        "notes": [{
            "note_id": "note-1",
            "detail_fetched": True,
            "comments": 0,
            "comment_count": 0,
        }],
    })
    with database.get_db() as connection:
        row = connection.execute(
            "SELECT comments, comments_collected FROM notes WHERE note_id = ?",
            ("note-1",),
        ).fetchone()
        zero_quality = connection.execute(
            "SELECT comments_collected FROM collector_quality_log WHERE note_id = ? ORDER BY id DESC LIMIT 1",
            ("note-1",),
        ).fetchone()
    assert tuple(row) == (0, 0)
    assert zero_quality[0] == 0
