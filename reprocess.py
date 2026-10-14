"""历史数据再处理与跨平台事件聚合。"""

import hashlib
import json
import logging
import re
from collections.abc import Mapping
from datetime import datetime

import ai_analyzer
import database as db
import intelligence

logger = logging.getLogger(__name__)

def _event_key(title, hint, topics, event_date='', *, scope=None):
    """Build a deterministic, scope-separated key from source-derived signals."""
    text = ' '.join([str(hint or ''), str(title or ''), ' '.join(str(x) for x in (topics or []))])
    text = re.sub(r'20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?', '', text)
    text = re.sub(r'[“”"「」【】\[\]（）()]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().lower()
    # Explicit event hints take precedence. Without one, use the observed title
    # plus observed topics; never inject a default Subject, venue or location.
    label = str(hint or '').strip() or text
    label = re.sub(r'\s+', ' ', label).strip()[:120]
    bucket = 'unknown-date'
    if event_date:
        try:
            from datetime import datetime as _dt
            day = _dt.strptime(str(event_date)[:10], '%Y-%m-%d').date()
            bucket = str(day.toordinal() // 14)
        except (TypeError, ValueError):
            bucket = 'unknown-date'
    identity = {
        'scope': db._event_scope_token(_normalize_scope(scope, allow_global=False)),
        'label': label,
        'topics': [str(item).strip().lower() for item in (topics or []) if str(item).strip()][:3],
        'time_bucket': bucket,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                                       separators=(',', ':')).encode('utf-8')).hexdigest()[:24]
    return f"{identity['scope']}.{digest}"

def _normalize_scope(scope, *, allow_global=True):
    """Accept only an explicit CTH Subject/BMP BrandFocus scope."""
    if not isinstance(scope, Mapping):
        raise ValueError('SCOPE_REQUIRED')  # noqa: TRY004 - preserve the public scope error code.
    domain = str(scope.get('domain_id') or '').strip().lower()
    if domain in {'bmp', 'zbmp'}:
        domain, product = 'zbmp', 'ZBMP'
    elif domain in {'cth'}:
        domain, product = 'cth', 'CTH'
    else:
        raise ValueError('SCOPE_DOMAIN_INVALID')
    subject_id = scope.get('subject_id')
    brand_focus_id = scope.get('brand_focus_id')
    global_scope = scope.get('global_scope') is True
    if subject_id is not None and (not isinstance(subject_id, str) or not subject_id or subject_id != subject_id.strip()):
        raise ValueError('SCOPE_MISMATCH')
    if brand_focus_id is not None and (not isinstance(brand_focus_id, str) or not brand_focus_id or brand_focus_id != brand_focus_id.strip()):
        raise ValueError('SCOPE_MISMATCH')
    if global_scope:
        if not allow_global or subject_id or brand_focus_id:
            raise ValueError('FOCUS_SCOPE_REQUIRED')
    elif domain == 'cth':
        if not subject_id or brand_focus_id:
            raise ValueError('SCOPE_MISMATCH')
    elif not brand_focus_id or subject_id:
        raise ValueError('SCOPE_MISMATCH')
    return {'domain_id': domain, 'product_id': product, 'subject_id': subject_id,
            'brand_focus_id': brand_focus_id, 'global_scope': global_scope}


def _canonical_source_ids(scope, *, source_table='notes', source_type='note', limit=5000,
                          source_ids=None, connection=None):
    """Return IDs only after revalidating each candidate through Canonical scope."""
    from canonical_data import list_scoped_canonical

    exact = _normalize_scope(scope)
    limit = max(1, min(int(limit), 5000))
    where = ["product_id=?", "domain_id=?", "scope_status='VERIFIED'",
             "source_table=?", "source_type=?", "NULLIF(TRIM(source_id),'') IS NOT NULL"]
    params = [exact['product_id'], exact['domain_id'], source_table, source_type]
    column = 'subject_id' if exact['domain_id'] == 'cth' else 'brand_focus_id'
    other_column = 'brand_focus_id' if column == 'subject_id' else 'subject_id'
    if not exact['global_scope']:
        where.append(f"{column}=?")
        params.append(exact[column])
    else:
        where.append(f"NULLIF(TRIM({column}),'') IS NOT NULL")
    where.append(f"COALESCE({other_column},'')=''")
    if source_ids is not None:
        if not isinstance(source_ids, (list, tuple)) or not source_ids or len(source_ids) > 100:
            raise ValueError('CANONICAL_SOURCE_IDS_INVALID')
        normalized_ids = []
        for source_id in source_ids:
            if not isinstance(source_id, str) or not source_id or source_id != source_id.strip():
                raise ValueError('CANONICAL_SOURCE_IDS_INVALID')
            if source_id not in normalized_ids:
                normalized_ids.append(source_id)
        where.append("source_id IN (" + ",".join("?" for _ in normalized_ids) + ")")
        params.extend(normalized_ids)
    def read_ids(conn):
        rows = conn.execute(
            "SELECT source_id FROM canonical_data WHERE " + " AND ".join(where)
            + " ORDER BY captured_at DESC, canonical_id ASC LIMIT ?", tuple(params + [limit])
        ).fetchall()
        candidates = list(dict.fromkeys(str(row['source_id']) for row in rows if row['source_id']))
        verified = []
        for start in range(0, len(candidates), 100):
            batch = candidates[start:start + 100]
            result = list_scoped_canonical(
                conn, product_id=exact['product_id'], subject_id=exact['subject_id'],
                brand_focus_id=exact['brand_focus_id'], source_ids=batch,
                limit=len(batch), source_level=True,
            )
            verified.extend(
                str(record['source_id']) for record in result['records']
                if record.get('source_table') == source_table
                and record.get('source_type') == source_type
                and record.get('scope_status') == 'VERIFIED'
            )
        return list(dict.fromkeys(verified))
    if connection is not None:
        return read_ids(connection)
    with db.get_db() as conn:
        verified = read_ids(conn)
    return list(dict.fromkeys(verified))


def _scoped_note(row, scope):
    exact = _normalize_scope(scope)
    note = db.note_to_dict(row)
    if not isinstance(note, dict):
        raise ValueError('CANONICAL_NOTE_NOT_FOUND')  # noqa: TRY004 - preserve the public result contract.
    if (note.get('product_id') != exact['product_id']
            or note.get('domain_id') != exact['domain_id']
            or str(note.get('scope_status') or '').upper() != 'VERIFIED'):
        raise ValueError('CANONICAL_NOTE_SCOPE_MISMATCH')
    if exact['global_scope']:
        if exact['domain_id'] == 'cth':
            if not note.get('subject_id') or note.get('brand_focus_id'):
                raise ValueError('CANONICAL_NOTE_SCOPE_MISMATCH')
        elif not note.get('brand_focus_id') or note.get('subject_id'):
            raise ValueError('CANONICAL_NOTE_SCOPE_MISMATCH')
    elif (note.get('subject_id') or None) != exact['subject_id'] or (note.get('brand_focus_id') or None) != exact['brand_focus_id']:
        raise ValueError('CANONICAL_NOTE_SCOPE_MISMATCH')
    return note


def _load_scoped_note(note_id, scope):
    exact = _normalize_scope(scope)
    ids = _canonical_source_ids(exact, source_ids=[note_id], limit=1)
    if note_id not in ids:
        raise ValueError('CANONICAL_NOTE_SCOPE_MISMATCH')
    with db.get_db() as conn:
        row = conn.execute('SELECT * FROM notes WHERE note_id=?', (note_id,)).fetchone()
    if row is None:
        raise ValueError('CANONICAL_NOTE_NOT_FOUND')
    return _scoped_note(row, exact)


def _write_scoped_analysis(note, scope, analysis):
    exact = _normalize_scope(scope)
    sentiment = str(analysis.get('sentiment') or 'unknown')
    risk_level = str(analysis.get('risk_level') or 'unknown')
    if sentiment not in {'positive', 'neutral', 'negative', 'unknown'}:
        sentiment = 'unknown'
    if risk_level not in {'low', 'medium', 'high', 'critical', 'unknown'}:
        risk_level = 'unknown'
    sentiment_score = analysis.get('sentiment_score') if sentiment != 'unknown' else None
    risk_score = analysis.get('risk_score') if risk_level != 'unknown' else None
    focus_column = 'subject_id' if exact['domain_id'] == 'cth' else 'brand_focus_id'
    other_column = 'brand_focus_id' if focus_column == 'subject_id' else 'subject_id'
    focus_value = note.get(focus_column) if exact['global_scope'] else exact[focus_column]
    if not isinstance(focus_value, str) or not focus_value:
        raise ValueError('CANONICAL_NOTE_SCOPE_MISMATCH')
    evidence_ref = note.get('scope_evidence_ref')
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ValueError('CANONICAL_NOTE_EVIDENCE_REQUIRED')
    with db.get_db() as conn:
        if note['note_id'] not in _canonical_source_ids(
                exact, source_ids=[note['note_id']], limit=1, connection=conn):
            raise ValueError('CANONICAL_NOTE_SCOPE_CHANGED')
        cursor = conn.execute(
            "UPDATE notes SET sentiment=?, sentiment_score=?, risk_level=?, risk_score=?, "
            "summary=?, topics=?, ai_provider='rule', ai_analyzed_at=datetime('now','localtime') "
            f"WHERE note_id=? AND product_id=? AND domain_id=? AND scope_status='VERIFIED' "
            f"AND {focus_column}=? AND COALESCE({other_column},'')='' AND scope_evidence_ref=?",
            (sentiment, sentiment_score, risk_level, risk_score,
             str(analysis.get('summary') or ''), json.dumps(analysis.get('topics') or [], ensure_ascii=False),
             note['note_id'], exact['product_id'], exact['domain_id'], focus_value,
             evidence_ref),
        )
        if cursor.rowcount != 1:
            raise ValueError('CANONICAL_NOTE_SCOPE_CHANGED')
        history = conn.execute(
            "INSERT INTO note_review_history(note_id,old_relevance,new_relevance,old_sentiment,new_sentiment,"
            "old_risk,new_risk,reason,provider) "
            "SELECT ?,?,?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM notes "
            "WHERE note_id=? AND product_id=? AND domain_id=? AND scope_status='VERIFIED' "
            f"AND {focus_column}=? AND COALESCE({other_column},'')='' AND scope_evidence_ref=?)",
            (note['note_id'], note.get('relevance_status') or 'unknown',
             note.get('relevance_status') or 'unknown', note.get('sentiment') or 'unknown',
             sentiment, note.get('risk_level') or 'unknown', risk_level,
             'canonical_scope_verified; deterministic_analysis', 'rule',
             note['note_id'], exact['product_id'], exact['domain_id'], focus_value, evidence_ref),
        )
        if history.rowcount != 1:
            raise ValueError('CANONICAL_NOTE_SCOPE_CHANGED')


def analyze_note_row(row, translate=False, *, scope=None):
    note = _scoped_note(row, scope)
    _load_scoped_note(note['note_id'], scope)
    analysis = ai_analyzer.analyze_note(note, provider='rule')
    # Canonical scope proves the data's admitted identity, not a model's factual claim.
    analysis['is_official'] = note.get('is_official', 0)
    _write_scoped_analysis(note, scope, analysis)
    return 'processed'


def reprocess_notes(limit=5000, translate=False, *, scope=None):
    try:
        exact = _normalize_scope(scope)
    except ValueError as exc:
        return {'processed': 0, 'errors': 0, 'status': str(exc)}
    try:
        normalized_limit = min(max(int(limit), 1), 5000)
        ids = _canonical_source_ids(exact, limit=normalized_limit)
        rows = []
        for start in range(0, len(ids), 900):
            batch = ids[start:start + 900]
            rows.extend(db.get_notes_for_canonical_source_ids(batch, limit=len(batch)))
    except Exception as exc:  # noqa: BLE001 - convert repository read failures into an explicit scoped error.
        return {'processed': 0, 'errors': 0, 'status': 'CANONICAL_SCOPE_READ_FAILED',
                'error_type': type(exc).__name__}
    counts = {'processed': 0, 'errors': 0, 'status': 'COMPLETED'}
    for row in rows:
        try:
            _scoped_note(row, exact)
            analyze_note_row(row, translate=translate, scope=exact)
            counts['processed'] += 1
        except Exception as exc:  # noqa: BLE001 - isolate per-record failures and continue remaining scoped records.
            counts['errors'] += 1
            logger.warning('Scoped note analysis failed for a source ID (%s)', type(exc).__name__)
    if counts['errors']:
        counts['status'] = 'PARTIAL'
    return counts


def discover_web(limit=120, translate=False, *, queries=None, scope=None, actor=None):
    """Web acquisition is Collector-owned; never write a parallel raw/web table here."""
    try:
        exact = _normalize_scope(scope)
    except ValueError as exc:
        return {'fetched': 0, 'accepted': 0, 'status': str(exc)}
    if not isinstance(queries, (list, tuple)) or not queries:
        return {'fetched': 0, 'accepted': 0, 'status': 'QUERY_REQUIRED'}
    if actor is None:
        return {'fetched': 0, 'accepted': 0, 'status': 'ACTOR_REQUIRED'}
    from lumenis.system.collector.adapters.secondary_collection import collect_search
    results = []
    for query in queries[:20]:
        if not isinstance(query, str) or not query.strip():
            continue
        result = collect_search('web_rss', query.strip(), max_results=min(max(int(limit), 1), 20),
                                operator='human_ui', scope=exact, actor=actor)
        results.append(result)
        if str(result.get('status') or '').upper() in {
            'BLOCKED', 'NEED_VERIFY', 'SESSION_EXPIRED', 'RATE_LIMITED', 'COOLING_DOWN',
            'APPROVAL_REQUIRED', 'PERMISSION_UNAVAILABLE', 'SCOPE_UNAUTHORIZED',
        }:
            break
    return {'fetched': sum(int(item.get('raw_count') or 0) for item in results),
            'accepted': sum(int(item.get('imported') or 0) for item in results),
            'status': 'COMPLETED' if results and all(item.get('ok') is True for item in results) else 'PARTIAL',
            'results': results}


def _source_topics(row):
    value = row.get('topics') or []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            value = [item.strip() for item in value.split(',') if item.strip()]
    if not isinstance(value, (list, tuple)):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))[:30]


def _source_publication_time(row):
    if row.get('source_table') == 'notes':
        return str(row.get('publish_datetime') or row.get('publish_date') or '').strip()
    return str(row.get('published_at') or '').strip()


def build_cross_platform_events(limit=100, *, scope=None):
    """Aggregate admitted source rows into deterministic, Evidence-bound events.

    The caller supplies a server-authorized CTH/BMP scope. A GLOBAL request is
    partitioned by its registered Subject/BrandFocus before any aggregation;
    event sources are never combined across focuses. The database owner
    rechecks each source's signed scope Evidence and Canonical projection both
    when reading and immediately before persistence.
    """
    requested = _normalize_scope(scope, allow_global=True)
    try:
        limit = min(max(int(limit), 1), 500)
    except (TypeError, ValueError):
        raise ValueError('EVENT_LIMIT_INVALID') from None
    from canonical_metrics import sentiment_count

    source_read = db.get_scoped_event_source_rows(
        requested, limit=min(5000, max(100, limit * 20)),
        source_types=('note', 'web_mention'),
    )
    source_rows = source_read['sources']
    rejected_source_count = source_read['rejected_count']
    if source_read['truncated']:
        # Never replace a previously complete event/mention set with a
        # truncated view of the authorized source population.
        return {
            'events': [],
            'source_count': len(source_rows),
            'rejected_source_count': rejected_source_count,
            'truncated': True,
            'status': 'PARTIAL',
            'persistence_status': 'NOT_RUN_INCOMPLETE_SOURCE_READ',
        }
    focus_field = 'subject_id' if requested['domain_id'] == 'cth' else 'brand_focus_id'
    partitions = {}
    for source in source_rows:
        focus_id = source.get(focus_field)
        if not isinstance(focus_id, str) or not focus_id.strip():
            continue
        exact = {
            'domain_id': requested['domain_id'], 'product_id': requested['product_id'],
            'subject_id': focus_id if focus_field == 'subject_id' else None,
            'brand_focus_id': focus_id if focus_field == 'brand_focus_id' else None,
            'global_scope': False,
        }
        token = db._event_scope_token(exact)
        partitions.setdefault(token, (exact, []))[1].append(source)
    if not requested['global_scope']:
        partitions.setdefault(db._event_scope_token(requested), (requested, []))

    groups = []
    for exact, sources in partitions.values():
        grouped = {}
        for source in sources:
            topics = _source_topics(source)
            title = str(source.get('title') or '').strip()
            hint = str(source.get('event_hint') or '').strip()
            if not hint and not title:
                continue
            published = _source_publication_time(source)
            key = _event_key(title, hint, topics, published, scope=exact)
            source_type = source['source_type']
            source_id = str(source['source_id'])
            grouped.setdefault(key, {})[(source_type, source_id)] = source

        for key, values in grouped.items():
            records = sorted(values.values(), key=lambda item: (item['source_type'], item['source_id']))
            # event_mentions is an existing bounded relationship owner; split only
            # oversized clusters into deterministic chunks without dropping sources.
            for part, offset in enumerate(range(0, len(records), 500), start=1):
                chunk = records[offset:offset + 500]
                scoped_key = key if len(records) <= 500 else f'{key}.{part:03d}'
                groups.append((exact, scoped_key, chunk))
    groups.sort(key=lambda item: (
        max((_source_publication_time(row) for row in item[2]), default=''), item[0]['domain_id'],
        item[0]['subject_id'] or item[0]['brand_focus_id'] or '', item[1],
    ), reverse=True)

    created = []
    for exact, event_key, records in groups[:limit]:
        topics = list(dict.fromkeys(topic for row in records for topic in _source_topics(row)))[:8]
        titles = [str(row.get('title') or '').strip() for row in records if str(row.get('title') or '').strip()]
        hints = [str(row.get('event_hint') or '').strip() for row in records if str(row.get('event_hint') or '').strip()]
        title = (hints[0] if hints else titles[0] if titles else '')[:120]
        published = sorted(value for value in (_source_publication_time(row) for row in records) if value)
        sentiments = sentiment_count(records)
        known_risk_levels = [str(row.get('risk_level') or '').strip().lower() for row in records
                             if str(row.get('risk_level') or '').strip().lower() in
                             {'low', 'medium', 'high', 'critical'}]
        level_rank = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        risk_level = max(known_risk_levels, key=lambda value: level_rank[value]) if known_risk_levels else 'unknown'
        numeric_risks = []
        for row in records:
            value = row.get('risk_score')
            if type(value) in (int, float) and value >= 0:
                numeric_risks.append(int(value))
        risk_score = max(numeric_risks) if numeric_risks else None
        negative_count = sentiments.get('negative') if sentiments.get('known') else None
        risk_reason = (
            f"规则汇总：{len(records)}条已核验来源中，"
            f"{len(known_risk_levels)}条提供了可识别风险等级；"
            f"负面情绪计数={negative_count if negative_count is not None else '未知'}。"
        )
        event = {
            'event_key': event_key,
            'title': title,
            'summary': f"由{len(records)}条同一事件提示或标题分组的来源记录形成；分组本身不构成事实认定。",
            'fact_status': 'unconfirmed',
            'impact': 'unknown',
            'risk_reason': risk_reason,
            'recommended_action': '核对原始来源后，由当前业务负责人记录判断与处置结果。',
            'first_seen': published[0] if published else '',
            'last_seen': published[-1] if published else '',
            'event_date': published[0][:10] if published else '',
            'risk_level': risk_level,
            'risk_score': risk_score,
            'status': 'active',
            'keywords': topics,
            'translations': {},
        }
        mentions = [{
            'source_type': row['source_type'],
            'source_id': str(row['source_id']),
            'source_platform': str(row.get('source_platform') or row.get('source_adapter') or row['source_type']),
        } for row in records]
        event_id = db.upsert_event(event, scope=exact, mentions=mentions)
        created.append({'event_id': event_id, **event, 'sources': mentions})
    return {'events': created, 'source_count': len(source_rows),
            'rejected_source_count': rejected_source_count,
            'truncated': source_read['truncated'],
            'status': 'PARTIAL' if source_read['truncated'] or rejected_source_count else 'COMPLETED'}


# === Legacy event entry ======================================================
# Kept as a source-compatible name only. The old writer has no scoped Evidence
# contract and must not create cross-Subject events from an implicit reference.
def aggregate_events(limit: int = 100, *, scope=None):
    """Preserve the compatibility name while requiring the event owner's scope contract."""
    return build_cross_platform_events(limit=limit, scope=scope)


def full_refresh(limit=5000, web_limit=120, translate=False, *, web_queries=None, scope=None, actor=None):
    try:
        exact = _normalize_scope(scope)
    except ValueError as exc:
        return {'status': str(exc), 'notes': {'processed': 0, 'errors': 0, 'status': str(exc)},
                'web': {'fetched': 0, 'accepted': 0, 'status': str(exc)},
                'events': {'status': 'NOT_RUN'}, 'ai_enabled': intelligence.ai_enabled()}
    notes = reprocess_notes(limit, translate, scope=exact)
    web = discover_web(web_limit, translate, queries=web_queries, scope=exact, actor=actor)
    try:
        build_cross_platform_events(scope=exact)
        events = {'status': 'COMPLETED'}
    except ValueError as exc:
        events = {'status': 'BLOCKED', 'code': str(exc)}
    overall = 'COMPLETED' if (notes.get('status') == 'COMPLETED'
                               and web.get('status') == 'COMPLETED'
                               and events.get('status') == 'COMPLETED') else 'PARTIAL'
    return {'status': overall,
            'backup': None, 'notes': notes, 'web': web, 'events': events,
            'ai_enabled': intelligence.ai_enabled()}


def run_event_pipeline(limit=100, alert_notes=None, *, scope=None):
    """Run the existing deterministic scoped event aggregation path."""
    result = {'events': 0, 'graph_imported': 0, 'relations': {}, 'alerts': [], 'errors': []}
    try:
        exact = _normalize_scope(scope, allow_global=False)
    except ValueError as exc:
        result.update({'status': 'BLOCKED', 'code': str(exc)})
        return result
    try:
        aggregation = aggregate_events(limit=limit, scope=exact)
        result['events'] = len(aggregation['events'])
    except (ValueError, RuntimeError) as exc:
        result.update({'status': 'BLOCKED', 'code': str(exc)})
        return result
    # EventGraph has no exact scope argument today. Do not import all scopes into
    # its unscoped graph as a side effect of an otherwise scoped user request.
    result['graph_status'] = 'NOT_RUN_SCOPE_CONTRACT_REQUIRED'
    if alert_notes is not None:
        result['alerts_status'] = 'NOT_RUN_CALLER_NOTES_REQUIRE_SCOPE_VERIFICATION'
    result['status'] = aggregation.get('status', 'COMPLETED')
    result['rejected_source_count'] = aggregation.get('rejected_source_count', 0)
    result['truncated'] = aggregation.get('truncated', False)
    return result


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--limit',type=int,default=5000)
    ap.add_argument('--web-limit',type=int,default=120)
    ap.add_argument('--translate',action='store_true')
    args=ap.parse_args()
    print(json.dumps(full_refresh(args.limit,args.web_limit,args.translate),ensure_ascii=False,indent=2))
