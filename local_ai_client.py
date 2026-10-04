"""Retired local-AI compatibility interface.

The original Ollama client surface remains importable for historical callers.
The production provider registry keeps it disabled, so normal product calls
return an honest unavailable state before any discovery or inference request.
"""

import os
import sys
import json
import requests
from datetime import datetime
from lumenis.system.ai_gateway.providers import is_provider_available

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ZBC Phase 7: module status markers
MODULE_STATUS = 'DISABLED'
AI_ROLE = 'COMPATIBILITY_ADAPTER'  # Existing /api/local-ai/* interface; runtime provider is retired.
NOTE = 'Compatibility interface retained; Ollama discovery and inference are disabled.'


class LocalAIClient:
    """本地AI客户端"""

    def __init__(self):
        self.base_url = os.environ.get('OLLAMA_BASE_URL', os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434'))
        self.default_model = os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder:7b-agent')
        self.timeout = 60
        self.available = False
        self.available_models = []

    def check_availability(self):
        """检查本地AI是否可用"""
        if not is_provider_available('ollama'):
            self.available = False
            self.available_models = []
            return False
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
        if not is_provider_available('ollama'):
            self.available = False
            self.available_models = []
            return {'ok': False, 'status': 'provider_disabled', 'error': 'provider_disabled'}
        if not self.available:
            if not self.check_availability():
                return {'ok': False, 'status': 'unavailable', 'error': '本地AI不可用，请确保Ollama已启动'}

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
                if data.get('done') is False:
                    return {'ok': False, 'error': '本地模型尚未完成响应'}
                content = data.get('response')
                if not isinstance(content, str) or not content.strip():
                    return {'ok': False, 'error': '本地模型返回空内容'}
                return {
                    'ok': True,
                    'response': content,
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
        if not is_provider_available('ollama'):
            self.available = False
            self.available_models = []
            return {'ok': False, 'status': 'provider_disabled', 'error': 'provider_disabled'}
        if not self.available:
            if not self.check_availability():
                return {'ok': False, 'status': 'unavailable', 'error': '本地AI不可用'}

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
                if data.get('done') is False:
                    return {'ok': False, 'error': '本地模型尚未完成响应'}
                message = data.get('message')
                content = message.get('content') if isinstance(message, dict) else None
                if not isinstance(content, str) or not content.strip():
                    return {'ok': False, 'error': '本地模型返回空内容'}
                return {
                    'ok': True,
                    'message': content,
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
        if not is_provider_available('ollama'):
            self.available = False
            self.available_models = []
            return {
                'available': False,
                'status': 'provider_disabled',
                'reason': 'RETIRED_LOCAL_AI_COMPATIBILITY_ONLY',
                'available_models': [],
                'compatibility_adapter': True,
                'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        self.check_availability()
        status = 'available' if self.available else 'unavailable'
        return {
            'available': self.available,
            'status': status,
            'reason': None if self.available else status,
            'base_url': self.base_url,
            'default_model': self.default_model,
            'available_models': self.available_models,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    # ============================================
    # P0: Ollama 正式本地 AI Runtime（健康检查 + 降级逻辑）
    # ============================================

    RUNTIME_READY = "ready"
    RUNTIME_DEGRADED = "degraded"
    RUNTIME_BLOCKED = "blocked"

    def health_check(self, retries=2, retry_interval=1.0):
        """Ollama 本地 AI Runtime 健康检查（P0）。

        多级检查：连接性 → 模型可用性 → 生成能力探测。
        硬红线：Ollama 不可用时标记 BLOCKED，不静默回退云端，不伪造可用状态。
        """
        import time as _time
        result = {
            "runtime_status": self.RUNTIME_BLOCKED,
            "ollama_reachable": False,
            "model_available": False,
            "available_models": [],
            "default_model": self.default_model,
            "blocked_reason": "",
            "degradation_mode": "none",
            "checked_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        if not is_provider_available('ollama'):
            self.available = False
            self.available_models = []
            result['blocked_reason'] = 'provider_disabled'
            result['degradation_mode'] = 'provider_disabled'
            return result

        last_error = None
        for attempt in range(retries + 1):
            try:
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    self.available = True
                    self.available_models = [m['name'] for m in data.get('models', [])]
                    result["ollama_reachable"] = True
                    result["available_models"] = self.available_models
                    break
                else:
                    last_error = f"HTTP {response.status_code}"
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接失败: {e}"
            except requests.exceptions.Timeout:
                last_error = "连接超时(5s)"
            except Exception as e:
                last_error = str(e)
            if attempt < retries:
                _time.sleep(retry_interval)

        if not result["ollama_reachable"]:
            self.available = False
            result["runtime_status"] = self.RUNTIME_BLOCKED
            result["blocked_reason"] = (
                f"Ollama 服务不可达({self.base_url})。最后错误: {last_error}。"
                f"启动条件: 1)安装 Ollama(https://ollama.com); "
                f"2)ollama serve; 3)ollama pull {self.default_model}; "
                f"4)确认端口11434可访问(或设置 OLLAMA_URL)。"
            )
            result["degradation_mode"] = (
                "本地AI Runtime不可用，AI功能标记BLOCKED，"
                "不静默回退云端大模型(云端不作为生产依赖)，需人工启动Ollama后恢复。"
            )
            return result

        if self.default_model in self.available_models:
            result["model_available"] = True
        else:
            if self.available_models:
                result["runtime_status"] = self.RUNTIME_DEGRADED
                result["degradation_mode"] = (
                    f"默认模型{self.default_model}未安装，自动使用{self.available_models[0]}。"
                    f"建议: ollama pull {self.default_model}"
                )
            else:
                result["runtime_status"] = self.RUNTIME_BLOCKED
                result["blocked_reason"] = f"Ollama运行中但无已安装模型。启动条件: ollama pull {self.default_model}"
                result["degradation_mode"] = "无可用模型，AI功能BLOCKED"
            return result

        result["runtime_status"] = self.RUNTIME_READY
        return result

    def is_runtime_ready(self):
        """检查本地AI Runtime是否就绪（P0生产依赖检查）。"""
        health = self.health_check(retries=0)
        return health["runtime_status"] == self.RUNTIME_READY

    def generate_with_runtime_check(self, prompt, model=None, system_prompt=None, temperature=0.7):
        """带Runtime检查的生成（P0：先检查健康状态，BLOCKED时明确返回阻塞信息）。"""
        health = self.health_check(retries=1)
        if health["runtime_status"] == self.RUNTIME_BLOCKED:
            return {
                "ok": False,
                "status": "provider_disabled" if health["blocked_reason"] == 'provider_disabled' else "blocked",
                "error": health["blocked_reason"],
                "degradation_mode": health["degradation_mode"],
                "data": None,
            }
        if health["runtime_status"] == self.RUNTIME_DEGRADED and health["available_models"]:
            model = health["available_models"][0]
        result = self.generate(prompt, model=model, system_prompt=system_prompt, temperature=temperature)
        if result.get("ok"):
            result["runtime_status"] = health["runtime_status"]
        return result


# 全局实例
local_ai = LocalAIClient()

print("[LocalAI] retired compatibility adapter retained; discovery and inference are disabled", flush=True)
