"""Bounded deterministic regional statement extraction inside original Importer.

Consumes original Parser text/locators; no OCR, model, network or truth owner.
Recognized statement layouts yield source assertions; ambiguity stays candidates.
"""
from __future__ import annotations
import calendar
import hashlib
import json
import re
from datetime import date, timedelta
from decimal import Decimal

LABELS = {
    'Revenue': 'revenue', 'Revenue from contracts with customers': 'revenue',
    'Rental income': 'rental_income', 'Gross rental income': 'rental_income',
    'Advertising expenses': 'advertising_expense', 'Advertising expense': 'advertising_expense',
    'Marketing expenses': 'marketing_expense', 'Selling and marketing expenses': 'selling_marketing_expense',
    'Administrative and selling expenses': 'selling_general_admin_expense',
    'Selling, general and administrative expenses': 'selling_general_admin_expense',
    '营业收入': 'revenue', '营业总收入': 'total_operating_revenue',
    '销售费用': 'selling_expense', '广告费': 'advertising_expense',
    '广告宣传费': 'advertising_promotion_expense', '租金收入': 'rental_income',
}
NUMBER = r'(?:\((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\)|-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|—|–|-)'
MONEY = {'HK$M': ('HKD', 1000000), 'HK$ million': ('HKD', 1000000),
         "HK$'000": ('HKD', 1000), "RMB'000": ('CNY', 1000),
         'RMB million': ('CNY', 1000000), 'RMB千元': ('CNY', 1000)}
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}


def _entity(text, exchange):
    cover = text[:6000]
    if exchange == 'HKEX':
        m = re.search(r'(?m)^([^\n]{3,200}(?:LIMITED|Limited))\s*\n\(Incorporated[^\n]*\)\s*\n\(Stock Code:\s*(\d{4,5})\)', cover)
        if m:
            return {'name': m[1].strip(), 'scheme': 'HKEX-StockCode', 'identifier': m[2].zfill(5)}
    else:
        name = re.search(r'(?m)^(?:公司名称[：:]\s*)?([^\n]{2,100}股份有限公司)\s*$', cover)
        code = re.search(r'(?:股票|证券)代码\s*[：:]\s*(\d{6})', cover)
        if name and code:
            return {'name': name[1].strip(), 'scheme': exchange+'-StockCode', 'identifier': code[1]}
    return None


def _periods(page, years):
    """Only explicit calendar dates and named annual/half-year durations."""
    matches = list(re.finditer(r'For the (year|six months|half year) ended (\d{1,2})(?:st|nd|rd|th)?\s+(\w+)\s+(20\d{2})', page, re.I))
    if len(matches) == 1:
        m = matches[0]
        if int(m[4]) != years[0] or m[3].lower() not in MONTHS:
            return None
        month, day = MONTHS[m[3].lower()], int(m[2])
        count = 12 if m[1].lower() == 'year' else 6
        result = []
        for year in years:
            try:
                finish = date(year, month, day)
                # Only complete calendar months; arbitrary fiscal endpoints are candidates.
                if day != calendar.monthrange(year, month)[1]:
                    return None
                next_month = year * 12 + month
                first = next_month - count
                begin = date(first // 12, first % 12 + 1, 1)
            except ValueError:
                return None
            result.append((begin.isoformat(), finish.isoformat()))
        return result
    # Chinese annual statements explicitly label both columns as 年度.
    if all(re.search(str(y)+r'\s*年度', page) for y in years):
        return [(f'{y}-01-01', f'{y}-12-31') for y in years]
    # Chinese half-year statement columns with explicit start/end calendar dates.
    dates = re.findall(r'(20\d{2})\s*年\s*1\s*[-至—]\s*6\s*月', page)
    if [int(x) for x in dates] == years:
        return [(f'{y}-01-01', f'{y}-06-30') for y in years]
    return None


def parse_regional_statement(text, locators, *, exchange, filing_id, filed=None, form=None):
    from .financial import _fact, SCHEMA
    if exchange not in {'HKEX', 'SSE', 'SZSE'} or not isinstance(text, str) or not 0 < len(text) <= 8*1024*1024:
        raise ValueError('FINANCIAL_REGIONAL_SOURCE_INVALID')
    entity = _entity(text, exchange)
    facts, candidates = [], []
    pages = [x for x in locators if x.get('unit') == 'pdf_page']
    if not pages:
        pages = [{'unit': 'parsed-text', 'index': None, 'start': 0, 'end': len(text)}]
    # A page may contain several tables. Never let a first table's metadata
    # authorize later parent/segment/note rows or a second column header.
    statement_pattern = r'Consolidated (?:Statement of Profit or Loss|Income Statement)|合并利润表'
    bounded_pages = []
    for page in pages:
        start, end = page['start'], page['end']
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(text):
            raise ValueError('FINANCIAL_LOCATOR_INVALID')
        headings = list(re.finditer(statement_pattern, text[start:end], re.I))
        if not headings:
            for label, metric in LABELS.items():
                for match in re.finditer(r'(?im)^\s*'+re.escape(label)+r'\s+([^\n]+)$', text[start:end]):
                    candidates.append({'metric':metric, 'label':label, 'status':'REVIEW_REQUIRED',
                        'reason':'PRIMARY_STATEMENT_CONTEXT_NOT_VERIFIED',
                        'locator':{'unit':'parsed-text','start':start+match.start(),'end':start+match.end(),
                                   'page':page['index'],'quote_sha256':hashlib.sha256(match[0].encode()).hexdigest()}})
        for index, heading in enumerate(headings):
            bounded_pages.append(dict(page, start=start+heading.start(),
                end=start+headings[index+1].start() if index+1 < len(headings) else end))
    for page in bounded_pages:
        start, end = page['start'], page['end']
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(text):
            raise ValueError('FINANCIAL_LOCATOR_INVALID')
        body = text[start:end]
        statement = re.search(statement_pattern, body, re.I)
        if not statement:
            continue
        rows = []
        for label, metric in LABELS.items():
            for match in re.finditer(r'(?im)^\s*'+re.escape(label)+r'\s+([^\n]+)$', body):
                if match.start() > statement.end():
                    rows.append((label, metric, match))
        rows.sort(key=lambda row: row[2].start())
        if not rows:
            continue
        # A year-only header (or Chinese annual columns) before the first metric.
        header = body[statement.end():min(m.start() for _, _, m in rows)]
        year_lines = re.findall(r'(?m)^\s*(20\d{2})\s*(?:年度|年)?\s+(20\d{2})\s*(?:年度|年)?\s*$', header)
        years = list(map(int, year_lines[0])) if len(year_lines) == 1 else []
        periods = _periods(header, years) if len(years) == 2 and years[0] > years[1] else None
        money = {value for marker, value in MONEY.items() for line in header.splitlines()
                 if re.fullmatch(r'(?:Note\s+|附注\s+)?'+re.escape(marker)+r'\s+'+re.escape(marker), line.strip(), re.I)}
        if re.search(r'币种\s*[：:]?\s*人民币', header):
            scale = re.findall(r'单位\s*[：:]?\s*(亿元|万元|千元|元)', header)
            if len(set(scale)) == 1:
                money.add(('CNY', {'元':1,'千元':1000,'万元':10000,'亿元':100000000}[scale[0]]))
        # An explicit later section or column-context line ends this table.
        # Ambiguous continuations remain review candidates, never guessed facts.
        boundary_pattern = (
            r'(?im)^[^\S\n]*(?:'
            r'(?:Notes?\s+(?:to|on)\b|Notes?\s*$|Parent\s+(?:company|entity)\b|'
            r'Company\s+(?:only|statement|income)\b|Segment\b|'
            r'(?:Consolidated\s+)?Statement\s+of\s+(?!Profit\s+or\s+Loss)|'
            r'财务报表附注|財務報表附註|母公司|分部|单位\s*[：:]|币种\s*[：:]|'
            r'For\s+the\s+(?:year|six\s+months|half\s+year)\s+ended\b|'
            r'20\d{2}(?:\s*(?:年度|年))?\s+20\d{2}\b|'
            r'(?:Note\s+|附注\s+)?(?:HK\$|RMB|USD|HKD|CNY|GBP|EUR|KRW)\b|'
            r'(?:Note\s+)?HK\$|(?-i:[A-Z]{3})\s+(?:thousand|million|billion)\b)[^\n]*)'
        )
        boundary = re.search(boundary_pattern, body[rows[0][2].end():])
        boundary_start = rows[0][2].end()+boundary.start() if boundary else None
        # The first supported label is not necessarily the first table row.
        # Validate the SAME context boundaries before it as after it. Only the
        # initial, explicit supported metadata lines may establish context;
        # metadata after an unrecognized numeric row cannot reset/inherit it.
        first_numeric_row = len(header)
        for line_match in re.finditer(r'(?m)^.*$', header):
            tokens = line_match[0].split()
            if len(tokens) >= 3 and all(re.fullmatch(NUMBER, token) for token in tokens[-2:]):
                first_numeric_row = line_match.start()
                break
        header_boundary_start = None
        for context in re.finditer(boundary_pattern, header):
            line = context[0].strip()
            known_metadata = (
                re.fullmatch(r'For the (year|six months|half year) ended \d{1,2}(?:st|nd|rd|th)?\s+\w+\s+20\d{2}', line, re.I)
                or re.fullmatch(r'(20\d{2})\s*(?:年度|年)?\s+(20\d{2})\s*(?:年度|年)?', line)
                or any(re.fullmatch(r'(?:Note\s+|附注\s+)?'+re.escape(marker)+r'\s+'+re.escape(marker), line, re.I) for marker in MONEY)
                or re.fullmatch(
                    r'(?:单位\s*[：:]?\s*(?:亿元|万元|千元|元)(?:\s*币种\s*[：:]?\s*人民币)?|'
                    r'币种\s*[：:]?\s*人民币(?:\s*单位\s*[：:]?\s*(?:亿元|万元|千元|元))?)', line)
            )
            if not known_metadata or context.start() >= first_numeric_row:
                header_boundary_start = statement.end()+context.start()
                break
        for label, metric, match in rows:
            locator = {'unit':'parsed-text', 'start':start+match.start(), 'end':start+match.end(),
                       'page':page['index'], 'quote_sha256':hashlib.sha256(match[0].encode()).hexdigest(),
                       'header_start':start+statement.start(), 'header_end':start+min(m.start() for _,_,m in rows)}
            reason = ('FILING_ENTITY_UNRESOLVED' if not entity else 'PERIOD_HEADER_AMBIGUOUS' if not periods
                      else 'CURRENCY_SCALE_AMBIGUOUS' if len(money) != 1 else None)
            changed_context = header_boundary_start if header_boundary_start is not None else boundary_start
            if changed_context is not None and match.start() >= changed_context:
                reason = reason or 'TABLE_CONTEXT_CHANGED_REVIEW_REQUIRED'
                locator['context_boundary_start'] = start+changed_context
            tokens = match[1].split()
            # Optional short note number is accepted only with an explicit Note column.
            if len(tokens) == 3 and re.search(r'\bNote\b|附注', header) and re.fullmatch(r'\d{1,2}|[一二三四五六七八九十]+', tokens[0]):
                tokens = tokens[1:]
            if len(tokens) != 2 or any(not re.fullmatch(NUMBER, token) for token in tokens):
                reason = reason or 'UNSUPPORTED_OR_AMBIGUOUS_VALUE_COLUMNS'
            if reason:
                candidates.append({'metric':metric,'label':label,'locator':locator,'status':'REVIEW_REQUIRED','reason':reason})
                continue
            currency, scale = next(iter(money))
            for column, (literal, (begin, finish)) in enumerate(zip(tokens, periods), 1):
                value = None if literal in {'—','–','-'} else Decimal(literal.replace(',','').replace('(','-').replace(')','')) * scale
                fact = _fact(metric=metric, concept='statement-label:'+label, value=value, unit=currency,
                    start=begin, end=finish, entity=entity, filing_id=filing_id, filed=filed, form=form,
                    locator=dict(locator, column=column, value_literal=literal), source_scale=scale,
                    statement_basis='consolidated primary income statement; explicit label and period header')
                fact.update(extraction_method='deterministic-explicit-statement/v1', extraction_review='NOT_REVIEWED',
                            source_label=label, allocation='FILING_ENTITY_ONLY')
                facts.append(fact)
    return {'schema':SCHEMA,'format':'regional-statement','filing_entity':entity,'facts':facts,'candidates':candidates,
            'missing':[{'metric':m,'status':'MISSING','reason':'NOT_EXTRACTED_FROM_SUPPORTED_EXPLICIT_STATEMENT'} for m in
                       ('marketing_expense','advertising_expense','revenue','retail_sales','occupancy','footfall')
                       if m not in {f['metric'] for f in facts}],
            'warnings':['Only explicit consolidated income-statement layouts are supported. Scans, notes, project tables and ambiguous headers require source-backed review.',
                        'Identifier and name are source assertions, not an independent legal identity verification. No group-to-brand allocation.']}


def opendart_request_config(*, corp_code, bsns_year, reprt_code, fs_div='CFS', credential_available=False):
    """Non-secret request descriptor for existing credential/Collector owners.

    Does not read, accept, persist or issue keys; credential availability is
    advisory until the configured credential owner supplies an authorized key.
    """
    if not re.fullmatch(r'\d{8}', str(corp_code)) or not re.fullmatch(r'20\d{2}', str(bsns_year)) or int(bsns_year) < 2015:
        raise ValueError('FINANCIAL_DART_REQUEST_INVALID')
    if reprt_code not in {'11011','11012','11013','11014'} or fs_div not in {'CFS','OFS'} or type(credential_available) is not bool:
        raise ValueError('FINANCIAL_DART_REQUEST_INVALID')
    return {'endpoint':'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json',
            'query':{'corp_code':corp_code,'bsns_year':str(bsns_year),'reprt_code':reprt_code},
            'selected_fs_div':fs_div,'credential_slot':'OPENDART_API_KEY', 'credential_query_parameter':'crtfc_key',
            'status':'CREDENTIAL_OWNER_REQUIRED' if credential_available else 'MISSING_CREDENTIAL',
            'key_in_payload':False,'live_acquisition':'NOT_VERIFIED',
            'note':'Do not persist the authenticated query URL; supply credentials only through the existing authorized credential owner.'}


def parse_opendart_json(raw, *, fs_div='CFS'):
    """Retained major-accounts response, never guess fiscal dates from year/code."""
    from .financial import _fact, SCHEMA, _date
    if not isinstance(fs_div, str) or fs_div not in {'CFS', 'OFS'}:
        raise ValueError('FINANCIAL_DART_BASIS_INVALID')
    if not isinstance(raw, bytes) or not 0 < len(raw) <= 8*1024*1024:
        raise ValueError('FINANCIAL_SOURCE_SIZE_INVALID')
    def pairs(items):
        out = {}
        for k,v in items:
            if k in out:
                raise ValueError('FINANCIAL_DUPLICATE_JSON_KEY')
            out[k] = v
        return out
    try:
        data = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('FINANCIAL_NUMBER_INVALID')))
    except (UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('FINANCIAL_DART_JSON_INVALID') from exc
    if not isinstance(data,dict) or not re.fullmatch(r'\d{3}', str(data.get('status',''))):
        raise ValueError('FINANCIAL_DART_RESPONSE_INVALID')
    code = data['status']
    result = {'schema':SCHEMA,'format':'opendart-json','filing_entity':None,'facts':[], 'candidates':[],
              'missing':[], 'warnings':['Explicit fiscal date ranges only; interim current and accumulated amounts are never conflated.'],
              'provider_status':code, 'selected_fs_div':fs_div,
              'excluded_basis_rows':0}
    if code != '000':
        states={'010':'INVALID_CREDENTIAL','011':'DISABLED_CREDENTIAL','012':'IP_NOT_ALLOWED',
                '013':'NO_DATA','014':'NO_FILE','020':'RATE_LIMITED','800':'MAINTENANCE','901':'EXPIRED_CREDENTIAL'}
        result['missing']=[{'status':'MISSING','reason':states.get(code,'PROVIDER_ERROR')}]
        return result
    entries=data.get('list')
    if not isinstance(entries,list) or len(entries)>10000:
        raise ValueError('FINANCIAL_DART_RESPONSE_INVALID')
    korean={'매출액':'revenue','영업수익':'revenue','광고선전비':'advertising_promotion_expense',
            '판매비와관리비':'selling_general_admin_expense','판매비 및 관리비':'selling_general_admin_expense'}
    for index,row in enumerate(entries):
        if not isinstance(row,dict):
            raise ValueError('FINANCIAL_DART_ROW_INVALID')
        label=row.get('account_nm','')
        metric=LABELS.get(label) or korean.get(label)
        if not metric or row.get('sj_div') not in {'IS','CIS'}:
            continue
        locator={'unit':'json-pointer','pointer':f'/list/{index}'}
        candidates=result['candidates']
        if (not re.fullmatch(r'\d{8}',str(row.get('corp_code',''))) or
                not re.fullmatch(r'\d{14}',str(row.get('rcept_no',''))) or row.get('fs_div') not in {'CFS','OFS'}):
            raise ValueError('FINANCIAL_DART_IDENTITY_INVALID')
        # Filter before emitting either facts or review candidates. Keep original
        # JSON indices; the retained source is never rewritten by selection.
        if row['fs_div'] != fs_div:
            result['excluded_basis_rows'] += 1
            continue
        dates=re.findall(r'(20\d{2})[.\-/](\d{2})[.\-/](\d{2})', str(row.get('thstrm_dt','')))
        reason=None
        if len(dates)!=2:
            reason='EXPLICIT_FISCAL_PERIOD_REQUIRED'
        else:
            begin,finish=['-'.join(d) for d in dates]
            _date(begin);_date(finish)
        # The provider binds thstrm_dt to the current term. It supplies no
        # independent accumulated-period dates in this endpoint. Never attach
        # cumulative money to a single-quarter date or infer dates from a code.
        field='thstrm_amount'
        if row.get('thstrm_add_amount') is not None:
            candidates.append({'metric':metric,'label':label,
                'locator':dict(locator,pointer=locator['pointer']+'/thstrm_add_amount'),
                'status':'REVIEW_REQUIRED','reason':'ACCUMULATED_PERIOD_NOT_EXPLICIT',
                'value_literal':row['thstrm_add_amount'],'amount_basis':'accumulated',
                'period_start':None,'period_end':None})
        literal=row.get(field)
        currency=row.get('currency')
        if not reason and (not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency)):
            reason='EXPLICIT_CURRENCY_REQUIRED'
        if not reason and (not isinstance(literal,str) or not re.fullmatch(NUMBER,literal.strip())):
            reason='CURRENT_TERM_AMOUNT_REQUIRED'
        if reason:
            candidates.append({'metric':metric,'label':label,'locator':locator,'status':'REVIEW_REQUIRED','reason':reason})
            continue
        literal=literal.strip()
        value=None if literal in {'—','–','-'} else Decimal(literal.replace(',','').replace('(','-').replace(')',''))
        entity={'name':row.get('corp_name'),'scheme':'OpenDART-CorpCode','identifier':row['corp_code']}
        fact=_fact(metric=metric,concept='opendart-account:'+label,value=value,unit=currency,start=begin,end=finish,
            entity=entity,filing_id=row['rcept_no'],filed=None,form=row.get('reprt_code'),
            locator=dict(locator,pointer=locator['pointer']+'/'+field),
            statement_basis=('consolidated' if row['fs_div']=='CFS' else 'separate')+' income statement; '+field,
            dimensions={'financial_statement_basis':row['fs_div']})
        fact.update(extraction_method='opendart-explicit-date-amount/v1',source_label=label,extraction_review='NOT_REVIEWED')
        result['facts'].append(fact)
    if not result['facts']:
        result['missing'].append({'status':'MISSING','reason':'NO_SUPPORTED_EXPLICIT_DATED_ACCOUNT'})
    return result
