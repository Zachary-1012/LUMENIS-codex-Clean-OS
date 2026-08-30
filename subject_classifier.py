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
        分类传播主体类型（V2：多类型匹配+冲突解决）

        核心改进：
        - 先收集所有匹配的类型，再按优先级解决冲突
        - 媒体+官方同时匹配时，判定为媒体（如"羊城晚报官方账号"）
        - 机构+官方同时匹配时，判定为机构
        - 传统媒体关键词（日报/晚报/电视台）置信度更高
        """
        reasons = []
        confidence = 0.3

        full_text = f'{author_name} {author_desc} {verified_type}'.lower()

        # V2: 多类型匹配
        matches = {}

        official_match = self._match_official_detailed(full_text, verified_type)
        if official_match:
            matches['official'] = official_match

        media_match = self._match_media_detailed(full_text, verified_type)
        if media_match:
            matches['media'] = media_match

        institution_match = self._match_institution_detailed(full_text, verified_type)
        if institution_match:
            matches['institution'] = institution_match

        kos_match = self._match_kos_detailed(full_text, content_pattern)
        if kos_match:
            matches['kos'] = kos_match

        # 冲突解决
        if matches:
            resolved = self._resolve_conflicts(matches, full_text)
            subject_type = resolved['type']
            confidence = max(confidence, resolved['confidence'])
            reasons.extend(resolved['reasons'])

            content_hint_map = {
                'official': 'official',
                'media': 'ugc',
                'institution': 'official',
                'kos': 'commercial',
            }
            return self._result(subject_type, confidence, reasons,
                                content_hint_map.get(subject_type, 'ugc'))

        # KOL/KOC/普通用户判断（基于粉丝数）
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

        # 默认普通用户
        reasons.append('无明显主体特征，默认普通用户')
        return self._result('normal_user', confidence, reasons, 'ugc')

    def _resolve_conflicts(self, matches: dict, full_text: str) -> dict:
        """冲突解决：当多个类型同时匹配时，按优先级规则解决"""
        types = list(matches.keys())

        # 规则1：媒体 + 官方 → 媒体（如"羊城晚报官方账号"）
        if 'media' in matches and 'official' in matches:
            media_kw = matches['media']['matched_keywords']
            official_kw = matches['official']['matched_keywords']
            return {
                'type': 'media',
                'confidence': 0.9,
                'reasons': [
                    f'同时匹配媒体关键词{media_kw}和官方关键词{official_kw}',
                    '冲突解决：媒体+官方组合判定为媒体（"XX晚报官方账号"是媒体账号）',
                    f'媒体关键词更具体（{media_kw}），"官方"为通用后缀不改变媒体属性',
                ],
            }

        # 规则2：机构 + 官方 → 机构
        if 'institution' in matches and 'official' in matches:
            return {
                'type': 'institution',
                'confidence': 0.85,
                'reasons': [
                    '同时匹配机构关键词和官方关键词',
                    '冲突解决：机构+官方组合判定为机构（如"XX协会官方"是机构账号）',
                ],
            }

        # 规则3：媒体 + 机构 → 媒体
        if 'media' in matches and 'institution' in matches:
            return {
                'type': 'media',
                'confidence': 0.85,
                'reasons': [
                    '同时匹配媒体关键词和机构关键词',
                    '冲突解决：媒体+机构组合判定为媒体（媒体属性更明确）',
                ],
            }

        # 规则4：KOS + 官方 → KOS
        if 'kos' in matches and 'official' in matches:
            return {
                'type': 'kos',
                'confidence': 0.8,
                'reasons': [
                    '同时匹配KOS关键词和官方关键词',
                    '冲突解决：KOS+官方组合判定为KOS（导购/销售账号本质是KOS）',
                ],
            }

        # 规则5：单一匹配
        if len(types) == 1:
            t = types[0]
            return {
                'type': t,
                'confidence': matches[t]['confidence'],
                'reasons': [f'匹配{t}关键词：{matches[t]["matched_keywords"]}'],
            }

        # 规则6：其他多匹配情况，按置信度最高
        best_type = max(matches.keys(), key=lambda k: matches[k]['confidence'])
        return {
            'type': best_type,
            'confidence': matches[best_type]['confidence'],
            'reasons': [
                f'多类型匹配：{list(matches.keys())}',
                f'按置信度最高选择：{best_type}',
            ],
        }

    def _match_official_detailed(self, text: str, verified_type: str):
        """详细匹配官方账号"""
        matched = []
        for kw in self.official_keywords:
            if kw.lower() in text:
                matched.append(kw)
        if '企业' in verified_type or '机构' in verified_type:
            matched.append(f'认证类型:{verified_type}')
        if matched:
            return {'matched_keywords': matched, 'confidence': 0.9}
        return None

    def _match_media_detailed(self, text: str, verified_type: str):
        """详细匹配媒体账号"""
        matched = []
        for kw in self.media_keywords:
            if kw.lower() in text:
                matched.append(kw)
        if '媒体' in verified_type or '新闻' in verified_type:
            matched.append(f'认证类型:{verified_type}')
        if matched:
            strong_media = ['日报', '晚报', '电视台', '广播', '周刊', '杂志', '新闻']
            has_strong = any(kw in matched for kw in strong_media)
            conf = 0.9 if has_strong else 0.8
            return {'matched_keywords': matched, 'confidence': conf}
        return None

    def _match_institution_detailed(self, text: str, verified_type: str):
        """详细匹配机构账号"""
        matched = []
        for kw in self.institution_keywords:
            if kw.lower() in text:
                matched.append(kw)
        if matched:
            return {'matched_keywords': matched, 'confidence': 0.85}
        return None

    def _match_kos_detailed(self, text: str, content_pattern: str):
        """详细匹配KOS账号"""
        matched = []
        for kw in self.kos_keywords:
            if kw.lower() in text:
                matched.append(kw)
        if '销售' in content_pattern or '导购' in content_pattern or '转化' in content_pattern:
            matched.append(f'内容模式:{content_pattern}')
        if matched:
            return {'matched_keywords': matched, 'confidence': 0.75}
        return None

    # 保留旧接口兼容
    def _match_official(self, text: str, verified_type: str) -> bool:
        return self._match_official_detailed(text, verified_type) is not None

    def _match_media(self, text: str, verified_type: str) -> bool:
        return self._match_media_detailed(text, verified_type) is not None

    def _match_institution(self, text: str, verified_type: str) -> bool:
        return self._match_institution_detailed(text, verified_type) is not None

    def _match_kos(self, text: str, content_pattern: str) -> bool:
        return self._match_kos_detailed(text, content_pattern) is not None



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
