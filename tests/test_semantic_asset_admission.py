"""Production memory must not promote unreviewed assets into facts."""
from agent_memory.semantic import SemanticMemory
from tests.test_saved_document_workflow import workspace
from tests.test_scoped_retrieval_completeness import _catalog_source, _memory


def test_all_asset_read_paths_require_verified_admission(workspace, monkeypatch):
    ws = workspace
    states = [('FACT', 'ADMITTED'), ('VERIFIED', 'ADMITTED'),
              ('PENDING', 'ADMITTED'), ('CONCEPT', 'ADMITTED'),
              ('FACT', 'CANDIDATE'), ('FACT', None), (None, 'ADMITTED')]
    sources = {}
    for index, (knowledge, admission) in enumerate(states):
        source, _ = _catalog_source(ws, monkeypatch, str(index), content='brand reference ' + str(index))
        sources[str(index)] = source
        with ws['repo'].transaction() as con:
            con.execute('UPDATE intelligence_assets SET knowledge_status=?,admission_status=? WHERE asset_id=?',
                        (knowledge, admission, str(index)))
    memory = _memory(ws)
    assert {a['asset_id'] for a in memory.search_assets('brand')} == {'0', '1'}
    assert {a['asset_id'] for a in memory.get_assets_by_library('market')} == {'0', '1'}
    assert memory.get_asset('0')['evidence_id'] == sources['0']['evidence_id']
    assert memory.get_asset('1')['source_id'] == sources['1']['source_id']
    for index in range(2, 7):
        assert memory.get_asset(str(index)) is None
    # Catalog labels alone and missing task/scope cannot admit any source.
    unbound = SemanticMemory(db_path=memory.db_path, enabled=True)
    assert unbound.search_assets('brand') == []
    assert unbound.get_assets_by_library('market') == []
    assert unbound.get_asset('0') is None
    with ws['repo'].transaction() as con:
        con.execute("INSERT INTO intelligence_assets(asset_id,title,summary,sub_library,knowledge_status,admission_status) VALUES('unsigned','brand','brand','market','FACT','ADMITTED')")
        con.execute("UPDATE app_evidence_records SET integrity_digest='invalid' WHERE id=?", (sources['0']['evidence_id'],))
    assert memory.get_asset('unsigned') is None
    assert memory.get_asset('0') is None
    assert {a['asset_id'] for a in memory.search_assets('brand')} == {'1'}
