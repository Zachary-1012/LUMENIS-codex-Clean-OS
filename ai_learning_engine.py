"""
豆包AI全网舆情检索与自学习进化模块 - 广州太古汇舆情监测系统 v5.8.0

功能：
1. 使用豆包AI进行全网舆情事件检索，充实案例库
2. 自学习进化机制：每次豆包AI运行时，系统学习其操作方式、功能、逻辑，并累计
3. 独立指令在底层逻辑，确保系统持续学习进化
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from db_paths import main_db_path  # P0-DBISO-01

# 配置日志
logger = logging.getLogger(__name__)

# ZBC Phase 7: module status markers
MODULE_STATUS = 'LEGACY_PARTIAL'
AI_ROLE = 'AUXILIARY_RESEARCH'  # web sentiment search uses ark_llm (LEGACY), guarded by AI_PROVIDER
NOTE = 'WebSentimentSearch uses ark_llm.chat(); disabled when AI_PROVIDER=zhipu. Learning records are local JSON only.'

class AILearningEngine:
    """AI自学习进化引擎"""
    
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.learning_file = os.path.join(self.data_dir, 'ai_learning_records.json')
        self.knowledge_base_file = os.path.join(self.data_dir, 'ai_knowledge_base.json')
        self.operation_log_file = os.path.join(self.data_dir, 'ai_operation_log.json')
        
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载学习记录
        self.learning_records = self._load_json(self.learning_file, default=[])
        self.knowledge_base = self._load_json(self.knowledge_base_file, default={
            'operation_patterns': {},
            'response_templates': {},
            'optimization_suggestions': [],
            'learned_skills': [],
            'evolution_level': 1,
            'total_learning_count': 0,
            'last_learning_time': None,
        })
        self.operation_log = self._load_json(self.operation_log_file, default=[])
    
    def _load_json(self, filepath, default=None):
        """加载JSON文件"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载JSON文件失败 {filepath}: {e}")
        return default if default is not None else {}
    
    def _save_json(self, filepath, data):
        """保存JSON文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存JSON文件失败 {filepath}: {e}")
    
    def record_operation(self, operation_type, operation_details, result, duration_ms=None):
        """记录AI操作，用于学习"""
        record = {
            'id': f'opt_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}',
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'operation_details': operation_details,
            'result': result,
            'duration_ms': duration_ms,
            'success': result.get('ok', False) if isinstance(result, dict) else False,
        }
        
        self.operation_log.append(record)
        # 只保留最近1000条记录
        if len(self.operation_log) > 1000:
            self.operation_log = self.operation_log[-1000:]
        
        self._save_json(self.operation_log_file, self.operation_log)
        
        # 触发学习
        self._learn_from_operation(record)
        
        logger.info(f"记录AI操作: {operation_type}, 成功: {record['success']}")
        return record
    
    def _learn_from_operation(self, record):
        """从操作中学习"""
        try:
            operation_type = record['operation_type']
            success = record['success']
            
            # 更新操作模式统计
            if operation_type not in self.knowledge_base['operation_patterns']:
                self.knowledge_base['operation_patterns'][operation_type] = {
                    'total_count': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'avg_duration_ms': 0,
                    'best_practices': [],
                    'common_errors': [],
                    'last_used': None,
                }
            
            pattern = self.knowledge_base['operation_patterns'][operation_type]
            pattern['total_count'] += 1
            
            if success:
                pattern['success_count'] += 1
                # 记录成功的操作细节作为最佳实践
                if record.get('operation_details'):
                    best_practice = {
                        'timestamp': record['timestamp'],
                        'details': record['operation_details'],
                        'result': record['result'],
                        'duration_ms': record.get('duration_ms'),
                    }
                    if best_practice not in pattern['best_practices']:
                        pattern['best_practices'].append(best_practice)
                        # 只保留最近20条最佳实践
                        if len(pattern['best_practices']) > 20:
                            pattern['best_practices'] = pattern['best_practices'][-20:]
            else:
                pattern['failure_count'] += 1
                # 记录常见错误
                if record.get('result') and isinstance(record['result'], dict):
                    error = record['result'].get('error', 'Unknown error')
                    if error not in pattern['common_errors']:
                        pattern['common_errors'].append(error)
                        # 只保留最近20个常见错误
                        if len(pattern['common_errors']) > 20:
                            pattern['common_errors'] = pattern['common_errors'][-20:]
            
            # 更新平均耗时
            if record.get('duration_ms'):
                total_duration = pattern['avg_duration_ms'] * (pattern['total_count'] - 1) + record['duration_ms']
                pattern['avg_duration_ms'] = total_duration / pattern['total_count']
            
            pattern['last_used'] = record['timestamp']
            
            # 更新学习统计
            self.knowledge_base['total_learning_count'] += 1
            self.knowledge_base['last_learning_time'] = datetime.now().isoformat()
            
            # 计算进化等级（基于学习次数）
            self.knowledge_base['evolution_level'] = min(10, 1 + self.knowledge_base['total_learning_count'] // 100)
            
            # 保存知识库
            self._save_json(self.knowledge_base_file, self.knowledge_base)
            
            # 记录学习记录
            learning_record = {
                'timestamp': datetime.now().isoformat(),
                'operation_type': operation_type,
                'learned_pattern': success,
                'evolution_level': self.knowledge_base['evolution_level'],
            }
            self.learning_records.append(learning_record)
            # 只保留最近500条学习记录
            if len(self.learning_records) > 500:
                self.learning_records = self.learning_records[-500:]
            self._save_json(self.learning_file, self.learning_records)
            
        except Exception as e:
            logger.error(f"学习过程出错: {e}")
    
    def get_optimization_suggestion(self, operation_type):
        """根据学习记录获取优化建议"""
        pattern = self.knowledge_base['operation_patterns'].get(operation_type)
        if not pattern:
            return None
        
        suggestions = []
        
        # 成功率建议
        success_rate = pattern['success_count'] / max(1, pattern['total_count'])
        if success_rate < 0.8:
            suggestions.append(f"成功率较低 ({success_rate:.1%})，建议检查常见错误: {', '.join(pattern['common_errors'][-3:])}")
        
        # 耗时建议
        if pattern['avg_duration_ms'] > 5000:
            suggestions.append(f"平均耗时较长 ({pattern['avg_duration_ms']:.0f}ms)，建议参考最佳实践优化")
        
        # 最佳实践建议
        if pattern['best_practices']:
            latest_best = pattern['best_practices'][-1]
            suggestions.append(f"参考最近成功案例: {json.dumps(latest_best.get('details', {}), ensure_ascii=False)[:100]}")
        
        return suggestions if suggestions else None
    
    def get_learning_status(self):
        """获取学习状态"""
        return {
            'evolution_level': self.knowledge_base.get('evolution_level', 1),
            'total_learning_count': self.knowledge_base.get('total_learning_count', 0),
            'last_learning_time': self.knowledge_base.get('last_learning_time'),
            'learned_operation_types': list(self.knowledge_base.get('operation_patterns', {}).keys()),
            'total_operation_records': len(self.operation_log),
            'success_rate': self._calculate_overall_success_rate(),
        }
    
    def _calculate_overall_success_rate(self):
        """计算总体成功率"""
        total = 0
        success = 0
        for pattern in self.knowledge_base.get('operation_patterns', {}).values():
            total += pattern.get('total_count', 0)
            success += pattern.get('success_count', 0)
        return success / max(1, total)


class WebSentimentSearch:
    """全网舆情检索（使用豆包AI）"""
    
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.learning_engine = AILearningEngine(base_dir)
        
        # 尝试导入ark_llm（受 AI_PROVIDER 主开关约束：仅豆包主力模式启用）
        self.ai_provider = os.getenv('AI_PROVIDER', 'zhipu').strip().lower()
        self.ark_channel_enabled = self.ai_provider in ('ark', 'doubao', 'volc', 'doubao-ark')
        try:
            import ark_llm
            self.ark_llm = ark_llm
            self.ai_available = self.ark_channel_enabled
            if not self.ark_channel_enabled:
                logger.warning(
                    f"豆包通道已禁用：AI_PROVIDER={self.ai_provider}（智谱主力模式，豆包最小输出）")
        except ImportError:
            self.ark_llm = None
            self.ai_available = False
            logger.warning("ark_llm模块不可用，全网舆情检索功能受限")
    
    def search_public_opinion(self, keywords=None, platform='all', limit=20):
        """使用豆包AI进行全网舆情检索"""
        start_time = time.time()
        
        if keywords is None:
            keywords = ['广州太古汇', '太古汇 舆情', '太古汇 投诉']
        
        operation_details = {
            'keywords': keywords,
            'platform': platform,
            'limit': limit,
        }
        
        try:
            if not self.ai_available:
                result = {
                    'ok': False,
                    'error': 'AI模块不可用',
                    'results': [],
                }
            else:
                # 构建提示词
                prompt = self._build_search_prompt(keywords, platform, limit)
                
                # 使用豆包AI进行检索分析
                response = self.ark_llm.chat(prompt, system_prompt=self._get_system_prompt())
                
                # 解析AI返回的结果
                results = self._parse_ai_response(response)
                
                result = {
                    'ok': True,
                    'results': results,
                    'total': len(results),
                    'ai_response': response[:500] if response else '',
                }
                
                # 保存到案例库
                self._save_to_case_library(results)
                
        except Exception as e:
            logger.error(f"全网舆情检索失败: {e}")
            result = {
                'ok': False,
                'error': str(e),
                'results': [],
            }
        
        # 记录操作并学习
        duration_ms = (time.time() - start_time) * 1000
        self.learning_engine.record_operation(
            operation_type='web_sentiment_search',
            operation_details=operation_details,
            result=result,
            duration_ms=duration_ms
        )
        
        return result
    
    def _build_search_prompt(self, keywords, platform, limit):
        """构建搜索提示词"""
        keywords_str = '、'.join(keywords)
        platform_str = {
            'all': '全网（微博、知乎、小红书、B站、抖音等）',
            'weibo': '微博',
            'zhihu': '知乎',
            'xiaohongshu': '小红书',
            'bilibili': 'B站',
        }.get(platform, '全网')
        
        return f"""请帮我检索{platform_str}关于"{keywords_str}"的最新舆情事件，要求：

1. 检索最近7天内的相关讨论和事件
2. 重点关注负面舆情、投诉、争议事件
3. 每个事件包含：标题、摘要、来源平台、发布时间、情感倾向、风险等级
4. 最多返回{limit}条结果
5. 优先返回有实质内容、有传播力的事件

请以JSON格式返回结果，格式如下：
[
  {{
    "title": "事件标题",
    "summary": "事件摘要（100字以内）",
    "platform": "来源平台",
    "publish_time": "发布时间（YYYY-MM-DD）",
    "sentiment": "positive/negative/neutral",
    "risk_level": "high/medium/low",
    "keywords": "相关关键词",
    "url": "原文链接（如有）"
  }}
]"""
    
    def _get_system_prompt(self):
        """获取系统提示词"""
        return """你是一个专业的舆情分析专家，擅长从全网检索和分析舆情事件。
要求：
1. 只返回真实存在的、可验证的舆情事件
2. 客观中立，不加入主观臆断
3. 严格按照要求的JSON格式返回
4. 对于不确定的信息，标注为"待核实"
5. 重点关注与广州太古汇相关的真实舆情事件"""
    
    def _parse_ai_response(self, response):
        """解析AI返回的结果"""
        if not response:
            return []
        
        try:
            # 尝试提取JSON部分
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                results = json.loads(json_str)
                return results if isinstance(results, list) else []
        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
        
        return []
    
    def _save_to_case_library(self, results):
        """保存到案例库"""
        try:
            import sqlite3
            db_path = main_db_path()  # P0-DBISO-01 隔离重定向（默认仍为 data/monitor.db）
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            for result in results:
                try:
                    # 检查是否已存在
                    cursor.execute("SELECT id FROM web_events WHERE title = ?", (result.get('title', ''),))
                    if cursor.fetchone():
                        continue
                    
                    # 插入新事件
                    cursor.execute("""
                        INSERT INTO web_events (title, summary, platform, risk_level, mention_count, first_seen, last_seen, status, keywords)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        result.get('title', ''),
                        result.get('summary', ''),
                        result.get('platform', 'unknown'),
                        result.get('risk_level', 'low'),
                        1,
                        result.get('publish_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'pending',
                        result.get('keywords', ''),
                    ))
                except Exception as e:
                    logger.error(f"保存案例失败: {e}")
            
            conn.commit()
            conn.close()
            logger.info(f"已保存 {len(results)} 条舆情事件到案例库")
            
        except Exception as e:
            logger.error(f"保存案例库失败: {e}")
    
    def get_search_history(self, limit=20):
        """获取搜索历史"""
        # 从学习引擎获取操作记录
        history = []
        for record in self.learning_engine.operation_log:
            if record.get('operation_type') == 'web_sentiment_search':
                history.append(record)
                if len(history) >= limit:
                    break
        return history


# 全局单例
_ai_learning_engine = None
_web_sentiment_search = None

def get_ai_learning_engine():
    """获取AI学习引擎单例"""
    global _ai_learning_engine
    if _ai_learning_engine is None:
        _ai_learning_engine = AILearningEngine()
    return _ai_learning_engine

def get_web_sentiment_search():
    """获取全网舆情检索单例"""
    global _web_sentiment_search
    if _web_sentiment_search is None:
        _web_sentiment_search = WebSentimentSearch()
    return _web_sentiment_search


# 测试
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=" * 60)
    print("豆包AI全网舆情检索与自学习进化模块")
    print("=" * 60)
    
    # 测试学习引擎
    engine = get_ai_learning_engine()
    status = engine.get_learning_status()
    print(f"\n学习状态:")
    print(f"  进化等级: {status['evolution_level']}")
    print(f"  总学习次数: {status['total_learning_count']}")
    print(f"  已学习操作类型: {status['learned_operation_types']}")
    print(f"  总体成功率: {status['success_rate']:.1%}")
    
    # 测试全网舆情检索
    print(f"\n测试全网舆情检索...")
    search = get_web_sentiment_search()
    result = search.search_public_opinion(keywords=['广州太古汇'], limit=5)
    print(f"检索结果: {result.get('ok', False)}, 数量: {result.get('total', 0)}")
    if result.get('results'):
        for i, item in enumerate(result['results'][:3]):
            print(f"  {i+1}. {item.get('title', '无标题')}")
