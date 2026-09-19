"""
主体过滤 - 广州太古汇精准识别
排除词先于正向关键词，一票否决
爬虫可以抓到"上海太古汇"，但主体过滤决定是否入库
"""
import re
from typing import Dict, List, Tuple, Optional


class SubjectFilter:
    """主体过滤器"""
    
    def __init__(self):
        # 正向关键词（包含任一即可能相关）
        self.positive_keywords = [
            '广州太古汇', '太古汇广州', '广州太古',
            '太古汇', 'TaiKoo Hui', 'taikoo hui',
            '天环广场', '天河路383号', '天河路',
        ]
        
        # 排除词（包含任一即排除，一票否决）
        self.exclude_keywords = [
            '上海太古汇', '成都太古汇', '成都远洋太古里',
            '北京太古汇', '香港太古汇', '沈阳太古汇',
            '上海前滩太古里', '成都太古里', '北京三里屯太古里',
            '上海兴业太古汇',
        ]
        
        # 广州相关地标（辅助判断）
        self.guangzhou_landmarks = [
            '广州', '天河', '珠江新城', '体育西路',
            '石牌桥', '天环', '正佳', '万菱汇',
            '天河城', '广州塔', '花城汇',
        ]
        
        # 品牌关键词（场内品牌，辅助判断）
        self.brand_keywords = []  # 从brand_directory.json加载
    
    def load_brands(self, brand_directory_path: str):
        """加载场内品牌关键词"""
        try:
            import json
            with open(brand_directory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            brands = data.get('brands', data) if isinstance(data, dict) else data
            for brand in brands:
                if isinstance(brand, dict):
                    name = brand.get('brand_name', '')
                    name_cn = brand.get('brand_name_cn', '')
                    if name:
                        self.brand_keywords.append(name)
                    if name_cn:
                        self.brand_keywords.append(name_cn)
                elif isinstance(brand, str):
                    self.brand_keywords.append(brand)
            print(f"[SubjectFilter] 加载{len(self.brand_keywords)}个品牌关键词")
        except Exception as e:
            print(f"[SubjectFilter] 加载品牌失败: {e}")
    
    def is_excluded(self, text: str) -> Tuple[bool, str]:
        """检查是否被排除（一票否决）"""
        for kw in self.exclude_keywords:
            if kw in text:
                return True, f"排除词命中: {kw}"
        return False, ""
    
    def is_positive(self, text: str) -> Tuple[bool, str]:
        """检查是否包含正向关键词"""
        for kw in self.positive_keywords:
            if kw in text:
                return True, f"正向词命中: {kw}"
        return False, ""
    
    def has_guangzhou_context(self, text: str) -> bool:
        """检查是否有广州上下文"""
        for landmark in self.guangzhou_landmarks:
            if landmark in text:
                return True
        return False
    
    def has_brand_match(self, text: str) -> bool:
        """检查是否匹配场内品牌"""
        for brand in self.brand_keywords:
            if brand and brand in text:
                return True
        return False
    
    def verify(self, title: str, content: str = "", 
               author: str = "") -> Tuple[bool, str, float]:
        """
        主体验证
        返回: (is_related, reason, confidence)
        confidence: 0-1，置信度
        """
        text = f"{title} {content} {author}".strip()
        
        if not text:
            return False, "空内容", 0.0
        
        # 1. 排除词优先（一票否决）
        is_excluded, exclude_reason = self.is_excluded(text)
        if is_excluded:
            return False, exclude_reason, 0.0
        
        # 2. 正向关键词直接命中
        is_pos, pos_reason = self.is_positive(text)
        if is_pos:
            # 检查是否有广州上下文增强置信度
            if self.has_guangzhou_context(text):
                return True, f"{pos_reason} + 广州上下文", 0.95
            return True, pos_reason, 0.85
        
        # 3. 广州地标 + 品牌匹配（弱相关）
        if self.has_guangzhou_context(text) and self.has_brand_match(text):
            return True, "广州地标 + 场内品牌匹配", 0.6
        
        # 4. 只有广州地标（可能相关）
        if self.has_guangzhou_context(text):
            return False, "仅有广州地标，无太古汇关键词", 0.2
        
        return False, "无相关关键词", 0.0
    
    def filter_notes(self, notes: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        批量过滤笔记
        返回: (related_notes, excluded_notes)
        """
        related = []
        excluded = []
        
        for note in notes:
            title = note.get("title", "")
            content = note.get("content", "")
            author = note.get("author_nickname", "")
            
            is_rel, reason, confidence = self.verify(title, content, author)
            
            note["_subject_verified"] = is_rel
            note["_subject_reason"] = reason
            note["_subject_confidence"] = confidence
            
            if is_rel:
                related.append(note)
            else:
                excluded.append(note)
        
        return related, excluded


def filter_subject(notes, subject_hit) -> list:
    """模块级适配函数：兼容 SYSTEM Collector XHS live_engine.py 的调用契约
    filter_subject(notes, subject_hit) -> accepted_notes
    委托外部传入的 subject_hit 权威回调（subject_rules.subject_hit_text），
    不在采集器内重写主体口径（红线：主体过滤唯一入口）。"""
    accepted = []
    for note in notes:
        text = ' '.join(
            str(note.get(k, '')) for k in ('title', 'body', 'content', 'source_keyword', 'matched_keywords')
            if note.get(k)
        )
        if subject_hit(text):
            accepted.append(note)
    return accepted
