# -*- coding: utf-8 -*-
"""AI API Blueprint（批4拆分自 app.py）
包含：ai/status, ai/test, ark/*, ai-learning/*, web-sentiment/*, ai/chat, ai/providers,
ai/analyze-v570, ai-filter/*, ai/channel-health, ai/analyze
原则：只搬不移逻辑，函数体零改动，路由与行为保持一致。
"""
from __future__ import annotations
import json
import threading
from flask import Blueprint, jsonify, request

bp = Blueprint("ai_api", __name__)

# 依赖模块（与 app.py 保持一致）
import intelligence
import ai_governance
import ai_analyzer
import ai_learning_engine
import ai_filter
import ai_channel
import function_registry
from report_api import _canonical_report_metrics


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
    """AI学习状态查询"""
    try:
        engine = ai_learning_engine.get_ai_learning_engine()
        status = engine.get_learning_status()
        return jsonify({'ok': True, **status})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/web-sentiment/search', methods=['POST'])
def api_web_sentiment_search():
    """全网舆情检索（使用豆包AI）"""
    try:
        data = request.get_json(silent=True) or {}
        keywords = data.get('keywords')
        platform = data.get('platform', 'all')
        limit = data.get('limit', 20)
        
        search = ai_learning_engine.get_web_sentiment_search()
        result = search.search_public_opinion(keywords=keywords, platform=platform, limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@bp.route('/api/web-sentiment/history')
def api_web_sentiment_history():
    """全网舆情检索历史"""
    try:
        limit = request.args.get('limit', 20, type=int)
        search = ai_learning_engine.get_web_sentiment_search()
        history = search.get_search_history(limit=limit)
        return jsonify({'ok': True, 'history': history})
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
    try: raw,provider=intelligence._chat(system,user,0.15,1800)
    except Exception as exc: raw,provider=None,'rule'; print('[Nomi] chat failed:',exc)
    status=intelligence.ai_status()
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
        import ai_channel as _aic
        import intelligence as _intel
        _st = _intel.ai_status()
        _h = _aic.channel_health(provider=_st.get('provider',''), model=_st.get('model',''))
        return jsonify({'ok': True, 'enabled': bool(_st.get('enabled')), **{'health': _h}})
    except Exception as _e:
        return jsonify({'ok': False, 'error': str(_e)}), 500

# ===== v5.8.0 新增API =====

# ===== 小红书 P0 生产编排 API（双子星库 Contract） =====

@bp.route('/api/ai/analyze', methods=['POST'])
def api_ai_analyze_v580():
    """AI分析舆情"""
    data = request.get_json(silent=True) or {}
    note_id = data.get('note_id')
    provider = data.get('provider', 'local')
    analysis_type = data.get('type', 'summary')  # summary/sentiment/risk/event
    
    # 这里可以集成实际的AI调用逻辑
    # 暂时返回模拟数据
    return jsonify({
        'ok': True,
        'provider': provider,
        'note_id': note_id,
        'analysis': {
            'summary': '这是AI分析的摘要内容',
            'sentiment': 'neutral',
            'risk_level': 'low',
            'event_type': 'general'
        }
    })


@bp.route('/api/ai-learning/optimization/<operation_type>')
def api_ai_learning_optimization(operation_type):
    """获取操作优化建议（从 app.py 迁入 ai_api.py，拆分收尾）"""
    try:
        engine = ai_learning_engine.get_ai_learning_engine()
        suggestion = engine.get_optimization_suggestion(operation_type)
        return jsonify({'ok': True, 'operation_type': operation_type, 'suggestion': suggestion})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def register_ai_api(app):
    """注册 AI API 蓝图。"""
    app.register_blueprint(bp)
    return bp
