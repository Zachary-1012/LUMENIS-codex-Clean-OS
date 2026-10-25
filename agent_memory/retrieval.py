"""Rebuildable ranking over already authorized source snapshots.

Lexical ranking is deterministic BM25, never described as neural retrieval.
Dense vectors and cross-encoder scores must come from a separately admitted
Gateway capability; this module neither loads weights nor invents vectors.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter


def terms(text):
    """Unicode words plus CJK bigrams; keep negations, dates and numbers."""
    text = unicodedata.normalize('NFKC', text).casefold()
    result = []
    for token in re.findall(r"[\u3400-\u9fff]+|[^\W_]+(?:[-'][^\W_]+)*", text):
        if any('\u3400' <= char <= '\u9fff' for char in token):
            result.extend(token)
            result.extend(token[index:index + 2] for index in range(len(token) - 1))
        else:
            result.append(token)
    return result


def bm25(query, documents, *, k1=1.2, b=0.75):
    """Return (source index, positive score), largest score first."""
    query_terms = set(terms(query))
    if not query_terms or not documents:
        return []
    counters = [Counter(terms(document)) for document in documents]
    lengths = [sum(counter.values()) for counter in counters]
    average = sum(lengths) / len(lengths) or 1
    frequencies = {term: sum(term in counter for counter in counters) for term in query_terms}
    scored = []
    for index, counter in enumerate(counters):
        score = 0.0
        for term in query_terms:
            frequency = counter[term]
            if frequency:
                idf = math.log1p((len(counters) - frequencies[term] + 0.5) / (frequencies[term] + 0.5))
                score += idf * frequency * (k1 + 1) / (frequency + k1 * (1 - b + b * lengths[index] / average))
        if score:
            scored.append((index, score))
    return sorted(scored, key=lambda item: (-item[1], item[0]))


def dense_cosine(query_vector, document_vectors):
    """Cosine ranking for actual admitted embeddings; no lexical stand-in."""
    dimension = len(query_vector)
    def checked(vector):
        if (not dimension or len(vector) != dimension
                or any(type(value) not in (int, float) or not math.isfinite(value) for value in vector)):
            raise ValueError('MEMORY_DENSE_VECTOR_INVALID')
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm or not math.isfinite(norm):
            raise ValueError('MEMORY_DENSE_VECTOR_INVALID')
        return norm
    query_norm = checked(query_vector)
    scores = []
    for index, vector in enumerate(document_vectors):
        norm = checked(vector)
        score = sum(a * b for a, b in zip(query_vector, vector)) / (query_norm * norm)
        scores.append((index, score))
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def reciprocal_rank_fusion(*rankings, k=60):
    """Fuse ranks, never add incomparable BM25 and cosine scores."""
    if type(k) is not int or k < 1:
        raise ValueError('MEMORY_RRF_PARAMETER_INVALID')
    scores = {}
    for ranking in rankings:
        seen = set()
        for rank, (identity, _) in enumerate(ranking, 1):
            if identity in seen:
                raise ValueError('MEMORY_DUPLICATE_RANK_IDENTITY')
            seen.add(identity)
            scores[identity] = scores.get(identity, 0.0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def cross_encoder_rank(query, documents, fused, scorer, *, candidate_limit=60):
    """Run one admitted scorer over a bounded RRF candidate set."""
    if type(candidate_limit) is not int or not 1 <= candidate_limit <= 200:
        raise ValueError('MEMORY_RERANK_LIMIT_INVALID')
    selected = fused[:candidate_limit]
    scores = scorer([(query, documents[index]) for index, _ in selected])
    if (type(scores) is not list or len(scores) != len(selected)
            or any(type(score) not in (int, float) or not math.isfinite(score) for score in scores)):
        raise ValueError('MEMORY_RERANK_RESULT_INVALID')
    ranked = [(index, score) for (index, _), score in zip(selected, scores)]
    # Keep the RRF order when the cross-encoder gives equal scores.
    return sorted(ranked, key=lambda item: -item[1])


def original_passage(query, text, *, maximum_characters=1200, overlap=160):
    """Select a ranked original range; never synthesize or change its text.

    This is a display/reference window, not a replacement for mandatory user
    context. The original source version and full-body hash remain the owner.
    """
    if (type(query) is not str or type(text) is not str
            or type(maximum_characters) is not int or not 1 <= maximum_characters <= 64000
            or type(overlap) is not int or not 0 <= overlap < maximum_characters):
        raise ValueError('MEMORY_PASSAGE_PARAMETERS_INVALID')
    if not text:
        return None
    last = max(0, len(text) - maximum_characters)
    starts = list(range(0, last + 1, maximum_characters - overlap))
    if starts[-1] != last:
        starts.append(last)
    ranges = [(start, min(len(text), start + maximum_characters)) for start in starts]
    ranked = bm25(query, [text[start:end] for start, end in ranges])
    index = ranked[0][0] if ranked else 0
    start, end = ranges[index]
    return {'start': start, 'end': end, 'body_query_match': bool(ranked),
            'selection': 'BM25_ORIGINAL_SOURCE_WINDOW' if ranked else 'ORIGINAL_SOURCE_HEAD_NO_BODY_MATCH',
            'offset_unit': 'unicode_codepoint', 'source_characters': len(text)}


def lexical_search(query, rows, *, limit):
    from lumenis.system.ai_gateway.core import owned_retrieval_status
    capability = owned_retrieval_status()
    documents = ['\n'.join(str(row.get(key) or '') for key in
                 ('title', 'summary', 'content', 'text', 'tags')) for row in rows]
    lexical = bm25(query, documents)
    selected = reciprocal_rank_fusion(lexical) if terms(query) else [(index, None) for index in range(len(rows))]
    report = {
        'mode': 'BM25_ONLY', 'lexical': 'BM25', 'fusion': 'RRF',
        'dense': capability['embedding']['state'], 'cross_encoder': capability['cross_encoder']['state'],
        'gateway_capabilities': capability,
        'authorized_candidates': len(rows), 'lexical_matches': len(lexical),
        'neural_retrieval_performed': False, 'index_persistence': 'REBUILT_FROM_VERIFIED_SOURCES',
        'tokenization': 'unicode_words_cjk_unigrams_bigrams_v1',
    }
    from lumenis.ai_hub.context_pack import digest
    report['source_snapshot_sha256'] = digest(rows)
    report['query_sha256'] = digest(query)
    return [rows[index] for index, _ in selected[:limit]], report
