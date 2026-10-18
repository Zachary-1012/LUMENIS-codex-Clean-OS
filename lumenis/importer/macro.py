"""G169 public macro observations inside the existing Importer owner.

Reads admitted Evidence, never creates a second truth or source store. Explicit
NBS release grammars are finite; unknown layouts stay missing. These national
background observations do not identify marketing causality or brand outcomes.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlsplit

from lumenis.shared.database import get_repository
from lumenis.shared.reporting import saved_work
from . import documents

SCHEMA = 'lumenis.macro-observations/v1'
MONTHS = {name: i for i, name in enumerate(calendar.month_name) if name}
_MONTH = '(?:' + '|'.join(MONTHS) + ')'
_NUMBER = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?'
METRICS = {'retail_sales': 'CNY', 'cpi_yoy_percent': 'percent_yoy',
    'domestic_tourism_trips':'person_trips','domestic_tourism_spend':'CNY',
    'monitored_district_footfall':'person_visits'}
REGION = 'CN-national'
LIMITATIONS = [
    'Public background within the reported national/municipal coverage; no allocation to a city, project or brand.',
    'Source assertions, not independently audited economic facts or causal marketing effects.',
    'CPI yearly-change arithmetic mean is a background covariate, not quarterly inflation or a price-level index.',
    'No interpolation, missing-as-zero, YTD-to-month subtraction or seasonal-adjustment revision synthesis.',
    'Finite official NBS/MCT/Beijing release grammars, not complete national or municipal coverage.',
    'Holiday totals are not quarters. Visits/trips are repeatable events, not unique people; monitored districts are not the entire city.',
    'Historical releases retain their actual year; they are not current market conditions.',
    'Declared official URL and matching text identify a claimed provider, not authenticated publisher acquisition; AVAILABLE describes statistical coverage only.',
    'No claim of complete public-data coverage, real twelve-quarter MMM, contribution or ROI.',
]


def _fail(code):
    raise ValueError(code)


def _provider(url):
    if not isinstance(url,str):
        _fail('MACRO_OFFICIAL_SOURCE_REQUIRED')
    parsed=urlsplit(url)
    if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443)
            or parsed.query or parsed.fragment):
        _fail('MACRO_OFFICIAL_SOURCE_REQUIRED')
    patterns={
        'www.stats.gov.cn':('NBS',r'/english/PressRelease/\d{6}/t\d{8}_\d+\.html'),
        'zwgk.mct.gov.cn':('MCT',r'/zfxxgkml/tjxx/\d{6}/t\d{8}_\d+\.html'),
        'www.mct.gov.cn':('MCT',r'/whzx/whyw/\d{6}/t\d{8}_\d+\.htm'),
        'sw.beijing.gov.cn':('BEIJING_COMMERCE',r'/(?:phone/)?zwxx/swxx/\d{6}/t\d{8}_\d+\.html'),
    }
    provider,pattern=patterns.get(parsed.hostname,(None,''))
    if provider is None or not re.fullmatch(pattern,parsed.path):
        _fail('MACRO_OFFICIAL_SOURCE_REQUIRED')
    return provider


def _official(url):
    _provider(url)
    return url


def _instant(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.utcoffset() is None:
            raise ValueError()
        return result
    except (ValueError, TypeError, AttributeError):
        _fail('MACRO_ASOF_OFFSET_REQUIRED')


def parse_nbs_release(text, *, source_url):
    """Extract only exact national headline/lead statements, keeping text offsets."""
    if _provider(source_url)!='NBS':
        _fail('MACRO_NBS_SOURCE_REQUIRED')
    if not isinstance(text, str) or not 0 < len(text.encode()) <= 2 * 1024 * 1024:
        _fail('MACRO_SOURCE_SIZE_INVALID')
    titles = list(re.finditer(r'(?:Total Retail Sales of Consumer Goods (?:in|from January to)|Consumer Price Index (?:for|in)) (' + _MONTH + r') (20\d{2})', text))
    signatures = {(m[1], m[2], 'retail' if m[0].startswith('Total') else 'cpi') for m in titles}
    if len(signatures) != 1:
        return {'facts': [], 'missing': [{'reason': 'RELEASE_TITLE_PERIOD_AMBIGUOUS'}]}
    month_name, year, kind = next(iter(signatures)); year = int(year); month = MONTHS[month_name]
    header = titles[0]
    publication = re.search(r'\b(20\d{2}-\d{2}-\d{2} \d{2}:\d{2})\b', text[header.end():header.end() + 300])
    published_literal = publication[1] if publication else None
    if published_literal:
        try:
            if datetime.fromisoformat(published_literal).date() < date(year, month, calendar.monthrange(year, month)[1]):
                _fail('MACRO_PUBLICATION_BEFORE_PERIOD_END')
        except ValueError:
            _fail('MACRO_PUBLICATION_DATE_INVALID')
    facts = []

    def add(match, metric, value, start_month, basis):
        if abs(value)>Decimal('1e24'):
            _fail('MACRO_NUMBER_INVALID')
        start, end = date(year, start_month, 1), date(year, month, calendar.monthrange(year, month)[1])
        fact = {'metric': metric, 'value': format(value, 'f'), 'unit': METRICS[metric],
            'region': REGION, 'region_basis': 'NBS national release scope',
            'period_start': start.isoformat(), 'period_end': end.isoformat(),
            'period_kind': 'month' if start_month == month else 'cumulative', 'definition': basis,
            'published_literal': published_literal, 'publication_timezone': 'UNKNOWN',
            'publisher': 'National Bureau of Statistics of China', 'status': 'DISCLOSED',
            'locator': {'start': match.start(), 'end': match.end(),
                        'quote_sha256': hashlib.sha256(match[0].encode()).hexdigest()},
            'header_locator': {'start': header.start(), 'end': header.end()},
            'revision_policy': 'retained capture vintage; upstream revision identity unknown'}
        fact['observation_id'] = 'MACRO-' + hashlib.sha256(json.dumps(fact, sort_keys=True).encode()).hexdigest()[:32]
        facts.append(fact)

    if kind == 'retail':
        for match in re.finditer(r'In ' + month_name + r', the total retail sales of consumer goods reached (' + _NUMBER + r') billion yuan', text):
            add(match, 'retail_sales', Decimal(match[1].replace(',', '')) * Decimal(10**9), month, 'national-total-nominal-retail-sales')
        for match in re.finditer(r'From January to ' + month_name + r', the total retail sales of consumer goods reached (' + _NUMBER + r') billion yuan', text):
            add(match, 'retail_sales', Decimal(match[1].replace(',', '')) * Decimal(10**9), 1, 'national-total-nominal-retail-sales')
    else:
        for match in re.finditer(r'In ' + month_name + ' ' + str(year) + r', the national consumer price index \(CPI\) (increased|decreased) by (' + _NUMBER + r') percent year on year', text):
            add(match, 'cpi_yoy_percent', Decimal(match[2].replace(',', '')) * (-1 if match[1] == 'decreased' else 1), month, 'national-all-items-cpi-year-on-year-change')
    # Duplicate contradictory lead sentences are unsafe, even if one appears later.
    keys = [(f['metric'], f['period_start'], f['period_end']) for f in facts]
    if len(keys) != len(set(keys)):
        return {'facts': [], 'missing': [{'reason': 'RELEASE_OBSERVATIONS_AMBIGUOUS'}]}
    return {'facts': facts, 'missing': [] if facts else [{'reason': 'SUPPORTED_NATIONAL_LEAD_NOT_FOUND'}]}


def align_quarters(facts, *, region, metric, periods, as_of):
    """Conservative, capture-as-of alignment; no user-provided numbers accepted."""
    cutoff = _instant(as_of)
    def capture_time(fact):
        try:
            return _instant(fact.get('captured_at'))
        except ValueError:
            return None
    if metric not in METRICS or not isinstance(region, str) or not region.strip():
        _fail('MACRO_SELECTION_INVALID')
    if (not isinstance(periods, list) or not 1 <= len(periods) <= 200
            or any(not isinstance(p, str) or not re.fullmatch(r'20\d{2}-Q[1-4]', p) for p in periods)
            or len(set(periods)) != len(periods)):
        _fail('MACRO_QUARTERS_INVALID')
    rows = []
    for period in periods:
        year, quarter = int(period[:4]), int(period[-1]); first = 3 * quarter - 2; last = first + 2
        start = date(year, first, 1).isoformat(); end = date(year, last, calendar.monthrange(year, last)[1]).isoformat()
        base = {'period': period, 'region': region, 'metric': metric, 'unit': METRICS[metric], 'value': None, 'state': 'MISSING', 'source_refs': []}
        candidates = [f for f in facts if f['region'] == region and f['metric'] == metric
                      and f['unit'] == METRICS[metric] and f['period_start'] is not None and f['period_end'] is not None
                      and f['period_start'] >= start and f['period_end'] <= end
                      and capture_time(f) is not None and capture_time(f) <= cutoff]
        selected = []
        # Every span chooses its latest captured vintage. Equal-time conflict stays missing.
        ambiguous = False
        for span in sorted({(f['period_start'], f['period_end']) for f in candidates}):
            versions = [f for f in candidates if (f['period_start'], f['period_end']) == span]
            latest = max(_instant(f['captured_at']) for f in versions)
            latest_rows = [f for f in versions if _instant(f['captured_at']) == latest]
            if len({(f['value'], f['definition']) for f in latest_rows}) != 1:
                ambiguous = True; break
            selected.append(sorted(latest_rows, key=lambda f: f['observation_id'])[0])
        full = [f for f in selected if f['period_start'] == start and f['period_end'] == end]
        monthly = [f for f in selected if f['period_kind'] == 'month']
        if ambiguous:
            base['reason'] = 'CONFLICTING_CAPTURE_VINTAGES'
        elif metric in {'retail_sales','domestic_tourism_trips','domestic_tourism_spend'} and full:
            chosen = full; value = Decimal(full[0]['value']); method = 'explicit-reported-quarter-total'
        elif metric in {'retail_sales','cpi_yoy_percent'} and len(monthly) == 3 and {int(f['period_start'][5:7]) for f in monthly} == {first, first + 1, last}:
            chosen = monthly; value = sum(Decimal(f['value']) for f in monthly)
            method = 'sum-complete-monthly-totals' if metric == 'retail_sales' else 'arithmetic-mean-monthly-yoy-percent'
            if metric == 'cpi_yoy_percent':
                value /= 3
        else:
            relevant=[f for f in facts if f['region']==region and f['metric']==metric]
            base['reason'] = ('HOLIDAY_TOTAL_NOT_QUARTER' if relevant and all(f['period_kind']=='holiday' for f in relevant)
                else 'REGION_UNAVAILABLE' if not any(f['region']==region for f in facts)
                else 'INCOMPLETE_QUARTER_OR_ASOF_VINTAGE')
        if 'reason' not in base:
            base.update(state='AVAILABLE', value=format(value, 'f'), aggregation=method,
                        source_refs=[f['source_ref'] for f in chosen], observation_ids=[f['observation_id'] for f in chosen])
        rows.append(base)
    return {'state': 'AVAILABLE' if all(r['state'] == 'AVAILABLE' for r in rows) else 'INSUFFICIENT',
            'as_of': as_of, 'vintage_basis': 'capture-time; not historical point-in-time release reconstruction',
            'region': region, 'metric': metric, 'unit': METRICS[metric], 'periods': rows}


def analyze_macro_sources(evidence_ids, *, actor, scope, selection=None):
    context = saved_work.authorize(actor, scope, action='read')
    if (not isinstance(evidence_ids, list) or not 1 <= len(evidence_ids) <= 60
            or any(type(e) is not int or e <= 0 for e in evidence_ids) or len(set(evidence_ids)) != len(evidence_ids)):
        _fail('MACRO_EVIDENCE_IDS_INVALID')
    result = {'schema': SCHEMA, 'facts': [], 'sources': [], 'missing': [], 'citations': [],
              'derived': True, 'canonical_fact_promotion': False, 'causal_claim': False,
              'limitations': LIMITATIONS, 'status': 'MISSING'}
    for evidence_id in evidence_ids:
        original = documents.reopen_imported_source(evidence_id, actor=actor, scope=scope)
        with get_repository().connection(read_only=True, wal=False) as con:
            evidence = saved_work._verified_evidence(con, evidence_id, context, actor)
        provenance = evidence['provenance']; declared = provenance.get('provenance', {})
        url = _official(provenance.get('source_url'))
        parsed = parse_macro_release(evidence['raw_content'], source_url=url)
        ref = {'evidence_id': evidence_id, 'source_id': original['source_id'], 'sha256': original['sha256'], 'artifact_ref': original['artifact_ref']}
        source = {**ref, 'source_url': url, 'captured_at': declared.get('captured_at'),
                  'published_at': declared.get('published_at'), 'rights': declared.get('rights'),
                  'rights_statement': declared.get('rights_statement'),
                  'content_origin': provenance.get('content_origin'), 'retained_input_bytes_verified': True,
                  'capture_mode': evidence.get('capture_mode', 'UNKNOWN'),
                  'ingestion_mode': provenance.get('capture_mode', 'UNKNOWN'),
                  'declared_provider': _provider(url),
                  'origin_verification': 'NOT_INDEPENDENTLY_VERIFIED',
                  'official_network_acquisition': 'UNKNOWN',
                  'acquisition_authenticity': 'NOT_INDEPENDENTLY_VERIFIED'}
        result['sources'].append(source)
        result['missing'].extend(dict(item, evidence_id=evidence_id) for item in parsed['missing'])
        spans = set()
        for fact in parsed['facts']:
            fact.update(source_ref=ref, captured_at=source['captured_at'],
                        content_origin=source['content_origin'], fact_verification='SOURCE_ASSERTION_NOT_INDEPENDENTLY_VERIFIED')
            result['facts'].append(fact)
            spans.add((fact['locator']['start'], fact['locator']['end']))
            spans.add((fact['header_locator']['start'], fact['header_locator']['end']))
        if not spans:
            spans.add((0, min(len(evidence['raw_content']), 100)))
        # One exact bounded span per source keeps up to sixty source references
        # inside original SavedWork's 100-citation limit, without dropping any.
        start,end=min(a for a,_ in spans),max(b for _,b in spans)
        result['citations'].append(documents.locate_quote(evidence_id, actor=actor, scope=scope, start=start, end=end)['citation'])
    if selection is not None:
        if not isinstance(selection, dict) or set(selection) != {'region', 'metric', 'periods', 'as_of'}:
            _fail('MACRO_SELECTION_INVALID')
        result['quarterly_control'] = align_quarters(result['facts'], **selection)
        result['quarterly_control'].update(
            availability_basis='PERIOD_REGION_UNIT_DEFINITION_COVERAGE_ONLY',
            origin_verification='NOT_INDEPENDENTLY_VERIFIED',
            official_network_acquisition='UNKNOWN')
    result['status'] = 'AVAILABLE' if result['facts'] else 'MISSING'
    return result


def save_macro_analysis(evidence_ids, *, actor, scope, request_id, selection=None, work_id=None, previous_artifact_id=None):
    result = analyze_macro_sources(evidence_ids, actor=actor, scope=scope, selection=selection)
    citations = result.pop('citations')
    lines = ['Public macro background', 'Context within explicit source geography and population; no brand attribution or causal ROI.',
             f"Source observations: {len(result['facts'])}"]
    for fact in result['facts']:
        period=(f"{fact['period_label']} ({fact['duration_days']} days; exact start/end not stated)" if fact.get('period_kind')=='holiday'
                else f"{fact['period_start']}..{fact['period_end']}")
        lines.append(f"{fact['region']} | {fact['metric']} | {period} | {fact['value']} {fact['unit']}")
        if fact.get('coverage'):
            lines.append('Reported coverage: '+json.dumps(fact['coverage'],ensure_ascii=False,sort_keys=True))
    if selection:
        control = result['quarterly_control']; lines.append('Quarterly control readiness: ' + control['state'])
        lines.extend(f"{row['period']}: {row['value'] if row['value'] is not None else '—'} {row['unit']} ({row.get('reason', row.get('aggregation'))})" for row in control['periods'])
    lines += ['Sources:']+[f"{source['source_url']} | declared provider: {source['declared_provider']} | capture mode: {source['capture_mode']} | origin: {source['origin_verification']} | official network acquisition: UNKNOWN" for source in result['sources']]
    lines += ['Limitations:'] + LIMITATIONS
    def recheck(*_):
        analyze_macro_sources(evidence_ids, actor=actor, scope=scope, selection=selection)
    return saved_work.save_work(title='Public macro background', markdown='\n'.join(lines), kind='research',
        payload={'macro': result}, citations=citations, request_id=request_id, actor=actor, scope=scope,
        work_id=work_id, previous_artifact_id=previous_artifact_id,
        contract={'id': SCHEMA, 'version': '1', 'required_payload_paths': ['macro.facts', 'macro.sources']},
        before_commit=recheck)


TARGET_SCHEMA = 'lumenis.macro-acquisition-plan/v1'
CAPTURE_SCHEMA = 'lumenis.macro-capture/v1'


def _macro_target(source_evidence_id, *, actor, scope):
    """Refresh an already-admitted exact official URL; never guess a new release."""
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    from subject_registry import list_subjects
    context=saved_work.authorize(actor,scope,action='read')
    if context['global_scope']:
        _fail('MACRO_EXACT_REGISTERED_TARGET_REQUIRED')
    analyzed=analyze_macro_sources([source_evidence_id],actor=actor,scope=scope)
    if not analyzed['facts']:
        _fail('MACRO_SUPPORTED_SOURCE_REQUIRED')
    source=analyzed['sources'][0]
    with get_repository().connection(read_only=True,wal=False) as con:
        registered=list_subjects(context['domain_id'],connection=con)
    domain='CTH' if context['domain_id']=='cth' else 'BMP'
    scope_key=context['subject_id'] or context['brand_focus_id']
    plan=build_acquisition_plan(context_mode='FOCUS',domain_id=domain,
        subject_id=context['subject_id'],brand_focus_id=context['brand_focus_id'],registry_loader=lambda:registered,
        business_requests=[{'domain_id':domain,'scope_key':scope_key,'purpose':'macro_background',
            'dimension':'market_activity','platforms':['public_http'],
            'tracking_sources':[{'url':source['source_url'],'scope_key':scope_key,'evidence_ref':f'app_evidence_records:{source_evidence_id}'}]}])
    if not plan.is_runnable or len(plan.queries)!=1 or plan.queries[0].keyword!=source['source_url']:
        _fail('MACRO_ACQUISITION_PLAN_UNAVAILABLE')
    return {'schema':TARGET_SCHEMA,'source_evidence_id':source_evidence_id,'source_sha256':source['sha256'],
        'url':source['source_url'],'format':'official-macro-release','max_bytes':2*1024*1024,
        'acquisition_plan':plan.to_dict(),'acquisition_owner':'SYSTEM Collector public_http',
        'publisher':analyzed['facts'][0]['publisher'],'data_region':analyzed['facts'][0]['region'],
        'source_periods':sorted({(f['period_start'],f['period_end'],f.get('period_label')) for f in analyzed['facts']}),
        'source_metrics':sorted({f['metric'] for f in analyzed['facts']}),
        'source_dimensions':_source_dimensions(analyzed['facts']),
        'scope_role':'BACKGROUND_CONTEXT_NOT_ENTITY_OUTCOME','plan_is_identity_fact':False}


def save_macro_target(source_evidence_id, *, actor, scope, request_id, work_id=None, previous_artifact_id=None):
    target=_macro_target(source_evidence_id,actor=actor,scope=scope)
    citation=documents.locate_quote(source_evidence_id,actor=actor,scope=scope,start=0,end=1)['citation']
    return saved_work.save_work(title='Macro public source refresh plan',markdown=target['url']+'\nSource-scoped background context; no entity outcome allocation or automatic scheduler.',
        kind='research',payload={'macro_target':target},citations=[citation],request_id=request_id,actor=actor,scope=scope,
        work_id=work_id,previous_artifact_id=previous_artifact_id,
        contract={'id':TARGET_SCHEMA,'version':'1','required_payload_paths':['macro_target']})


def _read_macro_target(target_artifact_id, *, actor, scope):
    work=saved_work.reopen_work(target_artifact_id,actor=actor,scope=scope)
    if work['document']['contract']['id']!=TARGET_SCHEMA:
        _fail('MACRO_TARGET_CONTRACT_INVALID')
    target=work['document']['payload'].get('macro_target')
    if not isinstance(target,dict):
        _fail('MACRO_TARGET_INVALID')
    verified=_macro_target(target.get('source_evidence_id'),actor=actor,scope=scope)
    if saved_work._json(verified)!=saved_work._json(target):
        _fail('MACRO_TARGET_CHANGED')
    return work,verified


def prepare_macro_collection(target_artifact_id, *, actor, scope):
    work,target=_read_macro_target(target_artifact_id,actor=actor,scope=scope)
    resource='macro-source-read:v1:'+saved_work._digest({'target_artifact_id':target_artifact_id,
        'target_sha256':work['artifact']['sha256'],'scope':scope,'url':target['url'],'max_bytes':target['max_bytes']})
    return {'state':'PREPARED','resource':resource,'url':target['url'],'scope':scope,'max_bytes':target['max_bytes'],
        'effect':'READ_PUBLIC_MACRO_SOURCE_AND_RETAIN_ORIGINAL','target_artifact_id':target_artifact_id}


def _macro_capture_spec():
    return {'error_prefix':'MACRO','capture_schema':CAPTURE_SCHEMA,'capture_key':'macro_capture',
        'run_key':'macro_collection_run','capture_request_prefix':'macro-capture-',
        'capture_title':'Macro source original capture','run_title':'Macro collection check',
        'filename':lambda _target:'release.html','media_type':lambda _target:'text/html',
        # Active HTML is always downloaded as inert bytes by the existing custody owner.
        'attachment_media_type':lambda _target:'application/octet-stream',
        'original_filing':lambda _target:False,
        'source_title':lambda target:target['publisher']+' public macro release',
        'unavailable_hint':'Retry the same approved official URL when safe network is available, or import an approved retained original; no unbounded crawl or fallback client.'}


def _validate_macro_response(raw,target):
    import tempfile
    from pathlib import Path
    from .parser import parse_file
    with tempfile.TemporaryDirectory(prefix='lumenis-macro-validate-') as temporary:
        path=Path(temporary)/'release.html';path.write_bytes(raw)
        parsed=parse_macro_release(parse_file(str(path)).text,source_url=target['url'])
    periods=sorted({(f['period_start'],f['period_end'],f.get('period_label')) for f in parsed['facts']})
    if (not parsed['facts'] or saved_work._json(periods)!=saved_work._json(target['source_periods'])
            or sorted({f['metric'] for f in parsed['facts']})!=target['source_metrics']
            or _source_dimensions(parsed['facts'])!=target['source_dimensions']):
        _fail('MACRO_RESPONSE_PERIOD_OR_METRIC_MISMATCH')


def _existing_macro_request(request_id, *, actor, scope):
    return documents._existing_source_request(request_id,actor=actor,scope=scope,error_prefix='MACRO')


def collect_macro_target(target_artifact_id, *, actor, scope, request_id):
    return documents._collect_admitted_document(target_artifact_id,actor=actor,scope=scope,request_id=request_id,
        spec=_macro_capture_spec(),prepare_collection=prepare_macro_collection,read_target=_read_macro_target,
        existing_request=_existing_macro_request,validate_response=_validate_macro_response,prepare_capture=prepare_macro_capture)


def _read_macro_capture(capture_artifact_id, *, actor, scope):
    return documents._read_admitted_document_capture(capture_artifact_id,actor=actor,scope=scope,
        spec=_macro_capture_spec(),read_target=_read_macro_target,validate_response=_validate_macro_response)


def prepare_macro_capture(capture_artifact_id, *, actor, scope):
    return documents._prepare_admitted_document_capture(capture_artifact_id,actor=actor,scope=scope,read_capture=_read_macro_capture)


def import_macro_capture(capture_artifact_id, *, actor, scope):
    material,source=documents._import_admitted_document_capture(capture_artifact_id,actor=actor,scope=scope,
        read_capture=_read_macro_capture,error_prefix='MACRO')
    analysis=analyze_macro_sources([source['evidence_id']],actor=actor,scope=scope)
    return {'state':'IMPORTED','source':source,'analysis':analysis,'capture_artifact_id':capture_artifact_id,'target_artifact_id':material['target_artifact_id']}



def _chinese_publication(text):
    match=re.search(r'发布时间[：:]\s*(20\d{2}(?:-\d{2}-\d{2}|年\d{2}月\d{2}日)(?: \d{2}:\d{2})?)',text)
    return match[1] if match else None


def _public_fact(text, match, header, *, metric, value, publisher, region, definition,
                 period_start=None, period_end=None, period_kind='holiday', period_label=None,
                 duration_days=None, coverage=None):
    if abs(value)>Decimal('1e24') or duration_days is not None and not 1<=duration_days<=31:
        _fail('MACRO_NUMBER_OR_DURATION_INVALID')
    published=_chinese_publication(text)
    if published:
        normalized=published.replace('年','-').replace('月','-').replace('日','')
        publication_date=datetime.fromisoformat(normalized).date()
        if (period_end and publication_date<date.fromisoformat(period_end)
                or period_label and publication_date.year<int(period_label[:4])):
            _fail('MACRO_PUBLICATION_BEFORE_PERIOD_END')
    if coverage and 'district_count' in coverage and coverage['district_count']<=0:
        _fail('MACRO_POPULATION_INVALID')
    fact={'metric':metric,'value':format(value,'f'),'unit':METRICS[metric],
        'region':region,'region_basis':'explicit publisher statistical coverage',
        'period_start':period_start,'period_end':period_end,'period_kind':period_kind,
        'period_label':period_label,'duration_days':duration_days,
        'period_date_status':'EXPLICIT_CALENDAR_QUARTER' if period_kind=='quarter' else 'EXACT_START_END_NOT_STATED',
        'definition':definition,'coverage':coverage or {},'publisher':publisher,'status':'DISCLOSED',
        'published_literal':_chinese_publication(text),'publication_timezone':'UNKNOWN',
        'locator':{'start':match.start(),'end':match.end(),'quote_sha256':hashlib.sha256(match[0].encode()).hexdigest()},
        'header_locator':{'start':header.start(),'end':header.end()},
        'revision_policy':'retained capture vintage; upstream revision identity unknown'}
    fact['observation_id']='MACRO-'+hashlib.sha256(json.dumps(fact,sort_keys=True).encode()).hexdigest()[:32]
    return fact


def parse_macro_release(text, *, source_url):
    provider=_provider(source_url)
    if provider=='NBS':return parse_nbs_release(text,source_url=source_url)
    if not isinstance(text,str) or not 0<len(text.encode())<=2*1024*1024:
        _fail('MACRO_SOURCE_SIZE_INVALID')
    facts=[]
    if provider=='MCT':
        publisher='Ministry of Culture and Tourism of China'
        headings=list(re.finditer(r'(20\d{2})年([一二三四])季度国内出游数据情况',text))
        if headings:
            if '根据国内出游抽样调查统计结果' not in text:
                return {'facts':[],'missing':[{'reason':'SURVEY_BASIS_UNAVAILABLE'}]}
            if len({m[0] for m in headings})!=1:
                return {'facts':[],'missing':[{'reason':'RELEASE_TITLE_PERIOD_AMBIGUOUS'}]}
            header=headings[0];year=int(header[1]);quarter='一二三四'.index(header[2])+1
            first=quarter*3-2;last=first+2
            start=date(year,first,1).isoformat();end=date(year,last,calendar.monthrange(year,last)[1]).isoformat()
            prefix=str(year)+'年'+header[2]+'季度，'
            for match in re.finditer(prefix+r'国内出游人次(\d+(?:\.\d+)?)亿',text):
                facts.append(_public_fact(text,match,header,metric='domestic_tourism_trips',value=Decimal(match[1])*10**8,
                    publisher=publisher,region=REGION,definition='domestic-tourism-sample-survey-person-trips-not-unique-persons',
                    period_start=start,period_end=end,period_kind='quarter',period_label=f'{year}-Q{quarter}',
                    coverage={'population':'national domestic tourism','method':'sample survey reported by publisher'}))
            for match in re.finditer(prefix+r'国内居民出游总花费(\d+(?:\.\d+)?)万亿元',text):
                facts.append(_public_fact(text,match,header,metric='domestic_tourism_spend',value=Decimal(match[1])*10**12,
                    publisher=publisher,region=REGION,definition='domestic-tourism-sample-survey-total-spend',
                    period_start=start,period_end=end,period_kind='quarter',period_label=f'{year}-Q{quarter}',
                    coverage={'population':'national domestic tourism','method':'sample survey reported by publisher'}))
        else:
            headings=list(re.finditer(r'(20\d{2})年春节假期文化和旅游市场情况',text))
            if len({m[0] for m in headings})==1:
                header=headings[0];year=int(header[1])
                pattern=r'经文化和旅游部数据中心测算，春节假期(\d{1,2})天，全国国内出游(\d+(?:\.\d+)?)亿人次[^。\n]{0,80}?国内出游总花费(\d+(?:\.\d+)?)亿元'
                for match in re.finditer(pattern,text):
                    for metric,value,definition in (
                        ('domestic_tourism_trips',Decimal(match[2])*10**8,'holiday-domestic-person-trips-not-unique-persons'),
                        ('domestic_tourism_spend',Decimal(match[3])*10**8,'holiday-domestic-tourism-total-spend')):
                        facts.append(_public_fact(text,match,header,metric=metric,value=value,publisher=publisher,region=REGION,
                            definition=definition,period_label=f'{year}-春节',duration_days=int(match[1]),
                            coverage={'population':'national domestic tourism during named holiday','method':'publisher data-center estimate'}))
    elif provider=='BEIJING_COMMERCE':
        header=re.search(r'清明假期本市消费市场活跃有序',text)
        periods=list(re.finditer(r'(20\d{2})年清明假期',text))
        duration=re.search(r'假期(三|3)天',text)
        if header and len({m[0] for m in periods})==1 and duration:
            for match in re.finditer(r'全市(\d{1,3})个重点商圈客流量(\d+(?:\.\d+)?)万人次',text):
                facts.append(_public_fact(text,match,header,metric='monitored_district_footfall',
                    value=Decimal(match[2])*10**4,publisher='Beijing Municipal Commerce Bureau',region='CN-Beijing',
                    definition='monitored-commercial-district-visitor-events-not-unique-people',
                    period_label=periods[0][1]+'-清明',duration_days=3,
                    coverage={'population':'monitored key commercial districts only','district_count':int(match[1]),
                              'scope_not_all_city':True,'method':'publisher aggregate; deduplication method not disclosed'}))
    keys=[(f['metric'],f['period_start'],f['period_end'],f['period_label']) for f in facts]
    if len(set(keys))!=len(keys):
        return {'facts':[],'missing':[{'reason':'RELEASE_OBSERVATIONS_AMBIGUOUS'}]}
    return {'facts':facts,'missing':[] if facts else [{'reason':'SUPPORTED_OFFICIAL_STATEMENT_NOT_FOUND'}]}



def _source_dimensions(facts):
    """Refresh revisions may change values, not silently change population/unit."""
    return sorted({saved_work._json({k:f.get(k) for k in
        ('metric','unit','region','definition','publisher','coverage','duration_days','period_kind')}).decode('utf-8') for f in facts})
