"""New no-network research tests; synthetic fixtures never prove live outcomes."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from agent_research import analyze_source_records, run_research, ResearchRunner
from agent_research.reference_assets import query_reference_assets
from agent_research.taxonomy import get_research_taxonomy, normalize_dimension, is_valid_dimension


def source(**kwargs):
    record = {'source_id': 'source-one', 'evidence_id': 'scoped-evidence:one',
              'scope_evidence_ref': 'scoped-evidence:one', 'title': 'Pilot report',
              'content_excerpt': 'Pilot registration increased from 100 to 120 in April; attribution unknown.',
              'content_hash': 'a' * 64, 'rights': 'UNKNOWN', 'published_at': '2024-05-01',
              'source_url': 'https://example.com/pilot'}
    return {**record, **kwargs}


def test_empty_legacy_path_has_no_generated_evidence():
    result = run_research('Growth research')
    assert result.status == 'needs_sources'
    assert result.ranked_findings == result.evidence_lineage == []
    assert result.confidence is None
    assert result.metrics['evaluation_status'] == 'NO_DATA'


def test_bound_output_is_deterministic_literal_and_not_fact():
    record = source()
    before = copy.deepcopy(record)
    one = analyze_source_records('registration growth', [record])
    assert one == analyze_source_records('registration growth', [record])
    assert record == before
    finding = one['ranked_findings'][0]
    assert finding['content'] == record['content_excerpt']
    assert finding['evidence_refs'] == [record['evidence_id']]
    assert finding['claim_type'] == 'source_statement'
    assert finding['confidence'] is None and finding['validated'] is False
    assert one['metrics']['business_effect'] is None
    assert one['hypotheses'][0]['status'] == 'proposed'
    assert one['comparisons'][0]['numeric_literals'] == ['100', '120']
    assert one['comparisons'][0]['comparison_status'].startswith('NOT_COMPARABLE')
    assert one['evidence_lineage'][0]['provenance']['fact_verified'] is False


@pytest.mark.parametrize('change', [
    {'evidence_id': 'fake'}, {'scope_evidence_ref': ''}, {'content_excerpt': ''},
    {'withdrawn': True}, {'revoked': True}, {'actor_id': 'other'}, {'scope': {'foreign': True}},
])
def test_invalid_or_revoked_records_never_emit_findings(change):
    result = analyze_source_records('growth', [source(**change)], actor_id='owner', scope={})
    assert result['status'] == 'needs_sources'
    assert not result['evidence_lineage']
    assert result['rejected_records']


def test_reference_duplicate_and_conflict():
    assert analyze_source_records('growth', [source(), source()])['metrics']['usable_source_count'] == 1
    with pytest.raises(ValueError, match='CONFLICTING_SOURCE_REFERENCE'):
        analyze_source_records('growth', [source(), source(content_excerpt='Changed text')])


def test_excerpt_hash_is_checked_but_full_hash_not_misrepresented():
    record = source()
    record['excerpt_sha256'] = hashlib.sha256(record['content_excerpt'].encode()).hexdigest()
    assert analyze_source_records('growth', [record])['status'] == 'research_draft'
    with pytest.raises(ValueError, match='EXCERPT_HASH'):
        analyze_source_records('growth', [source(excerpt_sha256='bad')])


def test_rounds_never_inflate_findings_or_confidence():
    runner = ResearchRunner()
    assert runner.run_research('growth', records=[source()], max_rounds=1) == runner.run_research('growth', records=[source()], max_rounds=20)


def test_full_taxonomy_and_strict_unknowns():
    for lang in ('zh', 'en', 'ko'):
        taxonomy = get_research_taxonomy(lang)
        assert len(taxonomy['dimensions']) == 9 and len(taxonomy['regions']) == 7
        assert len(taxonomy['claim_labels']) == 5
        assert all(row['label'] == row[lang] for row in taxonomy['dimensions'])
    assert not is_valid_dimension(None)
    with pytest.raises(ValueError):
        normalize_dimension('wrong')
    with pytest.raises(ValueError):
        analyze_source_records('growth', [], regions=['EU'])
    with pytest.raises(ValueError):
        analyze_source_records('growth', [], languages=['bad'])


def test_all_assets_and_provenance_are_preserved():
    for kind, count in [('markets', 7), ('platforms', 12), ('rules', 14), ('scenarios', 3)]:
        result = query_reference_assets(kind, page_size=100)
        assert result['total'] == count
        for item in result['items']:
            assert item['rights'] == item['license'] == 'UNKNOWN'
            assert item['canonical'] is False
            assert item['review_status'] == 'PENDING_REVERIFICATION'
            assert len(item['provenance']['source_file_sha256']) == 64
            if kind == 'scenarios':
                assert item['classification'] == 'synthetic_sample'
                assert item['provenance']['original_date'] is None
                assert 'expected_outcome' in item['data']
            else:
                assert item['provenance']['original_date']
                assert item['provenance']['source_url'] == item['data']['evidence']['url']
    all_rows = query_reference_assets(page_size=100)['items']
    assert {r['code'] for r in all_rows if r['kind'] == 'markets'} == {'CN', 'US', 'EU', 'GB', 'JP', 'KR', 'SEA'}


def test_pagination_filter_and_copy_isolation():
    pages = [query_reference_assets(page=p, page_size=5) for p in range(1, 9)]
    ids = [r['asset_id'] for p in pages for r in p['items']]
    assert len(ids) == len(set(ids)) == 36
    assert not pages[-1]['has_more']
    europe = query_reference_assets('markets', region='europe')['items']
    assert {r['code'] for r in europe} == {'EU', 'GB'}
    china = query_reference_assets('markets', query='中国')['items']
    assert china
    china[0]['data']['name'] = 'mutated'
    assert query_reference_assets('markets', query='中国')['items'][0]['data']['name'] != 'mutated'
    with pytest.raises(ValueError):
        query_reference_assets(page=0)
    with pytest.raises(ValueError):
        query_reference_assets(region='unknown')


def test_shared_artifact_binding_is_not_external_truth():
    digest = 'b' * 64
    ref = f'saved_work:ART-shared:{digest}'
    record = source(source_artifact_ref='ART-shared', source_artifact_sha256=digest,
                    evidence_id=ref, scope_evidence_ref=ref, canonical_id=None)
    result = analyze_source_records('growth', [record], scope={'product_id': 'shared'})
    assert result['status'] == 'research_draft'
    assert not result['ranked_findings'][0]['fact_verified']
    assert result['evidence_lineage'][0]['provenance']['source_artifact_ref'] == 'ART-shared'
    bad = {**record, 'source_artifact_sha256': 'c' * 64}
    assert analyze_source_records('growth', [bad])['status'] == 'needs_sources'


def test_exact_original_asset_identities_and_global_discovery():
    assert query_reference_assets(region='global')['total'] == 36
    assert {row['code'] for row in query_reference_assets('platforms')['items']} == {
        'xiaohongshu', 'douyin', 'bilibili', 'wechat_channels', 'youtube', 'tiktok',
        'instagram', 'x', 'reddit', 'linkedin', 'github', 'zhihu'}
    assert {row['code'] for row in query_reference_assets('rules')['items']} == {
        'CN-AD-DISC-001', 'CN-PIPL-001', 'US-FTC-ENDORSE-001', 'EU-GDPR-ART6-001',
        'GB-GDPR-001', 'CN-ANTI-UNFAIR-001', 'CN-DEEP-SYNTH-001', 'EU-AI-ACT-001',
        'CN-LOTTERY-001', 'GLOBAL-COPYRIGHT-UGC-001', 'CN-MEDICAL-AD-001',
        'CN-FINANCIAL-MKT-001', 'GLOBAL-AFFILIATE-001', 'GLOBAL-MINOR-PROTECT-001'}
    assert {row['code'] for row in query_reference_assets('scenarios')['items']} == {
        'indie_game_sea', 'consumer_electronics_eu', 'saas_devtool_global'}


@pytest.mark.parametrize('kwargs', [{'records': None}, {'goal': None}, {'scope': []},
                                     {'regions': 'global'}, {'languages': 'zh'}])
def test_invalid_input_types_do_not_default_to_valid(kwargs):
    with pytest.raises(ValueError):
        analyze_source_records(**{'goal': 'growth', 'records': [], **kwargs})
