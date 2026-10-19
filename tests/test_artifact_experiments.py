"""Owned, explicitly declared outcomes; no assertion of real audience exposure."""
import copy
import json
import pytest
from tests.test_saved_document_workflow import workspace, _save
from lumenis.system.security import permission
from lumenis.shared.reporting import artifact_experiments as experiments


def _input(w, data):
    path = w['root'] / 'experiment.txt'
    path.write_text(json.dumps(data))
    args = dict(actor=w['actor'], scope=w['scope'], provenance={
        'source_url': None, 'source_origin': {'kind':'approved-file','ref':'owned-variant-observations'}, 'published_at': None, 'captured_at': '2026-10-17T00:00:00Z',
        'rights': 'owner-approved', 'title': 'Owned synthetic variant observations',
        'content_origin': {'kind': 'self-authored', 'claim_type': 'synthetic_sample'},
    })
    resource = w['documents'].document_import_resource(str(path), **args)
    w['gate'].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=resource, granted_by='isolated-test')
    return w['documents'].import_document(str(path), **args)


@pytest.fixture
def experiment(workspace, monkeypatch):
    w = workspace
    monkeypatch.setattr(experiments, 'get_repository', lambda: w['repo'])
    versions = [_save(w, title=title, request_id='variant-title-'+str(i))
                for i,title in enumerate(['Owned first headline', 'Owned second headline'])]
    arms = [{'id': chr(97+i), 'variant': {
        'kind': 'saved_work_title', 'artifact_id': version['artifact']['artifact_id'],
        'sha256': version['artifact']['sha256'], 'version': version['document']['version'],
    }} for i,version in enumerate(versions)]
    data = {'schema': experiments.SCHEMA,
            'metric': {'name': 'declared_click', 'trial_definition': 'one unique fixture impression',
                       'success_definition': 'fixture click outcome true'},
            'observation_origin': 'engineering_fixture',
            'window': {'start': '2026-10-01T00:00:00Z', 'end': '2026-10-02T00:00:00Z'},
            'arms': arms,
            'observations': [{'event_id': str(i), 'arm_id': 'a' if i<30 else 'b',
                              'observed_at': '2026-10-01T12:00:00Z', 'outcome': i % 3 == 0} for i in range(60)],
            'decision': {'minimum_trials': 20, 'stop_probability': .95, 'enable_thompson': False}}
    return w, data, versions


def test_title_variants_source_save_revision_and_old_versions(experiment):
    from canonical_metrics import registry_snapshot
    registered = registry_snapshot()["FN-STATISTICS-EXPERIMENT"]
    assert registered["artifact_bound_api"] == "/api/experience/reports/artifact-experiments"
    assert experiments.capabilities()["business_purpose"] == registered["business_purpose"]
    w, data, variants = experiment
    source = _input(w, data)
    result = experiments.analyze(source['evidence_id'], actor=w['actor'], scope=w['scope'])
    assert result['state'] == 'READY'
    assert result['result']['counts'] == [{'id':'a','successes':10,'trials':30}, {'id':'b','successes':10,'trials':30}]
    assert result['result']['variants'][0]['variant']['title'] == 'Owned first headline'
    old = experiments.save(source['evidence_id'], actor=w['actor'], scope=w['scope'], request_id='experiment-save-1')
    # A later document title never silently changes the originally selected version.
    _save(w, title='New headline revision', request_id='variant-new-revision',
          work_id=variants[0]['document']['work_id'], previous_artifact_id=variants[0]['artifact']['artifact_id'])
    assert experiments.read(old['artifact']['artifact_id'], actor=w['actor'], scope=w['scope'])['document']['version'] == 1
    data['observations'][0]['outcome'] = False
    source2 = _input(w, data)
    new = experiments.save(source2['evidence_id'], actor=w['actor'], scope=w['scope'], request_id='experiment-save-2',
                           work_id=old['document']['work_id'], previous_artifact_id=old['artifact']['artifact_id'])
    assert new['document']['version'] == 2
    for saved in (old,new):
        reopened = experiments.read(saved['artifact']['artifact_id'], actor=w['actor'], scope=w['scope'])
        assert reopened['artifact']['sha256'] == saved['artifact']['sha256']


@pytest.mark.parametrize('change,code', [
    ('hash', 'VERSION_MISMATCH'), ('version', 'VERSION_MISMATCH'),
    ('same', 'IDENTICAL_VARIANTS'), ('duplicate_event', 'OBSERVATION_INVALID'),
    ('unknown_arm', 'OBSERVATION_INVALID'), ('not_bool', 'OBSERVATION_INVALID'),
    ('outside', 'OUTSIDE_WINDOW'), ('timezone', 'TIMEZONE_REQUIRED'),
    ('fake_label', 'VARIANT_INVALID'),
])
def test_invalid_source_binding_never_invents_trials(experiment, change, code):
    w, data, _ = experiment
    if change == 'hash': data['arms'][0]['variant']['sha256'] = '0'*64
    elif change == 'version': data['arms'][0]['variant']['version'] = 2
    elif change == 'same': data['arms'][1]['variant'] = copy.deepcopy(data['arms'][0]['variant'])
    elif change == 'duplicate_event': data['observations'][1]['event_id'] = '0'
    elif change == 'unknown_arm': data['observations'][0]['arm_id'] = 'fake'
    elif change == 'not_bool': data['observations'][0]['outcome'] = 1
    elif change == 'outside': data['observations'][0]['observed_at'] = data['window']['end']
    elif change == 'timezone': data['observations'][0]['observed_at'] = '2026-10-01T12:00:00'
    elif change == 'fake_label': data['arms'][0]['variant']['title'] = 'Not the saved title'
    source = _input(w, data)
    with pytest.raises(ValueError, match=code):
        experiments.analyze(source['evidence_id'], actor=w['actor'], scope=w['scope'])


def test_generic_report_cannot_fake_variant_identity_and_source_corruption(experiment):
    w, data, _ = experiment
    source = _input(w, data)
    analyzed = experiments.analyze(source['evidence_id'], actor=w['actor'], scope=w['scope'])
    forged = copy.deepcopy(analyzed['saved_work_draft'])
    forged['payload']['artifact_experiment']['variants'][0]['variant']['title'] = 'Invented title'
    saved = w['work'].save_work(**forged, actor=w['actor'], scope=w['scope'], request_id='forged-experiment')
    with pytest.raises(ValueError, match='REPORT_BINDING_MISMATCH'):
        experiments.read(saved['artifact']['artifact_id'], actor=w['actor'], scope=w['scope'])
    valid = experiments.save(source['evidence_id'], actor=w['actor'], scope=w['scope'], request_id='valid-experiment')
    relative = w['repo'].query_one('SELECT relative_path FROM lumenis_shared_artifacts WHERE artifact_id=?', (source['source_artifact_ref'],))[0]
    (w['root'] / 'artifacts' / relative).write_bytes(b'changed original source')
    with pytest.raises(ValueError):
        experiments.read(valid['artifact']['artifact_id'], actor=w['actor'], scope=w['scope'])


def test_scope_actor_and_upstream_artifact_integrity(experiment):
    w, data, variants = experiment
    source = _input(w, data)
    saved = experiments.save(source['evidence_id'], actor=w['actor'], scope=w['scope'], request_id='access-experiment')
    with pytest.raises((ValueError, PermissionError)):
        experiments.read(saved['artifact']['artifact_id'], actor='unverified-actor', scope=w['scope'])
    wrong = {**w['scope'], 'domain_id': 'zbmp'}
    with pytest.raises((ValueError, PermissionError)):
        experiments.read(saved['artifact']['artifact_id'], actor=w['actor'], scope=wrong)
    relative = w['repo'].query_one('SELECT relative_path FROM lumenis_shared_artifacts WHERE artifact_id=?', (variants[0]['artifact']['artifact_id'],))[0]
    (w['root'] / 'artifacts' / relative).write_bytes(b'changed title artifact')
    with pytest.raises(ValueError):
        experiments.read(saved['artifact']['artifact_id'], actor=w['actor'], scope=w['scope'])

from tests.test_content_project_storage import media_store


def test_real_rendered_cover_variants_save_read_and_live_account_revocation(media_store, monkeypatch, tmp_path):
    from tests.test_content_project_storage import approve, import_source, ACTOR, SCOPE
    import shared_artifacts as artifacts
    import canonical_data
    from lumenis.shared.evidence import store
    from lumenis.importer import documents
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.content_creation.video_editing import Timeline

    repository = media_store['repository']
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'fixture':'owned-test-key'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'fixture')
    for module in (experiments, saved_work, documents, store):
        monkeypatch.setattr(module, 'get_repository', lambda: repository)
    store.init_evidence_store(str(repository.db_path))
    with repository.transaction() as con:
        store.ensure_evidence_schema(con)
    canonical_data.ensure_canonical_table(str(repository.db_path))
    approve(media_store)
    original = import_source(media_store)
    sid = original['artifact']['artifact_id']
    variants = []
    with artifacts.resolve_content_source_assets([sid], actor=ACTOR, **SCOPE) as sources:
        asset = sources[0]['asset']
        timeline = Timeline.from_assets([asset]).add_audio_track('voice', audio_role='voiceover')
        timeline = timeline.add_clip(asset.asset_id, track_id='voice', audio_role='voiceover', source_out=.4)
        for i,title in enumerate(['封面甲', '封面乙']):
            staged = artifacts.stage_timeline_artifact(
                timeline, actor=ACTOR, **SCOPE, source_execution_id='experiment-cover-'+str(i),
                output_kind='audio', source_artifact_refs=[sid],
                delivery_options={'podcast_cover': {'title':title, 'subtitle':'自有合成工程例'}},
            )
            project, _, record, _ = artifacts._verified_content_project(staged['artifact']['artifact_id'], actor=ACTOR, **SCOPE)
            variants.append({'id':str(i), 'variant': {
                'kind':'media_cover', 'artifact_id':record['artifact_id'], 'sha256':record['sha256'],
                'version':project['timeline']['version'], 'filename':'podcast-cover.png',
                'member_sha256':project['delivery_manifest']['podcast-cover.png']['sha256']}})
    w = {'root':tmp_path, 'repo':repository, 'gate':media_store['gate'], 'actor':ACTOR,
         'scope':{'domain_id':'zbmp','subject_id':None,'brand_focus_id':None,'global_scope':True},
         'documents':documents, 'work':saved_work}
    data = {'schema':experiments.SCHEMA,
            'metric':{'name':'owned click','trial_definition':'fixture impression','success_definition':'fixture outcome'},
            'observation_origin':'engineering_fixture',
            'window':{'start':'2026-10-01T00:00:00Z','end':'2026-10-02T00:00:00Z'},
            'arms':variants,
            'observations':[{'event_id':str(i),'arm_id':str(i%2),'observed_at':'2026-10-01T12:00:00Z','outcome':i%4==0} for i in range(60)],
            'decision':{'minimum_trials':20,'stop_probability':.95,'enable_thompson':False}}
    source = _input(w,data)
    saved = experiments.save(source['evidence_id'], actor=ACTOR, scope=w['scope'], request_id='cover-experiment-save')
    reopened = experiments.read(saved['artifact']['artifact_id'], actor=ACTOR, scope=w['scope'])
    assert reopened['document']['payload']['artifact_experiment']['variants'][0]['variant']['copy']['title'] == '封面甲'
    with repository.transaction() as con:
        con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    with pytest.raises((ValueError, PermissionError)):
        experiments.read(saved['artifact']['artifact_id'], actor=ACTOR, scope=w['scope'])


def test_variant_change_before_commit_rolls_back(experiment, monkeypatch):
    w, data, variants = experiment
    source = _input(w, data)
    original = experiments.analyze
    calls = 0
    count = w['repo'].query_one('SELECT count(*) FROM lumenis_shared_artifacts')[0]

    def changing(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            relative = w['repo'].query_one('SELECT relative_path FROM lumenis_shared_artifacts WHERE artifact_id=?', (variants[0]['artifact']['artifact_id'],))[0]
            (w['root'] / 'artifacts' / relative).write_bytes(b'changed before publication')
        return original(*args, **kwargs)

    monkeypatch.setattr(experiments, 'analyze', changing)
    with pytest.raises(ValueError):
        experiments.save(source['evidence_id'], actor=w['actor'], scope=w['scope'], request_id='rollback-experiment')
    assert calls == 2
    assert w['repo'].query_one('SELECT count(*) FROM lumenis_shared_artifacts')[0] == count


def test_independent_shared_user_recorded_observations_and_title_versions(experiment):
    w, data, legacy_variants = experiment
    shared = {**w, 'scope': {'scope_kind':'shared_workspace','version':1}}
    variants = [_save(shared, title='Shared title '+str(i), request_id='shared-title-'+str(i)) for i in range(2)]
    data['observation_origin'] = 'user_declared_observations'
    data['arms'] = [{'id':chr(97+i),'variant':{
        'kind':'saved_work_title','artifact_id':v['artifact']['artifact_id'],
        'sha256':v['artifact']['sha256'],'version':v['document']['version']}} for i,v in enumerate(variants)]
    recorded = _save(shared, title='User recorded observations', request_id='shared-observations-1',
                     markdown='User-recorded observations; no independent audience or delivery verification.',
                     payload={'artifact_experiment_input':data})
    inputs = {'observation_artifact_id':recorded['artifact']['artifact_id'],
              'observation_sha256':recorded['artifact']['sha256']}
    result = experiments.analyze(**inputs, actor=w['actor'], scope=shared['scope'])
    assert result['result']['observation_input']['kind'] == 'USER_RECORDED_SAVED_WORK'
    assert result['result']['source_evidence_id'] is None
    assert result['saved_work_draft']['citations'] == []
    saved = experiments.save(**inputs, actor=w['actor'], scope=shared['scope'], request_id='shared-experiment-save')
    reopened = experiments.read(saved['artifact']['artifact_id'], actor=w['actor'], scope=shared['scope'])
    assert reopened['document']['context']['scope_kind'] == 'shared_workspace'
    with pytest.raises(ValueError, match='OBSERVATION_VERSION_MISMATCH'):
        experiments.analyze(**{**inputs,'observation_sha256':'0'*64}, actor=w['actor'], scope=shared['scope'])
    with pytest.raises((ValueError,PermissionError)):
        experiments.read(saved['artifact']['artifact_id'], actor=w['actor'], scope=w['scope'])
    # A title from another owner scope cannot be silently adopted as Shared.
    data['arms'][0]['variant'].update(artifact_id=legacy_variants[0]['artifact']['artifact_id'],
                                     sha256=legacy_variants[0]['artifact']['sha256'])
    wrong = _save(shared, title='Mixed scope observations', request_id='shared-observations-wrong',
                  payload={'artifact_experiment_input':data})
    with pytest.raises((ValueError,PermissionError)):
        experiments.analyze(observation_artifact_id=wrong['artifact']['artifact_id'],
                            observation_sha256=wrong['artifact']['sha256'], actor=w['actor'], scope=shared['scope'])


def test_original_v1_evidence_report_remains_exactly_readable(experiment):
    w, data, _ = experiment
    source = _input(w,data)
    draft = experiments.analyze(source['evidence_id'], actor=w['actor'], scope=w['scope'])['saved_work_draft']
    # Exact pre-Shared v1 wire representation; numeric fields and IDs are unchanged.
    draft['payload']['artifact_experiment'].pop('observation_input')
    draft['payload']['artifact_experiment'].pop('variant_verification')
    draft['markdown'] = '# Saved variant comparison\n\n' + json.dumps(draft['payload'],ensure_ascii=False,indent=2,allow_nan=False)
    saved = w['work'].save_work(**draft, actor=w['actor'], scope=w['scope'], request_id='old-v1-experiment')
    result = experiments.read(saved['artifact']['artifact_id'],actor=w['actor'],scope=w['scope'])
    assert result['document']['payload'] == draft['payload']
    assert result['variant_binding_state'] == 'CURRENT_AUTHORIZATION_AND_EXACT_VERSION_VERIFIED'


# Typed Content variants keep this existing analysis owner and mathematics.
from tests.test_content_multiplatform_routes import client as creation_client
from tests.test_content_multiplatform_routes import create as create_multiplatform, source_spec


@pytest.fixture
def content_experiment(creation_client, monkeypatch):
    http, w = creation_client
    monkeypatch.setattr(experiments, 'get_repository', lambda: w['repo'])
    from experience_runtime import experience_bp
    w['app'].register_blueprint(experience_bp)
    w['http'] = http
    value, source, _ = source_spec(creation_client)
    saved = create_multiplatform(creation_client, value=value)
    variants = saved['document']['payload']['multiplatform']['variants']
    selected = [variants[0], variants[2]]
    data = {'schema': experiments.SCHEMA,
        'metric': {'name': 'declared_read', 'trial_definition': 'one unique manually recorded reader',
                   'success_definition': 'user declared completion'},
        'observation_origin': 'user_declared_observations',
        'window': {'start': '2026-10-01T00:00:00Z', 'end': '2026-10-02T00:00:00Z'},
        'arms': [{'id': chr(97+i), 'variant': {'kind': 'content_variant', 'artifact_id': saved['artifact']['artifact_id'],
                  'sha256': saved['artifact']['sha256'], 'version': saved['document']['version'],
                  'variant_id': variant['id'], 'body_sha256': variant['body_sha256']}} for i, variant in enumerate(selected)],
        'observations': [{'event_id': str(i), 'arm_id': 'a' if i < 30 else 'b',
                          'observed_at': '2026-10-01T12:00:00Z', 'outcome': i % 3 == 0} for i in range(60)],
        'decision': {'minimum_trials': 20, 'stop_probability': .95, 'enable_thompson': False}}
    return w, data, saved, source


def recorded_content_observations(w, data, request_id='content-observations-01'):
    return _save(w, request_id=request_id, payload={'artifact_experiment_input': data})


def test_content_variant_real_binding_analysis_save_reopen(content_experiment):
    w, data, saved, source = content_experiment
    observation = recorded_content_observations(w, data)
    args = {'observation_artifact_id': observation['artifact']['artifact_id'],
            'observation_sha256': observation['artifact']['sha256'], 'actor': w['actor'], 'scope': w['scope']}
    analyzed = experiments.analyze(**args)
    assert analyzed['result']['measurement_truth'] == 'NOT_INDEPENDENTLY_VERIFIED'
    assert analyzed['result']['observation_input']['kind'] == 'USER_RECORDED_SAVED_WORK'
    assert analyzed['result']['counts'] == [{'id': 'a', 'successes': 10, 'trials': 30}, {'id': 'b', 'successes': 10, 'trials': 30}]
    variant = analyzed['result']['variants'][0]['variant']
    assert variant['source_bindings'][0]['evidence_id'] == source['evidence_id']
    assert variant['platform'] == 'website' and variant['language_quality'] == 'NOT_VERIFIED'
    output = experiments.save(**args, request_id='content-experiment-save-01')
    reopened = experiments.read(output['artifact']['artifact_id'], actor=w['actor'], scope=w['scope'])
    assert reopened['document'] == output['document']
    assert experiments.save(**args, request_id='content-experiment-save-01')['replayed']


@pytest.mark.parametrize('field,value', [('body_sha256', '0'*64), ('variant_id', 'missing'), ('version', 2)])
def test_content_variant_wrong_identity_rejected(content_experiment, field, value):
    w, data, saved, _ = content_experiment
    data['arms'][0]['variant'][field] = value
    observation = recorded_content_observations(w, data)
    with pytest.raises((ValueError, PermissionError), match='MISMATCH'):
        experiments.analyze(observation_artifact_id=observation['artifact']['artifact_id'],
            observation_sha256=observation['artifact']['sha256'], actor=w['actor'], scope=w['scope'])


def test_content_variant_copied_payload_has_no_owner_receipt(content_experiment):
    w, data, saved, _ = content_experiment
    forged = _save(w, request_id='copied-content-01', payload=saved['document']['payload'],
                   markdown=saved['document']['markdown'], citations=saved['document']['citations'])
    data['arms'][0]['variant'].update(artifact_id=forged['artifact']['artifact_id'], sha256=forged['artifact']['sha256'])
    observation = recorded_content_observations(w, data)
    with pytest.raises(PermissionError, match='RECEIPT'):
        experiments.analyze(observation_artifact_id=observation['artifact']['artifact_id'],
            observation_sha256=observation['artifact']['sha256'], actor=w['actor'], scope=w['scope'])


def test_content_variant_upstream_source_mutation_blocks_analysis(content_experiment):
    w, data, saved, source = content_experiment
    observation = recorded_content_observations(w, data)
    w['repo'].execute("UPDATE app_evidence_records SET content_hash='changed' WHERE id=?", (source['evidence_id'],))
    with pytest.raises((ValueError, PermissionError)):
        experiments.analyze(observation_artifact_id=observation['artifact']['artifact_id'],
            observation_sha256=observation['artifact']['sha256'], actor=w['actor'], scope=w['scope'])


def test_content_variant_existing_analysis_api_roundtrip(content_experiment):
    w, data, _, _ = content_experiment
    observed = recorded_content_observations(w, data)
    inputs = {'observation_artifact_id': observed['artifact']['artifact_id'],
              'observation_sha256': observed['artifact']['sha256']}
    path = '/api/experience/reports/artifact-experiments'
    analysis = w['http'].post(path, headers=w['headers'], json={'mode': 'analyze', **inputs})
    assert analysis.status_code == 200, analysis.get_json()
    assert analysis.get_json()['result']['result']['measurement_truth'] == 'NOT_INDEPENDENTLY_VERIFIED'
    saved = w['http'].post(path, headers=w['headers'], json={'mode': 'save', 'request_id': 'content-analysis-api-01', **inputs})
    assert saved.status_code == 200, saved.get_json()
    result = saved.get_json()['result']
    read = w['http'].post(path, headers=w['headers'], json={'mode': 'read', 'artifact_id': result['artifact']['artifact_id']})
    assert read.status_code == 200 and read.get_json()['result']['document'] == result['document'], read.get_json()
