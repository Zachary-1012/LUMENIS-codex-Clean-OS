"""Original SavedWork dependency adoption; user edits never become source facts."""
import pytest
from tests.test_saved_document_workflow import workspace, _save
from lumenis.shared.reporting import work_dependencies as owner


def _setup(ws):
    source = _save(ws, request_id='dep-source-001', markdown='Original report facts.')
    target = _save(ws, request_id='dep-target-001', markdown='Heading\n\nOld paragraph\n\nUntouched tail')
    kwargs = {'actor': ws['actor'], 'scope': ws['scope']}
    spec = {'artifact_id': source['artifact']['artifact_id'], 'start': 0, 'end': 8, 'quote': 'Original'}
    args = dict(dependency_id='paragraph-1', location={'type': 'markdown_paragraph', 'index': 1},
                source=spec, expected_text='Old paragraph', request_id='dep-binding-001', reason='User declares report input')
    return source, target, kwargs, args


def test_explicit_dependency_update_preserves_other_text_and_history(workspace):
    ws = workspace
    source, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    assert owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)['replayed']
    current = owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)
    assert current['items'][0]['state'] == 'CURRENT'
    revised = ws['work'].revise_work(source['artifact']['artifact_id'], **kwargs, request_id='dep-source-002',
        expected_sha256=source['artifact']['sha256'], reason='Revised source text',
        edits=[{'pointer': '/markdown', 'expected': 'Original report facts.', 'value': 'Revised report facts.'}])
    impact = owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)
    assert impact['items'][0]['state'] == 'SOURCE_VERSION_CHANGED'
    update = dict(dependency_id='paragraph-1', source={'artifact_id': revised['artifact']['artifact_id'], 'start': 0, 'end': 7, 'quote': 'Revised'},
                  replacement_text='My explicit revised paragraph', expected_preview_hash=impact['preview_hash'],
                  request_id='dep-accepted-001', reason='I accept this limited edit')
    result = owner.accept_update(bound['artifact']['artifact_id'], **kwargs, **update)
    assert result['document']['markdown'] == 'Heading\n\nMy explicit revised paragraph\n\nUntouched tail'
    assert owner.accept_update(bound['artifact']['artifact_id'], **kwargs, **update)['replayed']
    assert ws['work'].read_committed_work(bound['artifact']['artifact_id'], **kwargs)['document']['markdown'] == target['document']['markdown']
    assert owner.preview_impact(result['artifact']['artifact_id'], **kwargs)['items'][0]['state'] == 'CURRENT'


def test_generic_metadata_cannot_create_or_inherit_dependency_receipt(workspace):
    ws = workspace
    source, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    forged = _save(ws, request_id='dep-forged-001', payload=bound['document']['payload'])
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.preview_impact(forged['artifact']['artifact_id'], **kwargs)
    revised = ws['work'].revise_work(bound['artifact']['artifact_id'], **kwargs, request_id='dep-generic-002',
        expected_sha256=bound['artifact']['sha256'], reason='Generic revision',
        edits=[{'pointer': '/title', 'expected': bound['document']['title'], 'value': 'Changed title'}])
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.preview_impact(revised['artifact']['artifact_id'], **kwargs)


@pytest.mark.parametrize('change,error', [
    ({'source': {'artifact_id': 'missing', 'start': 0, 'end': 2, 'quote': 'no'}}, 'WORK'),
    ({'location': {'type': 'arbitrary', 'path': '/payload/admin'}}, 'LOCATION'),
    ({'expected_text': 'not current'}, 'TARGET_CHANGED'),
])
def test_bad_dependency_inputs_rejected(workspace, change, error):
    _, target, kwargs, args = _setup(workspace)
    with pytest.raises((ValueError, RuntimeError), match=error):
        owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **{**args, **change})


def test_topic_card_binding_updates_only_selected_field(workspace):
    ws = workspace
    source, _, kwargs, args = _setup(ws)
    target = _save(ws, request_id='dep-topic-target', kind='podcast_episode', contract={'id': 'lumenis.podcast-topic-vault', 'version': '1', 'required_payload_paths': ['topic_cards']},
                   payload={'topic_cards': [{'topic_id': 'a', 'title': 'Original title', 'notes': 'Keep notes'},
                                            {'topic_id': 'b', 'title': 'Keep second title', 'notes': ''}]})
    args.update(location={'type': 'topic_card', 'topic_id': 'a', 'field': 'title'}, expected_text='Original title')
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    impact = owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)
    result = owner.accept_update(bound['artifact']['artifact_id'], **kwargs, dependency_id=args['dependency_id'], source=args['source'],
        replacement_text='My chosen title', expected_preview_hash=impact['preview_hash'], request_id='dep-topic-accept', reason='Explicit title change')
    assert result['document']['payload']['topic_cards'][0] == {'topic_id': 'a', 'title': 'My chosen title', 'notes': 'Keep notes'}
    assert result['document']['payload']['topic_cards'][1] == target['document']['payload']['topic_cards'][1]


def test_shared_independent_scope_no_fake_domain(workspace):
    ws = workspace
    ws['scope'] = {'scope_kind': 'shared_workspace', 'version': 1}
    _, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    assert owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)['items'][0]['state'] == 'CURRENT'
    with ws['repo'].connection(read_only=True) as con:
        row = con.execute('SELECT product,inputs_json FROM app_evidence_records WHERE source=?', (owner.SCHEMA,)).fetchone()
    assert row['product'] == 'SHARED'
    assert 'shared_workspace' in row['inputs_json']


def test_preview_cannot_cross_scope_and_tampered_receipt_rejected(workspace):
    ws = workspace
    _, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    with pytest.raises((ValueError, PermissionError)):
        owner.preview_impact(bound['artifact']['artifact_id'], actor=ws['actor'], scope={**ws['scope'], 'domain_id': 'zbmp'})
    with ws['repo'].transaction() as con:
        con.execute('UPDATE app_evidence_records SET content_hash=? WHERE source=?', ('0' * 64, owner.SCHEMA))
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)


def test_local_principal_revocation_rolls_back_dependency_and_receipt(workspace, monkeypatch):
    from lumenis.system.security import permission
    ws = workspace
    _, target, kwargs, args = _setup(ws)
    original = owner.store.record_evidence
    def revoke_after_sign(**params):
        result = original(**params)
        ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
        return result
    monkeypatch.setattr(owner.store, 'record_evidence', revoke_after_sign)
    with pytest.raises((ValueError, PermissionError)):
        owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    with ws['repo'].connection(read_only=True) as con:
        assert con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE source=?', (owner.SCHEMA,)).fetchone()[0] == 0
    ws['app'].config['LUMENIS_OPEN_WORKSPACE'] = True
    assert owner._latest(target['artifact']['artifact_id'], **kwargs)['artifact']['artifact_id'] == target['artifact']['artifact_id']


@pytest.mark.parametrize('domain', ['cth', 'bmp'])
def test_account_scope_binding_alias_and_revocation(workspace, domain):
    ws = workspace
    with ws['repo'].transaction() as con:
        con.execute('CREATE TABLE IF NOT EXISTS v4_users (id INTEGER PRIMARY KEY, role TEXT, status TEXT)')
        con.executemany("INSERT INTO v4_users VALUES (?,'owner','active')", [(99123,), (99124,)])
    ws['actor'] = {'id': 99123}
    ws['scope'] = {**ws['scope'], 'domain_id': domain}
    _, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    normalized = {**kwargs, 'scope': {**ws['scope'], 'domain_id': 'zbmp' if domain == 'bmp' else domain}}
    assert owner.preview_impact(bound['artifact']['artifact_id'], **normalized)['items'][0]['state'] == 'CURRENT'
    with pytest.raises((ValueError, PermissionError)):
        owner.preview_impact(bound['artifact']['artifact_id'], actor={'id': 99124}, scope=ws['scope'])
    with ws['repo'].transaction() as con:
        con.execute("UPDATE v4_users SET status='inactive' WHERE id=99123")
    with pytest.raises((ValueError, PermissionError)):
        owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)


def test_stale_preview_and_wrong_source_work_rejected(workspace):
    ws = workspace
    _, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    impact = owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)
    request = dict(dependency_id=args['dependency_id'], source=args['source'], replacement_text='Chosen edit',
                   expected_preview_hash='0' * 64, request_id='dep-stale-update', reason='Explicit change')
    with pytest.raises(ValueError, match='PREVIEW_CHANGED'):
        owner.accept_update(bound['artifact']['artifact_id'], **kwargs, **request)
    other = _save(ws, request_id='dep-foreign-source', markdown='Other source')
    request.update(expected_preview_hash=impact['preview_hash'], source={'artifact_id': other['artifact']['artifact_id'], 'start': 0, 'end': 5, 'quote': 'Other'})
    with pytest.raises(ValueError, match='SOURCE_WORK_MISMATCH'):
        owner.accept_update(bound['artifact']['artifact_id'], **kwargs, **request)


def test_source_integrity_failure_never_returns_preview_text(workspace):
    import shared_artifacts
    ws = workspace
    source, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    path = shared_artifacts.artifact_root() / source['artifact']['relative_path']
    path.write_bytes(b'corrupted original source bytes')
    with pytest.raises(ValueError, match='INTEGRITY_FAILED'):
        owner.preview_impact(bound['artifact']['artifact_id'], **kwargs)


def test_request_id_conflict_does_not_create_new_version(workspace):
    _, target, kwargs, args = _setup(workspace)
    with pytest.raises(ValueError, match='REQUEST_REUSE_CONFLICT'):
        owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **{**args, 'request_id': 'dep-target-001'})
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    with pytest.raises(ValueError, match='REQUEST_REUSE_CONFLICT'):
        owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **{**args, 'reason': 'Different reason'})
    assert owner._latest(bound['artifact']['artifact_id'], **kwargs)['artifact']['artifact_id'] == bound['artifact']['artifact_id']


def test_explicit_rebinding_discards_forged_payload_and_checks_new_source(workspace):
    ws = workspace
    _, target, kwargs, args = _setup(ws)
    forged = _save(ws, request_id='dep-forged-reset', markdown=target['document']['markdown'],
                   payload={owner.KEY: {'schema': 'forged', 'items': [{'source': 'private'}]}})
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.bind_dependency(forged['artifact']['artifact_id'], **kwargs, **args)
    reset_args = {**args, 'replace_bindings': True, 'request_id': 'dep-reset-valid'}
    rebound = owner.bind_dependency(forged['artifact']['artifact_id'], **kwargs, **reset_args)
    items = owner.preview_impact(rebound['artifact']['artifact_id'], **kwargs)['items']
    assert len(items) == 1 and items[0]['id'] == args['dependency_id']
    assert owner.bind_dependency(forged['artifact']['artifact_id'], **kwargs, **reset_args)['replayed']
    with pytest.raises(ValueError, match='REQUEST_REUSE_CONFLICT'):
        owner.bind_dependency(forged['artifact']['artifact_id'], **kwargs, **{**reset_args, 'replace_bindings': False})


def test_generic_revision_explicit_new_declaration_requires_current_location(workspace):
    ws = workspace
    _, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    revised = ws['work'].revise_work(bound['artifact']['artifact_id'], **kwargs,
        request_id='dep-edited-reset', expected_sha256=bound['artifact']['sha256'], reason='Human edit',
        edits=[{'pointer': '/markdown', 'expected': bound['document']['markdown'],
                'value': 'Heading\n\nEdited paragraph\n\nUntouched tail'}])
    reset_args = {**args, 'replace_bindings': True, 'request_id': 'dep-redeclare'}
    with pytest.raises(ValueError, match='TARGET_CHANGED'):
        owner.bind_dependency(revised['artifact']['artifact_id'], **kwargs, **reset_args)
    with pytest.raises(ValueError, match='WORK'):
        owner.bind_dependency(revised['artifact']['artifact_id'], **kwargs,
            **{**reset_args, 'expected_text': 'Edited paragraph', 'source': {**args['source'], 'artifact_id': 'missing'}})
    rebound = owner.bind_dependency(revised['artifact']['artifact_id'], **kwargs,
        **{**reset_args, 'expected_text': 'Edited paragraph'})
    assert owner.preview_impact(rebound['artifact']['artifact_id'], **kwargs)['items'][0]['target_text'] == 'Edited paragraph'


def _revision_setup(ws):
    source, target, kwargs, args = _setup(ws)
    bound = owner.bind_dependency(target['artifact']['artifact_id'], **kwargs, **args)
    request = dict(request_id='dep-owned-revision-001', expected_sha256=bound['artifact']['sha256'],
                   reason='Normal user edit', edits=[{'pointer': '/title',
                   'expected': bound['document']['title'], 'value': 'Edited title'},
                   {'pointer': '/markdown', 'expected': bound['document']['markdown'],
                    'value': bound['document']['markdown']}])
    return source, bound, kwargs, request


def _owned_counts(ws):
    with ws['repo'].connection(read_only=True) as con:
        return (con.execute('SELECT COUNT(*) FROM lumenis_shared_artifacts').fetchone()[0],
                con.execute('SELECT COUNT(*) FROM app_evidence_records WHERE source=?', (owner.SCHEMA,)).fetchone()[0])


def test_owned_revision_real_caller_shape_replay_and_history(workspace):
    ws = workspace
    _, bound, kwargs, request = _revision_setup(ws)
    before = _owned_counts(ws)
    revised = owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert revised['document']['version'] == bound['document']['version'] + 1
    assert revised['document']['title'] == 'Edited title'
    assert revised['document']['markdown'] == bound['document']['markdown']
    assert revised['document']['citations'] == bound['document']['citations']
    assert owner.preview_impact(revised['artifact']['artifact_id'], **kwargs)['items'][0]['state'] == 'CURRENT'
    assert _owned_counts(ws) == (before[0] + 1, before[1] + 1)
    assert owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)['replayed']
    later = owner.revise_owned_work(revised['artifact']['artifact_id'], **kwargs,
        **{**request, 'request_id': 'dep-owned-revision-002', 'expected_sha256': revised['artifact']['sha256'],
           'edits': [{'pointer': '/title', 'expected': 'Edited title', 'value': 'Later title'}]})
    replay = owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert replay['artifact']['artifact_id'] == revised['artifact']['artifact_id']
    assert ws['work'].read_committed_work(bound['artifact']['artifact_id'], **kwargs)['document'] == bound['document']
    assert later['document']['version'] == revised['document']['version'] + 1
    with pytest.raises(ValueError, match='REUSE_CONFLICT'):
        owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **{**request, 'reason': 'Different request'})


@pytest.mark.parametrize('markdown', ['Changed heading\n\nOld paragraph\n\nUntouched tail',
                                      'Heading\n\nOld paragraph\n\nEdited tail'])
def test_owned_revision_unbound_full_markdown_edits(workspace, markdown):
    _, bound, kwargs, request = _revision_setup(workspace)
    request['edits'] = [{'pointer': '/markdown', 'expected': bound['document']['markdown'], 'value': markdown}]
    result = owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert result['document']['markdown'] == markdown
    assert owner.preview_impact(result['artifact']['artifact_id'], **kwargs)['items'][0]['state'] == 'CURRENT'


@pytest.mark.parametrize('markdown', ['Heading\n\nChanged dependency\n\nUntouched tail',
    'New\n\nHeading\n\nOld paragraph\n\nUntouched tail',
    'Heading\n\nUntouched tail\n\nOld paragraph',
    'Old paragraph\n\nOld paragraph\n\nUntouched tail', 'Heading\n\nUntouched tail'])
def test_owned_revision_changed_shifted_or_duplicate_location_no_write(workspace, markdown):
    _, bound, kwargs, request = _revision_setup(workspace)
    before = _owned_counts(workspace)
    request['edits'] = [{'pointer': '/markdown', 'expected': bound['document']['markdown'], 'value': markdown}]
    with pytest.raises(ValueError, match='LOCATION_CHANGE'):
        owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert _owned_counts(workspace) == before
    assert owner._latest(bound['artifact']['artifact_id'], **kwargs)['document'] == bound['document']


def test_owned_revision_refuses_dependency_scalar_edit_and_forged_parent(workspace):
    _, bound, kwargs, request = _revision_setup(workspace)
    before = _owned_counts(workspace)
    request['edits'] = [{'pointer': '/payload/work_dependencies/items/0/source/quote',
                        'expected': 'Original', 'value': 'Forged'}]
    with pytest.raises(ValueError, match='METADATA_EDIT_FORBIDDEN'):
        owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert _owned_counts(workspace) == before
    forged = _save(workspace, request_id='dep-forged-revision', payload=bound['document']['payload'])
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.revise_owned_work(forged['artifact']['artifact_id'], **kwargs,
            **{**request, 'expected_sha256': forged['artifact']['sha256'],
               'edits': [{'pointer': '/title', 'expected': forged['document']['title'], 'value': 'Forged title'}]})


def test_owned_revision_preserves_stale_source_without_adoption(workspace):
    source, bound, kwargs, request = _revision_setup(workspace)
    workspace['work'].revise_work(source['artifact']['artifact_id'], **kwargs,
        request_id='dep-source-newer-001', expected_sha256=source['artifact']['sha256'],
        reason='New source version', edits=[{'pointer': '/title', 'expected': source['document']['title'], 'value': 'New source title'}])
    revised = owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    impact = owner.preview_impact(revised['artifact']['artifact_id'], **kwargs)
    assert impact['items'][0]['state'] == 'SOURCE_VERSION_CHANGED'
    assert impact['items'][0]['bound_source']['artifact_id'] == source['artifact']['artifact_id']


@pytest.mark.parametrize('failure', ['sign', 'revoke'])
def test_owned_revision_callback_failure_rolls_back(workspace, monkeypatch, failure):
    _, bound, kwargs, request = _revision_setup(workspace)
    before = _owned_counts(workspace)
    files_before = {str(p) for p in workspace['root'].rglob('*') if p.is_file() and p.suffix == '.json'}
    original = owner.store.record_evidence
    def fail(**params):
        result = original(**params)
        if failure == 'sign':
            raise RuntimeError('INJECTED_SIGN_FAILURE')
        workspace['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
        return result
    monkeypatch.setattr(owner.store, 'record_evidence', fail)
    with pytest.raises((ValueError, RuntimeError, PermissionError)):
        owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert _owned_counts(workspace) == before
    workspace['app'].config['LUMENIS_OPEN_WORKSPACE'] = True
    assert {str(p) for p in workspace['root'].rglob('*') if p.is_file() and p.suffix == '.json'} == files_before
    assert owner._latest(bound['artifact']['artifact_id'], **kwargs)['document'] == bound['document']


@pytest.mark.parametrize('length', [2000, 2001, 4000])
def test_owned_revision_preserves_normal_reason_limit(workspace, length):
    _, bound, kwargs, request = _revision_setup(workspace)
    result = owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **{**request, 'reason': 'x' * length})
    assert result['document']['title'] == 'Edited title'


def test_owned_revision_source_head_race_rolls_back_target(workspace, monkeypatch):
    source, bound, kwargs, request = _revision_setup(workspace)
    original = owner._save
    observed = {}
    def change_source(*args, **kw):
        workspace['work'].revise_work(source['artifact']['artifact_id'], **kwargs,
            request_id='dep-source-race-001', expected_sha256=source['artifact']['sha256'],
            reason='Concurrent source version', edits=[{'pointer': '/title',
            'expected': source['document']['title'], 'value': 'Concurrent source'}])
        observed['counts'] = _owned_counts(workspace)
        observed['files'] = {str(p) for p in workspace['root'].rglob('*') if p.is_file() and p.suffix == '.json'}
        return original(*args, **kw)
    monkeypatch.setattr(owner, '_save', change_source)
    with pytest.raises(ValueError, match='SOURCE_CHANGED'):
        owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert _owned_counts(workspace) == observed['counts']
    assert {str(p) for p in workspace['root'].rglob('*') if p.is_file() and p.suffix == '.json'} == observed['files']
    assert owner._latest(bound['artifact']['artifact_id'], **kwargs)['document'] == bound['document']


def test_owned_revision_scope_stale_hash_and_original_generic_guard(workspace):
    _, bound, kwargs, request = _revision_setup(workspace)
    before = _owned_counts(workspace)
    with pytest.raises((ValueError, PermissionError)):
        owner.revise_owned_work(bound['artifact']['artifact_id'], **{**kwargs, 'scope': {**workspace['scope'], 'domain_id': 'zbmp'}}, **request)
    with pytest.raises(ValueError, match='SOURCE_CHANGED'):
        owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **{**request, 'expected_sha256': '0' * 64})
    assert _owned_counts(workspace) == before


def test_owned_revision_unrelated_scalar_and_unicode_range(workspace):
    _, bound, kwargs, request = _revision_setup(workspace)
    request['edits'] = [{'pointer': '/payload/unknowns/0',
        'expected': 'Usefulness needs user review', 'value': 'Human constraint: budget undecided'},
        {'pointer': '/markdown', 'start': 0, 'end': 7, 'expected': 'Heading', 'replacement': '标题 🧭'}]
    result = owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert result['document']['markdown'].startswith('标题 🧭\n\nOld paragraph')
    assert owner.preview_impact(result['artifact']['artifact_id'], **kwargs)['items'][0]['state'] == 'CURRENT'


@pytest.mark.parametrize('scope', [
    {'scope_kind': 'shared_workspace', 'version': 1},
    {'domain_id': 'cth', 'subject_id': None, 'brand_focus_id': None, 'global_scope': True},
    {'domain_id': 'bmp', 'subject_id': None, 'brand_focus_id': None, 'global_scope': True}])
def test_owned_revision_existing_independent_and_domain_scopes(workspace, scope):
    workspace['scope'] = scope
    _, bound, kwargs, request = _revision_setup(workspace)
    result = owner.revise_owned_work(bound['artifact']['artifact_id'], **kwargs, **request)
    assert owner.preview_impact(result['artifact']['artifact_id'], **kwargs)['items'][0]['state'] == 'CURRENT'


@pytest.mark.parametrize('material', [None, [], 'copied-owner-label'])
def test_owned_revision_never_promotes_empty_or_malformed_owner_metadata(workspace, material):
    forged = _save(workspace, request_id='dep-null-forged-001', payload={owner.KEY: material})
    before = _owned_counts(workspace)
    with pytest.raises(ValueError, match='OWNER_RECEIPT_REQUIRED'):
        owner.revise_owned_work(forged['artifact']['artifact_id'], actor=workspace['actor'],
            scope=workspace['scope'], request_id='dep-null-forged-002',
            expected_sha256=forged['artifact']['sha256'], reason='No receipt',
            edits=[{'pointer': '/title', 'expected': forged['document']['title'], 'value': 'Attempt'}])
    assert _owned_counts(workspace) == before
