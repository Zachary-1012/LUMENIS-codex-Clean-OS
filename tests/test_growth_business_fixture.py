"""Real Importer/retained-byte setup for synthetic business route tests."""
from pathlib import Path
import sqlite3


def prepare_owner_source(ws):
    from experience_runtime import _source_brief_context
    from lumenis.importer import documents
    from lumenis.system.security import permission
    import shared_artifacts
    shared_artifacts.ensure_artifact_table()
    ws['gate'].grant_permission(permission.PermissionLevel.COMMIT)
    path = Path(ws['db']).parent / 'owned-business-source.txt'
    path.write_text('The source reports zero participants.', encoding='utf-8')
    provenance = {'source_url': 'https://example.org/owned-route', 'published_at': None,
        'captured_at': '2026-10-03T00:00:00Z', 'rights': 'public-reference-only',
        'title': 'Self-authored synthetic source for isolated owner test'}
    with ws['app'].test_request_context('/', headers=ws['headers'], environ_overrides={'REMOTE_ADDR': '127.0.0.1'}):
        _, _, _, actor = _source_brief_context('write', include_actor=True)
        args = {'actor': actor, 'scope': ws['scope'], 'provenance': provenance}
        resource = documents.document_import_resource(str(path), **args)
        ws['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value,
                                 resource=resource, granted_by='isolated-test')
        imported = documents.import_document(str(path), **args)
    if ws.get('source_id') != imported['source_id']:
        with sqlite3.connect(ws['db']) as con:
            con.execute('DELETE FROM canonical_data WHERE source_id=?', (ws.get('source_id'),))
    ws['source_id'] = imported['source_id']
    return imported
