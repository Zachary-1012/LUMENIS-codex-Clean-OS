"""G166–168 financial adapters over existing Importer/Evidence/SavedWork owners.

No independent network client, credentials store, sidecar database or truth promotion. Readers
consume retained source bytes; revisions stay immutable in existing SavedWork.
A filing entity is not its brand, subsidiary or property. Missing stays missing.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from lumenis.shared.database import get_repository
from lumenis.shared.reporting import saved_work
from . import documents

SCHEMA = 'lumenis.financial-observations/v1'
CONCEPTS = {
    'AdvertisingExpense': 'advertising_expense',
    'AdvertisingAndMarketingExpense': 'marketing_expense',
    'MarketingAndAdvertisingExpense': 'marketing_expense',
    'SellingAndMarketingExpense': 'selling_marketing_expense',
    'SellingGeneralAndAdministrativeExpense': 'selling_general_admin_expense',
    'RevenueFromContractWithCustomerExcludingAssessedTax': 'revenue',
    'RevenueFromContractWithCustomerIncludingAssessedTax': 'revenue_including_tax',
    'Revenues': 'revenue', 'Revenue': 'revenue', 'SalesRevenueNet': 'net_sales',
    'OperatingLeaseLeaseIncome': 'rental_income', 'RentalIncome': 'rental_income',
}
MANUAL_METRICS = set(CONCEPTS.values()) | {'retail_sales', 'tenant_sales_growth',
    'rental_income_growth', 'occupancy', 'footfall', 'footfall_description', 'segment_revenue'}
CAPABILITIES = {
    'SEC': {'formats': ['sec-companyfacts', 'sec-companyconcept', 'xbrl-instance', 'disclosure-extract'],
            'key_required': False, 'acquisition_owner': 'SYSTEM Collector',
            'live_status': 'NOT_VERIFIED', 'note': 'Companyfacts is whole-filing-entity standard-taxonomy data; frames are not aligned fiscal quarters.'},
    'HKEX': {'formats': ['disclosure-extract', 'regional-statement'], 'key_required': False,
             'live_status': 'NOT_VERIFIED', 'note': 'Deterministic explicit consolidated statement headers/labels with page/text locators; unknown layouts remain review candidates.'},
    'SSE': {'formats': ['disclosure-extract', 'regional-statement'], 'key_required': False, 'live_status': 'NOT_VERIFIED'},
    'SZSE': {'formats': ['disclosure-extract', 'regional-statement'], 'key_required': False, 'live_status': 'NOT_VERIFIED'},
    'OpenDART': {'formats': ['disclosure-extract', 'opendart-json'], 'key_required': True,
                'live_status': 'MISSING_CREDENTIAL', 'note': 'Retained major-account JSON parsing supported; secret-free request descriptor available. No key supplied; no live API acquisition claim.'},
}


def _fail(code):
    raise ValueError(code)


def _text(value, code='FINANCIAL_TEXT_INVALID'):
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        _fail(code)
    return value.strip()


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        _fail('FINANCIAL_DATE_INVALID')
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail('FINANCIAL_DATE_INVALID')


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        _fail('FINANCIAL_NUMBER_INVALID')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        _fail('FINANCIAL_NUMBER_INVALID')
    if (not number.is_finite() or not -18 <= number.as_tuple().exponent <= 30
            or len(number.as_tuple().digits) > 128 or abs(number) > Decimal('1e30')):
        _fail('FINANCIAL_NUMBER_INVALID')
    return format(number, 'f')


def _period(start, end):
    finish = _date(end)
    if start is None:
        return 'instant'
    begin = _date(start)
    days = (finish - begin).days + 1
    if days < 1:
        _fail('FINANCIAL_PERIOD_INVALID')
    return ('quarter' if 80 <= days <= 100 else 'half_year' if 170 <= days <= 195
            else 'nine_months' if 260 <= days <= 285 else 'year' if 350 <= days <= 380 else 'duration')


def _fact(*, metric, concept, value, unit, start, end, entity, filing_id,
          filed, form, locator, disclosure_scope='filing_entity', dimensions=None,
          statement_basis='taxonomy-disclosed', source_scale=1):
    unit = _text(unit)
    if form is not None:
        form = _text(form)
    if filed is not None:
        if _date(filed) < _date(end):
            _fail('FINANCIAL_FILING_BEFORE_PERIOD_END')
    result = dict(metric=metric, concept=concept, value=None if value is None else _number(value),
        unit=unit, currency=unit if re.fullmatch('[A-Z]{3}', unit) else None,
        period_start=start, period_end=end, period_kind=_period(start, end),
        filing_entity=entity, filing_id=_text(filing_id), filed=filed, form=form,
        disclosure_scope=disclosure_scope, dimensions=dimensions or {},
        statement_basis=statement_basis, source_scale=source_scale, locator=locator,
        status='MISSING' if value is None else 'DISCLOSED',
        fact_verification='SOURCE_ASSERTION_NOT_INDEPENDENTLY_VERIFIED')
    result['observation_id'] = 'FIN-' + hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:32]
    return result


def parse_sec_json(raw: bytes) -> dict:
    """Decode companyfacts or companyconcept without deduplicating amendments.

    All units, accession IDs and period starts are retained. SG&A is deliberately
    a different metric; six/nine-month cumulative periods never become quarters.
    """
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 8 * 1024 * 1024:
        _fail('FINANCIAL_SOURCE_SIZE_INVALID')
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                _fail('FINANCIAL_DUPLICATE_JSON_KEY')
            result[k] = v
        return result
    try:
        data = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
                          parse_float=Decimal, parse_constant=lambda _: _fail('FINANCIAL_NUMBER_INVALID'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('FINANCIAL_JSON_INVALID') from exc
    if not isinstance(data, dict) or not re.fullmatch(r'\d{1,10}', str(data.get('cik', ''))):
        _fail('FINANCIAL_SEC_IDENTITY_REQUIRED')
    entity = {'name': _text(data.get('entityName')), 'scheme': 'SEC-CIK', 'identifier': str(data['cik']).zfill(10)}
    concepts = data.get('facts')
    companyconcept = concepts is None
    if companyconcept:
        concepts = {data.get('taxonomy'): {data.get('tag'): data}}
    if not isinstance(concepts, dict):
        _fail('FINANCIAL_SEC_FACTS_INVALID')
    facts, missing = [], []
    for taxonomy, tags in concepts.items():
        if taxonomy not in {'us-gaap', 'ifrs-full'}:
            continue
        if not isinstance(tags, dict):
            _fail('FINANCIAL_SEC_FACTS_INVALID')
        for tag, series in tags.items():
            if tag not in CONCEPTS:
                continue
            if not isinstance(series, dict) or not isinstance(series.get('units'), dict):
                _fail('FINANCIAL_SEC_UNITS_INVALID')
            for unit, entries in series['units'].items():
                if not isinstance(entries, list):
                    _fail('FINANCIAL_SEC_FACTS_INVALID')
                for index, entry in enumerate(entries):
                    if not isinstance(entry, dict) or not {'val','end','accn','filed','form'}.issubset(entry):
                        _fail('FINANCIAL_SEC_FACT_INVALID')
                    if not re.fullmatch(r'\d{10}-\d{2}-\d{6}', str(entry['accn'])):
                        _fail('FINANCIAL_SEC_ACCESSION_INVALID')
                    pointer = ('' if companyconcept else f'/facts/{taxonomy}/{tag}') + f'/units/{unit}/{index}'
                    facts.append(_fact(metric=CONCEPTS[tag], concept=f'{taxonomy}:{tag}', value=entry['val'], unit=unit,
                        start=entry.get('start'), end=entry['end'], entity=entity, filing_id=entry['accn'],
                        filed=entry['filed'], form=entry['form'], locator={'unit':'json-pointer','pointer':pointer},
                        statement_basis='standard-taxonomy; statement-vs-note not provided by SEC API'))
                    facts[-1].update(fiscal_year=entry.get('fy'), fiscal_period=entry.get('fp'),
                                     sec_frame=entry.get('frame'), calendar_alignment_inferred=False)
                    if len(facts) > 10000:
                        _fail('FINANCIAL_TOO_MANY_FACTS')
    present = {f['metric'] for f in facts}
    for metric in ('marketing_expense','advertising_expense','selling_marketing_expense','revenue','retail_sales','occupancy','footfall'):
        if metric not in present:
            missing.append({'metric':metric,'status':'MISSING','reason':'NOT_DISCLOSED_IN_SELECTED_SUPPORTED_CONCEPTS'})
    return {'schema': SCHEMA, 'format':'sec-companyconcept' if companyconcept else 'sec-companyfacts',
            'filing_entity':entity, 'facts':facts, 'missing':missing, 'warnings':[
                'Company facts describe the entire filing entity; no automatic brand/project allocation.',
                'All filing versions retained; select an explicit as-of policy before time-series analysis.',
                'Absence from standard concepts does not prove absence from the complete filing.']}


def parse_xbrl_instance(raw: bytes, *, filing_id, filed=None, form=None) -> dict:
    """Small bounded XBRL-instance reader, not an inline-XBRL/taxonomy validator."""
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 8 * 1024 * 1024:
        _fail('FINANCIAL_SOURCE_SIZE_INVALID')
    if b'\x00' in raw or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        _fail('FINANCIAL_XML_EXTERNAL_ENTITY_FORBIDDEN')
    try:
        namespace_stack, pending, namespaces = [], [], {}
        root = None
        count = 0
        for event, node in ET.iterparse(io.BytesIO(raw), events=('start-ns','start','end')):
            if event == 'start-ns':
                pending.append(node)
            elif event == 'start':
                count += 1
                if count > 100000 or len(namespace_stack) > 128:
                    _fail('FINANCIAL_XML_COMPLEXITY_LIMIT')
                current = dict(namespace_stack[-1]) if namespace_stack else {}
                current.update(pending)
                pending.clear()
                namespace_stack.append(current)
                namespaces[id(node)] = current
                if root is None:
                    root = node
            else:
                namespace_stack.pop()
    except ET.ParseError as exc:
        raise ValueError('FINANCIAL_XML_INVALID') from exc
    ns = {'x':'http://www.xbrl.org/2003/instance', 'd':'http://xbrl.org/2006/xbrldi'}
    if root.tag != '{http://www.xbrl.org/2003/instance}xbrl':
        _fail('FINANCIAL_XBRL_INSTANCE_REQUIRED')
    def qname(value, element):
        value = _text(value, 'FINANCIAL_XBRL_QNAME_INVALID')
        if not re.fullmatch(r'(?:[A-Za-z_][\w.-]*:)?[A-Za-z_][\w.-]*', value):
            _fail('FINANCIAL_XBRL_QNAME_INVALID')
        prefix, local = value.split(':',1) if ':' in value else ('',value)
        uri = namespaces[id(element)].get(prefix)
        if not uri:
            _fail('FINANCIAL_XBRL_QNAME_UNBOUND')
        return '{'+uri+'}'+local

    def measure(element):
        expanded = qname(element.text, element)
        uri, local = expanded[1:].split('}',1)
        if uri == 'http://www.xbrl.org/2003/iso4217' and re.fullmatch('[A-Z]{3}',local):
            return local, expanded
        if uri == ns['x'] and local in {'pure','shares'}:
            return local, expanded
        return expanded, expanded  # Unknown units remain explicit, never a currency.

    contexts, units, facts = {}, {}, []
    for item in root.findall('x:context', ns):
        identifier = item.find('x:entity/x:identifier', ns)
        if identifier is None or not identifier.text:
            _fail('FINANCIAL_XBRL_IDENTITY_REQUIRED')
        _text(identifier.get('scheme'), 'FINANCIAL_XBRL_IDENTITY_REQUIRED')
        key = item.get('id')
        if not key or key in contexts:
            _fail('FINANCIAL_XBRL_CONTEXT_INVALID')
        dimensions = {}
        for member in item.findall('.//d:explicitMember', ns) + item.findall('.//d:typedMember', ns):
            dimension = qname(member.get('dimension'),member)
            if dimension in dimensions:
                _fail('FINANCIAL_XBRL_DIMENSION_DUPLICATE')
            dimensions[dimension] = (qname(member.text,member) if member.tag.endswith('explicitMember')
                else ET.tostring(member,encoding='unicode'))
        contexts[key] = {'entity': {'name':None,'scheme':identifier.get('scheme'),'identifier':identifier.text.strip()},
            'start':item.findtext('x:period/x:startDate', namespaces=ns),
            'end':item.findtext('x:period/x:endDate', namespaces=ns) or item.findtext('x:period/x:instant', namespaces=ns),
            'dimensions':dimensions}
    for item in root.findall('x:unit', ns):
        measures = item.findall('x:measure', ns)
        if not item.get('id') or item.get('id') in units:
            _fail('FINANCIAL_XBRL_UNIT_INVALID')
        divide = item.find('x:divide',ns)
        if measures and divide is None:
            resolved = [measure(m) for m in measures]
            units[item.get('id')] = {'label':'*'.join(v[0] for v in resolved),
                'numerator':[v[1] for v in resolved],'denominator':[]}
        elif divide is not None and not measures:
            numerator = divide.findall('x:unitNumerator/x:measure',ns)
            denominator = divide.findall('x:unitDenominator/x:measure',ns)
            if not numerator or not denominator:
                _fail('FINANCIAL_XBRL_UNIT_INVALID')
            top, bottom = [measure(m) for m in numerator], [measure(m) for m in denominator]
            units[item.get('id')] = {'label':'*'.join(v[0] for v in top)+'/'+'*'.join(v[0] for v in bottom),
                'numerator':[v[1] for v in top],'denominator':[v[1] for v in bottom]}
        else:
            _fail('FINANCIAL_XBRL_UNIT_INVALID')
    for index, item in enumerate(root):
        tag = item.tag.split('}')[-1]
        namespace = item.tag.split('}')[0].lstrip('{')
        if tag not in CONCEPTS or not (re.fullmatch(r'http://fasb\.org/us-gaap/20\d{2}', namespace) or re.fullmatch(r'https?://xbrl\.ifrs\.org/taxonomy/20\d{2}-\d{2}-\d{2}/ifrs-full', namespace)):
            continue
        context = contexts.get(item.get('contextRef'))
        unit = units.get(item.get('unitRef'))
        if context is None or not unit:
            _fail('FINANCIAL_XBRL_CONTEXT_OR_UNIT_MISSING')
        nil = item.get('{http://www.w3.org/2001/XMLSchema-instance}nil') in {'true','1'}
        if not nil and item.text is None:
            _fail('FINANCIAL_NUMBER_INVALID')
        facts.append(_fact(metric=CONCEPTS[tag], concept=item.tag, value=None if nil else item.text,
            unit=unit['label'], start=context['start'], end=context['end'], entity=context['entity'],
            filing_id=filing_id, filed=filed, form=form,
            disclosure_scope='dimensioned' if context['dimensions'] else 'filing_entity', dimensions=context['dimensions'],
            locator={'unit':'xml-element-index','index':index,'context_ref':item.get('contextRef'),'id':item.get('id')}))
        facts[-1]['unit_definition'] = unit
        if unit['denominator'] or len(unit['numerator']) != 1 or not unit['numerator'][0].startswith('{http://www.xbrl.org/2003/iso4217}'):
            facts[-1]['currency'] = None
    return {'schema':SCHEMA,'format':'xbrl-instance','filing_entity':None,'facts':facts,
            'missing':[] if facts else [{'status':'MISSING','reason':'NO_SUPPORTED_STANDARD_FACTS'}],
            'warnings':['XBRL instance adapter; not inline XBRL, taxonomy validation or automatic dimension-to-project mapping.']}


def parse_disclosures(text: str, annotations: list) -> dict:
    """Validate caller-reviewed fact interpretations against retained text spans.

    This is explicit source annotation, never AI factual extraction. Dates,
    currency and scope remain reviewable interpretations with exact quotations.
    """
    if not isinstance(annotations, list) or not 1 <= len(annotations) <= 100:
        _fail('FINANCIAL_ANNOTATIONS_REQUIRED')
    facts = []
    required = {'metric','value','value_literal','scale','unit','period_start','period_end',
                'filing_entity','filing_id','filed','form','disclosure_scope','statement_basis','start','end'}
    for row in annotations:
        if not isinstance(row, dict) or not required.issubset(row) or set(row)-required-{'page'}:
            _fail('FINANCIAL_ANNOTATION_INVALID')
        if row['metric'] not in MANUAL_METRICS or row['disclosure_scope'] not in {'filing_entity','project','segment','brand'}:
            _fail('FINANCIAL_DISCLOSURE_SCOPE_INVALID')
        start, end = row['start'], row['end']
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or end-start > 4000:
            _fail('FINANCIAL_LOCATOR_INVALID')
        quote = text[start:end]
        if row.get('page') is not None and (type(row['page']) is not int or row['page'] < 1):
            _fail('FINANCIAL_PAGE_INVALID')
        entity = row['filing_entity']
        if not isinstance(entity, dict) or set(entity) != {'name','scheme','identifier'}:
            _fail('FINANCIAL_FILING_ENTITY_INVALID')
        _text(entity['name']); _text(entity['scheme']); _text(entity['identifier'])
        literal = _text(row['value_literal'])
        if literal not in quote:
            _fail('FINANCIAL_VALUE_NOT_IN_SOURCE')
        scale = Decimal(_number(row['scale']))
        if scale not in {Decimal('1'),Decimal('1000'),Decimal('1000000'),Decimal('1000000000')}:
            _fail('FINANCIAL_SCALE_INVALID')
        if row['metric'] == 'footfall_description':
            if row['value'] != literal or scale != 1 or row['unit'] != 'text':
                _fail('FINANCIAL_NARRATIVE_INVALID')
            fact = _fact(metric=row['metric'], concept='reviewed-disclosure:'+row['metric'],
                value=None,unit='text',start=row['period_start'],end=row['period_end'],entity=entity,
                filing_id=row['filing_id'],filed=row['filed'],form=row['form'],
                disclosure_scope=row['disclosure_scope'],statement_basis=_text(row['statement_basis']),
                locator={'unit':'parsed-text','start':start,'end':end,'quote':quote,'page':row.get('page')})
            fact.update(value=literal,status='QUALITATIVE',numeric_value=None)
            fact['observation_id']='FIN-'+hashlib.sha256(json.dumps(fact,sort_keys=True).encode()).hexdigest()[:32]
            facts.append(fact)
            continue
        numeric = Decimal(_number(literal.replace(',','').replace('%','')))
        if Decimal(_number(row['value'])) != numeric * scale:
            _fail('FINANCIAL_VALUE_SCALE_MISMATCH')
        facts.append(_fact(metric=row['metric'],concept='reviewed-disclosure:'+row['metric'],
            value=row['value'],unit=row['unit'],start=row['period_start'],end=row['period_end'],entity=entity,
            filing_id=row['filing_id'],filed=row['filed'],form=row['form'],
            disclosure_scope=row['disclosure_scope'], statement_basis=_text(row['statement_basis']),
            source_scale=row['scale'], locator={'unit':'parsed-text','start':start,'end':end,'quote':quote,'page':row.get('page')}))
    return {'schema':SCHEMA,'format':'disclosure-extract','filing_entity':None,'facts':facts,
            'missing':[{'metric':m,'status':'MISSING','reason':'NOT_IN_SELECTED_DISCLOSURE_ANNOTATIONS'} for m in
                ('marketing_expense','retail_sales','occupancy','footfall') if m not in {f['metric'] for f in facts}],
            'warnings':['Dates, currency, filing identity and scope are caller-reviewed interpretations, not independently verified.']}


def _name(value):
    return ' '.join(unicodedata.normalize('NFKC', value or '').casefold().split())


def match_registered_entity(entity, *, actor, scope) -> dict:
    """Exact names only; never fuzzy/keyword/group-child matching or registry writes."""
    context = saved_work.authorize(actor, scope, action='read')
    from subject_registry import list_subjects, SubjectRegistryUnavailableError
    if not isinstance(entity, dict) or not entity.get('name'):
        return {'status':'MISSING','reason':'OFFICIAL_NAME_UNAVAILABLE','candidates':[]}
    try:
        with get_repository().connection(read_only=True, wal=False) as con:
            rows = list_subjects(context['domain_id'], connection=con)
    except SubjectRegistryUnavailableError:
        return {'status':'MISSING','reason':'REGISTERED_IDENTITY_UNAVAILABLE','candidates':[]}
    matches = [row for row in rows if _name(entity['name']) in {_name(row['name_en']),_name(row['name_zh'])}]
    # Registry names are configuration, not proof of CIK/LEI identity. A name
    # candidate must not silently become a verified identifier association.
    registry_domain = {'cth': 'CTH', 'zbmp': 'BMP'}[context['domain_id']]
    allowed = [row for row in matches if row.get('domain_id') == registry_domain and (
               context['global_scope'] is True or
               (bool(context['subject_id']) and context['subject_id'] == row.get('subject_id')) or
               (bool(context['brand_focus_id']) and context['brand_focus_id'] == row.get('brand_focus_id')))]
    if len(matches) != 1 or len(allowed) != 1:
        return {'status':'MISSING' if not allowed else 'AMBIGUOUS','reason':'NO_UNIQUE_EXACT_REGISTERED_NAME','candidates':[]}
    row = allowed[0]
    return {'status':'EXACT_NAME_CANDIDATE','subject_id':row['subject_id'],'brand_focus_id':row['brand_focus_id'],
            'domain_id':row['domain_id'],'identifier_verification':'NOT_VERIFIED',
            'allocation':'FILING_ENTITY_ONLY','reason':'Official identifier association needs source-backed review; no group/brand/project inheritance.'}


def analyze_financial_source(evidence_id, *, actor, scope, format='sec-companyfacts', annotations=None,
                             filing_id=None, filed=None, form=None, identity_review_artifact_id=None) -> dict:
    context = saved_work.authorize(actor, scope, action='read')
    source = documents.reopen_imported_source(evidence_id, actor=actor, scope=scope)
    with get_repository().connection(read_only=True, wal=False) as con:
        evidence = saved_work._verified_evidence(con, evidence_id, context, actor)
    text = evidence['raw_content']
    if format in {'sec-companyfacts','sec-companyconcept'}:
        result = parse_sec_json(source['content'])
    elif format == 'xbrl-instance':
        result = parse_xbrl_instance(source['content'], filing_id=filing_id, filed=filed, form=form)
    elif format == 'disclosure-extract':
        result = parse_disclosures(text, annotations)
    elif format == 'regional-statement':
        from urllib.parse import urlsplit
        from .financial_tables import parse_regional_statement
        host = (urlsplit(evidence['provenance'].get('source_url') or '').hostname or '').lower()
        exchange = ('HKEX' if host == 'hkexnews.hk' or host.endswith('.hkexnews.hk') else
                    'SSE' if host == 'sse.com.cn' or host.endswith('.sse.com.cn') else
                    'SZSE' if host == 'szse.cn' or host.endswith('.szse.cn') else None)
        if exchange is None:
            _fail('FINANCIAL_OFFICIAL_REGIONAL_SOURCE_REQUIRED')
        result = parse_regional_statement(text, evidence['provenance'].get('locators', []),
            exchange=exchange, filing_id=filing_id or source['sha256'], filed=filed, form=form)
    elif format == 'opendart-json':
        from .financial_tables import parse_opendart_json
        result = parse_opendart_json(source['content'])
    else:
        _fail('FINANCIAL_FORMAT_UNSUPPORTED')
    if len(result['facts']) > 10000:
        _fail('FINANCIAL_TOO_MANY_FACTS')
    origin = evidence['provenance'].get('content_origin', {})
    result.update(source={'evidence_id':evidence_id,'source_id':source['source_id'],'source_sha256':source['sha256'],
        'source_artifact_ref':source['artifact_ref'],'retained_filename':source['filename'],
        'source_url':evidence['provenance'].get('source_url'),'capture_mode':evidence['provenance'].get('capture_mode'),
        'claim_type':origin.get('claim_type'), 'rights':evidence['provenance'].get('provenance',{}).get('rights'),
        'original_filing_bytes_verified':False, 'retained_input_bytes_verified':True,
        'acquisition_authenticity':'NOT_INDEPENDENTLY_VERIFIED'},
        status='AVAILABLE' if result['facts'] else 'MISSING', derived=True, canonical_fact_promotion=False,
        entity_mappings=[])
    marker = evidence['provenance'].get('entity_profile')
    if isinstance(marker, dict) and marker.get('schema') == 'lumenis.entity-profile-assertions/v1':
        compilation = json.loads(source['content'])
        if hashlib.sha256(source['content']).hexdigest() != marker.get('sha256'):
            _fail('FINANCIAL_COMPILATION_HASH_MISMATCH')
        result['source']['upstream_sources'] = [{key: item.get(key) for key in
            ('id','source_url','capture_method','reviewed_on','origin_captured_at','excerpt_sha256','source_range','rights')}
            for item in compilation.get('sources', [])]
        for fact in result['facts']:
            quote = fact['locator'].get('quote')
            fact['upstream_source_ids'] = [item['id'] for item in compilation.get('sources', [])
                if quote and quote in item.get('excerpt', '')]
            if format == 'disclosure-extract' and not fact['upstream_source_ids']:
                _fail('FINANCIAL_COMPILATION_QUOTE_UNBOUND')
    for fact in result['facts']:
        fact['source_ref'] = {'evidence_id':evidence_id,'source_id':source['source_id'],
            'sha256':source['sha256'],'artifact_ref':source['artifact_ref']}
    entities = {json.dumps(f['filing_entity'],sort_keys=True) for f in result['facts']}
    for entity in sorted(entities):
        result['entity_mappings'].append({'filing_entity':json.loads(entity),
            'mapping':(read_financial_identity_review(identity_review_artifact_id,json.loads(entity),actor=actor,scope=scope)
                       if identity_review_artifact_id else match_registered_entity(json.loads(entity),actor=actor,scope=scope))})
    if format in {'disclosure-extract', 'regional-statement'}:
        spans = (sorted({(row['start'],row['end']) for row in annotations}) if format == 'disclosure-extract'
                 else sorted({(f['locator']['start'], f['locator']['end']) for f in result['facts']} |
                             {(f['locator']['header_start'], f['locator']['header_end']) for f in result['facts']}))
        if not spans:
            spans = [(0, min(len(text), 1000))]
        result['citations'] = [documents.locate_quote(evidence_id, actor=actor,scope=scope,
            start=start,end=end)['citation'] for start,end in spans]
        for fact in result['facts']:
            if 'quote' in fact['locator']:
                quote = fact['locator'].pop('quote')
                fact['locator']['quote_sha256'] = hashlib.sha256(quote.encode()).hexdigest()
    else:
        result['citations'] = [documents.locate_quote(evidence_id,actor=actor,scope=scope,
            start=0,end=min(len(text),1000))['citation']]
    return result


def save_financial_analysis(evidence_id, *, actor, scope, request_id, work_id=None,
                            previous_artifact_id=None, **options):
    result = analyze_financial_source(evidence_id, actor=actor,scope=scope,**options)
    citations = result.pop('citations')
    summary = ['Financial disclosures',f"Source: {result['source']['source_url']}",
               f"Status: {result['status']}; observations: {len(result['facts'])}",
               'Source assertions; no automatic allocation, missing-value imputation or Canonical fact promotion.']
    summary.extend('Reported origin (assisted excerpt): '+str(item['source_url'])
                   for item in result['source'].get('upstream_sources', []))
    summary.extend(f"{f['metric']} | {f['period_start']}..{f['period_end']} | {f['value']} {f['unit']} | {f['filing_id']}"
                   for f in result['facts'])
    def recheck_identity(*_):
        review_id = options.get('identity_review_artifact_id')
        if review_id:
            for mapping in result['entity_mappings']:
                read_financial_identity_review(review_id,mapping['filing_entity'],actor=actor,scope=scope)
    return saved_work.save_work(title='Financial disclosures', markdown='\n'.join(summary),kind='research',
        payload={'financial':result},citations=citations,request_id=request_id,actor=actor,scope=scope,
        work_id=work_id,previous_artifact_id=previous_artifact_id,
        contract={'id':SCHEMA,'version':'1','required_payload_paths':['financial.facts','financial.source']},
        before_commit=recheck_identity)


def spend_proxy(*, rate=None, exposure=None, probability=None) -> dict:
    """A bounded estimate, not observed spending. Every input needs provenance."""
    if rate is None or exposure is None or probability is None:
        return {'status':'MISSING','reason':'RATE_EXPOSURE_AND_AD_PROBABILITY_REQUIRED','interval':None}
    required = {'lower','upper','currency','basis','source_ref','period_start','period_end','channel','entity'}
    if not isinstance(rate,dict) or set(rate) != required or rate['basis'] not in {'CPM','CPC','per_content'}:
        _fail('SPEND_RATE_INVALID')
    if not isinstance(exposure,dict) or set(exposure) != {'value','basis','source_ref','period_start','period_end','channel','entity'}:
        _fail('SPEND_EXPOSURE_INVALID')
    if not isinstance(probability,dict) or set(probability) != {'lower','upper','source_ref'}:
        _fail('SPEND_PROBABILITY_INVALID')
    for item in (rate,exposure,probability):
        _text(item['source_ref'])
    for key in ('period_start','period_end','channel','entity'):
        if rate[key] != exposure[key]:
            _fail('SPEND_SCOPE_MISMATCH')
    _period(rate['period_start'],rate['period_end'])
    if exposure['basis'] != {'CPM':'impressions','CPC':'clicks','per_content':'content_count'}[rate['basis']]:
        _fail('SPEND_MEASURE_MISMATCH')
    if not re.fullmatch('[A-Z]{3}',rate['currency']):
        _fail('SPEND_CURRENCY_INVALID')
    lower, upper, count, pl, pu = [Decimal(_number(v)) for v in
        (rate['lower'],rate['upper'],exposure['value'],probability['lower'],probability['upper'])]
    if not 0 <= lower <= upper or count < 0 or not 0 <= pl <= pu <= 1:
        _fail('SPEND_RANGE_INVALID')
    divisor = 1000 if rate['basis']=='CPM' else 1
    return {'status':'ESTIMATED','interval':[str(lower*count*pl/divisor),str(upper*count*pu/divisor)],
            'currency':rate['currency'],'method':'rate-range × observed exposure × ad-probability-range',
            'inputs':{'rate':rate,'exposure':exposure,'probability':probability},
            'limitations':['List-price proxy, not actual paid spend; no inferred clicks or impressions.'],
            'canonical_fact_promotion':False}


def select_quarterly_series(facts, *, metric, unit, filing_entity, as_of):
    """Explicit as-of, unit and entity selection. Refuse revision ambiguity.

    No interpolation, annual split, cumulative subtraction or invented quarters.
    Calendar-quarter alignment is deliberately strict for the current MMM caller.
    """
    _date(as_of)
    chosen = {}
    for fact in facts:
        if (fact['metric'] != metric or fact['unit'] != unit or fact['filing_entity'] != filing_entity
                or fact['disclosure_scope'] != 'filing_entity' or fact['period_kind'] != 'quarter'
                or fact['status'] != 'DISCLOSED' or not fact['filed'] or fact['filed'] > as_of):
            continue
        start, end = _date(fact['period_start']), _date(fact['period_end'])
        quarter = (start.month-1)//3+1
        ends = {1:(3,31),2:(6,30),3:(9,30),4:(12,31)}
        if start.day != 1 or start.month not in {1,4,7,10} or (end.month,end.day)!=ends[quarter] or start.year!=end.year:
            continue
        key = f'{start.year}-Q{quarter}'
        previous = chosen.get(key)
        if previous and previous['filed'] == fact['filed'] and previous['value'] != fact['value']:
            return {'status':'INSUFFICIENT','reason':'AMBIGUOUS_SAME_DATE_REVISIONS','periods':[]}
        if previous is None or fact['filed'] > previous['filed']:
            chosen[key] = fact
    rows = [{'period':key,'value':value['value'],'observation_id':value['observation_id'],
             'filing_id':value['filing_id'],'filed':value['filed']} for key,value in sorted(chosen.items())]
    ordinals = [int(row['period'][:4])*4 + int(row['period'][-1]) for row in rows]
    contiguous = all(b-a == 1 for a,b in zip(ordinals,ordinals[1:]))
    ready = len(rows)>=12 and contiguous
    return {'status':'AVAILABLE' if ready else 'INSUFFICIENT','reason':None if ready else ('NON_CONTIGUOUS_QUARTERS' if not contiguous else 'FEWER_THAN_12_DISCLOSED_QUARTERS'),
            'periods':rows,'unit':unit,'filing_entity':filing_entity,'as_of':as_of,'selection':'latest-filed-by-explicit-as-of'}


# Acquisition is a typed use of existing Registry -> Collector -> Importer.
# SavedWork below retains user plans and captured originals; it is not an
# alternate SourceTarget registry, identity authority or scheduler.
TARGET_SCHEMA = 'lumenis.financial-acquisition-plan/v1'
CAPTURE_SCHEMA = 'lumenis.financial-capture/v1'


def _registered_target(identity_evidence_id, *, actor, scope, format, taxonomy, concept):
    if format == 'regional-statement':
        return _regional_registered_target(identity_evidence_id, actor=actor, scope=scope)
    from urllib.parse import urlsplit
    context = saved_work.authorize(actor, scope, action='read')
    if context['global_scope']:
        _fail('FINANCIAL_EXACT_REGISTERED_TARGET_REQUIRED')
    if context['brand_focus_id'] is not None:
        _fail('FINANCIAL_LEGAL_ISSUER_SCOPE_REQUIRED')
    if format not in {'sec-companyfacts','sec-companyconcept'} or taxonomy not in {'us-gaap','ifrs-full'}:
        _fail('FINANCIAL_AUTOMATIC_FORMAT_UNSUPPORTED')
    if concept not in CONCEPTS:
        _fail('FINANCIAL_CONCEPT_UNSUPPORTED')
    source = documents.reopen_imported_source(identity_evidence_id,actor=actor,scope=scope)
    with get_repository().connection(read_only=True,wal=False) as con:
        evidence = saved_work._verified_evidence(con,identity_evidence_id,context,actor)
    url = evidence['provenance'].get('source_url')
    if not isinstance(url,str) or urlsplit(url).hostname != 'data.sec.gov' or urlsplit(url).scheme != 'https':
        _fail('FINANCIAL_SEC_IDENTITY_SOURCE_REQUIRED')
    parsed = parse_sec_json(source['content'])
    entity = parsed['filing_entity']
    mapping = match_registered_entity(entity,actor=actor,scope=scope)
    if mapping['status'] != 'EXACT_NAME_CANDIDATE':
        _fail('FINANCIAL_REGISTRY_FILING_IDENTITY_MISMATCH')
    cik = entity['identifier']
    # The official data URL and JSON CIK must independently agree. A supplied
    # company name alone is not enough to bind a different issuer's endpoint.
    if not re.fullmatch(r'/api/xbrl/(?:companyfacts/CIK'+cik+r'\.json|companyconcept/CIK'+cik+r'/(?:us-gaap|ifrs-full)/[A-Za-z][A-Za-z0-9]*\.json)',urlsplit(url).path):
        _fail('FINANCIAL_SEC_IDENTITY_URL_MISMATCH')
    target_url = (f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json' if format=='sec-companyfacts'
                  else f'https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json')
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    from subject_registry import list_subjects
    with get_repository().connection(read_only=True,wal=False) as con:
        registered = [row for row in list_subjects(context['domain_id'],connection=con)
            if row['subject_id'] == mapping['subject_id']]
    scope_key=context['subject_id'] or context['brand_focus_id']
    domain='CTH' if context['domain_id']=='cth' else 'BMP'
    plan=build_acquisition_plan(context_mode='FOCUS',domain_id=domain,
        subject_id=context['subject_id'],brand_focus_id=context['brand_focus_id'],
        registry_loader=lambda:registered,
        business_requests=[{'domain_id':domain,'scope_key':scope_key,
            'purpose':'financial_disclosure','dimension':'market_activity','platforms':['public_http'],
            'tracking_sources':[{'url':target_url,'scope_key':scope_key,
                'evidence_ref':f'app_evidence_records:{identity_evidence_id}'}]}])
    if not plan.is_runnable or len(plan.queries)!=1 or plan.queries[0].keyword!=target_url:
        _fail('FINANCIAL_ACQUISITION_PLAN_UNAVAILABLE')
    return {'schema':TARGET_SCHEMA,'plan_is_identity_fact':False,'acquisition_plan':plan.to_dict(),
            'identity_evidence_id':identity_evidence_id,'identity_source_sha256':source['sha256'],
            'filing_entity':entity,'registry_ref':{k:mapping[k] for k in ('subject_id','brand_focus_id','domain_id')},
            'format':format,'taxonomy':taxonomy,'concept':concept,'url':target_url,
            'max_bytes':2*1024*1024,'scope':'filing_entity','acquisition_owner':'SYSTEM Collector public_http',
            'identity_assurance':'Exact registered name plus source-asserted CIK and matching SEC URL; no independent legal-identity audit'}


def save_financial_target(identity_evidence_id, *, actor, scope, request_id,
                          format='sec-companyconcept', taxonomy='us-gaap', concept='AdvertisingExpense',
                          work_id=None, previous_artifact_id=None):
    target = _registered_target(identity_evidence_id,actor=actor,scope=scope,format=format,taxonomy=taxonomy,concept=concept)
    evidence = documents.locate_quote(identity_evidence_id,actor=actor,scope=scope,start=0,end=1)['citation']
    return saved_work.save_work(title='Financial acquisition plan',markdown='Registered-entity source plan: '+target['url']+
        '\nThis plan is configuration, not an entity fact or a new SourceTarget registry. Original-source admission remains separately gated.',
        kind='research',payload={'financial_target':target},citations=[evidence],request_id=request_id,
        actor=actor,scope=scope,work_id=work_id,previous_artifact_id=previous_artifact_id,
        contract={'id':TARGET_SCHEMA,'version':'1','required_payload_paths':['financial_target']})


def _read_target(target_artifact_id, *, actor, scope):
    work = saved_work.reopen_work(target_artifact_id,actor=actor,scope=scope)
    if work['document']['contract']['id'] != TARGET_SCHEMA:
        _fail('FINANCIAL_TARGET_CONTRACT_INVALID')
    target = work['document']['payload'].get('financial_target')
    if not isinstance(target,dict):
        _fail('FINANCIAL_TARGET_INVALID')
    verified = _registered_target(target.get('identity_evidence_id'),actor=actor,scope=scope,
        format=target.get('format'),taxonomy=target.get('taxonomy'),concept=target.get('concept'))
    if saved_work._json(target) != saved_work._json(verified):
        _fail('FINANCIAL_TARGET_CHANGED')
    return work, verified


def prepare_financial_collection(target_artifact_id, *, actor, scope):
    work, target = _read_target(target_artifact_id,actor=actor,scope=scope)
    resource = 'financial-source-read:v1:'+saved_work._digest({'target_artifact_id':target_artifact_id,
        'target_sha256':work['artifact']['sha256'],'scope':scope,'url':target['url'],'max_bytes':target['max_bytes']})
    return {'state':'PREPARED','resource':resource,'url':target['url'],'scope':scope,'max_bytes':target['max_bytes'],
            'effect':'READ_PUBLIC_FINANCIAL_SOURCE_AND_RETAIN_ORIGINAL','target_artifact_id':target_artifact_id}


def _existing_request(request_id, *, actor, scope):
    return documents._existing_source_request(request_id,actor=actor,scope=scope,error_prefix='FINANCIAL')


def _financial_capture_spec():
    return {'error_prefix':'FINANCIAL', 'capture_schema':CAPTURE_SCHEMA,
        'capture_key':'financial_capture', 'run_key':'financial_collection_run',
        'capture_request_prefix':'financial-capture-',
        'capture_title':'Financial source original capture', 'run_title':'Financial collection check',
        'filename':lambda target:'filing.pdf' if target['format']=='regional-statement' else 'filing.json',
        'media_type':lambda target:'application/pdf' if target['format']=='regional-statement' else 'application/json',
        'original_filing':lambda target:target['format']=='regional-statement',
        'source_title':lambda target:'Public financial data '+target['filing_entity']['name'],
        'unavailable_hint':'For oversized companyfacts choose a smaller official companyconcept target; never parse a truncated document.'}


def _validate_financial_response(raw, target):
    parsed = _regional_raw(raw,target) if target['format']=='regional-statement' else parse_sec_json(raw)
    if parsed['filing_entity'] != target['filing_entity']:
        _fail('FINANCIAL_RESPONSE_FILING_IDENTITY_MISMATCH')
    if target['format']=='sec-companyconcept':
        source_object=json.loads(raw)
        if source_object.get('taxonomy')!=target['taxonomy'] or source_object.get('tag')!=target['concept']:
            _fail('FINANCIAL_RESPONSE_CONCEPT_MISMATCH')


def collect_financial_target(target_artifact_id, *, actor, scope, request_id):
    return documents._collect_admitted_document(target_artifact_id,actor=actor,scope=scope,request_id=request_id,
        spec=_financial_capture_spec(),prepare_collection=prepare_financial_collection,read_target=_read_target,
        existing_request=_existing_request,validate_response=_validate_financial_response,
        prepare_capture=prepare_financial_capture)


def _capture_material(capture_artifact_id, *, actor, scope):
    return documents._read_admitted_document_capture(capture_artifact_id,actor=actor,scope=scope,
        spec=_financial_capture_spec(),read_target=_read_target,validate_response=_validate_financial_response)


def prepare_financial_capture(capture_artifact_id, *, actor, scope):
    return documents._prepare_admitted_document_capture(capture_artifact_id,actor=actor,scope=scope,
        read_capture=_capture_material)


def import_financial_capture(capture_artifact_id, *, actor, scope):
    material,source = documents._import_admitted_document_capture(capture_artifact_id,actor=actor,scope=scope,
        read_capture=_capture_material,error_prefix='FINANCIAL')
    analysis=analyze_financial_source(source['evidence_id'],actor=actor,scope=scope,format=material['format'])
    return {'state':'IMPORTED','source':source,'analysis':analysis,'capture_artifact_id':capture_artifact_id,
            'target_artifact_id':material['target_artifact_id']}


IDENTITY_REVIEW_SCHEMA = 'lumenis.financial-identity-review/v1'


def _identity_review_material(evidence_id, *, actor, scope, entity, name_span, identifier_span):
    """Validate reviewer-selected literal evidence against the original Registry."""
    from urllib.parse import urlsplit
    context = saved_work.authorize(actor, scope, action='read')
    if context['global_scope'] or context['brand_focus_id'] is not None:
        _fail('FINANCIAL_LEGAL_ISSUER_SCOPE_REQUIRED')
    if not isinstance(entity, dict) or set(entity) != {'name','scheme','identifier'}:
        _fail('FINANCIAL_FILING_ENTITY_INVALID')
    for value in entity.values():
        _text(value)
    patterns={'SEC-CIK':r'\d{10}','HKEX-StockCode':r'\d{5}','SSE-StockCode':r'\d{6}',
              'SZSE-StockCode':r'\d{6}','OpenDART-CorpCode':r'\d{8}'}
    if not re.fullmatch(patterns.get(entity['scheme'],r'(?!)'),entity['identifier']):
        _fail('FINANCIAL_IDENTITY_IDENTIFIER_INVALID')
    hosts={'SEC-CIK':{'www.sec.gov','sec.gov','data.sec.gov'},
           'HKEX-StockCode':{'www.hkexnews.hk','www1.hkexnews.hk','hkexnews.hk'},
           'SSE-StockCode':{'www.sse.com.cn','sse.com.cn','static.sse.com.cn'},
           'SZSE-StockCode':{'www.szse.cn','szse.cn','disc.static.szse.cn'},
           'OpenDART-CorpCode':{'opendart.fss.or.kr','engopendart.fss.or.kr','dart.fss.or.kr'}}
    source=documents.reopen_imported_source(evidence_id,actor=actor,scope=scope)
    with get_repository().connection(read_only=True,wal=False) as con:
        evidence=saved_work._verified_evidence(con,evidence_id,context,actor)
    url=urlsplit(evidence['provenance'].get('source_url') or '')
    if url.scheme!='https' or url.hostname not in hosts.get(entity['scheme'],set()):
        _fail('FINANCIAL_IDENTITY_OFFICIAL_SOURCE_REQUIRED')
    citations=[]
    for span, expected in ((name_span,entity['name']),(identifier_span,entity['identifier'])):
        if not isinstance(span,dict) or set(span)!={'start','end'}:
            _fail('FINANCIAL_IDENTITY_SPAN_REQUIRED')
        citation=documents.locate_quote(evidence_id,actor=actor,scope=scope,**span)['citation']
        if _name(citation['quote']) != _name(expected):
            _fail('FINANCIAL_IDENTITY_LITERAL_MISMATCH')
        citations.append(citation)
    mapping=match_registered_entity(entity,actor=actor,scope=scope)
    if mapping['status']!='EXACT_NAME_CANDIDATE' or mapping['subject_id']!=context['subject_id']:
        _fail('FINANCIAL_REGISTRY_FILING_IDENTITY_MISMATCH')
    return {'identity_evidence_id':evidence_id,'source_sha256':source['sha256'],'source_url':url.geturl(),
            'filing_entity':entity,'name_span':name_span,'identifier_span':identifier_span,
            'registry_ref':{k:mapping[k] for k in ('domain_id','subject_id','brand_focus_id')},
            'allocation':'FILING_ENTITY_ONLY','independent_legal_verification':'NOT_VERIFIED'}, citations


def save_financial_identity_review(identity_evidence_id, *, actor, scope, entity, name_span,
                                   identifier_span, reviewed, review_note, request_id,
                                   work_id=None, previous_artifact_id=None):
    context=saved_work.authorize(actor,scope,action='write')
    if type(reviewed) is not bool or (not reviewed and (not work_id or not previous_artifact_id)):
        _fail('FINANCIAL_EXPLICIT_IDENTITY_REVIEW_REQUIRED')
    note=_text(review_note,'FINANCIAL_IDENTITY_REVIEW_NOTE_REQUIRED')
    material,citations=_identity_review_material(identity_evidence_id,actor=actor,scope=scope,
        entity=entity,name_span=name_span,identifier_span=identifier_span)
    material.update(status='REVIEWED_SOURCE_ASSOCIATION' if reviewed else 'REVOKED',review_note=note,
                    reviewer={k:v for k,v in context.items() if k in {'actor_id','principal_kind','principal_ref'}})
    def recheck(con, record, document):
        current,_=_identity_review_material(identity_evidence_id,actor=actor,scope=scope,
            entity=entity,name_span=name_span,identifier_span=identifier_span)
        if any(current[k]!=material[k] for k in current):
            _fail('FINANCIAL_IDENTITY_REVIEW_SOURCE_CHANGED')
        from lumenis.shared.evidence import store
        current_context = saved_work.authorize(actor, scope, action='write', connection=con)
        binding = _identity_review_binding(record, document, current_context)
        receipt_id = store.record_evidence(
            source=IDENTITY_REVIEW_SCHEMA, feature_id=record['artifact_id'], asset_id=record['artifact_id'],
            product='ZBMP' if current_context['domain_id']=='zbmp' else 'CTH',
            domain_id=current_context['domain_id'], subject_id=current_context['subject_id'],
            brand_focus_id=current_context['brand_focus_id'], global_scope=current_context['global_scope'],
            inputs={'review_binding':binding}, outputs={'review_recorded':True},
            account=current_context.get('principal_ref') or 'actor:'+str(current_context['actor_id']),
            provider=__name__, status='pending', capture_mode='explicit-actor-review', connection=con)
        row=con.execute('SELECT * FROM app_evidence_records WHERE id=?',(receipt_id,)).fetchone()
        if not row or not store.verify_evidence_record_integrity(row):
            _fail('FINANCIAL_IDENTITY_REVIEW_RECEIPT_SIGNING_FAILED')
    return saved_work.save_work(title='Reviewed filing identity association',
        markdown=entity['name']+' | '+entity['scheme']+' | '+entity['identifier']+
                 '\nStatus: '+material['status']+'; Independent legal verification: NOT_VERIFIED.\n'+note,
        kind='research',payload={'financial_identity_review':material},citations=citations,
        request_id=request_id,actor=actor,scope=scope,work_id=work_id,previous_artifact_id=previous_artifact_id,
        contract={'id':IDENTITY_REVIEW_SCHEMA,'version':'1','required_payload_paths':['financial_identity_review']},
        before_commit=recheck)


def _identity_review_binding(artifact, document, context):
    return {'contract':'financial-identity-review-receipt/v1', 'context':context,
            'artifact_id':artifact['artifact_id'], 'artifact_sha256':artifact['sha256'],
            'work_id':document['work_id'], 'version':document['version'],
            'parent_artifact_id':document.get('parent_artifact_id'),
            'review_sha256':saved_work._digest(document['payload']['financial_identity_review'])}


def _verify_identity_review_receipt(work, context, con):
    from lumenis.shared.evidence import store
    rows=con.execute('SELECT * FROM app_evidence_records WHERE source=? AND asset_id=?',
                     (IDENTITY_REVIEW_SCHEMA,work['artifact']['artifact_id'])).fetchall()
    if len(rows)!=1 or not store.verify_evidence_record_integrity(rows[0]):
        _fail('FINANCIAL_IDENTITY_REVIEW_OWNER_RECEIPT_REQUIRED')
    row=dict(rows[0])
    expected=_identity_review_binding(work['artifact'],work['document'],context)
    if (row.get('provider')!=__name__ or row.get('feature_id')!=expected['artifact_id']
            or row.get('capture_mode')!='explicit-actor-review'
            or json.loads(row['inputs_json']).get('review_binding')!=expected):
        _fail('FINANCIAL_IDENTITY_REVIEW_OWNER_RECEIPT_MISMATCH')


def read_financial_identity_review(artifact_id, entity, *, actor, scope):
    work=saved_work.reopen_work(artifact_id,actor=actor,scope=scope)
    if work['document']['contract']['id']!=IDENTITY_REVIEW_SCHEMA:
        _fail('FINANCIAL_IDENTITY_REVIEW_CONTRACT_INVALID')
    context=saved_work.authorize(actor,scope,action='read')
    with get_repository().connection(read_only=True,wal=False) as con:
        versions=saved_work._versions(con,work['document']['work_id'],context,actor)
        _verify_identity_review_receipt(work,context,con)
    if not versions or versions[-1]['artifact']['artifact_id']!=artifact_id:
        _fail('FINANCIAL_IDENTITY_REVIEW_SUPERSEDED')
    review=work['document']['payload'].get('financial_identity_review',{})
    if review.get('filing_entity')!=entity or review.get('status')!='REVIEWED_SOURCE_ASSOCIATION':
        _fail('FINANCIAL_IDENTITY_REVIEW_ENTITY_MISMATCH')
    current,_=_identity_review_material(review['identity_evidence_id'],actor=actor,scope=scope,
        entity=entity,name_span=review['name_span'],identifier_span=review['identifier_span'])
    if any(review.get(k)!=v for k,v in current.items()):
        _fail('FINANCIAL_IDENTITY_REVIEW_SOURCE_CHANGED')
    return {'status':'REVIEWED_SOURCE_ASSOCIATION',**current['registry_ref'],
            'identifier_verification':'SOURCE_BACKED_HUMAN_REVIEW','independent_legal_verification':'NOT_VERIFIED',
            'allocation':'FILING_ENTITY_ONLY','review_artifact_id':artifact_id,
            'identity_evidence_id':review['identity_evidence_id'],'source_sha256':review['source_sha256']}


def _regional_raw(raw, target):
    import tempfile
    from pathlib import Path
    from .parser import parse_file
    from .financial_tables import parse_regional_statement
    if not isinstance(raw,bytes) or not raw.startswith(b'%PDF-') or not 0 < len(raw) <= 2*1024*1024:
        _fail('FINANCIAL_REGIONAL_PDF_REQUIRED')
    with tempfile.TemporaryDirectory(prefix='lumenis-financial-parser-') as directory:
        path=Path(directory)/'filing.pdf';path.write_bytes(raw)
        parsed=parse_file(str(path))
    return parse_regional_statement(parsed.text,parsed.locators,exchange=target['exchange'],
                                    filing_id=hashlib.sha256(raw).hexdigest())


def _regional_registered_target(identity_evidence_id, *, actor, scope):
    from urllib.parse import urlsplit
    from .financial_tables import parse_regional_statement
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan
    from subject_registry import list_subjects
    context=saved_work.authorize(actor,scope,action='read')
    if context['global_scope'] or context['brand_focus_id'] is not None:
        _fail('FINANCIAL_LEGAL_ISSUER_SCOPE_REQUIRED')
    source=documents.reopen_imported_source(identity_evidence_id,actor=actor,scope=scope)
    with get_repository().connection(read_only=True,wal=False) as con:
        evidence=saved_work._verified_evidence(con,identity_evidence_id,context,actor)
        registered=list_subjects(context['domain_id'],connection=con)
    url=evidence['provenance'].get('source_url') or ''
    parsed_url=urlsplit(url);host=(parsed_url.hostname or '').lower()
    exchange=('HKEX' if host=='hkexnews.hk' or host.endswith('.hkexnews.hk') else
              'SSE' if host=='sse.com.cn' or host.endswith('.sse.com.cn') else
              'SZSE' if host=='szse.cn' or host.endswith('.szse.cn') else None)
    if parsed_url.scheme!='https' or exchange is None or not parsed_url.path.lower().endswith('.pdf') or parsed_url.query or parsed_url.fragment:
        _fail('FINANCIAL_OFFICIAL_REGIONAL_PDF_REQUIRED')
    if not source['content'].startswith(b'%PDF-'):
        _fail('FINANCIAL_REGIONAL_PDF_REQUIRED')
    parsed=parse_regional_statement(evidence['raw_content'],evidence['provenance'].get('locators',[]),
        exchange=exchange,filing_id=source['sha256'])
    entity=parsed['filing_entity'];mapping=match_registered_entity(entity,actor=actor,scope=scope)
    if mapping['status']!='EXACT_NAME_CANDIDATE' or mapping['subject_id']!=context['subject_id']:
        _fail('FINANCIAL_REGISTRY_FILING_IDENTITY_MISMATCH')
    registered=[row for row in registered if row['subject_id']==context['subject_id']]
    domain='CTH' if context['domain_id']=='cth' else 'BMP'
    plan=build_acquisition_plan(context_mode='FOCUS',domain_id=domain,subject_id=context['subject_id'],
        brand_focus_id=None,registry_loader=lambda:registered,business_requests=[{'domain_id':domain,
        'scope_key':context['subject_id'],'purpose':'financial_disclosure','dimension':'market_activity',
        'platforms':['public_http'],'tracking_sources':[{'url':url,'scope_key':context['subject_id'],
        'evidence_ref':f'app_evidence_records:{identity_evidence_id}'}]}])
    if not plan.is_runnable or len(plan.queries)!=1 or plan.queries[0].keyword!=url:
        _fail('FINANCIAL_ACQUISITION_PLAN_UNAVAILABLE')
    return {'schema':TARGET_SCHEMA,'plan_is_identity_fact':False,'acquisition_plan':plan.to_dict(),
        'identity_evidence_id':identity_evidence_id,'identity_source_sha256':source['sha256'],
        'filing_entity':entity,'registry_ref':{k:mapping[k] for k in ('subject_id','brand_focus_id','domain_id')},
        'format':'regional-statement','taxonomy':None,'concept':None,'exchange':exchange,'url':url,
        'max_bytes':2*1024*1024,'scope':'filing_entity','acquisition_owner':'SYSTEM Collector public_http',
        'identity_assurance':'Source cover name/code plus exact registered issuer name; independent legal verification NOT_VERIFIED',
        'discovery':'Exact reviewed filing URL only; no automatic exchange-wide discovery or new-period URL inference'}
