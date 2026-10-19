"""Deterministic analysis of already-authorized SourceBrief records.

This pure function is NOT an authorization or evidence resolver. Its trusted
caller must freshly resolve scope, actor, bytes, rights and withdrawal state via
existing SourceBrief owners, including on reopen. Caller-supplied context and
matching IDs cannot establish permission or independent factual verification.
No external model, service, database, network or effect is used here.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from .taxonomy import normalize_dimension, is_valid_region


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _tokens(text):
    # Latin terms and overlapping CJK bigrams; lexical relevance is not quality.
    words = re.findall(r'[a-zA-Z0-9_]{2,}', text.casefold())
    for run in re.findall(r'[\u3400-\u9fff]+', text):
        words.extend(run[i:i + 2] for i in range(max(1, len(run) - 1)))
    return set(words)


def analyze_source_records(goal: str, records: list[dict], *, actor_id: str = '',
                           scope: dict | None = None, dimension: str = 'growth_opportunity',
                           regions: list[str] | None = None,
                           languages: list[str] | None = None,
                           hypothesis_reviews: list[dict] | None = None,
                           decision_brief: dict | None = None) -> dict:
    """Analyze caller-resolved records, retaining literal citations and unknowns.

    Identifiers are stable derivatives of exact input; no generated identifier
    is represented as source evidence. Confidence remains unknown (None).
    """
    if not isinstance(goal, str) or not isinstance(records, list) or not isinstance(actor_id, str):
        raise ValueError('INVALID_RESEARCH_INPUT')
    dimension = normalize_dimension(dimension)
    if regions is not None and (not isinstance(regions, list) or any(not is_valid_region(r) for r in regions)):
        raise ValueError('UNKNOWN_RESEARCH_REGION')
    if languages is not None and (not isinstance(languages, list) or any(l not in ('zh', 'en', 'ko') for l in languages)):
        raise ValueError('UNKNOWN_RESEARCH_LANGUAGE')
    if scope is not None and not isinstance(scope, dict):
        raise ValueError('INVALID_RESEARCH_SCOPE')
    findings, lineage, rejected, seen = [], [], [], {}
    terms = _tokens(goal)
    for index, raw in enumerate(records):
        if not isinstance(raw, dict):
            raise ValueError('INVALID_SOURCE_RECORD')
        row = deepcopy(raw)
        ref, sid = row.get('scope_evidence_ref'), row.get('source_id')
        if not isinstance(ref, str) or not ref.strip() or row.get('evidence_id') != ref or not isinstance(sid, str) or not sid.strip():
            rejected.append({'index': index, 'reason': 'missing_or_mismatched_source_binding'})
            continue
        artifact = row.get('source_artifact_ref')
        if artifact is not None and (row.get('source_type') == 'private_document' or ref.startswith('saved_work:')):
            artifact_hash = row.get('source_artifact_sha256')
            if (not isinstance(artifact, str) or not artifact.startswith('ART-')
                    or not isinstance(artifact_hash, str)
                    or not re.fullmatch(r'[0-9a-f]{64}', artifact_hash)
                    or ref != f'saved_work:{artifact}:{artifact_hash}'):
                rejected.append({'index': index, 'reason': 'mismatched_saved_work_binding'})
                continue
        if row.get('withdrawn') is True or row.get('revoked') is True:
            rejected.append({'index': index, 'reason': 'withdrawn_source'})
            continue
        if (row.get('actor_id') is not None and row['actor_id'] != actor_id) or (row.get('scope') is not None and row['scope'] != scope):
            rejected.append({'index': index, 'reason': 'context_mismatch'})
            continue
        excerpt = row.get('content_excerpt')
        if not isinstance(excerpt, str) or not excerpt.strip():
            rejected.append({'index': index, 'reason': 'missing_source_text'})
            continue
        fingerprint = _digest(row)
        if ref in seen:
            if seen[ref] != fingerprint:
                raise ValueError('CONFLICTING_SOURCE_REFERENCE')
            continue
        seen[ref] = fingerprint
        # Full-content hashes belong to the upstream resolver. Never compare a
        # truncated excerpt hash to a full document hash and claim verification.
        if row.get('excerpt_sha256') is not None and row['excerpt_sha256'] != hashlib.sha256(excerpt.encode()).hexdigest():
            raise ValueError('SOURCE_EXCERPT_HASH_MISMATCH')
        matches = sorted(terms & _tokens(excerpt))
        fid, lid = 'finding_' + fingerprint[:24], 'lineage_' + fingerprint[:24]
        finding = {'finding_id': fid, 'specialist_id': 'source_reader', 'content': excerpt,
                   'title': row.get('title'), 'claim_type': 'source_statement',
                   'evidence_refs': [ref], 'source_id': sid, 'lineage_id': lid,
                   'validated': False, 'fact_verified': False, 'confidence': None,
                   'rank_score': len(matches), 'rank_method': 'question_lexical_overlap',
                   'matched_terms': matches, 'excerpt_truncated': row.get('excerpt_truncated', row.get('truncated', 'UNKNOWN')),
                   'published_at': row.get('published_at') or row.get('publish_datetime'),
                   'content_hash': row.get('content_hash'), 'rights': row.get('rights', 'UNKNOWN')}
        findings.append(finding)
        lineage.append({'lineage_id': lid, 'evidence_id': ref, 'source': sid,
                        'lineage_steps': [sid, ref, fid], 'provenance': {
                            'method': 'literal_source_excerpt', 'record_sha256': fingerprint,
                            'content_hash': row.get('content_hash'), 'source_url': row.get('source_url'),
                            'source_artifact_ref': row.get('source_artifact_ref'),
                            'source_artifact_sha256': row.get('source_artifact_sha256'),
                            'published_at': finding['published_at'], 'captured_at': row.get('captured_at'),
                            'rights': finding['rights'], 'authorization_status': 'caller_resolved_not_reverified_here',
                            'fact_verified': False}})
    findings.sort(key=lambda f: (-f['rank_score'], f['finding_id']))
    refs = [f['evidence_refs'][0] for f in findings]
    hypotheses = []
    source_set_digest = _digest([goal, actor_id, scope, dimension, regions or [], languages or [],
                                 sorted(seen.items())])
    if findings and goal.strip():
        for f in findings:
            hypotheses.append({'hypothesis_id': 'hypothesis_' + _digest([source_set_digest, f['finding_id']])[:24],
                'claim_type': 'hypothesis', 'status': 'proposed', 'confidence': None,
                'finding_ids': [f['finding_id']], 'review_history': [],
                'source_set_sha256': source_set_digest,
                'statement': f'来源「{f["title"] or f["source_id"]}」中的材料是否足以支持研究问题「{goal.strip()}」？',
                'evidence_refs': f['evidence_refs'],
                'validation_needed': ['核对完整原文、时间、范围及独立反证。', '增长效果需实际观察与可比基线，不能由引文推定。']})
    transcript = _apply_reviews(hypotheses, findings, lineage, hypothesis_reviews)
    comparisons = [{'source_id': f['source_id'], 'evidence_refs': f['evidence_refs'],
                    'published_at': f['published_at'], 'question_term_matches': f['matched_terms'],
                    'numeric_literals': re.findall(r'(?<!\w)[+-]?\d+(?:[,.]\d+)*(?:%|％)?', f['content']),
                    'comparison_status': 'NOT_COMPARABLE_WITHOUT_MEASURE_DEFINITIONS',
                    'unit': None, 'currency': None, 'period': None, 'denominator': None}
                   for f in findings]
    status = 'research_draft' if findings and goal.strip() else 'needs_sources' if not findings else 'needs_question'
    result = {'schema': 'source_bound_research.v1', 'status': status, 'goal': goal,
              'dimension': dimension, 'regions': list(regions or []), 'languages': list(languages or []),
              'actor_id': actor_id, 'scope': deepcopy(scope), 'ranked_findings': findings,
              'hypotheses': hypotheses, 'comparisons': comparisons, 'evidence_lineage': lineage,
              'rejected_records': rejected, 'debate_transcript': transcript,
              'effective_hypotheses': [deepcopy(h) for h in hypotheses if h['support_eligible']],
              'effective_findings': [deepcopy(f) for f in findings if f['support_eligible']],
              'review_method': 'caller_resolved_human_disposition_state_machine',
              'source_set_sha256': source_set_digest,
              'review_status': ('not_reviewed' if not transcript else
                                'needs_revision' if any(not h['support_eligible'] for h in hypotheses)
                                else 'reviewed_unverified'),
              'metrics': {'input_record_count': len(records), 'usable_source_count': len(findings),
                          'source_reference_count': len(set(refs)), 'method': 'descriptive_input_counts_only',
                          'source_evidence_refs': refs, 'business_effect': None, 'quality_score': None,
                          'review_event_count': len(transcript),
                          'effective_hypothesis_count': sum(h['support_eligible'] for h in hypotheses),
                          'confidence': None, 'evaluation_status': 'NO_DATA' if not findings else 'NOT_EVALUATED'},
              'limitations': ['仅对已提供片段做来源声明摘录与词项匹配，引用不等于事实核验。',
                              '上游调用者必须实时核验actor、scope、源版本、使用权和撤回状态。',
                              '反证理由是人工声明；本函数只核对引用与状态迁移，不判定其语义真实或授予审批权。',
                              '未核实因果、总体趋势、当前法律效力或增长效果；数值未统一单位/币种/期间/分母。'],
              'permission_granted': False, 'canonical_promotion': False,
              'summary': (f'整理 {len(findings)} 条可引用来源片段；形成 {len(hypotheses)} 个待核验问题。未验证事实或业务效果。'
                          if findings else '缺少可引用的来源正文；需要已授权的SourceBrief材料，未生成证据或事实结论。')}
    if decision_brief is not None:
        result['decision_brief'] = _decision_brief(decision_brief, findings, lineage)
    result['research_id'] = 'research_' + _digest(result)[:24]
    return result


def _apply_reviews(hypotheses, findings, lineage, reviews):
    """Replay caller-resolved human opinions, never infer factual contradiction.

    Owner must bind reviewer identity/time and persistence/CAS externally. Here
    only the declared rationale and exact current source references are checked.
    Review order is intentional; a reinstatement does not verify any fact.
    """
    if reviews is None:
        reviews = []
    if not isinstance(reviews, list):
        raise ValueError('INVALID_HYPOTHESIS_REVIEWS')
    by_id = {h['hypothesis_id']: h for h in hypotheses}
    by_ref = {item['evidence_id']: item for item in lineage}
    transitions = {
        'proposed': {'challenge': 'challenged', 'reject': 'rejected'},
        'challenged': {'reject': 'rejected', 'reinstate': 'reinstated'},
        'rejected': {'reinstate': 'reinstated'},
        'reinstated': {'challenge': 'challenged', 'reject': 'rejected'},
    }
    transcript, ids = [], set()
    for position, raw in enumerate(reviews):
        if (not isinstance(raw, dict) or set(raw) != {
                'review_id', 'hypothesis_id', 'disposition', 'rationale', 'evidence_refs'}
                or any(not isinstance(raw.get(k), str) or not raw[k].strip()
                       for k in ('review_id', 'hypothesis_id', 'disposition', 'rationale'))):
            raise ValueError('INVALID_HYPOTHESIS_REVIEW')
        review = deepcopy(raw)
        if review['review_id'] in ids:
            raise ValueError('DUPLICATE_HYPOTHESIS_REVIEW')
        ids.add(review['review_id'])
        hypothesis = by_id.get(review['hypothesis_id'])
        if hypothesis is None:
            raise ValueError('STALE_OR_UNKNOWN_HYPOTHESIS')
        refs = review['evidence_refs']
        if (not isinstance(refs, list) or not refs or
                any(not isinstance(ref, str) or ref not in by_ref for ref in refs)
                or len(set(refs)) != len(refs)):
            raise ValueError('UNAVAILABLE_REVIEW_EVIDENCE')
        previous = hypothesis['status']
        state = transitions[previous].get(review['disposition'])
        if state is None:
            raise ValueError('INVALID_HYPOTHESIS_TRANSITION')
        bindings = [{'source_id': by_ref[ref]['source'], 'evidence_ref': ref,
                     'content_hash': by_ref[ref]['provenance']['content_hash'],
                     'record_sha256': by_ref[ref]['provenance']['record_sha256']}
                    for ref in refs]
        event = {**review, 'sequence': position + 1, 'previous_status': previous,
                 'status': state, 'resolved_source_bindings': bindings,
                 'claim_type': 'human_review_statement', 'fact_verified': False,
                 'method': 'declared_disposition_with_current_source_binding',
                 'authorization_status': 'caller_resolved_not_reverified_here',
                 'source_set_sha256': hypothesis['source_set_sha256']}
        hypothesis['status'] = state
        hypothesis['review_history'].append(deepcopy(event))
        transcript.append(event)
    finding_states = {}
    for h in hypotheses:
        h['review_status'] = h['status']
        h['support_eligible'] = h['status'] in ('proposed', 'reinstated')
        h['support_meaning'] = 'unverified_research_candidate_only'
        for fid in h['finding_ids']:
            finding_states[fid] = h
    for finding in findings:
        h = finding_states.get(finding['finding_id'])
        finding['support_eligible'] = bool(h and h['support_eligible'])
        finding['hypothesis_status'] = h['status'] if h else 'needs_question'
        finding['support_meaning'] = 'unverified_research_candidate_only'
    return transcript

def _decision_brief(spec, findings, lineage):
    """Bind operator-proposed alternatives to literal, currently usable excerpts.

    No product identity, semantic entailment, official relationship or image
    contents can be established by this deterministic text-bound comparison.
    """
    if (type(spec) is not dict or set(spec) != {'requirements', 'candidates', 'combinations'}
            or any(type(spec[k]) is not list for k in spec)
            or not 1 <= len(spec['requirements']) <= 20
            or len(spec['candidates']) > 30 or len(spec['combinations']) > 20):
        raise ValueError('DECISION_BRIEF_INPUT_INVALID')
    def label(value):
        return isinstance(value, str) and 0 < len(value.strip()) <= 300
    reqs = spec['requirements']
    if any(not label(r) for r in reqs) or len(set(reqs)) != len(reqs):
        raise ValueError('DECISION_REQUIREMENTS_INVALID')
    source_counts = {}
    for f in findings:
        source_counts[f['source_id']] = source_counts.get(f['source_id'], 0) + 1
    by_source = {f['source_id']: f for f in findings if f.get('support_eligible') and source_counts[f['source_id']] == 1}
    origins = {entry['evidence_id']: entry['provenance'] for entry in lineage}
    def anchor(value):
        if (type(value) is not dict or set(value) != {'source_id','start','end','quote'}
                or not isinstance(value['source_id'], str) or not value['source_id']
                or type(value['start']) is not int or type(value['end']) is not int
                or not 0 <= value['start'] < value['end']
                or not isinstance(value['quote'], str) or not 0 < len(value['quote']) <= 2000):
            raise ValueError('DECISION_EVIDENCE_ANCHOR_INVALID')
        f = by_source.get(value['source_id'])
        if f is None:
            return {'status':'SOURCE_UNAVAILABLE','source_id':value['source_id']}
        if (value['end'] > len(f['content'])
                or f['content'][value['start']:value['end']] != value['quote']):
            raise ValueError('DECISION_EVIDENCE_QUOTE_MISMATCH')
        return {**deepcopy(value), 'status':'SOURCE_STATEMENT_PRESENT',
                'offset_unit':'unicode_codepoint_in_resolved_excerpt',
                'evidence_refs':f['evidence_refs'], 'finding_id':f['finding_id'],
                'provenance':deepcopy(origins[f['evidence_refs'][0]]),
                'semantic_entailment':'NOT_VERIFIED', 'fact_verified':False}
    candidates, ids = [], set()
    for c in spec['candidates']:
        if (type(c) is not dict or set(c) != {'id','label','evidence','requirement_evidence','images'}
                or not label(c['id']) or c['id'] in ids or not label(c['label'])
                or type(c['requirement_evidence']) is not dict
                or set(c['requirement_evidence']) - set(reqs)
                or type(c['images']) is not list or len(c['images']) > 8):
            raise ValueError('DECISION_CANDIDATE_INVALID')
        ids.add(c['id'])
        evidence = anchor(c['evidence'])
        matched = {r:anchor(v) for r,v in c['requirement_evidence'].items()}
        images = []
        for image in c['images']:
            if type(image) is not dict or set(image) != {'url','evidence'}:
                raise ValueError('DECISION_IMAGE_REFERENCE_INVALID')
            from urllib.parse import urlsplit
            if not isinstance(image['url'], str) or len(image['url']) > 2000:
                raise ValueError('DECISION_IMAGE_REFERENCE_INVALID')
            url = urlsplit(image['url'])
            if url.scheme not in {'https','http'} or not url.hostname or url.username or url.password:
                raise ValueError('DECISION_IMAGE_REFERENCE_INVALID')
            binding = anchor(image['evidence'])
            if image['url'] not in image['evidence']['quote']:
                raise ValueError('DECISION_IMAGE_URL_NOT_IN_SOURCE')
            images.append({'source_url': image['url'] if binding['status']=='SOURCE_STATEMENT_PRESENT' else None,
                           'evidence':binding, 'media_status':'NOT_READ',
                           'image_identity':'NOT_VERIFIED', 'reuse_rights':'UNKNOWN'})
        unknown = [r for r in reqs if matched.get(r,{}).get('status') != 'SOURCE_STATEMENT_PRESENT']
        candidates.append({'candidate_id':c['id'],'label':c['label'],
            'label_origin':'operator_proposal','identity_status':'NOT_VERIFIED',
            'evidence':evidence,'requirement_evidence':matched,'unknown_requirements':unknown,
            'images':images, 'selection_status':'PROPOSED' if evidence['status']=='SOURCE_STATEMENT_PRESENT' else 'UNAVAILABLE',
            'requirement_satisfaction':'NOT_VERIFIED','official_status':'NOT_VERIFIED'})
    combinations=[]
    for combo in spec['combinations']:
        if (type(combo) is not dict or set(combo) - {'label','candidate_ids','evidence','relationship_type'}
                or not {'label','candidate_ids','evidence'} <= set(combo)
                or not isinstance(combo.get('relationship_type','combined_proposal'), str)
                or combo.get('relationship_type','combined_proposal') not in {'official_look','editorial_styling','recommended_combo','sellable_bundle','related_case','combined_proposal'}
                or not label(combo['label']) or type(combo['candidate_ids']) is not list
                or not 2 <= len(combo['candidate_ids']) <= 10
                or any(not isinstance(i,str) or i not in ids for i in combo['candidate_ids'])
                or len(set(combo['candidate_ids'])) != len(combo['candidate_ids'])):
            raise ValueError('DECISION_COMBINATION_INVALID')
        binding=anchor(combo['evidence'])
        members_available=all(c['selection_status']=='PROPOSED' for c in candidates if c['candidate_id'] in combo['candidate_ids'])
        combinations.append({'label':combo['label'],'candidate_ids':list(combo['candidate_ids']),
            'requested_relationship_type':combo.get('relationship_type','combined_proposal'),
            'relationship_type_verified':False,
            'relation_evidence':binding,'relation_status':'PROPOSAL_WITH_SOURCE_QUOTE' if binding['status']=='SOURCE_STATEMENT_PRESENT' and members_available else 'UNKNOWN',
            'official_set_status':'NOT_VERIFIED','compatibility':'NOT_VERIFIED'})
    available=sum(c['selection_status']=='PROPOSED' for c in candidates)
    return {'schema':'source_bound_decision.v1','input':deepcopy(spec),
            'status':'needs_sources' if not available else 'partial_draft',
            'requirements':list(reqs),'candidates':candidates,'combinations':combinations,
            'available_candidate_count':available,'selected_candidate_ids':[],
            'coverage':'PARTIAL' if available else 'UNKNOWN','business_execution_authorized':False,
            'next_steps':['核对候选身份、条件含义与原文完整性。','沿原媒体Owner读取图片并核对版本与用途权利。','选择后沿原业务审批或创作任务继续；本草案不执行外部动作。']}


def decision_brief_markdown(analysis):
    """Render a useful comparison appendix without auto-embedding remote images."""
    from lumenis.shared.reporting.operational_brief import _markdown_text
    brief=analysis.get('decision_brief') if isinstance(analysis,dict) else None
    if not brief:
        return ''
    text=['需求与候选比较（待核验草案）', '覆盖：'+brief['coverage']]
    for r in brief['requirements']:
        text.append('需求：'+_markdown_text(r))
    for c in brief['candidates']:
        text.append('候选：'+_markdown_text(c['label'])+'；'+c['selection_status'])
        text.append('尚无对应引文：'+('、'.join(_markdown_text(r) for r in c['unknown_requirements']) or '均有引文，仍需核对是否满足条件'))
        for binding in [c['evidence'],*c['requirement_evidence'].values()]:
            if binding['status']=='SOURCE_STATEMENT_PRESENT':
                text.append('来源 '+_markdown_text(binding['source_id'])+'：'+_markdown_text(binding['quote']))
        for image in c['images']:
            text.append('图片来源待读取：'+_markdown_text(image['source_url'] or '来源当前不可用'))
    for combo in brief['combinations']:
        text.append('组合：'+_markdown_text(combo['label'])+'；'+combo['relation_status']+'；官方成套未核验')
    text.extend(brief['next_steps'])
    return '\n\n'.join(text)
