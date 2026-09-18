"""
AI分析器
对导入的文本进行：实体识别、情感分析、自动打标签、关联话题/事件
对接现有 ark_llm.py
"""
import re
import json
from typing import List, Dict
from .parser import ParseResult, split_into_chunks


class AnalyzedNote:
    """分析后的笔记"""
    def __init__(self):
        self.title: str = ""
        self.content: str = ""
        self.author: str = "外部导入"
        self.publish_date: str = ""
        self.source_platform: str = "import"
        self.sentiment: str = "neutral"  # positive/negative/neutral
        self.sentiment_score: float = 0.0
        self.topics: List[str] = []
        self.category: str = ""
        self.keywords: List[str] = []
        self.summary: str = ""
        self.raw_chunk: str = ""


def analyze_text(text: str, context_keywords: List[str] = None) -> List[AnalyzedNote]:
    """
    分析文本，返回结构化笔记列表
    优先用AI分析，回退到规则分析
    """
    chunks = split_into_chunks(text, max_chunk_size=800)
    results = []
    for chunk in chunks:
        note = _analyze_chunk(chunk, context_keywords)
        if note.title or note.content:
            results.append(note)
    return results


def _analyze_chunk(chunk: str, context_keywords: List[str] = None) -> AnalyzedNote:
    """分析单个文本块"""
    note = AnalyzedNote()
    note.raw_chunk = chunk
    note.content = chunk[:500] if len(chunk) > 500 else chunk

    # 尝试用AI分析
    try:
        ai_result = _ai_analyze(chunk, context_keywords)
        if ai_result:
            note.title = ai_result.get("title", _extract_title(chunk))
            note.sentiment = ai_result.get("sentiment", "neutral")
            note.sentiment_score = ai_result.get("sentiment_score", 0.0)
            note.topics = ai_result.get("topics", [])
            note.category = ai_result.get("category", "")
            note.keywords = ai_result.get("keywords", [])
            note.summary = ai_result.get("summary", chunk[:100])
            return note
    except Exception:
        pass

    # 规则分析回退
    note.title = _extract_title(chunk)
    note.sentiment = _rule_sentiment(chunk)
    note.keywords = _extract_keywords(chunk, context_keywords)
    note.summary = chunk[:100]
    return note


def _ai_analyze(text: str, context_keywords: List[str] = None) -> dict:
    """调用AI分析（对接现有ark_llm.py）"""
    try:
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from ark_llm import analyze_sentiment, extract_keywords

        sentiment_result = analyze_sentiment(text)
        keywords_result = extract_keywords(text)

        return {
            "title": _extract_title(text),
            "sentiment": sentiment_result.get("sentiment", "neutral"),
            "sentiment_score": sentiment_result.get("score", 0.0),
            "keywords": keywords_result.get("keywords", []),
            "topics": context_keywords or [],
            "summary": text[:100],
        }
    except Exception:
        return None


def _extract_title(text: str) -> str:
    """从文本中提取标题（第一行或最长句子）"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return ""
    # 第一行如果较短，作为标题
    if len(lines[0]) < 50:
        return lines[0]
    # 否则取最长的句子前30字
    longest = max(lines, key=len)
    return longest[:30] + ("..." if len(longest) > 30 else "")


def _rule_sentiment(text: str) -> str:
    """规则情感分析"""
    positive_words = ["好", "赞", "喜欢", "满意", "优秀", "推荐", "不错", "方便", "舒适", "热闹"]
    negative_words = ["差", "烂", "失望", "糟糕", "投诉", "问题", "故障", "拥挤", "贵", "难吃"]
    pos_count = sum(text.count(w) for w in positive_words)
    neg_count = sum(text.count(w) for w in negative_words)
    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"


def _extract_keywords(text: str, context_keywords: List[str] = None) -> List[str]:
    """规则关键词提取"""
    keywords = []
    if context_keywords:
        for kw in context_keywords:
            if kw in text:
                keywords.append(kw)
    # 简单提取高频词（2-4字词）
    words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)
    from collections import Counter
    freq = Counter(words)
    for word, count in freq.most_common(10):
        if count >= 2 and word not in keywords and len(word) >= 2:
            keywords.append(word)
    return keywords[:10]


def match_existing_topics(notes: List[AnalyzedNote], topics: List[str]) -> Dict[str, List[int]]:
    """将分析后的笔记关联到已有话题"""
    matches = {t: [] for t in topics}
    for i, note in enumerate(notes):
        for topic in topics:
            if topic in note.content or topic in note.title or topic in note.keywords:
                matches[topic].append(i)
    return matches


# ============ 表格型文件按行成稿 ============
# 中文/英文表头模糊映射，覆盖常见导出列名
_COLUMN_ALIASES = {
    "title":   ["标题", "主题", "名称", "笔记标题", "title", "subject", "name"],
    "content": ["正文", "内容", "文本", "描述", "笔记内容", "评论内容", "content", "text", "body", "desc"],
    "author":  ["作者", "昵称", "用户", "账号", "博主", "author", "nickname", "user", "account"],
    "date":    ["发布日期", "发布时间", "时间", "日期", "publish", "date", "time", "created"],
}


def _map_columns(header):
    """把表头行映射到 title/content/author/date 列下标，匹配不到返回 None。"""
    idx = {"title": None, "content": None, "author": None, "date": None}
    for col, cell in enumerate(header):
        h = str(cell).strip().lower()
        if not h:
            continue
        for key, aliases in _COLUMN_ALIASES.items():
            if idx[key] is None and any(a.lower() in h for a in aliases):
                idx[key] = col
    return idx


def _looks_like_header(header) -> bool:
    joined = " ".join(str(h) for h in header).lower()
    return any(a.lower() in joined for aliases in _COLUMN_ALIASES.values() for a in aliases)


def analyze_table_rows(parsed, context_keywords=None) -> List[AnalyzedNote]:
    """Excel/CSV：首行表头，后续每一行独立成一条笔记（避免整表被合并成一条）。"""
    if not parsed.tables:
        return []
    table = parsed.tables[0]
    if not table:
        return []
    idx = _map_columns([str(c) for c in table[0]])
    rows = table[1:] if _looks_like_header(table[0]) else table
    notes = []
    for row in rows:
        if not any(str(c).strip() for c in row):
            continue

        def cell(key):
            i = idx.get(key)
            return str(row[i]).strip() if (i is not None and i < len(row) and row[i] is not None) else ""

        title, content = cell("title"), cell("content")
        if not title and not content:
            continue
        text = f"{title}。{content}" if title else content
        note = AnalyzedNote()
        note.title = title or (content[:30] + ("..." if len(content) > 30 else ""))
        note.content = content or title
        note.author = cell("author") or "外部导入"
        note.publish_date = cell("date")
        note.source_platform = "import"
        note.sentiment = _rule_sentiment(text)
        note.keywords = _extract_keywords(text, context_keywords)
        note.topics = [k for k in (context_keywords or []) if k and k in text]
        note.summary = (content or title)[:100]
        notes.append(note)
    return notes


def analyze_parsed(parsed, context_keywords=None) -> List[AnalyzedNote]:
    """统一分析入口：表格型文件按行成稿，PDF/Word/TXT 走文本分块。"""
    fmt = parsed.metadata.get("format", "")
    if fmt in ("excel", "csv") and parsed.tables:
        rows = analyze_table_rows(parsed, context_keywords)
        if rows:
            return rows
    return analyze_text(parsed.text, context_keywords)
