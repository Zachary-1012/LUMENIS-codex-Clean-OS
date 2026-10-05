"""Source-grounded document analysis through the single SYSTEM AI Gateway."""
import re
from typing import List, Dict, Optional
from .parser import ParseResult, split_into_chunks


class AnalyzedNote:
    """分析后的笔记"""
    def __init__(self):
        self.title: str = ""
        self.content: str = ""
        self.author: str = "外部导入"
        self.publish_date: str = ""
        self.source_platform: str = "import"
        self.sentiment: str = "unknown"
        self.sentiment_score: Optional[float] = None
        self.risk_level: str = "unknown"
        self.risk_score: Optional[int] = None
        self.topics: List[str] = []
        self.category: str = ""
        self.keywords: List[str] = []
        self.summary: str = ""
        self.ai_provider: str = "unknown"
        self.analysis_status: str = "UNAVAILABLE"
        self.analysis_code: str = "OWNED_RUNTIME_NOT_BOUND"
        self.keyword_method: str = ""
        self.raw_chunk: str = ""


def analyze_text(text: str, context_keywords: List[str] = None) -> List[AnalyzedNote]:
    """
    分析文本，返回结构化笔记列表
    Text parsing continues without a model; absent owned inference remains
    explicitly unavailable and never becomes fabricated sentiment or summary.
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

    result = _ai_analyze(chunk, context_keywords)
    analysis = result.get("analysis") if result.get("status") == "COMPLETED" else None
    if isinstance(analysis, dict):
        note.title = str(analysis.get("title") or _extract_title(chunk))
        note.sentiment = str(analysis.get("sentiment") or "unknown")
        note.sentiment_score = analysis.get("sentiment_score")
        note.risk_level = str(analysis.get("risk_level") or "unknown")
        note.risk_score = analysis.get("risk_score")
        note.topics = analysis.get("topics") if isinstance(analysis.get("topics"), list) else []
        note.category = str(analysis.get("category") or "")
        note.keywords = analysis.get("keywords") if isinstance(analysis.get("keywords"), list) else []
        note.summary = str(analysis.get("summary") or "")
        note.ai_provider = "owned"
        note.analysis_status = "COMPLETED"
        note.analysis_code = ""
        note.keyword_method = "owned_model"
        return note

    note.title = _extract_title(chunk)
    note.sentiment = "unknown"
    note.sentiment_score = None
    note.risk_level = "unknown"
    note.risk_score = None
    note.summary = ""
    note.keywords = _extract_keywords(chunk, context_keywords)
    note.keyword_method = "deterministic_source_terms"
    note.ai_provider = "unknown"
    note.analysis_status = str(result.get("status") or "UNAVAILABLE")
    note.analysis_code = str(result.get("code") or "OWNED_ANALYSIS_NOT_COMPLETED")
    return note


def _ai_analyze(text: str, context_keywords: List[str] = None) -> dict:
    """Call the owned Gateway only; return explicit non-completion otherwise."""
    try:
        from lumenis.system.ai_gateway.core import run_owned_analysis

        prompt = text
        if context_keywords:
            prompt = "Registered task terms: " + ", ".join(
                str(value) for value in context_keywords if isinstance(value, str) and value.strip()
            ) + "\n\nSource text:\n" + text
        result = run_owned_analysis(text=prompt, analysis_type="summary")
    except Exception as exc:
        return {"status": "ERROR", "code": type(exc).__name__, "analysis": None}

    if (not isinstance(result, dict) or result.get("ok") is not True
            or result.get("status") != "COMPLETED"
            or not isinstance(result.get("analysis"), dict)):
        return {
            "status": str(result.get("status") or "ERROR") if isinstance(result, dict) else "ERROR",
            "code": str(result.get("code") or "OWNED_ANALYSIS_NOT_COMPLETED")
            if isinstance(result, dict) else "OWNED_GATEWAY_INVALID_RESPONSE",
            "analysis": None,
        }
    return {"status": "COMPLETED", "code": "", "analysis": result["analysis"]}


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
        # Table parsing is source extraction only. Do not turn keyword counts
        # into sentiment or relabel a source excerpt as an AI summary.
        note.sentiment = "unknown"
        note.sentiment_score = None
        note.risk_level = "unknown"
        note.risk_score = None
        note.keywords = _extract_keywords(text, context_keywords)
        note.topics = [k for k in (context_keywords or []) if k and k in text]
        note.summary = ""
        note.ai_provider = "unknown"
        note.analysis_status = "NOT_RUN"
        note.analysis_code = "STRUCTURED_ROW_ANALYSIS_NOT_RUN"
        note.keyword_method = "deterministic_source_terms"
        note.raw_chunk = text
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
