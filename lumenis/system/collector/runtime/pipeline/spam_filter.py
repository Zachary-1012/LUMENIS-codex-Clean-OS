"""
水军/广告/灌水噪声过滤
过滤营销号、广告、灌水、无意义内容
"""
import re
from typing import Dict, List, Optional, Tuple


class SpamFilter:
    """水军过滤器"""
    
    def __init__(self):
        # 广告关键词
        self.ad_keywords = [
            '加微信', '加v', '加V', 'vx', 'VX', '私我', '私信',
            '代购', '代发', '代理', '加盟', '招商', '推广',
            '点击链接', '扫码', '二维码', '领取', '免费领',
            '优惠码', '折扣码', '优惠券', '限时', '秒杀',
            '淘宝', '拼多多', '京东', '抖音小店', '小黄车',
            '点赞关注', '互赞', '互粉', '涨粉', '刷赞',
        ]
        
        # 灌水模式
        self.spam_patterns = [
            r'^[哈啊哦嗯呵]+$',  # 纯语气词
            r'^(666|999|233|555)+$',  # 纯数字梗
            r'^[^\w\u4e00-\u9fff]+$',  # 纯符号
            r'(.+)\1{3,}',  # 重复3次以上
        ]
        
        # 营销号特征
        self.marketing_patterns = [
            r'关注.*获取.*',
            r'回复.*获取.*',
            r'点击.*查看.*',
            r'详情.*咨询.*',
            r'专业.*服务.*',
        ]
        
        # 低质量内容阈值
        self.min_content_length = 5
        self.max_ad_keyword_count = 2
    
    def is_spam(self, content: str, title: str = "", author: str = "") -> Tuple[bool, str]:
        """
        判断是否为水军/广告/灌水内容
        返回: (is_spam, reason)
        """
        text = f"{title} {content}".strip()
        
        if not text:
            return True, "空内容"
        
        # 1. 检查灌水模式
        for pattern in self.spam_patterns:
            if re.match(pattern, text.strip()):
                return True, f"灌水内容（模式: {pattern}）"
        
        # 2. 内容过短
        if len(text.strip()) < self.min_content_length:
            return True, f"内容过短（{len(text.strip())}字）"
        
        # 3. 广告关键词检测
        ad_count = 0
        found_keywords = []
        for kw in self.ad_keywords:
            if kw in text:
                ad_count += 1
                found_keywords.append(kw)
        
        if ad_count >= self.max_ad_keyword_count:
            return True, f"广告内容（关键词: {', '.join(found_keywords[:3])}）"
        
        # 4. 营销号模式检测
        for pattern in self.marketing_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"营销号内容（模式: {pattern}）"
        
        # 5. 无意义字符比例过高
        meaningful_chars = len(re.findall(r'[\u4e00-\u9fff\w]', text))
        if meaningful_chars / max(len(text), 1) < 0.3:
            return True, "无意义字符比例过高"
        
        return False, ""
    
    def filter_notes(self, notes: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        批量过滤笔记
        返回: (valid_notes, spam_notes)
        """
        valid = []
        spam = []
        
        for note in notes:
            content = note.get("content", "")
            title = note.get("title", "")
            author = note.get("author_nickname", "")
            
            is_spam, reason = self.is_spam(content, title, author)
            
            if is_spam:
                note["_spam"] = True
                note["_spam_reason"] = reason
                spam.append(note)
            else:
                note["_spam"] = False
                valid.append(note)
        
        return valid, spam
    
    def filter_comments(self, comments: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """批量过滤评论"""
        valid = []
        spam = []
        
        for comment in comments:
            content = comment.get("content", "")
            is_spam, reason = self.is_spam(content)
            
            if is_spam:
                comment["_spam"] = True
                comment["_spam_reason"] = reason
                spam.append(comment)
            else:
                comment["_spam"] = False
                valid.append(comment)
        
        return valid, spam
