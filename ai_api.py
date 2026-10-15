# -*- coding: utf-8 -*-
"""LUMENIS AI API Blueprint.

AI runtime is owned by SYSTEM AI Gateway. Learning endpoints consume Shared
Learning. The historical ungrounded "AI web search" route is kept only as an
explicit retired compatibility surface and cannot create canonical events.
"""
from __future__ import annotations
import re
import threading
from flask import Blueprint, jsonify, request

bp = Blueprint("ai_api", __name__)

# 依赖模块（与 app.py 保持一致）
from lumenis.system.ai_gateway import core as intelligence
import ai_governance
import ai_filter
from lumenis.system.ai_gateway import channel as ai_channel
from lumenis.shared.learning import operations as learning_operations
import function_registry
import database as db


def _owned_runtime_status():
    try:
        status = intelligence.owned_inference_status()
    except Exception:
        status = None
    if not isinstance(status, dict):
        return {
            'provider': 'owned', 'available': False, 'service_binding': 'NOT_BOUND',
            'state': 'UNAVAILABLE', 'reason': 'OWNED_RUNTIME_STATUS_UNAVAILABLE',
        }
    return status


def _run_owned_analysis(text, analysis_type, note_id=None):
    try:
        result = intelligence.run_owned_analysis(
            text=text, analysis_type=analysis_type, note_id=note_id,
        )
    except Exception:
        return {
            'ok': False, 'status': 'ERROR', 'code': 'OWNED_ANALYSIS_EXECUTION_FAILED',
            'provider': 'owned', 'analysis': None,
        }
    if not isinstance(result, dict):
        return {
            'ok': False, 'status': 'ERROR', 'code': 'OWNED_ANALYSIS_RESULT_INVALID',
            'provider': 'owned', 'analysis': None,
        }
    return result


def _owned_result_complete(result):
    if not isinstance(result, dict) or result.get('ok') is not True:
        return False
    if result.get('status') != 'COMPLETED' or result.get('provider') != 'owned':
        return False
    analysis = result.get('analysis')
    return bool(analysis.strip()) if isinstance(analysis, str) else bool(analysis)


def _owned_result_text(result):
    analysis = result.get('analysis') if isinstance(result, dict) else None
    if isinstance(analysis, str):
        return analysis.strip()
    if isinstance(analysis, dict):
        for key in ('reply', 'summary', 'text', 'content'):
            value = analysis.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _owned_failure_response(result, **fields):
    status = result.get('status') if isinstance(result, dict) else 'ERROR'
    code = result.get('code') if isinstance(result, dict) else None
    if not isinstance(code, str) or not code:
        code = 'OWNED_ANALYSIS_NOT_COMPLETED'
    return jsonify({
        **fields, 'ok': False, 'status': status or 'ERROR', 'code': code,
        'provider': 'owned', 'analysis': None,
    }), 503 if status == 'UNAVAILABLE' else 502


@bp.route('/api/ai/status')
def api_ai_status():
    from lumenis.system.ai_gateway import user_api_adapter
    if user_api_adapter.is_selected():
        runtime = user_api_adapter.status()
        return jsonify({'ok': True, 'enabled': runtime['configured'],
                        'status': runtime['state'], 'provider': 'user_api',
                        'interface': 'system-ai-gateway', 'runtime': runtime,
                        'service_binding': runtime['service_binding'],
                        'fallback_allowed': False, 'providers': ['user_api']})
    status = _owned_runtime_status()
    return jsonify({
        'ok': True, 'enabled': status.get('available') is True,
        'status': status.get('state') or 'UNAVAILABLE',
        'provider': 'owned', 'interface': 'system-ai-gateway',
        'service_binding': status.get('service_binding') or 'NOT_BOUND',
        'fallback_allowed': False, 'providers': ['owned_gateway'], 'runtime': status,
    })

@bp.route('/api/ai/test', methods=['POST'])
def api_ai_test():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'JSON_OBJECT_REQUIRED'}), 400
    text = data.get('text')
    if not isinstance(text, str) or not text.strip():
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_TEXT_REQUIRED'}), 400
    if len(text) > 4000:
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_TEXT_TOO_LARGE'}), 413
    # AI 治理：额度检查
    allowed, quota = ai_governance._usage_tracker.check_quota()
    if not allowed:
        return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota}), 429
    # AI 治理：脱敏
    desensitized_text, mapping = ai_governance.desensitize_text(text)
    result = _run_owned_analysis(desensitized_text, 'conversation')
    owned_reply = _owned_result_text(result)
    if not _owned_result_complete(result) or not owned_reply:
        ai_governance.record_ai_call(
            'ai/test', provider='owned', success=False, prompt_tokens=0,
            completion_tokens=0, total_tokens=0,
        )
        return _owned_failure_response(result, reply=None)
    # AI 治理：回传补回实体
    reply = ai_governance.restore_text(owned_reply, mapping)
    # AI 治理：记录使用统计
    ai_governance.record_ai_call('ai/test', prompt_tokens=len(text)//2,
                                   completion_tokens=len(reply)//2,
                                   total_tokens=(len(text)+len(reply))//2,
                                   provider='owned', success=True)
    # AI 治理：输出标记
    marked = ai_governance.mark_ai_output(
        {'ok': True, 'reply': reply, 'provider': 'owned', 'status': 'COMPLETED'},
        provider='owned', endpoint='ai/test',
    )
    return jsonify(marked)

# Legacy `/api/ark/*` URLs remain as compatibility routes; all execution goes
# through the SYSTEM Gateway and the owned runtime, never a provider-specific API.

@bp.route('/api/ark/status')
def api_ark_status():
    """Legacy status shape backed by the owned runtime status only."""
    status = _owned_runtime_status()
    return jsonify({
        'ok': True, 'enabled': status.get('available') is True,
        'status': status.get('state') or 'UNAVAILABLE', 'provider': 'owned',
        'model': status.get('model_id'), 'runtime': 'owned',
        'service_binding': status.get('service_binding') or 'NOT_BOUND',
        'detail': status.get('reason') or 'OWNED_RUNTIME_NOT_BOUND',
    })

@bp.route('/api/ark/chat', methods=['POST'])
def api_ark_chat():
    """Legacy chat contract routed to owned inference without local fallback."""
    try:
        data = request.get_json(silent=True) or {}
        message = str(data.get('message') or data.get('text') or '').strip()
        if not message:
            return jsonify({'ok': False, 'error': '消息不能为空'}), 400
        if len(message) > 4000:
            return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'MESSAGE_TOO_LARGE'}), 413
        system_prompt = data.get('system_prompt')
        if system_prompt is not None and not isinstance(system_prompt, str):
            return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'SYSTEM_PROMPT_INVALID'}), 400
        if isinstance(system_prompt, str) and len(system_prompt) > 4000:
            return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'SYSTEM_PROMPT_TOO_LARGE'}), 413
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'status': 'BUDGET_BLOCKED',
                            'code': 'AI_DAILY_QUOTA_EXCEEDED', 'quota': quota}), 429
        # AI 治理：脱敏
        desensitized_msg, mapping = ai_governance.desensitize_text(message)
        prompt = ((system_prompt or 'LUMENIS assistant') + '\n\n' + desensitized_msg)
        result = _run_owned_analysis(prompt, 'conversation', data.get('note_id'))
        owned_reply = _owned_result_text(result)
        if not _owned_result_complete(result) or not owned_reply:
            ai_governance.record_ai_call('ark/chat', provider='owned', success=False)
            if _owned_result_complete(result):
                result = {'status': 'ERROR', 'code': 'OWNED_CHAT_RESULT_INVALID'}
            failed, status_code = _owned_failure_response(result, reply=None)
            return failed, status_code
        reply = ai_governance.restore_text(owned_reply, mapping)
        # AI 治理：记录使用统计
        ai_governance.record_ai_call('ark/chat', prompt_tokens=len(message)//2,
                                       completion_tokens=len(reply)//2,
                                       total_tokens=(len(message)+len(reply))//2,
                                       provider='owned', success=True)
        # AI 治理：输出标记
        result = ai_governance.mark_ai_output(
            {'ok': True, 'status': 'COMPLETED', 'reply': reply, 'provider': 'owned',
             'fallback': False, 'desensitized': bool(mapping)},
            provider='owned', endpoint='ark/chat')
        return jsonify(result)
    except Exception as e:
        ai_governance.record_ai_call('ark/chat', provider='owned', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/ark/sentiment', methods=['POST'])
def api_ark_sentiment():
    """Legacy sentiment contract backed only by owned inference."""
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text') or data.get('content') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': '文本不能为空'}), 400
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota}), 429
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        result = _run_owned_analysis(desensitized_text, 'sentiment', data.get('note_id'))
        if not _owned_result_complete(result) or not isinstance(result.get('analysis'), dict):
            ai_governance.record_ai_call('ark/sentiment', provider='owned', success=False)
            return _owned_failure_response(
                result if not _owned_result_complete(result) else {
                    'status': 'ERROR', 'code': 'OWNED_SENTIMENT_RESULT_INVALID',
                },
                sentiment=None, label=None, summary=None, keywords=None,
            )
        analysis = dict(result['analysis'])
        sentiment = analysis.get('sentiment')
        label = analysis.get('label')
        keywords = analysis.get('keywords')
        if (type(sentiment) is not int or sentiment not in {-1, 0, 1}
                or label not in {'positive', 'neutral', 'negative'}
                or not isinstance(analysis.get('summary'), str)
                or not isinstance(keywords, list)
                or any(not isinstance(item, str) or not item.strip() for item in keywords)):
            ai_governance.record_ai_call('ark/sentiment', provider='owned', success=False)
            return _owned_failure_response(
                {'status': 'ERROR', 'code': 'OWNED_SENTIMENT_RESULT_INVALID'},
                sentiment=None, label=None, summary=None, keywords=None,
            )
        if isinstance(analysis.get('summary'), str):
            analysis['summary'] = ai_governance.restore_text(analysis['summary'], mapping)
        ai_governance.record_ai_call('ark/sentiment', prompt_tokens=len(text)//2,
                                       completion_tokens=len(str(analysis.get('summary') or ''))//2,
                                       total_tokens=(len(text)+len(str(analysis.get('summary') or '')))//2,
                                       provider='owned', success=True)
        marked = ai_governance.mark_ai_output(
            {'ok': True, 'status': 'COMPLETED', 'sentiment': analysis.get('sentiment'),
             'label': analysis.get('label'), 'summary': analysis.get('summary'),
             'keywords': analysis.get('keywords'), 'provider': 'owned', 'fallback': False,
             'desensitized': bool(mapping)},
            provider='owned', endpoint='ark/sentiment')
        return jsonify(marked)
    except Exception as e:
        ai_governance.record_ai_call('ark/sentiment', provider='owned', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/ark/summary', methods=['POST'])
def api_ark_summary():
    """Legacy summary contract backed only by owned inference."""
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text') or data.get('content') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': '文本不能为空'}), 400
        max_length = data.get('max_length', 200)
        try:
            max_length = int(max_length)
        except Exception:
            max_length = 200
        if not 1 <= max_length <= 2000:
            return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'MAX_LENGTH_INVALID'}), 400
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'status': 'BUDGET_BLOCKED',
                            'code': 'AI_DAILY_QUOTA_EXCEEDED', 'quota': quota}), 429
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        result = _run_owned_analysis(desensitized_text, 'summary', data.get('note_id'))
        summary = _owned_result_text(result)
        if not _owned_result_complete(result) or not summary:
            ai_governance.record_ai_call('ark/summary', provider='owned', success=False)
            return _owned_failure_response(
                result if not _owned_result_complete(result) else {
                    'status': 'ERROR', 'code': 'OWNED_SUMMARY_RESULT_INVALID',
                }, summary=None,
            )
        summary = ai_governance.restore_text(summary[:max_length], mapping)
        ai_governance.record_ai_call('ark/summary', prompt_tokens=len(text)//2,
                                       completion_tokens=len(summary)//2,
                                       total_tokens=(len(text)+len(summary))//2,
                                       provider='owned', success=True)
        result = ai_governance.mark_ai_output(
            {'ok': True, 'status': 'COMPLETED', 'summary': summary,
             'provider': 'owned', 'desensitized': bool(mapping),
             'quota_remaining': quota['call_remaining']},
            provider='owned', endpoint='ark/summary')
        return jsonify(result)
    except Exception as e:
        ai_governance.record_ai_call('ark/summary', provider='owned', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/ark/keywords', methods=['POST'])
def api_ark_keywords():
    """Legacy keyword contract backed only by owned inference."""
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text') or data.get('content') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': '文本不能为空'}), 400
        num_keywords = data.get('num_keywords', 10)
        try:
            num_keywords = int(num_keywords)
        except Exception:
            num_keywords = 10
        if not 1 <= num_keywords <= 30:
            return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'NUM_KEYWORDS_INVALID'}), 400
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'status': 'BUDGET_BLOCKED',
                            'code': 'AI_DAILY_QUOTA_EXCEEDED', 'quota': quota}), 429
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        result = _run_owned_analysis(desensitized_text, 'keywords', data.get('note_id'))
        analysis = result.get('analysis') if isinstance(result, dict) else None
        keywords = analysis.get('keywords') if isinstance(analysis, dict) else None
        if (not _owned_result_complete(result) or not isinstance(keywords, list)
                or not keywords or any(not isinstance(item, str) or not item.strip() for item in keywords)):
            ai_governance.record_ai_call('ark/keywords', provider='owned', success=False)
            return _owned_failure_response(
                result if not _owned_result_complete(result) else {
                    'status': 'ERROR', 'code': 'OWNED_KEYWORD_RESULT_INVALID',
                }, keywords=None,
            )
        restored_keywords = [ai_governance.restore_text(item, mapping) for item in keywords[:num_keywords]]
        ai_governance.record_ai_call('ark/keywords', prompt_tokens=len(text)//2,
                                       completion_tokens=sum(len(item) for item in restored_keywords)//2,
                                       total_tokens=(len(text)+sum(len(item) for item in restored_keywords))//2,
                                       provider='owned', success=True)
        return jsonify(ai_governance.mark_ai_output(
            {'ok': True, 'status': 'COMPLETED', 'keywords': restored_keywords,
             'provider': 'owned', 'fallback': False, 'desensitized': bool(mapping),
             'quota_remaining': quota['call_remaining']},
            provider='owned', endpoint='ark/keywords',
        ))
    except Exception as e:
        ai_governance.record_ai_call('ark/keywords', provider='owned', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== 采集器自动化 API ==========

@bp.route('/api/ai-learning/status')
def api_ai_learning_status():
    """Shared Learning operation-pattern status."""
    try:
        return jsonify({'ok': True, **learning_operations.get_learning_status()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/web-sentiment/search', methods=['POST'])
def api_web_sentiment_search():
    """Retired unsafe compatibility route.

    The old implementation asked an LLM to impersonate web retrieval and then
    wrote generated rows into web_events. That violates Evidence/Canonical Data
    ownership. Keep the route explicit rather than silently fabricating search.
    """
    data = request.get_json(silent=True) or {}
    result = {
        'ok': False,
        'status': 'RETIRED_UNGROUNDED',
        'error': '未接入可验证外部检索证据源；旧 AI 模拟全网检索已退役，请使用生产采集器与 Evidence-backed 数据源。',
        'results': [],
        'total': 0,
        'requested': {
            'keywords': data.get('keywords'),
            'platform': data.get('platform', 'all'),
            'limit': data.get('limit', 20),
        },
        'production_truth_write': False,
    }
    return jsonify(result), 410

@bp.route('/api/web-sentiment/history')
def api_web_sentiment_history():
    """Return only governed historical operation records, never invented events."""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = learning_operations.get_operation_history(
            operation_type='web_sentiment_search', limit=limit)
        return jsonify({
            'ok': True,
            'status': 'RETIRED_UNGROUNDED',
            'history': history,
            'production_truth_write': False,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ========== 全网舆情案例数据库 API ==========

@bp.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'JSON_OBJECT_REQUIRED'}), 400
    text = data.get('message', data.get('text'))
    if not isinstance(text, str) or not text.strip():
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'MESSAGE_REQUIRED'}), 400
    if len(text) > 4000:
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'MESSAGE_TOO_LARGE'}), 413
    from lumenis.system.ai_gateway import user_api_adapter
    if user_api_adapter.is_selected():
        from lumenis.ai_hub import service
        result = service.chat(text, history=data.get('history'))
        return jsonify(result), 200 if result['ok'] else 503
    functions = function_registry.search_function_metadata(text, 5)
    context = (
        '可用功能入口（仅路由信息，不代表当前业务数据）：'
        + '、'.join(item.get('label', '') for item in functions)
        if functions else '未匹配到功能入口；本次对话未读取业务记录或案例资料。'
    )
    history = data.get('history') or []
    if not isinstance(history, list):
        history = []
    history_text = []
    for item in history[-6:]:
        if isinstance(item, dict):
            role = '用户' if item.get('role') in ('user', 'human') else 'LUMENIS'
            content = str(item.get('content') or '')[:800]
            if content:
                history_text.append(f'{role}：{content}')
    prompt = (
        '你是 LUMENIS 的业务助手。当前聊天没有绑定逐来源核验的 SourceUse 操作；'
        '功能目录仅用于导航，不是业务数据。区分用户描述与已核验事实；'
        '不要声称读取、核验或引用当前品牌、案例、笔记或事件数据，也不得编造业务数字。\n\n'
        f'用户问题：{text.strip()}\n功能路由提示（非业务数据）：{context}'
    )
    if history_text:
        prompt += '\n最近对话：\n' + '\n'.join(history_text)
    if len(prompt) > 24000:
        return jsonify({'ok': False, 'status': 'INVALID_INPUT', 'code': 'CONTEXT_TOO_LARGE'}), 413
    result = _run_owned_analysis(prompt, 'conversation', data.get('note_id'))
    runtime = _owned_runtime_status()
    if not _owned_result_complete(result):
        failure, status_code = _owned_failure_response(
            result, reply=None, context=context, ai_status=runtime,
        )
        return failure, status_code
    reply = _owned_result_text(result)
    if not reply:
        return _owned_failure_response(
            {'status': 'ERROR', 'code': 'OWNED_CHAT_RESULT_INVALID'},
            reply=None, context=context, ai_status=runtime,
        )
    return jsonify({
        'ok': True, 'status': 'COMPLETED', 'reply': reply,
        'provider': 'owned', 'ai_status': runtime, 'context': context,
    })

@bp.route('/api/ai/providers')
def api_ai_providers_v570():
    from lumenis.system.ai_gateway import user_api_adapter
    if user_api_adapter.is_selected():
        return jsonify({'ok': True, 'provider': 'user_api',
                        'external': user_api_adapter.status(),
                        'owned': _owned_runtime_status(), 'fallback_allowed': False})
    status = _owned_runtime_status()
    return jsonify({
        'ok': True, 'provider': 'owned', 'owned': status,
        'local': {'available': False, 'provider': 'retired', 'status': 'DISABLED'},
        'remote': [], 'fallback_allowed': False,
    })

@bp.route('/api/ai/analyze-v570',methods=['POST'])
def api_ai_analyze_v570():
    """Legacy response shape backed by the owned Gateway, with honest status."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'JSON_OBJECT_REQUIRED',
            'text': '', 'context': '', 'provider': 'owned', 'analysis': None,
            'error': 'JSON_OBJECT_REQUIRED',
        }), 400

    text = data.get('text')
    context = data.get('context', '')
    note_id = data.get('note_id')
    if (not isinstance(text, str) or not text.strip()
            or not isinstance(context, str)
            or (note_id is not None and not isinstance(note_id, (str, int)))):
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_INPUT_INVALID',
            'text': text if isinstance(text, str) else '',
            'context': context if isinstance(context, str) else '',
            'provider': 'owned', 'analysis': None, 'error': 'ANALYSIS_INPUT_INVALID',
        }), 400
    if len(text) > 12000 or len(context) > 12000:
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_TEXT_TOO_LARGE',
            'text': text, 'context': context, 'provider': 'owned',
            'analysis': None, 'error': 'ANALYSIS_TEXT_TOO_LARGE',
        }), 413

    source_text = text.strip()
    if context.strip():
        source_text += '\n\nContext supplied with the source:\n' + context.strip()
    try:
        result = intelligence.run_owned_analysis(
            text=source_text, analysis_type='summary', note_id=note_id,
        )
    except Exception:
        result = None
    if (isinstance(result, dict) and result.get('ok') is True
            and result.get('status') == 'COMPLETED' and result.get('analysis')):
        return jsonify({
            'ok': True, 'status': 'COMPLETED', 'code': None,
            'text': text, 'context': context, 'provider': 'owned',
            'analysis': result['analysis'], 'error': '',
        })

    status = result.get('status') if isinstance(result, dict) else 'ERROR'
    code = result.get('code') if isinstance(result, dict) else None
    if not isinstance(code, str) or not code:
        code = 'OWNED_ANALYSIS_NOT_COMPLETED'
    http_status = 503 if status == 'UNAVAILABLE' else 502
    return jsonify({
        'ok': False, 'status': status or 'ERROR', 'code': code,
        'text': text, 'context': context, 'provider': 'owned',
        'analysis': None, 'error': code,
    }), http_status

@bp.route('/api/ai-filter/stats')
def api_ai_filter_stats():
    return jsonify({'ok':True,'stats':db.get_filter_stats()})

@bp.route('/api/ai-filter/run', methods=['POST'])
def api_ai_filter_run():
    data = request.get_json(silent=True) or {}
    limit = max(1, min(2000, int(data.get('limit', 500))))
    def worker():
        try:
            ai_filter.run_filter_batch(limit)
        except Exception as e:
            print('[AIFilter] 运行失败:', e)
    threading.Thread(target=worker, daemon=True).start()
    return jsonify({'ok':True,'message':f'AI过滤任务已启动，处理 {limit} 条','limit':limit})

@bp.route('/api/ai-filter/cleanup', methods=['POST'])
def api_ai_filter_cleanup():
    data = request.get_json(silent=True) or {}
    execute = bool(data.get('execute', False))
    result = ai_filter.cleanup_rejected_notes(dry_run=not execute)
    return jsonify({'ok':True,'result':result})

@bp.route('/api/ai/channel-health', methods=['GET'])
def api_ai_channel_health():
    """云端 AI 通道多层稳固层健康快照（熔断/心跳/可用性），供前端小 icon 与 24h 监控"""
    try:
        from lumenis.system.ai_gateway import core as _intel
        _st = _intel.ai_status()
        _h = ai_channel.channel_health(provider=_st.get('provider',''), model=_st.get('model',''))
        return jsonify({'ok': True, 'enabled': bool(_st.get('enabled')), **{'health': _h}})
    except Exception as _e:
        return jsonify({'ok': False, 'error': str(_e)}), 500

# ===== v5.8.0 新增API =====

# ===== 小红书 P0 生产编排 API（双子星库 Contract） =====

@bp.route('/api/ai/analyze', methods=['POST'])
def api_ai_analyze_v580():
    """Analyze supplied source text through the owned SYSTEM AI Gateway only."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'JSON_OBJECT_REQUIRED',
            'provider': 'owned', 'analysis': None,
        }), 400

    note_id = data.get('note_id')
    if note_id is not None and not isinstance(note_id, (str, int)):
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'NOTE_ID_INVALID',
            'provider': 'owned', 'note_id': None, 'analysis': None,
        }), 400

    analysis_type = data.get('type', 'summary')
    if not isinstance(analysis_type, str) or analysis_type not in {'summary', 'sentiment', 'risk', 'event'}:
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_TYPE_UNSUPPORTED',
            'provider': 'owned', 'note_id': note_id, 'analysis': None,
        }), 400

    text = data.get('text')
    if text is None:
        text = data.get('content', data.get('source_text'))
    if not isinstance(text, str) or not text.strip():
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_TEXT_REQUIRED',
            'provider': 'owned', 'note_id': note_id, 'analysis': None,
        }), 400
    if len(text) > 12000:
        return jsonify({
            'ok': False, 'status': 'INVALID_INPUT', 'code': 'ANALYSIS_TEXT_TOO_LARGE',
            'provider': 'owned', 'note_id': note_id, 'analysis': None,
        }), 413

    result = intelligence.run_owned_analysis(
        text=text.strip(), analysis_type=analysis_type, note_id=note_id,
    )
    if not isinstance(result, dict):
        return jsonify({
            'ok': False, 'status': 'ERROR', 'code': 'OWNED_GATEWAY_INVALID_RESPONSE',
            'provider': 'owned', 'note_id': note_id, 'analysis': None,
        }), 502

    if (result.get('ok') is True and result.get('status') == 'COMPLETED'
            and isinstance(result.get('analysis'), dict) and result['analysis']):
        return jsonify({
            'ok': True, 'status': 'COMPLETED', 'provider': 'owned',
            'note_id': note_id, 'analysis': result['analysis'],
        })

    status = result.get('status') or 'ERROR'
    http_status = 503 if status == 'UNAVAILABLE' else 502
    return jsonify({
        'ok': False, 'status': status,
        'code': result.get('code') or 'OWNED_ANALYSIS_NOT_COMPLETED',
        'provider': 'owned', 'note_id': note_id, 'analysis': None,
    }), http_status


@bp.route('/api/ai-learning/optimization/<operation_type>')
def api_ai_learning_optimization(operation_type):
    """Return evidence-bound optimization hints from Shared Learning."""
    try:
        suggestion = learning_operations.get_optimization_suggestion(operation_type)
        return jsonify({
            'ok': True,
            'operation_type': operation_type,
            'suggestion': suggestion,
            'owner': 'lumenis.shared.learning.operations',
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# AI Task Engine API（Production-Ready）
# 调用链：User → Task → Parser → Intent → Agent → Skill → Permission → Execution → Evidence → Verification → Trace
# ═══════════════════════════════════════════════════════════════

def _get_engine():
    """延迟获取 TaskEngine 单例。"""
    from ai_task_engine import get_task_engine
    return get_task_engine()


def _source_brief_task_local_access_allowed():
    """Open only source-bound tasks for the existing sealed local workspace."""
    from lumenis.shared.reporting.source_brief_job import get_source_brief_job
    from lumenis.system.security.permission import resolve_local_workspace_principal
    actor = resolve_local_workspace_principal(module='reports', action='read')
    if actor is None:
        return False
    try:
        if request.endpoint == 'ai_api.api_ai_tasks' and request.method == 'POST':
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or 'task' in body or 'skill_id' in body:
                return False
            context = body.get('context')
        elif request.endpoint in {'ai_api.api_ai_tasks_get', 'ai_api.api_ai_tasks_run'}:
            expected_method = 'POST' if request.endpoint.endswith('_run') else 'GET'
            if request.method != expected_method:
                return False
            task = _get_engine().get_task((request.view_args or {}).get('task_id', ''))
            if not task or task.get('created_by') != actor.principal_ref:
                return False
            context = task.get('context')
        else:
            return False
        if (not isinstance(context, dict) or context.get('analysis_operation') not in {'source_statistics', 'openai_math'}
                or not isinstance(context.get('source_brief_job_id'), str)):
            return False
        from experience_runtime import _source_brief_context
        from lumenis.shared.reporting.source_brief_job import _scope_material
        current_ref, _, material = _source_brief_context('read')
        if current_ref != actor.principal_ref:
            return False
        get_source_brief_job(context['source_brief_job_id'], actor_id=current_ref, actor=actor,
                             expected_scope=_scope_material(**material))
        return True
    except (ValueError, PermissionError, LookupError, RuntimeError):
        return False


@bp.before_request
def _scoped_report_task_boundary():
    """Report tasks require Reporting's live actor and exact scope checks."""
    path = request.path
    if (path.startswith('/api/ai/tasks/rbrief_')
            or (path == '/api/ai/trace' and request.args.get('task_id', '').startswith('rbrief_'))):
        return jsonify({'ok': False, 'code': 'REPORT_TASK_SCOPED_ROUTE_REQUIRED'}), 403
    task_id = (request.view_args or {}).get('task_id')
    if task_id:
        engine = _get_engine()
        task = engine.get_task(task_id)
        if task and (task.get('context') or {}).get('source_brief_job_id'):
            try:
                engine._read_analysis_source(task)
                if task.get('status') == 'succeeded':
                    stored = task.get('result')
                    output = stored.get('output') if isinstance(stored, dict) else None
                    valid, _ = engine._verify_owner_outcome(task, output)
                    if not valid:
                        return jsonify({'ok': False, 'code': 'ANALYSIS_OWNER_READBACK_NOT_VERIFIED'}), 409
            except (ValueError, PermissionError, LookupError, RuntimeError):
                return jsonify({'ok': False, 'code': 'ANALYSIS_SOURCE_ACCESS_DENIED'}), 403


@bp.route('/api/ai/tasks', methods=['GET', 'POST'])
def api_ai_tasks():
    """Single compatibility entry for TaskEngine and Skill Execution tasks."""
    if request.method == 'GET':
        return api_ai_tasks_list()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'ok': False, 'code': 'JSON_OBJECT_REQUIRED'}), 400
    if 'task' in data or 'skill_id' in data:
        return api_ai_skill_execution_create(data)
    return api_ai_tasks_create(data)


def api_ai_tasks_create(data=None):
    """创建 AI Task。
    Body: {"input": "用户自然语言", "context": {...}, "created_by": "user"}
    """
    try:
        if data is None:
            data = request.get_json(silent=True) or {}
        user_input = data.get('input', '')
        context = data.get('context', {})
        created_by = data.get('created_by', 'system')
        if not isinstance(context, dict):
            return jsonify({'ok': False, 'code': 'TASK_CONTEXT_OBJECT_REQUIRED'}), 400
        if 'source_brief_job_id' in context:
            if context.get('analysis_operation') not in {'source_statistics', 'openai_math'}:
                return jsonify({'ok': False, 'code': 'EXPLICIT_SOURCE_STATISTICS_OPERATION_REQUIRED'}), 400
            # The authenticated server principal and immutable Owner version are
            # bound here; body-supplied actor/hash fields cannot authorize a read.
            from lumenis.auth.service import get_current_user
            from lumenis.shared.reporting.source_brief_job import get_source_brief_job
            from lumenis.system.security.permission import (
                resolve_local_workspace_principal,
            )
            actor = resolve_local_workspace_principal(module='reports', action='read')
            if actor is None:
                actor = get_current_user()
            if actor is None:
                return jsonify({'ok': False, 'code': 'ANALYSIS_AUTH_REQUIRED'}), 403
            created_by = getattr(actor, 'principal_ref', None)
            if created_by is None and isinstance(actor, dict) and type(actor.get('id')) is int:
                created_by = f"actor:{actor['id']}"
            if created_by is None:
                return jsonify({'ok': False, 'code': 'ANALYSIS_AUTH_REQUIRED'}), 403
            from experience_runtime import _source_brief_context
            from lumenis.shared.reporting.source_brief_job import _scope_material
            current_ref, _, material = _source_brief_context('read')
            if current_ref != created_by:
                return jsonify({'ok': False, 'code': 'ANALYSIS_TASK_ACTOR_MISMATCH'}), 403
            report = get_source_brief_job(context['source_brief_job_id'], actor_id=created_by, actor=actor,
                                         expected_scope=_scope_material(**material))
            context = {**context, 'source_brief_artifact_hash': report['artifact_outcome']['artifact_hash']}
            if context.get('analysis_operation') == 'openai_math':
                from lumenis.shared.evaluation.openai_math_papers.product_outcome import freeze_problem
                problem, declaration, frozen_hash = freeze_problem(
                    context.get('openai_math_problem'), context.get('openai_math_declaration'))
                parent = context.get('openai_math_parent_artifact_id')
                if parent is not None and (not isinstance(parent, str)
                                          or not re.fullmatch(r'ART-[0-9a-f]{16}', parent)):
                    return jsonify({'ok': False, 'code': 'MATHEMATICAL_PARENT_INVALID'}), 400
                # Freeze server-owned identity, not a body-supplied trusted hash.
                context = {**context, 'openai_math_problem': problem,
                           'openai_math_declaration': declaration,
                           'openai_math_problem_sha256': frozen_hash,
                           'openai_math_source_scope': _scope_material(**material)}
        if not isinstance(user_input, str) or not user_input.strip():
            return jsonify({'ok': False, 'error': 'input is required'}), 400
        engine = _get_engine()
        if context.get('analysis_operation') == 'openai_math':
            if 'source_brief_job_id' not in context:
                return jsonify({'ok': False, 'code': 'ANALYSIS_SOURCE_REQUIRED'}), 400
            task = engine.create_mathematical_task(user_input, context, created_by=created_by)
        else:
            task = engine.create_task(user_input, context=context, created_by=created_by)
        return jsonify({'ok': True, 'task': task})
    except PermissionError:
        return jsonify({'ok': False, 'code': 'ANALYSIS_SOURCE_PERMISSION_DENIED'}), 403
    except (ValueError, LookupError):
        return jsonify({'ok': False, 'code': 'ANALYSIS_SOURCE_INVALID'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def api_ai_skill_execution_create(data):
    """Preserve the existing Skill Execution contract on the shared endpoint."""
    task_desc = data.get('task', '')
    skill_id = data.get('skill_id', '')
    if not isinstance(task_desc, str) or not isinstance(skill_id, str):
        return jsonify({'ok': False, 'code': 'SKILL_TASK_INPUT_INVALID'}), 400
    if not task_desc.strip() and not skill_id.strip():
        return jsonify({'ok': False, 'error': 'task or skill_id required'}), 400
    try:
        from lumenis.shared.agents.skills.execution import run_execution_chain, ActionType
        try:
            action_type = ActionType(data.get('action_type', 'ANALYZE'))
        except (TypeError, ValueError):
            return jsonify({'ok': False, 'code': 'ACTION_TYPE_INVALID'}), 400
        ctx = run_execution_chain(
            skill_id=skill_id or 'zbc.generic_analysis',
            task=task_desc,
            input_payload=data.get('input', {}),
            action_type=action_type,
            user_id=data.get('user_id'),
            product=data.get('product', 'SYSTEM'),
            domain=data.get('domain', 'global'),
        )
        evidence_record = getattr(ctx, 'evidence_record', None)
        return jsonify({
            'ok': True,
            'execution_id': ctx.execution_id,
            'status': getattr(ctx.status, 'value', str(ctx.status)),
            'evidence_recorded': bool(
                isinstance(evidence_record, dict) and evidence_record.get('ok')
            ),
        })
    except Exception:
        return jsonify({'ok': False, 'code': 'SKILL_EXECUTION_FAILED'}), 500


@bp.route('/api/ai/tasks/<task_id>', methods=['GET'])
def api_ai_tasks_get(task_id):
    """查询任务状态。"""
    try:
        engine = _get_engine()
        task = engine.get_task(task_id)
        if not task:
            return jsonify({'ok': False, 'error': 'task not found'}), 404
        return jsonify({'ok': True, 'task': task})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/tasks/<task_id>/run', methods=['POST'])
def api_ai_tasks_run(task_id):
    """执行任务（完整调用链：parse → agent → skill → permission → execute）。"""
    try:
        engine = _get_engine()
        task = engine.get_task(task_id)
        if not task:
            return jsonify({'ok': False, 'error': 'task not found'}), 404
        result = engine.run_task(task_id)
        return jsonify({'ok': True, 'task': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/tasks/<task_id>/steps', methods=['GET'])
def api_ai_tasks_steps(task_id):
    """查询执行步骤时间线。"""
    try:
        engine = _get_engine()
        steps = engine.get_steps(task_id)
        return jsonify({'ok': True, 'steps': steps, 'count': len(steps)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/tasks/<task_id>/evidence', methods=['GET'])
def api_ai_tasks_evidence(task_id):
    """查询证据列表。"""
    try:
        engine = _get_engine()
        evidence = engine.get_evidence(task_id)
        return jsonify({'ok': True, 'evidence': evidence, 'count': len(evidence)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/tasks/<task_id>/approve', methods=['POST'])
def api_ai_tasks_approve(task_id):
    """人工审批通过。
    Body: {"approved_by": "user", "note": "审批说明"}
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        approved_by = data.get('approved_by', 'human')
        note = data.get('note', '')
        engine = _get_engine()
        result = engine.approve_task(task_id, approved_by=approved_by, approval_note=note)
        return jsonify({'ok': True, 'task': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/tasks/<task_id>/cancel', methods=['POST'])
def api_ai_tasks_cancel(task_id):
    """取消任务。"""
    try:
        engine = _get_engine()
        result = engine.cancel_task(task_id)
        return jsonify({'ok': True, 'task': result})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def api_ai_tasks_list():
    """List TaskEngine and Skill Execution records in one compatibility view."""
    try:
        limit = max(1, min(200, int(request.args.get('limit', 50))))
        offset = max(0, min(100000, int(request.args.get('offset', 0))))
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'code': 'AI_TASK_PAGINATION_INVALID'}), 400
    try:
        status = request.args.get('status') or None
        engine = _get_engine()
        window = offset + limit
        engine_tasks = engine.list_tasks(status=status, limit=window, offset=0)
        from lumenis.shared.agents.skills.execution import query_executions
        executions = query_executions(
            status=status, limit=window, offset=0, strict=True,
        )
        combined = [
            {**dict(task), 'task_kind': 'TASK_ENGINE'} for task in engine_tasks
        ] + [
            {**dict(execution), 'task_kind': 'SKILL_EXECUTION'}
            for execution in executions
        ]
        combined.sort(
            key=lambda item: str(
                item.get('created_at') or item.get('timestamp') or item.get('started_at') or ''
            ),
            reverse=True,
        )
        page = combined[offset:offset + limit]
        task_engine_page = [item for item in page if item['task_kind'] == 'TASK_ENGINE']
        execution_page = [item for item in page if item['task_kind'] == 'SKILL_EXECUTION']
        return jsonify({
            'ok': True, 'tasks': page, 'count': len(page),
            'task_engine_tasks': task_engine_page,
            'skill_executions': execution_page,
        })
    except Exception:
        return jsonify({'ok': False, 'code': 'AI_TASK_LIST_UNAVAILABLE'}), 503


@bp.route('/api/ai/skills', methods=['GET'])
def api_ai_skills():
    """可用 Skill 列表。"""
    try:
        from lumenis.shared.agents.skills.registry import get_skill_registry
        reg = get_skill_registry()
        skills = [s.to_dict() for s in reg.list_all()]
        return jsonify({'ok': True, 'skills': skills, 'stats': reg.stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/agents', methods=['GET'])
def api_ai_agents():
    """可用 Agent 列表。"""
    try:
        from ai_agent_registry import get_agent_registry
        reg = get_agent_registry()
        agents = [a.to_dict() for a in reg.list_all()]
        return jsonify({'ok': True, 'agents': agents, 'stats': reg.stats()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/capabilities', methods=['GET'])
def api_ai_capabilities():
    """能力清单（Intent + Agent + Skill + 熔断状态 + OSAI边界）。"""
    try:
        engine = _get_engine()
        caps = engine.get_capabilities()
        return jsonify({'ok': True, 'capabilities': caps})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/trace', methods=['GET'])
def api_ai_trace():
    """调用链查询（支持 ?task_id=&limit=）。"""
    try:
        task_id = request.args.get('task_id')
        limit = int(request.args.get('limit', 100))
        engine = _get_engine()
        traces = engine.get_trace(task_id=task_id, limit=limit)
        return jsonify({'ok': True, 'traces': traces, 'count': len(traces)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/permissions', methods=['GET'])
def api_ai_permissions():
    """当前用户权限矩阵。"""
    try:
        engine = _get_engine()
        perms = engine.get_permissions()
        return jsonify({'ok': True, 'permissions': perms})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/task-engine/health', methods=['GET'])
def api_ai_task_engine_health():
    """Task Engine 健康检查。"""
    try:
        engine = _get_engine()
        return jsonify({'ok': True, 'health': engine.health_check()})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@bp.route('/api/ai/task-engine/dlq', methods=['GET'])
def api_ai_task_engine_dlq():
    """死信队列查询。"""
    try:
        engine = _get_engine()
        dlq = engine.get_dlq()
        return jsonify({'ok': True, 'dlq': dlq, 'count': len(dlq)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def register_ai_api(app):
    """注册 AI API 蓝图。"""
    app.register_blueprint(bp)
    return bp
