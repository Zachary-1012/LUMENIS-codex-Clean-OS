"""Both existing BMP identifier headers resolve to one registered scope."""
from tests.test_saved_document_workflow import workspace
from tests.test_entity_profile_lifecycle import _register


def test_brand_header_is_resolved_and_conflicting_pair_is_rejected(workspace):
    from experience_runtime import _bmp01_read_scope
    import subject_registry
    scope = _register(workspace)
    registered = subject_registry.list_subjects('BMP')[0]
    headers = {'X-Domain-ID': 'BMP', 'X-Lumenis-Context-Mode': 'FOCUS',
               'X-Brand-Focus-ID': scope['brand_focus_id']}
    with workspace['app'].test_request_context('/', environ_overrides={'REMOTE_ADDR': '127.0.0.1'}, headers=headers):
        binding, error = _bmp01_read_scope()
        assert error is None
        assert binding['brand_focus_id'] == scope['brand_focus_id']
        assert binding['subject_id'] == registered['subject_id']
    with workspace['app'].test_request_context('/', environ_overrides={'REMOTE_ADDR': '127.0.0.1'}, headers={**headers, 'X-Subject-ID': registered['subject_id']}):
        binding, error = _bmp01_read_scope()
        assert error is None and binding['scope_verified']
    with workspace['app'].test_request_context('/', environ_overrides={'REMOTE_ADDR': '127.0.0.1'}, headers={**headers, 'X-Subject-ID': registered['subject_id'], 'X-Brand-Focus-ID': 'foreign'}):
        binding, error = _bmp01_read_scope()
        assert binding is None and error[1] == 400
    with workspace['app'].test_request_context('/', environ_overrides={'REMOTE_ADDR': '127.0.0.1'}, headers={**headers, 'X-Lumenis-Context-Mode': 'GLOBAL_ALL'}):
        binding, error = _bmp01_read_scope()
        assert binding is None and error[1] == 400
