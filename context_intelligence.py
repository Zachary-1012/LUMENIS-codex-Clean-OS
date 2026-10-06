"""
LUMENIS compatibility Context Intelligence Engine (shadow / non-invasive)

Purpose
-------
Turn a note + comments into structured context signals that can feed the
existing EventGraph/Risk/Report layers without changing the production path.

Design rules
------------
1. Subject filtering remains upstream and authoritative.
2. This module never decides legal violation / cyberbullying / account guilt.
3. It produces explainable signals, not final conclusions.
4. No external network calls, model calls, or PII enrichment.
5. Integration must remain behind a feature gate until regression tests pass.

Inspired by the research review of Xiaohongshu's AI/context products and
open-source multimodal work, but intentionally platform-neutral.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List


_SENTIMENT_WORDS = {
    "positive": {"喜欢", "好看", "推荐", "惊喜", "满意", "值得", "种草", "终于来了", "绝了"},
    "negative": {"失望", "避雷", "投诉", "太贵", "差", "糟糕", "恶心", "排队", "踩雷", "不推荐"},
}

_INTENT_RULES = {
    "complaint": ("投诉", "避雷", "失望", "售后", "服务差", "态度差", "退款"),
    "recommendation": ("推荐", "值得", "种草", "安利", "必买", "推荐去"),
    "comparison": ("相比", "比", "不如", "更好", "同款", "竞品", "对比"),
    "question": ("怎么", "哪里", "多少", "什么时候", "有没有", "求问", "请问"),
    "experience": ("体验", "去了", "到店", "打卡", "逛了", "吃了", "买了"),
}

_EVENT_CUES = {
    "opening": ("开业", "新店", "首店", "来了", "开门"),
    "campaign": ("活动", "展览", "周年", "联名", "快闪", "发布会"),
    "service_issue": ("投诉", "排队", "停车", "服务", "售后", "故障"),
    "product": ("新品", "上新", "限定", "发售", "价格"),
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _contains(text: str, words: Iterable[str]) -> List[str]:
    return [word for word in words if word and word in text]


def _token_bigrams(text: str) -> Counter:
    """Small deterministic topic fingerprint; intentionally not an NLP model."""
    counter: Counter = Counter()
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        for i in range(len(segment) - 1):
            counter[segment[i : i + 2]] += 1
    return counter


def analyze_context(note: Dict[str, Any], comments: Iterable[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Build an explainable context object from a note and optional comments.

    Output is safe to store as a derived feature object. It contains no
    account-level inference and no personal-data enrichment.
    """
    comments = list(comments or note.get("comment_list") or [])
    title = _text(note.get("title"))
    content = _text(note.get("content"))
    note_text = f"{title} {content}".strip()
    comment_texts = []
    for comment in comments:
        if isinstance(comment, dict):
            value = _text(comment.get("content") or comment.get("text") or comment.get("comment"))
        else:
            value = _text(comment)
        if value:
            comment_texts.append(value)

    combined = " ".join([note_text, *comment_texts])
    intent_hits = {
        intent: _contains(combined, cues)
        for intent, cues in _INTENT_RULES.items()
    }
    event_hits = {
        event_type: _contains(combined, cues)
        for event_type, cues in _EVENT_CUES.items()
    }

    sentiment_hits = {
        polarity: _contains(combined, words)
        for polarity, words in _SENTIMENT_WORDS.items()
    }
    sentiment_counts = {k: len(v) for k, v in sentiment_hits.items()}
    if sentiment_counts["positive"] > sentiment_counts["negative"]:
        dominant_sentiment = "positive"
    elif sentiment_counts["negative"] > sentiment_counts["positive"]:
        dominant_sentiment = "negative"
    else:
        dominant_sentiment = "neutral"

    # Comment-derived signals: useful for EventGraph, but deliberately bounded.
    comment_signals = {
        "comment_count": len(comment_texts),
        "question_count": sum("?" in x or "？" in x for x in comment_texts),
        "complaint_count": sum(bool(_contains(x, _INTENT_RULES["complaint"])) for x in comment_texts),
        "recommendation_count": sum(bool(_contains(x, _INTENT_RULES["recommendation"])) for x in comment_texts),
        "comparison_count": sum(bool(_contains(x, _INTENT_RULES["comparison"])) for x in comment_texts),
    }

    # Event candidates are signals only. The existing EventGraph remains the
    # authoritative persistence/relationship layer.
    candidates: List[Dict[str, Any]] = []
    for event_type, hits in event_hits.items():
        if hits:
            candidates.append({
                "event_signal": event_type,
                "evidence": hits[:5],
                "source": "context_rule",
                "confidence": min(0.9, 0.45 + 0.1 * len(hits)),
            })

    topics = [x for x, _ in _token_bigrams(combined).most_common(8)]

    return {
        "schema_version": "context-intelligence.v1",
        "source_note_id": _text(note.get("note_id")),
        "context": {
            "note_length": len(note_text),
            "comment_count": len(comment_texts),
            "dominant_sentiment": dominant_sentiment,
            "intent_hits": intent_hits,
            "event_hits": event_hits,
            "topic_fingerprint": topics,
        },
        "comment_signals": comment_signals,
        "event_candidates": candidates,
        "provenance": {
            "method": "deterministic_shadow_rules",
            "model_version": None,
            "external_call": False,
            "pii_enrichment": False,
        },
    }


def to_event_metadata(context: Dict[str, Any]) -> Dict[str, Any]:
    """Convert context output into non-authoritative EventGraph metadata."""
    return {
        "context_intelligence": {
            "schema_version": context.get("schema_version"),
            "event_candidates": context.get("event_candidates", []),
            "comment_signals": context.get("comment_signals", {}),
            "dominant_sentiment": context.get("context", {}).get("dominant_sentiment", "neutral"),
            "provenance": context.get("provenance", {}),
        }
    }
