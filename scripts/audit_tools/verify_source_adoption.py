"""Validate the local source provenance attachment, not a second runtime contract."""
from __future__ import annotations
import json
from pathlib import Path

RECORD = '00-GOVERNANCE/LUMENIS-SOURCE-ADOPTION-V1.json'
FINGERPRINT = '68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f'
SOURCE_COMMIT = 'e6cde984480cff3176eb39b038c7c0a66e1e2124'


def validate_local_adoption(root: Path) -> None:
    root = root.resolve()
    data = json.loads((root / RECORD).read_text(encoding='utf-8'))
    assert data['schema'] == 'lumenis.source-adoption-record/v1'
    assert data['record_version'] == '1.0.0'
    assert data['scope'] == 'LOCAL_SOURCE_ADOPTION_ONLY'
    assert data['authority'] == 'LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md'
    assert data['plan'] == 'LOOP-PLAN-20261014/product-plan-full.md'
    assert data['source_repository'] == 'Zachary-1012/global-growth-intelligence'
    assert data['source_commit'] == SOURCE_COMMIT
    assert data['status'] in {'IN_PROGRESS_OWNER_VALIDATION_REQUIRED', 'VERIFIED_BOUNDED_SOURCE_ADOPTION'}
    exchange = data['exchange_contract']
    assert exchange['version'] == '1.1.0' and exchange['fingerprint'] == FINGERPRINT
    for field in ('modified', 'external_repositories_modified', 'local_attachment_is_exchange_version'):
        assert exchange[field] is False, field
    contract = json.loads((root / '00-GOVERNANCE' / exchange['path']).read_text(encoding='utf-8'))
    assert contract['contract_version'] == exchange['version']
    assert contract['protocol_fingerprint_sha256'] == exchange['fingerprint']
    expected_boundaries = {'new_product_domain', 'parallel_runtime_account_database', 'cross_database_copy',
                           'unrestricted_writer', 'automatic_truth_promotion', 'external_delivery_authorized'}
    assert set(data['boundaries']) == expected_boundaries
    assert all(value is False for value in data['boundaries'].values())
    assert data['inventory'] == {'files': 72, 'route_intentions': 51, 'capabilities': 33, 'dimensions': 9,
                                'reference_records': {'market': 7, 'platform': 12, 'policy': 14, 'scenario': 3}}
    assert data['rights']['original_source_license_file'] == 'ABSENT'
    assert data['rights']['third_party_reuse'] == 'UNKNOWN'
    assert data['rights']['seed_fact_status'] == 'HISTORICAL_REFERENCE_REVERIFY'
    maps = {}
    for key, relative in data['maps'].items():
        path = (root / relative).resolve()
        assert path.is_relative_to(root / '00-GOVERNANCE/evidence/round-15/source-adoption-20261018'), key
        maps[key] = json.loads(path.read_text(encoding='utf-8'))
    assert set(maps) == {'files', 'endpoints', 'capabilities', 'rights', 'seed_records'}
    assert len(maps['files']) == 72 and len({r['path'] for r in maps['files']}) == 72
    for row in maps['files']:
        assert row['verified'] is True
        assert row['git_blob_sha1'] == row['expected_blob_sha1']
        assert len(row['sha256']) == 64 and row['adoption_target'] and row['proposed_owner']
    assert len(maps['endpoints']) == 51
    assert len({(r['method'], r['source_path']) for r in maps['endpoints']}) == 51
    assert all(r['owner'] and r['target'] and r['acceptance'] and r.get('target_callable')
               and r.get('target_http_contract') and r.get('semantic_adaptation') for r in maps['endpoints'])
    expected_ids = {f'{prefix}{i:02}' for prefix, count in [('R', 9), ('E', 8), ('B', 8), ('I', 8)] for i in range(1, count + 1)}
    assert {r['id'] for r in maps['capabilities']} == expected_ids
    assert len(maps['capabilities']) == 33
    assert all(r['existing_owner'] and r['positive_acceptance'] and r['negative_acceptance']
               and r.get('current_target_callable') and r.get('remaining') for r in maps['capabilities'])
    assert len(maps['seed_records']) == 36
    for kind, count in data['inventory']['reference_records'].items():
        assert sum(r['source_kind'] == kind for r in maps['seed_records']) == count
    for row in maps['seed_records']:
        assert row['rights'] == 'UNKNOWN' and row['freshness'] == 'NOT_REVERIFIED'
        assert row['source_claim_is_current_fact'] is False
        assert row['scenario_is_observed_outcome'] is False
        assert row['source_commit'] == SOURCE_COMMIT
    assert len(maps['rights']) == 4
    assert all(r['reuse_license'] == 'NOT_DECLARED_IN_SOURCE' and isinstance(r['source_urls'], list) for r in maps['rights'])
    for relative in ('AGENTS.md', 'README.md', '00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md',
                     '00-GOVERNANCE/CANONICAL_REGISTRY.md', '00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md',
                     '00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md', '00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md'):
        assert 'LUMENIS-SOURCE-ADOPTION-V1.json' in (root / relative).read_text(encoding='utf-8'), relative
    assert len((root / 'AGENTS.md').read_bytes()) + 16384 <= 131072


if __name__ == '__main__':
    validate_local_adoption(Path(__file__).resolve().parents[2])
    print('LOCAL SOURCE ADOPTION provenance/mapping/boundary OK; not product acceptance')
