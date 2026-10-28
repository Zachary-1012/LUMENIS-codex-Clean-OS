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

# BM25 initialization and term-frequency scoring adapted from rank_bm25
# by Dorian Brown and contributors, Apache-2.0, revision
# 47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099 (rank_bm25.py).
# OEVIRA modifications: query-specific sparse postings, positive Lucene IDF,
# deterministic ties, multilingual original-text windows, no NumPy/process pool.
# Full upstream license/attribution is retained in THIRD_PARTY_NOTICES.md.
_BM25_UPSTREAM = 'dorianbrown/rank_bm25@47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099'


def terms(text):
    """Unicode words and CJK/Hangul ngrams; this is lexical tokenization."""
    text = unicodedata.normalize('NFKC', text).casefold()
    result = []
    for token in re.findall(r"[\u3400-\u9fff]+|[\uac00-\ud7a3]+|[^\W_]+(?:[-'][^\W_]+)*", text):
        if any('\u3400' <= char <= '\u9fff' for char in token):
            result.extend(token)
            result.extend(token[index:index + 2] for index in range(len(token) - 1))
        elif any('\uac00' <= char <= '\ud7a3' for char in token):
            # Retain the exact word and overlapping syllable pairs, so Korean
            # grammatical particles do not hide an otherwise exact lexical hit.
            result.append(token)
            if len(token) > 2:
                result.extend(token[index:index + 2] for index in range(len(token) - 1))
        else:
            result.append(token)
    return result


class _BM25Index:
    """Ephemeral rank_bm25 derivative over one already authorized snapshot.

    Each document is tokenized once. Only query-term postings survive indexing;
    no source body, cross-user cache or independent Canonical store is retained.
    """

    def __init__(self, documents, query_terms, *, is_cancelled=None):
        self.doc_len = []
        self.postings = {term: [] for term in query_terms}
        self.is_cancelled = is_cancelled
        for index, document in enumerate(documents):
            self.check_cancelled()
            frequencies = Counter(terms(document))
            self.doc_len.append(sum(frequencies.values()))
            for term in frequencies.keys() & self.postings.keys():
                self.postings[term].append((index, frequencies[term]))
        self.corpus_size = len(self.doc_len)
        self.avgdl = sum(self.doc_len) / self.corpus_size if self.corpus_size else 0

    def check_cancelled(self):
        if self.is_cancelled is not None and self.is_cancelled():
            raise RuntimeError('MEMORY_SEARCH_CANCELLED')

    def get_scores(self, *, k1=1.2, b=0.75):
        scores = {}
        average = self.avgdl or 1
        for postings in self.postings.values():
            self.check_cancelled()
            idf = math.log1p((self.corpus_size - len(postings) + 0.5) / (len(postings) + 0.5))
            for index, frequency in postings:
                normalization = k1 * (1 - b + b * self.doc_len[index] / average)
                scores[index] = scores.get(index, 0.0) + idf * frequency * (k1 + 1) / (frequency + normalization)
        return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def bm25(query, documents, *, k1=1.2, b=0.75, is_cancelled=None):
    """Return (source index, positive score), largest score first."""
    if (type(k1) not in (int, float) or not math.isfinite(k1) or k1 <= 0
            or type(b) not in (int, float) or not math.isfinite(b) or not 0 <= b <= 1):
        raise ValueError('MEMORY_BM25_PARAMETERS_INVALID')
    query_terms = list(dict.fromkeys(terms(query)))
    if not query_terms:
        return []
    return _BM25Index(documents, query_terms, is_cancelled=is_cancelled).get_scores(k1=k1, b=b)


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
    ranges = list(_passage_ranges(text, maximum_characters=maximum_characters, overlap=overlap))
    ranked = bm25(query, [text[start:end] for start, end in ranges])
    index = ranked[0][0] if ranked else 0
    start, end = ranges[index]
    return {'start': start, 'end': end, 'body_query_match': bool(ranked),
            'selection': 'BM25_ORIGINAL_SOURCE_WINDOW' if ranked else 'ORIGINAL_SOURCE_HEAD_NO_BODY_MATCH',
            'offset_unit': 'unicode_codepoint', 'source_characters': len(text)}


def _passage_ranges(text, *, maximum_characters=1200, overlap=160):
    last = max(0, len(text) - maximum_characters)
    previous = None
    for start in range(0, last + 1, maximum_characters - overlap):
        yield start, min(len(text), start + maximum_characters)
        previous = start
    if previous != last:
        yield last, len(text)


def _source_parts(row):
    # Some compatibility records repeat their complete body in summary/content.
    # Repetition must not increase their relevance or triple tokenization work.
    body = next((row[key] for key in ('text', 'content', 'summary')
                 if type(row.get(key)) is str and row[key].strip()), '')
    metadata = []
    for key in ('title', 'tags'):
        value = row.get(key)
        if type(value) is list:
            value = ' '.join(item for item in value if type(item) is str)
        if type(value) is str and value.strip() and value != body:
            metadata.append(value)
    return body, '\n'.join(metadata)


def lexical_search(query, rows, *, limit, is_cancelled=None):
    """Rank original passages, then return each source once with its identity.

    A long document competes by its relevant passages rather than its total
    length. Sources with identical text retain separate provenance. The complete
    snapshot is authorized by the caller before ranking and rechecked afterward.
    """
    if type(limit) is not int or limit < 0:
        raise ValueError('MEMORY_SEARCH_LIMIT_INVALID')
    from lumenis.system.ai_gateway.core import owned_retrieval_status
    capability = owned_retrieval_status()
    locations = []
    def passages():
        for source_index, row in enumerate(rows):
            body, metadata = _source_parts(row)
            if metadata:
                locations.append((source_index, None, None))
                yield metadata
            for start, end in _passage_ranges(body):
                locations.append((source_index, start, end))
                yield body[start:end]
    lexical = bm25(query, passages(), is_cancelled=is_cancelled)
    source_ranked, seen, previews = [], set(), {}
    for passage_index, score in lexical:
        source_index, start, end = locations[passage_index]
        if source_index in seen:
            continue
        seen.add(source_index)
        source_ranked.append((source_index, score))
        body = _source_parts(rows[source_index])[0]
        previews[source_index] = (original_passage(query, body) if start is None else
            {'start': start, 'end': end, 'offset_unit': 'unicode_codepoint', 'body_query_match': True,
             'selection': 'BM25_ORIGINAL_SOURCE_WINDOW', 'source_characters': len(body)})
    # An explicitly empty query lists the authorized source set. Punctuation-only
    # input is an unmatched query, not implicit permission to list everything.
    selected = reciprocal_rank_fusion(source_ranked) if query.strip() else [(index, None) for index in range(len(rows))]
    report = {
        'mode': 'BM25_ONLY', 'lexical': 'BM25', 'fusion': 'RRF',
        'dense': capability['embedding']['state'], 'cross_encoder': capability['cross_encoder']['state'],
        'gateway_capabilities': capability,
        'authorized_candidates': len(rows), 'lexical_matches': len(source_ranked),
        'scored_passages': len(locations), 'matched_passages': len(lexical),
        'neural_retrieval_performed': False, 'index_persistence': 'REBUILT_FROM_VERIFIED_SOURCES',
        'tokenization': 'unicode_words_cjk_hangul_ngrams_v2', 'lexical_implementation': _BM25_UPSTREAM,
        'ranked_passages': [previews.get(index) for index, _ in selected[:limit]],
    }
    from lumenis.ai_hub.context_pack import digest
    report['source_snapshot_sha256'] = digest(rows)
    report['query_sha256'] = digest(query)
    return [rows[index] for index, _ in selected[:limit]], report
