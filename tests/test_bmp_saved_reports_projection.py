from tests.test_saved_document_workflow import workspace


def test_reports_project_actual_saved_versions(workspace, monkeypatch):
    import experience_runtime
    import experience_screens
    ws = workspace
    scope = {'domain_id':'zbmp','subject_id':None,'brand_focus_id':None,'global_scope':True}
    saved = ws['work'].save_work(actor=ws['actor'], scope=scope, kind='research', title='Synthetic private BMP research',
        markdown='Private deterministic result', payload={}, citations=[], request_id='bmp-report-projection-001')
    monkeypatch.setattr(experience_runtime, '_bmp_saved_work_actor_scope', lambda binding: (ws['actor'],scope))
    result = experience_screens._build_bmp09(binding={'canonical_scope':'GLOBAL_ALL'})
    # Saved artifact projection is a semantic contract; section positions can change.
    rows = result['saved_artifacts']
    assert len(rows) == 1
    assert rows[0]['id'] == saved['artifact']['artifact_id']
    assert rows[0]['assessment'] == 'NOT_ESTABLISHED_BY_STORAGE'
    assert rows[0]['version'] == 1


def test_content_screens_delegate_exact_scope_and_separate_podcast_plans(workspace, monkeypatch):
    import experience_runtime as runtime
    import experience_screens as screens
    import shared_artifacts
    ws = workspace
    scope = {'domain_id':'zbmp','subject_id':None,'brand_focus_id':None,'global_scope':True}
    monkeypatch.setattr(runtime, '_content_project_scope', lambda *a, **k: (ws['actor'],scope))
    monkeypatch.setattr(runtime, '_shared_work_actor_scope', lambda action: (ws['actor'],scope))
    observed=[]
    def project_list(**kwargs):
        observed.append(kwargs)
        return {'status':'complete','next_cursor':None,'projects':[
            {'artifact_id':'ART-audio','output_kind':'audio','status':'ready'},
            {'artifact_id':'ART-video','output_kind':'video','status':'ready'}]}
    monkeypatch.setattr(shared_artifacts,'list_content_projects',project_list)
    binding={'canonical_scope':'GLOBAL_ALL'}
    content=screens._build_bmp06(binding=binding)
    podcast=screens._build_bmp08(binding=binding)
    assert len(content['sections'][1]['rows'])==2
    assert podcast['sections'][1]['rows'][0]['artifact_id']=='ART-audio'
    assert len(podcast['sections'][1]['rows'])==1
    assert podcast['sections'][2]['rows']==[]
    assert all(row['domain_id']=='zbmp' and row['actor'] is ws['actor'] for row in observed)
