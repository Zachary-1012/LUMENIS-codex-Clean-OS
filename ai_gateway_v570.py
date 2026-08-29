"""
AI Gateway v5.7.0
统一AI分析接口，支持本地AI和远程AI提供商
"""
import os
import json
import requests
from datetime import datetime

def providers():
    """返回可用的AI提供商列表"""
    provider_list = []
    
    # 检查本地AI
    try:
        import ai_analyzer
        local_status = ai_analyzer.ai_status()
        if local_status.get('available', False):
            provider_list.append({
                'id': 'local',
                'name': '本地AI (Ollama/LM Studio)',
                'type': 'local',
                'status': 'available'
            })
    except Exception:
        pass
    
    # 检查远程AI提供商（从环境变量）
    remote_providers = [
        {'id': 'dashscope', 'name': '豆包/通义千问', 'env_key': 'DASHSCOPE_API_KEY', 'model_env': 'QWEN_MODEL'},
        {'id': 'openai', 'name': 'OpenAI GPT', 'env_key': 'OPENAI_API_KEY', 'model_env': 'OPENAI_MODEL'},
        {'id': 'deepseek', 'name': 'DeepSeek', 'env_key': 'DEEPSEEK_API_KEY', 'model_env': 'DEEPSEEK_MODEL'},
    ]
    
    for p in remote_providers:
        api_key = os.getenv(p['env_key'], '')
        if api_key:
            provider_list.append({
                'id': p['id'],
                'name': p['name'],
                'type': 'remote',
                'model': os.getenv(p['model_env'], 'default'),
                'status': 'configured'
            })
    
    return provider_list

def analyze(text, context=''):
    """
    统一AI分析接口
    优先使用本地AI，本地不可用时使用远程AI
    """
    result = {
        'ok': False,
        'text': text,
        'context': context,
        'provider': 'none',
        'analysis': '',
        'error': ''
    }
    
    if not text:
        result['error'] = '文本为空'
        return result
    
    # 1. 尝试本地AI
    try:
        import ai_analyzer
        local_result = ai_analyzer.analyze_sentiment(text, context)
        if local_result and local_result.get('ok', False):
            result['ok'] = True
            result['provider'] = 'local'
            result['analysis'] = local_result.get('analysis', '')
            result['sentiment'] = local_result.get('sentiment', 'neutral')
            result['risk_level'] = local_result.get('risk_level', 'low')
            return result
    except Exception as e:
        result['error'] = f'本地AI失败: {str(e)}'
    
    # 2. 尝试远程AI（豆包/通义千问）
    dashscope_key = os.getenv('DASHSCOPE_API_KEY', '')
    if dashscope_key:
        try:
            model = os.getenv('QWEN_MODEL', 'qwen-plus')
            url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
            headers = {
                'Authorization': f'Bearer {dashscope_key}',
                'Content-Type': 'application/json'
            }
            prompt = f"请分析以下舆情内容：\n\n文本：{text}\n\n上下文：{context}\n\n请给出：1.情感倾向 2.风险等级 3.关键信息 4.建议处理方式"
            payload = {
                'model': model,
                'input': {'messages': [{'role': 'user', 'content': prompt}]},
                'parameters': {'result_format': 'message'}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                analysis_text = data.get('output', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
                result['ok'] = True
                result['provider'] = 'dashscope'
                result['analysis'] = analysis_text
                return result
        except Exception as e:
            result['error'] = f'远程AI失败: {str(e)}'
    
    # 3. 尝试OpenAI
    openai_key = os.getenv('OPENAI_API_KEY', '')
    if openai_key:
        try:
            model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            url = 'https://api.openai.com/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {openai_key}',
                'Content-Type': 'application/json'
            }
            prompt = f"请分析以下舆情内容：\n\n文本：{text}\n\n上下文：{context}\n\n请给出：1.情感倾向 2.风险等级 3.关键信息 4.建议处理方式"
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 1000
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                analysis_text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                result['ok'] = True
                result['provider'] = 'openai'
                result['analysis'] = analysis_text
                return result
        except Exception as e:
            result['error'] = f'OpenAI失败: {str(e)}'
    
    # 4. 所有AI都不可用，返回基于规则的简单分析
    result['ok'] = True
    result['provider'] = 'rule_based'
    result['analysis'] = _rule_based_analysis(text, context)
    result['sentiment'] = _detect_sentiment(text)
    result['risk_level'] = _detect_risk(text)
    
    return result

def _rule_based_analysis(text, context=''):
    """基于规则的简单分析"""
    sentiment = _detect_sentiment(text)
    risk = _detect_risk(text)
    
    analysis = f"【规则分析】\n"
    analysis += f"情感倾向：{sentiment}\n"
    analysis += f"风险等级：{risk}\n"
    analysis += f"文本长度：{len(text)}字\n"
    
    if context:
        analysis += f"上下文：{context[:100]}...\n"
    
    # 关键词检测
    negative_words = ['投诉', '差评', '避雷', '垃圾', '失望', '愤怒', '曝光', '维权', '退款', '欺骗', '虚假', '态度差', '服务差', '排队', '拥挤', '脏乱', '不安全', '事故', '受伤']
    found_neg = [w for w in negative_words if w in text]
    if found_neg:
        analysis += f"负面关键词：{', '.join(found_neg[:5])}\n"
    
    positive_words = ['好评', '推荐', '喜欢', '满意', '赞', '棒', '优秀', '贴心', '方便', '划算', '值得']
    found_pos = [w for w in positive_words if w in text]
    if found_pos:
        analysis += f"正面关键词：{', '.join(found_pos[:5])}\n"
    
    analysis += "\n【建议】\n"
    if risk == 'high':
        analysis += "⚠️ 高风险舆情，建议立即关注并处理\n"
        analysis += "1. 核实事件真实性\n2. 准备回应话术\n3. 监控传播情况\n"
    elif risk == 'medium':
        analysis += "⚡ 中等风险，建议持续关注\n"
        analysis += "1. 记录事件\n2. 准备应对方案\n3. 观察是否升级\n"
    else:
        analysis += "✅ 低风险，正常监测即可\n"
    
    return analysis

def _detect_sentiment(text):
    """检测情感倾向"""
    negative_words = ['投诉', '差评', '避雷', '垃圾', '失望', '愤怒', '曝光', '维权', '退款', '欺骗', '虚假', '态度差', '服务差']
    positive_words = ['好评', '推荐', '喜欢', '满意', '赞', '棒', '优秀', '贴心']
    
    neg_count = sum(1 for w in negative_words if w in text)
    pos_count = sum(1 for w in positive_words if w in text)
    
    if neg_count > pos_count:
        return 'negative'
    elif pos_count > neg_count:
        return 'positive'
    else:
        return 'neutral'

def _detect_risk(text):
    """检测风险等级"""
    high_risk_words = ['事故', '受伤', '安全', '违法', '歧视', '曝光', '维权', '报警', '起诉', '媒体', '热搜']
    medium_risk_words = ['投诉', '差评', '避雷', '失望', '愤怒', '退款', '欺骗', '虚假', '态度差', '服务差', '排队', '拥挤']
    
    high_count = sum(1 for w in high_risk_words if w in text)
    medium_count = sum(1 for w in medium_risk_words if w in text)
    
    if high_count > 0:
        return 'high'
    elif medium_count >= 2:
        return 'medium'
    else:
        return 'low'
