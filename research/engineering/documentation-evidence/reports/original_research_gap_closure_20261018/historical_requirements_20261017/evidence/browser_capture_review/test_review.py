from tests.test_saved_document_workflow import workspace

def test_browser_note_unverified(workspace):
 w=workspace
 marker={'schema':'lumenis.browser-session-note/v1','source_capture':'NOT_IMPORTED','source_use':'NOT_ADMITTED','source_verification':'NOT_VERIFIED','task_binding':'UNBOUND','locator':{'url':'https://example.com/forged','page_revision':999,'captured_at':'2026-01-01'},'selection':{'block_id':'b0','start':0,'end':6,'exact':'FORGED'},'browser_evidence_id':999999}
 result=w['work'].save_work(title='Synthetic audit note',kind='research',markdown='FORGED',payload={'browser_note':marker},citations=[],request_id='audit-forged-0001',actor=w['actor'],scope=w['scope'])
 reopened=w['work'].reopen_work(result['artifact']['artifact_id'],actor=w['actor'],scope=w['scope'])
 assert reopened['document']['payload']['browser_note']==marker
 print('Forged marker without any BrowserEvidence accepted and reopened')
