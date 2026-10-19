"""Exact manuscript/source links through the original saved-work owner."""
import copy
import json
import pytest
from tests.test_saved_document_workflow import workspace, _source, _save

TEXT = '😀 e\u0301 한글 Same phrase. 👩\u200d💻 Same phrase.'

def citation(ws, relationship='supports'):
    _, _, source = _source(ws)
    c = ws['documents'].locate_quote(source['evidence_id'], actor=ws['actor'],
        scope=ws['scope'], start=0, end=20)['citation']
    start = TEXT.rindex('Same phrase.')
    c['claim_links'] = [dict(start=start, end=start+12, quote='Same phrase.',
        relationship=relationship, reason='Declared interpretation for review')]
    return c

def args(ws):
    return dict(actor=ws['actor'], scope=ws['scope'])

@pytest.mark.parametrize('relationship', ['supports','contradicts','qualifies','context_only'])
def test_unicode_duplicate_phrase_save_reopen_search_export(workspace, relationship):
    ws = workspace
    c = citation(ws, relationship)
    saved = _save(ws, markdown=TEXT, citations=[c])
    aid = saved['artifact']['artifact_id']
    reopened = ws['work'].reopen_work(aid, **args(ws))
    assert reopened['document']['citations'][0]['claim_links'] == c['claim_links']
    receipt = reopened['receipt']['sources'][0]
    assert receipt['claim_links'] == c['claim_links']
    assert receipt['claim_offset_unit'] == 'unicode_codepoint'
    assert receipt['claim_link_validation'] == 'SPAN_CHECKED_RELATIONSHIP_UNREVIEWED'
    found = ws['work'].search_work(query='Same phrase', **args(ws))
    assert found['items'][0]['artifact']['artifact_id'] == aid
    impact = ws['work'].search_work(evidence_id=c['evidence_id'], **args(ws))
    assert impact['items'][0]['source_matches']['citations'][0]['claim_links'] == c['claim_links']
    for fmt in ('json','md','txt'):
        exported = ws['work'].export_work(aid, format=fmt, **args(ws))['content'].decode()
        assert 'claim_links' in exported
        assert relationship in exported
        if fmt == 'json':
            assert json.loads(exported)['citations'][0]['claim_links'] == c['claim_links']

@pytest.mark.parametrize('change', [
    {'start': True}, {'end': False}, {'start': -1}, {'end': 10000},
    {'quote': 'different'}, {'relationship': 'proven'}, {'reason': ' '},
    {'reason': 'x'*1001}, {'extra': 1}, {'start': 32, 'end': 44},
])
def test_bad_links_fail_before_write(workspace, change):
    c = citation(workspace)
    c['claim_links'][0].update(change)
    with pytest.raises(ValueError, match='WORK_CLAIM_LINK'):
        _save(workspace, markdown=TEXT, citations=[c])
    assert workspace['work'].search_work(**args(workspace))['items'] == []

@pytest.mark.parametrize('links', [[], [None], 'not-a-list'])
def test_invalid_link_container(workspace, links):
    c = citation(workspace); c['claim_links'] = links
    with pytest.raises(ValueError, match='WORK_CLAIM_LINK'):
        _save(workspace, markdown=TEXT, citations=[c])

def test_duplicate_span_rejected(workspace):
    c = citation(workspace); c['claim_links'] *= 2
    with pytest.raises(ValueError, match='WORK_CLAIM_LINK'):
        _save(workspace, markdown=TEXT, citations=[c])

def test_revision_requires_explicit_valid_new_span(workspace):
    ws = workspace; c = citation(ws)
    saved = _save(ws, markdown=TEXT, citations=[c])
    params = dict(work_id=saved['document']['work_id'], previous_artifact_id=saved['artifact']['artifact_id'])
    edited = 'New prefix ' + TEXT
    with pytest.raises(ValueError, match='WORK_CLAIM_LINK_UNGROUNDED'):
        _save(ws, request_id='revision-invalid', markdown=edited, citations=[c], **params)
    updated = copy.deepcopy(c)
    for k in ('start', 'end'): updated['claim_links'][0][k] += len('New prefix ')
    revised = _save(ws, request_id='revision-valid', markdown=edited, citations=[updated], **params)
    assert revised['document']['version'] == 2
    assert ws['work'].reopen_work(saved['artifact']['artifact_id'], **args(ws))['document']['markdown'] == TEXT

def test_replay_cannot_change_interpretation(workspace):
    c = citation(workspace)
    _save(workspace, markdown=TEXT, citations=[c])
    c['claim_links'][0]['relationship'] = 'contradicts'
    with pytest.raises(ValueError):
        _save(workspace, markdown=TEXT, citations=[c])

def test_consumer_without_manuscript_cannot_validate_links(workspace):
    ws = workspace; c = citation(ws)
    with ws['repo'].connection(read_only=True, wal=False) as con:
        with pytest.raises(ValueError, match='WORK_CLAIM_LINKS_INVALID'):
            ws['work']._validate_citations(con, [c], ws['scope'], ws['actor'])

@pytest.mark.parametrize('operation', ['reopen','search','export'])
def test_revoked_reader_does_not_receive_linked_document(workspace, operation):
    ws=workspace; c=citation(ws)
    aid=_save(ws, markdown=TEXT, citations=[c])['artifact']['artifact_id']
    ws['app'].config['LUMENIS_OPEN_WORKSPACE']=False
    with pytest.raises(ValueError, match='WORK_PERMISSION_DENIED'):
        if operation=='reopen': ws['work'].reopen_work(aid, **args(ws))
        elif operation=='search': ws['work'].search_work(query='Same phrase', **args(ws))
        else: ws['work'].export_work(aid, format='md', **args(ws))

def test_export_rechecks_after_conversion(workspace, monkeypatch):
    ws=workspace; c=citation(ws)
    aid=_save(ws, markdown=TEXT, citations=[c])['artifact']['artifact_id']
    from lumenis.shared.reporting.word_pdf_export import ReportExporter
    def convert(*a, **kw):
        ws['app'].config['LUMENIS_OPEN_WORKSPACE']=False
        return b'converted confidential manuscript'
    monkeypatch.setattr(ReportExporter, 'export_saved_document', convert)
    with pytest.raises(ValueError, match='WORK_PERMISSION_DENIED'):
        ws['work'].export_work(aid, format='xlsx', **args(ws))

def test_legacy_citations_remain_compatible(workspace):
    c=citation(workspace); del c['claim_links']
    saved=_save(workspace, citations=[c])
    assert 'claim_links' not in saved['receipt']['sources'][0]


def test_local_revision_revalidates_retained_links_and_explicit_replacement(workspace):
    ws=workspace; c=citation(ws)
    saved=_save(ws, markdown=TEXT, citations=[c]); aid=saved['artifact']['artifact_id']
    link=c['claim_links'][0]
    params=dict(request_id='local-claim-edit', expected_sha256=saved['artifact']['sha256'],
        reason='Explicit interpretation correction', edits=[dict(pointer='/markdown',
        start=link['start'], end=link['end'], expected=link['quote'], replacement='Changed claim.')])
    with pytest.raises(ValueError, match='WORK_CLAIM_LINK_UNGROUNDED'):
        ws['work'].revise_work(aid, **args(ws), **params)
    updated=copy.deepcopy(c)
    updated['claim_links'][0].update(end=link['start']+len('Changed claim.'), quote='Changed claim.')
    revised=ws['work'].revise_work(aid, citations=[updated], **args(ws), **params)
    assert revised['document']['version']==2
    replay=ws['work'].revise_work(aid, citations=[updated], **args(ws), **params)
    assert replay['replayed'] and replay['artifact']['artifact_id']==revised['artifact']['artifact_id']
