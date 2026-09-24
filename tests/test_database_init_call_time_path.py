import os
import subprocess
import sys
from pathlib import Path


def test_init_db_uses_current_canonical_path(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    import_time_db = tmp_path / "import-time" / "old.sqlite3"
    call_time_db = tmp_path / "call-time" / "active.sqlite3"
    env = os.environ.copy()
    env["ZBC_DB_PATH"] = str(import_time_db)
    env["ROUND03_CALL_TIME_DB"] = str(call_time_db)
    code = (
        "import os, database; "
        "os.environ['ZBC_DB_PATH'] = os.environ['ROUND03_CALL_TIME_DB']; "
        "database.init_db()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert call_time_db.is_file(), "canonical call-time database was not created"
    assert not import_time_db.parent.exists(), "init_db created an obsolete import-time directory"
