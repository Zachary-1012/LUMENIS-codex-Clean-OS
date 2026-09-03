"""广州太古汇主体口径：全系统唯一、可审计的硬过滤规则。

原则：
1. SUBJECT_EXCLUDE_WORDS 一票否决。
2. 五个业务字段任一命中 SUBJECT_WORDS 才算主体相关。
3. 任何展示、统计、事件、报告都应复用本模块。
"""
from __future__ import annotations

import re
from typing import Iterable

SUBJECT_WORDS = [
    '广州太古汇', '太古汇', '太古汇商场', '太古仓', '汇悦台',
    '太古汇保安', '太古汇停车场', '太古汇售后', '太古汇客服台',
    'LV太古汇', '香奈儿太古汇', '迪奥太古汇', 'Dior太古汇',
    '太古汇发廊', '太古汇日料', '太古汇理发店', '太古汇总监',
]

SUBJECT_EXCLUDE_WORDS = [
    '上海太古汇', '兴业太古汇', '上海兴业太古汇', '北京太古汇',
    '三里屯太古汇', '成都太古汇', '成都远洋太古汇', '远洋太古汇',
    '深圳太古汇', '香港太古汇', '太古城', '上海站', '上海静安',
    '上海静安区', '南京西路', '魔都', '新天地', '北京三里屯',
]

SUBJECT_FIELDS = ('title', 'body', 'content', 'source_keyword', 'matched_keywords')

# ============== 多品牌配置（KOS P1：海南中免/CDF 第一验证品牌）==============
# 原则：不破坏广州太古汇核心过滤；新增品牌独立配置，按需切换。
BRAND_PROFILES = {
    "guangzhou_taikoo_hui": {
        "display_name": "广州太古汇",
        "subject_words": SUBJECT_WORDS,
        "exclude_words": SUBJECT_EXCLUDE_WORDS,
        "collect_keywords": ["广州太古汇", "太古汇", "太古汇 探店", "太古汇 活动"],
    },
    "hainan_cdf": {
        "display_name": "海南中免/CDF",
        "subject_words": [
            "海南中免", "中免", "CDF", "cdf", "中国免税",
            "三亚国际免税城", "海口国际免税城", "三亚免税", "海口免税",
            "中免集团", "海南免税", "离岛免税",
        ],
        "exclude_words": [
            "中免集团总部", "北京中免", "上海中免", "深圳中免",
            "日上免税", "海旅免税", "深免", "中出服", "珠海免税",
        ],
        "collect_keywords": ["海南中免", "CDF 免税", "三亚国际免税城", "海口国际免税城", "离岛免税"],
    },
}

ACTIVE_BRAND = "guangzhou_taikoo_hui"  # 当前激活品牌，可通过环境变量或API切换


def get_active_brand() -> str:
    """获取当前激活品牌key。"""
    import os
    return os.environ.get("ZBC_ACTIVE_BRAND", ACTIVE_BRAND)


def get_brand_config(brand_key: str = "") -> dict:
    """获取指定品牌配置，默认当前激活品牌。"""
    key = brand_key or get_active_brand()
    return BRAND_PROFILES.get(key, BRAND_PROFILES["guangzhou_taikoo_hui"])


def subject_hit_for_brand(title="", body="", content="", source_keyword="", matched_keywords="", brand_key="") -> bool:
    """指定品牌的主体判断（不修改默认 subject_hit，保持广州太古汇硬过滤不变）。"""
    cfg = get_brand_config(brand_key)
    fields = [str(x or "") for x in (title, body, content, source_keyword, matched_keywords)]
    joined = " ".join(fields).lower()
    for word in cfg["exclude_words"]:
        if word.lower() in joined:
            return False
    return any(word.lower() in f.lower() for f in fields for word in cfg["subject_words"])



def _text(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, (list, tuple, set)):
        return ' '.join(str(x) for x in value)
    return str(value)


def subject_hit(
    title: object = '',
    body: object = '',
    content: object = '',
    source_keyword: object = '',
    matched_keywords: object = '',
) -> bool:
    """严格主体判断：排除词优先，一票否决；随后检查正向主体词。"""
    fields = [_text(x) for x in (title, body, content, source_keyword, matched_keywords)]
    joined = ' '.join(fields).lower()
    for word in SUBJECT_EXCLUDE_WORDS:
        if word.lower() in joined:
            return False
    return any(word.lower() in field.lower() for field in fields for word in SUBJECT_WORDS)


def subject_hit_note(note: dict) -> bool:
    return subject_hit(*(note.get(k, '') for k in SUBJECT_FIELDS))


def subject_reason(note: dict) -> str:
    fields = [_text(note.get(k, '')) for k in SUBJECT_FIELDS]
    joined = ' '.join(fields).lower()
    for word in SUBJECT_EXCLUDE_WORDS:
        if word.lower() in joined:
            return f'主体排除词一票否决:{word}'
    for word in SUBJECT_WORDS:
        if any(word.lower() in field.lower() for field in fields):
            return f'命中主体词:{word}'
    return '未命中广州太古汇主体词'


def _column(alias: str, field: str) -> str:
    prefix = f'{alias}.' if alias else ''
    # body/source_keyword/matched_keywords 是新增兼容字段；旧库会由 migration 自动补齐。
    return f"LOWER(COALESCE({prefix}{field}, ''))"


def _subject_sql_and_values(alias: str = '') -> tuple[str, list[str]]:
    """返回可直接拼接到 WHERE 的统一主体 SQL + 参数。"""
    positives = []
    values: list[str] = []
    for field in SUBJECT_FIELDS:
        for word in SUBJECT_WORDS:
            positives.append(f"{_column(alias, field)} LIKE ?")
            values.append(f'%{word.lower()}%')
    excludes = []
    for field in SUBJECT_FIELDS:
        for word in SUBJECT_EXCLUDE_WORDS:
            excludes.append(f"{_column(alias, field)} LIKE ?")
            values.append(f'%{word.lower()}%')
    return f"({' OR '.join(positives)}) AND NOT ({' OR '.join(excludes)})", values


# 保留项目历史命名，避免旧模块/脚本调用断裂。
subject_sql_and_values = _subject_sql_and_values


def canonical_text(note: dict) -> str:
    return ' '.join(_text(note.get(k, '')) for k in SUBJECT_FIELDS).strip()


def subject_hit_text(text: str) -> bool:
    """单文本适配入口：兼容历史调用点（persist_rednote_data / persist_live）拼接后的全文。
    语义与 subject_hit 一致：排除词一票否决 + 任一正向主体词命中。
    将拼接文本整体作为 title 字段判定；若需按五字段精确判定请直接调用 subject_hit。
    """
    return subject_hit(title=text)
