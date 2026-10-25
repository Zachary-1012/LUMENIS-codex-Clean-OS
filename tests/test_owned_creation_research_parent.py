"""Research-to-creation continuation preserves the original producing owners."""
import pytest

import content_generation as creation
from lumenis.shared.content_creation import internal_pitch as pitch
from tests import test_creation_upstream_flow as original
from tests.test_owned_creation_workflow import fake_gateway, revision, run

workspace = original.workspace
upstream = original.upstream


def test_owned_selected_revision_preserves_research_binding_and_return(upstream, monkeypatch):
    ws, research, ref = upstream
    monkeypatch.setattr(creation, 'get_repository', lambda:ws['repo'])
    first = original.run(ws, original.values(ws, ref, 'research-parent-owned-0001'))
    first['revision_sections'] = first['work']['revision_sections']
    calls = fake_gateway(ws, monkeypatch)
    result = run(ws, pitch.prepare_internal_pitch(**revision(ws, first)))
    assert result['work']['document']['contract'] == pitch.SOURCE_CONTRACT
    assert result['work']['document']['payload']['upstream_binding'] == first['work']['document']['payload']['upstream_binding']
    assert result['research_return_ref']['artifact_id'] == research['artifact']['artifact_id']
    assert result['work']['document']['payload']['manuscript']['sections'][0] == first['work']['document']['payload']['manuscript']['sections'][0]
    assert len(calls) == 1


def test_owned_source_revocation_in_commit_rolls_back_output_and_evidence(upstream, monkeypatch):
    ws, research, ref = upstream
    monkeypatch.setattr(creation, 'get_repository', lambda:ws['repo'])
    first = original.run(ws, original.values(ws, ref, 'research-parent-revoke-0001'))
    first['revision_sections'] = first['work']['revision_sections']
    fake_gateway(ws, monkeypatch)
    task = pitch.prepare_internal_pitch(**revision(ws, first))
    previous = ws['work'].save_work
    def revoke(*args, **kwargs):
        commit = kwargs['before_commit']
        def before_commit(con, artifact, document):
            con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE subject_id='SUBJ-PITCH'")
            commit(con, artifact, document)
        return previous(*args, **{**kwargs,'before_commit':before_commit})
    monkeypatch.setattr(ws['work'], 'save_work', revoke)
    counts = tuple(ws['repo'].query_one('SELECT COUNT(*) FROM '+table)[0] for table in ('lumenis_shared_artifacts','app_evidence_records'))
    with pytest.raises(ValueError, match='WORK_PERMISSION_DENIED'):
        run(ws, task)
    assert tuple(ws['repo'].query_one('SELECT COUNT(*) FROM '+table)[0] for table in ('lumenis_shared_artifacts','app_evidence_records')) == counts
    assert ws['repo'].query_one("SELECT status FROM lumenis_subject_registry WHERE subject_id='SUBJ-PITCH'")[0] == 'configured'
