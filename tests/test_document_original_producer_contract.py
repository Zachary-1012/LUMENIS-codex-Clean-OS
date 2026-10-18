"""Original-byte reader rejects validly signed records from unrelated producers."""
import json
import pytest
from tests.test_saved_document_workflow import workspace, _source


@pytest.mark.parametrize('column,value', [
    ('source', 'collector'), ('feature_id', 'UNRELATED_FEATURE'),
    ('provider', 'other-provider'), ('version', 'document-import/999'),
])
def test_original_reader_rejects_resigned_wrong_producer(workspace, column, value):
    from lumenis.shared.evidence import store
    _, _, imported = _source(workspace)
    with workspace['repo'].transaction() as con:
        # Column is from the fixed parameter list above, never request input.
        con.execute(f'UPDATE app_evidence_records SET {column}=? WHERE id=?',
                    (value, imported['evidence_id']))
        store._sign_evidence_record(con, imported['evidence_id'])
    with workspace['repo'].connection(read_only=True, wal=False) as con:
        cur = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (imported['evidence_id'],))
        record = dict(zip((c[0] for c in cur.description), cur.fetchone()))
        assert store.classify_evidence_integrity(record)['verified'] is True
        record['provenance'] = json.loads(record['collection_metadata'])
        with pytest.raises(ValueError, match='DOCUMENT_SOURCE_PRODUCER_INVALID'):
            workspace['documents']._source_bytes(con, record)


@pytest.mark.parametrize('column,value', [
    ('source','document_import'), ('feature_id','DOCUMENT_IMPORT'),
    ('provider','collector-native-original'), ('version','collected-native-source:v1'),
])
def test_browser_source_rejects_resigned_producer_substitution(workspace,monkeypatch,column,value):
    from tests.test_browser_extract_saved_work import _admitted_snapshot
    from lumenis.shared.evidence import store
    ws=workspace;obj,cap,args,source,token=_admitted_snapshot(ws,monkeypatch)
    with ws['repo'].transaction() as con:
        con.execute(f'UPDATE app_evidence_records SET {column}=? WHERE id=?',(value,source['evidence_id']))
        store._sign_evidence_record(con,source['evidence_id'])
    with ws['repo'].connection() as con:
        record=dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',(source['evidence_id'],)).fetchone())
        assert store.classify_evidence_integrity(record)['verified']
        record['provenance']=json.loads(record['collection_metadata'])
        with pytest.raises(ValueError):
            ws['documents']._source_bytes(con,record)
