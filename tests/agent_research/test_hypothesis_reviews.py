"""Pure review replay: synthetic inputs never establish authorization or facts."""
from copy import deepcopy
import pytest
from agent_research.source_bound import analyze_source_records
from agent_research.runner import ResearchRunner, run_research


def rows():
    return [{'source_id': name, 'evidence_id': 'scope:' + name,
             'scope_evidence_ref': 'scope:' + name, 'content_excerpt': text,
             'content_hash': char * 64, 'rights': 'UNKNOWN', 'title': name}
            for name, text, char in [('pilot', 'Registration increased in a small pilot.', 'a'),
                                     ('counter', 'Pilot had no comparable baseline.', 'b')]]


def review(disposition='challenge', **changes):
    initial = analyze_source_records('pilot registration', rows())
    hid = next(h['hypothesis_id'] for h in initial['hypotheses'] if h['evidence_refs'] == ['scope:pilot'])
    return dict(review_id='review-one', hypothesis_id=hid, disposition=disposition,
                rationale='Baseline is absent; the growth inference is disputed.',
                evidence_refs=['scope:counter'], **changes)


def test_challenge_reject_reinstate_is_ordered_human_history_not_fact():
    events = [review(), {**review('reject'), 'review_id': 'review-two'},
              {**review('reinstate'), 'review_id': 'review-three', 'rationale': 'Reconsider as an unverified question.'}]
    original = deepcopy(events)
    result = analyze_source_records('pilot registration', rows(), hypothesis_reviews=events)
    assert events == original
    assert result == analyze_source_records('pilot registration', rows(), hypothesis_reviews=events)
    assert [e['status'] for e in result['debate_transcript']] == ['challenged', 'rejected', 'reinstated']
    h = next(h for h in result['hypotheses'] if h['hypothesis_id'] == events[0]['hypothesis_id'])
    assert h['review_history'] == result['debate_transcript']
    assert h['support_eligible'] and h['confidence'] is None
    assert result['debate_transcript'][0]['resolved_source_bindings'][0]['source_id'] == 'counter'
    assert not result['permission_granted'] and not result['canonical_promotion']
    assert all(not f['fact_verified'] and not f['validated'] for f in result['ranked_findings'])


@pytest.mark.parametrize('disposition', ['challenge', 'reject'])
def test_disputed_hypothesis_and_finding_removed_from_effective_support(disposition):
    event = review(disposition)
    result = analyze_source_records('pilot registration', rows(), hypothesis_reviews=[event])
    assert len(result['ranked_findings']) == 2 and len(result['hypotheses']) == 2
    assert all(h['hypothesis_id'] != event['hypothesis_id'] for h in result['effective_hypotheses'])
    assert [f['source_id'] for f in result['effective_findings']] == ['counter']
    assert next(f for f in result['ranked_findings'] if f['source_id'] == 'pilot')['content'] == rows()[0]['content_excerpt']


@pytest.mark.parametrize('change', [
    {'evidence_refs': ['fabricated']}, {'evidence_refs': []}, {'evidence_refs': ['scope:counter'] * 2},
    {'hypothesis_id': 'missing'}, {'rationale': ''}, {'disposition': 'verified'},
    {'actor_id': 'client-admin'}, {'evidence_refs': 'scope:counter'},
])
def test_invalid_reviews_fail_closed(change):
    with pytest.raises(ValueError):
        analyze_source_records('pilot registration', rows(), hypothesis_reviews=[{**review(), **change}])


@pytest.mark.parametrize('change', [{'content_excerpt': 'Changed counterexample'},
    {'content_hash': 'c' * 64}, {'withdrawn': True}, {'revoked': True},
    {'scope': {'foreign': True}}, {'evidence_id': 'fake'}])
def test_source_changes_or_withdrawal_invalidate_previous_review(change):
    current = rows()
    current[1].update(change)
    with pytest.raises(ValueError, match='STALE_OR_UNKNOWN_HYPOTHESIS'):
        analyze_source_records('pilot registration', current, hypothesis_reviews=[review()])


def test_duplicate_and_unavailable_transitions_rejected():
    with pytest.raises(ValueError, match='DUPLICATE'):
        analyze_source_records('pilot registration', rows(), hypothesis_reviews=[review(), review()])
    with pytest.raises(ValueError, match='TRANSITION'):
        analyze_source_records('pilot registration', rows(), hypothesis_reviews=[review('reinstate')])


def test_all_sources_are_represented_and_input_order_does_not_change_hypothesis_ids():
    records = rows() + [{**rows()[0], 'source_id': str(i), 'evidence_id': str(i), 'scope_evidence_ref': str(i)} for i in range(5)]
    first = analyze_source_records('pilot registration', records)
    second = analyze_source_records('pilot registration', list(reversed(records)))
    assert first['hypotheses'] == second['hypotheses']
    assert len(first['hypotheses']) == 7
    assert first['debate_transcript'] == []


def test_runner_transmits_real_reviews_without_simulated_specialists():
    result = ResearchRunner().run_research('pilot registration', records=rows(), hypothesis_reviews=[review('reject')], max_rounds=99)
    assert len(result.debate_transcript) == 1 and len(result.effective_findings) == 1
    assert result == run_research('pilot registration', records=rows(), hypothesis_reviews=[review('reject')])


@pytest.mark.parametrize('context', [{'actor_id': 'other'}, {'scope': {'other': True}},
    {'dimension': 'global_market'}, {'languages': ['en']}, {'regions': ['global']}])
def test_review_cannot_be_reused_in_changed_research_context(context):
    with pytest.raises(ValueError):
        analyze_source_records('pilot registration', rows(), hypothesis_reviews=[review()], **context)
