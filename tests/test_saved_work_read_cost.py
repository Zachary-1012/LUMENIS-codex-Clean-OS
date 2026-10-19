import json
from pathlib import Path
from tests.test_saved_document_workflow import workspace, _save

def test_latest_history_reads_are_linear_and_results_preserved(workspace, monkeypatch):
    ws=workspace
    previous=None
    for n in range(18):
        options={} if previous is None else {'work_id':previous['document']['work_id'], 'previous_artifact_id':previous['artifact']['artifact_id'], 'expected_draft_digest':previous['document']['draft_digest']}
        previous=_save(ws, request_id=f'history-{n:08d}', markdown=f'Revision {n} '+('bounded synthetic text '*100), **options)
    original=Path.open
    counts={'files':0,'bytes':0}
    def measured(path,*args,**kwargs):
        if args and args[0]=='rb' and str(ws['root']/'artifacts') in str(path):
            counts['files']+=1; counts['bytes']+=path.stat().st_size
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',measured)
    result=ws['work'].search_work(actor=ws['actor'],scope=ws['scope'],latest_only=True)
    assert [x['artifact']['artifact_id'] for x in result['items']]==[previous['artifact']['artifact_id']]
    assert result['items'][0]['document']==previous['document']
    assert result['verification_complete'] and not result['has_more']
    print('MEASURED_SYNTHETIC_READ_COST',json.dumps(counts))
    assert counts['files']<=18*8, counts
