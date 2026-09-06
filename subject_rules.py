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
        "region": "海南",
        "country": "中国",
        "store_type": "免税城",
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
    "hongkong_dfs": {
        "display_name": "香港DFS免税店",
        "region": "香港",
        "country": "中国",
        "store_type": "DFS免税店",
        "subject_words": [
            "香港DFS", "DFS香港", "DFS免税", "香港免税店",
            "尖沙咀DFS", "铜锣湾DFS", "DFS T广场", "DFS Galleria",
            "香港免税", "DFS香港店",
        ],
        "exclude_words": [
            "澳门DFS", "首尔DFS", "东京DFS", "新加坡DFS", "冲绳DFS",
        ],
        "collect_keywords": ["香港DFS", "DFS免税店 香港", "尖沙咀DFS", "香港免税购物"],
    },
    "macau_dfs": {
        "display_name": "澳门DFS免税店",
        "region": "澳门",
        "country": "中国",
        "store_type": "DFS免税店",
        "subject_words": [
            "澳门DFS", "DFS澳门", "澳门免税店", "澳门免税",
            "路氹DFS", "新濠天地DFS", "澳门T广场", "澳门DFS Galleria",
        ],
        "exclude_words": [
            "香港DFS", "首尔DFS", "东京DFS", "新加坡DFS",
        ],
        "collect_keywords": ["澳门DFS", "DFS免税店 澳门", "澳门免税购物", "路氹DFS"],
    },
    "seoul_dfs": {
        "display_name": "首尔DFS免税店",
        "region": "首尔",
        "country": "韩国",
        "store_type": "DFS免税店",
        "subject_words": [
            "首尔DFS", "DFS首尔", "韩国DFS", "首尔免税店",
            "明洞DFS", "乐天免税", "新罗免税", "韩国免税店",
            "首尔免税", "DFS Korea", "Seoul DFS",
        ],
        "exclude_words": [
            "香港DFS", "澳门DFS", "东京DFS", "济州DFS", "釜山DFS",
        ],
        "collect_keywords": ["首尔DFS", "韩国免税店", "明洞免税", "首尔免税购物"],
    },
    "tokyo_dfs": {
        "display_name": "东京DFS免税店",
        "region": "东京",
        "country": "日本",
        "store_type": "DFS免税店",
        "subject_words": [
            "东京DFS", "DFS东京", "日本DFS", "东京免税店",
            "银座DFS", "新宿DFS", "冲绳DFS", "日本免税店",
            "东京免税", "DFS Japan", "Tokyo DFS", "DFS旗下",
        ],
        "exclude_words": [
            "香港DFS", "澳门DFS", "首尔DFS", "大阪DFS", "京都DFS",
        ],
        "collect_keywords": ["东京DFS", "日本免税店", "银座免税", "东京免税购物"],
    },
}

ACTIVE_BRAND = "guangzhou_taikoo_hui"  # 生产安全默认=广州太古汇（CTH-POMS 生产主体，红线口径不得被弱化/切换）；
# 其他品牌（海南中免/DFS 等 KOS 多品牌）必须通过环境变量 ZBC_ACTIVE_BRAND 或 subject_hit_for_brand(brand_key=)
# 显式激活，禁止把全局默认改成非广州品牌，以免并行品牌线改变广州生产主体口径。


def get_active_brand() -> str:
    """获取当前激活品牌key。

    V2 P0-19: 委托给 SubjectContext 管理主体边界。
    active_brand 不再承担系统数据边界职责，仅作为兼容层返回 brand_key。
    真实的主体边界由 subject_context.get_subject_context() 统一管理。

    优先级（Shard D 请求级隔离）：
      1. 线程级 SubjectContext（由 Flask before_request 或 brand_scope 设置）
      2. 环境变量 ZBC_ACTIVE_BRAND
      3. CTH 默认 guangzhou_taikoo_hui
    """
    try:
        from subject_context import get_thread_context, get_subject_context
        ctx = get_thread_context()
        if ctx is not None:
            return ctx.brand_key
        return get_subject_context().brand_key
    except Exception:
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
    """严格主体判断：使用当前激活品牌配置，排除词优先一票否决，随后检查正向主体词。"""
    cfg = get_brand_config()
    fields = [_text(x) for x in (title, body, content, source_keyword, matched_keywords)]
    joined = ' '.join(fields).lower()
    for word in cfg.get("exclude_words", SUBJECT_EXCLUDE_WORDS):
        if word.lower() in joined:
            return False
    return any(word.lower() in field.lower() for field in fields for word in cfg.get("subject_words", SUBJECT_WORDS))


def subject_hit_note(note: dict) -> bool:
    return subject_hit(*(note.get(k, '') for k in SUBJECT_FIELDS))


def subject_reason(note: dict) -> str:
    cfg = get_brand_config()
    fields = [_text(note.get(k, '')) for k in SUBJECT_FIELDS]
    joined = ' '.join(fields).lower()
    for word in cfg.get("exclude_words", SUBJECT_EXCLUDE_WORDS):
        if word.lower() in joined:
            return f'主体排除词一票否决:{word}'
    for word in cfg.get("subject_words", SUBJECT_WORDS):
        if any(word.lower() in field.lower() for field in fields):
            return f'命中主体词:{word}'
    return f'未命中{cfg.get("display_name", "品牌")}主体词'


def _column(alias: str, field: str) -> str:
    prefix = f'{alias}.' if alias else ''
    # body/source_keyword/matched_keywords 是新增兼容字段；旧库会由 migration 自动补齐。
    return f"LOWER(COALESCE({prefix}{field}, ''))"


def _subject_sql_and_values(alias: str = '') -> tuple[str, list[str]]:
    """返回可直接拼接到 WHERE 的统一主体 SQL + 参数。
    V4 P0-01：委托品牌化版本，确保 Python/SQL/采集/报告/统计口径统一。
    V2 P0-1：接入 Domain Isolation，CTH 域强制主体保护。
    旧调用点无需修改，自动走当前激活品牌配置。"""
    brand = get_active_brand()
    # V2 P0-1: CTH 域隔离保护 — 仅当显式设置 ZBC_PRODUCT_ID=CTH 时强制主体
    # 默认尊重 ZBC_ACTIVE_BRAND 环境变量（多品牌 KOS 场景）
    import os
    if os.environ.get("ZBC_PRODUCT_ID") == "CTH" and brand != "guangzhou_taikoo_hui":
        brand = "guangzhou_taikoo_hui"
    return _subject_sql_and_values_for(brand, alias)


# 保留项目历史命名，避免旧模块/脚本调用断裂。
subject_sql_and_values = _subject_sql_and_values


def subject_policy_info(brand_key: str = "") -> dict:
    """V4 P0-01：返回当前主体策略元信息（subject_id/policy_version/reason）。
    所有主体判断结果应附带此信息，便于追溯口径。"""
    cfg = get_brand_config(brand_key)
    return {
        "subject_id": cfg.get("brand_key", get_active_brand()),
        "policy_version": cfg.get("policy_version", "1.0"),
        "subject_words_count": len(cfg.get("subject_words", SUBJECT_WORDS)),
        "exclude_words_count": len(cfg.get("exclude_words", SUBJECT_EXCLUDE_WORDS)),
        "active_brand": get_active_brand(),
    }


def _subject_sql_and_values_for(brand_key: str, alias: str = '') -> tuple[str, list[str]]:
    """品牌化主体 SQL：按品牌配置的 subject_words/exclude_words 生成 WHERE 子句。
    不修改 _subject_sql_and_values（保留广州太古汇历史口径），新增品牌链路（如海南中免）使用本函数。
    """
    cfg = get_brand_config(brand_key)
    sw = cfg.get("subject_words", SUBJECT_WORDS)
    ew = cfg.get("exclude_words", SUBJECT_EXCLUDE_WORDS)
    positives = []
    values: list[str] = []
    for field in SUBJECT_FIELDS:
        for word in sw:
            positives.append(f"{_column(alias, field)} LIKE ?")
            values.append(f'%{word.lower()}%')
    excludes = []
    for field in SUBJECT_FIELDS:
        for word in ew:
            excludes.append(f"{_column(alias, field)} LIKE ?")
            values.append(f'%{word.lower()}%')
    return f"({' OR '.join(positives)}) AND NOT ({' OR '.join(excludes)})", values


def subject_sql_and_values_for(brand_key: str = "", alias: str = '') -> tuple[str, list[str]]:
    """品牌化主体 SQL（默认当前激活品牌）。供 KOS/中免等品牌链路聚合查询使用。"""
    return _subject_sql_and_values_for(brand_key or get_active_brand(), alias)


def collect_keywords_for(brand_key: str = "") -> list[str]:
    """品牌采集关键词：优先 collect_keywords，其次取 subject_words。供 profile 采集任务生成。"""
    cfg = get_brand_config(brand_key)
    kws = cfg.get("collect_keywords") or []
    if not kws:
        kws = list(cfg.get("subject_words", []))
    return [k for k in kws if k]


def canonical_text(note: dict) -> str:
    return ' '.join(_text(note.get(k, '')) for k in SUBJECT_FIELDS).strip()


def subject_hit_text(text: str) -> bool:
    """单文本适配入口：兼容历史调用点（persist_rednote_data / persist_live）拼接后的全文。
    语义与 subject_hit 一致：排除词一票否决 + 任一正向主体词命中。
    将拼接文本整体作为 title 字段判定；若需按五字段精确判定请直接调用 subject_hit。
    """
    return subject_hit(title=text)
