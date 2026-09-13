"""Production memory must not promote unreviewed assets into facts."""
import sqlite3

from agent_memory.semantic import SemanticMemory


def test_all_asset_read_paths_require_verified_admission(tmp_path):
    path = tmp_path / 'assets.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE intelligence_assets (asset_id TEXT, title TEXT, summary TEXT, tags TEXT, sub_library TEXT, updated_at TEXT, knowledge_status TEXT, admission_status TEXT)')
        for index, (knowledge, admission) in enumerate([
            ('FACT', 'ADMITTED'), ('VERIFIED', 'ADMITTED'),
            ('PENDING', 'ADMITTED'), ('CONCEPT', 'ADMITTED'),
            ('FACT', 'CANDIDATE'), ('FACT', None), (None, 'ADMITTED'),
        ]):
            conn.execute('INSERT INTO intelligence_assets VALUES (?,?,?,?,?,?,?,?)',
                         (str(index), 'brand', 'brand', '', 'market', '2026-09-13', knowledge, admission))
    memory = SemanticMemory(db_path=str(path), enabled=True)
    assert {a['asset_id'] for a in memory.search_assets('brand')} == {'0', '1'}
    assert {a['asset_id'] for a in memory.get_assets_by_library('market')} == {'0', '1'}
    assert memory.get_asset('0') is not None
    for index in range(2, 7):
        assert memory.get_asset(str(index)) is None
