"""Lexical scoring and rank fusion for hybrid search.

Two independent rankings feed into ``reciprocal_rank_fusion``: a lexical
one from :func:`bm25_scores` (term overlap on the market's ``objet``) and
a semantic one from cosine similarity against the vector index (computed
in ``decp.index.store`` / ``decp.retrieval.search``). Fusing by rank
rather than by raw score avoids having to calibrate BM25 and cosine
similarity onto a common scale.
"""

from __future__ import annotations

import math
import re

_TOKEN_RE = re.compile(r"[a-zà-ÿ0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def bm25_scores(
    query: str,
    documents: dict[str, str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> dict[str, float]:
    """Score each document in ``documents`` (id -> text) against ``query``.

    A document that shares no term with the query gets a score of 0.0
    (never negative), so callers can drop non-matches with ``score > 0``.
    """
    query_terms = tokenize(query)
    doc_tokens = {doc_id: tokenize(text) for doc_id, text in documents.items()}
    doc_lengths = {doc_id: len(tokens) for doc_id, tokens in doc_tokens.items()}
    n_docs = len(doc_tokens)
    scores = dict.fromkeys(doc_tokens, 0.0)

    if n_docs == 0 or not query_terms:
        return scores

    avg_len = sum(doc_lengths.values()) / n_docs

    for term in set(query_terms):
        containing = [doc_id for doc_id, tokens in doc_tokens.items() if term in tokens]
        if not containing:
            continue
        idf = math.log((n_docs - len(containing) + 0.5) / (len(containing) + 0.5) + 1)
        for doc_id in containing:
            tokens = doc_tokens[doc_id]
            freq = tokens.count(term)
            length_norm = 1 - b + b * (doc_lengths[doc_id] / avg_len if avg_len else 0)
            denom = freq + k1 * length_norm
            scores[doc_id] += idf * (freq * (k1 + 1)) / denom if denom else 0.0

    return scores


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Combine several ranked id lists into one, by reciprocal rank.

    Each ``ranking`` is a list of document ids, best match first. A
    document appearing near the top of any ranking scores highly; one
    appearing in several rankings scores higher still. Returns
    ``(doc_id, score)`` pairs sorted best first.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
