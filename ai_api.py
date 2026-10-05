# -*- coding: utf-8 -*-
"""LUMENIS AI API Blueprint.

AI runtime is owned by SYSTEM AI Gateway. Learning endpoints consume Shared
Learning. The historical ungrounded "AI web search" route is kept only as an
explicit retired compatibility surface and cannot create canonical events.
"""
from __future__ import annotations
import json
import threading
from flask import Blueprint, jsonify, request

bp = Blueprint("ai_api", __name__)

# 依赖模块（与 app.py 保持一致）
from lumenis.system.ai_gateway import core as intelligence
import ai_governance
import ai_analyzer
import ai_filter
from lumenis.system.ai_gateway import channel as ai_channel
from lumenis.shared.learning import operations as learning_operations
import function_registry
import database as db
from lumenis.shared.reporting.routes import _canonical_report_metrics


@bp.route('/api/ai/status')
def api_ai_status():
    status = intelligence.ai_status()
    return jsonify({'ok': True, **status, 'interface': 'local-ai-gateway', 'fallback': 'local_rule', 'providers': ['ollama','lmstudio','llama_cpp','qwen','openai','deepseek']})

@bp.route('/api/ai/test', methods=['POST'])
def api_ai_test():
    data = request.get_json(silent=True) or {}
    text = str(data.get('text') or '请用一句话说明广州太古汇舆情监测系统正在监测什么。').strip()[:1200]
    # AI 治理：额度检查
    allowed, quota = ai_governance._usage_tracker.check_quota()
    if not allowed:
        return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota}), 429
    # AI 治理：脱敏
    desensitized_text, mapping = ai_governance.desensitize_text(text)
    result = intelligence.test_connection(desensitized_text)
    # AI 治理：回传补回实体
    if isinstance(result, dict) and 'reply' in result:
        result['reply'] = ai_governance.restore_text(str(result['reply']), mapping)
    # AI 治理：记录使用统计
    ai_governance.record_ai_call('ai/test', prompt_tokens=len(text)//2,
                                   completion_tokens=len(str(result.get('reply','')))//2 if isinstance(result, dict) else 0,
                                   total_tokens=len(text)//2, provider=result.get('provider','zhipu') if isinstance(result, dict) else 'zhipu',
                                   success=True)
    # AI 治理：输出标记
    marked = ai_governance.mark_ai_output(result if isinstance(result, dict) else {'result': result},
                                             provider=result.get('provider','zhipu') if isinstance(result, dict) else 'zhipu',
                                             endpoint='ai/test')
    return jsonify(marked)

# ========== 豆包AI API（ark_llm）- 可选辅助功能 ==========
# 【S1 2026-09-02】云智(ARK)已停用，改用智谱(zhipu)驱动（intelligence 网关）。
# 保留路由名/响应结构与前端兼容；provider 字段标记真实来源（zhipu/local/rule）。

@bp.route('/api/ark/status')
def api_ark_status():
    """AI API状态查询（智谱驱动）"""
    try:
        st = intelligence.ai_status()
        return jsonify({'ok': True, 'enabled': st.get('enabled'), 'provider': st.get('provider'),
                        'model': st.get('model'), 'runtime': st.get('runtime'),
                        'detail': st.get('detail', '')})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e), 'provider': 'local_rule', 'enabled': False}), 500

@bp.route('/api/ark/chat', methods=['POST'])
def api_ark_chat():
    """AI通用聊天（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
    try:
        data = request.get_json(silent=True) or {}
        message = str(data.get('message') or data.get('text') or '').strip()
        if not message:
            return jsonify({'ok': False, 'error': '消息不能为空'}), 400
        system_prompt = data.get('system_prompt')
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota, 'fallback': 'local'}), 429
        # AI 治理：脱敏
        desensitized_msg, mapping = ai_governance.desensitize_text(message)
        raw, provider = intelligence._chat(system_prompt or '你是广州太古汇舆情监测系统的智能助手', desensitized_msg, 0.15, 1800)
        # AI 治理：回传补回实体
        reply = ai_governance.restore_text(raw.strip() if raw else 'AI引擎已就绪', mapping)
        # AI 治理：记录使用统计
        ai_governance.record_ai_call('ark/chat', prompt_tokens=len(message)//2,
                                       completion_tokens=len(reply)//2,
                                       total_tokens=(len(message)+len(reply))//2,
                                       provider=provider or 'local_rule', success=True)
        # AI 治理：输出标记
        result = ai_governance.mark_ai_output(
            {'ok': True, 'reply': reply, 'provider': provider or 'local_rule',
             'fallback': provider in ('rule', 'local_rule'), 'desensitized': bool(mapping)},
            provider=provider or 'local_rule', endpoint='ark/chat')
        return jsonify(result)
    except Exception as e:
        ai_governance.record_ai_call('ark/chat', provider='zhipu', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/ark/sentiment', methods=['POST'])
def api_ark_sentiment():
    """AI舆情分析（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
    try:
        data = request.get_json(silent=True) or {}
        text = str(data.get('text') or data.get('content') or '').strip()
        if not text:
            return jsonify({'ok': False, 'error': '文本不能为空'}), 400
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota}), 429
        # AI 治理：脱敏
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        result = intelligence.analyze_sentiment(desensitized_text)
        # AI 治理：回传补回实体
        if result.get('summary'):
            result['summary'] = ai_governance.restore_text(str(result['summary']), mapping)
        # AI 治理：记录使用统计
        ai_governance.record_ai_call('ark/sentiment', prompt_tokens=len(text)//2,
                                       completion_tokens=len(str(result.get('summary','')))//2,
                                       total_tokens=len(text)//2,
                                       provider=result.get('provider','zhipu'), success=True)
        # AI 治理：输出标记
        marked = ai_governance.mark_ai_output(
            {'ok': True, 'sentiment': result.get('sentiment'), 'label': result.get('label'),
             'summary': result.get('summary'), 'keywords': result.get('keywords'),
             'provider': result.get('provider'), 'fallback': result.get('provider') == 'rule',
             'desensitized': bool(mapping)},
            provider=result.get('provider','zhipu'), endpoint='ark/sentiment')
        return jsonify(marked)
    except Exception as e:
        ai_governance.record_ai_call('ark/sentiment', provider='zhipu', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/ark/summary', methods=['POST'])
def api_ark_summary():
    """AI摘要生成（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
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
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            return jsonify({'ok': False, 'error': 'AI 每日额度已超限', 'quota': quota, 'fallback': 'local'}), 429
        # AI 治理：脱敏（敏感实体→占位符）
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        # 调用智谱
        summary = intelligence.generate_summary(desensitized_text, max_length=max_length)
        # AI 治理：回传补回实体
        summary = ai_governance.restore_text(summary, mapping)
        # AI 治理：记录使用统计
        ai_governance.record_ai_call('ark/summary', prompt_tokens=len(text)//2,
                                       completion_tokens=len(summary)//2,
                                       total_tokens=(len(text)+len(summary))//2,
                                       provider='zhipu', success=True)
        # AI 治理：输出标记（增强层，非 System Truth，可用于 Zachary 学习）
        result = ai_governance.mark_ai_output(
            {'ok': True, 'summary': summary, 'desensitized': bool(mapping),
             'quota_remaining': quota['call_remaining']},
            provider='zhipu', endpoint='ark/summary')
        return jsonify(result)
    except Exception as e:
        ai_governance.record_ai_call('ark/summary', provider='zhipu', success=False)
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/ark/keywords', methods=['POST'])
def api_ark_keywords():
    """AI关键词提取（智谱驱动+AI治理：脱敏回传/额度控制/使用统计/输出标记）"""
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
        # AI 治理：额度检查
        allowed, quota = ai_governance._usage_tracker.check_quota()
        if not allowed:
            # 额度超限直接回退本地
            topics = ai_analyzer.extract_topics(text, '')
            return jsonify({'ok': True, 'keywords': topics, 'provider': 'local',
                            'fallback': True, 'quota_exceeded': True}), 200
        # AI 治理：脱敏
        desensitized_text, mapping = ai_governance.desensitize_text(text)
        # 调用智谱
        keywords = intelligence.extract_keywords(desensitized_text, num_keywords=num_keywords)
        if keywords:
            # AI 治理：回传补回实体（关键词列表）
            restored_keywords = [ai_governance.restore_text(kw, mapping) for kw in keywords]
            ai_governance.record_ai_call('ark/keywords', prompt_tokens=len(text)//2,
                                           completion_tokens=sum(len(k) for k in restored_keywords)//2,
                                           total_tokens=(len(text)+sum(len(k) for k in restored_keywords))//2,
                                           provider='zhipu', success=True)
            result = ai_governance.mark_ai_output(
                {'ok': True, 'keywords': restored_keywords, 'desensitized': bool(mapping),
                 'quota_remaining': quota['call_remaining']},
                provider='zhipu', endpoint='ark/keywords')
            return jsonify(result)
        # 回退本地规则提取
        topics = ai_analyzer.extract_topics(text, '')
        ai_governance.record_ai_call('ark/keywords', provider='local', success=True)
        return jsonify({'ok': True, 'keywords': topics, 'provider': 'local', 'fallback': True})
    except Exception as e:
        ai_governance.record_ai_call('ark/keywords', provider='zhipu', success=False)
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
    data=request.get_json(silent=True) or {}
    text=str(data.get('message') or data.get('text') or '').strip()[:4000]
    if not text: return jsonify({'ok':False,'error':'问题不能为空'}),400
    context=function_registry.build_context(text, db)
    try: stats=db.get_stats()
    except Exception: stats={}
    # UDIP V1.0 (P5): AI 语义层——业务指标走 Canonical，不自行计算/推断
    # MET-RISK-01/02 由 daily_report.generate_today_summary 权威计算，AI 只消费、不重算
    try:
        _canonical_ai = _canonical_report_metrics('daily', None)
        _canonical_str = 'Canonical 指标(权威,AI只引用不重算): ' + json.dumps(_canonical_ai, ensure_ascii=False, default=str)[:1200]
    except Exception:
        _canonical_ai = {}
        _canonical_str = 'Canonical 指标暂不可用'
    history=data.get('history') or []
    if not isinstance(history,list): history=[]
    history_text=[]
    for item in history[-6:]:
        if isinstance(item,dict):
            role='用户' if item.get('role') in ('user','human') else '诺米'
            content=str(item.get('content') or '')[:800]
            if content: history_text.append(f'{role}：{content}')
    system='你是广州太古汇舆情监测系统的智能助手“诺米”。你拥有系统结构化检索能力。必须优先依据检索结果回答，不编造数据库事实；涉及舆情事实时明确区分“系统已监测”“用户描述”“待核验”。可以回答系统操作、品牌/业态、品牌官网、案例、公关回复、风险分析、报告、事件与架构问题。需要处置建议时使用：判断→依据→动作→责任方/时限→复盘指标。若没有足够数据，明确告诉用户缺什么，不要用常识冒充系统数据。'
    user=f'用户问题：{text}\n\n函数与数据检索结果：\n{context}\n\n当前统计：{json.dumps(stats,ensure_ascii=False,default=str)[:5000]}\n\n{_canonical_str}'
    if history_text: user += '\n\n最近对话：\n' + '\n'.join(history_text)
    status=intelligence.ai_status()
    # Explicitly stay local/rule when no model is actually ready.  This keeps
    # a missing Ollama model from falling through to an unrequested cloud call
    # and preserves the user's local-first/no-waste boundary.
    if not status.get('enabled'):
        fallback='我已完成系统检索，但当前本机模型暂不可用，未发起站外模型调用。\n\n' + context
        return jsonify({'ok':True,'reply':fallback,'provider':'local_rule','ai_status':status,'context':context})
    try: raw,provider=intelligence._chat(system,user,0.15,1800)
    except Exception as exc: raw,provider=None,'rule'; print('[Nomi] chat failed:',exc)
    if raw: return jsonify({'ok':True,'reply':raw.strip(),'provider':provider,'ai_status':status,'context':context})
    fallback='我已完成系统检索，但当前可调用模型暂不可用。\n\n' + context
    return jsonify({'ok':True,'reply':fallback,'provider':'local_rule','ai_status':status,'context':context})

@bp.route('/api/ai/providers')
def api_ai_providers_v570():
    try:
        local = ai_analyzer.ai_status() if hasattr(ai_analyzer, 'ai_status') else {'available': False, 'model': 'none', 'message': '本地AI未配置'}
    except Exception:
        local = {'available': False, 'model': 'none', 'message': '本地AI状态获取失败'}
    # P1-A(2026-09-02): ai_gateway_v570已废弃，统一到intelligence.py
    try:
        ai_stat = intelligence.ai_status()
        remote = [{
            'id': ai_stat.get('provider', 'unknown'),
            'name': f"AI Provider ({ai_stat.get('provider', 'unknown')})",
            'type': ai_stat.get('runtime', 'unknown'),
            'status': 'available' if ai_stat.get('enabled') else 'unavailable',
            'model': ai_stat.get('model', 'unknown')
        }] if ai_stat.get('enabled') else []
    except Exception:
        remote = []
    return jsonify({'ok': True, 'local': local, 'remote': remote})

@bp.route('/api/ai/analyze-v570',methods=['POST'])
def api_ai_analyze_v570():
    # P1-A(2026-09-02): ai_gateway_v570已废弃，统一到intelligence._chat()
    data=request.get_json(silent=True) or {}
    text=data.get('text','')
    context=data.get('context','')
    if not text:
        return jsonify({'ok': False, 'text': text, 'context': context, 'provider': 'none', 'analysis': '', 'error': '文本为空'})
    try:
        system_prompt = "你是广州太古汇舆情分析助手。请分析以下内容的情感倾向、风险等级和关键要点。"
        user_prompt = f"内容：{text}\n上下文：{context or '无'}\n请给出：1)情感倾向 2)风险等级 3)关键要点 4)建议"
        raw, provider, _ = intelligence.chat(system_prompt, user_prompt, level='medium', temperature=0.3, max_tokens=800, pack_id='glm_4_5_air')
        return jsonify({'ok': True, 'text': text, 'context': context, 'provider': provider, 'analysis': raw or '', 'error': ''})
    except Exception as e:
        return jsonify({'ok': False, 'text': text, 'context': context, 'provider': 'none', 'analysis': '', 'error': str(e)})

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


@bp.before_request
def _scoped_report_task_boundary():
    """Report tasks require Reporting's live actor and exact scope checks."""
    path = request.path
    if (path.startswith('/api/ai/tasks/rbrief_')
            or (path == '/api/ai/trace' and request.args.get('task_id', '').startswith('rbrief_'))):
        return jsonify({'ok': False, 'code': 'REPORT_TASK_SCOPED_ROUTE_REQUIRED'}), 403


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
        if not isinstance(user_input, str) or not user_input.strip():
            return jsonify({'ok': False, 'error': 'input is required'}), 400
        engine = _get_engine()
        task = engine.create_task(user_input, context=context, created_by=created_by)
        return jsonify({'ok': True, 'task': task})
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
    except Exception as e:
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
