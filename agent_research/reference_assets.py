"""Read-only historical research catalog; no DB seeding or Canonical writes."""
from __future__ import annotations

import json
from pathlib import Path
from .taxonomy import is_valid_region

# Search expansion is a discovery aid, never a statement of legal jurisdiction.
_REGION_CODES = {'north_america': {'US', 'NA'}, 'europe': {'EU', 'GB', 'Europe'},
                 'asia_pacific': {'CN', 'JP', 'KR', 'SEA', 'APAC'}, 'china': {'CN'},
                 'global': {'Global', 'global'}, 'latin_america': {'LATAM'},
                 'middle_east_africa': {'MEA'}}


def query_reference_assets(kind=None, query='', region=None, page=1, page_size=20):
    """Return copied source records, filtered then paged in stable asset ID order.

    Unknown kind/region is an error, not silent global coverage. Country/market
    codes are supported alongside the seven regional taxonomy keys.
    """
    if kind is not None and kind not in ('markets', 'platforms', 'rules', 'scenarios'):
        raise ValueError('UNKNOWN_REFERENCE_KIND')
    if type(page) is not int or page < 1 or type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError('INVALID_REFERENCE_PAGINATION')
    if not isinstance(query, str):
        raise ValueError('INVALID_REFERENCE_QUERY')
    if region is not None and (not isinstance(region, str) or (not is_valid_region(region) and region not in {'CN', 'US', 'EU', 'GB', 'JP', 'KR', 'SEA'})):
        raise ValueError('UNKNOWN_REFERENCE_REGION')
    codes = _REGION_CODES.get(region, {region})
    records = json.loads(Path(__file__).with_name('reference_assets.json').read_text(encoding='utf-8'))
    rows = []
    for row in records:
        data = row['data']
        if kind and row['kind'] != kind:
            continue
        if query.casefold() not in json.dumps(data, ensure_ascii=False).casefold():
            continue
        if region and region != 'global':
            locations = {data.get('country'), data.get('country_code'), data.get('region')}
            locations.update(data.get('regional_availability', []))
            target = (data.get('inputs') or {}).get('target_market_name')
            locations.add({'东南亚': 'SEA', '欧盟': 'EU', '美国': 'US'}.get(target, target))
            # Global documents are surfaced for review, never deemed applicable.
            if not (locations & codes or data.get('jurisdiction') == 'Global'):
                continue
        rows.append(row)
    rows.sort(key=lambda row: row['asset_id'])
    start = (page - 1) * page_size
    return {'items': rows[start:start + page_size], 'total': len(rows), 'page': page,
            'page_size': page_size, 'has_more': start + page_size < len(rows),
            'status': 'historical_references', 'permission_granted': False,
            'coverage': 'Only the 36 pinned historical research references; absence is not legal clearance.'}


def match_rule_references(*, content, regions=None, industry=None, business=None,
                          platform=None, as_of=None):
    """Discover possibly relevant historical rules, never determine legality.

    A supplied date only compares the seed's declared start date. No expiry,
    amendment or current-law verification is implied. Missing selectors stay
    unknown rather than being treated as a global permission or clearance.
    """
    from datetime import date
    if not isinstance(content, str) or (regions is not None and not isinstance(regions, list)):
        raise ValueError('INVALID_RULE_MATCH_INPUT')
    for value in (industry, business, platform):
        if value is not None and not isinstance(value, str):
            raise ValueError('INVALID_RULE_MATCH_INPUT')
    selected_date = date.fromisoformat(as_of) if isinstance(as_of, str) else None
    if as_of is not None and selected_date is None:
        raise ValueError('INVALID_RULE_MATCH_DATE')
    region_codes = set()
    for region in regions or []:
        if not isinstance(region, str) or (not is_valid_region(region) and region not in {'CN', 'US', 'EU', 'GB', 'JP', 'KR', 'SEA'}):
            raise ValueError('UNKNOWN_REFERENCE_REGION')
        region_codes.update(_REGION_CODES.get(region, {region}))
    hits = []
    for row in query_reference_assets('rules', page_size=100)['items']:
        data = row['data']
        keywords = [word for word in data.get('trigger_condition', '').split() if word]
        matched = [word for word in keywords if word.casefold() in content.casefold()]
        if not matched:
            continue
        global_rule = data.get('jurisdiction', '').casefold() == 'global'
        region_match = bool(global_rule or {data.get('country'), data.get('region')} & region_codes)
        if regions and 'global' not in regions and not region_match:
            continue
        if industry and data.get('industry') and data['industry'].casefold() not in (industry.casefold(), 'all', 'general'):
            continue
        if platform and data.get('platform') and data['platform'].casefold() != platform.casefold():
            continue
        declared_date = data.get('effective_date')
        date_state = 'UNKNOWN'
        if selected_date and declared_date:
            date_state = 'ON_OR_AFTER_DECLARED_START_UNVERIFIED' if selected_date >= date.fromisoformat(declared_date) else 'BEFORE_DECLARED_START'
        hits.append({'reference': row, 'matched_terms': matched,
                     'match_status': 'POSSIBLY_RELEVANT_REFERENCE',
                     'region_status': 'UNKNOWN' if not regions else 'DISCOVERY_SCOPE_ONLY',
                     'industry_status': 'UNKNOWN' if not industry else 'SELECTOR_MATCH',
                     'platform_status': 'UNKNOWN' if not platform else 'SELECTOR_MATCH',
                     'business_context': business, 'business_match_status': 'CONTEXT_ONLY_NO_RULE_FIELD',
                     'as_of': as_of, 'date_status': date_state,
                     'current_legal_validity': 'UNKNOWN', 'required_action': None})
    return {'items': hits, 'total': len(hits), 'status': 'reference_review_needed',
            'as_of': as_of, 'permission_granted': False, 'legal_clearance': None,
            'limitations': ['Keyword and selector discovery only; verify original law, amendments, exceptions and jurisdiction.',
                            'No matches do not establish compliance; declared start dates do not establish current validity.']}
