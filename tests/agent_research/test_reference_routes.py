"""Real reference selection -> task/report/SavedWork dependency HTTP chain."""
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_growth_research_shared import research, upload, start, poll, BASE, SHARED


def adopt(ws):
    response = ws['api'].post(BASE + '/reference-work', headers=SHARED,
        json={'asset_id': 'scenarios:indie_game_sea', 'request_id': 'http-adopt-scenario',
              'edits': {'inputs': {'budget': 300, 'budget_currency': 'USD'}, 'goal': 'Interview 20 participants'}})
    assert response.status_code == 200, response.get_json()
    return response.get_json()['result']['reference']


def revise(ws, ref, operation='update', request_id='http-revise-scenario'):
    response = ws['api'].post(BASE + '/reference-work/' + ref['artifact_id'], headers=SHARED,
        json={'request_id': request_id, 'expected_sha256': ref['sha256'], 'operation': operation,
              **({'edits': {'inputs': {'budget': 450}}} if operation == 'update' else {})})
    assert response.status_code == 200, response.get_json()
    return response.get_json()['result']['reference']


def test_scenario_selection_edit_deferred_task_report_and_saved_readback(research):
    ref = revise(research, adopt(research))
    response = research['api'].get(BASE + '/reference-work/' + ref['artifact_id'], headers=SHARED)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()['result']['document']['payload']['research_reference']['current']['inputs']['budget'] == 450
    source = upload(research, 'A source supplied for analysis. Growth effects remain unknown.')
    task = start(research, source, reference=ref, defer=True, business_question='Assess the interview plan')
    assert task['state'] == 'pending' and task['reference'] == ref
    resumed = research['api'].post(BASE + '/tasks/' + task['task_id'] + '/resume', headers=SHARED, json={})
    assert resumed.status_code == 202, resumed.get_json()
    task = poll(research, resumed.get_json()['task'])
    assert task['state'] == 'succeeded', task
    report = task['result']
    assert report['reference_context']['parameters']['inputs']['budget'] == 450
    assert report['reference_context']['fact_verified'] is False
    saved = research['api'].post(BASE + '/jobs/' + report['job_id'] + '/save', headers=SHARED,
        json={'request_id': 'http-reference-report-save', 'title': 'Scenario research'})
    assert saved.status_code == 200, saved.get_json()
    artifact_id = saved.get_json()['result']['artifact']['artifact_id']
    assert research['api'].get('/api/experience/saved-work/' + artifact_id, headers=SHARED).status_code == 200
    revise(research, ref, request_id='http-invalidate-reference')
    for url in (BASE + '/tasks/' + task['task_id'], BASE + '/jobs/' + report['job_id'],
                '/api/experience/saved-work/' + artifact_id):
        rejected = research['api'].get(url, headers=SHARED)
        assert rejected.status_code != 200, (url, rejected.get_json())


def test_withdrawn_reference_blocks_pending_task_and_new_start(research):
    ref = adopt(research)
    task = start(research, reference=ref, defer=True)
    revise(research, ref, operation='withdraw', request_id='http-withdraw-reference')
    rejected = research['api'].get(BASE + '/tasks/' + task['task_id'], headers=SHARED)
    assert rejected.status_code != 200, rejected.get_json()
    rejected = research['api'].post(BASE + '/start', headers=SHARED,
        json={'reference': ref, 'defer': True})
    assert rejected.status_code != 202, rejected.get_json()


def test_rule_http_reference_date_and_no_clearance(research):
    response = research['api'].post(BASE + '/references/match-rules', headers=SHARED,
        json={'content': '广告 推广', 'regions': ['china'], 'as_of': '2000-01-01'})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()['result']
    assert result['legal_clearance'] is None
    assert all(row['current_legal_validity'] == 'UNKNOWN' for row in result['items'])
    research['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    assert research['api'].get(BASE + '/reference-work', headers=SHARED).status_code in (401, 403)


def test_signed_library_http_select_adopt_reopen_update_and_withdraw(research):
    catalog = research['api'].get(BASE + '/references', headers=SHARED,
                                  query_string={'kind': 'markets', 'query': '美国'}).get_json()['result']
    selected = next(item for item in catalog['items'] if item['code'] == 'US')
    adopted = research['api'].post(BASE + '/reference-library', headers=SHARED,
                                   json={'asset_id': selected['asset_id'], 'request_id': 'http-library-adoption'})
    assert adopted.status_code == 200, adopted.get_json()
    entry = adopted.get_json()['result']
    evidence_id, ref = entry['binding_evidence_id'], entry['reference']
    reopened = research['api'].get(BASE + '/reference-library/' + str(evidence_id), headers=SHARED)
    assert reopened.status_code == 200, reopened.get_json()
    assert reopened.get_json()['result']['knowledge_status'] == 'REFERENCE'
    assert reopened.get_json()['result']['license'] == 'UNKNOWN'
    changed = research['api'].post(BASE + '/reference-work/' + ref['artifact_id'], headers=SHARED,
        json={'request_id': 'http-library-update', 'expected_sha256': ref['sha256'], 'operation': 'update',
              'edits': {'data': {'name': 'User-declared US study label'}}})
    assert changed.status_code == 200, changed.get_json()
    assert research['api'].get(BASE + '/reference-library/' + str(evidence_id), headers=SHARED).status_code != 200
    listed = research['api'].get(BASE + '/reference-library', headers=SHARED,
                                 query_string={'query': 'markets:US'}).get_json()['result']
    assert listed['verification_complete'] and len(listed['items']) == 1
    current = listed['items'][0]
    revise(research, current['reference'], operation='withdraw', request_id='http-library-withdraw')
    assert research['api'].get(BASE + '/reference-library/' + str(current['binding_evidence_id']), headers=SHARED).status_code != 200
    assert research['api'].get(BASE + '/reference-library', headers=SHARED).get_json()['result']['items'] == []
