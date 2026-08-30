"""
传播主体分类器（V3.0 P1.1 传播主体体系）
归属：Z-Brand Core / ZBMP / 品牌智能层
目标：
  1. 实现 subject_type（传播主体身份）与 content_type（内容属性）的严格分离
  2. 统一传播主体分类：官方、KOS、KOL、KOC、普通用户、媒体、机构
  3. 为品牌传播分析提供主体维度的数据基础

设计原则（V3.0 基线要求）：
  - subject_type 与 content_type 严格分离
  - 正确示例：subject_type=KOL, content_type=UGC
  - 错误示例：user_type=UGC（混淆了主体身份和内容属性）
  - 主体判断基于账号特征（名称、认证、粉丝数、内容模式），不基于内容类型
  - 内容类型判断基于内容特征（文案、图片、互动模式），不基于账号身份

主体分类定义：
  - official（官方）：品牌官方账号、企业认证账号、商场/购物中心官方账号
  - kos（KOS）：Key Opinion Sales，品牌导购/销售顾问账号，以销售转化为目标
  - kol（KOL）：Key Opinion Leader，关键意见领袖，粉丝量大、影响力强
  - koc（KOC）：Key Opinion Consumer，关键意见消费者，粉丝量小但真实度高
  - normal_user（普通用户）：普通消费者账号，无明显影响力特征
  - media（媒体）：新闻媒体、自媒体大号、资讯类账号
  - institution（机构）：政府机构、行业协会、非营利组织等
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


# 主体类型定义
SUBJECT_TYPES = {
    'official': '官方',
    'kos': 'KOS',
    'kol': 'KOL',
    'koc': 'KOC',
    'normal_user': '普通用户',
    'media': '媒体',
    'institution': '机构',
}

# 内容类型定义（与现有content_type保持一致）
CONTENT_TYPES = {
    'ugc': 'UGC',
    'commercial': '商业',
    'official': '官方',
    'review': '测评',
    'experience': '体验',
    'complaint': '投诉',
    'event': '活动内容',
}

# 官方账号关键词
OFFICIAL_KEYWORDS = [
    '官方', '旗舰店', '专卖店', '购物中心', '商场', '百货', '广场',
    '太古汇', '太古里', '万象城', '万达', '银泰', '大悦城', '天环',
    'official', 'store', 'mall', 'plaza',
]

# 媒体账号关键词
MEDIA_KEYWORDS = [
    '新闻', '日报', '晚报', '电视台', '广播', '周刊', '杂志', '资讯',
    '爆料', '吃瓜', '热搜', '头条', '快报',
    'news', 'media', 'daily', 'times',
]

# 机构账号关键词
INSTITUTION_KEYWORDS = [
    '协会', '学会', '联合会', '商会', '基金会', '研究院', '研究所',
    '政府', '局', '委员会', '办公室', '中心',
    'association', 'institute', 'foundation', 'government',
]

# KOS特征关键词
KOS_KEYWORDS = [
    '导购', '销售', '顾问', '柜姐', '柜哥', 'BA', 'SA',
    '专柜', '门店', '店铺',
]


class SubjectClassifier:
    """传播主体分类器"""

    def __init__(self):
        self.official_keywords = OFFICIAL_KEYWORDS
        self.media_keywords = MEDIA_KEYWORDS
        self.institution_keywords = INSTITUTION_KEYWORDS
        self.kos_keywords = KOS_KEYWORDS

    def classify(self, author_name: str = '', author_desc: str = '',
                 followers: int = 0, is_verified: bool = False,
                 verified_type: str = '', content_pattern: str = '') -> Dict[str, Any]:
        """
        分类传播主体类型

        参数：
            author_name: 作者名称
            author_desc: 作者简介/描述
            followers: 粉丝数
            is_verified: 是否认证
            verified_type: 认证类型（企业/个人/媒体等）
            content_pattern: 内容模式（销售导向/内容创作/日常分享等）

        返回：
            {
                'subject_type': 'kol',  # 主体类型
                'subject_type_name': 'KOL',  # 主体类型中文名
                'confidence': 0.8,  # 置信度
                'reasons': ['粉丝数>10万', '内容创作导向'],  # 判断依据
                'content_type_hint': 'ugc',  # 内容类型建议（仅供参考，最终由content分类器决定）
            }
        """
        reasons = []
        confidence = 0.3  # 默认置信度

        # 合并文本用于关键词匹配
        full_text = f'{author_name} {author_desc} {verified_type}'.lower()

        # 1. 官方账号判断
        if self._match_official(full_text, verified_type):
            reasons.append('名称/认证包含官方关键词')
            confidence = max(confidence, 0.9)
            return self._result('official', confidence, reasons, 'official')

        # 2. 媒体账号判断
        if self._match_media(full_text, verified_type):
            reasons.append('名称/认证包含媒体关键词')
            confidence = max(confidence, 0.85)
            return self._result('media', confidence, reasons, 'ugc')

        # 3. 机构账号判断
        if self._match_institution(full_text, verified_type):
            reasons.append('名称/认证包含机构关键词')
            confidence = max(confidence, 0.85)
            return self._result('institution', confidence, reasons, 'official')

        # 4. KOS判断（销售导向）
        if self._match_kos(full_text, content_pattern):
            reasons.append('名称/内容包含销售/导购特征')
            confidence = max(confidence, 0.75)
            return self._result('kos', confidence, reasons, 'commercial')

        # 5. KOL/KOC/普通用户判断（基于粉丝数）
        if followers > 0:
            if followers >= 100000:
                reasons.append(f'粉丝数{followers}>10万')
                confidence = max(confidence, 0.8)
                return self._result('kol', confidence, reasons, 'ugc')
            elif followers >= 10000:
                reasons.append(f'粉丝数{followers}在1万-10万之间')
                confidence = max(confidence, 0.7)
                return self._result('kol', confidence, reasons, 'ugc')
            elif followers >= 1000:
                reasons.append(f'粉丝数{followers}在1千-1万之间')
                confidence = max(confidence, 0.65)
                return self._result('koc', confidence, reasons, 'ugc')
            else:
                reasons.append(f'粉丝数{followers}<1千')
                confidence = max(confidence, 0.6)
                return self._result('normal_user', confidence, reasons, 'ugc')

        # 6. 默认普通用户
        reasons.append('无明显主体特征，默认普通用户')
        return self._result('normal_user', confidence, reasons, 'ugc')

    def _match_official(self, text: str, verified_type: str) -> bool:
        """匹配官方账号"""
        if '企业' in verified_type or '机构' in verified_type:
            for kw in self.official_keywords:
                if kw.lower() in text:
                    return True
        for kw in self.official_keywords:
            if kw.lower() in text:
                return True
        return False

    def _match_media(self, text: str, verified_type: str) -> bool:
        """匹配媒体账号"""
        if '媒体' in verified_type or '新闻' in verified_type:
            return True
        for kw in self.media_keywords:
            if kw.lower() in text:
                return True
        return False

    def _match_institution(self, text: str, verified_type: str) -> bool:
        """匹配机构账号"""
        for kw in self.institution_keywords:
            if kw.lower() in text:
                return True
        return False

    def _match_kos(self, text: str, content_pattern: str) -> bool:
        """匹配KOS账号"""
        for kw in self.kos_keywords:
            if kw.lower() in text:
                return True
        if '销售' in content_pattern or '导购' in content_pattern or '转化' in content_pattern:
            return True
        return False

    def _result(self, subject_type: str, confidence: float,
                reasons: list, content_type_hint: str) -> Dict[str, Any]:
        """构造结果"""
        return {
            'subject_type': subject_type,
            'subject_type_name': SUBJECT_TYPES.get(subject_type, subject_type),
            'confidence': round(confidence, 2),
            'reasons': reasons,
            'content_type_hint': content_type_hint,
        }

    @staticmethod
    def get_subject_type_name(subject_type: str) -> str:
        """获取主体类型中文名"""
        return SUBJECT_TYPES.get(subject_type, subject_type)

    @staticmethod
    def get_all_subject_types() -> Dict[str, str]:
        """获取所有主体类型"""
        return SUBJECT_TYPES.copy()

    @staticmethod
    def get_all_content_types() -> Dict[str, str]:
        """获取所有内容类型"""
        return CONTENT_TYPES.copy()


# 全局单例
_classifier_instance: Optional[SubjectClassifier] = None

def get_subject_classifier() -> SubjectClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = SubjectClassifier()
    return _classifier_instance
