"""Platform-neutral Context Intelligence Engine (shadow-only).

The engine converts an already-collected note and its public comment context
into explainable derived signals. It never changes subject filtering, creates
an authoritative event, makes legal/account-guilt conclusions, enriches PII,
or performs network calls.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List

SENTIMENT = {
    "positive": ("喜欢", "好看", "推荐", "惊喜", "满意", "值得", "种草", "绝了"),
    "negative": ("失望", "避雷", "投诉", "太贵", "差", "糟糕", "排队", "踩雷", "不推荐"),
}
INTENTS = {
    "complaint": ("投诉", "避雷", "失望", "售后", "服务差", "态度差", "退款"),
    "recommendation": ("推荐", "值得", "种草", "安利", "必买", "推荐去"),
    "comparison": ("相比", "比", "不如", "更好", "同款", "竞品", "对比"),
    "question": ("怎么", "哪里", "多少", "什么时候", "有没有", "求问", "请问"),
    "experience": ("体验", "去了", "到店", "打卡", "逛了", "吃了", "买了"),
}
EVENT_CUES = {
    "opening": ("开业", "新店", "首店", "来了", "开门"),
    "campaign": ("活动", "展览", "周年", "联名", "快闪", "发布会"),
    "service_issue": ("投诉", "排队", "停车", "服务", "售后", "故障"),
    "product": ("新品", "上新", "限定", "发售", "价格"),
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _hits(text: str, words: Iterable[str]) -> List[str]:
    return [word for word in words if word and word in text]


def _bigrams(text: str) -> List[str]:
    counter: Counter[str] = Counter()
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        for i in range(len(segment) - 1):
            counter[segment[i:i + 2]] += 1
    return [token for token, _ in counter.most_common(8)]


def analyze_context(note: Dict[str, Any], comments: Iterable[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    comments = list(comments or note.get("comment_list") or [])
    title = _text(note.get("title"))
    content = _text(note.get("content"))
    note_text = f"{title} {content}".strip()
    comment_texts: List[str] = []
    for item in comments:
        value = item if isinstance(item, str) else (item.get("content") or item.get("text") or item.get("comment"))
        value = _text(value)
        if value:
            comment_texts.append(value)

    combined = " ".join([note_text, *comment_texts]).strip()
    sentiment_hits = {key: _hits(combined, words) for key, words in SENTIMENT.items()}
    pos, neg = len(sentiment_hits["positive"]), len(sentiment_hits["negative"])
    dominant = "positive" if pos > neg else "negative" if neg > pos else "neutral"
    intent_hits = {key: _hits(combined, words) for key, words in INTENTS.items()}
    event_hits = {key: _hits(combined, words) for key, words in EVENT_CUES.items()}

    event_candidates = [
        {
            "event_signal": event_type,
            "evidence": hits[:5],
            "source": "context_rule",
            "confidence": min(0.9, 0.45 + 0.1 * len(hits)),
        }
        for event_type, hits in event_hits.items() if hits
    ]

    comment_signals = {
        "comment_count": len(comment_texts),
        "question_count": sum("?" in x or "？" in x for x in comment_texts),
        "complaint_count": sum(bool(_hits(x, INTENTS["complaint"])) for x in comment_texts),
        "recommendation_count": sum(bool(_hits(x, INTENTS["recommendation"])) for x in comment_texts),
        "comparison_count": sum(bool(_hits(x, INTENTS["comparison"])) for x in comment_texts),
    }

    return {
        "schema_version": "context-intelligence.v1",
        "source_note_id": _text(note.get("note_id")),
        "context": {
            "note_length": len(note_text),
            "comment_count": len(comment_texts),
            "dominant_sentiment": dominant,
            "intent_hits": intent_hits,
            "event_hits": event_hits,
            "topic_fingerprint": _bigrams(combined),
        },
        "comment_signals": comment_signals,
        "event_candidates": event_candidates,
        "provenance": {
            "method": "deterministic_shadow_rules",
            "model_version": None,
            "external_call": False,
            "pii_enrichment": False,
            "authoritative": False,
        },
    }


def to_event_metadata(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return non-authoritative metadata; EventGraph remains the source of truth."""
    return {"context_intelligence": {
        "schema_version": context.get("schema_version"),
        "event_candidates": context.get("event_candidates", []),
        "comment_signals": context.get("comment_signals", {}),
        "dominant_sentiment": context.get("context", {}).get("dominant_sentiment", "neutral"),
        "provenance": context.get("provenance", {}),
    }}
