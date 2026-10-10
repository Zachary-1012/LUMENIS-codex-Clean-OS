"""Source-grounded document analysis through the single SYSTEM AI Gateway."""
import hashlib
import json
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
        self.source_locator: Optional[Dict] = None
        self.source_row_sha256: Optional[str] = None


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


def extract_source_keyword_candidates(
    text: str, context_keywords: List[str] = None,
) -> List[Dict]:
    """Return deterministic, source-located keyword candidates without inference.

    Terms retain their exact spelling from the body. These are derived text
    candidates, not platform-native topics, popularity signals, or admissions.
    """
    if not isinstance(text, str) or not text:
        return []

    supplied_terms = (
        [term for term in context_keywords if isinstance(term, str) and term.strip()]
        if isinstance(context_keywords, (list, tuple)) else []
    )
    candidates = {}

    def add_candidate(term, kind, spans):
        if not isinstance(term, str) or not term or not spans:
            return
        current = candidates.get(term)
        if current is None or kind == "VERBATIM_BODY_HASHTAG_LITERAL":
            candidates[term] = {"kind": kind, "spans": spans}

    for term in _extract_keywords(text, supplied_terms):
        spans = [match.span() for match in re.finditer(re.escape(term), text)]
        add_candidate(term, "DERIVED_TEXT_KEYWORD", spans)

    hashtag_spans = {}
    for match in re.finditer(r"(?<!#)#[\w]+", text, flags=re.UNICODE):
        hashtag_spans.setdefault(match.group(0), []).append(match.span())
    for term, spans in hashtag_spans.items():
        add_candidate(term, "VERBATIM_BODY_HASHTAG_LITERAL", spans)

    english_terms = {}
    english_pattern = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*)(?![A-Za-z0-9])")
    for match in english_pattern.finditer(text):
        term = match.group(1)
        if sum(char.isascii() and char.isalpha() for char in term) >= 2:
            english_terms.setdefault(term, []).append(match.span(1))
    frequent_english = sorted(
        ((term, spans) for term, spans in english_terms.items() if len(spans) >= 2),
        key=lambda item: (-len(item[1]), item[1][0][0]),
    )
    for term, spans in frequent_english:
        add_candidate(term, "DERIVED_TEXT_KEYWORD", spans)

    results = []
    for term, candidate in list(candidates.items())[:20]:
        spans = candidate["spans"]
        results.append({
            "term": term,
            "kind": candidate["kind"],
            "body_locators": [
                {"unit": "source-body", "json_path": "$.body", "start": start,
                 "end": end, "offset_unit": "unicode-codepoint"}
                for start, end in spans[:5]
            ],
            "occurrence_count": len(spans),
            "platform_heat": None,
            "representative_demand": None,
            "admitted": False,
            "automatic_adoption": False,
            "owned_inference": "NOT_RUN",
            "algorithm_version": "deterministic-collector-keywords:v1",
        })
    return results


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


def extract_source_rows(parsed) -> List[AnalyzedNote]:
    """Create deterministic source excerpts for canonical row projection.

    This path performs no AI analysis. Sentiment/risk/summary remain
    UNKNOWN/NOT_RUN; user-visible AI analysis is a separate owned-Gateway job.
    """
    fmt = parsed.metadata.get("format", "")
    if fmt in ("excel", "csv") and parsed.tables:
        rows = analyze_table_rows(parsed, context_keywords=[])
        if rows:
            table = parsed.tables[0]
            has_header = bool(table and _looks_like_header(table[0]))
            headers = ([None if value is None else str(value) for value in table[0]]
                       if has_header else None)
            table_rows = table[1:] if has_header else table
            row_indices = []
            columns = _map_columns([str(value) for value in table[0]]) if table else {}
            for original_index, row in enumerate(table_rows, start=1 if has_header else 0):
                if not any(str(value).strip() for value in row):
                    continue

                def cell(key):
                    column = columns.get(key)
                    return (str(row[column]).strip()
                            if column is not None and column < len(row) and row[column] is not None
                            else "")

                if not cell("title") and not cell("content"):
                    continue
                row_indices.append((original_index, row))
            if len(row_indices) != len(rows):
                raise ValueError("DOCUMENT_ROW_PROJECTION_COUNT_MISMATCH")
            for note, (original_index, row) in zip(rows, row_indices):
                source_row = json.dumps(
                    {"headers": headers,
                     "values": [None if value is None else str(value) for value in row]},
                    ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                )
                note.raw_chunk = source_row
                note.source_locator = {
                    "unit": "parsed_table_row", "table_index": 0,
                    "row_index": original_index,
                }
                note.source_row_sha256 = hashlib.sha256(source_row.encode("utf-8")).hexdigest()
            return rows
    result: List[AnalyzedNote] = []
    source_text = str(parsed.text or "")
    search_from = 0
    for chunk in split_into_chunks(source_text, max_chunk_size=800):
        if not chunk.strip():
            continue
        start = source_text.find(chunk, search_from)
        if start < 0:
            raise ValueError("DOCUMENT_ROW_PROJECTION_LOCATOR_UNAVAILABLE")
        end = start + len(chunk)
        note = AnalyzedNote()
        note.title = _extract_title(chunk)
        note.content = chunk[:500]
        note.raw_chunk = chunk
        note.source_locator = {"unit": "parsed_text_range", "start": start, "end": end}
        note.source_row_sha256 = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        note.sentiment = "unknown"
        note.sentiment_score = None
        note.risk_level = "unknown"
        note.risk_score = None
        note.summary = ""
        note.topics = []
        note.keywords = []
        note.ai_provider = "unknown"
        note.analysis_status = "NOT_RUN"
        note.analysis_code = "SOURCE_ROW_PROJECTION_NOT_ANALYZED"
        note.keyword_method = "source_excerpt"
        result.append(note)
        search_from = end
    return result


def source_rows_fingerprint(parsed, rows: List[AnalyzedNote], *, count: int) -> str:
    """Bind preview row order and locators to the exact parsed source snapshot."""
    if type(count) is not int or count < 0 or count > len(rows):
        raise ValueError("DOCUMENT_PREVIEW_ROW_COUNT_INVALID")
    selected = rows[:count]
    if any(not row.source_locator or not row.source_row_sha256 for row in selected):
        raise ValueError("DOCUMENT_PREVIEW_ROW_LOCATOR_UNAVAILABLE")
    metadata = parsed.metadata if isinstance(parsed.metadata, dict) else {}
    source_sha256 = metadata.get("source_fingerprint")
    parsed_text_sha256 = metadata.get("parsed_text_sha256")
    if (not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
            or not isinstance(parsed_text_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", parsed_text_sha256)):
        raise ValueError("DOCUMENT_PREVIEW_SOURCE_FINGERPRINT_REQUIRED")
    payload = {
        "schema": "document-preview-rows/v1",
        "source_sha256": source_sha256,
        "parsed_text_sha256": parsed_text_sha256,
        "format": str(metadata.get("format") or ""),
        "parser": str(metadata.get("parser") or ""),
        "parser_version": str(metadata.get("parser_version") or ""),
        "preview_count": count,
        "rows": [
            {"index": index, "title": row.title, "content": row.content,
             "locator": row.source_locator, "source_row_sha256": row.source_row_sha256}
            for index, row in enumerate(selected)
        ],
    }
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
