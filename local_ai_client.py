"""
本地AI对接模块 v1.0
功能：
1. 对接本地Ollama AI
2. 支持多种本地模型（qwen2/llama3/mistral等）
3. 舆情分析（情绪/事件/风险）
4. 智能摘要生成
5. 公关话术推荐
6. 案例对标分析
7. 自动检测本地AI可用性
"""

import os
import sys
import json
import requests
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ZBC Phase 7: module status markers
MODULE_STATUS = 'ACTIVE_FALLBACK'
AI_ROLE = 'LOCAL_INFERENCE'  # Ollama local client, used by /api/local-ai/* routes; intelligence.py has its own local path
NOTE = 'Independent LocalAIClient for Ollama; intelligence.py _chat() also supports local models via auto-detection.'


class LocalAIClient:
    """本地AI客户端"""

    def __init__(self):
        self.base_url = os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434')
        self.default_model = os.environ.get('OLLAMA_MODEL', 'qwen2:7b')
        self.timeout = 60
        self.available = False
        self.available_models = []

    def check_availability(self):
        """检查本地AI是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.available = True
                self.available_models = [m['name'] for m in data.get('models', [])]
                return True
        except Exception as e:
            print(f"[LocalAI] 本地AI不可用: {e}", flush=True)
        self.available = False
        return False

    def generate(self, prompt, model=None, system_prompt=None, temperature=0.7):
        """生成文本"""
        if not self.available:
            if not self.check_availability():
                return {'ok': False, 'error': '本地AI不可用，请确保Ollama已启动'}

        model = model or self.default_model
        if model not in self.available_models:
            # 尝试使用默认模型
            if self.available_models:
                model = self.available_models[0]
            else:
                return {'ok': False, 'error': '没有可用的本地模型'}

        try:
            payload = {
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': temperature
                }
            }
            if system_prompt:
                payload['system'] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'ok': True,
                    'response': data.get('response', ''),
                    'model': model,
                    'total_duration': data.get('total_duration', 0) / 1e9,
                    'eval_count': data.get('eval_count', 0)
                }
            else:
                return {'ok': False, 'error': f'API返回错误: {response.status_code}'}

        except requests.exceptions.Timeout:
            return {'ok': False, 'error': '请求超时'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def chat(self, messages, model=None, temperature=0.7):
        """聊天对话"""
        if not self.available:
            if not self.check_availability():
                return {'ok': False, 'error': '本地AI不可用'}

        model = model or self.default_model
        if model not in self.available_models and self.available_models:
            model = self.available_models[0]

        try:
            payload = {
                'model': model,
                'messages': messages,
                'stream': False,
                'options': {'temperature': temperature}
            }

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'ok': True,
                    'message': data.get('message', {}).get('content', ''),
                    'model': model
                }
            else:
                return {'ok': False, 'error': f'API返回错误: {response.status_code}'}

        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # ============================================
    # 舆情分析功能
    # ============================================

    def analyze_sentiment(self, text, title=''):
        """情绪分析"""
        prompt = f"""请分析以下小红书笔记的情绪倾向。

标题：{title}
内容：{text}

请严格按照以下格式回答：
情绪：正面/负面/中性
置信度：0-100
关键词：3-5个关键词
简要分析：50字以内"""

        return self.generate(prompt, system_prompt="你是一个专业的舆情分析师，擅长分析社交媒体内容的情绪倾向。")

    def analyze_event(self, text, title=''):
        """事件分类分析"""
        prompt = f"""请对以下小红书笔记进行事件分类分析。

标题：{title}
内容：{text}

请严格按照以下格式回答：
事件类型：服务/产品/环境/价格/活动/安全/其他
紧急程度：高/中/低
涉及品牌：如有请列出
事件摘要：100字以内"""

        return self.generate(prompt, system_prompt="你是一个专业的商业舆情分析师，擅长识别和分类商业事件。")

    def analyze_risk(self, text, title=''):
        """风险评估"""
        prompt = f"""请评估以下小红书笔记的舆情风险等级。

标题：{title}
内容：{text}

请严格按照以下格式回答：
风险等级：高/中/低
风险类型：品牌声誉/服务投诉/产品质量/安全隐患/价格争议/其他
传播潜力：高/中/低
应对建议：100字以内"""

        return self.generate(prompt, system_prompt="你是一个资深的公关风险评估专家，擅长识别和评估舆情风险。")

    def generate_summary(self, notes):
        """生成舆情摘要"""
        notes_text = '\n'.join([f"- {n.get('title', '')}（{n.get('sentiment', '')}）" for n in notes[:20]])

        prompt = f"""请根据以下舆情笔记生成一份摘要报告。

笔记列表：
{notes_text}

请按照以下结构生成摘要：
1. 总体概况（50字）
2. 主要话题（3-5个）
3. 情绪分布
4. 重点关注事项
5. 建议措施"""

        return self.generate(prompt, system_prompt="你是一个专业的舆情报告撰写专家，擅长总结和分析舆情数据。")

    def recommend_pr_response(self, note):
        """推荐公关应对话术"""
        prompt = f"""请为以下负面舆情笔记推荐公关应对话术。

标题：{note.get('title', '')}
内容：{note.get('content', '')}
情绪：{note.get('sentiment', '')}
风险等级：{note.get('risk_level', '')}

请提供：
1. 官方回应话术（100字以内，语气诚恳专业）
2. 私信回复话术（50字以内，亲切友好）
3. 后续跟进建议（50字以内）"""

        return self.generate(prompt, system_prompt="你是一个资深的公关专家，擅长处理商业舆情和危机公关。")

    def get_status(self):
        """获取本地AI状态"""
        self.check_availability()
        return {
            'available': self.available,
            'base_url': self.base_url,
            'default_model': self.default_model,
            'available_models': self.available_models,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# 全局实例
local_ai = LocalAIClient()

print("[LocalAI] 本地AI对接模块已加载", flush=True)
