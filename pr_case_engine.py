"""
公关案例引擎 - 全网舆情案例库和话术库管理
功能：
1. 案例库检索（按场景/等级/关键词）
2. 同类案例自动匹配（专报触发时）
3. 公关话术推荐（按场景）
4. ACT法则通用回复结构
5. 专报触发条件判断
"""
import json
import os
from typing import List, Dict, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
CASE_LIBRARY_FILE = os.path.join(ROOT, 'pr_case_library.json')
RESPONSE_TEMPLATES_FILE = os.path.join(ROOT, 'pr_response_templates.json')


class PREngine:
    """公关案例引擎"""
    
    def __init__(self):
        self.case_library = self._load_json(CASE_LIBRARY_FILE)
        self.response_templates = self._load_json(RESPONSE_TEMPLATES_FILE)
        self.cases = self.case_library.get('cases', [])
        self.templates = self.response_templates.get('templates', [])
        self.scenes = self.case_library.get('scenes', {})
        self.triggers = self.response_templates.get('special_report_triggers', {}).get('triggers', [])
    
    def _load_json(self, filepath: str) -> Dict:
        """加载JSON文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PR Engine] 加载 {filepath} 失败: {e}")
            return {}
    
    def get_all_cases(self) -> List[Dict]:
        """获取所有案例"""
        return self.cases
    
    def get_case_by_id(self, case_id: str) -> Optional[Dict]:
        """按ID获取案例"""
        for case in self.cases:
            if case.get('id') == case_id:
                return case
        return None
    
    def search_cases(self, scene: str = None, level: str = None, keyword: str = None) -> List[Dict]:
        """
        搜索案例
        Args:
            scene: 场景分类（service_attitude/activity_safety/food_safety等）
            level: 等级（critical/medium/low）
            keyword: 关键词（在事件/回应/启示中搜索）
        """
        results = self.cases
        
        if scene:
            results = [c for c in results if c.get('scene') == scene]
        
        if level:
            results = [c for c in results if c.get('level') == level]
        
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                c for c in results 
                if keyword_lower in c.get('event', '').lower()
                or keyword_lower in c.get('response', '').lower()
                or keyword_lower in c.get('insight', '').lower()
                or keyword_lower in c.get('name', '').lower()
            ]
        
        return results
    
    def match_similar_cases(self, note: Dict, top_n: int = 3) -> List[Dict]:
        """
        为笔记匹配同类案例
        Args:
            note: 笔记数据（含category/sentiment/risk_level/summary等）
            top_n: 返回前N个匹配案例
        Returns:
            匹配的案例列表，按相关度排序
        """
        # 1. 根据笔记分类确定场景
        scene = self._infer_scene(note)
        
        # 2. 根据风险等级筛选
        risk_level = note.get('risk_level', 'medium')
        
        # 3. 搜索同场景案例
        candidates = self.search_cases(scene=scene)
        
        # 4. 如果同场景案例不足，扩大搜索范围
        if len(candidates) < top_n:
            all_candidates = self.search_cases(keyword=note.get('summary', ''))
            for c in all_candidates:
                if c not in candidates:
                    candidates.append(c)
        
        # 5. 按等级匹配度排序
        def match_score(case):
            score = 0
            if case.get('scene') == scene:
                score += 10
            if case.get('level') == risk_level:
                score += 5
            elif case.get('level') == 'critical' and risk_level == 'high':
                score += 3
            return score
        
        candidates.sort(key=match_score, reverse=True)
        
        return candidates[:top_n]
    
    def _infer_scene(self, note: Dict) -> str:
        """根据笔记内容推断场景分类"""
        category = note.get('category', '')
        summary = note.get('summary', '') + note.get('title', '')
        summary_lower = summary.lower()
        
        # 食品安全
        if any(kw in summary_lower for kw in ['食品', '卫生', '老鼠', '虫子', '异物', '变质', '过期', '餐饮', '餐厅', '火锅', '寿司']):
            return 'food_safety'
        
        # 活动安全/秩序
        if any(kw in summary_lower for kw in ['活动', '排队', '拥挤', '摔倒', '受伤', '人流', '秩序', '展览', '快闪', '开业']):
            return 'activity_safety'
        
        # 服务态度/歧视
        if any(kw in summary_lower for kw in ['服务', '态度', '歧视', '嘲讽', '辱骂', '打人', '冲突', '柜姐', '店员', '员工', '穷逛', '买不起']):
            return 'service_attitude'
        
        # 内容/物料争议
        if any(kw in summary_lower for kw in ['海报', '标语', '广告', '物料', '洗手间', '导视', '谐音', '创意', '审核']):
            return 'content_audit'
        
        # 价格/规则争议
        if any(kw in summary_lower for kw in ['价格', '押金', '规则', '退款', '收费', '霸王条款', '凑重', '积分']):
            return 'price_rule'
        
        # 默认服务态度
        return 'service_attitude'
    
    def get_response_template(self, scene: str) -> Optional[Dict]:
        """按场景获取公关话术模板"""
        for template in self.templates:
            if template.get('scene') == scene:
                return template
        return None
    
    def recommend_response(self, note: Dict) -> Dict:
        """
        为笔记推荐公关话术
        Args:
            note: 笔记数据
        Returns:
            包含场景、话术公式、禁忌、示例、相关案例的推荐结果
        """
        scene = self._infer_scene(note)
        template = self.get_response_template(scene)
        similar_cases = self.match_similar_cases(note, top_n=3)
        
        return {
            'scene': scene,
            'scene_name': self.scenes.get(scene, scene),
            'template': template,
            'act_law': self.response_templates.get('act_law', {}),
            'similar_cases': similar_cases,
            'case_ids': [c.get('id') for c in similar_cases]
        }
    
    def check_special_report_trigger(self, notes: List[Dict], note: Dict = None) -> Dict:
        """
        检查是否触发专报条件
        Args:
            notes: 近期笔记列表（用于判断集中爆发）
            note: 当前笔记（用于判断单条触发）
        Returns:
            {triggered: bool, triggers: [...], reason: str}
        """
        triggered = []
        
        if note:
            # TRIG-01: 高互动负面
            if note.get('sentiment') == 'negative':
                engagement = (
                    int(note.get('likes', 0) or 0) +
                    int(note.get('comments', 0) or 0) * 3 +
                    int(note.get('collects', 0) or 0) +
                    int(note.get('shares', 0) or 0) * 5
                )
                if engagement >= 500:
                    triggered.append({
                        'code': 'TRIG-01',
                        'name': '高互动负面',
                        'detail': f'互动量{engagement}≥500'
                    })
            
            # TRIG-03: 敏感议题
            scene = self._infer_scene(note)
            if scene in ['food_safety', 'activity_safety']:
                triggered.append({
                    'code': 'TRIG-03',
                    'name': '敏感议题',
                    'detail': f'涉及{self.scenes.get(scene, scene)}敏感议题'
                })
        
        # TRIG-02: 负面集中爆发（24小时内≥3条）
        if notes:
            from datetime import datetime, timedelta
            now = datetime.now()
            recent_negative = [
                n for n in notes 
                if n.get('sentiment') == 'negative'
                and n.get('collected_at')
                and (now - datetime.fromisoformat(str(n.get('collected_at')).replace('Z', ''))).total_seconds() < 86400
            ]
            if len(recent_negative) >= 3:
                triggered.append({
                    'code': 'TRIG-02',
                    'name': '负面集中爆发',
                    'detail': f'24小时内负面笔记{len(recent_negative)}条≥3'
                })
        
        return {
            'triggered': len(triggered) > 0,
            'triggers': triggered,
            'reason': '; '.join([t['detail'] for t in triggered]) if triggered else '未触发专报条件'
        }
    
    def get_scenes(self) -> Dict:
        """获取所有场景分类"""
        return self.scenes
    
    def get_statistics(self) -> Dict:
        """获取案例库统计"""
        scene_stats = {}
        level_stats = {'critical': 0, 'medium': 0, 'low': 0}
        
        for case in self.cases:
            scene = case.get('scene', 'unknown')
            scene_stats[scene] = scene_stats.get(scene, 0) + 1
            level = case.get('level', 'unknown')
            if level in level_stats:
                level_stats[level] += 1
        
        return {
            'total_cases': len(self.cases),
            'total_templates': len(self.templates),
            'scene_stats': scene_stats,
            'level_stats': level_stats,
            'scenes': self.scenes
        }


# 全局单例
_pr_engine = None

def get_pr_engine() -> PREngine:
    """获取公关案例引擎单例"""
    global _pr_engine
    if _pr_engine is None:
        _pr_engine = PREngine()
    return _pr_engine


if __name__ == '__main__':
    engine = get_pr_engine()
    print("=== 公关案例引擎统计 ===")
    print(json.dumps(engine.get_statistics(), ensure_ascii=False, indent=2))
    print("\n=== 测试案例匹配 ===")
    test_note = {
        'title': '顾客在餐厅发现异物',
        'summary': '顾客在火锅中发现疑似异物，视频传播',
        'sentiment': 'negative',
        'risk_level': 'high',
        'category': '餐饮'
    }
    result = engine.recommend_response(test_note)
    print(f"场景: {result['scene_name']}")
    print(f"话术公式: {result['template']['formula'] if result['template'] else '无'}")
    print(f"匹配案例: {result['case_ids']}")
