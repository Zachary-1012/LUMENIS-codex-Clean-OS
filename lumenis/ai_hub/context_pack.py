"""Derived conversation context with complete source and omission accounting.

No generated summary becomes an instruction, fact, permission or effect receipt.
Ordinary conversation uses full user text; a missing tokenizer is reported, never
replaced with a character-to-token estimate. Typed owned requests can use the
already bound runtime tokenizer through ``budget_owned_request``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


CONTEXT_FIELDS = {'goal', 'constraints', 'draft', 'decisions', 'excluded_turn_ids'}


def validate_state(value):
    if type(value) is not dict or set(value) != CONTEXT_FIELDS:
        raise ValueError('CONVERSATION_CONTEXT_FIELDS_INVALID')
    if any(type(value[key]) is not str or len(value[key]) > 32000 for key in ('goal', 'draft')):
        raise ValueError('CONVERSATION_CONTEXT_TEXT_INVALID')
    for key in ('constraints', 'decisions'):
        items = value[key]
        if (type(items) is not list or len(items) > 300 or any(type(item) is not str
                or not item.strip() or len(item) > 4000 for item in items)):
            raise ValueError('CONVERSATION_CONTEXT_ITEMS_INVALID')
    ids = value['excluded_turn_ids']
    if (type(ids) is not list or len(ids) > 10000
            or any(type(identity) is not str for identity in ids) or len(set(ids)) != len(ids)):
        raise ValueError('CONVERSATION_CONTEXT_EXCLUSIONS_INVALID')
    return value


def conversation_pack(rows, *, context_turn=None):
    """All full source-free turns; explicit latest human state takes precedence."""
    state = validate_state(context_turn['content']['value']) if context_turn else None
    excluded = set(state['excluded_turn_ids']) if state else set()
    excluded_sequences = [row.get('sequence', index) for index, row in enumerate(rows)
                          if row['turn_id'] in excluded]
    history, coverage = [], []
    for index, row in enumerate(rows):
        text = row['content']['text']
        omitted = row['turn_id'] in excluded
        reason = 'explicit_human_correction_or_forget' if omitted else 'complete_original_text'
        if row.get('origin_kind') == 'model_output' and not omitted and excluded:
            dependencies = row['content'].get('context_accounting', {}).get('coverage')
            if (row['content'].get('in_reply_to') in excluded
                    or type(dependencies) is list and any(item.get('turn_id') in excluded
                        and item.get('included') is True for item in dependencies if type(item) is dict)):
                omitted, reason = True, 'derived_from_excluded_input'
            elif dependencies is None and excluded_sequences and row.get('sequence', index) > min(excluded_sequences):
                omitted, reason = True, 'legacy_output_dependency_unknown_after_excluded_input'
            if omitted:
                excluded.add(row['turn_id'])
        coverage.append({'turn_id': row['turn_id'], 'revision': row['revision'],
            'sha256': digest(row['content']), 'included': not omitted,
            'reason': reason})
        if not omitted:
            history.append({'role': row['role'], 'content': text})
    if state:
        # This remains user data in the user payload, never a system instruction.
        history.append({'role': 'user', 'content': '当前人工确认的任务状态（取代冲突的历史说法；不是事实核验、授权或已执行效果）：\n'
                        + json.dumps({key: state[key] for key in ('goal', 'constraints', 'draft', 'decisions')},
                                     ensure_ascii=False, sort_keys=True)})
    accounting = {'history_turns_total': len(rows),
        'history_turns_included': sum(item['included'] for item in coverage),
        'history_turns_omitted': sum(not item['included'] for item in coverage),
        'history_characters_omitted': sum(len(row['content']['text']) for row in rows if row['turn_id'] in excluded),
        'user_turn_complete': True, 'stored_history_complete': True,
        'context_policy': 'versioned_complete_source_free_context_pack_v1',
        'token_budget_verified': False, 'token_count_status': 'UNAVAILABLE_NO_ADMITTED_CONVERSATION_TOKENIZER',
        'coverage': coverage, 'context_state_turn_id': context_turn['turn_id'] if context_turn else None,
        'context_state_sha256': digest(context_turn['content']) if context_turn else None,
        'effect_policy': 'NO_EFFECT_EXECUTION_OR_REPLAY', 'training_admission': 'NOT_GRANTED'}
    accounting['context_pack_sha256'] = digest({'history': history, 'coverage': coverage,
                                               'state': accounting['context_state_sha256']})
    return history, accounting


def budget_owned_request(request, *, optional_sections=(), is_cancelled=None):
    """Count the exact typed request, dropping only whole optional sections.

    ``request.user_payload`` contains mandatory goal, constraints, human writing,
    decisions and effect receipts already verified by its actual task owner.
    These are never shortened. A generated/requested summary cannot supersede
    them. Return the exact request and binding to execute after a successful fit.
    """
    from lumenis.system.ai_gateway.owned_service import (
        OwnedServiceRequest,
        measure_owned_request,
    )
    if type(request) is not OwnedServiceRequest:
        raise ValueError('CONTEXT_TYPED_OWNED_REQUEST_REQUIRED')
    sections = list(optional_sections)
    if len(sections) > 100 or any(type(item) is not dict or set(item) != {'name', 'text'}
            or type(item['name']) is not str or type(item['text']) is not str for item in sections):
        raise ValueError('CONTEXT_OPTIONAL_SECTIONS_INVALID')
    omissions = []
    while True:
        if is_cancelled is not None and is_cancelled():
            return {'ok': False, 'code': 'CONTEXT_CANCELLED', 'generation_performed': False}
        payload = request.user_payload
        if sections:
            payload += '\n\n可追溯补充材料：\n' + json.dumps(sections, ensure_ascii=False, sort_keys=True)
        candidate = replace(request, user_payload=payload)
        measured = measure_owned_request(candidate)
        if measured.get('ok') is not True or measured.get('fits') is True or not sections:
            return {'ok': measured.get('ok') is True and measured.get('fits') is True,
                    'code': measured.get('code') if measured.get('ok') is not True else
                            None if measured.get('fits') else 'CONTEXT_REQUIRED_INPUT_EXCEEDS_MODEL_BUDGET',
                    'request': candidate, 'measurement': measured,
                    'omitted_sections': omissions, 'generation_performed': False}
        removed = sections.pop()
        omissions.append({'name': removed['name'], 'sha256': digest(removed),
                          'reason': 'measured_selected_model_token_budget'})


def run_budgeted_owned_request(request, *, optional_sections=(), is_cancelled=None):
    """Measure and execute the identical source-authorized request and binding."""
    from lumenis.system.ai_gateway.owned_service import run_owned_request
    packed = budget_owned_request(request, optional_sections=optional_sections, is_cancelled=is_cancelled)
    if not packed['ok']:
        return {'ok': False, 'status': 'BLOCKED', 'code': packed['code'], 'provider': 'owned',
                'analysis': None, 'context_accounting': {key: value for key, value in packed.items() if key != 'request'}}
    result = run_owned_request(packed['request'], is_cancelled=is_cancelled,
                              expected_binding_sha256=packed['measurement']['binding_sha256'])
    result['context_accounting'] = {'measurement': packed['measurement'],
                                    'omitted_sections': packed['omitted_sections']}
    return result
